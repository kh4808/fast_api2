import cv2
import numpy as np
import io
from server.ocr.core.ocr_recognizer import OCRRecognizer


class OCRService:
    def __init__(self):
        self.recognizer = OCRRecognizer(highlighter_padding=5)

    def process_image(self, file_bytes: bytes, filename: str = ""):
        """
        이미지 또는 PDF 파일을 처리하여 OCR 수행

        Args:
            file_bytes: 파일의 바이트 데이터
            filename: 파일명 (확장자 확인용)

        Returns:
            dict: {"count": int, "words": List[str]}
        """
        # 파일 타입 확인
        is_pdf = filename.lower().endswith('.pdf') or self._is_pdf_bytes(file_bytes)

        if is_pdf:
            # PDF 처리
            return self._process_pdf(file_bytes)
        else:
            # 이미지 처리
            return self._process_image_bytes(file_bytes)

    def _is_pdf_bytes(self, file_bytes: bytes) -> bool:
        """바이트 데이터가 PDF인지 확인 (매직 넘버 체크)"""
        return file_bytes[:4] == b'%PDF'

    def _process_image_bytes(self, file_bytes: bytes):
        """기존 이미지 처리 로직"""
        np_arr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("이미지를 디코딩할 수 없습니다. 지원되는 형식: PNG, JPG, JPEG")

        # OCR 결과 전체 받아오기
        results, _ = self.recognizer.recognize(image)

        # ✅ 단어 리스트만 추출
        words = [r["text"] for r in results if r.get("text")]

        return {
            "count": len(words),
            "words": words
        }

    def _process_pdf(self, file_bytes: bytes):
        """
        PDF를 이미지로 변환 후 OCR 수행

        PyMuPDF(fitz)를 사용하여 PDF의 각 페이지를 이미지로 변환
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

            # 페이지를 이미지로 렌더링 (DPI 150으로 적절한 품질 확보)
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

        pdf_document.close()

        return {
            "count": len(all_words),
            "words": all_words,
            "pages": len(pdf_document)  # 추가 정보: 페이지 수
        }
