import os
import hashlib
import importlib
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_DIR / "app"
REAL_DATABASE = APP_DIR / "epl_logistics.db"

# Establish a safe baseline before pytest imports test modules during collection.
# Individual fixtures may replace this URL with a narrower per-test database.
_ORIGINAL_DATABASE_ENV = {
    name: os.environ.get(name)
    for name in ("DATABASE_MODE", "DATABASE_URL", "EPL_ENV_FILE")
}
_COLLECTION_DATABASE = Path(tempfile.gettempdir()) / (
    f"epl-pytest-collection-{os.getpid()}.sqlite3"
)
os.environ["DATABASE_MODE"] = "sqlite"
os.environ["DATABASE_URL"] = f"sqlite:///{_COLLECTION_DATABASE.as_posix()}"
os.environ["EPL_ENV_FILE"] = str(_COLLECTION_DATABASE.with_suffix(".env.disabled"))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def _database_fingerprint(path):
    if not path.exists():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with sqlite3.connect(path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        counts = {
            name: connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            for (name,) in tables
            if name != "sqlite_sequence"
        }
    return (path.stat().st_mtime_ns, path.stat().st_size, digest, counts)


# Token dùng chung cho các test tự dựng TestClient. Xác thực giờ là
# mặc định-chặn (xem app/auth_middleware.py), nên test nào không đi qua fixture
# app_client phải tự gửi bearer token này.
API_TEST_TOKEN = "pytest-api-token"
API_TEST_HEADERS = {"Authorization": f"Bearer {API_TEST_TOKEN}"}


def seed_open_accounting_period(db, period_id="TEST-OPEN-PERIOD"):
    """Tạo một kỳ kế toán đang mở, bao trùm rộng.

    Hạch toán AR, AP và settlement đều đòi một kỳ kế toán đang mở bao trùm thời
    điểm ghi sổ, nên mọi luồng test đi tới bước lập hóa đơn đều cần gọi hàm này.
    Trước đây riêng đường AR không kiểm, nên client có thể ghi doanh thu lùi vào
    một kỳ đã đóng.
    """
    import datetime as _dt
    import importlib as _importlib

    models = _importlib.import_module("models")
    year = _dt.datetime.now(_dt.timezone.utc).year
    db.merge(models.AccountingPeriod(
        id=period_id,
        starts_at=_dt.datetime(year - 2, 1, 1),
        ends_at=_dt.datetime(year + 2, 12, 31, 23, 59, 59),
        status="open",
    ))
    db.commit()


@pytest.fixture(scope="session", autouse=True)
def configure_api_test_token():
    """Cấp một token API cố định cho cả phiên test."""
    baseline = os.environ.get("EPL_TMS_API_TOKEN")
    os.environ["EPL_TMS_API_TOKEN"] = API_TEST_TOKEN
    yield API_TEST_TOKEN
    if baseline is None:
        os.environ.pop("EPL_TMS_API_TOKEN", None)
    else:
        os.environ["EPL_TMS_API_TOKEN"] = baseline


@pytest.fixture(scope="session", autouse=True)
def isolate_application_database(tmp_path_factory):
    before = _database_fingerprint(REAL_DATABASE)
    test_database = tmp_path_factory.mktemp("database") / "suite.sqlite3"
    os.environ["DATABASE_MODE"] = "sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{test_database.as_posix()}"
    yield test_database
    assert _database_fingerprint(REAL_DATABASE) == before, (
        "Tests changed the real application database"
    )
    for name, value in _ORIGINAL_DATABASE_ENV.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def _remove_app_modules():
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
def app_client(tmp_path):
    from fastapi.testclient import TestClient

    real_before = _database_fingerprint(REAL_DATABASE)
    database_file = tmp_path / "http.sqlite3"
    baseline = {
        name: os.environ.get(name)
        for name in ("DATABASE_MODE", "DATABASE_URL", "EPL_ENV_FILE")
    }
    os.environ["DATABASE_MODE"] = "sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{database_file.as_posix()}"
    os.environ["EPL_ENV_FILE"] = str(tmp_path / "no-env-file")
    _remove_app_modules()

    database_module = importlib.import_module("database")
    main_module = importlib.import_module("main")
    database_module.Base.metadata.create_all(bind=database_module.engine)

    @main_module.app.middleware("http")
    async def inject_test_principal(request, call_next):
        principal = request.headers.get("X-Test-Principal")
        request.state.principal = principal or "test-user"
        return await call_next(request)

    def override_get_db():
        session = database_module.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    main_module.app.dependency_overrides[database_module.get_db] = override_get_db
    try:
        with TestClient(main_module.app) as client:
            yield client, database_file, real_before
    finally:
        main_module.app.dependency_overrides.clear()
        database_module.engine.dispose()
        _remove_app_modules()
        for name, value in baseline.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@pytest.fixture
def workflow_builder(app_client):
    client, _, _ = app_client

    # Bộ dựng này chạy luồng nghiệp vụ tới bước lập hóa đơn, và hạch toán đòi
    # một kỳ kế toán đang mở, nên cấu hình tài chính hợp lệ thuộc về nó.
    import importlib as _importlib
    _database = _importlib.import_module("database")
    with _database.SessionLocal() as _db:
        seed_open_accounting_period(_db)

    class Builder:
        def customer(self, id="CUS-T1"):
            assert client.post("/api/customers", json={"id": id, "name": "Khách Test"}).status_code in (200, 201)
            return id

        def route(self, id="RT-T1"):
            assert client.post("/api/routes", json={"id": id, "name": "Tuyến Test", "distance_km": 10, "segments_json": "[]"}).status_code in (200, 201)
            return id

        def vehicle(self, id="VEH-T1"):
            assert client.post("/api/vehicles", json={"id": id, "type": "Xe tải", "status": "Sẵn sàng"}).status_code in (200, 201)
            return id

        def driver(self, id="DRV-T1"):
            assert client.post("/api/drivers", json={"id": id, "name": "Tài xế Test", "status": "🟢 Rảnh (Sẵn sàng)"}).status_code in (200, 201)
            return id

        def master_data(self):
            self.customer(); self.route(); self.vehicle(); self.driver()
            return self

        def driver_shift(self, start, end, driver_id="DRV-T1", vehicle_id=None, id="SHIFT-T1"):
            payload = {
                "id": id,
                "driver_id": driver_id,
                "shift_type": "custom",
                "availability_kind": "work",
                "shift_start": start,
                "shift_end": end,
                "status": "planned",
            }
            if vehicle_id:
                payload["vehicle_id"] = vehicle_id
            response = client.post("/api/tms/scheduling/driver-shifts", json=payload)
            assert response.status_code == 200, response.text
            return id

        def quotation(self, id="QT-T1", approve=False):
            response = client.post("/api/quotations", json={"id": id, "customer_id": "CUS-T1", "route_id": "RT-T1"}, headers={"X-User-Id": "tester"})
            assert response.status_code == 200
            if approve:
                assert client.put(f"/api/quotations/{id}/approve", headers={"X-User-Id": "tester"}).status_code == 200
            return id

        def sales_order(self, id="SO-T1", quotation_id="QT-T1", confirm=False):
            response = client.post("/api/sales-orders", json={"id": id, "quotation_id": quotation_id}, headers={"X-User-Id": "tester"})
            assert response.status_code == 200
            if confirm:
                assert client.put(f"/api/sales-orders/{id}/confirm", headers={"X-User-Id": "tester"}).status_code == 200
            return id

        def delivery_order(self, id="DO-T1", so_id="SO-T1", approve=False):
            response = client.post("/api/delivery-orders", json={"id": id, "so_id": so_id}, headers={"X-User-Id": "tester"})
            assert response.status_code == 200
            assert response.json()["data"]["canonical_status"] == "pending"
            return id

    return Builder()


@pytest.fixture
def import_database():
    def run(extra_env):
        env = os.environ.copy()
        for name, value in extra_env.items():
            if value is None:
                env.pop(name, None)
            else:
                env[name] = value
        env["PYTHONPATH"] = str(APP_DIR)
        return subprocess.run(
            [sys.executable, "-c", "import database"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    return run
