# -*- coding: utf-8 -*-
"""DÒNG TIỀN CỦA MỘT DO ĐÃ VÀO CHỨNG TỪ NÀO — cho màn "Tổng hợp thu chi" bên Web anh Tune (chủ dự án chốt 02/10/2026).

Kế toán chọn một DO, màn bên đó hiện các dòng Thu / Chi của gói bàn giao (services/ban_giao.dong_goi). Dòng đã thành chứng từ
thì hiện số và KHOÁ; chỉ dòng tiền CHƯA có chứng từ mới được lập phiếu — không bao giờ ghi sổ hai lần. Mỗi dòng mang thêm:

    line_key    khoá ổn định của dòng: cuoc:<Trip.id> · exp:<TripExpense.id> · thue:<Trip.id> (tiền thuê ở header.hire).
                Bên kia ghép header.line_key_prefix "DO:<do_id>:" + line_key làm SourceLineKey (≤ 100 ký tự).
    settlement  {state, kind, ref_no, doc_no, doc_status, label}
        state   has_voucher  đã có chứng từ bên kế toán (phiếu chi / thu đã tạo, bút toán đã nhận, SO đã tạo) → khoá
                pending      thuộc một đường tự động của bên em mà chứng từ chưa sang, hoặc chờ bước sau → vẫn khoá (lập tay là trùng)
                not_payable  EPL không chi tiền dòng này → khoá
                open         EPL chi mà chưa vào chứng từ / đường tự động nào → bên kia lập phiếu chi "Chi khác" được
        ref_no  số bên em (PTU-…, PCSC-…, EPLLAO-<nguon>-<ma_nguon>, TTX-…, TCX-…, PC_TU/…) · doc_no số bên kế toán (CTR-, CKH-,
                GL…, TK-…) · doc_status trạng thái bản ghi bên em · label câu tiếng Việt dự phòng (Web tự dịch theo kind / state)
    Dòng cước thêm `debt`: bản đọc lại thu tiền SO (gui_so_tune.thu_*) — chỉ để xem, bên anh Tune đọc dư nợ từ DB bên đó.

PHÂN DÒNG CHI — đọc BẢN GHI THẬT trước, rồi mới theo luật của chính các đường tự động (không viết lại công thức):
  1. xe thuê, chủ xe tự trả (paid_by_epl False — cùng cờ `paid_by` của gói) ......................... not_payable · owner_paid
  1b. xe thuê, dầu / phụ tùng kho EPL XUẤT BÁN cho đối tác (so_nhien_lieu.dong_ban) → sales_order theo SO NHIÊN LIỆU (02/10):
     SO đã tạo → has_voucher (doc_no = số SO), chưa → pending. Giá vốn 607/1371 của dòng vẫn là bút toán xuat_ban (journal).
  2. dòng nằm trong một bút toán chờ chưa huỷ (but_toan_cho nguồn no_ncc · xuat_noi_bo · xuat_ban, `dong[].ref` = id dòng)
     → journal: bên kia đã nhận (da_gui) thì has_voucher, còn cho_gui thì pending
  3. dòng nằm trong một phiếu chi "Chi khác" mục V chưa huỷ (chi_muc_tune.expense_ids) → pay_now: da_gui · da_chi has_voucher,
     loi pending
  4. dòng 0 đồng → not_payable
  5. dòng lấy kho đã rời kho chưa có bút toán — but_toan_cho.dong_xuat_kho nói bút toán nó PHẢI có → pending · journal (bút toán
     xuất kho ghi lúc khoá phiếu; phiếu khoá trước luật đó 01/10 thì không có)
  6. dòng Có 4021 (but_toan_cho.dong_khoa_phieu no_ncc: ghi nợ trạm, chipping, thẻ cao tốc, garage cho nợ…) chưa có bút toán
     → pending · journal. Dòng lấy kho còn lại (chưa rời kho, hoặc xuất theo sổ kho cũ) → pending · journal: không qua tiền
  7. dòng quỹ trả ngay mục V (chi_muc_tune.dong_quy_chi) chưa có phiếu chi → pending · pay_now (ghi sổ mục V là tự lập)
  8. tiền mặt tài xế cầm đi (tinh_toan.la_tien_mat_tai_xe — đúng luật tờ tạm ứng PTU và màn Tất toán) → advance: phiếu chi
     "Chi trước" bên kế toán (chi_tune). Dòng KHÔNG nằm trong số tiền đã ứng (dầu đổ dọc đường thêm sau lúc ứng — xem
     _trong_tam_ung): xe nhà → driver_settlement (tất toán tháng chi bù); xe thuê → open (EPL chưa đưa tiền mà đã trừ vào tiền
     trả chủ xe)
  9. trả theo chuyến cùng lương (tinh_toan.cach_tra "luong", chỉ xe nhà) → open · payroll — bên điều xe không lập chứng từ CHI
     TIỀN; từ 06/10 DO khoá có bút toán cung_luong Nợ 625 / Có 4201 (ghi chi phí) — vẫn open, label + ref_no / doc_no nói bút toán
     đó, gói mang pay_acc_code 4201/1011 (services/ban_giao.py)
 10. trừ thẻ cao tốc mà không có bút toán (mã người dùng tự chọn khác 4021) → not_payable · toll_card
 11. còn lại → open
CHI TẠI QUỸ TRANG ĐIỀU XE (trước 01/10, hoặc Sếp chi tay — routes/phieu.py, phieu_linh.cap_phat): tiền đã ra mà chỉ có tờ ở sổ
chứng từ bên em (bảng chung_tu: PC_TU, PC_SC, PXK_NL / PXK_PT), không có phiếu bên kế toán → pending, câu nói "đối soát, không
lập lại". Tờ đó từng sang trang kế toán tạm — số bên đó là số thử, không coi là chứng từ kế toán.
Tiền thuê xe liên kết (header.hire): settlement theo đề nghị trả chủ xe (chi_chu_xe_tune / trips.owner_payment_id) ·
owner_payment, kèm `journal` = bút toán thue_xe (Nợ 621 / Có 4022 + phí 4022 / 715 + quá tải 4022 / 758 từ 06/10). Xe thuê có xuất bán: header.fuel_so {order_code, total, paid,
remaining, status, read_at} — bản đọc lại thu tiền SO nhiên liệu (gui_so_nhien_lieu_tune).

Chỉ ĐỌC: không ghi gì, không hỏi sang hệ kế toán — trạng thái là bản chép lần đọc lại gần nhất của từng đường.
"""
import hashlib
import json
import re

from models import ButToanCho, ChiChuXeTune, ChiMucTune, ChiTune, ChungTu, FuelMove, PartMove, Voucher
from services import but_toan_cho as BTC
from services.tinh_toan import cach_tra, la_tien_mat_tai_xe, tien_dong

KHOA_HOP_LE = re.compile(r"^[A-Za-z0-9:_-]{1,60}$")
NGUON_DONG = (BTC.NO_NCC,) + BTC.NGUON_XUAT_KHO        # bút toán có dòng trỏ về TripExpense (`ref`)
TEN_NGUON = {BTC.NO_NCC: "Ghi nợ nhà cung cấp", BTC.XUAT_NOI_BO: "Xuất kho nội bộ", BTC.XUAT_BAN: "Xuất bán cho chủ xe",
             BTC.THUE_XE: "Chi phí thuê xe liên kết"}
HANG = {"da_chi": 3, "da_gui": 2, "loi": 1}             # nhiều lần cùng một dòng: lấy lần đi xa nhất
TEN_MUC = {"fuel": "III", "travel": "IV", "repair": "V", "other": "VI"}
DOI_SOAT = "chưa có phiếu bên kế toán; đối soát, không lập lại."


def khoa_dong(loai, ma):
    """line_key của một dòng: "<loai>:<mã>" — mã lạ (ký tự ngoài chữ / số / :_-, quá dài) thì băm, vẫn đứng yên giữa các lần đọc."""
    k = "%s:%s" % (loai, ma)
    if KHOA_HOP_LE.match(k):
        return k
    return "%s:h%s" % (loai, hashlib.sha1(str(ma).encode("utf-8")).hexdigest()[:20])


def tien_to(do_id):
    return "DO:%s:" % do_id


def _ket(state, kind, label, ref_no=None, doc_no=None, doc_status=None):
    return {"state": state, "kind": kind, "ref_no": ref_no, "doc_no": doc_no, "doc_status": doc_status, "label": label}


def _so(v):
    return "{:,.0f}".format(round(v or 0))


def _ten_no(d):
    """Tên khoản ghi nợ nhà cung cấp của một dòng — thẻ cao tốc, trạm dầu ghi nợ, hay nhà cung cấp theo đợt."""
    if getattr(d, "toll_card_id", None):
        return "Trừ thẻ cao tốc (ghi nợ nhà cung cấp thẻ)"
    if getattr(d, "ghi_no", False):
        return "Ghi nợ trạm / nhà cung cấp"
    return TEN_NGUON[BTC.NO_NCC]


# ================================================================ dòng thu cước
def cuoc(so):
    """(settlement, debt) của dòng cước theo lần gửi SO (GuiSoTune của DO)."""
    if so is None:
        return _ket("pending", "sales_order", "Chưa tạo SO — KT Thu/Chi bấm «Tạo SO bên kế toán» ở màn Đề nghị thu."), None
    if so.status == "synced":
        thu = {"da_thu": " · đã thu đủ", "thu_mot_phan": " · thu một phần", "chua_thu": " · chưa thu"}.get(so.thu_trang_thai, "")
        debt = {"order_code": so.order_code, "currency": so.currency, "total": so.thu_tong, "paid": so.thu_da_thu,
                "remaining": so.thu_con_no,
                "read_at": so.thu_doc_luc.replace(microsecond=0).isoformat() + "+00:00" if so.thu_doc_luc else None}
        return _ket("has_voucher", "sales_order", "Đã tạo SO %s bên kế toán%s" % (so.order_code or "—", thu),
                    doc_no=so.order_code, doc_status=so.status), debt
    if so.status == "conflict":
        return _ket("pending", "sales_order", "Gửi SO bị bên kế toán báo trùng (409) — hai bên đối soát, không lập lại.",
                    doc_status=so.status), None
    return _ket("pending", "sales_order", "Chưa tạo được SO (%s) — KT Thu/Chi gửi lại «Tạo SO bên kế toán» ở màn Đề nghị thu."
                % (so.error_message or so.error_code or "lỗi"), doc_status=so.status), None


# ================================================================ bút toán chờ
def _but_toan(r, ten):
    """settlement của một bút toán chờ (bản ghi thật)."""
    if r.status == "da_gui":
        dao = " — đang chờ bút toán đảo" if r.can_dao else ""
        return _ket("has_voucher", "journal", "%s — bút toán %s đã sang kế toán%s" % (ten, r.so_ben_ke_toan or r.ma_ben_ke_toan or "—", dao),
                    ref_no=r.source_ref, doc_no=r.so_ben_ke_toan, doc_status="can_dao" if r.can_dao else r.status)
    loi = " (lần gửi trước lỗi: %s)" % (r.loi_gui or r.error_code) if (r.loi_gui or r.error_code) else ""
    return _ket("pending", "journal", "%s — bút toán chờ gửi sang kế toán%s; không lập phiếu chi." % (ten, loi),
                ref_no=r.source_ref, doc_status=r.status)


def _but_toan_theo_dong(db, p):
    """{TripExpense.id: ButToanCho} — bút toán chưa huỷ của phiếu có dòng `ref` trỏ về dòng chi; đã gửi thắng chờ gửi."""
    ra = {}
    for r in (db.query(ButToanCho).filter(ButToanCho.trip_id == p.id, ButToanCho.nguon.in_(NGUON_DONG), ButToanCho.status != "huy")
              .order_by(ButToanCho.created_at)):
        try:
            dong = json.loads(r.dong or "[]")
        except ValueError:
            dong = []
        for x in dong:
            ref = x.get("ref") if isinstance(x, dict) else None
            if ref and (ref not in ra or (ra[ref].status != "da_gui" and r.status == "da_gui")):
                ra[ref] = r
    return ra


def _ma_ben_em(nguon, ma_nguon):
    """SourceRef bút toán SẼ mang khi được ghi (but_toan_cho._dat, phiên 1)."""
    return ("EPLLAO-%s-%s" % (nguon, ma_nguon))[:100]


# ================================================================ sổ chứng từ bên em — chi tại quỹ trang điều xe
def _to_quy(db, p, loai, nguon_id=None):
    """Tờ `loai` (PC_TU · PC_SC) của phiếu ở sổ chứng từ bên em — dấu vết quỹ trang điều xe đã chi tại chỗ."""
    q = db.query(ChungTu).filter(ChungTu.trip_id == p.id, ChungTu.loai == loai)
    if nguon_id is not None:
        q = q.filter(ChungTu.nguon_id == nguon_id)
    return q.order_by(ChungTu.ts.desc()).first()


def _xuat_kho_cu(db, p):
    """({TripExpense.id: tờ PXK_NL / PXK_PT}, {mục: [số tờ]}) — dòng kho xuất theo SỔ KHO CŨ của trang điều xe (fuel_moves /
    part_moves mang expense_id), trước khi kho dời sang kho tạm; dòng sổ không ghi expense_id (dữ liệu gieo tháng 8) thì chỉ
    biết tờ của phiếu theo mục."""
    cts = db.query(ChungTu).filter(ChungTu.trip_id == p.id, ChungTu.loai.in_(("PXK_NL", "PXK_PT"))).all()
    if not cts:
        return {}, {}
    theo = {c.nguon_id: c for c in cts}
    ra = {}
    for m in db.query(FuelMove).filter(FuelMove.id.in_([c.nguon_id for c in cts if c.nguon_bang == "fuel_moves"] or [""])):
        if m.expense_id:
            ra[m.expense_id] = theo[m.id]
    for m in db.query(PartMove).filter(PartMove.id.in_([c.nguon_id for c in cts if c.nguon_bang == "part_moves"] or [""])):
        if m.expense_id:
            ra[m.expense_id] = theo[m.id]
    muc = {}
    for c in sorted(cts, key=lambda c: c.so):
        muc.setdefault("fuel" if c.loai == "PXK_NL" else "repair", []).append(c.so)
    return ra, muc


# ================================================================ chi mục V quỹ trả ngay
def _chi_muc_theo_dong(db, p):
    """{TripExpense.id: ChiMucTune} — phiếu chi "Chi khác" mục V–VI chưa huỷ; một dòng nhiều lần thì lấy lần đi xa nhất."""
    ra = {}
    for r in db.query(ChiMucTune).filter(ChiMucTune.trip_id == p.id, ChiMucTune.status != "huy").order_by(ChiMucTune.lan):
        try:
            ids = json.loads(r.expense_ids or "[]")
        except ValueError:
            ids = []
        for i in ids:
            if i not in ra or HANG.get(r.status, 0) > HANG.get(ra[i].status, 0):
                ra[i] = r
    return ra


def _chi_muc(r):
    muc = TEN_MUC.get(r.section, r.section)
    if r.status in ("da_gui", "da_chi"):
        return _ket("has_voucher", "pay_now", "Quỹ trả ngay mục %s — phiếu chi «Chi khác» %s %s" % (
            muc, r.document_no or r.real_id or "", "đã chi" if r.status == "da_chi" else "chờ thủ quỹ chi"),
            ref_no=r.ref_no, doc_no=r.document_no, doc_status=r.status)
    return _ket("pending", "pay_now", "Quỹ trả ngay mục %s — phiếu chi chưa tạo được bên kế toán (%s); KT Chi phí gửi lại ở màn "
                "Phiếu đề nghị chi." % (muc, r.error_message or r.error_code or "lỗi"), ref_no=r.ref_no, doc_status=r.status)


# ================================================================ tạm ứng tiền mặt · tất toán tài xế
def _tam_ung(db, p):
    """(tờ PTU còn hiệu lực | None, phiếu chi "Chi trước" bên kế toán | None, tờ PC_TU quỹ trang điều xe đã chi | None).
    Một chuyến một tờ PTU (phieu_linh.dam_bao_tam_ung). PC_TU: quỹ chi tại chỗ theo tờ (nguồn vouchers) hoặc bấm thẳng "Chi
    tiền" mục IV (nguồn trip_sections — có khi không có tờ PTU)."""
    v = db.query(Voucher).filter(Voucher.trip_id == p.id, Voucher.kind == "advance").first()
    if v is not None and v.status == "huy":
        v = None
    rec = db.get(ChiTune, v.id) if v is not None else None
    ct = _to_quy(db, p, "PC_TU")
    return v, rec, ct


def _so_ung(v, rec, ct):
    """Số tiền đã ứng / sẽ ứng: phiếu chi bên kế toán (số đã gửi) › tờ PTU › tờ PC_TU quỹ đã chi."""
    if rec is not None and rec.amount_lak is not None:
        return rec.amount_lak
    if v is not None:
        return v.amount_lak
    return ct.tien_lak if ct is not None and ct.tien_lak is not None else (ct.tien if ct is not None else 0)


def _trong_tam_ung(p, tm, so_ung):
    """Những dòng tiền mặt (`tm`) nằm trong số tiền đã ứng `so_ung` → (tập id, khớp?).

    Tờ PTU chỉ giữ TỔNG (dam_bao_tam_ung: Σ la_tien_mat_tai_xe lúc ghi sổ mục IV; đã chi rồi thì đứng yên), không giữ dòng.
    Đối số: khớp tổng mọi dòng → cả thảy; khớp riêng mục IV + VI → dầu mục III mua dọc đường là tài xế tự trả, thêm sau lúc
    ứng (màn Tất toán chi bù phần đó); không khớp kiểu nào → coi mọi dòng thuộc tờ, báo lệch (đối soát)."""
    if abs(round(sum(tien_dong(p, d) for d in tm)) - round(so_ung or 0)) <= 1:
        return {d.id for d in tm}, True
    iv = [d for d in tm if d.section in ("travel", "other")]
    if iv and len(iv) < len(tm) and abs(round(sum(tien_dong(p, d) for d in iv)) - round(so_ung or 0)) <= 1:
        return {d.id for d in iv}, True
    return {d.id for d in tm}, False


def _tam_ung_dong(p, v, rec, ct, khop, so_ung, tong_tm):
    """settlement của một dòng thuộc số đã ứng (tờ PTU `v` / phiếu chi `rec` / tờ PC_TU `ct`)."""
    lech = "" if khop else " · số đã ứng %s LAK ≠ tiền mặt hiện tại %s LAK — %s" % (
        _so(so_ung), _so(tong_tm), "phần chênh tính lúc tất toán tháng" if p.company != "joint" else "đối soát với kế toán")
    ten = v.doc_no if v is not None else "mục IV"
    if rec is not None and rec.status in ("da_gui", "da_chi"):
        return _ket("has_voucher", "advance", "Tạm ứng %s — phiếu chi «Chi trước» %s %s%s" % (
            ten, rec.document_no or rec.real_id or "", "đã chi" if rec.status == "da_chi" else "chờ thủ quỹ chi", lech),
            ref_no=v.doc_no, doc_no=rec.document_no, doc_status=rec.status)
    if rec is not None:
        return _ket("pending", "advance", "Tạm ứng %s — phiếu chi chưa tạo được bên kế toán (%s); KT Chi phí gửi lại%s." % (
            ten, rec.error_message or rec.error_code or "lỗi", lech), ref_no=v.doc_no, doc_status=rec.status)
    if ct is not None or (v is not None and v.status == "da_cap"):
        return _ket("pending", "advance", "Tạm ứng %s đã chi tại quỹ trang điều xe%s%s — %s" % (
            ten, (" (%s)" % ct.so) if ct is not None else "", lech, DOI_SOAT),
            ref_no=v.doc_no if v is not None else ct.so, doc_status="chi_tai_quy")
    return _ket("pending", "advance", "Tạm ứng %s — phiếu chi «Chi trước» lập khi KT Chi phí ghi sổ mục IV; không lập tay%s." % (ten, lech),
                ref_no=v.doc_no, doc_status=v.status)


def _tat_toan(db, p):
    """settlement của dòng tài xế tự trả (xe nhà, ngoài số đã ứng) — tất toán tháng của tài xế, kỳ = tháng xe đi
    (routes/tat_toan._trong_ky): phiếu chi bù / thu hoàn bên kế toán, không có phiếu (chênh dưới 1 Kíp) thì bút toán QT_TU."""
    from services import chi_tat_toan_tune as CTT
    ngay = p.out_date or p.doc_date
    ky = ngay.strftime("%Y-%m") if ngay else None
    x = CTT._ban_chot(db, p.driver_id, ky) if (ky and p.driver_id) else None
    if x is None:
        return _ket("pending", "driver_settlement", "Tài xế tự trả (ngoài tạm ứng) — chờ tất toán kỳ %s ở màn Tất toán; không lập "
                    "phiếu chi." % (ky or "—"))
    rec, bt = CTT._phieu_tt(db, x), CTT._but_toan_tt(db, x)
    if rec is not None and rec.status in ("da_gui", "da_chi"):
        return _ket("has_voucher", "driver_settlement", "Tài xế tự trả (ngoài tạm ứng) — tất toán kỳ %s: phiếu %s %s %s" % (
            ky, "chi bù" if rec.loai == "TT_CHI" else "thu hoàn", rec.document_no or rec.real_id or "",
            "đã chi" if rec.status == "da_chi" else "chờ thủ quỹ"), ref_no=rec.ref_no, doc_no=rec.document_no, doc_status=rec.status)
    if rec is None and bt is not None and bt.status == "da_gui":
        return _ket("has_voucher", "driver_settlement", "Tài xế tự trả (ngoài tạm ứng) — quyết toán tạm ứng kỳ %s, bút toán %s" % (
            ky, bt.so_ben_ke_toan or ""), ref_no=bt.source_ref, doc_no=bt.so_ben_ke_toan, doc_status=bt.status)
    ref = rec.ref_no if rec is not None else (bt.source_ref if bt is not None else None)
    loi = (" (%s)" % (rec.error_message or rec.error_code)) if rec is not None and rec.status == "loi" else ""
    return _ket("pending", "driver_settlement", "Tài xế tự trả (ngoài tạm ứng) — đã chốt tất toán kỳ %s, chứng từ chưa sang kế "
                "toán%s; không lập phiếu chi." % (ky, loi),
                ref_no=ref, doc_status=rec.status if rec is not None else (bt.status if bt is not None else x.status))


# ================================================================ SO nhiên liệu cho đối tác (02/10)
def so_nl(b):
    """settlement của dòng xuất bán cho đối tác theo lần gửi SO nhiên liệu của DO."""
    if b is not None and b.status == "synced":
        con = "" if b.thu_con_no is None else " · còn nợ %s %s" % (_so(b.thu_con_no), b.currency or "LAK")
        return _ket("has_voucher", "sales_order", "Xuất bán cho đối tác — SO nhiên liệu %s%s (giá vốn: bút toán xuất kho)" % (
            b.order_code or "—", con), doc_no=b.order_code, doc_status=b.status)
    if b is not None and b.status == "conflict":
        return _ket("pending", "sales_order", "Xuất bán cho đối tác — gửi SO nhiên liệu bị bên kế toán báo trùng (409); đối soát, không "
                    "lập lại.", doc_status=b.status)
    if b is not None:
        return _ket("pending", "sales_order", "Xuất bán cho đối tác — chưa tạo được SO nhiên liệu (%s); KT Thu/Chi bấm lại «Tạo SO bên kế "
                    "toán» ở màn Đề nghị thu." % (b.error_message or b.error_code or "lỗi"), doc_status=b.status)
    return _ket("pending", "sales_order", "Xuất bán cho đối tác — chưa tạo SO nhiên liệu; KT Thu/Chi bấm «Tạo SO bên kế toán» ở màn Đề "
                "nghị thu (cùng SO cước).")


def fuel_so(b):
    """header.fuel_so của gói DO — None khi DO chưa gửi SO nhiên liệu."""
    if b is None:
        return None
    return {"order_code": b.order_code if b.status == "synced" else None, "status": b.status, "currency": b.currency or "LAK",
            "total": b.total_amount if b.status == "synced" else None, "paid": b.thu_da_thu, "remaining": b.thu_con_no,
            "read_at": b.thu_doc_luc.replace(microsecond=0).isoformat() + "+00:00" if b.thu_doc_luc else None}


# ================================================================ tiền thuê xe liên kết (header.hire)
def thue(db, p):
    """(settlement trả chủ xe, settlement bút toán thue_xe) của phiếu xe thuê."""
    bt = db.query(ButToanCho).filter(ButToanCho.nguon == BTC.THUE_XE, ButToanCho.ma_nguon == p.id, ButToanCho.status != "huy").first()
    ten = TEN_NGUON[BTC.THUE_XE]
    nk = _but_toan(bt, ten) if bt is not None else _ket(
        "pending", "journal", "%s — chưa có bút toán thuê xe Nợ 621 / Có 4022 (kèm phí quản lý Nợ 4022 / Có 715, cắt quá tải Nợ 4022 / Có 758 — 06/10) — ghi lúc khoá phiếu." % ten, ref_no=_ma_ben_em(BTC.THUE_XE, p.id))
    tot = None
    if p.owner_id:
        for r in db.query(ChiChuXeTune).filter(ChiChuXeTune.owner_id == p.owner_id, ChiChuXeTune.status != "huy"):
            try:
                ids = json.loads(r.trip_ids or "[]")
            except ValueError:
                ids = []
            if p.id in ids and (tot is None or HANG.get(r.status, 0) > HANG.get(tot.status, 0)):
                tot = r
    if tot is not None and tot.status in ("da_gui", "da_chi"):
        if tot.status == "da_chi" and not (tot.document_no or tot.real_id):
            # 02/10: cấn trừ hết SO nhiên liệu — đề nghị xong không có phiếu chi
            tra = _ket("has_voucher", "owner_payment", "Trả chủ xe %s — đã cấn trừ hết vào SO nhiên liệu (đề nghị %s), không có phiếu chi" % (
                p.owner_name or "", tot.ref_no), ref_no=tot.ref_no, doc_status=tot.status)
        else:
            tra = _ket("has_voucher", "owner_payment", "Trả chủ xe %s — phiếu chi «Chi khác» %s %s" % (
                p.owner_name or "", tot.document_no or tot.real_id or "", "đã chi" if tot.status == "da_chi" else "chờ thủ quỹ chi"),
                ref_no=tot.ref_no, doc_no=tot.document_no, doc_status=tot.status)
    elif tot is not None:
        tra = _ket("pending", "owner_payment", "Đề nghị trả chủ xe %s chưa tạo được phiếu chi bên kế toán (%s) — KT Thu/Chi gửi lại ở "
                   "màn Xe liên kết." % (tot.ref_no, tot.error_message or tot.error_code or "lỗi"), ref_no=tot.ref_no, doc_status=tot.status)
    elif (p.owner_payment_id or "").startswith("TUNE:"):
        tra = _ket("has_voucher", "owner_payment", "Đã trả chủ xe — phiếu chi %s" % p.owner_payment_id[5:],
                   doc_no=p.owner_payment_id[5:], doc_status="da_chi")
    elif p.owner_paid or p.owner_payment_id:
        tra = _ket("pending", "owner_payment", "Đã trả chủ xe ở trang kế toán tạm (trước khi chi qua hệ kế toán) — " + DOI_SOAT,
                   ref_no=p.owner_payment_id, doc_status="owner_paid")
    else:
        tra = _ket("pending", "owner_payment", "Chưa đề nghị trả chủ xe — KT Thu/Chi lập ở màn Xe liên kết; không lập tay.")
    return tra, nk


# ================================================================ gắn vào gói bàn giao
def gan(db, p, goi, dong, so):
    """Gắn line_key + settlement vào từng dòng của gói `{header, details}` (sửa tại chỗ). `dong` = dòng chi của phiếu (cùng
    danh sách dong_goi dựng details), `so` = lần gửi SO của DO (GuiSoTune | None)."""
    from services import so_nhien_lieu as NL
    h = goi["header"]
    h["line_key_prefix"] = tien_to(h["do_id"])
    lk = p.company == "joint"
    if lk and isinstance(h.get("hire"), dict):
        h["hire"]["line_key"] = khoa_dong("thue", p.id)
        h["hire"]["settlement"], h["hire"]["journal"] = thue(db, p)
    ban = {d.id for d in NL.dong_ban(p, dong)} if lk else set()
    nl = NL.so_cua(db, p) if lk else None
    h["fuel_so"] = fuel_so(nl)

    theo_id = {d.id: d for d in dong}
    bt, cm = _but_toan_theo_dong(db, p), _chi_muc_theo_dong(db, p)
    nho = {}

    def mot_lan(k, ham):
        if k not in nho:
            nho[k] = ham()
        return nho[k]

    # luật của các đường tự động và sổ chứng từ cũ — chỉ dựng khi có dòng chưa thấy trong bản ghi thật
    def xuat_kho():
        return {x["ref"]: (n, m) for (n, m), (_, ds, _) in BTC.dong_xuat_kho(db, p, dong).items() for x in ds}

    def no_ncc():
        return {x["ref"] for x in BTC.dong_khoa_phieu(db, p, dong).get(BTC.NO_NCC, ([], None))[0]}

    def quy_chi():
        from services import chi_muc_tune as CMT
        return {d.id for m in CMT.MUC for d in CMT.dong_quy_chi(db, p, m, dong)}

    def tam_ung():
        v, rec, ct = _tam_ung(db, p)
        tm = [d for d in dong if la_tien_mat_tai_xe(d, p.company)]
        if v is None and ct is None:
            return v, rec, ct, set(), True, 0, tm
        so_ung = _so_ung(v, rec, ct)
        trong, khop = _trong_tam_ung(p, tm, so_ung)
        return v, rec, ct, trong, khop, so_ung, tm

    def chia(d):
        if lk and d.paid_by_epl is False:
            return _ket("not_payable", "owner_paid", "Chủ xe tự trả — không phải tiền của EPL.")
        if d.id in ban:
            return so_nl(nl)
        if d.id in bt:
            r = bt[d.id]
            return _but_toan(r, _ten_no(d) if r.nguon == BTC.NO_NCC else TEN_NGUON.get(r.nguon, r.nguon))
        if d.id in cm:
            return _chi_muc(cm[d.id])
        if round(tien_dong(p, d)) <= 0:
            return _ket("not_payable", None, "Dòng 0 đồng — không có tiền để chi.")
        xk = mot_lan("xuat_kho", xuat_kho)
        if d.id in xk:
            n, m = xk[d.id]
            c = mot_lan("kho_cu", lambda: _xuat_kho_cu(db, p))[0].get(d.id)
            ten = "%s%s" % (TEN_NGUON[n], (" (sổ kho cũ %s)" % c.so) if c is not None else "")
            if not p.locked:
                # 06/10: B2 trả cả DO đang chạy — chưa có bút toán là ĐÚNG (bút toán xuất kho ghi lúc khoá DO), không phải lệch cần
                # đối soát như phiếu khoá trước luật 01/10
                return _ket("pending", "journal", "%s — bút toán xuất kho ghi lúc khoá DO (DO chưa khoá); không lập phiếu chi." % ten,
                            ref_no=_ma_ben_em(n, m))
            return _ket("pending", "journal", "%s — chưa có bút toán xuất kho (ghi lúc khoá phiếu; phiếu khoá trước khi có luật bút "
                        "toán xuất kho); đối soát với kế toán, không lập phiếu chi." % ten, ref_no=_ma_ben_em(n, m))
        if d.id in mot_lan("no_ncc", no_ncc):
            return _ket("pending", "journal", "%s — chưa có bút toán (ghi lúc khoá phiếu); không lập phiếu chi, trả nhà cung cấp theo "
                        "đợt." % _ten_no(d), ref_no=_ma_ben_em(BTC.NO_NCC, p.id))
        if d.source == "kho":
            theo_dong, theo_muc = mot_lan("kho_cu", lambda: _xuat_kho_cu(db, p))
            c = theo_dong.get(d.id)
            if c is not None:
                return _ket("pending", "journal", "Xuất kho theo sổ kho cũ (%s) — chưa có bút toán xuất kho bên kế toán; đối soát, không "
                            "lập phiếu chi." % c.so, ref_no=c.so, doc_status="so_kho_cu")
            cu = theo_muc.get(d.section)
            return _ket("pending", "journal", "Lấy kho, chưa có lần xuất ở kho tạm%s — chưa có bút toán xuất kho bên kế toán; đối soát, "
                        "không lập phiếu chi." % ((" (tờ xuất kho cũ của phiếu: %s)" % ", ".join(cu)) if cu else ""))
        if d.id in mot_lan("quy_chi", quy_chi):
            c = mot_lan("pc_sc:" + d.section, lambda: _to_quy(db, p, "PC_SC", "%s:%s" % (p.id, d.section)))
            if c is not None:
                return _ket("pending", "pay_now", "Quỹ trả ngay mục %s đã chi tại quỹ trang điều xe (%s) — %s" % (
                    TEN_MUC.get(d.section, d.section), c.so, DOI_SOAT), ref_no=c.so, doc_status="chi_tai_quy")
            return _ket("pending", "pay_now", "Quỹ trả ngay mục %s — phiếu chi «Chi khác» lập khi KT Chi phí ghi sổ mục; không lập "
                        "tay." % TEN_MUC.get(d.section, d.section))
        if la_tien_mat_tai_xe(d, p.company):
            v, rec, ct, trong, khop, so_ung, tm = mot_lan("tam_ung", tam_ung)
            if d.id in trong:
                return _tam_ung_dong(p, v, rec, ct, khop, so_ung, sum(tien_dong(p, x) for x in tm))
            if not lk:
                return dict(mot_lan("tat_toan", lambda: _tat_toan(db, p)))      # bản riêng mỗi dòng
            return _ket("open", "advance", "Tiền mặt EPL ứng mà không nằm trong số đã ứng%s — EPL chưa đưa tiền; lập phiếu chi nếu "
                        "EPL trả." % ((" (tờ %s)" % v.doc_no) if v is not None else ""), ref_no=v.doc_no if v is not None else None)
        if getattr(d, "toll_card_id", None):
            return _ket("not_payable", "toll_card", "Trừ vào thẻ cao tốc — không chi tiền theo chuyến.")
        # phiếu từng chi tại quỹ trang điều xe (tờ PC_TU, trước 01/10 hoặc Sếp chi tay): luật tạm ứng cũ có khi gom cả tiền
        # nước / tiền chuyến vào tờ đó — không chắc dòng còn lại chưa chi, nên khoá, đối soát (không mở cho bên kia lập phiếu)
        c = mot_lan("pc_tu", lambda: _to_quy(db, p, "PC_TU"))
        if c is not None:
            return _ket("pending", "payroll" if cach_tra(d, p.company) == "luong" else None,
                        "Phiếu có tờ chi tại quỹ trang điều xe (%s) theo luật cũ — dòng này có thể đã chi trong tờ đó; %s" % (c.so, DOI_SOAT),
                        ref_no=c.so, doc_status="chi_tai_quy")
        if d.section in ("travel", "other") and cach_tra(d, p.company) == "luong":
            # 06/10: DO khoá từ bản sửa đã ghi chi phí Nợ 625 / Có 4201 (bút toán cung_luong — KHÔNG phải chứng từ chi tiền, dòng
            # vẫn open để Web lập phiếu chi lương); gói mang pay_acc_code 4201/1011 → phiếu chi Nợ 4201 / Có tiền
            r = mot_lan("cung_luong", lambda: BTC.cung_luong_da_ghi(db, p.id)).get(d.id)
            if r is not None:
                return _ket("open", "payroll", "Trả theo chuyến cùng lương — chi phí đã ghi lúc khoá DO (Nợ 625 / Có 4201, bút toán %s); "
                            "kế toán lập phiếu chi lương Nợ 4201 / Có tiền khi trả." % (r.so_ben_ke_toan or r.source_ref),
                            ref_no=r.source_ref, doc_no=r.so_ben_ke_toan, doc_status=r.status)
            return _ket("open", "payroll", "Trả theo chuyến cùng lương — trang điều xe không lập chứng từ cho khoản này; kế toán lập "
                        "phiếu chi khi trả.")
        return _ket("open", None, "Chưa vào chứng từ nào bên kế toán.")

    for x in goi["details"]:
        if x.get("kind") == "thu":
            x["line_key"] = khoa_dong("cuoc", p.id)
            x["settlement"], x["debt"] = cuoc(so)
            continue
        d = theo_id.get(x.get("ref_id"))
        x["line_key"] = khoa_dong("exp", x.get("ref_id"))
        # không thấy dòng (không xảy ra — details dựng từ chính `dong`): khoá cho chắc, không để bên kia lập phiếu mù
        x["settlement"] = chia(d) if d is not None else _ket("pending", None, "Không đọc được dòng chi này — đối soát.")
    return goi
