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



# -------------------------------------
# 🧩 대화 세션 (1:N = 한 유저가 여러 세션)
# -------------------------------------
class ChatOrder(Base):
    __tablename__ = "chat_order"

    chat_order = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    detail = Column(String(1000), nullable=True)

    # 역참조
    user = relationship("User", back_populates="chat_orders")
    logs = relationship("ChatLog", back_populates="chat_order_rel", cascade="all, delete-orphan")
    summaries = relationship("ChatSummary", back_populates="chat_order_rel", cascade="all, delete-orphan")
    analyses = relationship("ChatAnalysis", back_populates="chat_order_rel", cascade="all, delete-orphan")


# -------------------------------------
# 💬 대화 로그 (실제 user↔AI 대화 저장)
# -------------------------------------
class ChatLog(Base):
    __tablename__ = "chat_log"

    id = Column(Integer, primary_key=True, index=True)
    chat_order = Column(Integer, ForeignKey("chat_order.chat_order"), nullable=False)
    chatNum = Column(Integer, nullable=False)  # 몇 번째 대화인지
    createdAt = Column(DateTime, default=datetime.utcnow)
    userChat = Column(String(2000), nullable=False)
    aiChat = Column(String(4000), nullable=False)

    chat_order_rel = relationship("ChatOrder", back_populates="logs")


# -------------------------------------
# 🧠 대화 요약 (10회 단위 등)
# -------------------------------------
class ChatSummary(Base):
    __tablename__ = "chat_summary"

    id = Column(Integer, primary_key=True, index=True)
    chat_order = Column(Integer, ForeignKey("chat_order.chat_order"), nullable=False)
    summary_num = Column(Integer, nullable=False)  # 1, 2, 3...
    detail = Column(String(4000), nullable=False)

    chat_order_rel = relationship("ChatOrder", back_populates="summaries")


# -------------------------------------
# 🔍 관심사 분석 (20회 또는 50회 단위)
# -------------------------------------
class ChatAnalysis(Base):
    __tablename__ = "chat_analysis"

    id = Column(Integer, primary_key=True, index=True)
    detail = Column(String(4000), nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow)
    chat_order = Column(Integer, ForeignKey("chat_order.chat_order"), nullable=False)

    chat_order_rel = relationship("ChatOrder", back_populates="analyses")


# ✅ User 테이블에 역참조 추가
class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    login_id = Column(String(255), unique=True, nullable=False)
    login_pw = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    nickname = Column(String(255), nullable=False)
    rank_id = Column(Integer, ForeignKey("ranks.id"), nullable=False)
    ranks = relationship("Ranks", back_populates="users")
    chat_orders = relationship("ChatOrder", back_populates="user", cascade="all, delete-orphan")





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
