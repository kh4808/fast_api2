# server/database_async.py - 비동기 DB 엔진
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "kumohcap")
DB_PASSWORD = os.getenv("DB_PASSWORD", "stonsepass")
DB_HOST = os.getenv("DB_HOST", "capston-1.cef8coqs6xh4.us-east-1.rds.amazonaws.com")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "capston_1")

# ============================================================================
# ✅ 비동기 MySQL 연결 URL (aiomysql 사용)
# ============================================================================
ASYNC_DATABASE_URL = (
    f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

# ============================================================================
# ✅ 비동기 엔진 생성
# ============================================================================
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,           # 연결 유효성 체크
    pool_size=20,                 # 커넥션 풀 크기 증가
    max_overflow=40,              # 최대 오버플로우
    pool_recycle=3600,            # 1시간마다 커넥션 재활용
    echo=False,                   # SQL 로그 (디버그 시 True)
)

# ============================================================================
# ✅ 비동기 세션 팩토리
# ============================================================================
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,       # 커밋 후에도 객체 접근 가능
)

Base = declarative_base()

# ============================================================================
# ✅ 의존성 주입용 비동기 세션 제공 함수
# ============================================================================
async def get_async_db():
    """FastAPI 의존성으로 사용할 비동기 DB 세션"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ============================================================================
# ✅ 기존 동기 DB (하위 호환용, 점진적 마이그레이션)
# ============================================================================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SYNC_DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

sync_engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def get_db():
    """기존 동기 세션 (하위 호환용)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
