# -*- coding: utf-8 -*-
"""Thử BÁO SỰ CỐ của màn tài xế mới (30/09) — giống màn Theo dõi: có "Có chi tiền", còn chạy được hay phải dừng.

    python kiem/thu_bao_su_co_tai_xe.py [http://127.0.0.1:8011]

Chủ dự án nhận xét màn tài xế: báo sự cố *"không giống cái báo sự cố trong module tracking á không có tích có chi tiền
rồi hay không để yêu cầu tạo phiếu chi"*. Nay tài xế báo được: loại sự cố (thêm lốp · bị giữ xe), xe còn chạy được
không, và nếu có chi tiền thì số tiền + tiền tệ + tài xế đã tự trả hay chưa. Khoản chi KHÔNG có tờ đề nghị chi riêng
(anh chốt 30/09): tổ sửa chữa duyệt thì thành dòng mục V rồi đi tiếp thành phiếu chi như bình thường.

Kịch bản: lập phiếu thử cho tx01 → báo lốp có chi tiền, đã tự trả, phải dừng → báo bị giữ xe không có tiền (cờ "đã tự
trả" bị bỏ vì không có số tiền) → chặn tiền âm, loại sai, thiếu mô tả → tổ sửa chữa duyệt: dòng mục V ghi "tài xế đã tự
trả" → từ chối lần báo thứ hai → danh sách phiếu của tài xế sắp cũ-trước (`sap=cu`) → dọn phiếu thử.
"""
import json
import os
import sys
import urllib.error
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _quy_trinh as Q  # noqa: E402 — lập phiếu theo quy trình 23/09 (Bãi lập không tiền)

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011").rstrip("/")
TOKEN = {}
SO_PHIEU = "TX-SUCO-01/EPL"
LOI = []


def goi(duong, du_lieu=None, vai=None, method=None):
    dau = {"Content-Type": "application/json"}
    if vai:
        dau["Authorization"] = "Bearer " + TOKEN[vai]
    than = json.dumps(du_lieu).encode() if du_lieu is not None else None
    r = urllib.request.Request(GOC + duong, data=than, headers=dau, method=method or ("POST" if than is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def ma_loi(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return d.get("ma", "") if isinstance(d, dict) else ""


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, them))
    sys.stdout.flush()
    if not dk:
        LOI.append(buoc)


def phai(s, mong, buoc, g=None):
    print("%s %-64s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma_loi(g)))
    sys.stdout.flush()
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def don():
    s, ds = goi("/api/trips?q=%s&co=20" % SO_PHIEU.split("/")[0], vai="admin")
    for p in [x for x in ds if x["doc_no"] == SO_PHIEU]:
        goi("/api/trips/%s/mo-khoa" % p["id"], {}, vai="admin")
        goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")


def main():
    for u in ("thabok", "ketoan", "totsua", "tx01", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 5 vai (Bãi, kế toán, tổ sửa chữa, tài xế, admin)")
    don()

    s, kh = goi("/api/customers", vai="ketoan")
    s, tuyen = goi("/api/routes", vai="ketoan")
    s, xe = goi("/api/vehicles", vai="thabok")
    s, tx = goi("/api/drivers", vai="thabok")
    s, toi = goi("/api/toi", vai="tx01")
    tai_xe = [d for d in tx if d["name"] == toi["full_name"]]
    if not tai_xe:
        raise SystemExit("DỪNG: không thấy hồ sơ tài xế của tx01 trong /api/drivers")
    xe_nha = [x for x in xe if x.get("owner_type") != "joint" and x.get("active") is not False]

    print("1. Lập phiếu thử cho tx01")
    s, P = Q.lap_phieu(goi, {
        "doc_no": SO_PHIEU, "kind": "gom", "doc_date": "2026-09-30", "out_date": "2026-09-30",
        "vehicle_id": xe_nha[0]["id"], "driver_id": tai_xe[0]["id"], "customer_id": kh[0]["id"],
        "route_id": tuyen[0]["id"], "goods_type": "iron_ore", "weight_origin": 35,
        "hang": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 35}],
    }, vai="thabok")
    phai(s, 200, "Bãi lập phiếu %s cho tài xế %s" % (SO_PHIEU, toi["full_name"]), P)
    pid = P["id"]

    try:
        print("2. Tài xế báo sự cố có chi tiền")
        s, g = goi("/api/trips/%s/bao-hong" % pid, {"incident_type": "tire", "note": "thử: nổ lốp sau trái, đã vá",
                                                     "can_run": False, "reported_cost": 150000, "currency": "LAK",
                                                     "paid_by_driver": True, "stop_seq": 1}, vai="tx01")
        phai(s, 200, "Tài xế báo nổ lốp · phải dừng · 150.000 LAK · đã tự trả", g)
        e1 = [e for e in g["events"] if e["kind"] == "incident" and e["status"] == "reported"][-1]
        dung(e1["incident_type"] == "tire", "loại sự cố lưu là 'tire'", e1["incident_type"])
        dung(e1["can_run"] is False, "ghi nhận xe PHẢI DỪNG", str(e1["can_run"]))
        dung(e1["paid_by_driver"] is True, "ghi nhận tài xế ĐÃ TỰ TRẢ", str(e1["paid_by_driver"]))
        dung(e1["reported_cost"] == 150000 and e1["currency"] == "LAK", "số tiền và tiền tệ đúng như tài xế báo",
             "%s %s" % (e1["reported_cost"], e1["currency"]))

        s, g = goi("/api/trips/%s/bao-hong" % pid, {"incident_type": "held", "note": "thử: bị giữ xe kiểm tra tải trọng",
                                                     "can_run": True, "paid_by_driver": True}, vai="tx01")
        phai(s, 200, "Tài xế báo bị giữ xe · không có tiền", g)
        e2 = [e for e in g["events"] if e["kind"] == "incident" and e["status"] == "reported" and e["id"] != e1["id"]][-1]
        dung(e2["incident_type"] == "held" and e2["can_run"] is True, "loại 'held' · còn chạy được")
        dung(e2["paid_by_driver"] is None and e2["reported_cost"] is None,
             "không có số tiền thì bỏ cờ 'đã tự trả' (không có gì để trả)", str(e2["paid_by_driver"]))

        print("3. Chặn khai sai")
        s, g = goi("/api/trips/%s/bao-hong" % pid, {"incident_type": "tire", "note": "thử", "reported_cost": -5}, vai="tx01")
        dung(s == 422 and ma_loi(g) == "SO_AM", "tiền âm → 422 SO_AM", "%s %s" % (s, ma_loi(g)))
        s, g = goi("/api/trips/%s/bao-hong" % pid, {"incident_type": "xyz", "note": "thử"}, vai="tx01")
        dung(s == 422 and ma_loi(g) == "LOAI_SAI", "loại lạ → 422 LOAI_SAI", "%s %s" % (s, ma_loi(g)))
        s, g = goi("/api/trips/%s/bao-hong" % pid, {"incident_type": "breakdown", "note": "  "}, vai="tx01")
        dung(s == 422 and ma_loi(g) == "THIEU_MO_TA", "thiếu mô tả → 422 THIEU_MO_TA", "%s %s" % (s, ma_loi(g)))

        print("4. Tài xế xem lại được hai cờ mới trên phiếu của mình")
        s, g = goi("/api/trips/%s" % pid, vai="tx01")
        ev = {e["id"]: e for e in g["events"]}
        dung(s == 200 and ev[e1["id"]]["can_run"] is False and ev[e1["id"]]["paid_by_driver"] is True,
             "GET phiếu trả đủ can_run / paid_by_driver")

        print("5. Tổ sửa chữa duyệt → dòng mục V (đi tiếp thành phiếu chi như bình thường)")
        s, g = goi("/api/trips/%s/events/%s/duyet" % (pid, e1["id"]), {"source": "mua", "item_name": "thử: vá lốp", "qty": 1}, vai="totsua")
        phai(s, 200, "Tổ sửa chữa duyệt lần báo lốp", g)
        v = [d for d in g["expenses"] if d["section"] == "repair"]
        dung(len(v) == 1 and v[0]["unit_price"] == 150000, "mục V có một dòng 150.000 (mặc định = số tài xế báo)",
             str([(d["unit_price"], d["currency"]) for d in v]))
        dung(bool(v) and "tài xế đã tự trả" in (v[0]["note"] or ""), "dòng mục V ghi rõ 'tài xế đã tự trả'", (v[0]["note"] if v else ""))
        dung(((g.get("sections") or {}).get("repair")) == "entered", "mục V chuyển sang 'đã nhập' để Bãi / kế toán kiểm tiếp")
        s, g = goi("/api/trips/%s/events/%s/duyet" % (pid, e2["id"]), {"reject": True, "reason": "thử: không phát sinh chi"}, vai="totsua")
        phai(s, 200, "Tổ sửa chữa từ chối lần báo bị giữ xe", g)

        print("6. Danh sách phiếu của tài xế: sắp mới-trước (mặc định) và cũ-trước (sap=cu)")
        s, moi = goi("/api/trips?co=5", vai="tx01")
        s2, cu = goi("/api/trips?co=5&sap=cu", vai="tx01")
        ngay_moi = [p["doc_date"] for p in moi]
        ngay_cu = [p["doc_date"] for p in cu]
        dung(s == 200 and ngay_moi == sorted(ngay_moi, reverse=True), "mặc định: ngày giảm dần", str(ngay_moi))
        dung(s2 == 200 and ngay_cu == sorted(ngay_cu), "sap=cu: ngày tăng dần", str(ngay_cu))
        dung(not moi or not cu or ngay_cu[0] <= ngay_moi[-1], "phiếu đầu của 'cũ trước' không mới hơn phiếu cuối của 'mới trước'")
    finally:
        don()
        print("✓ đã dọn phiếu thử %s" % SO_PHIEU)

    print()
    if LOI:
        print("BÁO SỰ CỐ TÀI XẾ: SAI %d bước — %s" % (len(LOI), "; ".join(LOI)))
        sys.exit(1)
    print("BÁO SỰ CỐ TÀI XẾ: ĐẠT")


if __name__ == "__main__":
    main()
