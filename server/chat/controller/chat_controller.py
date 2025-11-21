from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from server.chat.service.chat_service import process_chat_message
from server.chat.repository.chat_log_repository import get_recent_chat_logs
from server.auth_manager import get_current_user
from server.database import get_db
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


@router.get("/chat/logs")
async def get_chat_logs(
    chat_order: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    대화 로그를 가져옵니다.
    - chat_order 파라미터 있음: 해당 chat_order의 최근 10개 로그
    - chat_order 파라미터 없음: 모든 chat_order의 최근 10개 로그
    """
    logs = get_recent_chat_logs(
        db=db,
        user_id=current_user.id,
        chat_order=chat_order,
        limit=10
    )

    return {
        "logs": [
            {
                "chatNum": log.chatNum,
                "userChat": log.userChat,
                "aiChat": log.aiChat,
                "createdAt": log.createdAt.isoformat() if log.createdAt else None
            }
            for log in logs
        ]
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
