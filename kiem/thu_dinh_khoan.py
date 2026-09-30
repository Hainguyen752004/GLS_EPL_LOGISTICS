# -*- coding: utf-8 -*-
"""Thử BẢNG ĐỊNH KHOẢN (rà 30/09 theo Excel, quy trình của khách và danh mục THẬT của bên kế toán).

    python kiem/thu_dinh_khoan.py [http://127.0.0.1:8011]

Phần 1 — không cần máy chủ: mọi mã trang điều xe in ra đều là tài khoản LÁ của danh mục thật (bản chụp
services/danh_muc_tai_khoan_lao.json), trừ ba mã con của khách 1371 · 4021 · 4022 (bên kế toán chưa mở); "70" (mã nhóm)
không còn xuất hiện; bảng dòng chi đúng từng cách trả, xe nhà / xe liên kết.
Phần 2 — qua máy chủ thử:
  · phiếu xe nhà đúng mục IV tờ Excel mẫu: tiền mặt → 625/1601 · cùng lương → 625/4201 · chipping → 625/4021;
    mục VI tiền mặt → 625/1601; sửa ngoài → 614/4021; dầu kho → 625/1371;
  · dòng mang mã luật cũ (625/4021 cho khoản tiền mặt) gửi lên → máy đặt lại theo luật; mã người dùng tự chọn → giữ;
  · phiếu xe liên kết: tiền mặt → 4022/1011 · chipping → 4022/4021 · dầu kho (xuất bán) → 4022/707;
  · tờ tạm ứng quét QR: các dòng mang 625/1601; quỹ chi thẳng mục IV → PC_TU Nợ 1601 / Có 1011 đúng số tờ tạm ứng;
  · quỹ chi mục V → PC_SC chỉ gồm khoản quỹ trả ngay (garage), KHÔNG gồm lốp (nợ nhà cung cấp trả theo đợt);
  · danh mục Acc code có 1371 · 4021 · 4022 kèm chữ "chưa mở"; màn Quy trình có bảng dòng chi.
Bài tự lập phiếu thử và tự xoá (phiếu đã chi thì ở lại bản sao DB thử).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from services import chung_tu as CT  # noqa: E402
from services import tai_khoan as TK  # noqa: E402

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TKN = {}


def goi(duong, body=None, vai=None, method=None):
    du = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TKN[vai]} if vai else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def phai(s, mong, buoc, g=None):
    print("  %s %-78s %s" % ("✓" if s == mong else "SAI", buoc, s))
    if s != mong:
        raise SystemExit("DỪNG: %s — %s" % (buoc, g))


def dung(dk, buoc):
    print("  %s %s" % ("✓" if dk else "SAI", buoc))
    if not dk:
        raise SystemExit("DỪNG: " + buoc)


# ------------------------------------------------------------------ phần 1: không cần máy chủ
def phan_1():
    print("Phần 1 — bảng mã (không cần máy chủ)")
    dung(len(TK.DANH_MUC) >= 400 and TK.trang_thai("70") == "nhom", "Bản chụp danh mục thật %d mã; 70 là mã NHÓM" % len(TK.DANH_MUC))
    dung(all(TK.trang_thai(m) == "khong_co" for m in TK.MA_CON_KHACH) or all(TK.trang_thai(m) in ("that", "ma_con_khach") for m in TK.MA_CON_KHACH),
         "1371 · 4021 · 4022 là mã con của khách (%s)" % ", ".join("%s→%s" % (m, TK.trang_thai(m)) for m in TK.MA_CON_KHACH))
    ma = set()
    for cap in TK.MA_HE_THONG:
        n, c = cap.split("/")
        if c not in ("402", "371", "37"):      # ba đuôi này chỉ để nhận ra mã luật CŨ, máy không in ra nữa
            ma |= {n, c}
    for loai, (_t, _l, co_dk) in CT.LOAI.items():
        if not co_dk:
            continue
        for cty in ("EPL", "joint"):
            for muc in ("fuel", "travel", "repair"):
                for pt, tt in (("cash", "LAK"), ("cash", "USD"), ("bank", "LAK"), ("bank", "USD")):
                    no, _a, co, _b = CT.dinh_khoan(loai, cty, muc, tt, pt)
                    ma |= {x for x in (no, co) if x}
    xau = sorted(m for m in ma if TK.trang_thai(m) not in ("that", "ma_con_khach"))
    dung(not xau, "Mọi mã in ra (%d mã) là tài khoản lá của danh mục thật hoặc mã con của khách — lạc: %s" % (len(ma), xau or "không"))
    dung("70" not in ma, 'Không còn "70" (mã nhóm) — cước 708, bán hàng 707')
    MONG = {  # (cty, mục, nguồn, tham số) → cặp
        ("EPL", "fuel", "kho", ()): "625/1371", ("joint", "fuel", "kho", ()): "4022/707",
        ("EPL", "fuel", "mua", (("ghi_no", True),)): "625/4021", ("joint", "fuel", "mua", (("ghi_no", True),)): "4022/4021",
        ("EPL", "fuel", "mua", ()): "625/1601", ("joint", "fuel", "mua", ()): "4022/1011",
        ("EPL", "travel", None, (("cach", "tien_mat"),)): "625/1601", ("joint", "travel", None, (("cach", "tien_mat"),)): "4022/1011",
        ("EPL", "travel", None, (("cach", "luong"),)): "625/4201", ("joint", "travel", None, (("cach", "luong"),)): "4022/1011",
        ("EPL", "travel", None, (("cach", "ncc"),)): "625/4021", ("joint", "travel", None, (("cach", "ncc"),)): "4022/4021",
        ("EPL", "travel", None, (("the", True),)): "625/4021", ("EPL", "other", None, ()): "625/1601",
        ("EPL", "repair", "kho", ()): "614/1371", ("joint", "repair", "kho", ()): "4022/1371",
        ("EPL", "repair", "mua", ()): "614/4021", ("joint", "repair", "mua", ()): "4022/4021",
    }
    sai = {k: (TK.dinh_khoan_dong(k[0], k[1], k[2], **dict(k[3])), v) for k, v in MONG.items()
           if TK.dinh_khoan_dong(k[0], k[1], k[2], **dict(k[3])) != v}
    dung(not sai, "Bảng dòng chi đúng %d trường hợp (cách trả × xe nhà / liên kết)%s" % (len(MONG), " — sai: %s" % sai if sai else ""))
    dung(TK.dinh_khoan_dong("joint", "travel", None, paid_by_epl=False) is None, "Chủ xe tự chi → không định khoản")
    no, _a, co, _b = CT.dinh_khoan("PC_TU", "EPL", "travel", "LAK", "cash")
    dung((no, co) == ("1601", "1011"), "PC_TU xe nhà: Nợ 1601 tạm ứng nhân viên / Có 1011 (không còn ghi thẳng 625)")
    dung(CT.dinh_khoan("QT_TU", "EPL", "travel")[0::2] == ("625", "1601") and CT.dinh_khoan("TT_CHI", "EPL", "travel", "LAK", "cash")[0::2] == ("1601", "1011")
         and CT.dinh_khoan("TT_THU", "EPL", "travel", "LAK", "cash")[0::2] == ("1011", "1601"),
         "Tất toán: QT_TU 625/1601 · TT_CHI 1601/1011 · TT_THU 1011/1601")
    dung(TK.ten("625") == "Chi phí đi lại, công tác phí" and TK.ten("625", "lo").startswith("ຄ່າເດີນທາງ"),
         "Tên 625 theo danh mục thật: đi lại, công tác phí (không phải chi phí vận chuyển — đó là 621)")


# ------------------------------------------------------------------ phần 2: qua máy chủ
def tk_cua(p, khoa, muc=None):
    return {(e["item_key"] or e["item_name"]): e["acct_code"] for e in p["expenses"] if (muc is None or e["section"] == muc)}.get(khoa)


def phan_2():
    print("\nPhần 2 — qua máy chủ %s" % GOC)
    for u in ("thabok", "ketoancp", "quytb", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TKN[u] = g["token"]
    s, xe = goi("/api/vehicles", vai="admin"); s, tx = goi("/api/drivers", vai="admin"); s, kh = goi("/api/customers", vai="admin")
    s, fp = goi("/api/fuel-places", vai="admin")
    kho = next(x for x in fp if x["owner_type"] == "epl")
    nha = next(x for x in xe if x["owner_type"] != "joint")
    lk = next((x for x in xe if x["owner_type"] == "joint"), None)
    dong = [{"section": "travel", "item_key": k, "qty": 1, "unit_price": g, "currency": "LAK"}
            for k, g in (("x_water", 60000), ("x_vn", 430000), ("x_chip_lao", 620000), ("x_trip", 1800000), ("x_phone", 150000))]
    dong += [{"section": "fuel", "item_key": "diesel", "qty": 50, "place_id": kho["id"], "currency": "LAK"},
             {"section": "other", "item_key": "x_misc", "qty": 1, "unit_price": 20000, "currency": "LAK"},
             {"section": "repair", "item_key": "x_tire", "qty": 1, "unit_price": 150000, "currency": "LAK", "source": "mua"},
             {"section": "repair", "item_key": "x_air", "qty": 1, "unit_price": 90000, "currency": "LAK", "source": "mua"}]
    s, p = goi("/api/trips", {"doc_no": "THU-DK-%s/EPL" % time.strftime("%H%M%S"), "kind": "giao", "company": "EPL", "vehicle_id": nha["id"],
                              "driver_id": tx[0]["id"], "customer_id": kh[0]["id"], "doc_date": time.strftime("%Y-%m-%d"), "expenses": dong}, "admin")
    phai(s, 200, "Lập phiếu xe nhà: mục IV như tờ Excel mẫu + dầu kho + VI tiền mặt + V lốp, garage", p)
    pids = [p["id"]]
    try:
        s, p = goi("/api/trips/%s" % pids[0], vai="ketoancp")
        mong = {"x_water": "625/4201", "x_trip": "625/4201", "x_vn": "625/1601", "x_phone": "625/1601", "x_chip_lao": "625/4021"}
        thuc = {k: tk_cua(p, k, "travel") for k in mong}
        dung(thuc == mong, "Mục IV: cùng lương 625/4201 · tiền mặt 625/1601 · chipping 625/4021 — %s" % thuc)
        dung(tk_cua(p, "x_misc", "other") == "625/1601" and tk_cua(p, "diesel", "fuel") == "625/1371"
             and tk_cua(p, "x_tire", "repair") == "614/4021" and tk_cua(p, "x_air", "repair") == "614/4021",
             "VI tiền mặt 625/1601 · dầu kho 625/1371 · sửa ngoài 614/4021")

        # dòng mang mã LUẬT CŨ → máy đặt lại; mã người dùng tự chọn → giữ
        gui = [{"id": e["id"], "section": e["section"], "item_key": e["item_key"], "qty": e["qty"], "pay_channel": e.get("pay_channel"),
                "unit_price": e.get("unit_price"), "currency": e.get("currency"),
                "source": e.get("source"), "place_id": e.get("place_id"),
                "acct_code": ("625/4021" if e["item_key"] == "x_vn" else "628/1011" if e["item_key"] == "x_phone" else e["acct_code"])}
               for e in p["expenses"] if e["section"] in ("travel", "other", "fuel")]
        s, g = goi("/api/trips/%s" % pids[0], {"expenses": gui}, "admin", "PUT")
        phai(s, 200, "Gửi lại: x_vn mang mã luật cũ 625/4021, x_phone mang mã tự chọn 628/1011", g)
        s, p = goi("/api/trips/%s" % pids[0], vai="ketoancp")
        dung(tk_cua(p, "x_vn", "travel") == "625/1601" and tk_cua(p, "x_phone", "travel") == "628/1011",
             "Mã luật cũ đặt lại thành 625/1601; mã tự chọn 628/1011 giữ nguyên")
        gui = [dict(d, acct_code=None) if d["item_key"] == "x_phone" else d for d in gui]
        s, g = goi("/api/trips/%s" % pids[0], {"expenses": gui}, "admin", "PUT"); phai(s, 200, "Bỏ mã tự chọn → về luật", g)

        # tờ tạm ứng quét QR: dòng mang 625/1601
        s, v = goi("/api/trips/%s/vouchers" % pids[0], {"kind": "advance"}, "ketoancp"); phai(s, 200, "Lập tờ đề nghị tạm ứng", v)
        s, tc = goi("/api/vouchers/tra-cuu/%s" % v[0]["token"], vai="ketoancp"); phai(s, 200, "Quét QR tờ tạm ứng", tc)
        cap = {d["acct_code"] for d in tc.get("dong", [])}
        dung(cap == {"625/1601"}, "Dòng trên tờ tạm ứng đều 625/1601 (không còn 625/4021) — %s" % cap)

        # quỹ chi thẳng mục IV → PC_TU Nợ 1601 / Có 1011, đúng số tờ tạm ứng (gồm cả VI tiền mặt)
        for hd, vai in (("send", "thabok"), ("verify", "ketoancp"), ("book", "ketoancp"), ("pay", "quytb")):
            s, g = goi("/api/trips/%s/sections/travel/%s" % (pids[0], hd), {}, vai); phai(s, 200, "Mục IV: %s (%s)" % (hd, vai), g)
        s, ct = goi("/api/chung-tu?trip_id=%s" % pids[0], vai="admin")
        tu = [c for c in ct["ds"] if c["loai"] == "PC_TU"]
        dung(len(tu) == 1 and (tu[0]["no"], tu[0]["co"]) == ("1601", "1011") and round(tu[0]["tien"]) == 430000 + 150000 + 20000,
             "PC_TU Nợ 1601 / Có 1011 · 600.000 = đúng tờ tạm ứng (IV 580.000 + VI 20.000) — %s" % [(c["no"], c["co"], c["tien"]) for c in tu])

        # quỹ chi mục V → PC_SC chỉ garage, không gồm lốp (nợ nhà cung cấp trả theo đợt)
        for hd, vai in (("send", "admin"), ("verify", "ketoancp"), ("book", "ketoancp"), ("pay", "quytb")):
            s, g = goi("/api/trips/%s/sections/repair/%s" % (pids[0], hd), {}, vai); phai(s, 200, "Mục V: %s (%s)" % (hd, vai), g)
        s, ct = goi("/api/chung-tu?trip_id=%s" % pids[0], vai="admin")
        sc = [c for c in ct["ds"] if c["loai"] == "PC_SC"]
        dung(len(sc) == 1 and round(sc[0]["tien"]) == 90000 and [d["item"] for d in sc[0]["payload"]["lines"]] == ["x_air"],
             "PC_SC chỉ khoản garage 90.000 — lốp 150.000 là nợ nhà cung cấp, không chi tiền mặt theo chuyến")

        if lk:
            dl = [{"section": "travel", "item_key": "x_vn", "qty": 1, "unit_price": 430000, "currency": "LAK"},
                  {"section": "travel", "item_key": "x_trip", "qty": 1, "unit_price": 100000, "currency": "LAK"},
                  {"section": "travel", "item_key": "x_chip_lao", "qty": 1, "unit_price": 620000, "currency": "LAK"},
                  {"section": "fuel", "item_key": "diesel", "qty": 40, "place_id": kho["id"], "currency": "LAK"}]
            s, q = goi("/api/trips", {"doc_no": "THU-DKL-%s/EPL" % time.strftime("%H%M%S"), "kind": "giao", "company": "joint", "vehicle_id": lk["id"],
                                      "driver_id": tx[0]["id"], "customer_id": kh[0]["id"], "doc_date": time.strftime("%Y-%m-%d"), "expenses": dl}, "admin")
            phai(s, 200, "Lập phiếu xe liên kết: tiền mặt, tiền chuyến, chipping, dầu kho", q)
            pids.append(q["id"])
            s, q = goi("/api/trips/%s" % q["id"], vai="ketoancp")
            thuc = {k: tk_cua(q, k) for k in ("x_vn", "x_trip", "x_chip_lao", "diesel")}
            dung(thuc == {"x_vn": "4022/1011", "x_trip": "4022/1011", "x_chip_lao": "4022/4021", "diesel": "4022/707"},
                 "Xe liên kết: tiền mặt EPL ứng 4022/1011 (không có cùng lương) · chipping 4022/4021 · dầu kho xuất bán 4022/707 — %s" % thuc)

        s, acc = goi("/api/acc-codes", vai="ketoancp")
        con = {x["code"]: x for x in acc["data"] if x["code"] in TK.MA_CON_KHACH}
        dung(set(con) == set(TK.MA_CON_KHACH) and all("chưa mở" in x["description"] for x in con.values()),
             "Danh mục Acc code (%s) có 1371 · 4021 · 4022, ghi rõ bên kế toán chưa mở" % acc["source"])
        s, qt = goi("/api/quy-trinh", vai="ketoancp")
        dung(s == 200 and len(qt["dong_chi"]) == 8 and qt["danh_muc"]["so_ma"] == len(TK.DANH_MUC)
             and any(r["EPL"]["cap"] == "625/1601" for r in qt["dong_chi"]),
             "Màn Quy trình: bảng 8 loại dòng chi + nguồn danh mục (%s mã, chụp %s)" % (qt["danh_muc"]["so_ma"], qt["danh_muc"]["chup_ngay"]))
    finally:
        for pid in pids:
            s, _ = goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
            print("  · phiếu thử %s" % ("đã xoá" if s == 200 else "ở lại bản sao DB thử (mục đã chi thì không xoá được)"))


if __name__ == "__main__":
    phan_1()
    if "--khong-may" not in sys.argv:
        phan_2()
    print("\nTHỬ ĐỊNH KHOẢN: ĐẠT")
