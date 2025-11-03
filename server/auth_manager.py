import base64
from jose import JWTError, jwt
from fastapi import HTTPException, status, Request, Depends
from sqlalchemy.orm import Session
from server.database import get_db
from server.models import User
import os

class AuthManager:
    """
    JWT 관리 및 사용자 인증을 담당하는 클래스
    """

    def __init__(self):
        secret_str = os.getenv("JWT_SECRET", "u2fK6z1B8vwrqa65cg9bleZgibVQTF36v6kNl+X/22Q=")
        # ✅ Spring과 동일하게 base64 디코딩
        self.secret_key = base64.b64decode(secret_str)        
        self.algorithm = "HS256"

    # --------------------------------------------------
    # 1️⃣ JWT 유효성 검증
    # --------------------------------------------------
    def verify_token(self, token: str):
        """
        JWT 토큰이 유효한지 검증하고 payload 반환
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            print("✅ JWT decoded payload:", payload)  # ← 디버깅 로그 추가
            return payload
        except Exception as e:
            print("❌ JWT decode error:", type(e).__name__, str(e))  # ← 에러 구체적으로 출력
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired JWT token",
            )


    # --------------------------------------------------
    # 2️⃣ 토큰에서 login_id 또는 sub 추출
    # --------------------------------------------------
    def get_login_id_from_token(self, token: str) -> str:
        payload = self.verify_token(token)
        login_id = payload.get("loginId") or payload.get("sub")
        if not login_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="loginId claim not found in token",
            )
        return login_id

    # --------------------------------------------------
    # 3️⃣ 토큰으로부터 DB에서 User 객체 조회
    # --------------------------------------------------
    def get_user_from_token(self, db: Session, token: str) -> User:
        login_id = self.get_login_id_from_token(token)
        user = db.query(User).filter(User.login_id == login_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with login_id={login_id} not found",
            )
        return user

    # --------------------------------------------------
    # 4️⃣ 토큰에서 user_id만 바로 가져오기
    # --------------------------------------------------
    def get_user_id_from_token(self, db: Session, token: str) -> int:
        user = self.get_user_from_token(db, token)
        return user.id


# --------------------------------------------------
# FastAPI 의존성으로 사용할 수 있도록 래퍼 제공
# --------------------------------------------------
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Authorization 헤더에서 토큰을 읽고 user 객체 반환
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = auth_header.split(" ")[1]
    manager = AuthManager()
    return manager.get_user_from_token(db, token)
