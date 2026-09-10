import unicodedata

from services.errors import DomainError, conflict


READY_DRIVER_STATUS = "🟢 Rảnh (Sẵn sàng)"


def normalized_text(value):
    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    return " ".join("".join(char for char in text if unicodedata.category(char) != "Mn").split())


def is_ready_driver(driver):
    """CHỈ CÒN ĐỌC NHÃN CHO MÀN HÌNH — không dùng làm cửa điều phối nữa.

    Cửa "người này có rảnh không" nay do `services/lich_xe.kiem_to_lai_ranh`
    trả lời, và nó hỏi LỊCH: ca làm việc có phủ khung giờ chuyến không, có phân
    công nào đang mở chồng khung không. Xem đầu tệp `lich_xe.py` để biết vì sao
    một cờ trạng thái không trả lời được câu hỏi đó.

    Giữ hàm này vì vài chỗ hiển thị còn dùng, nhưng ĐỪNG đặt nó vào một cửa
    kiểm: nó là chuỗi tiếng Việt, và bản tiếng Lào không khớp chuỗi nào.
    """
    status = normalized_text(getattr(driver, "status", ""))
    busy_markers = ("ban", "dang theo xe", "dang thuc hien", "dang van chuyen")
    return not any(marker in status for marker in busy_markers) and (
        "ranh" in status or "san sang" in status or status == "available"
    )


def require_crew(main_driver, co_driver=None):
    """Tổ lái có ĐÚNG VAI TRÒ và là hai người khác nhau.

    KHÔNG còn kiểm trạng thái rảnh ở đây. `role` là dữ liệu gốc thật của nhân
    sự — một người là lái chính hay phụ xe không phụ thuộc vào giờ nào — nên nó
    ở lại. Còn "có rảnh không" thì phụ thuộc KHUNG GIỜ, và hàm này không nhận
    khung giờ nào cả: nó chỉ có thể so nhãn, và nhãn thì trôi. Người gọi phải
    gọi thêm `lich_xe.kiem_to_lai_ranh(db, crew_ids, start, end)`.
    """
    if normalized_text(getattr(main_driver, "role", "")) not in ("", "lai xe chinh"):
        raise conflict("MAIN_DRIVER_ROLE_INVALID", "Nhân sự được chọn không có vai trò tài xế chính.")
    if co_driver is None:
        return
    if co_driver.id == main_driver.id:
        raise DomainError("CREW_DUPLICATE", "Tài xế chính và phụ xe phải là hai người khác nhau.", 422)
    if normalized_text(getattr(co_driver, "role", "")) != "phu xe":
        raise conflict("CO_DRIVER_ROLE_INVALID", "Nhân sự được chọn không có vai trò phụ xe.")


def mark_crew_busy(driver, vehicle_id, reference):
    driver.status = f"Đang thực hiện {reference}"
    driver.assigned_vehicle = vehicle_id


def mark_crew_ready(driver):
    driver.status = READY_DRIVER_STATUS
    driver.assigned_vehicle = "Chưa gán"
