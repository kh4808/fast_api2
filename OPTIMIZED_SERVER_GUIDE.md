# FastAPI 서버 최적화 가이드

## 디렉토리 구조 (최적화 버전)

```
fast_api2/
├── server/
│   ├── __init__.py
│   ├── main_optimized.py          # ✅ 최적화된 메인
│   ├── database_async.py           # ✅ 비동기 DB 엔진
│   ├── dependencies.py             # ✅ 공통 의존성
│   ├── config.py                   # ✅ 설정 관리
│   │
│   ├── core/                       # ✅ 핵심 유틸리티
│   │   ├── executor.py             # Thread/Process Executor
│   │   ├── cache.py                # Redis 캐시
│   │   └── async_helpers.py        # 비동기 헬퍼
│   │
│   ├── ocr/
│   │   ├── controller/
│   │   │   └── ocr_controller_async.py  # ✅ 비동기 컨트롤러
│   │   ├── service/
│   │   │   └── ocr_service_async.py     # ✅ 비동기 서비스
│   │   └── core/
│   │       └── ocr_recognizer_async.py  # ✅ Thread offload
│   │
│   ├── chat/
│   │   ├── controller/
│   │   │   └── chat_controller_async.py
│   │   ├── service/
│   │   │   ├── chat_service_async.py
│   │   │   ├── supervisor_graph_async.py
│   │   │   └── tts_service_async.py
│   │   └── repository/
│   │       └── chat_repository_async.py  # ✅ AsyncSession
│   │
│   └── level_test/
│       ├── controller/
│       │   └── test_controller_async.py
│       ├── service/
│       │   └── test_service_async.py
│       └── repository/
│           └── test_repository_async.py
│
├── requirements_optimized.txt      # ✅ 추가 패키지
├── .env                            # 환경 변수
└── docker-compose.yml              # Docker 설정
```

## 주요 변경사항

### 1. 비동기 DB (AsyncSession)
- `aiomysql` 사용
- 모든 repository 함수를 async로 전환

### 2. CPU 바운드 작업 Thread Offload
- OCR, CEFR 분류를 `run_in_executor()` 사용
- Event loop 차단 방지

### 3. LLM 호출 비동기화
- `llm.ainvoke()` 사용
- LangChain 비동기 메서드 활용

### 4. 외부 API 비동기화
- Groq TTS를 asyncio 래핑
- httpx.AsyncClient 통일

### 5. 캐싱 도입
- Redis로 토큰 검증 캐싱
- CEFR 분류 결과 캐싱

### 6. Background Tasks
- 요약/분석을 백그라운드 처리
- TTS 생성을 백그라운드 처리

### 7. uvicorn 설정 최적화
- workers: CPU 코어 * 2 + 1
- timeout: 300s
- keepalive: 120s
