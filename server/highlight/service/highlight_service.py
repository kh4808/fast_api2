import cv2
import numpy as np
import base64
import easyocr
import logging
from .image_processor import process_highlight_image

logger = logging.getLogger(__name__)


class HighlightService:
    def __init__(self):
        # EasyOCR Reader 초기화 (영어만, 속도 최적화)
        logger.info("EasyOCR Reader 초기화 중 (영어, CPU 모드, 최적화)...")
        self.ocr_reader = easyocr.Reader(
            ['en'],
            gpu=False,
            verbose=False,              # 로그 끄기
            quantize=True,              # 모델 양자화 (속도 향상)
            cudnn_benchmark=False,       # CPU 모드에서는 불필요
        )
        logger.info("EasyOCR Reader 초기화 완료")

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
        logger.info("  [3-1] 바이트 데이터를 numpy 배열로 변환")
        np_arr = np.frombuffer(file_bytes, np.uint8)
        logger.info(f"    - numpy 배열 크기: {np_arr.shape}")

        logger.info("  [3-2] 이미지 디코딩")
        original_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if original_bgr is None:
            logger.error("    - 이미지 디코딩 실패!")
            raise ValueError("이미지를 읽을 수 없습니다")

        logger.info(f"    - 이미지 크기: {original_bgr.shape} (높이x너비x채널)")

        # 형광펜 하이라이트 영역 처리 (메모리에서만)
        logger.info("  [3-3] 형광펜 하이라이트 영역 처리 시작")
        logger.info(f"    - HSV 파라미터: H={h}, S={s}, V={v}")
        edited_image = process_highlight_image(original_bgr, h, s, v)
        logger.info(f"    - 처리된 이미지 크기: {edited_image.shape}")

        # EasyOCR로 텍스트 인식 (바로 이미지 배열 전달, 속도 최적화)
        logger.info("  [3-4] EasyOCR 텍스트 인식 시작")
        ocr_results = self.ocr_reader.readtext(
            edited_image,
            detail=1,                    # bbox, text, confidence 반환
            paragraph=False,             # 단락 병합 끄기 (빠름)
            min_size=10,                 # 최소 텍스트 크기 (작은 노이즈 무시)
            text_threshold=0.7,          # 텍스트 신뢰도 임계값
            low_text=0.4,                # 텍스트 낮은 신뢰도 임계값
            link_threshold=0.4,          # 링크 임계값
            canvas_size=2560,            # 캔버스 크기 제한 (메모리 절약)
            mag_ratio=1.0,               # 확대 비율 (1.0 = 원본)
            batch_size=1,                # 배치 크기
        )
        logger.info(f"    - OCR 결과 개수: {len(ocr_results)}")

        # 텍스트만 추출 (bbox, text, confidence 중에서 text만)
        logger.info("  [3-5] OCR 결과에서 텍스트 추출")
        words = []
        for idx, (bbox, text, confidence) in enumerate(ocr_results):
            logger.info(f"    - [{idx+1}] 텍스트: '{text}' (신뢰도: {confidence:.2f})")
            words.append(text)

        # Base64 인코딩
        logger.info("  [3-6] 이미지를 Base64로 인코딩")
        base64_str = self._encode_image_to_base64(edited_image)
        logger.info(f"    - Base64 문자열 길이: {len(base64_str)}")

        # 응답 데이터 생성
        return {
            "message": "processed",
            "base64": base64_str,
            "words": words,
            "word_count": len(words)
        }
