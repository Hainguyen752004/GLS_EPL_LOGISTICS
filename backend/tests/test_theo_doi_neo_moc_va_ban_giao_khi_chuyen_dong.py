# -*- coding: utf-8 -*-
"""Hai luật nối màn Theo dõi với bàn giao công nợ.

1. VỊ TRÍ MÔ PHỎNG NEO THEO MỐC CUỐI ĐÃ GHI. Đo trên màn Theo dõi thật (11/09): sáu chuyến
   đang chạy nhưng bản đồ chỉ thấy HAI xe — khung giờ kế hoạch đã qua nên mô phỏng theo giờ
   dồn bốn xe về Cát Lái và hai xe về Cái Mép, chồng lên nhau, trong khi lịch sử nói xe mới
   `check_in` ở kho. Giờ: `check_in`/`pickup` → 0%, `arrival`/`unloading` → 100%,
   `departure` → theo giờ nhưng không quá 97% cho tới khi có ai ghi "đến nơi".

2. CHỈ BÀN GIAO KHI CHUYẾN ĐÃ ĐÓNG. Chủ dự án: *"phải đến điểm cuối và hoàn tất mới quăng qua
   cho anh Khang"*. DO hạ ở điểm đầu của chuyến nhiều điểm giao đã `delivered` nhưng xe còn
   chạy → chưa vào danh sách bàn giao, API chi tiết trả 409 `DO_TRIP_CHUA_DONG`.
"""
import datetime as dt
import importlib
import types

from conftest import API_TEST_HEADERS


# ---------------------------------------------------------------- 1. mô phỏng neo theo mốc
def _chuyen_gia(bat_dau, ket_thuc):
    return types.SimpleNamespace(actual_departure_at=bat_dau, planned_departure_at=bat_dau,
                                 planned_arrival_at=ket_thuc)


def _tuyen_gia():
    return [{"origin": "Kho A", "destination": "Cảng Z", "distance_km": 100,
             "from_lat": 10.0, "from_lng": 106.0, "to_lat": 11.0, "to_lng": 107.0}]


def test_mo_phong_neo_theo_moc_cuoi():
    gps = importlib.import_module("services.gps_simulation")
    bat_dau = dt.datetime(2026, 9, 11, 1, 0)
    ket_thuc = bat_dau + dt.timedelta(hours=2)
    da_qua = ket_thuc + dt.timedelta(hours=3)          # khung giờ đã qua từ lâu
    chuyen = _chuyen_gia(bat_dau, ket_thuc)

    # Chưa có mốc nào: theo giờ → đã "tới" (hành vi cũ, giữ nguyên).
    cu = gps.vi_tri_mo_phong(chuyen, _tuyen_gia(), da_qua)
    assert cu["phan_tram"] == 100.0

    # Mốc cuối là check_in / pickup: xe còn ở kho dù giờ đã qua.
    for moc in ("check_in", "pickup"):
        o_kho = gps.vi_tri_mo_phong(chuyen, _tuyen_gia(), da_qua, moc_cuoi=moc)
        assert o_kho["phan_tram"] == 0.0 and (o_kho["lat"], o_kho["lng"]) == (10.0, 106.0), moc

    # Đã xuất bến nhưng chưa ai ghi "đến nơi": không được tự cho xe tới đích.
    dang_chay = gps.vi_tri_mo_phong(chuyen, _tuyen_gia(), da_qua, moc_cuoi="departure")
    assert dang_chay["phan_tram"] == 97.0 and dang_chay["con_lai_km"] == 3.0

    # Giữa đường theo giờ thì vẫn theo giờ.
    giua = gps.vi_tri_mo_phong(chuyen, _tuyen_gia(), bat_dau + dt.timedelta(hours=1), moc_cuoi="departure")
    assert giua["phan_tram"] == 50.0

    # Đã ghi đến nơi: ghim ở điểm cuối, kể cả khi giờ kế hoạch chưa tới.
    for moc in ("arrival", "unloading"):
        toi = gps.vi_tri_mo_phong(chuyen, _tuyen_gia(), bat_dau + dt.timedelta(minutes=10), moc_cuoi=moc)
        assert toi["phan_tram"] == 100.0 and (toi["lat"], toi["lng"]) == (11.0, 107.0), moc


# ---------------------------------------------------------------- 2. bàn giao khi chuyến đóng
def _do_da_giao_tren_chuyen(db, models, ma, trang_thai_chuyen, tien=2_000_000):
    khach = "CUS-" + ma
    if db.get(models.Customer, khach) is None:
        db.add(models.Customer(id=khach, name=khach))
    for ma_diem in ("LOC-BG-A", "LOC-BG-B"):
        if db.get(models.Location, ma_diem) is None:
            db.add(models.Location(id=ma_diem, name=ma_diem, type="Warehouse"))
    db.flush()
    db.add(models.DeliveryOrder(id=ma, customer_id=khach, canonical_status="delivered", status="Đã giao"))
    db.flush()
    db.add(models.DeliveryOrderCloseout(
        id="CLO-" + ma, do_id=ma, base_selling_price_snapshot=tien, base_price_source="quotation",
        base_price_source_id="QT-" + ma, surcharge_total=0, final_selling_price=tien, currency_code="VND",
        completed_at=dt.datetime(2026, 9, 10, 3, tzinfo=dt.timezone.utc), completed_by="ops"))
    khung = dt.datetime(2026, 9, 10, 1, tzinfo=dt.timezone.utc)
    db.add(models.FreightOrder(
        id="FO-" + ma, pickup_location_id="LOC-BG-A", delivery_location_id="LOC-BG-B",
        pickup_window_start=khung, pickup_window_end=khung + dt.timedelta(hours=2),
        delivery_window_start=khung + dt.timedelta(hours=2), delivery_window_end=khung + dt.timedelta(hours=9),
        max_weight_kg=24000, max_volume_m3=33, max_pallet_count=18, status="dispatched"))
    db.flush()
    db.add(models.TransportTrip(id="TRIP-" + ma, freight_order_id="FO-" + ma,
                                trip_type="multi_stop", status=trang_thai_chuyen))
    db.flush()
    db.add(models.TripDeliveryOrder(trip_id="TRIP-" + ma, do_id=ma))
    db.flush()


def test_do_da_giao_nhung_chuyen_con_chay_thi_chua_ban_giao(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        _do_da_giao_tren_chuyen(db, models, "DO-BG-DIEM-DAU", "in_transit")   # hạ ở điểm đầu, xe còn chạy
        _do_da_giao_tren_chuyen(db, models, "DO-BG-DIEM-CUOI", "completed")   # chuyến đã đóng
        db.commit()

    r = client.get("/api/handover/delivery-orders?page_size=50", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    ma = [x["do_id"] for x in r.json()["data"]["items"]]
    assert "DO-BG-DIEM-CUOI" in ma
    assert "DO-BG-DIEM-DAU" not in ma, "DO hạ ở điểm đầu chưa được bàn giao khi chuyến còn chạy"
    assert r.json()["data"]["total"] == len(ma), "`total` phải đếm sau khi loại, không đếm trước"

    r = client.get("/api/handover/delivery-orders/DO-BG-DIEM-DAU", headers=API_TEST_HEADERS)
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "DO_TRIP_CHUA_DONG"
    assert "TRIP-DO-BG-DIEM-DAU" in r.json()["detail"]["message"]

    r = client.get("/api/handover/delivery-orders/DO-BG-DIEM-CUOI", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["header"]["do_id"] == "DO-BG-DIEM-CUOI"

    # Chuyến đóng xong → DO điểm đầu xuất hiện, không cần làm gì thêm.
    with database.SessionLocal() as db:
        db.get(models.TransportTrip, "TRIP-DO-BG-DIEM-DAU").status = "completed"
        db.commit()
    r = client.get("/api/handover/delivery-orders?page_size=50", headers=API_TEST_HEADERS)
    assert "DO-BG-DIEM-DAU" in [x["do_id"] for x in r.json()["data"]["items"]]
    assert client.get("/api/handover/delivery-orders/DO-BG-DIEM-DAU", headers=API_TEST_HEADERS).status_code == 200
