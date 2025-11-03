# app/main.py
from dotenv import load_dotenv
load_dotenv(dotenv_path="server/.env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.chat.controller.chat_controller import router as chat_router
from server.level_test.controller.test_controller import router as test_router
from server.ocr.controller import ocr_controller

app = FastAPI(title="LangGraph Chat API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경: 모든 origin 허용 (프로덕션에서는 특정 도메인으로 제한)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(test_router, prefix="/api", tags=["vocabulary-test"])
app.include_router(ocr_controller.router)
