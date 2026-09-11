# -*- coding: utf-8 -*-
"""`GET /api/fleet/resource-summary` — số đếm nguồn lực cho màn chủ.

VÌ SAO CÓ SỐ NÀY. Hai cửa chặn điều phối là `VEHICLE_LEGAL_EXPIRED` và
`DRIVER_LICENSE_INVALID`. Trước đây người điều độ chỉ gặp chúng ĐÚNG LÚC xếp xe — tức là
lúc đã có đơn cần chạy và không còn thời gian đi gia hạn đăng kiểm. Màn chủ đếm sớm để họ
biết trước vài tuần.

ĐIỀU QUAN TRỌNG NHẤT BÀI NÀY KHOÁ: **phép đếm phải trùng phép gác.** Một con số đếm theo
luật riêng thì tệ hơn không có số, vì người vận hành tin vào nó rồi mới ăn 409. Nên bài
kiểm không chỉ so số mong đợi, nó còn gọi thẳng `_require_legal_vehicle` cho từng chiếc và
đòi hai bên kết luận giống nhau.

Hai bẫy cụ thể đã cài:

* **Thiếu ngày cũng là chặn.** Cửa gác coi `None` là hết hạn. Một bản đếm "hồn nhiên" sẽ bỏ
  qua xe chưa khai ngày rồi báo đội xe sạch sẽ.
* **Bằng lái lệch hạng cũng là chặn.** Cửa gác đòi `qualification.license_type` KHỚP hạng
  ghi trên hồ sơ tài xế. Bằng hạng C còn hạn mà hồ sơ khai FC thì vẫn không điều được.
"""
import datetime as dt
import importlib

import pytest

from conftest import API_TEST_HEADERS

HOM_NAY = dt.date.today()


def _ngay(cach):
    return (HOM_NAY + dt.timedelta(days=cach)).isoformat()


def _xe(db, models, ma, dang_kiem, bao_hiem, bao_duong, trang_thai="available"):
    db.add(models.Vehicle(id=ma, type="Xe tải 10 tấn", weight_capacity=10000,
                          operational_status=trang_thai, inspection_exp=dang_kiem,
                          insurance_date=bao_hiem, maintenance_date=bao_duong))


def _tai_xe(db, models, ma, hang="FC", trang_thai="available"):
    db.add(models.Driver(id=ma, name="TX " + ma, license_type=hang, operational_status=trang_thai))


def _bang(db, models, ma_tx, hang, tu, den, trang_thai="active"):
    db.add(models.DriverQualification(
        driver_id=ma_tx, license_type=hang,
        valid_from=dt.datetime.combine(dt.date.fromisoformat(tu), dt.time()),
        valid_to=dt.datetime.combine(dt.date.fromisoformat(den), dt.time()),
        status=trang_thai))


@pytest.fixture
def doi_xe(app_client):
    """Một đội xe nhỏ nhưng phủ đủ các trường hợp cửa gác quan tâm."""
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        # Sạch: cả ba mốc còn xa.
        _xe(db, models, "XE-SACH-1", _ngay(400), _ngay(400), _ngay(400))
        _xe(db, models, "XE-SACH-2", _ngay(90), _ngay(120), _ngay(60))
        # Sắp hết: bảo dưỡng còn 20 ngày — chưa chặn, nhưng phải nhắc.
        _xe(db, models, "XE-SAP", _ngay(400), _ngay(400), _ngay(20))
        # Đã hết hạn đăng kiểm.
        _xe(db, models, "XE-HET", _ngay(-3), _ngay(400), _ngay(400))
        # CHƯA KHAI bảo hiểm — cửa gác chặn, nên phải đếm là hết hạn chứ không bỏ qua.
        _xe(db, models, "XE-THIEU", _ngay(400), None, _ngay(400))
        # Đã đưa ra khỏi đội: không tính vào rảnh cũng không tính vào đang chạy.
        _xe(db, models, "XE-NGUNG", _ngay(400), _ngay(400), _ngay(400), trang_thai="out_of_service")

        _tai_xe(db, models, "TX-SACH", "FC")
        _bang(db, models, "TX-SACH", "FC", _ngay(-400), _ngay(400))
        _tai_xe(db, models, "TX-SAP", "FC")
        _bang(db, models, "TX-SAP", "FC", _ngay(-400), _ngay(15))
        _tai_xe(db, models, "TX-HET", "FC")
        _bang(db, models, "TX-HET", "FC", _ngay(-400), _ngay(-1))
        _tai_xe(db, models, "TX-KHONG-BANG", "FC")                       # không có dòng bằng nào
        _tai_xe(db, models, "TX-LECH-HANG", "FC")
        _bang(db, models, "TX-LECH-HANG", "C", _ngay(-400), _ngay(400))  # còn hạn nhưng lệch hạng
        _tai_xe(db, models, "TX-NGHI", "FC", trang_thai="off_duty")
        _bang(db, models, "TX-NGHI", "FC", _ngay(-400), _ngay(400))
        db.commit()
    return client


def test_dem_giay_to_xe_trung_voi_cua_gac_ke_ca_khi_thieu_ngay(doi_xe):
    r = doi_xe.get("/api/fleet/resource-summary", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    xe = d["vehicles"]

    assert xe["tong"] == 6
    # XE-HET (quá hạn) và XE-THIEU (chưa khai) — cả hai đều là chặn.
    assert xe["giay_to_het_han"] == 2
    # XE-SAP: còn 20 ngày, trong ngưỡng 30 nên nhắc, nhưng KHÔNG được đếm là hết hạn.
    assert xe["giay_to_sap_het"] == 1
    assert d["warn_within_days"] == 30
    sap = {x["id"]: x for x in d["vehicles_expiring_soon"]}
    assert list(sap) == ["XE-SAP"] and sap["XE-SAP"]["con_ngay"] == 20

    # Trạng thái vận hành: chưa điều chuyến nào nên 5 xe rảnh, 1 xe đã ra khỏi đội.
    assert xe["ngung_chay"] == 1 and xe["dang_chay"] == 0 and xe["bao_duong"] == 0
    assert xe["ranh"] == 5


def test_phep_dem_va_phep_gac_ket_luan_GIONG_NHAU_tung_chiec(doi_xe):
    """Đối chiếu trực tiếp với cửa gác — đây là điều làm con số này đáng tin.

    Nếu sau này ai nới luật ở một bên (bỏ mốc bảo hiểm khỏi cửa gác, hay cho phép thiếu
    ngày ở bản đếm) thì bài này đỏ, chứ không để màn chủ âm thầm nói dối.
    """
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    dispatch = importlib.import_module("services.tms_dispatch_service")
    from services.tom_luoc_nguon_luc import SAP_HET_NGAY, _ngay as doc_ngay

    with database.SessionLocal() as db:
        bi_chan, dem_chan = [], []
        for xe in db.query(models.Vehicle):
            try:
                dispatch._require_legal_vehicle(xe, HOM_NAY)
            except Exception:
                bi_chan.append(xe.id)
            moc = [doc_ngay(xe.inspection_exp), doc_ngay(xe.insurance_date),
                   doc_ngay(xe.maintenance_date)]
            if any(x is None or x < HOM_NAY for x in moc):
                dem_chan.append(xe.id)
        assert sorted(bi_chan) == sorted(dem_chan) == ["XE-HET", "XE-THIEU"]
        assert SAP_HET_NGAY == 30


def test_dem_bang_lai_chan_ca_khi_thieu_bang_va_khi_lech_hang(doi_xe):
    d = doi_xe.get("/api/fleet/resource-summary", headers=API_TEST_HEADERS).json()["data"]
    tx = d["drivers"]

    assert tx["tong"] == 6
    # TX-HET (hết hạn), TX-KHONG-BANG (chưa khai), TX-LECH-HANG (còn hạn nhưng sai hạng).
    assert tx["bang_het_han"] == 3
    assert tx["bang_sap_het"] == 1
    sap = d["drivers_expiring_soon"]
    assert [x["id"] for x in sap] == ["TX-SAP"] and sap[0]["con_ngay"] == 15
    assert sap[0]["name"] == "TX TX-SAP"

    assert tx["nghi"] == 1 and tx["dang_chay"] == 0 and tx["ranh"] == 5


def test_xe_va_to_lai_dang_giu_boi_chuyen_chua_xong_thi_khong_con_ranh(doi_xe):
    """Xe về trễ KHÔNG làm xe thành rảnh — cùng luật `phan_cong_dang_giu` của `lich_xe`.

    Khung giờ phân công ở đây đã TRÔI QUA (hôm qua) mà chuyến vẫn `in_transit`. Một bản đếm
    chỉ nhìn giờ sẽ trả lời "rảnh" cho chiếc đang trên đường — đúng lỗi đã đo trên dữ liệu
    thật: 6 chuyến còn chạy nhưng 6 xe đều hiện rảnh.
    """
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    hom_qua = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
    with database.SessionLocal() as db:
        for ma in ("LOC-NL-A", "LOC-NL-B"):
            if db.get(models.Location, ma) is None:
                db.add(models.Location(id=ma, name=ma))
        db.flush()
        db.add(models.FreightOrder(
            id="FO-NL-1", pickup_location_id="LOC-NL-A", delivery_location_id="LOC-NL-B",
            pickup_window_start=hom_qua, pickup_window_end=hom_qua + dt.timedelta(hours=2),
            delivery_window_start=hom_qua + dt.timedelta(hours=3),
            delivery_window_end=hom_qua + dt.timedelta(hours=8),
            max_weight_kg=10000, max_volume_m3=30, max_pallet_count=10, status="dispatched"))
        db.flush()
        db.add(models.TransportTrip(id="TRIP-NL-1", freight_order_id="FO-NL-1", status="in_transit"))
        db.flush()
        db.add(models.ResourceAssignment(
            freight_order_id="FO-NL-1", trip_id="TRIP-NL-1", vehicle_id="XE-SACH-1", driver_id="TX-SACH",
            status="active", assignment_start=hom_qua,
            assignment_end=hom_qua + dt.timedelta(hours=6)))
        db.commit()

    d = doi_xe.get("/api/fleet/resource-summary", headers=API_TEST_HEADERS).json()["data"]
    assert d["vehicles"]["dang_chay"] == 1 and d["vehicles"]["ranh"] == 4
    assert d["drivers"]["dang_chay"] == 1 and d["drivers"]["ranh"] == 4
