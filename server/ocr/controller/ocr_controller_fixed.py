from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from server.ocr.service.ocr_service import OCRService

router = APIRouter(prefix="/api/ocr", tags=["OCR"])
service = OCRService()

@router.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    """
    📤 이미지 또는 PDF 파일 업로드 후 OCR 결과 반환

    지원 형식:
    - 이미지: PNG, JPG, JPEG, GIF, WEBP
    - 문서: PDF (모든 페이지 처리)

    Returns:
        {
            "count": 인식된 단어 수,
            "words": ["word1", "word2", ...],
            "pages": PDF의 경우 페이지 수 (옵션)
        }
    """
    try:
        file_bytes = await file.read()
        filename = file.filename or ""

        # ✅ filename을 service에 전달하여 PDF/이미지 자동 판별
        response = service.process_image(file_bytes, filename)

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
        return JSONResponse(
            content={"error": f"OCR 처리 실패: {str(e)}"},
            status_code=500
        )
