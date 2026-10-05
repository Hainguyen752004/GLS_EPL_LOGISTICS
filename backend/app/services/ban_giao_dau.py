# -*- coding: utf-8 -*-
"""BÀN GIAO PHIẾU ĐỀ NGHỊ XUẤT KHO NHIÊN LIỆU (PLNL) cho kho của hệ anh Tune (QLSX) — chủ dự án duyệt 05/10: kho EPL làm thẳng
trên source anh Tune, bỏ kho tạm EPL_KETOAN 8031. Thủ kho mở màn "Quản lý kho" bên Web anh Tune, bấm "Cấp dầu theo phiếu đề
nghị": API bên đó đọc phiếu ở đây (goi), lập phiếu xuất kho 48 bên đó (SourceRef = source_ref(v), giá vốn bình quân di động của
đúng kho), rồi báo về đây (ghi_da_cap) — thay cho nhánh dầu của routes/phieu_linh.cap_phat (đi qua kho tạm).

GIAO ƯỚC (routes/ban_giao_dau.py gọi — giữ cố định):

    source_ref(v) -> str            khoá chống trùng bên kho QLSX: số PLNL, ký tự ngoài [A-Za-z0-9_.:-] đổi thành "." (≤ 100)
    goi(db, v, p=None) -> dict      gói một phiếu (xem _goi): DO, xe, xe nhà / xe thuê, đối tác, tài xế, kho, lít, dòng, cấp được không
    danh_sach(db, status, q, kho, page, page_size) -> (tong, [dict])
    ghi_da_cap(db, v, d) -> dict    báo đã cấp; gọi lại cùng số phiếu kho → trả lại, không ghi lần hai (replayed = True)
    tim(db, ref) -> Voucher | None  tờ PLNL theo mã tờ HOẶC SourceRef (bên kho chỉ giữ SourceRef)
    ghi_da_huy(db, ref, d) -> dict  phiếu xuất kho QLSX của tờ bị huỷ / xoá → tờ về "chờ cấp", gỡ stock_move_id + đơn giá dòng dầu;
                                    DO đã khoá → 409 DA_KHOA; gọi lại khi tờ đã về chờ → replayed (05/10)

Dòng chi được cấp mang `stock_move_id = "qlsx:<số phiếu kho>"` (TIEN_TO_MV) và `unit_price` = giá vốn bình quân kho QLSX trả về —
bút toán khoá phiếu (but_toan_cho.dong_xuat_kho: 625/1371 xe nhà, 607/1371 xe thuê) đọc đúng hai trường đó như với kho tạm.
"""
import datetime as dt
import re

from fastapi import HTTPException

from sqlalchemy import func

from models import DoiTuongTune, FuelPlace, Trip, TripExpense, TripLog, Voucher
from services import ban_giao as BG
from services import gia_von as GV
from services.chi_tune import LOAI_DOI_TUONG

MA_HANG = "EPLNL-"            # mã hàng nhiên liệu bên kế toán: EPLNL-<item_key> — cùng mã SO nhiên liệu (so_nhien_lieu._ten_dong)
TIEN_TO_MV = "qlsx:"          # TripExpense.stock_move_id của dòng đã cấp ở kho QLSX
SO_PHIEU_TOI_DA = 60
GHI_CHU_TOI_DA = 300
TRANG_THAI = {"cho", "da_cap", "huy"}


def _loi(ma, loi, code=422):
    raise HTTPException(code, {"ma": ma, "loi": loi})


def source_ref(v):
    return re.sub(r"[^A-Za-z0-9_.:-]", ".", v.doc_no or ("PLNL-" + v.id))[:100]


def tim(db, ref):
    """Tờ PLNL theo mã tờ, không có thì theo SourceRef (số PLNL đã đổi ký tự lạ thành ".") — phía kho chỉ giữ SourceRef."""
    ref = str(ref or "").strip()
    if not ref:
        return None
    v = db.get(Voucher, ref)
    if v is not None:
        return v
    if not ref.startswith("PLNL-"):
        return None
    return (db.query(Voucher).filter(Voucher.kind == "fuel",
                                     func.regexp_replace(Voucher.doc_no, "[^A-Za-z0-9_.:-]", ".", "g") == ref).first())


def _nhat_ky(db, p, nguoi, viec):
    db.add(TripLog(trip_id=p.id, user_name=(nguoi or "QLSX")[:80], role="qlsx", action=viec[:500]))


def _iso(x):
    return x.isoformat() if x else None


def _ma_doi_tuong(db, loai, ref_id):
    """Mã PUBOBJECT bên kế toán của tài xế / chủ xe — chỉ khi bên em đã tạo / nhớ ở doi_tuong_tune (mã chưa có bên đó thì kho
    QLSX từ chối cả phiếu). Chủ xe xe thuê thì luôn gửi mã chuẩn EPLCX-<owner_id> (bắt buộc — SO nhiên liệu / trả chủ xe dùng
    đúng mã này); bên kia chưa có thì báo rõ."""
    if not ref_id:
        return None
    r = db.get(DoiTuongTune, (loai, ref_id))
    if r is not None:
        return r.object_no
    return LOAI_DOI_TUONG[loai][1] + str(ref_id) if loai == "chu_xe" else None


def _dong_cho(db, p, v):
    """Dòng dầu kho của phiếu `p` thuộc điểm đổ của tờ `v` CHƯA rời kho — đúng bộ dòng tờ đề nghị đã gom (phieu_linh)."""
    from routes import phieu_linh as PL
    return PL._dong_kho_theo_diem(db, p).get(v.place_id, [])


def _dong_da_cap(db, p, v):
    goc = GV.kho_goc(db)
    return [d for d in (db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "fuel")
                        .order_by(TripExpense.line_no).all())
            if (d.place_id or goc) == v.place_id and (d.stock_move_id or "").startswith(TIEN_TO_MV)]


def _ten_dong(db, d):
    from services.ban_giao import _ten
    return (_ten(db, d)[0] or "Dầu")[:100]


def _goi(db, v, p, diem, dong, ma_tai_xe, ma_doi_tac):
    thue = p.company == "joint"
    dong_ra = [{"line_id": d.id, "item_code": MA_HANG + (d.item_key or "diesel"), "item_name": _ten_dong(db, d),
                "qty_l": d.qty or 0, "stock_move_id": d.stock_move_id} for d in dong]
    ma_hang = sorted({x["item_code"] for x in dong_ra})
    da_cap = [d.stock_move_id for d in dong if (d.stock_move_id or "").startswith(TIEN_TO_MV)]
    chan = None
    if v.status != "cho":
        chan = "Phiếu đã cấp." if v.status == "da_cap" else "Phiếu đã huỷ."
    elif diem is None or diem.owner_type != "epl" or not diem.code:
        chan = "Điểm đổ của phiếu không phải kho EPL có mã kho — không cấp ở kho QLSX được."
    elif not dong:
        chan = "Các dòng dầu kho của phiếu đã xuất hoặc đã bị xoá — lập lại phiếu đề nghị ở trang điều xe."
    elif thue and not p.owner_id:
        chan = "Xe thuê chưa gắn chủ xe (đối tác) — gắn chủ xe trên phiếu DO trước khi cấp."
    elif p.locked:
        chan = "Phiếu DO %s đã khoá — mở khoá ở trang điều xe rồi mới cấp." % p.doc_no
    return {
        "voucher_id": v.id, "voucher_no": v.doc_no, "source_ref": source_ref(v), "status": v.status,
        "doc_date": _iso(v.doc_date), "issued_by": v.issued_by, "issued_at": _iso(v.issued_at),
        "do_id": BG.TIEN_TO + p.id, "do_code": p.doc_no, "trip_kind": p.kind, "transport_status": p.transport_status,
        "trip_locked": bool(p.locked), "truck_no": v.truck_no or p.truck_no, "plate_head": p.plate_head,
        "route": " → ".join(x for x in (p.origin, p.destination) if x) or None, "customer_name": p.customer_name,
        "company": p.company, "vehicle_kind": "HIRED" if thue else "OWN", "purpose": "PARTNER_SALE" if thue else "INTERNAL",
        "owner_id": p.owner_id if thue else None, "owner_name": p.owner_name if thue else None,
        "partner_code": ma_doi_tac if thue else None,
        "driver_id": v.driver_id or p.driver_id, "driver_name": v.driver_name or p.driver_name, "driver_code": ma_tai_xe,
        "place_id": v.place_id, "warehouse_code": diem.code if diem else None, "warehouse_name": diem.name if diem else None,
        "item_code": ma_hang[0] if len(ma_hang) == 1 else None, "lines": dong_ra, "qty_l": v.qty_l or 0,
        "granted_qty": v.granted_qty, "granted_by": v.granted_by, "granted_at": _iso(v.granted_at), "granted_note": v.granted_note,
        "stock_doc_no": da_cap[0][len(TIEN_TO_MV):] if da_cap else None,
        "can_issue": chan is None, "block_reason": chan,
    }


def goi(db, v, p=None):
    if v is None or v.kind != "fuel":
        _loi("KHONG_THAY", "Không có phiếu đề nghị xuất kho nhiên liệu này.", 404)
    p = p or db.get(Trip, v.trip_id)
    if p is None:
        _loi("KHONG_THAY", "Phiếu đề nghị %s không còn phiếu DO." % v.doc_no, 404)
    diem = db.get(FuelPlace, v.place_id) if v.place_id else None
    dong = _dong_cho(db, p, v) if v.status == "cho" else _dong_da_cap(db, p, v)
    return _goi(db, v, p, diem, dong, _ma_doi_tuong(db, "tai_xe", v.driver_id or p.driver_id),
                _ma_doi_tuong(db, "chu_xe", p.owner_id) if p.company == "joint" else None)


def danh_sach(db, status="cho", q="", kho="", page=1, page_size=50):
    qs = db.query(Voucher).filter(Voucher.kind == "fuel")
    if status:
        if status not in TRANG_THAI:
            _loi("TRANG_THAI_SAI", "status chỉ nhận cho · da_cap · huy (để trống = tất cả).")
        qs = qs.filter(Voucher.status == status)
    chu = (q or "").strip()
    if chu:
        # `%` `_` người dùng gõ là chữ thường (như /api/handover/delivery-orders)
        k = "%" + chu.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
        from sqlalchemy import or_
        qs = qs.filter(or_(Voucher.doc_no.ilike(k, escape="!"), Voucher.truck_no.ilike(k, escape="!"),
                           Voucher.driver_name.ilike(k, escape="!"),
                           Voucher.trip_id.in_(db.query(Trip.id).filter(Trip.doc_no.ilike(k, escape="!")))))
    if kho:
        qs = qs.filter(Voucher.place_id.in_(db.query(FuelPlace.id).filter(FuelPlace.code == kho.strip())))
    tong = qs.count()
    ds = qs.order_by(Voucher.doc_date.desc(), Voucher.doc_no).offset((page - 1) * page_size).limit(page_size).all()
    phieu = {t.id: t for t in db.query(Trip).filter(Trip.id.in_({v.trip_id for v in ds}))} if ds else {}
    return tong, [goi(db, v, phieu.get(v.trip_id)) for v in ds if phieu.get(v.trip_id) is not None]


def _so(x, ten):
    try:
        n = float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        _loi("SO_SAI", "%s phải là số." % ten)
    if n != n or n in (float("inf"), float("-inf")):
        _loi("SO_SAI", "%s phải là số." % ten)
    return n


def ghi_da_cap(db, v_id, d):
    """Kho QLSX đã lập phiếu xuất cho tờ `v_id` — ghi lại ở đây (khoá dòng tờ trong giao dịch, gọi lại an toàn).

    d = {source_ref, stock_doc_no, stock_doc_id?, qty_l, note?, issued_by?, lines: [{item_code, qty, unit_cost}]}"""
    from services import but_toan_cho as BTC
    v = db.query(Voucher).filter(Voucher.id == v_id).with_for_update().first()
    if v is None or v.kind != "fuel":
        _loi("KHONG_THAY", "Không có phiếu đề nghị xuất kho nhiên liệu này.", 404)
    if str(d.get("source_ref") or "").strip() != source_ref(v):
        _loi("SAI_SOURCE_REF", "SourceRef không khớp phiếu %s (mong %s)." % (v.doc_no, source_ref(v)), 409)
    so = str(d.get("stock_doc_no") or "").strip()
    if not so or len(so) > SO_PHIEU_TOI_DA or any(ord(c) < 32 for c in so):
        _loi("THIEU_SO_PHIEU_KHO", "Thiếu số phiếu xuất kho bên QLSX (≤ %d ký tự)." % SO_PHIEU_TOI_DA)
    mv = TIEN_TO_MV + so
    p = db.get(Trip, v.trip_id)
    if p is None:
        _loi("KHONG_THAY", "Phiếu đề nghị %s không còn phiếu DO." % v.doc_no, 404)
    if v.status == "da_cap":
        if any(x.stock_move_id == mv for x in _dong_da_cap(db, p, v)):
            return dict(goi(db, v, p), replayed=True)
        _loi("DA_CAP", "Phiếu %s đã cấp theo chứng từ khác — không ghi lần hai." % v.doc_no, 409)
    if v.status != "cho":
        _loi("DA_HUY", "Phiếu %s đã huỷ ở trang điều xe — huỷ phiếu xuất kho bên QLSX." % v.doc_no, 409)

    lit = _so(d.get("qty_l"), "Số lít cấp")
    if lit <= 0:
        _loi("SO_LIT_SAI", "Số lít cấp phải lớn hơn 0.")
    if lit > (v.qty_l or 0) + 0.001:
        _loi("VUOT_DE_NGHI", "Cấp %s lít vượt số đề nghị %s lít." % (lit, v.qty_l))
    ly_do = str(d.get("note") or "").strip()[:GHI_CHU_TOI_DA]
    lech = abs(lit - (v.qty_l or 0)) > 0.001
    if lech and not ly_do:
        _loi("THIEU_LY_DO", "Cấp %s lít khác số đề nghị %s lít thì phải ghi lý do." % (lit, v.qty_l))
    dong = _dong_cho(db, p, v)
    if not dong:
        _loi("KHONG_CON_DONG", "Các dòng dầu của kho này đã xuất rồi.", 409)
    gia = {}
    for x in d.get("lines") or []:
        ma = str((x or {}).get("item_code") or "").strip()
        if ma:
            g = _so(x.get("unit_cost"), "Giá vốn dòng %s" % ma)
            if g < 0:
                _loi("GIA_VON_SAI", "Giá vốn dòng %s không được âm." % ma)
            gia[ma] = g
    ma_hang = {MA_HANG + (e.item_key or "diesel") for e in dong}
    thieu = sorted(ma_hang - set(gia))
    if thieu:
        _loi("THIEU_GIA_VON", "Thiếu giá vốn của mã hàng %s từ phiếu kho." % ", ".join(thieu))
    if lech and len(dong) > 1:
        _loi("CAP_LECH_NHIEU_DONG", "Phiếu %s gồm nhiều dòng dầu — chỉ cấp đủ số đề nghị, không cấp lệch." % v.doc_no)

    truoc_khoa = BTC.dau_khoa(db, p)
    for e in dong:
        e.unit_price, e.currency = gia[MA_HANG + (e.item_key or "diesel")], "LAK"
        e.stock_move_id = mv
    if lech:
        dong[0].qty = lit                        # cấp lệch thì phiếu xuất xe ghi theo số thật (như cap_phat)
    nguoi = str(d.get("issued_by") or "").strip()[:80] or "QLSX"
    v.granted_qty, v.granted_note = lit, ly_do or None
    v.status, v.granted_by, v.granted_at = "da_cap", "%s (kho QLSX %s)" % (nguoi, so), dt.datetime.utcnow()
    BTC.chan_sua_sau_khoa(db, p, truoc_khoa)    # phiếu đã khoá mà lệch bút toán → 409 DA_KHOA, không ghi
    _nhat_ky(db, p, nguoi, "Cấp %s lít dầu theo %s ở kho QLSX — phiếu xuất kho %s" % (lit, v.doc_no, so))
    db.commit()
    return dict(goi(db, v, p), replayed=False)


def ghi_da_huy(db, ref, d):
    """Kho QLSX đã huỷ / xoá phiếu xuất của tờ `ref` (mã tờ hoặc SourceRef) → tờ về "chờ cấp" để cấp lại.

    d = {source_ref?, stock_doc_no?, reason?, cancelled_by?}. Gỡ `stock_move_id = qlsx:<số phiếu>` và đơn giá (giá vốn) của các dòng
    dầu đã cấp theo tờ; cấp thiếu một dòng thì trả số lít dòng về số đề nghị. DO đã khoá → 409 (bút toán khoá phiếu đã theo lần cấp)."""
    v0 = tim(db, ref)
    if v0 is None or v0.kind != "fuel":
        _loi("KHONG_THAY", "Không có phiếu đề nghị xuất kho nhiên liệu %s." % ref, 404)
    v = db.query(Voucher).filter(Voucher.id == v0.id).with_for_update().first()
    sr = str(d.get("source_ref") or "").strip()
    if sr and sr != source_ref(v):
        _loi("SAI_SOURCE_REF", "SourceRef không khớp phiếu %s (mong %s)." % (v.doc_no, source_ref(v)), 409)
    so = str(d.get("stock_doc_no") or "").strip()
    p = db.get(Trip, v.trip_id)
    if p is None:
        _loi("KHONG_THAY", "Phiếu đề nghị %s không còn phiếu DO." % v.doc_no, 404)
    dong = _dong_da_cap(db, p, v)
    if v.status == "cho" and not dong:
        return dict(goi(db, v, p), replayed=True)          # đã mở lại từ lần báo trước
    if v.status == "huy" and not dong:
        return dict(goi(db, v, p), replayed=True)          # tờ đã huỷ ở đây — không còn gì để mở lại
    if not dong:
        _loi("KHONG_PHAI_KHO_QLSX", "Phiếu %s không cấp ở kho QLSX (không có dòng qlsx:…) — không mở lại từ kho QLSX." % v.doc_no, 409)
    if so and any(x.stock_move_id != TIEN_TO_MV + so for x in dong):
        _loi("KHAC_PHIEU_KHO", "Phiếu %s cấp theo phiếu kho %s, không phải %s." % (
            v.doc_no, ", ".join(sorted({x.stock_move_id[len(TIEN_TO_MV):] for x in dong})), so), 409)
    if p.locked:
        _loi("DA_KHOA", "DO %s đã khoá ở trang điều xe — mở khoá DO trước rồi mới huỷ phiếu kho cấp dầu." % p.doc_no, 409)
    cu = sorted({x.stock_move_id[len(TIEN_TO_MV):] for x in dong})
    for e in dong:
        e.stock_move_id, e.unit_price = None, 0
    if len(dong) == 1 and v.qty_l:
        dong[0].qty = v.qty_l                    # cấp thiếu đã ghi số thật lên dòng → trả về số đề nghị
    v.status, v.granted_by, v.granted_at, v.granted_qty, v.granted_note = "cho", None, None, None, None
    ly_do = str(d.get("reason") or "").strip()[:200]
    _nhat_ky(db, p, str(d.get("cancelled_by") or "").strip(), "Kho QLSX huỷ phiếu xuất %s của %s — mở lại phiếu đề nghị%s" % (
        ", ".join(cu), v.doc_no, (" (lý do: %s)" % ly_do) if ly_do else ""))
    db.commit()
    return dict(goi(db, v, p), replayed=False, cancelled_stock_doc_no=", ".join(cu))
