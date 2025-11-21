from sqlalchemy.orm import Session
from typing import Optional
from server.models import ChatLog, ChatOrder

def get_recent_chat_logs(db: Session, user_id: int, chat_order: Optional[int] = None, limit: int = 10):
    """
    특정 유저의 chat logs를 가져옵니다.
    - chat_order가 있으면: 해당 chat_order의 최근 로그
    - chat_order가 없으면: 모든 chat_order의 최근 로그
    """
    if chat_order is not None:
        # 특정 chat_order의 로그 조회
        chat_order_obj = (
            db.query(ChatOrder)
            .filter(ChatOrder.user_id == user_id, ChatOrder.chat_order == chat_order)
            .first()
        )

        if not chat_order_obj:
            return []

        logs = (
            db.query(ChatLog)
            .filter(ChatLog.chat_order_id == chat_order_obj.id)
            .order_by(ChatLog.createdAt.desc())
            .limit(limit)
            .all()
        )
    else:
        # 모든 chat_order의 최근 로그 조회
        logs = (
            db.query(ChatLog)
            .join(ChatOrder, ChatLog.chat_order_id == ChatOrder.id)
            .filter(ChatOrder.user_id == user_id)
            .order_by(ChatLog.createdAt.desc())
            .limit(limit)
            .all()
        )

    # 시간 순서대로 정렬 (오래된 것부터)
    logs.reverse()
    return logs
