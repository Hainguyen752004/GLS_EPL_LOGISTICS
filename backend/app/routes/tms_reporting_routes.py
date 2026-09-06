import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import EPLExpenseVoucher
from schemas.reporting import ExpenseVoucherRequest
from services import tms_reporting_service
from services.errors import DomainError, conflict, raise_http
from services.finance_authorization import resolve_finance_context


router = APIRouter(prefix="/api/tms/reporting", tags=["TMS Reporting"])


def _context(request, db, required):
    db.info["request_ip"] = request.client.host if request.client else None
    try:
        return resolve_finance_context(
            db, getattr(request.state, "principal", None), set(required)
        )
    except DomainError as error:
        raise_http(error)


def _key(value):
    if not isinstance(value, str) or not value.strip():
        raise_http(DomainError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Thiếu Idempotency-Key cho thao tác tài chính.",
            422,
        ))
    return value.strip()


def _report(db, date_from, date_to, customer_id, vehicle_id, currency_code):
    return tms_reporting_service.get_transport_revenue(
        db, date_from, date_to, customer_id, vehicle_id, currency_code
    )


@router.get("/transport-revenue")
def transport_revenue(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    customer_id: Optional[str] = None,
    vehicle_id: Optional[str] = None,
    currency_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    _context(request, db, {"finance_read"})
    try:
        parsed_from = tms_reporting_service._date(date_from) if date_from else None
        parsed_to = tms_reporting_service._date(date_to) if date_to else None
        data = _report(db, parsed_from, parsed_to, customer_id, vehicle_id, currency_code)
        return {"message": "Đã tải báo cáo doanh thu vận tải.", "data": jsonable_encoder(data)}
    except DomainError as error:
        raise_http(error)


# Ký tự mở đầu khiến Excel/LibreOffice coi ô là công thức.
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value):
    """Trung hòa CSV formula injection.

    Tên khách hàng, ghi chú và điểm đi/đến được ghi nguyên văn vào file CSV rồi
    phục vụ dưới dạng attachment. Một ô bắt đầu bằng "=" sẽ được Excel thực thi
    như công thức, nên `=cmd|'/c calc'!A0` đặt trong tên khách hàng sẽ chạy trên
    máy của người làm tài chính khi họ mở file export.
    """
    if value is None:
        return value
    if not isinstance(value, str):
        return value
    return "'" + value if value.startswith(_CSV_FORMULA_PREFIXES) else value


@router.get("/transport-revenue/export.csv")
def export_transport_revenue(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    customer_id: Optional[str] = None,
    vehicle_id: Optional[str] = None,
    currency_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    _context(request, db, {"finance_read"})
    # Ban JSON ngay ben tren co `try/except DomainError -> raise_http`, ban CSV
    # nay thi khong. Cung mot nguyen nhan — chua cau hinh tien te chuc nang,
    # ngay loc khong hop le — ma mot ben tra 422 kem loi doc duoc, con ben nay
    # nem DomainError khong ai bat: nguoi dung bam "Xuat CSV" va nhan 500
    # Internal Server Error, khong biet minh phai sua gi.
    try:
        data = _report(
            db,
            tms_reporting_service._date(date_from) if date_from else None,
            tms_reporting_service._date(date_to) if date_to else None,
            customer_id,
            vehicle_id,
            currency_code,
        )
    except DomainError as error:
        raise_http(error)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "STT", "Ngày đi", "Số lệnh điều xe", "Ngày ghi nhận", "Số hóa đơn",
        "Điểm đi", "Điểm đến", "Công ty đại lý", "Tên tài xế",
        "Biển số đầu kéo", "Biển số rơ-moóc", "Mã số xe", "Tên khách hàng",
        "Loại hàng hóa", "Số chuyến", "Đơn vị tính", "Trọng lượng (Tấn)",
        "Tổng tiền (Kip)", "Tổng tiền (Baht)", "Tổng tiền (USD)",
        "Tổng tiền (NDT)", "Tổng tiền (VNĐ)", "Ghi chú",
    ])
    for index, row in enumerate(data["rows"], 1):
        totals = row["totals"]
        writer.writerow([_csv_safe(cell) for cell in [
            index, row["departure_date"], row["dispatch_order_no"],
            row["recognition_date"], row["invoice_no"], row["origin"],
            row["destination"], row["agency_company"], row["driver_name"],
            row["tractor_plate"], row["trailer_plate"], row["vehicle_code"],
            row["customer_name"], row["cargo_type"], row["trip_count"],
            row["uom"], row["weight_tons"], totals.get("LAK"), totals.get("THB"),
            totals.get("USD"), totals.get("CNY"), totals.get("VND"), row["note"],
        ]])
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=bao-cao-doanh-thu-van-tai.csv"},
    )


@router.get("/expense-vouchers")
def expense_vouchers(request: Request, db: Session = Depends(get_db)):
    _context(request, db, {"finance_read"})
    return {
        "message": "Đã tải danh sách phiếu chi phí.",
        "data": jsonable_encoder(tms_reporting_service.list_expense_vouchers(db)),
    }


@router.get("/expense-vouchers/{identifier}")
def expense_voucher(request: Request, identifier: str, db: Session = Depends(get_db)):
    _context(request, db, {"finance_read"})
    try:
        data = tms_reporting_service.get_expense_voucher(db, identifier)
        return {"message": "Đã tải phiếu chi phí.", "data": jsonable_encoder(data)}
    except DomainError as error:
        raise_http(error)


@router.put("/trips/{trip_id}/expense-voucher")
def save_expense_voucher(
    request: Request,
    trip_id: str,
    data: ExpenseVoucherRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    actor, permissions = _context(request, db, {"finance_creator"})
    try:
        voucher = tms_reporting_service.save_expense_voucher(
            db,
            trip_id,
            data.model_dump(),
            request.method,
            request.url.path,
            _key(idempotency_key),
            actor,
            permissions,
        )
        db.commit()
        voucher = db.get(EPLExpenseVoucher, voucher.id)
        result = tms_reporting_service.serialize_expense_voucher(db, voucher)
        return {"message": "Đã lưu phiếu chi phí EPL vào cơ sở dữ liệu.", "data": jsonable_encoder(result)}
    except DomainError as error:
        db.rollback()
        raise_http(error)
    except IntegrityError:
        db.rollback()
        raise_http(conflict(
            "EXPENSE_VOUCHER_CONFLICT",
            "Số phiếu đã tồn tại hoặc hồ sơ vừa được người khác cập nhật.",
        ))
