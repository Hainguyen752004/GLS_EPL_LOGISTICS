# -*- coding: utf-8 -*-
"""ĐIỂM ĐỔ ↔ KHO TRÊN WEB (08/10 — anh Khampla: "có thêm chức năng tạo kho mới"; chủ dự án duyệt).

Ô "Nơi đổ" trên phiếu đọc bảng fuel_places. Trước 08/10 người ghi duy nhất là trang kế toán tạm 8031 (routes/lien_thong — bản chép), mà
8031 đã bỏ từ 05/10 → không còn chỗ nào thêm được điểm đổ. Nay:
  · KHO DẦU EPL (owner_type 'epl'): tạo ở Web — Quản lý kho → Khai báo kho. Ở trang điều xe chọn kho đó từ danh mục kho một lần (gan) →
    điểm đổ mang mã kho (code = WarehouseCode — cũng là mã kho khi xuất dầu, services/kho_qlsx); tên, địa chỉ, đang dùng / ngưng chép
    từ Web (dong_bo — màn Điểm đổ, luồng nền dong_bo_nen). Ở đây chỉ sửa nước (LA / VN) và ghi chú.
  · TRẠM DẦU NGOÀI (owner_type 'ngoai'): không phải kho — thêm / sửa / ngưng ngay ở màn Điểm đổ (routes/phieu_linh).

Danh mục kho đọc bằng API bên Web (POST supply-chain/warehouse/master/list) với tài khoản tích hợp của kho_qlsx — kho phụ tùng, kho
giấy… cũng nằm trong danh mục đó, nên kho nào là kho dầu do người chọn, không đoán theo loại kho.
"""
import datetime as dt

from fastapi import HTTPException

from models import FuelPlace
from services import kho_qlsx as KQ

DUONG_DS_KHO = "/api/v1/supply-chain/warehouse/master/list"


def kho_web():
    """Mọi kho bên Web → [{wh_id, code, name, address, active, loai, don_vi}]. Lỗi mạng / từ chối → HTTPException (kho_qlsx)."""
    ma, than = KQ._goi("POST", DUONG_DS_KHO, {})
    kq = KQ._ket(ma, than, "đọc danh mục kho")
    ds = (kq or {}).get("Data") if isinstance(kq, dict) else kq
    ra = []
    for w in ds or []:
        if not w.get("WarehouseCode"):
            continue
        ra.append({"wh_id": w.get("WhAutoId"), "code": str(w["WarehouseCode"]).strip(), "name": (w.get("WarehouseName") or "").strip(),
                   "address": (w.get("Address") or "").strip() or None, "active": bool(w.get("IsActive")),
                   "loai": w.get("WarehouseTypeName"), "don_vi": w.get("OrganizationName")})
    return ra


def _chep(x, w):
    """Chép thông tin kho Web lên điểm đổ → True nếu có gì đổi."""
    moi = {"code": w["code"], "name": w["name"] or x.name or w["code"], "address": w["address"] or x.address, "active": w["active"],
           "wh_id": w["wh_id"], "owner_type": "epl"}
    doi = any(getattr(x, k) != v for k, v in moi.items())
    for k, v in moi.items():
        setattr(x, k, v)
    x.wh_synced_at = dt.datetime.utcnow()
    return doi


def gan(db, wh_id, country=None):
    """Lấy một kho bên Web làm điểm đổ kho dầu EPL. Điểm đổ cùng mã đã có (bản chép cũ) → gắn vào đó, không lập trùng."""
    w = next((k for k in kho_web() if str(k["wh_id"]) == str(wh_id)), None)
    if w is None:
        raise HTTPException(404, {"ma": "KHONG_THAY_KHO", "loi": "Không thấy kho này trong danh mục kho trên Web."})
    x = db.query(FuelPlace).filter(FuelPlace.wh_id == w["wh_id"]).first() \
        or db.query(FuelPlace).filter(FuelPlace.code == w["code"]).first()
    if x is not None and x.owner_type == "ngoai":
        raise HTTPException(409, {"ma": "TRUNG_MA", "loi": "Mã %s đang là một trạm dầu ngoài — đổi mã trạm đó trước." % w["code"]})
    if x is None:
        x = FuelPlace(country=(country or "LA").upper(), owner_type="epl")
        db.add(x)
    elif country:
        x.country = country.upper()
    _chep(x, w)
    return x


def dong_bo(db, ds=None):
    """Chép lại tên / địa chỉ / trạng thái mọi điểm đổ kho dầu EPL từ kho Web (khớp wh_id, rồi mã). → {"cap_nhat", "mat": [mã]}."""
    ds = ds if ds is not None else kho_web()
    theo_id = {str(w["wh_id"]): w for w in ds}
    theo_ma = {w["code"]: w for w in ds}
    cap_nhat, mat = 0, []
    for x in db.query(FuelPlace).filter(FuelPlace.owner_type == "epl").all():
        w = theo_id.get(str(x.wh_id)) if x.wh_id else None
        w = w or theo_ma.get((x.code or "").strip())
        if w is None:
            mat.append(x.code or x.name)
            continue
        if _chep(x, w):
            cap_nhat += 1
    return {"cap_nhat": cap_nhat, "mat": mat}


def can_dong_bo(db, phut=60):
    """Luồng nền: có điểm đổ kho dầu chưa chép lần nào hoặc chép quá `phut` phút."""
    moc = dt.datetime.utcnow() - dt.timedelta(minutes=phut)
    return db.query(FuelPlace.id).filter(FuelPlace.owner_type == "epl") \
        .filter((FuelPlace.wh_synced_at.is_(None)) | (FuelPlace.wh_synced_at < moc)).first() is not None
