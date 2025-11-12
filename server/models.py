from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime
from sqlalchemy.orm import relationship
from server.database import Base


# -------------------------------------
# 🧩 대화 세션 (1:N = 한 유저가 여러 세션)
# -------------------------------------
class ChatOrder(Base):
    __tablename__ = "chat_order"

    # ✅ 전역 고유 PK
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # ✅ 유저별 세션 번호
    chat_order = Column(Integer, nullable=False)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    detail = Column(String(1000), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "chat_order", name="uq_user_chat_order"),
    )

    # 역참조
    user = relationship("User", back_populates="chat_orders")
    logs = relationship("ChatLog", back_populates="chat_order_rel", cascade="all, delete-orphan")
    summaries = relationship("ChatSummary", back_populates="chat_order_rel", cascade="all, delete-orphan")
    analyses = relationship("ChatAnalysis", back_populates="chat_order_rel", cascade="all, delete-orphan")

class ChatLog(Base):
    __tablename__ = "chat_log"

    id = Column(Integer, primary_key=True, index=True)
    chat_order_id = Column("chat_order", Integer, ForeignKey("chat_order.id"), nullable=False)
    chatNum = Column(Integer, nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow)
    userChat = Column(String(2000), nullable=False)
    aiChat = Column(String(4000), nullable=False)

    chat_order_rel = relationship("ChatOrder", back_populates="logs")


class ChatSummary(Base):
    __tablename__ = "chat_summary"

    id = Column(Integer, primary_key=True, index=True)
    chat_order_id = Column("chat_order", Integer, ForeignKey("chat_order.id"), nullable=False)
    summary_num = Column(Integer, nullable=False)
    detail = Column(String(4000), nullable=False)

    chat_order_rel = relationship("ChatOrder", back_populates="summaries")


class ChatAnalysis(Base):
    __tablename__ = "chat_analysis"

    id = Column(Integer, primary_key=True, index=True)
    chat_order_id = Column("chat_order", Integer, ForeignKey("chat_order.id"), nullable=False)
    detail = Column(String(4000), nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow)

    chat_order_rel = relationship("ChatOrder", back_populates="analyses")


# ✅ User 테이블
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


class LevelTestLog(Base):
    __tablename__ = "level_test_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)  # user 테이블과 연결
    user_question = Column(String(500), nullable=False)
    ai_response = Column(String(1000), nullable=False)
    level_test_num = Column(Integer, nullable=False)
    diolog_num = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

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
