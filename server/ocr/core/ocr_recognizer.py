import string
import cv2
import numpy as np
from paddleocr import PaddleOCR


class OCRRecognizer:
    def __init__(self, highlighter_padding: int = 5):
        self.highlighter_padding = highlighter_padding

        # ✅ 원본과 동일한 PaddleOCR 설정 (predict 기반)
        self.text_recognition = PaddleOCR(
            use_doc_unwarping=False,
            use_textline_orientation=False,
            use_doc_orientation_classify=False,
        )

        self.remove_punctuation_translator = str.maketrans('', '', string.punctuation)

    def recognize(self, image: np.ndarray):
        results = []
        highlights_mask, highlights_regions = self._detect_highlights_text(image)

        for region in highlights_regions:
            x, y = map(int, region["position"])
            w, h = map(int, region["size"])

            # 🔹 ROI 크롭 (형광펜 영역)
            x1 = max(0, x - self.highlighter_padding)
            y1 = max(0, y - self.highlighter_padding)
            x2 = min(image.shape[1], x + w + self.highlighter_padding)
            y2 = min(image.shape[0], y + h + self.highlighter_padding)
            cropped = image[y1:y2, x1:x2]

            # ✅ predict() 사용 (ocr()보다 문장 인식이 안정적)
            preds = self.text_recognition.predict(cropped)

            if not preds or not isinstance(preds, list):
                continue

            # PaddleOCR predict() 결과는 리스트이며 각 항목은 dict
            text_result = preds[0] if isinstance(preds[0], dict) else preds[0][0]

            rec_texts = text_result.get("rec_texts", [])
            rec_scores = text_result.get("rec_scores", [])

            for text, conf in zip(rec_texts, rec_scores):
                if len(text.strip()) == 0:
                    continue

                clean_text = text.translate(self.remove_punctuation_translator)
                if conf > 0:
                    results.append({
                        "bbox": [
                            (int(x), int(y)),
                            (int(x + w), int(y)),
                            (int(x + w), int(y + h)),
                            (int(x), int(y + h))
                        ],
                        "text": str(clean_text),
                        "confident": float(conf)
                    })

        return results, highlights_mask

    # 이하 하이라이트 탐지 부분은 그대로 유지
    def _detect_highlights_text(self, image: np.ndarray):
        background_color = self._estimate_background_color(image)
        color_diff = self._calculate_diff_with_background(image, background_color)
        diff_values = color_diff[color_diff > 0]
        threshold = np.percentile(diff_values, 70) if len(diff_values) > 0 else 30
        threshold = max(threshold, 30)
        color_candidates = color_diff > threshold
        return self._get_highlights_mask(image, color_candidates, background_color)

    @staticmethod
    def _estimate_background_color(image: np.ndarray, quantization: int = 32):
        pixels = image.reshape(-1, 3)
        quantized = (pixels // quantization) * quantization + (quantization // 2)
        unique_colors, counts = np.unique(quantized, axis=0, return_counts=True)
        top_idx = np.argsort(counts)[::-1][:5]
        for idx in top_idx:
            color = unique_colors[idx]
            freq = counts[idx]
            bright = np.mean(color)
            perc = freq / len(pixels) * 100
            if 20 < bright < 235 and perc > 5:
                mask = np.all(np.abs(pixels - color) <= quantization, axis=1)
                return np.mean(pixels[mask], axis=0)
        return unique_colors[top_idx[0]]

    @staticmethod
    def _calculate_diff_with_background(image: np.ndarray, bg_color: np.ndarray):
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
        lab_bg = cv2.cvtColor(np.uint8([[bg_color]]), cv2.COLOR_BGR2LAB)[0][0].astype(np.float32)
        return np.linalg.norm(lab - lab_bg, axis=2)

    def _get_highlights_mask(self, image: np.ndarray, color_candidate: np.ndarray, bg_color: np.ndarray):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        s, v = hsv[:, :, 1], hsv[:, :, 2]
        normal = ((s > 80) & (v > 50) & (v < 250))
        reflected = ((s > 30) & (s <= 80) & (v > 220))
        weak = ((s > 50) & (s <= 80) & (v > 100) & (v < 220))
        mask = (color_candidate & (normal | reflected | weak)).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        kernel2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10))
        mask_final = cv2.dilate(mask_clean, kernel2, iterations=1)
        return self._highlights_mask_post_processing(image, mask_final, bg_color)

    def _calculate_background_ratio(self, image: np.ndarray, region_mask: np.ndarray,
                                    bg_color: np.ndarray, threshold: float = 20):
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
        lab_bg = cv2.cvtColor(np.uint8([[bg_color]]), cv2.COLOR_BGR2LAB)[0][0].astype(np.float32)
        region_lab = lab[region_mask > 0]
        dist = np.linalg.norm(region_lab - lab_bg, axis=1)
        bg_pixels = dist < threshold
        return np.sum(bg_pixels) / len(dist)

    def _highlights_mask_post_processing(self, image: np.ndarray,
                                         highlights_mask: np.ndarray, bg_color: np.ndarray):
        h, w = image.shape[:2]
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(highlights_mask, connectivity=8)
        final_mask = np.zeros_like(highlights_mask)
        regions = []

        for i in range(1, num_labels):
            area = int(stats[i, cv2.CC_STAT_AREA])
            x, y = int(stats[i, cv2.CC_STAT_LEFT]), int(stats[i, cv2.CC_STAT_TOP])
            ww, hh = int(stats[i, cv2.CC_STAT_WIDTH]), int(stats[i, cv2.CC_STAT_HEIGHT])
            if area < 200 or area > w * h * 0.3:
                continue
            ratio = ww / hh if hh > 0 else 0
            if ratio < 1 or ratio > 20:
                continue
            region_mask = (labels == i).astype(np.uint8)
            if self._calculate_background_ratio(image, region_mask, bg_color) > 0.4:
                continue
            contours, _ = cv2.findContours(region_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            main_contour = contours[0]
            _, (rect_w, rect_h), _ = cv2.minAreaRect(main_contour)
            if rect_w * rect_h == 0:
                continue
            extent = area / (rect_w * rect_h)
            if extent < 0.6:
                continue
            convex = cv2.convexHull(main_contour)
            convex_area = cv2.contourArea(convex)
            if convex_area == 0 or (area / convex_area) < 0.6:
                continue
            mean_color = tuple(map(float, cv2.mean(image, mask=region_mask)[:3]))
            pixels = image[region_mask > 0]
            color_std = float(np.std(pixels, axis=0).mean())
            if color_std > 60:
                continue
            final_mask[region_mask > 0] = 255
            regions.append({
                "position": (x, y),
                "size": (ww, hh),
                "mask": region_mask,
                "color": mean_color,
                "color_std": color_std,
                "area": area,
                "centroid": (float(centroids[i][0]), float(centroids[i][1]))
            })
        return final_mask, regions
