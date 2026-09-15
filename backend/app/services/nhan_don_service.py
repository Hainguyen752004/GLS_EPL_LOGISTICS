"""Nhận đơn tự động: email hoặc tệp tải lên -> AI đọc -> hộp chờ duyệt -> đơn hàng thật.

Nguyên tắc của module này: **máy đọc, người duyệt.**

AI đọc phiếu rất nhanh nhưng không phải lúc nào cũng đúng, mà một đơn sai đi
thẳng vào luồng đóng gói nghĩa là hàng ra khỏi kho sai. Vì vậy không có đường
nào từ email đi thẳng vào `sales_orders`. Mọi thứ AI đọc ra chỉ là BẢN NHÁP nằm
trong hộp chờ; người duyệt mở tệp gốc đối chiếu, sửa lại nếu cần, chọn khách
hàng trong danh mục, rồi bấm duyệt. Lúc đó mới sinh đơn hàng thật.
"""

import base64
import datetime
import json
import logging

from sqlalchemy import func

from models import Customer, InboundOrder
from services import doc_don_ai, don_hang_service
from services.loi import LoiNghiepVu

logger = logging.getLogger(__name__)

# Chỉ nhận các kiểu tệp là phiếu đặt hàng. Ảnh chữ ký, logo trong thân thư cũng
# là tệp đính kèm, nhận bừa thì AI đọc logo và sinh ra đơn rỗng.
DUOI_NHAN = (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".xlsx", ".xls", ".xlsm", ".csv", ".txt")
TOI_DA_BYTE = 15 * 1024 * 1024


def _json(chu, mac_dinh):
    if not chu:
        return mac_dinh
    try:
        return json.loads(chu)
    except ValueError:
        return mac_dinh


def ra_dict(ib, kem_nhap=True):
    d = {
        "id": ib.id,
        "source": ib.source,
        "from_email": ib.from_email,
        "subject": ib.subject,
        "received_at": ib.received_at,
        "file_name": ib.file_name,
        "file_mime": ib.file_mime,
        "file_size": ib.file_size,
        "has_file": bool(ib.file_data),
        "status": ib.status,
        "ai_confidence": ib.ai_confidence,
        "ai_warnings": _json(ib.ai_warnings, []),
        "ai_error": ib.ai_error,
        "so_id": ib.so_id,
        "reviewed_by": ib.reviewed_by,
        "reviewed_at": ib.reviewed_at,
        "note": ib.note,
        "created_at": ib.created_at,
    }
    if kem_nhap:
        d["draft"] = _json(ib.draft, None)
        d["body_text"] = ib.body_text
    else:
        nhap = _json(ib.draft, None) or {}
        d["po_number"] = nhap.get("po_number")
        d["ship_to_name"] = nhap.get("ship_to_name")
        d["line_count"] = len(nhap.get("lines") or [])
    return d


def nap(db, ib_id):
    ib = db.query(InboundOrder).filter(InboundOrder.id == ib_id).first()
    if not ib:
        raise LoiNghiepVu("IB_NOT_FOUND", "Khong tim thay phieu nhan " + str(ib_id), 404)
    return ib


def danh_sach(db, trang_thai=None, q=None, trang=1, moi_trang=25):
    cau = db.query(InboundOrder)
    if trang_thai and trang_thai != "all":
        if trang_thai == "pending":
            cau = cau.filter(InboundOrder.status.in_(["new", "parsed", "failed"]))
        else:
            cau = cau.filter(InboundOrder.status == trang_thai)
    if q:
        tim = "%" + q.strip() + "%"
        cau = cau.filter(
            InboundOrder.id.ilike(tim)
            | InboundOrder.subject.ilike(tim)
            | InboundOrder.from_email.ilike(tim)
            | InboundOrder.file_name.ilike(tim)
        )
    tong = cau.count()
    hang = (
        cau.order_by(InboundOrder.received_at.desc())
        .offset((trang - 1) * moi_trang)
        .limit(moi_trang)
        .all()
    )
    dem = dict(
        db.query(InboundOrder.status, func.count(InboundOrder.id))
        .group_by(InboundOrder.status)
        .all()
    )
    return {
        "items": [ra_dict(x, kem_nhap=False) for x in hang],
        "total": tong,
        "page": trang,
        "page_size": moi_trang,
        "counts": {
            "pending": int(dem.get("new", 0)) + int(dem.get("parsed", 0)) + int(dem.get("failed", 0)),
            "parsed": int(dem.get("parsed", 0)),
            "failed": int(dem.get("failed", 0)),
            "approved": int(dem.get("approved", 0)),
            "rejected": int(dem.get("rejected", 0)),
        },
    }


def tep_goc(db, ib_id):
    """Tệp gốc để người duyệt mở ra đối chiếu. Không có tệp gốc thì không duyệt được."""
    ib = nap(db, ib_id)
    if not ib.file_data:
        raise LoiNghiepVu("IB_NO_FILE", "Phiếu này không có tệp đính kèm", 404)
    return base64.b64decode(ib.file_data), ib.file_mime or "application/octet-stream", ib.file_name


# --------------------------------------------------------------------------
# Nhận vào
# --------------------------------------------------------------------------
def _hop_le(ten, mime, so_byte):
    if so_byte > TOI_DA_BYTE:
        raise LoiNghiepVu("IB_FILE_TOO_BIG", "Tệp lớn hơn 15 MB, máy chủ không nhận")
    if not (ten or "").lower().endswith(DUOI_NHAN):
        raise LoiNghiepVu(
            "IB_FILE_TYPE",
            "Không nhận tệp kiểu này (" + str(ten) + ") — chỉ nhận PDF, ảnh, Excel, CSV, TXT",
        )


def them_tu_tep(db, ten, mime, du_lieu, nguoi, ghi_chu=None):
    """Người dùng tự tải phiếu lên — dùng khi khách gửi qua Zalo, WhatsApp hay cầm giấy tới."""
    _hop_le(ten, mime, len(du_lieu))
    ib = InboundOrder(
        source="upload",
        from_email=nguoi,
        subject=ten,
        file_name=ten,
        file_mime=mime,
        file_size=len(du_lieu),
        file_data=base64.b64encode(du_lieu).decode("ascii"),
        received_at=datetime.datetime.utcnow(),
        status="new",
        note=ghi_chu,
    )
    db.add(ib)
    db.flush()
    return ib


def _tep_dang_ke(files):
    """Chọn tệp giống phiếu đặt hàng nhất: ưu tiên PDF, rồi Excel, rồi ảnh, rồi tệp to nhất."""
    hop_le = [t for t in files if (t.get("name") or "").lower().endswith(DUOI_NHAN)]
    if not hop_le:
        return None
    thu_tu = {".pdf": 0, ".xlsx": 1, ".xls": 1, ".xlsm": 1, ".csv": 2, ".txt": 3}

    def diem(t):
        ten = t["name"].lower()
        duoi = ten[ten.rfind(".") :]
        return (thu_tu.get(duoi, 4), -len(t.get("data") or b""))

    return sorted(hop_le, key=diem)[0]


def quet_hop_thu(db, gioi_han=10, nguoi="system"):
    """Quét thư chưa đọc, mỗi thư thành một phiếu trong hộp chờ.

    Đánh dấu đã đọc NGAY sau khi ghi vào hộp chờ, không đợi AI đọc xong: AI có
    thể hỏng, nhưng lá thư thì đã nằm an toàn trong hộp chờ rồi, và bỏ dấu chưa
    đọc chính là thứ ngăn lần quét sau nhận lại một đơn hai lần.
    """
    from services import gmail_service

    ds = gmail_service.danh_sach_thu_chua_doc(gioi_han)
    moi, bo_qua = [], 0
    for mid in ds:
        if db.query(InboundOrder).filter(InboundOrder.message_id == mid).first():
            bo_qua += 1
            continue
        try:
            thu = gmail_service.chi_tiet_thu(mid)
        except LoiNghiepVu as loi:
            logger.warning("Bo qua thu %s: %s", mid, loi.thong_diep)
            continue

        tep = _tep_dang_ke(thu["files"])
        if not tep and not thu["text"]:
            bo_qua += 1
            gmail_service.danh_dau_da_doc(mid)
            continue

        ib = InboundOrder(
            source="gmail",
            message_id=mid,
            from_email=thu["from_email"],
            subject=thu["subject"],
            body_text=thu["text"][:20000] or None,
            received_at=thu["received_at"],
            status="new",
        )
        if tep:
            ib.file_name = tep["name"]
            ib.file_mime = tep["mime"]
            ib.file_size = len(tep["data"])
            ib.file_data = base64.b64encode(tep["data"]).decode("ascii")
        db.add(ib)
        db.flush()
        gmail_service.danh_dau_da_doc(mid)
        moi.append(ib)

    db.commit()

    # Đọc bằng AI SAU khi đã lưu hết. AI hỏng thì phiếu vẫn còn, bấm "Đọc lại" là xong.
    for ib in moi:
        try:
            doc_bang_ai(db, ib.id)
        except Exception as loi:  # noqa: BLE001 - mot phieu hong khong duoc chan ca me
            logger.warning("AI khong doc duoc %s: %s", ib.id, loi)
    db.commit()
    return {"new": len(moi), "skipped": bo_qua, "scanned": len(ds)}


# --------------------------------------------------------------------------
# AI đọc
# --------------------------------------------------------------------------
def doc_bang_ai(db, ib_id):
    """Cho AI đọc phiếu ra bản nháp. Gọi lại được nhiều lần, lần sau đè lần trước."""
    ib = nap(db, ib_id)
    if ib.status == "approved":
        raise LoiNghiepVu("IB_ALREADY_APPROVED", "Phiếu này đã duyệt thành đơn hàng rồi", 409)
    try:
        if ib.file_data:
            nhap = doc_don_ai.doc_tep(
                base64.b64decode(ib.file_data), ib.file_mime, ib.file_name or "", ib.body_text or ""
            )
        else:
            nhap = doc_don_ai.doc_chu(ib.body_text or "")
    except Exception as loi:  # noqa: BLE001
        # Bắt MỌI lỗi chứ không riêng LoiAI: một lỗi lạ từ phía AI mà lọt ra
        # ngoài thì phiếu kẹt ở "mới nhận" và người duyệt không hiểu vì sao màn
        # không hiện gì. Ghi lại lý do rồi để họ bấm Đọc lại.
        ib.status = "failed"
        ib.ai_error = str(loi)[:500]
        db.flush()
        raise LoiNghiepVu("IB_AI_FAILED", str(loi), 502)

    _doan_khach(db, nhap)
    ib.draft = json.dumps(nhap, ensure_ascii=False)
    ib.ai_confidence = nhap.get("confidence") or 0
    ib.ai_warnings = json.dumps(nhap.get("warnings") or [], ensure_ascii=False)
    ib.ai_error = None
    ib.status = "parsed"
    db.flush()
    return ib


def _doan_khach(db, nhap):
    """Dò tên nơi nhận trong danh mục để người duyệt đỡ phải chọn tay.

    Chỉ GỢI Ý. Người duyệt vẫn phải xác nhận ô chọn khách hàng, vì đây là thứ
    quyết định hàng đi về đâu — khớp gần đúng mà tự chốt là sai địa chỉ giao.
    """
    for khoa, loai in (("ship_to", "customer"), ("vendor", "vendor")):
        ma = (nhap.get(khoa + "_code") or "").strip()
        ten = (nhap.get(khoa + "_name") or "").strip()
        tim = None
        if ma:
            tim = (
                db.query(Customer)
                .filter(func.lower(Customer.code) == ma.lower(), Customer.kind == loai)
                .first()
            )
        if not tim and ten:
            tim = (
                db.query(Customer)
                .filter(Customer.kind == loai, Customer.name.ilike("%" + ten + "%"))
                .first()
            )
        nhap[khoa + "_suggest_id"] = tim.id if tim else None
        nhap[khoa + "_suggest_name"] = tim.name if tim else None
    return nhap


def sua_nhap(db, ib_id, nhap_moi):
    """Người duyệt sửa bản nháp trước khi duyệt. Sửa xong vẫn là bản nháp."""
    ib = nap(db, ib_id)
    if ib.status == "approved":
        raise LoiNghiepVu("IB_ALREADY_APPROVED", "Phiếu này đã duyệt thành đơn hàng rồi", 409)
    if not isinstance(nhap_moi, dict):
        raise LoiNghiepVu("IB_DRAFT_INVALID", "Bản nháp gửi lên không đúng định dạng")
    cu = _json(ib.draft, {}) or {}
    cu.update(nhap_moi)
    ib.draft = json.dumps(cu, ensure_ascii=False)
    if ib.status == "failed":
        ib.status = "parsed"
    db.flush()
    return ib


# --------------------------------------------------------------------------
# Duyệt
# --------------------------------------------------------------------------
def duyet(db, ib_id, payload, nguoi):
    """Biến bản nháp thành ĐƠN HÀNG THẬT.

    Đây là cửa duy nhất đi từ hộp chờ sang `sales_orders`, và nó đi qua đúng
    `don_hang_service.tao` như khi người ta gõ tay — nên mọi ràng buộc của đơn
    hàng (phải có PO, PO không trùng, phải chọn khách trong danh mục, dòng hàng
    phải có số lượng) áp y hệt. Không có đường tắt nào cho đơn tới từ email.
    """
    ib = nap(db, ib_id)
    if ib.status == "approved":
        raise LoiNghiepVu("IB_ALREADY_APPROVED", "Phiếu này đã duyệt thành đơn hàng rồi", 409)
    if ib.status == "rejected":
        raise LoiNghiepVu("IB_REJECTED", "Phiếu này đã bị bỏ, không duyệt được nữa", 409)

    nhap = dict(_json(ib.draft, {}) or {})
    nhap.update(payload or {})
    if not nhap.get("lines"):
        raise LoiNghiepVu("IB_NO_LINES", "Bản nháp chưa có dòng hàng nào để tạo đơn")
    if not nhap.get("customer_id"):
        raise LoiNghiepVu("IB_NO_CUSTOMER", "Phải chọn khách hàng trong danh mục trước khi duyệt")

    don = don_hang_service.tao(
        db,
        {
            "po_number": nhap.get("po_number"),
            "order_date": nhap.get("order_date"),
            "shipping_date": nhap.get("shipping_date"),
            "customer_id": nhap.get("customer_id"),
            "vendor_id": nhap.get("vendor_id"),
            "tax_number": nhap.get("tax_number"),
            "currency": nhap.get("currency"),
            "note": nhap.get("note") or ("Nhan tu dong tu " + ib.source + " - " + ib.id),
            "lines": nhap["lines"],
        },
        nguoi,
    )
    ib.draft = json.dumps(nhap, ensure_ascii=False)
    ib.status = "approved"
    ib.so_id = don.id
    ib.reviewed_by = nguoi
    ib.reviewed_at = datetime.datetime.utcnow()
    db.flush()
    return ib, don


def bo(db, ib_id, ly_do, nguoi):
    ib = nap(db, ib_id)
    if ib.status == "approved":
        raise LoiNghiepVu("IB_ALREADY_APPROVED", "Phiếu này đã duyệt thành đơn hàng rồi", 409)
    ib.status = "rejected"
    ib.note = (ly_do or "").strip() or ib.note
    ib.reviewed_by = nguoi
    ib.reviewed_at = datetime.datetime.utcnow()
    db.flush()
    return ib


def trang_thai_ket_noi():
    """Giao diện hỏi để biết có bật nút Quét hộp thư không."""
    from services import gmail_service

    thu = gmail_service.kiem_tra()
    return {
        "ai_ready": doc_don_ai.san_sang(),
        "gmail_ready": thu["ok"],
        "gmail_reason": thu["reason"],
        "mailbox": thu["mailbox"],
    }
