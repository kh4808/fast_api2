# server/test/controller/test_controller.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from server.auth_manager import get_current_user
from server.database import get_db
from server.level_test.service.test_service import process_test_message, analyze_test_result
from server.models import User
from fastapi import Header



router = APIRouter()

# 요청 스키마
class TestRequest(BaseModel):
    message: str


async def get_token(Authorization: str = Header(...)):
    return Authorization.replace("Bearer ", "")


# uri 모음
@router.get("/test")
async def chat_log():
    """
    이전 채팅 모음을 반환
    """


    return {"response": "Chat initialized"}



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


