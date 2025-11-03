# app/api/chat/service.py
import server.chat.service.supervisor_graph as supervisor_graph

# 그래프 인스턴스 1회 생성 (서버 구동 시 로드)
supervisor_app = supervisor_graph.build_supervisor_graph()

async def process_chat_message(message: str):
    """
    사용자의 채팅을 LangGraph에 전달하고 결과를 반환
    """
    initial_state = {
        "user_input": message,
        "history": "",
        "history_summary": "Radio show is started. You need to speak",
        "turn_count": 0
    }

    # LangGraph 실행
    result_state = supervisor_app.invoke(initial_state)

    # state 전부가 json형태로 전해짐
    return result_state
