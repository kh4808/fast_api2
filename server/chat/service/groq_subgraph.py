# %pip install python-dotenv
# %pip install langchain-openai
# %pip install groq
# %pip install langchain-tavily

# API KEY를 환경변수로 관리하기 위한 설정 파일
# 설치: pip install python-dotenv
from dotenv import load_dotenv

# API KEY 정보로드
load_dotenv()

# %%
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, add_messages


class State(TypedDict):
    user_input: str
    web_search: str
    summary: str
    host_persona: str
    guest_persona: str
    history: str
    history_summary: str
    turn_count: int
    host_message: str
    guest_message:str

    

# %% [markdown]
# 

# %%
from langchain_openai import ChatOpenAI

summary_llm = ChatOpenAI(model="gpt-4o-mini")
agent_manager_llm = ChatOpenAI(model="gpt-4o")
host_llm = ChatOpenAI(model="gpt-4o")
guest_llm = ChatOpenAI(model="gpt-4o")
history_summary_llm = ChatOpenAI(model="gpt-4o-mini")

llm = ChatOpenAI(
    model="qwen:4b",                     # Ollama 모델 이름
    base_url="http://127.0.0.1:11434/v1",# Ollama 서버 주소
    api_key="none"                       # 필요 없음, dummy 값
)

# 같은 LLM을 여러 역할에 재사용
#summary_llm = llm
#agent_manager_llm = llm
#host_llm = llm
#guest_llm = llm
#history_summary_llm = llm

# %%
from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import AIMessage
from langchain_tavily import TavilySearch

tavily_tool = TavilySearch(
    max_results=5,
    topic="general",
    # include_answer=False,
    # include_raw_content=False,
    # include_images=False,
    # include_image_descriptions=False,
    # search_depth="basic",
    # time_range="day",
    # include_domains=None,
    # exclude_domains=None
)

def retrieve(state: State) -> State:
    user_input = state["user_input"]

    # 1. 웹 검색 실행
    result_dict = tavily_tool.invoke(user_input)   # dict 반환
    raw_results = result_dict.get("results", [])   # list of dicts

    # 2. 결과 요약 (앞에서 3개만 추림)
    web_search = [r.get("title", "") + ": " + r.get("content", "") for r in raw_results[:3]]

    return {
        "user_input": state["user_input"],
        "web_search": web_search
    }


def summarize(state: State) -> State:
    web_search = "\n".join(state["web_search"])
    temp_message = [
        SystemMessage(f"""
        Please, summarize about {web_search}. 
        Focus on the commonalities and differences of web_search.
        """)
    ]
    summary = summary_llm.invoke(temp_message)
    return {
        "summary": summary.content,
        "user_input": state["user_input"],
    }


# %%
import re

def agent_manager(state: State) -> State:
    temp_message = [
        SystemMessage(
        """
        Look at the input and divide it into two perspectives.
        Your answer will act as an AI persona. That AIs have the identity of a radio host and a radio guest 
        
        Let me give you an example of an answer.

        Example:
        If the input is about diet 

        your answer:

        1.host:You have a view in favor of using drugs such as diet supplements or stomach rubies.
        2.guest:You stand up for creating a healthy lifecycle without medication assistance"""
        ),
        HumanMessage(state["summary"])
    ]
    persona = agent_manager_llm.invoke(temp_message)

    text = persona.content  # ✅ AIMessage → 문자열 추출

    host_match = re.search(r"[1①]\s*[\.\)]?\s*host:\s*(.*)", text, re.IGNORECASE)
    guest_match = re.search(r"[2②]\s*[\.\)]?\s*guest:\s*(.*)", text, re.IGNORECASE)


    host = host_match.group(1).strip() if host_match else ""
    guest = guest_match.group(1).strip() if guest_match else ""

    

    return {
        "host_persona": host,
        "guest_persona": guest,
        "summary": state["summary"],
        "user_input": state["user_input"],
    }



# %%
from langchain_core.tools import tool 
from langchain_core.runnables import history


@tool
def tavily_search_host(query: str) -> str:
    """If you need to deep and technical answer, use this to web search """
    result_dict = tavily_tool.invoke(query)       # dict 반환
    raw_results = result_dict.get("results", [])  # list 꺼내기
    return "\n".join(r.get("content", "") for r in raw_results)


def host_agent(state: State) -> State:
    tools = [tavily_search_host]

    temp_message = [
        SystemMessage(
            f"""
            You are the radio host.
            Persona: {state['host_persona']} 
            Lead the conversation. 
            You should be able to ask questions about professional knowledge related to the subject.
            You should be able to organize your interlocutor's remarks and deliver them to the audience.
            You should talk not longer than 2 sentences.
            If you need to deep and technical answer, use this to web search {tools[0].name}.
            """
        ),
        HumanMessage(state["history_summary"])
    ]

    host_message = host_llm.invoke(temp_message)

    return {
        "host_message": f"Host: {host_message.content}",
    }



# %%
def history_summarize(state: State) -> State:
    history_summary = state["history_summary"]

    new_history = state["history"]
    if state.get("host_message"):
        new_history += "\n" + state["host_message"]
    if state.get("guest_message"):
        new_history += "\n" + state["guest_message"]

    last_text = (state.get("guest_message") or 
                 state.get("host_message") or 
                 "No history yet.")
    
    temp_message = [
        SystemMessage(
            f"""
            history_summary: {history_summary}
            last_text: {last_text}
            
            last_text is the answer of history_summary.
            Summarize the conversation history briefly (3~4 sentences max).
            """
        )
    ]

    final_summary = history_summary_llm.invoke(temp_message)

    return {
        "history": new_history,
        "history_summary": final_summary.content, 
        "turn_count": state.get("turn_count", 0) + 1, 
        "host_message": "",   
        "guest_message": "", 
        "user_input": state["user_input"],
        "host_persona": state["host_persona"],
        "guest_persona": state["guest_persona"],
    }



def check_turns(state: State) -> str:
    MAX_TURNS = 10
    turn = state.get("turn_count", 0)

    if turn >= MAX_TURNS:
        return "end"

    # 홀수 턴 → guest
    if turn % 2 == 1:
        return "guest_agent"
    # 짝수 턴 → host
    return "host_agent"


# %%
@tool
def tavily_search_guest(query: str) -> str:
    """If you need to deep and technical answer, use this to web search """
    result_dict = tavily_tool.invoke(query)
    raw_results = result_dict.get("results", [])
    return "\n".join(r.get("content", "") for r in raw_results)


def guest_agent(state: State) -> State:
    tools = [tavily_search_guest]

    temp_message = [
        SystemMessage(
            f"""
            You are the radio guest.
            Persona: {state['guest_persona']}
            The discussion topic MUST be based strictly on this summary data: {state['summary']}
            {state["history_summary"]} is previous conversation history.
            If you need to deep and technical answer, use this to web search {tools[0].name}.
            Style & Tone:
            - Answer concisely, 2~3 sentences max.
            - Prioritize clear explanations and useful information.
            - Avoid jokes or unnecessary small talk.
            - Always anchor your response to the summary data.
            """
        )
    ]

    guest_message = guest_llm.invoke(temp_message)

    return {
        "guest_message": f"Guest: {guest_message.content}",
    }



# %%
# === 그래프 정의 ===
# graph = StateGraph(State)

# # === 노드 등록 ===
# graph.add_node("retrieve", retrieve)
# graph.add_node("summarize", summarize)
# graph.add_node("agent_manager", agent_manager)
# graph.add_node("host_agent", host_agent)
# graph.add_node("guest_agent", guest_agent)
# graph.add_node("history_summarize", history_summarize)
# # ⛔ check_turns는 node가 아님! → add_node 필요 없음

# # === 기본 플로우 ===
# graph.add_edge("retrieve", "summarize")
# graph.add_edge("summarize", "agent_manager")
# graph.add_edge("agent_manager", "host_agent")

# # === 반복 루프: host ↔ guest ===
# graph.add_edge("host_agent", "history_summarize")
# graph.add_edge("guest_agent", "history_summarize")

# # === 조건부 분기 ===
# graph.add_conditional_edges(
#     "history_summarize",
#     check_turns,   # 여기서 분기 함수 사용
#     {
#         "host_agent": "host_agent",
#         "guest_agent": "guest_agent",
#         "end": "__end__"
#     }
# )

# # === 진입점 설정 ===
# graph.set_entry_point("retrieve")

# # === 컴파일 ===
# app = graph.compile()


# # %%
# initial_state = {
#     "user_input": "I recently started diet",
#     "history": "",
#     "history_summary": "Radio show is started. You need to speak",
#     "turn_count": 0
# }

# final_state = app.invoke(initial_state)

# %% [markdown]
# 

# %%
# === 히스토리 불러오기 ===
# print("=== 전체 대화 히스토리 ===")
# print(final_state["history"])

# print("\n=== 최종 요약 ===")
# print(final_state["history_summary"])

# # %%
# print(final_state["summary"])

# # %%
# print(final_state["guest_persona"])
# print(final_state["host_persona"])


# %%
# %pip install --upgrade groq pydub


# %%
# import os
# from groq import Groq
# from pydub import AudioSegment

# # ✅ Groq API 키 설정
# client = Groq(api_key=os.environ["GROQ_API_KEY"])

# # ✅ 화자별 목소리 매핑
# voice_map = {
#     "Host": "Fritz-PlayAI",   # 남성 중저음, 내레이션 스타일
#     "Guest": "Mason-PlayAI",  # 여성 밝은톤, 대화형 스타일
# }

# # ✅ 대화 스크립트 가져오기
# # final_state["history"]가 문자열 or 리스트일 수 있음
# if isinstance(final_state["history"], list):
#     script = "\n".join(final_state["history"])
# else:
#     script = str(final_state["history"])

# if not script.strip():
#     raise ValueError("⚠️ final_state['history']가 비어있습니다. 대화 로그를 먼저 생성하세요.")

# # ✅ 줄 단위로 나누기
# lines = [line.strip() for line in script.strip().split("\n") if line.strip()]

# segments = []

# for line in lines:
#     if ":" not in line:
#         continue

#     # 화자와 대사 분리
#     speaker, text = line.split(":", 1)
#     speaker = speaker.strip()
#     text = text.strip()

#     # 화자별 음성 선택
#     voice = voice_map.get(speaker, "Fritz-PlayAI")

#     print(f"[{speaker}] → {voice} 로 변환 중...")

#     # ✅ Groq TTS 호출
#     response = client.audio.speech.create(
#         model="playai-tts",      # Groq 공식 TTS 모델
#         voice=voice,             # 화자별 음성
#         input=text,              # 대사
#         response_format="wav"    # wav 형식 (기본)
#     )

#     # ✅ 파일 저장
#     filename = f"{speaker}_{len(segments)}.wav"
#     with open(filename, "wb") as f:
#         f.write(response.read())

#     # ✅ 오디오 파일 로드
#     seg = AudioSegment.from_file(filename, format="wav")
#     segments.append(seg)

# # ✅ 모든 오디오 합치기
# final_audio = AudioSegment.silent(duration=500)
# for seg in segments:
#     final_audio += seg + AudioSegment.silent(duration=300)

# # ✅ 최종 mp3로 내보내기
# final_audio.export("dialogue_output.mp3", format="mp3")
# print("✅ 대화 음성 변환 완료: dialogue_output.mp3")



# subgraph_radio_show.py

def build_podcast_graph():
    graph = StateGraph(State)

    graph.add_node("retrieve", retrieve)
    graph.add_node("summarize", summarize)
    graph.add_node("agent_manager", agent_manager)
    graph.add_node("host_agent", host_agent)
    graph.add_node("guest_agent", guest_agent)
    graph.add_node("history_summarize", history_summarize)
    # ⛔ check_turns는 node가 아님! → add_node 필요 없음

    # === 기본 플로우 ===
    graph.add_edge("retrieve", "summarize")
    graph.add_edge("summarize", "agent_manager")
    graph.add_edge("agent_manager", "host_agent")

    # === 반복 루프: host ↔ guest ===
    graph.add_edge("host_agent", "history_summarize")
    graph.add_edge("guest_agent", "history_summarize")

    # === 조건부 분기 ===
    graph.add_conditional_edges(
        "history_summarize",
        check_turns,   # 여기서 분기 함수 사용
        {
            "host_agent": "host_agent",
            "guest_agent": "guest_agent",
            "end": "__end__"
        }
    )

    # === 진입점 설정 ===
    graph.set_entry_point("retrieve")
    # ✅ 서브그래프를 LangGraph 앱으로 컴파일
    return graph.compile()
