from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from server.highlight.service.highlight_service import HighlightService
import logging

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

router = APIRouter(prefix="/api/highlight", tags=["Highlight"])
highlight_service = HighlightService()


@router.post("/process")
async def process_highlight_text(
    image: UploadFile = File(...),
    h: int = Form(...),
    s: int = Form(...),
    v: int = Form(...)
):
    """
    형광펜 하이라이트 영역 추출 및 텍스트 인식 (올인원)
    메모리에서만 처리되어 디스크 저장 없음

    Args:
        image: 업로드할 이미지 파일
        h: Hue 값 (0-179) - 형광펜 색상
        s: Saturation 값 (0-255) - 채도
        v: Value 값 (0-255) - 명도

    Returns:
        {
            "message": "processed",
            "base64": "...",
            "words": ["word1", "word2", ...],
            "word_count": 10
        }
    """
    try:
        logger.info("="*80)
        logger.info("[STEP 1] 하이라이트 처리 요청 수신")
        logger.info(f"  - 파일명: {image.filename}")
        logger.info(f"  - Content-Type: {image.content_type}")
        logger.info(f"  - HSV 파라미터: H={h}, S={s}, V={v}")

        # 파일 읽기
        logger.info("[STEP 2] 파일 읽기 시작")
        file_bytes = await image.read()
        file_size = len(file_bytes)
        logger.info(f"  - 파일 크기: {file_size:,} bytes ({file_size/1024:.2f} KB)")

        # 이미지 처리 + OCR (한 번에!)
        logger.info("[STEP 3] 하이라이트 처리 및 OCR 시작")
        result = highlight_service.process_and_recognize(file_bytes, h, s, v)

        logger.info("[STEP 4] 처리 완료")
        logger.info(f"  - 인식된 단어 수: {result['word_count']}")
        logger.info(f"  - 인식된 단어: {result['words']}")
        logger.info(f"  - Base64 이미지 길이: {len(result['base64'])} 문자")
        logger.info("="*80)

        return result
    except ValueError as e:
        logger.error(f"[ERROR] ValueError 발생: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"[ERROR] 예외 발생: {str(e)}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)
