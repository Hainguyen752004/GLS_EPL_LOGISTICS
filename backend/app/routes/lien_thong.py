# -*- coding: utf-8 -*-
"""LIÊN THÔNG hai trang — trang điều xe (đây) ↔ trang kế toán (EPL_KETOAN).

    GET  /api/lien-thong/kiem          trang kế toán gọi sang thử khoá: đúng khoá + đúng người thì trả người đó
    GET  /api/lien-thong/thu           Sếp bấm "Kiểm kết nối": gọi sang trang kế toán và báo thật kết quả
    POST /api/lien-thong/tao-khoa      Sếp tạo (lại) khoá cho trang kế toán gọi sang — chép khoá này vào Cài đặt bên đó
"""
import secrets
import time

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import FuelMove, FuelPlace, Part, SaleLine, Supplier, TripEvent, TripExpense, User, Voucher
from services import day_ke_toan as DK
from services import goi_ke_toan as KT
from services.bao_mat import can_vai, may_ke_toan_goi, nguoi_hien_tai, token_nhan_ke_toan

router = APIRouter()


@router.get("/api/lien-thong/kiem")
def kiem(u=Depends(may_ke_toan_goi)):
    return {"ok": True, "ben": "EPL_LAO_REAL", "nguoi": u.username, "vai": u.role}


@router.get("/api/lien-thong/thu")
def thu(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    goc, token = KT.cau_hinh(db)
    t0 = time.time()
    ra = {"api": goc, "co_token_nhan": bool(token_nhan_ke_toan(db))}
    try:
        ra.update(ok=True, ms=int((time.time() - t0) * 1000), ben_kia=KT.goi(db, "GET", "/api/lien-thong/kiem", nguoi=user))
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {"loi": str(e.detail)}
        ra.update(ok=False, co_token=bool(token), ma=d.get("ma"), loi=d.get("loi"))
    return ra


@router.post("/api/lien-thong/tao-khoa")
def tao_khoa(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    """Khoá mới thay khoá cũ ngay — trang kế toán phải dán khoá mới vào Cài đặt thì mới gọi sang được tiếp.
    Trả khoá đúng một lần trong câu trả lời này để Sếp chép; sau đó màn chỉ báo "đã có khoá"."""
    k = secrets.token_urlsafe(32)
    DK.dat_cau_hinh(db, "token_nhan_ke_toan", k, user)
    db.commit()
    return {"token_nhan_ke_toan": k}


# ================================================================ bản chép danh mục kho (28/09)
# Điểm đổ nhiên liệu: bản GỐC ở trang kế toán. Ở đây là bản chép chỉ đọc, cùng mã — phiếu, phiếu lĩnh, tài khoản
# thủ kho vẫn trỏ vào bảng fuel_places như cũ. Chỉ trang kế toán ghi vào đây, qua các đường máy dưới đây.
COT_DIEM = ("code", "name", "country", "owner_type", "supplier_id", "address", "note", "active")


@router.get("/api/lien-thong/diem-do/thong-tin")
def diem_do_thong_tin(db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    """Hai thứ màn Điểm đổ bên kế toán cần mà còn ở đây: danh sách nhà cung cấp (để gắn trạm bán dầu) và số phiếu
    lĩnh đang chờ cấp ở từng điểm."""
    ncc = [{"id": s.id, "name": s.name} for s in db.query(Supplier).order_by(Supplier.name).all()]
    cho = dict(db.query(Voucher.place_id, func.count(Voucher.id))
               .filter(Voucher.status == "cho", Voucher.place_id.isnot(None)).group_by(Voucher.place_id).all())
    return {"nha_cung_cap": ncc, "cho_cap": cho}


@router.put("/api/lien-thong/ban-sao/diem-do/{pid}")
def ghi_ban_sao_diem(pid: str, d: dict = Body(...), db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    if not str(d.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Điểm đổ phải có tên."})
    if d.get("owner_type") not in ("epl", "ngoai"):
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "Loại điểm đổ không hợp lệ."})
    if d.get("supplier_id") and not db.get(Supplier, d["supplier_id"]):
        raise HTTPException(422, {"ma": "KHONG_THAY_NCC", "loi": "Không có nhà cung cấp này ở trang điều xe."})
    x = db.get(FuelPlace, pid)
    if not x:
        x = FuelPlace(id=pid); db.add(x)
    for c in COT_DIEM:
        if c in d:
            setattr(x, c, d[c] if d[c] != "" else None)
    x.active = bool(x.active)
    db.commit()
    return {"ok": True, "id": pid}


@router.delete("/api/lien-thong/ban-sao/diem-do/{pid}")
def xoa_ban_sao_diem(pid: str, db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    x = db.get(FuelPlace, pid)
    if not x:
        return {"ok": True, "id": pid}          # bên này chưa có thì coi như đã xoá
    dung = [ten for ten, bang, cot in (("phiếu xuất xe", TripExpense, TripExpense.place_id),
                                       ("khai đổ dầu", TripEvent, TripEvent.place_id),
                                       ("phiếu lĩnh", Voucher, Voucher.place_id),
                                       ("sổ kho dầu", FuelMove, FuelMove.place_id),
                                       ("phiếu bán hàng", SaleLine, SaleLine.place_id),
                                       ("tài khoản thủ kho", User, User.place_id))
            if db.query(bang).filter(cot == pid).first()]
    if dung:
        raise HTTPException(409, {"ma": "DANG_DUNG",
                                  "loi": "Điểm đổ đã có trên %s — chỉ được ngưng dùng, không xoá." % ", ".join(dung)})
    db.delete(x); db.commit()
    return {"ok": True, "id": pid}


# Phụ tùng: bản GỐC (tồn, giá, sổ) ở trang kế toán. Ở đây là bản chép DANH MỤC — tên, đơn vị, tồn tối thiểu, đang dùng —
# để dòng chi mục V, dòng lệnh sửa, dòng bán vẫn trỏ đúng. Không nhận tồn, không nhận giá (số đó chỉ bên kia giữ).
@router.put("/api/lien-thong/ban-sao/phu-tung/{pid}")
def ghi_ban_sao_phu_tung(pid: str, d: dict = Body(...), db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    if not str(d.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Phụ tùng phải có tên."})
    x = db.get(Part, pid)
    if not x:
        x = Part(id=pid, qty=0, unit_price=0); db.add(x)
    x.name = str(d["name"]).strip()
    x.unit = d.get("unit") or "u_pc"
    x.min_qty = d.get("min_qty") or 0
    x.active = bool(d.get("active", True))
    db.commit()
    return {"ok": True, "id": pid}



# ================================================================ màn Cấp phát ở trang kế toán (đợt 4, 28/09)
# Phiếu lĩnh / tạm ứng vẫn ở đây (giấy của chuyến). Màn Cấp phát bên kế toán gọi sang, dưới tên người đang bấm — quyền
# và mọi quy tắc là của chính routes/phieu_linh.py, không viết lại. Cấp dầu thì phieu_linh gọi ngược sang kho dầu bên đó.
@router.get("/api/lien-thong/cap-phat")
def lt_cap_phat(request: Request, response: Response, trang_thai: str = "cho", db: Session = Depends(get_db),
                u=Depends(may_ke_toan_goi)):
    from routes import phieu_linh as PL
    return PL.ds_cho_cap(request, response, trang_thai=trang_thai, loai="", co=500, db=db, user=u)


@router.get("/api/lien-thong/cap-phat/tra-cuu/{token}")
def lt_tra_cuu(token: str, request: Request, db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    from routes import phieu_linh as PL
    return PL.tra_cuu(token, request, db=db, user=u)


@router.post("/api/lien-thong/cap-phat/{vid}/cap")
def lt_cap(vid: str, d: dict = Body(default={}), db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    from routes import phieu_linh as PL
    return PL.cap_phat(vid, d, db=db, user=u)


@router.get("/api/lien-thong/ty-gia")
def lt_ty_gia(db: Session = Depends(get_db), u=Depends(may_ke_toan_goi)):
    """Tỷ giá quy Kíp hiện hành (màn Tỷ giá ở đây) — gợi ý khi nhập kho dầu bằng ngoại tệ ở trang kế toán."""
    from models import ExchangeRate
    return {r.code: r.rate_to_lak for r in db.query(ExchangeRate).all()}


@router.get("/api/lien-thong/dia-chi")
def dia_chi(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Địa chỉ trang kế toán để giao diện bên này mở sang (nút Cấp phát, Kho nhiên liệu…)."""
    from services import kho_ke_toan as KK
    return {"ke_toan_web": KK.web_ke_toan(db)}
