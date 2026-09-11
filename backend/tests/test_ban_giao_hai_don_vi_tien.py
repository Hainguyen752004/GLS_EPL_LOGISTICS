# -*- coding: utf-8 -*-
"""Hồ sơ bàn giao có HAI đơn vị tiền: thu theo báo giá, chi theo phiếu chi phí thực tế.

Đo 11/09 trên máy chủ thật, DO sinh từ báo giá 120 USD: gói bàn giao trả
`currency: "USD"` cho cả hồ sơ trong khi `actual_cost_total = 851.000` là ĐỒNG, nên
`margin_amount = 135 − 851.000 = −850.865` và `margin_percent = −630.270%`, mà
`khop_gia_thanh` vẫn báo `true`. Bên công nợ đọc gói đó sẽ thấy chuyến lãi âm sáu
trăm nghìn phần trăm.

Ba điều khoá ở đây:
1. Báo giá ngoại tệ → `currency_thu` là tiền báo giá, `currency_chi` là tiền của phiếu
   chi phí, và mỗi dòng chi tiết mang `currency` của chính nó.
2. Lãi gộp tính TRONG MỘT đơn vị: giá thành quy đổi bằng `fx_rate` báo giá đã khoá.
3. Không có tỷ giá thì KHÔNG BỊA: lãi trả `None` kèm `margin_unavailable_reason`.
"""
import datetime as dt
import importlib

from conftest import API_TEST_HEADERS


def _do_ngoai_te(db, models, ma, tien, gia_goc, phu_phi, fx, chi_vnd, co_fx=True):
    """Một DO đã hoàn tất: báo giá bằng `tien`, phiếu chi phí thực tế bằng VND.

    `co_fx=False` nghĩa là CHƯA KHAI tỷ giá. Cột `quotations.fx_rate` có mặc định 1.0 nên
    không khai được bằng None — 1.0 chính là giá trị "chưa khai", và mã phải hiểu như vậy.
    """
    khach = "CUS-" + ma
    if db.get(models.Customer, khach) is None:
        db.add(models.Customer(id=khach, name=khach))
    for ma_tien, so_le in (("VND", 0), ("USD", 2), ("LAK", 0), ("THB", 2)):
        if db.get(models.CurrencyDefinition, ma_tien) is None:
            db.add(models.CurrencyDefinition(code=ma_tien, minor_units=so_le, is_active=True))
        if ma_tien != "THB" and db.get(models.Currency, ma_tien) is None:
            db.add(models.Currency(id=ma_tien, exchange_rate=(1 if ma_tien == "VND" else fx)))
    db.flush()
    db.add(models.Quotation(
        id="QT-" + ma, customer_id=khach, route_id="RT-T1", currency_code=tien,
        fx_rate=(fx if co_fx else 1.0), unit_price=gia_goc, selling_price=gia_goc,
        total_cost=gia_goc / 3, price_basis="per_trip", canonical_status="split", status="Đã tách"))
    db.flush()   # báo giá phải có TRƯỚC khi DO trỏ vào nó (khoá ngoại quotation_id)
    db.add(models.DeliveryOrder(
        id=ma, customer_id=khach, route_id="RT-T1", quotation_id="QT-" + ma,
        canonical_status="delivered", status="Đã giao", price_basis="per_trip",
        unit_price=gia_goc, billed_qty=1))
    db.flush()
    db.add(models.DeliveryOrderCloseout(
        id="CLO-" + ma, do_id=ma, base_selling_price_snapshot=gia_goc, base_price_source="quotation",
        base_price_source_id="QT-" + ma, surcharge_total=phu_phi, final_selling_price=gia_goc + phu_phi,
        currency_code=tien, completed_at=dt.datetime(2026, 9, 10, 3, tzinfo=dt.timezone.utc),
        completed_by="ops"))
    db.flush()   # hồ sơ chốt phải có trước dòng khách trả thêm trỏ vào nó
    if phu_phi:
        # Dòng khách trả thêm: có nó thì sổ thu mới khớp giá cuối của DO.
        db.add(models.DeliveryOrderChargeAdjustment(
            id="ADJ-" + ma, closeout_id="CLO-" + ma, line_no=1, name="Khách trả thêm",
            cost_index="1017", original_amount=0, actual_amount=phu_phi, increase_amount=phu_phi, created_by="ops"))
    db.flush()
    # Phiếu chi phí thực tế cần một lệnh vận chuyển (khoá ngoại `freight_order_id`).
    for ma_diem in ("LOC-BG-A", "LOC-BG-B"):
        if db.get(models.Location, ma_diem) is None:
            db.add(models.Location(id=ma_diem, name=ma_diem, type="Warehouse"))
    db.flush()   # địa điểm phải có trước lệnh vận chuyển trỏ vào nó
    khung = dt.datetime(2026, 9, 10, 1, tzinfo=dt.timezone.utc)
    db.add(models.FreightOrder(
        id="FO-" + ma, pickup_location_id="LOC-BG-A", delivery_location_id="LOC-BG-B",
        pickup_window_start=khung, pickup_window_end=khung + dt.timedelta(hours=2),
        delivery_window_start=khung + dt.timedelta(hours=2), delivery_window_end=khung + dt.timedelta(hours=9),
        max_weight_kg=24000, max_volume_m3=33, max_pallet_count=18, status="delivered"))
    if db.get(models.Carrier, "CAR-BG") is None:
        db.add(models.Carrier(id="CAR-BG", name="Đội xe nội bộ (kiểm)", status="active"))
    db.flush()
    # Chuyến + móc DO↔chuyến: hồ sơ tìm phiếu chi phí THEO CHUYẾN của DO.
    db.add(models.TransportTrip(id="TRIP-" + ma, freight_order_id="FO-" + ma,
                                trip_type="one_way", status="completed"))
    db.flush()
    db.add(models.TripDeliveryOrder(trip_id="TRIP-" + ma, do_id=ma))
    db.flush()
    cost = models.FreightActualCost(
        id="COST-" + ma, freight_order_id="FO-" + ma, trip_id="TRIP-" + ma, carrier_id="CAR-BG",
        currency_code="VND", functional_currency="VND", exchange_rate_snapshot=1,
        exchange_rate_date=dt.date(2026, 9, 10), exchange_rate_source="functional",
        status="approved", total_amount=chi_vnd, is_active=True, created_by="ops", updated_by="ops")
    db.add(cost)
    db.flush()
    db.add(models.FreightChargeItem(
        id="IT-" + ma, cost_id=cost.id, description="Chi phí xăng dầu /km", charge_type="fuel",
        cost_index="1091", original_amount=chi_vnd, actual_amount=chi_vnd, increase_amount=0,
        quantity=1, unit_price=chi_vnd, tax_code="EXEMPT", tax_rate_snapshot=0, tax_mode="exempt",
        net_amount=chi_vnd, tax_amount=0, total_amount=0, created_by="ops", updated_by="ops"))


def _header(client, ma):
    r = client.get("/api/handover/delivery-orders/%s" % ma, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_bao_gia_usd_chi_phi_vnd_thi_lai_gop_quy_doi_dung(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        # 120 USD cước + 15 USD trả thêm = 135 USD; chi 851.000 đ; tỷ giá 26.173,5 đ/USD.
        _do_ngoai_te(db, models, "DO-USD-1", "USD", 120, 15, 26173.5, 851_000)
        db.commit()
    d = _header(client, "DO-USD-1")
    h = d["header"]
    assert h["currency_thu"] == "USD" and h["currency_chi"] == "VND"
    assert h["final_selling_price"] == 135.0
    assert h["actual_cost_total"] == 851_000.0 and h["actual_cost_total_currency"] == "VND"
    assert h["actual_cost_total_quy_doi"] == 32.51        # 851.000 / 26.173,5
    assert h["margin_amount"] == 102.49 and h["margin_currency"] == "USD"
    assert h["margin_percent"] == 75.92                  # 102,49 / 135
    assert h["fx_rate"] == 26173.5 and h["fx_rate_source"] == "quotation"
    assert not h["margin_unavailable_reason"]
    # Đơn vị cước: thiếu nó thì bên kia không dựng được dòng hoá đơn.
    assert h["price_basis"] == "per_trip" and h["billed_qty"] == 1.0 and h["unit_price"] == 120.0
    # Sổ tổng: không còn phép trừ chéo đơn vị.
    t = h["ledger_totals"]
    assert t["currency_thu"] == "USD" and t["currency_chi"] == "VND"
    assert t["tong_chi_quy_doi"] == 32.51 and t["lai_gop"] == 102.49
    # Mỗi dòng mang đơn vị của chính nó.
    tien_theo_loai = {(x["kind"], x["currency"]) for x in d["details"]}
    assert ("chi", "VND") in tien_theo_loai and ("thu", "USD") in tien_theo_loai
    assert all(x["currency"] in ("USD", "VND") for x in d["details"])


def test_bao_gia_lak_va_bao_gia_vnd_van_dung(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        _do_ngoai_te(db, models, "DO-LAK-1", "LAK", 2_900_000, 150_000, 1.18, 1_278_000)
        _do_ngoai_te(db, models, "DO-VND-1", "VND", 2_486_000, 180_000, 1.0, 896_800)
        db.commit()
    h = _header(client, "DO-LAK-1")["header"]
    assert h["currency_thu"] == "LAK" and h["actual_cost_total_currency"] == "VND"
    assert h["actual_cost_total_quy_doi"] == 1_083_050.85      # 1.278.000 / 1,18
    assert h["margin_amount"] == 1_966_949.15 and h["margin_currency"] == "LAK"

    # Báo giá VNĐ: một đơn vị tiền, số không đổi so với trước khi sửa.
    h = _header(client, "DO-VND-1")["header"]
    assert h["currency_thu"] == h["currency_chi"] == "VND" and h["fx_rate"] is None
    assert h["margin_amount"] == 1_769_200.0 and h["margin_percent"] == 66.36
    assert h["ledger_totals"]["khop_gia_thanh"] is True


def test_khong_co_ty_gia_thi_khong_bia_lai_gop(app_client, workflow_builder):
    """Báo giá THB không khai `fx_rate` và không có dòng nào trong bảng tiền tệ của bộ kiểm."""
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        if db.get(models.Currency, "THB") is not None:
            db.delete(db.get(models.Currency, "THB"))
        _do_ngoai_te(db, models, "DO-THB-1", "THB", 5_000, 0, 0, 900_000, co_fx=False)
        db.commit()
    h = _header(client, "DO-THB-1")["header"]
    assert h["currency_thu"] == "THB" and h["currency_chi"] == "VND"
    assert h["margin_amount"] is None and h["margin_percent"] is None
    assert "tỷ giá" in h["margin_unavailable_reason"]
    assert h["actual_cost_total"] == 900_000.0        # số thật vẫn trả, chỉ không quy đổi
    assert h["actual_cost_total_quy_doi"] is None
    assert h["ledger_totals"]["lai_gop"] is None
