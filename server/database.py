from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# .env 불러오기 (.env 파일이 fastapi_server 루트에 있다면 상대 경로 맞춰줘야 함)
load_dotenv()

DB_USER = os.getenv("DB_USER", "kumohcap")
DB_PASSWORD = os.getenv("DB_PASSWORD", "stonsepass")
DB_HOST = os.getenv("DB_HOST", "capston-1.cef8coqs6xh4.us-east-1.rds.amazonaws.com")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "capston_1")

# MySQL 연결 URL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

# SQLAlchemy 설정
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
