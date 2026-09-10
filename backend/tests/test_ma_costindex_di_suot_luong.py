# -*- coding: utf-8 -*-
"""Ma COSTINDEX di suot luong: cong thuc -> dong chi phi thuc te -> ho so hoan tat.

Ba phep kiem nho, khong can server:

  1. `bang_costindex` / `costindex_cho` — phep tra ma tu MOT cong thuc, theo ba
     cach ma ba noi goi biet (khoa, charge_type, ten).
  2. `_sanitize_formula_terms` GIU `cost_index` khi luu cong thuc — mat o day
     la mat ngay tu cua dau, va khong loi nao bao.
  3. `_save_trip_cost_rows` GHI `cost_index` xuong `freight_charge_items`, ke
     ca khi giao dien khong gui — tra tu cong thuc cua xe chay chuyen.
"""
import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy.orm import sessionmaker

from database import Base


TERMS = [
    {"key": "fuel", "label": "Chi phí xăng dầu /km", "kind": "cost", "rate": 6250, "cost_index": "EPL-CP-XD"},
    {"key": "wh", "label": "Phí bãi & lưu kho", "kind": "cost", "rate": 200000, "cost_index": "EPL-CP-BAI"},
    {"key": "rate", "label": "Cước phí vận chuyển /kg", "kind": "revenue", "rate": 1500, "cost_index": "EPL-TH-CUOC"},
    {"key": "custom_x", "label": "Phí chờ lưu ca", "kind": "cost", "rate": 50000},   # chua gan ma
]


def test_tra_ma_theo_khoa_charge_type_va_ten():
    from services.khoan_muc_chi_phi import bang_costindex, costindex_cho

    bang = bang_costindex(TERMS)
    # Theo KHOA cong thuc (tuong minh nhat).
    assert costindex_cho(bang, khoa="fuel") == "EPL-CP-XD"
    # Theo charge_type: `wh` cua cong thuc la `yard` cua bang chi phi.
    assert costindex_cho(bang, charge_type="yard") == "EPL-CP-BAI"
    # Theo TEN, ke ca ten khong trung tuyet doi voi nhan cong thuc.
    assert costindex_cho(bang, ten="Phí cầu đường") == ""          # cong thuc nay khong co BOT
    assert costindex_cho(bang, ten="Chi phí xăng dầu") == "EPL-CP-XD"
    # Khoan muc chua gan ma -> RONG, khong bia.
    assert costindex_cho(bang, khoa="custom_x", ten="Phí chờ lưu ca") == ""
    assert costindex_cho({}, khoa="fuel") == ""


def test_luu_cong_thuc_giu_ma_costindex():
    from routes.fleet_routes import _sanitize_formula_terms

    sach = _sanitize_formula_terms([
        {"key": "fuel", "label": "Xăng", "rate": "6,250", "cost_index": "  epl-cp-xd "},
        {"key": "toll", "label": "BOT", "rate": 1},
        {"key": "x", "label": "Dài", "rate": 1, "cost_index": "A" * 80},
    ])
    assert sach[0]["cost_index"] == "epl-cp-xd"      # cat trang, giu nguyen chu
    assert sach[1]["cost_index"] == ""               # khong gui thi rong, khong None
    assert len(sach[2]["cost_index"]) == 32           # gioi han do dai cot


def test_dong_chi_phi_thuc_te_mang_ma_du_giao_dien_khong_gui(may_kiem):
    """`_save_trip_cost_rows` phai ghi `cost_index` vao `freight_charge_items`.

    Giao dien cu khong gui `cost_index` (chi gui name/original/actual/note).
    Neu may chu chi luu cai duoc gui thi moi dong chi phi cua may chu cu deu
    NULL, va ho so hoan tat phai doan lai — nen may chu tu tra tu cong thuc cua
    xe dang chay chuyen.
    """
    import json
    import models
    from models import (CostFormula, Customer, DeliveryOrder, FreightChargeItem, FreightOrder,
                        Location, TransportTrip, Vehicle, VehicleType, Carrier,
                        CurrencyDefinition, FinanceControlConfig)
    from services.tms_cost_service import save_trip_cost_rows

    engine = may_kiem()
    # Dung `models.Base`, khong dung `Base` nap o dau tep: fixture phien
    # `isolate_application_database` nap lai module `database`, nen `Base` nap
    # luc thu thap la mot doi tuong CU — metadata cua no khong con la metadata
    # ma cac lop trong `models` dang dang ky vao, va `create_all` tren no dung
    # thieu bang ("relation carriers does not exist") trong khi model thi co.
    models.Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        # Du lieu goc — chot TUNG LUOT vi cac model chi khai ForeignKey tran.
        db.add_all([Location(id="L-A", name="A"), Location(id="L-B", name="B"),
                    VehicleType(id="VT-CI", name="Xe kiem costindex", max_weight=10000),
                    Customer(id="CUS-CI", name="Khach"),
                    CurrencyDefinition(code="VND", minor_units=0),
                    FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
                    Carrier(id="CAR-CI", name="Noi bo", tax_code="T", is_internal=True)])
        db.flush()
        db.add(Vehicle(id="51C-CI", type="VT-CI", status="Sẵn sàng"))
        db.add(CostFormula(id="vehicle-type::VT-CI::VND", name="CT", formula_expression=json.dumps(
            {"vehicle_type_id": "VT-CI", "currency": "VND", "components": {}, "terms": TERMS})))
        db.flush()
        luc = dt.datetime(2026, 8, 11, 8)
        db.add(FreightOrder(id="FO-CI", pickup_location_id="L-A", delivery_location_id="L-B",
                            pickup_window_start=luc, pickup_window_end=luc + dt.timedelta(hours=1),
                            delivery_window_start=luc + dt.timedelta(hours=4),
                            delivery_window_end=luc + dt.timedelta(hours=8),
                            total_weight_kg=1000, total_volume_m3=5, total_pallet_count=2,
                            max_weight_kg=10000, max_volume_m3=20, max_pallet_count=10,
                            status="delivered"))
        db.flush()
        db.add(TransportTrip(id="TRIP-CI", freight_order_id="FO-CI", trip_type="one_way",
                             status="completed", version=1, vehicle_id="51C-CI"))
        db.commit()

        save_trip_cost_rows(db, "TRIP-CI", {"currency_code": "VND", "carrier_id": "CAR-CI", "lines": [
            # Giao dien CU: khong co cost_index, khong co charge_type.
            {"name": "Chi phí xăng dầu /km", "original_amount": "100000", "actual_amount": "110000"},
            {"name": "Phí bãi & lưu kho", "original_amount": "200000", "actual_amount": "200000"},
            # Giao dien MOI gui ma -> ton trong ma duoc gui.
            {"name": "Phí chờ lưu ca", "original_amount": "50000", "actual_amount": "50000",
             "cost_index": "EPL-CP-CHO"},
        ]}, "PUT", "/trips/TRIP-CI/actual-cost", "k-ci-1", "maker", {"finance_creator"})
        db.commit()

        ma = {r.description: (r.charge_type, r.cost_index) for r in db.query(FreightChargeItem).all()}
        assert ma["Chi phí xăng dầu /km"] == ("fuel", "EPL-CP-XD")
        assert ma["Phí bãi & lưu kho"] == ("yard", "EPL-CP-BAI")
        assert ma["Phí chờ lưu ca"] == ("waiting", "EPL-CP-CHO")
    finally:
        db.close()
        engine.dispose()
