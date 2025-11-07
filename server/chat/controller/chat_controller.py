# app/api/chat/controller.py
from fastapi import APIRouter
from pydantic import BaseModel
from server.chat.service.chat_service import process_chat_message

router = APIRouter()


# 요청 바디 모델
class ChatRequest(BaseModel):
    message: str


# uri 모음
@router.get("/chat")
async def chat_log():
    """
    이전 채팅 모음을 반환
    """
    return {"response": "Chat initialized"}


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    사용자 메시지를 받아 LangGraph로 처리
    """
    result = await process_chat_message(request.message)
    return {
        "response": result.get("output"),
        "audio": result.get("audio_base64")  # ✅ 이제 Postman에서도 값이 들어옴
    }


# ✨ 추가: 디버그용 엔드포인트 (토큰 없이 테스트)
@router.post("/chat/debug")
async def chat_debug_endpoint(request: ChatRequest):
    """
    디버그용: 토큰 없이 채팅 테스트
    Flutter 앱 개발 중 사용
    """
    result = await process_chat_message(request.message)

    return {
        "user_message": request.message,
        "ai_response": result
    }