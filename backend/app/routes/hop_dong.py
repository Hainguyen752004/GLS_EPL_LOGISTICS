# -*- coding: utf-8 -*-
"""HỢP ĐỒNG — ສັນຍາ (chủ dự án chốt 24/09).

Hai loại, cùng một bảng:
    khach    hợp đồng vận chuyển với khách        — ສັນຍາຂົນສົ່ງ
    thue_xe  hợp đồng thuê xe với chủ xe liên kết — ສັນຍາເຊົ່າລົດ

Hợp đồng là giấy KHUNG ký một lần: số, ngày ký, hiệu lực, bản scan. Điều khoản tính tiền vẫn nằm ở chỗ đã có
(bảng giá khách × tuyến, điều khoản chủ xe) — không dựng bộ giá thứ hai. Phiếu xuất xe tự mang số hợp đồng còn
hiệu lực của khách (và của chủ xe nếu là xe liên kết) — xem `tim()` và routes/phieu.py `_ap_truong`.

    GET    /api/hop-dong?kind=&customer_id=&owner_id=     danh sách (mọi vai trừ tài xế, thủ kho)
    POST   /api/hop-dong                                  thêm   (khách: KT Thu/Chi, KT Doanh thu · thuê xe: KT Thu/Chi)
    PUT    /api/hop-dong/{id}                             sửa
    DELETE /api/hop-dong/{id}                             xoá — chỉ khi chưa phiếu nào chạy theo; có rồi thì "ngưng dùng"
    POST   /api/hop-dong/{id}/tep                         đưa bản scan lên (ảnh / PDF, 8 MB)
    GET    /api/hop-dong-tep/{fid}?tk=                    mở bản scan — chỉ vai được thấy tiền bán (giấy có giá)
    DELETE /api/hop-dong-tep/{fid}
"""
import datetime as dt
import mimetypes
import os

from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import LOAI_HOP_DONG, Contract, ContractFile, Customer, Owner, Trip, ma_moi
from services.bao_mat import nguoi_hien_tai, nguoi_tu_token
from services.phan_quyen import thay_tien_ban
from services.tep import loi_co_tep, ten_tep, TEP_KIEU, TEP_TOI_DA, THU_MUC_HOP_DONG

router = APIRouter()
SAP_HET_NGAY = 30                     # còn ≤ 30 ngày thì báo "sắp hết hạn" (bằng lái dùng 60, hợp đồng ký lại nhanh hơn)
VAI_SUA = {"khach": ("acct", "rev", "admin"), "thue_xe": ("acct", "admin")}
VAI_KHONG_XEM = ("driver", "depot", "parts")


def _loi(ma, loi, code=422):
    raise HTTPException(code, {"ma": ma, "loi": loi})


def _ngay(v, ten):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        _loi("NGAY_SAI", "%s phải là ngày dạng YYYY-MM-DD." % ten)


def trang_thai(c, ngay=None):
    """con_han · sap_het · het_han · chua_hieu_luc · ngung — tính theo `ngay` (mặc định hôm nay)."""
    ngay = ngay or dt.date.today()
    if not c.active:
        return "ngung"
    tu = c.valid_from or c.sign_date
    if tu and tu > ngay:
        return "chua_hieu_luc"
    if c.valid_to and c.valid_to < ngay:
        return "het_han"
    if c.valid_to and (c.valid_to - ngay).days <= SAP_HET_NGAY:
        return "sap_het"
    return "con_han"


def tim(db, kind, doi_tac_id, ngay=None):
    """Hợp đồng còn hiệu lực của khách / chủ xe tại ngày `ngay` — cái có hiệu lực muộn nhất. Không có thì None."""
    if not doi_tac_id:
        return None
    ngay = ngay or dt.date.today()
    cot = Contract.customer_id if kind == "khach" else Contract.owner_id
    ds = (db.query(Contract).filter(Contract.kind == kind, cot == doi_tac_id, Contract.active.is_(True))
          .filter(or_(Contract.valid_to.is_(None), Contract.valid_to >= ngay)).all())
    ds = [c for c in ds if not ((c.valid_from or c.sign_date) and (c.valid_from or c.sign_date) > ngay)]
    ds.sort(key=lambda c: (c.valid_from or c.sign_date or dt.date.min, c.created_at or dt.datetime.min), reverse=True)
    return ds[0] if ds else None


def het_han_gan_nhat(db, kind, doi_tac_id, ngay):
    """Hợp đồng đã HẾT HẠN trước `ngay` (để cảnh báo lúc khoá phiếu: khách có hợp đồng nhưng hết hạn rồi)."""
    cot = Contract.customer_id if kind == "khach" else Contract.owner_id
    ds = [c for c in db.query(Contract).filter(Contract.kind == kind, cot == doi_tac_id, Contract.active.is_(True)).all()
          if c.valid_to and c.valid_to < ngay]
    return max(ds, key=lambda c: c.valid_to) if ds else None


def _xuat_tep(f):
    return {"id": f.id, "filename": f.filename, "content_type": f.content_type, "size": f.size, "by_user": f.by_user,
            "ts": f.ts.isoformat() if f.ts else None, "url": "/api/hop-dong-tep/%s" % f.id,
            "la_anh": (f.content_type or "").startswith("image/")}


def xuat(db, c, vai, dem=None):
    """`dem` = {(kind, id hợp đồng): số phiếu} đã đếm sẵn cho cả danh sách (đếm theo tháng, đệm) — không có thì đếm thẳng."""
    kh = db.get(Customer, c.customer_id) if c.customer_id else None
    chu = db.get(Owner, c.owner_id) if c.owner_id else None
    ngay_con = (c.valid_to - dt.date.today()).days if c.valid_to else None
    cot = Trip.contract_id if c.kind == "khach" else Trip.hire_contract_id
    ra = {"id": c.id, "contract_no": c.contract_no, "kind": c.kind, "customer_id": c.customer_id, "owner_id": c.owner_id,
          "doi_tac": (kh.name if kh else None) or (chu.name if chu else None),
          "sign_date": c.sign_date.isoformat() if c.sign_date else None,
          "valid_from": c.valid_from.isoformat() if c.valid_from else None,
          "valid_to": c.valid_to.isoformat() if c.valid_to else None,
          "note": c.note, "active": bool(c.active), "trang_thai": trang_thai(c), "ngay_con": ngay_con,
          "so_phieu": (dem.get(c.id, 0) if dem is not None else db.query(Trip.id).filter(cot == c.id).count()),
          "created_by": c.created_by}
    # Bản scan có giá cước / giá thuê → chỉ vai được thấy tiền bán mới thấy tệp (Bãi thấy số, hạn — không thấy giấy).
    if thay_tien_ban(vai):
        ra["files"] = [_xuat_tep(f) for f in db.query(ContractFile).filter(ContractFile.contract_id == c.id).order_by(ContractFile.ts).all()]
    return ra


def _quyen_sua(user, kind):
    if user.role not in VAI_SUA.get(kind, ("admin",)):
        _loi("KHONG_CO_QUYEN", "Hợp đồng %s do kế toán Viêng Chăn quản lý." % ("vận chuyển với khách" if kind == "khach" else "thuê xe"), 403)


def _ap(db, c, d, moi):
    if moi or "kind" in d:
        k = (d.get("kind") or c.kind or "khach").strip()
        if k not in LOAI_HOP_DONG:
            _loi("LOAI_SAI", "Loại hợp đồng phải là 'khach' (vận chuyển với khách) hoặc 'thue_xe' (thuê xe liên kết).")
        c.kind = k
    if moi or "contract_no" in d:
        so = str(d.get("contract_no") or "").strip()
        if not so:
            _loi("THIEU_SO", "Chưa ghi số hợp đồng.")
        trung = db.query(Contract).filter(Contract.contract_no == so, Contract.id != (c.id or "")).first()
        if trung:
            _loi("TRUNG_SO", "Số hợp đồng %s đã có." % so, 409)
        c.contract_no = so
    if c.kind == "khach":
        if moi or "customer_id" in d:
            if not db.get(Customer, str(d.get("customer_id") or "")):
                _loi("KHONG_THAY", "Chưa chọn khách hàng của hợp đồng.")
            c.customer_id, c.owner_id = str(d["customer_id"]), None
    else:
        if moi or "owner_id" in d:
            if not db.get(Owner, str(d.get("owner_id") or "")):
                _loi("KHONG_THAY", "Chưa chọn chủ xe liên kết của hợp đồng.")
            c.owner_id, c.customer_id = str(d["owner_id"]), None
    for k, ten in (("sign_date", "Ngày ký"), ("valid_from", "Hiệu lực từ"), ("valid_to", "Hiệu lực đến")):
        if k in d:
            setattr(c, k, _ngay(d[k], ten))
    if c.valid_from and c.valid_to and c.valid_to < c.valid_from:
        _loi("NGAY_SAI", "Ngày hết hạn phải sau ngày bắt đầu hiệu lực.")
    if "note" in d:
        c.note = (d.get("note") or "").strip() or None
    if "active" in d:
        c.active = bool(d["active"])


@router.get("/api/hop-dong")
def ds(kind: str = None, customer_id: str = None, owner_id: str = None, db: Session = Depends(get_db),
       user=Depends(nguoi_hien_tai)):
    if user.role in VAI_KHONG_XEM:
        _loi("KHONG_CO_QUYEN", "Vai này không xem hợp đồng.", 403)
    q = db.query(Contract)
    if kind: q = q.filter(Contract.kind == kind)
    if customer_id: q = q.filter(Contract.customer_id == customer_id)
    if owner_id: q = q.filter(Contract.owner_id == owner_id)
    ds_ = q.all()
    ds_.sort(key=lambda c: (not c.active, -(c.valid_from or c.sign_date or dt.date.min).toordinal(), c.contract_no))
    from services import dem_bao_cao as DEM
    dem_kh = DEM.dem_phieu_theo(db, "sp-hop-dong", Trip.contract_id) if any(c.kind == "khach" for c in ds_) else {}
    dem_th = DEM.dem_phieu_theo(db, "sp-hop-dong-thue", Trip.hire_contract_id) if any(c.kind != "khach" for c in ds_) else {}
    return [xuat(db, c, user.role, dem_kh if c.kind == "khach" else dem_th) for c in ds_]


@router.post("/api/hop-dong")
def them(d: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _quyen_sua(user, (d.get("kind") or "khach"))
    c = Contract(created_by=user.full_name)
    _ap(db, c, d, True)
    db.add(c); db.commit()
    return xuat(db, c, user.role)


@router.put("/api/hop-dong/{cid}")
def sua(cid: str, d: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    c = db.get(Contract, cid) or _loi("KHONG_THAY", "Không có hợp đồng này.", 404)
    _quyen_sua(user, c.kind)
    so_cu = c.contract_no
    _ap(db, c, d, False)
    if c.contract_no != so_cu:
        # Phiếu CHƯA KHOÁ mang số mới; phiếu đã khoá giữ số đã in trên giấy.
        cot = Trip.contract_id if c.kind == "khach" else Trip.hire_contract_id
        for p in db.query(Trip).filter(cot == c.id, Trip.locked.is_(False)).all():
            if c.kind == "khach": p.contract_no = c.contract_no
            else: p.hire_contract_no = c.contract_no
    db.commit()
    return xuat(db, c, user.role)


@router.delete("/api/hop-dong/{cid}")
def xoa(cid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    c = db.get(Contract, cid) or _loi("KHONG_THAY", "Không có hợp đồng này.", 404)
    _quyen_sua(user, c.kind)
    cot = Trip.contract_id if c.kind == "khach" else Trip.hire_contract_id
    n = db.query(Trip.id).filter(cot == c.id).count()
    if n:
        _loi("DA_CO_PHIEU", "Đã có %d phiếu chạy theo hợp đồng %s — không xoá được. Tích 'Ngưng dùng' thay vì xoá." % (n, c.contract_no), 409)
    for f in db.query(ContractFile).filter(ContractFile.contract_id == c.id).all():
        _xoa_dia(f); db.delete(f)
    db.flush()                            # tệp ra khỏi DB trước, rồi mới xoá hợp đồng (khoá ngoại ondelete=CASCADE)
    db.delete(c); db.commit()
    return {"ok": True}


def _xoa_dia(f):
    try:
        os.remove(os.path.join(THU_MUC_HOP_DONG, f.contract_id, f.stored))
    except OSError:
        pass


@router.post("/api/hop-dong/{cid}/tep")
async def them_tep(cid: str, tep: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    c = db.get(Contract, cid) or _loi("KHONG_THAY", "Không có hợp đồng này.", 404)
    _quyen_sua(user, c.kind)
    kieu = (tep.content_type or mimetypes.guess_type(tep.filename or "")[0] or "").lower()
    if kieu not in TEP_KIEU:
        _loi("KIEU_TEP", "Chỉ nhận ảnh (JPG, PNG, WEBP, HEIC) hoặc PDF.")
    du = await tep.read()
    if len(du) > TEP_TOI_DA or loi_co_tep(kieu, len(du)):
        _loi("TEP_QUA_LON", loi_co_tep(kieu, len(du)) or "Tệp %.1f MB, tối đa 10 MB." % (len(du) / 1048576))
    if not du:
        _loi("TEP_RONG", "Tệp rỗng.")
    f = ContractFile(contract_id=c.id, filename=ten_tep(tep.filename, "hop_dong"),          # giữ chữ Lào (08/10)
                     content_type=kieu, size=len(du), by_user=user.full_name)
    f.id = ma_moi()
    f.stored = f.id + TEP_KIEU[kieu]
    os.makedirs(os.path.join(THU_MUC_HOP_DONG, c.id), exist_ok=True)
    with open(os.path.join(THU_MUC_HOP_DONG, c.id, f.stored), "wb") as o:
        o.write(du)
    db.add(f); db.commit()
    return _xuat_tep(f)


@router.get("/api/hop-dong-tep/{fid}")
def mo_tep(fid: str, request: Request, tk: str = "", db: Session = Depends(get_db)):
    """Thẻ <img>/<a> không gửi header nên nhận phiên qua ?tk=…. Giấy hợp đồng có giá → chỉ vai thấy tiền bán."""
    f = db.get(ContractFile, fid) or _loi("KHONG_THAY", "Không có tệp này.", 404)
    dau = request.headers.get("Authorization", "")
    token = tk or (dau[7:].strip() if dau.lower().startswith("bearer ") else "")
    u = nguoi_tu_token(db, token)      # token EPL cũ hoặc token GLS (08/10); không có / sai → 401
    if not thay_tien_ban(u.role):
        _loi("KHONG_CO_QUYEN", "Bản hợp đồng có giá cước — vai này không mở được.", 403)
    duong = os.path.join(THU_MUC_HOP_DONG, f.contract_id, f.stored)
    if not os.path.exists(duong):
        _loi("MAT_TEP", "Tệp không còn trên máy chủ.", 404)
    return FileResponse(duong, media_type=f.content_type, filename=f.filename, content_disposition_type="inline")


@router.delete("/api/hop-dong-tep/{fid}")
def xoa_tep(fid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    f = db.get(ContractFile, fid) or _loi("KHONG_THAY", "Không có tệp này.", 404)
    c = db.get(Contract, f.contract_id)
    _quyen_sua(user, c.kind if c else "khach")
    _xoa_dia(f); db.delete(f); db.commit()
    return {"ok": True}
