# server/chat/service/supervisor_graph.py
from typing import TypedDict, Optional
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

import server.chat.service.groq_subgraph as groq_subgraph
from server.chat.service.tts_service import generate_tts_audio
from server.chat.service.chat_logic_service import handle_chat_flow  # ✅ DB/비즈니스 로직 분리

from transformers import pipeline

# CEFR 판별 모델 (로컬 캐시 자동 저장됨)

load_dotenv()

# ▶️ 모델 분리 (요약/관심사/대응)
cefr_classifier = pipeline(
    "text-classification",
    model="dksysd/cefr-classifier",
    tokenizer="dksysd/cefr-classifier"
)
CHAT_GENERATE_LLM = ChatOpenAI(model="gpt-4o")

SUMMARY_LLM = ChatOpenAI(model="gpt-4o-mini")
ANALYSIS_LLM = ChatOpenAI(model="gpt-4o-mini")

# (기존) 라우팅/팟캐스트
supervisor_llm = ChatOpenAI(model="gpt-4o")
podcast_app = groq_subgraph.build_podcast_graph()
# 참고: 일반 챗용으로 Groq 모델을 쓰고 싶으면 handle_chat_flow 내부가 아닌 여기에서 교체하면 됨
# chat_agent = ChatGroq(model="llama-3.3-70b-versatile")

class SupervisorState(TypedDict, total=False):
    # 입력/출력
    user_input: str
    output: str
    audio_base64: str

    # 라우팅
    route: str  # "podcast" | "chat"

    # 채팅 관리
    userId: int
    chatNum: int                # 현재까지의 누적 대화 횟수(요청 시 전달 받음) — 응답 시 +1 반영
    chatOrder: int  
    initialChat: bool             # 세션 ID
    history: str                # (옵션) 프롬프트용
    history_summary: str        # (옵션) 프롬프트용
    cefr_level : str


def route_decision(state: SupervisorState) -> SupervisorState:
    """podcast or chat 분기 결정"""
    msg = [
        SystemMessage("""
            You are a routing assistant.
            Your task is to decide whether the user’s input should be handled by the podcast generator or by the general chat assistant.
    
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
    route_raw = supervisor_llm.invoke(msg).content.strip().lower()
    route = "podcast" if "podcast" in route_raw else "chat"
    return {**state, "route": route}


def run_podcast(state: SupervisorState) -> SupervisorState:
    """팟캐스트 분기: 기존 그래프 + TTS"""
    res = podcast_app.invoke({
        "user_input": state["user_input"],
        "history": "",
        "history_summary": "Radio show is started. You need to speak",
        "turn_count": 0
    })
    script = res.get("history", "")
    audio = generate_tts_audio(script)
    return {**state, "output": script, "audio_base64": audio, "route": "podcast"}


def predict_cefr_level(user_input: str) -> str:
    """
    HuggingFace CEFR 분류 모델로 문장의 CEFR 레벨을 예측한다.
    return 예: "A2", "B1", "C1" 등
    """
    try:
        result = cefr_classifier(user_input)
        label = result[0]["label"]
        return label  # "A1" ~ "C2"
    except Exception as e:
        print("CEFR 분석 오류:", e)
        return "UNKNOWN"


def run_chat(state: SupervisorState) -> SupervisorState:
    """
    요구사항 수행 흐름 + CEFR 레벨 분석 추가
    """

    user_input = state.get("user_input", "")
    if user_input:
        # 1) CEFR 레벨 예측
        cefr_level = predict_cefr_level(user_input)

        # 2) state에 레벨 추가
        state["cefr_level"] = cefr_level

    # 3) 이후 기존 로직 실행
    result = handle_chat_flow(
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



def build_supervisor_graph():
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
