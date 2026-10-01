# -*- coding: utf-8 -*-
"""Thử CHỦ XE LIÊN KẾT — danh mục, phí riêng từng chủ, trả gộp nhiều phiếu (anh Khampla C4.2 · C4.3).

    python kiem/thu_chu_xe.py [http://127.0.0.1:8010]

Kịch bản: kế toán lập chủ xe mới với phí 3 %, ngưỡng 38 t, trả gộp tháng → Bãi thêm xe liên kết gắn
chủ đó → Bãi lập hai phiếu gom bằng xe đó (phí trên phiếu tự điền 3 % / 38 t) → đi tới khoá → quỹ
trả GỘP hai phiếu một lần → một tờ PC_CX, hai phiếu đánh đã trả → trả lại thì bị chặn → dọn.

Từ 28/09 (đợt 7b) công nợ và trả chủ xe ở TRANG KẾ TOÁN (Tiền vận chuyển → Xe liên kết; EPL_KT, mặc định 8031 — máy
điều xe đang kiểm phải trỏ vào đó): bài đi qua bên đó, đọc bản chép "đã trả" trên phiếu bên này. Phiếu đã trả không xoá
được; dọn thì Sếp huỷ đợt trả bên kế toán trước.
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ke_toan as K       # noqa: E402 — bán hàng ở trang kế toán (28/09, đợt 6)

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
TOKEN = {}


def goi(duong, du_lieu=None, vai=None, method=None):
    dau = {"Content-Type": "application/json"}
    if vai:
        dau["Authorization"] = "Bearer " + TOKEN[vai]
    than = json.dumps(du_lieu).encode() if du_lieu is not None else None
    r = urllib.request.Request(GOC + duong, data=than, headers=dau,
                               method=method or ("POST" if than is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def phai(s, mong, buoc, g=None):
    dt_ = (g or {}).get("detail") if isinstance(g, dict) else None
    if dt_ is None and isinstance(g, dict) and "ma" in g:
        dt_ = g
    ma = dt_.get("ma", "") if isinstance(dt_, dict) else ""
    print("%s %-60s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def chi_tam_ung(pid, phai):
    """Quy trình: tài xế cầm tiền đi đường (mục IV "đã chi") rồi mới xuất phát / báo xe tới — từ 23/09 máy chặn
    cả hai cửa. Từ 01/10 tạm ứng chi ở hệ kế toán (kiem/thu_chi_tam_ung_ke_toan.py thử đường đó); bài này không phải về
    tạm ứng nên bước chi do SẾP chi tay — máy rút phiếu chi còn chờ bên kế toán, không để thủ quỹ chi lần nữa."""
    for hd, v in (("send", "thabok"), ("verify", "ketoancp"), ("book", "ketoancp"), ("pay", "admin")):
        s, g = goi("/api/trips/%s/sections/travel/%s" % (pid, hd), {}, vai=v)
        if s == 409 and isinstance(g, dict) and (g.get("detail") or {}).get("ma") in ("MUC_TRONG", "SAI_BUOC"):
            return          # mục IV trống, hoặc đã đi qua bước này rồi
        phai(s, 200, "mục IV: %s (%s)" % (hd, v), g)


def main():
    for u in ("thabok", "ketoan", "ketoancp", "khonl", "quyvc", "quytb", "doanhthu", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 8 vai")

    # ---------------------------------------------------------------- 0. dọn dấu vết lần chạy trước bị đứt
    s, ds = goi("/api/trips", vai="admin")
    for p in [x for x in ds if x["doc_no"] in ("THU-CX-A/EPL", "THU-CX-B/EPL")]:
        if p.get("owner_payment_id"):                  # đợt trả ở trang kế toán: Sếp huỷ trước thì phiếu mới xoá được
            K.kt("/api/xe-lien-ket/dot/%s" % p["owner_payment_id"], vai="admin", method="DELETE")
        goi("/api/trips/%s/mo-khoa" % p["id"], {}, vai="admin"); goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")
    s, bh = K.kt("/api/ban-hang", vai="ketoan")
    for b in [x for x in (bh.get("ds") or []) if x.get("note") == "thử: chủ xe mua dầu ở quầy" and x.get("status") == "issued"]:
        K.kt("/api/ban-hang/%s" % b["id"], vai="ketoan", method="DELETE")
    s, ds = goi("/api/vehicles", vai="admin")
    for x in [x for x in ds if x["truck_no"] in ("THU-CX-01", "THU-CX-02") and x["active"]]:
        goi("/api/vehicles/%s" % x["id"], {"active": False}, vai="admin", method="PUT")
    s, ds = goi("/api/owners", vai="admin")
    for x in [x for x in ds if "Chủ thử" in (x["name"] or "") and x["active"]]:
        goi("/api/owners/%s" % x["id"], {"name": x["name"], "active": False}, vai="admin", method="PUT")

    # ---------------------------------------------------------------- 1. danh mục chủ xe
    s, g = goi("/api/owners", {"name": "Chủ thử", "fee_pct": 3}, vai="thabok")
    phai(s, 403, "Bãi thêm chủ xe → bị từ chối (điều khoản hợp đồng là của kế toán)", g)
    s, chu = goi("/api/owners", {"name": "ທ້າວ ທົດສອບ (Chủ thử)", "phone": "020 1111 2222", "fee_pct": 3, "over_limit_t": 38,
                                 "over_price": 1.5, "hire_ccy": "USD", "pay_mode": "thang", "note": "thử bộ kiểm"}, vai="ketoan")
    phai(s, 200, "Kế toán lập chủ xe: phí 3 % · ngưỡng 38 t · trả gộp tháng", chu)
    s, g = goi("/api/owners", {"name": "x", "pay_mode": "tuy_y"}, vai="ketoan"); phai(s, 422, "Cách trả lạ → bị từ chối", g)
    s, g = goi("/api/owners", {"name": "x", "fee_pct": 150}, vai="ketoan"); phai(s, 422, "Phí 150 % → bị từ chối", g)
    s, ds = goi("/api/owners", vai="thabok")
    c0 = next(c for c in ds if c["id"] == chu["id"])
    assert "fee_pct" not in c0 and "cho_tra" not in c0, "Bãi không được thấy phí và số chờ trả của chủ xe: %s" % list(c0)
    print("  ✓ %-60s" % "Bãi xem danh mục chủ xe: có tên, không có phí và tiền")

    # ---------------------------------------------------------------- 2. xe liên kết gắn chủ xe
    s, xe = goi("/api/vehicles", {"truck_no": "THU-CX-01", "plate_head": "ກຂ 0001", "owner_type": "joint", "owner_id": chu["id"]}, vai="thabok")
    phai(s, 200, "Bãi thêm xe liên kết, chọn chủ xe từ danh mục", xe)
    assert xe["owner_name"] == chu["name"], "tên chủ xe phải chép từ danh mục: %s" % xe["owner_name"]
    s, g = goi("/api/vehicles", {"truck_no": "THU-CX-02", "owner_type": "joint", "owner_id": "khong-co"}, vai="thabok")
    phai(s, 422, "Chủ xe không có trong danh mục → bị từ chối", g)

    # ---------------------------------------------------------------- 3. hai phiếu gom bằng xe đó → phí tự điền theo chủ
    s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok"); s, tuyen = goi("/api/routes", vai="thabok")
    phieu = []
    for i, (so, tan) in enumerate((("THU-CX-A/EPL", 41.0), ("THU-CX-B/EPL", 39.0))):
        s, P = goi("/api/trips", {"doc_no": so, "kind": "gom", "doc_date": "2026-09-1%d" % (i + 5), "out_date": "2026-09-1%d" % (i + 5),
                                  "vehicle_id": xe["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"],
                                  "odo_out": 100, "goods": [{"goods_name": "ແຮ່ເຫຼັກ", "qty_t": tan}],
                                  "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 50, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"}]}, vai="thabok")
        phai(s, 200, "Bãi lập phiếu gom %s bằng xe của chủ thử" % so, P)
        assert P["company"] == "joint" and P["owner_id"] == chu["id"], "phiếu phải nhận chủ xe từ xe: %s" % P.get("owner_id")
        assert "fee_pct" not in P, "Bãi không được thấy phí chủ xe (nợ kỹ thuật 3.1)"
        s, P = goi("/api/trips/%s" % P["id"], vai="ketoan")
        assert P["fee_pct"] == 3 and P["over_limit_t"] == 38 and P["over_price"] == 1.5, \
            "phí/ngưỡng/mức trừ phải tự điền theo CHỦ XE (3 · 38 · 1.5): %s %s %s" % (P["fee_pct"], P["over_limit_t"], P["over_price"])
        phieu.append(P)
    print("  ✓ %-60s" % "phiếu tự điền phí 3 % · ngưỡng 38 t · trừ 1,5 USD/t theo hồ sơ chủ xe")

    # kế toán đặt giá bán và giá thuê, đi tới khoá
    for P in phieu:
        s, g = goi("/api/trips/%s" % P["id"], {"price": 41, "price_ccy": "USD", "hire_price": 40, "hire_ccy": "USD"}, vai="ketoan", method="PUT")
        phai(s, 200, "Kế toán đặt giá bán 41, giá thuê 40 USD/t cho %s" % P["doc_no"], g)
        for muc in ("info", "trans", "fuel"):
            s, g = goi("/api/trips/%s/sections/%s/send" % (P["id"], muc), {}, vai="thabok"); phai(s, 200, "gửi kiểm %s" % muc, g)
        # xe thuê: dầu lấy từ kho là XUẤT BÁN cho chủ xe — KT kho gõ giá bán trước khi kiểm mục III (chủ dự án 29/09)
        s, pk = goi("/api/trips/%s" % P["id"], vai="khonl")
        s, g = goi("/api/trips/%s" % P["id"], {"expenses": [{"id": e["id"], "section": "fuel", "sale_price": 31000}
                                                          for e in pk["expenses"] if e["section"] == "fuel"]}, vai="khonl", method="PUT")
        phai(s, 200, "KT kho gõ giá bán dầu cho chủ xe", g)
        for muc, v in (("info", "ketoan"), ("trans", "ketoan"), ("fuel", "khonl")):
            s, g = goi("/api/trips/%s/sections/%s/verify" % (P["id"], muc), {}, vai=v); phai(s, 200, "kiểm %s" % muc, g)
        # dầu kho chỉ rời kho theo phiếu ĐỀ NGHỊ đã cấp (chủ dự án 30/09): Bãi in đề nghị → cấp dầu → mới ghi sổ mục III
        s, v = goi("/api/trips/%s/vouchers" % P["id"], {"kind": "fuel"}, vai="thabok"); phai(s, 200, "Bãi in phiếu đề nghị xuất kho nhiên liệu", v)
        for x in v:
            s, g = goi("/api/vouchers/%s/cap" % x["id"], {"qty": x["qty_l"]}, vai="khonl"); phai(s, 200, "Cấp dầu theo " + x["doc_no"], g)
        s, g = goi("/api/trips/%s/sections/fuel/book" % P["id"], {}, vai="khonl"); phai(s, 200, "ghi sổ III", g)
        s, g = goi("/api/trips/%s/sections/fuel/pay" % P["id"], {}, vai="quyvc"); phai(s, 200, "chi III", g)
        chi_tam_ung(P["id"], phai)
        s, g = goi("/api/trips/%s/transport-status" % P["id"], {"status": "arrived", "weight_dest": P["weight_origin"], "odo_back": 300, "back_date": "2026-09-18"}, vai="thabok")
        phai(s, 200, "xe về, cân bãi", g)
        s, g = goi("/api/trips/%s/khoa" % P["id"], {"xac_nhan": True}, vai="ketoan"); phai(s, 200, "khoá %s" % P["doc_no"], g)
        # phí 3 % trên tiền thuê, vượt 38 t trừ 1,5 USD/t — đúng điều khoản chủ xe
        k = g["tinh"]; thue = round(P["weight_origin"] * 40, 2)
        assert abs(k["phi"] - round(thue * 0.03, 2)) < 0.01, "phí phải là 3 %% của %s: %s" % (thue, k["phi"])
        assert abs(k["tru_vuot"] - round(max(0, P["weight_origin"] - 38) * 1.5, 2)) < 0.01, "quá tải phải theo ngưỡng 38 t × 1,5: %s" % k["tru_vuot"]
    print("  ✓ %-60s" % "hai phiếu đã khoá; phí và quá tải tính theo điều khoản chủ xe")

    # ---------------------------------------------------------------- 4. công nợ và trả gộp — TRANG KẾ TOÁN từ 28/09 (đợt 7b)
    s, g = goi("/api/owners/%s/cong-no" % chu["id"], vai="quytb"); phai(s, 409, "Đường cũ bên điều xe → 409 'đã dời sang trang kế toán'", g)
    s, g = K.kt("/api/xe-lien-ket/chu-xe/%s/cho-tra" % chu["id"], vai="thabok"); phai(s, 403, "Bãi xem công nợ chủ xe → bị từ chối", g)
    s, cn = K.kt("/api/xe-lien-ket/chu-xe/%s/cho-tra" % chu["id"], vai="quytb"); phai(s, 200, "Quỹ xem phiếu chờ trả (trang kế toán)", cn)
    s, dsc = K.kt("/api/xe-lien-ket/chu-xe", vai="quytb")
    c1 = next(c for c in dsc if c["id"] == chu["id"])
    assert len(cn["cho_tra"]) == 2 and c1["cho_tra"]["so_phieu"] == 2, "phải có 2 phiếu chờ trả: %s" % c1["cho_tra"]
    tong_usd = round(sum(p["tra_chu_xe"] for p in cn["cho_tra"]), 2)
    print("  ✓ %-60s %s USD" % ("2 phiếu chờ trả, tổng", tong_usd))

    # ---------------------------------------------------------------- 3b. chủ xe mua ở QUẦY → trừ vào tiền trả (chủ dự án 23/09)
    # "deal 1tr6, mua xăng 3 trăm → trả 1tr3": chủ xe mua 10 lít dầu 30.000 LAK/L = 300.000 LAK, không trả tiền mặt.
    s, dd = goi("/api/fuel-places", vai="ketoan"); kho_tb = next(x for x in dd if x.get("code") == "KHO-TB")
    # (phiếu bán ở TRANG KẾ TOÁN từ đợt 6 — chủ xe lấy từ danh mục bên này)
    s, ban = K.kt("/api/ban-hang", {"sale_date": "2026-09-19", "owner_id": chu["id"], "currency": "LAK", "note": "thử: chủ xe mua dầu ở quầy",
                                    "lines": [{"item_type": "fuel", "place_id": kho_tb["id"], "qty": 10, "unit_price": 30000}]}, vai="ketoan")
    phai(s, 200, "Chủ xe mua 10 lít dầu ở quầy (trang kế toán, 300.000 LAK, trừ vào tiền trả)", ban)
    assert ban["owner_id"] == chu["id"] and ban["customer_id"] is None and ban["total_lak"] == 300000, ban
    s, g = K.kt("/api/ban-hang/%s/thu" % ban["id"], {}, vai="quytb"); phai(s, 409, "Thu tiền mặt phiếu trừ chủ xe → bị từ chối", g)
    hd = [v for v in K.to_kho(ban["doc_no"], "HD_BAN") if (v.get("lines") or {}).get("doc_no") == ban["doc_no"]]
    assert hd and hd[0]["debit"] == "4022" and hd[0]["credit"] == "707", "bán cho chủ xe: Nợ 4022 (giảm phải trả chủ xe) / Có 707 bán hàng hoá: %s" % hd
    print("  ✓ %-60s Nợ %s / Có %s" % ("hoá đơn bán cho chủ xe không thành nợ khách", hd[0]["debit"], hd[0]["credit"]))
    s, cn = K.kt("/api/xe-lien-ket/chu-xe/%s/cho-tra" % chu["id"], vai="quytb")
    s, dsc = K.kt("/api/xe-lien-ket/chu-xe", vai="quytb")
    c1 = next(c for c in dsc if c["id"] == chu["id"])
    assert [b_["doc_no"] for b_ in cn["ban_cho_tru"]] == [ban["doc_no"]] and c1["cho_tra"]["ban_cho_tru_lak"] == 300000, c1["cho_tra"]
    print("  ✓ %-60s %s LAK" % ("công nợ chủ xe hiện phiếu bán chờ trừ", format(c1["cho_tra"]["ban_cho_tru_lak"], ",")))
    ids = [p["id"] for p in cn["cho_tra"]]
    s, g = K.kt("/api/xe-lien-ket/chu-xe/%s/tra" % chu["id"], {"trip_ids": ids}, vai="ketoan"); phai(s, 403, "Kế toán trả tiền → bị từ chối (quỹ chi)", g)
    s, g = K.kt("/api/xe-lien-ket/chu-xe/%s/tra" % chu["id"], {"trip_ids": []}, vai="quytb"); phai(s, 422, "Trả mà không chọn phiếu → bị từ chối", g)
    # trang điều xe tắt → chặn, không lập đợt nào
    s, ch = K.kt("/api/cau-hinh", vai="admin"); dx_cu = ch["dieu_xe_api"]
    K.kt("/api/cau-hinh", {"dieu_xe_api": "http://127.0.0.1:8097"}, vai="admin", method="PUT")
    try:
        s, g = K.kt("/api/xe-lien-ket/chu-xe/%s/tra" % chu["id"], {"trip_ids": ids, "method": "bank"}, vai="quytb")
        phai(s, 503, "Trang điều xe tắt → trả chủ xe bị chặn, báo rõ", g)
    finally:
        K.kt("/api/cau-hinh", {"dieu_xe_api": dx_cu}, vai="admin", method="PUT")
    s, dot = K.kt("/api/xe-lien-ket/chu-xe/%s/tra" % chu["id"], {"trip_ids": ids, "pay_date": "2026-09-30", "method": "bank", "ref": "UNC-CX-01"}, vai="quytb")
    phai(s, 200, "Quỹ trả GỘP hai phiếu một lần (chuyển khoản, trang kế toán)", dot)
    s, cn = K.kt("/api/xe-lien-ket/chu-xe/%s/cho-tra" % chu["id"], vai="quytb")
    assert not cn["cho_tra"] and not cn["ban_cho_tru"], "sau trả gộp: 0 phiếu chờ, 0 phiếu bán chờ trừ: %s" % cn
    tru = round(300000 / 22000, 2)                    # 300.000 LAK quy về USD theo tỷ giá trên phiếu
    assert abs(dot["gross"] - tong_usd) < 0.01 and abs(dot["sales_deducted"] - tru) < 0.01 and abs(dot["amount"] - (tong_usd - tru)) < 0.02 \
        and dot["currency"] == "USD" and sorted(dot["phieu"]) == sorted(p["doc_no"] for p in phieu) and dot["ban"] == [ban["doc_no"]], \
        "đợt trả = tổng phiếu − hàng mua ở quầy, đủ hai phiếu và phiếu bán: %s" % dot
    print("  ✓ %-60s %s − %s = %s %s" % ("đợt trả TRỪ hàng mua ở quầy", dot["gross"], dot["sales_deducted"], dot["amount"], dot["currency"]))
    s, b2 = K.kt("/api/ban-hang/%s" % ban["id"], vai="ketoan")
    assert b2["status"] == "offset" and b2["owner_payment_id"] == dot["id"], "phiếu bán phải đánh đã trừ, trỏ về đợt: %s" % b2
    print("  ✓ %-60s %s" % ("phiếu bán đánh 'đã trừ', trỏ về đợt", b2["status"]))
    s, g = K.kt("/api/ban-hang/%s" % ban["id"], vai="ketoan", method="DELETE"); phai(s, 409, "Bỏ phiếu bán đã trừ → bị từ chối", g)

    s, ct = K.kt("/api/chung-tu?loai=PC_CX&limit=1000", vai="ketoan")
    to = [v for v in ct if v["source"] == "EPL_KETOAN" and all(p["doc_no"] in (v.get("memo") or "") for p in phieu)]
    assert len(to) == 1 and to[0]["credit"] == "1022" and to[0]["debit"] == "4022" and to[0]["entry_id"], \
        "một đợt → MỘT tờ PC_CX sinh ở sổ, Nợ 4022 / Có ngân hàng ngoại tệ 1022, vào sổ ngay: %s" % to
    assert abs(to[0]["amount"] - dot["amount"]) < 0.01, "PC_CX là số THỰC CHI sau khi trừ: %s ≠ %s" % (to[0]["amount"], dot["amount"])
    print("  ✓ %-60s %s · Nợ %s / Có %s" % ("một tờ PC_CX cho cả đợt", to[0]["ref"], to[0]["debit"], to[0]["credit"]))

    for P in phieu:
        s, g = goi("/api/trips/%s" % P["id"], vai="quytb")
        assert g["owner_paid"] and g["owner_payment_id"] == dot["id"], "phiếu %s phải đánh đã trả và trỏ về đợt (bản chép)" % P["doc_no"]
    print("  ✓ %-60s" % "bản chép trên phiếu (điều xe): đã trả, trỏ về đợt")
    s, g = goi("/api/trips/%s/tra-chu-xe" % phieu[0]["id"], {}, vai="quytb"); phai(s, 409, "Nút cũ bên điều xe → 409 'đã dời'", g)
    s, g = K.kt("/api/xe-lien-ket/phieu/%s/tra" % phieu[0]["id"], {}, vai="quytb"); phai(s, 409, "Trả lại từng phiếu đã nằm trong đợt → từ chối", g)
    s, g = K.kt("/api/xe-lien-ket/chu-xe/%s/tra" % chu["id"], {"trip_ids": ids}, vai="quytb"); phai(s, 409, "Trả gộp lần hai cùng phiếu → từ chối", g)

    # ---------------------------------------------------------------- 5. dọn
    s, g = goi("/api/trips/%s" % phieu[0]["id"], vai="admin", method="DELETE"); phai(s, 409, "Phiếu đã trả chủ xe → không xoá được (kể cả Sếp)", g)
    s, g = K.kt("/api/xe-lien-ket/dot/%s" % dot["id"], vai="quytb", method="DELETE"); phai(s, 403, "Quỹ huỷ đợt trả → bị từ chối (chỉ Sếp)", g)
    s, g = K.kt("/api/xe-lien-ket/dot/%s" % dot["id"], vai="admin", method="DELETE"); phai(s, 200, "Sếp huỷ đợt trả thử (trang kế toán)", g)
    s, b3 = K.kt("/api/ban-hang/%s" % ban["id"], vai="ketoan")
    assert b3["status"] == "issued" and not b3["owner_payment_id"], "huỷ đợt → phiếu bán về lại chờ trừ: %s" % b3
    assert not [v for v in K.kt("/api/chung-tu?loai=PC_CX&limit=1000", vai="ketoan")[1] if v["ref"] == to[0]["ref"]], "huỷ đợt → tờ PC_CX rút khỏi sổ"
    s, g = goi("/api/trips/%s" % phieu[0]["id"], vai="quytb")
    assert not g["owner_paid"] and not g["owner_payment_id"], "huỷ đợt → phiếu về 'chưa trả' (bản chép)"
    print("  ✓ %-60s" % "huỷ đợt: phiếu bán về chờ trừ, PC_CX rút, phiếu về chưa trả")
    s, g = K.kt("/api/ban-hang/%s" % ban["id"], vai="ketoan", method="DELETE"); phai(s, 200, "Bỏ phiếu bán thử (hàng về kho)", g)
    for P in phieu:
        s, g = goi("/api/trips/%s/mo-khoa" % P["id"], {}, vai="admin")
        s, g = goi("/api/trips/%s" % P["id"], vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử %s" % P["doc_no"], g)
    s, g = goi("/api/vehicles/%s" % xe["id"], {"active": False}, vai="thabok", method="PUT"); phai(s, 200, "Ngưng dùng xe thử", g)
    s, g = goi("/api/owners/%s" % chu["id"], {"name": chu["name"], "active": False}, vai="ketoan", method="PUT"); phai(s, 200, "Ngưng chủ xe thử", g)

    print("\nTHỬ CHỦ XE: ĐẠT — danh mục · phí riêng từng chủ tự điền vào phiếu · trả gộp nhiều phiếu một tờ PC_CX · chặn trả trùng · phân quyền")


if __name__ == "__main__":
    main()
