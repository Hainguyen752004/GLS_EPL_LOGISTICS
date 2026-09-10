# -*- coding: utf-8 -*-
"""Acc code dùng chung theo KHOẢN MỤC — đặt một lần trên một loại xe, loại khác kế thừa.

Chủ dự án (10/09): gán 1091 cho "Chi phí xăng dầu /km" ở Container 20FT, sang Xe
tải 10 tấn cùng khoản mục lại trống. Ba điều khoá:
1. Lưu loại A có mã → lưu loại B cùng khoản mục KHÔNG gửi mã → B nhận mã của A.
2. Đổi mã ở bất kỳ loại nào → mọi loại đang theo mã chung đổi theo (một khoản mục = một mã).
3. Khoản mục tự thêm (không có `key` chuẩn) nhận diện theo TÊN, bỏ dấu, không phân biệt hoa thường.
"""
import importlib

from conftest import API_TEST_HEADERS


def _luu(client, loai, terms):
    r = client.post("/api/cost-formulas", json={"vehicle_type_id": loai, "currency": "VND", "terms": terms},
                    headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    return {t["key"]: t for t in r.json()["data"]["terms"]}


def _doc(client, loai):
    r = client.get("/api/cost-formulas", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    for f in r.json():
        if f.get("vehicle_type_id") == loai:
            return {t["key"]: t for t in f["terms"]}
    raise AssertionError("khong thay cong thuc " + loai)


def _them_loai_xe(*ma):
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        for m in ma:
            if db.get(models.VehicleType, m) is None:
                db.add(models.VehicleType(id=m, name=m, max_weight=20000, volume_capacity_m3=40, pallet_capacity=20))
        db.commit()


def test_loai_xe_khac_ke_thua_acc_code_cua_cung_khoan_muc(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _them_loai_xe("VT-CHUNG-A", "VT-CHUNG-B", "VT-CHUNG-C")

    _luu(client, "VT-CHUNG-A", [
        {"key": "fuel", "label": "Chi phí xăng dầu /km", "kind": "cost", "factor": "per_km", "rate": 4800, "cost_index": "1091"},
        {"key": "driver", "label": "Phụ cấp chuyến tài xế", "kind": "cost", "factor": "per_trip", "rate": 400000, "cost_index": "1017"},
        {"key": "phu_them", "label": "Phí Vệ Sinh Thùng", "kind": "cost", "factor": "per_trip", "rate": 50000, "cost_index": "1300"},
    ])
    # B: cùng khoản mục, KHÔNG gửi mã → kế thừa. Khoản mục tự thêm nhận theo tên (khác dấu, khác hoa thường).
    b = _luu(client, "VT-CHUNG-B", [
        {"key": "fuel", "label": "Chi phí xăng dầu /km", "kind": "cost", "factor": "per_km", "rate": 5200},
        {"key": "driver", "label": "Phụ cấp chuyến tài xế", "kind": "cost", "factor": "per_trip", "rate": 350000},
        {"key": "term_9", "label": "phi ve sinh thung", "kind": "cost", "factor": "per_trip", "rate": 40000},
        {"key": "toll", "label": "Phí cầu đường / BOT", "kind": "cost", "factor": "per_trip", "rate": 150000},
    ])
    assert b["fuel"]["cost_index"] == "1091"
    assert b["driver"]["cost_index"] == "1017"
    assert b["term_9"]["cost_index"] == "1300"
    assert b["toll"]["cost_index"] == ""          # chưa ai đặt → vẫn trống, không bịa

    # Mapping tài khoản có dòng dùng chung.
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        assert db.get(models.AccountMapping, "khoan_muc::fuel").account_code == "1091"
        assert db.get(models.AccountMapping, "khoan_muc::ten::phi ve sinh thung").account_code == "1300"

    # MỘT khoản mục = MỘT Acc code trên mọi loại xe: C đặt mã mới cho xăng dầu → A, B (đang
    # theo mã chung 1091) đổi theo. Đổi ở đâu cũng là đổi chung — đúng câu "chi phí giống
    # nhau thì lưu chung acc code"; muốn mã riêng thì đó là một khoản mục khác (tên khác).
    _luu(client, "VT-CHUNG-C", [
        {"key": "fuel", "label": "Chi phí xăng dầu /km", "kind": "cost", "factor": "per_km", "rate": 4000, "cost_index": "1500"},
    ])
    assert _doc(client, "VT-CHUNG-A")["fuel"]["cost_index"] == "1500"
    assert _doc(client, "VT-CHUNG-B")["fuel"]["cost_index"] == "1500"
    # A đổi lại → cả ba cùng đổi; các mã khác của B không mất khi A chỉ lưu một dòng.
    _luu(client, "VT-CHUNG-A", [
        {"key": "fuel", "label": "Chi phí xăng dầu /km", "kind": "cost", "factor": "per_km", "rate": 4800, "cost_index": "1092"},
    ])
    assert _doc(client, "VT-CHUNG-B")["fuel"]["cost_index"] == "1092"
    assert _doc(client, "VT-CHUNG-C")["fuel"]["cost_index"] == "1092"
    assert _doc(client, "VT-CHUNG-B")["driver"]["cost_index"] == "1017"
