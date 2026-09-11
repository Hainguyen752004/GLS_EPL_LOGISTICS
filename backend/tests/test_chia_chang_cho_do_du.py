# -*- coding: utf-8 -*-
"""MỌI lệnh giao hàng trong một chuyến phải có chặng giao — không thì từ chối lúc lập chuyến.

LỖI ĐÃ ĐO ĐƯỢC trên máy chủ thật (11/09). Cách chia chặng cũ là một câu:

    do_id = do_ids[-1] if sequence == len(segments) else do_ids[0]

nên chuyến chở NHIỀU DO hơn số chặng thì có DO không nhận được chặng nào. Đo: 2 DO trên
tuyến Sóng Thần → Cát Lái (MỘT chặng) → chặng duy nhất thuộc DO thứ hai; DO thứ nhất có tập
chặng rỗng nên `POST /complete-delivery` trả `POD_LINEAGE_INVALID` mãi mãi, DO không bao giờ
đóng được, và chuyến giữ xe cùng tài xế tới khi có người huỷ tay. 3 DO trên 2 chặng thì DO ở
giữa mất chặng y như vậy. Máy chủ KHÔNG chặn gì lúc lập chuyến.

Bốn điều khoá ở đây:
1. DO nhiều hơn chặng → 409 `TRIP_DO_NHIEU_HON_CHANG`, và KHÔNG tạo chuyến nào.
2. DO ít hơn hoặc bằng số chặng → mỗi DO có ít nhất một chặng; DO cuối nhận các chặng còn lại.
3. Khai tay `stop_plan[].do_id` thì hệ theo khai; khai mã lạ → 422.
4. Khai tay mà bỏ sót một DO → 409 `TRIP_DO_KHONG_CO_CHANG`.
"""
import importlib
import json

from conftest import API_TEST_HEADERS


def _tuyen(ma, cac_chang):
    """Tuyến với số chặng cho trước (mỗi chặng 10 km)."""
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    diem = ["Kho A", "Trung chuyển 1", "Trung chuyển 2", "Cảng Z"]
    chang = [{"origin": diem[i], "destination": diem[i + 1], "distance_km": 10}
             for i in range(cac_chang)]
    with database.SessionLocal() as db:
        r = db.get(models.Route, ma) or models.Route(id=ma)
        r.name = "%s (%d chặng)" % (ma, cac_chang)
        r.distance_km = 10 * cac_chang
        r.segments_json = json.dumps(chang, ensure_ascii=False)
        db.add(r)
        db.commit()
    return ma


def _lap_chuyen(client, ma_trip, do_ids, stop_plan=None):
    than = {"id": ma_trip, "do_ids": do_ids, "trip_type": "one_way",
            "planned_departure_at": "2026-08-12T02:00:00+00:00",
            "avg_speed_kmh": 40, "dwell_minutes": 30, "return_purpose": "none"}
    if stop_plan is not None:
        than["stop_plan"] = stop_plan
    return client.post("/api/tms/trips/from-delivery-orders", json=than,
                       headers={**API_TEST_HEADERS, "Idempotency-Key": "lap-" + ma_trip})


def _do_tren_tuyen(workflow_builder, client, qid, ma_tuyen, so_do):
    """Sinh `so_do` DO cùng tuyến từ một báo giá (mỗi DO một dòng hàng)."""
    import datetime as dt
    from zoneinfo import ZoneInfo
    hom_nay = dt.datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    dau = {"X-User-Id": "tester"}
    r = client.post("/api/quotations", json={
        "id": qid, "customer_id": "CUS-T1", "route_id": ma_tuyen,
        "valid_to": (hom_nay + dt.timedelta(days=30)).isoformat(),
        "total_cost": 1_000_000, "selling_price": 3_000_000,
        "packaging_spec": "Nguyên khối, niêm phong tại kho",
        "pickup_window_start": "2026-08-12T01:00:00+00:00",
        "pickup_window_end": "2026-08-12T04:00:00+00:00",
        "delivery_window_start": "2026-08-12T04:00:00+00:00",
        "delivery_window_end": "2026-08-12T13:00:00+00:00",
    }, headers=dau)
    assert r.status_code == 200, r.text
    r = client.put("/api/quotations/%s/items" % qid, json={
        "items": [{"name": "Cont hàng", "quantity": so_do, "uom": "Cont"}]}, headers=dau)
    assert r.status_code == 200, r.text
    assert client.put("/api/quotations/%s/approve" % qid, headers=dau).status_code == 200
    assert client.post("/api/quotations/%s/send" % qid, json={}, headers=dau).status_code == 200
    r = client.post("/api/quotations/%s/accept" % qid, json={}, headers=dau)
    assert r.status_code == 200, r.text
    ds = r.json().get("do_ids") or []
    assert len(ds) == so_do, ds
    return ds


def test_nhieu_do_hon_chang_thi_tu_choi_lap_chuyen(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _tuyen("RT-1CHANG", 1)
    ds = _do_tren_tuyen(workflow_builder, client, "QT-CHANG-1", "RT-1CHANG", 2)

    r = _lap_chuyen(client, "TRIP-CHANG-X", ds)
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "TRIP_DO_NHIEU_HON_CHANG"
    assert "tách thành nhiều chuyến" in r.json()["detail"]["message"]
    # KHÔNG được tạo chuyến nửa vời.
    assert client.get("/api/tms/trips/TRIP-CHANG-X", headers=API_TEST_HEADERS).status_code == 404

    # Một DO trên tuyến một chặng thì vẫn lập được (đường thường ngày không bị siết).
    r = _lap_chuyen(client, "TRIP-CHANG-1", ds[:1])
    assert r.status_code == 200, r.text
    legs = r.json()["data"]["legs"]
    assert [l["do_id"] for l in legs] == [ds[0]]


def test_moi_do_deu_co_chang_khi_du_chang(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _tuyen("RT-3CHANG", 3)
    ds = _do_tren_tuyen(workflow_builder, client, "QT-CHANG-3", "RT-3CHANG", 2)

    r = _lap_chuyen(client, "TRIP-CHANG-3", ds)
    assert r.status_code == 200, r.text
    legs = sorted(r.json()["data"]["legs"], key=lambda l: l["sequence_no"])
    gan = [l["do_id"] for l in legs]
    # DO thứ i nhận chặng thứ i; DO CUỐI nhận các chặng còn lại.
    assert gan == [ds[0], ds[1], ds[1]], gan
    assert set(gan) == set(ds), "mọi DO phải có chặng giao"


def test_khai_tay_diem_dung_va_cac_cua_chan(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _tuyen("RT-3CHANG-B", 3)
    ds = _do_tren_tuyen(workflow_builder, client, "QT-CHANG-3B", "RT-3CHANG-B", 3)

    # Khai tay: DO3 hạ ở chặng 1, DO1 chặng 2, DO2 chặng 3.
    r = _lap_chuyen(client, "TRIP-KHAI-TAY", ds, stop_plan=[
        {"sequence_no": 1, "do_id": ds[2], "receiver_name": "Kho 1"},
        {"sequence_no": 2, "do_id": ds[0], "receiver_name": "Kho 2"},
        {"sequence_no": 3, "do_id": ds[1], "receiver_name": "Cảng"},
    ])
    assert r.status_code == 200, r.text
    legs = sorted(r.json()["data"]["legs"], key=lambda l: l["sequence_no"])
    assert [l["do_id"] for l in legs] == [ds[2], ds[0], ds[1]]

    # Mã lạ → 422.
    r = _lap_chuyen(client, "TRIP-KHAI-LA", ds, stop_plan=[
        {"sequence_no": 1, "do_id": "DO-KHONG-THUOC-CHUYEN"}])
    assert r.status_code == 422 and r.json()["detail"]["code"] == "TRIP_DO_INVALID"

    # Khai tay mà bỏ sót một DO (dồn hai chặng đầu cho DO1, chặng cuối cho DO1 nữa) → 409.
    r = _lap_chuyen(client, "TRIP-KHAI-THIEU", ds, stop_plan=[
        {"sequence_no": 1, "do_id": ds[0]},
        {"sequence_no": 2, "do_id": ds[0]},
        {"sequence_no": 3, "do_id": ds[0]},
    ])
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "TRIP_DO_KHONG_CO_CHANG"
    assert ds[1] in r.json()["detail"]["message"] and ds[2] in r.json()["detail"]["message"]
