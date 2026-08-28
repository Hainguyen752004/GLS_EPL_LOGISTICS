import unicodedata

from services.errors import DomainError, conflict


READY_DRIVER_STATUS = "🟢 Rảnh (Sẵn sàng)"


def normalized_text(value):
    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    return " ".join("".join(char for char in text if unicodedata.category(char) != "Mn").split())


def is_ready_driver(driver):
    status = normalized_text(getattr(driver, "status", ""))
    busy_markers = ("ban", "dang theo xe", "dang thuc hien", "dang van chuyen")
    return not any(marker in status for marker in busy_markers) and (
        "ranh" in status or "san sang" in status or status == "available"
    )


def require_crew(main_driver, co_driver=None):
    if normalized_text(getattr(main_driver, "role", "")) not in ("", "lai xe chinh"):
        raise conflict("MAIN_DRIVER_ROLE_INVALID", "Nhân sự được chọn không có vai trò tài xế chính.")
    if not is_ready_driver(main_driver):
        raise conflict("DRIVER_BUSY", f"Tài xế {main_driver.id} không ở trạng thái sẵn sàng.")
    if co_driver is None:
        return
    if co_driver.id == main_driver.id:
        raise DomainError("CREW_DUPLICATE", "Tài xế chính và phụ xe phải là hai người khác nhau.", 422)
    if normalized_text(getattr(co_driver, "role", "")) != "phu xe":
        raise conflict("CO_DRIVER_ROLE_INVALID", "Nhân sự được chọn không có vai trò phụ xe.")
    if not is_ready_driver(co_driver):
        raise conflict("CO_DRIVER_BUSY", f"Phụ xe {co_driver.id} không ở trạng thái sẵn sàng.")


def mark_crew_busy(driver, vehicle_id, reference):
    driver.status = f"Đang thực hiện {reference}"
    driver.assigned_vehicle = vehicle_id


def mark_crew_ready(driver):
    driver.status = READY_DRIVER_STATUS
    driver.assigned_vehicle = "Chưa gán"
