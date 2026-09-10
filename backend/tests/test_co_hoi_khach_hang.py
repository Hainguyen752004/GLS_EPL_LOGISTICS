# -*- coding: utf-8 -*-
"""CRM-01 Cơ hội khách hàng và CRM-02 Hồ sơ khách — bước đứng TRƯỚC báo giá.

Tài liệu phạm vi mở chuỗi vận hành bằng "Lead / Customer → Quotation → …". Chủ
dự án duyệt làm thành màn riêng với bảng riêng. Bài kiểm khoá đúng luồng:

1. ghi nhận cơ hội cho khách CHƯA có trong danh mục (chỉ có tên) → mã LEAD-…;
2. giai đoạn chuyển tay theo luật: `quoted` và `won` KHÔNG đặt tay được;
   `lost` phải có lý do;
3. "Lập báo giá" sinh báo giá NHÁP kế thừa khách (tạo khách mới), tuyến, khối
   lượng, số chuyến/tháng; cơ hội sang `quoted` và trỏ vào báo giá; lập lần hai
   bị chặn;
4. khách chấp nhận báo giá đó → cơ hội tự sang `won` (móc ở bước chấp nhận);
5. hồ sơ khách gom đúng số cơ hội / báo giá / DO.
"""
import datetime as dt

from conftest import API_TEST_HEADERS

GIO = dict(API_TEST_HEADERS)


def _tao(client, **ghi_de):
    than = {"prospect_name": "Công ty May Hưng Thịnh", "contact_name": "Chị Lan",
            "contact_phone": "0901", "source": "phone", "route_id": "RT-T1",
            "cargo_type": "Vải cuộn", "est_weight_kg": 12000, "est_trips_per_month": 8,
            "notes": "Khách hỏi giá tuyến VSIP"}
    than.update(ghi_de)
    r = client.post("/api/crm/opportunities", json=than, headers=GIO)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_ghi_nhan_co_hoi_khach_moi_va_doi_giai_doan(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    o = _tao(client)
    assert o["id"].startswith("LEAD-") and o["stage"] == "new"
    assert o["customer_id"] is None and o["customer_name"] == "Công ty May Hưng Thịnh"

    # quoted / won khong dat tay
    for gd in ("quoted", "won"):
        r = client.put(f"/api/crm/opportunities/{o['id']}/stage",
                       json={"stage": gd, "expected_version": o["version"]}, headers=GIO)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "CRM_STAGE_TRANSITION_INVALID", r.text

    r = client.put(f"/api/crm/opportunities/{o['id']}/stage",
                   json={"stage": "contacted", "expected_version": o["version"]}, headers=GIO)
    assert r.status_code == 200 and r.json()["data"]["stage"] == "contacted"
    v = r.json()["data"]["version"]

    # mat phai co ly do
    r = client.put(f"/api/crm/opportunities/{o['id']}/stage",
                   json={"stage": "lost", "expected_version": v}, headers=GIO)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "CRM_LOST_REASON_REQUIRED"
    r = client.put(f"/api/crm/opportunities/{o['id']}/stage",
                   json={"stage": "lost", "expected_version": v, "lost_reason": "Chọn đối thủ giá thấp hơn"}, headers=GIO)
    assert r.status_code == 200 and r.json()["data"]["lost_reason"].startswith("Chọn")

    kpi = client.get("/api/crm/opportunities/summary", headers=GIO).json()["data"]
    assert kpi["by_stage"]["lost"] >= 1


def test_lap_bao_gia_tu_co_hoi_roi_khach_chap_nhan_thi_chot(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    o = _tao(client, prospect_name="Nidec Lào", est_weight_kg=19000, est_trips_per_month=16)

    r = client.post(f"/api/crm/opportunities/{o['id']}/quotation",
                    json={"expected_version": o["version"]}, headers=GIO)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    qid = d["quotation"]["id"]
    assert d["stage"] == "quoted" and d["quotation_id"] == qid
    assert d["customer_id"], "khách chưa có danh mục thì phải được tạo khi lập báo giá"

    q = client.get(f"/api/quotations/{qid}/detail", headers=GIO).json()["data"]
    assert q["canonical_status"] == "draft"
    assert q["customer_id"] == d["customer_id"] and q["route_id"] == "RT-T1"
    assert float(q["weight_kg"]) == 19000.0 and int(q.get("trips_per_month") or 0) == 16
    assert o["id"] in (q.get("notes_internal") or ""), "ghi chú nội bộ phải nói báo giá từ cơ hội nào"

    # lap lan hai bi chan
    r = client.post(f"/api/crm/opportunities/{o['id']}/quotation",
                    json={"expected_version": d["version"]}, headers=GIO)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "OPPORTUNITY_ALREADY_QUOTED"

    # hoan thien bao gia -> gui -> khach chap nhan -> co hoi WON
    import importlib
    database = importlib.import_module("database"); models = importlib.import_module("models")
    with database.SessionLocal() as db:
        if db.get(models.VehicleType, "VT-T1") is None:
            db.add(models.VehicleType(id="VT-T1", name="Đầu kéo 20' (kiểm)", max_weight=24000,
                                      volume_capacity_m3=33, pallet_capacity=18))
            db.commit()
    hom_nay = dt.date.today()
    r = client.put(f"/api/quotations/{qid}", json={
        "vehicle_type_id": "VT-T1", "price_basis": "per_trip", "unit_price": 3_000_000,
        "total_cost": 2_000_000, "valid_to": (hom_nay + dt.timedelta(days=30)).isoformat(),
        "pickup_window_start": "2026-09-20T01:00:00+00:00", "pickup_window_end": "2026-09-20T04:00:00+00:00",
        "delivery_window_start": "2026-09-20T04:00:00+00:00", "delivery_window_end": "2026-09-20T13:00:00+00:00",
    }, headers=GIO)
    assert r.status_code == 200, r.text
    r = client.post(f"/api/quotations/{qid}/send", json={}, headers=GIO)
    assert r.status_code == 200, r.text
    r = client.post(f"/api/quotations/{qid}/accept", json={}, headers=GIO)
    assert r.status_code == 200, r.text

    o2 = client.get(f"/api/crm/opportunities/{o['id']}", headers=GIO).json()["data"]
    assert o2["stage"] == "won", o2

    # ho so khach gom dung
    hs = client.get(f"/api/crm/customers/{d['customer_id']}/profile", headers=GIO).json()["data"]
    assert hs["customer"]["name"] == "Nidec Lào"
    assert hs["summary"]["quotations_accepted"] == 1
    assert hs["summary"]["do_total"] >= 1, "chấp nhận báo giá phải đã sinh DO"
    assert any(x["id"] == o["id"] for x in hs["opportunities"])


def test_lap_bao_gia_doi_tuyen(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    o = _tao(client, route_id=None, origin_text="Kho A", destination_text="Cảng B")
    r = client.post(f"/api/crm/opportunities/{o['id']}/quotation",
                    json={"expected_version": o["version"]}, headers=GIO)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "CRM_ROUTE_REQUIRED"


def test_khach_tu_choi_bao_gia_thi_co_hoi_tu_mat(app_client, workflow_builder):
    """Đối xứng với bài chấp nhận → won: từ chối → lost, lý do lấy từ phiếu."""
    client, _, _ = app_client
    workflow_builder.master_data()
    o = _tao(client, prospect_name="Gạch Đồng Tâm Lào")
    d = client.post(f"/api/crm/opportunities/{o['id']}/quotation",
                    json={"expected_version": o["version"]}, headers=GIO).json()["data"]
    qid = d["quotation_id"]

    # chưa hết hạn, còn chờ khách -> cờ hết hạn phải TẮT
    o1 = client.get(f"/api/crm/opportunities/{o['id']}", headers=GIO).json()["data"]
    assert o1["quotation_status"] == "draft" and o1["quotation_expired"] is False

    r = client.post(f"/api/quotations/{qid}/reject",
                    json={"reason": "Khách chọn nhà xe quen, giá thấp hơn 8%"}, headers=GIO)
    assert r.status_code == 200, r.text

    o2 = client.get(f"/api/crm/opportunities/{o['id']}", headers=GIO).json()["data"]
    assert o2["stage"] == "lost", o2
    assert qid in o2["lost_reason"] and "nhà xe quen" in o2["lost_reason"]
    assert o2["version"] == o1["version"] + 1, "đổi giai đoạn phải tăng version để chống sửa chồng"

    # từ chối lần hai không được lùi thêm gì (idempotent với cơ hội)
    client.post(f"/api/quotations/{qid}/reject", json={"reason": "lặp"}, headers=GIO)
    o3 = client.get(f"/api/crm/opportunities/{o['id']}", headers=GIO).json()["data"]
    assert o3["version"] == o2["version"] and "nhà xe quen" in o3["lost_reason"]


def test_bao_gia_het_han_thi_the_co_hoi_bao_het_han(app_client, workflow_builder):
    """Hết hạn không lưu thành trạng thái, nên cơ hội cũng tính lúc đọc."""
    client, _, _ = app_client
    workflow_builder.master_data()
    o = _tao(client, prospect_name="Cà phê Paksong")
    d = client.post(f"/api/crm/opportunities/{o['id']}/quotation",
                    json={"expected_version": o["version"]}, headers=GIO).json()["data"]
    qid = d["quotation_id"]

    import importlib
    database = importlib.import_module("database"); models = importlib.import_module("models")
    hom_qua = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    with database.SessionLocal() as db:
        q = db.get(models.Quotation, qid)
        q.canonical_status = "sent"
        q.valid_to = hom_qua
        db.commit()

    o2 = client.get(f"/api/crm/opportunities/{o['id']}", headers=GIO).json()["data"]
    assert o2["stage"] == "quoted", "hết hạn KHÔNG tự đánh mất — người bán còn gia hạn được"
    assert o2["quotation_expired"] is True
    ds = client.get("/api/crm/opportunities", headers=GIO).json()["data"]
    assert any(x["id"] == o["id"] and x["quotation_expired"] for x in ds), "danh sách cũng phải mang cờ"
