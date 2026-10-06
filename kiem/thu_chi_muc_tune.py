# -*- coding: utf-8 -*-
"""Thử CHI MỤC V–VI Ở HỆ KẾ TOÁN anh Tune (chủ dự án 01/10/2026 — bỏ trang kế toán tạm, thay tờ PC_SC).

    python kiem/thu_chi_muc_tune.py

06/10 (anh Hải duyệt): chạy TRONG TIẾN TRÌNH (kiem/_tien_trinh_tune.py) — trước đây cần máy thử 8014 nối API 5090 thật và tạo
rồi rút phiếu chi thật bên DB demo. Nay: TestClient trên bản sao _d7, mỗi phần một giao dịch ngoài cuối ROLLBACK; API phiếu chi
bên kế toán GIẢ (GiaKeToan — lưu đúng thân save-and-commit, đọc / danh sách / xoá như API thật, "thủ quỹ ghi sổ" / "xoá tay"
là thao tác trong bài); mọi lời gọi mạng bị chặn; xe / tài xế / khách / chủ xe thử TẠO MỚI trong giao dịch.

Kịch bản (giữ như bản 01/10):
  1. Xe nhà, mục V có garage quỹ trả ngay 300.000 (+ lốp nợ cửa hàng nếu d7 có nhà cung cấp lốp — không qua quỹ); mục VI một
     khoản tiền mặt. KT Chi phí ghi sổ mục V → phiếu chi "Chi khác" (DOTY 60) bên kế toán, chưa ghi sổ, đối tượng tài xế
     EPLTX-…, Nợ 614 / Có 1011, đúng 300.000, tham chiếu PCSC-V-<số phiếu>-1. Quỹ bấm Chi ở trang này → 409 nói số phiếu bên
     đó. Bãi xem được trạng thái, không thấy tiền. Ghi sổ mục VI (không có khoản quỹ trả) → không lập phiếu; Quỹ chi mục VI
     trên trang này như cũ.
  2. (đóng vai thủ quỹ) ghi sổ phiếu bên kế toán → trang này hỏi lại → mục V "đã chi", nhật ký "(hệ kế toán)"; gửi lại không
     tạo phiếu thứ hai; xoá phiếu đã chi bên kế toán → 409.
  3. Xe thuê: Nợ 4022 / Có 1011, đối tượng chủ xe EPLCX-…. Phiếu bên kế toán bị XOÁ TAY → hỏi lại: PHIEU_CHI_MAT (không kẹt
     "chờ chi") → gửi lại lập phiếu mới. Có khoản sửa mới (mục V mở lại) → phiếu chờ bị rút; ghi sổ lại → lần 2, đủ hai khoản.
  4. Phân quyền đường mới theo vai. 5. Xoá phiếu → rút phiếu chi bên kế toán.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _tien_trinh_tune as TT                           # noqa: E402 — chặn mạng, khung giao dịch ROLLBACK, API kế toán giả

import models as M                                      # noqa: E402

dung, ma, cau = TT.dung, TT.ma, TT.cau
VAI = {"admin": "admin", "ketoan": "acct", "ketoancp": "expacct", "khonl": "fuel", "khotb": "depot", "khopt": "parts",
       "totsua": "repair", "quyvc": "treasury", "quytb": "cash", "doanhthu": "rev", "thabok": "yard", "tx01": "driver"}
GIA = TT.GiaKeToan()
TT.gan_ke_toan(GIA)


def phai(s, mong, buoc, g=None):
    if s != mong:
        raise AssertionError("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, str(g)[:400]))
    print("  ✓ %s %s" % (buoc, s))


def phieu_kt(rid):
    r = GIA.goi("GET", "/api/v1/accounting/cmpayment-receipt/%s?voucherType=CMP" % rid) or {}
    return r.get("Master") or {}, r.get("Entries") or []


def lap(ca, so, cong_ty, xe, tai_xe, kh, ncc):
    dong = [{"section": "repair", "item_name": "thử CMT: garage thay bạc đạn", "qty": 1, "unit_price": 300000, "currency": "LAK", "source": "mua"},
            {"section": "other", "item_key": "x_misc", "qty": 1, "unit_price": 50000, "currency": "LAK"}]
    if "x_tire" in ncc:
        dong.append({"section": "repair", "item_key": "x_tire", "qty": 1, "unit_price": 900000, "currency": "LAK", "source": "mua"})
    s, p = ca.goi("/api/trips", {"doc_no": so, "kind": "giao", "company": cong_ty, "vehicle_id": xe.id, "driver_id": tai_xe.id,
                                 "customer_id": kh.id, "doc_date": TT.dt.date.today().isoformat(), "expenses": dong}, "admin")
    phai(s, 200, "Sếp lập phiếu %s (%s)" % (so, "xe thuê" if cong_ty == "joint" else "xe nhà"), p)
    return p["id"]


def duyet(ca, pid, muc, *hd):
    g = None
    for h, vai in (("send", "admin"), ("verify", "ketoancp"), ("book", "ketoancp")):
        if h in hd:
            s, g = ca.goi("/api/trips/%s/sections/%s/%s" % (pid, muc, h), {}, vai)
            phai(s, 200, "mục %s: %s (%s)" % ({"repair": "V", "other": "VI"}[muc], h, vai), g)
    return g


def phan_1_2(ca, d, ncc):
    so1 = "%s-1/EPL" % d.tag
    print("1. Xe nhà: ghi sổ mục V → phiếu chi \"Chi khác\" bên kế toán")
    p1 = lap(ca, so1, "EPL", d.nha, d.tx1, d.kh, ncc)
    s, g = ca.goi("/api/trips/%s/chi-muc-ke-toan" % p1, u="ketoancp")
    dung(s == 200 and g["o_ke_toan"] and not g["repair"]["lan"] and g["repair"]["tien_quy_lak"] == 300000
         and g["other"]["can_chi"] is False, "chưa ghi sổ: chưa có phiếu chi; mục V quỹ trả 300.000; mục VI không có khoản quỹ trả")
    g = duyet(ca, p1, "repair", "send", "verify", "book")
    lan = g["chi_muc_ke_toan"]["repair"]["lan"]
    r = lan[-1] if lan else {}
    dung(r.get("status") == "da_gui" and "CKH" in str(r.get("document_no") or "") and r.get("amount_lak") == 300000
         and r.get("ref_no") == "PCSC-V-%s-1" % so1 and g["sections"]["repair"] == "booked",
         "ghi sổ xong → phiếu chi chờ thủ quỹ bên kế toán, 300.000, tham chiếu PCSC-V-…-1; mục V vẫn 'đã ghi sổ'",
         "%s %s %s" % (r.get("status"), r.get("document_no"), r.get("ref_no")))
    rid = r.get("real_id")
    m, en = phieu_kt(rid)
    dung(m.get("STATUS") == 1 and m.get("DOTY") == 60 and m.get("REFDOCUMENTNO") == r.get("ref_no") and round(m.get("AMOUNT") or 0) == 300000,
         "bên kế toán: phiếu \"Chi khác\" (DOTY 60), chưa ghi sổ, đúng tham chiếu, 300.000",
         "%s · DOTY %s · %s" % (m.get("STATUS"), m.get("DOTY"), m.get("REFDOCUMENTNO")))
    nk = [(e.get("ET_DEBTORACCOUNT"), e.get("ET_CREDITACCOUNT")) for e in en]
    dung(nk == [("614", "1011")], "định khoản Nợ 614 / Có 1011 (xe nhà, sửa chữa), MỘT dòng — lốp nợ cửa hàng không qua quỹ", nk)
    dung(GIA.so_doi_tuong(m.get("OBJECTID")) == "EPLTX-" + d.tx1.id and GIA.duong.get("EPLTX-" + d.tx1.id) == "staff",
         "đối tượng: tài xế EPLTX-… (danh mục nhân viên bên kế toán)", GIA.so_doi_tuong(m.get("OBJECTID")))
    s, g = ca.goi("/api/trips/%s/chi-muc-ke-toan" % p1, u="thabok")
    dung(s == 200 and g["repair"]["lan"][-1]["amount_lak"] is None and "tien_quy_lak" not in g["repair"],
         "Bãi xem được trạng thái, không thấy số tiền")
    s, g = ca.goi("/api/trips/%s/sections/repair/pay" % p1, {}, "quytb")
    dung(s == 409 and ma(g) == "CHI_O_KE_TOAN" and (r.get("document_no") or "~") in cau(g),
         "Quỹ bấm Chi mục V → 409, câu báo nói số phiếu chi bên kế toán", cau(g)[:100])
    g = duyet(ca, p1, "other", "send", "verify", "book")
    dung(not g["chi_muc_ke_toan"]["other"]["lan"], "ghi sổ mục VI (không có khoản quỹ trả) → không lập phiếu chi bên kế toán")
    s, g = ca.goi("/api/trips/%s/sections/other/pay" % p1, {}, "quytb")
    dung(s == 200 and g["sections"]["other"] == "paid", "Quỹ chi mục VI trên trang này như cũ (không có tiền quỹ chi)", s)

    print("2. Thủ quỹ ghi sổ bên kế toán → mục V đã chi")
    GIA.ghi_so(rid)
    s, g = ca.goi("/api/trips/%s/chi-muc-ke-toan?cap_nhat=1" % p1, u="quytb")
    r = g["repair"]["lan"][-1]
    dung(s == 200 and r["status"] == "da_chi" and r["post_by"] and g["repair"]["muc"] == "paid" and g["repair"]["tien_con_lak"] == 0,
         "hỏi lại → phiếu đã ghi sổ, mục V 'đã chi', không còn khoản phải chi", "%s · %s" % (r["status"], r["post_by"]))
    s, p = ca.goi("/api/trips/%s" % p1, u="admin")
    dung(any(l["action"] == "sec_repair:pay" and "(hệ kế toán)" in (l["user"] or "") for l in p["logs"]),
         "nhật ký: 'chi mục V' bởi thủ quỹ (hệ kế toán)")
    s, g = ca.goi("/api/trips/%s/chi-muc-ke-toan/repair" % p1, {}, "ketoancp")
    dung(s == 200 and len(g["lan"]) == 1 and len(GIA.con(r["obj_id"], r["ref_no"])) == 1,
         "gửi lại khi đã chi → không tạo phiếu thứ hai bên kế toán")
    s, g = ca.goi("/api/trips/%s" % p1, u="admin", method="DELETE")
    dung(s == 409 and ma(g) == "DA_CHI_O_KE_TOAN", "Sếp xoá phiếu đã chi ở hệ kế toán → 409 (đối soát bên đó trước)", ma(g))


def phan_3_4_5(ca, d, ncc):
    so2 = "%s-2/EPL" % d.tag
    print("3. Xe thuê: phiếu bên kế toán bị xoá tay · mục mở lại · xoá phiếu")
    p2 = lap(ca, so2, "joint", d.thue, d.tx2, d.kh, ncc)
    g = duyet(ca, p2, "repair", "send", "verify", "book")
    r = g["chi_muc_ke_toan"]["repair"]["lan"][-1]
    m, en = phieu_kt(r["real_id"])
    nk = [(e.get("ET_DEBTORACCOUNT"), e.get("ET_CREDITACCOUNT")) for e in en]
    dung(r["status"] == "da_gui" and nk == [("4022", "1011")], "xe thuê: Nợ 4022 (trừ vào tiền trả chủ xe) / Có 1011", nk)
    dung(GIA.so_doi_tuong(m.get("OBJECTID")) == "EPLCX-" + d.chu.id and GIA.duong.get("EPLCX-" + d.chu.id) == "suppliers",
         "đối tượng là chủ xe (EPLCX-…, danh mục nhà cung cấp), không phải tài xế", GIA.so_doi_tuong(m.get("OBJECTID")))
    GIA.xoa_tay(r["real_id"])
    s, g = ca.goi("/api/trips/%s/chi-muc-ke-toan?cap_nhat=1" % p2, u="ketoancp")
    r2 = g["repair"]["lan"][-1]
    dung(r2["status"] == "loi" and r2["error_code"] == "PHIEU_CHI_MAT", "hỏi lại → PHIEU_CHI_MAT, không kẹt 'chờ chi'",
         (r2.get("error_message") or "")[:90])
    s, g = ca.goi("/api/trips/%s/chi-muc-ke-toan/repair" % p2, {}, "ketoancp")
    r3 = (g.get("lan") or [{}])[-1]
    dung(s == 200 and r3.get("status") == "da_gui" and r3.get("real_id") and r3["real_id"] != r["real_id"] and r3["lan"] == 1,
         "gửi lại → lập phiếu mới bên kế toán", "%s → %s" % (r["document_no"], r3.get("document_no")))
    s, g = ca.goi("/api/trips/%s/events" % p2, {"kind": "repair", "incident_type": "breakdown",
                                                "repair": {"source": "mua", "item_name": "thử CMT: thay dây curoa", "qty": 1,
                                                           "unit_price": 120000}}, "totsua")
    phai(s, 200, "Tổ sửa chữa khai thêm khoản sửa (mục V mở lại)", g)
    r4 = g["chi_muc_ke_toan"]["repair"]["lan"][-1]
    dung(g["sections"]["repair"] == "entered" and r4["status"] == "huy" and not GIA.con(r3["obj_id"], r3["ref_no"]),
         "mục V mở lại → phiếu chi chờ bên kế toán được RÚT (không để thủ quỹ chi theo số cũ)")
    g = duyet(ca, p2, "repair", "verify", "book")
    r5 = g["chi_muc_ke_toan"]["repair"]["lan"][-1]
    dung(r5["status"] == "da_gui" and r5["lan"] == 2 and r5["amount_lak"] == 420000 and r5["ref_no"].endswith("-2"),
         "ghi sổ lại → lần 2, đủ hai khoản 420.000", "%s %s" % (r5["ref_no"], r5["amount_lak"]))
    so_dong = len(GIA.than(r5["real_id"])["Entries"])
    dung(so_dong == 2, "phiếu lần 2 hai dòng định khoản (mỗi khoản quỹ trả một dòng)", so_dong)

    print("4. Phân quyền đường mới")
    for u, vai in VAI.items():
        s, g = ca.goi("/api/trips/%s/chi-muc-ke-toan" % p2, u=u)
        mong = 403 if vai in ("driver", "depot", "parts", "repair") else 200
        dung(s == mong, "GET chi-muc-ke-toan — %-8s (%s) → %s" % (u, vai, s))
        s, g = ca.goi("/api/trips/%s/chi-muc-ke-toan/repair" % p2, {}, u)
        dung(s == (200 if vai in ("expacct", "admin") else 403), "POST gửi lại — %-8s (%s) → %s" % (u, vai, s))
    s, g = ca.goi("/api/trips/%s/chi-muc-ke-toan/fuel" % p2, {}, "ketoancp")
    dung(s == 422, "gửi chi mục III ở đường này → 422 (chỉ mục V, VI)", s)

    print("5. Xoá phiếu → rút phiếu chi bên kế toán")
    s, g = ca.goi("/api/trips/%s" % p2, u="admin", method="DELETE")
    phai(s, 200, "Sếp xoá phiếu xe thuê", g)
    dung(not GIA.con(r5["obj_id"], r5["ref_no"]), "phiếu chi %s bên kế toán đã rút" % r5["document_no"])


def main():
    for ten, phan in (("phần 1–2 (xe nhà)", phan_1_2), ("phần 3–5 (xe thuê, quyền, xoá)", phan_3_4_5)):
        with TT.Ca(tuple(VAI)) as ca:
            d = TT.du_lieu_thu(ca.db, "CMT")
            ncc = {x for (x,) in ca.db.query(M.Supplier.item_key).filter(M.Supplier.item_key.isnot(None), M.Supplier.active.is_(True))}
            try:
                phan(ca, d, ncc)
            except AssertionError as e:
                dung(False, "%s dừng giữa chừng" % ten, e)
    TT.ket_thuc("CHI MỤC V–VI Ở HỆ KẾ TOÁN")


if __name__ == "__main__":
    main()
