# -*- coding: utf-8 -*-
"""Chặng TRUNG CHUYỂN không phải điểm giao — POD chỉ đòi ở nơi hàng thật sự được hạ.

HAI LỖI ĐÃ ĐO ĐƯỢC trên máy chủ thật (11/09), cả hai đều nằm ở cách dựng chặng chuyến:

1. Mọi chặng của tuyến đều bị đặt `leg_type="delivery"`. Tuyến
   `VSIP II-A → Vành đai 3 → Cảng Cát Lái` có hai chặng, nên một DO phải nộp POD tại
   **Vành đai 3** — nơi xe chỉ đi ngang. POD là bằng chứng giao hàng và nó đi vào hồ sơ bàn
   giao cho bên công nợ, nên đó là ghi nhận một việc không xảy ra. Có với cả chuyến MỘT DO.
2. Chuyến chở nhiều DO hơn số chặng thì có DO **không nhận được chặng nào**, nên không nộp
   được POD, không bao giờ đóng được, và chuyến giữ xe lại tới khi có người huỷ tay.

Luật mới: mặc định mọi DO của chuyến được giao ở ĐIỂM CUỐI tuyến. Chặng giữa là `outbound`
(đi ngang, không POD); chặng cuối là `delivery` của DO thứ nhất; mỗi DO còn lại có một chặng
HẠ HÀNG riêng tại đúng điểm cuối đó, 0 km và 0 phút dừng nên ETA không đổi. Khai tay
`stop_plan[].do_id` thì thành chuyến nhiều điểm giao thật.
"""
import datetime as dt
import importlib
import json

from conftest import API_TEST_HEADERS

KHUNG = {"pickup_window_start": "2026-08-12T01:00:00+00:00",
         "pickup_window_end": "2026-08-12T04:00:00+00:00",
         "delivery_window_start": "2026-08-12T04:00:00+00:00",
         "delivery_window_end": "2026-08-12T13:00:00+00:00"}


def _tuyen(ma, so_chang, km_moi_chang=10):
    """Tuyến `so_chang` chặng: Kho A → Trung chuyển 1 → … → Cảng Z."""
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    diem = ["Kho A"] + ["Trung chuyển %d" % i for i in range(1, so_chang)] + ["Cảng Z"]
    chang = [{"origin": diem[i], "destination": diem[i + 1], "distance_km": km_moi_chang}
             for i in range(so_chang)]
    with database.SessionLocal() as db:
        r = db.get(models.Route, ma) or models.Route(id=ma)
        r.name = "%s (%d chặng)" % (ma, so_chang)
        r.distance_km = km_moi_chang * so_chang
        r.segments_json = json.dumps(chang, ensure_ascii=False)
        db.add(r)
        db.commit()
    return ma


def _sinh_do(client, qid, ma_tuyen, so_do):
    """Một báo giá → `so_do` DO cùng tuyến, đủ bốn mốc giờ để lập chuyến."""
    dau = {"X-User-Id": "tester"}
    hom_nay = dt.date(2026, 8, 1)
    r = client.post("/api/quotations", json={
        "id": qid, "customer_id": "CUS-T1", "route_id": ma_tuyen,
        "valid_to": (hom_nay + dt.timedelta(days=400)).isoformat(),
        "total_cost": 1_000_000, "selling_price": 3_000_000,
        "packaging_spec": "Nguyên khối, niêm phong tại kho", **KHUNG,
    }, headers=dau)
    assert r.status_code == 200, r.text
    assert client.put("/api/quotations/%s/items" % qid, json={
        "items": [{"name": "Cont hàng", "quantity": so_do, "uom": "Cont"}]},
        headers=dau).status_code == 200
    assert client.put("/api/quotations/%s/approve" % qid, headers=dau).status_code == 200
    assert client.post("/api/quotations/%s/send" % qid, json={}, headers=dau).status_code == 200
    # Hàng nguyên khối phải có số niêm phong, không thì cửa xuất bến chặn (SEAL_NUMBER_REQUIRED).
    r = client.post("/api/quotations/%s/accept" % qid, json={
        "dos": [{"seal_no": "SL-%s-%02d" % (qid, i + 1)} for i in range(so_do)]}, headers=dau)
    assert r.status_code == 200, r.text
    ds = r.json().get("do_ids") or []
    assert len(ds) == so_do, ds
    return ds


def _lap_chuyen(client, ma_trip, do_ids, stop_plan=None):
    than = {"id": ma_trip, "do_ids": do_ids, "trip_type": "one_way",
            "planned_departure_at": "2026-08-12T02:00:00+00:00",
            "avg_speed_kmh": 40, "dwell_minutes": 30, "return_purpose": "none"}
    if stop_plan is not None:
        than["stop_plan"] = stop_plan
    return client.post("/api/tms/trips/from-delivery-orders", json=than,
                       headers={**API_TEST_HEADERS, "Idempotency-Key": "lap-" + ma_trip})


def _chang(goi_trip):
    return sorted(goi_trip["data"]["legs"], key=lambda l: l["sequence_no"])


def test_mot_do_tuyen_co_diem_trung_chuyen_chi_doi_pod_o_diem_cuoi(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _tuyen("RT-TC-3", 3)
    ds = _sinh_do(client, "QT-TC-1", "RT-TC-3", 1)

    r = _lap_chuyen(client, "TRIP-TC-1", ds)
    assert r.status_code == 200, r.text
    chang = _chang(r.json())
    assert [c["leg_type"] for c in chang] == ["outbound", "outbound", "delivery"]
    assert all(c["do_id"] == ds[0] for c in chang), "chặng đi ngang vẫn thuộc DO để tính quãng đường"
    # Chặng giao là chặng tới ĐIỂM CUỐI, không phải điểm trung chuyển.
    giao = [c for c in chang if c["leg_type"] == "delivery"]
    assert len(giao) == 1 and giao[0]["destination"] == "Cảng Z"
    # ETA và tổng quãng đường vẫn đúng theo cả ba chặng.
    assert float(r.json()["data"]["total_distance_km"]) == 30.0


def test_nhieu_do_moi_do_co_chang_ha_hang_tai_diem_cuoi(app_client, workflow_builder):
    """Kể cả trên tuyến MỘT chặng — hình dạng trước đây làm DO không bao giờ đóng được."""
    client, _, _ = app_client
    workflow_builder.master_data()
    _tuyen("RT-TC-1", 1, km_moi_chang=25)
    ds = _sinh_do(client, "QT-TC-2", "RT-TC-1", 3)

    r = _lap_chuyen(client, "TRIP-TC-2", ds)
    assert r.status_code == 200, r.text
    chang = _chang(r.json())
    assert [c["leg_type"] for c in chang] == ["delivery", "delivery", "delivery"]
    # Mỗi DO đúng MỘT chặng giao, và cả ba đều ở điểm cuối thật.
    assert [c["do_id"] for c in chang] == ds
    assert all(c["destination"] == "Cảng Z" for c in chang)
    # Chặng hạ thêm không có km nên tổng quãng đường và ETA không bị nhân lên.
    assert [float(c["distance_km"]) for c in chang] == [25.0, 0.0, 0.0]
    assert float(r.json()["data"]["total_distance_km"]) == 25.0
    assert chang[1]["planned_arrival_at"] == chang[0]["planned_arrival_at"]

    # Tuyến nhiều chặng: chặng giữa là đi ngang, chặng cuối giao, DO còn lại hạ thêm.
    _tuyen("RT-TC-2", 2)
    ds2 = _sinh_do(client, "QT-TC-3", "RT-TC-2", 2)
    r = _lap_chuyen(client, "TRIP-TC-3", ds2)
    assert r.status_code == 200, r.text
    chang = _chang(r.json())
    assert [(c["leg_type"], c["do_id"], c["destination"]) for c in chang] == [
        ("outbound", ds2[0], "Trung chuyển 1"),
        ("delivery", ds2[0], "Cảng Z"),
        ("delivery", ds2[1], "Cảng Z"),
    ]


def test_khai_tay_thanh_chuyen_nhieu_diem_giao_that(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _tuyen("RT-TC-3B", 3)
    ds = _sinh_do(client, "QT-TC-4", "RT-TC-3B", 2)

    # Hàng DO1 hạ ở điểm dừng 1 (Trung chuyển 1), DO2 ở điểm cuối; chặng 2 chỉ đi ngang.
    r = _lap_chuyen(client, "TRIP-TC-4", ds, stop_plan=[
        {"sequence_no": 1, "do_id": ds[0], "receiver_name": "Kho trung chuyển"},
        {"sequence_no": 3, "do_id": ds[1], "receiver_name": "Cảng Z"},
    ])
    assert r.status_code == 200, r.text
    chang = _chang(r.json())
    assert [(c["leg_type"], c["do_id"]) for c in chang] == [
        ("delivery", ds[0]), ("outbound", ds[0]), ("delivery", ds[1])]

    # Khai mã không thuộc chuyến → 422; khai thiếu một DO → 409.
    r = _lap_chuyen(client, "TRIP-TC-LA", ds, stop_plan=[{"sequence_no": 1, "do_id": "DO-LA"}])
    assert r.status_code == 422 and r.json()["detail"]["code"] == "TRIP_DO_INVALID"
    r = _lap_chuyen(client, "TRIP-TC-THIEU", ds, stop_plan=[{"sequence_no": 1, "do_id": ds[0]}])
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "TRIP_DO_KHONG_CO_CHANG" and ds[1] in r.json()["detail"]["message"]


def test_hoan_tat_dong_ca_chang_di_ngang_nen_chuyen_dong_va_xe_duoc_tra(app_client, workflow_builder):
    """Chặng `outbound` không có POD, nên nếu không đóng nó thì chuyến treo và xe bị giữ mãi."""
    client, _, _ = app_client
    workflow_builder.master_data()
    _tuyen("RT-TC-DONG", 2)
    ds = _sinh_do(client, "QT-TC-5", "RT-TC-DONG", 1)
    do_id = ds[0]
    ma_trip = workflow_builder.dieu_phoi_qua_chuyen(do_id, ma_trip="TRIP-TC-DONG")

    goi = client.get("/api/tms/trips/%s" % ma_trip, headers=API_TEST_HEADERS).json()
    chang = _chang(goi)
    assert [c["leg_type"] for c in chang] == ["outbound", "delivery"]
    giao = [c for c in chang if c["leg_type"] == "delivery"]

    import json as _json
    pod = [{"leg_id": giao[0]["id"], "vehicle_id": "VEH-T1", "stop_no": giao[0]["sequence_no"],
            "delivery_time": "2026-08-12T09:00:00+00:00", "location_text": giao[0]["destination"],
            "receiver_name": "Anh Nam", "receiver_phone": "0909000111",
            "delivery_result": "delivered_full", "cargo_condition": "Nguyên niêm phong",
            "file_field": "pod_1", "signature_file_field": "sig_1", "note": "POD kiểm"}]
    r = client.post("/api/delivery-orders/%s/complete-delivery" % do_id,
                    data={"payload": _json.dumps({"trip_id": ma_trip, "currency_code": "VND",
                                                  "pod_entries": pod, "charge_adjustments": []})},
                    files={"pod_1": ("pod.png", b"\x89PNG\r\n\x1a\npod", "image/png"),
                           "sig_1": ("sig.png", b"\x89PNG\r\n\x1a\nsig", "image/png")},
                    headers={**API_TEST_HEADERS, "Idempotency-Key": "hoan-tat-tc"})
    assert r.status_code == 200, r.text
    # MỘT POD là đủ — trước đây phải nộp thêm một POD tại điểm trung chuyển.
    assert len(r.json()["data"]["pod_records"]) == 1

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        cac_chang = db.query(models.TransportTripLeg).filter_by(trip_id=ma_trip).all()
        assert {c.status for c in cac_chang} == {"completed"}, "chặng đi ngang phải được đóng theo"
        assert db.get(models.TransportTrip, ma_trip).status == "completed"
        assert db.get(models.DeliveryOrder, do_id).canonical_status == "delivered"
        assert db.get(models.Vehicle, "VEH-T1").operational_status == "available", "xe phải được trả"


def test_quang_duong_con_lai_tinh_theo_ca_chuyen(app_client, workflow_builder):
    """DO thứ hai chỉ có chặng hạ 0 km, nên tính theo chặng của riêng nó sẽ ra 0 km — sai."""
    client, _, _ = app_client
    workflow_builder.master_data()
    _tuyen("RT-TC-KM", 2, km_moi_chang=30)
    ds = _sinh_do(client, "QT-TC-6", "RT-TC-KM", 2)
    workflow_builder.san_sang_dieu_phoi(ds[0])
    workflow_builder.san_sang_dieu_phoi(ds[1])
    r = _lap_chuyen(client, "TRIP-TC-KM", ds)
    assert r.status_code == 200, r.text
    phien_ban = r.json()["data"]["version"]
    r = client.put("/api/tms/trips/TRIP-TC-KM/dispatch", json={
        "vehicle_id": "VEH-T1", "driver_id": "DRV-T1", "co_driver_id": None,
        "expected_version": phien_ban,
        "assignment_start": "2026-08-12T02:00:00+00:00",
        "assignment_end": "2026-08-12T12:00:00+00:00"}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        for ma in ds:
            theo_doi = db.get(models.VehicleTracking, ma)
            assert theo_doi is not None and float(theo_doi.remaining_distance_km) == 60.0, ma
