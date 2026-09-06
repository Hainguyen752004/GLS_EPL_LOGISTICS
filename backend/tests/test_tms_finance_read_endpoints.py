"""Ba endpoint DOC cua tai chinh van tai chua co dau vet nao trong bo test.

    GET /api/tms/finance/costs
    GET /api/tms/finance/costs/{cost_id}
    GET /api/tms/finance/dashboard

Ca ba deu doi quyen `finance_read`. Duong GHI cua nhom tai chinh
(create_ap / submit / approve / post / payments) da duoc phu rat ky trong
test_tms_freight_finance.py, nhung ba duong DOC nay thi khong — va chinh
chung nuoi man Finance Cockpit tren giao dien.

Vi sao dang nay dang duoc kiem: mot endpoint doc thieu kiem quyen se lam ro
so lieu tai chinh cho bat ky ai goi duoc API, va no khong he lam vo mot bai
kiem nao khac. `GET /costs` con gioi han 100 ban ghi — con so do dinh vao
man hinh nen phai duoc ghi lai o dau do.
"""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from database import Base

# `tests` khong phai package, nen import theo ten module tran — dung cach ma
# conftest.py da dat sys.path.
from test_tms_freight_finance import _approved_cost_for_ap


@pytest.fixture
def db_session(tmp_path):
    """Ban sao cua fixture cung ten trong test_tms_freight_finance.py.

    Fixture do la CUC BO trong tep kia (khong nam trong conftest.py), nen
    import ham `_approved_cost_for_ap` khong keo fixture theo. Cho nay giu
    nguyen hai chi tiet quan trong cua ban goc: bat `PRAGMA foreign_keys=ON`
    (mac dinh cua SQLite la TAT, nen thieu dong nay thi moi rang buoc khoa
    ngoai trong luoc do deu khong duoc kiem), va nap `models` truoc khi
    create_all de moi bang duoc dang ky.
    """
    import models  # noqa: F401

    engine = create_engine("sqlite:///" + str(tmp_path / "finance_read.db"))

    @event.listens_for(engine, "connect")
    def _bat_khoa_ngoai(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _khach_va_quyen(db_session):
    """Dung hai vai: mot co finance_read, mot khong co gi."""
    from models import Role, User

    if db_session.get(Role, "FIN_READ") is None:
        db_session.add(Role(id="FIN_READ", permissions='["finance_read"]'))
    if db_session.get(Role, "FIN_NONE") is None:
        db_session.add(Role(id="FIN_NONE", permissions="[]"))
    if db_session.get(User, "nguoi-doc") is None:
        db_session.add(User(id="nguoi-doc", username="nguoi-doc", role_id="FIN_READ"))
    if db_session.get(User, "nguoi-la") is None:
        db_session.add(User(id="nguoi-la", username="nguoi-la", role_id="FIN_NONE"))
    db_session.commit()


def _client(db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import database
    from routes.tms_finance_routes import router

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[database.get_db] = lambda: db_session

    @app.middleware("http")
    async def principal(request, call_next):
        if request.headers.get("X-Test-Principal"):
            request.state.principal = request.headers["X-Test-Principal"]
        return await call_next(request)

    return TestClient(app)


DOC = {"X-Test-Principal": "nguoi-doc"}
LA = {"X-Test-Principal": "nguoi-la"}


def test_khong_co_principal_thi_401_va_thieu_quyen_thi_403(db_session):
    """Fail-closed. Mot endpoint DOC lot kiem quyen la ro so lieu tai chinh
    cho bat ky ai goi duoc API, ma khong lam vo bai kiem nao khac."""
    _khach_va_quyen(db_session)
    client = _client(db_session)

    for duong in ("/api/tms/finance/costs",
                  "/api/tms/finance/costs/COST-KHONG-CO",
                  "/api/tms/finance/dashboard"):
        assert client.get(duong).status_code == 401, duong
        assert client.get(duong, headers=LA).status_code == 403, duong


def test_liet_ke_chi_phi_tra_ve_ho_so_that(db_session):
    _khach_va_quyen(db_session)
    cost = _approved_cost_for_ap(db_session, "READ1")
    db_session.commit()
    client = _client(db_session)

    r = client.get("/api/tms/finance/costs", headers=DOC)
    assert r.status_code == 200, r.text
    than = r.json()
    assert "message" in than and isinstance(than["data"], list), than
    ma = [c["id"] for c in than["data"]]
    assert cost.id in ma, ma


def test_lay_mot_ho_so_chi_phi_va_404_khi_khong_co(db_session):
    _khach_va_quyen(db_session)
    cost = _approved_cost_for_ap(db_session, "READ2")
    db_session.commit()
    client = _client(db_session)

    r = client.get("/api/tms/finance/costs/" + cost.id, headers=DOC)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["id"] == cost.id
    assert data["trip_id"] == cost.trip_id
    # `total_amount` duoc tinh bu tu cac dong charge item khi cot tong con
    # trong, nen phai ra so > 0 chu khong phai None.
    assert data["total_amount"] is not None and Decimal(str(data["total_amount"])) > 0, data

    assert client.get("/api/tms/finance/costs/COST-KHONG-CO",
                      headers=DOC).status_code == 404


def test_liet_ke_chi_phi_gioi_han_100_ban_ghi(db_session):
    """`GET /costs` co `.limit(100)` cung trong ma. Con so do dinh thang vao
    man Finance Cockpit — o hang nghin chuyen thi man hinh chi thay 100 ho so
    moi nhat, va no KHONG noi ra dieu do. Ghi lai day de lan sau doi thi
    phai doi ca cho hien thi."""
    import inspect

    import routes.tms_finance_routes as mod

    nguon = inspect.getsource(mod.list_costs)
    assert ".limit(100)" in nguon, nguon
    assert "created_at.desc()" in nguon, nguon


def test_dashboard_tai_chinh_tra_ve_dung_phong_bi(db_session):
    _khach_va_quyen(db_session)
    _approved_cost_for_ap(db_session, "READ3")
    db_session.commit()
    client = _client(db_session)

    r = client.get("/api/tms/finance/dashboard", headers=DOC)
    assert r.status_code == 200, r.text
    than = r.json()
    assert "message" in than and "data" in than, than
    # Dashboard phai la mot doi tuong tong hop, khong phai mang tho.
    assert isinstance(than["data"], dict), than["data"]
