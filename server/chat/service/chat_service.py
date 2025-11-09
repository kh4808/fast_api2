import server.chat.service.supervisor_graph as supervisor_graph

supervisor_app = supervisor_graph.build_supervisor_graph()

async def process_chat_message(message: str, user_id: int, initial_chat: bool):
    """
    LangGraph에 상태 전달.
    - initial_chat=True → 새로운 chatOrder 생성
    - initial_chat=False → 마지막 chatLog.chatNum 불러와서 +1
    """
    initial_state = {
        "user_input": message,
        "route": "",
        "output": "",
        "audio_base64": "",
        "userId": user_id,
        "initialChat": initial_chat,  # ✅ 새 필드
        "chatNum": 0,                 # 서버가 내부에서 결정
        "chatOrder": 0,
        "history": "",
        "history_summary": ""
    }
    return supervisor_app.invoke(initial_state)
