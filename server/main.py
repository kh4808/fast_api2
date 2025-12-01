# app/main.py
from dotenv import load_dotenv
load_dotenv(dotenv_path="server/.env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.chat.controller.chat_controller import router as chat_router
from server.level_test.controller.test_controller import router as test_router
from server.ocr.controller import ocr_controller

app = FastAPI(title="LangGraph Chat API")

# ============================================================================
# ⭐ CORS 설정 (GitHub Pages + localhost + ngrok 완전 대응)
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r'(http://localhost:\d+'
        r'|http://127\.0\.0\.1:\d+'
        r'|https://.*\.ngrok-free\.dev'
        r'|https://.*\.ngrok-free\.app'
        r'|https://.*\.ngrok\.io'
        r'|https://.*\.github\.io)'  # ⭐ GitHub Pages 추가
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Authorization", "Content-Type", "Content-Disposition"],
    max_age=3600,
)

# ============================================================================
# ⭐ 라우터 등록
# ============================================================================
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(test_router, prefix="/api", tags=["level-test"])
app.include_router(ocr_controller.router)

# ============================================================================
# Health Check
# ============================================================================
@app.get("/")
async def root():
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
    return {
        "status": "healthy",
        "service": "FastAPI LangGraph Chat API"
    }

# ============================================================================
# CORS Test
# ============================================================================
@app.get("/api/cors-test")
async def cors_test():
    return {
        "message": "CORS is working correctly!",
        "cors_settings": {
            "allow_origin_regex": "localhost:*, 127.0.0.1:*, *.ngrok, *.github.io",
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        }
    }
