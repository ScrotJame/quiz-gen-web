import os
import pytest
from src.services.ai.local_ocr import get_local_ocr_engine

IMG_PATH = os.path.join(
    os.path.dirname(__file__),
    "img_test",
    "1789221134481_113071411994592294_8763807615947960872_e150c0f4b2503c99046398c5ade3fb34.jpg",
)

TARGET_EXPECTED_LINES = [
    "của chủ nghĩa tư bản",
    "b. Xây dựng các giá trị tốt đẹp như lao động, sáng tao, công bằng, dân chủ,",
    "bình đẳng, tự do",
    "C. Bảo vệ nền tảng tư tưởng của Đảng Cộng sản",
    "d. Tất cả các đáp án",
    "32.Tìm đáp án đúng nhất về điều kiện khách quan quy định sứ mệnh",
    "lịch sử của giai cấp công nhân?",
    "a. Sự phát triển của các phong trào công nhân",
    "b. Sự ra đời của Đảng Cộng sản",
    "c. Địa vị kinh tế và chính trị - xã hôi của giai cấp công nhân",
    "d. Sự liên minh giữa giai cấp công nhân với giai cấp nông dân và các tầng",
    "lớp lao động khác",
    "33.Chỉ ra nhân tố chủ quan quan trọng nhất đễ giai cấp công nhân thực",
    "hiện thắng lợi sứ mệnh lịch sử cũa mình?",
    "a. Sự phát triển của phong trào công nhân",
    "b.Sự ra đời của Đảng Cộng sản",
    "c. Sự liên minh giữa giai cấp công nhân với giai cấp nông dân và các tầng",
    "lớp lao động khác",
    "d. Môi trường lao động hiện đại",
    "34.Nhân tố nào quan trọng nhất được coi là ngọn cờ tư tưởng dẫn dắt giai cấp công nhân hoàn thành sứ mệnh lịch sử của mình?",
    "a. Tinh thần đoàn kết",
    "b. Chủ nghĩa Mác-Lênin",
    "c. Lý luận học",
    "d. Tinh thần cách mạng",
    "35. Đảng Cộng sản ra đời và đảm nhận vai trò lãnh đạo phong trào cách mạng của giai cấp công nhân đã đánh dấu điều gì?",
    "a. Giai cấp công nhân chí phát triển về lượng",
    "ba bự trưởng thành vượt bậc của giai cấp công nhân",
    "c. Dự báo sự thắng lợi của giai cấp tư bản",
]


@pytest.mark.skipif(not os.path.exists(IMG_PATH), reason="Ảnh test không tồn tại")
def test_local_ocr_exact_match_sample_image():
    engine = get_local_ocr_engine()
    if engine is None:
        pytest.skip("Local OCR engine không khả dụng")

    with open(IMG_PATH, "rb") as f:
        img_bytes = f.read()

    ocr_text, line_count, _ = engine.extract_text_sync(img_bytes)
    lines = ocr_text.strip().splitlines()

    assert len(lines) == len(TARGET_EXPECTED_LINES)
    for idx, (got, exp) in enumerate(zip(lines, TARGET_EXPECTED_LINES)):
        assert got == exp, f"Lệch dòng {idx}: GOT '{got}' != EXP '{exp}'"
