from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from server.highlight.service.highlight_service import HighlightService

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
        # 파일 읽기
        file_bytes = await image.read()

        # 이미지 처리 + OCR (한 번에!)
        result = highlight_service.process_and_recognize(file_bytes, h, s, v)

        return result
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
