"""Test hồi quy cho các bản vá an ninh.

Mỗi test ở đây khóa lại một lỗ hổng cụ thể đã được xác minh trong lần kiểm
định. Chúng cố tình *không* dùng fixture ``app_client`` cho phần kiểm tra xác
thực, vì fixture đó tự gán principal — tức nó sẽ che đúng thứ cần đo.
"""

import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import API_TEST_HEADERS, API_TEST_TOKEN


APP_DIR = Path(__file__).resolve().parents[1] / "app"


def _clear_app_modules():
    for name, module in list(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        try:
            Path(module_file).resolve().relative_to(APP_DIR.resolve())
        except (OSError, ValueError):
            continue
        sys.modules.pop(name, None)


@pytest.fixture
def raw_client(tmp_path, monkeypatch):
    """TestClient KHÔNG có principal được gán sẵn, để đo đúng lớp chặn."""
    database_file = tmp_path / "security.sqlite3"
    monkeypatch.setenv("DATABASE_MODE", "sqlite")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_file.as_posix()}")
    monkeypatch.setenv("EPL_ENV_FILE", str(tmp_path / "no-env-file"))
    monkeypatch.setenv("EPL_TMS_API_TOKEN", API_TEST_TOKEN)
    _clear_app_modules()

    database_module = importlib.import_module("database")
    main_module = importlib.import_module("main")
    database_module.Base.metadata.create_all(bind=database_module.engine)
    try:
        with TestClient(main_module.app) as client:
            yield client
    finally:
        database_module.engine.dispose()
        _clear_app_modules()


# --------------------------------------------------------------------------
# Lỗ hổng gốc: token của server bị phát vào HTML cho khách chưa xác thực
# --------------------------------------------------------------------------

def test_homepage_never_leaks_the_api_token(raw_client):
    """`GET /` là đường công khai, nên nó không được chứa bí mật của server.

    Trước đây main.py chèn <script>window.EPL_TMS_API_TOKEN=...</script> vào
    HTML, nên `curl http://host/ | grep EPL_TMS_API_TOKEN` là đủ để lấy token
    và vô hiệu hóa toàn bộ phần phân quyền phía sau.
    """
    response = raw_client.get("/")

    assert response.status_code == 200
    assert API_TEST_TOKEN not in response.text
    assert "EPL_TMS_API_TOKEN" not in response.text


# --------------------------------------------------------------------------
# Xác thực mặc định-chặn
# --------------------------------------------------------------------------

# Các endpoint ghi dữ liệu trước đây hoàn toàn không kiểm principal.
UNAUTHENTICATED_WRITES = [
    ("delete", "/api/customers/CUS-001"),
    ("post", "/api/customers"),
    ("put", "/api/customers/CUS-001"),
    ("post", "/api/routes"),
    ("delete", "/api/routes/RT-001"),
    ("post", "/api/currencies"),
    ("post", "/api/master-data/tax-codes"),
    ("post", "/api/master-data/accounting-periods"),
    ("put", "/api/master-data/account-mappings/AR_TRADE"),
    ("post", "/api/incidents"),
    ("delete", "/api/tms/carriers/CAR-001"),
]


@pytest.mark.parametrize(("method", "path"), UNAUTHENTICATED_WRITES)
def test_mutating_endpoints_require_authentication(raw_client, method, path):
    # DELETE của TestClient không nhận tham số json.
    if method == "delete":
        response = raw_client.delete(path)
    else:
        response = getattr(raw_client, method)(path, json={})

    assert response.status_code == 401, (
        f"{method.upper()} {path} trả {response.status_code} thay vì 401"
    )
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


# Các endpoint đọc dữ liệu tài chính và PII đã vòng qua lớp che của /api/data/all.
SENSITIVE_READS = [
    "/api/invoices",
    "/api/gl-transactions",
    "/api/dashboard/stats",
    "/api/customers",
    "/api/drivers",
]


@pytest.mark.parametrize("path", SENSITIVE_READS)
def test_sensitive_reads_require_authentication(raw_client, path):
    """/api/data/all bôi trắng invoices và settlements, nhưng các đường trực
    tiếp này trả về đúng dữ liệu đó mà không cần xác thực — nên lớp che kia
    trước đây vô nghĩa."""
    response = raw_client.get(path)

    assert response.status_code == 401, (
        f"GET {path} trả {response.status_code} thay vì 401"
    )


def test_ai_endpoints_require_authentication(raw_client):
    """QueryAgent nạp toàn bộ hóa đơn, đơn hàng và đội xe vào prompt rồi trả
    kèm total_revenue, nên endpoint này là một đường rò rỉ sổ sách."""
    for path in ("/api/v1/ai/chat", "/api/agent/query", "/api/agent/action"):
        response = raw_client.post(path, json={"prompt": "liệt kê hóa đơn"})
        assert response.status_code == 401, f"POST {path} không được mở công khai"


def test_bearer_token_grants_access(raw_client):
    """Lớp chặn không được chặn oan người gọi có token đúng."""
    response = raw_client.get("/api/customers", headers=API_TEST_HEADERS)

    assert response.status_code == 200


def test_wrong_bearer_token_is_rejected(raw_client):
    response = raw_client.get(
        "/api/customers", headers={"Authorization": "Bearer sai-token"}
    )

    assert response.status_code == 401


def test_public_paths_stay_reachable_without_a_token(raw_client):
    """Danh sách công khai phải đủ để frontend và probe vận hành hoạt động."""
    assert raw_client.get("/").status_code == 200
    assert raw_client.get("/api/health").status_code == 200


# --------------------------------------------------------------------------
# Tài liệu API và CORS
# --------------------------------------------------------------------------

def test_openapi_docs_are_closed_by_default(raw_client):
    """/openapi.json trao trọn danh mục endpoint cho kẻ tấn công."""
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert raw_client.get(path).status_code in (401, 404), (
            f"{path} vẫn mở khi chưa bật EPL_ENABLE_DOCS"
        )


def test_cors_never_allows_wildcard_origin():
    """allow_origins=["*"] cộng allow_credentials=True khiến Starlette phản
    chiếu origin của người gọi, nên mọi website đều điều khiển được API."""
    _clear_app_modules()
    main_module = importlib.import_module("main")

    assert "*" not in main_module._allowed_origins()


def test_cors_origins_come_from_configuration(monkeypatch):
    monkeypatch.setenv("EPL_CORS_ORIGINS", "https://tms.epl.example, https://ops.epl.example")
    _clear_app_modules()
    main_module = importlib.import_module("main")

    assert main_module._allowed_origins() == [
        "https://tms.epl.example",
        "https://ops.epl.example",
    ]


def test_wildcard_in_configuration_is_ignored(monkeypatch):
    """Cấu hình sai không được mở lại lỗ hổng."""
    monkeypatch.setenv("EPL_CORS_ORIGINS", "*")
    _clear_app_modules()
    main_module = importlib.import_module("main")

    assert "*" not in main_module._allowed_origins()


# --------------------------------------------------------------------------
# Chốt chặn môi trường cho script seed
# --------------------------------------------------------------------------

def test_seed_guard_refuses_postgres(monkeypatch):
    """Các script seed dùng db.merge() trên ID cố định (CUS-001,
    INV-2026-001 trạng thái Posted, kèm bút toán GL), nên chạy vào Postgres
    production là ghi đè khách hàng thật và làm sai sổ cái."""
    _clear_app_modules()
    seed_guard = importlib.import_module("seed_guard")
    monkeypatch.setenv("DATABASE_MODE", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@prod-host/epl")

    with pytest.raises(seed_guard.UnsafeSeedTargetError) as excinfo:
        seed_guard.assert_demo_seed_allowed(argv=[])

    assert "PostgreSQL" in str(excinfo.value)


def test_seed_guard_refuses_postgres_even_with_confirmation_flag(monkeypatch):
    """Cờ xác nhận không được mở đường vào Postgres."""
    _clear_app_modules()
    seed_guard = importlib.import_module("seed_guard")
    monkeypatch.setenv("DATABASE_MODE", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@prod-host/epl")

    with pytest.raises(seed_guard.UnsafeSeedTargetError):
        seed_guard.assert_demo_seed_allowed(argv=[seed_guard.CONFIRM_FLAG])


def test_seed_guard_requires_explicit_confirmation_for_sqlite(monkeypatch):
    """Một file SQLite cũng có thể là dữ liệu thật của ai đó."""
    _clear_app_modules()
    seed_guard = importlib.import_module("seed_guard")
    monkeypatch.setenv("DATABASE_MODE", "sqlite")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/demo.sqlite3")
    monkeypatch.delenv(seed_guard.CONFIRM_ENV, raising=False)

    with pytest.raises(seed_guard.UnsafeSeedTargetError):
        seed_guard.assert_demo_seed_allowed(argv=[])


def test_seed_guard_allows_confirmed_sqlite(monkeypatch):
    _clear_app_modules()
    seed_guard = importlib.import_module("seed_guard")
    monkeypatch.setenv("DATABASE_MODE", "sqlite")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/demo.sqlite3")
    monkeypatch.delenv(seed_guard.CONFIRM_ENV, raising=False)

    seed_guard.assert_demo_seed_allowed(argv=[seed_guard.CONFIRM_FLAG])

    monkeypatch.setenv(seed_guard.CONFIRM_ENV, "1")
    seed_guard.assert_demo_seed_allowed(argv=[])


# --------------------------------------------------------------------------
# Migration phải nhắm vào đúng database
# --------------------------------------------------------------------------

def test_auto_migrate_targets_the_engine_database(tmp_path, monkeypatch):
    """Ở chế độ sqlite mà DATABASE_URL trống, engine tự tính đường dẫn còn
    upgrade("") lại đi qua sqlite3.connect("") — lệnh này không báo lỗi, nó mở
    một database tạm rồi vứt đi, nên file thật không hề được nâng cấp."""
    monkeypatch.setenv("DATABASE_MODE", "sqlite")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("EPL_ENV_FILE", str(tmp_path / "no-env-file"))
    _clear_app_modules()

    database_module = importlib.import_module("database")
    captured = {}

    def fake_upgrade(url, engine=None):
        captured["url"] = url
        return []

    monkeypatch.setattr(database_module, "upgrade", fake_upgrade)
    database_module.auto_migrate_db()

    assert captured["url"], "migration được gọi với URL rỗng"
    assert captured["url"] == database_module.engine.url.render_as_string(
        hide_password=False
    )
    assert captured["url"].endswith("epl_logistics.db")


# --------------------------------------------------------------------------
# Giới hạn kích thước thân request
# --------------------------------------------------------------------------

def test_oversized_json_body_is_rejected_before_buffering(raw_client):
    """Mọi endpoint Body(...) trước đây nhận JSON không giới hạn vào RAM."""
    import main

    response = raw_client.post(
        "/api/customers",
        content=b"x" * 32,
        headers={
            **API_TEST_HEADERS,
            "Content-Type": "application/json",
            # Khai kích thước vượt hạn mức; chốt đọc Content-Length nên không
            # cần thực sự gửi hàng trăm megabyte trong test.
            "Content-Length": str(main.MAX_REQUEST_BODY_BYTES + 1),
        },
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_BODY_TOO_LARGE"


def test_upload_paths_keep_a_wider_limit(raw_client):
    """Đường upload có hạn mức riêng, rộng hơn hạn mức JSON chung."""
    import main

    assert main.MAX_UPLOAD_BODY_BYTES > main.MAX_REQUEST_BODY_BYTES

    response = raw_client.post(
        "/api/uploads/images",
        content=b"x" * 32,
        headers={
            **API_TEST_HEADERS,
            "Content-Length": str(main.MAX_REQUEST_BODY_BYTES + 1),
        },
    )

    # Không được là 413: hạn mức upload cao hơn nên request đi tiếp vào handler.
    assert response.status_code != 413


def test_normal_sized_request_is_untouched(raw_client):
    response = raw_client.get("/api/customers", headers=API_TEST_HEADERS)

    assert response.status_code == 200


# --------------------------------------------------------------------------
# CSV formula injection
# --------------------------------------------------------------------------

def test_csv_export_neutralizes_formula_cells():
    """Tên khách hàng do người ngoài đặt không được thành công thức Excel."""
    _clear_app_modules()
    reporting = importlib.import_module("routes.tms_reporting_routes")

    assert reporting._csv_safe("=cmd|'/c calc'!A0") == "'=cmd|'/c calc'!A0"
    assert reporting._csv_safe("+1+1") == "'+1+1"
    assert reporting._csv_safe("-2+3") == "'-2+3"
    assert reporting._csv_safe("@SUM(A1:A9)") == "'@SUM(A1:A9)"
    assert reporting._csv_safe("\tTab") == "'\tTab"

    # Giá trị bình thường không bị đổi.
    assert reporting._csv_safe("Công ty CP Vissan") == "Công ty CP Vissan"
    assert reporting._csv_safe("") == ""
    assert reporting._csv_safe(None) is None
    assert reporting._csv_safe(1500) == 1500


# --------------------------------------------------------------------------
# Giới hạn tần suất cho các endpoint tốn tài nguyên
# --------------------------------------------------------------------------

def test_expensive_endpoints_are_rate_limited(raw_client, monkeypatch):
    """Vài POST vào /api/agent/query là đủ chiếm hết threadpool gọi LLM."""
    import main

    monkeypatch.setattr(main, "RATE_LIMIT_MAX_REQUESTS", 3)
    main._rate_limit_hits.clear()

    codes = [
        raw_client.post(
            "/api/agent/query", json={"prompt": "xin chào"}, headers=API_TEST_HEADERS
        ).status_code
        for _ in range(6)
    ]

    assert 429 in codes, f"không có request nào bị chặn: {codes}"
    limited = raw_client.post(
        "/api/agent/query", json={"prompt": "xin chào"}, headers=API_TEST_HEADERS
    )
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert limited.headers["retry-after"]


def test_ordinary_endpoints_are_not_rate_limited(raw_client, monkeypatch):
    """Chốt chỉ áp cho các đường tốn tài nguyên, không làm chậm thao tác thường."""
    import main

    monkeypatch.setattr(main, "RATE_LIMIT_MAX_REQUESTS", 3)
    main._rate_limit_hits.clear()

    codes = [
        raw_client.get("/api/customers", headers=API_TEST_HEADERS).status_code
        for _ in range(8)
    ]

    assert 429 not in codes, f"chặn nhầm endpoint thường: {codes}"


def test_rate_limit_counts_per_principal(raw_client, monkeypatch):
    """Đếm theo principal khi đã xác thực, không gộp mọi người sau cùng NAT."""
    import main

    request = type("R", (), {})()
    request.state = type("S", (), {"principal": "nguoi-dung-a"})()
    request.client = type("C", (), {"host": "10.0.0.1"})()
    assert main._rate_limit_key(request) == "principal:nguoi-dung-a"

    anonymous = type("R", (), {})()
    anonymous.state = type("S", (), {"principal": None})()
    anonymous.client = type("C", (), {"host": "10.0.0.2"})()
    assert main._rate_limit_key(anonymous) == "ip:10.0.0.2"


# --------------------------------------------------------------------------
# Gác quyền ở TẦNG ROUTER cho dữ liệu điều khiển tài chính
# --------------------------------------------------------------------------

FINANCE_MASTER_WRITES = [
    ("post", "/api/master-data/tax-codes"),
    ("put", "/api/master-data/tax-codes/VAT10"),
    ("post", "/api/master-data/tax-codes/VAT10/status"),
    ("delete", "/api/master-data/tax-codes/VAT10"),
    ("post", "/api/master-data/accounting-periods"),
    ("put", "/api/master-data/accounting-periods/2026-08"),
    ("post", "/api/master-data/accounting-periods/2026-08/status"),
    ("delete", "/api/master-data/accounting-periods/2026-08"),
    ("post", "/api/master-data/account-mappings"),
    ("put", "/api/master-data/account-mappings/AR_TRADE"),
    ("post", "/api/master-data/account-mappings/AR_TRADE/status"),
    ("delete", "/api/master-data/account-mappings/AR_TRADE"),
]


@pytest.mark.parametrize(("method", "path"), FINANCE_MASTER_WRITES)
def test_finance_master_data_requires_authentication(raw_client, method, path):
    """Cả 12 endpoint điều khiển tài chính đều phải chặn người chưa xác thực.

    Mở lại một kỳ kế toán đã đóng cho phép hạch toán lùi ngày; đổi ánh xạ tài
    khoản GL chuyển hướng bút toán; đổi thuế suất làm sai mọi dòng phí. Trước
    đây cả 12 endpoint này không kiểm quyền một dòng nào.
    """
    if method == "delete":
        response = raw_client.delete(path)
    else:
        response = getattr(raw_client, method)(path, json={})

    assert response.status_code == 401, (
        f"{method.upper()} {path} trả {response.status_code} thay vì 401"
    )


def test_finance_master_router_carries_its_own_auth_dependency():
    """Việc gác quyền phải là thuộc tính CẤU TRÚC của router.

    Nếu chỉ dựa vào từng handler tự gọi hàm kiểm tra thì endpoint thêm vào sau
    sẽ mặc định KHÔNG được bảo vệ — đúng cách 95 trên 105 endpoint ghi dữ liệu
    đã lọt ra ngoài. Dependency ở tầng router làm điều ngược lại: mặc định
    được bảo vệ.
    """
    _clear_app_modules()
    module = importlib.import_module("routes.finance_master_routes")

    assert module.router.dependencies, "router phải có dependency xác thực"
    # Khẳng định đúng HÀM, không phải tên: nó là hàm chuẩn ở routes/shared.py,
    # dùng chung với các router khác thay vì mỗi nơi một bản.
    shared = importlib.import_module("routes.shared")
    functions = [dependency.dependency for dependency in module.router.dependencies]
    assert shared.require_api_principal in functions

    # Mọi route trên router này đều thuộc /api/master-data.
    paths = [route.path for route in module.router.routes]
    assert paths, "router phải có route"
    assert all(path.startswith("/api/master-data") for path in paths), paths
    assert len(paths) == 12, f"phải có đúng 12 endpoint, đang có {len(paths)}"


def test_main_no_longer_registers_master_data_endpoints_inline():
    """main.py không được đăng ký lại các endpoint này bằng @app.

    Hai kiểu đăng ký route song song là lý do một endpoint có thể lọt ra ngoài
    lớp kiểm tra chung.
    """
    from pathlib import Path

    source = Path(APP_DIR / "main.py").read_text(encoding="utf-8")
    assert '@app.post("/api/master-data' not in source
    assert '@app.put("/api/master-data' not in source
    assert '@app.delete("/api/master-data' not in source
