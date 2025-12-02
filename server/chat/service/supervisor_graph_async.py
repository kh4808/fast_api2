# server/chat/service/supervisor_graph_async.py - 비동기 Supervisor Graph
from typing import TypedDict, Optional
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import asyncio

import server.chat.service.groq_subgraph as groq_subgraph
from server.chat.service.tts_service import generate_tts_audio
from server.chat.service.chat_logic_service_async import handle_chat_flow_async
from server.core.executor import run_in_threadpool

from transformers import pipeline

load_dotenv()

# ============================================================================
# ✅ 모델 전역 로딩 (서버 시작 시 한 번만)
# ============================================================================
print("🔄 Loading CEFR classifier model...")
cefr_classifier = pipeline(
    "text-classification",
    model="dksysd/cefr-classifier",
    tokenizer="dksysd/cefr-classifier"
)
print("✅ CEFR classifier loaded")

# LLM 모델 (비동기 사용 가능)
CHAT_GENERATE_LLM = ChatOpenAI(model="gpt-4o")
SUMMARY_LLM = ChatOpenAI(model="gpt-4o-mini")
ANALYSIS_LLM = ChatOpenAI(model="gpt-4o-mini")

supervisor_llm = ChatOpenAI(model="gpt-4o")
podcast_app = groq_subgraph.build_podcast_graph()


class SupervisorState(TypedDict, total=False):
    user_input: str
    output: str
    audio_base64: str
    route: str
    userId: int
    chatNum: int
    chatOrder: int
    initialChat: bool
    history: str
    history_summary: str
    cefr_level: str


# ============================================================================
# ✅ 라우팅 결정 (비동기)
# ============================================================================
async def route_decision(state: SupervisorState) -> SupervisorState:
    """podcast or chat 분기 결정 (비동기)"""
    msg = [
        SystemMessage("""
            You are a routing assistant.
            Your task is to decide whether the user's input should be handled by the podcast generator or by the general chat assistant.

            1. When a user requests to create a podcast
            2. When the user wants to practice listening
            3. When a user requests a listening activity, such as a radio show

            In the above three cases, branch out to "podcast"

            Otherwise — for general questions, discussions, explanations, or normal chat —
            route to "chat".

            Respond with only one word: either "podcast" or "chat".
        """),
        HumanMessage(state["user_input"])
    ]

    # ✅ 비동기 LLM 호출
    response = await supervisor_llm.ainvoke(msg)
    route_raw = response.content.strip().lower()
    route = "podcast" if "podcast" in route_raw else "chat"

    print(f"[ROUTE] 🔀 Decided: {route}")
    return {**state, "route": route}


# ============================================================================
# ✅ 팟캐스트 실행 (동기 코드를 비동기로 래핑)
# ============================================================================
async def run_podcast(state: SupervisorState) -> SupervisorState:
    """팟캐스트 분기 (비동기)"""
    # TODO: podcast_app도 비동기로 전환 필요
    # 현재는 thread pool에서 실행
    res = await run_in_threadpool(
        podcast_app.invoke,
        {
            "user_input": state["user_input"],
            "history": "",
            "history_summary": "Radio show is started. You need to speak",
            "turn_count": 0
        }
    )
    script = res.get("history", "")

    # TTS는 동기이므로 thread pool에서 실행
    audio = await run_in_threadpool(generate_tts_audio, script)

    return {**state, "output": script, "audio_base64": audio, "route": "podcast"}


# ============================================================================
# ✅ CEFR 레벨 예측 (CPU 집약적, thread pool에서 실행)
# ============================================================================
async def predict_cefr_level_async(user_input: str) -> str:
    """
    HuggingFace CEFR 분류 모델로 문장의 CEFR 레벨을 예측 (비동기)

    ✅ CPU 집약적 작업이므로 thread pool에서 실행
    """
    try:
        # ✅ transformers.pipeline은 CPU 집약적이므로 thread pool에서 실행
        result = await run_in_threadpool(cefr_classifier, user_input)
        label = result[0]["label"]
        print(f"[CEFR] 📊 Predicted: {label}")
        return label  # "A1" ~ "C2"
    except Exception as e:
        print(f"[CEFR] ❌ Error: {e}")
        return "UNKNOWN"


# ============================================================================
# ✅ 채팅 실행 (완전 비동기)
# ============================================================================
async def run_chat(state: SupervisorState) -> SupervisorState:
    """
    채팅 플로우 (완전 비동기)

    ✅ 최적화 포인트:
    - CEFR 분류: Thread pool에서 실행
    - DB 쿼리: AsyncSession 사용
    - LLM 호출: ainvoke() 사용
    """
    user_input = state.get("user_input", "")

    # ✅ 1단계: CEFR 레벨 예측 (비동기)
    if user_input:
        cefr_level = await predict_cefr_level_async(user_input)
        state["cefr_level"] = cefr_level

    # ✅ 2단계: 채팅 플로우 실행 (비동기)
    result = await handle_chat_flow_async(
        state=state,
        chat_llm=CHAT_GENERATE_LLM,
        summary_llm=SUMMARY_LLM,
        analysis_llm=ANALYSIS_LLM
    )

    return {
        **state,
        **result,
        "route": "chat",
        "cefr_level": state.get("cefr_level")
    }


# ============================================================================
# ✅ Supervisor Graph 빌드
# ============================================================================
def build_supervisor_graph():
    """
    비동기 Supervisor Graph 빌드

    ⚠️ LangGraph는 동기/비동기 모두 지원하지만,
       각 노드 함수를 async def로 정의해야 비동기로 실행됨
    """
    g = StateGraph(SupervisorState)
    g.add_node("route_decision", route_decision)
    g.add_node("podcast", run_podcast)
    g.add_node("chat", run_chat)

    g.set_entry_point("route_decision")
    g.add_conditional_edges("route_decision", lambda s: s["route"], {
        "podcast": "podcast",
        "chat": "chat"
    })
    return g.compile()
