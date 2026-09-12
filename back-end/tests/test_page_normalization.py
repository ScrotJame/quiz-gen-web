"""Tests cho module page_normalization: auto_crop_document, auto_deskew, robust_sort_lines."""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from src.services.ai.page_normalization import (
    _four_point_transform,
    _order_points,
    auto_crop_document,
    auto_deskew,
    normalize_page,
    robust_sort_lines,
)


def _create_mock_document_image(width: int = 400, height: int = 600, angle: float = 0.0) -> np.ndarray:
    """Tạo ảnh tài liệu mẫu có nền tối và trang giấy trắng có các dòng kẻ ngang."""
    # Nền tối (bàn/chiếu)
    canvas = np.zeros((height + 100, width + 100, 3), dtype=np.uint8)
    canvas[:] = (40, 40, 40)

    # Trang giấy trắng
    doc = np.ones((height, width, 3), dtype=np.uint8) * 255
    # Vẽ vài dòng chữ giả lập (đoạn thẳng ngang màu đen)
    for y in range(80, height - 80, 50):
        cv2.line(doc, (40, y), (width - 40, y), (0, 0, 0), 3)

    if abs(angle) > 0.01:
        center = (width // 2, height // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        doc = cv2.warpAffine(doc, M, (width, height), borderValue=(40, 40, 40))

    canvas[50 : 50 + height, 50 : 50 + width] = doc
    return canvas


def test_order_points() -> None:
    """Kiểm tra thuật toán sắp xếp 4 đỉnh tứ giác theo thứ tự TL, TR, BR, BL."""
    pts = np.array([[100, 100], [0, 100], [100, 0], [0, 0]], dtype=float)
    ordered = _order_points(pts)
    np.testing.assert_array_equal(ordered[0], [0, 0])      # Top-left
    np.testing.assert_array_equal(ordered[1], [100, 0])    # Top-right
    np.testing.assert_array_equal(ordered[2], [100, 100])  # Bottom-right
    np.testing.assert_array_equal(ordered[3], [0, 100])    # Bottom-left


def test_four_point_transform() -> None:
    """Kiểm tra kéo phẳng ảnh bằng 4 điểm góc."""
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    pts = np.array([[20, 20], [180, 20], [180, 180], [20, 180]], dtype=float)
    warped = _four_point_transform(img, pts)
    assert warped.shape[0] > 0
    assert warped.shape[1] > 0


def test_auto_crop_document_fallback_on_blank() -> None:
    """Khi ảnh trắng hoàn toàn không có contour nổi bật, trả về ảnh gốc."""
    blank = np.ones((300, 300, 3), dtype=np.uint8) * 255
    out = auto_crop_document(blank)
    assert out.shape == blank.shape


def test_auto_crop_document_crops_white_page() -> None:
    """Tự động phát hiện và cắt vùng trang giấy trắng trên nền tối."""
    img = _create_mock_document_image(300, 400, angle=0.0)
    out = auto_crop_document(img)
    assert out is not None
    assert out.shape[0] > 100
    assert out.shape[1] > 100


def test_auto_deskew_no_lines_returns_same() -> None:
    """Khi không có đường thẳng, auto_deskew giữ nguyên ảnh."""
    blank = np.ones((200, 200, 3), dtype=np.uint8) * 255
    out = auto_deskew(blank)
    np.testing.assert_array_equal(out, blank)


def test_auto_deskew_horizontal_lines() -> None:
    """Với các đoạn thẳng ngang song song nghiêng 4 độ, auto_deskew ước lượng và xoay lại."""
    canvas = np.ones((400, 500, 3), dtype=np.uint8) * 255
    for y in range(50, 350, 40):
        cv2.line(canvas, (50, y), (450, y), (0, 0, 0), 2)

    # Xoay canvas 4 độ
    center = (250, 200)
    M = cv2.getRotationMatrix2D(center, 4.0, 1.0)
    tilted = cv2.warpAffine(canvas, M, (500, 400), borderValue=(255, 255, 255))

    out = auto_deskew(tilted)
    assert out is not None
    assert out.shape[0] > 0


def test_robust_sort_lines_sorting() -> None:
    """Kiểm tra robust_sort_lines sắp xếp theo hàng và từ trái sang phải."""
    boxes = [
        # Hàng 2: bên phải, bên trái
        {"polygon": [[200, 100], [280, 100], [280, 120], [200, 120]], "id": "row2_right"},
        {"polygon": [[20, 105], [100, 105], [100, 125], [20, 125]], "id": "row2_left"},
        # Hàng 1: bên phải, bên trái
        {"polygon": [[180, 20], [260, 20], [260, 40], [180, 40]], "id": "row1_right"},
        {"polygon": [[10, 22], [90, 22], [90, 42], [10, 42]], "id": "row1_left"},
    ]

    sorted_boxes = robust_sort_lines(boxes)
    assert len(sorted_boxes) == 4
    # Thứ tự phải là: row1_left -> row1_right -> row2_left -> row2_right
    assert sorted_boxes[0]["id"] == "row1_left"
    assert sorted_boxes[1]["id"] == "row1_right"
    assert sorted_boxes[2]["id"] == "row2_left"
    assert sorted_boxes[3]["id"] == "row2_right"


def test_robust_sort_lines_raw_boxes() -> None:
    """Kiểm tra robust_sort_lines với định dạng list 4 điểm tọa độ thô."""
    boxes = [
        [[10, 50], [90, 50], [90, 70], [10, 70]],
        [[10, 10], [90, 10], [90, 30], [10, 30]],
    ]
    sorted_b = robust_sort_lines(boxes)
    assert len(sorted_b) == 2
    # Box trên (y=10) phải đứng trước box dưới (y=50)
    assert sorted_b[0][0][1] == 10
    assert sorted_b[1][0][1] == 50


def test_normalize_page_pipeline() -> None:
    """Kiểm tra normalize_page chạy trơn tru qua cả auto_crop và auto_deskew."""
    img = _create_mock_document_image(300, 400, angle=3.0)
    out = normalize_page(img)
    assert out is not None
    assert isinstance(out, np.ndarray)
    assert out.ndim == 3
    assert out.shape[0] > 50
    assert out.shape[1] > 50
