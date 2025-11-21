# app/main.py
from dotenv import load_dotenv
load_dotenv(dotenv_path="server/.env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.chat.controller.chat_controller import router as chat_router
from server.level_test.controller.test_controller import router as test_router
from server.ocr.controller import ocr_controller

app = FastAPI(title="LangGraph Chat API")

# # CORS 설정
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # 개발 환경: 모든 origin 허용 (프로덕션에서는 특정 도메인으로 제한)
#     allow_credentials=True,
#     allow_methods=["*"],  # 모든 HTTP 메서드 허용
#     allow_headers=["*"],  # 모든 헤더 허용
# )

# app.include_router(chat_router, prefix="/api", tags=["chat"])
# app.include_router(test_router, prefix="/api", tags=["vocabulary-test"])
# app.include_router(ocr_controller.router)


# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r'(http://localhost:\d+|http://127\.0\.0\.1:\d+|https://.*\.ngrok-free\.dev|https://.*\.ngrok-free\.app|https://.*\.ngrok\.io)',
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Authorization", "Content-Type", "Content-Disposition"],
    max_age=3600,  # Preflight 캐싱 시간 (1시간)
)


# ============================================================================
# Health Check 엔드포인트
# ============================================================================
@app.get("/")
async def root():
    """루트 엔드포인트 - API 상태 확인"""
    return {
        "message": "LangGraph Chat API is running",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "chat": "/api/chat",
            "level_test": "/api/test",
            "ocr": "/api/ocr/extract",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "FastAPI LangGraph Chat API"
    }

# ============================================================================
# CORS 테스트 엔드포인트 (디버깅용)
# ============================================================================
@app.get("/api/cors-test")
async def cors_test():
    """CORS 설정이 올바르게 작동하는지 테스트"""
    return {
        "message": "CORS is working correctly!",
        "cors_settings": {
            "allow_origin_regex": "localhost:*, 127.0.0.1:*, *.ngrok-free.dev, *.ngrok-free.app",
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        }
    }

