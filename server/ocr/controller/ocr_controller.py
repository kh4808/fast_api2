from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from server.ocr.service.ocr_service import OCRService

router = APIRouter(prefix="/api/ocr", tags=["OCR"])
service = OCRService()

@router.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    """
    📤 이미지 파일 업로드 후 OCR 결과 반환
    """
    try:
        file_bytes = await file.read()
        response = service.process_image(file_bytes)
        return response
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
