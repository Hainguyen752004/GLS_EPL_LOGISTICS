# -*- coding: utf-8 -*-
"""Thử 05/10 — bàn giao phiếu đề nghị xuất kho nhiên liệu (PLNL) cho kho QLSX anh Tune (routes/ban_giao_dau.py,
services/ban_giao_dau.py) trên bản sao _d7. MỌI THỨ trong một giao dịch ngoài (phiên chạy savepoint), cuối ROLLBACK: không ghi gì
vào d7. Gọi qua FastAPI TestClient (khoá máy thật: đặt khoá thử TRONG giao dịch), không chạy sự kiện khởi động, không gọi mạng.

    python kiem/thu_ban_giao_dau.py

d7 không còn tờ PLNL chờ cấp → trong giao dịch đặt lại 3 tờ đã cấp về "chờ" (gỡ stock_move_id dòng dầu kho của điểm đổ đó):
  G4-0004 (xe nhà, chưa khoá) · G4-0002 (xe thuê, mở khoá trong giao dịch) · G4-0005 (xe nhà, ĐANG khoá → không cấp được).
"""
import os
import sys

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from services import ban_giao_dau as BGD                # noqa: E402
from services import but_toan_cho as BTC                # noqa: E402
from services import day_ke_toan as DK                  # noqa: E402

KQ = []
KHOA = "khoa-thu-ban-giao-dau-0510"


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


def dat_cho(db, doc_no, mo_khoa=False):
    """Tờ PLNL `doc_no` về "chờ" trong giao dịch: gỡ dấu cấp + stock_move_id các dòng dầu kho của đúng điểm đổ."""
    from services import gia_von as GV
    v = db.query(M.Voucher).filter(M.Voucher.doc_no == doc_no).one()
    p = db.get(M.Trip, v.trip_id)
    goc = GV.kho_goc(db)
    for d in db.query(M.TripExpense).filter(M.TripExpense.trip_id == p.id, M.TripExpense.section == "fuel",
                                            M.TripExpense.source == "kho").all():
        if (d.place_id or goc) == v.place_id:
            d.stock_move_id = None
    v.status, v.granted_by, v.granted_at, v.granted_qty, v.granted_note = "cho", None, None, None, None
    if mo_khoa:
        p.locked = False
    db.commit()
    return v, p


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))   # 8011 chạy song song: chờ khoá quá 10 giây thì hỏng, không treo
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)
    def _db():
        # như database.get_db: hết request thì phiên đóng — phần chưa commit (route ném lỗi) bị bỏ
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    H = {"Authorization": "Bearer " + KHOA}
    try:
        DK.dat_cau_hinh(db, "token_nhan_qlsx", KHOA)
        db.commit()
        v4, p4 = dat_cho(db, "PLNL-G4-0004-10/EPL-1")
        v2, p2 = dat_cho(db, "PLNL-G4-0002-10/EPL-1", mo_khoa=True)
        v5, p5 = dat_cho(db, "PLNL-G4-0005-10/EPL-1")

        print("== 1. khoá máy")
        r = c.get("/api/handover/fuel-vouchers")
        dung(r.status_code == 401, "không khoá → 401", r.status_code)
        r = c.get("/api/handover/fuel-vouchers", headers={"Authorization": "Bearer sai"})
        dung(r.status_code == 401, "sai khoá → 401", r.status_code)

        print("== 2. danh sách / chi tiết")
        r = c.get("/api/handover/fuel-vouchers", headers=H)
        d = r.json()["data"]
        so = {x["voucher_no"] for x in d["items"]}
        dung(r.status_code == 200 and {v4.doc_no, v2.doc_no, v5.doc_no} <= so and d["total"] >= 3, "mặc định chờ cấp: có 3 tờ vừa đặt",
             (d["total"], sorted(so)))
        r = c.get("/api/handover/fuel-vouchers", params={"q": "G4-0004-10", "status": "cho"}, headers=H)
        dung([x["voucher_no"] for x in r.json()["data"]["items"]] == [v4.doc_no], "tìm theo số DO", r.json()["data"]["total"])
        r = c.get("/api/handover/fuel-vouchers", params={"warehouse_code": "KHO-XE-VN"}, headers=H)
        dung(all(x["warehouse_code"] == "KHO-XE-VN" for x in r.json()["data"]["items"]), "lọc theo mã kho", r.json()["data"]["total"])
        r = c.get("/api/handover/fuel-vouchers", params={"status": "xyz"}, headers=H)
        dung(r.status_code == 422, "status lạ → 422", r.status_code)
        r = c.get("/api/handover/fuel-vouchers/" + v4.id, headers=H)
        x = r.json()["data"]
        dung(x["source_ref"] == "PLNL-G4-0004-10.EPL-1" and x["purpose"] == "INTERNAL" and x["vehicle_kind"] == "OWN"
             and x["warehouse_code"] == "KHO-TB" and x["item_code"] == "EPLNL-diesel" and abs(x["qty_l"] - 100) < 1e-9
             and x["can_issue"] and x["partner_code"] is None and x["do_code"] == "G4-0004-10/EPL" and x["do_id"] == "EPLLAO-" + p4.id,
             "xe nhà: SourceRef, INTERNAL, kho KHO-TB, EPLNL-diesel, 100 L, cấp được",
             {k: x[k] for k in ("source_ref", "purpose", "warehouse_code", "item_code", "qty_l", "can_issue", "driver_code")})
        tx = db.get(M.DoiTuongTune, ("tai_xe", p4.driver_id))
        dung(x["driver_code"] == (tx.object_no if tx else None), "mã tài xế chỉ khi đã có bên kế toán (doi_tuong_tune)", x["driver_code"])
        x2 = c.get("/api/handover/fuel-vouchers/" + v2.id, headers=H).json()["data"]
        dung(x2["purpose"] == "PARTNER_SALE" and x2["vehicle_kind"] == "HIRED" and x2["partner_code"] == "EPLCX-" + p2.owner_id
             and x2["owner_id"] == p2.owner_id and x2["can_issue"], "xe thuê: PARTNER_SALE, đối tác EPLCX-<chủ xe>", x2["partner_code"])
        x5 = c.get("/api/handover/fuel-vouchers/" + v5.id, headers=H).json()["data"]
        dung(not x5["can_issue"] and "khoá" in (x5["block_reason"] or ""), "DO đang khoá → không cấp được, có lý do", x5["block_reason"])
        r = c.get("/api/handover/fuel-vouchers/khong-co", headers=H)
        dung(r.status_code == 404, "tờ không có → 404", r.status_code)

        print("== 3. báo đã cấp — kiểm đầu vào")
        url4 = "/api/handover/fuel-vouchers/%s/issued" % v4.id
        tot = {"source_ref": x["source_ref"], "stock_doc_no": "1368-XTH-261005-0001", "stock_doc_id": 99001, "qty_l": 100,
               "issued_by": "tune", "lines": [{"item_code": "EPLNL-diesel", "qty": 100, "unit_cost": 26500}]}
        for ten, sua, ma, http in (("sai SourceRef", {"source_ref": "PLNL-khac"}, "SAI_SOURCE_REF", 409),
                                   ("thiếu số phiếu kho", {"stock_doc_no": " "}, "THIEU_SO_PHIEU_KHO", 422),
                                   ("vượt số đề nghị", {"qty_l": 100.5}, "VUOT_DE_NGHI", 422),
                                   ("cấp thiếu không lý do", {"qty_l": 80}, "THIEU_LY_DO", 422),
                                   ("số lít 0", {"qty_l": 0}, "SO_LIT_SAI", 422),
                                   ("thiếu giá vốn", {"lines": []}, "THIEU_GIA_VON", 422),
                                   ("giá vốn âm", {"lines": [{"item_code": "EPLNL-diesel", "unit_cost": -1}]}, "GIA_VON_SAI", 422)):
            r = c.post(url4, json=dict(tot, **sua), headers=H)
            dung(r.status_code == http and r.json()["detail"]["ma"] == ma, ten, (r.status_code, r.json().get("detail")))
        db.expire_all()
        dung(db.get(M.Voucher, v4.id).status == "cho", "lỗi đầu vào không ghi gì", db.get(M.Voucher, v4.id).status)

        print("== 4. báo đã cấp — xe nhà đủ số")
        r = c.post(url4, json=tot, headers=H)
        x = r.json().get("data") or {}
        dung(r.status_code == 200 and x.get("status") == "da_cap" and x.get("replayed") is False
             and x.get("stock_doc_no") == "1368-XTH-261005-0001" and abs((x.get("granted_qty") or 0) - 100) < 1e-9,
             "ghi đã cấp, số phiếu kho, 100 L", (r.status_code, r.json().get("message")))
        db.expire_all()
        dong = [d for d in db.query(M.TripExpense).filter(M.TripExpense.trip_id == p4.id, M.TripExpense.section == "fuel").all()
                if d.stock_move_id == "qlsx:1368-XTH-261005-0001"]
        dung(dong and all(abs((d.unit_price or 0) - 26500) < 1e-9 and d.currency == "LAK" for d in dong),
             "dòng dầu: stock_move_id qlsx:<số phiếu>, đơn giá = giá vốn kho QLSX", [(d.qty, d.unit_price) for d in dong])
        bt = BTC.dong_xuat_kho(db, db.get(M.Trip, p4.id))
        k = (BTC.XUAT_NOI_BO, "dau:qlsx:1368-XTH-261005-0001")
        tien = sum(z["tien"] for z in bt.get(k, (None, [], None))[1])
        dung(k in bt and tien == 2650000 and all((z["no"], z["co"]) == ("625", "1371") for z in bt[k][1]),
             "bút toán khoá phiếu: xuất nội bộ 625/1371 = 100 × 26.500", (sorted(bt), tien))
        ds = c.get("/api/handover/fuel-vouchers", headers=H).json()["data"]["items"]
        dung(v4.doc_no not in {z["voucher_no"] for z in ds}, "đã cấp thì rời danh sách chờ")

        print("== 5. gọi lại")
        r = c.post(url4, json=tot, headers=H)
        dung(r.status_code == 200 and r.json()["data"]["replayed"] is True, "cùng số phiếu kho → trả lại, replayed", r.json().get("message"))
        r = c.post(url4, json=dict(tot, stock_doc_no="1368-XTH-261005-0099"), headers=H)
        dung(r.status_code == 409 and r.json()["detail"]["ma"] == "DA_CAP", "khác số phiếu kho → 409 DA_CAP", r.status_code)

        print("== 6. xe thuê cấp thiếu có lý do")
        url2 = "/api/handover/fuel-vouchers/%s/issued" % v2.id
        r = c.post(url2, json={"source_ref": x2["source_ref"], "stock_doc_no": "1368-XTH-261005-0002", "qty_l": 120,
                               "note": "Bồn còn ít", "issued_by": "tune", "lines": [{"item_code": "EPLNL-diesel", "unit_cost": 26400}]},
                   headers=H)
        y = r.json().get("data") or {}
        db.expire_all()
        dong2 = [d for d in db.query(M.TripExpense).filter(M.TripExpense.trip_id == p2.id, M.TripExpense.section == "fuel").all()
                 if d.stock_move_id == "qlsx:1368-XTH-261005-0002"]
        dung(r.status_code == 200 and y.get("granted_note") == "Bồn còn ít" and len(dong2) == 1 and abs(dong2[0].qty - 120) < 1e-9,
             "120/150 L: lý do ghi lại, dòng phiếu theo số thật", (r.status_code, [(d.qty, d.unit_price) for d in dong2]))
        bt2 = BTC.dong_xuat_kho(db, db.get(M.Trip, p2.id))
        k2 = (BTC.XUAT_BAN, "dau:qlsx:1368-XTH-261005-0002")
        dung(k2 in bt2 and all((z["no"], z["co"]) == ("607", "1371") for z in bt2[k2][1])
             and sum(z["tien"] for z in bt2[k2][1]) == 3168000, "bút toán xuất bán: chỉ giá vốn 607/1371 = 120 × 26.400",
             [(z["no"], z["co"], z["tien"]) for z in bt2.get(k2, (None, [], None))[1]])

        print("== 7. DO đang khoá / tờ đã huỷ")
        r = c.post("/api/handover/fuel-vouchers/%s/issued" % v5.id,
                   json={"source_ref": x5["source_ref"], "stock_doc_no": "1368-XTH-261005-0003", "qty_l": 100,
                         "lines": [{"item_code": "EPLNL-diesel", "unit_cost": 26500}]}, headers=H)
        db.expire_all()
        dung(r.status_code == 409 and db.get(M.Voucher, v5.id).status == "cho", "DO khoá: lệch bút toán khoá → 409, không ghi",
             (r.status_code, (r.json().get("detail") or {}).get("ma")))
        v5b = db.get(M.Voucher, v5.id)
        v5b.status = "huy"
        db.commit()
        r = c.post("/api/handover/fuel-vouchers/%s/issued" % v5.id,
                   json={"source_ref": x5["source_ref"], "stock_doc_no": "1368-XTH-261005-0003", "qty_l": 100,
                         "lines": [{"item_code": "EPLNL-diesel", "unit_cost": 26500}]}, headers=H)
        dung(r.status_code == 409 and r.json()["detail"]["ma"] == "DA_HUY", "tờ đã huỷ → 409 DA_HUY", r.status_code)

        print("== 8. xoá phiếu đã cấp ở kho QLSX bị chặn")
        from routes import phieu as RP
        import types
        sep = types.SimpleNamespace(role="admin", full_name="Thử admin", username="thu_admin", id="thu", driver_id=None)
        try:
            RP.xoa_phieu(p4.id, db=db, user=sep) if hasattr(RP, "xoa_phieu") else None
            dung(False, "xoá phiếu có dầu cấp ở kho QLSX phải bị chặn")
        except Exception as e:                                   # noqa: BLE001
            ma = (getattr(e, "detail", None) or {}).get("ma") if isinstance(getattr(e, "detail", None), dict) else str(e)
            dung(ma == "DA_CAP_KHO_QLSX", "xoá phiếu (Sếp) → 409 DA_CAP_KHO_QLSX", ma)

        print("== 9. kho QLSX huỷ phiếu xuất → mở lại phiếu đề nghị (/cancelled)")
        sr4 = "PLNL-G4-0004-10.EPL-1"
        r = c.get("/api/handover/fuel-vouchers/" + sr4, headers=H)
        dung(r.status_code == 200 and r.json()["data"]["voucher_id"] == v4.id, "chi tiết theo SourceRef", r.status_code)
        url9 = "/api/handover/fuel-vouchers/%s/cancelled" % sr4
        r = c.post(url9, json={"source_ref": sr4, "stock_doc_no": "1368-XTH-261005-0099"}, headers=H)
        dung(r.status_code == 409 and r.json()["detail"]["ma"] == "KHAC_PHIEU_KHO", "khác số phiếu kho → 409 KHAC_PHIEU_KHO", r.status_code)
        r = c.post(url9, json={"source_ref": "PLNL-khac"}, headers=H)
        dung(r.status_code == 409 and r.json()["detail"]["ma"] == "SAI_SOURCE_REF", "SourceRef không khớp → 409", r.status_code)
        db.get(M.Trip, p4.id).locked = True
        db.commit()
        r = c.post(url9, json={"source_ref": sr4, "stock_doc_no": "1368-XTH-261005-0001"}, headers=H)
        db.expire_all()
        dung(r.status_code == 409 and r.json()["detail"]["ma"] == "DA_KHOA" and "mở khoá DO" in r.json()["detail"]["loi"]
             and db.get(M.Voucher, v4.id).status == "da_cap", "DO đã khoá → 409 DA_KHOA, không mở lại", r.json().get("detail"))
        db.get(M.Trip, p4.id).locked = False
        db.commit()
        r = c.post(url9, json={"source_ref": sr4, "stock_doc_no": "1368-XTH-261005-0001", "reason": "Xoá phiếu trên màn kho Web",
                               "cancelled_by": "tune"}, headers=H)
        x9 = r.json().get("data") or {}
        db.expire_all()
        dong9 = [d for d in db.query(M.TripExpense).filter(M.TripExpense.trip_id == p4.id, M.TripExpense.section == "fuel").all()
                 if d.place_id == v4.place_id or d.place_id is None]
        dung(r.status_code == 200 and x9.get("status") == "cho" and x9.get("replayed") is False and x9.get("can_issue")
             and db.get(M.Voucher, v4.id).granted_qty is None
             and all(d.stock_move_id is None and (d.unit_price or 0) == 0 for d in dong9 if d.source == "kho"),
             "mở lại: tờ chờ cấp, gỡ stock_move_id + đơn giá dòng dầu", (r.status_code, [(d.stock_move_id, d.unit_price) for d in dong9]))
        nk = db.query(M.TripLog).filter(M.TripLog.trip_id == p4.id, M.TripLog.action.like("Kho QLSX huỷ phiếu xuất%")).all()
        dung(len(nk) == 1 and "1368-XTH-261005-0001" in nk[0].action and nk[0].user_name == "tune", "ghi nhật ký phiếu",
             [z.action for z in nk])
        dung(not any(k[1].startswith("dau:qlsx:") for k in BTC.dong_xuat_kho(db, db.get(M.Trip, p4.id))),
             "bút toán xuất kho của lần cấp đã bỏ")
        ds = c.get("/api/handover/fuel-vouchers", headers=H).json()["data"]["items"]
        dung(v4.doc_no in {z["voucher_no"] for z in ds}, "tờ về lại danh sách chờ cấp")
        r = c.post(url9, json={"source_ref": sr4, "stock_doc_no": "1368-XTH-261005-0001"}, headers=H)
        dung(r.status_code == 200 and r.json()["data"]["replayed"] is True, "báo lại → replayed, không đổi gì", r.json().get("message"))
        r = c.post("/api/handover/fuel-vouchers/%s/cancelled" % v2.id, json={"stock_doc_no": "1368-XTH-261005-0002"}, headers=H)
        db.expire_all()
        d2 = [d for d in db.query(M.TripExpense).filter(M.TripExpense.trip_id == p2.id, M.TripExpense.section == "fuel").all()
              if d.source == "kho" and (d.place_id or "") == v2.place_id]
        dung(r.status_code == 200 and d2 and abs(d2[0].qty - 150) < 1e-9, "xe thuê cấp thiếu 120 → mở lại, dòng về 150 L đề nghị",
             (r.status_code, [(d.qty, d.stock_move_id) for d in d2]))
        v1 = db.query(M.Voucher).filter(M.Voucher.doc_no == "PLNL-G4-0001-10/EPL-1").one()
        r = c.post("/api/handover/fuel-vouchers/%s/cancelled" % v1.id, json={}, headers=H)
        dung(r.status_code == 409 and r.json()["detail"]["ma"] == "KHONG_PHAI_KHO_QLSX", "tờ cấp ở kho tạm → 409 KHONG_PHAI_KHO_QLSX",
             r.status_code)
        r = c.post("/api/handover/fuel-vouchers/PLNL-khong-co/cancelled", json={}, headers=H)
        dung(r.status_code == 404, "SourceRef không có → 404", r.status_code)
    finally:
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("đã ROLLBACK — bản sao d7 không đổi")
    print("TỔNG: %d/%d đạt" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
