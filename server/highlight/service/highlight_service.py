import cv2
import numpy as np
import base64
import easyocr
from .image_processor import process_highlight_image


class HighlightService:
    def __init__(self):
        # EasyOCR Reader 초기화 (영어만)
        self.ocr_reader = easyocr.Reader(['en'], gpu=False)

    def _encode_image_to_base64(self, bgr_img):
        """이미지를 base64로 인코딩"""
        _, buffer = cv2.imencode(".png", bgr_img)
        return base64.b64encode(buffer).decode("utf-8")

    def process_and_recognize(self, file_bytes: bytes, h: int, s: int, v: int):
        """
        이미지를 HSV 값으로 처리하여 형광펜 영역 추출 및 텍스트 인식
        (메모리에서만 처리, 파일 저장 없음)

        Args:
            file_bytes: 업로드된 이미지 파일의 바이트 데이터
            h: Hue 값 (0-179)
            s: Saturation 값 (0-255)
            v: Value 값 (0-255)

        Returns:
            dict: 편집된 이미지 정보 + 인식된 텍스트 목록
        """
        # 바이트 데이터를 numpy 배열로 변환
        np_arr = np.frombuffer(file_bytes, np.uint8)
        original_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if original_bgr is None:
            raise ValueError("이미지를 읽을 수 없습니다")

        # 형광펜 하이라이트 영역 처리 (메모리에서만)
        edited_image = process_highlight_image(original_bgr, h, s, v)

        # EasyOCR로 텍스트 인식 (바로 이미지 배열 전달)
        ocr_results = self.ocr_reader.readtext(edited_image)

        # 텍스트만 추출 (bbox, text, confidence 중에서 text만)
        words = [text for (bbox, text, confidence) in ocr_results]

        # 응답 데이터 생성
        return {
            "message": "processed",
            "base64": self._encode_image_to_base64(edited_image),
            "words": words,
            "word_count": len(words)
        }
