# server/test/controller/test_controller.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from server.auth_manager import get_current_user
from server.database import get_db
from server.level_test.service.test_service import process_test_message, analyze_test_result
from server.level_test.repository.log_repository import get_recent_logs
from server.models import User
from fastapi import Header



router = APIRouter()

# 요청 스키마
class TestRequest(BaseModel):
    message: str


async def get_token(Authorization: str = Header(...)):
    return Authorization.replace("Bearer ", "")


# uri 모음
@router.get("/test/logs")
async def get_test_logs(
    level_test_num: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    레벨 테스트 로그를 가져옵니다.
    - level_test_num 파라미터 있음: 해당 level_test_num의 최근 10개 로그
    - level_test_num 파라미터 없음: 모든 level_test_num의 최근 10개 로그
    """
    logs = get_recent_logs(
        db=db,
        user_id=user.id,
        level_test_num=level_test_num,
        limit=10
    )

    return {
        "logs": [
            {
                "dialog_num": log.diolog_num,
                "user_question": log.user_question,
                "ai_response": log.ai_response,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    }



@router.post("/test")
async def test_endpoint(
    request: TestRequest,
    user: User = Depends(get_current_user),  # ✅ Authorization 헤더에서 User 자동 주입
    db: Session = Depends(get_db), 
    token: str = Depends(get_token)           # ✅ DB 세션 주입
):
    """어휘력 테스트 문장 1회 입력 (qwen:4b로 처리)"""
    result = await process_test_message(db=db, login_id=user.login_id, message=request.message, token=token)
    return result


