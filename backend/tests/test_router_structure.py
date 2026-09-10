"""main.py không được ôm endpoint nghiệp vụ inline.

main.py từng có 63 endpoint đăng ký bằng @app trong khi thư mục routes/ đã tồn
tại — hai kiểu đăng ký route song song. Đó chính là cách một endpoint lọt ra
ngoài lớp kiểm tra chung: 95 trên 105 endpoint ghi dữ liệu từng không kiểm quyền.

File này khóa lại cấu trúc sau khi tách, để việc đó không lặng lẽ quay lại.
"""

import importlib
import re
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"

# Chỉ những đường thuộc VỎ ỨNG DỤNG được phép ở lại main.py: chúng phục vụ
# HTML và tài nguyên tĩnh, không phải nghiệp vụ.
ALLOWED_INLINE_PATHS = {
    "/",
    "/favicon.ico",
    "/tongquan.jpg",
    "/test-runner",
    "/kich-ban-test",
}

BUSINESS_ROUTERS = [
    "routes.finance_master_routes",
    "routes.currency_routes",
    "routes.master_data_routes",
    "routes.fleet_routes",
    "routes.delivery_routes",

    "routes.operations_routes",
    "routes.data_export_routes",
    "routes.ai_upload_routes",
]

# Router phải gác quyền ở TẦNG ROUTER. ai_upload là ngoại lệ có chủ ý: xem lý do
# trong docstring của test tương ứng bên dưới.
ROUTERS_REQUIRING_AUTH = [name for name in BUSINESS_ROUTERS if name != "routes.ai_upload_routes"]

def _main_source():
    return (APP_DIR / "main.py").read_text(encoding="utf-8")

def test_main_only_keeps_application_shell_endpoints():
    paths = set(re.findall(r'@app\.(?:get|post|put|patch|delete)\("([^"]+)"', _main_source()))

    unexpected = sorted(paths - ALLOWED_INLINE_PATHS)
    assert not unexpected, (
        "endpoint nghiệp vụ phải nằm trên router, không đăng ký inline trong "
        f"main.py: {unexpected}"
    )

def test_main_no_longer_declares_any_api_endpoint_inline():
    """Không một đường /api/ nào được đăng ký bằng @app."""
    api_paths = sorted(
        path
        for path in re.findall(r'@app\.(?:get|post|put|patch|delete)\("([^"]+)"', _main_source())
        if path.startswith("/api/")
    )
    assert api_paths == []

def test_main_stays_small():
    """main.py là nơi dựng ứng dụng, không phải nơi chứa nghiệp vụ.

    Ngưỡng này cố tình rộng; nó chỉ để chặn việc quay lại thói cũ, chứ không
    nhằm bắt lỗi từng dòng.
    """
    line_count = len(_main_source().splitlines())
    assert line_count < 700, (
        f"main.py đang có {line_count} dòng — nghiệp vụ có lẽ đã bị thêm lại vào đây"
    )

@pytest.mark.parametrize("module_name", ROUTERS_REQUIRING_AUTH)
def test_business_routers_guard_at_router_level(module_name):
    """Gác quyền phải là thuộc tính CẤU TRÚC, không phải thói quen của người viết.

    Dependency ở tầng router làm endpoint thêm vào sau được bảo vệ MẶC ĐỊNH.
    Nếu chỉ dựa vào từng handler tự gọi hàm kiểm tra thì mặc định là KHÔNG
    được bảo vệ — đúng cách 95 trên 105 endpoint đã lọt ra ngoài.
    """
    shared = importlib.import_module("routes.shared")
    module = importlib.import_module(module_name)

    assert module.router.dependencies, f"{module_name} thiếu dependency xác thực"
    functions = [dependency.dependency for dependency in module.router.dependencies]
    assert shared.require_api_principal in functions, (
        f"{module_name} phải dùng require_api_principal ở tầng router"
    )

def test_upload_router_is_deliberately_unguarded():
    """ai_upload_routes KHÔNG gác ở tầng router, và đó là chủ ý.

    GET /uploads/{asset_path} phải công khai: giao diện hiển thị ảnh xe và tài
    xế bằng <img src="/uploads/...">, mà thẻ <img> không gửi được header
    Authorization — lớp bọc fetch trong frontend/js/api-auth.js không chạm tới
    nó. Gác ở tầng router sẽ làm mọi ảnh thành 401.

    Đường đọc đó tự phòng thủ thay vì dựa vào xác thực, và các endpoint còn lại
    của file vẫn bị auth_middleware chặn ở tầng ứng dụng.
    """
    module = importlib.import_module("routes.ai_upload_routes")
    assert not module.router.dependencies

    source = (APP_DIR / "routes" / "ai_upload_routes.py").read_text(encoding="utf-8")
    assert "img src" in source, "phải ghi rõ lý do không gác, để không ai 'sửa' lại"

def test_uploads_path_is_public_in_the_middleware():
    """Danh sách công khai phải chứa /uploads/, nếu không ảnh biến thành 401."""
    auth = importlib.import_module("auth_middleware")

    assert auth._is_public("/uploads/vehicles/abc.jpg", "GET") is True
    # Nhưng các đường API khác thì không.
    assert auth._is_public("/api/vehicles", "GET") is False
    assert auth._is_public("/api/data/all", "GET") is False

def test_cross_cutting_helpers_live_in_one_place():
    """Năm hàm dùng chéo phải có MỘT nguồn duy nhất.

    Nhân bản mỗi router một bản là con đường dẫn tới đúng chỗ đã sai một lần:
    các bản sao trôi khỏi nhau rồi sinh lỗi khác nhau — như ba hàm escape và
    năm hàm định dạng ngày ở frontend đã từng.
    """
    shared = importlib.import_module("routes.shared")
    for name in (
        "require_api_principal",
        "decimal_to_float",
        "iso_or_none",
        "safe_permissions",
        "serialize_cost_formula",
    ):
        assert callable(getattr(shared, name)), f"routes/shared.py thiếu {name}"

    # main.py không được định nghĩa lại chúng.
    source = _main_source()
    for name in ("_decimal_to_float", "_iso_or_none", "_require_api_principal",
                 "_safe_permissions", "_serialize_cost_formula"):
        assert not re.search(rf"^def {name}\(", source, re.M), (
            f"{name} phải đến từ routes/shared.py, không định nghĩa lại trong main.py"
        )
