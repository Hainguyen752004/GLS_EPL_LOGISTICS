# -*- coding: utf-8 -*-
"""Thử BÚT TOÁN XUẤT KHO CHO CHUYẾN (chủ dự án 01/10: "xuất dầu là xuất nội bộ và còn là xuất bán") — dầu kho mục III và
phụ tùng kho mục V thành bút toán chờ gửi lúc KHOÁ PHIẾU, một lần xuất một bút toán (services/but_toan_cho.dong_xuat_kho).

    python kiem/thu_but_toan_xuat_kho.py [http://127.0.0.1:8015] [cổng máy giả 8095]

CHỈ chạy trên máy thử (bản sao DB). Máy điều xe phải nối kho tạm thử (8031) — bài cấp dầu và xuất phụ tùng thật ở đó, xoá phiếu
thử là trả lại kho. Máy chủ BẬT cờ QLSX_GUI_BUT_TOAN trỏ máy giả (scratchpad xk_8015.ps1 -Gui) thì bài dựng máy giả hệ kế toán
ở cổng tham số 2 và kiểm cả gói gửi đi; cờ tắt thì bỏ phần gói (in rõ).

  0 Luật 02/10 — xe thuê lấy kho EPL LUÔN là xuất bán: lập phiếu / đổi dòng / lấy phụ tùng kho với «chủ xe tự trả» → 422
    KHO_XE_THUE_XUAT_BAN (câu đủ ba tiếng, kho không bị trừ).
  0b Khoá khi dầu kho chưa cấp (xe nhà lẫn xe thuê) → 409 DAU_KHO_CHUA_CAP; phụ tùng ghi «lấy từ kho» trên bảng mục V mà chưa
    xuất → 409 PT_KHO_CHUA_XUAT. Kho tạm chặn cấp quá tồn: bài nhập trước 120 L vào kho Thà Bốc (kiem/_ke_toan.nhap_truoc, giá =
    bình quân hiện tại), dọn xong gỡ dòng nhập — kho Thà Bốc về đúng số trước bài.
  A xe nhà · dầu kho 50 L (cấp theo phiếu đề nghị) + 1 phụ tùng kho → hai bút toán `xuat_noi_bo`:
      dầu Nợ 625 / Có 1371 · phụ tùng Nợ 614 / Có 1371, tiền = số lượng × giá vốn bình quân kho lúc xuất.
  B xe thuê, EPL ứng · dầu kho 40 L + 1 phụ tùng kho + chipping ghi nợ NCC. Khoá khi chưa có giá bán → 409 THIEU_GIA_BAN (nói
      mục, ai gõ); KT kho xăng dầu / KT Chi phí gõ giá bán → khoá → hai bút toán `xuat_ban`: Nợ 4022 / Có 707 theo GIÁ BÁN
      (đối tượng chủ xe — đúng số trừ vào tiền trả chủ xe) + Nợ 607 / Có 1371 theo giá vốn.
  C xe thuê · dầu kho 30 L. Biến DATABASE_URL trỏ bản sao _d7 thì giả lập dữ liệu cũ (ghi thẳng DB dòng «chủ xe tự trả»): khoá
      bị chặn 409 KHO_XE_THUE_XUAT_BAN kèm cách sửa; KT kho xăng dầu bấm «EPL ứng» + giá bán → khoá → `xuat_ban`.
  Sau khoá: KT kho xăng dầu, KT Chi phí, Sếp đổi giá bán / đơn giá dòng kho hay dòng ghi nợ NCC → 409 DA_KHOA; lưu lại đúng số
      cũ thì được; thêm phụ tùng kho → 409; tiền thuê xe (giá thuê, phí, quá tải, cân cuối) → 409 DA_KHOA. Mở khoá → huỷ (cờ bật: gỡ bên kế toán), sửa được; khoá lại → cùng bản, số mới.
  Trước khi khoá: chưa có (dầu đã cấp vẫn chưa). Không trùng `ban_chu_xe` (bán ở quầy). Vai không thấy giá vốn (Bãi, thủ kho,
  tổ sửa, KT kho xăng dầu…) không đọc được. Dọn xong kho phụ tùng trả lại đủ.
"""
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ke_toan as K       # noqa: E402 — kho tạm chặn cấp quá tồn (VUOT_TON): nhập trước đúng số lít sẽ cấp, dọn thì gỡ

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


def ma(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return d.get("ma") if isinstance(d, dict) else None


def ba_tieng(g, *chu):
    """Câu lỗi có đủ ba tiếng (loi · loi_lo · loi_en) và câu Việt chứa các chữ `chu`."""
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return isinstance(d, dict) and all(d.get(k) for k in ("loi", "loi_lo", "loi_en")) and all(c in d["loi"] for c in chu)


def gia_lap_du_lieu_cu(eid):
    """Dòng kho xe thuê ghi "chủ xe tự trả" như dữ liệu trước 02/10 — API nay chặn nên phải ghi thẳng DB. Chỉ khi biến
    DATABASE_URL trỏ bản sao (_d7); không có thì bỏ bước (in rõ)."""
    url = os.environ.get("DATABASE_URL", "")
    if "_d7" not in url:
        return False
    from sqlalchemy import create_engine, text
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text("UPDATE trip_expenses SET paid_by_epl = false WHERE id = :i"), {"i": eid})
    eng.dispose()
    return True


def ton_pt(pid):
    s, ds = goi("/api/parts", u="admin")
    return next((x.get("qty") for x in ds or [] if x["id"] == pid), None)


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
    # kho dầu Thà Bốc; kho tạm chặn cấp quá tồn (VUOT_TON) → nhập trước đúng 120 lít sẽ cấp, theo giá bình quân hiện tại (giá
    # vốn kho không đổi), dọn xong gỡ dòng nhập — kho về đúng số trước bài (như thu_phieu_linh.py)
    k0 = K.kho_dau("KHO-TB")
    kho_dau = next((k for k in kx["nhien_lieu"] if k.get("place_id") == k0["id"] and (k0.get("gia_bq") or 0) > 0), None)
    s, pts = goi("/api/parts", u="admin")
    pt = next((x for x in pts if (x.get("qty") or 0) >= 3 and (x.get("unit_price") or 0) > 0), None)
    if not kho_dau or not pt:
        sys.exit("DỪNG: kho tạm thử: kho dầu Thà Bốc chưa có giá bình quân, hoặc không có phụ tùng tồn ≥ 3 có giá — %s · %s" % (bool(kho_dau), bool(pt)))
    print("  · kho dầu %s giá bình quân %s · phụ tùng %s tồn %s giá %s" % (kho_dau["name"], kho_dau["gia_bq"], pt["name"], pt["qty"], pt["unit_price"]))
    nha = next(v for v in xe if v["owner_type"] == "EPL" and v["active"])
    thue = next(v for v in xe if v["owner_type"] == "joint" and v["active"] and v.get("owner_id"))
    taixe = [t for t in tx if t["active"]]
    dau = lambda lit, **k: dict({"section": "fuel", "item_key": "diesel", "qty": lit, "place_id": kho_dau["place_id"]}, **k)
    chip = {"section": "travel", "item_key": "x_chip_lao", "qty": 1, "unit_price": 150000, "currency": "LAK"}   # ghi nợ NCC (no_ncc)
    A = lap(TIEN_TO + "A/EPL", "EPL", nha, taixe[0], kh[0], [dau(50)])
    B = lap(TIEN_TO + "B/EPL", "joint", thue, taixe[1], kh[0], [dau(40), chip])
    C, NHAP = None, None
    try:
        print("0. Luật 02/10: xe thuê lấy kho EPL luôn là xuất bán — không có «chủ xe tự trả»")
        s, g = goi("/api/trips", {"doc_no": TIEN_TO + "C/EPL", "kind": "giao", "company": "joint", "vehicle_id": thue["id"],
                                  "driver_id": taixe[2]["id"], "customer_id": kh[0]["id"], "doc_date": HOM_NAY, "weight_origin": 40,
                                  "price": 40, "price_ccy": "USD", "hire_price": 30, "hire_ccy": "USD",
                                  "expenses": [dau(30, paid_by_epl=False)]}, u="admin")
        dung(s == 422 and ma(g) == "KHO_XE_THUE_XUAT_BAN" and ba_tieng(g, "mục III dòng 1", "phiếu bán ở quầy"),
             "lập phiếu xe thuê có dầu kho «chủ xe tự trả» → 422, câu đủ ba tiếng", "%s %s" % (s, ma(g)))
        C = lap(TIEN_TO + "C/EPL", "joint", thue, taixe[2], kh[0], [dau(30)])
        s, pc = goi("/api/trips/" + C, u="admin")
        f_c = dong_cua(pc, "fuel")[0]
        s, g = goi("/api/trips/" + C, {"expenses": [dict(f_c, paid_by_epl=False)]}, u="thabok", method="PUT")
        dung(s == 422 and ma(g) == "KHO_XE_THUE_XUAT_BAN", "Bãi đổi dòng dầu kho xe thuê sang «chủ xe tự trả» → 422", "%s %s" % (s, ma(g)))
        ton0 = ton_pt(pt["id"])
        s, g = goi("/api/trips/%s/events" % C, {"kind": "repair", "incident_type": "tire", "note": "thử luật 02/10",
                                                "repair": {"source": "kho", "part_id": pt["id"], "qty": 1, "paid_by_epl": False}}, u="totsua")
        dung(s == 422 and ma(g) == "KHO_XE_THUE_XUAT_BAN" and ton_pt(pt["id"]) == ton0,
             "tổ sửa lấy phụ tùng kho «chủ xe tự trả» cho xe thuê → 422, kho không bị trừ", "%s %s · tồn %s → %s" % (s, ma(g), ton0, ton_pt(pt["id"])))

        print("0b. Khoá khi hàng lấy kho chưa rời kho → chặn (dầu chưa cấp theo phiếu đề nghị)")
        for tid, ten in ((A, "xe nhà"), (B, "xe thuê")):
            s, g = goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan")
            dung(s == 409 and ma(g) == "DAU_KHO_CHUA_CAP" and ba_tieng(g, "mục III dòng 1 (", "KT kho xăng dầu", "Cấp phát"),
                 "khoá %s khi dầu kho chưa cấp → 409 DAU_KHO_CHUA_CAP, nói dòng nào, ai cấp (đủ ba tiếng)" % ten,
                 ((g or {}).get("detail") or {}).get("loi", "")[:120])

        print("1. Xuất kho thật ở kho tạm (nhập trước, cấp dầu theo phiếu đề nghị, lấy phụ tùng)")
        gia_dau, gia_pt = kho_dau["gia_bq"], pt["unit_price"]
        NHAP = K.nhap_truoc(k0["id"], 120, "thử bút toán xuất kho: nhập trước rồi cấp 50 + 40 + 30 L")
        for tid, lit in ((A, 50), (B, 40), (C, 30)):
            cap_dau(tid, lit)
        for tid in (A, B):
            lay_phu_tung(tid, pt["id"])
        s, pa = goi("/api/trips/" + A, u="admin"); s, pb = goi("/api/trips/" + B, u="admin"); s, pc = goi("/api/trips/" + C, u="admin")
        dau_a, pt_a = dong_cua(pa, "fuel")[0], dong_cua(pa, "repair")[0]
        # phụ tùng ghi "lấy kho" ngay trên bảng mục V (không qua «Sửa xe») thì chưa rời kho → khoá bị chặn; bỏ dòng thì khoá được
        s, g = goi("/api/trips/" + A, {"expenses": [pt_a, {"section": "repair", "source": "kho", "part_id": pt["id"], "qty": 1}]},
                   u="admin", method="PUT")
        phai(s, 200, "Sếp ghi thêm một dòng phụ tùng «lấy từ kho» trên bảng mục V của A (chưa xuất kho)", g)
        s, g = goi("/api/trips/%s/khoa" % A, {"xac_nhan": True}, u="ketoan")
        dung(s == 409 and ma(g) == "PT_KHO_CHUA_XUAT" and ba_tieng(g, "mục V dòng 2", "Sửa xe"),
             "khoá A khi phụ tùng ghi lấy kho mà chưa xuất → 409 PT_KHO_CHUA_XUAT (đủ ba tiếng)", "%s %s" % (s, ma(g)))
        s, g = goi("/api/trips/" + A, {"expenses": [pt_a]}, u="admin", method="PUT")
        phai(s, 200, "bỏ dòng phụ tùng chưa xuất", g)
        dau_b, pt_b, chip_b = dong_cua(pb, "fuel")[0], dong_cua(pb, "repair")[0], dong_cua(pb, "travel")[0]
        dau_c = dong_cua(pc, "fuel")[0]
        dung(all(e["stock_move_id"] for e in (dau_a, pt_a, dau_b, pt_b, dau_c)), "dòng kho đã rời kho (có mã lần xuất)")
        dung(abs(dau_a["unit_price"] - gia_dau) < 0.01 and abs(dau_b["unit_price"] - gia_dau) < 0.01 and abs(pt_a["unit_price"] - gia_pt) < 0.01,
             "giá vốn trên dòng = giá bình quân kho lúc xuất (kho tạm trả về)", "%s · %s" % (dau_a["unit_price"], pt_a["unit_price"]))
        dung(not kho(bt(A)) and not kho(bt(B)), "trước khi khoá: dầu đã cấp vẫn CHƯA có bút toán xuất kho (ghi lúc khoá)")

        print("2. Khoá phiếu: chặn khi xuất bán chưa có giá bán / dòng cũ «chủ xe tự trả»")
        s, g = goi("/api/trips/%s/khoa" % B, {"xac_nhan": True}, u="ketoan")
        dung(s == 409 and ma(g) == "THIEU_GIA_BAN" and ba_tieng(g, "mục III dòng 1", "KT kho xăng dầu", "mục V dòng 1", "KT Chi phí"),
             "khoá B khi dầu, phụ tùng xuất bán chưa có giá bán → 409 THIEU_GIA_BAN, nói mục nào, ai gõ (đủ ba tiếng)",
             ((g or {}).get("detail") or {}).get("loi", "")[:150])
        s, g = goi("/api/trips/" + B, {"expenses": [{"id": dau_b["id"], "section": "fuel", "sale_price": 35000}]}, u="khonl", method="PUT")
        phai(s, 200, "KT kho xăng dầu gõ giá bán dầu cho chủ xe 35.000 LAK/L", g)
        s, g = goi("/api/trips/" + B, {"expenses": [{"id": pt_b["id"], "section": "repair", "sale_price": round(gia_pt * 1.2)}]}, u="ketoancp", method="PUT")
        phai(s, 200, "KT Chi phí gõ giá bán phụ tùng cho chủ xe %s LAK" % round(gia_pt * 1.2), g)
        cu_c = gia_lap_du_lieu_cu(dau_c["id"])
        if cu_c:
            s, g = goi("/api/trips/%s/khoa" % C, {"xac_nhan": True}, u="ketoan")
            dung(s == 409 and ma(g) == "KHO_XE_THUE_XUAT_BAN" and ba_tieng(g, "mục III dòng 1", "EPL ứng"),
                 "dữ liệu cũ: dầu kho xe thuê ghi «chủ xe tự trả» → khoá bị chặn, chỉ cách sửa (đủ ba tiếng)", "%s %s" % (s, ma(g)))
            s, g = goi("/api/trips/" + C, {"expenses": [{"id": dau_c["id"], "section": "fuel", "paid_by_epl": False, "sale_price": 36000}]},
                       u="khonl", method="PUT")
            dung(s == 200, "gửi nguyên «chủ xe tự trả» của dòng cũ không làm hỏng lần lưu (để khoá chặn)", s)
        else:
            print("  · bỏ bước dữ liệu cũ: không có DATABASE_URL bản sao _d7 để giả lập dòng ghi «chủ xe tự trả» từ trước 02/10")
        s, g = goi("/api/trips/" + C, {"expenses": [{"id": dau_c["id"], "section": "fuel", "paid_by_epl": True, "sale_price": 36000}]},
                   u="khonl", method="PUT")
        phai(s, 200, "KT kho xăng dầu bấm «EPL ứng» + gõ giá bán 36.000 cho dầu của C", g)
        s, pc = goi("/api/trips/" + C, u="admin")
        dung(dong_cua(pc, "fuel")[0]["paid_by_epl"] is True and dong_cua(pc, "fuel")[0]["sale_price"] == 36000, "dòng dầu C: EPL ứng, có giá bán")
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
        s, pb = goi("/api/trips/" + B, u="admin")
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

        print("  C — xe thuê, dòng dầu kho đã sửa về EPL ứng (luật 02/10)")
        kc = kho(bt(C))
        dc = {x["ve"]: x for b in kc for x in b["dong"]}
        dung(len(kc) == 1 and kc[0]["nguon"] == "xuat_ban" and (dc.get("doanh_thu") or {}).get("tien") == 30 * 36000
             and (dc.get("gia_von") or {}).get("tien") == round(30 * gia_dau),
             "C có xuat_ban: 4022/707 = 30 × 36.000 · 607/1371 = 30 × giá vốn", str([(x["no"], x["co"], x["tien"]) for x in dc.values()]))

        print("3. Sau khoá: không ai sửa được giá các dòng đã vào bút toán khoá phiếu")
        for u, body, ten in (
                ("khonl", {"expenses": [{"id": dau_b["id"], "section": "fuel", "sale_price": 40000}]}, "KT kho xăng dầu đổi giá bán dầu"),
                ("ketoancp", {"expenses": [{"id": pt_b["id"], "section": "repair", "sale_price": round(gia_pt * 1.5)}]}, "KT Chi phí đổi giá bán phụ tùng"),
                ("ketoancp", {"expenses": [dict(chip_b, unit_price=175000)]}, "KT Chi phí đổi đơn giá dòng ghi nợ NCC (chipping)"),
                ("admin", {"expenses": [dict(dau_b, sale_price=41000)]}, "Sếp đổi giá bán dầu")):
            s, g = goi("/api/trips/" + B, body, u=u, method="PUT")
            dung(s == 409 and ma(g) == "DA_KHOA" and ba_tieng(g, "mở khoá"), "%s sau khoá → 409 DA_KHOA (đủ ba tiếng)" % ten, "%s %s" % (s, ma(g)))
        s, pb2 = goi("/api/trips/" + B, u="admin")
        dung(dong_cua(pb2, "fuel")[0]["sale_price"] == 35000 and dong_cua(pb2, "travel")[0]["unit_price"] == 150000, "số trên phiếu không đổi")
        s, g = goi("/api/trips/" + B, {"expenses": [{"id": dau_b["id"], "section": "fuel", "sale_price": 35000}]}, u="khonl", method="PUT")
        dung(s == 200, "lưu lại đúng số cũ sau khoá → không bị chặn", s)
        s, g = goi("/api/trips/" + B, {"expenses": [dict(chip_b)]}, u="admin", method="PUT")
        dung(s == 200, "Sếp lưu lại mục IV không đổi số (dòng được tạo lại mã mới) → không bị chặn", "%s %s" % (s, ma(g)))
        s, g = goi("/api/trips/%s/events" % B, {"kind": "repair", "incident_type": "tire", "note": "thêm sau khoá",
                                                "repair": {"source": "kho", "part_id": pt["id"], "qty": 1}}, u="totsua")
        dung(s == 409 and ma(g) == "DA_KHOA", "tổ sửa lấy thêm phụ tùng kho cho phiếu đã khoá → 409, kho không bị trừ", "%s %s" % (s, ma(g)))

        for u, body, ten in (("ketoan", {"hire_price": 31}, "KT Thu/Chi đổi giá thuê 30 → 31 USD/t"),
                             ("ketoan", {"fee_pct": 3}, "KT Thu/Chi đổi phí 2 % → 3 %"),
                             ("admin", {"over_limit_t": 35}, "Sếp đổi ngưỡng quá tải 40 → 35 t")):
            s, g = goi("/api/trips/" + B, body, u=u, method="PUT")
            dung(s == 409 and ma(g) == "DA_KHOA" and ba_tieng(g, "tiền thuê xe"), "%s sau khoá → 409 DA_KHOA (tiền thuê xe)" % ten,
                 "%s %s" % (s, ma(g)))
        s, g = goi("/api/trips/%s/transport-status" % B, {"status": "arrived", "weight_dest": 39, "odo_back": 1500, "back_date": HOM_NAY},
                   u="admin")
        dung(s == 409 and ma(g) == "DA_KHOA", "Sếp sửa cân cuối xe thuê 40 → 39 t sau khoá → 409 (đổi tiền thuê, phí)", "%s %s" % (s, ma(g)))
        s, pb3 = goi("/api/trips/" + B, u="admin")
        dung(pb3["hire_price"] == 30 and pb3["weight_dest"] == 40 and (pb3.get("fee_pct") in (None, 2, 2.0)),
             "số thuê xe trên phiếu không đổi", "%s · %s · %s" % (pb3["hire_price"], pb3["weight_dest"], pb3.get("fee_pct")))
        s, g = goi("/api/trips/" + B, {"hire_price": 30}, u="ketoan", method="PUT")
        dung(s == 200, "lưu lại đúng giá thuê cũ sau khoá → không bị chặn", s)

        print("3b. Ai đọc được (giá vốn không lộ)")
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

        print("5. Mở khoá → huỷ; sửa giá; khoá lại → cùng bản theo số mới")
        cu = {b["id"] for b in kho(bt(B))}
        s, g = goi("/api/trips/%s/mo-khoa" % B, {}, u="ketoan"); phai(s, 200, "KT Thu/Chi mở khoá B", g)
        r = kho(bt(B))
        dung(r and all(b["status"] == "huy" and not b["can_dao"] for b in r), "mở khoá: mọi bút toán xuất kho của B → huỷ",
             str({b["ma_nguon"]: b["status"] for b in r}))
        if co_gui:
            dung(all(GIA.ct[b["source_ref"]]["Reversed"] for b in kb.values()), "cờ bật: đã gỡ chứng từ bên kế toán")
        s, g = goi("/api/trips/" + B, {"expenses": [{"id": dau_b["id"], "section": "fuel", "sale_price": 40000}]}, u="khonl", method="PUT")
        dung(s == 200, "mở khoá rồi KT kho xăng dầu đổi giá bán dầu 40.000 → được", s)
        s, g = goi("/api/trips/%s/khoa" % B, {"xac_nhan": True}, u="ketoan"); phai(s, 200, "Khoá lại B", g)
        r = kho(bt(B))
        song = [b for b in r if b["status"] != "huy"]
        moi_dau = next((x for b in song if b["ma_nguon"] == "dau:" + dau_b["stock_move_id"] for x in b["dong"] if x["ve"] == "doanh_thu"), {})
        dung({b["id"] for b in r} == cu and len(song) == 2 and moi_dau.get("tien") == 40 * 40000,
             "khoá lại: cùng hai bản ghi, sống lại, 4022/707 dầu theo giá mới 40 × 40.000",
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
        if NHAP:
            print("  · gỡ dòng nhập thử → %s" % K.go_nhap(NHAP))
        if GIA.may:
            GIA.may.shutdown(); GIA.may.server_close()
    print("  · tồn phụ tùng sau khi dọn: %s (trước bài %s)" % (ton_pt(pt["id"]), pt["qty"]))
    dung(ton_pt(pt["id"]) == pt["qty"], "dọn xong: kho phụ tùng trả lại đủ")
    k1 = K.kho_dau("KHO-TB")
    dung(abs(k1["ton_lit"] - k0["ton_lit"]) < 0.001 and abs((k1.get("gia_bq") or 0) - (k0.get("gia_bq") or 0)) < 0.01,
         "dọn xong: kho dầu Thà Bốc về đúng số trước bài", "%s L → %s L · giá %s → %s" % (k0["ton_lit"], k1["ton_lit"], k0.get("gia_bq"), k1.get("gia_bq")))
    print("\n%s" % ("BÚT TOÁN XUẤT KHO: ĐẠT" if not LOI else "BÚT TOÁN XUẤT KHO: SAI %d chỗ:\n  - " % len(LOI) + "\n  - ".join(LOI)))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
