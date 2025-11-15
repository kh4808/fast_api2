from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from server.chat.service.chat_service import process_chat_message
from server.auth_manager import get_current_user
from server.models import User

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    initialChat: Optional[bool] = False  # ✅ 첫 대화 여부만 전달


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    사용자 메시지를 받아 LangGraph로 처리
    - initialChat=True → 새로운 chatOrder 생성
    - initialChat=False → 기존 chatOrder의 마지막 chatNum 불러와서 +1
    """
    result = await process_chat_message(
        message=request.message,
        user_id=current_user.id,
        initial_chat=request.initialChat
    )

    return {
        "response": result.get("output"),
        "audio": result.get("audio_base64"),
        "chatNum": result.get("chatNum"),
        "chatOrder": result.get("chatOrder"),
        "cefr_level": result.get("cefr_level")
    }


# 디버그용 (JWT 없이)
@router.post("/chat/debug")
async def chat_debug_endpoint(request: ChatRequest):
    result = await process_chat_message(
        message=request.message,
        user_id=1,
        initial_chat=request.initialChat
    )

    return {
        "user_message": request.message,
        "ai_response": result.get("output"),
        "chatNum": result.get("chatNum"),
        "chatOrder": result.get("chatOrder"),
    }
