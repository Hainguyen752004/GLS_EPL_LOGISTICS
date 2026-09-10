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

import os
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse
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
    exclude: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Vai bao gia gan nhat da bao cho khach nay.

    Nguoi ban can biet lan truoc bao bao nhieu TRUOC KHI go mot con so moi — do
    la thu chan viec bao 3,9 trieu hom nay cho mot khach thang truoc da bao 4,1
    trieu cung tuyen.
    """
    try:
        return {"message": "Đã tải giá đã báo cho khách này.",
                "data": bao_gia.gia_da_bao_cho_khach(db, cid, route_id, limit, exclude)}
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
    ket_qua = {}

    def viec():
        q = bao_gia.gui_khach(db, qid, actor)
        ket_qua["trang_thai"] = q.canonical_status
        return bao_gia.mot_bao_gia(db, q.id)

    # THÔNG BÁO PHẢI NÓI ĐÚNG THỨ VỪA XẢY RA. Biên dưới ngưỡng thì báo giá sang
    # "chờ duyệt nội bộ" chứ không đến tay khách; nói "đã gửi cho khách" ở nước
    # đó là để người bán ngồi đợi một câu trả lời sẽ không bao giờ đến.
    goi = _lenh(db, viec, "Đã gửi báo giá cho khách.")
    if ket_qua.get("trang_thai") == "pending_approval":
        goi["message"] = ("Biên dưới ngưỡng nên báo giá chuyển sang CHỜ DUYỆT NỘI BỘ — "
                          "chưa gửi cho khách. Cần trưởng phòng kinh doanh duyệt.")
    return goi


@router.post("/api/quotations/{qid}/accept")
async def khach_chap_nhan(
    request: Request, qid: str,
    data: Dict[str, Any] = Body(default={}), db: Session = Depends(get_db),
):
    """Ghi nhan khach chap nhan VA SINH LENH GIAO HANG ngay — khong con buoc tach tay.

    DO ke thua tuyen, gia khoa, khung gio tu bao gia (khong di qua Don hang).
    Than tuy chon `{"dos": [...]}` cho phep khai tung DO (gio lay, so seal);
    bo trong thi sinh N DO mac dinh, N = tong so luong o bang Hang hoa.
    """
    actor = _actor(request)
    ket_qua = {}

    def viec():
        ket_qua.update(bao_gia.chap_nhan_va_sinh_do(db, qid, actor, (data or {}).get("dos")))
        return bao_gia.mot_bao_gia(db, qid)

    goi = _lenh(db, viec, "Đã ghi nhận khách chấp nhận.")
    goi["do_ids"] = ket_qua.get("do_ids") or []
    goi["gia_moi_chuyen"] = ket_qua.get("gia_moi_chuyen")
    goi["message"] = ("Đã ghi nhận khách chấp nhận · đã sinh %d lệnh giao hàng từ báo giá "
                      "(giá khoá %s đ/chuyến). Xem ở Lệnh giao hàng → Cần xử lý."
                      % (len(goi["do_ids"]), "{:,.0f}".format(ket_qua.get("gia_moi_chuyen") or 0)))
    return goi


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


# ===========================================================================
# DUYỆT NỘI BỘ
# ===========================================================================

@router.post("/api/quotations/{qid}/internal-approve")
async def duyet_noi_bo(request: Request, qid: str, db: Session = Depends(get_db)):
    """Trưởng phòng đồng ý bán dưới ngưỡng biên, báo giá đi tiếp sang khách.

    Báo giá LỖ không đi qua được đường này — `kiem_bao_gia_truoc_khi_duyet`
    chặn trước. Duyệt nội bộ mở cho khoảng biên mỏng, không mở cho khoản lỗ.
    """
    actor = _actor(request)

    def viec():
        q = bao_gia.duyet_noi_bo(db, qid, actor)
        return bao_gia.mot_bao_gia(db, q.id)

    return _lenh(db, viec, "Đã duyệt nội bộ. Báo giá đã gửi cho khách.")


@router.post("/api/quotations/{qid}/return-to-draft")
async def tra_ve_nhap(
    request: Request, qid: str,
    data: Dict[str, Any] = Body(default={}), db: Session = Depends(get_db),
):
    actor = _actor(request)

    def viec():
        q = bao_gia.tra_ve_nhap(db, qid, (data or {}).get("reason", ""), actor)
        return bao_gia.mot_bao_gia(db, q.id)

    return _lenh(db, viec, "Đã trả báo giá về bản nháp để sửa giá.")


# ===========================================================================
# CHỨNG TỪ ĐÍNH KÈM
#
# KHÔNG dùng `/uploads/{đường}` dùng chung với ảnh xe và ảnh tài xế. Đường đó
# CỐ Ý để công khai — thẻ <img src> không gửi được phiên đăng nhập — còn ở đây
# là hợp đồng và tờ khai hải quan của khách. Nên chứng từ báo giá đi qua một
# đường tải xuống RIÊNG, nằm dưới dependency xác thực của router này.
# ===========================================================================

def _thu_muc_chung_tu() -> Path:
    """Thư mục chứa chứng từ báo giá, dùng cùng gốc với ảnh dữ liệu gốc."""
    cau_hinh = os.environ.get("EPL_UPLOAD_DIR")
    goc = (Path(cau_hinh).expanduser().resolve() if cau_hinh
           else (Path(__file__).resolve().parent.parent.parent / "uploads").resolve())
    return (goc / "quotations").resolve()


def _duoi_hop_le(ten_tep: str) -> str:
    """Đuôi tệp, đối chiếu với DANH SÁCH CHO PHÉP.

    Danh sách cho phép chứ không danh sách chặn: một danh sách chặn luôn thiếu
    một đuôi nào đó, và ở đây một đuôi bị thiếu nghĩa là một tệp chạy được nằm
    trong thư mục máy chủ.
    """
    duoi = Path(str(ten_tep or "")).suffix.lower()
    if duoi not in bao_gia.DUOI_CHUNG_TU:
        raise_http(DomainError(
            "ATTACHMENT_TYPE_INVALID",
            "Chỉ đính kèm được PDF, DOCX, DOC, PNG, JPG. Tệp gửi lên có đuôi %s."
            % (duoi or "không rõ"), 422))
    return duoi


@router.post("/api/quotations/{qid}/attachments", status_code=201)
async def them_chung_tu(
    request: Request, qid: str,
    doc_type: str = Form("Khác"), note: str = Form(""),
    file: UploadFile = File(...), db: Session = Depends(get_db),
):
    """Đính kèm một chứng từ — được gọi NGAY KHI CÒN NHÁP, không bắt lưu trước.

    Tên tệp trên đĩa là một mã sinh ra, KHÔNG phải tên người dùng đặt. Tên
    người dùng đặt có thể là `../../.env`; nó được lưu nguyên trong cột
    `file_name` để hiện lại cho đúng, chứ không dùng làm đường dẫn.
    """
    actor = _actor(request)
    duoi = _duoi_hop_le(file.filename)

    # ĐỌC THEO KHÚC và dừng ngay khi qua trần: đọc cả tệp vào bộ nhớ rồi mới đo
    # nghĩa là một tệp 2 GB làm hết bộ nhớ máy chủ trước khi ai kiểm được gì.
    noi_dung = bytearray()
    while True:
        khuc = await file.read(1024 * 1024)
        if not khuc:
            break
        noi_dung.extend(khuc)
        if len(noi_dung) > bao_gia.TRAN_KICH_THUOC_BYTE:
            raise_http(DomainError(
                "ATTACHMENT_TOO_LARGE",
                "Chứng từ tối đa 25 MB. Tệp %s lớn hơn mức đó." % file.filename, 413))
    if not noi_dung:
        raise_http(DomainError("ATTACHMENT_EMPTY",
                               "Tệp %s rỗng — không đính kèm được." % file.filename, 422))

    thu_muc = _thu_muc_chung_tu()
    thu_muc.mkdir(parents=True, exist_ok=True)
    ten_tren_dia = "%s%s" % (uuid4().hex, duoi)
    duong = thu_muc / ten_tren_dia
    tam = thu_muc / (".%s.tmp" % ten_tren_dia)
    try:
        with open(tam, "wb") as tay:
            tay.write(bytes(noi_dung))
        os.replace(tam, duong)
    finally:
        if tam.exists():
            tam.unlink()

    def viec():
        dong = bao_gia.them_chung_tu(
            db, qid, doc_type, file.filename, ten_tren_dia,
            bao_gia.DUOI_CHUNG_TU[duoi], len(noi_dung), note, actor)
        return {"id": dong.id, "doc_type": dong.doc_type, "file_name": dong.file_name,
                "size_bytes": dong.size_bytes, "note": dong.note,
                "uploaded_by": dong.uploaded_by,
                "uploaded_at": dong.uploaded_at.isoformat() if dong.uploaded_at else None}

    return _lenh(db, viec, "Đã đính kèm chứng từ. Nó đi theo DO xuống vận hành và kế toán.")


@router.get("/api/quotations/{qid}/attachments/{aid}/file")
async def tai_chung_tu(qid: str, aid: str, db: Session = Depends(get_db)):
    try:
        dong = bao_gia.mot_chung_tu(db, qid, aid)
    except DomainError as loi:
        raise_http(loi)
    # Ghép đường từ THƯ MỤC CHUẨN cộng tên trên đĩa, rồi kiểm lại kết quả vẫn
    # nằm trong thư mục đó. Một cột cơ sở dữ liệu bị sửa tay thành `../..` thì
    # bước kiểm này là thứ duy nhất chặn việc trả về một tệp ngoài thư mục.
    thu_muc = _thu_muc_chung_tu()
    duong = (thu_muc / Path(str(dong.storage_url)).name).resolve()
    try:
        duong.relative_to(thu_muc)
    except ValueError:
        raise_http(DomainError("ATTACHMENT_NOT_FOUND", "Không tìm thấy tệp chứng từ.", 404))
    if not duong.is_file():
        raise_http(DomainError(
            "ATTACHMENT_FILE_MISSING",
            "Bản ghi chứng từ %s còn nhưng tệp trên đĩa không còn." % dong.file_name, 404))
    return FileResponse(duong, media_type=dong.mime_type or "application/octet-stream",
                        filename=dong.file_name)


@router.delete("/api/quotations/{qid}/attachments/{aid}")
async def xoa_chung_tu(request: Request, qid: str, aid: str, db: Session = Depends(get_db)):
    actor = _actor(request)

    def viec():
        ten = bao_gia.xoa_chung_tu(db, qid, aid, actor)
        return {"id": aid, "ten_tren_dia": ten}

    ket_qua = _lenh(db, viec, "Đã xoá chứng từ.")
    # XOÁ TỆP SAU KHI commit thành công. Xoá trước thì một lỗi ở bước commit sẽ
    # để lại một dòng trỏ tay không.
    ten = (ket_qua.get("data") or {}).get("ten_tren_dia")
    if ten:
        duong = (_thu_muc_chung_tu() / Path(str(ten)).name)
        try:
            if duong.is_file():
                duong.unlink()
        except OSError:
            # Bản ghi đã xoá là điều người dùng thấy; một tệp còn lại trên đĩa
            # không được làm yêu cầu này thất bại.
            pass
    return ket_qua
