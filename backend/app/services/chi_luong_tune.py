# -*- coding: utf-8 -*-
"""TRẢ CÙNG LƯƠNG — đọc lại phiếu chi lương THẬT bên hệ kế toán anh Tune theo từng dòng (06/10/2026).

Em chính chốt 06/10: tiền chưa trả cho tài xế thì báo cáo không được ghi "đã chi". Khoản "trả theo chuyến cùng lương" (mục IV,
cách trả `luong`, chỉ xe nhà — tinh_toan.cach_tra) KHÔNG đi qua phiếu chi nào của trang điều xe: kế toán lập phiếu chi trên WEB anh
Tune theo DO (hộp "Tạo phiếu chi theo DO" → phiếu "Chi khác" CKH, gộp các dòng theo khoá B2 `DO:EPLLAO-<trip>:exp:<id>` —
ban_giao.trang_thai_chi.open_line_keys). Mục IV vẫn tự qua bước Chi lúc ghi sổ khi chỉ có khoản cùng lương (routes/phieu.py, giữ
nguyên) — đó là trạng thái DUYỆT của mục, không phải tiền đã tới tay tài xế. Báo cáo Tiền chuyến & nước tài xế (routes/bao_cao.py)
đọc tiền theo PHIẾU THẬT ở bảng chi_luong_tune do module này ghi:

    da_tra   phiếu chứa dòng đã ghi sổ (ST 12 / 13 — chi_tune.DA_GHI_SO): số phiếu, lúc ghi sổ
    cho      chưa nằm phiếu nào, hoặc phiếu chưa ghi sổ (ST 1)          → "Chờ trả cùng lương"
    (không có dòng ở bảng: chưa hỏi lần nào → cũng là chờ)

Đường bên API anh Tune (chỉ đọc, thêm 06/10): POST /api/v1/integrations/logistics/line-vouchers {"Keys": [≤ 500 khoá]} →
Result {KeyCount, Items: [{Key, DocumentId, VoucherNo, StatusId, Posted, PostedAt, BaseAmount, CurrencyId}]} — dùng lại hàm
GetLineVouchersByKeysAsync (cùng hàm viên trạng thái chi của Vụ việc DO bên Web). Cổng: mục cấu hình LogisticsJournalEntry
(AllowedUserIds) — cùng tài khoản tích hợp gửi bút toán chờ. Token, gốc API dùng chung chi_tune._goi / gui_tune.cau_hinh.

Luồng nền (services/dong_bo_nen.py, loại "chi_luong") gọi `dong_bo` mỗi lượt: các dòng cùng lương của DO đã ghi sổ mục IV mà chưa
"đã trả", hỏi lâu nhất trước, theo lô 500 khoá. Dòng đã "đã trả" không hỏi lại. BẬT bằng EPL_DONG_BO_CHI_LUONG=1 trong .env — chỉ
bật sau khi API anh Tune đang chạy đã có đường line-vouchers (bản cũ trả 404: mỗi lượt sẽ ghi lỗi).
"""
import datetime as dt
import os

from sqlalchemy import and_, func, or_

from models import ChiLuongTune, Trip, TripExpense, TripSection

DUONG = "/api/v1/integrations/logistics/line-vouchers"
LO = 500                                  # khoá mỗi lần gọi — LogisticsLineVoucherLimits.MaxKeys bên API
# Khoản "của tài xế" trên màn Tiền chuyến & nước (mục IV): tiền chuyến, tiền nước, đi VN, điện thoại, ăn — routes/bao_cao.py dùng chung
KHOAN_TAI_XE = {"x_trip", "x_water", "x_vn", "x_phone", "x_food"}
MUC_IV_DA_GHI_SO = ("booked", "paid")     # mục IV đã ghi sổ (paid = tự qua bước Chi khi chỉ có khoản cùng lương)


def bat():
    """Luồng nền có hỏi loại chi_luong không — EPL_DONG_BO_CHI_LUONG=1 (mặc định TẮT tới khi API anh Tune chạy bản có đường)."""
    return (os.getenv("EPL_DONG_BO_CHI_LUONG") or "").strip().lower() in ("1", "true", "bat", "on")


def khoa_dong(trip_id, line_id):
    """Khoá dòng B2 của một dòng chi — đúng khuôn ban_giao.trang_thai_chi.open_line_keys (`DO:EPLLAO-<trip>:exp:<id>`)."""
    from services import ban_giao as BG
    from services import chung_tu_dong_do as CTD
    return CTD.tien_to(BG.TIEN_TO + trip_id) + CTD.khoa_dong("exp", line_id)


def _loc_luong():
    """Điều kiện SQL thô cho "cách trả cùng lương" (tinh_toan.cach_tra): chọn `luong`, hoặc không chọn mà khoản mặc định là luong.
    Lọc lại bằng chính cach_tra trong Python — SQL chỉ để khỏi kéo cả bảng."""
    from services.tinh_toan import CACH_TRA, CACH_TRA_MAC_DINH
    mac_dinh = [k for k, v in CACH_TRA_MAC_DINH.items() if v == "luong"]
    return or_(TripExpense.pay_channel == "luong",
               and_(or_(TripExpense.pay_channel.is_(None), TripExpense.pay_channel.notin_(CACH_TRA)),
                    TripExpense.item_key.in_(mac_dinh)))


def dong_cho(db, n):
    """Các dòng cùng lương chờ hỏi, lâu nhất trước: xe nhà, mục IV đã ghi sổ, dòng EPL ứng, khoản tài xế, cách trả luong, tiền > 0,
    chưa "đã trả". → [(TripExpense.id, Trip.id, Trip.doc_date)]."""
    from services.tinh_toan import cach_tra
    q = (db.query(TripExpense.id, TripExpense.trip_id, TripExpense.item_key, TripExpense.pay_channel, Trip.company, Trip.doc_date)
         .join(Trip, Trip.id == TripExpense.trip_id)
         .join(TripSection, and_(TripSection.trip_id == Trip.id, TripSection.section == "travel"))
         .outerjoin(ChiLuongTune, ChiLuongTune.line_id == TripExpense.id)
         .filter(TripSection.status.in_(MUC_IV_DA_GHI_SO), TripExpense.section == "travel", TripExpense.paid_by_epl.is_(True),
                 TripExpense.item_key.in_(KHOAN_TAI_XE), or_(Trip.company.is_(None), Trip.company != "joint"), _loc_luong(),
                 func.coalesce(TripExpense.qty, 0) * func.coalesce(TripExpense.unit_price, 0) > 0,
                 or_(ChiLuongTune.status.is_(None), ChiLuongTune.status != "da_tra"))
         .order_by(ChiLuongTune.checked_at.asc().nullsfirst(), Trip.doc_date, TripExpense.id)
         .limit(n))
    return [(r.id, r.trip_id, r.doc_date) for r in q if cach_tra(r, r.company) == "luong"]


def doc_phieu(keys):
    """Một lần gọi đường đọc bên API anh Tune → {khoá: Item} — mỗi khoá lấy phiếu ĐÃ GHI SỔ nếu có, không thì phiếu đầu (API xếp
    sẵn: khoá, đã ghi sổ trước). Lỗi mạng / HTTP → HTTPException của chi_tune._goi (5xx = lỗi bên kia, 4xx = từ chối)."""
    from services import chi_tune as CHI
    kq = CHI._goi("POST", DUONG, {"Keys": list(keys)}) or {}
    ra = {}
    for it in (kq.get("Items") or []):
        k = it.get("Key") if isinstance(it, dict) else None
        if not k:
            continue
        if k not in ra or (_da_ghi_so(it) and not _da_ghi_so(ra[k])):
            ra[k] = it
    return ra


def _da_ghi_so(it):
    from services import chi_tune as CHI
    try:
        return bool(it.get("Posted")) or int(it.get("StatusId") or 0) in CHI.DA_GHI_SO
    except (TypeError, ValueError):
        return False


def dong_bo(db, n):
    """Hỏi lại tối đa max(n, LO) dòng chờ (một lô 500 khoá là một lần gọi) và ghi chi_luong_tune. Dòng chuyển trạng thái (chờ ↔ đã
    trả) thì báo bộ đệm báo cáo NGÀY của phiếu đó đổi (dem_bao_cao.danh_dau_doi) — ghi checked_at thôi thì không. Commit sau mỗi lô.
    → {"da_hoi": số dòng đã hỏi, "cap_nhat": số dòng đổi trạng thái}. Lỗi gọi API ném ra (bên gọi quyết định dừng lượt)."""
    from services import chi_tune as CHI
    from services import dem_bao_cao as DEM
    ds = dong_cho(db, max(int(n or 0), LO))
    ket = {"da_hoi": 0, "cap_nhat": 0}
    for i in range(0, len(ds), LO):
        lo = [(khoa_dong(tid, lid), lid, tid, ngay) for lid, tid, ngay in ds[i:i + LO]]
        tim = doc_phieu([k for k, _, _, _ in lo])
        luc = dt.datetime.utcnow()
        doi_ngay = []
        co = {r.line_id: r for r in db.query(ChiLuongTune).filter(ChiLuongTune.line_id.in_([x[1] for x in lo]))}   # một câu cho cả lô
        for k, lid, tid, ngay in lo:
            rec = co.get(lid)
            if rec is None:
                rec = ChiLuongTune(line_id=lid, trip_id=tid, status="cho")
                db.add(rec)
            truoc = rec.status
            it = tim.get(k)
            rec.line_key, rec.checked_at = k, luc
            rec.voucher_no = (it.get("VoucherNo") or None) if it else None
            rec.document_id = int(it.get("DocumentId") or 0) or None if it else None
            rec.tune_status = int(it.get("StatusId") or 0) or None if it else None
            rec.amount_base = float(it.get("BaseAmount") or 0) if it else None
            if it and _da_ghi_so(it):
                rec.status, rec.posted_at = "da_tra", CHI._ngay_gio(it.get("PostedAt"))
            else:
                rec.status, rec.posted_at = "cho", None
            if rec.status != truoc:
                ket["cap_nhat"] += 1
                if ngay:
                    doi_ngay.append(ngay)
        DEM.danh_dau_doi(db, doi_ngay)
        db.commit()
        ket["da_hoi"] += len(lo)
    return ket

