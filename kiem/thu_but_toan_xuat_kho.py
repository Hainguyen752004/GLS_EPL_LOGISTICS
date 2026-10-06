# -*- coding: utf-8 -*-
"""Thử BÚT TOÁN XUẤT KHO CHO CHUYẾN (chủ dự án 01/10: "xuất dầu là xuất nội bộ và còn là xuất bán") — dầu kho mục III và
phụ tùng kho mục V thành bút toán chờ gửi lúc KHOÁ PHIẾU, một lần xuất một bút toán (services/but_toan_cho.dong_xuat_kho).

    python kiem/thu_but_toan_xuat_kho.py

06/10 (anh Hải duyệt): chạy TRONG TIẾN TRÌNH (kiem/_tien_trinh_tune.py) — trước đây cần máy thử 8015 nối kho tạm 8031 + máy giả
8095. Kho tạm đã bỏ (05/10): kho EPL ở hệ anh Tune (QLSX). Nay: TestClient trên bản sao _d7, MỘT giao dịch ngoài cuối ROLLBACK
(không ghi gì vào d7, không gọi 5090); xe / chủ xe / tài xế / khách / kho dầu / phụ tùng thử TẠO MỚI trong giao dịch.
  · Kho QLSX GIẢ trong bài (services/kho_qlsx._goi): tồn + giá vốn bình quân, phiếu xuất 48 phụ tùng (xuất / huỷ theo SourceRef).
  · Thủ kho bên Web anh Tune GIẢ: đọc tờ PLNL qua /api/handover/fuel-vouchers/{id} (khoá máy QLSX thay bằng override trong bài),
    lập phiếu xuất dầu theo giá vốn bình quân của đúng kho, báo về …/issued; xoá phiếu xuất → báo …/cancelled.
  · Cờ QLSX_GUI_BUT_TOAN=1 trong tiến trình bài, trỏ máy giả HTTP hệ kế toán ở 127.0.0.1 (cổng hệ điều hành cấp) — khoá phiếu tự gửi.

  0 Luật 02/10 — xe thuê lấy kho EPL LUÔN là xuất bán: lập phiếu / đổi dòng / lấy phụ tùng kho với «chủ xe tự trả» → 422
    KHO_XE_THUE_XUAT_BAN (câu đủ ba tiếng, kho không bị trừ).
  0b Khoá khi dầu kho chưa cấp (xe nhà lẫn xe thuê) → 409 DAU_KHO_CHUA_CAP (chỉ đường Web: Quản lý kho → Cấp dầu theo phiếu đề
    nghị); phụ tùng ghi «lấy từ kho» trên bảng mục V mà chưa xuất → 409 PT_KHO_CHUA_XUAT.
  1 Cấp dầu theo tờ PLNL ở kho QLSX (gói tờ: kho, INTERNAL / PARTNER_SALE + EPLCX-<chủ xe>), phụ tùng xuất qua kho QLSX; dòng mang
    qlsx:<số phiếu kho>, đơn giá = giá vốn bình quân bên đó; trước khoá chưa có bút toán xuất kho.
  2 Xe thuê thiếu giá bán → 409 THIEU_GIA_BAN (nói mục, ai gõ); dòng cũ «chủ xe tự trả» (ghi thẳng dòng THỬ trong giao dịch) →
    409 KHO_XE_THUE_XUAT_BAN kèm cách sửa; KT kho xăng dầu bấm «EPL ứng» + giá bán → khoá.
  A xe nhà → `xuat_noi_bo`: dầu Nợ 625 / Có 1371 · phụ tùng Nợ 614 / Có 1371 = số lượng × giá vốn bình quân lúc xuất.
  B, C xe thuê → `xuat_ban`: CHỈ vế giá vốn Nợ 607 / Có 1371 (02/10: phần bán theo giá bán là SO nhiên liệu bên kế toán — không
    còn Nợ 4022 / Có 707 trong bút toán này); số trừ tiền trả chủ xe theo giá bán.
  3 Sau khoá: đổi giá bán / đơn giá dòng kho / dòng ghi nợ NCC, thêm phụ tùng kho, tiền thuê xe → 409 DA_KHOA; lưu lại số cũ được.
  3b Ai đọc được (giá vốn không lộ). 4 Gói gửi máy giả: tài khoản · tiền Kíp · ngày · kỳ · không đối tượng · Idempotency-Key.
  5 Mở khoá → huỷ + gỡ bên kế toán; đổi giá bán; khoá lại → cùng bản, SourceRef '-2', tiền giá vốn không đổi.
  6 DO đã khoá → kho QLSX không huỷ được phiếu cấp dầu (409 DA_KHOA). Xoá DO còn dầu cấp ở kho QLSX → 409 DA_CAP_KHO_QLSX; thủ
    kho huỷ phiếu xuất bên đó → tờ về chờ cấp → xoá được, phụ tùng huỷ theo SourceRef (trả tồn), bút toán còn dấu vết «huỷ».
"""
import datetime as dt
import json
import os
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _tien_trinh_tune as TT                           # noqa: E402 — chặn mạng, khung giao dịch ROLLBACK

import models as M                                      # noqa: E402
from main import app                                    # noqa: E402
from services import gui_tune as GT                     # noqa: E402
from services import kho_qlsx as KQ                     # noqa: E402
from services.bao_mat import may_qlsx_goi               # noqa: E402

LOI = []
HOM_NAY = dt.date.today().isoformat()
DUONG = "/api/v1/integrations/logistics/journal-entries"
VAI = {"admin": "admin", "ketoan": "acct", "ketoancp": "expacct", "khonl": "fuel", "khotb": "depot", "khopt": "parts",
       "totsua": "repair", "thabok": "yard", "quyvc": "treasury"}
CA = None                     # TT.Ca đang chạy


# ================================================================ máy giả hệ kế toán — bút toán (giao ước b9227aa, gọn)
class GIA:
    ct, nhan, so, may, cong = {}, [], 9000, None, None


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
    GIA.may = ThreadingHTTPServer(("127.0.0.1", 0), Xu)
    GIA.cong = GIA.may.server_address[1]
    TT.cho_phep_may_gia(GIA.cong)
    GT.cau_hinh = lambda dang_nhap=True: ("http://127.0.0.1:%d" % GIA.cong, "token-gia")
    threading.Thread(target=GIA.may.serve_forever, daemon=True).start()


def tat_gia():
    if GIA.may is not None:
        GIA.may.shutdown(); GIA.may.server_close(); GIA.may = None
        TT.bo_may_gia(GIA.cong)


# ================================================================ kho QLSX giả (services/kho_qlsx._goi) + thủ kho bên Web anh Tune
class KHO:
    ton = {}          # (mã kho, mã hàng) → [số lượng, giá vốn bình quân]
    phieu = {}        # SourceRef → kết quả phiếu xuất phụ tùng
    huy = []          # SourceRef phụ tùng đã huỷ
    nhan = []         # (method, đường, thân, khoá)
    dau = {}          # SourceRef tờ PLNL → {so, dong:[(khoá tồn, lít)]} — phiếu xuất dầu thủ kho lập
    n = 0


def _env(ma, kq=None, loi=None, cau=None):
    if loi:
        return ma, {"Success": False, "Code": ma, "Message": cau, "ErrorDetail": {"ErrorCode": loi}}
    return ma, {"Success": True, "Code": ma, "Message": "OK", "Result": kq}


def kho_goi(method, duong, body=None, key=None):
    KHO.nhan.append((method, duong, body, key))
    if duong.startswith(KQ.DUONG + "/stock-balance"):
        from urllib.parse import parse_qs, unquote, urlsplit
        q = parse_qs(urlsplit(duong).query)
        kho = set(unquote(q["warehouseCodes"][0]).split(",")) if "warehouseCodes" in q else None
        hang = set(unquote(q["itemCodes"][0]).split(",")) if "itemCodes" in q else None
        rows = [{"warehouseCode": k, "itemCode": h, "qty": v[0], "avgUnitCost": v[1], "amount": round(v[0] * v[1])}
                for (k, h), v in KHO.ton.items() if (kho is None or k in kho) and (hang is None or h in hang)]
        return _env(200, {"rows": rows})
    if duong == KQ.DUONG + "/stock-issues" and method == "POST":
        if key in KHO.phieu and key not in KHO.huy:
            return _env(200, dict(KHO.phieu[key], replayed=True))
        for d in body["Lines"]:
            v = KHO.ton.get((d["WarehouseCode"], d["ItemCode"]), [0, 0])
            if v[0] + 1e-9 < d["Qty"]:
                return _env(409, loi="LOGISTICS_STOCK_INSUFFICIENT", cau="%s tại %s còn %s, cần %s." % (d["ItemCode"], d["WarehouseCode"], v[0], d["Qty"]))
        KHO.n += 1
        lines = []
        for d in body["Lines"]:
            v = KHO.ton[(d["WarehouseCode"], d["ItemCode"])]
            v[0] -= d["Qty"]
            lines.append({"itemCode": d["ItemCode"], "warehouseCode": d["WarehouseCode"], "qty": d["Qty"], "unitCost": v[1],
                          "amount": round(d["Qty"] * v[1], 2)})
        kq = {"documentId": 9000 + KHO.n, "documentNo": "PXK-GIA-%d" % KHO.n, "sourceRef": key, "purpose": body["Purpose"],
              "objectCode": body.get("ObjectCode"), "lines": lines, "replayed": False}
        KHO.phieu[key] = kq
        if key in KHO.huy:
            KHO.huy.remove(key)
        return _env(201, kq)
    if duong == KQ.DUONG + "/stock-issues/cancel":
        sr = body["SourceRef"]
        if sr not in KHO.phieu:
            return 404, {"Success": False, "Code": 404, "Message": "không thấy", "ErrorDetail": {"ErrorCode": "LOGISTICS_STOCK_NOT_FOUND"}}
        if sr not in KHO.huy:
            for x in KHO.phieu[sr]["lines"]:
                KHO.ton[(x["warehouseCode"], x["itemCode"])][0] += x["qty"]
            KHO.huy.append(sr)
        return _env(200, dict(KHO.phieu[sr], state="CANCELLED"))
    return 404, {"Success": False, "Code": 404, "Message": "giả: không có đường %s" % duong}


def thu_kho_cap(vid):
    """Thủ kho bấm «Cấp dầu theo phiếu đề nghị» trên Web anh Tune: API bên đó đọc tờ ở đây, lập phiếu xuất 48 (giá vốn bình quân
    của đúng kho), báo về …/issued. → (gói tờ trước khi cấp, kết quả báo về)."""
    s, g = goi("/api/handover/fuel-vouchers/" + vid)
    phai(s, 200, "kho QLSX đọc tờ PLNL", g)
    v = g["data"]
    if not v["can_issue"]:
        raise SystemExit("DỪNG: tờ %s không cấp được: %s" % (v["voucher_no"], v["block_reason"]))
    KHO.n += 1
    so = "PXK-GIA-NL-%d" % KHO.n
    dong, ds = [], []
    for x in v["lines"]:
        k = (v["warehouse_code"], x["item_code"])
        t = KHO.ton[k]
        if t[0] + 1e-9 < x["qty_l"]:
            raise SystemExit("DỪNG: kho giả %s không đủ dầu" % (k,))
        t[0] -= x["qty_l"]
        dong.append((k, x["qty_l"]))
        ds.append({"item_code": x["item_code"], "qty": x["qty_l"], "unit_cost": t[1]})
    KHO.dau[v["source_ref"]] = {"so": so, "dong": dong}
    s, r = goi("/api/handover/fuel-vouchers/%s/issued" % vid, {"source_ref": v["source_ref"], "stock_doc_no": so, "stock_doc_id": 9500 + KHO.n,
                                                               "qty_l": v["qty_l"], "issued_by": "Thủ kho giả", "lines": ds})
    phai(s, 200, "kho QLSX báo đã cấp %s lít theo %s (phiếu kho %s)" % (v["qty_l"], v["voucher_no"], so), r)
    return v, r["data"]


def thu_kho_huy(sr):
    """Thủ kho xoá phiếu xuất dầu của tờ (SourceRef) trên Web anh Tune → bên đó báo …/cancelled; trang điều xe nhận thì tồn trả lại."""
    x = KHO.dau[sr]
    s, r = goi("/api/handover/fuel-vouchers/%s/cancelled" % sr, {"source_ref": sr, "stock_doc_no": x["so"], "reason": "thử bút toán xuất kho",
                                                                 "cancelled_by": "Thủ kho giả"})
    if s == 200:
        for k, lit in x["dong"]:
            KHO.ton[k][0] += lit
    return s, r


# ================================================================ gọi trang điều xe (TestClient, cùng phiên trong giao dịch)
def goi(duong, body=None, u=None, method=None):
    return CA.goi(duong, body, u, method)


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, them))
    sys.stdout.flush()
    if not dk:
        LOI.append(buoc)


def phai(s, mong, buoc, g=None):
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, json.dumps(g, ensure_ascii=False, default=str)[:500]))
    print("  ✓ %s %s" % (buoc, s))


def bt(tid, nguon=None):
    s, g = goi("/api/but-toan-cho?gioi_han=1000&trip_id=" + tid + ("&nguon=" + nguon if nguon else ""), u="ketoan")
    if s != 200:
        phai(s, 200, "KT Thu/Chi đọc bút toán chờ của phiếu", g)
    return g["ds"]


def kho(ds):
    return [b for b in ds if b["nguon"] in ("xuat_noi_bo", "xuat_ban")]


def dong_cua(p, section):
    return [e for e in p["expenses"] if e["section"] == section]


def ma(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return d.get("ma") if isinstance(d, dict) else None


def ba_tieng(g, *chu):
    """Câu lỗi có đủ ba tiếng (loi · loi_lo · loi_en) và câu Việt chứa các chữ `chu`."""
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return isinstance(d, dict) and all(d.get(k) for k in ("loi", "loi_lo", "loi_en")) and all(c in d["loi"] for c in chu)


def loi(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return (d.get("loi") if isinstance(d, dict) else str(g)) or ""


def lap(so, cong_ty, xe, tx, kh, dong):
    body = {"doc_no": so, "kind": "giao", "company": cong_ty, "vehicle_id": xe.id, "driver_id": tx.id, "customer_id": kh.id,
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


def lap_to_dau(tid):
    s, vs = goi("/api/trips/%s/vouchers" % tid, {"kind": "fuel"}, u="thabok")
    phai(s, 200, "Bãi lập phiếu đề nghị xuất kho nhiên liệu", vs)
    return vs[0]


def lay_phu_tung(tid, pid):
    s, g = goi("/api/trips/%s/events" % tid, {"kind": "repair", "incident_type": "tire", "note": "thử bút toán xuất kho",
                                              "repair": {"source": "kho", "part_id": pid, "qty": 1, "paid_by_epl": True}}, u="totsua")
    phai(s, 200, "Tổ sửa lấy 1 phụ tùng kho (EPL ứng) — xuất ở kho QLSX", g)
    return g


def main():
    global CA
    os.environ["QLSX_GUI_BUT_TOAN"] = "1"
    TT.CHI._goi = TT.CHI_GOI_THAT                      # tiền / kỳ / đối tượng đi qua urllib tới máy giả trong bài
    KQ._goi = kho_goi
    bat_gia()
    try:
        with TT.Ca(tuple(VAI)) as CA:
            app.dependency_overrides[may_qlsx_goi] = lambda: "qlsx"     # khoá máy QLSX: bài đóng vai API bên đó
            chay()
    finally:
        tat_gia()
    print("\n%s" % ("BÚT TOÁN XUẤT KHO: ĐẠT" if not LOI else "BÚT TOÁN XUẤT KHO: SAI %d chỗ:\n  - " % len(LOI) + "\n  - ".join(LOI)))
    print("đã ROLLBACK — bản sao d7 không đổi; %d lời gọi mạng ngoài máy giả bị chặn%s" % (len(TT.MANG), (" " + str(TT.MANG[:3])) if TT.MANG else ""))
    sys.exit(1 if LOI or TT.MANG else 0)


def chay():
    db = CA.db
    d = TT.du_lieu_thu(db, "BTXK")
    tx3 = M.Driver(name="ທ້າວ ທົດລອງ %s 3" % d.tag, name_latin="Thu %s 3" % d.tag)
    noi = M.FuelPlace(code=d.tag + "-KHO", name="Kho dầu thử %s" % d.tag, country="LA", owner_type="epl")
    ptu = M.Part(name="Phụ tùng thử %s" % d.tag, unit="u_pc", qty=0, unit_price=0)
    db.add_all([tx3, noi, ptu])
    db.commit()
    gia_dau, gia_pt = 26500.0, 500000.0
    K_DAU, K_PT = (noi.code, KQ.MA_DAU), (KQ.kho_pt(), KQ.ma_pt(ptu.id))
    KHO.ton[K_DAU] = [500.0, gia_dau]
    KHO.ton[K_PT] = [5.0, gia_pt]
    s, g = goi("/api/but-toan-cho", u="ketoan")
    if not g.get("co_duong_gui"):
        raise SystemExit("DỪNG: cờ QLSX_GUI_BUT_TOAN chưa có tác dụng trong tiến trình bài")
    print("Kho QLSX giả: %s %s L giá %s · phụ tùng %s tồn %s giá %s" % (noi.code, KHO.ton[K_DAU][0], gia_dau, K_PT[1], KHO.ton[K_PT][0], gia_pt))
    dau = lambda lit, **k: dict({"section": "fuel", "item_key": "diesel", "qty": lit, "place_id": noi.id}, **k)
    chip = {"section": "travel", "item_key": "x_chip_lao", "qty": 1, "unit_price": 150000, "currency": "LAK"}   # ghi nợ NCC (no_ncc)
    A = lap(d.tag + "-A/EPL", "EPL", d.nha, d.tx1, d.kh, [dau(50)])
    B = lap(d.tag + "-B/EPL", "joint", d.thue, d.tx2, d.kh, [dau(40), chip])

    print("0. Luật 02/10: xe thuê lấy kho EPL luôn là xuất bán — không có «chủ xe tự trả»")
    s, g = goi("/api/trips", {"doc_no": d.tag + "-C/EPL", "kind": "giao", "company": "joint", "vehicle_id": d.thue.id,
                              "driver_id": tx3.id, "customer_id": d.kh.id, "doc_date": HOM_NAY, "weight_origin": 40,
                              "price": 40, "price_ccy": "USD", "hire_price": 30, "hire_ccy": "USD",
                              "expenses": [dau(30, paid_by_epl=False)]}, u="admin")
    dung(s == 422 and ma(g) == "KHO_XE_THUE_XUAT_BAN" and ba_tieng(g, "mục III dòng 1", "phiếu bán ở quầy"),
         "lập phiếu xe thuê có dầu kho «chủ xe tự trả» → 422, câu đủ ba tiếng", "%s %s" % (s, ma(g)))
    C = lap(d.tag + "-C/EPL", "joint", d.thue, tx3, d.kh, [dau(30)])
    s, pc = goi("/api/trips/" + C, u="admin")
    f_c = dong_cua(pc, "fuel")[0]
    s, g = goi("/api/trips/" + C, {"expenses": [dict(f_c, paid_by_epl=False)]}, u="thabok", method="PUT")
    dung(s == 422 and ma(g) == "KHO_XE_THUE_XUAT_BAN", "Bãi đổi dòng dầu kho xe thuê sang «chủ xe tự trả» → 422", "%s %s" % (s, ma(g)))
    ton0, n0 = KHO.ton[K_PT][0], len(KHO.phieu)
    s, g = goi("/api/trips/%s/events" % C, {"kind": "repair", "incident_type": "tire", "note": "thử luật 02/10",
                                            "repair": {"source": "kho", "part_id": ptu.id, "qty": 1, "paid_by_epl": False}}, u="totsua")
    dung(s == 422 and ma(g) == "KHO_XE_THUE_XUAT_BAN" and KHO.ton[K_PT][0] == ton0 and len(KHO.phieu) == n0,
         "tổ sửa lấy phụ tùng kho «chủ xe tự trả» cho xe thuê → 422, kho QLSX không có phiếu xuất", "%s %s · tồn %s → %s" % (
             s, ma(g), ton0, KHO.ton[K_PT][0]))

    print("0b. Khoá khi hàng lấy kho chưa rời kho → chặn (dầu chưa cấp theo phiếu đề nghị)")
    for tid, ten in ((A, "xe nhà"), (B, "xe thuê")):
        s, g = goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan")
        dung(s == 409 and ma(g) == "DAU_KHO_CHUA_CAP" and ba_tieng(g, "mục III dòng 1 (", "Quản lý kho", "Cấp dầu theo phiếu đề nghị"),
             "khoá %s khi dầu kho chưa cấp → 409 DAU_KHO_CHUA_CAP, nói dòng nào, cấp ở đâu (đủ ba tiếng)" % ten, loi(g)[:120])

    print("1. Xuất kho ở kho QLSX: thủ kho cấp dầu theo tờ PLNL, tổ sửa lấy phụ tùng")
    to = {}
    for tid, ten in ((A, "A"), (B, "B"), (C, "C")):
        v = lap_to_dau(tid)
        goi_to, kq = thu_kho_cap(v["id"])
        to[ten] = goi_to
    dung(to["A"]["purpose"] == "INTERNAL" and to["A"]["warehouse_code"] == noi.code and to["A"]["partner_code"] is None
         and to["A"]["item_code"] == KQ.MA_DAU and to["A"]["qty_l"] == 50,
         "gói tờ A cho kho QLSX: xe nhà INTERNAL, đúng kho, EPLNL-diesel, 50 L", {k: to["A"][k] for k in ("purpose", "warehouse_code", "qty_l")})
    dung(to["B"]["purpose"] == "PARTNER_SALE" and to["B"]["partner_code"] == "EPLCX-" + d.chu.id and to["B"]["vehicle_kind"] == "HIRED",
         "gói tờ B: xe thuê PARTNER_SALE + đối tác EPLCX-<chủ xe>", (to["B"]["purpose"], to["B"]["partner_code"]))
    s, g = goi("/api/handover/fuel-vouchers/%s/issued" % to["A"]["voucher_id"],
               {"source_ref": to["A"]["source_ref"], "stock_doc_no": KHO.dau[to["A"]["source_ref"]]["so"], "qty_l": 50,
                "lines": [{"item_code": KQ.MA_DAU, "qty": 50, "unit_cost": gia_dau}]})
    dung(s == 200 and g["data"].get("replayed") is True, "kho QLSX báo lại cùng phiếu kho → replayed, không ghi lần hai", s)
    for tid in (A, B):
        lay_phu_tung(tid, ptu.id)
    xk = [x for x in KHO.nhan if x[1] == KQ.DUONG + "/stock-issues"]
    dung(len(xk) == 2 and xk[0][2]["Purpose"] == "INTERNAL" and xk[1][2]["Purpose"] == "PARTNER_SALE"
         and xk[1][2].get("ObjectCode") == "EPLCX-" + d.chu.id and all(x[3].startswith("EPLLAO:trip_expense:") for x in xk),
         "phụ tùng: phiếu xuất 48 ở kho QLSX — A INTERNAL, B PARTNER_SALE + EPLCX-<chủ xe>, SourceRef EPLLAO:trip_expense:<dòng>",
         [(x[2]["Purpose"], x[2].get("ObjectCode"), x[3][:40]) for x in xk])
    dung(KHO.ton[K_DAU][0] == 500 - 50 - 40 - 30 and KHO.ton[K_PT][0] == 3, "kho QLSX trừ tồn: dầu 120 L, phụ tùng 2",
         (KHO.ton[K_DAU][0], KHO.ton[K_PT][0]))
    s, pa = goi("/api/trips/" + A, u="admin"); s, pb = goi("/api/trips/" + B, u="admin"); s, pc = goi("/api/trips/" + C, u="admin")
    dau_a, pt_a = dong_cua(pa, "fuel")[0], dong_cua(pa, "repair")[0]
    # phụ tùng ghi "lấy kho" ngay trên bảng mục V (không qua «Sửa xe») thì chưa rời kho → khoá bị chặn; bỏ dòng thì khoá được
    s, g = goi("/api/trips/" + A, {"expenses": [pt_a, {"section": "repair", "source": "kho", "part_id": ptu.id, "qty": 1}]},
               u="admin", method="PUT")
    phai(s, 200, "Sếp ghi thêm một dòng phụ tùng «lấy từ kho» trên bảng mục V của A (chưa xuất kho)", g)
    s, g = goi("/api/trips/%s/khoa" % A, {"xac_nhan": True}, u="ketoan")
    dung(s == 409 and ma(g) == "PT_KHO_CHUA_XUAT" and ba_tieng(g, "mục V dòng 2", "Sửa xe"),
         "khoá A khi phụ tùng ghi lấy kho mà chưa xuất → 409 PT_KHO_CHUA_XUAT (đủ ba tiếng)", "%s %s" % (s, ma(g)))
    s, g = goi("/api/trips/" + A, {"expenses": [pt_a]}, u="admin", method="PUT")
    phai(s, 200, "bỏ dòng phụ tùng chưa xuất", g)
    dau_b, pt_b, chip_b = dong_cua(pb, "fuel")[0], dong_cua(pb, "repair")[0], dong_cua(pb, "travel")[0]
    dau_c = dong_cua(pc, "fuel")[0]
    dung(all(str(e["stock_move_id"] or "").startswith("qlsx:") for e in (dau_a, pt_a, dau_b, pt_b, dau_c)),
         "dòng kho đã rời kho: mang qlsx:<số phiếu kho>", [e["stock_move_id"] for e in (dau_a, pt_a, dau_b, pt_b, dau_c)])
    dung(abs(dau_a["unit_price"] - gia_dau) < 0.01 and abs(dau_b["unit_price"] - gia_dau) < 0.01 and abs(pt_a["unit_price"] - gia_pt) < 0.01,
         "giá vốn trên dòng = giá bình quân kho QLSX lúc xuất", "%s · %s" % (dau_a["unit_price"], pt_a["unit_price"]))
    dung(not kho(bt(A)) and not kho(bt(B)), "trước khi khoá: dầu đã cấp vẫn CHƯA có bút toán xuất kho (ghi lúc khoá)")

    print("2. Khoá phiếu: chặn khi xuất bán chưa có giá bán / dòng cũ «chủ xe tự trả»")
    s, g = goi("/api/trips/%s/khoa" % B, {"xac_nhan": True}, u="ketoan")
    dung(s == 409 and ma(g) == "THIEU_GIA_BAN" and ba_tieng(g, "mục III dòng 1", "KT kho xăng dầu", "mục V dòng 1", "KT Chi phí"),
         "khoá B khi dầu, phụ tùng xuất bán chưa có giá bán → 409 THIEU_GIA_BAN, nói mục nào, ai gõ (đủ ba tiếng)", loi(g)[:150])
    s, g = goi("/api/trips/" + B, {"expenses": [{"id": dau_b["id"], "section": "fuel", "sale_price": 35000}]}, u="khonl", method="PUT")
    phai(s, 200, "KT kho xăng dầu gõ giá bán dầu cho chủ xe 35.000 LAK/L", g)
    ban_pt = round(gia_pt * 1.2)
    s, g = goi("/api/trips/" + B, {"expenses": [{"id": pt_b["id"], "section": "repair", "sale_price": ban_pt}]}, u="ketoancp", method="PUT")
    phai(s, 200, "KT Chi phí gõ giá bán phụ tùng cho chủ xe %s LAK" % ban_pt, g)
    # dữ liệu cũ (trước 02/10): dòng kho xe thuê ghi "chủ xe tự trả" — API nay chặn nên ghi thẳng DÒNG THỬ của bài (trong giao dịch)
    e = db.get(M.TripExpense, dau_c["id"])
    e.paid_by_epl = False
    db.commit()
    s, g = goi("/api/trips/%s/khoa" % C, {"xac_nhan": True}, u="ketoan")
    dung(s == 409 and ma(g) == "KHO_XE_THUE_XUAT_BAN" and ba_tieng(g, "mục III dòng 1", "EPL ứng"),
         "dữ liệu cũ: dầu kho xe thuê ghi «chủ xe tự trả» → khoá bị chặn, chỉ cách sửa (đủ ba tiếng)", "%s %s" % (s, ma(g)))
    s, g = goi("/api/trips/" + C, {"expenses": [{"id": dau_c["id"], "section": "fuel", "paid_by_epl": False, "sale_price": 36000}]},
               u="khonl", method="PUT")
    dung(s == 200, "gửi nguyên «chủ xe tự trả» của dòng cũ không làm hỏng lần lưu (để khoá chặn)", "%s %s" % (s, ma(g)))
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
    dd = (x_dau or {}).get("dong") or [{}]
    dung(len(dd) == 1 and dd[0]["no"] == "625" and dd[0]["co"] == "1371" and dd[0]["ccy"] == "LAK" and dd[0]["tien"] == round(50 * gia_dau)
         and dd[0]["doi_tuong"] is None and dd[0].get("hinh_thuc") == "noi_bo" and dd[0].get("ref") == dau_a["id"],
         "dầu: Nợ 625 / Có 1371 = 50 L × %s = %s LAK" % (gia_dau, round(50 * gia_dau)), json.dumps(dd[0], ensure_ascii=False)[:160])
    dd = (x_pt or {}).get("dong") or [{}]
    dung(len(dd) == 1 and dd[0]["no"] == "614" and dd[0]["co"] == "1371" and dd[0]["tien"] == round(gia_pt),
         "phụ tùng: Nợ 614 / Có 1371 = 1 × %s LAK" % gia_pt)
    dung(all(b["ngay"] == HOM_NAY and b["trip_id"] == A and b["source_ref"] == "EPLLAO-%s-%s" % (b["nguon"], b["ma_nguon"])
             and "nội bộ" in (b["dien_giai"] or "") for b in ka.values()),
         "ngày chứng từ = ngày xuất thật, SourceRef EPLLAO-xuat_noi_bo-<lần xuất>, diễn giải ghi chữ 'nội bộ'",
         [(b["ngay"], b["source_ref"]) for b in ka.values()])
    dung("PLNL-" in (x_dau or {}).get("dien_giai", ""), "diễn giải dầu ghi số phiếu đề nghị xuất kho", (x_dau or {}).get("dien_giai"))
    ncc = [x for b in bt(A, "no_ncc") for x in b["dong"]]
    dung(not any(x.get("ref") in (dau_a["id"], pt_a["id"]) for x in ncc), "dòng kho không nằm trong no_ncc (không ghi hai lần)")

    print("  B — xe thuê, EPL ứng: xuất bán — bút toán chỉ vế giá vốn (phần bán = SO nhiên liệu)")
    kb = {b["ma_nguon"]: b for b in kho(bt(B))}
    y_dau, y_pt = kb.get("dau:" + dau_b["stock_move_id"]), kb.get("pt:" + pt_b["stock_move_id"])
    dung(len(kb) == 2 and y_dau and y_pt and all(b["nguon"] == "xuat_ban" for b in kb.values()), "hai bút toán xuat_ban", sorted(kb))
    for ten, b, sl, von in (("dầu", y_dau, 40, gia_dau), ("phụ tùng", y_pt, 1, gia_pt)):
        ds = (b or {}).get("dong") or []
        gv = ds[0] if ds else {}
        dung(len(ds) == 1 and gv.get("ve") == "gia_von" and gv.get("no") == "607" and gv.get("co") == "1371"
             and gv.get("tien") == round(sl * von) and gv.get("doi_tuong") is None,
             "%s: một dòng Nợ 607 / Có 1371 = %s × %s (giá vốn bình quân) = %s, không đối tượng" % (ten, sl, von, round(sl * von)),
             [(x.get("no"), x.get("co"), x.get("tien")) for x in ds])
        dung("chủ xe" in (b or {}).get("dien_giai", "") and all("Xuất bán cho chủ xe" in x["dien_giai"] and "SO nhiên liệu" in x["dien_giai"]
                                                                for x in ds),
             "%s: chữ 'xuất bán cho chủ xe' ở bút toán, dòng ghi phần bán đi SO nhiên liệu" % ten)
    dung(not any(x.get("co") == "707" or x.get("ve") == "doanh_thu" for b in kb.values() for x in b["dong"]),
         "không còn vế Nợ 4022 / Có 707 trong bút toán xuất kho (02/10 — phần bán là SO nhiên liệu)")
    s, pb = goi("/api/trips/" + B, u="admin")
    chi = ((pb.get("tinh") or {}).get("chi") or {})
    dung(chi.get("fuel") == 40 * 35000 and chi.get("repair") == ban_pt,
         "số trừ tiền trả chủ xe theo GIÁ BÁN (mục III 40 × 35.000, mục V %s)" % ban_pt, {m: chi.get(m) for m in ("fuel", "repair")})

    print("  C — xe thuê, dòng dầu kho đã sửa về EPL ứng (luật 02/10)")
    kc = kho(bt(C))
    dc = [x for b in kc for x in b["dong"]]
    dung(len(kc) == 1 and kc[0]["nguon"] == "xuat_ban" and len(dc) == 1 and dc[0]["no"] == "607" and dc[0]["tien"] == round(30 * gia_dau),
         "C có xuat_ban: 607/1371 = 30 × giá vốn", str([(x["no"], x["co"], x["tien"]) for x in dc]))

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
    ton0 = KHO.ton[K_PT][0]
    s, g = goi("/api/trips/%s/events" % B, {"kind": "repair", "incident_type": "tire", "note": "thêm sau khoá",
                                            "repair": {"source": "kho", "part_id": ptu.id, "qty": 1}}, u="totsua")
    dung(s == 409 and ma(g) == "DA_KHOA" and KHO.ton[K_PT][0] == ton0,
         "tổ sửa lấy thêm phụ tùng kho cho phiếu đã khoá → 409, kho QLSX không bị trừ", "%s %s · tồn %s → %s" % (s, ma(g), ton0, KHO.ton[K_PT][0]))
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
        s, g = goi("/api/but-toan-cho?nguon=xuat_ban&trip_id=" + B, u=u)
        dung(s == (200 if u in ("admin", "ketoan", "ketoancp") else 403), "GET bút toán xuất kho — %-8s (%s) → %s" % (u, VAI[u], s))
    for u in ("thabok", "totsua", "khonl", "khotb"):
        s, p = goi("/api/trips/" + B, u=u)
        dung(s != 200 or "but_toan_cho" not in p, "phiếu không mang khối bút toán cho %s" % u)
    s, g = goi("/api/but-toan-cho?nguon=xuat_noi_bo,xuat_ban&trip_id=" + A, u="ketoancp")
    dung(s == 200 and {b["nguon"] for b in g["ds"]} == {"xuat_noi_bo"}, "lọc theo nguồn mới được")

    print("4. Gói gửi sang máy giả hệ kế toán (tự gửi lúc khoá)")
    for b in list(ka.values()) + list(kb.values()):
        b2 = next(x for x in bt(b["trip_id"], b["nguon"]) if x["id"] == b["id"])
        dung(b2["status"] == "da_gui" and str(b2["so_ben_ke_toan"]).startswith("GIA-XK"), "tự gửi lúc khoá: %s → %s" % (b["source_ref"], b2["so_ben_ke_toan"]))
    for ten, b in (("A dầu", x_dau), ("A phụ tùng", x_pt), ("B dầu", y_dau), ("B phụ tùng", y_pt)):
        g = (GIA.ct.get(b["source_ref"]) or {}).get("body") or {}
        en = g.get("Entries") or []
        mong = [(x["no"], x["co"], x["tien"]) for x in b["dong"]]
        dung([(e["DebitAccount"], e["CreditAccount"], e["Amount"]) for e in en] == mong
             and all(e["CurrencyId"] == 26 and e["ExchangeRate"] == 1 for e in en) and g.get("DocumentDate") == HOM_NAY
             and g.get("SourceRef") == b["source_ref"] and g.get("FiciAutoId") == 77,
             "gói %s: tài khoản · tiền Kíp (mã tiền 26, tỷ giá 1) · ngày xuất · kỳ" % ten, json.dumps(mong))
        dung(all(e.get("ObjectId") is None for e in en), "gói %s: dòng giá vốn không đối tượng" % ten)
        dung(all(len(e.get("Note") or "") <= 250 and "Xuất" in (e.get("Note") or "") for e in en), "gói %s: ghi chú dòng có chữ loại khoản" % ten)
    hd = [x for x in GIA.nhan if x[0] == "POST" and x[1] == DUONG]
    dung(hd and all(x[2].get("Idempotency-Key") == x[3]["SourceRef"] for x in hd), "Idempotency-Key = SourceRef")

    print("5. Mở khoá → huỷ; sửa giá; khoá lại → cùng bản")
    cu = {b["id"]: b for b in kho(bt(B))}
    s, g = goi("/api/trips/%s/mo-khoa" % B, {}, u="ketoan"); phai(s, 200, "KT Thu/Chi mở khoá B", g)
    r = kho(bt(B))
    dung(r and all(b["status"] == "huy" and not b["can_dao"] for b in r), "mở khoá: mọi bút toán xuất kho của B → huỷ",
         str({b["ma_nguon"]: b["status"] for b in r}))
    dung(all(GIA.ct[b["source_ref"]]["Reversed"] for b in kb.values()), "đã gỡ chứng từ bên kế toán")
    s, g = goi("/api/trips/" + B, {"expenses": [{"id": dau_b["id"], "section": "fuel", "sale_price": 40000}]}, u="khonl", method="PUT")
    dung(s == 200, "mở khoá rồi KT kho xăng dầu đổi giá bán dầu 40.000 → được", s)
    s, g = goi("/api/trips/%s/khoa" % B, {"xac_nhan": True}, u="ketoan"); phai(s, 200, "Khoá lại B", g)
    r = kho(bt(B))
    song = [b for b in r if b["status"] != "huy"]
    dung(set(b["id"] for b in r) == set(cu) and len(song) == 2
         and all([(x["no"], x["co"], x["tien"]) for x in b["dong"]] == [(x["no"], x["co"], x["tien"]) for x in cu[b["id"]]["dong"]] for b in song),
         "khoá lại: cùng hai bản ghi, sống lại, tiền giá vốn không đổi (giá bán không vào bút toán)",
         str([(b["ma_nguon"], b["status"], b["phien"]) for b in r]))
    dung(all(b["status"] == "da_gui" and b["source_ref"].endswith("-2") for b in song), "gửi lại với SourceRef phiên mới '-2'",
         [b["source_ref"][-30:] for b in song])
    s, pb4 = goi("/api/trips/" + B, u="admin")
    dung(((pb4.get("tinh") or {}).get("chi") or {}).get("fuel") == 40 * 40000, "số trừ chủ xe theo giá bán mới 40 × 40.000")

    print("6. Huỷ phiếu kho bên QLSX · xoá phiếu")
    sr_b = to["B"]["source_ref"]
    s, g = thu_kho_huy(sr_b)
    dung(s == 409 and ma(g) == "DA_KHOA" and KHO.ton[K_DAU][0] == 500 - 120,
         "DO B đã khoá → kho QLSX không huỷ được phiếu cấp dầu (409 DA_KHOA), tồn nguyên", "%s %s" % (s, ma(g)))
    s, g = goi("/api/trips/%s/mo-khoa" % A, {}, u="admin"); phai(s, 200, "Sếp mở khoá A", g)
    s, g = goi("/api/trips/" + A, u="admin", method="DELETE")
    dung(s == 409 and ma(g) == "DA_CAP_KHO_QLSX" and KHO.dau[to["A"]["source_ref"]]["so"] in loi(g),
         "xoá A khi dầu đã cấp ở kho QLSX → 409 DA_CAP_KHO_QLSX, nói số phiếu kho", "%s %s" % (s, loi(g)[:120]))
    s, g = thu_kho_huy(to["A"]["source_ref"])
    dung(s == 200 and g["data"]["status"] == "cho" and KHO.ton[K_DAU][0] == 500 - 70,
         "thủ kho huỷ phiếu xuất dầu của A bên QLSX → tờ về chờ cấp, tồn trả 50 L", "%s %s" % (s, (g.get("data") or {}).get("status")))
    s, pa = goi("/api/trips/" + A, u="admin")
    dung(s == 200 and not dong_cua(pa, "fuel")[0]["stock_move_id"], "dòng dầu A gỡ mã phiếu kho")
    s, g = goi("/api/trips/" + A, u="admin", method="DELETE"); phai(s, 200, "Sếp xoá phiếu thử A (phụ tùng huỷ ở kho QLSX)", g)
    dung("EPLLAO:trip_expense:" + pt_a["id"] in KHO.huy and KHO.ton[K_PT][0] == 4,
         "phụ tùng A: stock-issues/cancel đúng SourceRef, tồn trả lại (còn 4 — phụ tùng B vẫn xuất)", (KHO.huy, KHO.ton[K_PT][0]))
    s, g = goi("/api/but-toan-cho?nguon=xuat_noi_bo&status=huy&gioi_han=1000", u="admin")
    dung(s == 200 and all(any(b["ma_nguon"] == m and b["status"] == "huy" for b in g["ds"]) for m in ka),
         "bút toán của phiếu đã xoá còn dấu vết, trạng thái huỷ")
    dung(all(GIA.ct[b["source_ref"]]["Reversed"] for b in ka.values()), "chứng từ bên kế toán của A đã gỡ")


if __name__ == "__main__":
    main()
