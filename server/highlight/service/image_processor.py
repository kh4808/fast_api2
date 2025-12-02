import cv2
import numpy as np


def _apply_sv_floor(hsv_image, s, v, floor=30):
    """채도/명도 보정: s 또는 v가 너무 낮으면 하한선(floor)로 끌어올림."""
    if s < floor or v < floor:
        hsv_channels = list(cv2.split(hsv_image))  # [H, S, V]
        # np.maximum은 dtype 유지. floor는 int로 캐스팅
        hsv_channels[1] = np.maximum(hsv_channels[1], np.uint8(floor))  # S
        hsv_channels[2] = np.maximum(hsv_channels[2], np.uint8(floor))  # V
        hsv_image = cv2.merge(hsv_channels)
    return hsv_image


def _inrange_h_wrap(hsv_image, h, s_thresh, v_thresh, hue_margin=5):
    """Hue wrap(0~179) 고려하여 inRange 마스크 생성."""
    lower_hue = (h - hue_margin) % 180
    upper_hue = (h + hue_margin) % 180

    if lower_hue > upper_hue:
        lower1 = np.array([0,          s_thresh, v_thresh], dtype=np.uint8)
        upper1 = np.array([upper_hue,  255,      255],      dtype=np.uint8)
        lower2 = np.array([lower_hue,  s_thresh, v_thresh], dtype=np.uint8)
        upper2 = np.array([179,        255,      255],      dtype=np.uint8)
        mask1 = cv2.inRange(hsv_image, lower1, upper1)
        mask2 = cv2.inRange(hsv_image, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)
    else:
        lower = np.array([lower_hue, s_thresh, v_thresh], dtype=np.uint8)
        upper = np.array([upper_hue, 255,      255],      dtype=np.uint8)
        mask = cv2.inRange(hsv_image, lower, upper)
    return mask


def _composite_on_white(original_bgr, mask_255):
    """마스크(0/255) 영역은 원본 유지, 나머지는 흰색으로."""
    white_background = np.full_like(original_bgr, 255)
    result = np.where(mask_255[:, :, np.newaxis] == 255, original_bgr, white_background)
    return result


def process_highlight_image(original_bgr, h, s, v):
    """
    형광펜 하이라이트 영역 추출 및 처리:
    - HSV 변환
    - s/v 하한 보정(최소 30)
    - hue ±5, s/v ≥ 30
    - morphology close -> dilate
    - 흰 배경 합성
    """
    hsv_image = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2HSV)
    hsv_image = _apply_sv_floor(hsv_image, s, v, floor=30)

    # ±5, S/V 하한 30
    mask = _inrange_h_wrap(hsv_image, h, s_thresh=30, v_thresh=30, hue_margin=5)

    # 모폴로지(닫기) + 팽창
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask_cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)

    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    final_mask = cv2.dilate(mask_cleaned, kernel_dilate, iterations=1)

    result = _composite_on_white(original_bgr, final_mask)
    return result
