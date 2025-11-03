import cv2
import numpy as np
from server.ocr.core.ocr_recognizer import OCRRecognizer


class OCRService:
    def __init__(self):
        self.recognizer = OCRRecognizer(highlighter_padding=5)

    def process_image(self, file_bytes: bytes):
        np_arr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # OCR 결과 전체 받아오기
        results, _ = self.recognizer.recognize(image)

        # ✅ 단어 리스트만 추출
        words = [r["text"] for r in results if r.get("text")]

        return {
            "count": len(words),
            "words": words  # ← ✅ bbox 없이 텍스트만 반환
        }
