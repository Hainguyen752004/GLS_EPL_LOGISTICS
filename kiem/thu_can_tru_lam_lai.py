# -*- coding: utf-8 -*-
"""UAT 03/10 — cấn trừ SO nhiên liệu khi bên kế toán ĐÃ GỠ lần cấn trừ trước (bút toán cấn trừ hỏng: diễn giải 229 ký tự vượt cột
DOC_DESCRIPTION → 422 DEBT_OFFSET_JOURNAL_FAILED, bên đó tự gỡ TKN). Chạy trên bản sao _d7, mọi thứ trong một giao dịch ngoài rồi
ROLLBACK; hệ kế toán anh Tune GIẢ LẬP (dùng lại bộ giả của kiem/thu_tat_toan_doi_tac.py) — không gọi mạng thật.

    python kiem/thu_can_tru_lam_lai.py

  1 Không cần DB: gửi lại cùng khoá → bên kia trả bản ĐÃ GỠ (Success, State CANCELLED, Replayed) → KHÔNG ghi "đã cấn trừ"; lập lần
    mới (khoá :r<lần>, lý do ngắn) và cấn trừ thật. Bản đã gỡ trả về cả với khoá mới → lỗi 409 DEBT_OFFSET_DA_GO, không ghi đã gửi.
  2 Đề nghị thật trên máy thử (đề nghị đang "lỗi" vì 52508, nếu có): «Gửi lại» → cấn trừ mới rồi phiếu chi phần còn lại.
"""
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thu_tat_toan_doi_tac as T                        # noqa: E402  (đặt DATABASE_URL = _d7, cài bộ giả hệ kế toán)

from fastapi import HTTPException                       # noqa: E402

import models as M                                      # noqa: E402
from services import chi_tune as CHI                    # noqa: E402
from services import so_nhien_lieu as NL                # noqa: E402

GIA, dung = T.GIA, T.dung


class DbGia:
    def __init__(self, trip):
        self.trip = trip

    def get(self, cls, i):
        return self.trip if cls is M.Trip and i == self.trip.id else None

    def commit(self):
        pass


def ca_1():
    print("1. Gửi lại khi bên kia đã gỡ lần cấn trừ (không DB)")
    T.reset_gia()
    GIA.so["EPLLAO-x"] = {"key": "k", "body": "{}", "kq": {"orderCode": "TK-GIA-1"}, "total": 4950000.0, "remaining": 4950000.0}
    p = types.SimpleNamespace(id="x", doc_no="G4-0002-10/EPL")
    khoa = NL.khoa_can_tru("TCX-GIA-1", "TK-GIA-1")
    than_cu = NL.goi_can_tru("TK-GIA-1", 4950000, "TCX-GIA-1", "Cấn trừ SO nhiên liệu TK-GIA-1 vào tiền trả đối tác ທ້າວ ຄຳຫລ້າ · phiếu "
                             "G4-0002-10/EPL · đề nghị TCX-GIA-1")
    ct = types.SimpleNamespace(status="loi", attempts=1, last_attempt_at=None, request_body=json.dumps(than_cu, ensure_ascii=False),
                               idempotency_key=khoa, order_code="TK-GIA-1", ref_no="TCX-GIA-1", amount=4950000.0, trip_id="x",
                               http_status=422, response_body=None, error_code="DEBT_OFFSET_JOURNAL_FAILED", error_message="…",
                               so_tkn=None, real_id=None)
    GIA.go[khoa] = "4-TKN-1368-2-261003-0001"                # lần đầu: bên kia gỡ TKN này
    n0 = len(GIA.nhan)
    NL.gui_can_tru(DbGia(p), ct)
    goi = [g for g in GIA.nhan[n0:] if g[1] == NL.DUONG_CAN_TRU]
    dung(len(goi) == 2 and goi[0][3] == khoa and goi[1][3] == khoa + ":r2", "gửi cùng khoá → bản đã gỡ → gửi lần mới bằng khoá :r2",
         [g[3] for g in goi])
    dung(ct.status == "da_gui" and ct.so_tkn and ct.so_tkn != "4-TKN-1368-2-261003-0001" and ct.idempotency_key == khoa + ":r2",
         "lần cấn trừ mới: đã gửi, số TKN mới (không nhận số TKN đã gỡ)", (ct.status, ct.so_tkn))
    dung(goi[1][2]["Reason"] == "DO G4-0002-10/EPL" and json.loads(ct.request_body)["Reason"] == "DO G4-0002-10/EPL"
         and GIA.so["EPLLAO-x"]["remaining"] == 0, "thân mới: lý do ngắn «DO <số DO>», trừ đúng còn nợ SO", goi[1][2]["Reason"])
    d = "Cấn trừ công nợ đối tác · %s · SO %s · 4-TKN-1368-2-261003-0001 · %s" % ("TCX-261003140253-0a07", "TK-20261003-000172",
                                                                               NL.ly_do_can_tru("G4-0002-10/EPL"))
    dung(len(d) <= 130, "diễn giải bên kế toán ghép với lý do mới: %d ký tự (lần hỏng 229)" % len(d))
    # bản đã gỡ trả về cả với khoá mới → lỗi rõ, không ghi "đã gửi"
    ct2 = types.SimpleNamespace(**dict(vars(ct), status="loi", idempotency_key="logistics-offset:TCX-GIA-2:TK-GIA-1", attempts=3,
                                       ref_no="TCX-GIA-2", so_tkn=None))
    GIA.go[ct2.idempotency_key] = "4-TKN-GO-A"
    GIA.go[ct2.idempotency_key + ":r4"] = "4-TKN-GO-B"
    try:
        NL.gui_can_tru(DbGia(p), ct2)
        dung(False, "bản đã gỡ hai lần phải báo lỗi")
    except HTTPException as e:
        dung(e.status_code == 409 and e.detail["ma"] == "DEBT_OFFSET_DA_GO" and ct2.status == "loi" and not ct2.so_tkn,
             "bản đã gỡ cả với khoá mới → 409 DEBT_OFFSET_DA_GO, không ghi đã cấn trừ", e.detail["loi"])


def ca_2():
    print("2. Đề nghị đang lỗi trên máy thử → Gửi lại")
    with T.Phien() as db:
        r = (db.query(M.ChiChuXeTune).filter(M.ChiChuXeTune.status == "loi").order_by(M.ChiChuXeTune.created_at.desc()).first())
        cts = CHI._can_tru_cua(db, r) if r is not None else []
        ct = next((c for c in cts if c.status == "loi" and c.error_code == "DEBT_OFFSET_JOURNAL_FAILED"), None)
        if ct is None:
            print("  (máy thử không có đề nghị lỗi 52508 — bỏ ca)")
            return
        T.reset_gia()
        p = db.get(M.Trip, ct.trip_id)
        GIA.so["EPLLAO-" + p.id] = {"key": "k", "body": "{}", "kq": {"orderCode": ct.order_code, "doId": "EPLLAO-" + p.id},
                                    "total": float(ct.amount), "remaining": float(ct.amount)}
        khoa_cu = ct.idempotency_key
        GIA.go[khoa_cu] = "4-TKN-1368-2-261003-0001"
        print("    đề nghị %s · %s · cấn trừ %s Kíp SO %s · lý do cũ %d ký tự" % (r.ref_no, r.amount, ct.amount, ct.order_code,
                                                                                 len(json.loads(ct.request_body)["Reason"])))
        kq = T.RTD.viec_de_nghi(r.ref_no, "gui-lai", db=db, user=T.ACCT)
        db.refresh(ct)
        pc = GIA.phieu[r.real_id]["body"] if r.real_id in GIA.phieu else None
        dung(kq["trang_thai"] == "da_gui" and ct.status == "da_gui" and ct.idempotency_key.startswith(khoa_cu + ":r")
             and ct.so_tkn != "4-TKN-1368-2-261003-0001", "Gửi lại: cấn trừ mới (khoá %s) rồi phiếu chi" % ct.idempotency_key,
             (kq["trang_thai"], ct.so_tkn))
        dung(pc is not None and abs(pc["Header"]["Amount"] - r.amount) < 0.011 and pc["Entries"][0]["DebitAccount"] == "4022",
             "phiếu chi phần còn lại %s %s (Nợ 4022)" % (r.amount, r.currency), pc["Header"]["Amount"] if pc else None)


def main():
    for ca in (ca_1, ca_2):
        try:
            ca()
        except Exception as e:                       # noqa: BLE001
            import traceback
            traceback.print_exc()
            dung(False, "%s vỡ: %s" % (ca.__name__, e))
    print("đã ROLLBACK — bản sao d7 không đổi")
    print("TỔNG: %d/%d đạt" % (sum(T.KQ), len(T.KQ)))


if __name__ == "__main__":
    main()
