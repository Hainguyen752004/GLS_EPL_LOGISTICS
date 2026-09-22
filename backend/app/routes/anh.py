# -*- coding: utf-8 -*-
"""Ảnh xe và ảnh tài xế — ຮູບລົດ · ຮູບໂຊເຟີ.

Một bộ máy dùng chung cho hai loại ảnh, chỉ khác bảng và thư mục con. Cả hai nằm **đúng chỗ chứa tệp
của phiếu** (`EPL_LAO_TEP`): `xe/<vehicle_id>/…` và `tai-xe/<driver_id>/…` — một chỗ chứa thì một chỗ
sao lưu, giới hạn dung lượng và kiểu tệp đặt một lần ở `services/tep.py`.

Quy tắc chung: ảnh đầu tiên tự thành ảnh đại diện (khỏi bắt bấm thêm nút cho việc hiển nhiên); xoá ảnh
đại diện thì ảnh mới nhất lên thay; thẻ `<img>` không gửi header nên nhận phiên qua `?tk=…`, y như tệp
đính kèm phiếu.
"""
import mimetypes
import os
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Driver, DriverPhoto, Vehicle, VehiclePhoto, ma_moi
from services.bao_mat import can_vai, doc_phien, nguoi_hien_tai
from services.tep import ANH_KIEU, TEP_DIR, TEP_TOI_DA

router = APIRouter()
SUA = can_vai("yard", "acct")        # cùng người sửa danh mục xe · tài xế


class Loai:
    """Một loại ảnh: bảng nào, cột khoá ngoại nào, thư mục con nào, đường /api nào."""
    def __init__(self, ten, model, chu_model, cot, thu_muc, duong, ten_chu):
        self.ten, self.model, self.chu_model, self.cot = ten, model, chu_model, cot
        self.thu_muc = os.path.join(TEP_DIR, thu_muc)
        self.duong, self.ten_chu = duong, ten_chu

    def chu_id(self, a):
        return getattr(a, self.cot)

    def cua(self, db, chu_id):
        return (db.query(self.model).filter(getattr(self.model, self.cot) == chu_id)
                .order_by(self.model.chinh.desc(), self.model.ts.desc()).all())


XE = Loai("xe", VehiclePhoto, Vehicle, "vehicle_id", "xe", "anh-xe", "xe")
TAI_XE = Loai("tai-xe", DriverPhoto, Driver, "driver_id", "tai-xe", "anh-tai-xe", "tài xế")


def xuat_anh(loai, a):
    return {"id": a.id, loai.cot: loai.chu_id(a), "filename": a.filename, "content_type": a.content_type,
            "size": a.size, "chinh": bool(a.chinh), "note": a.note, "by_user": a.by_user,
            "ts": a.ts.isoformat() if a.ts else None, "url": "/api/%s/%s" % (loai.duong, a.id)}


def ds_anh(loai, db, chu_id):
    return [xuat_anh(loai, a) for a in loai.cua(db, chu_id)]


def anh_chinh_map(loai, db):
    """{chủ_id: url ảnh đại diện} lấy MỘT lượt cho cả danh sách — 500 xe thì đừng hỏi 500 lần."""
    return {loai.chu_id(a): "/api/%s/%s" % (loai.duong, a.id)
            for a in db.query(loai.model).filter(loai.model.chinh.is_(True)).all()}


def anh_chinh(loai, db, chu_id):
    a = (db.query(loai.model).filter(getattr(loai.model, loai.cot) == chu_id, loai.model.chinh.is_(True)).first())
    return ("/api/%s/%s" % (loai.duong, a.id)) if a is not None else None


async def _them(loai, chu_id, tep, note, chinh, db, user):
    chu = db.get(loai.chu_model, chu_id)
    if not chu:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có %s này." % loai.ten_chu})
    kieu = (tep.content_type or mimetypes.guess_type(tep.filename or "")[0] or "").lower()
    if kieu not in ANH_KIEU:
        raise HTTPException(422, {"ma": "KIEU_TEP", "loi": "Ảnh chỉ nhận JPG, PNG, WEBP hoặc HEIC."})
    du = await tep.read()
    if not du:
        raise HTTPException(422, {"ma": "TEP_RONG", "loi": "Tệp rỗng."})
    if len(du) > TEP_TOI_DA:
        raise HTTPException(422, {"ma": "TEP_QUA_LON", "loi": "Tệp %.1f MB, tối đa 8 MB." % (len(du) / 1048576)})
    a = loai.model(filename=re.sub(r"[^\w.\-() ]+", "_", tep.filename or "anh")[:120],
                   content_type=kieu, size=len(du), note=(note or None), by_user=user.full_name)
    setattr(a, loai.cot, chu.id)
    a.id = ma_moi()
    a.stored = a.id + ANH_KIEU[kieu]
    da_co = db.query(loai.model).filter(getattr(loai.model, loai.cot) == chu.id).count()
    a.chinh = bool(chinh) or da_co == 0
    if a.chinh:
        for cu in loai.cua(db, chu.id):
            cu.chinh = False
    os.makedirs(os.path.join(loai.thu_muc, chu.id), exist_ok=True)
    with open(os.path.join(loai.thu_muc, chu.id, a.stored), "wb") as f:
        f.write(du)
    db.add(a); db.commit()
    return ds_anh(loai, db, chu.id)


def _mo(loai, aid, request, tk, db):
    a = db.get(loai.model, aid)
    if not a:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có ảnh này."})
    dau = request.headers.get("Authorization", "")
    token = tk or (dau[7:].strip() if dau.lower().startswith("bearer ") else "")
    if not token or not doc_phien(token):
        raise HTTPException(401, {"ma": "CHUA_DANG_NHAP", "loi": "Vui lòng đăng nhập."})
    duong = os.path.join(loai.thu_muc, loai.chu_id(a), a.stored)
    if not os.path.exists(duong):
        raise HTTPException(404, {"ma": "MAT_TEP", "loi": "Ảnh không còn trên máy chủ."})
    return FileResponse(duong, media_type=a.content_type, filename=a.filename, content_disposition_type="inline")


def _dat_chinh(loai, aid, db):
    a = db.get(loai.model, aid)
    if not a:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có ảnh này."})
    for x in loai.cua(db, loai.chu_id(a)):
        x.chinh = (x.id == a.id)
    db.commit()
    return ds_anh(loai, db, loai.chu_id(a))


def _xoa(loai, aid, db):
    a = db.get(loai.model, aid)
    if not a:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có ảnh này."})
    chu_id, la_chinh = loai.chu_id(a), bool(a.chinh)
    try:
        os.remove(os.path.join(loai.thu_muc, chu_id, a.stored))
    except OSError:
        pass                      # tệp đã mất thì vẫn xoá dòng, không để bảng treo bản ghi chết
    db.delete(a); db.flush()
    if la_chinh:                  # xoá ảnh đại diện thì ảnh còn lại mới nhất lên thay
        con = (db.query(loai.model).filter(getattr(loai.model, loai.cot) == chu_id)
               .order_by(loai.model.ts.desc()).first())
        if con is not None:
            con.chinh = True
    db.commit()
    return ds_anh(loai, db, chu_id)


# ================================================================ ảnh xe
@router.get("/api/vehicles/{vid}/anh")
def ds_anh_xe(vid: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    if not db.get(Vehicle, vid):
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có xe này."})
    return ds_anh(XE, db, vid)


@router.post("/api/vehicles/{vid}/anh")
async def them_anh_xe(vid: str, tep: UploadFile = File(...), note: str = Form(""), chinh: str = Form(""),
                      db: Session = Depends(get_db), user=Depends(SUA)):
    return await _them(XE, vid, tep, note, chinh, db, user)


@router.get("/api/anh-xe/{aid}")
def mo_anh_xe(aid: str, request: Request, tk: str = "", db: Session = Depends(get_db)):
    return _mo(XE, aid, request, tk, db)


@router.put("/api/anh-xe/{aid}")
def dat_anh_xe_chinh(aid: str, db: Session = Depends(get_db), _=Depends(SUA)):
    return _dat_chinh(XE, aid, db)


@router.delete("/api/anh-xe/{aid}")
def xoa_anh_xe(aid: str, db: Session = Depends(get_db), _=Depends(SUA)):
    return _xoa(XE, aid, db)


# ================================================================ ảnh tài xế
@router.get("/api/drivers/{did}/anh")
def ds_anh_tai_xe(did: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    if not db.get(Driver, did):
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    return ds_anh(TAI_XE, db, did)


@router.post("/api/drivers/{did}/anh")
async def them_anh_tai_xe(did: str, tep: UploadFile = File(...), note: str = Form(""), chinh: str = Form(""),
                          db: Session = Depends(get_db), user=Depends(SUA)):
    return await _them(TAI_XE, did, tep, note, chinh, db, user)


@router.get("/api/anh-tai-xe/{aid}")
def mo_anh_tai_xe(aid: str, request: Request, tk: str = "", db: Session = Depends(get_db)):
    return _mo(TAI_XE, aid, request, tk, db)


@router.put("/api/anh-tai-xe/{aid}")
def dat_anh_tai_xe_chinh(aid: str, db: Session = Depends(get_db), _=Depends(SUA)):
    return _dat_chinh(TAI_XE, aid, db)


@router.delete("/api/anh-tai-xe/{aid}")
def xoa_anh_tai_xe(aid: str, db: Session = Depends(get_db), _=Depends(SUA)):
    return _xoa(TAI_XE, aid, db)
