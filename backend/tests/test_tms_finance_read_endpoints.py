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
def db_session(tmp_path, may_kiem):
    """Ban sao cua fixture cung ten trong test_tms_freight_finance.py.

    Fixture do la CUC BO trong tep kia (khong nam trong conftest.py), nen
    import ham `_approved_cost_for_ap` khong keo fixture theo.

    KHONG CON `PRAGMA foreign_keys=ON`. Ban truoc phai bat tay dong do vi mac
    dinh cua SQLite la TAT khoa ngoai, nen thieu no thi moi rang buoc khoa ngoai
    trong luoc do deu khong duoc kiem. PostgreSQL cuong che khoa ngoai san, va
    `PRAGMA` khong phai cau lenh cua no — de lai la `AttributeError` ngay o buoc
    mo ket noi.

    Van phai nap `models` truoc `create_all` de moi bang duoc dang ky.
    """
    import models  # noqa: F401

    engine = may_kiem()
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


def _submitted_cost(db_session, suffix):
    """Mot ho so chi phi DUNG LAI o `submitted` — tuc dang cho duyet.

    Ban sao rut gon cua `_approved_cost_for_ap`, bo dung buoc `approve_cost`
    cuoi cung. Can mot dong `submitted` that vi day chinh la trang thai ma
    man hinh dem sai: tren PostgreSQL that co ba dong nhu vay ma the "Actual
    Cost cho duyet" van ghi 0.
    """
    import datetime as dt
    from decimal import Decimal

    from sqlalchemy import select

    from models import Carrier, CurrencyDefinition, FinanceControlConfig, TaxCode
    from services.tms_cost_service import create_cost, save_charge_item, submit_cost
    from test_tms_freight_finance import _delivered_order

    order = _delivered_order(db_session, suffix=f"-SUB-{suffix}")
    if db_session.get(CurrencyDefinition, "VND") is None:
        db_session.add(CurrencyDefinition(code="VND", minor_units=0))
    if db_session.get(FinanceControlConfig, "GLOBAL") is None:
        db_session.add(FinanceControlConfig(id="GLOBAL", functional_currency="VND"))
    if db_session.scalar(select(TaxCode).where(TaxCode.code == "VAT10",
                                              TaxCode.effective_from == dt.date(2020, 1, 1))) is None:
        db_session.add(TaxCode(code="VAT10", effective_from=dt.date(2020, 1, 1),
                               rate=Decimal("0.10"), mode="exclusive"))
    db_session.add(Carrier(id=f"CAR-S-{suffix}", name=f"Carrier {suffix}",
                           tax_code=f"TAXS-{suffix}", is_internal=True))
    db_session.flush()
    cost = create_cost(db_session, order.id,
                       {"id": f"COST-SUB-{suffix}", "carrier_id": f"CAR-S-{suffix}", "currency_code": "VND"},
                       "POST", "/costs", f"cost-sub-{suffix}", "maker", {"finance_creator"})
    save_charge_item(db_session, cost.id,
                     {"id": f"ITEM-SUB-{suffix}", "charge_type": "fuel", "quantity": "3",
                      "unit_price": "1000", "tax_code": "VAT10", "tax_mode": "exclusive"},
                     1, "POST", f"/costs/{cost.id}/items", f"item-sub-{suffix}", "maker", {"finance_creator"})
    submit_cost(db_session, cost.id, 2, "POST", f"/costs/{cost.id}/submit",
                f"submit-sub-{suffix}", "maker", {"finance_creator"})
    return cost


def test_dashboard_dem_dung_theo_NHAN_nguoi_dung_doc(db_session):
    """Bon con so phai trung voi NHAN, khong phai voi mot tap trang thai tien tay.

    Vi sao dang nay dang duoc ghim. Man Finance Cockpit truoc day dem bon con
    so nay ngay tai may khach, tren `appState.freight_actual_costs /
    ap_invoices / settlements` — ma `/api/data/all` thi CO TINH boi trang dung
    ba tap do thanh mang rong. Ket qua: ca bon the hien 0 vinh vien. Do duoc
    tren PostgreSQL that: ba ho so chi phi dang `submitted` cho duyet, the van
    ghi 0, va ba viec can duyet bien mat khoi tam mat.

    Gio bon con so den tu `COUNT(*)` cua may chu. Nhung dem toan bang thi con
    mot cai bay thu hai: dem SAI TAP TRANG THAI. Nhan "cho duyet" ma gom ca
    dong da duyet thi con so dung ve ky thuat va sai voi cai nguoi doc hieu.
    """
    from services.tms_ap_service import create_ap_from_cost
    from services.tms_settlement_service import get_finance_dashboard

    _khach_va_quyen(db_session)
    quyen = {"finance_read"}

    # Chua co gi thi phai la 0 that, khong phai None.
    goi = get_finance_dashboard(db_session, {}, "nguoi-doc", quyen)
    assert goi["actual_cost_pending_count"] == 0, goi
    assert float(goi["total_payable"]) == 0.0, goi

    # Mot dong `submitted` = mot viec cho duyet.
    _submitted_cost(db_session, "D1")
    db_session.commit()
    goi = get_finance_dashboard(db_session, {}, "nguoi-doc", quyen)
    assert goi["actual_cost_pending_count"] == 1, goi

    # Mot dong DA DUYET khong con la viec cho duyet — con so phai GIU NGUYEN.
    cost = _approved_cost_for_ap(db_session, "DASH")
    db_session.commit()
    goi = get_finance_dashboard(db_session, {}, "nguoi-doc", quyen)
    assert goi["actual_cost_pending_count"] == 1, \
        "dong da duyet bi dem vao 'cho duyet' — nhan noi sai voi con so"

    # AP moi tao (`draft`) la viec cho hach toan, va la tien con no nha xe.
    ap = create_ap_from_cost(db_session, cost.id,
                             {"vendor_invoice_no": "VN-DASH-1", "invoice_date": "2026-08-10",
                              "due_date": "2026-09-10"},
                             "POST", "/ap-invoices", "ap-dash", "ap-maker", {"finance_creator"})
    db_session.commit()
    goi = get_finance_dashboard(db_session, {}, "nguoi-doc", quyen)
    assert goi["ap_waiting_post_count"] == 1, goi
    assert float(goi["total_payable"]) == float(ap.total_amount), \
        ("tong phai tra phai bang tong hoa don chua tra", goi, ap.total_amount)
    assert goi["settlement_open_count"] == 0, goi


def test_dashboard_noi_ra_gioi_han_100_cua_ba_duong_liet_ke(db_session):
    """Con so tong den tu COUNT(*), con danh sach ben duoi chi co 100 dong.

    Hai con so khac nhau tren cung mot man hinh la chuyen binh thuong — cai
    KHONG binh thuong la khong noi ra. `list_row_cap` de man hinh ghi duoc
    "dem 240, xem duoc 100 moi nhat"; thieu no thi nguoi dung tuong 100 dong
    dang thay la tat ca.
    """
    import inspect

    import routes.tms_finance_routes as mod
    from services.tms_settlement_service import SO_BAN_GHI_LIET_KE_TOI_DA, get_finance_dashboard

    _khach_va_quyen(db_session)
    goi = get_finance_dashboard(db_session, {}, "nguoi-doc", {"finance_read"})
    assert goi["list_row_cap"] == SO_BAN_GHI_LIET_KE_TOI_DA, goi

    # Con so do phai la giới hạn THẬT của ba đường liệt kê, không phải một số
    # ai đó gõ vào. Đổi `.limit()` mà quên hằng số này thì màn hình nói sai.
    for ham in (mod.list_costs, mod.list_ap_invoices, mod.list_settlements):
        nguon = inspect.getsource(ham)
        assert f".limit({SO_BAN_GHI_LIET_KE_TOI_DA})" in nguon, (ham.__name__, nguon)
