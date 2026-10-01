# -*- coding: utf-8 -*-
"""Thử GỬI BÚT TOÁN CHỜ sang hệ kế toán anh Tune — bằng MÁY GIẢ trong bài (không gọi 5090).

    python kiem/thu_gui_but_toan.py [http://127.0.0.1:8014] [cổng máy giả 8096]

Máy chủ trang điều xe đang thử phải chạy với:
    QLSX_GUI_BUT_TOAN=1 · QLSX_BASE_URL=http://127.0.0.1:<cổng máy giả> · QLSX_ACCESS_TOKEN=<chuỗi bất kỳ>
(scratchpad gb_khoi_dong_8014_gia.ps1). Máy giả trả đúng giao ước GLS-QLSX-APIs `b9227aa` (LogisticsJournalEntryController):
    POST /api/v1/integrations/logistics/journal-entries (Idempotency-Key = SourceRef) → 201 {DocumentId, DocumentNo, StatusId 13,
         IsExisting false} · cùng nội dung → 200 IsExisting · khác nội dung → 409 ErrorDetail.ErrorCode LOGISTICS_JOURNAL_52512 ·
         tài khoản sai → 400 ErrorDetail {ErrorCode INVALID_ACCOUNTS, InvalidAccounts}
    POST …/journal-entries/reverse {SourceRef} → {DocumentId, Reversed true} · không còn chứng từ đang hoạt động → {DocumentId null,
         Reversed false} · GET …/journal-entries/{SourceRef} → … | 404 (đã gỡ cũng 404); gỡ xong POST lại cùng SourceRef = chứng từ mới
cùng mấy đường danh mục bên đó cần (đối tượng, tiền, kỳ).

Nhánh: khoá phiếu xe thuê → tự gửi hai bút toán (đúng tài khoản, tiền, đối tượng, khoá chống trùng) · gửi lại bản đã gửi → 409 ·
mở khoá → đảo → huỷ · khoá lại → SourceRef mới "-2" · 400 tài khoản sai → giữ "chờ gửi", lỗi rõ · mất mạng → giữ, đếm lần thử ·
bên kia đã lưu mà trả 503 → lần sau hỏi lại (GET) nhận đúng chứng từ · GET 404 mà POST trả IsExisting → nhận · đảo hỏng → chờ đảo →
Gửi hết đảo được · phân quyền · mất phản hồi khi gửi rồi mở khoá → hỏi lại, gỡ (không sót chứng từ bên kia) ·
gỡ xong mà mất phản hồi → Gửi hết nhận Reversed=false → huỷ · 409 khác số → tự gỡ chứng từ cũ, gửi bản đúng · phân loại lỗi
(403 · HTTP 200 kèm Code 500 · 503 chưa bật → Gửi hết dừng ngay).
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8014").rstrip("/")
CONG = int(sys.argv[2]) if len(sys.argv) > 2 else 8096
if GOC.endswith((":8010", ":8020")):
    sys.exit("Không chạy bài này trên máy thật.")
TK, LOI = {}, []
SO = "THU-GBT-A/EPL"
DUONG = "/api/v1/integrations/logistics/journal-entries"


# ================================================================ máy giả hệ kế toán
class GIA:
    ct = {}            # SourceRef → {DocumentId, DocumentNo, StatusId, Reversed, body}
    nhan = []          # (method, path, headers, body)
    che_do = set()     # sai_tk · luu_roi_503 · get_404 · dao_hong · dao_roi_503 · khac_noi_dung · cam_403 · loi_500_trong_200 · chua_bat
    da_go = []         # DocumentNo đã gỡ
    so = 7000
    may = None


def bao(than, ma=200):
    return ma, {"Success": ma < 400, "Code": ma, "Message": None if ma < 400 else than.get("_cau"), "Result": than}


class Xu(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _tra(self, ma, than):
        b = json.dumps(than, ensure_ascii=False).encode("utf-8")
        self.send_response(ma); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def _than(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"null") if n else None

    def do_GET(self):
        GIA.nhan.append(("GET", self.path, dict(self.headers), None))
        if self.path.startswith("/api/v1/common/GetAllCurrency"):
            return self._tra(200, {"Success": True, "Result": [{"CUR_AUTOID": 26, "CUR_NAME": "LAK"}, {"CUR_AUTOID": 2, "CUR_NAME": "USD"},
                                                              {"CUR_AUTOID": 1, "CUR_NAME": "VND"}, {"CUR_AUTOID": 5, "CUR_NAME": "THB"}]})
        if self.path.startswith("/api/v1/common/GetFinancyCicle"):
            return self._tra(200, {"Success": True, "Result": [{"FICI_AUTOID": 77, "FICI_NAME": "2026", "FICI_DATEFROM": "2026-01-01",
                                                              "FICI_DATETO": "2026-12-31", "FICI_ISACTIVE": True, "FICI_ISCLOSE": False}]})
        if self.path.startswith(DUONG + "/"):
            ref = urllib.request.unquote(self.path[len(DUONG) + 1:])
            c = GIA.ct.get(ref)
            if c is None or c["Reversed"] or "get_404" in GIA.che_do:
                return self._tra(404, {"Success": False, "Code": 404, "Message": "Không có chứng từ", "Result": None,
                                       "ErrorDetail": {"ErrorCode": "JOURNAL_ENTRY_NOT_FOUND"}})
            return self._tra(200, {"Success": True, "Result": {k: c[k] for k in ("DocumentId", "DocumentNo", "StatusId")}})
        self._tra(404, {"Success": False, "Code": 404, "Message": "không có đường"})

    def do_POST(self):
        b = self._than()
        GIA.nhan.append(("POST", self.path, dict(self.headers), b))
        if self.path.startswith("/api/v1/master-data/") and self.path.endswith("/list"):
            return self._tra(200, {"Success": True, "Result": {"Data": []}})
        if self.path.startswith("/api/v1/master-data/") and self.path.endswith("/upsert"):
            GIA.so += 1
            return self._tra(200, {"Success": True, "Result": GIA.so})
        if self.path == DUONG + "/reverse":
            c = GIA.ct.get((b or {}).get("SourceRef"))
            if "dao_hong" in GIA.che_do:
                return self._tra(503, {"Success": False, "Code": 503, "Message": "bận"})
            if c is None or c["Reversed"]:
                return self._tra(200, {"Success": True, "Code": 200, "Result": {"SourceRef": (b or {}).get("SourceRef"),
                                                                              "DocumentId": None, "Reversed": False}})
            c["Reversed"] = True
            GIA.da_go.append(c["DocumentNo"])
            if "dao_roi_503" in GIA.che_do:
                return self._tra(503, {"Success": False, "Code": 503, "Message": "hết giờ (đã gỡ)"})
            return self._tra(200, {"Success": True, "Code": 200, "Result": {"DocumentId": c["DocumentId"], "Reversed": True}})
        if self.path == DUONG:
            ref = (b or {}).get("SourceRef")
            if self.headers.get("Idempotency-Key") != ref:
                return self._tra(400, {"Success": False, "Code": 400, "Message": "Idempotency-Key phải bằng SourceRef"})
            if "cam_403" in GIA.che_do:
                return self._tra(403, {"Success": False, "Code": 403, "Message": "Tài khoản tích hợp không được phép gửi bút toán",
                                       "Result": None, "ErrorDetail": {"ErrorCode": "LOGISTICS_JOURNAL_FORBIDDEN"}})
            if "loi_500_trong_200" in GIA.che_do:
                return self._tra(200, {"Success": False, "Code": 500, "Message": "Lỗi không xác định", "Result": None})
            if "chua_bat" in GIA.che_do:
                return self._tra(503, {"Success": False, "Code": 503, "Message": "Thiếu thủ tục trên DB kế toán", "Result": None,
                                       "ErrorDetail": {"ErrorCode": "LOGISTICS_JOURNAL_SCRIPT_REQUIRED"}})
            if "sai_tk" in GIA.che_do:
                return self._tra(400, {"Success": False, "Code": 400, "Message": "Tài khoản không có trong danh mục", "Result": None,
                                       "ErrorDetail": {"ErrorCode": "INVALID_ACCOUNTS", "InvalidAccounts": ["9999"]}})
            khac = {"Success": False, "Code": 409, "Message": "Cùng SourceRef, khác nội dung", "Result": None,
                    "ErrorDetail": {"ErrorCode": "LOGISTICS_JOURNAL_52512"}}
            if "khac_noi_dung" in GIA.che_do and (ref not in GIA.ct or GIA.ct[ref]["Reversed"]):
                # chứng từ cũ cùng SourceRef nằm sẵn bên kia (lần gửi trước mất phản hồi) với số khác
                GIA.che_do.discard("khac_noi_dung"); GIA.so += 1
                GIA.ct[ref] = {"DocumentId": GIA.so, "DocumentNo": "GIA-BT-CU-%d" % GIA.so, "StatusId": 13, "Reversed": False,
                               "body": {"Entries": []}}
                return self._tra(409, khac)
            if ref in GIA.ct and not GIA.ct[ref]["Reversed"]:
                c = GIA.ct[ref]
                if c["body"] is not None and c["body"].get("Entries") != (b or {}).get("Entries"):
                    return self._tra(409, khac)
                return self._tra(200, {"Success": True, "Code": 200, "Result": {"SourceRef": ref, "DocumentId": c["DocumentId"],
                                                                              "DocumentNo": c["DocumentNo"], "StatusId": c["StatusId"],
                                                                              "IsExisting": True}})
            GIA.so += 1
            c = GIA.ct[ref] = {"DocumentId": GIA.so, "DocumentNo": "GIA-BT-%d" % GIA.so, "StatusId": 13, "Reversed": False, "body": b}
            if "luu_roi_503" in GIA.che_do:
                return self._tra(503, {"Success": False, "Code": 503, "Message": "hết giờ (đã lưu)"})
            return self._tra(201, {"Success": True, "Code": 201, "Result": {"SourceRef": ref, "DocumentId": c["DocumentId"],
                                                                          "DocumentNo": c["DocumentNo"], "StatusId": 13, "IsExisting": False}})
        self._tra(404, {"Success": False, "Code": 404, "Message": "không có đường"})


def bat_gia():
    GIA.may = ThreadingHTTPServer(("127.0.0.1", CONG), Xu)
    threading.Thread(target=GIA.may.serve_forever, daemon=True).start()


def tat_gia():
    GIA.may.shutdown(); GIA.may.server_close(); GIA.may = None


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


def ma(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return d.get("ma") if isinstance(d, dict) else None


def bt(tid):
    s, g = goi("/api/but-toan-cho?trip_id=" + tid, u="ketoan")
    return {b["nguon"]: b for b in g["ds"]}


def don():
    s, ds = goi("/api/trips?q=THU-GBT", u="admin")
    for p in [x for x in (ds or []) if x["doc_no"] == SO]:
        goi("/api/trips/%s/mo-khoa" % p["id"], {}, u="admin"); goi("/api/trips/" + p["id"], u="admin", method="DELETE")


def main():
    for u in ("admin", "ketoan", "ketoancp", "thabok", "doanhthu"):
        TK[u] = goi("/api/dang-nhap", {"username": u, "password": "1234"})[1]["token"]
    bat_gia()
    s, g = goi("/api/but-toan-cho", u="ketoan")
    if not g.get("co_duong_gui"):
        sys.exit("DỪNG: máy chủ %s chưa bật QLSX_GUI_BUT_TOAN (trỏ máy giả cổng %d)" % (GOC, CONG))
    don()
    s, xe = goi("/api/vehicles", u="admin"); s, tx = goi("/api/drivers", u="admin"); s, kh = goi("/api/customers", u="admin")
    thue = next(v for v in xe if v["owner_type"] == "joint" and v["active"])
    s, p = goi("/api/trips", {"doc_no": SO, "kind": "giao", "company": "joint", "vehicle_id": thue["id"], "driver_id": tx[0]["id"],
                              "customer_id": kh[0]["id"], "doc_date": "2026-10-01", "weight_origin": 40, "price": 40, "price_ccy": "USD",
                              "hire_price": 30, "hire_ccy": "USD", "pod_no": "GBT",
                              "expenses": [{"section": "travel", "item_key": "x_chip_lao", "qty": 1, "unit_price": 150000, "currency": "LAK"}]}, u="admin")
    tid = p["id"]
    goi("/api/trips/%s/transport-status" % tid, {"status": "arrived", "weight_dest": 40, "odo_back": 10, "back_date": "2026-10-01"}, u="admin")
    try:
        print("1. Khoá phiếu → tự gửi")
        s, g = goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan"); dung(s == 200, "KT Thu/Chi khoá phiếu", s)
        b = bt(tid)
        t, n = b.get("thue_xe") or {}, b.get("no_ncc") or {}
        dung(t.get("status") == "da_gui" and str(t.get("so_ben_ke_toan") or "").startswith("GIA-BT") and n.get("status") == "da_gui",
             "hai bút toán đã gửi, có số chứng từ bên kế toán", "%s · %s" % (t.get("so_ben_ke_toan"), n.get("so_ben_ke_toan")))
        gt = GIA.ct.get(t.get("source_ref"), {}).get("body") or {}
        e = (gt.get("Entries") or [{}])[0]
        dung(gt.get("SourceRef") == "EPLLAO-thue_xe-" + tid and e.get("DebitAccount") == "621" and e.get("CreditAccount") == "4022"
             and e.get("Amount") == 1200 and e.get("CurrencyId") == 2 and e.get("ExchangeRate") == 22000 and e.get("ObjectId")
             and gt.get("FiciAutoId") == 77 and gt.get("DocumentDate") == "2026-10-01",
             "gói thuê xe: 621/4022 · 1.200 USD (mã tiền 2, tỷ giá 22.000) · đối tượng chủ xe · kỳ · ngày", json.dumps(e)[:120])
        en = (GIA.ct.get(n.get("source_ref"), {}).get("body") or {}).get("Entries") or [{}]
        dung(en[0].get("DebitAccount") == "4022" and en[0].get("CreditAccount") == "4021" and en[0].get("CurrencyId") == 26
             and en[0].get("Amount") == 150000 and en[0].get("ObjectId"), "gói ghi nợ NCC: 4022/4021 · 150.000 LAK · có đối tượng")
        hd = [x for x in GIA.nhan if x[0] == "POST" and x[1] == DUONG]
        dung(all(x[2].get("Idempotency-Key") == x[3]["SourceRef"] for x in hd), "Idempotency-Key = SourceRef ở mọi lần gửi")
        s, g = goi("/api/but-toan-cho/%s/gui" % t["id"], {}, u="ketoan")
        dung(s == 409 and ma(g) == "KHONG_GUI", "gửi lại bản đã gửi → 409 KHONG_GUI", s)
        s, g = goi("/api/but-toan-cho/%s/cap-nhat" % t["id"], {}, u="ketoancp")
        dung(s == 200 and g.get("tune_status") == 13, "Cập nhật → hỏi lại bên kế toán, StatusId 13 (ghi sổ tạm)", g.get("tune_status"))

        print("2. Mở khoá → đảo; khoá lại → SourceRef mới")
        s, g = goi("/api/trips/%s/mo-khoa" % tid, {}, u="ketoan"); dung(s == 200, "mở khoá", s)
        b = bt(tid)
        dung(all(x["status"] == "huy" and not x["can_dao"] for x in b.values()) and GIA.ct[t["source_ref"]]["Reversed"],
             "đã đảo bên kế toán → huỷ", str({k: v["status"] for k, v in b.items()}))
        s, g = goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan")
        b = bt(tid)
        dung(b["thue_xe"]["status"] == "da_gui" and b["thue_xe"]["source_ref"] == "EPLLAO-thue_xe-%s-2" % tid and b["thue_xe"]["phien"] == 2
             and b["thue_xe"]["so_ben_ke_toan"] != t["so_ben_ke_toan"], "khoá lại → chứng từ mới, SourceRef '-2'", b["thue_xe"]["source_ref"])

        print("3. 400 tài khoản sai · mất mạng · 503 đã lưu · IsExisting")
        goi("/api/trips/%s/mo-khoa" % tid, {}, u="ketoan")
        GIA.che_do = {"sai_tk"}
        goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan")
        b = bt(tid)
        x = b["thue_xe"]
        dung(x["status"] == "cho_gui" and x["error_code"] == "TAI_KHOAN_SAI" and "9999" in (x["loi_gui"] or ""),
             "400 tài khoản sai → giữ chờ gửi, lỗi nói tài khoản", x["loi_gui"])
        GIA.che_do = set(); tat_gia()
        s, g = goi("/api/but-toan-cho/%s/gui" % x["id"], {}, u="ketoancp")
        x2 = bt(tid)["thue_xe"]
        dung(s == 502 and ma(g) == "KHONG_GOI_DUOC" and x2["status"] == "cho_gui" and x2["attempts"] > x["attempts"],
             "mất mạng → 502, giữ chờ gửi, đếm lần thử", "%s lần" % x2["attempts"])
        bat_gia(); GIA.che_do = {"luu_roi_503"}
        s, g = goi("/api/but-toan-cho/%s/gui" % x["id"], {}, u="ketoancp")
        x3 = bt(tid)["thue_xe"]
        dung(s == 502 and x3["status"] == "cho_gui" and x3["error_code"] == "HTTP_5XX", "bên kia lưu rồi mà trả 503 → giữ chờ gửi (chưa rõ)")
        GIA.che_do = set()
        so_post = len([z for z in GIA.nhan if z[0] == "POST" and z[1] == DUONG])
        s, g = goi("/api/but-toan-cho/%s/gui" % x["id"], {}, u="ketoancp")
        x4 = bt(tid)["thue_xe"]
        dung(s == 200 and x4["status"] == "da_gui" and x4["so_ben_ke_toan"] == GIA.ct[x4["source_ref"]]["DocumentNo"]
             and len([z for z in GIA.nhan if z[0] == "POST" and z[1] == DUONG]) == so_post,
             "gửi lại sau 503 → HỎI LẠI (GET) trước, nhận đúng chứng từ đã lưu, không POST lần nữa", x4["so_ben_ke_toan"])
        n = bt(tid)["no_ncc"]
        GIA.ct[n["source_ref"]] = {"DocumentId": 99, "DocumentNo": "GIA-BT-CU", "StatusId": 13, "Reversed": False, "body": None}
        GIA.che_do = {"get_404"}
        s, g = goi("/api/but-toan-cho/gui-het", {}, u="ketoan")
        n2 = bt(tid)["no_ncc"]
        dung(s == 200 and n2["status"] == "da_gui" and n2["so_ben_ke_toan"] == "GIA-BT-CU", "Gửi hết: POST trả IsExisting → nhận chứng từ đã có",
             json.dumps(g)[:90])
        GIA.che_do = set()

        print("4. Đảo hỏng → chờ đảo → Gửi hết đảo được")
        GIA.che_do = {"dao_hong"}
        s, g = goi("/api/trips/%s/mo-khoa" % tid, {}, u="ketoan"); dung(s == 200, "mở khoá khi bên kế toán không đảo được vẫn mở", s)
        b = bt(tid)
        dung(all(v["status"] == "da_gui" and v["can_dao"] for v in b.values()), "chưa đảo được → chờ đảo (can_dao)")
        GIA.che_do = set()
        s, g = goi("/api/but-toan-cho/gui-het", {}, u="ketoancp")
        b = bt(tid)
        dung(s == 200 and g.get("da_dao") == 2 and all(v["status"] == "huy" and not v["can_dao"] for v in b.values()),
             "Gửi hết → đảo cả hai, huỷ", json.dumps(g)[:90])

        print("5. Phân quyền")
        for u in ("thabok", "doanhthu"):
            s, g = goi("/api/but-toan-cho/gui-het", {}, u=u); dung(s == 403, "%s Gửi hết → 403" % u, s)
            s, g = goi("/api/but-toan-cho/%s/gui" % t["id"], {}, u=u); dung(s == 403, "%s Gửi một bản → 403" % u, s)
        dung(goi("/api/but-toan-cho/gui-het", {})[0] == 401, "không đăng nhập → 401")

        print("6. Mất phản hồi — không sót, không kẹt chứng từ bên kế toán")
        GIA.che_do = {"luu_roi_503"}
        goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan")
        b = bt(tid)
        dung(all(v["status"] == "cho_gui" and v["error_code"] == "HTTP_5XX" for v in b.values()),
             "khoá: bên kia lưu rồi mà trả 503 → chờ gửi (chưa rõ)", str({k: (v["status"], v["error_code"]) for k, v in b.items()}))
        GIA.che_do = set()
        s, g = goi("/api/trips/%s/mo-khoa" % tid, {}, u="ketoan")
        b = bt(tid)
        dung(s == 200 and all(v["status"] == "huy" and (GIA.ct.get(v["source_ref"]) or {}).get("Reversed") for v in b.values()),
             "mở khoá → hỏi lại, thấy chứng từ bên kia → gỡ luôn (không sót)", str({k: v["status"] for k, v in b.items()}))
        goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan")
        GIA.che_do = {"dao_roi_503"}
        goi("/api/trips/%s/mo-khoa" % tid, {}, u="ketoan")
        b = bt(tid)
        dung(all(v["status"] == "da_gui" and v["can_dao"] for v in b.values()), "gỡ xong mà bên kia trả 503 → chờ đảo")
        GIA.che_do = set()
        s, g = goi("/api/but-toan-cho/gui-het", {}, u="ketoan")
        b = bt(tid)
        dung(s == 200 and g.get("da_dao") == 2 and all(v["status"] == "huy" and not v["can_dao"] for v in b.values()),
             "Gửi hết: bên kia trả Reversed=false (đã gỡ trước đó) → huỷ, không kẹt", json.dumps(g)[:90])
        GIA.che_do = {"khac_noi_dung"}
        s, g = goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan")
        b = bt(tid)
        cu = [x for x in GIA.da_go if x.startswith("GIA-BT-CU-")]
        dung(s == 200 and cu and all(v["status"] == "da_gui" and not str(v["so_ben_ke_toan"]).startswith("GIA-BT-CU") for v in b.values()),
             "409 cùng SourceRef khác số → tự gỡ chứng từ cũ rồi gửi bản đúng", "%s · %s" % (cu, {k: v["so_ben_ke_toan"] for k, v in b.items()}))

        print("7. Phân loại lỗi bên kế toán")
        for che, ky_vong, ten in (("cam_403", "KHONG_DUOC_PHEP", "403 không được phép (câu lỗi có chữ 'tài khoản') → không xếp nhầm là sai tài khoản"),
                                  ("loi_500_trong_200", "HTTP_5XX", "HTTP 200 kèm Code 500 → lỗi máy chủ (chưa rõ), không phải bị từ chối"),
                                  ("chua_bat", "BEN_DO_CHUA_BAT", "503 chưa áp script → 'chưa bật', giữ chờ gửi")):
            goi("/api/trips/%s/mo-khoa" % tid, {}, u="ketoan")
            GIA.che_do = {che}
            goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan")
            x = bt(tid)["thue_xe"]
            dung(x["status"] == "cho_gui" and x["error_code"] == ky_vong, ten, "%s · %s" % (x["error_code"], x["loi_gui"]))
        s, g = goi("/api/but-toan-cho/gui-het", {}, u="ketoan")
        dung(s == 200 and g.get("thu") == 1 and g.get("loi") == 1, "Gửi hết gặp 'chưa bật' → dừng ngay, không thử từng bản", json.dumps(g)[:90])
        GIA.che_do = set()
    finally:
        GIA.che_do = set()
        if GIA.may is None:
            bat_gia()
        don()
        print("  · dọn phiếu thử")
        tat_gia()
    print("\n%s" % ("GỬI BÚT TOÁN: ĐẠT" if not LOI else "GỬI BÚT TOÁN: SAI %d chỗ:\n  - " % len(LOI) + "\n  - ".join(LOI)))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
