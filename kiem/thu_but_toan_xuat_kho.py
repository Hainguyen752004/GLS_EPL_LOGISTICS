# -*- coding: utf-8 -*-
"""Thử BÚT TOÁN XUẤT KHO CHO CHUYẾN (chủ dự án 01/10: "xuất dầu là xuất nội bộ và còn là xuất bán") — dầu kho mục III và
phụ tùng kho mục V thành bút toán chờ gửi lúc KHOÁ PHIẾU, một lần xuất một bút toán (services/but_toan_cho.dong_xuat_kho).

    python kiem/thu_but_toan_xuat_kho.py [http://127.0.0.1:8015] [cổng máy giả 8095]

CHỈ chạy trên máy thử (bản sao DB). Máy điều xe phải nối kho tạm thử (8031) — bài cấp dầu và xuất phụ tùng thật ở đó, xoá phiếu
thử là trả lại kho. Máy chủ BẬT cờ QLSX_GUI_BUT_TOAN trỏ máy giả (scratchpad xk_8015.ps1 -Gui) thì bài dựng máy giả hệ kế toán
ở cổng tham số 2 và kiểm cả gói gửi đi; cờ tắt thì bỏ phần gói (in rõ).

  A xe nhà · dầu kho 50 L (cấp theo phiếu đề nghị) + 1 phụ tùng kho → hai bút toán `xuat_noi_bo`:
      dầu Nợ 625 / Có 1371 · phụ tùng Nợ 614 / Có 1371, tiền = số lượng × giá vốn bình quân kho lúc xuất.
  B xe thuê, EPL ứng · dầu kho 40 L + 1 phụ tùng kho, KT kho xăng dầu / KT Chi phí gõ giá bán → hai bút toán `xuat_ban`:
      Nợ 4022 / Có 707 theo GIÁ BÁN (đối tượng chủ xe — đúng số trừ vào tiền trả chủ xe) + Nợ 607 / Có 1371 theo giá vốn.
  C xe thuê, chủ xe tự trả (dầu kho + phụ tùng kho đã rời kho) → không có bút toán xuất kho.
  Trước khi khoá: chưa có (dầu đã cấp vẫn chưa). Mở khoá → huỷ (cờ bật: gỡ bên kế toán). Khoá lại → cùng bản, không trùng.
  Không trùng `ban_chu_xe` (bán ở quầy). Vai không thấy giá vốn (Bãi, thủ kho, tổ sửa, KT kho xăng dầu…) không đọc được.
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8015").rstrip("/")
CONG = int(sys.argv[2]) if len(sys.argv) > 2 else 8095
if GOC.endswith((":8010", ":8020", ":8001")):
    sys.exit("Không chạy bài này trên máy thật.")
TK, LOI = {}, []
TIEN_TO = "THU-BTXK-"
HOM_NAY = time.strftime("%Y-%m-%d")
DUONG = "/api/v1/integrations/logistics/journal-entries"
VAI = {"admin": "admin", "ketoan": "acct", "ketoancp": "expacct", "khonl": "fuel", "khotb": "depot", "khopt": "parts",
       "totsua": "repair", "thabok": "yard", "quyvc": "treasury"}


# ================================================================ máy giả hệ kế toán (đúng giao ước b9227aa, gọn)
class GIA:
    ct, nhan, so, may = {}, [], 9000, None


class Xu(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _tra(self, ma, than):
        b = json.dumps(than, ensure_ascii=False).encode("utf-8")
        self.send_response(ma); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        GIA.nhan.append(("GET", self.path, dict(self.headers), None))
        if self.path.startswith("/api/v1/common/GetAllCurrency"):
            return self._tra(200, {"Success": True, "Result": [{"CUR_AUTOID": 26, "CUR_NAME": "LAK"}, {"CUR_AUTOID": 2, "CUR_NAME": "USD"},
                                                              {"CUR_AUTOID": 1, "CUR_NAME": "VND"}, {"CUR_AUTOID": 5, "CUR_NAME": "THB"}]})
        if self.path.startswith("/api/v1/common/GetFinancyCicle"):
            return self._tra(200, {"Success": True, "Result": [{"FICI_AUTOID": 77, "FICI_NAME": "2026", "FICI_DATEFROM": "2026-01-01",
                                                              "FICI_DATETO": "2026-12-31", "FICI_ISACTIVE": True, "FICI_ISCLOSE": False}]})
        if self.path.startswith(DUONG + "/"):
            c = GIA.ct.get(urllib.request.unquote(self.path[len(DUONG) + 1:]))
            if c is None or c["Reversed"]:
                return self._tra(404, {"Success": False, "Code": 404, "Result": None, "ErrorDetail": {"ErrorCode": "JOURNAL_ENTRY_NOT_FOUND"}})
            return self._tra(200, {"Success": True, "Result": {k: c[k] for k in ("DocumentId", "DocumentNo", "StatusId")}})
        self._tra(404, {"Success": False, "Code": 404, "Message": "không có đường"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        b = json.loads(self.rfile.read(n) or b"null") if n else None
        GIA.nhan.append(("POST", self.path, dict(self.headers), b))
        if self.path.startswith("/api/v1/master-data/") and self.path.endswith("/list"):
            return self._tra(200, {"Success": True, "Result": {"Data": []}})
        if self.path.startswith("/api/v1/master-data/") and self.path.endswith("/upsert"):
            GIA.so += 1
            return self._tra(200, {"Success": True, "Result": GIA.so})
        if self.path == DUONG + "/reverse":
            c = GIA.ct.get((b or {}).get("SourceRef"))
            if c is None or c["Reversed"]:
                return self._tra(200, {"Success": True, "Result": {"DocumentId": None, "Reversed": False}})
            c["Reversed"] = True
            return self._tra(200, {"Success": True, "Result": {"DocumentId": c["DocumentId"], "Reversed": True}})
        if self.path == DUONG:
            ref = (b or {}).get("SourceRef")
            if self.headers.get("Idempotency-Key") != ref:
                return self._tra(400, {"Success": False, "Code": 400, "Message": "Idempotency-Key phải bằng SourceRef"})
            c = GIA.ct.get(ref)
            if c and not c["Reversed"]:
                return self._tra(200, {"Success": True, "Result": {"SourceRef": ref, "DocumentId": c["DocumentId"], "DocumentNo": c["DocumentNo"],
                                                                  "StatusId": 13, "IsExisting": True}})
            GIA.so += 1
            GIA.ct[ref] = {"DocumentId": GIA.so, "DocumentNo": "GIA-XK-%d" % GIA.so, "StatusId": 13, "Reversed": False, "body": b}
            return self._tra(201, {"Success": True, "Result": {"SourceRef": ref, "DocumentId": GIA.so, "DocumentNo": "GIA-XK-%d" % GIA.so,
                                                              "StatusId": 13, "IsExisting": False}})
        self._tra(404, {"Success": False, "Code": 404, "Message": "không có đường"})


def bat_gia():
    GIA.may = ThreadingHTTPServer(("127.0.0.1", CONG), Xu)
    threading.Thread(target=GIA.may.serve_forever, daemon=True).start()


# ================================================================ gọi trang điều xe
def goi(duong, body=None, u=None, method=None):
    r = urllib.request.Request(GOC + duong, data=json.dumps(body).encode() if body is not None else None,
                               method=method or ("POST" if body is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[u]} if u else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, {}


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, them))
    sys.stdout.flush()
    if not dk:
        LOI.append(buoc)


def phai(s, mong, buoc, g=None):
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, json.dumps(g, ensure_ascii=False)[:500]))
    print("  ✓ %s %s" % (buoc, s))


def bt(tid, nguon=None):
    s, g = goi("/api/but-toan-cho?gioi_han=1000&trip_id=" + tid + ("&nguon=" + nguon if nguon else ""), u="ketoan")
    if s != 200:
        phai(s, 200, "KT Thu/Chi đọc bút toán chờ của phiếu", g)
    return g["ds"]


def kho(ds):
    return [b for b in ds if b["nguon"] in ("xuat_noi_bo", "xuat_ban")]


def don():
    s, ds = goi("/api/trips?q=" + TIEN_TO, u="admin")
    for p in [x for x in (ds or []) if str(x.get("doc_no") or "").startswith(TIEN_TO)]:
        goi("/api/trips/%s/mo-khoa" % p["id"], {}, u="admin")
        s, g = goi("/api/trips/" + p["id"], u="admin", method="DELETE")
        print("  · dọn phiếu thử %s → %s %s" % (p["doc_no"], s, "" if s == 200 else json.dumps(g, ensure_ascii=False)[:160]))


def lap(so, cong_ty, xe, tx, kh, dong):
    body = {"doc_no": so, "kind": "giao", "company": cong_ty, "vehicle_id": xe["id"], "driver_id": tx["id"], "customer_id": kh["id"],
            "doc_date": HOM_NAY, "out_date": HOM_NAY, "weight_origin": 40, "odo_out": 1000, "price": 40, "price_ccy": "USD",
            "pod_no": "BTXK-POD", "ore_bill_no": "BTXK", "expenses": dong}
    if cong_ty == "joint":
        body.update({"hire_price": 30, "hire_ccy": "USD"})
    s, p = goi("/api/trips", body, u="admin")
    phai(s, 200, "Sếp lập phiếu thử %s (%s)" % (so, "xe thuê" if cong_ty == "joint" else "xe nhà"), p)
    s, g = goi("/api/trips/%s/transport-status" % p["id"], {"status": "arrived", "weight_dest": 40, "odo_back": 1500,
                                                           "back_date": HOM_NAY}, u="admin")
    phai(s, 200, "Sếp báo xe tới", g)
    return p["id"]


def cap_dau(tid, lit):
    s, vs = goi("/api/trips/%s/vouchers" % tid, {"kind": "fuel"}, u="thabok"); phai(s, 200, "Bãi lập phiếu đề nghị xuất kho nhiên liệu", vs)
    s, r = goi("/api/vouchers/%s/cap" % vs[0]["id"], {"qty": lit}, u="khonl"); phai(s, 200, "KT kho xăng dầu cấp %s lít ở kho tạm" % lit, r)
    return vs[0]


def lay_phu_tung(tid, pid, tra=True):
    s, g = goi("/api/trips/%s/events" % tid, {"kind": "repair", "incident_type": "tire", "note": "thử bút toán xuất kho",
                                              "repair": {"source": "kho", "part_id": pid, "qty": 1, "paid_by_epl": tra}}, u="totsua")
    phai(s, 200, "Tổ sửa lấy 1 phụ tùng kho (%s)" % ("EPL ứng" if tra else "chủ xe tự trả"), g)
    return g


def dong_cua(p, section):
    return [e for e in p["expenses"] if e["section"] == section]


def main():
    for u in VAI:
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            sys.exit("Không đăng nhập được %s: %s" % (u, g))
        TK[u] = g["token"]
    s, g = goi("/api/but-toan-cho", u="ketoan")
    co_gui = bool(g.get("co_duong_gui"))
    print("Cờ gửi bút toán: %s" % ("BẬT — máy giả hệ kế toán cổng %d" % CONG if co_gui else "TẮT — bỏ phần gói gửi đi"))
    if co_gui:
        bat_gia()
    don()
    s, xe = goi("/api/vehicles", u="admin"); s, tx = goi("/api/drivers", u="admin"); s, kh = goi("/api/customers", u="admin")
    s, kx = goi("/api/kho-xem", u="admin"); phai(s, 200, "Sếp xem kho (tồn, giá bình quân)", kx)
    kho_dau = next((k for k in kx["nhien_lieu"] if k.get("active") is not False and (k.get("gia_bq") or 0) > 0), None)
    s, pts = goi("/api/parts", u="admin")
    pt = next((x for x in pts if (x.get("qty") or 0) >= 3 and (x.get("unit_price") or 0) > 0), None)
    if not kho_dau or not pt:
        sys.exit("DỪNG: kho tạm thử không có kho dầu có giá hoặc phụ tùng tồn ≥ 3 có giá — %s · %s" % (bool(kho_dau), bool(pt)))
    print("  · kho dầu %s giá bình quân %s · phụ tùng %s tồn %s giá %s" % (kho_dau["name"], kho_dau["gia_bq"], pt["name"], pt["qty"], pt["unit_price"]))
    nha = next(v for v in xe if v["owner_type"] == "EPL" and v["active"])
    thue = next(v for v in xe if v["owner_type"] == "joint" and v["active"] and v.get("owner_id"))
    taixe = [t for t in tx if t["active"]]
    A = lap(TIEN_TO + "A/EPL", "EPL", nha, taixe[0], kh[0], [{"section": "fuel", "item_key": "diesel", "qty": 50, "place_id": kho_dau["place_id"]}])
    B = lap(TIEN_TO + "B/EPL", "joint", thue, taixe[1], kh[0], [{"section": "fuel", "item_key": "diesel", "qty": 40, "place_id": kho_dau["place_id"]}])
    C = lap(TIEN_TO + "C/EPL", "joint", thue, taixe[2], kh[0], [{"section": "fuel", "item_key": "diesel", "qty": 30, "place_id": kho_dau["place_id"],
                                                              "paid_by_epl": False}])
    try:
        print("1. Xuất kho thật ở kho tạm (cấp dầu theo phiếu đề nghị, lấy phụ tùng)")
        gia_dau, gia_pt = kho_dau["gia_bq"], pt["unit_price"]
        for tid, lit in ((A, 50), (B, 40)):
            cap_dau(tid, lit)
            lay_phu_tung(tid, pt["id"])
        lay_phu_tung(C, pt["id"], tra=False)
        s, pb = goi("/api/trips/" + B, u="admin")
        fb, rb = dong_cua(pb, "fuel")[0], dong_cua(pb, "repair")[0]
        s, g = goi("/api/trips/" + B, {"expenses": [{"id": fb["id"], "section": "fuel", "sale_price": 35000}]}, u="khonl", method="PUT")
        phai(s, 200, "KT kho xăng dầu gõ giá bán dầu cho chủ xe 35.000 LAK/L", g)
        s, g = goi("/api/trips/" + B, {"expenses": [{"id": rb["id"], "section": "repair", "sale_price": round(gia_pt * 1.2)}]}, u="ketoancp", method="PUT")
        phai(s, 200, "KT Chi phí gõ giá bán phụ tùng cho chủ xe %s LAK" % round(gia_pt * 1.2), g)
        s, pa = goi("/api/trips/" + A, u="admin"); s, pb = goi("/api/trips/" + B, u="admin"); s, pc = goi("/api/trips/" + C, u="admin")
        dau_a, pt_a = dong_cua(pa, "fuel")[0], dong_cua(pa, "repair")[0]
        dau_b, pt_b = dong_cua(pb, "fuel")[0], dong_cua(pb, "repair")[0]
        dung(all(e["stock_move_id"] for e in (dau_a, pt_a, dau_b, pt_b)) and dong_cua(pc, "repair")[0]["stock_move_id"],
             "dòng kho đã rời kho (có mã lần xuất)")
        dung(abs(dau_a["unit_price"] - gia_dau) < 0.01 and abs(dau_b["unit_price"] - gia_dau) < 0.01 and abs(pt_a["unit_price"] - gia_pt) < 0.01,
             "giá vốn trên dòng = giá bình quân kho lúc xuất (kho tạm trả về)", "%s · %s" % (dau_a["unit_price"], pt_a["unit_price"]))
        dung(not kho(bt(A)) and not kho(bt(B)), "trước khi khoá: dầu đã cấp vẫn CHƯA có bút toán xuất kho (ghi lúc khoá)")

        print("2. Khoá phiếu → bút toán xuất kho")
        for tid in (A, B, C):
            s, g = goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan"); phai(s, 200, "KT Thu/Chi khoá phiếu", g)

        print("  A — xe nhà: xuất nội bộ theo giá vốn")
        ka = {b["ma_nguon"]: b for b in kho(bt(A))}
        x_dau, x_pt = ka.get("dau:" + dau_a["stock_move_id"]), ka.get("pt:" + pt_a["stock_move_id"])
        dung(len(ka) == 2 and x_dau and x_pt and all(b["nguon"] == "xuat_noi_bo" for b in ka.values()),
             "hai bút toán xuat_noi_bo — một lần xuất một bản (dầu, phụ tùng)", sorted(ka))
        d = (x_dau or {}).get("dong") or [{}]
        dung(len(d) == 1 and d[0]["no"] == "625" and d[0]["co"] == "1371" and d[0]["ccy"] == "LAK" and d[0]["tien"] == round(50 * gia_dau)
             and d[0]["doi_tuong"] is None and d[0].get("hinh_thuc") == "noi_bo" and d[0].get("ref") == dau_a["id"],
             "dầu: Nợ 625 / Có 1371 = 50 L × %s = %s LAK" % (gia_dau, round(50 * gia_dau)), json.dumps(d[0], ensure_ascii=False)[:160])
        d = (x_pt or {}).get("dong") or [{}]
        dung(len(d) == 1 and d[0]["no"] == "614" and d[0]["co"] == "1371" and d[0]["tien"] == round(gia_pt),
             "phụ tùng: Nợ 614 / Có 1371 = 1 × %s LAK" % gia_pt)
        dung(all(b["ngay"] == HOM_NAY and b["trip_id"] == A and b["source_ref"] == "EPLLAO-%s-%s" % (b["nguon"], b["ma_nguon"])
                 and "nội bộ" in (b["dien_giai"] or "") for b in ka.values()),
             "ngày chứng từ = ngày xuất thật, SourceRef EPLLAO-xuat_noi_bo-<lần xuất>, diễn giải ghi chữ 'nội bộ'")
        dung("PLNL-" in (x_dau or {}).get("dien_giai", ""), "diễn giải dầu ghi số phiếu đề nghị xuất kho", (x_dau or {}).get("dien_giai"))
        ncc = [x for b in bt(A, "no_ncc") for x in b["dong"]]
        dung(not any(x.get("ref") in (dau_a["id"], pt_a["id"]) for x in ncc), "dòng kho không nằm trong no_ncc (không ghi hai lần)")

        print("  B — xe thuê, EPL ứng: xuất bán theo giá bán + giá vốn")
        kb = {b["ma_nguon"]: b for b in kho(bt(B))}
        y_dau, y_pt = kb.get("dau:" + dau_b["stock_move_id"]), kb.get("pt:" + pt_b["stock_move_id"])
        dung(len(kb) == 2 and y_dau and y_pt and all(b["nguon"] == "xuat_ban" for b in kb.values()), "hai bút toán xuat_ban", sorted(kb))
        chu = {"loai": "chu_xe", "ref_id": pb["owner_id"]}
        for ten, b, sl, ban, von in (("dầu", y_dau, 40, 35000, gia_dau), ("phụ tùng", y_pt, 1, round(gia_pt * 1.2), gia_pt)):
            d = {x["ve"]: x for x in (b or {}).get("dong") or []}
            dt_, gv = d.get("doanh_thu") or {}, d.get("gia_von") or {}
            dung(len((b or {}).get("dong") or []) == 2 and dt_.get("no") == "4022" and dt_.get("co") == "707" and dt_.get("tien") == round(sl * ban)
                 and dt_.get("doi_tuong") == chu and not dt_.get("gia_ban_tam"),
                 "%s: Nợ 4022 / Có 707 = %s × %s (giá bán) = %s, đối tượng chủ xe" % (ten, sl, ban, round(sl * ban)))
            dung(gv.get("no") == "607" and gv.get("co") == "1371" and gv.get("tien") == round(sl * von) and gv.get("doi_tuong") is None,
                 "%s: Nợ 607 / Có 1371 = %s × %s (giá vốn bình quân) = %s" % (ten, sl, von, round(sl * von)))
            dung("chủ xe" in (b or {}).get("dien_giai", "") and all("Xuất bán cho chủ xe" in x["dien_giai"] for x in (b or {}).get("dong") or []),
                 "%s: chữ 'xuất bán cho chủ xe' ở bút toán và từng dòng" % ten)
        tru = {m: sum(x["tien"] for b in kb.values() for x in b["dong"] if x["ve"] == "doanh_thu" and x["section"] == m) for m in ("fuel", "repair")}
        dung(tru["fuel"] == pb["tinh"]["chi"]["fuel"] and tru["repair"] == pb["tinh"]["chi"]["repair"],
             "Có 707 khớp đúng số trừ vào tiền trả chủ xe (mục III, V của phiếu)", "%s · %s" % (tru, {m: pb["tinh"]["chi"][m] for m in tru}))
        s, ban = goi("/api/but-toan-cho?nguon=ban_chu_xe&gioi_han=1000", u="ketoan")
        ids = {dau_b["id"], pt_b["id"], dau_b["stock_move_id"], pt_b["stock_move_id"]}
        dung(s == 200 and not any(b["trip_id"] in (A, B, C) or b["ma_nguon"] in ids or any(x.get("ref") in ids for x in b["dong"])
                                  for b in ban["ds"]), "không trùng ban_chu_xe (bán ở quầy): không bản nào của các phiếu thử",
             "%d bản ban_chu_xe trong DB" % len(ban["ds"]))

        print("  C — xe thuê, chủ xe tự trả")
        dung(not kho(bt(C)), "không có bút toán xuất kho (phụ tùng đã rời kho nhưng chủ xe tự trả)")

        print("3. Ai đọc được (giá vốn không lộ)")
        for u in VAI:
            s, g = goi("/api/but-toan-cho?nguon=xuat_ban", u=u)
            dung(s == (200 if u in ("admin", "ketoan", "ketoancp") else 403), "GET bút toán xuất kho — %-8s (%s) → %s" % (u, VAI[u], s))
        for u in ("thabok", "totsua", "khonl", "khotb"):
            s, p = goi("/api/trips/" + B, u=u)
            dung(s != 200 or "but_toan_cho" not in p, "phiếu không mang khối bút toán cho %s" % u)
        s, g = goi("/api/but-toan-cho?nguon=xuat_noi_bo,xuat_ban&trip_id=" + A, u="ketoancp")
        dung(s == 200 and {b["nguon"] for b in g["ds"]} == {"xuat_noi_bo"}, "lọc theo nguồn mới được")

        if co_gui:
            print("4. Gói gửi sang máy giả hệ kế toán")
            for b in list(ka.values()) + list(kb.values()):
                r = bt(b["trip_id"], b["nguon"])
                b2 = next(x for x in r if x["id"] == b["id"])
                dung(b2["status"] == "da_gui" and str(b2["so_ben_ke_toan"]).startswith("GIA-XK"), "tự gửi lúc khoá: %s → %s" % (b["source_ref"], b2["so_ben_ke_toan"]))
            for ten, b in (("A dầu", x_dau), ("A phụ tùng", x_pt), ("B dầu", y_dau), ("B phụ tùng", y_pt)):
                g = (GIA.ct.get(b["source_ref"]) or {}).get("body") or {}
                en = g.get("Entries") or []
                mong = [(x["no"], x["co"], x["tien"]) for x in b["dong"]]
                dung([(e["DebitAccount"], e["CreditAccount"], e["Amount"]) for e in en] == mong
                     and all(e["CurrencyId"] == 26 and e["ExchangeRate"] == 1 for e in en) and g.get("DocumentDate") == HOM_NAY
                     and g.get("SourceRef") == b["source_ref"] and g.get("FiciAutoId") == 77,
                     "gói %s: tài khoản · tiền Kíp (mã tiền 26, tỷ giá 1) · ngày xuất · kỳ" % ten, json.dumps(mong))
                for e, x in zip(en, b["dong"]):
                    if x.get("ve") == "doanh_thu":
                        dung(e.get("ObjectId"), "gói %s: dòng 4022/707 mang đối tượng chủ xe (ObjectId %s)" % (ten, e.get("ObjectId")))
                    else:
                        dung(e.get("ObjectId") is None, "gói %s: dòng %s/%s không đối tượng" % (ten, e["DebitAccount"], e["CreditAccount"]))
                    dung(len(e.get("Note") or "") <= 250 and ("Xuất" in (e.get("Note") or "")), "gói %s: ghi chú dòng có chữ loại khoản" % ten)
            hd = [x for x in GIA.nhan if x[0] == "POST" and x[1] == DUONG]
            dung(hd and all(x[2].get("Idempotency-Key") == x[3]["SourceRef"] for x in hd), "Idempotency-Key = SourceRef")
        else:
            print("4. (cờ gửi tắt — bỏ phần gói; chạy lại với máy chủ bật cờ để kiểm gói)")

        print("5. Mở khoá → huỷ; khoá lại → cùng bản, không trùng")
        cu = {b["id"] for b in kho(bt(B))}
        s, g = goi("/api/trips/%s/mo-khoa" % B, {}, u="ketoan"); phai(s, 200, "KT Thu/Chi mở khoá B", g)
        r = kho(bt(B))
        dung(r and all(b["status"] == "huy" and not b["can_dao"] for b in r), "mở khoá: mọi bút toán xuất kho của B → huỷ",
             str({b["ma_nguon"]: b["status"] for b in r}))
        if co_gui:
            dung(all(GIA.ct[b["source_ref"]]["Reversed"] for b in kb.values()), "cờ bật: đã gỡ chứng từ bên kế toán")
        s, g = goi("/api/trips/%s/khoa" % B, {"xac_nhan": True}, u="ketoan"); phai(s, 200, "Khoá lại B", g)
        r = kho(bt(B))
        song = [b for b in r if b["status"] != "huy"]
        dung({b["id"] for b in r} == cu and len(song) == 2, "khoá lại: cùng hai bản ghi, sống lại (không sinh trùng)",
             str([(b["ma_nguon"], b["status"], b["phien"]) for b in r]))
        if co_gui:
            dung(all(b["status"] == "da_gui" and b["source_ref"].endswith("-2") for b in song), "cờ bật: gửi lại với SourceRef phiên mới '-2'")

        print("6. Xoá phiếu → bút toán xuất kho huỷ, hàng về kho")
        s, g = goi("/api/trips/%s/mo-khoa" % A, {}, u="admin")
        s, g = goi("/api/trips/" + A, u="admin", method="DELETE"); phai(s, 200, "Sếp xoá phiếu thử A (trả dầu, phụ tùng về kho tạm)", g)
        s, g = goi("/api/but-toan-cho?nguon=xuat_noi_bo&status=huy&gioi_han=1000", u="admin")
        dung(all(any(b["ma_nguon"] == m and b["status"] == "huy" for b in g["ds"]) for m in ka), "bút toán của phiếu đã xoá còn dấu vết, trạng thái huỷ")
    finally:
        don()
        if GIA.may:
            GIA.may.shutdown(); GIA.may.server_close()
    print("\n%s" % ("BÚT TOÁN XUẤT KHO: ĐẠT" if not LOI else "BÚT TOÁN XUẤT KHO: SAI %d chỗ:\n  - " % len(LOI) + "\n  - ".join(LOI)))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
