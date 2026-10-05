# -*- coding: utf-8 -*-
"""Thử đợt 02/10 tối (máy chủ trang điều xe) trên bản sao _d7 — MỌI THỨ trong một giao dịch ngoài, phiên chạy savepoint, cuối
ROLLBACK: không ghi gì vào d7. Hệ kế toán anh Tune và kho tạm GIẢ LẬP trong bài (không gọi mạng thật).

    python kiem/thu_tat_toan_doi_tac.py

  2 Phiếu chi tạm ứng: mỗi dòng tiền mặt của tờ PTU một dòng định khoản (Nợ / Có như cũ, SourceLineKey EPLLAO:<trip>:<dòng>),
    Σ = tiền đầu phiếu, lệch làm tròn dồn dòng cuối và ghi rõ; chống trùng (list theo đối tượng + số PTU) vẫn dùng lại phiếu cũ.
  3 SO nhiên liệu (THU-KBAZ-T1 xe thuê, 200 l dầu kho giá bán 33.000): gói đúng khuôn API agent 2, gửi cùng nút «Tạo SO bên kế
    toán» (cước đã có → chỉ gửi phần thiếu), gửi lại không gọi nữa, kết quả chưa rõ → gửi lại đúng khoá; 52951 → conflict;
    xem trước có phần nhiên liệu; mở khoá bị chặn DA_TAO_SO; bút toán xuat_ban chỉ còn 607/1371; gói DO: dòng dầu → sales_order,
    header.fuel_so.
  4 Tất toán đối tác: phan_tra theo đúng ví dụ chủ dự án (thuê 10, không ứng, không dầu → 10 · thuê 10, ứng 2, dầu 3 → cấn 3, chi
    5); đề nghị trên T1 (đặt lại "chưa trả" trong giao dịch): chưa có SO → chặn; có SO → cấn trừ rồi phiếu chi phần còn lại; đối tác
    trả bớt SO → còn trả tăng; cấn trừ hết → không phiếu chi, phiếu "đã trả"; bỏ đề nghị → gỡ cấn trừ + rút phiếu chi; GET màn
    Tất toán đối tác đủ khoá giao ước.
  5 Tất toán tài xế (THU-KBAZ-G1, kỳ 2026-10): từng dòng mục III/IV/VI với cách trả / nguồn / số PTU / phiếu chi, đã ứng 250.000,
    đã chi thật 1.210.000, chênh 960.000.
"""
import json
import os
import sys
import types

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
sys.path.insert(0, os.path.join(GOC, "kiem"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from fastapi import HTTPException                       # noqa: E402
from sqlalchemy import create_engine                    # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
import _mau_kbaz as MAU                                 # noqa: E402
from routes import de_nghi as RDN                       # noqa: E402
from routes import phieu as RP                          # noqa: E402
from routes import tat_toan as RTT                      # noqa: E402
from routes import tat_toan_doi_tac as RTD              # noqa: E402
from services import ban_giao as BG                     # noqa: E402
from services import but_toan_cho as BTC                # noqa: E402
from services import chi_tune as CHI                    # noqa: E402
from services import goi_ke_toan as KT                  # noqa: E402
from services import gui_tune as GT                     # noqa: E402
from services import so_nhien_lieu as NL                # noqa: E402
from services import tra_chu_xe as TC                   # noqa: E402

KQ = []


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


# ================================================================ hệ kế toán giả + kho tạm giả
class GIA:
    so = {}            # do_id → {key, body, orderCode, total, remaining}
    tkn = {}           # key → {OrderCode, Amount, so}
    phieu = {}         # RealId → {body, status}
    nhan = []          # (đường, thân) đã nhận
    loi_so = None      # (http, envelope) — ép lần POST SO nhiên liệu tới trả lỗi
    da_ghi_so = set()  # RealId thủ quỹ đã ghi sổ (STATUS 12)
    loi_but_toan = 0   # số lần cấn trừ tới: bút toán bên kia hỏng → bên kia TỰ GỠ TKN (UAT 03/10: 52508 diễn giải dài)
    go = {}            # key → số TKN đã gỡ: gửi lại cùng khoá chỉ đọc lại bản đã gỡ (Success, State CANCELLED, Replayed)
    n = 0


def _so_moi():
    GIA.n += 1
    return GIA.n


def gia_nl_goi(method, duong, body_json=None, key=None):
    """so_nhien_lieu._goi: fuel-sales-orders + collection-offset."""
    than = json.loads(body_json) if body_json else None
    GIA.nhan.append((method, duong, than, key))
    if duong == NL.DUONG and method == "POST":
        if GIA.loi_so is not None:
            ma, env = GIA.loi_so
            GIA.loi_so = None
            return ma, env, json.dumps(env)
        do = than["header"]["do_id"]
        cu = GIA.so.get(do)
        if cu is not None:
            if cu["key"] == key and cu["body"] == body_json:
                env = {"Success": True, "Code": 200, "Result": dict(cu["kq"], replayed=True)}
                return 200, env, json.dumps(env)
            env = {"Success": False, "Code": 409, "Message": "khác nội dung", "ErrorDetail": {"ErrorCode": "LOGISTICS_FUEL_52951"}}
            return 409, env, json.dumps(env)
        n = _so_moi()
        kq = {"doId": do, "orderId": 9000 + n, "orderCode": "GIA-NL-%04d" % n, "retkAutoId": 8000 + n, "retkCode": "GIA-RETK-%d" % n,
              "totalAmount": than["header"]["total"], "currency": "LAK", "replayed": False}
        GIA.so[do] = {"key": key, "body": body_json, "kq": kq, "total": float(than["header"]["total"]), "remaining": float(than["header"]["total"])}
        env = {"Success": True, "Code": 201, "Result": kq}
        return 201, env, json.dumps(env)
    if duong.startswith(NL.DUONG + "/") and method == "GET":
        x = GIA.so.get(duong.rsplit("/", 1)[-1])
        if x is None:
            return 404, {"Success": False, "Code": 404}, "{}"
        env = {"Success": True, "Result": dict(x["kq"], remaining=x["remaining"])}
        return 200, env, json.dumps(env)
    if duong == NL.DUONG_CAN_TRU:
        if key in GIA.go:
            env = {"Success": True, "Message": "Đã cấn trừ với Idempotency-Key này; trả lại kết quả cũ.",
                   "Result": {"documentNo": GIA.go[key], "State": "CANCELLED", "Replayed": True}}
            return 200, env, json.dumps(env)
        if GIA.loi_but_toan and key not in GIA.tkn:
            GIA.loi_but_toan -= 1
            so = "4-TKN-GO-%04d" % _so_moi()
            GIA.go[key] = so
            env = {"Success": False, "Code": 422, "Message": "Không lập được bút toán cấn trừ (Diễn giải hoặc ghi chú dòng vượt sức chứa cột "
                   "DOC_DESCRIPTION / GLB_NOTE / ET_NOTE; không cắt ngầm.). Đã gỡ phiếu thu nợ %s và trả lại dư nợ." % so,
                   "ErrorDetail": {"ErrorCode": "DEBT_OFFSET_JOURNAL_FAILED"}}
            return 422, env, json.dumps(env)
        if key in GIA.tkn:
            env = {"Success": True, "Result": {"documentNo": GIA.tkn[key]["so"]}}
            return 200, env, json.dumps(env)
        x = next((v for v in GIA.so.values() if v["kq"]["orderCode"] == than["OrderCode"]), None)
        if x is None or float(than["Amount"]) > x["remaining"] + 0.001:
            env = {"Success": False, "Code": 422, "Message": "cấn trừ vượt còn nợ", "ErrorDetail": {"ErrorCode": "OFFSET_OVER"}}
            return 422, env, json.dumps(env)
        x["remaining"] -= float(than["Amount"])
        so = "4-TKN-GIA-%04d" % _so_moi()
        GIA.tkn[key] = {"OrderCode": than["OrderCode"], "Amount": float(than["Amount"]), "so": so, "ref": than["RefNo"]}
        env = {"Success": True, "Result": {"documentNo": so, "documentId": GIA.n}}
        return 200, env, json.dumps(env)
    if duong == NL.DUONG_CAN_TRU + "/cancel":
        k = next((k for k, v in GIA.tkn.items() if v["OrderCode"] == than["OrderCode"] and v["ref"] == than["RefNo"]), None)
        if k is None:
            return 404, {"Success": False, "Code": 404}, "{}"
        v = GIA.tkn.pop(k)
        x = next(x for x in GIA.so.values() if x["kq"]["orderCode"] == v["OrderCode"])
        x["remaining"] += v["Amount"]
        env = {"Success": True, "Result": True}
        return 200, env, json.dumps(env)
    return 404, {"Success": False, "Code": 404, "Message": "không có đường"}, "{}"


def gia_chi_goi(method, duong, body=None):
    """chi_tune._goi — trả Result của envelope."""
    GIA.nhan.append((method, duong, body, None))
    if "master-data/" in duong and duong.endswith("/list"):
        return {"Data": [{"ObjId": 7000 + len(body.get("ObjKey") or ""), "ObjectNo": body.get("ObjKey")}]}
    if "GetAllCurrency" in duong:
        return [{"CUR_AUTOID": 26, "CUR_NAME": "LAK"}, {"CUR_AUTOID": 2, "CUR_NAME": "USD"}]
    if "GetFinancyCicle" in duong:
        return [{"FICI_AUTOID": 77, "FICI_NAME": "2026", "FICI_DATEFROM": "2026-01-01", "FICI_DATETO": "2026-12-31",
                 "FICI_ISACTIVE": True, "FICI_ISCLOSE": False}]
    if duong.endswith("cmpayment-receipt/list"):
        return {"Rows": [{"DOC_DOCUMENTID": k, "DOC_DOCUMENTNO": "GIA-C-%d" % k, "DOC_REFDOCUMENTNO": v["body"]["Header"]["RefDocumentNo"],
                          "CM_AMOUNT": v["body"]["Header"]["Amount"], "ST_AUTOID": 12 if k in GIA.da_ghi_so else 1}
                         for k, v in GIA.phieu.items() if v["body"]["Header"]["ObjectId"] == body.get("ObjectId") and not v.get("xoa")]}
    if duong.endswith("save-and-commit"):
        n = 990000 + _so_moi()
        GIA.phieu[n] = {"body": body}
        return {"RealId": n}
    if "cmpayment-receipt/" in duong and "?voucherType" in duong:
        n = int(duong.split("cmpayment-receipt/")[1].split("?")[0])
        x = GIA.phieu.get(n)
        if x is None or x.get("xoa"):
            return {"Master": None}
        return {"Master": {"DOCUMENTNO": "GIA-C-%d" % n, "STATUS": 12 if n in GIA.da_ghi_so else 1, "POSTNAME": "thủ quỹ giả"}}
    if duong.endswith("cmpayment-receipt/delete"):
        GIA.phieu[body["DocumentId"]]["xoa"] = True
        return True
    if duong.endswith("sales/debt/customer-detail"):
        no = [{"OrderCode": v["kq"]["orderCode"], "RETK_PAYMENTAMOUNT": v["total"], "RCTD_DEBTMONEY": v["remaining"],
               "RETK_MONEYPAID": 0, "CurrencyCode": "LAK"} for v in GIA.so.values() if v["remaining"] > 0.001]
        don = [{"OrderCode": v["kq"]["orderCode"], "FinalTotalAmount": v["total"], "CurrencyCode": "LAK"} for v in GIA.so.values()]
        return {"Summary": {}, "Debts": no, "Orders": don, "Aging": [], "Collections": []}
    raise HTTPException(502, {"ma": "BEN_KE_TOAN_TU_CHOI", "loi": "giả: không có đường %s" % duong})


def gia_kho(db, pt, duong, body=None, nguoi=None, het_gio=15):
    GIA.nhan.append((pt, "kho " + duong, body, None))
    if "/ban-hang/cho-tru" in duong:
        return []
    if "/ban-hang/" in duong:
        return []
    return {}


NL._goi = gia_nl_goi
CHI._goi = gia_chi_goi
KT.goi = gia_kho
GT.cau_hinh = lambda dang_nhap=True: ("http://ke-toan-gia.local", "token-gia")
MAU.chan_kho_qlsx()                                       # bài này dùng bộ giả kho tạm; không gọi kho QLSX thật


def nguoi(vai, ten="Thử"):
    return types.SimpleNamespace(role=vai, full_name="%s %s" % (ten, vai), username="thu_" + vai, id="thu", driver_id=None)


ACCT, ADMIN, EXP = nguoi("acct"), nguoi("admin"), nguoi("expacct")


class Phien:
    """Một ca một kết nối + giao dịch ngoài riêng; phiên chạy savepoint (route commit chỉ chốt savepoint); ra khỏi ca ROLLBACK."""
    eng = None

    def __enter__(self):
        if Phien.eng is None:
            Phien.eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
        self.conn = Phien.eng.connect()
        self.ngoai = self.conn.begin()
        from sqlalchemy import text
        self.conn.execute(text("SET LOCAL lock_timeout = '10s'"))   # 8011 chạy song song: chờ khoá quá 10 giây thì hỏng, không treo
        for t in ("gui_so_nhien_lieu_tune", "can_tru_tune"):          # bảng mới: dựng TRONG giao dịch (rollback xoá luôn)
            M.Base.metadata.tables[t].create(bind=self.conn, checkfirst=True)
        try:
            _dung_mau(self.conn)
        except BaseException:                                   # __enter__ hỏng thì __exit__ không chạy: tự trả giao dịch, kẻo
            self.ngoai.rollback(); self.conn.close()            # giữ khoá — ca sau dựng mẫu sẽ chờ khoá mãi
            raise
        self.db = Session(bind=self.conn, join_transaction_mode="create_savepoint", autoflush=False)
        return self.db

    def __exit__(self, *a):
        self.db.close()
        self.ngoai.rollback()
        self.conn.close()
        return False


_dung_mau = MAU.dung_mau


def phieu(db, so):
    return db.query(M.Trip).filter(M.Trip.doc_no == so).one()


def reset_gia():
    GIA.so.clear(); GIA.tkn.clear(); GIA.phieu.clear(); GIA.da_ghi_so.clear(); GIA.loi_so = None


def chua_tra(db, t1):
    """Đặt T1 về "chưa trả chủ xe" (trong giao dịch của ca): đề nghị cũ bỏ, bản chép đã trả xoá."""
    for r in db.query(M.ChiChuXeTune).filter(M.ChiChuXeTune.owner_id == t1.owner_id):
        r.status = "huy"
    t1.owner_paid, t1.owner_payment_id, t1.owner_paid_usd, t1.owner_paid_lak = False, None, None, None
    db.commit()


def ca_2():
    print("2. Phiếu chi tạm ứng — mỗi dòng một dòng định khoản")
    with Phien() as db:
        t1, g1 = phieu(db, "THU-KBAZ-T1/EPL"), phieu(db, "THU-KBAZ-G1/EPL")
        v = db.query(M.Voucher).filter(M.Voucher.trip_id == t1.id, M.Voucher.kind == "advance").one()
        body = CHI.dung_goi(db, t1, v, 7777)
        e = body["Entries"]
        dung(len(e) == 3, "T1: 3 dòng tiền mặt (sang VN, điện thoại, cao tốc) → 3 dòng định khoản", [x["Description"] for x in e])
        dung(sum(x["Amount"] for x in e) == body["Header"]["Amount"] == 4247000, "Σ dòng = tiền đầu phiếu 4.247.000",
             (sum(x["Amount"] for x in e), body["Header"]["Amount"]))
        dung(all(x["DebitAccount"] == "4022" and x["CreditAccount"] == "1011" and x["ObjectId"] == 7777 for x in e),
             "xe thuê: Nợ 4022 / Có 1011, đối tượng mọi dòng = đầu phiếu")
        dung(all(x["SourceLineKey"].startswith("EPLLAO:%s:" % t1.id) for x in e) and len({x["SourceLineKey"] for x in e}) == 3,
             "SourceLineKey EPLLAO:<trip>:<dòng chi>, không trùng", e[0]["SourceLineKey"])
        dung(e[0]["Description"].startswith("Mục IV · ") and t1.doc_no in e[0]["Description"], "diễn giải «Mục IV · khoản · SL × đơn giá · DO»",
             e[0]["Description"])
        vg = db.query(M.Voucher).filter(M.Voucher.trip_id == g1.id, M.Voucher.kind == "advance").one()
        tm = [d for d in db.query(M.TripExpense).filter(M.TripExpense.trip_id == g1.id).order_by(M.TripExpense.section, M.TripExpense.line_no)
              if RP.la_tien_mat_tai_xe(d, g1.company)]
        vg.amount_lak = 1210000                                  # tờ còn chờ: số theo các dòng hiện có (dam_bao_tam_ung)
        bg = CHI.dung_goi(db, g1, vg, 8888)
        dung(any(x["Description"].startswith("Mục III · dầu mua 30 lít") for x in bg["Entries"]) and len(bg["Entries"]) == len(tm)
             and all(x["DebitAccount"] == "1601" for x in bg["Entries"]), "G1 xe nhà: có dòng «Mục III · dầu mua … lít», Nợ 1601",
             [x["Description"][:44] for x in bg["Entries"]])
        g1.rate_vnd = 1.006                                       # làm tròn: hai dòng 100 VND = 100,6 Kíp → 101 + 101 ≠ 201
        for d in tm:
            if d.section == "travel":
                d.currency, d.unit_price = "VND", 100
        db.flush()
        vg.amount_lak = sum((d.qty or 0) * (d.unit_price or 0) * (1.006 if d.currency == "VND" else 1) for d in tm)
        bg = CHI.dung_goi(db, g1, vg, 8888)
        dung(sum(x["Amount"] for x in bg["Entries"]) == bg["Header"]["Amount"] == round(vg.amount_lak),
             "lệch làm tròn dồn vào dòng cuối, Σ = đầu phiếu", ([x["Amount"] for x in bg["Entries"]], bg["Header"]["Amount"]))
        dung("làm tròn" in bg["Entries"][-1]["Description"], "dòng cuối ghi rõ phần làm tròn", bg["Entries"][-1]["Description"][-44:])
        vg.amount_lak = 99
        try:
            CHI.dung_goi(db, g1, vg, 8888)
            dung(False, "tờ lệch dòng quá phần làm tròn bị chặn")
        except HTTPException as x:
            dung(x.detail.get("ma") == "TAM_UNG_LECH_DONG", "tờ lệch dòng quá phần làm tròn → 409 TAM_UNG_LECH_DONG", x.detail.get("loi"))
    with Phien() as db:
        reset_gia()
        g1 = phieu(db, "THU-KBAZ-G1/EPL")
        vg = db.query(M.Voucher).filter(M.Voucher.trip_id == g1.id, M.Voucher.kind == "advance").one()
        db.delete(db.get(M.ChiTune, vg.id))
        vg.status, vg.amount_lak = "cho", 1210000
        db.commit()
        r = CHI.gui(db, g1, vg, EXP)
        lap = [x for x in GIA.phieu.values() if x["body"]["Header"]["RefDocumentNo"] == vg.doc_no]
        dung(r.status == "da_gui" and len(lap) == 1 and len(lap[0]["body"]["Entries"]) == 3,
             "gửi phiếu chi tạm ứng G1 qua chi_tune.gui: một phiếu, 3 dòng (dầu mua, ăn, điện thoại)", (r.status, r.document_no))
        db.delete(r)
        db.commit()
        r = CHI.gui(db, g1, vg, EXP)
        lap = [x for x in GIA.phieu.values() if x["body"]["Header"]["RefDocumentNo"] == vg.doc_no]
        dung(len(lap) == 1 and "dung_lai" in (r.response_body or ""), "gửi lại cùng số: chống trùng (list theo đối tượng + số PTU) dùng "
             "lại phiếu cũ, không lập thêm", r.document_no)


def ca_3():
    print("3. SO nhiên liệu cho đối tác (T1)")
    with Phien() as db:
        reset_gia()
        t1 = phieu(db, "THU-KBAZ-T1/EPL")
        dung(NL.can_so(db, t1), "T1 xe thuê có dầu kho xuất bán → có phần SO nhiên liệu")
        b, tom = NL.dung_goi(db, t1)
        h, d0 = b["header"], b["details"][0]
        dung(set(b) == {"schemaVersion", "header", "details"} and h["partner_code"] == "EPLCX-" + t1.owner_id and h["currency"] == "LAK"
             and h["do_id"] == "EPLLAO-" + t1.id, "header đúng khuôn (do_id, partner_code EPLCX-<owner>, LAK)", h)
        dung(d0["qty"] == 200 and d0["unit_price"] == 33000 and d0["amount"] == 6600000 and h["total"] == 6600000 and d0["unit"] == "Lít"
             and d0["section"] == "III" and d0.get("item_key") == "diesel" and d0["ref"], "dòng: 200 Lít × 33.000 = 6.600.000 = total", d0)
        kq = RDN.tao_so(t1.id, db=db, user=ACCT)
        nl = kq.get("nhien_lieu") or {}
        dung(kq["da_co_truoc"] is True and (nl.get("trang_thai") or {}).get("status") == "synced" and nl.get("da_co_truoc") is False,
             "«Tạo SO bên kế toán»: SO cước đã có → chỉ gửi SO nhiên liệu (synced)", (nl.get("trang_thai") or {}).get("order_code"))
        k = [x for x in GIA.nhan if x[1] == NL.DUONG]
        dung(k and k[-1][3] == "logistics-fuel:EPLLAO-%s" % t1.id, "Idempotency-Key logistics-fuel:EPLLAO-<trip>", k[-1][3] if k else None)
        n = len([x for x in GIA.nhan if x[1] == NL.DUONG])
        kq2 = RDN.tao_so(t1.id, db=db, user=ACCT)
        dung(kq2["nhien_lieu"]["da_co_truoc"] is True and len([x for x in GIA.nhan if x[1] == NL.DUONG]) == n,
             "bấm lại: đã có cả hai, không gọi nữa")
        xt = RDN.xem_tao_so(t1.id, db=db, user=ACCT)
        dung((xt.get("nhien_lieu") or {}).get("can") is True and xt["nhien_lieu"]["trang_thai"]["status"] == "synced",
             "GET tao-so: liệt kê cả phần nhiên liệu")
        so_nl = NL.so_cua(db, t1)
        sc = db.get(M.GuiSoTune, "EPLLAO-" + t1.id)              # cước "hỏng rõ" trong ca — để thấy riêng luật SO nhiên liệu
        sc.status, sc.http_status, sc.error_code = "failed", 422, "QLSX_422"
        db.commit()
        try:
            RP.mo_khoa_phieu(t1.id, db=db, user=ACCT)
            dung(False, "mở khoá khi đã có SO nhiên liệu bị chặn")
        except HTTPException as x:
            dung(x.detail.get("ma") == "DA_TAO_SO" and "nhiên liệu" in x.detail.get("loi", ""), "mở khoá khi đã có SO nhiên liệu → 409 "
                 "DA_TAO_SO", x.detail.get("loi"))
        sc.status, sc.http_status, sc.error_code = "synced", 201, None
        db.commit()
        ds = [x for (_, dong, _) in BTC.dong_xuat_kho(db, t1).values() for x in dong]
        dung(ds and all(x["no"] == "607" and x["co"] == "1371" for x in ds), "bút toán xuat_ban chỉ còn giá vốn 607 / 1371",
             [(x["no"], x["co"], x["tien"]) for x in ds])
        g = BG.dong_goi(db, t1)
        dau = next(x for x in g["details"] if x.get("item_key") == "diesel")
        dung(dau["settlement"]["kind"] == "sales_order" and dau["settlement"]["state"] == "has_voucher"
             and dau["settlement"]["doc_no"] == so_nl.order_code, "gói DO: dòng dầu → sales_order theo SO nhiên liệu", dau["settlement"]["label"])
        dung((g["header"].get("fuel_so") or {}).get("order_code") == so_nl.order_code, "header.fuel_so", g["header"].get("fuel_so"))
    with Phien() as db:                                         # kết quả chưa rõ → gửi lại ĐÚNG gói, đúng khoá
        reset_gia()
        t1 = phieu(db, "THU-KBAZ-T1/EPL")
        GIA.loi_so = (503, {"Success": False, "Code": 503, "Message": "bận", "ErrorDetail": {"ErrorCode": "LOGISTICS_FUEL_52953"}})
        try:
            NL.gui(db, t1, ACCT)
        except HTTPException:
            pass
        b = NL.so_cua(db, t1)
        cu = b.request_body
        NL.gui(db, t1, ACCT)
        k = [x for x in GIA.nhan if x[1] == NL.DUONG][-1]
        dung(b.status == "synced" and json.dumps(k[2], ensure_ascii=False, separators=(",", ":")) == cu and k[3] == b.idempotency_key,
             "lần trước chưa rõ (503 bận) → gửi lại đúng gói, đúng khoá → synced")
    with Phien() as db:
        reset_gia()
        t1 = phieu(db, "THU-KBAZ-T1/EPL")
        GIA.loi_so = (409, {"Success": False, "Code": 409, "Message": "khác nội dung", "ErrorDetail": {"ErrorCode": "LOGISTICS_FUEL_52951"}})
        try:
            NL.gui(db, t1, ACCT)
            dung(False, "52951 → conflict")
        except HTTPException as x:
            dung(NL.so_cua(db, t1).status == "conflict" and x.status_code == 409, "bên kia báo 52951 → conflict (đối soát, không gửi lại)")
        try:
            NL.gui(db, t1, ACCT)
            dung(False, "conflict không tự gửi lại")
        except HTTPException as x:
            dung(x.detail.get("ma") == "DA_XUNG_DOT", "đã conflict → bấm lại bị chặn DA_XUNG_DOT")


def _co_so(db, t1):
    """Ca 4: T1 chưa trả + SO nhiên liệu đã tạo (máy giả)."""
    reset_gia()
    chua_tra(db, t1)
    NL.gui(db, t1, ACCT)


def ca_4():
    print("4. Tất toán đối tác")
    _vi_du_chu_du_an()
    with Phien() as db:
        t1 = phieu(db, "THU-KBAZ-T1/EPL")
        reset_gia()
        chua_tra(db, t1)
        x = TC.dong_phieu(db, t1)
        dung(x["cho_so"] and x["nhien_lieu_lak"] == 6600000, "chưa có SO: phiếu đánh dấu chờ SO nhiên liệu", x["cho_so"])
        try:
            CHI.de_nghi_tra_chu_xe(db, t1.owner_id, [t1.id], "cash", ACCT)
            dung(False, "chưa có SO nhiên liệu → chặn lập đề nghị")
        except HTTPException as e:
            dung(e.detail.get("ma") == "CHUA_TAO_SO_NHIEN_LIEU" and "Tạo SO" in e.detail.get("loi", ""), "chưa có SO nhiên liệu → 409 "
                 "CHUA_TAO_SO_NHIEN_LIEU (tạo SO trước)", e.detail.get("loi"))
    with Phien() as db:
        t1 = phieu(db, "THU-KBAZ-T1/EPL")
        _co_so(db, t1)
        x = TC.dong_phieu(db, t1)
        dung(abs(x["con_tra"] - x["tra_chu_xe"]) <= 0.011 and x["can_tru_lak"] > 0,
             "SO còn nợ đủ 6.600.000: còn trả = tra_chu_xe cũ (cấn trừ đủ phần dầu)", (x["con_tra"], x["tra_chu_xe"], x["hire_ccy"]))
        dung(x["tam_ung_lak"] == 4247000 and x["no_ncc_lak"] == 620000, "tạm ứng 4.247.000 · nợ NCC EPL trả thay 620.000 (chipping)",
             (x["tam_ung_lak"], x["no_ncc_lak"]))
        GIA.so["EPLLAO-" + t1.id]["remaining"] = 1000000.0      # đối tác đã tự trả bớt SO
        r = CHI.de_nghi_tra_chu_xe(db, t1.owner_id, [t1.id], "cash", ACCT)
        cts = CHI._can_tru_cua(db, r)
        dung(len(cts) == 1 and cts[0].status == "da_gui" and cts[0].amount == 1000000 and cts[0].so_tkn,
             "lập đề nghị: đọc lại còn nợ, cấn trừ đúng 1.000.000 (phiếu TKN)", (cts[0].amount, cts[0].so_tkn) if cts else None)
        g = [g for g in GIA.nhan if g[1] == NL.DUONG_CAN_TRU][-1]
        dung(g[3] == "logistics-offset:%s:%s" % (r.ref_no, cts[0].order_code)
             and set(g[2]) == {"OrderCode", "Amount", "CurrencyCode", "RefNo", "Reason", "Date"} and g[2]["RefNo"] == r.ref_no,
             "collection-offset: khoá logistics-offset:<TCX>:<SO>, thân {OrderCode, Amount, CurrencyCode, RefNo, Reason, Date}", g[3])
        pc = GIA.phieu[r.real_id]["body"] if r.real_id else None
        dung(r.status == "da_gui" and pc and pc["Header"]["Amount"] == r.amount and pc["Entries"][0]["DebitAccount"] == "4022",
             "phiếu chi phần còn lại (Nợ 4022 / Có tiền)", pc["Header"]["Amount"] if pc else None)
        r_h = TC.phan_tra(t1, db.query(M.TripExpense).filter(M.TripExpense.trip_id == t1.id).all(), NL.so_cua(db, t1))["ty_gia_thue"]
        dung(abs(r.amount_lak - (x["con_tra_lak"] + 5600000)) <= r_h, "còn trả tăng đúng phần đối tác đã tự trả SO (5.600.000 Kíp)",
             (r.amount_lak, x["con_tra_lak"]))
        dung(t1.id not in {y["id"] for y in CHI._dong_chu_xe(db, t1.owner_id)}, "phiếu trong đề nghị không còn chờ trả")
        GIA.da_ghi_so.add(r.real_id)                            # thủ quỹ ghi sổ → phiếu "đã trả"
        CHI.dong_bo_chu_xe(db, r, ACCT)
        t1 = db.get(M.Trip, t1.id)
        dung(r.status == "da_chi" and (t1.owner_payment_id or "").startswith("TUNE:") and abs((t1.owner_paid_usd or 0) - r.amount) < 0.011,
             "thủ quỹ ghi sổ → phiếu đã trả, số trả thực ghi lên phiếu", (t1.owner_payment_id, t1.owner_paid_usd, r.amount))
    with Phien() as db:                                         # bỏ đề nghị: gỡ cấn trừ + rút phiếu chi
        t1 = phieu(db, "THU-KBAZ-T1/EPL")
        _co_so(db, t1)
        r = CHI.de_nghi_tra_chu_xe(db, t1.owner_id, [t1.id], "bank", ACCT)
        con_truoc, rid = GIA.so["EPLLAO-" + t1.id]["remaining"], r.real_id
        kq = RTD.viec_de_nghi(r.ref_no, "bo", db=db, user=ACCT)
        dung(kq["trang_thai"] == "huy" and all(c["trang_thai"] == "huy" for c in kq["can_tru"]) and GIA.phieu[rid].get("xoa")
             and GIA.so["EPLLAO-" + t1.id]["remaining"] == 6600000.0 and con_truoc < 6600000.0,
             "bỏ đề nghị: gỡ cấn trừ (SO về đủ nợ), rút phiếu chi chưa ghi sổ", kq["can_tru"])
        dung(t1.id in {y["id"] for y in CHI._dong_chu_xe(db, t1.owner_id)}, "phiếu về lại chờ trả")
    with Phien() as db:                                         # cấn trừ hết → không phiếu chi
        t1 = phieu(db, "THU-KBAZ-T1/EPL")
        _co_so(db, t1)
        goc = TC.dong_phieu(db, t1)["tra_truoc_can_tru_lak"]
        GIA.so["EPLLAO-" + t1.id].update(total=float(goc + 500000), remaining=float(goc + 500000))
        n0 = len(GIA.phieu)
        kq = RTD.lap_de_nghi({"owner_id": t1.owner_id, "trip_ids": [t1.id], "cach_tra": "cash"}, db=db, user=ACCT)
        t1 = db.get(M.Trip, t1.id)
        dung(kq["phieu_chi"] is None and len(GIA.phieu) == n0 and kq["trang_thai"] == "da_chi" and kq["can_tru"][0]["tien"] == goc
             and (t1.owner_payment_id or "") == "TUNE:" + kq["so"], "cấn trừ hết (SO còn nợ > tiền trả): không phiếu chi, đề nghị xong, "
             "phiếu đã trả", (kq["so"], kq["can_tru"][0]["tien"], goc))
        try:
            RTD.viec_de_nghi(kq["so"], "bo", db=db, user=ACCT)
            dung(False, "đề nghị đã cấn trừ xong không bỏ được")
        except HTTPException as e:
            dung(e.status_code == 409, "đề nghị đã cấn trừ xong → bỏ bị chặn 409", e.detail.get("loi"))
    with Phien() as db:                                         # cấn trừ hỏng → đề nghị "loi", giữ phiếu; gửi lại làm tiếp
        t1 = phieu(db, "THU-KBAZ-T1/EPL")
        _co_so(db, t1)
        so_cu = NL.so_cua(db, t1).order_code
        luu = GIA.so["EPLLAO-" + t1.id]
        luu["kq"]["orderCode"] = "TAM-DOI"                       # bên kia "không thấy SO" lúc cấn trừ → 422
        r = None
        try:
            CHI.de_nghi_tra_chu_xe(db, t1.owner_id, [t1.id], "cash", ACCT)
        except HTTPException as e:
            dung(e.detail.get("so") and "Cấn trừ" in (e.detail.get("loi") or "") + (e.detail.get("ma") or "") or e.detail.get("so"),
                 "cấn trừ bị từ chối → báo lỗi kèm số đề nghị", {k: e.detail.get(k) for k in ("ma", "so", "loi")})
            r = db.query(M.ChiChuXeTune).filter(M.ChiChuXeTune.ref_no == e.detail.get("so")).first()
        dung(r is not None and r.status == "loi" and t1.id not in {y["id"] for y in CHI._dong_chu_xe(db, t1.owner_id)},
             "đề nghị ở trạng thái lỗi, phiếu vẫn bị giữ (không lập trùng)", r.status if r else None)
        luu["kq"]["orderCode"] = so_cu
        kq = RTD.viec_de_nghi(r.ref_no, "gui-lai", db=db, user=ACCT)
        dung(kq["trang_thai"] == "da_gui" and kq["can_tru"][0]["trang_thai"] == "da_gui" and kq["can_tru"][0]["order_code"] == so_cu,
             "gửi lại: cấn trừ (cùng khoá) rồi phiếu chi", kq["can_tru"])
    with Phien() as db:                                         # UAT 03/10: bút toán cấn trừ hỏng, bên kia tự gỡ TKN → gửi lại
        t1 = phieu(db, "THU-KBAZ-T1/EPL")
        _co_so(db, t1)
        GIA.loi_but_toan = 1
        r = None
        try:
            CHI.de_nghi_tra_chu_xe(db, t1.owner_id, [t1.id], "cash", ACCT)
        except HTTPException as e:
            r = db.query(M.ChiChuXeTune).filter(M.ChiChuXeTune.ref_no == e.detail.get("so")).first()
            dung(e.detail.get("ma") == "DEBT_OFFSET_JOURNAL_FAILED" and r is not None and r.status == "loi" and not r.real_id,
                 "bút toán cấn trừ hỏng (bên kia gỡ TKN) → đề nghị lỗi, chưa có phiếu chi", {k: e.detail.get(k) for k in ("ma", "so")})
        g = [g for g in GIA.nhan if g[1] == NL.DUONG_CAN_TRU][-1]
        dung(len(g[2]["Reason"]) <= 40 and g[2]["Reason"] == "DO " + t1.doc_no
             and len("Cấn trừ công nợ đối tác · %s · SO %s · 4-TKN-1368-2-261003-0001 · %s" % (g[2]["RefNo"], g[2]["OrderCode"], g[2]["Reason"])) <= 150,
             "lý do cấn trừ ngắn «DO <số DO>» — diễn giải bên kia ghép ≤ 150 ký tự (lần hỏng: 229)", g[2]["Reason"])
        khoa_cu, n_phieu = g[3], len(GIA.phieu)
        kq = RTD.viec_de_nghi(r.ref_no, "gui-lai", db=db, user=ACCT)
        cts = CHI._can_tru_cua(db, r)
        moi = [g for g in GIA.nhan if g[1] == NL.DUONG_CAN_TRU][-1]
        dung(moi[3] != khoa_cu and moi[3].startswith(khoa_cu + ":r") and cts[0].status == "da_gui" and not cts[0].so_tkn.startswith("4-TKN-GO")
             and cts[0].idempotency_key == moi[3],
             "gửi lại: bên kia trả bản ĐÃ GỠ (State CANCELLED) → KHÔNG coi là đã cấn trừ; khoá mới :r<lần>, cấn trừ thật", (moi[3], cts[0].so_tkn))
        dung(kq["trang_thai"] == "da_gui" and len(GIA.phieu) == n_phieu + 1, "rồi mới lập phiếu chi phần còn lại", kq["trang_thai"])
        kq2 = RTD.viec_de_nghi(r.ref_no, "bo", db=db, user=ACCT)
        huy = [g for g in GIA.nhan if g[1] == NL.DUONG_CAN_TRU + "/cancel"][-1]
        dung(kq2["trang_thai"] == "huy" and huy[3] == moi[3].replace("logistics-offset:", "logistics-offset-cancel:", 1)
             and huy[2]["DocumentNo"] == cts[0].so_tkn, "bỏ đề nghị: huỷ đúng lần cấn trừ mới (khoá huỷ theo khoá tạo hiện tại)", huy[3])
    with Phien() as db:                                         # GET màn Tất toán đối tác — đủ khoá giao ước
        t1 = phieu(db, "THU-KBAZ-T1/EPL")
        _co_so(db, t1)
        ky = (t1.out_date or t1.doc_date).strftime("%Y-%m")
        b = RTD.bang(ky=ky, owner_id=t1.owner_id, cap_nhat=1, db=db, user=ACCT)
        _kiem_khoa(b)
        print("    mẫu doi_tac[0]:", json.dumps({k: v for k, v in b["doi_tac"][0].items() if k != "de_nghi"}, ensure_ascii=False)[:500])
        print("    mẫu chi_tiet[0]:", json.dumps(b["chi_tiet"][0], ensure_ascii=False)[:900])
        bl = RTD.bang(ky=ky, owner_id="", cap_nhat=0, db=db, user=EXP)
        dung("chi_tiet" not in bl and bl["tong"]["so_doi_tac"] >= 1, "không truyền owner_id: không có chi_tiet; KT Chi phí xem được")
        try:
            RTD.lap_de_nghi({"owner_id": t1.owner_id, "trip_ids": [t1.id]}, db=db, user=EXP)
            dung(False, "KT Chi phí không lập đề nghị")
        except HTTPException as e:
            dung(e.status_code == 403, "KT Chi phí lập đề nghị → 403")
        try:
            RTD.bang(ky=ky, owner_id="", cap_nhat=0, db=db, user=nguoi("yard"))
            dung(False, "Bãi không xem")
        except HTTPException as e:
            dung(e.status_code == 403, "Bãi xem → 403")


def ca_5():
    print("5. Tất toán tài xế — chi tiết từng dòng (G1, kỳ 2026-10)")
    with Phien() as db:
        g1 = phieu(db, "THU-KBAZ-G1/EPL")
        d = RTT.mot(db, g1.driver_id, "2026-10")
        ph = next(x for x in d["phieu"] if x["trip_id"] == g1.id)
        dung(ph["da_ung_lak"] == 250000 and ph["da_chi_that_lak"] == 1210000 and ph["chenh_lak"] == 960000,
             "đã ứng 250.000 · đã chi thật 1.210.000 · chênh 960.000", (ph["da_ung_lak"], ph["da_chi_that_lak"], ph["chenh_lak"]))
        n = {x["nguon"] for x in ph["dong"]}
        dung({"tam_ung", "tu_chi", "cung_luong", "kho"} <= n, "nguồn: tạm ứng · tự chi (dầu mua dọc đường) · cùng lương · kho",
             sorted((x["khoan"], x["cach_tra"], x["nguon"]) for x in ph["dong"]))
        tu = [x for x in ph["dong"] if x["nguon"] == "tam_ung"]
        dung(tu and all(x["so_ptu"] == "PTU-THU-KBAZ-G1/EPL" and x["phieu_chi"] == "1368-CTR-261001-00072" and x["muc"] == "IV" for x in tu),
             "dòng tạm ứng mang số PTU + phiếu chi bên kế toán", [(x["khoan"], x["phieu_chi"]) for x in tu])
        dau = next(x for x in ph["dong"] if x["nguon"] == "tu_chi")
        dung(dau["muc"] == "III" and dau["cach_tra"] == "tien_mat" and dau["phieu_chi"] is None, "dầu mua dọc đường: mục III, tài xế tự chi",
             dau)
        dung(all(set(x) >= {"muc", "khoan", "sl", "don_gia", "tien_te", "tien_lak", "cach_tra", "nguon", "so_ptu", "phieu_chi"} for x in ph["dong"]),
             "mỗi dòng đủ khoá giao ước")
        dung(set(ph) >= {"trip_id", "doc_no", "chi_lak", "dong", "da_ung_lak", "da_chi_that_lak", "chenh_lak"}, "giữ khoá cũ + khoá mới")
        dung(set(d) >= {"driver_id", "so_phieu", "tong_ung_lak", "tong_chi_lak", "chenh_lech_lak", "phieu"}, "khoá cũ của kỳ giữ nguyên")


def main():
    for ca in (ca_2, ca_3, ca_4, ca_5):
        try:
            ca()
        except Exception as e:                                   # noqa: BLE001 — một ca vỡ thì ghi, chạy ca sau
            import traceback
            traceback.print_exc()
            dung(False, "%s vỡ: %s" % (ca.__name__, str(e).replace(URL, "<url>")[:300]))
    print("đã ROLLBACK mọi ca — bản sao d7 không đổi")
    print("TỔNG: %d/%d đạt" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


def _vi_du_chu_du_an():
    """Hai ví dụ của chủ dự án — phiếu dựng trong bộ nhớ (không ghi DB)."""
    def phieu():
        return M.Trip(id="vidu", doc_no="VD", company="joint", price=20, price_ccy="LAK", price_mode="chuyen", hire_price=10, hire_ccy="LAK",
                      fee_pct=0, over_limit_t=40, over_price=0, weight_dest=10, rate_usd=22000, rate_thb=700, rate_vnd=1.2, rate_cny=3000)
    p = phieu()
    x = TC.phan_tra(p, [], None)
    dung(x["con_tra"] == 10 and x["can_tru"] == 0, "thuê 10, không ứng, không dầu → trả 10", x["con_tra"])
    ung = M.TripExpense(id="u", trip_id="vidu", section="travel", item_key="x_food", qty=1, unit_price=2, currency="LAK", paid_by_epl=True)
    dau = M.TripExpense(id="d", trip_id="vidu", section="fuel", item_key="diesel", qty=1, unit_price=1, sale_price=3, currency="LAK",
                        source="kho", stock_move_id="mv", paid_by_epl=True)
    so = M.GuiSoNhienLieuTune(do_id="EPLLAO-vidu", status="synced", order_code="SO-VD", total_amount=3, thu_con_no=3)
    x = TC.phan_tra(p, [ung, dau], so)
    dung(x["can_tru"] == 3 and x["con_tra"] == 5 and x["tam_ung"] == 2, "thuê 10, ứng 2, dầu 3 → cấn trừ 3, chi 5",
         (x["can_tru"], x["con_tra"]))
    so.thu_con_no = 0
    x = TC.phan_tra(p, [ung, dau], so)
    dung(x["can_tru"] == 0 and x["con_tra"] == 8, "đối tác đã tự trả SO dầu → không cấn trừ, trả 8", x["con_tra"])


GIAO_UOC_DT = {"owner_id", "ten", "ma_ke_toan", "tien_te", "so_phieu", "tien_thue", "phi", "qua_tai", "tam_ung", "no_ncc", "nhien_lieu",
               "nhien_lieu_con_no", "con_tra", "con_tra_lak", "trang_thai", "de_nghi"}
GIAO_UOC_TONG = {"so_doi_tac", "tien_thue_lak", "phi_lak", "qua_tai_lak", "tam_ung_lak", "no_ncc_lak", "nhien_lieu_lak",
                 "nhien_lieu_con_no_lak", "con_tra_lak", "da_tra_lak"}
GIAO_UOC_CT = {"trip_id", "doc_no", "ngay", "tuyen", "xe", "tai_xe", "tan_tinh", "gia_thue", "tien_te", "tien_thue", "phi_pct", "phi",
               "qua_tai_t", "qua_tai", "tam_ung", "no_ncc", "nhien_lieu", "con_tra", "con_tra_lak", "trang_thai_tra", "so_de_nghi"}


def _kiem_khoa(b):
    dung(set(b) >= {"ky", "tong", "doi_tac", "chi_tiet"} and set(b["tong"]) >= GIAO_UOC_TONG, "GET: ky · tong (đủ khoá) · doi_tac · chi_tiet",
         sorted(GIAO_UOC_TONG - set(b["tong"])))
    dt_ = b["doi_tac"][0] if b["doi_tac"] else {}
    dung(set(dt_) >= GIAO_UOC_DT and dt_["trang_thai"] in ("chua_lap", "cho_so_nhien_lieu", "cho_thu_quy", "da_tra", "loi"),
         "doi_tac[]: đủ khoá giao ước", (dt_.get("ten"), dt_.get("trang_thai"), sorted(GIAO_UOC_DT - set(dt_))))
    ct = b["chi_tiet"][0] if b["chi_tiet"] else {}
    dung(set(ct) >= GIAO_UOC_CT and set(ct["tam_ung"]) >= {"so_ptu", "phieu_chi", "tien", "tien_lak", "dong"}
         and set(ct["nhien_lieu"]) >= {"order_code", "trang_thai", "tien_lak", "da_thu_lak", "con_no_lak", "dong"}
         and all(set(x) >= {"khoan", "nha_cung_cap", "tien_lak", "but_toan"} for x in ct["no_ncc"])
         and all(set(x) >= {"mat_hang", "lit", "gia_ban", "tien_lak", "gia_von_lak"} for x in ct["nhien_lieu"]["dong"])
         and all(set(x) >= {"khoan", "sl", "don_gia", "tien_te", "tien_lak"} for x in ct["tam_ung"]["dong"]),
         "chi_tiet[]: đủ khoá giao ước (tạm ứng / nợ NCC / nhiên liệu từng dòng)", sorted(GIAO_UOC_CT - set(ct)))
    dung(ct.get("nhien_lieu", {}).get("trang_thai") in ("da_tao", "can_tru", "da_thu") and ct["no_ncc"] and ct["no_ncc"][0]["but_toan"] == "GL021020269",
         "T1: SO nhiên liệu đã tạo · nợ NCC chipping mang bút toán GL021020269", (ct.get("nhien_lieu", {}).get("trang_thai"),
                                                                                ct["no_ncc"][:1]))


if __name__ == "__main__":
    main()
