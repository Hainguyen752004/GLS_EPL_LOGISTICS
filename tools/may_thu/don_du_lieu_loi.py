# -*- coding: utf-8 -*-
"""DỌN DỮ LIỆU LỖI / THIẾU TRƯỜNG của trang điều xe trên DB BẢN SAO máy thử (epl_lao_d<số>) — trước khi chủ dự án bấm tay demo.

    python tools/may_thu/don_du_lieu_loi.py                    CHỈ LIỆT KÊ — phiên CHỈ ĐỌC (Postgres tự chặn mọi lệnh ghi)
    python tools/may_thu/don_du_lieu_loi.py --khoa-tune        … và in dòng KHOÁ CÒN SỐNG để dán vào @KhoaTrangDieuXe của
                                                               GLS-QLSX-APIs/Backend.API/Database/Scripts/20261006_don_du_lieu_epl_loi.sql
                                                               (script đó tìm chứng từ bên anh Tune trỏ tới thứ trang điều xe không còn)
    python tools/may_thu/don_du_lieu_loi.py --that             làm các mục "XOÁ" / "SỬA" trong MỘT giao dịch, hậu kiểm rồi COMMIT
    python tools/may_thu/don_du_lieu_loi.py --that --gom-trang-thai    xoá cả DO kẹt trạng thái vô lý (nhóm G3; mặc định chỉ liệt kê)
    --tep url_epl_lao_d8.txt                                   tệp chuỗi nối khác trong .may_thu (mặc định url_epl_lao_d7.txt)

NHÓM (G…) — mỗi nhóm in: số lượng, mã (DO số / số chứng từ), vì sao coi là lỗi, việc sẽ làm, rủi ro:
  G1  DO thiếu trường bắt buộc (loại chuyến, ngày lập, khách, tuyến, xe, tài xế, điểm đi / đến)        → XOÁ DO
  G2  DO rác thử (số / khách / tài xế / ghi chú mang dấu "test", "thử", "UAT", "THU-")                  → XOÁ DO
      DO số lạ (không theo mẫu G4-/T4-nnnn-mm/EPL) mà không có dấu thử                                 → chỉ liệt kê
  G3  DO kẹt trạng thái vô lý (đã về mà thiếu ngày đi, khoá mà thiếu cân / chưa về / mục I–II chưa kiểm,
      gom đã về mà chưa nhập kho hàng, giao lấy lô mà chưa xuất, thiếu mục duyệt…)                       → liệt kê (--gom-trang-thai: XOÁ)
  G4  Dòng chi lỗi (số lượng ≤ 0, đơn giá âm, EPL trả mà tiền 0, mục / tiền tệ lạ, không tên)          → XOÁ DÒNG khi DO chưa khoá,
      mục còn chờ / đã nhập, chưa xuất kho / trừ thẻ, không sự kiện nào trỏ tới; còn lại chỉ liệt kê
  G4b Dòng tiền 0 do CHỦ XE TỰ TRẢ (xe thuê tự lo — đúng kịch bản)                                      → giữ
  G5  Phiếu lĩnh / đề nghị tạm ứng lỗi (trạng thái lạ, đã cấp mà thiếu số cấp, tạm ứng ≤ 0)             → liệt kê
  G6  Bút toán chờ lỗi / kẹt (trạng thái lạ, gửi lỗi, chờ đảo, đã gửi mà thiếu số bên kia)               → liệt kê;
      bút toán CHỜ GỬI mồ côi (DO đã xoá)                                                               → SỬA thành "huỷ"
  G7  Bản ghi gửi sang anh Tune lỗi / kẹt (SO lỗi, phiếu chi lỗi, tạm ứng chờ chi mà chuyến đã về…)      → liệt kê;
      lượt gửi SO lỗi HẲN (không có SO bên kia) của DO đã xoá                                           → XOÁ
  G8  Sổ chứng từ: tờ mồ côi CHƯA đối chiếu (DO / phiếu lĩnh đã xoá)                                    → XOÁ; tờ đẩy lỗi → liệt kê
  G9  Kho hàng ở bãi: tồn lô âm, xuất không rõ lô                                                       → liệt kê;
      đơn điều chỉnh trỏ lô không còn                                                                   → XOÁ
  G10 Dòng xuất kho TẠM cũ (trước 05/10) — không trả kho tự động được, chặn xoá DO                     → liệt kê
  G11 Xe / tài xế kẹt "đang chạy" mà không còn DO nào chưa về                                           → SỬA về "rảnh";
      xe / tài xế đứng trên ≥ 2 DO chưa về                                                              → liệt kê
  G12 Danh mục thiếu trường (khách chưa có mã kế toán, trạm ngoài thiếu NCC, NCC thiếu định khoản, xe thuê
      thiếu chủ) và tên mang dấu thử                                                                     → liệt kê (danh mục không xoá);
      tuyến thử "THU…" đã ngưng mà không ai dùng                                                        → XOÁ
  G13 Ánh xạ đối tượng bên anh Tune (doi_tuong_tune) trỏ người không còn                                → liệt kê

XOÁ DO đi ĐÚNG đường xoá của hệ (routes/phieu.py xoa_phieu, vai Sếp) nhưng KHÔNG GỌI MẠNG: DO còn bất cứ thứ gì đã sang hệ anh Tune
(SO cước / SO nhiên liệu đã tạo hoặc gửi chưa rõ, phiếu chi tạm ứng / mục V–VI có phiếu bên đó, đề nghị trả chủ xe, đã trả chủ xe,
bút toán đã gửi hoặc gửi chưa rõ, dòng đã xuất kho QLSX, dòng kho tạm cũ, đã trừ thẻ cao tốc, đã cấn trừ) hay lô gom đã có DO giao
khác lấy → KHÔNG xoá, in lý do — gỡ bên anh Tune trước (script SQL ở trên) rồi chạy lại. Xoá thì kéo theo: phiếu chi lỗi chưa có
bên kia, bút toán chờ gửi → "huỷ" (giữ dấu vết như BTC.huy), sổ dầu cũ của phiếu lĩnh + tờ, sổ kho hàng + đơn điều chỉnh + tờ
PNK_HH / PXK_HH / DC_HH chưa đối chiếu, nhả xe / tài xế, sự kiện, đính kèm, dòng chi, mục, nhật ký, tờ chứng từ chưa đối chiếu, lượt
gửi SO lỗi hẳn; khoá ngoại tự xoá dòng hàng, phiếu lĩnh, lần thu, GPS… Tờ ĐÃ đối chiếu giữ nguyên (như hệ).
Tệp đính kèm trên đĩa KHÔNG xoá — chỉ in đường dẫn: d7 là bản sao nên cùng mã phiếu với DB của anh, thư mục tệp có thể dùng chung.
Xong thì tăng phiên bản báo cáo '*' (bộ đệm báo cáo tính lại) — như ORM của hệ làm khi xoá hàng loạt.

Chỉ chạy trên DB tên có hậu tố bản sao (…_d<số>); gặp epl_lao / epl_ketoan thật thì dừng. Trước --that: sao lưu (pg_dump) như
don_may_thu.py. Không dừng / khởi động máy 8011 — giao dịch khoá đúng các DO sắp xoá (FOR UPDATE) rồi kiểm lại điều kiện.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

import sqlalchemy as sa

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

MT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".may_thu"))
NGUOI = "Công cụ dọn dữ liệu lỗi (don_du_lieu_loi)"

# chép từ backend/app/models.py · services/* (không import app: import là dựng engine + ghi log, và các service gọi mạng)
CHUOI = {"info": ("wait", "entered", "verified"), "trans": ("wait", "entered", "verified")}
CHUOI.update({m: ("wait", "entered", "verified", "booked", "paid") for m in ("fuel", "travel", "repair", "other")})
MUC_CHI = ("fuel", "travel", "repair", "other")
TIEN_TE = ("LAK", "USD", "THB", "VND", "CNY")
TT_VAN_CHUYEN = ("dispatched", "transit", "arrived")
TT_TAI_CHINH = ("unpaid", "partial", "paid")
TT_PHIEU_LINH = ("cho", "da_cap", "huy")
TT_BUT_TOAN = ("cho_gui", "da_gui", "huy")
CHUA_RO_SO = ("QLSX_KHONG_GOI_DUOC", "LOGISTICS_52903")          # services/gui_tune.KET_QUA_CHUA_RO
CHUA_RO_NL = ("QLSX_KHONG_GOI_DUOC", "LOGISTICS_FUEL_52953")     # services/so_nhien_lieu.KET_QUA_CHUA_RO
CHUA_RO_BT = ("KHONG_GOI_DUOC", "HTTP_5XX")                      # services/gui_but_toan_tune.CHUA_RO
MAT = "PHIEU_CHI_MAT"                                            # services/chi_tune.MAT — phiếu bên kia đã mất
TIEN_TO_QLSX = "qlsx:"
MAU_SO = r"^[GT]4-[0-9]{4}-[0-9]{2}/EPL$"                         # routes/phieu._so_phieu_moi
DAU_THU = r"(test|thử|ທົດສອບ|\muat\M|THU-|dummy|asdf)"          # Postgres ~* (không phân biệt hoa thường); ທົດສອບ = "thử"
DAU_THU_PY = r"(test|thử|ທົດສອບ|\buat\b|THU-|dummy|asdf)"      # cùng dấu, cú pháp Python re
SAI = 0.0005

VIEC = {"XOA_DO": "XOÁ DO", "XOA_DONG": "XOÁ DÒNG", "XOA": "XOÁ", "SUA": "SỬA", "GIU": "giữ — chỉ liệt kê"}


def mo(tep, that):
    url = open(os.path.join(MT, tep), encoding="utf-8").read().strip()
    ten = sa.engine.make_url(url).database or ""
    if not re.search(r"_d\d+$", ten) or ten in ("epl_lao", "epl_ketoan"):
        sys.exit("DỪNG: %s trỏ DB «%s» — công cụ chỉ chạy trên bản sao của máy thử (tên …_d<số>)." % (tep, ten))
    tuy = "-c timezone=UTC -c statement_timeout=120000" + ("" if that else " -c default_transaction_read_only=on")
    return ten, sa.create_engine(url, connect_args={"connect_timeout": 10, "options": tuy})


def q(c, sql, **kw):
    return [dict(r._mapping) for r in c.execute(sa.text(sql), kw)]


def mot(c, sql, **kw):
    r = q(c, sql, **kw)
    return r[0] if r else None


def ex(c, sql, **kw):
    return c.execute(sa.text(sql), kw).rowcount


class Nhom:
    def __init__(self, ma, ten, ly_do, rui_ro):
        self.ma, self.ten, self.ly_do, self.rui_ro, self.muc = ma, ten, ly_do, rui_ro, []

    def them(self, ma, chi_tiet, viec="GIU", **kem):
        self.muc.append(dict(kem, ma=ma, chi_tiet=chi_tiet, viec=viec))


# ================================================================ KHẢO SÁT (chỉ đọc)
def cac_do(c):
    return q(c, """
        select t.*, (select count(*) from trip_sections s where s.trip_id = t.id) n_muc,
               (select json_object_agg(s.section, s.status) from trip_sections s where s.trip_id = t.id) muc,
               exists (select 1 from goods_moves g where g.trip_id = t.id and g.kind = 'in') co_nhap,
               exists (select 1 from goods_moves g where g.trip_id = t.id and g.kind = 'out') co_xuat,
               exists (select 1 from trip_goods g where g.trip_id = t.id and g.loai = 'hang') co_hang,
               exists (select 1 from trip_goods g where g.trip_id = t.id and g.tu_phieu_id is not null) lay_lo
        from trips t order by t.created_at""")


def thieu_truong(t):
    thieu = []
    if t["kind"] not in ("gom", "giao"):
        thieu.append("loại chuyến")
    if not t["doc_date"]:
        thieu.append("ngày lập")
    if not t["customer_id"] or not (t["customer_name"] or "").strip():
        thieu.append("khách")
    if not t["route_id"]:
        thieu.append("tuyến")
    if not t["vehicle_id"] or not (t["truck_no"] or "").strip():
        thieu.append("xe")
    if not t["driver_id"] or not (t["driver_name"] or "").strip():
        thieu.append("tài xế")
    if not (t["origin"] or "").strip() or not (t["destination"] or "").strip():
        thieu.append("điểm đi / đến")
    return thieu


def vo_ly(t):
    ly, ts, muc = [], t["transport_status"], t["muc"] or {}
    if ts not in TT_VAN_CHUYEN:
        ly.append("trạng thái vận chuyển lạ «%s»" % ts)
    if t["finance_status"] not in TT_TAI_CHINH:
        ly.append("trạng thái thu lạ «%s»" % t["finance_status"])
    if ts in ("transit", "arrived") and not t["out_date"]:
        ly.append("đã chạy / đã về mà thiếu ngày xuất phát")
    if ts == "arrived" and not t["back_date"]:
        ly.append("đã về mà thiếu ngày về")
    if t["back_date"] and ts != "arrived":
        ly.append("có ngày về mà chưa về (%s)" % ts)
    if t["doc_date"] and t["out_date"] and t["out_date"] < t["doc_date"]:
        ly.append("ngày xuất phát trước ngày lập")
    if t["out_date"] and t["back_date"] and t["back_date"] < t["out_date"]:
        ly.append("ngày về trước ngày xuất phát")
    if t["locked"] and ts != "arrived":
        ly.append("đã khoá mà chưa về")
    if t["locked"] and t["weight_dest"] is None:
        ly.append("đã khoá mà thiếu cân nơi giao")
    if t["locked"] and not (muc.get("info") == "verified" and muc.get("trans") == "verified"):
        ly.append("đã khoá mà mục I/II chưa kiểm")
    if t["kind"] == "gom" and ts == "arrived" and t["co_hang"] and not t["co_nhap"]:
        ly.append("DO gom đã về mà chưa nhập kho hàng")
    if t["kind"] == "giao" and t["lay_lo"] and not t["co_xuat"]:
        ly.append("DO giao lấy lô mà chưa có dòng xuất kho hàng")
    if t["n_muc"] != len(CHUOI):
        ly.append("có %d/6 mục duyệt" % t["n_muc"])
    la = ["%s=%s" % (k, v) for k, v in muc.items() if v not in CHUOI.get(k, ())]
    if la:
        ly.append("mục / trạng thái lạ: " + ", ".join(la))
    return ly


def chan_xoa(c, t):
    """Vì sao DO này KHÔNG xoá được ở đây (đã sang hệ anh Tune / dính kho / dính DO khác). Rỗng = xoá được."""
    ly, tid = [], t["id"]
    for bang, ten, cr in (("gui_so_tune", "SO cước", CHUA_RO_SO), ("gui_so_nhien_lieu_tune", "SO nhiên liệu", CHUA_RO_NL)):
        r = mot(c, "select status, http_status, error_code, order_code, coalesce(request_body, '') <> '' co_goi from %s where do_id = :d"
                % bang, d="EPLLAO-" + tid)
        if r and (r["status"] in ("synced", "conflict") or (r["co_goi"] and r["status"] != "synced" and (
                r["http_status"] is None or r["http_status"] >= 500 or (r["error_code"] or "") in cr))):
            ly.append("đã gửi %s sang anh Tune (%s)" % (ten, r["order_code"] or r["status"] + ", kết quả chưa rõ"))
    if t["owner_payment_id"] or t["owner_paid"]:
        ly.append("đã trả chủ xe ở hệ kế toán (%s)" % (t["owner_payment_id"] or "owner_paid"))
    for r in q(c, "select id, ref_no, status, trip_ids from chi_chu_xe_tune where status in ('da_gui', 'da_chi', 'loi')"):
        try:
            ids = json.loads(r["trip_ids"] or "[]")
        except ValueError:
            ids = []
        if tid not in ids:
            continue
        if r["status"] == "loi" and not mot(c, "select 1 x from can_tru_tune where de_nghi_id = :i and status <> 'huy'", i=r["id"]):
            continue
        ly.append("nằm trong đề nghị trả chủ xe %s (%s)" % (r["ref_no"], r["status"]))
    for r in q(c, "select status, real_id, document_no, error_code from chi_tune where trip_id = :t", t=tid):
        if r["status"] in ("da_gui", "da_chi") or (r["real_id"] and r["error_code"] != MAT):
            ly.append("phiếu chi tạm ứng bên anh Tune %s (%s)" % (r["document_no"] or r["real_id"], r["status"]))
    for r in q(c, "select section, status, real_id, document_no, error_code from chi_muc_tune where trip_id = :t", t=tid):
        if r["status"] in ("da_gui", "da_chi") or (r["status"] != "huy" and r["real_id"] and r["error_code"] != MAT):
            ly.append("phiếu chi mục %s bên anh Tune %s (%s)" % (r["section"], r["document_no"] or r["real_id"], r["status"]))
    for r in q(c, "select nguon, ma_nguon, status, error_code, so_ben_ke_toan from but_toan_cho where trip_id = :t and status <> 'huy'", t=tid):
        if r["status"] == "da_gui":
            ly.append("bút toán %s đã gửi (%s) — gỡ bên anh Tune trước" % (r["nguon"], r["so_ben_ke_toan"] or "?"))
        elif r["status"] != "cho_gui":
            ly.append("bút toán %s trạng thái lạ «%s»" % (r["nguon"], r["status"]))
        elif (r["error_code"] or "") in CHUA_RO_BT:
            ly.append("bút toán %s gửi chưa rõ kết quả (%s)" % (r["nguon"], r["error_code"]))
    for r in q(c, "select section, line_no, stock_move_id, card_move_id from trip_expenses where trip_id = :t "
                  "and (stock_move_id is not null or card_move_id is not null) order by section, line_no", t=tid):
        mv = r["stock_move_id"] or ""
        if mv.startswith(TIEN_TO_QLSX):
            ly.append("dòng %s/%s đã xuất kho QLSX (phiếu %s)" % (r["section"], r["line_no"], mv[len(TIEN_TO_QLSX):]))
        elif mv:
            ly.append("dòng %s/%s xuất ở kho tạm cũ (%s) — cần phiếu nhập điều chỉnh bên kho QLSX" % (r["section"], r["line_no"], mv))
        if r["card_move_id"]:
            ly.append("dòng %s/%s đã trừ thẻ cao tốc" % (r["section"], r["line_no"]))
    for r in q(c, "select so_tkn, status from can_tru_tune where trip_id = :t and status <> 'huy'", t=tid):
        ly.append("đã cấn trừ SO nhiên liệu (TKN %s, %s)" % (r["so_tkn"] or "?", r["status"]))
    lay = q(c, """select distinct x.doc_no from goods_moves g join trips x on x.id = g.trip_id
                  where g.lo_trip_id = :t and g.trip_id <> :t and g.kind = 'out'
                  union select distinct x.doc_no from trip_goods g join trips x on x.id = g.trip_id
                  where g.tu_phieu_id = :t and g.trip_id <> :t""", t=tid)
    if lay:
        ly.append("lô hàng đã có DO giao lấy: " + ", ".join(sorted(r["doc_no"] for r in lay)))
    return ly


def khao_sat(c, gom_trang_thai):
    ds = cac_do(c)
    so_do = {t["id"]: t["doc_no"] for t in ds}
    nh = []

    g1 = Nhom("G1", "DO thiếu trường bắt buộc", "phiếu không đủ khách / tuyến / xe / tài xế / loại / ngày thì không in, không tính "
              "tiền, không gửi đề nghị thu được", "mất phiếu thật nếu chỉ thiếu do lỗi màn hình — xem kỹ trước khi --that")
    g2 = Nhom("G2", "DO rác thử / số lạ", "mang dấu dữ liệu thử của các đợt UAT, hoặc số không theo mẫu G4-/T4-nnnn-mm/EPL",
              "số lạ mà không có dấu thử có thể là phiếu gõ tay thật → chỉ liệt kê")
    g3 = Nhom("G3", "DO kẹt trạng thái vô lý", "trạng thái mâu thuẫn nhau — màn hình / báo cáo hiện sai, bước sau bị chặn",
              "thường là phiếu thật bị bỏ dở — sửa tay đúng hơn xoá; chỉ xoá khi --gom-trang-thai")
    for t in ds:
        th = thieu_truong(t)
        if th:
            g1.them(t["doc_no"], "thiếu: " + ", ".join(th), "XOA_DO", trip=t)
        rac = re.search(DAU_THU_PY, " ".join(str(t[k] or "") for k in ("doc_no", "customer_name", "driver_name", "note")), re.I)
        if rac and not th:
            g2.them(t["doc_no"], "dấu thử «%s»" % rac.group(0), "XOA_DO", trip=t)
        elif not re.match(MAU_SO, t["doc_no"] or "") and not th:
            g2.them(t["doc_no"], "số không theo mẫu (không có dấu thử)", "GIU")
        vl = vo_ly(t)
        if vl and not th and not rac:
            g3.them(t["doc_no"], "; ".join(vl), "XOA_DO" if gom_trang_thai else "GIU", trip=t)
    nh += [g1, g2, g3]

    g4 = Nhom("G4", "Dòng chi lỗi", "số lượng ≤ 0, đơn giá âm, EPL trả mà tiền 0, mục / tiền tệ lạ, không tên — tổng tiền / tạm ứng "
              "/ bút toán sai theo", "dòng của DO đã khoá / đã duyệt / đã xuất kho không xoá ở đây (lệch với chứng từ đã gửi)")
    g4b = Nhom("G4b", "Dòng tiền 0 do chủ xe tự trả", "xe thuê tự lo: EPL không biết giá, không trả — đúng kịch bản, không phải lỗi",
               "không")
    for r in q(c, """
        select e.id, e.trip_id, t.doc_no, t.locked, e.section, e.line_no, coalesce(e.item_key, e.item_name) ten, e.qty, e.unit_price,
               e.currency, e.paid_by_epl, e.source, e.stock_move_id, e.card_move_id, s.status muc_tt,
               exists (select 1 from trip_events v where v.expense_id = e.id) co_su_kien
        from trip_expenses e join trips t on t.id = e.trip_id
        left join trip_sections s on s.trip_id = e.trip_id and s.section = e.section
        where e.qty <= 0 or e.unit_price < 0 or e.unit_price = 0 or e.section <> all(:muc) or e.currency <> all(:tt)
           or coalesce(e.item_key, e.item_name, '') = ''
        order by t.doc_no, e.section, e.line_no""", muc=list(MUC_CHI), tt=list(TIEN_TE)):
        ma = "%s · %s/%s %s" % (r["doc_no"], r["section"], r["line_no"], r["ten"] or "(không tên)")
        loi = []
        if r["qty"] <= 0:
            loi.append("số lượng %s" % r["qty"])
        if r["unit_price"] < 0:
            loi.append("đơn giá âm %s" % r["unit_price"])
        if r["section"] not in MUC_CHI:
            loi.append("mục lạ «%s»" % r["section"])
        if r["currency"] not in TIEN_TE:
            loi.append("tiền tệ lạ «%s»" % r["currency"])
        if not r["ten"]:
            loi.append("không tên khoản")
        if r["unit_price"] == 0:
            if not r["paid_by_epl"]:
                if not loi:
                    g4b.them(ma, "tiền 0, chủ xe tự trả")
                    continue
            elif r["source"] == "kho" and not r["stock_move_id"]:            # dòng kho chưa cấp: giá vốn chưa có — không phải lỗi
                pass
            elif r["muc_tt"] in ("wait", "entered") and not r["locked"]:     # mục chưa kiểm: đơn giá do KT Chi phí gõ lúc kiểm
                pass                                                         # (Bãi không thấy / không gõ tiền) — chưa định giá, không phải lỗi
            else:
                loi.append("EPL trả mà tiền 0")
        if not loi:
            continue
        xoa = (not r["locked"] and r["muc_tt"] in ("wait", "entered") and not r["stock_move_id"] and not r["card_move_id"]
               and not r["co_su_kien"])
        g4.them(ma, ", ".join(loi) + ("" if xoa else " — DO đã khoá / mục đã duyệt / đã xuất kho / có sự kiện: giữ"),
                "XOA_DONG" if xoa else "GIU", id=r["id"], trip_id=r["trip_id"])
    nh += [g4, g4b]

    g5 = Nhom("G5", "Phiếu lĩnh / đề nghị tạm ứng lỗi", "trạng thái lạ, đã cấp mà thiếu số lít cấp, đề nghị tạm ứng ≤ 0",
              "tờ đã in cho tài xế — sửa bằng màn Phiếu lĩnh")
    for r in q(c, """select v.doc_no, v.kind, v.status, v.granted_qty, v.amount_lak from vouchers v
                     where v.status <> all(:tt) or (v.kind = 'fuel' and v.status = 'da_cap' and v.granted_qty is null)
                        or (v.kind = 'advance' and coalesce(v.amount_lak, 0) <= 0) or v.kind not in ('fuel', 'advance')
                     order by v.doc_no""", tt=list(TT_PHIEU_LINH)):
        g5.them(r["doc_no"], "%s · %s · cấp %s · tiền %s" % (r["kind"], r["status"], r["granted_qty"], r["amount_lak"]))
    nh.append(g5)

    g6 = Nhom("G6", "Bút toán chờ lỗi / kẹt", "sổ kế toán bên anh Tune thiếu / thừa bút toán so với DO",
              "bản đã gửi phải gỡ bên anh Tune (proc_Logistics_JournalEntry_Reverse) — không sửa lặng lẽ ở đây")
    for r in q(c, """select b.id, b.nguon, b.ma_nguon, b.status, b.can_dao, b.error_code, left(b.loi_gui, 120) loi, b.so_ben_ke_toan,
                            b.ma_ben_ke_toan, b.trip_id, t.doc_no
                     from but_toan_cho b left join trips t on t.id = b.trip_id
                     where b.status <> all(:tt) or (b.status = 'cho_gui' and (b.error_code is not null or b.loi_gui is not null))
                        or b.can_dao or (b.status = 'da_gui' and b.ma_ben_ke_toan is null)
                        or (b.status <> 'huy' and b.trip_id is null)
                     order by b.created_at""", tt=list(TT_BUT_TOAN)):
        ma = "%s:%s (%s)" % (r["nguon"], r["ma_nguon"], r["doc_no"] or "DO không còn")
        if r["trip_id"] is None and r["status"] == "cho_gui" and (r["error_code"] or "") not in CHUA_RO_BT:
            g6.them(ma, "chờ gửi mà DO đã xoá → huỷ", "SUA", id=r["id"])
            continue
        loi = []
        if r["status"] not in TT_BUT_TOAN:
            loi.append("trạng thái lạ «%s»" % r["status"])
        if r["status"] == "cho_gui" and (r["error_code"] or r["loi"]):
            loi.append("gửi lỗi %s %s" % (r["error_code"] or "", r["loi"] or ""))
        if r["can_dao"]:
            loi.append("chờ bút toán đảo (%s)" % (r["so_ben_ke_toan"] or "?"))
        if r["status"] == "da_gui" and not r["ma_ben_ke_toan"]:
            loi.append("đã gửi mà thiếu số bên kia")
        if r["trip_id"] is None:
            loi.append("DO đã xoá mà bút toán %s vẫn %s" % (r["so_ben_ke_toan"] or "", r["status"]))
        g6.them(ma, "; ".join(loi))
    nh.append(g6)

    g7 = Nhom("G7", "Gửi sang anh Tune lỗi / kẹt", "lượt gửi SO / phiếu chi lỗi hoặc treo — hai bên lệch",
              "bản có số bên kia phải xử lý bên anh Tune trước; ở đây chỉ xoá lượt gửi lỗi hẳn của DO đã xoá")
    for bang, ten, cr in (("gui_so_tune", "SO cước", CHUA_RO_SO), ("gui_so_nhien_lieu_tune", "SO nhiên liệu", CHUA_RO_NL)):
        for r in q(c, """select g.do_id, g.status, g.http_status, g.error_code, left(g.error_message, 100) loi, g.order_code, g.trip_id,
                                coalesce(g.request_body, '') <> '' co_goi, t.doc_no
                         from %s g left join trips t on t.id = g.trip_id
                         where g.status <> 'synced' or g.trip_id is null order by g.do_id""" % bang):
            chua_ro = r["co_goi"] and r["status"] != "synced" and (
                r["http_status"] is None or r["http_status"] >= 500 or (r["error_code"] or "") in cr)
            ma = "%s %s (%s)" % (ten, r["do_id"], r["doc_no"] or "DO không còn")
            if r["trip_id"] is None and r["status"] == "failed" and not chua_ro:
                g7.them(ma, "lượt gửi lỗi hẳn của DO đã xoá", "XOA", bang=bang, do_id=r["do_id"])
            else:
                g7.them(ma, "%s %s %s%s" % (r["status"], r["error_code"] or "", r["loi"] or "", " · KẾT QUẢ CHƯA RÕ" if chua_ro else "")
                        + (" · SO %s còn bên anh Tune mà DO đã xoá" % r["order_code"] if r["trip_id"] is None and r["order_code"] else ""))
    for r in q(c, """select t.doc_no, c.status, c.document_no, c.error_code, left(c.error_message, 100) loi, t.transport_status, t.locked
                     from chi_tune c join trips t on t.id = c.trip_id
                     where c.status = 'loi' or (c.status = 'da_gui' and (t.transport_status = 'arrived' or t.locked))
                     order by t.doc_no"""):
        if r["status"] == "loi":
            g7.them("tạm ứng %s" % r["doc_no"], "phiếu chi tạm ứng lỗi %s %s" % (r["error_code"] or "", r["loi"] or ""))
        else:
            g7.them("tạm ứng %s" % r["doc_no"], "phiếu chi %s chờ thủ quỹ chi mà chuyến đã %s — ghi sổ (hoặc xoá) bên anh Tune"
                    % (r["document_no"], "khoá" if r["locked"] else "về"))
    for bang, nhan in (("chi_muc_tune", "chi mục V/VI"), ("chi_chu_xe_tune", "trả chủ xe"), ("can_tru_tune", "cấn trừ SO nhiên liệu"),
                       ("phieu_tien_tune", "phiếu tiền tất toán / NCC")):
        for r in q(c, "select ref_no, status, error_code, left(error_message, 100) loi from %s where status = 'loi' order by ref_no" % bang):
            g7.them("%s %s" % (nhan, r["ref_no"]), "lỗi %s %s" % (r["error_code"] or "", r["loi"] or ""))
    nh.append(g7)

    g8 = Nhom("G8", "Sổ chứng từ mồ côi / đẩy lỗi", "tờ chưa đối chiếu của DO / phiếu lĩnh đã xoá — sổ chứng từ hiện tờ không có nguồn",
              "không — chỉ xoá tờ CHƯA đối chiếu (như CT.rut); tờ đã đối chiếu giữ")
    for r in q(c, """select c.id, c.loai, c.so, c.trip_doc_no, c.da_day, c.loi_day,
                            (c.nguon_bang = 'trips' and c.trip_id is null and not exists (select 1 from trips t where t.id = c.nguon_id))
                            or (c.nguon_bang = 'vouchers' and not exists (select 1 from vouchers v where v.id = c.nguon_id)) mo_coi
                     from chung_tu c order by c.so"""):
        if r["mo_coi"] and not r["da_day"]:
            g8.them(r["so"], "%s của %s — nguồn không còn" % (r["loai"], r["trip_doc_no"] or "?"), "XOA", id=r["id"])
        elif r["mo_coi"]:
            g8.them(r["so"], "%s của %s — nguồn không còn, tờ ĐÃ đối chiếu: giữ" % (r["loai"], r["trip_doc_no"] or "?"))
        elif r["loi_day"]:
            g8.them(r["so"], "đẩy lỗi: " + r["loi_day"][:100])
    nh.append(g8)

    g9 = Nhom("G9", "Kho hàng ở bãi lỗi", "tồn lô âm / xuất không rõ lô — sổ kho hàng sai", "sửa bằng đơn điều chỉnh (Bãi lập, KT duyệt)")
    for r in q(c, """select l.doc_no, sum(case g.kind when 'in' then g.qty_t when 'out' then -g.qty_t else g.qty_t end) ton
                     from goods_moves g join trips l on l.id = g.lo_trip_id group by l.doc_no
                     having sum(case g.kind when 'in' then g.qty_t when 'out' then -g.qty_t else g.qty_t end) < -:sai""", sai=SAI):
        g9.them("lô " + r["doc_no"], "tồn âm %.3f t" % r["ton"])
    for r in q(c, "select trip_doc_no, qty_t from goods_moves where kind = 'out' and lo_trip_id is null order by move_date"):
        g9.them(r["trip_doc_no"] or "?", "xuất %.3f t không rõ lô" % r["qty_t"])
    for r in q(c, "select d.id, d.lo_trip_id, d.trang_thai, d.tan from dieu_chinh_hang d where not exists (select 1 from trips t where t.id = d.lo_trip_id)"):
        g9.them("đơn điều chỉnh " + r["id"], "lô %s không còn (%s, %s t)" % (r["lo_trip_id"], r["trang_thai"], r["tan"]),
                "XOA" if r["trang_thai"] != "da_duyet" else "GIU", id=r["id"])
    nh.append(g9)

    g10 = Nhom("G10", "Dòng xuất kho TẠM cũ (trước 05/10)", "kho đã chuyển sang QLSX — hệ không trả kho tự động cho dòng này nữa "
               "(xoá DO → 409 DONG_KHO_TAM_CU)", "không xoá; muốn xoá DO thì lập phiếu nhập điều chỉnh bên kho QLSX trước")
    for r in q(c, """select t.doc_no, e.section, e.line_no, e.stock_move_id from trip_expenses e join trips t on t.id = e.trip_id
                     where e.stock_move_id is not null and e.stock_move_id not like 'qlsx:%' order by t.doc_no, e.section, e.line_no"""):
        g10.them("%s · %s/%s" % (r["doc_no"], r["section"], r["line_no"]), "phiếu kho tạm %s" % r["stock_move_id"])
    nh.append(g10)

    g11 = Nhom("G11", "Xe / tài xế kẹt trạng thái", "xe / tài xế báo 'đang chạy' mà không còn DO nào chưa về → không chọn được "
               "khi lập DO mới; hoặc đứng trên nhiều DO chưa về cùng lúc", "không — đặt lại như hệ (_doi_trang_thai_xe_tai_xe)")
    for bang, cot, nhan, ten in (("vehicles", "vehicle_id", "xe", "truck_no"), ("drivers", "driver_id", "tài xế", "name")):
        for r in q(c, """select x.id, x.%s ten from %s x where x.status = 'on_trip'
                         and not exists (select 1 from trips t where t.%s = x.id and t.transport_status <> 'arrived')""" % (ten, bang, cot)):
            g11.them("%s %s" % (nhan, r["ten"]), "đang chạy mà không còn DO chưa về → rảnh", "SUA", bang=bang, id=r["id"])
        for r in q(c, """select x.%s ten, string_agg(t.doc_no, ', ' order by t.doc_no) ds from trips t join %s x on x.id = t.%s
                         where t.transport_status <> 'arrived' group by x.%s having count(*) > 1""" % (ten, bang, cot, ten)):
            g11.them("%s %s" % (nhan, r["ten"]), "đứng trên nhiều DO chưa về: " + r["ds"])
    nh.append(g11)

    g12 = Nhom("G12", "Danh mục thiếu trường / tên thử", "thiếu mã khách kế toán thì đề nghị thu (SO) hỏng; trạm ngoài thiếu NCC thì "
               "công nợ dầu mua không về đâu…", "danh mục không xoá (phiếu cũ trỏ tới) — sửa tay; chỉ xoá tuyến thử đã ngưng, không ai dùng")
    for r in q(c, "select name from customers where active and coalesce(trim(code), '') = '' order by name"):
        g12.them("khách " + r["name"], "chưa có mã khách bên kế toán (EPLKH-…) — Tạo SO sẽ hỏng")
    for r in q(c, "select coalesce(code, name) ma from fuel_places where active and owner_type = 'ngoai' and supplier_id is null"):
        g12.them("trạm " + r["ma"], "trạm ngoài chưa gắn nhà cung cấp")
    for r in q(c, "select name from suppliers where active and coalesce(trim(acct_code), '') = ''"):
        g12.them("NCC " + r["name"], "thiếu định khoản")
    for r in q(c, "select truck_no from vehicles where active and owner_type = 'joint' and owner_id is null"):
        g12.them("xe " + r["truck_no"], "xe thuê thiếu chủ xe")
    for bang, cot, nhan in (("customers", "name", "khách"), ("owners", "name", "chủ xe"), ("drivers", "name", "tài xế"),
                            ("vehicles", "truck_no", "xe"), ("suppliers", "name", "NCC")):
        for r in q(c, "select %s ten, active from %s where %s ~* :dau" % (cot, bang, cot), dau=DAU_THU):
            g12.them("%s %s" % (nhan, r["ten"]), "tên mang dấu thử%s — don_may_thu.py dọn chủ xe thử" % ("" if r["active"] else " (đã ngưng)"))
    for r in q(c, """select r.id, r.name, exists (select 1 from trips t where t.route_id = r.id) or exists (select 1 from customer_rates k
                     where k.route_id = r.id) dung from routes r where r.name ~ '^THU' and not r.active order by r.name"""):
        g12.them("tuyến " + r["name"], "tuyến thử đã ngưng" + (" — còn phiếu / bảng giá dùng: giữ" if r["dung"] else ", không ai dùng"),
                 "GIU" if r["dung"] else "XOA", id=r["id"])
    nh.append(g12)

    g13 = Nhom("G13", "Ánh xạ đối tượng mồ côi", "doi_tuong_tune trỏ người không còn bên này", "không xoá — đối tượng bên anh Tune giữ")
    for r in q(c, """select m.loai, m.ref_id, m.object_no from doi_tuong_tune m where not (
                        (m.loai = 'tai_xe' and exists (select 1 from drivers x where x.id = m.ref_id))
                     or (m.loai = 'chu_xe' and exists (select 1 from owners x where x.id = m.ref_id))
                     or (m.loai = 'khach' and exists (select 1 from customers x where x.id = m.ref_id))
                     or (m.loai = 'ncc' and exists (select 1 from suppliers x where x.id = m.ref_id)))"""):
        g13.them(r["object_no"], "%s %s không còn" % (r["loai"], r["ref_id"]))
    nh.append(g13)

    # DO sắp xoá: chặn nếu đã dính hệ anh Tune / kho / DO khác — chuyển thành "giữ" kèm lý do
    for g in nh:
        for m in g.muc:
            if m["viec"] == "XOA_DO":
                ly = chan_xoa(c, m["trip"])
                if ly:
                    m["viec"], m["chi_tiet"] = "GIU", m["chi_tiet"] + " — KHÔNG XOÁ ĐƯỢC: " + "; ".join(ly)
    return nh, so_do


# ================================================================ LÀM (--that)
def nha_xe_tai_xe(c, t):
    """routes/phieu._doi_trang_thai_xe_tai_xe(…, 'available', 'available'): còn DO khác chưa về thì 'đang chạy', không thì rảnh;
    xe đang sửa giữ nguyên; ngưng dùng không đụng."""
    if t["vehicle_id"]:
        ex(c, """update vehicles set status = case when exists (select 1 from trips x where x.vehicle_id = vehicles.id and x.id <> :t
                 and x.transport_status <> 'arrived') then 'on_trip' else 'available' end
                 where id = :v and status not in ('inactive', 'maintenance')""", t=t["id"], v=t["vehicle_id"])
    if t["driver_id"]:
        ex(c, """update drivers set status = case when exists (select 1 from trips x where x.driver_id = drivers.id and x.id <> :t
                 and x.transport_status <> 'arrived') then 'on_trip' else 'available' end
                 where id = :d and status <> 'inactive'""", t=t["id"], d=t["driver_id"])


def xoa_do(c, t, bay_gio):
    """routes/phieu.xoa_phieu — phần cục bộ (chan_xoa đã loại mọi DO cần gọi sang anh Tune). Trả {việc: số dòng}, [tệp đĩa]."""
    tid, n = t["id"], {}
    n["phiếu chi lỗi chưa có bên kia"] = ex(c, "delete from chi_tune where trip_id = :t", t=tid)
    n["phiếu chi mục V/VI lỗi / đã huỷ"] = ex(c, "delete from chi_muc_tune where trip_id = :t", t=tid)
    n["bút toán chờ gửi → huỷ"] = ex(c, "update but_toan_cho set status = 'huy', huy_luc = :g, huy_by = :by, updated_at = :g "
                                        "where trip_id = :t and status = 'cho_gui'", t=tid, g=bay_gio, by=NGUOI)
    fm = [r["id"] for r in q(c, "select m.id from fuel_moves m join vouchers v on v.id = m.voucher_id where v.trip_id = :t", t=tid)]
    if fm:
        n["tờ sổ dầu cũ"] = ex(c, "delete from chung_tu where not da_day and nguon_bang = 'fuel_moves' and nguon_id = any(:i)", i=fm)
        n["sổ dầu cũ của phiếu lĩnh"] = ex(c, "delete from fuel_moves where id = any(:i)", i=fm)
    adj = [r["id"] for r in q(c, "select id from goods_moves where (trip_id = :t or lo_trip_id = :t) and kind = 'adj'", t=tid)]
    if adj:
        n["tờ DC_HH"] = ex(c, "delete from chung_tu where not da_day and loai = 'DC_HH' and nguon_bang = 'goods_moves' "
                              "and nguon_id = any(:i)", i=adj)
    n["sổ kho hàng"] = ex(c, "delete from goods_moves where trip_id = :t or lo_trip_id = :t", t=tid)
    n["đơn điều chỉnh lô"] = ex(c, "delete from dieu_chinh_hang where lo_trip_id = :t", t=tid)
    n["tờ PNK_HH / PXK_HH"] = ex(c, "delete from chung_tu where not da_day and nguon_bang = 'trips' and nguon_id = :t "
                                    "and loai in ('PNK_HH', 'PXK_HH')", t=tid)
    nha_xe_tai_xe(c, t)
    tep = [r["stored"] for r in q(c, "select stored from trip_attachments where trip_id = :t", t=tid)]
    for bang in ("trip_events", "trip_attachments", "trip_expenses", "trip_sections", "trip_logs"):
        n[bang] = ex(c, "delete from %s where trip_id = :t" % bang, t=tid)
    n["tờ chứng từ chưa đối chiếu"] = ex(c, "delete from chung_tu where not da_day and trip_id = :t", t=tid)
    n["lượt gửi SO lỗi hẳn"] = (ex(c, "delete from gui_so_tune where trip_id = :t", t=tid)
                                + ex(c, "delete from gui_so_nhien_lieu_tune where trip_id = :t", t=tid))
    n["DO"] = ex(c, "delete from trips where id = :t", t=tid)
    if n["DO"] != 1:
        raise RuntimeError("Xoá DO %s không đúng một dòng (%d) — rollback." % (t["doc_no"], n["DO"]))
    return {k: v for k, v in n.items() if v}, tep


def lam(c, nh, gom_trang_thai):
    bay_gio = dt.datetime.utcnow()
    da, tep_dia = [], []
    do_xoa = {m["trip"]["id"]: m for g in nh for m in g.muc if m["viec"] == "XOA_DO"}
    if do_xoa:
        # khoá đúng các DO sắp xoá rồi KIỂM LẠI (máy 8011 vẫn chạy — có thể vừa gửi gì sang anh Tune)
        moi = {t["id"]: t for t in q(c, "select * from trips where id = any(:i) for update", i=list(do_xoa))}
        for tid, m in do_xoa.items():
            t = moi.get(tid)
            if t is None:
                print("   bỏ qua %s: DO đã không còn" % m["ma"])
                continue
            ly = chan_xoa(c, t)
            if ly:
                print("   bỏ qua %s: vừa đổi — %s" % (m["ma"], "; ".join(ly)))
                continue
            n, tep = xoa_do(c, t, bay_gio)
            da.append("XOÁ DO %s: %s" % (t["doc_no"], ", ".join("%s %d" % kv for kv in n.items())))
            tep_dia += [os.path.join(tid, s) for s in tep]
    for g in nh:
        for m in g.muc:
            v = m["viec"]
            if v == "XOA_DONG":
                k = ex(c, """delete from trip_expenses e using trips t, trip_sections s where e.id = :i and t.id = e.trip_id and not t.locked
                             and s.trip_id = e.trip_id and s.section = e.section and s.status in ('wait', 'entered')
                             and e.stock_move_id is null and e.card_move_id is null
                             and not exists (select 1 from trip_events v where v.expense_id = e.id)""", i=m["id"])
                da.append("XOÁ DÒNG %s: %d" % (m["ma"], k))
            elif v == "SUA" and g.ma == "G6":
                k = ex(c, "update but_toan_cho set status = 'huy', huy_luc = :g, huy_by = :by, updated_at = :g "
                          "where id = :i and status = 'cho_gui' and trip_id is null", i=m["id"], g=bay_gio, by=NGUOI)
                da.append("HUỶ bút toán mồ côi %s: %d" % (m["ma"], k))
            elif v == "SUA" and g.ma == "G11":
                cot = "vehicle_id" if m["bang"] == "vehicles" else "driver_id"
                k = ex(c, """update %s x set status = 'available' where x.id = :i and x.status = 'on_trip' and not exists
                             (select 1 from trips t where t.%s = x.id and t.transport_status <> 'arrived')""" % (m["bang"], cot), i=m["id"])
                da.append("ĐẶT RẢNH %s: %d" % (m["ma"], k))
            elif v == "XOA" and g.ma == "G7":
                k = ex(c, "delete from %s where do_id = :d and trip_id is null and status = 'failed'" % m["bang"], d=m["do_id"])
                da.append("XOÁ lượt gửi %s: %d" % (m["ma"], k))
            elif v == "XOA" and g.ma == "G8":
                k = ex(c, "delete from chung_tu where id = :i and not da_day", i=m["id"])
                da.append("XOÁ tờ %s: %d" % (m["ma"], k))
            elif v == "XOA" and g.ma == "G9":
                k = ex(c, "delete from dieu_chinh_hang d where d.id = :i and d.trang_thai <> 'da_duyet' "
                          "and not exists (select 1 from trips t where t.id = d.lo_trip_id)", i=m["id"])
                da.append("XOÁ %s: %d" % (m["ma"], k))
            elif v == "XOA" and g.ma == "G12":
                k = ex(c, """delete from routes r where r.id = :i and not r.active and not exists (select 1 from trips t where t.route_id = r.id)
                             and not exists (select 1 from customer_rates k where k.route_id = r.id)""", i=m["id"])
                da.append("XOÁ %s: %d" % (m["ma"], k))
    if da:
        # bộ đệm báo cáo: như ORM của hệ khi xoá hàng loạt (services/dem_bao_cao._ghi_hang_loat) — khoá '*' → mọi tháng tính lại
        ex(c, "insert into phien_ban_thang (khoa, so) values ('*', 1) on conflict (khoa) do update set so = phien_ban_thang.so + 1")
        # hậu kiểm: DO đã xoá không còn, không còn tờ chưa đối chiếu / dòng sổ kho trỏ tới
        xoa = [tid for tid in do_xoa if not mot(c, "select 1 x from trips where id = :t", t=tid)]
        con = mot(c, """select (select count(*) from chung_tu where not da_day and (trip_id = any(:i) or (nguon_bang = 'trips' and nguon_id = any(:i))))
                               + (select count(*) from goods_moves where trip_id = any(:i) or lo_trip_id = any(:i))
                               + (select count(*) from but_toan_cho where status = 'cho_gui' and ma_nguon = any(:i)) n""", i=xoa or [""])
        if con["n"]:
            raise RuntimeError("Hậu kiểm hỏng: còn %d dòng trỏ DO đã xoá — rollback." % con["n"])
    return da, tep_dia


# ================================================================ KHOÁ CÒN SỐNG (đối chiếu với bên anh Tune)
def khoa_con_song(c):
    """Mọi khoá mà chứng từ bên anh Tune có thể mang (OrderSourceNo, DOC_REFDOCUMENTNO, SourceRef, số phiếu kho / phiếu chi / SO)
    của thứ CÒN ở trang điều xe — script SQL coi chứng từ EPL bên đó mà khoá không nằm trong danh sách là mồ côi."""
    k = set()
    k |= {"EPLLAO-" + r["id"] for r in q(c, "select id from trips")}
    for r in q(c, "select id, kind, doc_no from vouchers"):
        k.add(r["doc_no"])                                                     # PTU-… = RefDocumentNo phiếu chi tạm ứng
        k.add(re.sub(r"[^A-Za-z0-9_.:-]", ".", r["doc_no"] or ("PLNL-" + r["id"]))[:100])   # SourceRef phiếu xuất kho dầu QLSX
        k.add("EPLLAO:voucher:" + r["id"])
    k |= {"EPLLAO:trip_expense:" + r["id"] for r in q(c, "select id from trip_expenses where source = 'kho'")}
    for bang in ("trip_expenses", "repair_lines", "sale_lines"):
        k |= {r["mv"][len(TIEN_TO_QLSX):] for r in q(c, "select stock_move_id mv from %s where stock_move_id like 'qlsx:%%'" % bang)}
    for bang in ("chi_muc_tune", "chi_chu_xe_tune", "phieu_tien_tune"):
        k |= {r["ref_no"] for r in q(c, "select ref_no from %s where status <> 'huy'" % bang)}
    for bang in ("chi_tune", "chi_muc_tune", "chi_chu_xe_tune", "phieu_tien_tune"):
        k |= {r["document_no"] for r in q(c, "select document_no from %s where document_no is not null and status <> 'huy'" % bang)}
    for r in q(c, "select source_ref, phien, so_ben_ke_toan from but_toan_cho where status <> 'huy' and source_ref is not null"):
        k.add(r["source_ref"] if (r["phien"] or 1) <= 1 else "%s-%d" % (r["source_ref"], r["phien"]))
        if r["so_ben_ke_toan"]:
            k.add(r["so_ben_ke_toan"])
    k |= {"EPLLAO-cantru-" + r["so_tkn"] for r in q(c, "select so_tkn from can_tru_tune where status <> 'huy' and so_tkn is not null")}
    for bang in ("gui_so_tune", "gui_so_nhien_lieu_tune"):
        k |= {r["order_code"] for r in q(c, "select order_code from %s where order_code is not null" % bang)}
    # mã đối tượng PUBOBJECT (services/chi_tune.doi_tuong): tài xế EPLTX-, chủ xe EPLCX-, NCC EPLNCC-, khách = mã kế toán của khách
    k |= {"EPLTX-" + r["id"] for r in q(c, "select id from drivers")}
    k |= {"EPLCX-" + r["id"] for r in q(c, "select id from owners")}
    k |= {"EPLNCC-" + r["id"] for r in q(c, "select id from suppliers")}
    k |= {r["code"] for r in q(c, "select code from customers where coalesce(code, '') <> ''")}
    k |= {r["object_no"] for r in q(c, "select object_no from doi_tuong_tune")}
    return sorted(x for x in k if x and "," not in x)


# ================================================================ IN
def in_ket_qua(nh):
    tong = {}
    for g in nh:
        dem = {}
        for m in g.muc:
            dem[m["viec"]] = dem.get(m["viec"], 0) + 1
            tong[m["viec"]] = tong.get(m["viec"], 0) + 1
        print("\n[%s] %s — %d mục%s" % (g.ma, g.ten, len(g.muc), (" (" + ", ".join("%s %d" % (VIEC[k], v) for k, v in dem.items()) + ")")
                                         if g.muc else ""))
        if not g.muc:
            continue
        print("     vì sao lỗi: %s\n     rủi ro nếu xoá: %s" % (g.ly_do, g.rui_ro))
        for m in g.muc:
            print("     · %-9s %s — %s" % (VIEC[m["viec"]].split(" —")[0], m["ma"], m["chi_tiet"]))
    return tong


def main():
    ap = argparse.ArgumentParser(description="Dọn dữ liệu lỗi / thiếu trường trên bản sao máy thử (mặc định chỉ liệt kê).")
    ap.add_argument("--that", action="store_true", help="xoá / sửa thật trong MỘT giao dịch")
    ap.add_argument("--gom-trang-thai", action="store_true", help="xoá cả DO kẹt trạng thái vô lý (G3)")
    ap.add_argument("--khoa-tune", action="store_true", help="in dòng khoá còn sống cho @KhoaTrangDieuXe của script SQL")
    ap.add_argument("--tep", default="url_epl_lao_d7.txt", help="tệp chuỗi nối trong .may_thu")
    a = ap.parse_args()
    ten, e = mo(a.tep, a.that)
    print("== %s — %s%s" % (ten, "LÀM THẬT (một giao dịch)" if a.that else "CHỈ LIỆT KÊ (phiên chỉ đọc)",
                            " · gồm DO kẹt trạng thái" if a.gom_trang_thai else ""))
    with e.begin() as c:
        nh, so_do = khao_sat(c, a.gom_trang_thai)
        tong = in_ket_qua(nh)
        print("\nTỔNG: %d DO trên trang điều xe · %s" % (len(so_do), ", ".join("%s %d" % (VIEC[k], v) for k, v in tong.items()) or "không có lỗi"))
        if a.khoa_tune:
            ds = khoa_con_song(c)
            print("\nKHOÁ CÒN SỐNG (%d) — dán nguyên dòng dưới vào @KhoaTrangDieuXe của 20261006_don_du_lieu_epl_loi.sql:" % len(ds))
            print(",".join(ds))
        if not a.that:
            print("\nChưa ghi gì. --that để làm các mục XOÁ / SỬA (sao lưu pg_dump trước).")
            return
        da, tep = lam(c, nh, a.gom_trang_thai)
        print("\nĐÃ LÀM (%d):" % len(da))
        for x in da:
            print("   " + x)
        if tep:
            print("Tệp đính kèm trên đĩa KHÔNG xoá (thư mục tệp có thể dùng chung với máy của anh) — tự xoá nếu chắc:")
            for x in tep:
                print("   <EPL_LAO_TEP>/" + x.replace("\\", "/"))
        print("COMMIT." if da else "Không có gì để làm.")


if __name__ == "__main__":
    main()
