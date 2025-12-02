# server/ocr/service/ocr_service_async.py - 비동기 OCR 서비스
import cv2
import numpy as np
from server.ocr.core.ocr_recognizer import OCRRecognizer
from server.core.executor import run_in_threadpool


class AsyncOCRService:
    """
    비동기 OCR 서비스

    - 이미지/PDF 디코딩을 thread pool에서 처리
    - OCR 추론을 thread pool에서 처리
    - Event loop 차단 방지
    """

    def __init__(self):
        # ✅ 모델은 한 번만 로딩 (서버 시작 시)
        self.recognizer = OCRRecognizer(highlighter_padding=5)

    async def process_image(self, file_bytes: bytes, filename: str = ""):
        """
        이미지 또는 PDF를 비동기로 처리하여 OCR 수행

        Args:
            file_bytes: 파일의 바이트 데이터
            filename: 파일명 (확장자 확인용)

        Returns:
            dict: {"count": int, "words": List[str], "pages": int (PDF만)}
        """
        # ✅ 파일 타입 확인을 thread pool에서 수행
        is_pdf = filename.lower().endswith('.pdf') or await self._is_pdf_async(file_bytes)

        if is_pdf:
            return await self._process_pdf_async(file_bytes)
        else:
            return await self._process_image_bytes_async(file_bytes)

    async def _is_pdf_async(self, file_bytes: bytes) -> bool:
        """비동기로 PDF 여부 확인 (매직 넘버 체크)"""
        # 간단한 작업이지만 일관성을 위해 async로 유지
        return file_bytes[:4] == b'%PDF'

    async def _process_image_bytes_async(self, file_bytes: bytes):
        """
        이미지 바이트를 비동기로 처리

        ✅ cv2.imdecode와 OCR 추론을 thread pool에서 실행
        """
        # ✅ 1단계: 이미지 디코딩 (thread pool)
        np_arr = np.frombuffer(file_bytes, np.uint8)
        image = await run_in_threadpool(cv2.imdecode, np_arr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("이미지를 디코딩할 수 없습니다. 지원되는 형식: PNG, JPG, JPEG")

        # ✅ 2단계: OCR 추론 (thread pool)
        results = await run_in_threadpool(self._run_ocr_sync, image)

        # ✅ 단어 리스트만 추출
        words = [r["text"] for r in results if r.get("text")]

        return {
            "count": len(words),
            "words": words
        }

    def _run_ocr_sync(self, image: np.ndarray):
        """
        동기 OCR 추론 (thread pool에서 실행됨)

        ⚠️ 이 함수는 직접 호출하지 말고 run_in_threadpool을 통해서만 호출
        """
        results, _ = self.recognizer.recognize(image)
        return results

    async def _process_pdf_async(self, file_bytes: bytes):
        """
        PDF를 비동기로 처리

        ✅ PDF 렌더링과 OCR을 thread pool에서 실행
        """
        # PDF 처리는 CPU 집약적이므로 전체를 thread pool에서 실행
        result = await run_in_threadpool(self._process_pdf_sync, file_bytes)
        return result

    def _process_pdf_sync(self, file_bytes: bytes):
        """
        동기 PDF 처리 (thread pool에서 실행됨)

        ⚠️ 이 함수는 직접 호출하지 말고 run_in_threadpool을 통해서만 호출
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "PDF 처리를 위해 PyMuPDF가 필요합니다. "
                "설치: pip install PyMuPDF"
            )

        all_words = []

        # PDF 문서 열기
        try:
            pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"PDF 파일을 열 수 없습니다: {str(e)}")

        # 각 페이지 처리
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]

            # 페이지를 이미지로 렌더링
            pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))

            # Pixmap을 numpy 배열로 변환
            img_data = pix.tobytes("png")
            np_arr = np.frombuffer(img_data, np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if image is None:
                print(f"Warning: 페이지 {page_num + 1}을(를) 이미지로 변환할 수 없습니다.")
                continue

            # OCR 수행
            try:
                results, _ = self.recognizer.recognize(image)
                words = [r["text"] for r in results if r.get("text")]
                all_words.extend(words)
            except Exception as e:
                print(f"Warning: 페이지 {page_num + 1} OCR 실패: {str(e)}")
                continue

        page_count = len(pdf_document)
        pdf_document.close()

        return {
            "count": len(all_words),
            "words": all_words,
            "pages": page_count
        }
