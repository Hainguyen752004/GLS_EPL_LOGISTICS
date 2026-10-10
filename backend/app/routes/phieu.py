# -*- coding: utf-8 -*-
"""Phiếu xuất xe đi vận chuyển — ໃບເບີກລົດອອກໄປຂົນສົ່ງ. Trái tim của bản Lào.

Một phiếu = một tờ giấy họ đang dùng: sáu mục I–VI, mỗi mục một trạng thái duyệt riêng,
ai làm gì ghi vào nhật ký. Không có Trip, không có DO, không có báo giá.

Hai quy tắc từ tài liệu quy trình của họ ("EPL flow of Logistics") và lời anh chủ dự án:
  · CÓ TRONG KHO → phiếu XUẤT KHO (định khoản …/371); KHÔNG CÓ → phiếu CHI mua ngoài (…/402).
    Nhiên liệu đổ ở kho Thà Bốc → khi kế toán kho GHI SỔ mục III thì tự sinh dòng xuất kho.
    Phụ tùng lấy từ kho khi sửa xe → trừ tồn kho ngay lúc khai.
  · Xe nhà định khoản 625/… và 614/…; xe liên kết định khoản 4022/… (chi hộ nhà thầu phụ).
"""
import datetime as dt
import mimetypes
import os
import re

from collections import defaultdict

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, inspect as sa_inspect, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, object_session

from database import BIEU_THUC_TIM_PHIEU, get_db
from models import (Contract, Owner, TripAttachment, TripGoods, ma_moi, CHUOI, LOAI_DO, LOAI_SU_CO, SU_CO_SUA_CHUA, MUC, MUC_CHI,
                    CACH_TINH_CUOC, SU_KIEN, TIEN_TE, TRANG_THAI_VAN_CHUYEN,
                    Customer, Driver, ExchangeRate, FuelMove, FuelPlace, Part, Route, RouteStop, Trip,
                    GuiSoTune, TripEvent, TripExpense, TripLog, TripSection, Vehicle)
from services.bao_mat import nguoi_hien_tai, nguoi_tu_token
from services.phan_quyen import chuyen_muc, doi_cach_tra, duoc_sua_muc, duoc_sua_tien, nhap_gia_chi, thay_gia_kho, thay_tien_ban, thay_tien_chi
from services import kho_ke_toan as KK
from services import loi_dich as LD
from routes.danh_muc import tim_gia
from services.tinh_toan import (CACH_TRA, CACH_TRA_MAC_DINH, cach_tra, chuan_tien, la_tien_mat_tai_xe, la_xuat_ban, tien_dong,
                                tinh_phieu, ty_gia, hinh_thuc)
from services import kho_hang as KH
from services import chung_tu as CT
from services import chi_tune as CHI
from services import chi_muc_tune as CMT
from services import quyen_phieu as QP
from services import but_toan_cho as BTC
from services import gui_tune as GT
from services import so_nhien_lieu as NL
from services import tai_khoan as TK
from services import de_nghi_thu as DNT
from services import khoan_muc as KMC
from services.tep import loi_co_tep, ten_tep, TEP_DIR, TEP_KIEU, TEP_TOI_DA
from routes import hop_dong as HD
from routes.tuyen import cach_tra_goi_y, gia_goi_y, goi_y_cua, km_ca_chuyen
from routes import the_cao_toc as THE

router = APIRouter()

# Khoản mục chuẩn của từng mục chi — từ 08/10 là danh mục cấu hình được (bảng cost_items, services/khoan_muc: KHOAN_MUC là từ
# điển dùng chung, nap() ghi lại tại chỗ). Người dùng vẫn gõ tên tự do được ("Khác — tự gõ").
KHOAN_MUC = KMC.KHOAN_MUC
# Các cặp định khoản hay dùng cho dòng chi — luật và tên ở services/tai_khoan.py (rà 30/09).
# 06/10: thêm biến thể ghi nợ — mục V mua ngoài quỹ trả ngay nay là …/1011, …/4021 chỉ còn khi ghi nợ / theo đợt
MA_TK = sorted({TK.dinh_khoan_dong(c, m, s, cach=k, ghi_no=g) for c in ("EPL", "joint") for m in MUC_CHI for s in ("kho", "mua", None)
                for k in (None, "ncc", "luong") for g in (False, True)} - {None})
COT_PHIEU = ("doc_no", "kind", "doc_date", "out_date", "back_date", "company", "owner_name", "vehicle_id",
             "truck_no", "brand_model", "plate_head", "plate_trailer", "driver_id", "driver_name",
             "odo_out", "odo_back", "customer_id", "customer_name", "route_id", "goods_type", "ore_bill_no",
             "ore_bill_date", "origin", "destination", "weight_origin", "weight_dest", "price", "price_ccy", "price_mode",
             "hire_price", "hire_ccy", "fee_pct", "over_limit_t", "over_price", "rate_usd", "rate_thb",
             "rate_vnd", "rate_cny", "note", "pod_no", "pod_date", "pod_receiver", "pod_phone", "pod_condition", "pod_note")
COT_NGAY = ("doc_date", "out_date", "back_date", "ore_bill_date", "pod_date")
# Ô tiền của mục II: Bãi không thấy, người kiểm mục II (KT Thu/Chi VC) sửa được khi khác hợp đồng
COT_TIEN = ("price", "price_ccy", "price_mode", "hire_price", "hire_ccy", "fee_pct", "over_limit_t", "over_price",
            "ore_bill_no", "ore_bill_date")
# Số và ngày phiếu quặng: kế toán nhập KHI NHẬN GIẤY (anh Khampla, C3.7). Bãi chỉ đính kèm ảnh.
COT_KE_TOAN = ("ore_bill_no", "ore_bill_date")
COT_SO = ("odo_out", "odo_back", "weight_origin", "weight_dest", "price", "hire_price",
          "fee_pct", "over_limit_t", "over_price", "rate_usd", "rate_thb", "rate_vnd", "rate_cny")
COT_TIEN_TE = ("price_ccy", "hire_ccy")          # ô CHỌN tiền tệ, không phải số
# Trường nào thuộc mục nào — để khoá theo trạng thái duyệt của mục
MUC_CUA_COT = {
    "info":  {"doc_date", "out_date", "back_date", "kind", "company", "owner_name", "vehicle_id", "truck_no",
              "brand_model", "plate_head", "plate_trailer", "driver_id", "driver_name", "odo_out", "odo_back"},
    "trans": {"customer_id", "customer_name", "route_id", "goods_type", "ore_bill_no", "ore_bill_date", "origin",
              "destination", "weight_origin", "weight_dest", "price", "price_ccy", "price_mode", "hire_price", "hire_ccy",
              "fee_pct", "over_limit_t", "over_price"},
}
# Lưu phiếu và các nút mục (02/10, chủ dự án than chậm): commit giữa yêu cầu (GiaoDichKho) mặc định làm MỌI đối tượng hết hạn —
# dựng lại phiếu trả về sau đó đọc lại từng thứ đã có trong tay (người dùng, phiếu, khách, hợp đồng…), mỗi thứ một lượt tới DB ở
# xa. Hai đường này tự ghi những gì nó đổi, nên giữ nguyên trạng trong phiên là đúng số; câu truy vấn mới vẫn đọc DB như thường.
HET_HAN_SAU_COMMIT = False                  # Session.expire_on_commit của hai đường đó
# cột của một dòng chi được chép khi lưu lại dòng cùng mã (_ap_dong_chi) — mọi cột trừ mã dòng và mã phiếu
COT_DONG_CHI = tuple(c.name for c in TripExpense.__table__.columns if c.name not in ("id", "trip_id"))


def ma_tk_mac_dinh(company, section, source=None, place=None):
    """Định khoản mặc định khi chưa có dòng đầy đủ — luật ở services/tai_khoan.dinh_khoan_dong."""
    return TK.dinh_khoan_dong(company, section, source, place=place)


def _gan_tk(p, e, ma=None):
    """Đặt mã định khoản cho một dòng chi: mã người dùng tự chọn (ngoài bộ mã máy đặt) thì giữ, còn lại tính theo luật
    hiện hành với ĐỦ thông tin của dòng (cách trả, ghi nợ, thẻ, ai trả) — không phải chỉ mục và nguồn như trước 30/09."""
    e.acct_code = ma if (ma and not TK.la_ma_he_thong(ma)) else None
    if e.acct_code:
        # 10/10 (soát logic): mã gửi lên TRÙNG mã màn đang hiện cho dòng (luật + TK riêng nhà cung cấp / chủ xe — tk_dong_rieng) thì
        # không phải mã tự chọn. Hộp Định khoản điền sẵn mã đã thay TK riêng; bấm Đồng ý không đổi gì mà ghim mã đó thì dòng thành
        # "tự chọn", rơi khỏi bút toán nợ NCC lúc khoá và không theo TK riêng về sau.
        db, thu = object_session(p), e.acct_code
        e.acct_code = None
        chu = TK.chu_xe_rieng(db, p.owner_id) if db is not None and p.company == "joint" else None
        if db is None or TK.tk_dong_rieng(p.company, e, db, chu=chu) != thu:
            e.acct_code = thu
    e.acct_code = TK.tk_dong(p.company, e)
    return e


def _ngay(v):
    if v in (None, ""):
        return None
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD, nhận '%s'." % v})


def _doi_so(moi, cu, ten):
    """Ô số gửi lên có khác số đang lưu không (trống = None)."""
    v = _so(moi, ten)
    return (v is None) != (cu is None) or (v is not None and abs(v - cu) > 1e-9)


def _so(v, ten):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Ô %s phải là số, nhận '%s'." % (ten, v)})


def _tien_te(v, ten, bat_buoc=False):
    """Ô chọn tiền tệ. Gõ bậy thì báo rõ chứ không lặng lẽ đổi thành LAK — nhầm tiền là nhầm tiền thật."""
    if v in (None, ""):
        return "USD" if bat_buoc else None
    m = str(v).strip().upper()
    if m not in TIEN_TE:
        raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Ô %s phải là một trong %s, nhận '%s'." % (ten, ", ".join(TIEN_TE), v)})
    return m


def _ghi_log(db, phieu, user, hanh_dong, ts=None):
    """`ts` (06/10): giờ thật của thao tác gửi muộn từ hàng đợi máy tài xế — None thì giờ máy chủ như trước."""
    db.add(TripLog(trip_id=phieu.id, user_name=user.full_name, role=user.role, action=hanh_dong, **({"ts": ts} if ts else {})))


def _muc_cua(db, phieu):
    ds = {s.section: s for s in db.query(TripSection).filter(TripSection.trip_id == phieu.id).all()}
    for m in MUC:                       # phiếu cũ thiếu dòng nào thì bù "wait"
        if m not in ds:
            s = TripSection(trip_id=phieu.id, section=m, status="wait"); db.add(s); ds[m] = s
    return ds


def _trang_thai_muc(ds):
    """Như _muc_cua nhưng CHỈ ĐỌC (danh sách là GET, không được ghi thêm dòng "wait" vào DB)."""
    ra = {k: v.status for k, v in ds.items()}
    for m in MUC:
        ra.setdefault(m, "wait")
    return ra


def _tk_rieng(db, phieu, dong):
    """09/10 (anh Khampla): tài khoản riêng của nhà cung cấp trên các dòng và của chủ xe phiếu xe thuê — màn cũ tính mã mặc định
    trên trình duyệt (tkMacDinh) rồi thay theo bảng này, như services/tai_khoan.doi_cap. Chỉ đối tượng có mã riêng.
    `ncc` theo id nhà cung cấp ghi trên dòng; `ncc_khoan` theo khoản mục của dòng KHÔNG ghi nhà cung cấp (TK.ncc_cua_dong)."""
    ra = {"ncc": {}, "ncc_khoan": {}, "chu_xe": None}
    for d in dong:
        s = TK.ncc_cua_dong(db, d)
        if s is None or not (s.acct_no or s.acct_co):
            continue
        tk = {"no": s.acct_no or None, "co": s.acct_co or None}
        if getattr(d, "supplier_id", None):
            ra["ncc"][d.supplier_id] = tk
        else:
            ra["ncc_khoan"][d.item_key] = tk
    if phieu.company == "joint" and phieu.owner_id:
        o = db.get(Owner, phieu.owner_id)
        if o is not None and (o.acct_no or o.acct_co):
            ra["chu_xe"] = {"no": o.acct_no or None, "co": o.acct_co or None}
    return ra


def _dong_chi(db, phieu):
    return (db.query(TripExpense).filter(TripExpense.trip_id == phieu.id)
            .order_by(TripExpense.section, TripExpense.line_no).all())


def _xuat_dong(d, company=None):
    return {"id": d.id, "section": d.section, "line_no": d.line_no, "item_key": d.item_key,
            "item_name": d.item_name, "qty": d.qty, "unit_price": d.unit_price, "sale_price": d.sale_price, "currency": d.currency,
            "place": d.place, "place_id": d.place_id, "supplier_id": d.supplier_id, "paid_by_epl": d.paid_by_epl, "acct_code": TK.tk_dong(company, d), "source": d.source,
            "part_id": d.part_id, "stock_move_id": d.stock_move_id,
            "toll_card_id": d.toll_card_id, "card_move_id": d.card_move_id,
            "ghi_no": bool(d.ghi_no), "note": d.note,
            # cách trả (Excel anh Khampla, 29/09) và dòng này có vào tiền mặt tài xế cầm đi không — màn tài xế dùng thẳng
            "pay_channel": d.pay_channel, "cach_tra": cach_tra(d, company) if d.section in ("travel", "other") else None,
            "tien_mat_tx": la_tien_mat_tai_xe(d, company)}


def muc_su_kien(e):
    """Khai báo của tài xế rơi vào mục nào của phiếu: khai dầu → III; sự cố sửa chữa → V; sự cố khác → VI."""
    if e.kind == "refuel":
        return "fuel"
    if e.kind == "repair" or (e.incident_type or "breakdown") in SU_CO_SUA_CHUA:
        return "repair"
    return "other"


# ai duyệt khai báo của tài xế, theo mục nó rơi vào (xem SU_CO_SUA_CHUA)
DUYET_SU_KIEN = {"fuel": ("yard", "fuel", "admin"), "repair": ("repair", "admin"), "other": ("yard", "admin")}


def _xuat_su_kien(e):
    # 10/10: ghi chú máy tự ghi (tài xế báo về, báo cân mỏ, đổi xe — tiếng Việt trong DB) kèm note_lo / note_en (services/loi_dich)
    return LD.gan_ban_dich({"id": e.id, "ts": e.ts.isoformat() if e.ts else None, "kind": e.kind, "stop_seq": e.stop_seq, "muc": muc_su_kien(e),
            "incident_type": e.incident_type, "note": e.note, "expense_id": e.expense_id, "by_user": e.by_user,
            "status": e.status or "approved", "reported_cost": e.reported_cost, "currency": e.currency,
            "qty_l": e.qty_l, "place_id": e.place_id, "supplier_id": e.supplier_id,
            "can_run": e.can_run, "paid_by_driver": e.paid_by_driver,
            "approved_by": e.approved_by, "approved_at": e.approved_at.isoformat() if e.approved_at else None}, "note")


def _cau_chua_tam_ung(db, p, hau_qua):
    """Câu báo khi tài xế chưa nhận tạm ứng; None = vừa hỏi lại hệ kế toán thì thủ quỹ đã ghi sổ, mục IV đã "đã chi"."""
    if not CHI.chi_o_ke_toan():
        return "Chưa chi tiền tạm ứng (mục IV chưa 'đã chi') — tài xế chưa nhận tiền thì %s." % hau_qua
    r = CHI.cua_phieu(db, p, cap_nhat=True)
    if _muc_cua(db, p)["travel"].status == "paid":
        return None
    if r is not None and r.status == "da_gui":
        return "Phiếu chi tạm ứng %s bên hệ kế toán chưa ghi sổ — tài xế chưa nhận tiền thì %s. Thủ quỹ chi và ghi sổ ở bên đó." % (
            r.document_no or r.real_id, hau_qua)
    if r is not None and r.status == "loi":
        return "Chưa tạo được phiếu chi tạm ứng bên hệ kế toán (%s) — KT Chi phí gửi lại ở màn Phiếu đề nghị chi; %s." % (
            r.error_message or r.error_code, hau_qua)
    return "Mục IV chưa ghi sổ — KT Chi phí ghi sổ thì phiếu chi tạm ứng mới sang hệ kế toán để thủ quỹ chi; %s." % hau_qua


def _cua_tai_xe(db, p, user):
    """Vai tài xế chỉ được đụng phiếu của chính mình."""
    if user.role != "driver":
        return
    if not user.driver_id or p.driver_id != user.driver_id:
        raise HTTPException(403, {"ma": "KHONG_PHAI_PHIEU_CUA_BAN", "loi": "Đây không phải phiếu của bạn."})


_TEN_MUC = {"fuel": "III (nhiên liệu)", "travel": "IV (đi đường)", "repair": "V (sửa chữa)", "other": "VI (chi khác)"}


def _gon(x):
    x = float(x or 0)
    return ("%d" % x) if x == int(x) else ("%g" % x)


def _dong_tam_ung(p, cac_dong):
    """Các dòng TIỀN MẶT tài xế cầm đi: mọi khoản EPL ứng trừ những gì xuất từ kho (dầu kho, phụ tùng kho)."""
    return [d for d in cac_dong if la_tien_mat_tai_xe(d, p.company)]


def da_thu_theo_phieu(db, trip_ids):
    """Tổng đã thu (LAK) của nhiều phiếu trong MỘT truy vấn — danh sách 200 phiếu thì đừng hỏi 200 lần.
    Từ 01/10 (bỏ trang kế toán tạm — `collected_lak` bên đó là số thử): BẢN ĐỌC LẠI thu tiền SO bên hệ anh Tune
    (gui_so_tune.thu_da_thu, theo tiền SO) quy Kíp theo tỷ giá khoá trên phiếu. Chưa có SO / chưa đọc lại thì 0."""
    ids = [i for i in (trip_ids or []) if i]
    if not ids:
        return {}
    q = (db.query(GuiSoTune.trip_id, GuiSoTune.thu_da_thu, GuiSoTune.currency, Trip.price_ccy, Trip.rate_usd, Trip.rate_thb,
                  Trip.rate_vnd, Trip.rate_cny)
         .join(Trip, Trip.id == GuiSoTune.trip_id)
         .filter(GuiSoTune.trip_id.in_(ids), GuiSoTune.status == "synced", GuiSoTune.thu_da_thu > 0))
    return {r.trip_id: float(r.thu_da_thu) * ty_gia(r, r.currency or r.price_ccy) for r in q}


def _diem_tuyen(db, phieu):
    if not phieu.route_id:
        return []
    return [{"seq": s.seq, "name": s.name, "km_from_prev": s.km_from_prev}
            for s in db.query(RouteStop).filter(RouteStop.route_id == phieu.route_id).order_by(RouteStop.seq).all()]


# Khoá TIỀN BÁN trên một tờ phiếu: giá khách trả, giá thuê xe ngoài, phần trừ của chủ xe, lãi chuyến.
# Bãi, tài xế, thủ kho và hai tổ ở Thà Bốc không được thấy — đó là biên lợi nhuận của công ty.
COT_TIEN_BAN = ("price", "price_ccy", "price_mode", "hire_price", "hire_ccy",
                "fee_pct", "over_limit_t", "over_price", "owner_paid_usd", "owner_paid_lak")
# Trong khối `tinh`: mọi thứ dính doanh thu, tiền thuê, lãi và công nợ khách. Phần CHI phí thì giữ —
# chính họ nhập và chi, giấu đi là họ không kiểm được việc của mình.
TINH_TIEN_BAN = ("don_gia", "doanh_thu", "doanh_thu_lak", "gia_thue", "tien_thue", "tien_thue_lak",
                 "tien_thue_theo_cuoc", "phi", "tru_vuot", "ung_truoc", "tra_chu_xe", "tra_chu_xe_lak",
                 "chu_xe_tu_tra_lak", "lai", "lai_lak", "giu_lai", "da_thu", "da_thu_lak",
                 "con_lai", "con_lai_lak", "tong_chi_ccy")


def _bo_tien_ban(ra):
    """Bỏ HẲN các khoá tiền bán khỏi gói dữ liệu trả về (không phải để rỗng, mà không có khoá)."""
    for c in COT_TIEN_BAN:
        ra.pop(c, None)
    t = ra.get("tinh")
    if isinstance(t, dict):
        for c in TINH_TIEN_BAN:
            t.pop(c, None)
    for x in (ra.get("thu_tien") or []):
        x.pop("amount", None); x.pop("amount_lak", None); x.pop("rate_to_lak", None)
    for d in (ra.get("expenses") or []):
        d.pop("sale_price", None)                 # giá bán dầu, phụ tùng cho chủ xe là tiền BÁN (29/09 · 30/09)
    ra.pop("so_ke_toan", None)                    # SO bên kế toán mang cước, số đã thu của khách
    ra.pop("but_toan_cho", None)                  # bút toán chờ mang tiền thuê xe liên kết
    return ra


def nap_lo(db, ds):
    """Nạp MỘT lần cho cả trang danh sách những gì xuat_phieu cần hỏi DB: dòng chi, mục duyệt, số tệp đính kèm,
    và tuyến · hoá đơn gộp · khách · hợp đồng (nạp vào phiên để db.get() sau đó lấy ngay, không hỏi lại).
    Trước 24/09 mỗi phiếu hỏi DB ~9 lần: trang 50 phiếu là 450 câu SQL; nay là 8 câu cho cả trang."""
    ids = [p.id for p in ds]
    nap = {"dong": defaultdict(list), "muc": defaultdict(dict), "tep": defaultdict(lambda: [0, 0, 0]), "giu": [], "so": {}}
    if not ids:
        return nap
    for d in (db.query(TripExpense).filter(TripExpense.trip_id.in_(ids))
              .order_by(TripExpense.trip_id, TripExpense.section, TripExpense.line_no)):
        nap["dong"][d.trip_id].append(d)
    for m in db.query(TripSection).filter(TripSection.trip_id.in_(ids)):
        nap["muc"][m.trip_id][m.section] = m
    for b in db.query(GuiSoTune).filter(GuiSoTune.trip_id.in_(ids)):
        nap["so"][b.trip_id] = b
    for tid, kind, n in (db.query(TripAttachment.trip_id, TripAttachment.kind, func.count())
                         .filter(TripAttachment.trip_id.in_(ids)).group_by(TripAttachment.trip_id, TripAttachment.kind)):
        t = nap["tep"][tid]
        t[0] += n
        t[1] += n if kind == "pod" else 0
        t[2] += n if kind == "pod_sign" else 0
    for M, cot in ((Route, ("route_id",)), (Customer, ("customer_id",)),
                   (Contract, ("contract_id", "hire_contract_id"))):
        k = {getattr(p, c) for p in ds for c in cot if getattr(p, c)}
        if k:
            nap["giu"] += db.query(M).filter(M.id.in_(k)).all()     # giữ tham chiếu: phiên chỉ nhớ yếu
    return nap


def _dem_tep(db, trip_id):
    """(số tệp, số ảnh POD, số chữ ký POD) của một phiếu — MỘT câu (trước 02/10 ba câu đếm riêng)."""
    t = [0, 0, 0]
    for kind, n in (db.query(TripAttachment.kind, func.count()).filter(TripAttachment.trip_id == trip_id)
                    .group_by(TripAttachment.kind)):
        t[0] += n
        t[1] += n if kind == "pod" else 0
        t[2] += n if kind == "pod_sign" else 0
    return t


def xuat_phieu(db, phieu, day_du=True, da_thu=None, vai=None, nap=None):
    """Gói dữ liệu một tờ phiếu. `vai` là vai người gọi: vai không được thấy tiền bán thì các khoá đó
    bị BỎ HẲN ở đây — trước 22/09 chỉ giao diện che, mở công cụ trình duyệt là đọc được hết.
    `nap` (từ nap_lo) là phần đã nạp sẵn cho cả danh sách — có thì không hỏi DB từng phiếu."""
    dong = nap["dong"].get(phieu.id, []) if nap else _dong_chi(db, phieu)
    tep = nap["tep"].get(phieu.id, (0, 0, 0)) if nap else _dem_tep(db, phieu.id)
    so = nap["so"].get(phieu.id) if nap else DNT.so_cua(db, phieu)      # một lần — trước 02/10 hỏi hai lần (đã thu, SO)
    if da_thu is None:
        da_thu = DNT.da_thu_lak(phieu, so)
    ra = {c: getattr(phieu, c) for c in COT_PHIEU}
    for c in COT_NGAY:
        ra[c] = ra[c].isoformat() if ra[c] else None
    tuyen = db.get(Route, phieu.route_id) if phieu.route_id else None
    kh = db.get(Customer, phieu.customer_id) if phieu.customer_id else None
    ra.update({"id": phieu.id, "transport_status": phieu.transport_status,
               # 01/10 (bỏ trang kế toán tạm — invoiced · inv_no · invoice_id · invoiced_date · last_paid_date bên đó là số thử,
               # không gửi nữa): hoá đơn, thu tiền khách ở hệ anh Tune. `da_tao_so` = bên đó đã tạo SO cho DO (ghi công nợ
               # khách); `so_ke_toan` = lần gửi SO + bản đọc lại thu tiền; finance_status = bản chép trạng thái thu bên đó.
               "finance_status": phieu.finance_status,
               "da_tao_so": bool(so is not None and so.status == "synced"),
               "so_ke_toan": GT.xuat(so),
               "inv_mode": (kh.invoice_mode if kh else None) or "phieu",
               "locked": bool(phieu.locked), "locked_by": phieu.locked_by,
               "locked_at": phieu.locked_at.isoformat() if phieu.locked_at else None,
               "owner_id": phieu.owner_id, "owner_payment_id": phieu.owner_payment_id,
               "owner_paid": bool(phieu.owner_paid or phieu.owner_payment_id), "owner_paid_usd": phieu.owner_paid_usd,
               "owner_paid_lak": phieu.owner_paid_lak, "owner_paid_by": phieu.owner_paid_by,
               "owner_paid_at": phieu.owner_paid_at.isoformat() if phieu.owner_paid_at else None,
               "odo_est": (phieu.odo_out + km_ca_chuyen(tuyen)) if (phieu.odo_out and tuyen and km_ca_chuyen(tuyen)) else None,
               "attachments": tep[0], "pod_files": tep[1], "pod_signed": tep[2] > 0,
               "pod_at": phieu.pod_at.isoformat(timespec="minutes") if phieu.pod_at else None,
               "pod_lat": phieu.pod_lat, "pod_lng": phieu.pod_lng, "pod_by": phieu.pod_by,
               "contract_id": phieu.contract_id, "contract_no": phieu.contract_no,
               "hire_contract_id": phieu.hire_contract_id, "hire_contract_no": phieu.hire_contract_no,
               "contract_state": _tt_hop_dong(db, phieu.contract_id, phieu),
               "hire_contract_state": _tt_hop_dong(db, phieu.hire_contract_id, phieu),
               "created_by": phieu.created_by,
               "created_at": phieu.created_at.isoformat() if phieu.created_at else None,
               "tinh": tinh_phieu(phieu, dong, da_thu),
               "hinh_thuc": {"tam_ung": hinh_thuc(phieu, "tam_ung"), "xuat": hinh_thuc(phieu, "xuat")},
               "sections": _trang_thai_muc(nap["muc"].get(phieu.id, {})) if nap else {s.section: s.status for s in _muc_cua(db, phieu).values()}})
    if day_du:
        ra["goods"] = KH.dong_hang(db, phieu.id)
        ra["ton_lo"] = KH.ton_lo(db, phieu.id) if phieu.kind == "gom" else None
        ra["expenses"] = [_xuat_dong(d, phieu.company) for d in dong]
        ra["tk_rieng"] = _tk_rieng(db, phieu, dong)
        ra["logs"] = [{"ts": l.ts.isoformat() if l.ts else None, "user": l.user_name, "role": l.role,
                       "action": l.action}
                      for l in db.query(TripLog).filter(TripLog.trip_id == phieu.id)
                      .order_by(TripLog.ts.desc()).limit(60).all()]
        su_kien = db.query(TripEvent).filter(TripEvent.trip_id == phieu.id).order_by(TripEvent.ts).all()
        ra["events"] = [_xuat_su_kien(e) for e in su_kien]
        # tạm ứng chi ở hệ kế toán (01/10): trạng thái phiếu chi bên đó — số tiền bỏ với vai không thấy tiền chi
        ra["chi_tam_ung"] = dict(CHI.xuat(CHI.cua_phieu(db, phieu), thay_tien=vai is None or thay_tien_chi(vai)) or {},
                                 o_ke_toan=CHI.chi_o_ke_toan())
        # chi mục V, VI ở hệ kế toán (01/10): phiếu chi "Chi khác" bên đó cho khoản quỹ trả ngay — trạng thái từng lần
        lan = CMT.cac_lan(db, phieu.id)
        ra["chi_muc_ke_toan"] = {m: CMT.tom_tat(db, phieu, m, [r for r in lan if r.section == m], dong,
                                                thay_tien=vai is None or thay_tien_chi(vai)) for m in CMT.MUC}
        # bút toán chờ gửi của phiếu (khoá phiếu: thuê xe, ghi nợ nhà cung cấp) — chỉ vai xem được màn bút toán
        if vai is None or vai in BTC.VAI_XEM:
            ra["but_toan_cho"] = [BTC.xuat(r, phieu.doc_no) for r in BTC.danh_sach(db, trip_id=phieu.id)]
        ra["route_stops"] = _diem_tuyen(db, phieu)
        # điểm xa nhất đã tới trên tuyến — để vẽ tiến độ
        da_toi = [e.stop_seq for e in su_kien if e.kind == "arrive_stop" and e.stop_seq]
        toi = max(da_toi) if da_toi else (1 if phieu.transport_status != "dispatched" else 0)
        # Xe ĐÃ BÁO TỚI NƠI thì coi như đã qua hết chặng, dù Bãi không bấm đủ từng mốc trên đường.
        # Không vậy thì màn theo dõi ghi "Đã giao hàng" mà vẫn "1/4 chặng" — hai câu đá nhau.
        if phieu.transport_status == "arrived" and ra["route_stops"]:
            toi = max(toi, len(ra["route_stops"]))
        ra["stop_reached"] = toi
        if vai is not None:
            # Việc 11 (màn Web): ô nào sửa được, nút nào hiện ở mục nào, việc mức phiếu — tính trên bản đầy đủ, trước khi bỏ tiền
            ra["quyen"] = QP.quyen(ra, vai)
    if vai is not None and not thay_tien_chi(vai):
        _bo_tien_chi(ra)
    elif vai is not None and not thay_gia_kho(vai):
        _bo_gia_kho(ra)
    if vai is not None and not thay_tien_ban(vai):
        return _bo_tien_ban(ra)
    return ra


def _tt_hop_dong(db, cid, p):
    """Trạng thái hợp đồng TẠI NGÀY PHIẾU (con_han · sap_het · het_han · chua_hieu_luc · ngung) — None nếu không có."""
    if not cid:
        return None
    hd = db.get(Contract, cid)
    return HD.trang_thai(hd, p.doc_date or dt.date.today()) if hd else None


# Tiền CHI bỏ khỏi gói của Bãi và tài xế (anh Khampla A2): đơn giá, tiền tệ, mã tài khoản từng dòng; tổng chi;
# tỷ giá trên phiếu; số tiền báo trong khai báo dọc đường. Số lượng, nơi đổ, ai trả thì giữ — việc của họ.
COT_TY_GIA = ("rate_usd", "rate_thb", "rate_vnd", "rate_cny")
DONG_TIEN_CHI = ("unit_price", "currency", "acct_code")
TINH_TIEN_CHI = ("chi", "tong_chi_lak", "tong_chi_ccy")


def _bo_tien_chi(ra):
    for c in COT_TY_GIA:
        ra.pop(c, None)
    for d in (ra.get("expenses") or []):
        for c in DONG_TIEN_CHI:
            d.pop(c, None)
    t = ra.get("tinh")
    if isinstance(t, dict):
        for c in TINH_TIEN_CHI:
            t.pop(c, None)
    for e in (ra.get("events") or []):
        e.pop("reported_cost", None); e.pop("currency", None)
    ra.pop("tk_rieng", None)                 # TK riêng nhà cung cấp / chủ xe — Bãi không thấy mã tài khoản (A2), soát 10/10
    return ra


def _bo_gia_kho(ra):
    """Tổ sửa chữa (30/09): thấy tiền chi mua ngoài / garage (chính họ hỏi thợ) nhưng KHÔNG thấy giá vốn kho — bỏ đơn giá
    dòng lấy kho (dầu, phụ tùng) và mọi tổng chi (tổng có giá kho bên trong, trừ ngược ra được)."""
    for d in (ra.get("expenses") or []):
        if d.get("source") == "kho":
            d.pop("unit_price", None)
    t = ra.get("tinh")
    if isinstance(t, dict):
        for c in TINH_TIEN_CHI:
            t.pop(c, None)
    return ra


# ---------------------------------------------------------------- danh sách & xem
@router.get("/api/khoan-muc")
def khoan_muc(db: Session = Depends(get_db)):
    from routes.nha_cung_cap import khoan_muc_ncc
    KMC.nap(db)          # 08/10: danh mục cấu hình được — tiến trình nào cũng nạp lại khi có người mở phiếu
    # ncc_items (06/10): khoản mục có nhà cung cấp theo dõi nợ — gương JS tkMacDinh tính mục V "theo đợt" (…/4021) như tai_khoan
    # all_items · names (08/10): mọi khoản kể cả đã ngưng (dòng cũ vẫn hiện đúng tên) · tên ba thứ tiếng của khoản thêm mới
    return {"items": KHOAN_MUC, "all_items": KMC.TAT_CA, "names": KMC.TEN, "acct_codes": MA_TK, "pay_channels": list(CACH_TRA), "pay_default": CACH_TRA_MAC_DINH, "chain": {k: list(v) for k, v in CHUOI.items()},
            "acct_rule": TK.luat_cho_giao_dien(), "ncc_items": sorted(khoan_muc_ncc(db)),
            "event_kinds": list(SU_KIEN), "incident_types": list(LOAI_SU_CO)}


CO_TOI_DA = 500          # một trang không quá 500 phiếu — muốn nhiều hơn thì lọc tháng / tìm
TRAN_DEM = 10000         # tổng số khớp chỉ đếm tới đây — quá thì báo "10.000+" (đếm đủ cả năm / cả bảng thì tăng theo dữ liệu)


def dem_tran(qs, response, tran=TRAN_DEM):
    """Đếm số dòng khớp bộ lọc nhưng DỪNG ở `tran`: header X-Tong = min(số khớp, tran), X-Tong-Tran = 1 khi còn nhiều hơn.
    Một trang 50 phiếu không phụ thuộc tổng dữ liệu — chỉ câu đếm là tăng theo (4 năm 0,23 s; 500 GB ~8 s) — nên đếm có trần."""
    n = qs.order_by(None).limit(tran + 1).count()
    response.headers["X-Tong"] = str(min(n, tran))
    if n > tran:
        response.headers["X-Tong-Tran"] = "1"
    return min(n, tran), n > tran


def _dau_thang(thang):
    try:
        y, m = (int(x) for x in str(thang).split("-")[:2])
        return dt.date(y, m, 1), (dt.date(y + (m == 12), m % 12 + 1, 1))
    except (TypeError, ValueError):
        raise HTTPException(422, {"ma": "THANG_SAI", "loi": "Tháng phải có dạng YYYY-MM."})


def loc_phieu(qs, q=None, thang=None, tu=None, den=None):
    """Lọc tháng / khoảng ngày / chữ tìm — dùng chung cho danh sách phiếu và các màn tra phiếu khác."""
    if thang:
        a, b = _dau_thang(thang)
        qs = qs.filter(Trip.doc_date >= a, Trip.doc_date < b)
    if tu:
        qs = qs.filter(Trip.doc_date >= _ngay(tu))
    if den:
        qs = qs.filter(Trip.doc_date <= _ngay(den))
    if q and q.strip():
        t = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        # đúng biểu thức của chỉ mục trigram ix_trips_tim (database.py) — viết khác đi là PostgreSQL quét cả bảng
        qs = qs.filter(text("(%s) ILIKE :tim ESCAPE '\\'" % BIEU_THUC_TIM_PHIEU).bindparams(tim=t))
    return qs


@router.get("/api/trips")
def ds_phieu(response: Response, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai),
             transport_status: str = None, finance_status: str = None, company: str = None, q: str = None,
             thang: str = None, tu: str = None, den: str = None, kind: str = None, customer_id: str = None,
             vehicle_id: str = None, owner_id: str = None, invoiced: bool = None, locked: bool = None,
             da_tao_so: bool = None, trang: int = 1, co: int = 50, sap: str = None):
    """Danh sách phiếu — LỌC · TÌM · PHÂN TRANG ngay trong SQL (chủ dự án chốt 24/09: nghìn chuyến / ngày).

    Trước đây trả MỌI phiếu rồi tìm bằng Python: một năm 365.000 phiếu là quá 60 giây. Nay mặc định 50 phiếu mới
    nhất (`co` tối đa 500, `trang` từ 1); header X-Tong là tổng số phiếu khớp bộ lọc để giao diện vẽ phân trang.
    `transport_status` / `finance_status` nhận nhiều giá trị cách nhau dấu phẩy. `da_tao_so` (01/10): DO bên hệ kế toán đã có
    SO hay chưa; `invoiced` (cờ hoá đơn trang tạm cũ) nay hiểu là `da_tao_so`."""
    qs = db.query(Trip)
    if user.role == "driver":                    # tài xế chỉ thấy phiếu của mình
        qs = qs.filter(Trip.driver_id == (user.driver_id or "__khong_co__"))
    if transport_status: qs = qs.filter(Trip.transport_status.in_(transport_status.split(",")))
    if finance_status: qs = qs.filter(Trip.finance_status.in_(finance_status.split(",")))
    if company: qs = qs.filter(Trip.company == company)
    if kind: qs = qs.filter(Trip.kind == kind)
    if customer_id: qs = qs.filter(Trip.customer_id == customer_id)
    if vehicle_id: qs = qs.filter(Trip.vehicle_id == vehicle_id)
    if owner_id: qs = qs.filter(Trip.owner_id == owner_id)
    if da_tao_so is None:
        da_tao_so = invoiced
    if da_tao_so is not None:
        co_so = db.query(GuiSoTune.trip_id).filter(GuiSoTune.status == "synced", GuiSoTune.trip_id.isnot(None))
        qs = qs.filter(Trip.id.in_(co_so) if da_tao_so else ~Trip.id.in_(co_so))
    if locked is not None: qs = qs.filter(Trip.locked.is_(True) if locked else or_(Trip.locked.is_(False), Trip.locked.is_(None)))
    qs = loc_phieu(qs, q, thang, tu, den)
    co = max(1, min(int(co or 50), CO_TOI_DA))
    trang = max(1, int(trang or 1))
    dem_tran(qs, response)
    # `sap=cu`: cũ nhất trước (màn Lịch sử phiếu của tài xế, 30/09); mặc định mới nhất trước. Phiếu KHÔNG có ngày lập luôn
    # nằm cuối (01/10): PostgreSQL mặc định xếp NULL lên đầu khi giảm dần, nên một phiếu thiếu ngày đứng đầu danh sách và
    # màn Tổng quan lấy "tháng của phiếu mới nhất" ra ô trống → rơi về tháng hiện tại không có số liệu.
    thu_tu = ((Trip.doc_date.asc().nullslast(), Trip.doc_no.asc()) if sap == "cu"
              else (Trip.doc_date.desc().nullslast(), Trip.doc_no.desc()))
    ds = qs.order_by(*thu_tu).offset((trang - 1) * co).limit(co).all()
    thu = da_thu_theo_phieu(db, [p.id for p in ds])
    nap = nap_lo(db, ds)
    return [xuat_phieu(db, p, day_du=False, da_thu=thu.get(p.id, 0), vai=user.role, nap=nap) for p in ds]


@router.get("/api/trips/{tid}")
def xem_phieu(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _cua_tai_xe(db, p, user)
    return xuat_phieu(db, p, vai=user.role)


# ---------------------------------------------------------------- lập & sửa
def _so_phieu_moi(db, loai="giao"):
    """T4-0428-08/EPL → số kế tiếp trong tháng hiện tại. Chỉ là gợi ý, người lập sửa được.
    Phiếu GOM (mỏ → bãi) đánh dãy riêng G4-…, giống bộ mẫu (G4-0101-09) — trước đây mọi loại đều ra T4-."""
    dau = "G4" if loai == "gom" else "T4"
    thang = dt.date.today().strftime("%m")
    cuoi = (db.query(Trip).filter(Trip.doc_no.like("%s-%%-%s/EPL" % (dau, thang)))
            .order_by(Trip.doc_no.desc()).first())
    so = 1
    if cuoi:
        try:
            so = int(cuoi.doc_no.split("-")[1]) + 1
        except (IndexError, ValueError):
            so = 1
    return "%s-%04d-%s/EPL" % (dau, so, thang)


@router.get("/api/trips-so-moi")
def so_moi(kind: str = "giao", db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return {"doc_no": _so_phieu_moi(db, kind)}


@router.get("/api/trips-moi")
def phieu_moi(kind: str = "giao", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Việc 11 (màn Web): tờ phiếu trắng — số gợi ý theo loại, giá trị mặc định (như lap_phieu), quyền của người gọi trên phiếu mới."""
    loai = kind if kind in LOAI_DO else "giao"
    tg = {r.code: r.rate_to_lak for r in db.query(ExchangeRate).all()}
    return {"doc_no": _so_phieu_moi(db, loai),
            "mac_dinh": {"kind": loai, "company": "EPL", "doc_date": dt.date.today().isoformat(), "out_date": dt.date.today().isoformat(),
                         "price_ccy": "USD", "price_mode": "ton",
                         "goods_type": "iron_ore", "fee_pct": 2, "over_limit_t": 40, "over_price": 1,
                         "rate_usd": tg.get("USD", 22000), "rate_thb": tg.get("THB", 700), "rate_vnd": tg.get("VND", 1.2),
                         "rate_cny": tg.get("CNY", 3000)},
            "quyen": QP.quyen({"kind": loai}, user.role, moi=True)}


@router.get("/api/trips-goi-y")
def goi_y_chi(route_id: str, company: str = "EPL", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """11b (màn Web): dòng chi GỢI Ý theo tuyến cho mục III, IV, VI (sếp 30/09: "kê sẵn chi phí kiểu gợi ý, họ thêm bớt chỉnh sửa") —
    bộ riêng của tuyến, không có thì bộ chung Excel (routes/tuyen.goi_y_cua). Luật mặc định như màn cũ (JS dienGoiY): dầu theo nơi đổ
    (kho / mua; xe thuê: kho → EPL ứng, mua → chủ xe tự trả); xe thuê thì khoản đi đường mặc định "chủ xe tự trả" (06/10, CA-3).
    Vai không thấy tiền chi: không có đơn giá (máy chủ đặt giá gợi ý lúc lưu). → {"dong", "nguon": tuyen | chung, "ten"}."""
    r = db.get(Route, route_id)
    if r is None:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tuyến này."})
    ds, nguon = goi_y_cua(db, r)
    lien_ket = company == "joint"
    ra = []
    for x in ds:
        m = x.get("section")
        if m not in ("fuel", "travel", "other"):
            continue
        d = {"section": m, "item_key": x.get("item_key") or None, "item_name": x.get("item_name") or None, "qty": x.get("qty"),
             "unit_price": x.get("unit_price") or 0, "currency": x.get("currency") or "LAK", "place_id": x.get("place_id") or None,
             "paid_by_epl": True, "pay_channel": x.get("pay_channel") or None}
        if m == "fuel":
            d["source"] = _nguon_theo_diem(db, d)
            if lien_ket:
                d["paid_by_epl"] = d["source"] == "kho"
        elif lien_ket:
            d["paid_by_epl"] = False
        if not thay_tien_chi(user.role):
            d.pop("unit_price"); d.pop("currency")
        ra.append(d)
    return {"dong": ra, "nguon": nguon, "ten": r.name}


# ô của tờ phiếu đi vào phép tính thử (tinh_phieu · km · hao hụt · giá hợp đồng gợi ý)
COT_TINH_THU = ("company", "vehicle_id", "route_id", "customer_id", "goods_type", "doc_date", "odo_out", "odo_back", "weight_origin",
                "weight_dest", "price", "price_ccy", "price_mode", "hire_price", "hire_ccy", "fee_pct", "over_limit_t", "over_price")


@router.post("/api/trips/tinh-thu")
def tinh_thu(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Việc 11 (màn Web): TÍNH THỬ số của tờ phiếu đang nhập — KHÔNG ghi gì. Màn cũ chép phép tính (tinh_toan.tinh_phieu) vào JS
    để số nhảy khi gõ; Web gọi đường này (chuẩn tài liệu 04 §14.1: không tính số có thẩm quyền trên trình duyệt).
    Thân: `id` (phiếu đang sửa — ô không gửi lấy theo phiếu) hoặc không (phiếu mới — mặc định như lap_phieu) + các ô COT_TINH_THU
    + tuỳ chọn `expenses` (dòng chi đang sửa; không gửi thì lấy dòng đã lưu) + tuỳ chọn `goods` (dòng hàng đang sửa: có tấn thì cân
    đầu = tổng tấn, như KH.dat_dong_hang lúc lưu). Vai không thấy tiền bán: ô giá gửi lên bị bỏ, số tiền bán bị bỏ khỏi kết quả như
    xuat_phieu. Có khách + tuyến mà phiếu chưa có đơn giá: lấy giá hợp đồng (như _ap_truong lúc lưu) và trả kèm `gia_hop_dong` để màn
    điền sẵn ô giá. → {"tinh", "odo_km", "odo_est", "hao_t", "weight_origin", "gia_hop_dong"}."""
    from types import SimpleNamespace
    goc = db.get(Trip, str(data["id"])) if data.get("id") else None
    if data.get("id") and goc is None:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    p = SimpleNamespace(**{c.name: (getattr(goc, c.name) if goc is not None else None) for c in Trip.__table__.columns})
    if goc is None:
        tg = {r.code: r.rate_to_lak for r in db.query(ExchangeRate).all()}
        p.rate_usd, p.rate_thb, p.rate_vnd, p.rate_cny = tg.get("USD", 22000), tg.get("THB", 700), tg.get("VND", 1.2), tg.get("CNY", 3000)
        p.company, p.price_ccy, p.price_mode = "EPL", "USD", "ton"
    tien_ban = thay_tien_ban(user.role)
    for c in COT_TINH_THU:
        if c not in data or (c in COT_TIEN and not tien_ban):
            continue
        v = data[c]
        if c in COT_SO:
            v = _so(v, c) if v not in (None, "") else None
        elif c in COT_NGAY:
            v = _ngay(v)
        elif isinstance(v, str):
            v = v.strip() or None
        setattr(p, c, v)
    if isinstance(data.get("goods"), list):
        tong = round(sum(_so(g.get("qty_t"), "qty_t") or 0 for g in data["goods"] if (g or {}).get("loai", "hang") == "hang"), 3)
        if tong:
            p.weight_origin = tong
    gia_hd = None
    if tien_ban and p.customer_id and p.route_id and not p.price:
        g = tim_gia(db, p.customer_id, p.route_id, p.goods_type or "iron_ore", p.doc_date)
        if g:
            p.price, p.price_ccy, p.price_mode = g.price, chuan_tien(g.price_ccy, "USD"), g.price_mode or "ton"
            gia_hd = {"price": p.price, "price_ccy": p.price_ccy, "price_mode": p.price_mode}
            if p.hire_price is None and g.hire_price:
                p.hire_price, p.hire_ccy = g.hire_price, chuan_tien(g.hire_ccy or g.price_ccy, "USD")
                gia_hd.update(hire_price=p.hire_price, hire_ccy=p.hire_ccy)
    if p.vehicle_id and (goc is None or "vehicle_id" in data):
        x = db.get(Vehicle, p.vehicle_id)
        if x is not None and x.owner_type == "joint":            # như _ap_truong: xe của chủ xe liên kết → phiếu xe liên kết
            if "company" not in data:
                p.company = "joint"
            p.owner_id = x.owner_id or p.owner_id
    p.company = p.company if p.company in ("EPL", "joint") else "EPL"
    if p.company == "joint" and p.owner_id:                       # điều khoản chủ xe cho ô còn trống (như lap_phieu)
        o = db.get(Owner, p.owner_id)
        if o is not None:
            p.fee_pct = o.fee_pct if p.fee_pct is None else p.fee_pct
            p.over_limit_t = o.over_limit_t if p.over_limit_t is None else p.over_limit_t
            p.over_price = o.over_price if p.over_price is None else p.over_price
            p.hire_ccy = p.hire_ccy or o.hire_ccy
    if "expenses" in data:
        # 11b: dòng đang sửa trên màn Web — dựng đủ ô để tính tiền, định khoản, cách trả và quyền từng dòng (như _dong_tu_du_lieu)
        dong = []
        for i, d in enumerate(data.get("expenses") or []):
            m = d.get("section")
            if m not in MUC_CHI:
                raise HTTPException(422, {"ma": "MUC_SAI", "loi": "Dòng %d: mục %s không hợp lệ." % (i + 1, m)})
            if m == "fuel":
                nguon = _nguon_theo_diem(db, d)
            elif m == "repair":
                nguon = d.get("source") if d.get("source") in ("kho", "mua") else ("kho" if d.get("part_id") else "mua")
            else:
                nguon = None
            ca = str(d.get("pay_channel") or "").strip()
            dong.append(SimpleNamespace(
                section=m, item_key=d.get("item_key") or None, item_name=d.get("item_name") or None,
                qty=_so(d.get("qty"), "qty") or 0, unit_price=_so(d.get("unit_price"), "unit_price") or 0,
                currency=str(d.get("currency") or "LAK").upper(), paid_by_epl=d.get("paid_by_epl", True) is not False, source=nguon,
                sale_price=_so(d.get("sale_price"), "sale_price") if d.get("sale_price") not in (None, "") else None,
                place_id=d.get("place_id") or None, place=d.get("place"), part_id=d.get("part_id") or None,
                supplier_id=d.get("supplier_id") or (_ncc_theo_diem(db, d) if m == "fuel" else None),
                ghi_no=bool(d.get("ghi_no")) and nguon != "kho", toll_card_id=(d.get("toll_card_id") or None) if m == "travel" else None,
                card_move_id=d.get("card_move_id") or None, stock_move_id=d.get("stock_move_id") or None,
                pay_channel=ca if ca in CACH_TRA else None, acct_code=d.get("acct_code") or None))
    else:
        dong = _dong_chi(db, goc) if goc is not None else []
    da_thu = DNT.da_thu_lak(goc, DNT.so_cua(db, goc)) if goc is not None else 0
    tuyen = db.get(Route, p.route_id) if p.route_id else None
    ca = km_ca_chuyen(tuyen) if tuyen is not None else 0
    ra = {"tinh": tinh_phieu(p, dong, da_thu),
          "odo_km": abs(p.odo_back - p.odo_out) if (p.odo_out is not None and p.odo_back is not None) else None,
          "odo_est": (p.odo_out + ca) if (p.odo_out and ca) else None,
          "hao_t": round(p.weight_origin - p.weight_dest, 3) if (p.weight_origin is not None and p.weight_dest is not None) else None,
          "weight_origin": p.weight_origin, "gia_hop_dong": gia_hd}
    # 11b: từng dòng chi — nguồn (kho / mua), xuất bán, thành tiền LAK, định khoản và cách trả đang hiệu lực, tiền mặt tài xế cầm,
    # quyền từng ô (QP.quyen_dong). Tiền bỏ với vai không thấy (Bãi: mọi tiền chi; tổ sửa chữa / thủ kho: giá vốn kho).
    if dong:
        p_q = {"kind": p.kind, "company": p.company, "locked": bool(getattr(goc, "locked", False)),
               "transport_status": getattr(goc, "transport_status", None), "expenses": [{"section": d.section} for d in dong],
               "sections": {s.section: s.status for s in _muc_cua(db, goc).values()} if goc is not None else {}}
        q = QP.quyen(p_q, user.role, moi=goc is None)
        thay_chi, thay_kho = thay_tien_chi(user.role), thay_gia_kho(user.role)
        chu_rieng = db.get(Owner, p.owner_id) if p.company == "joint" and getattr(p, "owner_id", None) else None
        ra["dong"] = []
        for d in dong:
            xb = la_xuat_ban(p, d)
            ra["dong"].append({
                "nguon": d.source, "xuat_ban": xb,
                "tien_lak": round(tien_dong(p, d)) if thay_chi and (thay_kho or d.source != "kho") else None,
                "tk": TK.tk_dong_rieng(p.company, d, db, chu=chu_rieng) if thay_chi else None,   # 09/10: kèm TK riêng NCC / chủ xe
                "cach_tra": cach_tra(d, p.company) if thay_chi and d.section in ("travel", "other") else None,
                "tien_mat_tx": la_tien_mat_tai_xe(d, p.company),
                "quyen": QP.quyen_dong(q, d, d.source, xb)})
    if not thay_tien_chi(user.role):
        _bo_tien_chi(ra)
    elif not thay_gia_kho(user.role):
        _bo_gia_kho(ra)
    if not tien_ban:
        _bo_tien_ban(ra)
    return ra


def _chan_phieu_trang(p):
    """Phiếu xuất xe phải có xe và tài xế — chủ dự án 01/10: "Sếp lưu được phiếu trắng, không xe, không tài xế — CÓ CHẶN".
    Áp cho mọi vai, kể cả Sếp."""
    if not p.vehicle_id:
        raise HTTPException(422, {"ma": "THIEU_XE", "loi": "Chọn xe trước khi lưu phiếu xuất xe."})
    if not (p.driver_id or (p.driver_name or "").strip()):
        raise HTTPException(422, {"ma": "THIEU_TAI_XE", "loi": "Chọn tài xế trước khi lưu phiếu xuất xe."})


def _ap_truong(db, p, data, user, muc_tt=None):
    """Ghi các trường vào phiếu. Khi sửa, chỉ ghi trường của mục còn được sửa."""
    kh_cu, chu_cu = p.customer_id, p.owner_id
    for c in COT_PHIEU:
        if c not in data:
            continue
        if c in COT_KE_TOAN and user.role not in ("acct", "admin"):
            # Bãi gửi cả bản phiếu lên khi lưu; ô không đổi thì bỏ qua, ô đổi thì từ chối rõ.
            moi_gt = _ngay(data[c]) if c in COT_NGAY else ((str(data[c]).strip() or None) if data[c] is not None else None)
            if moi_gt != getattr(p, c):
                raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Số và ngày phiếu quặng do kế toán nhập khi nhận giấy; Bãi chỉ đính kèm ảnh."})
            continue
        if c in COT_TIEN and c not in COT_KE_TOAN and not thay_tien_ban(user.role):
            # Giá cước, giá thuê xe liên kết, phí, ngưỡng tấn: Bãi không thấy nên không nhập (anh Khampla A2);
            # giá thuê xe do KT Viêng Chăn nhập theo hợp đồng (C4.1). Ô không đổi thì bỏ qua, đổi thì từ chối rõ.
            cu_gt = getattr(p, c)
            if cu_gt is None and p.id is None:
                # Phiếu MỚI chưa ghi: cột chưa mang giá trị mặc định (phí 2 %, ngưỡng 40 t, USD, theo tấn…) — mặc định chỉ
                # vào lúc ghi. Tờ phiếu trắng trên màn gửi đúng các mặc định đó (ô giấu với Bãi); so với mặc định chứ không
                # so với "trống", không thì Bãi không lập được phiếu nào (chủ dự án gặp 28/09).
                md = Trip.__table__.c[c].default
                cu_gt = md.arg if md is not None and md.is_scalar else None
            moi_gt = data[c]
            if c in COT_SO: moi_gt = _so(moi_gt, c) if moi_gt not in (None, "") else None
            elif isinstance(moi_gt, str): moi_gt = moi_gt.strip().upper() or None
            if moi_gt not in (None, "") and moi_gt != cu_gt and not (isinstance(cu_gt, str) and str(moi_gt).upper() == cu_gt.upper()):
                raise HTTPException(403, {"ma": "KHONG_CO_QUYEN",
                                          "loi": "Giá cước, giá thuê xe và phí do kế toán Viêng Chăn nhập; Bãi không nhập ô này."})
            continue
        if c in ("back_date", "odo_back", "weight_dest") and p.transport_status != "arrived":
            # Ngày xe về, km về, cân cuối điền KHI XE VỀ (chủ dự án 29/09): tài xế / Bãi "Báo đã về" (ngày, km), hoặc Bãi
            # "Xe đã tới · nhập cân cuối" — hai đường đó ghi thẳng, không qua đây. Trước lúc đó màn phiếu khoá các ô này;
            # bản phiếu gửi lên mang giá trị cũ thì bỏ qua, giá trị mới thì từ chối rõ. Xe đã tới thì sửa được như cũ.
            moi_gt = _ngay(data[c]) if c in COT_NGAY else (_so(data[c], c) if data[c] not in (None, "") else None)
            if moi_gt is not None and moi_gt != getattr(p, c):
                raise HTTPException(409, {"ma": "CHUA_VE", "loi": (
                    "Cân cuối điền khi xe tới: Bãi bấm Xe đã tới · nhập cân cuối." if c == "weight_dest" else
                    "Ngày xe về và km về điền khi xe về: tài xế bấm Báo đã về, hoặc Bãi bấm Xe đã tới · nhập cân cuối.")})
            continue
        if muc_tt is not None:
            muc = next((m for m, cot in MUC_CUA_COT.items() if c in cot), None)
            if muc and not duoc_sua_muc(user.role, muc, muc_tt[muc]) and not (c in COT_TIEN and duoc_sua_tien(user.role, muc, muc_tt[muc])):
                raise HTTPException(409, {"ma": "MUC_DA_KHOA",
                                          "loi": "Mục %s đã khoá (%s); phải trả lại mới sửa được." % (muc, muc_tt[muc])})
        v = data[c]
        if c in COT_NGAY: v = _ngay(v)
        elif c in COT_SO: v = _so(v, c)
        elif c in COT_TIEN_TE: v = _tien_te(v, c, bat_buoc=(c == "price_ccy"))
        elif c == "price_mode":
            v = (str(v or "ton").strip().lower() or "ton")
            if v not in CACH_TINH_CUOC:
                raise HTTPException(422, {"ma": "CACH_TINH_SAI", "loi": "Cách tính cước phải là 'ton' (theo tấn) hoặc 'chuyen' (trọn chuyến)."})
        elif isinstance(v, str): v = v.strip() or None
        setattr(p, c, v)
    # Chép tên/biển từ danh mục nếu chỉ gửi mã
    if p.vehicle_id:
        x = db.get(Vehicle, p.vehicle_id)
        if x and not data.get("truck_no"):
            p.truck_no, p.brand_model, p.plate_head, p.plate_trailer = x.truck_no, x.brand_model, x.plate_head, x.plate_trailer
        if x and x.owner_type == "joint":
            # Xe của chủ xe liên kết thì phiếu là phiếu xe liên kết — không bắt người lập chọn lại. Chủ xe theo xe kể cả khi màn
            # gửi kèm số xe (giữ biển người lập sửa tay): trước 08/10 khối này nằm trong nhánh "không gửi truck_no" → màn phiếu
            # (luôn gửi truck_no) lập phiếu xe thuê không có owner_id — không tự điền hợp đồng thuê, điều khoản chủ xe.
            if "company" not in data: p.company = "joint"
            if not p.owner_name: p.owner_name = x.owner_name
            if x.owner_id: p.owner_id = x.owner_id
    if p.driver_id and not data.get("driver_name"):
        d = db.get(Driver, p.driver_id)
        if d: p.driver_name = d.name
    if p.customer_id and not data.get("customer_name"):
        k = db.get(Customer, p.customer_id)
        if k: p.customer_name = k.name
    # Tuyến: điền điểm đi/đến nếu người lập chưa gõ
    if p.route_id:
        r = db.get(Route, p.route_id)
        if not r:
            raise HTTPException(422, {"ma": "TUYEN_SAI", "loi": "Không có tuyến này."})
        if not p.origin: p.origin = r.origin
        if not p.destination: p.destination = r.destination
    # Không gửi loại xe thì mặc định xe nhà — cột có default ở CSDL nhưng phép kiểm chạy TRƯỚC khi ghi.
    if not p.company:
        p.company = "EPL"
    if p.company not in ("EPL", "joint"):
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "company phải là EPL hoặc joint."})
    # K3: Bãi không thấy tiền nên không gửi giá; có khách + tuyến trong bảng giá thì máy điền đơn giá hợp đồng.
    # Chỉ điền khi phiếu CHƯA có giá — kế toán đã gõ giá khác hợp đồng thì giữ của kế toán.
    if p.customer_id and p.route_id and not p.price:
        g = tim_gia(db, p.customer_id, p.route_id, p.goods_type, p.doc_date)
        if g:
            # Giá hợp đồng mang theo TIỀN TỆ của hợp đồng đó: khách Trung Quốc ký bằng Nhân dân tệ
            # thì phiếu phải là Nhân dân tệ, không được rơi về USD.
            p.price, p.price_ccy = g.price, chuan_tien(g.price_ccy, "USD")
            p.price_mode = g.price_mode or "ton"
            if p.hire_price is None and g.hire_price:
                p.hire_price, p.hire_ccy = g.hire_price, chuan_tien(g.hire_ccy or g.price_ccy, "USD")
    _ap_hop_dong(db, p, data, user, kh_cu, chu_cu)


def _ap_hop_dong(db, p, data, user, kh_cu, chu_cu):
    """HỢP ĐỒNG trên phiếu (chốt 24/09): tự điền số hợp đồng còn hiệu lực của khách — và của chủ xe nếu là xe liên
    kết — như đơn giá đang tự điền. Chỉ điền lúc lập phiếu và khi đổi khách / chủ xe; kế toán chọn tay một hợp đồng
    khác, hay chọn "không có hợp đồng" (`contract_id` / `hire_contract_id`), thì các lần lưu sau giữ của kế toán."""
    ngay = p.doc_date or dt.date.today()
    for cot_id, cot_so, loai, doi_tac, cu in (("contract_id", "contract_no", "khach", p.customer_id, kh_cu),
                                              ("hire_contract_id", "hire_contract_no", "thue_xe",
                                               p.owner_id if p.company == "joint" else None, chu_cu)):
        if cot_id in data:
            if user.role not in ("acct", "rev", "admin"):
                if (data[cot_id] or None) != getattr(p, cot_id):
                    raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Hợp đồng trên phiếu do kế toán Viêng Chăn chọn."})
                continue
            if data[cot_id]:
                hd = db.get(Contract, str(data[cot_id]))
                if not hd or hd.kind != loai or (hd.customer_id if loai == "khach" else hd.owner_id) != doi_tac:
                    raise HTTPException(422, {"ma": "HOP_DONG_SAI", "loi": "Hợp đồng này không phải của %s trên phiếu."
                                              % ("khách" if loai == "khach" else "chủ xe")})
                setattr(p, cot_id, hd.id); setattr(p, cot_so, hd.contract_no)
            else:
                setattr(p, cot_id, None); setattr(p, cot_so, None)
            continue
        if not doi_tac:
            setattr(p, cot_id, None); setattr(p, cot_so, None)
        elif doi_tac != cu:                       # lập phiếu (cu = None) hoặc đổi khách / chủ xe
            hd = HD.tim(db, loai, doi_tac, ngay)
            setattr(p, cot_id, hd.id if hd else None); setattr(p, cot_so, hd.contract_no if hd else None)
    if not p.price_ccy:
        p.price_ccy = "USD"
    if not p.price_mode:
        p.price_mode = "ton"
    if p.company == "joint" and p.hire_price is None:
        p.hire_price, p.hire_ccy = p.price, p.price_ccy   # mặc định bằng giá nhận — người lập sửa sau


def _nguon_theo_diem(db, d):
    """Kho hay mua là do ĐIỂM ĐỔ quyết định: kho của EPL thì lĩnh (kho), trạm bán dầu thì mua.
    Phiếu cũ chưa có điểm đổ thì vẫn đọc khoá cũ fp_yard/fp_vn để không mất dữ liệu."""
    if d.get("place_id"):
        x = db.get(FuelPlace, d["place_id"])
        if x:
            return "kho" if x.owner_type == "epl" else "mua"
    return "kho" if (d.get("place") or "fp_yard") == "fp_yard" else "mua"


def _ncc_theo_diem(db, d):
    """Nhà cung cấp của điểm đổ (trạm ngoài). Kho của mình thì không có ai để nợ."""
    if db is None or not d.get("place_id"):
        return None
    dd = db.get(FuelPlace, str(d["place_id"]))
    return dd.supplier_id if (dd is not None and dd.owner_type != "epl") else None


def _gia_mac_dinh(db, p, m, source, d):
    """Giá của dòng khi người nhập KHÔNG được đặt giá (Bãi): kho → bình quân kho; phí cầu đường → theo tuyến; còn lại 0
    để kế toán kiểm mục nhập. Trả (đơn giá, tiền tệ)."""
    if db is None:
        return 0, "LAK"
    if m == "fuel" and source == "kho":
        return KK.gia_dau(db, d.get("place_id")), "LAK"                   # kho nhiên liệu ở trang kế toán (28/09)
    if m == "repair" and source == "kho" and d.get("part_id"):
        return KK.gia_phu_tung(db, d["part_id"]), "LAK"         # kho phụ tùng ở trang kế toán (28/09)
    if m == "travel" and d.get("item_key") == "x_toll" and p.route_id:
        r = db.get(Route, p.route_id)
        if r and (r.toll_lak or 0) > 0:
            return r.toll_lak, "LAK"
    if m in ("fuel", "travel", "other") and p.route_id and source != "kho":
        # giá GỢI Ý của tuyến (30/09): kế toán thấy sẵn, sửa khi kiểm — Bãi vẫn không thấy, không nhập tiền
        g = gia_goi_y(db, p.route_id, m, d)
        if g is not None:
            return g
    return 0, str(d.get("currency") or "LAK").upper()


def _dong_tu_du_lieu(p, m, i, d, db=None, dat_gia=True, cu=None):
    """Dựng một dòng chi từ dữ liệu gửi lên; áp định khoản mặc định theo xe nhà/liên kết và nguồn kho/mua.
    `dat_gia=False` (Bãi, tài xế): đơn giá gửi lên bị bỏ qua, lấy giá mặc định.
    `cu` = dòng đang có cùng mã: dòng KHO chưa xuất mà không đổi kho / phụ tùng / số lượng và đã có giá thì giữ giá đó, không
    hỏi lại kho tạm (02/10 — mỗi lần lưu phiếu hỏi giá bình quân sang kho tạm 100–600 ms dù dòng không đổi; giá thật của dòng
    là giá lúc cấp / xuất — phieu_linh.cap_phat chép giá của lần xuất lên dòng)."""
    source = d.get("source")
    if m == "fuel":
        source = _nguon_theo_diem(db, d) if db is not None else ("kho" if (d.get("place") or "fp_yard") == "fp_yard" else "mua")
    elif m == "repair":
        if source not in ("kho", "mua"):
            source = "kho" if d.get("part_id") else "mua"
    else:
        source = None
    if source == "kho" and cu is not None and cu.source == "kho" and (cu.unit_price or 0) > 0 \
            and (cu.place_id or None) == (d.get("place_id") or None) and (cu.part_id or None) == (d.get("part_id") or None) \
            and abs((cu.qty or 0) - (_so(d.get("qty"), "qty") or 0)) < 1e-9:
        gia, tien_te = cu.unit_price, cu.currency or "LAK"
    elif source == "kho":
        # lấy từ kho (dầu C5.3; phụ tùng từ 30/09): giá là giá bình quân của kho, không ai gõ tay — tổ sửa chữa không thấy
        # giá kho nên gửi lên trống, không được thành 0
        gia, tien_te = _gia_mac_dinh(db, p, m, source, d)
    elif not dat_gia and cu is not None:
        gia, tien_te = cu.unit_price, cu.currency          # Bãi không gửi giá: dòng cũ giữ đúng giá kế toán đã nhập
    elif not dat_gia:
        gia, tien_te = _gia_mac_dinh(db, p, m, source, d)
    else:
        gia, tien_te = (_so(d.get("unit_price"), "unit_price") or 0), str(d.get("currency") or "LAK").upper()
    return _gan_tk(p, TripExpense(
        trip_id=p.id, section=m, line_no=i,
        item_key=(d.get("item_key") or None), item_name=(d.get("item_name") or None),
        qty=_so(d.get("qty"), "qty") or 0, unit_price=gia,
        currency=tien_te, place=d.get("place"),
        place_id=d.get("place_id") or None,
        # Đổ ở TRẠM NGOÀI thì dòng chi mang luôn nhà cung cấp của trạm đó — công nợ trạm dầu (C5.1)
        # phải tra được từ dòng chi, chứ không bắt người đọc lần từ điểm đổ sang nhà cung cấp.
        supplier_id=(d.get("supplier_id") or _ncc_theo_diem(db, d) or None),
        paid_by_epl=bool(d.get("paid_by_epl", True)),
        source=source, part_id=d.get("part_id") or None, stock_move_id=d.get("stock_move_id") or None,
        # Phí cầu đường trả bằng thẻ (C6.1): dòng nhớ thẻ nào, thẻ bị trừ lúc kế toán ghi sổ mục IV.
        toll_card_id=(d.get("toll_card_id") or None) if m == "travel" else None,
        # Ghi nợ tại trạm (C5.1): chỉ có nghĩa với khoản MUA NGOÀI — hàng lấy từ kho mình thì nợ ai.
        ghi_no=bool(d.get("ghi_no")) and source != "kho", note=d.get("note"),
        pay_channel=_cach_tra_gui(m, d, p.company)), d.get("acct_code"))


def _cach_tra_gui(m, d, company=None):
    """Cách trả gửi lên (mục IV, VI): một trong CACH_TRA; bỏ trống / trùng mặc định của khoản mục thì để trống."""
    c = str(d.get("pay_channel") or "").strip()
    if m not in ("travel", "other") or not c:
        return None
    if c not in CACH_TRA:
        raise HTTPException(422, {"ma": "CACH_TRA_SAI", "loi": "Cách trả phải là tiền mặt khi xe đi, trả cùng lương hoặc ghi nợ nhà cung cấp."})
    if company == "joint" and c == "luong":
        c = "tien_mat"            # xe thuê: không có trả cùng lương — EPL ứng là tạm ứng ghi công nợ chủ xe (30/09)
    return None if c == CACH_TRA_MAC_DINH.get(d.get("item_key") or "", "tien_mat") else c


def _cach_tra_mac_dinh(db, p, m, d, cu=None):
    """Cách trả của một dòng mục IV / VI do vai KHÔNG được đổi cách trả gửi lên (Bãi — 08/10): dòng cũ cùng khoản mục giữ cách trả
    đang có (KT Chi phí có thể đã đổi); dòng mới / đổi khoản mục → theo bộ gợi ý của tuyến, rồi mặc định khoản mục. Cách trả Bãi gửi
    lên bị bỏ qua — màn khoá ô này với Bãi."""
    if cu is not None and (cu.item_key or None) == (d.get("item_key") or None) and (cu.item_name or None) == (d.get("item_name") or None):
        return cu.pay_channel
    return _cach_tra_gui(m, {"item_key": d.get("item_key"), "pay_channel": cach_tra_goi_y(db, p.route_id, m, d)}, p.company)


def _ai_tra_dong_kho(p, e, d, cac_dong=()):
    """"Ai trả" của một dòng KHO đã có (giữ lại khi lưu, hoặc kế toán gõ giá): xe thuê thì dầu / phụ tùng lấy kho luôn là xuất
    bán — chỉ đổi được VỀ "EPL ứng" (sửa dòng cũ ghi "chủ xe tự trả"); đổi một dòng đang EPL ứng sang "chủ xe tự trả" → 422
    KHO_XE_THUE_XUAT_BAN. Dòng cũ đang "chủ xe tự trả" gửi nguyên thì để yên (khoá phiếu chặn, chỉ cách sửa)."""
    if "paid_by_epl" not in d or not la_xuat_ban(p, e):
        return
    if d.get("paid_by_epl"):
        e.paid_by_epl = True
    elif e.paid_by_epl is not False:
        e.paid_by_epl = False
        BTC.chan_kho_xe_thue_tu_tra(p, e, list(cac_dong))


def _ap_dong_chi(db, p, cac_dong, user, muc_tt):
    """Thay TOÀN BỘ dòng chi của những mục được gửi lên. Mục đã khoá thì từ chối.
    Dòng đã sinh phiếu xuất kho (stock_move_id) được giữ nguyên số lượng — xuất rồi không sửa trên phiếu."""
    theo_muc = {}
    for i, d in enumerate(cac_dong or []):
        m = d.get("section")
        if m not in MUC_CHI:
            raise HTTPException(422, {"ma": "MUC_SAI", "loi": "Dòng %d: mục %s không hợp lệ." % (i + 1, m)})
        theo_muc.setdefault(m, []).append(d)
    dat_gia = nhap_gia_chi(user.role)
    doi_ca = doi_cach_tra(user.role)          # 08/10: Bãi không quyết cách trả — giữ của dòng cũ / mặc định (_cach_tra_mac_dinh)
    # một câu cho mọi mục (02/10: trước đây một câu mỗi mục, rồi xoá và ghi lại MỌI dòng — DB ở xa, mỗi câu 10–35 ms)
    tat_ca = defaultdict(dict)
    for e in db.query(TripExpense).filter(TripExpense.trip_id == p.id).all():
        tat_ca[e.section][e.id] = e
    for m in theo_muc:
        if not duoc_sua_muc(user.role, m, muc_tt[m]):
            if duoc_sua_tien(user.role, m, muc_tt[m]):
                _ap_gia(db, p, m, theo_muc[m], user, cu=tat_ca[m])
                continue
            raise HTTPException(409, {"ma": "MUC_DA_KHOA",
                                      "loi": "Mục %s đã khoá (%s), không sửa được dòng chi." % (m, muc_tt[m])})
        cu = tat_ca[m]
        # Bãi không thấy giá nên không gửi giá: dòng cũ giữ đúng giá kế toán đã nhập (khớp theo id — _dong_tu_du_lieu `cu`).
        ban_cu = {e.id: e.sale_price for e in cu.values()}
        # Dòng đã sinh phiếu xuất kho là CHỨNG TỪ KHO — không xoá, không đổi số trên phiếu. Người
        # dùng bỏ nó khỏi danh sách gửi lên thì từ chối cả lần lưu và nói rõ dòng nào.
        # Dòng đã TRỪ THẺ cao tốc cũng vậy: số dư thẻ đã giảm thật, không xoá lặng lẽ trên phiếu.
        giu = {e.id: e for e in cu.values() if e.stock_move_id or e.card_move_id}
        da_gui = {d.get("id") for d in theo_muc[m]}
        for e in giu.values():
            if e.id not in da_gui:
                raise HTTPException(409, {"ma": "DA_XUAT_KHO" if e.stock_move_id else "DA_TRU_THE",
                                          "loi": "Dòng '%s' đã %s, không xoá được trên phiếu."
                                                 % (e.item_name or e.item_key, "xuất kho" if e.stock_move_id else "trừ vào thẻ cao tốc")})
        bo = {i for i in cu if i not in giu}             # dòng không được gửi lại → xoá ở cuối
        i = 0
        da_dung = set()
        for d in theo_muc[m]:
            i += 1
            e = giu.get(d.get("id"))
            if e:
                e.line_no = i; e.note = d.get("note")
                if doi_ca:
                    e.pay_channel = _cach_tra_gui(m, d, p.company)
                _ai_tra_dong_kho(p, e, d, cu.values())
                # dòng giữ lại trước đây không đổi "ai trả" — dòng kho xe thuê cũ ghi "chủ xe tự trả" thì bấm "EPL ứng" ở đây
                if dat_gia and "sale_price" in d and la_xuat_ban(p, e):
                    e.sale_price = _gia_ban(p, e, d)     # phụ tùng xuất kho ngay lúc khai — giá bán gõ sau, lúc kiểm
                _gan_tk(p, e, d.get("acct_code") or e.acct_code)
                continue
            # 02/10: dòng cũ gửi lại giữ đúng mã dòng — bút toán chờ (dong[].ref), phiếu chi mục V (expense_ids), sự kiện đã duyệt
            # và màn Tổng hợp thu chi bên kế toán (line_key exp:<id>) khoá theo mã này; tạo mã mới mỗi lần lưu là đứt các dây đó
            cu_e = cu.get(d.get("id")) if d.get("id") not in da_dung else None
            moi = _dong_tu_du_lieu(p, m, i, d, db, dat_gia=dat_gia, cu=cu_e)
            if not doi_ca and m in ("travel", "other"):
                moi.pay_channel = _cach_tra_mac_dinh(db, p, m, d, cu_e)
                _gan_tk(p, moi, d.get("acct_code"))
            if moi.paid_by_epl is False and la_xuat_ban(p, moi):
                # dầu / phụ tùng LẤY KHO của xe thuê luôn là xuất bán (chủ dự án 30/09, nhắc lại 02/10): lập mới hay đổi sang
                # "chủ xe tự trả" → 422. Dòng cũ vốn đã ghi vậy mà gửi nguyên thì để yên — khoá phiếu chặn và chỉ cách sửa.
                if cu_e is None or cu_e.paid_by_epl is not False or not la_xuat_ban(p, cu_e):
                    BTC.chan_kho_xe_thue_tu_tra(p, moi)
            if la_xuat_ban(p, moi):      # giá bán chỉ ở dầu, phụ tùng kho của xe thuê
                moi.sale_price = _gia_ban(p, moi, d) if (dat_gia and "sale_price" in d) else ban_cu.get(d.get("id"))
            if cu_e is not None:
                # cùng mã: chép số mới lên CHÍNH dòng đó — không xoá rồi ghi lại; ô không đổi thì không có câu UPDATE nào
                da_dung.add(cu_e.id)
                bo.discard(cu_e.id)
                for c in COT_DONG_CHI:
                    setattr(cu_e, c, getattr(moi, c))
            else:
                db.add(moi)
        for k in bo:
            db.delete(cu[k])


def _ap_gia(db, p, m, cac_dong, user, cu=None):
    """Người KIỂM mục (KT kho xăng dầu mục III, KT Chi phí mục IV–VI) nhập ĐƠN GIÁ và TIỀN TỆ cho các dòng Bãi
    đã khai, khi mục còn "đã nhập". Không thêm, không xoá, không đổi số lượng — muốn thế thì trả lại cho Bãi.
    Dòng lấy từ kho giữ giá bình quân của kho. `cu`: dòng của mục đã nạp sẵn {id: dòng} (_ap_dong_chi)."""
    if cu is None:
        cu = {e.id: e for e in db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == m).all()}
    for d in cac_dong:
        e = cu.get(d.get("id"))
        if e is None:
            raise HTTPException(409, {"ma": "CHI_SUA_GIA",
                                      "loi": "Kế toán chỉ nhập đơn giá cho dòng Bãi đã khai; thêm dòng thì trả lại cho Bãi."})
        if e.source == "kho":
            # giá vốn là bình quân kho; xe THUÊ thì KT kho xăng dầu gõ GIÁ BÁN cho chủ xe (29/09). Người gõ giá bán cũng là người
            # bấm "EPL ứng" cho dòng kho xe thuê cũ còn ghi "chủ xe tự trả" (02/10) — không cho đổi ngược lại
            _ai_tra_dong_kho(p, e, d, cu.values())
            if "sale_price" in d:
                e.sale_price = _gia_ban(p, e, d)
            continue
        if "unit_price" in d:
            gia = _so(d.get("unit_price"), "unit_price") or 0
            if gia < 0:
                raise HTTPException(422, {"ma": "SO_SAI", "loi": "Đơn giá không âm."})
            e.unit_price = gia
        if d.get("currency"):
            e.currency = _tien_te(d["currency"], "currency")
        # cách trả mục IV / VI: KT Chi phí VC đổi lúc kiểm (08/10, anh Khampla) — Bãi đã khai dòng với cách trả mặc định
        if m in ("travel", "other") and "pay_channel" in d and doi_cach_tra(user.role):
            e.pay_channel = _cach_tra_gui(m, d, p.company)
        _gan_tk(p, e, d.get("acct_code") or e.acct_code)


def _gia_ban(p, e, d):
    """Giá bán cho chủ xe: chỉ có nghĩa ở phiếu XE THUÊ, dòng dầu (29/09) hoặc phụ tùng (30/09) lấy từ KHO. Chỗ khác trống."""
    if not la_xuat_ban(p, e):
        return None
    v = _so(d.get("sale_price"), "sale_price") if d.get("sale_price") not in (None, "") else None
    if v is not None and v < 0:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Giá bán không âm."})
    return v


def _con_chay_phieu_khac(db, p, cot, gia_tri):
    """Xe / tài xế còn phiếu nào KHÁC chưa về không (rà 23/09: xe còn chuyến thứ hai mà bị trả về "rảnh")."""
    return db.query(Trip.id).filter(getattr(Trip, cot) == gia_tri, Trip.id != p.id,
                                    Trip.transport_status != "arrived").first() is not None


def _doi_trang_thai_xe_tai_xe(db, p, trang_thai_xe, trang_thai_tai_xe):
    """Nhả xe / tài xế ("available") chỉ khi họ không còn phiếu nào khác đang chạy; xe đang sửa thì
    vẫn là "đang sửa" — lệnh sửa chữa xong mới trả xe về rảnh."""
    if p.vehicle_id:
        x = db.get(Vehicle, p.vehicle_id)
        if x and x.status != "inactive":
            if trang_thai_xe != "available":
                x.status = trang_thai_xe
            elif x.status != "maintenance":
                x.status = "on_trip" if _con_chay_phieu_khac(db, p, "vehicle_id", x.id) else "available"
    if p.driver_id:
        d = db.get(Driver, p.driver_id)
        if d and d.status != "inactive":
            if trang_thai_tai_xe != "available":
                d.status = trang_thai_tai_xe
            else:
                d.status = "on_trip" if _con_chay_phieu_khac(db, p, "driver_id", d.id) else "available"


def _ghi_do(db, p, user):
    CT.ghi(db, "DO", nguon_bang="trips", nguon_id=p.id, trip=p, ngay=p.doc_date or dt.date.today(),
           doi_tuong_loai="khach", doi_tuong_ten=p.customer_name, by_user=user.full_name,
           mo_ta="Phiếu xuất xe %s · %s → %s" % (p.doc_no, p.origin or "", p.destination or ""),
           payload={"truck_no": p.truck_no, "driver_name": p.driver_name, "company": p.company})


# Tên mặt hàng theo ô "Loại hàng" — dòng hàng phiếu gom máy tự ghi (29/09). Lô hàng trong sổ kho mang đúng tên này,
# nên không dịch theo ngôn ngữ màn hình (cùng chữ với dòng hàng đang có).
TEN_LOAI_HANG = {"iron_ore": "ແຮ່ເຫຼັກ (quặng sắt)", "other_goods": "ສິນຄ້າອື່ນ (hàng khác)"}


def _dong_hang_gom(db, p, user, gd=None, loai_cu=None):
    """Phiếu GOM một mặt hàng (chủ dự án 29/09): màn phiếu không còn bảng "Hàng trên phiếu" — Loại hàng + Cân tại mỏ là
    đủ, máy ghi dòng hàng từ hai ô đó. Không có dòng hàng thì xe về tới bãi hàng không vào kho, phiếu giao không có lô
    để lấy (bẫy cũ: chỉ gõ cân tại mỏ). Phiếu gom đã có từ hai dòng hàng trở lên thì giữ bảng, không đụng.
    `loai_cu`: loại hàng trước lần sửa — đổi loại thì dòng đổi tên theo, không đổi thì giữ tên dòng đang có."""
    if p.kind != "gom":
        return
    hang = db.query(TripGoods).filter(TripGoods.trip_id == p.id, TripGoods.loai == "hang").all()
    if len(hang) > 1:
        return
    tan = round(p.weight_origin or 0, 3)
    loai = p.goods_type or "iron_ore"
    ten = hang[0].goods_name if hang and (loai_cu is None or loai_cu == loai) else TEN_LOAI_HANG.get(loai, loai)
    if hang and abs((hang[0].qty_t or 0) - tan) < 0.0005 and hang[0].goods_name == ten:
        return
    if not hang and tan <= 0:
        return
    KH.dat_dong_hang(db, p, [{"loai": "hang", "goods_name": ten, "qty_t": tan, "note": hang[0].note if hang else None}]
                     if tan > 0 else [], user, gd)


@router.post("/api/trips")
def lap_phieu(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    if user.role not in ("yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc lập phiếu xuất xe."})
    loai_do = (data.get("kind") or "giao").strip()
    if loai_do not in LOAI_DO:
        raise HTTPException(422, {"ma": "LOAI_DO_SAI", "loi": "Loại phiếu phải là 'gom' (đi lấy hàng) hoặc 'giao' (đi giao hàng)."})
    p = Trip(doc_no=str(data.get("doc_no") or _so_phieu_moi(db, loai_do)).strip(), kind=loai_do, created_by=user.full_name)
    if db.query(Trip).filter(Trip.doc_no == p.doc_no).first():
        raise HTTPException(409, {"ma": "TRUNG_SO", "loi": "Số phiếu %s đã có." % p.doc_no})
    # Tỷ giá mặc định lấy từ bảng tỷ giá, rồi khoá vào phiếu
    tg = {r.code: r.rate_to_lak for r in db.query(ExchangeRate).all()}
    p.rate_usd, p.rate_thb = tg.get("USD", 22000), tg.get("THB", 700)
    p.rate_vnd, p.rate_cny = tg.get("VND", 1.2), tg.get("CNY", 3000)
    _ap_truong(db, p, data, user)
    _chan_phieu_trang(p)
    # C4.2 (anh Khampla): phí, ngưỡng tấn, mức trừ quá tải, tiền thuê là ĐIỀU KHOẢN của từng chủ xe —
    # ô nào người lập không gửi thì lấy theo hồ sơ chủ xe, không lấy hằng số chung.
    if p.company == "joint" and p.owner_id:
        o = db.get(Owner, p.owner_id)
        if o:
            # ô không gửi — hoặc gửi mà không được nhận (Bãi không nhập tiền) — thì theo hồ sơ chủ xe
            if p.fee_pct is None: p.fee_pct = o.fee_pct
            if p.over_limit_t is None: p.over_limit_t = o.over_limit_t
            if p.over_price is None: p.over_price = o.over_price
            if not p.hire_ccy: p.hire_ccy = o.hire_ccy
    db.add(p)
    try:
        db.flush()
    except IntegrityError:
        # hai người lưu cùng lúc cùng số gợi ý: lần kiểm ở trên cùng lọt, DB chặn ở cột unique — báo 409 rõ (rà 01/10:
        # trước đây văng 500)
        db.rollback()
        raise HTTPException(409, {"ma": "TRUNG_SO", "loi": "Số phiếu %s vừa có người khác lưu trước — bấm Lưu lại để lấy số mới." % p.doc_no})
    muc_tt = {m: "wait" for m in MUC}
    for m in MUC:
        db.add(TripSection(trip_id=p.id, section=m, status="wait"))
    dong = list(data.get("expenses") or [])
    # BOT thuộc ĐƯỜNG: tuyến có phí cao tốc mà phiếu chưa có dòng x_toll → tự thêm
    if p.route_id:
        r = db.get(Route, p.route_id)
        if r and (r.toll_lak or 0) > 0 and not any(d.get("item_key") == "x_toll" for d in dong):
            dong.append({"section": "travel", "item_key": "x_toll", "qty": 1, "unit_price": r.toll_lak, "currency": "LAK"})
    _ap_dong_chi(db, p, dong, user, muc_tt)
    # Phiếu giao lấy hàng của lô: sổ kho hàng ở trang kế toán (đợt 5) — xuất ở bên đó trong cùng lần lưu; bên này
    # lưu hỏng thì phần xuất bên đó được trả lại.
    with KK.GiaoDichKho(db, user) as gd:
        KH.dat_dong_hang(db, p, data.get("goods"), user, gd)
        if not data.get("goods"):
            _dong_hang_gom(db, p, user, gd)            # phiếu gom: dòng hàng từ Loại hàng + Cân tại mỏ (29/09)
        _doi_trang_thai_xe_tai_xe(db, p, "on_trip", "on_trip")
        _ghi_log(db, p, user, "a_create")
        db.flush(); _ghi_do(db, p, user)
    return xuat_phieu(db, p, vai=user.role)


VAI_SAU_KHOA = ("acct", "expacct", "rev", "treasury", "cash", "fuel", "admin")   # vai còn được thao tác khi phiếu đã khoá


def _chan_khoa(p, user):
    """Bước 14: phiếu đã khoá thì Bãi và tài xế không ghi thêm gì; kế toán, quỹ, kho vẫn kiểm và chi tiếp."""
    if p.locked and user.role not in VAI_SAU_KHOA:
        raise HTTPException(409, {"ma": "DA_KHOA", "loi": "Phiếu %s đã khoá (%s). Muốn sửa phải nhờ kế toán mở khoá." % (p.doc_no, p.locked_by or "")})


@router.put("/api/trips/{tid}")
def sua_phieu(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    db.expire_on_commit = HET_HAN_SAU_COMMIT
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _chan_khoa(p, user)
    truoc_khoa = BTC.dau_khoa(db, p)        # phiếu đang khoá: dấu các dòng đã vào bút toán khoá phiếu (02/10)
    muc_tt = {m: s.status for m, s in _muc_cua(db, p).items()}
    # ---- Luật hàng và kho (hai DO):
    #  · Loại phiếu không đổi được nữa khi đã có dòng hàng hay dòng sổ kho — đổi là phiếu gom mang dòng xuất kho.
    #  · Phiếu GOM đã nhập kho thì dòng hàng và hai ô cân ĐÓNG: sổ kho đã ghi theo số đó, sửa phiếu mà không
    #    sửa sổ thì hai bên nói hai số. Muốn khác thì xoá phiếu giao đã lấy hàng rồi làm lại, hoặc lập phiếu
    #    điều chỉnh — không âm thầm sửa lịch sử kho.
    #  · Phiếu GIAO đã tới nơi vẫn sửa được (cân cuối gõ nhầm là chuyện thường), nhưng sửa xong máy tính lại
    #    dòng hao hụt ngay bên dưới.
    #  (Sổ kho hàng ở trang kế toán từ đợt 5. Dòng sổ của một phiếu luôn sinh từ dòng hàng của chính nó, nên "có dòng
    #  hàng" đã bao "có dòng sổ"; còn "đã nhập kho" thì hỏi bên đó — chỉ khi phiếu gom đụng tới hàng / cân.)
    hang_cu = db.query(TripGoods).filter(TripGoods.trip_id == p.id).all()
    co_dong_hang = bool(hang_cu)
    if "kind" in data and (data["kind"] or p.kind) != p.kind and co_dong_hang:
        raise HTTPException(409, {"ma": "KHONG_DOI_LOAI",
                                  "loi": "Phiếu đã có dòng hàng hoặc đã ghi sổ kho, không đổi loại gom/giao được nữa."})
    # bản phiếu gửi lên mang cả ô cũ: chỉ hỏi kho tạm "đã nhập kho chưa" khi cân / dòng hàng THẬT SỰ đổi (02/10 — trước đây mỗi lần
    # lưu phiếu gom có hàng là một lời gọi kho tạm, kể cả khi chỉ bấm Gửi kiểm mục IV)
    hang_doi = "goods" in data and not KH.hang_khong_doi(db, p, data["goods"], cu=hang_cu)
    can_doi = any(k in data and _doi_so(data[k], getattr(p, k), k) for k in ("weight_origin", "weight_dest"))
    if (hang_doi or can_doi) and KH.da_nhap_kho(db, p):
        raise HTTPException(409, {"ma": "HANG_DA_NHAP_KHO",
                                  "loi": "Hàng của phiếu gom này đã vào kho bãi; dòng hàng và cân không sửa được nữa."})
    if "doc_no" in data and str(data["doc_no"]).strip() != p.doc_no:
        if db.query(Trip).filter(Trip.doc_no == str(data["doc_no"]).strip()).first():
            raise HTTPException(409, {"ma": "TRUNG_SO", "loi": "Số phiếu đã có."})
    loai_cu = p.goods_type
    _ap_truong(db, p, data, user, muc_tt)
    if "vehicle_id" in data or "driver_id" in data or "driver_name" in data:
        _chan_phieu_trang(p)        # sửa mà xoá xe / tài xế thì cũng chặn; sửa mục khác trên phiếu cũ thì không vướng
    if "expenses" in data:
        _ap_dong_chi(db, p, data["expenses"], user, muc_tt)
    if p.company != "joint" and sa_inspect(p).attrs.company.history.deleted:
        # xe nhà: xuất nội bộ, không có giá bán — dọn khi phiếu vừa đổi từ xe thuê sang. Giá bán trên dòng xe nhà không vào phép
        # tính nào (tinh_toan.gia_dong chỉ đọc ở xe thuê). Trước 02/10 câu UPDATE hàng loạt này chạy MỖI lần lưu — thêm một câu
        # SQL, và sửa hàng loạt làm bộ đệm báo cáo tính lại MỌI tháng (dem_bao_cao: khoá '*')
        for e in db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.sale_price.isnot(None)):
            e.sale_price = None
    # Sau khoá (chủ dự án 02/10): dòng kho, dòng ghi nợ nhà cung cấp đã vào bút toán khoá phiếu — không ai sửa được (kể cả KT
    # kho xăng dầu, KT Chi phí đang được thao tác phiếu đã khoá, kể cả Sếp) → 409 DA_KHOA; mở khoá rồi mới sửa
    BTC.chan_sua_sau_khoa(db, p, truoc_khoa)
    # Phiếu gom không gửi dòng hàng (màn phiếu bỏ bảng từ 29/09; bản màn cũ gửi bảng rỗng) → máy ghi dòng từ Loại hàng +
    # Cân tại mỏ. Chỉ khi mục II còn sửa được và xe chưa về tới bãi (về rồi là hàng đã vào kho theo dòng cũ).
    gom_tu_ghi = p.kind == "gom" and not data.get("goods")
    with KK.GiaoDichKho(db, user) as gd:
        if gom_tu_ghi:
            if ({"weight_origin", "goods_type", "goods"} & data.keys()) and p.transport_status != "arrived" \
                    and duoc_sua_muc(user.role, "trans", muc_tt["trans"]):
                _dong_hang_gom(db, p, user, gd, loai_cu)
        elif hang_doi:              # dòng hàng gửi lại y nguyên: không xoá / ghi lại, không gọi kho tạm (02/10)
            if not duoc_sua_muc(user.role, "trans", muc_tt["trans"]) and user.role != "admin":
                raise HTTPException(409, {"ma": "MUC_DA_KHOA", "loi": "Mục II đã khoá; phải trả lại mới sửa được dòng hàng."})
            KH.dat_dong_hang(db, p, data["goods"], user, gd, so_sanh=False)
        # Phiếu giao đã tới nơi: dòng hàng hay cân cuối vừa đổi thì dòng hao hụt phải tính lại theo số mới.
        if p.kind == "giao" and p.transport_status == "arrived" and (hang_doi or can_doi):
            KH.ghi_hao_hut_giao(db, p)
        # 05/10: tờ kho hàng theo DO, idempotent — DO đã có dòng sổ (nhập / xuất trước 05/10) mà thiếu PNK_HH / PXK_HH thì lưu lại là sinh
        if co_dong_hang or hang_doi:
            KK.dam_bao_to_hang(db, user, p)
        _ghi_log(db, p, user, "a_save")
    return xuat_phieu(db, p, vai=user.role)


# ---------------------------------------------------------------- duyệt từng mục
def _chan_chua_cap_theo_de_nghi(db, p, dong=None):
    """Mọi lần xuất dầu kho phải có PHIẾU ĐỀ NGHỊ đã cấp (chủ dự án 30/09): trước đây ghi sổ mục III tự xuất kho dòng dầu
    chưa cấp — dầu rời kho không có tờ đề nghị nào. Nay dòng dầu kho EPL ứng chưa được thủ kho cấp theo phiếu đề nghị
    xuất nhiên liệu thì chặn ghi sổ, nói rõ dòng nào. `dong`: dòng chi đã nạp sẵn (06/10 — ghi sổ III nạp một lần)."""
    thieu = [(i, e) for i, e in enumerate([e for e in (dong if dong is not None else _dong_chi(db, p)) if e.section == "fuel"], 1)
             if e.source == "kho" and e.paid_by_epl and (e.qty or 0) > 0 and not e.stock_move_id]
    if thieu:
        # 06/10: kho ở hệ anh Tune — thủ kho cấp trên Web kế toán (màn Cấp phát / kho tạm 8031 đã bỏ 05/10)
        raise BTC.loi3(409, "CHUA_CAP_THEO_DE_NGHI",
                       "Mục III: %s lấy từ kho chưa được cấp theo phiếu đề nghị xuất kho nhiên liệu. Bãi in phiếu đề nghị, thủ kho cấp "
                       "dầu trên Web kế toán (Quản lý kho → Cấp dầu theo phiếu đề nghị), rồi mới ghi sổ mục III."
                       % ", ".join("dòng %d (%s lít)" % (i, _gon(e.qty)) for i, e in thieu),
                       "ໜ້າ III: %s ເອົາຈາກສາງ ຍັງບໍ່ໄດ້ເບີກຕາມໃບສະເໜີເບີກນໍ້າມັນ. ສະໜາມພິມໃບສະເໜີ, ຜູ້ຮັກສາສາງເບີກນໍ້າມັນຢູ່ເວັບບັນຊີ "
                       "(ຈັດການສາງ → ເບີກນໍ້າມັນຕາມໃບສະເໜີ), ແລ້ວຈຶ່ງບັນທຶກບັນຊີໜ້າ III."
                       % ", ".join("ແຖວ %d (%s ລິດ)" % (i, _gon(e.qty)) for i, e in thieu),
                       "Section III: %s taken from the depot has not been issued against the fuel stock-out request. The yard prints "
                       "the request, the storekeeper issues the fuel on the accounting Web (Warehouse → Issue fuel by request), then "
                       "book section III." % ", ".join("line %d (%s L)" % (i, _gon(e.qty)) for i, e in thieu))


def muc_iii_co_tien(dong):
    """Mục III còn khoản QUỸ phải chi không (G11, 06/10): dòng EPL ứng không lấy kho — dầu mua trạm ngoài trả tiền mặt (vào tạm
    ứng) hoặc ghi nợ trạm. Mọi dòng EPL ứng đều LẤY KHO thì không có đồng nào qua tay thủ quỹ VC: bước "Chi" của họ chỉ đổi
    trạng thái, không sinh chứng từ — việc chờ đếm mãi không ai làm."""
    return any(d.section == "fuel" and d.paid_by_epl and d.source != "kho" and (d.qty or 0) > 0 for d in dong)


def muc_iv_khong_tien_mat(p, dong):
    """Mục IV KHÔNG có đồng tạm ứng nào cho quỹ chi (06/10, điều phối — ví dụ G4-0006): cả phiếu không có dòng tiền mặt tài xế cầm
    (la_tien_mat_tai_xe — tờ tạm ứng gói cả III dầu mua dọc đường, IV, VI), mọi khoản EPL ứng của mục IV là "trả cùng lương" / nợ
    nhà cung cấp / thẻ. Khi đó không có tờ tạm ứng, không có phiếu chi "Chi trước" bên kế toán (chi_tune.gui_sau_ghi_so thôi), nên
    trước đây mục IV kẹt "đã ghi sổ · chờ chi" mãi — khoản cùng lương do kế toán Web lập phiếu chi lương theo DO, trang này không đọc
    lại."""
    return not _dong_tam_ung(p, dong)


def _qua_chi_ton(db, user):
    """Dọn một lần — mục III đã ghi sổ mà chỉ lấy kho (G11) và mục IV đã ghi sổ mà không có tạm ứng tiền mặt (cùng lương) TRƯỚC khi có
    luật tự qua bước Chi → "đã chi" (không còn nằm trong việc chờ của thủ quỹ VC / quỹ tiền mặt). Mục IV đã có phiếu chi tạm ứng bên
    kế toán (chi_tune) thì để luồng đó lo. Trả [(số DO, mục)]."""
    from models import ChiTune
    ds = db.query(TripSection).filter(TripSection.section.in_(("fuel", "travel")), TripSection.status == "booked").all()
    dong = defaultdict(list)
    for e in db.query(TripExpense).filter(TripExpense.trip_id.in_(list({s.trip_id for s in ds}) or [""])):
        dong[e.trip_id].append(e)
    co_chi = {t for (t,) in db.query(ChiTune.trip_id).filter(ChiTune.trip_id.in_(list({s.trip_id for s in ds}) or [""]),
                                                            ChiTune.status != "huy")}
    ra = []
    for s in ds:
        p = db.get(Trip, s.trip_id)
        if s.section == "fuel" and not muc_iii_co_tien(dong[s.trip_id]):
            s.status = "paid"
            _ghi_log(db, p, user, "sec_fuel:pay_auto")
            ra.append((p.doc_no, "III"))
        elif s.section == "travel" and s.trip_id not in co_chi and muc_iv_khong_tien_mat(p, dong[s.trip_id]):
            s.status = "paid"
            _ghi_log(db, p, user, "sec_travel:pay_luong")
            ra.append((p.doc_no, "IV"))
    db.commit()
    return ra


@router.post("/api/muc/qua-chi-ton")
def qua_chi_ton(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Dọn một lần (06/10) — CHỈ Sếp: xem _qua_chi_ton. Gọi lại không đổi gì (idempotent). Trả các DO đã chuyển theo mục."""
    if user.role != "admin":
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Sếp dọn mục đã ghi sổ còn treo bước Chi."})
    ra = _qua_chi_ton(db, user)
    return {"so_do": len(ra), "do": sorted(d for d, m in ra if m == "III"), "do_iv": sorted(d for d, m in ra if m == "IV")}


@router.post("/api/trips/{tid}/sections/{muc}/{hanh_dong}")
def duyet_muc(tid: str, muc: str, hanh_dong: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    db.expire_on_commit = HET_HAN_SAU_COMMIT
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _chan_khoa(p, user)
    if p.locked and hanh_dong == "return" and user.role != "admin":
        # Trả lại mục là trả cho người NHẬP sửa (Bãi, tổ sửa chữa) — họ không ghi được vào phiếu đã khoá, nên trả lại chỉ làm mục
        # kẹt "chưa gửi" không ai sửa (rà giao diện 01/10). Muốn sửa thì KT Thu/Chi mở khoá phiếu trước; Sếp vẫn làm được.
        raise HTTPException(409, {"ma": "DA_KHOA", "loi": "Phiếu %s đã khoá — mở khoá phiếu rồi mới trả lại mục để sửa." % p.doc_no})
    ds = _muc_cua(db, p)
    s = ds[muc] if muc in ds else None
    if s is None:
        raise HTTPException(422, {"ma": "MUC_SAI", "loi": "Không có mục %s." % muc})
    # Hỏi QUYỀN trước, hỏi nội dung sau: vai không được đụng mục này thì phải nghe "không có quyền",
    # chứ nghe "mục còn trống" là câu trả lời của người khác — họ sẽ đi nhập cho đầy rồi vẫn bị chặn.
    moi_trang_thai = chuyen_muc(user.role, muc, s.status, hanh_dong)
    if muc == "travel" and hanh_dong == "pay" and user.role != "admin" and CHI.chi_o_ke_toan():
        raise HTTPException(409, {"ma": "CHI_O_KE_TOAN", "loi": CHI.cau_chan_chi(db, p)})
    if muc == "travel" and hanh_dong == "pay" and CHI.chi_o_ke_toan():
        # Sếp chi tay: thủ quỹ bên kế toán đã chi rồi thì chỉ nhận "đã chi" (không ra thêm tờ); còn chờ thì RÚT phiếu chi bên đó
        # trước, không để thủ quỹ chi lần nữa cho khoản Sếp vừa chi
        r = CHI.cua_phieu(db, p, cap_nhat=True)
        if r is not None and r.status == "da_chi":
            return xuat_phieu(db, p, vai=user.role)
        CHI.rut(db, trip_id=p.id)
    if muc in CMT.MUC and hanh_dong == "pay" and CHI.chi_o_ke_toan():
        # Chi mục V / VI ở hệ kế toán (01/10): khoản quỹ trả ngay thành phiếu chi "Chi khác" bên đó lúc KT Chi phí ghi sổ;
        # thủ quỹ chi và ghi sổ ở đó, trang này tự ghi "đã chi". Hỏi lại trước: bên đó đã ghi sổ hết thì mục đã "đã chi".
        lan = CMT.cua_phieu(db, p, muc, cap_nhat=True)
        if s.status == "paid":
            return xuat_phieu(db, p, vai=user.role)
        if CMT.con_phai_chi(db, p, muc, recs=lan):
            if user.role != "admin":
                raise HTTPException(409, {"ma": "CHI_O_KE_TOAN", "loi": CMT.cau_chan_chi(db, p, muc, lan)})
            CMT.rut_cho(db, p, muc)        # Sếp chi tay: rút phiếu chi chờ bên đó, không để thủ quỹ chi lần nữa
    if muc in MUC_CHI and hanh_dong == "send" and not any(d.section == muc for d in _dong_chi(db, p)):
        raise HTTPException(409, {"ma": "MUC_TRONG", "loi": "Mục %s chưa có dòng chi nào để gửi kiểm." % muc})
    if muc in MUC_CHI and hanh_dong == "verify":
        # Dòng EPL trả mà đơn giá 0 (bấm tay 23/09: 100 lít dầu kho giá 0) đi hết chuỗi duyệt, tới ghi sổ sinh tờ
        # 0 LAK có định khoản — sổ kế toán từ chối, còn 100 lít thì rời kho không mang tiền. Người nhập GIÁ là
        # người KIỂM (anh Khampla A2, C5.1: Bãi không thấy tiền), nên chặn lúc KIỂM, không chặn Bãi lúc gửi.
        dong_muc = [d for d in _dong_chi(db, p) if d.section == muc]
        thieu = [(i, d) for i, d in enumerate(dong_muc, 1) if d.paid_by_epl and (d.qty or 0) > 0 and (d.unit_price or 0) <= 0]
        if muc in ("fuel", "repair") and p.company == "joint":
            # xe thuê: dầu / phụ tùng lấy kho là xuất bán — EPL ứng và có giá bán (luật chung với khoá phiếu, đủ ba tiếng)
            BTC.chan_xuat_ban(p, _dong_chi(db, p), muc=muc, luc="kiem")
        if thieu:
            kho = [i for i, d in thieu if d.source == "kho"]
            raise HTTPException(409, {"ma": "THIEU_DON_GIA", "loi": "Mục %s: %s chưa có đơn giá — nhập đơn giá rồi kiểm lại.%s" % (
                _TEN_MUC.get(muc, muc), ", ".join("dòng %d (số lượng %s)" % (i, _gon(d.qty)) for i, d in thieu),
                " Dòng lấy từ kho chưa có giá vì kho đó chưa có phiếu nhập nào có giá." if kho else "")})
    # từ 30/09 ghi sổ mục III không xuất kho nữa (dầu kho chỉ rời kho theo phiếu đề nghị đã cấp); vẫn lưu trong GiaoDichKho
    # như mọi lần lưu có thể đụng trang kế toán
    tu_qua_chi = False
    with KK.GiaoDichKho(db, user):
        s.status = moi_trang_thai
        if muc == "fuel" and hanh_dong == "book":
            dong_iii = _dong_chi(db, p)
            _chan_chua_cap_theo_de_nghi(db, p, dong_iii)
            # G11 (06/10): mọi dòng EPL ứng đều lấy kho (dầu đã cấp theo phiếu đề nghị) → không có tiền cho thủ quỹ VC chi: mục tự
            # qua bước Chi ngay khi ghi sổ, không xếp vào việc chờ của họ. Còn dòng tiền mặt / ghi nợ trạm thì giữ như cũ.
            tu_qua_chi = not muc_iii_co_tien(dong_iii)
            if tu_qua_chi:
                s.status = "paid"
        if muc == "travel" and hanh_dong == "book":
            # Phí cầu đường trả bằng thẻ: ghi sổ là lúc trừ thẻ, đúng như dòng xuất kho nhiên liệu ở trên.
            THE.tru_the_theo_phieu(db, p, user)
            # 06/10 (điều phối, G4-0006): không có tạm ứng tiền mặt nào (mục IV chỉ "trả cùng lương" / nợ NCC / thẻ) → không có phiếu
            # chi tạm ứng cho quỹ chi: mục IV tự qua bước Chi lúc ghi sổ ("Chi ở kế toán — cùng lương"), không xếp vào việc chờ của quỹ
            # (như G11 mục III lấy kho). Có tiền mặt thì giữ như cũ: "đã chi" khi thủ quỹ bên kế toán ghi sổ phiếu chi tạm ứng.
            if muc_iv_khong_tien_mat(p, _dong_chi(db, p)):
                s.status = "paid"
                tu_qua_chi = True
        if muc in CMT.MUC and hanh_dong == "book" and CHI.chi_o_ke_toan():
            # 06/10 (chạy thử kịch bản CA-6, A4 / A7): mục V / VI không có khoản QUỸ trả ngay (chỉ lấy kho, nợ NCC, chủ xe tự trả)
            # → không có phiếu chi cho thủ quỹ: tự qua bước Chi lúc ghi sổ như mục III lấy kho / mục IV cùng lương. Trước đây treo
            # «Đã ghi sổ · chờ chi» mãi. Còn khoản quỹ trả ngay / phiếu chi đang chờ thì giữ như cũ (đồng bộ nền đổi «đã chi»).
            if not CMT.con_phai_chi(db, p, muc) and not any(r.status in ("da_gui", "loi") for r in CMT.cac_lan(db, p.id, muc)):
                s.status = "paid"
                tu_qua_chi = True
        if hanh_dong == "pay" and muc == "travel":
            # Mục IV có HAI đường thành "đã chi": quỹ quét QR phiếu tạm ứng (sinh PC_TU ở phieu_linh.py), hoặc quỹ bấm
            # thẳng "Chi tiền" ở đây. Đường thứ hai trước đây không sinh tờ nào — bấm tay 23/09 chi 2.183.500 LAK mà sổ
            # kế toán không hề biết. Nay sinh PC_TU như đường QR. Hai đường tự loại nhau: đã chi rồi thì đường kia là
            # sai bước (chuyen_muc), nên không thể ra hai tờ. Dòng trả bằng THẺ cao tốc không phải tiền mặt → không tính.
            # chỉ phần TIỀN MẶT tài xế cầm đi (cách trả tiền mặt — Excel anh Khampla 29/09): khoản trả cùng lương, ghi nợ
            # nhà cung cấp, trừ thẻ không qua tay quỹ lúc xe đi. Cùng luật với phiếu tạm ứng (la_tien_mat_tai_xe).
            # Rà định khoản 30/09: lấy ĐÚNG bộ dòng của tờ tạm ứng (mục III dầu mua dọc đường, IV, VI — la_tien_mat_tai_xe),
            # không chỉ mục IV. Trước đây đường này chi mục IV mà vẫn đánh dấu cả tờ tạm ứng "đã cấp": sổ ghi ra ít hơn số
            # tiền tài xế cầm đi, còn Tất toán thì đếm "đã ứng" theo tờ tạm ứng — hai bên lệch nhau đúng phần mục III, VI.
            dong = [d for d in _dong_chi(db, p) if la_tien_mat_tai_xe(d, p.company)]
            tong = sum(tien_dong(p, d) for d in dong)
            # Tờ tạm ứng (PTU) của chuyến thành "đã cấp" luôn: Tất toán đếm "đã ứng" theo tờ này, và quét QR ở Cấp phát
            # sau đó thì báo đã cấp — không ra hai lần chi (29/09: chi thẳng ở đây trước kia để tờ PTU "chờ" mãi).
            from routes.phieu_linh import dam_bao_tam_ung
            v = dam_bao_tam_ung(db, p, user)
            if v is not None and v.status == "cho":
                v.status, v.granted_by, v.granted_at = "da_cap", user.full_name, dt.datetime.utcnow()
            if v is not None:
                tong = v.amount_lak or 0            # đúng số trên tờ tạm ứng — cùng số đường quét QR ghi
            if tong > 0:
                CT.ghi(db, "PC_TU", nguon_bang="trip_sections", nguon_id="%s:travel" % p.id, trip=p, ngay=dt.date.today(),
                       phuong_thuc="cash", doi_tuong_loai="tai_xe", doi_tuong_ten=p.driver_name, tien=tong, tien_te="LAK",
                       section="travel", by_user=user.full_name, mo_ta="Chi mục IV đi đường phiếu %s" % p.doc_no,
                       payload={"truck_no": p.truck_no, "driver_id": p.driver_id, "hinh_thuc": hinh_thuc(p, "tam_ung"),
                                "owner_id": p.owner_id, "owner_name": p.owner_name,
                                "lines": [{"item": d.item_key or d.item_name, "qty": d.qty, "unit_price": d.unit_price,
                                           "currency": d.currency, "acct_code": TK.tk_dong(p.company, d)} for d in dong]})
        if hanh_dong == "pay" and muc in ("repair", "other"):
            # Quỹ chi các khoản của mục này: khoản mua ngoài / chi khác. Dòng lấy kho đã có PXK_PT riêng.
            # Rà định khoản 30/09 — chỉ những dòng QUỸ TRẢ NGAY bằng tiền mặt. Bỏ: dòng tiền mặt tài xế đã cầm đi theo
            # tờ tạm ứng (đã có PC_TU — trước đây mục VI bị chi hai lần), dòng trả cùng lương, dòng ghi nợ nhà cung cấp /
            # trừ thẻ, và dòng Theo dõi NCC đã tính là nợ nhà cung cấp (ví dụ lốp — Excel: ຕິດໜີ້ຜູ້ສະໜອງ ຈ່າຍເປັນງວດ).
            # Mục VI không còn dòng nào như thế: mỗi dòng hoặc tiền mặt theo tờ tạm ứng, hoặc trả cùng lương, hoặc ghi nợ NCC.
            # Từ 01/10 các dòng này chi ở hệ kế toán (services/chi_muc_tune.py) — tới đây chỉ khi chi trên trang điều xe
            # (EPL_CHI_TAM_UNG=tai_cho) hoặc Sếp chi tay; dòng đã nằm trong phiếu chi bên kế toán đã ghi sổ thì không chi lại.
            dong = CMT.con_phai_chi(db, p, muc) if CHI.chi_o_ke_toan() else CMT.dong_quy_chi(db, p, muc)
            tong = sum(tien_dong(p, d) for d in dong)
            if tong > 0:
                CT.ghi(db, "PC_SC", nguon_bang="trip_sections", nguon_id="%s:%s" % (p.id, muc), trip=p, ngay=dt.date.today(), phuong_thuc="cash",
                       doi_tuong_loai="tai_xe", doi_tuong_ten=p.driver_name, tien=tong, tien_te="LAK", section=muc,
                       by_user=user.full_name, mo_ta="Chi mục %s phiếu %s" % ({"repair": "V sửa chữa", "other": "VI khác"}[muc], p.doc_no),
                       payload={"lines": [{"item": d.item_key or d.item_name, "qty": d.qty, "unit_price": d.unit_price,
                                           "currency": d.currency, "acct_code": TK.tk_dong(p.company, d)} for d in dong]})
        _ghi_log(db, p, user, "sec_%s:%s" % (muc, hanh_dong))
        if tu_qua_chi:
            # nhật ký nói rõ vì sao tự qua bước Chi: mục III chỉ lấy kho (G11) · mục IV không có tạm ứng tiền mặt (cùng lương)
            _ghi_log(db, p, user, "sec_travel:pay_luong" if muc == "travel" else "sec_%s:pay_auto" % muc)
    if muc == "travel" and hanh_dong == "book":
        # ghi sổ mục IV xong → phiếu chi "Chi trước" bên hệ kế toán (chưa ghi sổ). Hỏng thì lỗi nằm trên tờ tạm ứng, gửi lại
        # ở màn Phiếu đề nghị chi; ghi sổ mục IV vẫn giữ — tài xế chỉ chưa xuất phát được cho tới khi thủ quỹ chi.
        CHI.gui_sau_ghi_so(db, p, user)
    if muc in CMT.MUC and hanh_dong == "book":
        # ghi sổ mục V / VI xong → phiếu chi "Chi khác" bên hệ kế toán cho khoản quỹ trả ngay (nếu có). Hỏng thì lỗi nằm trên
        # bản ghi, KT Chi phí gửi lại ở màn Phiếu đề nghị chi; ghi sổ mục vẫn giữ.
        CMT.gui_sau_ghi_so(db, p, muc, user)
    if muc in CMT.MUC and hanh_dong == "unlock":
        CMT.rut_cho(db, p, muc)            # Sếp mở khoá mục: phiếu chi chờ bên kế toán theo số cũ rút đi
        db.commit()
    return xuat_phieu(db, p, vai=user.role)


# ---------------------------------------------------------------- diễn biến trên đường
@router.get("/api/trips/{tid}/events")
def ds_su_kien(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if p:
        _cua_tai_xe(db, p, user)      # 07/10: tài xế chỉ đọc diễn biến phiếu của mình
    return [_xuat_su_kien(e) for e in db.query(TripEvent).filter(TripEvent.trip_id == tid).order_by(TripEvent.ts).all()]


@router.post("/api/trips/{tid}/events")
def ghi_su_kien(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bãi ghi diễn biến khi tài xế gọi về: tới điểm X · sự cố · sửa xe · ghi chú.

    SỬA XE trên đường sinh ngay một dòng chi vào MỤC V của phiếu:
      · lấy phụ tùng từ kho (source=kho, part_id) → trừ tồn kho ngay, định khoản …/371;
      · mua ngoài / garage (source=mua)            → công nợ nhà cung cấp, định khoản …/402.
    Mục V đang ở bước sau "đã nhập" thì quay về "đã nhập" để kế toán kiểm lại — có chi mới thì phải kiểm lại.
    """
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    # Diễn biến (tới điểm · sự cố · ghi chú) là việc của Bãi; nhưng DÒNG CHI SỬA CHỮA kèm theo là tiền
    # của mục V, nên phải do TỔ SỬA CHỮA khai (anh Khampla C1.2) — họ mới biết lấy kho hay ra gara.
    if data.get("repair"):
        if user.role not in ("repair", "admin"):
            raise HTTPException(403, {"ma": "KHONG_CO_QUYEN",
                                      "loi": "Khoản sửa chữa do tổ sửa chữa Thà Bốc khai, không phải vai %s." % user.role})
    elif user.role not in ("yard", "repair", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc ghi diễn biến trên đường."})
    if p.finance_status == "paid":
        raise HTTPException(409, {"ma": "PHIEU_DA_XONG", "loi": "Phiếu đã thu tiền xong, không ghi thêm diễn biến."})
    kind = data.get("kind")
    if kind not in SU_KIEN:
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "kind phải là %s." % ", ".join(SU_KIEN)})
    truoc_khoa = BTC.dau_khoa(db, p)        # phiếu đã khoá: thêm phụ tùng kho / khoản ghi nợ là lệch bút toán khoá (02/10)
    e = TripEvent(trip_id=p.id, kind=kind, note=(data.get("note") or "").strip() or None, by_user=user.full_name)
    diem = _diem_tuyen(db, p)
    if data.get("stop_seq") not in (None, ""):
        seq = int(data["stop_seq"])
        if diem and not any(d["seq"] == seq for d in diem):
            raise HTTPException(422, {"ma": "DIEM_SAI", "loi": "Tuyến không có điểm số %d." % seq})
        e.stop_seq = seq
    if kind == "arrive_stop":
        if e.stop_seq is None:
            raise HTTPException(422, {"ma": "THIEU_DIEM", "loi": "Tới điểm nào? Cần stop_seq."})
        if p.transport_status == "dispatched":
            p.transport_status = "transit"       # đã tới một điểm là đã lăn bánh
    if kind in ("incident", "repair"):
        lt = data.get("incident_type") or ("breakdown" if kind == "repair" else "other")
        if lt not in LOAI_SU_CO:
            raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "incident_type phải là %s." % ", ".join(LOAI_SU_CO)})
        e.incident_type = lt
    db.add(e); db.flush()
    rut_chi = False

    # Lấy phụ tùng từ kho = trừ tồn bên trang kế toán; cả lần lưu này đi trong GiaoDichKho: bên này hỏng ở đâu thì lần
    # xuất bên kia được huỷ, hai bên không lệch. Trang kế toán tắt → 503, không lưu được (chặn và báo rõ, 28/09).
    with KK.GiaoDichKho(db, user) as gd:
        sua = data.get("repair")
        if sua:
            source = sua.get("source")
            if source not in ("kho", "mua"):
                raise HTTPException(422, {"ma": "NGUON_SAI", "loi": "Sửa xe phải ghi nguồn: kho (xuất kho) hay mua (mua ngoài)."})
            qty = _so(sua.get("qty"), "qty") or 1
            gia = _so(sua.get("unit_price"), "unit_price")
            part = None
            if source == "kho":
                part = db.get(Part, sua.get("part_id") or "")     # bản chép danh mục — tồn và giá ở trang kế toán
                if not part:
                    raise HTTPException(422, {"ma": "THIEU_PHU_TUNG", "loi": "Lấy từ kho thì phải chọn phụ tùng."})
                gia = KK.gia_phu_tung(db, part.id)                   # lấy kho: giá bình quân của kho (30/09)
            if gia is None:
                raise HTTPException(422, {"ma": "THIEU_GIA", "loi": "Mua ngoài thì phải ghi đơn giá."})
            so_dong = db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "repair").count()
            dong = TripExpense(trip_id=p.id, section="repair", line_no=so_dong + 1,
                               item_key=(sua.get("item_key") or None) if not part else None,
                               item_name=(sua.get("item_name") or (part.name if part else None)),
                               qty=qty, unit_price=gia,
                               # lấy kho: giá là bình quân kho bằng Kíp → tiền của dòng luôn LAK (trước đây theo ô người dùng
                               # chọn, VND thì tờ xuất kho phụ tùng nhân tỷ giá VND với giá Kíp — kiểm kê API kho 30/09)
                               currency="LAK" if part else str(sua.get("currency") or "LAK").upper(),
                               paid_by_epl=bool(sua.get("paid_by_epl", True)), source=source, part_id=part.id if part else None,
                               acct_code=ma_tk_mac_dinh(p.company, "repair", source), note=e.note)
            db.add(dong); db.flush()
            BTC.chan_kho_xe_thue_tu_tra(p, dong)   # xe thuê: phụ tùng lấy kho luôn là xuất bán, không "chủ xe tự trả" (02/10)
            if part:
                # trang kế toán kiểm tồn (không đủ → 409), trừ tồn, ghi sổ kho và sinh PXK_PT ngay bên đó
                r = gd.xuat_phu_tung(khoa="trip_expense:" + dong.id, part_id=part.id, qty=qty, ngay=dt.date.today(),
                                     gia=dong.unit_price, tien_te=dong.currency, ty_gia=ty_gia(p, dong.currency),
                                     truck_no=p.truck_no, trip_doc_no=p.doc_no, expense_id=dong.id, company=p.company,
                                     section="repair", mo_ta="Xuất %s %s sửa xe %s" % (qty, part.name, p.truck_no),
                                     note="Sửa xe trên đường — %s" % (e.note or ""),
                                     owner_id=p.owner_id)   # xe thuê: đối tác của phiếu xuất bán bên kho anh Toàn (05/10)
                dong.stock_move_id = r["move_id"]
                if r.get("unit_price"):                         # kho QLSX (05/10): giá vốn bình quân bên đó lúc xuất
                    dong.unit_price = r["unit_price"]
            e.expense_id = dong.id
            # Khoản sửa xe khai từ màn theo dõi là dữ liệu ĐÃ NHẬP: mục V vào thẳng hàng chờ kế toán kiểm.
            # Mục đã qua bước kiểm/ghi sổ/chi thì kéo về "đã nhập" và ghi rõ là mở lại vì có chi mới.
            s = _muc_cua(db, p)["repair"]
            if s.status not in ("wait", "entered"):
                _ghi_log(db, p, user, "sec_repair:reopen")
            rut_chi = s.status == "booked"
            s.status = "entered"
            if p.vehicle_id and e.incident_type == "breakdown":
                x = db.get(Vehicle, p.vehicle_id)
                if x: x.status = "maintenance"
        BTC.chan_sua_sau_khoa(db, p, truoc_khoa)   # lệch bút toán khoá → 409, phụ tùng vừa xuất được trả lại kho
        _ghi_log(db, p, user, "ev_%s" % kind)
    if sua and rut_chi:
        CMT.rut_cho(db, p, "repair"); db.commit()
    return xuat_phieu(db, p, vai=user.role)


# ---------------------------------------------------------------- đổi xe giữa đường (C2.2, anh Khampla 22/09)
@router.post("/api/trips/{tid}/doi-xe")
def doi_xe(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Xe hỏng nặng giữa đường → đổi xe khác chở tiếp, TRÊN CÙNG MỘT PHIẾU.

    Anh Khampla C2.2: chuyện này có thật và xảy ra khi mục I đã kiểm xong. Không thể bắt họ lập
    phiếu mới — hàng, khách, tuyến, tiền đã chi vẫn là của chuyến này; lập phiếu mới là tách đôi
    một chuyến trong mọi báo cáo.

    Nên: ghi xe mới vào phiếu, để lại MỘT dòng diễn biến nói rõ đổi từ xe nào sang xe nào và vì sao
    (xe cũ vẫn tra được), rồi kéo **mục I về "đã nhập"** để kế toán kiểm lại — thông tin xe đã khác
    thì chữ ký kiểm cũ không còn đúng. Xe cũ chuyển sang *đang sửa* nếu lý do là hỏng; xe mới sang
    *đang chạy*.
    """
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc đổi xe — họ là người điều xe."})
    _chan_khoa(p, user)
    if p.transport_status == "arrived":
        raise HTTPException(409, {"ma": "PHIEU_DA_TOI", "loi": "Xe đã tới nơi rồi, không đổi xe nữa."})
    xe_moi = db.get(Vehicle, str(data.get("vehicle_id") or ""))
    if not xe_moi:
        raise HTTPException(422, {"ma": "THIEU_XE", "loi": "Đổi sang xe nào? Cần vehicle_id."})
    if xe_moi.id == p.vehicle_id:
        raise HTTPException(409, {"ma": "CUNG_XE", "loi": "Xe mới trùng xe đang chạy (%s)." % (p.truck_no or "")})
    if not xe_moi.active:
        raise HTTPException(409, {"ma": "XE_NGUNG", "loi": "Xe %s đã ngưng dùng." % xe_moi.truck_no})
    # KHÔNG đổi chéo xe nhà ↔ xe liên kết (anh chủ dự án chốt 22/09). Hai loại xe định khoản khác nhau
    # (625/614 với 4022): chứng từ đã sinh trước lúc đổi — xuất kho dầu, tạm ứng — mang mã của loại cũ và
    # không ghi lại được. Chuyện đổi chéo hiếm, mà chứng từ lệch là thứ kế toán ghét nhất → lập phiếu mới.
    loai_moi = "joint" if xe_moi.owner_type == "joint" else "EPL"
    if loai_moi != (p.company or "EPL"):
        raise HTTPException(409, {"ma": "KHAC_LOAI_XE",
                                  "loi": "Phiếu đang là %s, xe %s là %s — không đổi chéo xe nhà và xe liên kết trên cùng phiếu, vì chứng từ đã sinh mang mã của loại xe cũ. Lập phiếu mới cho xe này."
                                         % ("xe liên kết" if p.company == "joint" else "xe nhà", xe_moi.truck_no,
                                            "xe liên kết" if loai_moi == "joint" else "xe nhà")})
    ly_do = (data.get("ly_do") or data.get("reason") or "").strip()
    if not ly_do:
        raise HTTPException(422, {"ma": "THIEU_LY_DO", "loi": "Đổi xe phải ghi lý do — kế toán kiểm lại mục I sẽ đọc câu này."})
    truoc_khoa = BTC.dau_khoa(db, p)        # phiếu đã khoá: đổi chủ xe là lệch bút toán thuê xe (02/10)
    xe_cu = db.get(Vehicle, p.vehicle_id) if p.vehicle_id else None
    cu_ten = p.truck_no or (xe_cu.truck_no if xe_cu else "")
    cu_bien = p.plate_head or ""
    # Xe cũ nghỉ: hỏng thì vào xưởng, lý do khác (điều xe) thì về rảnh.
    if xe_cu is not None and xe_cu.status != "inactive":
        xe_cu.status = "maintenance" if data.get("xe_cu_hong", True) else (
            "on_trip" if _con_chay_phieu_khac(db, p, "vehicle_id", xe_cu.id) else "available")
    p.vehicle_id = xe_moi.id
    p.truck_no, p.brand_model = xe_moi.truck_no, xe_moi.brand_model
    p.plate_head, p.plate_trailer = xe_moi.plate_head, xe_moi.plate_trailer
    # Cùng loại xe (đã chặn chéo ở trên): xe liên kết sang xe liên kết thì chủ xe có thể khác → chép chủ mới.
    if xe_moi.owner_type == "joint":
        p.owner_id, p.owner_name = xe_moi.owner_id, xe_moi.owner_name
    if data.get("odo_out") not in (None, ""):
        p.odo_out = _so(data.get("odo_out"), "odo_out")
    elif xe_moi.odometer_km is not None:
        p.odo_out = xe_moi.odometer_km
    if xe_moi.status != "inactive":
        xe_moi.status = "on_trip"
    tx = None
    if data.get("driver_id"):
        tx = db.get(Driver, str(data["driver_id"]))
        if not tx:
            raise HTTPException(422, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
        cu_tx = db.get(Driver, p.driver_id) if p.driver_id else None
        if cu_tx is not None and cu_tx.id != tx.id and cu_tx.status != "inactive":
            cu_tx.status = "on_trip" if _con_chay_phieu_khac(db, p, "driver_id", cu_tx.id) else "available"
        p.driver_id, p.driver_name = tx.id, tx.name
        if tx.status != "inactive":
            tx.status = "on_trip"
    ghi_chu = "Đổi xe %s%s → %s%s · %s%s" % (
        cu_ten, (" (%s)" % cu_bien) if cu_bien else "", xe_moi.truck_no,
        (" (%s)" % xe_moi.plate_head) if xe_moi.plate_head else "", ly_do,
        (" · đổi tài xế sang %s" % tx.name) if tx is not None else "")
    e = TripEvent(trip_id=p.id, kind="change_truck", note=ghi_chu, by_user=user.full_name,
                  stop_seq=int(data["stop_seq"]) if str(data.get("stop_seq") or "").isdigit() else None)
    db.add(e)
    # Mục I nói về xe: đổi xe thì chữ ký kiểm cũ không còn đúng, kéo về "đã nhập" để kiểm lại.
    s = _muc_cua(db, p)["info"]
    if s.status not in ("wait", "entered"):
        _ghi_log(db, p, user, "sec_info:reopen")
    s.status = "entered"
    _ghi_log(db, p, user, "a_change_truck")
    BTC.chan_sua_sau_khoa(db, p, truoc_khoa)
    db.commit()
    return xuat_phieu(db, p, vai=user.role)


# ---------------------------------------------------------------- tài xế báo đã về (C2.1, anh Khampla 22/09)
@router.post("/api/trips/{tid}/bao-ve")
def bao_ve(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Tài xế báo NGÀY VỀ và KM VỀ qua điện thoại — đúng người biết hai con số đó.

    Chỉ ghi hai số và đánh mốc "tới điểm cuối"; KHÔNG tự chuyển phiếu sang "đã tới": cân tại bãi
    hoặc tại cảng là việc của Bãi, Bãi bấm *Xe đã tới* thì hai ô ngày về, km về đã được điền sẵn."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("driver", "yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ tài xế của phiếu (hoặc Bãi) báo xe về."})
    _cua_tai_xe(db, p, user)
    _chan_khoa(p, user)
    if p.transport_status == "arrived":
        raise HTTPException(409, {"ma": "PHIEU_DA_TOI", "loi": "Phiếu đã ghi xe tới nơi rồi."})
    ngay = _ngay(data.get("back_date")) or dt.date.today()
    km = _so(data.get("odo_back"), "odo_back")
    if km is not None and p.odo_out is not None and km < p.odo_out:
        raise HTTPException(422, {"ma": "KM_SAI", "loi": "Km về (%s) không thể nhỏ hơn km lúc đi (%s)." % (round(km), round(p.odo_out))})
    p.back_date = ngay
    if km is not None:
        p.odo_back = km
    if p.transport_status == "dispatched":
        p.transport_status = "transit"
    diem = _diem_tuyen(db, p)
    if diem:
        cuoi = max(d["seq"] for d in diem)
        if not db.query(TripEvent).filter(TripEvent.trip_id == p.id, TripEvent.kind == "arrive_stop", TripEvent.stop_seq == cuoi).count():
            db.add(TripEvent(trip_id=p.id, kind="arrive_stop", stop_seq=cuoi, by_user=user.full_name,
                             note="Tài xế báo đã về · km %s" % (round(km) if km is not None else "—")))
    _ghi_log(db, p, user, "drv_back")
    db.commit()
    return xuat_phieu(db, p, vai=user.role)


# ---------------------------------------------------------------- mức phiếu
@router.post("/api/trips/{tid}/transport-status")
def doi_trang_thai_van_chuyen(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """ອອກລົດ → ກຳລັງຈັດສົ່ງ → ຮອດແລ້ວ. Admin Thà Bốc ghi khi xe báo về. Xe về thì xe & tài xế rảnh lại,
    công-tơ-mét của xe cập nhật theo số lúc về."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("yard", "admin", "driver"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc hoặc tài xế của phiếu cập nhật trạng thái xe."})
    _cua_tai_xe(db, p, user)
    # G7 (06/10): «Xuất phát» bấm lúc MẤT MẠNG nằm trong hàng đợi của máy tài xế, có mạng lại mới gửi (kèm `ma_gui` + `luc` giờ
    # máy). Gửi lại / gửi muộn mà xe đã đi (hoặc đã tới) thì trả nguyên, không đổi gì — không ghi trùng, không kéo phiếu đã tới
    # về "đang chạy". `luc` hợp lệ thì nhật ký ghi theo giờ bấm thật.
    from routes.vi_tri import luc_thao_tac
    if (data.get("ma_gui") or "").strip() and data.get("status") == "transit" and p.transport_status != "dispatched":
        return xuat_phieu(db, p, vai=user.role)
    luc = luc_thao_tac(data, p) if (data.get("ma_gui") or "").strip() else None
    _chan_khoa(p, user)
    truoc_khoa = BTC.dau_khoa(db, p)        # phiếu đã khoá: cân cuối của xe thuê đổi tiền thuê / phí / quá tải (02/10)
    moi = data.get("status")
    if moi not in TRANG_THAI_VAN_CHUYEN:
        raise HTTPException(422, {"ma": "TRANG_THAI_SAI", "loi": "Trạng thái phải là %s." % ", ".join(TRANG_THAI_VAN_CHUYEN)})
    if moi == "transit" and user.role != "admin":
        # XUẤT PHÁT chỉ khi tài xế đã cầm tiền tạm ứng: mục IV (đi đường) phải ở "đã chi". Đây là đúng thứ tự
        # anh chủ dự án mô tả — lập phiếu → in phiếu chi → duyệt → tài xế lấy tiền → mới bấm đi.
        if _dong_tam_ung(p, _dong_chi(db, p)) and _muc_cua(db, p)["travel"].status != "paid":
            cau = _cau_chua_tam_ung(db, p, "chưa xuất phát")
            if cau:
                raise HTTPException(409, {"ma": "CHUA_NHAN_TAM_UNG", "loi": cau})
    if moi == "arrived" and user.role != "admin":
        # Trước đây bấm thẳng "Xe đã tới" (bỏ qua "Xuất phát") là lách được quy tắc tạm ứng ở trên: cả chuyến đi
        # xong mà tài xế chưa cầm đồng nào, tiền đi đường không có tờ. Cửa này giờ giống cửa Xuất phát.
        if [d for d in _dong_tam_ung(p, _dong_chi(db, p)) if d.section == "travel"] and _muc_cua(db, p)["travel"].status != "paid":
            cau = _cau_chua_tam_ung(db, p, "chưa báo xe tới được")
            if cau:
                raise HTTPException(409, {"ma": "CHUA_NHAN_TAM_UNG", "loi": cau})
    if moi == "arrived" and p.kind == "gom":
        # Phiếu gom: hàng vào kho theo DÒNG HÀNG, mà dòng hàng chỉ có khi đã có cân tại mỏ. Hộp "Xe đã tới" hỏi luôn ô đó
        # (29/09): đã có (tài xế báo từ mỏ, hoặc Bãi đã ghi) thì điền sẵn; chưa có thì phải nhập mới báo tới được —
        # trước đây xe về mà thiếu dòng hàng là hàng không vào kho, phiếu giao không có lô để lấy.
        tan = _so(data.get("weight_origin"), "weight_origin")
        if tan is not None and abs(tan - (p.weight_origin or 0)) > 0.0005:
            if tan < 0:
                raise HTTPException(422, {"ma": "SO_AM", "loi": "Cân tại mỏ không được âm."})
            if not duoc_sua_muc(user.role, "trans", _muc_cua(db, p)["trans"].status):
                raise HTTPException(409, {"ma": "MUC_DA_KHOA", "loi": "Mục II đã kiểm với cân tại mỏ %s t — muốn đổi thì kế toán "
                                                                      "trả lại mục II trước." % _gon(p.weight_origin)})
            p.weight_origin = tan
        _dong_hang_gom(db, p, user)
        if not db.query(TripGoods).filter(TripGoods.trip_id == p.id, TripGoods.loai == "hang").count():
            raise HTTPException(422, {"ma": "THIEU_CAN_MO", "loi": "Chưa có cân tại mỏ — nhập số tấn theo phiếu cân ở mỏ rồi "
                                                                  "mới báo xe tới: hàng vào kho theo số đó."})
        # 05/10 (máy tự tạo phiếu nhập kho hàng PNK_HH): CÂN BÃI bắt buộc — hàng vào kho theo cân bãi; trước đây trống thì lấy cân
        # mỏ, kho nhận số chưa ai cân ở bãi. Hộp "Xe đã tới" gửi kèm weight_dest, hoặc phiếu đã có sẵn.
        can_bai = _so(data.get("weight_dest"), "weight_dest") if data.get("weight_dest") not in (None, "") else p.weight_dest
        if can_bai is None or can_bai <= 0:
            raise HTTPException(422, KH.THIEU_CAN_BAI)
    if moi == "arrived":
        if data.get("weight_dest") not in (None, ""): p.weight_dest = _so(data["weight_dest"], "weight_dest")
        if data.get("back_date"): p.back_date = _ngay(data["back_date"])
        if data.get("odo_back") not in (None, ""): p.odo_back = _so(data["odo_back"], "odo_back")
        # POD — biên bản giao nhận hàng (chốt 24/09): nhập ngay lúc xe tới nếu có giấy; không có thì để trống, ghi sau.
        if (data.get("pod_no") or "").strip(): p.pod_no = data["pod_no"].strip()
        if (data.get("pod_receiver") or "").strip(): p.pod_receiver = data["pod_receiver"].strip()
        if p.pod_no and not p.pod_date: p.pod_date = _ngay(data.get("pod_date")) or p.back_date or dt.date.today()
        _doi_trang_thai_xe_tai_xe(db, p, "available", "available")
        if p.vehicle_id and p.odo_back:
            x = db.get(Vehicle, p.vehicle_id)
            if x and (x.odometer_km or 0) < p.odo_back: x.odometer_km = p.odo_back
    else:
        _doi_trang_thai_xe_tai_xe(db, p, "on_trip", "on_trip")
    p.transport_status = moi
    _ghi_log(db, p, user, "st_%s" % moi, ts=luc)
    BTC.chan_sua_sau_khoa(db, p, truoc_khoa)
    with KK.GiaoDichKho(db, user) as gd:
        # Xe về tới nơi: DO gom thì hàng VÀO KHO bãi (sổ và phiếu nhập kho ở trang kế toán — tắt thì chưa báo tới được),
        # DO giao thì chốt dòng hao hụt.
        if moi == "arrived":
            if p.kind == "gom":
                KH.nhap_kho(db, p, user, gd)            # đã nhập mà thiếu PNK_HH → sinh tờ, không nhập trùng (05/10)
            else:
                KH.ghi_hao_hut_giao(db, p)
                KK.dam_bao_to_hang(db, user, p)         # DO giao đã xuất mà thiếu PXK_HH → sinh tờ (05/10)
    return xuat_phieu(db, p, vai=user.role)


# ---------------------------------------------------------------- bước 14: kiểm lại toàn phiếu rồi khoá
def _canh_bao_khoa(db, p):
    """Những chỗ kế toán phải nhìn trước khi khoá. Chỉ CẢNH BÁO, không chặn: số thật đôi khi lệch thật."""
    cb = []
    tuyen = db.get(Route, p.route_id) if p.route_id else None
    if p.odo_out and p.odo_back and tuyen and km_ca_chuyen(tuyen):
        # ước tính = km lúc đi + km cả chuyến (chiều đi + chiều về nếu tuyến có — chủ dự án 29/09)
        ca = km_ca_chuyen(tuyen)
        uoc = p.odo_out + ca
        lech = (p.odo_back - uoc) / ca * 100
        if abs(lech) > 10:
            cb.append({"ma": "KM_LECH", "loi": "Km về thật %s lệch %.0f%% so với ước tính %s (tuyến %s km%s)."
                       % (round(p.odo_back), lech, round(uoc), round(tuyen.total_km or 0),
                          " + %s km chiều về" % round(tuyen.return_km) if tuyen.return_km else "")})
    if p.weight_origin and p.weight_dest is not None:
        hao = (p.weight_origin - p.weight_dest) / p.weight_origin * 100
        if hao > 1.5:
            cb.append({"ma": "HAO_HUT", "loi": "Hao hụt %.2f%% vượt mức 1,5%%." % hao})
    if p.weight_dest is None:
        cb.append({"ma": "THIEU_CAN_CUOI", "loi": "Chưa có cân cuối." if p.kind == "giao" else "Chưa có cân tại bãi khi xe về."})
    if not db.query(TripGoods).filter(TripGoods.trip_id == p.id, TripGoods.loai == "hang").count():
        cb.append({"ma": "THIEU_DONG_HANG", "loi": "Phiếu chưa ghi dòng hàng (mặt hàng, số tấn)."})
    if not p.odo_back:
        cb.append({"ma": "THIEU_KM_VE", "loi": "Chưa có km về thật."})
    # Phiếu quặng của khách: đính kèm ẢNH hoặc NHẬP TAY đều được (anh chủ dự án 23/09: "phiếu khách hàng thì mình
    # nhập tay được" — mặt hàng, số lượng, chi tiết nằm ở dòng hàng; số và ngày phiếu kế toán gõ). Chỉ cảnh báo khi
    # không có cả hai.
    # 06/10 (chạy thử kịch bản CA-2): phiếu quặng là giấy cân của khách Ở MỎ — gắn với chặng GOM. DO giao lấy hàng từ lô đã có
    # phiếu quặng trên DO gom; căn cứ đòi tiền chặng giao là POD (cảnh báo riêng bên dưới) → không nhắc phiếu quặng cho DO giao.
    co_anh = db.query(TripAttachment).filter(TripAttachment.trip_id == p.id, TripAttachment.kind == "ore_bill").count()
    if p.kind != "giao" and not co_anh and not (p.ore_bill_no or "").strip():
        cb.append({"ma": "THIEU_PHIEU_QUANG", "loi": "Chưa có phiếu quặng của khách — đính kèm ảnh, hoặc nhập tay số phiếu quặng."})
    # POD — biên bản giao nhận hàng: căn cứ đòi tiền khách. Nhập tay số POD hoặc đính kèm ảnh đều được (như phiếu quặng).
    co_pod = db.query(TripAttachment).filter(TripAttachment.trip_id == p.id, TripAttachment.kind.in_(("pod", "pod_sign"))).count()
    if p.kind == "giao" and not co_pod and not (p.pod_no or "").strip():
        cb.append({"ma": "THIEU_POD", "loi": "Chưa có biên bản giao nhận hàng (POD) — đính kèm ảnh, hoặc nhập tay số POD."})
    if p.pod_condition in ("thieu", "hong"):
        cb.append({"ma": "HANG_THIEU_HONG", "loi": "Người nhận %s ghi hàng %s khi ký nhận: %s" % (
            p.pod_receiver or "", "THIẾU" if p.pod_condition == "thieu" else "HƯ HỎNG", p.pod_note or "")})
    ngay = p.doc_date or dt.date.today()
    for cot, loai, doi_tac, ten in (("contract_id", "khach", p.customer_id, "khách"),
                                    ("hire_contract_id", "thue_xe", p.owner_id if p.company == "joint" else None, "chủ xe")):
        hd = db.get(Contract, getattr(p, cot)) if getattr(p, cot) else None
        if hd and HD.trang_thai(hd, ngay) == "het_han":
            cb.append({"ma": "HOP_DONG_HET_HAN", "loi": "Hợp đồng %s của %s đã hết hạn ngày %s — trước ngày phiếu."
                       % (hd.contract_no, ten, hd.valid_to.strftime("%d/%m/%Y"))})
        elif not hd and doi_tac:
            cu = HD.het_han_gan_nhat(db, loai, doi_tac, ngay)
            if cu:
                cb.append({"ma": "HOP_DONG_HET_HAN", "loi": "Hợp đồng %s của %s đã hết hạn ngày %s; chưa có hợp đồng mới."
                           % (cu.contract_no, ten, cu.valid_to.strftime("%d/%m/%Y"))})
    tt = {m: s.status for m, s in _muc_cua(db, p).items()}
    dong = _dong_chi(db, p)
    for m in MUC_CHI:
        if any(d.section == m for d in dong) and tt.get(m) in ("wait", "entered"):
            # 09/10: tên mục bằng số La Mã như trên tờ phiếu (trước đây chèn mã nội bộ: "Mục fuel …")
            from services.ban_giao import MUC as LA_MA
            cb.append({"ma": "MUC_CHUA_KIEM", "loi": "Mục %s có dòng chi nhưng chưa kiểm." % LA_MA.get(m, m)})
    # G5 (06/10): khai báo của tài xế CHƯA DUYỆT (khai đổ dầu dọc đường, báo sự cố) — khoá phiếu mà chưa duyệt là khoản dầu / sửa
    # chữa tài xế đã trả không vào phiếu, tất toán tài xế thiếu. Liệt kê từng lần; không có số tiền (Bãi cũng gọi kiểm lại — A2).
    cho = db.query(TripEvent).filter(TripEvent.trip_id == p.id, TripEvent.status == "reported").order_by(TripEvent.ts).all()
    if cho:
        diem = {x.id: x.name for x in db.query(FuelPlace).filter(FuelPlace.id.in_([e.place_id for e in cho if e.place_id] or [""]))}
        vi, lo, en = [], [], []
        for e in cho:
            luc = e.ts.strftime("%d/%m %H:%M") if e.ts else ""
            if e.kind == "refuel":
                tram = diem.get(e.place_id) or ""
                vi.append("khai đổ dầu %s L%s (%s)" % (_gon(e.qty_l), (" ở " + tram) if tram else "", luc))
                lo.append("ແຈ້ງໃສ່ນໍ້າມັນ %s L%s (%s)" % (_gon(e.qty_l), (" ທີ່ " + tram) if tram else "", luc))
                en.append("refuel declaration %s L%s (%s)" % (_gon(e.qty_l), (" at " + tram) if tram else "", luc))
            else:
                ghi = (" — " + e.note[:60]) if e.note else ""
                vi.append("báo sự cố %s%s (%s)" % (_LOAI_SU_CO_VI.get(e.incident_type, e.incident_type or ""), ghi, luc))
                lo.append("ແຈ້ງເຫດການ %s%s (%s)" % (_LOAI_SU_CO_LO.get(e.incident_type, e.incident_type or ""), ghi, luc))
                en.append("incident report %s%s (%s)" % (_LOAI_SU_CO_EN.get(e.incident_type, e.incident_type or ""), ghi, luc))
        cb.append({"ma": "KHAI_BAO_CHO_DUYET", "so": len(cho),
                   "loi": "Tài xế còn %d khai báo chưa duyệt: %s — duyệt hoặc từ chối trước khi khoá (Theo dõi tuyến → duyệt báo hỏng / "
                          "khai dầu)." % (len(cho), "; ".join(vi)),
                   "loi_lo": "ໂຊເຟີຍັງມີ %d ລາຍການແຈ້ງທີ່ຍັງບໍ່ອະນຸມັດ: %s — ອະນຸມັດ ຫຼື ປະຕິເສດ ກ່ອນລັອກ." % (len(cho), "; ".join(lo)),
                   "loi_en": "The driver has %d unapproved declaration(s): %s — approve or reject them before locking." % (len(cho), "; ".join(en))})
    return cb


# tên loại sự cố trong câu cảnh báo khoá phiếu (G5) — cùng nghĩa với khoá inc_* của giao diện
_LOAI_SU_CO_VI = {"breakdown": "hỏng xe", "tire": "nổ / thủng lốp", "accident": "tai nạn", "delay": "chậm / chờ", "held": "bị giữ xe",
                  "other": "khác"}
_LOAI_SU_CO_LO = {"breakdown": "ລົດເສຍ", "tire": "ຢາງແຕກ / ຮົ່ວ", "accident": "ອຸບັດເຫດ", "delay": "ຊ້າ / ລໍຖ້າ", "held": "ຖືກກັກລົດ",
                  "other": "ອື່ນໆ"}
_LOAI_SU_CO_EN = {"breakdown": "breakdown", "tire": "tyre burst / puncture", "accident": "accident", "delay": "delay", "held": "held / inspected",
                  "other": "other"}


@router.get("/api/trips/{tid}/kiem-lai")
def kiem_lai(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bảng rà trước khi khoá: kế toán bấm 'Kiểm lại' thấy ngay lệch gì."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _cua_tai_xe(db, p, user)          # 07/10: tài xế không đọc bảng rà phiếu người khác
    chan = []
    if not p.locked:
        # 06/10 (chạy thử kịch bản CA-3): báo trước chỗ CHẶN khoá — hộp Khoá từng báo «không có điểm lệch» rồi mới ra 409
        dong = _dong_chi(db, p)
        for kiem in (lambda: BTC.chan_khoa_chua_xuat(p, dong), lambda: BTC.chan_xuat_ban(p, dong, luc="khoa")):
            try:
                kiem()
            except HTTPException as e:
                if isinstance(e.detail, dict):
                    chan.append({k: e.detail.get(k) for k in ("ma", "loi", "loi_lo", "loi_en")})
    # 09/10: điểm cần xem / chỗ chặn khoá mang thêm bản tiếng Lào, Anh (services/loi_dich) — hộp Khoá hiện theo tiếng đang xem
    return LD.them_dich({"canh_bao": _canh_bao_khoa(db, p), "chan": chan, "locked": bool(p.locked)})


@router.post("/api/trips/{tid}/khoa")
def khoa_phieu(tid: str, data: dict = Body(default={}), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Xe về → kế toán rà lại cả phiếu → KHOÁ. Có cảnh báo thì phải gửi {"xac_nhan": true} mới khoá."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("acct", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán Viêng Chăn khoá phiếu."})
    if p.locked:
        raise HTTPException(409, {"ma": "DA_KHOA", "loi": "Phiếu đã khoá rồi."})
    if p.transport_status != "arrived":
        raise HTTPException(409, {"ma": "XE_CHUA_VE", "loi": "Xe chưa về (trạng thái %s) thì chưa khoá phiếu." % p.transport_status})
    # xe thuê: dầu / phụ tùng lấy kho là xuất bán — phải EPL ứng và có giá bán thì SO nhiên liệu cho đối tác (02/10) mới đúng số
    # (chủ dự án 02/10: chặn, không chỉ cảnh báo) → 409 KHO_XE_THUE_XUAT_BAN · THIEU_GIA_BAN, nói mục nào, ai gõ giá
    dong_khoa = _dong_chi(db, p)
    # dầu kho chưa cấp theo phiếu đề nghị / phụ tùng ghi lấy kho mà chưa xuất (02/10): hàng chưa rời kho thì không khoá — tiền
    # chi, tiền trừ chủ xe đã tính dòng đó mà chưa có chứng từ xuất kho → 409 DAU_KHO_CHUA_CAP · PT_KHO_CHUA_XUAT
    BTC.chan_khoa_chua_xuat(p, dong_khoa)
    BTC.chan_xuat_ban(p, dong_khoa, luc="khoa")
    cb = _canh_bao_khoa(db, p)
    if cb and not data.get("xac_nhan"):
        raise HTTPException(409, {"ma": "CO_CANH_BAO", "loi": "Phiếu còn %d điểm cần xem; xem rồi xác nhận khoá." % len(cb), "canh_bao": cb})
    p.locked, p.locked_by, p.locked_at = True, user.full_name, dt.datetime.utcnow()
    _ghi_log(db, p, user, "a_lock" if not cb else "a_lock_warn")
    # DO xong → phiếu đề nghị thu cho bên công nợ (sếp 30/09)
    DNT.ghi(db, p, user)
    # khoản KHÔNG qua tiền phải vào sổ lúc khoá (chủ dự án 01/10): xe thuê Nợ 621 / Có 4022 bằng tiền thuê; dòng ghi nợ nhà
    # cung cấp Nợ 625 · 614 / Có 4021 — thành bút toán chờ gửi (hệ anh Tune chưa có đường nhận bút toán tổng hợp)
    BTC.ghi_khoa_phieu(db, p, user.full_name)
    db.commit()
    ra = xuat_phieu(db, p, vai=user.role); ra["canh_bao"] = LD.them_dich(cb)
    return ra


@router.post("/api/trips/{tid}/mo-khoa")
def mo_khoa_phieu(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("acct", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán Viêng Chăn mở khoá."})
    # 01/10 (bỏ trang kế toán tạm): không xét hoá đơn / tờ đề nghị thu "đã đẩy" của trang tạm nữa — chỉ xét những gì đã gửi
    # sang hệ anh Tune: SO (công nợ khách), lần gửi SO chưa rõ kết quả, đề nghị trả chủ xe.
    so_kt = db.get(GuiSoTune, "EPLLAO-" + p.id)
    if so_kt is not None and so_kt.status == "synced" and user.role != "admin":
        raise HTTPException(409, {"ma": "DA_TAO_SO", "loi": "Bên công nợ đã tạo SO %s cho DO này — báo bên đó trước, rồi nhờ Sếp mở khoá."
                                                            % (so_kt.order_code or "")})
    if so_kt is not None and so_kt.status != "synced" and (GT._chua_ro(so_kt) or so_kt.status == "conflict"):
        # lần gửi trước mất mạng / hết giờ / bên kia báo trùng: bên đó có thể ĐÃ tạo SO theo số cũ — mở khoá sửa số rồi gửi lại
        # là hai bên hai số. Gửi lại (cùng gói, cùng khoá) để biết chắc, hoặc đối soát, rồi mới mở.
        raise HTTPException(409, {"ma": "SO_CHUA_RO", "loi": "Lần gửi SO trước của DO này chưa rõ kết quả (%s) — bấm gửi lại ở màn Phiếu đề "
                                                             "nghị thu để biết bên công nợ đã tạo SO chưa, rồi mới mở khoá." % (
                                                                 so_kt.error_code or so_kt.status)})
    # SO nhiên liệu cho đối tác (02/10) — chặn y như SO cước: số dầu / giá bán đã thành công nợ đối tác bên kế toán
    so_nl = NL.so_cua(db, p)
    if so_nl is not None and so_nl.status == "synced" and user.role != "admin":
        raise HTTPException(409, {"ma": "DA_TAO_SO", "loi": "Bên công nợ đã tạo SO nhiên liệu %s cho DO này (đối tác %s) — báo bên đó trước, "
                                                            "rồi nhờ Sếp mở khoá." % (so_nl.order_code or "", p.owner_name or "")})
    if so_nl is not None and so_nl.status != "synced" and (NL._chua_ro(so_nl) or so_nl.status == "conflict"):
        raise HTTPException(409, {"ma": "SO_CHUA_RO", "loi": "Lần gửi SO nhiên liệu trước của DO này chưa rõ kết quả (%s) — bấm «Tạo SO bên "
                                                             "kế toán» lần nữa để biết bên đó đã tạo chưa, rồi mới mở khoá." % (
                                                                 so_nl.error_code or so_nl.status)})
    # đề nghị trả chủ xe bên hệ kế toán (01/10): số trả chủ xe tính từ phiếu đã khoá — mở khoá thì số có thể đổi
    # 02/10: kể cả đề nghị lỗi mà đã cấn trừ SO nhiên liệu bên kế toán (chi_tune._dang_giu)
    r = CHI._dang_giu(db, p.owner_id).get(p.id) if p.owner_id else None
    if r is not None:
        raise HTTPException(409, {"ma": "TRONG_DE_NGHI_TRA_CHU_XE", "loi": (
            "Phiếu %s nằm trong đề nghị trả chủ xe %s (%s) — %s" % (p.doc_no, r.ref_no, r.document_no or "",
            "thủ quỹ đã chi / đã cấn trừ xong, đối soát ở hệ kế toán." if r.status == "da_chi" else
            "bỏ đề nghị đó ở màn Xe liên kết / Tất toán đối tác trước."))})
    DNT.rut(db, p)
    BTC.huy_khoa_phieu(db, p, user.full_name)      # bút toán chờ của lần khoá này: chưa gửi thì huỷ, khoá lại ghi theo số mới
    p.locked, p.locked_by, p.locked_at = False, None, None
    _ghi_log(db, p, user, "a_unlock_slip")
    db.commit()
    return xuat_phieu(db, p, vai=user.role)


# ---------------------------------------------------------------- xe liên kết: chi trả chủ xe → PC_CX
@router.post("/api/trips/{tid}/tra-chu-xe")
def tra_chu_xe(tid: str, user=Depends(nguoi_hien_tai)):
    """Trả chủ xe ở HỆ KẾ TOÁN anh Tune từ 01/10: màn Xe liên kết lập đề nghị trả → phiếu chi "Chi khác" bên đó, thủ quỹ chi và
    ghi sổ ở đó, phiếu nhận "đã trả chủ xe" (services/chi_tune.de_nghi_tra_chu_xe)."""
    raise HTTPException(409, {"ma": "DA_DOI_SANG_KE_TOAN", "loi": "Trả chủ xe: lập đề nghị trả ở màn Xe liên kết — phiếu chi bên hệ kế toán, "
                                                                 "thủ quỹ chi ở đó."})


# ---------------------------------------------------------------- tệp đính kèm (phiếu quặng của khách)
# Chỗ chứa tệp dùng chung với ảnh xe — xem services/tep.py.


def _xoa_tep_dia(a):
    try:
        os.remove(os.path.join(TEP_DIR, a.trip_id, a.stored))
    except OSError:
        pass


def _xuat_tep(a):
    return {"id": a.id, "trip_id": a.trip_id, "kind": a.kind, "filename": a.filename, "content_type": a.content_type,
            "size": a.size, "note": a.note, "by_user": a.by_user, "ts": a.ts.isoformat() if a.ts else None,
            "url": "/api/tep/%s" % a.id, "la_anh": (a.content_type or "").startswith("image/")}


@router.get("/api/trips/{tid}/tep")
def ds_tep(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _cua_tai_xe(db, p, user)
    # 11c (màn Web): mỗi tệp kèm `xoa` — người đưa lên hoặc KT Thu/Chi / Sếp xoá được, phiếu chưa khoá với vai đó (như xoa_tep)
    khoa = bool(p.locked) and user.role not in VAI_SAU_KHOA
    return [dict(_xuat_tep(a), xoa=not khoa and (user.role in ("acct", "admin") or a.by_user == user.full_name))
            for a in db.query(TripAttachment).filter(TripAttachment.trip_id == p.id).order_by(TripAttachment.ts).all()]


@router.post("/api/trips/{tid}/tep")
async def them_tep(tid: str, tep: UploadFile = File(...), kind: str = Form("ore_bill"), note: str = Form(""),
                   db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bãi (hoặc kế toán) chụp phiếu quặng của khách đưa lên. Ảnh hoặc PDF, tối đa 8 MB."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("yard", "acct", "rev", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Bãi hoặc kế toán đính kèm tệp."})
    _chan_khoa(p, user)
    kieu = (tep.content_type or mimetypes.guess_type(tep.filename or "")[0] or "").lower()
    if kieu not in TEP_KIEU:
        raise HTTPException(422, {"ma": "KIEU_TEP", "loi": "Chỉ nhận ảnh (JPG, PNG, WEBP, HEIC) hoặc PDF."})
    du = await tep.read()
    if len(du) > TEP_TOI_DA or loi_co_tep(kieu, len(du)):
        raise HTTPException(422, {"ma": "TEP_QUA_LON", "loi": loi_co_tep(kieu, len(du)) or "Tệp %.1f MB, tối đa 10 MB." % (len(du) / 1048576)})
    if not du:
        raise HTTPException(422, {"ma": "TEP_RONG", "loi": "Tệp rỗng."})
    a = TripAttachment(trip_id=p.id, kind=kind if kind in ("ore_bill", "pod", "other") else "ore_bill",
                       filename=ten_tep(tep.filename, "tep"), content_type=kieu,     # giữ chữ Lào (dấu kết hợp) — services/tep
                       size=len(du), note=(note or None), by_user=user.full_name)
    a.id = ma_moi()
    a.stored = a.id + TEP_KIEU[kieu]
    os.makedirs(os.path.join(TEP_DIR, p.id), exist_ok=True)
    with open(os.path.join(TEP_DIR, p.id, a.stored), "wb") as f:
        f.write(du)
    db.add(a)
    _ghi_log(db, p, user, "a_attach")
    db.commit()
    return _xuat_tep(a)


@router.get("/api/tep/{aid}")
def mo_tep(aid: str, request: Request, tk: str = "", db: Session = Depends(get_db)):
    """Trả tệp. Thẻ <img> không gửi header nên nhận phiên qua ?tk=…; không có phiên thì từ chối."""
    a = db.get(TripAttachment, aid)
    if not a:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tệp này."})
    dau = request.headers.get("Authorization", "")
    token = tk or (dau[7:].strip() if dau.lower().startswith("bearer ") else "")
    nguoi_tu_token(db, token)          # token EPL cũ hoặc token GLS (08/10); không có / sai → 401
    duong = os.path.join(TEP_DIR, a.trip_id, a.stored)
    if not os.path.exists(duong):
        raise HTTPException(404, {"ma": "MAT_TEP", "loi": "Tệp không còn trên máy chủ."})
    return FileResponse(duong, media_type=a.content_type, filename=a.filename,
                        content_disposition_type="inline")


@router.delete("/api/tep/{aid}")
def xoa_tep(aid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    a = db.get(TripAttachment, aid)
    if not a:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tệp này."})
    p = db.get(Trip, a.trip_id)
    if user.role not in ("acct", "admin") and a.by_user != user.full_name:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ người đưa lên hoặc kế toán xoá tệp."})
    if p: _chan_khoa(p, user)
    _xoa_tep_dia(a)
    db.delete(a)
    if p: _ghi_log(db, p, user, "a_detach")
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- hoá đơn · thu tiền: ở HỆ KẾ TOÁN anh Tune
# 28/09 dời sang trang kế toán tạm; 01/10 chủ dự án bỏ trang tạm (số bên đó là số thử). Nay: khoá phiếu → phiếu đề nghị thu →
# gửi SO sang hệ anh Tune (công nợ khách, hoá đơn, thu tiền ở đó); trang này chỉ đọc lại trạng thái (de_nghi_thu).
DA_DOI_HD = {"ma": "DA_DOI_SANG_KE_TOAN",
             "loi": "Hoá đơn và thu tiền khách làm ở hệ kế toán: khoá phiếu → gửi đề nghị thu (SO) ở màn Phiếu đề nghị thu; "
                    "thu tiền ghi ở công nợ khách bên đó."}


@router.post("/api/trips/{tid}/invoice")
def xuat_hoa_don(tid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_HD)


# ---------------------------------------------------------------- khách trả tiền: sổ thu từng lần
#
# Thu tiền khách ở hệ kế toán anh Tune từ 01/10: trạng thái thu của phiếu (finance_status) là bản chép đọc lại từ bên đó
# (services/de_nghi_thu.doc_thu_tune). Đường liên thông cũ của trang tạm ghi collected_lak sang đã gỡ (01/10); hàm dưới chỉ
# còn tools/don_rac_bo_kiem.py gọi (dọn dữ liệu bộ kiểm cũ) — bỏ cùng công cụ đó.
LECH_COI_LA_DU = 1.0          # lệch dưới 1 LAK thì coi là trả đủ — làm tròn tỷ giá thôi, không phải nợ


def _tinh_lai_trang_thai_thu(db, p):
    """Trạng thái tài chính = so tổng đã thu (collected_lak — bản chép cũ của trang tạm) với tiền hoá đơn, quy LAK."""
    da = float(p.collected_lak or 0)
    tong = tinh_phieu(p, _dong_chi(db, p))["doanh_thu_lak"]
    if da <= LECH_COI_LA_DU:
        p.finance_status = "unpaid"
    elif tong - da <= LECH_COI_LA_DU:
        p.finance_status = "paid"
    else:
        p.finance_status = "partial"
    return da, tong


@router.get("/api/trips/{tid}/thu-tien")
def ds_thu_tien(tid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_HD)


@router.post("/api/trips/{tid}/thu-tien")
def ghi_thu_tien(tid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_HD)


@router.delete("/api/thu-tien/{pid}")
def xoa_thu_tien(pid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_HD)


# ---------------------------------------------------------------- tài xế báo sự cố → duyệt theo loại → mục V hoặc VI
def _lan_gui_tai_xe(db, p, user, data, loai):
    """Lần khai báo gửi từ HÀNG ĐỢI MẤT MẠNG của máy tài xế (G7, 06/10 — như ký giao nhận / báo cân ở mỏ): mang `ma_gui` (mã lần
    gửi) và `luc` (giờ máy lúc bấm). Trả (luc, da_nhan): `luc` = giờ thật dùng làm giờ khai báo (None: không phải lần gửi từ hàng
    đợi, hoặc giờ máy vô lý → giờ máy chủ); `da_nhan` = máy chủ ĐÃ ghi lần này rồi (gửi lại vì mất phản hồi) — khoá chống trùng
    là (phiếu, người khai, loại, đúng giờ máy tới phần nghìn giây). Giờ máy vô lý thì không có khoá — vẫn nhận, như trước."""
    from routes.vi_tri import luc_thao_tac
    if not (data.get("ma_gui") or "").strip():
        return None, False
    luc = luc_thao_tac(data, p)
    if luc is None:
        return None, False
    da = db.query(TripEvent.id).filter(TripEvent.trip_id == p.id, TripEvent.by_user == user.full_name, TripEvent.kind.in_(loai),
                                       TripEvent.ts == luc).first()
    return luc, da is not None


def _bao_truoc_khi_toi(db, p, luc):
    """Khai báo gửi muộn (hàng đợi) mà giờ thật TRƯỚC lúc phiếu được ghi "đã tới" — xảy ra trên đường, vẫn nhận (phiếu chưa khoá)."""
    from routes.vi_tri import moc_toi
    if luc is None or p.transport_status != "arrived" or p.locked:
        return False
    m = moc_toi(db, p)
    return m is not None and luc <= m


@router.post("/api/trips/{tid}/bao-hong")
def bao_hong(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """TÀI XẾ báo sự cố / hỏng xe trên đường, kèm số tiền dự kiến. Chỉ là BÁO — chưa thành chi phí.
    Duyệt ở đường /duyet bên dưới: hỏng xe, lốp, tai nạn → tổ sửa chữa, dòng chi mục V; kẹt đường, bị giữ xe, khác → Bãi,
    dòng chi mục VI (`SU_CO_SUA_CHUA`). Gửi từ hàng đợi mất mạng (06/10): `ma_gui` + `luc` — xem _lan_gui_tai_xe."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("driver", "yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ tài xế của phiếu (hoặc Bãi) báo hỏng."})
    _cua_tai_xe(db, p, user)
    luc, da_nhan = _lan_gui_tai_xe(db, p, user, data, ("incident", "repair"))
    if da_nhan:
        return xuat_phieu(db, p, vai=user.role)
    if (p.transport_status == "arrived" and not _bao_truoc_khi_toi(db, p, luc)) or p.finance_status == "paid":
        raise HTTPException(409, {"ma": "PHIEU_DA_XONG", "loi": "Phiếu đã về / đã thu tiền, không báo hỏng nữa."})
    lt = data.get("incident_type") or "breakdown"
    if lt not in LOAI_SU_CO:
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "incident_type phải là %s." % ", ".join(LOAI_SU_CO)})
    ghi = (data.get("note") or "").strip()
    if not ghi:
        raise HTTPException(422, {"ma": "THIEU_MO_TA", "loi": "Báo hỏng phải ghi hỏng gì."})
    tien = _so(data.get("reported_cost"), "reported_cost")
    if tien is not None and tien < 0:
        raise HTTPException(422, {"ma": "SO_AM", "loi": "Số tiền không được âm."})
    e = TripEvent(trip_id=p.id, kind="incident", incident_type=lt, note=ghi, by_user=user.full_name,
                  status="reported", reported_cost=tien, currency=str(data.get("currency") or "LAK").upper())
    if luc is not None:
        e.ts = luc                       # giờ máy lúc báo thật (hàng đợi mất mạng, 06/10)
    # màn tài xế mới (30/09): còn chạy được không · khoản chi tài xế đã tự trả hay chưa (chỉ có nghĩa khi có số tiền)
    if data.get("can_run") is not None:
        e.can_run = bool(data["can_run"])
    if tien and data.get("paid_by_driver") is not None:
        e.paid_by_driver = bool(data["paid_by_driver"])
    if data.get("stop_seq") not in (None, ""):
        e.stop_seq = int(data["stop_seq"])
    db.add(e)
    _ghi_log(db, p, user, "ev_reported", ts=luc)
    db.commit()
    return xuat_phieu(db, p, vai=user.role)


def _duyet_chi_khac(db, p, e, data, user):
    """Duyệt sự cố KHÔNG phải sửa chữa (kẹt đường, bị giữ xe, khác) → một dòng mục VI chi khác.

    Bãi duyệt nhưng không thấy, không nhập tiền (A2): số tiền của dòng là số tài xế báo; KT Chi phí VC sửa khi kiểm mục
    VI. Tài xế không báo tiền thì chỉ ghi nhận là đã xem, không sinh dòng chi."""
    gia = _so(data.get("unit_price"), "unit_price") if nhap_gia_chi(user.role) else None
    if gia is None:
        gia = e.reported_cost
    if gia is not None and gia < 0:
        raise HTTPException(422, {"ma": "SO_AM", "loi": "Số tiền không được âm."})
    if not gia:
        e.status = "approved"
        _ghi_log(db, p, user, "ev_approved")
        db.commit()
        return xuat_phieu(db, p, vai=user.role)
    tien_te = str((data.get("currency") if nhap_gia_chi(user.role) else None) or e.currency or "LAK").upper()
    so_dong = db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "other").count()
    dong = _gan_tk(p, TripExpense(trip_id=p.id, section="other", line_no=so_dong + 1, item_key="x_misc",
                                  item_name=(data.get("item_name") or e.note or "")[:120] or None,
                                  qty=1, unit_price=gia, currency=tien_te, paid_by_epl=True,
                                  note=(e.note or "") + (" — tài xế đã tự trả" if e.paid_by_driver else "")))
    db.add(dong); db.flush()
    e.status, e.expense_id = "approved", dong.id
    s = _muc_cua(db, p)["other"]
    if s.status not in ("wait", "entered"):
        _ghi_log(db, p, user, "sec_other:reopen")
    rut_chi = s.status == "booked"
    s.status = "entered"
    _ghi_log(db, p, user, "ev_approved")
    db.commit()
    if rut_chi:
        CMT.rut_cho(db, p, "other"); db.commit()
    return xuat_phieu(db, p, vai=user.role)


def _duyet_do_dau(db, p, e, data, user):
    """Duyệt khai đổ dầu của tài xế → một dòng mục III, nguồn MUA (không đụng kho).

    Số lít và đơn giá lấy theo số tài xế khai, người duyệt sửa được. Tiền tệ thường là VND vì dầu
    mua bên Việt Nam; quy đổi về LAK dùng tỷ giá ghi trên chính phiếu này.
    """
    lit = _so(data.get("qty_l"), "qty_l") or e.qty_l or 0
    gia = _so(data.get("unit_price"), "unit_price") if nhap_gia_chi(user.role) else None
    if gia is None:
        gia = e.reported_cost or 0
    if lit <= 0 or gia < 0:
        raise HTTPException(422, {"ma": "THIEU_SO", "loi": "Phải có số lít lớn hơn 0."})
    # giá 0 được: Bãi duyệt số lít, KT kho xăng dầu nhập giá lúc kiểm mục III (chặn giá 0 ở bước kiểm)
    diem = db.get(FuelPlace, e.place_id) if e.place_id else None
    # 02/10 (chủ dự án): người duyệt chọn luôn "Trạm cho ghi nợ?" — có thì dòng mang ghi_no như ô "Ghi nợ tại trạm" trên
    # phiếu: định khoản Có 4021 (nợ nhà cung cấp, bút toán lúc khoá), không vào tiền mặt tài xế / tất toán. Ghi nợ thì phải
    # biết nợ ai: nhà cung cấp của trạm (như dòng lập trên phiếu — _ncc_theo_diem), trạm chưa gắn nhà cung cấp thì chặn.
    ghi_no = str(data.get("ghi_no") or "").strip().lower() in ("1", "true", "co", "yes")
    ncc = e.supplier_id or (diem.supplier_id if diem else None)
    if ghi_no and not ncc:
        raise BTC.loi3(422, "GHI_NO_THIEU_NCC",
                       "Trạm %s chưa gắn nhà cung cấp — không ghi nợ được (không biết nợ ai). KT Chi phí gắn trạm với nhà cung "
                       "cấp ở danh mục Nhà cung cấp, hoặc chọn «Không — tài xế trả tiền túi»." % (diem.name if diem else "đổ dầu"),
                       "ປໍ້າ %s ຍັງບໍ່ໄດ້ຜູກກັບຜູ້ສະໜອງ — ຂຽນໜີ້ບໍ່ໄດ້ (ບໍ່ຮູ້ວ່າເປັນໜີ້ໃຜ). ບັນຊີລາຍຈ່າຍຜູກປໍ້າກັບຜູ້ສະໜອງ ຢູ່ລາຍການ "
                       "ຜູ້ສະໜອງ, ຫຼື ເລືອກ «ບໍ່ — ໂຊເຟີຈ່າຍເງິນເອງ»." % (diem.name if diem else ""),
                       "Station %s has no supplier linked — it cannot be put on account (no one to owe). The expense accountant links "
                       "the station to a supplier in the Supplier list, or choose «No — the driver paid out of pocket»."
                       % (diem.name if diem else ""), trip_id=p.id)
    truoc_khoa = BTC.dau_khoa(db, p)        # phiếu đã khoá: dòng ghi nợ mới lệch bút toán nợ nhà cung cấp lúc khoá → chặn dưới
    so_dong = db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "fuel").count()
    dong = _gan_tk(p, TripExpense(trip_id=p.id, section="fuel", line_no=so_dong + 1, item_key="diesel",
                                  qty=lit, unit_price=gia, currency=str(data.get("currency") or e.currency or "VND").upper(),
                                  place=None, place_id=e.place_id, supplier_id=ncc, paid_by_epl=True, source="mua",
                                  ghi_no=ghi_no,
                                  note="Tài xế đổ dọc đường%s%s" % (" tại " + diem.name if diem else "",
                                                                    " — " + e.note if e.note else "")))
    db.add(dong); db.flush()
    BTC.chan_sua_sau_khoa(db, p, truoc_khoa)
    e.status, e.expense_id = "approved", dong.id
    muc = _muc_cua(db, p)["fuel"]
    if muc.status not in ("wait", "entered"):
        _ghi_log(db, p, user, "sec_fuel:reopen")
    muc.status = "entered"
    _ghi_log(db, p, user, "ev_refuel_approved")
    db.commit()
    return xuat_phieu(db, p, vai=user.role)


@router.post("/api/trips/{tid}/bao-nhien-lieu")
def bao_nhien_lieu(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """TÀI XẾ khai đổ dầu DỌC ĐƯỜNG — chiều về từ Việt Nam phải mua dầu chạy về.

    Đây là dầu MUA NGOÀI, không phải lĩnh kho, nên không có phiếu xuất kho: nó thành một dòng chi
    mục III nguồn "mua", định khoản …/402, và ghi rõ mua ở trạm nào của nhà cung cấp nào. Khai xong
    chỉ là BÁO, kế toán duyệt mới thành dòng chi thật — giống hệt cách báo hỏng. Gửi từ hàng đợi mất mạng (06/10): `ma_gui` +
    `luc` — xem _lan_gui_tai_xe (gửi lại lần đã nhận không ghi trùng; giờ khai = giờ máy lúc bấm).
    """
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("driver", "yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ tài xế của phiếu (hoặc Bãi) khai đổ dầu."})
    _cua_tai_xe(db, p, user)
    luc, da_nhan = _lan_gui_tai_xe(db, p, user, data, ("refuel",))
    if da_nhan:
        return xuat_phieu(db, p, vai=user.role)
    if p.finance_status == "paid":
        raise HTTPException(409, {"ma": "PHIEU_DA_XONG", "loi": "Phiếu đã thu tiền xong, không khai thêm."})
    lit = _so(data.get("qty_l"), "qty_l") or 0
    if lit <= 0:
        raise HTTPException(422, {"ma": "THIEU_SO_LIT", "loi": "Phải khai đổ bao nhiêu lít."})
    diem = db.get(FuelPlace, data.get("place_id") or "")
    if not diem:
        raise HTTPException(422, {"ma": "THIEU_NOI_DO", "loi": "Phải chọn nơi đổ."})
    if diem.owner_type == "epl":
        raise HTTPException(422, {"ma": "NOI_DO_LA_KHO",
                                  "loi": "%s là kho của công ty, lĩnh dầu ở kho thì dùng phiếu đề nghị xuất kho nhiên liệu." % diem.name})
    e = TripEvent(trip_id=p.id, kind="refuel", note=(data.get("note") or "").strip() or None,
                  by_user=user.full_name, status="reported", qty_l=lit,
                  # C5.1: tài xế chỉ báo số lít (trạm ghi nợ, cuối tháng cấn trừ) — giá do kế toán kho xăng dầu nhập
                  reported_cost=(_so(data.get("unit_price"), "unit_price") or 0) if nhap_gia_chi(user.role) else 0,
                  currency=str(data.get("currency") or "VND").upper(), place_id=diem.id,
                  supplier_id=(data.get("supplier_id") or diem.supplier_id or None))
    if luc is not None:
        e.ts = luc                       # giờ máy lúc khai thật (hàng đợi mất mạng, 06/10)
    db.add(e)
    _ghi_log(db, p, user, "ev_refuel_reported", ts=luc)
    db.commit()
    return xuat_phieu(db, p, vai=user.role)


@router.post("/api/trips/{tid}/events/{eid}/duyet")
def duyet_bao_hong(tid: str, eid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """TỔ SỬA CHỮA duyệt báo hỏng của tài xế → mở phiếu, thêm dòng sửa chữa vào mục V với số tiền duyệt
    (mặc định = số tài xế báo). Nguồn: kho (chọn phụ tùng, trừ tồn ngay) hoặc mua ngoài. Hoặc TỪ CHỐI.

    Người duyệt là **tổ sửa chữa Thà Bốc** (`repair`), không phải Admin Bãi: anh Khampla C1.2 nói tổ sửa
    là người riêng, và chính họ mới biết hỏng gì, lấy phụ tùng kho hay mang ra gara.

    Khai đổ dầu dọc đường (kind='refuel') cũng duyệt ở đây, nhưng rơi vào MỤC III nguồn mua nên vẫn do
    Bãi hoặc KT kho xăng dầu duyệt. Sự cố không phải sửa chữa (kẹt đường, bị giữ xe, khác) rơi vào MỤC VI chi khác, do Bãi
    duyệt — xem `SU_CO_SUA_CHUA`."""
    p = db.get(Trip, tid)
    e = db.get(TripEvent, eid)
    if not p or not e or e.trip_id != p.id:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có báo hỏng này."})
    muc = muc_su_kien(e)
    duoc = DUYET_SU_KIEN[muc]
    if user.role not in duoc:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN",
                                  "loi": "Vai %s không được duyệt khai báo này." % user.role})
    if e.status != "reported":
        raise HTTPException(409, {"ma": "DA_XU_LY", "loi": "Báo hỏng này đã được xử lý (%s)." % e.status})
    e.approved_by, e.approved_at = user.full_name, dt.datetime.utcnow()
    if data.get("reject"):
        e.status = "rejected"; e.note = (e.note or "") + (" — " + data["reason"] if data.get("reason") else "")
        _ghi_log(db, p, user, "ev_rejected"); db.commit()
        return xuat_phieu(db, p, vai=user.role)
    if e.kind == "refuel":
        return _duyet_do_dau(db, p, e, data, user)
    if muc == "other":
        return _duyet_chi_khac(db, p, e, data, user)
    source = data.get("source") or "mua"
    if source not in ("kho", "mua"):
        raise HTTPException(422, {"ma": "NGUON_SAI", "loi": "Nguồn phải là kho hay mua."})
    qty = _so(data.get("qty"), "qty") or 1
    gia = _so(data.get("unit_price"), "unit_price")
    tien_te = str(data.get("currency") or e.currency or "LAK").upper()
    part = None
    if source == "kho":
        part = db.get(Part, data.get("part_id") or "")         # bản chép danh mục — tồn và giá ở trang kế toán
        if not part:
            raise HTTPException(422, {"ma": "THIEU_PHU_TUNG", "loi": "Lấy từ kho thì phải chọn phụ tùng."})
        gia = KK.gia_phu_tung(db, part.id)                           # lấy kho: giá bình quân của kho (30/09)
    if gia is None:
        gia = e.reported_cost if e.reported_cost is not None else None
    if gia is None:
        raise HTTPException(422, {"ma": "THIEU_GIA", "loi": "Chưa có số tiền: tài xế không báo và người duyệt chưa nhập."})
    truoc_khoa = BTC.dau_khoa(db, p)
    with KK.GiaoDichKho(db, user) as gd:
        so_dong = db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "repair").count()
        dong = TripExpense(trip_id=p.id, section="repair", line_no=so_dong + 1, item_key=None,
                           item_name=(data.get("item_name") or (part.name if part else e.note))[:120],
                           qty=qty, unit_price=gia, currency="LAK" if part else tien_te, paid_by_epl=True, source=source,
                           part_id=part.id if part else None, acct_code=ma_tk_mac_dinh(p.company, "repair", source),
                           note=(e.note or "") + (" — tài xế đã tự trả" if e.paid_by_driver else ""))
        db.add(dong); db.flush()
        if part:
            r = gd.xuat_phu_tung(khoa="trip_expense:" + dong.id, part_id=part.id, qty=qty, ngay=dt.date.today(),
                                 gia=dong.unit_price, tien_te=dong.currency, ty_gia=ty_gia(p, dong.currency),
                                 truck_no=p.truck_no, trip_doc_no=p.doc_no, expense_id=dong.id, company=p.company,
                                 section="repair", mo_ta="Xuất %s %s sửa xe %s" % (qty, part.name, p.truck_no),
                                 note="Sửa xe trên đường (tài xế báo) — %s" % (e.note or ""),
                                 owner_id=p.owner_id)   # xe thuê: đối tác của phiếu xuất bán bên kho anh Toàn (05/10)
            dong.stock_move_id = r["move_id"]
            if r.get("unit_price"):                             # kho QLSX (05/10): giá vốn bình quân bên đó lúc xuất
                dong.unit_price = r["unit_price"]
        e.status = "approved"; e.kind = "repair"; e.expense_id = dong.id
        BTC.chan_sua_sau_khoa(db, p, truoc_khoa)   # phiếu đã khoá: lệch bút toán khoá → 409, phụ tùng vừa xuất được trả lại kho
        s = _muc_cua(db, p)["repair"]
        if s.status not in ("wait", "entered"):
            _ghi_log(db, p, user, "sec_repair:reopen")
        rut_chi = s.status == "booked"
        s.status = "entered"
        if p.vehicle_id and e.incident_type == "breakdown":
            x = db.get(Vehicle, p.vehicle_id)
            if x: x.status = "maintenance"
        _ghi_log(db, p, user, "ev_approved")
    if rut_chi:
        CMT.rut_cho(db, p, "repair"); db.commit()   # có khoản sửa mới: phiếu chi chờ bên kế toán theo số cũ rút đi
    return xuat_phieu(db, p, vai=user.role)


# ---------------------------------------------------------------- chứng từ: phiếu chi tạm ứng & phiếu thu
@router.get("/api/trips/{tid}/phieu-chi")
def phieu_chi(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """PHIẾU CHI TẠM ỨNG cho tài xế — sinh ngay từ phiếu xuất xe: mọi khoản tiền mặt EPL ứng (dầu đổ
    trạm ngoài, đi đường, khác); KHÔNG gồm dầu kho và phụ tùng kho (đó là phiếu xuất kho). Trạng thái
    duyệt lấy theo mục IV của phiếu: đã nhập → đã kiểm → đã ghi sổ → đã chi (tài xế đã cầm tiền)."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _cua_tai_xe(db, p, user)
    dong = _dong_tam_ung(p, _dong_chi(db, p))
    r = {"USD": p.rate_usd or 22000, "THB": p.rate_thb or 700, "VND": p.rate_vnd or 1.2, "LAK": 1.0}
    ds = []
    tong = 0.0
    for d in dong:
        lak = (d.qty or 0) * (d.unit_price or 0) * r.get((d.currency or "LAK").upper(), 1.0)
        tong += lak
        ds.append({"section": d.section, "item_key": d.item_key, "item_name": d.item_name, "qty": d.qty, "unit_price": d.unit_price,
                   "currency": d.currency, "acct_code": TK.tk_dong(p.company, d), "tien_lak": round(lak)})
    tt = {s.section: s.status for s in _muc_cua(db, p).values()}
    if not thay_tien_chi(user.role):
        # Bãi in phiếu tạm ứng cho tài xế nhưng không thấy tiền (anh Khampla A2): chỉ khoản mục và số lượng —
        # số tiền quỹ thấy khi quét mã. Rà giao diện 23/09: phiếu này từng gửi đủ đơn giá, thành tiền cho Bãi.
        for x in ds:
            for c in ("unit_price", "currency", "acct_code", "tien_lak"): x.pop(c, None)
        tong = None
    return {"doc_no": p.doc_no, "so_phieu_chi": "PC-" + p.doc_no.replace("/", "-"), "doc_date": p.doc_date.isoformat() if p.doc_date else None,
            "driver_name": p.driver_name, "truck_no": p.truck_no, "plate_head": p.plate_head, "plate_trailer": p.plate_trailer,
            "origin": p.origin, "destination": p.destination, "company": p.company, "owner_name": p.owner_name,
            "hinh_thuc": hinh_thuc(p, "tam_ung"),
            "dong": ds, "tong_lak": round(tong) if tong is not None else None, "trang_thai": tt.get("travel", "wait"),
            "tra_tien_xong": tt.get("travel") == "paid", "created_by": p.created_by}


@router.get("/api/trips/{tid}/phieu-thu")
def phieu_thu(tid: str, user=Depends(nguoi_hien_tai)):
    """Phiếu thu tiền khách in ở hệ kế toán anh Tune (công nợ khách) từ 01/10 — trang này không thu tiền."""
    raise HTTPException(409, DA_DOI_HD)


@router.delete("/api/trips/{tid}")
def xoa_phieu(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Chỉ xoá được phiếu chưa mục nào qua bước kiểm và chưa xuất kho gì — đã kiểm là chứng từ, không xoá."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc hoặc Sếp xoá phiếu."})
    if any(s.status not in ("wait", "entered") for s in _muc_cua(db, p).values()) and user.role != "admin":
        raise HTTPException(409, {"ma": "DA_DUYET", "loi": "Phiếu đã có mục được kiểm, không xoá được."})
    if any(e.stock_move_id for e in _dong_chi(db, p)) and user.role != "admin":
        raise HTTPException(409, {"ma": "DA_XUAT_KHO", "loi": "Phiếu đã có dòng xuất kho, không xoá được."})
    _chan_khoa(p, user)
    # 01/10 (bỏ trang kế toán tạm): chặn theo những gì đã sang hệ anh Tune, không theo cờ hoá đơn trang tạm. Có SO (công nợ
    # khách) hay lần gửi SO chưa rõ kết quả → chặn cả Sếp: xoá phiếu là để lại SO mồ côi bên đó.
    so_kt = db.get(GuiSoTune, "EPLLAO-" + p.id)
    if so_kt is not None and (so_kt.status in ("synced", "conflict") or GT._chua_ro(so_kt)):
        raise HTTPException(409, {"ma": "DA_TAO_SO", "loi": "Phiếu %s đã gửi đề nghị thu sang bên công nợ (SO %s) — huỷ SO bên đó (đối soát) "
                                                            "trước." % (p.doc_no, so_kt.order_code or so_kt.status)})
    so_nl = NL.so_cua(db, p)
    if so_nl is not None and (so_nl.status in ("synced", "conflict") or NL._chua_ro(so_nl)):
        raise HTTPException(409, {"ma": "DA_TAO_SO", "loi": "Phiếu %s đã gửi SO nhiên liệu cho đối tác sang bên công nợ (SO %s) — huỷ SO bên "
                                                            "đó (đối soát) trước." % (p.doc_no, so_nl.order_code or so_nl.status)})
    if p.owner_payment_id or p.owner_paid:
        raise HTTPException(409, {"ma": "DA_TRA_CHU_XE", "loi": "Phiếu %s đã trả chủ xe ở hệ kế toán — đối soát phiếu chi bên đó trước." % p.doc_no})
    r = CHI._dang_giu(db, p.owner_id).get(p.id) if p.owner_id else None
    if r is not None:
        raise HTTPException(409, {"ma": "TRONG_DE_NGHI_TRA_CHU_XE", "loi": "Phiếu %s nằm trong đề nghị trả chủ xe %s — bỏ đề nghị đó "
                                                                          "ở màn Xe liên kết / Tất toán đối tác trước." % (p.doc_no, r.ref_no)})
    # Phiếu lĩnh / phiếu tạm ứng ĐÃ CẤP: dầu đã ra khỏi kho, tiền đã tới tay tài xế. Trước đây xoá phiếu thì máy chủ
    # vấp khoá ngoại fuel_moves → vouchers và trả 500 (rà 23/09). Bãi: chặn rõ ràng. Sếp: trả dầu về kho rồi xoá.
    from models import Voucher
    da_cap = db.query(Voucher).filter(Voucher.trip_id == p.id, Voucher.status == "da_cap").all()
    if da_cap and user.role != "admin":
        raise HTTPException(409, {"ma": "DA_CAP_PHAT", "loi": "Phiếu đã có %s được cấp (%s), không xoá được."
                                  % ("phiếu đề nghị xuất kho nhiên liệu / đề nghị tạm ứng", ", ".join(v.doc_no or v.id for v in da_cap))})
    # 05/10: dầu cấp ở kho QLSX anh Tune (stock_move_id "qlsx:<số phiếu kho>", services/ban_giao_dau) — bên này không trả kho bên đó
    # được; chặn cả Sếp để không còn phiếu xuất kho bên đó cho một phiếu đã xoá.
    from services import ban_giao_dau as BGD
    qlsx = sorted({e.stock_move_id[len(BGD.TIEN_TO_MV):] for e in _dong_chi(db, p)
                   if e.section == "fuel" and (e.stock_move_id or "").startswith(BGD.TIEN_TO_MV)})   # phụ tùng mục V: KK.huy_xuat lo
    if qlsx:
        raise HTTPException(409, {"ma": "DA_CAP_KHO_QLSX", "loi": "Phiếu %s đã cấp dầu ở kho bên kế toán (phiếu kho %s) — huỷ phiếu xuất kho bên "
                                                                  "đó trước." % (p.doc_no, ", ".join(qlsx))})
    # phiếu chi tạm ứng / chi mục V–VI bên hệ kế toán (01/10): chưa ghi sổ thì rút bên đó; đã chi thì chặn kể cả Sếp — tiền
    # đã ra khỏi quỹ
    CHI.rut(db, trip_id=p.id)
    CMT.rut(db, p.id)
    BTC.huy_khoa_phieu(db, p, user.full_name)
    id_v = [v.id for v in db.query(Voucher.id).filter(Voucher.trip_id == p.id).all()]
    if id_v:
        for m in db.query(FuelMove).filter(FuelMove.voucher_id.in_(id_v)).all():
            CT.rut(db, nguon_bang="fuel_moves", nguon_id=m.id)
            db.delete(m)
        db.flush()
    KH.kiem_xoa(db, p)
    # Phụ tùng mục V lấy từ kho (kho ở trang kế toán từ 28/09): trả về kho bên đó — trả tồn, rút tờ PXK_PT — như dầu
    # đã cấp được trả về kho ở trên. Trang kế toán tắt thì chưa xoá được phiếu (chặn và báo rõ): không để sổ bên kia
    # giữ tờ xuất kho cho một phiếu không còn.
    for e in _dong_chi(db, p):
        if e.section == "repair" and e.source == "kho" and e.stock_move_id:
            KK.huy_xuat(db, user, move_id=e.stock_move_id, khoa="trip_expense:" + e.id)   # kho QLSX: huỷ theo SourceRef
    # Dầu mục III đã xuất (ghi sổ, hoặc thủ kho cấp theo phiếu lĩnh): trả về kho bên trang kế toán, rút PXK_NL. Nhiều
    # dòng cùng một kho dùng chung một lần cấp → trả MỘT lần cho mỗi lần xuất.
    for mv in sorted({e.stock_move_id for e in _dong_chi(db, p) if e.section == "fuel" and e.source == "kho" and e.stock_move_id}):
        KK.huy_xuat_dau(db, user, move_id=mv)
    # Sổ kho hàng (05/10: goods_moves bên này — services/kho_hang_dia.huy): xoá dòng nhập / xuất / điều chỉnh của phiếu này, đơn
    # điều chỉnh của lô, rút tờ PNK_HH / PXK_HH / DC_HH chưa đối chiếu. Lô đã có phiếu giao khác lấy → 409 (KH.kiem_xoa ở trên).
    KH.xoa_so(db, p, user)
    _doi_trang_thai_xe_tai_xe(db, p, "available", "available")
    db.query(TripEvent).filter(TripEvent.trip_id == p.id).delete()
    for a in db.query(TripAttachment).filter(TripAttachment.trip_id == p.id).all():
        _xoa_tep_dia(a); db.delete(a)
    db.query(TripExpense).filter(TripExpense.trip_id == p.id).delete()
    db.query(TripSection).filter(TripSection.trip_id == p.id).delete()
    db.query(TripLog).filter(TripLog.trip_id == p.id).delete()
    CT.rut(db, trip_id=p.id)
    db.delete(p); db.commit()
    return {"ok": True}
