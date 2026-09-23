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
thì sinh luôn dòng xuất kho và đánh dấu dòng chi, nên lúc kế toán ghi sổ mục III sẽ không xuất lần
hai (hàm _xuat_kho_nhien_lieu bỏ qua dòng đã có stock_move_id). Còn chi tạm ứng là việc TIỀN, nên nó
đi đúng chuỗi duyệt: mục IV phải "đã ghi sổ" rồi mới chi được, và chỉ vai giữ quỹ mới chi.
"""
import datetime as dt
import io
import secrets

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import FuelMove, FuelPlace, Supplier, Trip, TripExpense, TripSection, Voucher
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import chuyen_muc
from services.tinh_toan import ty_gia
from services import chung_tu as CT
from services import gia_von as GV

router = APIRouter()
SUA_DIEM = can_vai("yard", "acct", "fuel")
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


@router.post("/api/fuel-places")
def them_diem(d: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_DIEM)):
    if not str(d.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Điểm đổ phải có tên."})
    x = FuelPlace(code=d.get("code"), name=d["name"].strip(), country=(d.get("country") or "LA").upper(),
                  owner_type=d.get("owner_type") or "epl", supplier_id=d.get("supplier_id") or None,
                  address=d.get("address"), note=d.get("note"), active=bool(d.get("active", True)))
    db.add(x); db.commit()
    return xuat_diem(db, x)


@router.put("/api/fuel-places/{pid}")
def sua_diem(pid: str, d: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_DIEM)):
    x = db.get(FuelPlace, pid)
    if not x:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có điểm đổ này."})
    for c in ("code", "name", "country", "owner_type", "supplier_id", "address", "note", "active"):
        if c in d:
            setattr(x, c, d[c] if d[c] != "" else None)
    x.active = bool(x.active)
    db.commit()
    return xuat_diem(db, x)


@router.delete("/api/fuel-places/{pid}")
def xoa_diem(pid: str, db: Session = Depends(get_db), user=Depends(SUA_DIEM)):
    x = db.get(FuelPlace, pid)
    if not x:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có điểm đổ này."})
    if db.query(TripExpense).filter(TripExpense.place_id == pid).count():
        raise HTTPException(409, {"ma": "DANG_DUNG", "loi": "Điểm đổ đã có trên phiếu, chỉ được ngưng dùng."})
    db.delete(x); db.commit()
    return {"ok": True}


# ================================================================ phiếu lĩnh
def _lak(p, d):
    return (d.qty or 0) * (d.unit_price or 0) * ty_gia(p, d.currency)


def xuat_phieu_linh(db, v, goc=""):
    diem = db.get(FuelPlace, v.place_id) if v.place_id else None
    return {"id": v.id, "trip_id": v.trip_id, "kind": v.kind, "doc_no": v.doc_no,
            "doc_date": v.doc_date.isoformat() if v.doc_date else None,
            "place_id": v.place_id, "place_name": diem.name if diem else None,
            "place_country": diem.country if diem else None,
            "driver_id": v.driver_id, "driver_name": v.driver_name, "truck_no": v.truck_no,
            "qty_l": v.qty_l, "amount_lak": v.amount_lak, "status": v.status, "token": v.token,
            "qr": "/api/vouchers/%s/qr.png" % v.id, "tra_cuu": (goc or "") + "/#/cap-phat?ma=" + v.token,
            "issued_by": v.issued_by, "issued_at": v.issued_at.isoformat() if v.issued_at else None,
            "granted_by": v.granted_by, "granted_at": v.granted_at.isoformat() if v.granted_at else None,
            "granted_qty": v.granted_qty, "granted_note": v.granted_note, "note": v.note}


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
        diem = db.get(FuelPlace, d.place_id) if d.place_id else None
        if not diem or diem.owner_type != "epl":
            continue
        ra.setdefault(diem.id, []).append(d)
    return ra


def _tien_tam_ung(db, p):
    """Tiền mặt tài xế cầm đi: khoản EPL ứng, KHÔNG lấy từ kho, thuộc mục III (dầu mua dọc đường),
    IV (đi đường) và VI (khác). Phải trùng đúng bộ khoản mà màn Tất toán coi là "tài xế đã chi",
    nếu không thì hai màn nói hai con số khác nhau về cùng một chuyến."""
    return sum(_lak(p, d) for d in _dong(db, p)
               if d.paid_by_epl and d.source != "kho" and d.section in ("fuel", "travel", "other"))


@router.get("/api/trips/{tid}/vouchers")
def ds_phieu_linh_cua_phieu(tid: str, request: Request, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = _phieu(db, tid)
    goc = str(request.base_url).rstrip("/")
    ds = db.query(Voucher).filter(Voucher.trip_id == p.id).order_by(Voucher.kind, Voucher.doc_no).all()
    return [xuat_phieu_linh(db, v, goc) for v in ds]


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
        raise HTTPException(409, {"ma": "DA_KHOA", "loi": "Phiếu %s đã khoá, không lập thêm phiếu lĩnh." % p.doc_no})
    loai = d.get("kind") or "fuel"
    if loai not in TIEN_TO:
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "Chỉ có phiếu lĩnh nhiên liệu hoặc tạm ứng."})
    goc = str(request.base_url).rstrip("/")
    ngay = p.out_date or p.doc_date or dt.date.today()
    chung = dict(trip_id=p.id, kind=loai, doc_date=ngay, driver_id=p.driver_id,
                 driver_name=p.driver_name, truck_no=p.truck_no, issued_by=user.full_name)
    ra = []

    if loai == "advance":
        tien = _tien_tam_ung(db, p)
        if tien <= 0:
            raise HTTPException(422, {"ma": "KHONG_CO_TIEN", "loi": "Phiếu chưa có khoản nào EPL ứng cho tài xế."})
        v = db.query(Voucher).filter(Voucher.trip_id == p.id, Voucher.kind == "advance").first()
        if v is None:
            v = Voucher(doc_no="PTU-" + p.doc_no, token=secrets.token_urlsafe(9), amount_lak=tien, **chung)
            db.add(v)
        elif v.status == "cho":
            v.amount_lak = tien                     # chưa ai lấy tiền thì cập nhật theo số mới nhất
        db.flush()
        CT.ghi(db, "PTU", nguon_bang="vouchers", nguon_id=v.id, trip=p, ngay=ngay, doi_tuong_loai="tai_xe",
               doi_tuong_ten=p.driver_name, tien=v.amount_lak, tien_te="LAK", by_user=user.full_name,
               mo_ta="Tạm ứng đi đường phiếu %s" % p.doc_no, payload={"voucher_id": v.id, "doc_no": v.doc_no})
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
                   payload={"voucher_id": v.id, "doc_no": v.doc_no, "qty_l": v.qty_l})
        db.commit()
    return [xuat_phieu_linh(db, v, goc) for v in ra]


@router.get("/api/vouchers")
def ds_cho_cap(request: Request, trang_thai: str = "cho", loai: str = "", db: Session = Depends(get_db),
               user=Depends(nguoi_hien_tai)):
    """Danh sách phiếu lĩnh đang chờ. Thủ kho CHỈ thấy phiếu của kho mình phụ trách."""
    q = db.query(Voucher)
    if trang_thai:
        q = q.filter(Voucher.status == trang_thai)
    if loai:
        q = q.filter(Voucher.kind == loai)
    if user.role == "depot":
        if not user.place_id:
            raise HTTPException(409, {"ma": "CHUA_GAN_KHO", "loi": "Tài khoản thủ kho chưa gắn với điểm đổ nào."})
        q = q.filter(Voucher.kind == "fuel", Voucher.place_id == user.place_id)
    elif user.role == "driver":
        q = q.filter(Voucher.driver_id == (user.driver_id or "~"))
    goc = str(request.base_url).rstrip("/")
    ra = []
    for v in q.order_by(Voucher.doc_date.desc(), Voucher.doc_no).all():
        x = xuat_phieu_linh(db, v, goc)
        p = db.get(Trip, v.trip_id)
        if p:
            x.update({"origin": p.origin, "destination": p.destination, "plate_head": p.plate_head,
                      "plate_trailer": p.plate_trailer, "customer_name": p.customer_name,
                      "muc_travel": (db.query(TripSection)
                                     .filter(TripSection.trip_id == p.id, TripSection.section == "travel")
                                     .first() or TripSection(status="wait")).status})
        ra.append(x)
    return ra


@router.get("/api/vouchers/tra-cuu/{token}")
def tra_cuu(token: str, request: Request, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Quét mã QR ra đây. Trả cả thông tin xe và chuyến để người cấp đối chiếu đúng xe, đúng tài xế."""
    v = db.query(Voucher).filter(Voucher.token == token).first()
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Mã này không có trong hệ thống."})
    p = db.get(Trip, v.trip_id)
    x = xuat_phieu_linh(db, v, str(request.base_url).rstrip("/"))
    if p:
        x["phieu"] = {"doc_no": p.doc_no, "truck_no": p.truck_no, "plate_head": p.plate_head,
                      "plate_trailer": p.plate_trailer, "driver_name": p.driver_name, "company": p.company,
                      "owner_name": p.owner_name, "origin": p.origin, "destination": p.destination,
                      "customer_name": p.customer_name, "goods_type": p.goods_type,
                      "weight_origin": p.weight_origin, "price": p.price, "price_ccy": p.price_ccy,
                      "out_date": p.out_date.isoformat() if p.out_date else None,
                      "transport_status": p.transport_status}
        if v.kind == "fuel":
            dong = [e for e in _dong(db, p) if e.section == "fuel" and e.place_id == v.place_id]
        else:
            dong = [e for e in _dong(db, p)
                    if e.paid_by_epl and e.source != "kho" and e.section in ("travel", "other")]
        x["dong"] = [{"item_key": e.item_key, "item_name": e.item_name, "qty": e.qty, "unit_price": e.unit_price,
                      "currency": e.currency, "tien_lak": _lak(p, e), "acct_code": e.acct_code} for e in dong]
    return x


@router.post("/api/vouchers/{vid}/cap")
def cap_phat(vid: str, d: dict = Body(default={}), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Cấp dầu (thủ kho) hoặc chi tiền tạm ứng (quỹ). Hai việc khác nhau nên hai nhánh rõ ràng."""
    v = db.get(Voucher, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu lĩnh này."})
    if v.status != "cho":
        raise HTTPException(409, {"ma": "DA_CAP", "loi": "Phiếu này đã cấp hoặc đã huỷ."})
    p = _phieu(db, v.trip_id)

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
        # giá BÌNH QUÂN của đúng kho cấp, lúc cấp (anh Khampla C5.3) — dòng trên phiếu mang theo giá đó
        don_gia = GV.gia_bq_dau(db, v.place_id) or (dong[0].unit_price or 0) * ty_gia(p, dong[0].currency or "LAK")
        for e in dong:
            e.unit_price, e.currency = don_gia, "LAK"
        m = FuelMove(move_date=dt.date.today(), doc_no=v.doc_no, kind="out", truck_no=p.truck_no, qty_l=lit,
                     unit_price=don_gia, currency="LAK", unit_cost_lak=don_gia, place_id=v.place_id, voucher_id=v.id,
                     note="Cấp theo phiếu lĩnh %s" % v.doc_no, by_user=user.full_name, expense_id=dong[0].id)
        db.add(m); db.flush()
        for e in dong:
            e.stock_move_id = m.id
        diem = db.get(FuelPlace, v.place_id) if v.place_id else None
        CT.ghi(db, "PXK_NL", nguon_bang="fuel_moves", nguon_id=m.id, trip=p, ngay=m.move_date, doi_tuong_loai="kho",
               doi_tuong_ten=diem.name if diem else None, tien=lit * don_gia, tien_te=m.currency,
               tien_lak=lit * don_gia * ty_gia(p, m.currency), section="fuel", by_user=user.full_name,
               mo_ta="Cấp %s lít dầu theo %s" % (lit, v.doc_no),
               payload={"voucher_doc_no": v.doc_no, "qty_l": lit, "unit_price": don_gia, "currency": m.currency,
                        "place_id": v.place_id, "truck_no": p.truck_no, "driver_name": p.driver_name})
        if abs(lit - (v.qty_l or 0)) > 0.001 and len(dong) == 1:
            dong[0].qty = lit                        # cấp lệch thì phiếu xuất xe ghi theo số thật
        v.granted_qty, v.granted_note = lit, ly_do or None
    else:
        tt = (db.query(TripSection).filter(TripSection.trip_id == p.id, TripSection.section == "travel").first())
        if tt is None:
            tt = TripSection(trip_id=p.id, section="travel", status="wait"); db.add(tt)
        # Đi đúng chuỗi duyệt: chỉ vai giữ quỹ mới chi, và mục IV phải "đã ghi sổ" trước.
        tt.status = chuyen_muc(user.role, "travel", tt.status, "pay")
        CT.ghi(db, "PC_TU", nguon_bang="vouchers", nguon_id=v.id, trip=p, ngay=dt.date.today(), phuong_thuc="cash", doi_tuong_loai="tai_xe",
               doi_tuong_ten=p.driver_name, tien=v.amount_lak, tien_te="LAK", section="travel", by_user=user.full_name,
               mo_ta="Chi tạm ứng đi đường theo %s" % v.doc_no,
               payload={"voucher_doc_no": v.doc_no, "driver_id": p.driver_id, "truck_no": p.truck_no})

    v.status, v.granted_by, v.granted_at = "da_cap", user.full_name, dt.datetime.utcnow()
    db.commit()
    return xuat_phieu_linh(db, v)


@router.post("/api/vouchers/{vid}/huy")
def huy_phieu(vid: str, db: Session = Depends(get_db), user=Depends(can_vai("yard", "acct", "fuel"))):
    v = db.get(Voucher, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu lĩnh này."})
    if v.status == "da_cap":
        raise HTTPException(409, {"ma": "DA_CAP", "loi": "Phiếu đã cấp thì không huỷ được."})
    v.status = "huy"; db.commit()
    return xuat_phieu_linh(db, v)


# ================================================================ mã QR
@router.get("/api/vouchers/{vid}/qr.png")
def anh_qr(vid: str, request: Request, db: Session = Depends(get_db)):
    """Ảnh QR của phiếu lĩnh. Không chặn đăng nhập vì thẻ <img> của trình duyệt không gửi kèm phiên;
    nội dung QR chỉ là một đường dẫn tra cứu, mở ra vẫn phải đăng nhập mới xem được."""
    v = db.get(Voucher, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu lĩnh này."})
    noi_dung = str(request.base_url).rstrip("/") + "/#/cap-phat?ma=" + v.token
    try:
        import qrcode
    except ImportError:
        raise HTTPException(503, {"ma": "THIEU_THU_VIEN", "loi": "Máy chủ chưa cài thư viện qrcode."})
    anh = qrcode.make(noi_dung, border=2, box_size=6)
    buf = io.BytesIO()
    anh.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "public, max-age=600"})
