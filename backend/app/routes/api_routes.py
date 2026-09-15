"""Toàn bộ điểm cuối HTTP của bản demo.

Tất cả handler chạm cơ sở dữ liệu đều là `def` THƯỜNG, không phải `async def`.
SQLAlchemy đồng bộ mà đặt trong `async def` thì nó chặn vòng lặp sự kiện, và cả
máy chủ đứng im dưới tải — EPL_System đã có hẳn một bài kiểm để chặn chuyện này.
"""

from typing import Optional

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from config import NGUOI_DUNG_DEMO
from database import get_db
from models import Customer, Driver, Vehicle
from services import (
    don_hang_service,
    giao_hang_service,
    khach_hang_service,
    packing_service,
    theo_doi_service,
    tuyen_service,
)
from services.loi import LoiNghiepVu, nem_http

router = APIRouter()


def _nguoi(request: Request):
    return request.headers.get("X-PL-Actor") or NGUOI_DUNG_DEMO


def _tra(du_lieu, thong_diep="OK"):
    return {"message": thong_diep, "data": jsonable_encoder(du_lieu)}


def _lam(db, ham):
    """Chạy một thao tác ghi: thành công thì commit, lỗi thì rollback sạch."""
    try:
        gia_tri = ham()
        db.commit()
        return gia_tri
    except LoiNghiepVu as loi:
        db.rollback()
        nem_http(loi)
    except Exception:
        db.rollback()
        raise


# --------------------------------------------------------------------------
# Danh mục nền
# --------------------------------------------------------------------------
@router.get("/api/customers")
def ds_khach(q: Optional[str] = None, kind: Optional[str] = None, db: Session = Depends(get_db)):
    return _tra(khach_hang_service.danh_sach(db, q=q, kind=kind))


@router.get("/api/customers/{id_}")
def xem_khach(id_: str, db: Session = Depends(get_db)):
    try:
        return _tra(khach_hang_service.ra_dict(khach_hang_service.nap(db, id_)))
    except LoiNghiepVu as loi:
        nem_http(loi)


@router.post("/api/customers")
def tao_khach(payload: dict = Body(...), db: Session = Depends(get_db)):
    c = _lam(db, lambda: khach_hang_service.tao(db, payload))
    return _tra(khach_hang_service.ra_dict(c), "Đã tạo khách hàng")


@router.put("/api/customers/{id_}")
def sua_khach(id_: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    c = _lam(db, lambda: khach_hang_service.sua(db, id_, payload))
    return _tra(khach_hang_service.ra_dict(c), "Đã cập nhật khách hàng")


@router.delete("/api/customers/{id_}")
def xoa_khach(id_: str, db: Session = Depends(get_db)):
    _lam(db, lambda: khach_hang_service.xoa(db, id_))
    return _tra({"deleted": id_}, "Đã xoá khách hàng")


@router.get("/api/routes")
def ds_tuyen(q: Optional[str] = None, active_only: bool = False, db: Session = Depends(get_db)):
    return _tra(tuyen_service.danh_sach(db, q=q, chi_dang_dung=active_only))


@router.post("/api/routes")
def tao_tuyen(payload: dict = Body(...), db: Session = Depends(get_db)):
    r = _lam(db, lambda: tuyen_service.tao(db, payload))
    return _tra(tuyen_service.ra_dict(r, tuyen_service._diem(db, r)), "Đã tạo tuyến đường")


@router.put("/api/routes/{id_}")
def sua_tuyen(id_: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    r = _lam(db, lambda: tuyen_service.sua(db, id_, payload))
    return _tra(tuyen_service.ra_dict(r, tuyen_service._diem(db, r)), "Đã cập nhật tuyến đường")


@router.delete("/api/routes/{id_}")
def xoa_tuyen(id_: str, db: Session = Depends(get_db)):
    _lam(db, lambda: tuyen_service.xoa(db, id_))
    return _tra({"deleted": id_}, "Đã xoá tuyến đường")


@router.get("/api/vehicles")
def ds_xe(db: Session = Depends(get_db)):
    hang = db.query(Vehicle).order_by(Vehicle.plate_head).all()
    return _tra(
        [
            {
                "id": v.id,
                "plate_head": v.plate_head,
                "plate_trailer": v.plate_trailer,
                "internal_no": v.internal_no,
                "vehicle_type": v.vehicle_type,
                "payload_kg": v.payload_kg,
                "cube_m3": v.cube_m3,
                "status": v.status,
            }
            for v in hang
        ]
    )


@router.get("/api/drivers")
def ds_tai_xe(db: Session = Depends(get_db)):
    hang = db.query(Driver).order_by(Driver.full_name).all()
    return _tra(
        [
            {
                "id": d.id,
                "code": d.code,
                "full_name": d.full_name,
                "phone": d.phone,
                "licence_class": d.licence_class,
                "status": d.status,
            }
            for d in hang
        ]
    )


# --------------------------------------------------------------------------
# Đơn hàng khách
# --------------------------------------------------------------------------
@router.get("/api/sales-orders")
def ds_don(
    q: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return _tra(don_hang_service.danh_sach(db, q=q, trang_thai=status, trang=page, moi_trang=page_size))


@router.get("/api/sales-orders/{so_id}")
def xem_don(so_id: str, db: Session = Depends(get_db)):
    try:
        return _tra(don_hang_service.ra_dict(db, don_hang_service.nap(db, so_id)))
    except LoiNghiepVu as loi:
        nem_http(loi)


@router.post("/api/sales-orders")
def tao_don(request: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    don = _lam(db, lambda: don_hang_service.tao(db, payload, nguoi))
    return _tra(don_hang_service.ra_dict(db, don_hang_service.nap(db, don.id)), "Đã tạo đơn hàng")


@router.post("/api/sales-orders/{so_id}/cancel")
def huy_don(so_id: str, request: Request, payload: dict = Body(default={}), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    _lam(db, lambda: don_hang_service.huy(db, so_id, payload.get("reason"), nguoi))
    return _tra(don_hang_service.ra_dict(db, don_hang_service.nap(db, so_id)), "Đã huỷ đơn hàng")


# --------------------------------------------------------------------------
# Packing List
# --------------------------------------------------------------------------
@router.get("/api/packing-lists")
def ds_pl(
    q: Optional[str] = None,
    status: Optional[str] = None,
    so_id: Optional[str] = None,
    delivery_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return _tra(
        packing_service.danh_sach(
            db, q=q, trang_thai=status, so_id=so_id, delivery_id=delivery_id, trang=page, moi_trang=page_size
        )
    )


@router.get("/api/packing-lists/stats")
def thong_ke_pl(db: Session = Depends(get_db)):
    return _tra(packing_service.thong_ke(db))


@router.get("/api/packing-lists/{pl_id}")
def xem_pl(pl_id: str, db: Session = Depends(get_db)):
    try:
        return _tra(packing_service.ra_dict(packing_service.nap(db, pl_id)))
    except LoiNghiepVu as loi:
        nem_http(loi)


@router.post("/api/sales-orders/{so_id}/packing-lists")
def tao_pl(so_id: str, request: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    pl = _lam(db, lambda: packing_service.tao(db, so_id, payload, nguoi))
    return _tra(packing_service.ra_dict(pl), "Đã tạo Packing List")


@router.post("/api/sales-orders/{so_id}/packing-lists/auto")
def tao_pl_tu_dong(so_id: str, request: Request, payload: dict = Body(default={}), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    so_luong = int(payload.get("count") or 1)
    ds = _lam(db, lambda: packing_service.tao_tu_dong(db, so_id, so_luong, nguoi))
    return _tra([packing_service.ra_dict(pl) for pl in ds], "Đã chia Packing List từ phần còn lại")


@router.put("/api/packing-lists/{pl_id}")
def sua_pl(pl_id: str, request: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    pl = _lam(db, lambda: packing_service.sua(db, pl_id, payload, nguoi))
    return _tra(packing_service.ra_dict(pl), "Đã cập nhật Packing List")


@router.post("/api/packing-lists/{pl_id}/status")
def doi_trang_thai_pl(pl_id: str, request: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    pl = _lam(
        db,
        lambda: packing_service.doi_trang_thai(db, pl_id, payload.get("status"), nguoi, payload.get("note")),
    )
    return _tra(packing_service.ra_dict(pl), "Đã cập nhật trạng thái")


@router.post("/api/packing-lists/{pl_id}/print")
def in_tem_pl(pl_id: str, request: Request, payload: dict = Body(default={}), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    pl = _lam(db, lambda: packing_service.in_tem(db, pl_id, nguoi, bool(payload.get("reprint"))))
    return _tra(packing_service.ra_dict(pl), "Đã ghi nhận in tem")


@router.post("/api/packing-lists/{pl_id}/cancel")
def huy_pl(pl_id: str, request: Request, payload: dict = Body(default={}), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    pl = _lam(db, lambda: packing_service.huy(db, pl_id, payload.get("reason"), nguoi))
    return _tra(packing_service.ra_dict(pl), "Đã huỷ Packing List")


@router.get("/api/packing-lists/{pl_id}/qr.svg")
def qr_cua_phieu(pl_id: str, db: Session = Depends(get_db)):
    """QR in ở góc phiếu Packing List (mẫu 2). Nội dung: PL:<mã phiếu>."""
    import qrcode
    import qrcode.image.svg
    from fastapi.responses import Response

    try:
        packing_service.nap(db, pl_id)
    except LoiNghiepVu as loi:
        nem_http(loi)
    anh = qrcode.make("PL:" + pl_id, image_factory=qrcode.image.svg.SvgImage, box_size=10, border=2)
    dem = __import__("io").BytesIO()
    anh.save(dem)
    return Response(content=dem.getvalue(), media_type="image/svg+xml")


@router.get("/api/labels/{token}/qr.svg")
def qr_cua_tem(token: str, db: Session = Depends(get_db)):
    """Sinh mã QR cho một tem, trả về SVG.

    Vẽ ở máy chủ chứ không nhúng thư viện QR vào trang: bản demo phải in được
    ngay cả khi máy ở kho không ra được Internet.
    """
    import qrcode
    import qrcode.image.svg
    from fastapi.responses import Response

    from models import PackingLabel

    lb = db.query(PackingLabel).filter(PackingLabel.qr_token == token).first()
    if not lb:
        nem_http(LoiNghiepVu("LABEL_NOT_FOUND", "Không nhận ra tem QR này", 404))
    anh = qrcode.make(token, image_factory=qrcode.image.svg.SvgImage, box_size=10, border=2)
    dem = __import__("io").BytesIO()
    anh.save(dem)
    return Response(content=dem.getvalue(), media_type="image/svg+xml")


@router.post("/api/labels/scan")
def quet_tem(request: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    ket_qua = _lam(db, lambda: packing_service.quet_tem(db, payload.get("token"), nguoi, payload.get("step")))
    return _tra(ket_qua, "Đã ghi nhận quét tem")


# --------------------------------------------------------------------------
# Giao hàng
# --------------------------------------------------------------------------
@router.get("/api/deliveries")
def ds_giao(
    q: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return _tra(giao_hang_service.danh_sach(db, q=q, trang_thai=status, trang=page, moi_trang=page_size))


@router.get("/api/deliveries/stats")
def thong_ke_giao(db: Session = Depends(get_db)):
    return _tra(giao_hang_service.thong_ke(db))


@router.get("/api/deliveries/{gh_id}")
def xem_giao(gh_id: str, db: Session = Depends(get_db)):
    try:
        return _tra(giao_hang_service.ra_dict(giao_hang_service.nap(db, gh_id)))
    except LoiNghiepVu as loi:
        nem_http(loi)


@router.post("/api/deliveries")
def tao_giao(request: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    gh = _lam(db, lambda: giao_hang_service.tao(db, payload, nguoi))
    return _tra(giao_hang_service.ra_dict(gh), "Đã tạo chuyến giao hàng")


@router.post("/api/deliveries/{gh_id}/packing-lists")
def them_pl_vao_chuyen(gh_id: str, request: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    gh = _lam(
        db, lambda: giao_hang_service.them_packing_list(db, gh_id, payload.get("packing_list_ids") or [], nguoi)
    )
    return _tra(giao_hang_service.ra_dict(gh), "Đã xếp thêm Packing List")


@router.delete("/api/deliveries/{gh_id}/packing-lists/{pl_id}")
def bo_pl_khoi_chuyen(gh_id: str, pl_id: str, request: Request, db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    gh = _lam(db, lambda: giao_hang_service.bo_packing_list(db, gh_id, pl_id, nguoi))
    return _tra(giao_hang_service.ra_dict(gh), "Đã bỏ Packing List khỏi chuyến")


@router.post("/api/deliveries/{gh_id}/status")
def doi_trang_thai_giao(gh_id: str, request: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    gh = _lam(
        db,
        lambda: giao_hang_service.doi_trang_thai(db, gh_id, payload.get("status"), nguoi, payload.get("note")),
    )
    return _tra(giao_hang_service.ra_dict(gh), "Đã cập nhật trạng thái chuyến")


@router.post("/api/deliveries/{gh_id}/cancel")
def huy_giao(gh_id: str, request: Request, payload: dict = Body(default={}), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    gh = _lam(db, lambda: giao_hang_service.huy(db, gh_id, payload.get("reason"), nguoi))
    return _tra(giao_hang_service.ra_dict(gh), "Đã huỷ chuyến")


@router.post("/api/packing-lists/{pl_id}/pod")
def ghi_pod(pl_id: str, request: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    nguoi = _nguoi(request)
    pl = _lam(db, lambda: giao_hang_service.ghi_pod(db, pl_id, payload, nguoi))
    return _tra(packing_service.ra_dict(pl), "Đã ghi nhận giao hàng")


# --------------------------------------------------------------------------
# Theo dõi xe
# --------------------------------------------------------------------------
@router.get("/api/tracking")
def theo_doi_tong_quan(db: Session = Depends(get_db)):
    return _tra(theo_doi_service.tong_quan(db))


@router.get("/api/tracking/{gh_id}")
def theo_doi_chuyen(gh_id: str, db: Session = Depends(get_db)):
    try:
        gh = giao_hang_service.nap(db, gh_id)
        ket_qua = theo_doi_service.tinh_trang_chuyen(db, gh)
        ket_qua["trail"] = theo_doi_service.vet_duong(db, gh_id)
        return _tra(ket_qua)
    except LoiNghiepVu as loi:
        nem_http(loi)


@router.post("/api/tracking/{gh_id}/position")
def ghi_vi_tri(gh_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Điểm cuối cho thiết bị GPS hoặc app tài xế gửi vị trí lên."""
    kq = _lam(db, lambda: theo_doi_service.ghi_vi_tri(db, gh_id, payload, payload.get("source") or "gps"))
    return _tra(kq, "Đã ghi vị trí")


@router.post("/api/tracking/{gh_id}/simulate")
def mo_phong(gh_id: str, request: Request, payload: dict = Body(default={}), db: Session = Depends(get_db)):
    """Chỉ dùng cho demo: nhích xe thêm một đoạn dọc tuyến."""
    nguoi = _nguoi(request)
    buoc = float(payload.get("step") or 0.15)
    kq = _lam(db, lambda: theo_doi_service.mo_phong_chay_tiep(db, gh_id, buoc, nguoi))
    return _tra(kq, "Đã cập nhật vị trí mô phỏng")
