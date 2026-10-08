# -*- coding: utf-8 -*-
"""Chủ xe liên kết (ເຈົ້າຂອງລົດຮ່ວມ) — danh mục và sổ trả tiền.

Anh Khampla trả lời 22/09 (C4.2, C4.3): phí 2 %/phiếu và mức quá tải **khác nhau theo từng chủ xe /
hợp đồng**, và chủ xe được trả theo **ba kiểu** — từng phiếu ngay sau khoá (xe ngoài không hợp đồng),
gộp cuối tháng, hay theo đợt đã thoả thuận. Trước đây phần mềm chỉ có ba ô mặc định trên từng phiếu và
một nút trả từng phiếu.

Mô hình ở đây cố ý đơn giản:
  · `owners`: mỗi chủ xe một dòng, mang mặc định phí, ngưỡng tấn, mức trừ quá tải, tiền thuê, cách trả.
    Lập phiếu cho xe của chủ đó thì ba ô kia tự điền theo — kế toán vẫn sửa được trên phiếu.
  · `owner_payments`: MỘT LẦN TRẢ gồm MỘT HAY NHIỀU PHIẾU đã khoá của cùng chủ xe, cùng tiền thuê.
    Số tiền = tổng "trả chủ xe" của các phiếu trong đợt — không gõ tay, để khớp chứng từ từng phiếu.
    "Từng phiếu" là đợt một phiếu; "gộp tháng" là đợt gồm các phiếu trong tháng; "theo đợt" là đợt
    gồm những phiếu hai bên chốt trả lần này.
  · Phiếu nằm trong đợt nào thì `trips.owner_payment_id` trỏ tới đó — đó chính là "đã trả chủ xe".

Từ 01/10 TRẢ TIỀN ở hệ kế toán anh Tune (chủ dự án: bỏ phần tiền trang kế toán tạm, cắt sổ 01/10 — đợt trả bên đó là số
thử, bỏ; bảng owner_payments không dùng nữa). Ở đây: DANH MỤC chủ xe (lập phiếu tự điền phí, ngưỡng tấn theo chủ xe) và
ĐỀ NGHỊ TRẢ — phiếu chi "Chi khác" bên đó (Nợ 4022 / Có tiền) đứng tên chủ xe; thủ quỹ chi + ghi sổ → các phiếu "đã trả"
(services/chi_tune.py, services/tra_chu_xe.py).
"""
import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func, literal
from sqlalchemy.orm import Session

from database import get_db
from models import CACH_TRA_CHU_XE, TIEN_TE, Owner, Trip, TripExpense, Vehicle
from services import doi_tuong_gls as DT
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_ban
from services.tinh_toan import tinh_phieu

router = APIRouter()

SUA_CHU_XE = can_vai("acct")                    # phí, mức trừ, cách trả là điều khoản hợp đồng — kế toán VC giữ
COT = ("name", "phone", "address", "fee_pct", "over_limit_t", "over_price", "hire_ccy", "pay_mode", "note")
COT_SO = ("fee_pct", "over_limit_t", "over_price")
COT_TIEN = ("fee_pct", "over_limit_t", "over_price", "hire_ccy")   # Bãi không thấy — đây là phần trừ tiền của chủ xe


def _so(v, ten):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Ô %s phải là số, nhận '%s'." % (ten, v)})


def _ngay(v):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD, nhận '%s'." % v})


def _dong_chi(db, p):
    return db.query(TripExpense).filter(TripExpense.trip_id == p.id).order_by(TripExpense.section, TripExpense.line_no).all()


def xuat_chu_xe(db, o, user=None, xe=None):
    """`xe` (từ ds_chu_xe) là phần đã nạp sẵn cho cả danh sách — có thì không hỏi DB từng chủ xe."""
    r = {"id": o.id, "name": o.name, "phone": o.phone, "address": o.address, "pay_mode": o.pay_mode or "phieu",
         "note": o.note, "active": bool(o.active),
         # Việc 10: chủ xe là đối tượng danh mục nhà cung cấp chung — tên · điện thoại · địa chỉ · mã là bản chép
         "code": o.code, "obj_id": o.obj_id, "gls_synced_at": o.gls_synced_at.isoformat() if o.gls_synced_at else None,
         "so_xe": xe.get(o.id, []) if xe is not None else
                  [v.truck_no for v in db.query(Vehicle).filter(Vehicle.owner_id == o.id, Vehicle.active.is_(True)).all()]}
    if user is None or thay_tien_ban(user.role):
        r.update({"fee_pct": o.fee_pct, "over_limit_t": o.over_limit_t, "over_price": o.over_price, "hire_ccy": o.hire_ccy or "USD"})
    return r


def _cho_tra_lo(db, cac_chu):
    """Phần chờ trả (phiếu đã khoá chưa trả) của CẢ danh sách chủ xe — bốn câu thay cho (2 + số phiếu) câu MỖI chủ xe. Cùng
    công thức (tinh_phieu), cùng thứ tự cộng (ngày, số phiếu). Đường máy của trang kế toán tạm dùng hàm này đã bỏ (01/10);
    (bài so cũ kiem/thu_danh_muc_cu_moi.py đã dời vào kiem/loi_thoi/ ngày 06/10.) Không trừ phiếu đang nằm đề nghị trả bên kế toán —
    phần đó xem chi_tune.cho_tra_chu_xe."""
    from routes.bao_cao import COT_TINH           # nạp lúc gọi: bao_cao cũng nạp các route khác, tránh vòng import
    ids = [o.id for o in cac_chu]
    ra = {i: {"so_phieu": 0, "tong": {}, "tong_lak": 0} for i in ids}
    if not ids:
        return ra
    loc = (Trip.owner_id.in_(ids), Trip.company == "joint", Trip.locked.is_(True), Trip.owner_payment_id.is_(None))
    ds = db.query(Trip.owner_id, *COT_TINH).filter(*loc).order_by(Trip.doc_date, Trip.doc_no).all()
    dong = defaultdict(list)
    tien = func.sum(func.coalesce(TripExpense.qty, 0) * func.coalesce(TripExpense.sale_price, TripExpense.unit_price, 0))
    for r in (db.query(TripExpense.trip_id, TripExpense.section, TripExpense.currency, TripExpense.paid_by_epl,
                       literal(1.0).label("qty"), tien.label("unit_price"))
              .join(Trip, Trip.id == TripExpense.trip_id).filter(*loc)
              .group_by(TripExpense.trip_id, TripExpense.section, TripExpense.currency, TripExpense.paid_by_epl)):
        dong[r.trip_id].append(r)
    for p in ds:
        k = tinh_phieu(p, dong.get(p.id, []))
        o = ra[p.owner_id]
        o["so_phieu"] += 1
        if k.get("tra_chu_xe") and k["tra_chu_xe"] > 0:
            o["tong"][k["hire_ccy"]] = round(o["tong"].get(k["hire_ccy"], 0) + k["tra_chu_xe"], 2)
        o["tong_lak"] += k.get("tra_chu_xe_lak") or 0
    return ra


def _phieu_cho_tra(db, o):
    """Phiếu đã KHOÁ của chủ xe này mà chưa nằm trong đợt trả nào."""
    return (db.query(Trip).filter(Trip.owner_id == o.id, Trip.company == "joint", Trip.locked.is_(True),
                                  Trip.owner_payment_id.is_(None)).order_by(Trip.doc_date, Trip.doc_no).all())


def _dong_phieu(db, p):
    k = tinh_phieu(p, _dong_chi(db, p))
    return {"id": p.id, "doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
            "truck_no": p.truck_no, "customer_name": p.customer_name, "tan_tinh": k["tan_tinh"],
            "hire_ccy": k.get("hire_ccy"), "tien_thue": k.get("tien_thue"), "phi": k.get("phi"), "tru_vuot": k.get("tru_vuot"),
            "ung_truoc": k.get("ung_truoc"), "tra_chu_xe": k.get("tra_chu_xe"), "tra_chu_xe_lak": k.get("tra_chu_xe_lak"),
            "owner_payment_id": p.owner_payment_id}


# ================================================================ danh mục
@router.get("/api/owners")
def ds_chu_xe(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Mọi vai xem được tên và xe (Bãi cần chọn chủ xe khi thêm xe); phí chỉ vai thấy tiền bán. Số chờ trả ở trang kế toán."""
    ds = db.query(Owner).order_by(Owner.active.desc(), Owner.name).all()
    xe = defaultdict(list)
    for oid, so in db.query(Vehicle.owner_id, Vehicle.truck_no).filter(Vehicle.owner_id.in_([o.id for o in ds] or [""]),
                                                                       Vehicle.active.is_(True)):
        xe[oid].append(so)
    return [xuat_chu_xe(db, o, user, xe=xe) for o in ds]


def _ap(o, data):
    for k in COT:
        if k not in data:
            continue
        v = data[k]
        if k in COT_SO:
            v = _so(v, k)
        elif isinstance(v, str):
            v = v.strip() or None
        setattr(o, k, v)
    if not (o.name or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Chủ xe phải có tên."})
    o.pay_mode = o.pay_mode or "phieu"
    if o.pay_mode not in CACH_TRA_CHU_XE:
        raise HTTPException(422, {"ma": "CACH_TRA_SAI", "loi": "Cách trả phải là %s." % ", ".join(CACH_TRA_CHU_XE)})
    o.hire_ccy = (o.hire_ccy or "USD").upper()
    if o.hire_ccy not in TIEN_TE:
        raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Tiền thuê phải là một trong %s." % ", ".join(TIEN_TE)})
    if o.fee_pct is None: o.fee_pct = 2
    if o.over_limit_t is None: o.over_limit_t = 40
    if o.over_price is None: o.over_price = 1
    if o.fee_pct < 0 or o.fee_pct > 100:
        raise HTTPException(422, {"ma": "PHI_SAI", "loi": "Phí phải từ 0 đến 100 %."})


@router.get("/api/owners/gls")
def tim_chu_xe_gls(q: str = "", trang: int = 1, db: Session = Depends(get_db), _=Depends(SUA_CHU_XE)):
    """Việc 10: tìm chủ xe trong danh mục nhà cung cấp chung; dòng đã có hồ sơ kèm `owner_id` (nhà cung cấp: `supplier_id`)."""
    return DT.tim_kem_ho_so(db, "chu_xe", DT.tim("chu_xe", q, trang))


def _gan_chu_xe(db, oid, data):
    o, _moi = DT.lien_ket(db, "chu_xe", oid)
    _ap(o, {k: v for k, v in (data or {}).items() if k not in DT.O_CHUNG})   # phần riêng: phí, ngưỡng, mức trừ, tiền, cách trả, ghi chú
    return o


@router.post("/api/owners/gls/{obj_id}")
def lien_ket_chu_xe_gls(obj_id: int, data: dict = Body(default={}), db: Session = Depends(get_db), user=Depends(SUA_CHU_XE)):
    """Lập (hoặc chép lại) hồ sơ vận tải cho chủ xe `obj_id` của danh mục chung; thân tuỳ chọn: phần riêng vận tải."""
    o = _gan_chu_xe(db, obj_id, data)
    db.commit(); db.refresh(o)
    return xuat_chu_xe(db, o, user)


@router.post("/api/owners/dong-bo-gls")
def dong_bo_chu_xe_gls(db: Session = Depends(get_db), _=Depends(SUA_CHU_XE)):
    """Chép lại tên · điện thoại · địa chỉ · mã của mọi chủ xe đã gắn từ danh mục chung (tên mới chép cả sang danh mục xe)."""
    kq = DT.dong_bo(db, "chu_xe")
    db.commit()
    return kq


@router.post("/api/owners")
def them_chu_xe(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_CHU_XE)):
    """Thêm chủ xe. Việc 10: có `obj_id` → gắn đối tượng danh mục chung; EPL_NCC_GLS=1 mà không có → tạo trong danh mục chung
    trước (mã EPLCX-… hoặc ô Mã) rồi gắn. Cờ tắt → chủ xe riêng như cũ."""
    if data.get("obj_id") or DT.bat("chu_xe"):
        oid = data.get("obj_id") or DT.tao("chu_xe", data, str(data.get("code") or "").strip() or None)
        try:
            oid = int(oid)
        except (TypeError, ValueError):
            raise HTTPException(422, {"ma": "OBJ_ID_SAI", "loi": "Mã chủ xe trong danh mục không hợp lệ."})
        o = _gan_chu_xe(db, oid, data)
        db.commit(); db.refresh(o)
        return xuat_chu_xe(db, o, user)
    o = Owner(); _ap(o, data)
    db.add(o); db.commit(); db.refresh(o)
    return xuat_chu_xe(db, o, user)


@router.put("/api/owners/{oid}")
def sua_chu_xe(oid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_CHU_XE)):
    o = db.get(Owner, oid)
    if not o:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chủ xe này."})
    data = DT.chan_sua_chung("chu_xe", o, data)       # Việc 10: đã gắn danh mục chung + cờ bật → thông tin chung sửa ở đó
    _ap(o, data)
    if "active" in data:
        o.active = bool(data["active"])
    # Tên đổi thì xe và phiếu cũ vẫn giữ tên đã chép — nhưng danh mục xe nên theo tên mới
    for v in db.query(Vehicle).filter(Vehicle.owner_id == o.id).all():
        v.owner_name = o.name
    db.commit(); db.refresh(o)
    return xuat_chu_xe(db, o, user)


# ---------------------------------------------------------------- trả chủ xe qua hệ kế toán anh Tune (01/10)
# Chủ dự án chốt 01/10: tiền chi thật ở hệ anh Tune, trạng thái về bên này. Bên này lập ĐỀ NGHỊ trả cho các phiếu xe thuê đã
# khoá; bên đó có phiếu chi "Chi khác" (Nợ 4022 / Có tiền) đứng tên chủ xe; thủ quỹ chi + ghi sổ → phiếu thành "đã trả".
DE_NGHI_TRA = ("acct", "admin")                                     # KT Thu/Chi VC (người nhập giá thuê, khoá phiếu) và Sếp
KHONG_XEM_TRA = ("yard", "driver", "depot", "parts", "repair")       # tiền thuê xe liên kết là tiền bán — Bãi không thấy


def _ban_ghi_chu_xe(db, rid):
    from models import ChiChuXeTune
    r = db.get(ChiChuXeTune, rid)
    if r is None:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có đề nghị trả này."})
    return r


@router.get("/api/owners/{oid}/tra-ke-toan")
def tra_ke_toan(oid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Phiếu chờ đề nghị trả của một chủ xe + các lần đề nghị; đề nghị đang chờ thì hỏi lại hệ kế toán."""
    from models import ChiChuXeTune
    from services import chi_tune as CHI
    if user.role in KHONG_XEM_TRA:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem tiền trả chủ xe." % user.role})
    for r in db.query(ChiChuXeTune).filter(ChiChuXeTune.owner_id == oid, ChiChuXeTune.status == "da_gui").all():
        try:
            CHI.dong_bo_chu_xe(db, r, user=user)        # người bấm: đường máy kho tạm (chốt hàng quầy) cần tên đăng nhập
        except HTTPException:
            break
    return CHI.cho_tra_chu_xe(db, oid)


@router.get("/api/owners/{oid}/hang-quay")
def hang_quay(oid: str, trip_ids: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Hàng chủ xe mua ở quầy CHỜ TRỪ (phiếu bán ở kho tạm) + ước tính SỐ TRẢ THỰC = Σ phiếu − Σ hàng mua của các phiếu chọn
    (`trip_ids` cách dấu phẩy; trống = mọi phiếu chờ trả) — màn Xe liên kết hiện trước khi lập đề nghị. Kho tạm không nối
    được → 503 (không đoán số)."""
    from services import chi_tune as CHI
    from services import tra_chu_xe as TC
    if user.role in KHONG_XEM_TRA:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem tiền trả chủ xe." % user.role})
    cho = {x["id"]: x for x in CHI.cho_tra_chu_xe(db, oid)["cho"]}
    ids = list(dict.fromkeys(i for i in trip_ids.split(",") if i))
    if any(i not in cho for i in ids):
        raise HTTPException(409, {"ma": "PHIEU_KHONG_HOP_LE", "loi": "Có phiếu không còn chờ trả — tải lại danh sách."})
    chon = [cho[i] for i in ids] if ids else list(cho.values())
    if len({x["hire_ccy"] or "LAK" for x in chon}) > 1:
        raise HTTPException(422, {"ma": "KHAC_TIEN", "loi": "Các phiếu chọn khác tiền thuê — mỗi đề nghị một loại tiền."})
    hang = TC.hang_cho_tru(db, oid, user)
    # 02/10: ước tính theo số CÒN TRẢ sau cấn trừ SO nhiên liệu (theo bản đọc lại gần nhất) — đúng số đề nghị sẽ lập
    return {"hang": hang, "uoc_tinh": TC.tinh_tru(TC.sau_can_tru(chon), hang) if chon else None}


@router.post("/api/owners/{oid}/de-nghi-tra")
def de_nghi_tra(oid: str, d: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """{trip_ids: [...], phuong_thuc: cash|bank} → phiếu chi trả chủ xe bên hệ kế toán (chưa ghi sổ)."""
    from services import chi_tune as CHI
    if user.role not in DE_NGHI_TRA:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ KT Thu/Chi Viêng Chăn hoặc Sếp lập đề nghị trả chủ xe."})
    if not CHI.chi_o_ke_toan():
        raise HTTPException(409, {"ma": "CHI_TAI_CHO", "loi": "Đang để chi trên trang kế toán tạm (EPL_CHI_TAM_UNG=tai_cho)."})
    r = CHI.de_nghi_tra_chu_xe(db, oid, d.get("trip_ids") or [], (d.get("phuong_thuc") or "cash").strip(), user)
    return CHI.xuat_chu_xe(r)


@router.post("/api/chi-chu-xe/{rid}/{viec}")
def viec_de_nghi_tra(rid: str, viec: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """cap-nhat (hỏi lại hệ kế toán) · gui-lai (lần trước hỏng) · huy (bỏ đề nghị chưa chi, rút phiếu chi bên đó)."""
    from services import chi_tune as CHI
    if user.role in KHONG_XEM_TRA:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem tiền trả chủ xe." % user.role})
    r = _ban_ghi_chu_xe(db, rid)
    if viec == "cap-nhat":
        r = CHI.dong_bo_chu_xe(db, r, user=user)
    elif viec in ("gui-lai", "huy"):
        if user.role not in DE_NGHI_TRA:
            raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ KT Thu/Chi Viêng Chăn hoặc Sếp."})
        r = CHI.gui_lai_chu_xe(db, r, user) if viec == "gui-lai" else CHI.huy_chu_xe(db, r, user=user)
    else:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có việc %s." % viec})
    return CHI.xuat_chu_xe(r)
