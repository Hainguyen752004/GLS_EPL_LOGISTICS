# -*- coding: utf-8 -*-
"""Đăng nhập, xem mình là ai, quản lý tài khoản (admin)."""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import VAI, User
from services.bao_mat import bam_mat_khau, can_vai, khop_mat_khau, ky_phien, nguoi_hien_tai

router = APIRouter()


def xuat_user(u):
    return {"id": u.id, "username": u.username, "full_name": u.full_name,
            "role": u.role, "avatar": u.avatar or u.full_name[:2].upper(), "active": u.active}


@router.post("/api/dang-nhap")
def dang_nhap(data: dict = Body(...), db: Session = Depends(get_db)):
    ten = str(data.get("username") or "").strip()
    mk = str(data.get("password") or "")
    u = db.query(User).filter(User.username == ten).first()
    if not u or not u.active or not khop_mat_khau(mk, u.password_hash):
        raise HTTPException(401, {"ma": "SAI_TAI_KHOAN", "loi": "Sai tên đăng nhập hoặc mật khẩu."})
    return {"token": ky_phien(u.username), "user": xuat_user(u)}


@router.get("/api/toi")
def toi(user=Depends(nguoi_hien_tai)):
    return xuat_user(user)


@router.get("/api/tai-khoan-mau")
def tai_khoan_mau(db: Session = Depends(get_db)):
    """Danh sách tài khoản để bấm nhanh trên màn đăng nhập — bản demo. Không trả mật khẩu."""
    return [xuat_user(u) for u in db.query(User).filter(User.active.is_(True)).order_by(User.role).all()]


@router.get("/api/users")
def ds_user(db: Session = Depends(get_db), _=Depends(can_vai("admin"))):
    return [xuat_user(u) for u in db.query(User).order_by(User.username).all()]


@router.post("/api/users")
def them_user(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(can_vai("admin"))):
    ten = str(data.get("username") or "").strip()
    if not ten or not data.get("password") or not data.get("full_name"):
        raise HTTPException(422, {"ma": "THIEU", "loi": "Cần tên đăng nhập, mật khẩu và họ tên."})
    if data.get("role") not in VAI:
        raise HTTPException(422, {"ma": "VAI_SAI", "loi": "Vai phải là một trong %s." % ", ".join(VAI)})
    if db.query(User).filter(User.username == ten).first():
        raise HTTPException(409, {"ma": "TRUNG", "loi": "Tên đăng nhập đã có."})
    u = User(username=ten, password_hash=bam_mat_khau(str(data["password"])),
             full_name=str(data["full_name"]).strip(), role=data["role"],
             avatar=str(data.get("avatar") or "")[:2].upper())
    db.add(u); db.commit(); db.refresh(u)
    return xuat_user(u)


@router.put("/api/users/{uid}")
def sua_user(uid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(can_vai("admin"))):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài khoản này."})
    if "full_name" in data: u.full_name = str(data["full_name"]).strip()
    if "role" in data:
        if data["role"] not in VAI:
            raise HTTPException(422, {"ma": "VAI_SAI", "loi": "Vai không hợp lệ."})
        u.role = data["role"]
    if "avatar" in data: u.avatar = str(data["avatar"] or "")[:2].upper()
    if "active" in data: u.active = bool(data["active"])
    if data.get("password"): u.password_hash = bam_mat_khau(str(data["password"]))
    db.commit(); db.refresh(u)
    return xuat_user(u)
