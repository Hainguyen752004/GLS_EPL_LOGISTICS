"""Tep dinh kem cua don van chuyen: hop dong, bao gia da ky.

Lam theo dung mau cua POD (`delivery_completion_service`), ke ca cac tinh chat
an toan da co o do:

  · KHONG tin kieu tep do client khai. Kieu duoc suy ra tu MAGIC BYTE cua noi
    dung that. Kieu do client khai se duoc luu lai roi dung lam `media_type`
    luc phuc vu tep, nen tin theo no cho phep nguoi gui tu chon cach trinh
    duyet dien giai noi dung minh tai len.

  · Kiem kich thuoc TRUOC khi doc het. Doc het roi moi kiem nghia la ca tep
    da nam trong RAM truoc khi co bat ky loi tu choi nao.

  · Checksum duy nhat trong pham vi mot don: tai lai cung mot tep khong tao ra
    ban ghi thu hai.

Nhung KHAC POD o mot diem: POD chi nhan JPEG/PNG/PDF, con day con nhan DOCX vi
hop dong thuong o dang do. DOCX la mot tep ZIP, nen magic byte cua no
(`PK\\x03\\x04`) cung la magic byte cua moi tep ZIP. Dieu do chap nhan duoc vi
tep LUON duoc phuc vu dang `attachment` kem `nosniff` — trinh duyet khong bao
gio dien giai no, chi tai xuong.
"""
import datetime
import hashlib
import uuid

from models import SalesOrder, SalesOrderDocument
from services.errors import DomainError

#: 25 MB, dung con so giao dien da hua voi nguoi dung.
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024

ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
})

#: Chu ky nhan dang qua magic byte. Thu tu quan trong: chu ky dai kiem truoc.
_MAGIC_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"%PDF-", "application/pdf"),
    # DOCX la ZIP. `PK\x05\x06` va `PK\x07\x08` la ZIP rong / ZIP nhieu phan —
    # khong phai DOCX hop le, nen chi nhan `PK\x03\x04`.
    (b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
)

#: Loai chung tu duoc phep. Danh sach dong, khong nhan chuoi tuy y — cot nay
#: duoc hien thang len man hinh.
LOAI_CHUNG_TU = {
    "contract": "Hợp đồng",
    "signed_quotation": "Báo giá đã ký",
    "other": "Tài liệu khác",
}


def kiem_kich_thuoc(content: bytes) -> None:
    """Chan tep qua lon. Goi NGAY sau khi doc, truoc moi viec khac."""
    if len(content) > MAX_DOCUMENT_BYTES:
        raise DomainError(
            "SO_DOCUMENT_TOO_LARGE",
            "Tệp đính kèm tối đa 25 MB.",
            413,
        )
    if not content:
        raise DomainError(
            "SO_DOCUMENT_EMPTY",
            "Tệp đính kèm rỗng.",
            422,
        )


def suy_ra_mime(content: bytes, khai_bao: str | None) -> str:
    """Kieu tep suy ra tu NOI DUNG THAT, khong tin theo khai bao cua client."""
    head = content[:8]
    for chu_ky, mime in _MAGIC_SIGNATURES:
        if head.startswith(chu_ky):
            return mime
    khai_sach = (khai_bao or "").split(";")[0].strip().lower()
    if khai_sach in ALLOWED_MIME_TYPES:
        # Noi dung khong khop chu ky nao nhung client khai kieu hop le: tu
        # choi thay vi tin loi khai.
        raise DomainError(
            "SO_DOCUMENT_TYPE_INVALID",
            "Nội dung tệp không khớp với định dạng đã khai báo."
            " Chỉ nhận PDF, DOCX, JPEG hoặc PNG.",
            422,
        )
    raise DomainError(
        "SO_DOCUMENT_TYPE_INVALID",
        "Chỉ nhận tệp PDF, DOCX, JPEG hoặc PNG.",
        422,
    )


def _ten_an_toan(ten: str | None) -> str:
    """Ten tep sach: bo duong dan va ky tu dieu khien.

    Trinh duyet gui `filename` nguyen van tu may nguoi dung, nen no co the
    chua `..` hoac dau gach cheo. Ten nay di vao header Content-Disposition
    luc tai ve.
    """
    tho = (ten or "tai-lieu").replace("\\", "/").split("/")[-1]
    sach = "".join(ch for ch in tho if ch.isprintable() and ch not in '"\r\n')
    return (sach.strip() or "tai-lieu")[:255]


def them_tai_lieu(db, so_id, *, file_name, mime_type, content, document_type, note, actor):
    """Ghi mot tep dinh kem cho don van chuyen."""
    kiem_kich_thuoc(content)
    mime_that = suy_ra_mime(content, mime_type)

    if document_type not in LOAI_CHUNG_TU:
        raise DomainError(
            "SO_DOCUMENT_TYPE_UNKNOWN",
            "Loại chứng từ không hợp lệ: %s" % document_type,
            422,
        )

    don = db.get(SalesOrder, so_id)
    if not don:
        raise DomainError(
            "SALES_ORDER_NOT_FOUND",
            "Không tìm thấy đơn vận chuyển %s." % so_id,
            404,
        )

    checksum = hashlib.sha256(content).hexdigest()
    # Tai lai cung mot tep thi tra ve ban ghi da co, khong tao ban thu hai va
    # cung khong bao loi — nguoi dung bam nham hai lan la chuyen binh thuong.
    da_co = db.query(SalesOrderDocument).filter(
        SalesOrderDocument.so_id == so_id,
        SalesOrderDocument.checksum == checksum,
    ).first()
    if da_co:
        return da_co, False

    ban_ghi = SalesOrderDocument(
        id="SODOC-%s" % uuid.uuid4().hex,
        so_id=so_id,
        document_type=document_type,
        file_name=_ten_an_toan(file_name),
        mime_type=mime_that,
        file_size=len(content),
        checksum=checksum,
        content=content,
        note=(note or "").strip()[:500] or None,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        created_by=actor or "epl-module-user",
    )
    db.add(ban_ghi)
    db.flush()
    return ban_ghi, True


def danh_sach(db, so_id):
    """Cac tep dinh kem cua mot don. KHONG tra ve noi dung tep."""
    return db.query(SalesOrderDocument).filter(
        SalesOrderDocument.so_id == so_id
    ).order_by(SalesOrderDocument.created_at.desc()).all()


def serialize(ban_ghi):
    """Mo ta mot tep. Co y KHONG kem `content`.

    Danh sach tep duoc nap moi lan mo don; kem noi dung nghia la keo ca chuc
    MB qua mang chi de hien mot cai ten.
    """
    tao_luc = ban_ghi.created_at
    if tao_luc is not None and tao_luc.tzinfo is None:
        tao_luc = tao_luc.replace(tzinfo=datetime.timezone.utc)
    return {
        "id": ban_ghi.id,
        "so_id": ban_ghi.so_id,
        "document_type": ban_ghi.document_type,
        "document_type_label": LOAI_CHUNG_TU.get(ban_ghi.document_type, ban_ghi.document_type),
        "file_name": ban_ghi.file_name,
        "mime_type": ban_ghi.mime_type,
        "file_size": ban_ghi.file_size,
        "checksum": ban_ghi.checksum,
        "note": ban_ghi.note,
        "created_at": tao_luc.isoformat() if tao_luc else None,
        "created_by": ban_ghi.created_by,
        "download_url": "/api/sales-order-documents/%s" % ban_ghi.id,
    }


def xoa_tai_lieu(db, document_id):
    ban_ghi = db.get(SalesOrderDocument, document_id)
    if not ban_ghi:
        raise DomainError(
            "SO_DOCUMENT_NOT_FOUND",
            "Không tìm thấy tệp đính kèm.",
            404,
        )
    db.delete(ban_ghi)
    return ban_ghi
