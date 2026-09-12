# -*- coding: utf-8 -*-
"""page_normalization.py
----------------------
Giai đoạn "Page Normalization" chèn TRƯỚC pipeline OCR:
(Auto-crop document -> Auto-deskew -> CLAHE -> detector -> VietOCR).

Chức năng:
  1. auto_crop_document: Loại bỏ nền/chiếu/ngón tay, nắn phối cảnh về hình chữ nhật.
  2. auto_deskew: Ước lượng góc nghiêng bằng Hough Transform và xoay lại ảnh thẳng.
  3. robust_sort_lines: Nhóm & sắp xếp dòng theo tâm (centroid) và dung sai Y thích ứng.
  4. normalize_page: Entry point tổng hợp.
"""
from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BƯỚC 1: Document Boundary Detection & Perspective Crop
# ---------------------------------------------------------------------------
def auto_crop_document(image: np.ndarray, debug: bool = False) -> np.ndarray:
    """Tìm contour lớn nhất giống hình chữ nhật (trang giấy) trong ảnh và

    áp dụng four-point perspective transform để:
      - loại bỏ vải hoa văn / bàn / ngón tay ở viền ảnh
      - đồng thời sửa luôn phần lớn góc nghiêng vì trang được ép thẳng
        về đúng hình chữ nhật thay vì hình thang méo.

    Nếu không tìm được contour đủ tin cậy (diện tích quá nhỏ, không phải
    tứ giác), trả về ảnh gốc không đổi -> để auto_deskew() xử lý fallback.
    """
    orig = image.copy()
    h, w = image.shape[:2]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive threshold để chịu được ánh sáng không đều (gáy sách tối hơn mép ngoài)
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 10
    )
    thresh = cv2.dilate(thresh, np.ones((9, 9), np.uint8), iterations=2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return orig

    largest = max(contours, key=cv2.contourArea)
    area_ratio = cv2.contourArea(largest) / float(h * w)

    # Trang giấy phải chiếm phần lớn khung hình, nếu không có khả năng
    # detector bắt nhầm mảng vải/mặt bàn -> bỏ qua, dùng fallback deskew.
    if area_ratio < 0.35:
        if debug:
            logger.debug("[auto_crop_document] area_ratio=%.2f quá nhỏ, bỏ qua crop", area_ratio)
        return orig

    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

    if len(approx) != 4:
        # Không ra đúng tứ giác (trang bị cong nhiều, gấp nếp) -> dùng bounding box
        # nghiêng (minAreaRect) thay vì bỏ cuộc hoàn toàn.
        rect = cv2.minAreaRect(largest)
        box = cv2.boxPoints(rect)
        pts = box.reshape(4, 2)
    else:
        pts = approx.reshape(4, 2)

    ordered = _order_points(pts)
    warped = _four_point_transform(orig, ordered)
    return warped


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Sắp 4 điểm theo thứ tự: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    (tl, tr, br, bl) = pts
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = max(int(heightA), int(heightB))

    # Bảo đảm kích thước hợp lệ
    if maxWidth <= 0 or maxHeight <= 0:
        return image

    dst = np.array(
        [
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1],
        ],
        dtype="float32",
    )

    M = cv2.getPerspectiveTransform(pts.astype("float32"), dst)
    return cv2.warpPerspective(image, M, (maxWidth, maxHeight))


# ---------------------------------------------------------------------------
# BƯỚC 2: Fallback Deskew bằng Hough Transform (khi auto_crop_document
# không tìm được contour trang rõ ràng, ví dụ sách quá cong hoặc chụp cận)
# ---------------------------------------------------------------------------
def auto_deskew(image: np.ndarray, angle_limit: float = 15.0, debug: bool = False) -> np.ndarray:
    """Ước lượng góc nghiêng tổng thể của trang dựa trên các đoạn thẳng văn bản

    (Hough Transform), lấy góc trung vị (robust hơn trung bình vì loại được
    outlier do nhiễu/ngón tay), rồi xoay lại ảnh cho thẳng.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    min_line_len = max(20, int(image.shape[1] * 0.15))
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=150,
        minLineLength=min_line_len,
        maxLineGap=15,
    )

    if lines is None or len(lines) == 0:
        if debug:
            logger.debug("[auto_deskew] không phát hiện đường thẳng nào, giữ nguyên ảnh")
        return image

    angles = []
    pts_lines = lines.reshape(-1, 4)
    for x1, y1, x2, y2 in pts_lines:
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Chỉ giữ các đoạn gần ngang (loại đường dọc như mép sách, gáy sách)
        if -angle_limit <= angle <= angle_limit:
            angles.append(angle)

    if not angles:
        return image

    median_angle = float(np.median(angles))

    if abs(median_angle) < 0.3:
        # Nghiêng quá nhỏ, không đáng xoay (tránh làm mờ ảnh vô ích)
        return image

    if debug:
        logger.debug("[auto_deskew] góc nghiêng ước lượng: %.2f độ", median_angle)

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)

    # Mở rộng canvas để không bị cắt góc khi xoay
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]

    rotated = cv2.warpAffine(
        image,
        M,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


# ---------------------------------------------------------------------------
# BƯỚC 3: Robust Sort — lưới an toàn chống so le tọa độ Y do dư nghiêng/cong
# ---------------------------------------------------------------------------
def robust_sort_lines(boxes: list[Any], y_tolerance_ratio: float = 0.5) -> list[Any]:
    """Thay thế/bổ sung cho việc sort thô theo box[1] (tọa độ y top).

    boxes: list các box hoặc dict chứa 'polygon'
    Hỗ trợ cả 2 định dạng:
      - list 4 điểm tọa độ: [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], ...]
      - list dict: [{"polygon": [[x,y], ...], ...}]

    Ý tưởng: dùng TÂM (centroid) của mỗi box thay vì cạnh trên, và nhóm các
    box vào cùng "hàng" nếu độ lệch tâm-Y nhỏ hơn (chiều cao box * tolerance),
    thay vì so sánh y thô -> tránh trường hợp đáp án 'a.' câu dưới nhảy lên
    ngang hàng với đáp án 'd.' câu trên khi dòng bị nghiêng dư.
    """
    if not boxes:
        return []

    is_dict = isinstance(boxes[0], dict)

    def get_poly(b: Any) -> np.ndarray:
        if is_dict:
            return np.array(b["polygon"], dtype=float)
        return np.array(b, dtype=float)

    def centroid(poly: np.ndarray) -> tuple[float, float]:
        return float(poly[:, 0].mean()), float(poly[:, 1].mean())

    def box_bounds(poly: np.ndarray) -> tuple[float, float, float, float]:
        return (
            float(poly[:, 0].min()),
            float(poly[:, 0].max()),
            float(poly[:, 1].min()),
            float(poly[:, 1].max()),
        )

    enriched = []
    for b in boxes:
        poly = get_poly(b)
        cx, cy = centroid(poly)
        x_min, x_max, y_min, y_max = box_bounds(poly)
        h = max(float(y_max - y_min), 1.0)
        item_data = {
            "_cx": cx,
            "_cy": cy,
            "_h": h,
            "_x_min": x_min,
            "_x_max": x_max,
            "_y_min": y_min,
            "_y_max": y_max,
            "_raw": b,
        }
        if is_dict:
            enriched.append({**b, **item_data})
        else:
            enriched.append(item_data)

    # Sắp theo cy trước để bắt đầu gom nhóm hàng
    enriched.sort(key=lambda item: item["_cy"])

    rows: list[list[dict[str, Any]]] = []
    for b in enriched:
        placed = False
        for row in rows:
            # Hai box chỉ có thể cùng 1 dòng nếu KHÔNG đè lên nhau theo phương ngang
            h_overlapping = False
            for r in row:
                overlap_x = min(b["_x_max"], r["_x_max"]) - max(b["_x_min"], r["_x_min"])
                if overlap_x > 8.0:
                    h_overlapping = True
                    break
            if h_overlapping:
                continue

            ref_cy = float(np.mean([r["_cy"] for r in row]))
            ref_h = float(np.mean([r["_h"] for r in row]))
            if abs(b["_cy"] - ref_cy) <= ref_h * y_tolerance_ratio:
                row.append(b)
                placed = True
                break
        if not placed:
            rows.append([b])

    rows.sort(key=lambda row: float(np.mean([r["_cy"] for r in row])))
    result = []
    for row in rows:
        row.sort(key=lambda r: r["_cx"])
        for r in row:
            result.append(r["_raw"])
    return result


# ---------------------------------------------------------------------------
# Hàm tổng hợp — gọi 1 lần duy nhất ở đầu pipeline
# ---------------------------------------------------------------------------
def normalize_page(image: np.ndarray, debug: bool = False) -> np.ndarray:
    """Entry point: gộp bước 1 (auto_crop_document) + bước 2 (auto_deskew).

    - Bước 1 loại bỏ nền/vải/bàn và kéo phẳng hình thang.
    - Bước 2 xoay lại phần góc nghiêng dư (nếu có).
    """
    if image is None or image.size == 0:
        return image

    cropped = auto_crop_document(image, debug=debug)
    normalized = auto_deskew(cropped, debug=debug)
    return normalized
