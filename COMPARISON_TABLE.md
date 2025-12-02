# 📊 현재 코드 vs 최적화 코드 비교표

## 전체 파일 변경사항 요약

| 파일 | 현재 상태 | 변경 필요 | 새 파일 생성 | 우선순위 |
|------|----------|----------|------------|---------|
| `main.py` | 동기 | ✅ 수정 | - | 🔴 필수 |
| `database.py` | 동기 | - | `database_async.py` | 🔴 필수 |
| `ocr/service/ocr_service.py` | 동기 | ✅ 수정 | `ocr_service_async.py` | 🔴 필수 |
| `ocr/controller/ocr_controller.py` | 동기 | ✅ 수정 | `ocr_controller_async.py` | 🔴 필수 |
| `chat/service/supervisor_graph.py` | 동기 | ✅ 수정 | `supervisor_graph_async.py` | 🔴 필수 |
| `chat/service/chat_logic_service.py` | 동기 | ✅ 수정 | `chat_logic_service_async.py` | 🟡 권장 |
| `chat/repository/chat_log_repository.py` | 동기 | ✅ 수정 | `chat_repository_async.py` | 🟡 권장 |
| `level_test/service/test_service.py` | 일부 비동기 | ✅ 수정 | - | 🟢 선택 |
| `auth_manager.py` | 동기 DB 조회 | ✅ 수정 | - | 🟢 선택 |
| - | - | - | `core/executor.py` | 🔴 필수 |

---

## 1. Database 계층

### 📁 `server/database.py` → `server/database_async.py`

<table>
<tr>
<th width="50%">❌ 현재 (동기)</th>
<th width="50%">✅ 최적화 (비동기)</th>
</tr>
<tr>
<td>

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "mysql+pymysql://..."

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**문제:**
- `pymysql` - 동기 드라이버
- `SessionLocal()` - 동기 세션
- `yield db` - event loop 차단

</td>
<td>

```python
# database_async.py
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)

ASYNC_DATABASE_URL = "mysql+aiomysql://..."

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,          # ✅ 증가
    max_overflow=40        # ✅ 증가
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

**개선:**
- `aiomysql` - 비동기 드라이버
- `AsyncSession` - 비동기 세션
- `await session.close()` - 비차단

</td>
</tr>
</table>

### 변경 사항
- ✅ `pymysql` → `aiomysql`
- ✅ `create_engine` → `create_async_engine`
- ✅ `sessionmaker` → `async_sessionmaker`
- ✅ `Session` → `AsyncSession`
- ✅ `pool_size=20, max_overflow=40` 추가

---

## 2. OCR 서비스 계층

### 📁 `server/ocr/service/ocr_service.py`

<table>
<tr>
<th width="50%">❌ 현재 (동기)</th>
<th width="50%">✅ 최적화 (비동기)</th>
</tr>
<tr>
<td>

```python
# ocr_service.py
class OCRService:
    def __init__(self):
        self.recognizer = OCRRecognizer(...)

    def process_image(
        self,
        file_bytes: bytes
    ):
        np_arr = np.frombuffer(
            file_bytes, np.uint8
        )
        # ❌ 동기, 50-200ms 차단
        image = cv2.imdecode(
            np_arr,
            cv2.IMREAD_COLOR
        )

        # ❌ 동기, 2-5초 차단
        results, _ = self.recognizer.recognize(
            image
        )

        words = [r["text"] for r in results]

        return {
            "count": len(words),
            "words": words
        }
```

**문제:**
- `cv2.imdecode()` - 동기 (50-200ms)
- `recognizer.recognize()` - 동기 (2-5초)
- **총 2-5초 동안 event loop 차단**
- **동시 요청 불가**

</td>
<td>

```python
# ocr_service_async.py
from server.core.executor import (
    run_in_threadpool
)

class AsyncOCRService:
    def __init__(self):
        self.recognizer = OCRRecognizer(...)

    async def process_image(
        self,
        file_bytes: bytes
    ):
        np_arr = np.frombuffer(
            file_bytes, np.uint8
        )
        # ✅ thread pool에서 실행
        image = await run_in_threadpool(
            cv2.imdecode,
            np_arr,
            cv2.IMREAD_COLOR
        )

        # ✅ thread pool에서 실행
        results = await run_in_threadpool(
            self._run_ocr_sync,
            image
        )

        words = [r["text"] for r in results]

        return {
            "count": len(words),
            "words": words
        }

    def _run_ocr_sync(self, image):
        # 동기 코드는 그대로 유지
        results, _ = self.recognizer.recognize(
            image
        )
        return results
```

**개선:**
- `run_in_threadpool` 사용
- **event loop 차단 없음**
- **8개 동시 요청 처리 가능**

</td>
</tr>
</table>

### 변경 사항
- ✅ `def process_image` → `async def process_image`
- ✅ `cv2.imdecode` → `await run_in_threadpool(cv2.imdecode, ...)`
- ✅ `recognize()` → `await run_in_threadpool(self._run_ocr_sync, ...)`
- ✅ `_run_ocr_sync()` 메서드 추가 (동기 래퍼)

---

## 3. 채팅 서비스 계층

### 📁 `server/chat/service/supervisor_graph.py`

<table>
<tr>
<th width="50%">❌ 현재 (동기)</th>
<th width="50%">✅ 최적화 (비동기)</th>
</tr>
<tr>
<td>

```python
# supervisor_graph.py
from transformers import pipeline

# ❌ 모델 로딩 (10초, 서버 시작 시)
cefr_classifier = pipeline(
    "text-classification",
    model="dksysd/cefr-classifier"
)

def predict_cefr_level(
    user_input: str
) -> str:
    # ❌ 추론 (3초, event loop 차단)
    result = cefr_classifier(user_input)
    return result[0]["label"]


def run_chat(
    state: SupervisorState
) -> SupervisorState:
    # ❌ CEFR 분류 (동기)
    cefr_level = predict_cefr_level(
        state["user_input"]
    )

    # ❌ LLM 호출 (동기, 1-3초)
    result = handle_chat_flow(
        state, chat_llm, ...
    )

    return {...result}
```

**문제:**
- `cefr_classifier()` - 동기 (3초)
- `handle_chat_flow()` - 동기 DB/LLM
- **총 5-8초 동안 event loop 차단**

</td>
<td>

```python
# supervisor_graph_async.py
from transformers import pipeline
from server.core.executor import (
    run_in_threadpool
)

# ✅ 모델 로딩 (동일, 1회만)
cefr_classifier = pipeline(
    "text-classification",
    model="dksysd/cefr-classifier"
)

async def predict_cefr_level_async(
    user_input: str
) -> str:
    # ✅ thread pool에서 추론
    result = await run_in_threadpool(
        cefr_classifier, user_input
    )
    return result[0]["label"]


async def run_chat(
    state: SupervisorState
) -> SupervisorState:
    # ✅ CEFR 분류 (비동기)
    cefr_level = await predict_cefr_level_async(
        state["user_input"]
    )

    # ✅ LLM 호출 (비동기)
    result = await handle_chat_flow_async(
        state, chat_llm, ...
    )

    return {...result}
```

**개선:**
- `predict_cefr_level_async` - 비동기
- `handle_chat_flow_async` - 비동기
- **event loop 차단 없음**

</td>
</tr>
</table>

### 변경 사항
- ✅ `def predict_cefr_level` → `async def predict_cefr_level_async`
- ✅ `cefr_classifier(...)` → `await run_in_threadpool(cefr_classifier, ...)`
- ✅ `def run_chat` → `async def run_chat`
- ✅ `handle_chat_flow` → `await handle_chat_flow_async`

---

## 4. DB Repository 계층

### 📁 `server/chat/repository/chat_log_repository.py`

<table>
<tr>
<th width="50%">❌ 현재 (동기)</th>
<th width="50%">✅ 최적화 (비동기)</th>
</tr>
<tr>
<td>

```python
# chat_log_repository.py
from sqlalchemy.orm import Session

def get_recent_chat_logs(
    db: Session,
    user_id: int,
    limit: int = 10
):
    # ❌ 동기 쿼리 (50-200ms 차단)
    logs = (
        db.query(ChatLog)
        .filter(...)
        .order_by(ChatLog.createdAt.desc())
        .limit(limit)
        .all()
    )
    logs.reverse()
    return logs
```

**문제:**
- `db.query()` - 동기 (50-200ms)
- **event loop 차단**

</td>
<td>

```python
# chat_repository_async.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_recent_chat_logs_async(
    db: AsyncSession,
    user_id: int,
    limit: int = 10
):
    # ✅ 비동기 쿼리
    result = await db.execute(
        select(ChatLog)
        .filter(...)
        .order_by(ChatLog.createdAt.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    logs.reverse()
    return logs
```

**개선:**
- `await db.execute()` - 비동기
- **event loop 차단 없음**

</td>
</tr>
</table>

### 변경 사항
- ✅ `Session` → `AsyncSession`
- ✅ `def get_recent_chat_logs` → `async def get_recent_chat_logs_async`
- ✅ `db.query(...)` → `await db.execute(select(...))`
- ✅ `.all()` → `.scalars().all()`

---

## 5. Controller 계층

### 📁 `server/ocr/controller/ocr_controller.py`

<table>
<tr>
<th width="50%">❌ 현재 (동기)</th>
<th width="50%">✅ 최적화 (비동기)</th>
</tr>
<tr>
<td>

```python
# ocr_controller.py
from server.ocr.service.ocr_service import (
    OCRService
)

router = APIRouter(...)
service = OCRService()

@router.post("/extract")
async def extract_text(
    file: UploadFile = File(...)
):
    file_bytes = await file.read()
    filename = file.filename or ""

    # ❌ 동기 서비스 호출
    #    (async 함수에서 동기 함수 호출)
    response = service.process_image(
        file_bytes, filename
    )

    return response
```

**문제:**
- `service.process_image()` - 동기
- **async 함수에서 동기 함수 호출**
- **event loop 차단**

</td>
<td>

```python
# ocr_controller_async.py
from server.ocr.service.ocr_service_async import (
    AsyncOCRService
)

router = APIRouter(...)
service = AsyncOCRService()

@router.post("/extract")
async def extract_text_async(
    file: UploadFile = File(...)
):
    file_bytes = await file.read()
    filename = file.filename or ""

    # ✅ 비동기 서비스 호출
    response = await service.process_image(
        file_bytes, filename
    )

    return response
```

**개선:**
- `await service.process_image()` - 비동기
- **완전한 비동기 체인**

</td>
</tr>
</table>

### 변경 사항
- ✅ `OCRService` → `AsyncOCRService`
- ✅ `service.process_image(...)` → `await service.process_image(...)`

---

## 6. LLM 호출

### LangChain LLM

<table>
<tr>
<th width="50%">❌ 현재 (동기)</th>
<th width="50%">✅ 최적화 (비동기)</th>
</tr>
<tr>
<td>

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")

# ❌ 동기 호출 (1-3초 차단)
response = llm.invoke(messages)
text = response.content
```

**문제:**
- `llm.invoke()` - 동기 (1-3초)
- **event loop 차단**

</td>
<td>

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")

# ✅ 비동기 호출
response = await llm.ainvoke(messages)
text = response.content
```

**개선:**
- `ainvoke()` - 비동기
- **event loop 차단 없음**

</td>
</tr>
</table>

### 변경 사항
- ✅ `llm.invoke(...)` → `await llm.ainvoke(...)`

---

## 7. 파일 I/O

### aiofiles 사용

<table>
<tr>
<th width="50%">❌ 현재 (동기)</th>
<th width="50%">✅ 최적화 (비동기)</th>
</tr>
<tr>
<td>

```python
async def save_file(file: UploadFile):
    contents = await file.read()

    # ❌ 동기 파일 쓰기
    with open("temp.png", "wb") as f:
        f.write(contents)
```

**문제:**
- `open()`, `f.write()` - 동기
- **event loop 차단**

</td>
<td>

```python
import aiofiles

async def save_file(file: UploadFile):
    contents = await file.read()

    # ✅ 비동기 파일 쓰기
    async with aiofiles.open(
        "temp.png", "wb"
    ) as f:
        await f.write(contents)
```

**개선:**
- `aiofiles.open()` - 비동기
- **event loop 차단 없음**

</td>
</tr>
</table>

### 변경 사항
- ✅ `open(...)` → `async with aiofiles.open(...)`
- ✅ `f.write(...)` → `await f.write(...)`

---

## 📊 성능 영향 비교

| 병목 위치 | 현재 (동기) | 최적화 (비동기) | 개선율 |
|-----------|------------|----------------|--------|
| **OCR 처리** | 5초 (순차) | 5초 (병렬) | **80% 감소** (5개 동시) |
| **CEFR 분류** | 3초 (순차) | 3초 (병렬) | **80% 감소** (5개 동시) |
| **DB 쿼리** | 100ms (순차) | 100ms (병렬) | **90% 감소** (10개 동시) |
| **LLM 호출** | 2초 (순차) | 2초 (병렬) | **80% 감소** (5개 동시) |

---

## 🚀 즉시 적용 체크리스트

- [ ] `requirements.txt`에 추가 패키지 설치
  - [ ] `aiomysql`
  - [ ] `aiofiles`
  - [ ] `asyncio`
- [ ] `server/core/executor.py` 생성
- [ ] `server/database_async.py` 생성
- [ ] `server/ocr/service/ocr_service_async.py` 생성
- [ ] `server/ocr/controller/ocr_controller_async.py` 생성
- [ ] `server/chat/service/supervisor_graph_async.py` 생성
- [ ] `main.py` 수정 (비동기 라우터 등록)
- [ ] uvicorn/gunicorn 설정 변경 (workers 증가)
- [ ] 테스트 실행 (동시 요청 5개)
- [ ] 성능 측정 (before/after)

---

## ⚠️ 주의사항

1. **점진적 마이그레이션**
   - 기존 동기 코드 유지 (`database.py`)
   - 새로운 비동기 코드 추가 (`database_async.py`)
   - 하나씩 교체

2. **DB 모델 호환성**
   - SQLAlchemy 모델은 동일하게 사용 가능
   - 쿼리 방식만 변경 (`db.query` → `db.execute`)

3. **Thread Pool 크기**
   - `ThreadPoolExecutor(max_workers=8)`
   - CPU 코어 수에 맞게 조정
   - 너무 크면 메모리 부족

4. **Timeout 설정**
   - uvicorn: `--timeout-keep-alive 120`
   - Nginx: `proxy_read_timeout 300s`

---

## ✅ 예상 결과

**적용 전:**
- OCR 5개 동시: 25초 (순차 처리)
- 채팅 10개 동시: 55초 (순차 처리)

**적용 후:**
- OCR 5개 동시: 5초 (병렬 처리)
- 채팅 10개 동시: 8초 (병렬 처리)

**개선율:**
- **응답 시간: 80% 감소**
- **처리량: 400% 증가**
- **동시 처리: 700% 증가**
