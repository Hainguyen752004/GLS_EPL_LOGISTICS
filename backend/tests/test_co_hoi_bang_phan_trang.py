# -*- coding: utf-8 -*-
"""Bảng cơ hội ở quy mô lớn: máy chủ trả N thẻ đầu mỗi cột kèm số đếm thật;
danh sách phân trang; hai cột kho lọc theo số ngày; không truyền page thì vẫn
trả mảng như cũ (tương thích)."""
import datetime as dt

from conftest import API_TEST_HEADERS

GIO = dict(API_TEST_HEADERS)


def _tao(client, i, **ghi_de):
    than = {"prospect_name": "Khách %02d" % i, "source": "phone", "route_id": "RT-T1",
            "cargo_type": "Hàng %d" % i, "est_weight_kg": 1000 * (i + 1), "est_trips_per_month": 2, "owner": "sales-%d" % (i % 2)}
    than.update(ghi_de)
    r = client.post("/api/crm/opportunities", json=than, headers=GIO)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_bang_theo_cot_chi_tai_n_the_nhung_dem_du(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    ds = [_tao(client, i) for i in range(25)]
    # 3 cơ hội có hẹn TRỄ -> phải nằm đầu cột "new"
    tre = (dt.datetime.utcnow() - dt.timedelta(hours=2)).isoformat() + "Z"
    for o in ds[20:23]:
        r = client.put(f"/api/crm/opportunities/{o['id']}", json={"expected_version": o["version"], "next_action_at": tre}, headers=GIO)
        assert r.status_code == 200, r.text

    b = client.get("/api/crm/opportunities/board?per_col=10", headers=GIO).json()["data"]
    new = b["columns"]["new"]
    assert new["count"] == 25 and len(new["items"]) == 10, "đếm đủ 25 nhưng chỉ tải 10 thẻ"
    assert {x["id"] for x in new["items"][:3]} == {o["id"] for o in ds[20:23]}, "trễ hẹn phải lên đầu"
    assert new["kg_per_month"] == sum(1000 * (i + 1) * 2 for i in range(25))
    assert set(b["owners"]) == {"sales-0", "sales-1"}

    # phân trang: trang 3 cỡ 10 còn 5
    r = client.get("/api/crm/opportunities?stage=new&page=3&page_size=10&sort=urgency", headers=GIO).json()["data"]
    assert r["total"] == 25 and len(r["items"]) == 5 and r["page"] == 3
    # lọc người theo trên bảng và danh sách phải cùng số
    b2 = client.get("/api/crm/opportunities/board?owner=sales-1", headers=GIO).json()["data"]
    r2 = client.get("/api/crm/opportunities?stage=new&page=1&page_size=200&owner=sales-1", headers=GIO).json()["data"]
    assert b2["columns"]["new"]["count"] == r2["total"] == 12
    # không truyền page -> mảng như cũ
    cu = client.get("/api/crm/opportunities", headers=GIO).json()["data"]
    assert isinstance(cu, list) and len(cu) == 25


def test_cot_kho_loc_theo_so_ngay(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    o = _tao(client, 1)
    r = client.put(f"/api/crm/opportunities/{o['id']}/stage", json={"stage": "lost", "expected_version": o["version"], "lost_reason": "thử"}, headers=GIO)
    assert r.status_code == 200, r.text
    # lùi updated_at về 40 ngày trước
    import importlib
    database = importlib.import_module("database"); models = importlib.import_module("models")
    with database.SessionLocal() as db:
        x = db.get(models.CoHoiKhach, o["id"]); x.updated_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=40); db.commit()
    assert client.get("/api/crm/opportunities/board?since_days=7", headers=GIO).json()["data"]["columns"]["lost"]["count"] == 0
    assert client.get("/api/crm/opportunities/board?since_days=0", headers=GIO).json()["data"]["columns"]["lost"]["count"] == 1
    # cột đang làm việc KHÔNG bị since_days cắt
    o2 = _tao(client, 2)
    with database.SessionLocal() as db:
        x = db.get(models.CoHoiKhach, o2["id"]); x.updated_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=40); db.commit()
    assert client.get("/api/crm/opportunities/board?since_days=7", headers=GIO).json()["data"]["columns"]["new"]["count"] == 1
