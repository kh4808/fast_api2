# models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime

from sqlalchemy.orm import relationship
from server.database import Base


class LevelTestLog(Base):
    __tablename__ = "level_test_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)  # user 테이블과 연결
    user_question = Column(String(500), nullable=False)
    ai_response = Column(String(1000), nullable=False)
    level_test_num = Column(Integer, nullable=False)
    diolog_num = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    login_id = Column(String(255), unique=True, nullable=False)
    login_pw = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    nickname = Column(String(255), nullable=False)
    rank_id = Column(Integer, ForeignKey("ranks.id"), nullable=False)

    # 관계 설정 (선택적으로, 필요 시)
    ranks = relationship("Ranks", back_populates="users")



class Ranks(Base):
    __tablename__ = "ranks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(50), nullable=False)

    # ✅ 역참조 추가 (User → Ranks 관계의 반대 방향)
    users = relationship("User", back_populates="ranks")


class LevelTestSummary(Base):
    __tablename__ = "level_test_summary"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    level_test_num = Column(Integer, nullable=False)
    summary_num = Column(Integer, nullable=False)   # ✅ 1, 2, 3... (10문장 단위)
    summary_text = Column(String(2000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
