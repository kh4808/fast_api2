# server/ocr/controller/ocr_controller_async.py - 비동기 OCR 컨트롤러
from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from server.ocr.service.ocr_service_async import AsyncOCRService
import time

router = APIRouter(prefix="/api/ocr", tags=["OCR"])
service = AsyncOCRService()


@router.post("/extract")
async def extract_text_async(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    📤 이미지 또는 PDF 파일 업로드 후 OCR 결과 반환 (비동기)

    지원 형식:
    - 이미지: PNG, JPG, JPEG, GIF, WEBP
    - 문서: PDF (모든 페이지 처리)

    ✅ 최적화 포인트:
    - 파일 읽기: 비동기 (FastAPI 기본)
    - 이미지 디코딩: Thread pool에서 실행
    - OCR 추론: Thread pool에서 실행
    - Event loop 차단 없음 → 동시 처리 가능

    Returns:
        {
            "count": 인식된 단어 수,
            "words": ["word1", "word2", ...],
            "pages": PDF의 경우 페이지 수 (옵션),
            "processing_time": 처리 시간 (초)
        }
    """
    start_time = time.time()

    try:
        # ✅ 1단계: 파일 읽기 (비동기)
        file_bytes = await file.read()
        filename = file.filename or ""

        print(f"[OCR] 📄 File: {filename}, Size: {len(file_bytes)} bytes")

        # ✅ 2단계: OCR 처리 (비동기 - thread pool 사용)
        response = await service.process_image(file_bytes, filename)

        # ✅ 3단계: 처리 시간 측정
        processing_time = time.time() - start_time
        response["processing_time"] = round(processing_time, 2)

        print(f"[OCR] ✅ Processed in {processing_time:.2f}s, {response['count']} words found")

        return response

    except ValueError as e:
        # 파일 형식 오류 등
        return JSONResponse(
            content={"error": str(e)},
            status_code=400
        )
    except ImportError as e:
        # PyMuPDF 미설치
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
    except Exception as e:
        # 기타 오류
        print(f"[OCR] ❌ Error: {str(e)}")
        return JSONResponse(
            content={"error": f"OCR 처리 실패: {str(e)}"},
            status_code=500
        )


@router.post("/extract-background")
async def extract_text_background(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    📤 백그라운드 OCR 처리 (즉시 응답)

    - 큰 PDF나 대량 이미지 처리 시 사용
    - 즉시 job_id를 반환하고 백그라운드에서 처리
    - 결과는 별도 API나 WebSocket으로 전달 (구현 필요)

    Returns:
        {
            "job_id": "unique_job_id",
            "status": "processing",
            "message": "OCR 작업이 백그라운드에서 처리 중입니다"
        }
    """
    import uuid

    job_id = str(uuid.uuid4())
    file_bytes = await file.read()
    filename = file.filename or ""

    # ✅ 백그라운드에서 OCR 처리
    background_tasks.add_task(
        process_ocr_background,
        job_id,
        file_bytes,
        filename
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "OCR 작업이 백그라운드에서 처리 중입니다"
    }


async def process_ocr_background(job_id: str, file_bytes: bytes, filename: str):
    """
    백그라운드 OCR 처리 태스크

    TODO: 결과를 Redis에 저장하거나 WebSocket으로 전송
    """
    try:
        print(f"[OCR BG] 🔄 Processing job: {job_id}")
        result = await service.process_image(file_bytes, filename)
        print(f"[OCR BG] ✅ Job {job_id} completed: {result['count']} words")

        # TODO: 결과를 저장 (Redis, DB 등)
        # await save_result_to_redis(job_id, result)

    except Exception as e:
        print(f"[OCR BG] ❌ Job {job_id} failed: {str(e)}")
        # TODO: 실패 결과 저장
