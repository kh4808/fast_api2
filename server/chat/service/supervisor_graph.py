import server.chat.service.groq_subgraph as groq_subgraph
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from typing import TypedDict
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage, SystemMessage
from server.chat.service.tts_service import generate_tts_audio


# 나중에 함수 자체를 바꿔야함 (오디오 파일 생성까지 연결된 서브그래프 가져오기/ 지금은 스크립트만)
podcast_app = groq_subgraph.build_podcast_graph()

load_dotenv()

# summary_llm = ChatOpenAI(model="gpt-4o-mini")
# agent_manager_llm = ChatOpenAI(model="gpt-4o")
# host_llm = ChatOpenAI(model="gpt-4o")
# guest_llm = ChatOpenAI(model="gpt-4o")
# history_summary_llm = ChatOpenAI(model="gpt-4o-mini")

# llm = ChatOpenAI(
#     model="qwen:4b",                     # Ollama 모델 이름
#     base_url="http://127.0.0.1:11434/v1",# Ollama 서버 주소
#     api_key="none"                       # 필요 없음, dummy 값
# )

# 같은 LLM을 여러 역할에 재사용
#summary_llm = llm
#agent_manager_llm = llm
#host_llm = llm
#guest_llm = llm
#history_summary_llm = llm


supervisor_llm = ChatOpenAI(model="gpt-4o")
chat_agent = ChatGroq(model="llama-3.3-70b-versatile")


class SupervisorState(TypedDict):
    user_input: str
    route: str  # "radio_show" or "chat"
    output: str
    audio_base64: str 


# %%

def route_decision(state: SupervisorState) -> SupervisorState:
    user_input = state["user_input"]

    messages = [
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
        HumanMessage(user_input)
    ]
    route = supervisor_llm.invoke(messages).content.strip().lower()

    if "podcast" in route:
        route = "podcast"
    else:
        route = "chat"

    return {"route": route, "user_input": user_input, "output": ""}


# %%

# 일반 고도화 챗봇 : chat_agent - 젤 위에서 바꾸기
# podcast_app


def run_podcast(state: SupervisorState) -> SupervisorState:
    result = podcast_app.invoke({
        "user_input": state["user_input"],
        "history": "",
        "history_summary": "Radio show is started. You need to speak",
        "turn_count": 0
    })

    script = result["history"]
    audio_base64 = generate_tts_audio(script)

    return {
        "output": script,
        "audio_base64": audio_base64,  # ✅ 이제 LangGraph state에 반영됨
        "route": "podcast",
        "user_input": state["user_input"]
    }




def run_chat_llm(state: SupervisorState) -> SupervisorState:
    msg = [
        SystemMessage("You are a friendly and intelligent chat assistant. Provide useful answers."),
        HumanMessage(state["user_input"])
    ]
    response = chat_agent.invoke(msg)
    return {
        "output": response.content,
        "route": "chat",
        "user_input": state["user_input"]
    }


# %%

def build_supervisor_graph():
    """Supervisor 그래프를 생성하고 컴파일된 앱을 반환"""
    supervisor_graph = StateGraph(SupervisorState)

    # 노드 추가
    supervisor_graph.add_node("route_decision", route_decision)
    supervisor_graph.add_node("podcast", run_podcast)
    supervisor_graph.add_node("chat", run_chat_llm)

    # 진입점 설정
    supervisor_graph.set_entry_point("route_decision")

    # 조건부 이동 설정
    supervisor_graph.add_conditional_edges(
        "route_decision",
        lambda s: s["route"],
        {
            "podcast": "podcast",
            "chat": "chat"
        }
    )

    # 그래프 컴파일 후 반환
    return supervisor_graph.compile()

# supervisor_graph = StateGraph(SupervisorState)

# supervisor_graph.add_node("route_decision", route_decision)
# supervisor_graph.add_node("podcast", run_podcast)
# supervisor_graph.add_node("chat", run_chat_llm)

# supervisor_graph.set_entry_point("route_decision")

# supervisor_graph.add_conditional_edges(
#     "route_decision",
#     lambda s: s["route"],
#     {
#         "podcast": "podcast",
#         "chat": "chat"
#     }
# )

# supervisor_app = supervisor_graph.compile()


# # %%
# input1 = {
#     "user_input": "Please make about the psychology of dieting with a podcast.",
#     "history_summary": "Radio show is started. You need to speak",
#     "turn_count": 0
# }
# result1 = supervisor_app.invoke(input1)
# print(result1["route"])
# print(result1["output"])

# # %%
# print(result1["output"])

# # %%
# input2 = {"user_input": "Can you summarize the pros and cons of keto diet?"}
# result2 = supervisor_app.invoke(input2)
# print("💬", result2["output"]) 


