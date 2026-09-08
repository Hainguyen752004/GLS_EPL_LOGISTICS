"""Diem cuoi API cua man Bao gia cuoc — luong moi QT -> DO.

DAT O TEP RIENG, khong them vao `workflow_routes.py`. Ba ly do:

  · `workflow_routes.py` da hon mot nghin dong va dang co nguoi khac sua cung
    luc; them mot nhom diem cuoi vao do la tao ra xung dot khong can thiet.
  · Router nay mang dependency xac thuc o TANG ROUTER, nen diem cuoi them vao
    sau duoc bao ve mac dinh chu khong phu thuoc viec nguoi viet co nho goi ham
    kiem hay khong — chinh cach 95 tren 105 diem cuoi ghi du lieu da lot ra
    ngoai o ban truoc.
  · Cac diem cuoi cu (`GET/POST/PUT/DELETE /api/quotations`) van chay nguyen;
    tep nay chi THEM nhung duong luong moi can.

THU TU KHAI BAO CO Y NGHIA. `/api/quotations/summary` va `/price-preview` phai
khai TRUOC `/api/quotations/{qid}` — neu khong thi FastAPI khop "summary" vao
`{qid}` va tra ve "khong tim thay bao gia summary".
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from routes.finance_master_routes import require_authenticated_principal
from services import bao_gia_service as bao_gia
from services.errors import DomainError, conflict, raise_http


router = APIRouter(dependencies=[Depends(require_authenticated_principal)])


def _actor(request: Request) -> str:
    """Nguoi dang thao tac, lay tu phien da xac thuc.

    KHONG lay tu payload: mot ma nguoi dung do may khach tu khai thi ai cung
    ghi duoc nhat ky duoi ten nguoi khac, va nhat ky do la thu duy nhat tra loi
    duoc cau "ai duyet bao gia lo nay".
    """
    principal = getattr(request.state, "principal", None)
    if isinstance(principal, str) and principal.strip():
        return principal.strip()
    if isinstance(principal, dict):
        for ten in ("id", "sub", "username"):
            if str(principal.get(ten) or "").strip():
                return str(principal[ten]).strip()
    raise_http(DomainError("AUTHENTICATION_REQUIRED",
                           "Không xác định được người dùng đã xác thực.", 401))


def _lenh(db: Session, viec, thong_bao: str):
    """Khuon cho moi duong GHI: chay, commit, va doi loi thanh cau doc duoc.

    Mot khuon dung chung thay vi lap `try/except/commit` o muoi diem cuoi: lap
    thi som muon co mot cho quen `db.rollback()`, va sau do moi yeu cau di qua
    phien do deu vo voi mot loi khong lien quan.
    """
    try:
        du_lieu = viec()
        db.commit()
        return {"message": thong_bao, "data": du_lieu}
    except DomainError as loi:
        db.rollback()
        raise_http(loi)
    except IntegrityError:
        db.rollback()
        raise_http(conflict("QUOTATION_CONFLICT",
                            "Báo giá vừa được người khác sửa. Tải lại rồi thử lại."))


# ===========================================================================
# DOC
# ===========================================================================

@router.get("/api/quotations/summary")
async def dai_so_lieu(db: Session = Depends(get_db)):
    """Sau con so cua dai KPI — chinh la sau bo loc cua man danh sach."""
    try:
        return {"message": "Đã tải số liệu báo giá.", "data": bao_gia.dai_so_lieu(db)}
    except DomainError as loi:
        raise_http(loi)


@router.post("/api/quotations/price-preview")
async def xem_truoc_gia(data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Bang cau phan gia thanh, do vua tai cua tung loai xe, va goi y gia.

    DAY LA CHO TINH GIA — giao dien khong tu tinh. Spec ghi ro dieu do va no
    dung: mot cong thuc nam o hai cho se troi khoi nhau, roi man Bao gia va man
    Du lieu goc noi hai con so khac nhau cho cung mot chuyen.
    """
    try:
        return {"message": "Đã tính giá thành theo công thức loại xe.",
                "data": bao_gia.xem_truoc_gia(db, data)}
    except DomainError as loi:
        raise_http(loi)


@router.get("/api/quotations/board")
async def bang_bao_gia(
    status: str = Query("all"),
    customer_id: Optional[str] = Query(None),
    route_id: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Danh sach bao gia kem BIEN va SO NGAY CON LAI da tinh san.

    Tinh o may chu chu khong de giao dien tu tinh: bien la `(cuoc - gia thanh) /
    cuoc`, va neu giao dien tu tinh thi bang danh sach va phieu chi tiet co the
    hien hai con so khac nhau cho cung mot bao gia.
    """
    try:
        ds = bao_gia.danh_sach(db, {
            "status": status, "customer_id": customer_id,
            "route_id": route_id, "owner": owner, "q": q,
        })
        return {"message": "Đã tải danh sách báo giá.",
                "data": {"items": ds, "total": len(ds),
                         "kpis": bao_gia.dai_so_lieu(db)}}
    except DomainError as loi:
        raise_http(loi)


@router.get("/api/quotations/{qid}/detail")
async def chi_tiet(qid: str, db: Session = Depends(get_db)):
    """Mot bao gia kem moi thu man chi tiet can, trong MOT loi goi.

    Mot loi goi chu khong sau: dong hang hoa, chung tu, phien ban gia va danh
    sach DO da tach deu phai NHAT QUAN voi nhau tren mot man hinh. Goi rieng
    thi sau lan doc o sau thoi diem, va man hinh co the hien "3 DO du kien" o
    tren trong khi bang duoi da co 4 DO.
    """
    try:
        return {"message": "Đã tải phiếu báo giá.",
                "data": bao_gia.mot_bao_gia(db, qid)}
    except DomainError as loi:
        raise_http(loi)


@router.get("/api/customers/{cid}/price-history")
async def gia_da_bao(
    cid: str,
    route_id: Optional[str] = Query(None),
    limit: int = Query(3, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Vai bao gia gan nhat da bao cho khach nay.

    Nguoi ban can biet lan truoc bao bao nhieu TRUOC KHI go mot con so moi — do
    la thu chan viec bao 3,9 trieu hom nay cho mot khach thang truoc da bao 4,1
    trieu cung tuyen.
    """
    try:
        return {"message": "Đã tải giá đã báo cho khách này.",
                "data": bao_gia.gia_da_bao_cho_khach(db, cid, route_id, limit)}
    except DomainError as loi:
        raise_http(loi)


# ===========================================================================
# GHI
# ===========================================================================

@router.put("/api/quotations/{qid}/items")
async def ghi_dong_hang_hoa(
    request: Request, qid: str,
    data: Dict[str, Any] = Body(...), db: Session = Depends(get_db),
):
    """Ghi lai TOAN BO bang hang hoa cua mot bao gia.

    Thay ca bang thay vi sua tung dong: giao dien la mot bang nguoi dung them va
    xoa dong tu do, nen gui ca bang len la cach duy nhat khong sinh ra trang
    thai nua voi trong mot lan bam Luu.
    """
    actor = _actor(request)
    return _lenh(db,
                 lambda: bao_gia.thay_dong_hang_hoa(db, qid, data.get("items"), actor),
                 "Đã lưu bảng hàng hoá.")


@router.post("/api/quotations/{qid}/send")
async def gui_khach(request: Request, qid: str, db: Session = Depends(get_db)):
    """Gui bao gia cho khach: cap ma hien cho khach, chot phien ban gia.

    Bien duoi nguong thi KHONG sang "da gui" ma sang "cho duyet noi bo" — khac
    voi chot "khong duyet bao gia lo": lo la duoi gia thanh nen chan han, con
    duoi nguong bien la mot quyet dinh kinh doanh nen di qua nguoi duyet.
    """
    actor = _actor(request)

    def viec():
        q = bao_gia.gui_khach(db, qid, actor)
        return bao_gia.mot_bao_gia(db, q.id)

    return _lenh(db, viec, "Đã gửi báo giá cho khách.")


@router.post("/api/quotations/{qid}/accept")
async def khach_chap_nhan(request: Request, qid: str, db: Session = Depends(get_db)):
    """Ghi nhan khach chap nhan — buoc nay MO KHOA muc tach DO."""
    actor = _actor(request)

    def viec():
        q = bao_gia.khach_chap_nhan(db, qid, actor)
        return bao_gia.mot_bao_gia(db, q.id)

    return _lenh(db, viec, "Đã ghi nhận khách chấp nhận. Mục tách lệnh giao hàng đã mở.")


@router.post("/api/quotations/{qid}/reject")
async def khach_tu_choi(
    request: Request, qid: str,
    data: Dict[str, Any] = Body(default={}), db: Session = Depends(get_db),
):
    actor = _actor(request)

    def viec():
        q = bao_gia.khach_tu_choi(db, qid, (data or {}).get("reason", ""), actor)
        return bao_gia.mot_bao_gia(db, q.id)

    return _lenh(db, viec, "Đã đóng báo giá.")


@router.post("/api/quotations/{qid}/extend")
async def gia_han(
    request: Request, qid: str,
    data: Dict[str, Any] = Body(...), db: Session = Depends(get_db),
):
    """Gia han hieu luc, va mo lai mot bao gia da het han.

    Het han khong phai loi cua nguoi dung — gia dau va phi duong doi theo thang.
    Viec dung la soat lai gia roi gia han, chu khong phai tao mot bao gia moi va
    mat lich su cua cai cu.
    """
    actor = _actor(request)

    def viec():
        q = bao_gia.gia_han(db, qid, (data or {}).get("valid_to"), actor)
        return bao_gia.mot_bao_gia(db, q.id)

    return _lenh(db, viec, "Đã gia hạn hiệu lực báo giá.")


@router.post("/api/quotations/{qid}/split")
async def tach_do(
    request: Request, qid: str,
    data: Dict[str, Any] = Body(...), db: Session = Depends(get_db),
):
    """Tach bao gia da chap nhan thanh N lenh giao hang. MOT giao dich.

    Mot giao dich la yeu cau nghiep vu chu khong phai chi tiet ky thuat: tach ba
    DO ma dong thu ba vo thi hai DO dau da nam trong hang doi cua Dieu phoi, va
    khong ai biet bao gia nay da tach mot phan.
    """
    actor = _actor(request)
    return _lenh(db,
                 lambda: bao_gia.tach_thanh_do(db, qid, (data or {}).get("dos"), actor),
                 "Đã tạo lệnh giao hàng từ báo giá. Chúng nằm ở Giao hàng → Cần xử lý.")
