"""Các hàm phụ trợ dùng chéo giữa nhiều nhóm route.

Khi tách main.py thành nhiều router, năm hàm dưới đây là những hàm bị dùng ở
nhiều nhóm khác nhau. Để chúng lại trong main.py sẽ tạo import vòng
(main → router → main), còn nhân bản mỗi router một bản là con đường dẫn tới
đúng chỗ đã sai một lần: các bản sao trôi khỏi nhau rồi sinh lỗi khác nhau.

Đặt chúng ở một module không phụ thuộc router nào là cách duy nhất giữ được một
nguồn duy nhất.
"""

import json

from fastapi import Request

from models import CostFormula
from services.errors import DomainError, raise_http


def require_api_principal(request: Request):
    """Trả về danh tính đã xác thực, hoặc bật 401.

    auth_middleware đã chặn mặc định ở tầng ứng dụng, nhưng các handler vẫn cần
    lấy danh tính để ghi nhật ký kiểm toán (`created_by`, `updated_by`), nên hàm
    này vừa là lớp kiểm tra vừa là nơi đọc ra danh tính đó.
    """
    principal = getattr(request.state, "principal", None)
    if isinstance(principal, str) and principal.strip():
        return principal.strip()
    if isinstance(principal, dict):
        value = principal.get("id") or principal.get("sub") or principal.get("username")
        if value:
            return str(value)
    raise_http(DomainError("AUTHENTICATION_REQUIRED", "Vui lòng đăng nhập.", 401))


def decimal_to_float(value):
    """Đổi Decimal sang float để đưa vào JSON, an toàn với None và giá trị lạ.

    Chỉ dùng ở tầng TRÌNH BÀY. Không bao giờ dùng để tính toán: tầng tài chính
    nghiêm ngặt Decimal và services/tms_money.py chủ động bật lỗi với float.
    """
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def iso_or_none(value):
    """Chuỗi ISO của một mốc thời gian, hoặc None."""
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def safe_permissions(value):
    """Đọc danh sách quyền lưu dạng JSON, trả về [] khi dữ liệu không hợp lệ.

    Dữ liệu hỏng ở cột này không được làm vỡ cả màn hình; thiếu quyền là mặc
    định an toàn.
    """
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        permissions = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return permissions if isinstance(permissions, list) else []


def serialize_cost_formula(row: CostFormula):
    """Bung công thức chi phí từ JSON sang dạng giao diện đọc được."""
    try:
        payload = json.loads(row.formula_expression or "{}")
    except json.JSONDecodeError:
        payload = {}
    components = payload.get("components") if isinstance(payload.get("components"), dict) else {}
    return {
        "id": row.id,
        "name": row.name,
        "configured": True,
        "vehicle_type_id": payload.get("vehicle_type_id") or None,
        "currency": payload.get("currency") or "VND",
        "components": components,
        "tokens": payload.get("tokens") if isinstance(payload.get("tokens"), list) else [],
        "terms": payload.get("terms") if isinstance(payload.get("terms"), list) else [],
        "formula_expression": row.formula_expression,
    }
