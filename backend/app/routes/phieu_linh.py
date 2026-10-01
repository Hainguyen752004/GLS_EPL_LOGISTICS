# -*- coding: utf-8 -*-
"""Phiếu lĩnh — tờ giấy tài xế cầm đi, in từ MỘT mục của phiếu xuất xe, có mã QR.

Phiếu xuất xe là hồ sơ của cả chuyến. Nhưng tài xế không cầm cả hồ sơ đi lấy dầu, nên mỗi mục có
tiền đẻ ra một tờ riêng:

    mục III  →  PHIẾU LĨNH NHIÊN LIỆU  →  cầm đến KHO ghi ở ô "Nơi đổ"   →  thủ kho cấp dầu
    mục IV   →  PHIẾU TẠM ỨNG ĐI ĐƯỜNG →  cầm đến KẾ TOÁN / QUỸ          →  chi tiền mặt

Một chuyến có thể có NHIỀU phiếu lĩnh nhiên liệu (mỗi điểm đổ một tờ) nhưng chỉ MỘT phiếu tạm ứng.

Mã QR chứa một đường dẫn tra cứu kèm `token`, KHÔNG nhồi số liệu vào QR. Lý do: số liệu còn đổi sau
lúc in, nhồi vào rồi là tờ giấy nói một đằng hệ thống nói một nẻo; và QR nhồi nhiều thì dày đặc, máy
quét rẻ đọc không ra. Người quét đằng nào cũng có tài khoản và phải đăng nhập mới cấp được.

Ranh giới với luồng duyệt cũ: cấp dầu là việc VẬT LÝ, xảy ra TRƯỚC khi kế toán ghi sổ — thủ kho cấp
thì sinh luôn dòng xuất kho và đánh dấu dòng chi. Từ 30/09 đó là đường DUY NHẤT dầu kho rời kho: ghi sổ mục III không
tự xuất nữa, dòng dầu kho chưa cấp theo phiếu đề nghị thì chặn ghi sổ (phieu.py · _chan_chua_cap_theo_de_nghi). Còn chi tạm ứng là việc TIỀN, nên nó
đi đúng chuỗi duyệt: mục IV phải "đã ghi sổ" rồi mới chi được, và chỉ vai giữ quỹ mới chi.
"""
import datetime as dt
import io
import secrets

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import ChungTu, FuelPlace, Supplier, Trip, TripExpense, TripSection, Voucher
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import chuyen_muc, thay_gia_kho, thay_tien_ban, thay_tien_chi
from services.tinh_toan import hinh_thuc, la_tien_mat_tai_xe, ty_gia
from services import chung_tu as CT
from services import tai_khoan as TK
from services import gia_von as GV
from services import kho_ke_toan as KK

router = APIRouter()
TIEN_TO = {"fuel": "PLNL", "advance": "PTU"}


# ================================================================ điểm đổ nhiên liệu
def xuat_diem(db, x, chi_tiet=False):
    ra = {"id": x.id, "code": x.code, "name": x.name, "country": x.country, "owner_type": x.owner_type,
          "supplier_id": x.supplier_id, "address": x.address, "note": x.note, "active": x.active}
    if x.supplier_id:
        ncc = db.get(Supplier, x.supplier_id)
        ra["supplier_name"] = ncc.name if ncc else None
    if chi_tiet:
        ra["cho_cap"] = db.query(Voucher).filter(Voucher.place_id == x.id, Voucher.status == "cho").count()
    return ra


@router.get("/api/fuel-places")
def ds_diem(tat_ca: int = 0, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    q = db.query(FuelPlace)
    if not tat_ca:
        q = q.filter(FuelPlace.active.is_(True))
    return [xuat_diem(db, x, True) for x in q.order_by(FuelPlace.country, FuelPlace.name).all()]


DA_DOI = {"ma": "DA_DOI_SANG_KE_TOAN",
          "loi": "Điểm đổ nhiên liệu nay quản lý ở trang kế toán (Kho → Điểm đổ nhiên liệu). Ở đây chỉ còn bản chép để đọc."}


# Thêm / sửa / xoá điểm đổ dời sang trang kế toán (28/09): bản gốc ở đó, bên này là bản chép chỉ đọc (routes/lien_thong.py).
@router.post("/api/fuel-places")
def them_diem(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.put("/api/fuel-places/{pid}")
def sua_diem(pid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.delete("/api/fuel-places/{pid}")
def xoa_diem(pid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


# ================================================================ phiếu lĩnh
def _lak(p, d):
    return (d.qty or 0) * (d.unit_price or 0) * ty_gia(p, d.currency)


def dam_bao_tam_ung(db, p, user):
    """Tờ TẠM ỨNG (PTU, có mã QR) của chuyến: chưa có thì lập, còn "chờ" thì cập nhật số theo các dòng tiền mặt tài xế cầm
    đi lúc này (la_tien_mat_tai_xe — cách trả "Chi ngay khi xe đi"). Bãi in tờ trước khi kế toán nhập giá nên số có thể còn
    0; số đúng là số lúc quỹ chi. Không có dòng tiền mặt nào thì trả None."""
    dong = [d for d in _dong(db, p) if la_tien_mat_tai_xe(d, p.company)]
    if not dong:
        return None
    tien = sum(_lak(p, d) for d in dong)
    ngay = p.out_date or p.doc_date or dt.date.today()
    v = db.query(Voucher).filter(Voucher.trip_id == p.id, Voucher.kind == "advance").first()
    if v is None:
        v = Voucher(doc_no="PTU-" + p.doc_no, token=secrets.token_urlsafe(9), amount_lak=tien, trip_id=p.id, kind="advance",
                    doc_date=ngay, driver_id=p.driver_id, driver_name=p.driver_name, truck_no=p.truck_no, issued_by=user.full_name)
        db.add(v)
    elif v.status == "cho":
        v.amount_lak = tien                     # chưa ai lấy tiền thì theo số mới nhất
    db.flush()
    CT.ghi(db, "PTU", nguon_bang="vouchers", nguon_id=v.id, trip=p, ngay=ngay, doi_tuong_loai="tai_xe",
           doi_tuong_ten=p.driver_name, tien=v.amount_lak, tien_te="LAK", by_user=user.full_name,
           mo_ta="Đề nghị tạm ứng phiếu %s" % p.doc_no,
           payload={"voucher_id": v.id, "doc_no": v.doc_no, "hinh_thuc": hinh_thuc(p, "tam_ung"),
                    "owner_id": p.owner_id, "owner_name": p.owner_name})
    _khop_ct_tam_ung(db, v)
    return v


def _khop_ct_tam_ung(db, v):
    """Tờ chứng từ PTU ghi số LÚC BÃI IN tờ tạm ứng — kế toán chưa nhập giá nên có khi còn 0 (phiếu mẫu 29/09: PTU 0 LAK
    mà PC_TU 580.000). Chưa đẩy sang kế toán thì theo số tạm ứng hiện tại: tờ PTU phải bằng số quỹ chi (PC_TU)."""
    c = db.query(ChungTu).filter(ChungTu.loai == "PTU", ChungTu.nguon_bang == "vouchers", ChungTu.nguon_id == v.id).first()
    if c is not None and not c.da_day and abs((c.tien or 0) - (v.amount_lak or 0)) > 0.5:
        c.tien = c.tien_lak = v.amount_lak


def xuat_phieu_linh(db, v, goc="", vai=None):
    """`vai` là vai người gọi — vai không thấy tiền chi (Bãi, anh Khampla A2) thì không nhận số tiền tạm ứng."""
    diem = db.get(FuelPlace, v.place_id) if v.place_id else None
    if v.kind == "advance" and v.status == "cho":
        # tờ còn chờ: số hiện theo dòng tiền mặt LÚC NÀY (kế toán nhập giá sau khi Bãi in) — đúng số quỹ sẽ chi
        p_ = db.get(Trip, v.trip_id)
        if p_ is not None:
            v.amount_lak = _tien_tam_ung(db, p_)
            _khop_ct_tam_ung(db, v)
    return {"id": v.id, "trip_id": v.trip_id, "kind": v.kind, "doc_no": v.doc_no,
            "doc_date": v.doc_date.isoformat() if v.doc_date else None,
            "place_id": v.place_id, "place_name": diem.name if diem else None,
            "place_country": diem.country if diem else None,
            "driver_id": v.driver_id, "driver_name": v.driver_name, "truck_no": v.truck_no,
            "qty_l": v.qty_l, "amount_lak": v.amount_lak, "status": v.status, "token": v.token,
            # màn Cấp phát ở trang kế toán (28/09): đường tra cứu / mã QR mở thẳng bên đó
            "qr": "/api/vouchers/%s/qr.png" % v.id, "tra_cuu": (KK.web_ke_toan(db) or goc or "") + "/#/cap-phat?ma=" + v.token,
            "issued_by": v.issued_by, "issued_at": v.issued_at.isoformat() if v.issued_at else None,
            "granted_by": v.granted_by, "granted_at": v.granted_at.isoformat() if v.granted_at else None,
            "granted_qty": v.granted_qty, "granted_note": v.granted_note, "note": v.note,
            # bản chất đề nghị theo loại xe (29/09): nội bộ · ghi công nợ chủ xe · xuất bán cho chủ xe
            **_ban_chat(db, v),
            **({} if vai is None or thay_tien_chi(vai) else {"amount_lak": None})}


def _ban_chat(db, v):
    p = db.get(Trip, v.trip_id) if v.trip_id else None
    if p is None:
        return {"hinh_thuc": None, "owner_name": None}
    return {"hinh_thuc": hinh_thuc(p, "tam_ung" if v.kind == "advance" else "xuat"),
            "owner_name": p.owner_name if p.company == "joint" else None}


def _phieu(db, tid):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu xuất xe này."})
    return p


def _dong(db, p):
    return db.query(TripExpense).filter(TripExpense.trip_id == p.id).order_by(TripExpense.line_no).all()


def _dong_kho_theo_diem(db, p):
    """Các dòng nhiên liệu LĨNH TỪ KHO EPL, gom theo điểm đổ. Dòng mua ngoài không sinh phiếu lĩnh."""
    ra = {}
    for d in _dong(db, p):
        if d.section != "fuel" or not d.paid_by_epl or d.source != "kho" or d.stock_move_id:
            continue
        # dòng cũ chỉ có khoá "fp_yard", không có điểm đổ → kho gốc, như lúc ghi sổ còn tự xuất (từ 30/09 dầu kho CHỈ rời kho
        # theo phiếu đề nghị đã cấp, nên dòng nào cũng phải lập được phiếu đề nghị)
        ma = d.place_id or GV.kho_goc(db)
        diem = db.get(FuelPlace, ma) if ma else None
        if not diem or diem.owner_type != "epl":
            continue
        ra.setdefault(diem.id, []).append(d)
    return ra


def _tien_tam_ung(db, p):
    """Tiền mặt tài xế cầm đi: khoản EPL ứng, KHÔNG lấy từ kho, thuộc mục III (dầu mua dọc đường),
    IV (đi đường) và VI (khác). Phải trùng đúng bộ khoản mà màn Tất toán coi là "tài xế đã chi",
    nếu không thì hai màn nói hai con số khác nhau về cùng một chuyến."""
    return sum(_lak(p, d) for d in _dong(db, p) if la_tien_mat_tai_xe(d, p.company))


@router.get("/api/trips/{tid}/vouchers")
def ds_phieu_linh_cua_phieu(tid: str, request: Request, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = _phieu(db, tid)
    # tài xế chỉ xem tờ đề nghị của phiếu mình — tờ có mã QR, đưa mã của người khác là cấp nhầm người (30/09)
    if user.role == "driver" and (not user.driver_id or p.driver_id != user.driver_id):
        raise HTTPException(403, {"ma": "KHONG_PHAI_PHIEU_CUA_BAN", "loi": "Đây không phải phiếu của bạn."})
    goc = str(request.base_url).rstrip("/")
    ds = db.query(Voucher).filter(Voucher.trip_id == p.id).order_by(Voucher.kind, Voucher.doc_no).all()
    return [xuat_phieu_linh(db, v, goc, user.role) for v in ds]


@router.post("/api/trips/{tid}/vouchers")
def lap_phieu_linh(tid: str, request: Request, d: dict = Body(...), db: Session = Depends(get_db),
                   user=Depends(can_vai("yard", "acct", "expacct", "fuel", "cash", "treasury"))):
    """Lập (hoặc lấy lại) phiếu lĩnh của một chuyến.

    kind='fuel'    → mỗi ĐIỂM ĐỔ của kho EPL một tờ, số lít là tổng các dòng dầu lĩnh ở kho đó.
    kind='advance' → một tờ duy nhất, số tiền là tổng khoản EPL ứng ở mục IV và VI.
    Phiếu đã cấp rồi thì trả nguyên, không lập đè.
    """
    p = _phieu(db, tid)
    if p.locked and user.role in ("yard", "driver"):
        raise HTTPException(409, {"ma": "DA_KHOA", "loi": "Phiếu %s đã khoá, không lập thêm phiếu đề nghị." % p.doc_no})
    loai = d.get("kind") or "fuel"
    if loai not in TIEN_TO:
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "Chỉ có phiếu đề nghị xuất kho nhiên liệu hoặc phiếu đề nghị tạm ứng."})
    goc = str(request.base_url).rstrip("/")
    ngay = p.out_date or p.doc_date or dt.date.today()
    chung = dict(trip_id=p.id, kind=loai, doc_date=ngay, driver_id=p.driver_id,
                 driver_name=p.driver_name, truck_no=p.truck_no, issued_by=user.full_name)
    ra = []

    if loai == "advance":
        v = dam_bao_tam_ung(db, p, user)
        if v is None:
            raise HTTPException(422, {"ma": "KHONG_CO_TIEN", "loi": "Phiếu chưa có khoản nào tài xế cầm tiền mặt đi "
                                                                    "(cách trả «Chi ngay khi xe đi»)."})
        db.commit()
        ra = [v]
    else:
        nhom = _dong_kho_theo_diem(db, p)
        cu = {v.place_id: v for v in db.query(Voucher).filter(Voucher.trip_id == p.id, Voucher.kind == "fuel").all()}
        for pid, dong in nhom.items():
            lit = sum(x.qty or 0 for x in dong)
            v = cu.get(pid)
            if v is None:
                so = "PLNL-%s-%d" % (p.doc_no, db.query(Voucher).filter(
                    Voucher.trip_id == p.id, Voucher.kind == "fuel").count() + len(ra) + 1)
                v = Voucher(doc_no=so, token=secrets.token_urlsafe(9), place_id=pid, qty_l=lit, **chung)
                db.add(v); cu[pid] = v
            elif v.status == "cho":
                v.qty_l = lit
            ra.append(v)
        # phiếu đã lập nhưng dòng bị xoá hết thì huỷ cho khỏi treo ở màn thủ kho
        for pid, v in cu.items():
            if pid not in nhom and v.status == "cho":
                v.status = "huy"
        if not ra:
            raise HTTPException(422, {"ma": "KHONG_CO_DONG", "loi": "Phiếu chưa có dòng dầu nào lĩnh từ kho EPL."})
        db.flush()
        for v in ra:
            diem = db.get(FuelPlace, v.place_id) if v.place_id else None
            CT.ghi(db, "PLNL", nguon_bang="vouchers", nguon_id=v.id, trip=p, ngay=ngay, doi_tuong_loai="kho",
                   # Tờ phiếu lĩnh KHÔNG có tiền — số lít nằm trong payload. Trước đây ghi lít vào ô tiền với "tiền tệ" = L,
                   # bên nhận (sổ kế toán) từ chối đúng: L không phải tiền tệ. Bắt được khi đẩy thật sang EPL_KETOAN 22/09.
                   doi_tuong_ten=diem.name if diem else None, tien=None, tien_te="LAK", by_user=user.full_name,
                   mo_ta="Lĩnh %s lít tại %s" % (v.qty_l, diem.name if diem else "?"),
                   payload={"voucher_id": v.id, "doc_no": v.doc_no, "qty_l": v.qty_l, "hinh_thuc": hinh_thuc(p, "xuat"),
                            "owner_id": p.owner_id, "owner_name": p.owner_name})
        db.commit()
    return [xuat_phieu_linh(db, v, goc, user.role) for v in ra]


@router.get("/api/vouchers")
def ds_cho_cap(request: Request, response: Response, trang_thai: str = "cho", loai: str = "", co: int = 500, q: str = "",
               db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Danh sách phiếu lĩnh đang chờ. Thủ kho CHỈ thấy phiếu của kho mình phụ trách.
    Dữ liệu cả năm (24/09): tối đa `co` tờ mới nhất (mặc định 500) — header X-Tong là tổng số khớp; phiếu xe và
    mục IV nạp MỘT lần cho cả danh sách (trước đây hai câu cho mỗi tờ)."""
    if user.role in ("repair", "parts"):
        # hai vai này không có màn Phiếu đề nghị chi, không cấp dầu, không chi tiền (30/09)
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem phiếu đề nghị." % user.role})
    tim = (q or "").strip()
    q = db.query(Voucher)
    if trang_thai:
        q = q.filter(Voucher.status == trang_thai)
    if tim:
        # màn Phiếu đề nghị chi (30/09): tìm theo số đề nghị, số DO, số xe, tài xế
        k = "%" + tim + "%"
        q = q.filter(or_(Voucher.doc_no.ilike(k), Voucher.truck_no.ilike(k), Voucher.driver_name.ilike(k),
                         Voucher.trip_id.in_(db.query(Trip.id).filter(Trip.doc_no.ilike(k)))))
    if loai:
        q = q.filter(Voucher.kind == loai)
    if user.role == "depot":
        if not user.place_id:
            raise HTTPException(409, {"ma": "CHUA_GAN_KHO", "loi": "Tài khoản thủ kho chưa gắn với điểm đổ nào."})
        q = q.filter(Voucher.kind == "fuel", Voucher.place_id == user.place_id)
    elif user.role == "driver":
        q = q.filter(Voucher.driver_id == (user.driver_id or "~"))
    goc = str(request.base_url).rstrip("/")
    response.headers["X-Tong"] = str(q.order_by(None).count())
    ds = q.order_by(Voucher.doc_date.desc(), Voucher.doc_no).limit(max(1, min(int(co or 500), 2000))).all()
    ma = list({v.trip_id for v in ds if v.trip_id})
    phieu = {t.id: t for t in (db.query(Trip.id, Trip.origin, Trip.destination, Trip.plate_head, Trip.plate_trailer,
                                        Trip.customer_name, Trip.doc_no, Trip.kind, Trip.company)
                               .filter(Trip.id.in_(ma)))} if ma else {}
    iv = {}
    if ma:
        for tid, st in (db.query(TripSection.trip_id, TripSection.status)
                        .filter(TripSection.trip_id.in_(ma), TripSection.section == "travel")):
            iv.setdefault(tid, st)
    # phiếu chi tạm ứng bên hệ kế toán (01/10) — nạp một lần cho cả danh sách
    from models import ChiTune
    from services import chi_tune as CHI
    ung = [v.id for v in ds if v.kind == "advance"]
    chi = {c.voucher_id: c for c in db.query(ChiTune).filter(ChiTune.voucher_id.in_(ung))} if ung else {}
    ra = []
    for v in ds:
        x = xuat_phieu_linh(db, v, goc, user.role)
        p = phieu.get(v.trip_id)
        if p:
            x.update({"origin": p.origin, "destination": p.destination, "plate_head": p.plate_head,
                      "plate_trailer": p.plate_trailer, "customer_name": p.customer_name,
                      "muc_travel": iv.get(p.id, "wait"), "trip_doc_no": p.doc_no, "trip_kind": p.kind, "company": p.company})
        if v.kind == "advance":
            x["chi_ke_toan"] = CHI.xuat(chi.get(v.id), thay_tien=thay_tien_chi(user.role))
        ra.append(x)
    return ra


@router.get("/api/vouchers/tra-cuu/{token}")
def tra_cuu(token: str, request: Request, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Quét mã QR ra đây. Trả cả thông tin xe và chuyến để người cấp đối chiếu đúng xe, đúng tài xế."""
    v = db.query(Voucher).filter(Voucher.token == token).first()
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Mã này không có trong hệ thống."})
    p = db.get(Trip, v.trip_id)
    x = xuat_phieu_linh(db, v, str(request.base_url).rstrip("/"), user.role)
    if p:
        x["phieu"] = {"doc_no": p.doc_no, "truck_no": p.truck_no, "plate_head": p.plate_head,
                      "plate_trailer": p.plate_trailer, "driver_name": p.driver_name, "company": p.company,
                      "owner_name": p.owner_name, "origin": p.origin, "destination": p.destination,
                      "customer_name": p.customer_name, "goods_type": p.goods_type,
                      "weight_origin": p.weight_origin, "price": p.price, "price_ccy": p.price_ccy,
                      "out_date": p.out_date.isoformat() if p.out_date else None,
                      "transport_status": p.transport_status}
        if v.kind == "fuel":
            goc = GV.kho_goc(db)              # dòng cũ không có điểm đổ thuộc kho gốc (như _dong_kho_theo_diem)
            dong = [e for e in _dong(db, p) if e.section == "fuel" and (e.place_id or goc) == v.place_id]
        else:
            dong = [e for e in _dong(db, p) if la_tien_mat_tai_xe(e, p.company) and e.section in ("travel", "other")]
        x["dong"] = [{"item_key": e.item_key, "item_name": e.item_name, "qty": e.qty, "unit_price": e.unit_price,
                      "currency": e.currency, "tien_lak": _lak(p, e), "acct_code": TK.tk_dong(p.company, e)} for e in dong]
        # người quét QR không thấy tiền bán thì không nhận giá cước; không thấy tiền chi thì không nhận đơn giá
        if not thay_tien_ban(user.role):
            x["phieu"].pop("price", None); x["phieu"].pop("price_ccy", None)
        if not thay_tien_chi(user.role):
            for d in x["dong"]:
                for c in ("unit_price", "currency", "tien_lak", "acct_code"): d.pop(c, None)
        elif v.kind == "fuel" and not thay_gia_kho(user.role):
            # dầu kho mang GIÁ VỐN bình quân — thủ kho quét QR không thấy (30/09; trước đây lọc theo tiền chi nên thủ kho vẫn thấy)
            for d in x["dong"]:
                for c in ("unit_price", "tien_lak"): d.pop(c, None)
    return x


@router.post("/api/vouchers/{vid}/cap")
def cap_phat(vid: str, d: dict = Body(default={}), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Cấp dầu (thủ kho) hoặc chi tiền tạm ứng (quỹ). Hai việc khác nhau nên hai nhánh rõ ràng."""
    v = db.get(Voucher, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu đề nghị này."})
    if v.status != "cho":
        raise HTTPException(409, {"ma": "DA_CAP", "loi": "Phiếu này đã cấp hoặc đã huỷ."})
    p = _phieu(db, v.trip_id)

    # Cấp dầu = xuất ở kho nhiên liệu bên trang kế toán (28/09). Cả lần cấp đi trong GiaoDichKho: bên này hỏng thì lần
    # xuất bên kia được huỷ; trang kế toán tắt → 503, chưa cấp được (màn Cấp phát giữ việc trong hàng đợi, nối lại tự gửi).
    with KK.GiaoDichKho(db, user) as gd:
        if v.kind == "fuel":
            if user.role not in ("depot", "fuel", "admin"):
                raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ thủ kho nhiên liệu mới cấp dầu."})
            if user.role == "depot" and user.place_id != v.place_id:
                raise HTTPException(403, {"ma": "KHAC_KHO", "loi": "Phiếu này lĩnh ở kho khác, không phải kho của bạn."})
            lit = d.get("qty")
            lit = float(str(lit).replace(",", "")) if lit not in (None, "") else (v.qty_l or 0)
            if lit <= 0:
                raise HTTPException(422, {"ma": "SO_LIT_SAI", "loi": "Số lít cấp phải lớn hơn 0."})
            ly_do = str(d.get("note") or "").strip()
            if abs(lit - (v.qty_l or 0)) > 0.001 and not ly_do:
                raise HTTPException(422, {"ma": "THIEU_LY_DO",
                                          "loi": "Cấp %s lít khác số duyệt %s lít thì phải ghi lý do." % (lit, v.qty_l)})
            dong = _dong_kho_theo_diem(db, p).get(v.place_id, [])
            if not dong:
                raise HTTPException(409, {"ma": "KHONG_CON_DONG", "loi": "Các dòng dầu của kho này đã xuất rồi."})
            # giá BÌNH QUÂN của đúng kho cấp, lúc cấp (anh Khampla C5.3) — trang kế toán tính; dòng trên phiếu mang theo giá đó
            r = gd.xuat_dau(khoa="voucher:" + v.id, place_id=v.place_id, qty_l=lit, ngay=dt.date.today(), doc_no=v.doc_no,
                            truck_no=p.truck_no, expense_id=dong[0].id, voucher_id=v.id, voucher_doc_no=v.doc_no, trip_no=p.doc_no,
                            company=p.company, gia_du_phong=(dong[0].unit_price or 0) * ty_gia(p, dong[0].currency or "LAK"),
                            mo_ta="Cấp %s lít dầu theo %s" % (lit, v.doc_no), note="Cấp theo phiếu đề nghị %s" % v.doc_no)
            for e in dong:
                e.unit_price, e.currency = r["unit_price"], "LAK"
                e.stock_move_id = r["move_id"]
            if abs(lit - (v.qty_l or 0)) > 0.001 and len(dong) == 1:
                dong[0].qty = lit                        # cấp lệch thì phiếu xuất xe ghi theo số thật
            v.granted_qty, v.granted_note = lit, ly_do or None
        else:
            from services import chi_tune as CHI
            tt = (db.query(TripSection).filter(TripSection.trip_id == p.id, TripSection.section == "travel").first())
            if tt is None:
                tt = TripSection(trip_id=p.id, section="travel", status="wait"); db.add(tt)
            # Đi đúng chuỗi duyệt: chỉ vai giữ quỹ mới chi, và mục IV phải "đã ghi sổ" trước. Hỏi QUYỀN trước, rồi mới nói
            # tạm ứng chi ở hệ kế toán (01/10) — tài xế tự quét phải nghe "không có quyền".
            moi = chuyen_muc(user.role, "travel", tt.status, "pay")
            if CHI.chi_o_ke_toan() and user.role != "admin":
                raise HTTPException(409, {"ma": "CHI_O_KE_TOAN", "loi": CHI.cau_chan_chi(db, p)})
            tt.status = moi
            v.amount_lak = _tien_tam_ung(db, p)    # chi đúng số tiền mặt lúc chi — kế toán nhập giá sau khi Bãi in tờ
            _khop_ct_tam_ung(db, v)
            CT.ghi(db, "PC_TU", nguon_bang="vouchers", nguon_id=v.id, trip=p, ngay=dt.date.today(), phuong_thuc="cash", doi_tuong_loai="tai_xe",
                   doi_tuong_ten=p.driver_name, tien=v.amount_lak, tien_te="LAK", section="travel", by_user=user.full_name,
                   mo_ta="Chi theo đề nghị tạm ứng %s" % v.doc_no,
                   payload={"voucher_doc_no": v.doc_no, "driver_id": p.driver_id, "truck_no": p.truck_no,
                            "hinh_thuc": hinh_thuc(p, "tam_ung"), "owner_id": p.owner_id, "owner_name": p.owner_name})
        v.status, v.granted_by, v.granted_at = "da_cap", user.full_name, dt.datetime.utcnow()
    return xuat_phieu_linh(db, v, "", user.role)


@router.post("/api/vouchers/{vid}/huy")
def huy_phieu(vid: str, db: Session = Depends(get_db), user=Depends(can_vai("yard", "acct", "fuel"))):
    v = db.get(Voucher, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu đề nghị này."})
    if v.status == "da_cap":
        raise HTTPException(409, {"ma": "DA_CAP", "loi": "Phiếu đã cấp thì không huỷ được."})
    if v.kind == "advance":
        from services import chi_tune as CHI
        CHI.rut(db, voucher_id=v.id)                 # phiếu chi bên kế toán chưa ghi sổ thì rút; đã chi thì chặn
    v.status = "huy"; db.commit()
    return xuat_phieu_linh(db, v, "", user.role)


# ================================================================ mã QR
@router.get("/api/vouchers/{vid}/qr.png")
def anh_qr(vid: str, request: Request, db: Session = Depends(get_db)):
    """Ảnh QR của phiếu lĩnh. Không chặn đăng nhập vì thẻ <img> của trình duyệt không gửi kèm phiên;
    nội dung QR chỉ là một đường dẫn tra cứu, mở ra vẫn phải đăng nhập mới xem được."""
    v = db.get(Voucher, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu đề nghị này."})
    noi_dung = (KK.web_ke_toan(db) or str(request.base_url).rstrip("/")) + "/#/cap-phat?ma=" + v.token
    try:
        import qrcode
    except ImportError:
        raise HTTPException(503, {"ma": "THIEU_THU_VIEN", "loi": "Máy chủ chưa cài thư viện qrcode."})
    anh = qrcode.make(noi_dung, border=2, box_size=6)
    buf = io.BytesIO()
    anh.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "public, max-age=600"})
