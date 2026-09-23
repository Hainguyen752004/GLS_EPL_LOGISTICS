# -*- coding: utf-8 -*-
"""Thử màn TỶ GIÁ — ອັດຕາແລກປ່ຽນ.

    python kiem/thu_ty_gia.py [http://127.0.0.1:8010]

Tỷ giá là con số đi thẳng vào tiền, nên chỗ này phải chắc: ai được sửa, sửa rồi có ghi lịch sử
không, gõ lại đúng số cũ có đẻ ra dòng rác không, và — quan trọng nhất — **sửa tỷ giá có làm đổi
con số trên phiếu đã lập hay không** (không được đổi: phiếu khoá tỷ giá riêng của nó).

Cuối bài trả tỷ giá về đúng số ban đầu để không ảnh hưởng dữ liệu mẫu.
"""
import json
import sys
import urllib.error
import urllib.request

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
        with urllib.request.urlopen(r, timeout=40) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def phai(s, mong, buoc, g=None):
    dt_ = (g or {}).get("detail") if isinstance(g, dict) else None
    ma = dt_.get("ma", "") if isinstance(dt_, dict) else ""
    print("%s %-58s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def main():
    for u in ("thabok", "ketoan", "doanhthu", "admin", "tx01"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 5 vai")

    # ---------------------------------------------------------------- 1. ai xem, ai sửa
    s, g = goi("/api/rates")
    phai(s, 401, "Chưa đăng nhập mà hỏi tỷ giá → bị chặn", g)
    s, goc = goi("/api/rates", vai="thabok")
    GOC_TY_GIA.update(goc)             # để `finally` trả lại đúng số này dù bộ kiểm hỏng giữa chừng
    s, cu = goi("/api/trips?q=THU-TG-01", vai="admin")
    for x in [x for x in (cu or []) if x["doc_no"] == "THU-TG-01/EPL"]:
        goi("/api/trips/%s" % x["id"], vai="admin", method="DELETE"); print("  · đã dọn phiếu thử THU-TG-01/EPL sót lại")
    phai(s, 200, "Bãi XEM được tỷ giá (chi phí của họ có VND, THB)", goc)
    assert goc.get("LAK") == 1.0, "Kíp phải luôn bằng 1 — nó là tiền gốc: %s" % goc
    for m in ("USD", "THB", "VND", "CNY"):
        assert m in goc, "thiếu tỷ giá %s: %s" % (m, goc)
    print("  ✓ %-58s %s" % ("đủ bốn tỷ giá + Kíp gốc", " · ".join("%s=%s" % (k, v) for k, v in goc.items())))

    s, g = goi("/api/rates", {"USD": 25000}, vai="thabok", method="PUT")
    phai(s, 403, "Bãi SỬA tỷ giá → bị từ chối", g)
    s, g = goi("/api/rates", {"USD": 25000}, vai="tx01", method="PUT")
    phai(s, 403, "Tài xế sửa tỷ giá → bị từ chối", g)

    s, ct = goi("/api/rates/chi-tiet", vai="ketoan")
    phai(s, 200, "Màn Tỷ giá đọc được bảng chi tiết", ct)
    assert ct["goc"] == "LAK" and len(ct["ds"]) == 4, "bảng chi tiết phải có 4 loại tiền, gốc là Kíp: %s" % ct

    # ---------------------------------------------------------------- 2. phiếu đã lập KHÔNG đổi theo
    s, ds = goi("/api/trips", vai="ketoan")
    p0 = next(p for p in ds if p["price_ccy"] == "USD" and p["tinh"]["doanh_thu"])
    dt_truoc = p0["tinh"]["doanh_thu_lak"]
    rate_truoc = p0["rate_usd"]

    # ---------------------------------------------------------------- 3. sửa và ghi lịch sử
    moi = round(goc["USD"] * 1.1)
    s, g = goi("/api/rates", {"USD": moi, "ap_dung_tu": "2026-09-21", "ghi_chu": "thử bộ kiểm"}, vai="ketoan", method="PUT")
    phai(s, 200, "Kế toán đặt tỷ giá USD mới (%s → %s)" % (goc["USD"], moi), g)
    assert g["USD"] == moi and g["_da_doi"] == ["USD"], "phải nói rõ vừa đổi những mã nào: %s" % g

    s, ct = goi("/api/rates/chi-tiet", vai="ketoan")
    u = next(x for x in ct["ds"] if x["code"] == "USD")
    assert u["rate_to_lak"] == moi and u["truoc"] == goc["USD"], "thẻ USD phải nhớ số lần trước: %s" % u
    assert u["by_user"], "phải ghi ai đặt: %s" % u
    print("  ✓ %-58s %s → %s (%+.3f%%)" % ("thẻ USD nhớ số lần trước và người đặt", u["truoc"], u["rate_to_lak"], u["doi_pct"]))
    ls = [x for x in ct["lich_su"] if x["code"] == "USD"]
    assert ls and ls[0]["rate_cu"] == goc["USD"] and ls[0]["ghi_chu"] == "thử bộ kiểm" and ls[0]["nguon"] == "tay", \
        "lịch sử phải giữ số cũ, ghi chú và nguồn: %s" % (ls[:1])
    print("  ✓ %-58s %d dòng" % ("lịch sử ghi lại lần đổi kèm số cũ", len(ls)))

    # ---------------------------------------------------------------- 4. gõ lại đúng số cũ → không đẻ dòng rác
    truoc_n = len(ct["lich_su"])
    s, g = goi("/api/rates", {"USD": moi}, vai="ketoan", method="PUT")
    phai(s, 200, "Gõ lại ĐÚNG số đang dùng → không ghi lịch sử rỗng", g)
    assert g["_da_doi"] == [], "không đổi gì thì danh sách đã đổi phải rỗng: %s" % g["_da_doi"]
    s, ct2 = goi("/api/rates/chi-tiet", vai="ketoan")
    assert len(ct2["lich_su"]) == truoc_n, "số dòng lịch sử không được tăng: %s → %s" % (truoc_n, len(ct2["lich_su"]))

    # ---------------------------------------------------------------- 5. số sai
    for xau, ten in ((0, "0"), (-5, "số âm"), ("abc", "chữ")):
        s, g = goi("/api/rates", {"THB": xau}, vai="ketoan", method="PUT")
        phai(s, 422, "Tỷ giá %s → bị từ chối" % ten, g)

    # ---------------------------------------------------------------- 6. phiếu cũ không đổi theo
    s, p1 = goi("/api/trips/%s" % p0["id"], vai="ketoan")
    assert p1["rate_usd"] == rate_truoc, "phiếu đã lập phải GIỮ tỷ giá của nó: %s ≠ %s" % (p1["rate_usd"], rate_truoc)
    assert p1["tinh"]["doanh_thu_lak"] == dt_truoc, "doanh thu quy Kíp của phiếu cũ không được đổi theo tỷ giá mới"
    print("  ✓ %-58s %s LAK" % ("phiếu %s giữ nguyên tỷ giá và doanh thu" % p1["doc_no"], dt_truoc))

    # ---------------------------------------------------------------- 7. phiếu MỚI lấy tỷ giá mới
    s, kh = goi("/api/customers", vai="ketoan")
    s, xe = goi("/api/vehicles", vai="thabok")
    s, pm = goi("/api/trips", {"doc_no": "THU-TG-01/EPL", "kind": "gom", "doc_date": "2026-09-21",
                               "vehicle_id": xe[0]["id"], "customer_id": kh[0]["id"]}, vai="thabok")
    phai(s, 200, "Lập phiếu MỚI sau khi đổi tỷ giá", pm)
    # Bãi không thấy tỷ giá (anh Khampla A2) — đọc bằng vai kế toán
    assert "rate_usd" not in pm, "gói trả cho Bãi không được có tỷ giá"
    s, pm = goi("/api/trips/%s" % pm["id"], vai="ketoan")
    assert pm["rate_usd"] == moi, "phiếu mới phải lấy tỷ giá mới %s, nhận %s" % (moi, pm["rate_usd"])
    print("  ✓ %-58s %s" % ("phiếu mới khoá tỷ giá mới", pm["rate_usd"]))
    s, g = goi("/api/trips/%s" % pm["id"], vai="admin", method="DELETE")
    phai(s, 200, "Xoá phiếu thử (dọn)", g)

    # ---------------------------------------------------------------- 8. trả tỷ giá về như cũ
    s, g = goi("/api/rates", {"USD": goc["USD"], "ghi_chu": "trả lại sau bộ kiểm"}, vai="ketoan", method="PUT")
    phai(s, 200, "Trả tỷ giá USD về %s (dọn)" % goc["USD"], g)
    assert g["USD"] == goc["USD"]

    print("\nTHỬ TỶ GIÁ: ĐẠT — phân quyền xem/sửa · lịch sử có số cũ · không đẻ dòng rác · "
          "chặn số sai · phiếu cũ giữ tỷ giá của nó · phiếu mới lấy số mới")


GOC_TY_GIA = {}


def tra_ty_gia():
    """23/09: bộ kiểm hỏng giữa chừng hai lần, để sót USD 24.200 rồi 26.620 trong DB DÙNG CHUNG với máy chủ của
    chủ dự án — phiếu thật lập lúc đó sẽ khoá tỷ giá sai. Nên luôn trả lại tỷ giá gốc, kể cả khi hỏng."""
    if not GOC_TY_GIA.get("USD") or "ketoan" not in TOKEN:
        return
    s, hien = goi("/api/rates", vai="ketoan")
    if s == 200 and hien.get("USD") != GOC_TY_GIA["USD"]:
        s, g = goi("/api/rates", {"USD": GOC_TY_GIA["USD"], "ghi_chu": "trả lại sau bộ kiểm (hỏng giữa chừng)"}, vai="ketoan", method="PUT")
        print("  · đã trả tỷ giá USD về %s (%s)" % (GOC_TY_GIA["USD"], s))


if __name__ == "__main__":
    try:
        main()
    finally:
        tra_ty_gia()
