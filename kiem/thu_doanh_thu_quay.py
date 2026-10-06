# -*- coding: utf-8 -*-
"""Thử 06/10 — kế toán trang điều xe (chủ dự án chốt hướng 06/10) trên bản sao _d7: MỌI THỨ trong một giao dịch ngoài mỗi ca, phiên
chạy savepoint, cuối ROLLBACK (dùng lại khung + bộ giả hệ kế toán của kiem/thu_tat_toan_doi_tac.py — không gọi mạng thật; đường bút
toán journal-entries cũng giả trong bài).

    python kiem/thu_doanh_thu_quay.py

  G1  Doanh thu ghi lúc «Tạo SO bên kế toán» (THU-KBAZ-T1 xe thuê: SO cước 753,35 USD đã có + SO nhiên liệu 200 L × 33.000):
      bút toán doanh_thu Nợ 1211 / Có 708 (USD, tỷ giá khoá trên phiếu, đối tượng khách) · doanh_thu_ban Nợ 1211 / Có 707 (Kíp,
      đối tượng đối tác EPLCX-<chủ xe>); gói journal-entries đúng mã / đối tượng / tiền; bấm lại không trùng; hiện ở GET
      /api/but-toan-cho; mở khoá gỡ (chưa gửi → huỷ · đã gửi → bút toán đảo), khoá lại ghi lại (đã đảo → SourceRef "-2").
  G2  Kho QLSX: SO BÁN HÀNG đối tác mua ở quầy (bên kế toán) bị cấn trừ khi lập đề nghị trả: chỉ SO thường (bỏ SO cước / SO nhiên
      liệu), cũ trước, SO không vừa để lại; cấn trừ collection-offset theo tiền của SO (VND kèm tỷ giá); số trả còn lại đúng; không
      gọi kho tạm, không ghi Nợ 4022 / Có 707; bỏ đề nghị gỡ cấn trừ; SO đang chờ cấn trừ không vào đề nghị khác; cấn trừ hết thì
      không có phiếu chi; màn Tất toán đối tác có khung `quay`.
  G12 Nợ trạm Việt Nam ghi đúng nguyên tệ VND + tỷ giá khoá trên phiếu (không quy Kíp), gói gửi đúng CurrencyId / ExchangeRate.
  G9  Câu báo khoá phiếu khi dầu kho chưa cấp chỉ đúng màn Web; câu dòng kho xe thuê không còn "kho tạm".
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thu_tat_toan_doi_tac as T                        # noqa: E402  (đặt DATABASE_URL = _d7, cài bộ giả hệ kế toán / kho tạm)

from fastapi import HTTPException                       # noqa: E402

import models as M                                      # noqa: E402
from routes import chu_xe as RCX                        # noqa: E402
from routes import de_nghi as RDN                       # noqa: E402
from routes import phieu as RP                          # noqa: E402
from services import but_toan_cho as BTC                # noqa: E402
from services import chi_tune as CHI                    # noqa: E402
from services import gui_but_toan_tune as GBT           # noqa: E402
from services import so_nhien_lieu as NL                # noqa: E402
from services import tai_khoan as TK                    # noqa: E402
from services import tra_chu_xe as TC                   # noqa: E402

GIA, dung, ACCT, ADMIN = T.GIA, T.dung, T.ACCT, T.ADMIN


# ================================================================ bộ giả thêm: đường bút toán, SO quầy, tiền VND
class BT:
    nhan = []        # (method, duong, body, key)
    co = {}          # SourceRef → {"id", "body", "dao"}
    n = 0


def gia_gbt_goi(method, duong, body=None, key=None, cho=30):
    """gui_but_toan_tune._goi giả — journal-entries: tạo (cùng SourceRef cùng nội dung → IsExisting), đảo, đọc."""
    BT.nhan.append((method, duong, body, key))
    if method == "POST" and duong == GBT.DUONG:
        x = BT.co.get(body["SourceRef"])
        if x is not None and not x["dao"]:
            if json.dumps(x["body"]["Entries"], sort_keys=True) != json.dumps(body["Entries"], sort_keys=True):
                return 409, {"Success": False, "Code": 409, "ErrorDetail": {"ErrorCode": "LOGISTICS_JOURNAL_52512"}}
            return 200, {"Success": True, "Result": {"SourceRef": body["SourceRef"], "DocumentId": x["id"], "DocumentNo": "GL-GIA-%d" % x["id"],
                                                      "StatusId": 13, "IsExisting": True}}
        BT.n += 1
        BT.co[body["SourceRef"]] = {"id": 5000 + BT.n, "body": body, "dao": False}
        return 201, {"Success": True, "Result": {"SourceRef": body["SourceRef"], "DocumentId": 5000 + BT.n, "DocumentNo": "GL-GIA-%d" % (5000 + BT.n),
                                                  "StatusId": 13, "IsExisting": False}}
    if method == "POST" and duong == GBT.DUONG + "/reverse":
        x = BT.co.get(body["SourceRef"])
        if x is None or x["dao"]:
            return 200, {"Success": True, "Result": {"DocumentId": None, "Reversed": False}}
        x["dao"] = True
        return 200, {"Success": True, "Result": {"DocumentId": x["id"], "Reversed": True}}
    if method == "GET":
        x = BT.co.get(duong.rsplit("/", 1)[-1])
        if x is None or x["dao"]:
            return 404, {"Success": False, "Code": 404, "ErrorDetail": {"ErrorCode": "JOURNAL_ENTRY_NOT_FOUND"}}
        return 200, {"Success": True, "Result": {"DocumentId": x["id"], "DocumentNo": "GL-GIA-%d" % x["id"], "StatusId": 13}}
    return 404, {"Success": False, "Code": 404}


class Q:
    """SO bán hàng (mua ở quầy) của đối tác bên kế toán giả: số SO → {ccy, tien, con, ngay, nguon}."""
    so = {}
    loi = set()      # số SO mà lần cấn trừ tới bị từ chối (422)
    tkn = {}         # key → (số SO, tiền)
    n = 0


class DT:
    """Danh mục đối tượng bên kế toán giả: mã KHÔNG có bên đó (list trả rỗng) · các lần upsert (GHI) đã gọi."""
    khong_co = set()
    upsert = []


def gia_chi_goi(method, duong, body=None):
    """chi_tune._goi: thêm tiền VND vào danh mục tiền; customer-detail thêm các SO quầy (kèm OrderSource như bên đó gắn);
    master-data list trả rỗng cho mã trong DT.khong_co; upsert ghi lại (bài kiểm đường ĐỌC không được gọi)."""
    if "master-data/" in duong and duong.endswith("/list") and (body or {}).get("ObjKey") in DT.khong_co:
        GIA.nhan.append((method, duong, body, None))
        return {"Data": []}
    if "master-data/" in duong and duong.endswith("/upsert"):
        DT.upsert.append((duong, (body or {}).get("ObjectNo")))
        return 99000 + len(DT.upsert)
    if "GetAllCurrency" in duong:
        return [{"CUR_AUTOID": 26, "CUR_NAME": "LAK"}, {"CUR_AUTOID": 2, "CUR_NAME": "USD"}, {"CUR_AUTOID": 1, "CUR_NAME": "VND"}]
    kq = T.gia_chi_goi(method, duong, body)
    if duong.endswith("sales/debt/customer-detail"):
        for so, x in Q.so.items():
            if x["con"] > 0.001:
                kq["Debts"].append({"OrderCode": so, "RETK_CODE": "RT-" + so, "RETK_TIMECLOSETICKET": x["ngay"], "RETK_PAYMENTAMOUNT": x["tien"],
                                    "RCTD_DEBTMONEY": x["con"], "RETK_MONEYPAID": 0, "CurrencyCode": x["ccy"], "OrderSource": x["nguon"]})
            kq["Orders"].append({"OrderCode": so, "OrderDate": x["ngay"], "FinalTotalAmount": x["tien"], "CurrencyCode": x["ccy"]})
    return kq


def gia_nl_goi(method, duong, body_json=None, key=None):
    """so_nhien_lieu._goi: cấn trừ / gỡ cấn trừ SO quầy (kiểm tiền khớp tiền SO như thủ tục 52789, không vượt dư nợ 52790);
    SO nhiên liệu → bộ giả cũ."""
    than = json.loads(body_json) if body_json else None
    if duong in (NL.DUONG_CAN_TRU, NL.DUONG_CAN_TRU + "/cancel") and than and than.get("OrderCode") in Q.so:
        GIA.nhan.append((method, duong, than, key))
        x = Q.so[than["OrderCode"]]
        if duong.endswith("/cancel"):
            k = next((k for k, v in Q.tkn.items() if v[0] == than["OrderCode"] and k.split(":")[1] == than["RefNo"]), None)
            if k is None:
                return 404, {"Success": False, "Code": 404}, "{}"
            x["con"] += Q.tkn.pop(k)[1]
            return 200, {"Success": True, "Result": True}, "{}"
        if key in Q.tkn:
            return 200, {"Success": True, "Result": {"documentNo": "4-TKN-QUAY-%s" % key[-4:]}}, "{}"
        if than["OrderCode"] in Q.loi:
            Q.loi.discard(than["OrderCode"])
            return 422, {"Success": False, "Code": 422, "Message": "bận đối soát", "ErrorDetail": {"ErrorCode": "DEBT_OFFSET_X"}}, "{}"
        if than["CurrencyCode"] != x["ccy"]:
            return 422, {"Success": False, "Code": 422, "Message": "Mã tiền cấn trừ khác tiền của SO", "ErrorDetail": {"ErrorCode": "52789"}}, "{}"
        if float(than["Amount"]) > x["con"] + 0.001:
            return 422, {"Success": False, "Code": 422, "Message": "vượt dư nợ", "ErrorDetail": {"ErrorCode": "52790"}}, "{}"
        x["con"] -= float(than["Amount"])
        Q.n += 1
        Q.tkn[key] = (than["OrderCode"], float(than["Amount"]))
        return 200, {"Success": True, "Result": {"documentNo": "4-TKN-QUAY-%04d" % Q.n, "documentId": 77000 + Q.n}}, "{}"
    return T.gia_nl_goi(method, duong, body_json, key)


GBT._goi = gia_gbt_goi
CHI._goi = gia_chi_goi
NL._goi = gia_nl_goi


def co_gui(bat):
    if bat:
        os.environ["QLSX_GUI_BUT_TOAN"] = "1"
    else:
        os.environ.pop("QLSX_GUI_BUT_TOAN", None)


def btc(db, nguon, tid):
    return db.query(M.ButToanCho).filter(M.ButToanCho.nguon == nguon, M.ButToanCho.ma_nguon == tid).all()


# ================================================================ G1 — doanh thu lúc Tạo SO
def ca_g1():
    print("G1. Doanh thu ghi lúc «Tạo SO bên kế toán»")
    co_gui(False)
    with T.Phien() as db:
        T.reset_gia()
        t1 = T.phieu(db, "THU-KBAZ-T1/EPL")
        T.chua_tra(db, t1)
        dung(not btc(db, BTC.DOANH_THU, t1.id) and not btc(db, BTC.DOANH_THU_BAN, t1.id), "trước: chưa có bút toán doanh thu")
        kq = RDN.tao_so(t1.id, db=db, user=ACCT)
        sc, sn = db.get(M.GuiSoTune, "EPLLAO-" + t1.id), NL.so_cua(db, t1)
        dung(sc.status == "synced" and sn is not None and sn.status == "synced", "SO cước (có sẵn) + SO nhiên liệu (vừa tạo) đều synced",
             (sc.order_code, sn.order_code if sn else None))
        [dthu], [dban] = btc(db, BTC.DOANH_THU, t1.id), btc(db, BTC.DOANH_THU_BAN, t1.id)
        d = json.loads(dthu.dong)
        dung(len(d) == 1 and d[0]["no"] == TK.PHAI_THU == "1211" and d[0]["co"] == TK.DT_VAN_CHUYEN == "708",
             "SO cước: Nợ 1211 / Có 708 (mã lấy từ tai_khoan)", [(x["no"], x["co"]) for x in d])
        ty = float(t1.rate_usd)
        dung(d[0]["ccy"] == "USD" and abs(d[0]["tien"] - sc.total_amount) < 1e-9 and d[0]["ty_gia"] == ty
             and d[0]["tien_lak"] == round(sc.total_amount * ty), "tiền = tiền SO cước %s USD × tỷ giá khoá trên phiếu %s = %s Kíp" % (
                 sc.total_amount, ty, d[0].get("tien_lak")), d[0])
        dung(d[0]["doi_tuong"] == {"loai": "khach", "ref_id": t1.customer_id} and "phiếu " + t1.doc_no in dthu.dien_giai
             and sc.order_code in dthu.dien_giai, "đối tượng = khách của DO; diễn giải có «phiếu <DO>» và số SO", dthu.dien_giai)
        dung(dthu.source_ref == "EPLLAO-doanh_thu-" + t1.id and dthu.status == "cho_gui" and dthu.trip_id == t1.id
             and dthu.ngay == BTC._ngay_dia_phuong(sc.synced_at), "SourceRef EPLLAO-doanh_thu-<trip>, chờ gửi (cờ tắt), ngày = ngày SO",
             (dthu.source_ref, dthu.ngay))
        b = json.loads(dban.dong)
        dung(all(x["no"] == "1211" and x["co"] == TK.DT_BAN_HANG == "707" and x["ccy"] == "LAK"
                 and x["doi_tuong"] == {"loai": "chu_xe", "ref_id": t1.owner_id} for x in b)
             and abs(sum(x["tien"] for x in b) - sn.total_amount) < 0.005 and dban.tong == sn.total_amount == 6600000,
             "SO nhiên liệu: Nợ 1211 / Có 707, Kíp, đối tượng đối tác, Σ = tiền SO 6.600.000", [(x["no"], x["co"], x["tien"]) for x in b])
        dung(dban.source_ref == "EPLLAO-doanh_thu_ban-" + t1.id and "Bán dầu" in b[0]["dien_giai"] and "phiếu " + t1.doc_no in dban.dien_giai,
             "SourceRef EPLLAO-doanh_thu_ban-<trip>; dòng «Bán dầu cho đối tác … × …»", b[0]["dien_giai"])
        dung([x["nguon"] for x in kq.get("but_toan_doanh_thu") or []] == ["doanh_thu", "doanh_thu_ban"], "kết quả Tạo SO báo hai bút toán",
             kq.get("but_toan_doanh_thu"))
        RDN.tao_so(t1.id, db=db, user=ACCT)
        dung(len(btc(db, BTC.DOANH_THU, t1.id)) == 1 and len(btc(db, BTC.DOANH_THU_BAN, t1.id)) == 1
             and btc(db, BTC.DOANH_THU, t1.id)[0].id == dthu.id, "bấm lại: không trùng (một DO một bút toán mỗi loại)")
        ds = RDN.ds_but_toan_cho(nguon="doanh_thu,doanh_thu_ban", status="", trip_id=t1.id, thang="", tu="", den="", gioi_han=50,
                                 db=db, user=ACCT)["ds"]
        dung(sorted(x["nguon"] for x in ds) == ["doanh_thu", "doanh_thu_ban"] and all(x["trip_doc_no"] == t1.doc_no for x in ds)
             and next(x for x in ds if x["nguon"] == "doanh_thu")["dong"][0]["co_ten"], "hiện ở màn Bút toán chờ gửi (GET /api/but-toan-cho)",
             [(x["nguon"], x["dong"][0]["no_ten"], x["dong"][0]["co_ten"]) for x in ds])
        g = GBT.dung_goi(db, dthu)
        e = g["Entries"][0]
        dung(g["SourceRef"] == dthu.source_ref and e["DebitAccount"] == "1211" and e["CreditAccount"] == "708" and e["Amount"] == sc.total_amount
             and e["ExchangeRate"] == ty and e["CurrencyId"] == CHI.ma_tien("USD") and e["ObjectId"]
             and g["DocumentDate"] == dthu.ngay.isoformat(), "gói journal-entries SO cước: 1211/708, %s USD, tỷ giá %s, đối tượng %s" % (
                 e["Amount"], e["ExchangeRate"], e["ObjectId"]), e)
        k = db.get(M.Customer, t1.customer_id)
        ma_kh = (k.code or "").strip() or ("EPLKH-" + k.id)
        dt_kh = db.get(M.DoiTuongTune, ("khach", k.id))
        dung(dt_kh is not None and dt_kh.object_no == ma_kh and e["ObjectId"] == dt_kh.obj_id, "đối tượng gửi = khách SO đứng tên (%s)" % ma_kh)
        g2 = GBT.dung_goi(db, dban)
        dt_cx = db.get(M.DoiTuongTune, ("chu_xe", t1.owner_id))
        dung(all(x["DebitAccount"] == "1211" and x["CreditAccount"] == "707" and x["CurrencyId"] == 26 and x["ExchangeRate"] == 1
                 and x["ObjectId"] == dt_cx.obj_id for x in g2["Entries"]) and dt_cx.object_no == "EPLCX-" + t1.owner_id,
             "gói SO nhiên liệu: 1211/707 Kíp, đối tượng EPLCX-<chủ xe>", [(x["Amount"], x["ObjectId"]) for x in g2["Entries"]])
        # màn Hồ sơ DO: bút toán doanh thu hiện cạnh SO của nó (nhóm thu · so_nl), như các nguồn bút toán khác
        from routes import ho_so_do as RHS
        nh = RHS.mot_ho_so(t1.id, db=db, user=ACCT)["nhom"]
        g_thu = [x for x in nh["thu"]["kt"] if x["loai"] == "gl"]
        g_nl = [x for x in nh["so_nl"]["kt"] if x["loai"] == "gl"]
        dung([x["nguon"] for x in g_thu] == ["doanh_thu"] and [x["nguon"] for x in g_nl] == ["doanh_thu_ban"]
             and g_thu[0]["ref"] == dthu.source_ref and g_thu[0]["tt"] == "cho_gui" and g_thu[0]["tien"] == 753.35 and g_thu[0]["ccy"] == "USD"
             and nh["thu"]["muc"] == "cho_gui" and nh["so_nl"]["muc"] == "cho_gui",
             "Hồ sơ DO: nhóm Đề nghị thu có bút toán doanh_thu, nhóm SO nhiên liệu có doanh_thu_ban (chờ gửi → mức nhóm «chờ gửi»)",
             (nh["thu"]["muc"], nh["so_nl"]["muc"], g_thu[:1]))
        nb = RHS.mot_ho_so(t1.id, db=db, user=T.nguoi("treasury"))["nhom"]
        gb = [x for x in nb["thu"]["kt"] if x["loai"] == "gl"]
        dung(gb and "tien" not in gb[0] and "id" not in gb[0], "vai không xem bút toán (Quỹ VC): thấy dòng, không thấy số tiền bút toán")
        # mở khoá (Sếp — SO đã có) → gỡ; khoá lại → ghi lại đúng một bản
        RP.mo_khoa_phieu(t1.id, db=db, user=ADMIN)
        db.expire_all()
        dung(btc(db, BTC.DOANH_THU, t1.id)[0].status == "huy" and btc(db, BTC.DOANH_THU_BAN, t1.id)[0].status == "huy",
             "mở khoá: bút toán doanh thu chưa gửi → huỷ")
        RP.khoa_phieu(t1.id, {"xac_nhan": True}, db=db, user=ACCT)
        db.expire_all()
        a, b2 = btc(db, BTC.DOANH_THU, t1.id), btc(db, BTC.DOANH_THU_BAN, t1.id)
        dung(len(a) == 1 and a[0].status == "cho_gui" and len(b2) == 1 and b2[0].status == "cho_gui" and a[0].source_ref == dthu.source_ref
             and json.loads(a[0].dong)[0]["tien"] == sc.total_amount, "khoá lại (SO vẫn còn): ghi lại đúng một bản mỗi loại, cùng số SO")


def ca_g1_gui():
    print("G1b. Cờ gửi bút toán BẬT: tự gửi, không gửi trùng, mở khoá → bút toán đảo, khoá lại → SourceRef mới")
    co_gui(True)
    BT.nhan.clear(); BT.co.clear()
    try:
        with T.Phien() as db:
            T.reset_gia()
            t1 = T.phieu(db, "THU-KBAZ-T1/EPL")
            T.chua_tra(db, t1)
            RDN.tao_so(t1.id, db=db, user=ACCT)
            dthu = btc(db, BTC.DOANH_THU, t1.id)[0]
            post = [x for x in BT.nhan if x[0] == "POST" and x[1] == GBT.DUONG and x[2]["SourceRef"] == dthu.source_ref]
            dung(dthu.status == "da_gui" and dthu.so_ben_ke_toan and len(post) == 1 and post[0][3] == dthu.source_ref,
                 "Tạo SO → tự gửi bút toán doanh thu (Idempotency-Key = SourceRef), có số chứng từ", (dthu.status, dthu.so_ben_ke_toan))
            RDN.tao_so(t1.id, db=db, user=ACCT)
            post = [x for x in BT.nhan if x[0] == "POST" and x[1] == GBT.DUONG and x[2]["SourceRef"] == dthu.source_ref]
            dung(len(post) == 1, "bấm Tạo SO lần nữa: không gửi lại (bản đã gửi đứng yên)", len(post))
            RP.mo_khoa_phieu(t1.id, db=db, user=ADMIN)
            db.expire_all()
            dthu = btc(db, BTC.DOANH_THU, t1.id)[0]
            dao = [x for x in BT.nhan if x[1] == GBT.DUONG + "/reverse" and x[2]["SourceRef"] == "EPLLAO-doanh_thu-" + t1.id]
            dung(dthu.status == "huy" and not dthu.can_dao and len(dao) == 1, "mở khoá: bút toán đã gửi → gửi bút toán đảo, xong thì huỷ",
                 (dthu.status, dthu.can_dao))
            RP.khoa_phieu(t1.id, {"xac_nhan": True}, db=db, user=ACCT)
            db.expire_all()
            dthu = btc(db, BTC.DOANH_THU, t1.id)[0]
            dung(dthu.status == "da_gui" and dthu.phien == 2 and dthu.source_ref == "EPLLAO-doanh_thu-%s-2" % t1.id,
                 "khoá lại: ghi lại thành chứng từ mới SourceRef …-2 (không đụng chứng từ đã đảo)", dthu.source_ref)
    finally:
        co_gui(False)


# ================================================================ G12 — nợ trạm Việt Nam theo VND
def ca_g12():
    print("G12. Nợ trạm Việt Nam: ghi đúng VND + tỷ giá khoá trên phiếu")
    co_gui(False)
    with T.Phien() as db:
        g1 = T.phieu(db, "THU-KBAZ-G1/EPL")
        ncc = db.query(M.Supplier).first()
        d = M.TripExpense(trip_id=g1.id, section="fuel", line_no=9, item_key="diesel", qty=100, unit_price=25000, currency="VND",
                          source="mua", ghi_no=True, supplier_id=ncc.id if ncc else None, paid_by_epl=True)
        db.add(d)
        db.flush()
        bo = BTC.dong_khoa_phieu(db, g1)
        x = next((y for y in bo.get(BTC.NO_NCC, ([], None))[0] if y.get("ref") == d.id), None)
        r = float(g1.rate_vnd)
        dung(x is not None and x["no"] == "625" and x["co"] == "4021", "dòng dầu trạm VN ghi nợ: Nợ 625 / Có 4021", x and (x["no"], x["co"]))
        dung(x and x["ccy"] == "VND" and x["tien"] == 2500000 and x["ty_gia"] == r and x["tien_lak"] == round(2500000 * r)
             and "ccy_goc" not in x, "ghi NGUYÊN TỆ: 2.500.000 VND, tỷ giá khoá %s, quy Kíp %s (không còn quy Kíp làm tiền dòng)" % (
                 r, x and x.get("tien_lak")), x)
        rec = BTC.ghi(db, BTC.NO_NCC, "thu-g12-" + g1.id[:6], dt.date(2026, 10, 1), [x], "thử G12", trip_id=g1.id)
        dung(rec.tien_te == "VND" and rec.tong == 2500000, "bút toán một tiền VND: tổng 2.500.000 VND", (rec.tien_te, rec.tong))
        e = GBT.dung_goi(db, rec)["Entries"][0]
        dung(e["Amount"] == 2500000 and e["CurrencyId"] == 1 and e["ExchangeRate"] == r and e["DebitAccount"] == "625"
             and e["CreditAccount"] == "4021", "gói gửi: Amount 2.500.000, CurrencyId VND, ExchangeRate = tỷ giá phiếu", e)
        lak = next((y for y in bo[BTC.NO_NCC][0] if y.get("ccy") == "LAK"), None)
        dung(lak is None or "ty_gia" not in lak, "dòng Kíp giữ như cũ (không tỷ giá)")
        # G9 — câu báo
        d2 = M.TripExpense(trip_id=g1.id, section="fuel", line_no=10, item_key="diesel", qty=10, unit_price=0, currency="LAK", source="kho",
                           paid_by_epl=True)
        try:
            BTC.chan_khoa_chua_xuat(g1, [d2])
            dung(False, "dầu kho chưa cấp phải chặn khoá")
        except HTTPException as e2:
            dt_ = e2.detail
            dung("Quản lý kho → Danh sách chứng từ → Cấp dầu theo phiếu đề nghị" in dt_["loi"] and "màn Cấp phát" not in dt_["loi"]
                 and "ການຈັດການສາງ → ລາຍການເອກະສານ → ຈ່າຍນໍ້າມັນຕາມໃບສະເໜີ" in dt_["loi_lo"]
                 and "Warehouse management → Document list → Issue fuel by request" in dt_["loi_en"],
                 "G9: câu báo chỉ đúng màn Web (ba thứ tiếng)", dt_["loi"][-140:])
        t1 = T.phieu(db, "THU-KBAZ-T1/EPL")
        d3 = M.TripExpense(trip_id=t1.id, section="fuel", line_no=11, item_key="diesel", qty=10, unit_price=1, currency="LAK", source="kho",
                           paid_by_epl=False)
        try:
            BTC.chan_kho_xe_thue_tu_tra(t1, d3, [d3])
            dung(False, "xe thuê chủ xe tự trả dòng kho phải chặn")
        except HTTPException as e3:
            dung("kho tạm" not in e3.detail["loi"] and "ສາງຊົ່ວຄາວ" not in e3.detail["loi_lo"] and "temporary" not in e3.detail["loi_en"],
                 "G9: câu dòng kho xe thuê bỏ «kho tạm»", e3.detail["loi"][-60:])


# ================================================================ G2 — SO quầy cấn trừ vào tiền trả đối tác
def _dat_quay(goc_lak, r_vnd):
    """Ba SO quầy + hai SO không phải quầy: Q1 300.000 LAK (cũ nhất) · Q3 1.000.000 VND · Q2 lớn hơn phần còn lại (để lại)."""
    Q.so.clear(); Q.tkn.clear(); Q.loi.clear()
    Q.so.update({
        "TK-QUAY-1": {"ccy": "LAK", "tien": 300000.0, "con": 300000.0, "ngay": "2026-09-20T08:00:00", "nguon": "MANUAL"},
        "TK-QUAY-3": {"ccy": "VND", "tien": 1500000.0, "con": 1000000.0, "ngay": "2026-09-25T08:00:00", "nguon": "MANUAL"},
        "TK-QUAY-2": {"ccy": "LAK", "tien": float(goc_lak), "con": float(goc_lak), "ngay": "2026-09-28T08:00:00", "nguon": "CRM_QUOTE"},
        "TK-CUOC-X": {"ccy": "USD", "tien": 500.0, "con": 500.0, "ngay": "2026-09-21T08:00:00", "nguon": "LOGISTICS"},
    })


def ca_g2():
    print("G2. Kho QLSX: chủ xe mua ở quầy (SO bán hàng) bị cấn trừ vào tiền trả đối tác")
    co_gui(False)
    os.environ["KHO_NGUON"] = "qlsx"
    try:
        with T.Phien() as db:
            t1 = T.phieu(db, "THU-KBAZ-T1/EPL")
            T._co_so(db, t1)                                        # chưa trả + SO nhiên liệu (máy giả)
            x0 = TC.dong_phieu(db, t1)
            goc = x0["con_tra_lak"]                                 # còn trả sau cấn trừ SO nhiên liệu
            r_vnd = 1.2
            _dat_quay(goc, r_vnd)
            hang = TC.hang_cho_tru(db, t1.owner_id, ACCT)
            so_nl = NL.so_cua(db, t1).order_code
            dung([h["so"] for h in hang] == ["TK-QUAY-1", "TK-QUAY-3", "TK-QUAY-2"] and all(h["loai"] == TC.LOAI_QUAY for h in hang),
                 "đọc công nợ đối tác: chỉ SO bán hàng còn nợ, cũ trước — bỏ SO nhiên liệu %s và SO cước (OrderSource LOGISTICS)" % so_nl,
                 [h["so"] for h in hang])
            h3 = hang[1]
            dung(h3["currency"] == "VND" and h3["total"] == 1000000 and h3["ty_gia"] == r_vnd and h3["total_lak"] == 1200000,
                 "SO VND: cấn trừ phần CÒN NỢ 1.000.000 VND, tỷ giá hiện hành 1,2 → 1.200.000 Kíp", h3)
            dung(goc > 1500000, "T1 còn trả sau dầu %s Kíp > 1.500.000 (đủ cho Q1 + Q3)" % goc)
            # xem trước (màn Xe liên kết / hộp hỏi màn Tất toán đối tác)
            xt = RCX.hang_quay(t1.owner_id, trip_ids=t1.id, db=db, user=ACCT)
            u = xt["uoc_tinh"]
            dung(u["tru_lak"] == 1500000 and [h["doc_no"] for h in u["hang"]] == ["TK-QUAY-1", "TK-QUAY-3"]
                 and [h["doc_no"] for h in u["hang_de_lai"]] == ["TK-QUAY-2"], "xem trước: trừ Q1 + Q3 = 1.500.000 Kíp, Q2 không vừa → để lại",
                 (u["tru_lak"], u["tra_thuc_lak"]))
            # bảng Tất toán đối tác: khung quầy
            ky = (t1.out_date or t1.doc_date).strftime("%Y-%m")
            b = T.RTD.bang(ky=ky, owner_id=t1.owner_id, cap_nhat=1, db=db, user=ACCT)
            qy = b.get("quay") or {}
            u = qy.get("uoc_tinh") or {}
            lak = {x["so"]: x["con_no_lak"] for x in qy.get("ds") or []}
            # ước tính cho MỌI chuyến chưa trả của đối tác trong kỳ (d7 có thể có chuyến thật khác của cùng đối tác) → kiểm nhất quán
            dung(qy.get("doc") is True and list(lak) == ["TK-QUAY-1", "TK-QUAY-3", "TK-QUAY-2"]
                 and qy["con_no_lak"] == 300000 + 1200000 + goc and u.get("so_tru", [])[:2] == ["TK-QUAY-1", "TK-QUAY-3"]
                 and set(u["so_tru"]) | set(u["so_de_lai"]) == set(lak) and u["tru_lak"] == sum(lak[s] for s in u["so_tru"]),
                 "GET Tất toán đối tác (một đối tác): khung `quay` — 3 SO còn nợ, ước trừ cũ trước (Q1, Q3…)",
                 {k: qy.get(k) for k in ("doc", "con_no_lak", "uoc_tinh")})
            T._kiem_khoa(b)
            n_kho = len([g for g in GIA.nhan if str(g[1]).startswith("kho ")])
            n_btc = db.query(M.ButToanCho).filter(M.ButToanCho.nguon == TC.NGUON_BAN).count()
            # lập đề nghị
            r = CHI.de_nghi_tra_chu_xe(db, t1.owner_id, [t1.id], "cash", ACCT)
            cts = {c.order_code: c for c in CHI._can_tru_cua(db, r)}
            dung(set(cts) == {so_nl, "TK-QUAY-1", "TK-QUAY-3"} and all(c.status == "da_gui" and c.so_tkn for c in cts.values()),
                 "lập đề nghị: cấn trừ SO nhiên liệu + Q1 + Q3 (TKN), Q2 không", {k: (c.status, c.so_tkn) for k, c in cts.items()})
            c1, c3 = cts["TK-QUAY-1"], cts["TK-QUAY-3"]
            b1, b3 = json.loads(c1.request_body), json.loads(c3.request_body)
            dung(c1.trip_id is None and c1.currency == "LAK" and c1.amount == 300000 and set(b1) == {"OrderCode", "Amount", "CurrencyCode",
                                                                                                      "RefNo", "Reason", "Date"}
                 and b1["Reason"] == "Mua ở quầy" and c1.idempotency_key == "logistics-offset:%s:TK-QUAY-1" % r.ref_no,
                 "Q1: cấn trừ 300.000 LAK, khoá logistics-offset:<TCX>:<SO>, thân như SO nhiên liệu, lý do ngắn", b1)
            dung(c3.currency == "VND" and c3.amount == 1000000 and b3["CurrencyCode"] == "VND" and b3["ExchangeRate"] == r_vnd
                 and Q.so["TK-QUAY-3"]["con"] == 0 and Q.so["TK-QUAY-1"]["con"] == 0 and Q.so["TK-QUAY-2"]["con"] == goc,
                 "Q3: cấn trừ theo TIỀN CỦA SO (1.000.000 VND, ExchangeRate 1,2); bên kế toán còn nợ Q1 = Q3 = 0, Q2 nguyên", b3)
            pc = GIA.phieu[r.real_id]["body"] if r.real_id in GIA.phieu else None
            dung(r.status == "da_gui" and abs(r.amount_lak - (goc - 1500000)) <= 1 and pc and abs(pc["Header"]["Amount"] - r.amount) < 0.011
                 and "mua ở quầy SO TK-QUAY-1, TK-QUAY-3" in pc["Header"]["Description"],
                 "phiếu chi phần còn lại = %s − 1.500.000 = %s Kíp (%s %s)" % (goc, r.amount_lak, r.amount, r.currency),
                 pc["Header"]["Description"] if pc else None)
            t = json.loads(r.tru_hang)
            dung(t["tru_lak"] == 1500000 and [h.get("loai") for h in t["hang"]] == ["so_quay", "so_quay"] and not t["chot"],
                 "đề nghị lưu phần trừ quầy (loai so_quay)", {k: t[k] for k in ("tru_lak", "tra_thuc_lak")})
            dung(len([g for g in GIA.nhan if str(g[1]).startswith("kho ")]) == n_kho, "không gọi kho tạm (giữ chỗ phiếu bán)")
            dung([h["so"] for h in TC.hang_cho_tru(db, t1.owner_id, ACCT)] == ["TK-QUAY-2"], "sau cấn trừ: chỉ còn Q2 chờ trừ")
            GIA.da_ghi_so.add(r.real_id)                            # thủ quỹ ghi sổ → đã chi, chốt hàng quầy không ghi 4022/707
            CHI.dong_bo_chu_xe(db, r, ACCT)
            db.expire_all()
            t = json.loads(r.tru_hang)
            dung(r.status == "da_chi" and t["chot"] and db.query(M.ButToanCho).filter(M.ButToanCho.nguon == TC.NGUON_BAN).count() == n_btc
                 and len([g for g in GIA.nhan if str(g[1]).startswith("kho ")]) == n_kho,
                 "thủ quỹ ghi sổ: đề nghị đã chi, không chốt kho tạm, không ghi bút toán Nợ 4022 / Có 707 (bên kế toán đã ghi cấn trừ)")
        with T.Phien() as db:                                       # bỏ đề nghị → gỡ cấn trừ SO quầy
            t1 = T.phieu(db, "THU-KBAZ-T1/EPL")
            T._co_so(db, t1)
            goc = TC.dong_phieu(db, t1)["con_tra_lak"]
            _dat_quay(goc, 1.2)
            r = CHI.de_nghi_tra_chu_xe(db, t1.owner_id, [t1.id], "bank", ACCT)
            n_kho = len([g for g in GIA.nhan if str(g[1]).startswith("kho ")])
            kq = T.RTD.viec_de_nghi(r.ref_no, "bo", db=db, user=ACCT)
            q = [c for c in kq["can_tru"] if c["loai"] == "so_quay"]
            dung(kq["trang_thai"] == "huy" and len(q) == 2 and all(c["trang_thai"] == "huy" for c in q)
                 and Q.so["TK-QUAY-1"]["con"] == 300000 and Q.so["TK-QUAY-3"]["con"] == 1000000
                 and len([g for g in GIA.nhan if str(g[1]).startswith("kho ")]) == n_kho,
                 "bỏ đề nghị: gỡ cấn trừ SO quầy (bên kế toán trả lại nợ), không gọi kho tạm", [(c["order_code"], c["trang_thai"]) for c in q])
        with T.Phien() as db:                                       # SO đang chờ cấn trừ trong đề nghị lỗi → không vào đề nghị khác
            t1 = T.phieu(db, "THU-KBAZ-T1/EPL")
            T._co_so(db, t1)
            goc = TC.dong_phieu(db, t1)["con_tra_lak"]
            _dat_quay(goc, 1.2)
            Q.loi.add("TK-QUAY-1")
            ref = None
            try:
                CHI.de_nghi_tra_chu_xe(db, t1.owner_id, [t1.id], "cash", ACCT)
                dung(False, "cấn trừ Q1 bị từ chối → đề nghị lỗi")
            except HTTPException as e:
                ref = e.detail.get("so")
                dung(ref and "TK-QUAY-1" in (e.detail.get("loi") or "") + str(e.detail), "cấn trừ Q1 bị từ chối → đề nghị lỗi, báo số đề nghị",
                     {k: e.detail.get(k) for k in ("ma", "so")})
            sq = {x["so"]: x for x in TC.so_quay(db, t1.owner_id)}
            dung(sq["TK-QUAY-1"]["dang_de_nghi"] == ref and "TK-QUAY-1" not in [h["so"] for h in TC.hang_cho_tru(db, t1.owner_id, ACCT)],
                 "Q1 đang chờ cấn trừ trong đề nghị %s → không vào đề nghị khác (không trừ hai lần)" % ref)
            kq = T.RTD.viec_de_nghi(ref, "gui-lai", db=db, user=ACCT)
            dung(kq["trang_thai"] == "da_gui" and all(c["trang_thai"] == "da_gui" for c in kq["can_tru"]) and Q.so["TK-QUAY-1"]["con"] == 0,
                 "gửi lại: cấn trừ tiếp Q1 (cùng khoá) rồi phiếu chi", [(c["order_code"], c["trang_thai"]) for c in kq["can_tru"]])
        with T.Phien() as db:                                       # cấn trừ hết bằng SO quầy → không phiếu chi
            t1 = T.phieu(db, "THU-KBAZ-T1/EPL")
            T._co_so(db, t1)
            goc = TC.dong_phieu(db, t1)["con_tra_lak"]
            Q.so.clear(); Q.tkn.clear(); Q.loi.clear()
            Q.so["TK-QUAY-9"] = {"ccy": "LAK", "tien": float(goc), "con": float(goc), "ngay": "2026-09-30T08:00:00", "nguon": "MANUAL"}
            n0 = len(GIA.phieu)
            kq = T.RTD.lap_de_nghi({"owner_id": t1.owner_id, "trip_ids": [t1.id], "cach_tra": "cash"}, db=db, user=ACCT)
            t1 = db.get(M.Trip, t1.id)
            dung(kq["trang_thai"] == "da_chi" and kq["phieu_chi"] is None and len(GIA.phieu) == n0 and Q.so["TK-QUAY-9"]["con"] == 0
                 and (t1.owner_payment_id or "") == "TUNE:" + kq["so"] and (t1.owner_paid_lak or 0) == 0,
                 "SO quầy vừa đúng phần còn trả: cấn trừ hết, không phiếu chi, phiếu «đã trả» 0", (kq["so"], t1.owner_paid_lak))
        with T.Phien() as db:                                       # kho tạm: đường cũ không đổi (không đọc công nợ đối tác)
            os.environ["KHO_NGUON"] = "kho_tam"
            t1 = T.phieu(db, "THU-KBAZ-T1/EPL")
            n = len([g for g in GIA.nhan if "customer-detail" in str(g[1])])
            dung(TC.hang_cho_tru(db, t1.owner_id, ACCT) == [] and len([g for g in GIA.nhan if "customer-detail" in str(g[1])]) == n
                 and T.RTD.bang(ky="2026-10", owner_id=t1.owner_id, cap_nhat=0, db=db, user=ACCT).get("quay") is None,
                 "KHO_NGUON=kho_tam: hỏi kho tạm như cũ, không có khung quầy")
    finally:
        os.environ["KHO_NGUON"] = "kho_tam"


# ================================================================ đường ĐỌC an toàn (06/10): 5xx không đánh "phiếu mất", đọc công nợ không tạo đối tượng
def _chi_tune_that():
    """Bản nạp riêng của services/chi_tune.py với `_goi` THẬT (bài cha đã thay chi_tune._goi bằng bản giả) — lời gọi đi qua
    urllib.request.urlopen giả trong ca, không ra mạng (gui_tune.cau_hinh đã giả: máy ke-toan-gia.local)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("chi_tune_that_0610", os.path.join(T.GOC, "backend", "app", "services", "chi_tune.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _Tra:
    def __init__(self, ma, than):
        self.status, self._b = ma, json.dumps(than).encode("utf-8")

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def ca_doc():
    import io
    import types
    import urllib.error
    import urllib.request
    print("D. Đường đọc an toàn: doc_phieu chỉ đánh «phiếu mất» khi 4xx thật · đọc công nợ không tạo đối tượng bên kế toán")
    CT0 = _chi_tune_that()
    goc = urllib.request.urlopen

    class DbGia:
        n = 0

        def commit(self):
            DbGia.n += 1

    def thu(kieu):
        def mo(yc, timeout=None):
            if kieu == "mang":
                raise urllib.error.URLError("giả lập mất mạng")
            ma, than = kieu
            if ma >= 400:
                raise urllib.error.HTTPError(yc.full_url, ma, "giả", {}, io.BytesIO(json.dumps(than).encode("utf-8")))
            return _Tra(ma, than)
        urllib.request.urlopen = mo
        rec = types.SimpleNamespace(real_id=4242, status="da_gui", error_code=None, error_message=None, document_no="1368-CTR-THU",
                                    checked_at=None)
        DbGia.n, loi = 0, None
        try:
            kq = CT0.doc_phieu(DbGia(), rec)
        except HTTPException as e:
            kq, loi = None, e
        finally:
            urllib.request.urlopen = goc
        return rec, kq, loi
    try:
        for ten, kieu in (("HTTP 500", (500, {"Success": False, "Code": 500, "Message": "lỗi máy chủ"})),
                          ("HTTP 503 thân rỗng", (503, {})),
                          ("HTTP 200 kèm Success false · Code 500 (lỗi chưa bắt bên đó)", (200, {"Success": False, "Code": 500, "Message": "x"})),
                          ("mất mạng", "mang"), ("HTTP 403 (quyền)", (403, {"Success": False, "Code": 403, "Message": "Forbidden"}))):
            rec, kq, loi = thu(kieu)
            dung(loi is not None and rec.status == "da_gui" and rec.error_code is None and DbGia.n == 0,
                 "%s → báo lỗi tạm, phiếu GIỮ «chờ chi» (không đánh PHIEU_CHI_MAT, không ghi gì)" % ten,
                 (loi.detail.get("ma") if loi else None, rec.status, rec.error_code))
        rec, kq, loi = thu((404, {"Success": False, "Code": 404, "Message": "Không tìm thấy chứng từ"}))
        dung(loi is not None and rec.status == "loi" and rec.error_code == CHI.MAT, "HTTP 404 (không thấy) → PHIEU_CHI_MAT như cũ",
             (rec.status, rec.error_code))
        rec, kq, loi = thu((200, {"Success": False, "Message": "Chứng từ không tồn tại"}))
        dung(loi is not None and rec.error_code == CHI.MAT, "HTTP 200 kèm Success false (không Code) — bên kia từ chối đọc → PHIEU_CHI_MAT như cũ")
        rec, kq, loi = thu((200, {"Success": True, "Result": {"Master": None, "Entries": []}}))
        dung(loi is None and kq is None and rec.error_code == CHI.MAT, "Success true · Master null (phiếu đã xoá) → PHIEU_CHI_MAT như cũ")
        rec, kq, loi = thu((200, {"Success": True, "Result": {"Master": {"STATUS": 1, "DOCUMENTNO": "1368-CTR-THU"}}}))
        dung(loi is None and kq and kq["STATUS"] == 1 and rec.status == "da_gui", "đọc được → trả Master, không đổi trạng thái")
    finally:
        urllib.request.urlopen = goc

    os.environ["KHO_NGUON"] = "qlsx"
    try:
        with T.Phien() as db:
            o = M.Owner(id="thu0610lav", name="Đối tác lạ (thử 06/10)")
            k = M.Customer(id="thu0610khl", name="Khách lạ (thử 06/10)", code="KHLATHU0610")
            db.add_all([o, k])
            db.commit()
            DT.khong_co.update({"EPLCX-thu0610lav", "KHLATHU0610"})
            DT.upsert.clear()
            n_cd = len([g for g in GIA.nhan if "customer-detail" in str(g[1])])
            kq = CHI.cong_no_doi_tac(db, o)
            dung(not DT.upsert and kq.get("chua_co_doi_tuong") and kq["no"] == [] and db.get(M.DoiTuongTune, ("chu_xe", o.id)) is None
                 and len([g for g in GIA.nhan if "customer-detail" in str(g[1])]) == n_cd,
                 "công nợ đối tác chưa có bên kế toán: chỉ tìm, KHÔNG upsert, trả công nợ rỗng", DT.upsert)
            dung(TC.hang_cho_tru(db, o.id, ACCT) == [] and not DT.upsert, "trừ hàng quầy (đọc SO quầy) của đối tác lạ: rỗng, không upsert")
            b = T.RTD.bang(ky="2026-10", owner_id=o.id, cap_nhat=1, db=db, user=ACCT)
            dung(not DT.upsert and b.get("quay") is not None, "màn Tất toán đối tác mở đối tác lạ: không upsert", b.get("quay"))
            try:
                CHI.cong_no_khach(db, k)
                dung(False, "khách có mã mà bên kế toán không có → báo lỗi")
            except HTTPException as e:
                dung(e.detail.get("ma") == "MA_KHONG_CO_BEN_KE_TOAN" and not DT.upsert, "công nợ khách mã lạ: báo MA_KHONG_CO_BEN_KE_TOAN, "
                     "không upsert", e.detail.get("loi"))
            oid = CHI.doi_tuong(db, "chu_xe", o.id, o.name, to_chuc=False)
            dung(DT.upsert == [("/api/v1/master-data/suppliers/upsert", "EPLCX-thu0610lav")] and db.get(M.DoiTuongTune, ("chu_xe", o.id)).obj_id == oid,
                 "đường lập chứng từ (mặc định) vẫn TẠO đối tượng khi chưa có", DT.upsert)
            kq = CHI.cong_no_doi_tac(db, o)
            dung(kq.get("obj_id") == oid and not kq.get("chua_co_doi_tuong") and len(DT.upsert) == 1,
                 "đã có đối tượng → đọc công nợ thật (customer-detail), không tạo thêm")
    finally:
        os.environ["KHO_NGUON"] = "kho_tam"
        DT.khong_co.clear()


def main():
    for ca in (ca_g1, ca_g1_gui, ca_g12, ca_g2, ca_doc):
        try:
            ca()
        except Exception as e:                       # noqa: BLE001 — một ca vỡ thì ghi, chạy ca sau
            import traceback
            traceback.print_exc()
            dung(False, "%s vỡ: %s" % (ca.__name__, str(e).replace(T.URL, "<url>")[:300]))
    print("đã ROLLBACK mọi ca — bản sao d7 không đổi")
    print("TỔNG: %d/%d đạt" % (sum(T.KQ), len(T.KQ)))
    sys.exit(0 if all(T.KQ) else 1)


if __name__ == "__main__":
    main()
