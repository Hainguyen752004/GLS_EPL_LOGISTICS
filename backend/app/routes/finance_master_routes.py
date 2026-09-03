"""Dữ liệu điều khiển của nghiệp vụ tài chính: kỳ kế toán, mã thuế, ánh xạ GL.

Tách ra khỏi main.py vì hai lý do, và lý do thứ hai quan trọng hơn:

1. main.py từng ôm 63 endpoint inline trong khi đã có thư mục routes/ — hai kiểu
   đăng ký route song song, rất dễ để lọt một endpoint ra ngoài lớp kiểm tra
   chung.

2. Đây là những endpoint nguy hiểm nhất của hệ thống, và cả 12 cái từng KHÔNG
   kiểm quyền một dòng nào. Mở lại một kỳ kế toán đã đóng cho phép hạch toán lùi
   ngày; đổi ánh xạ tài khoản GL chuyển hướng bút toán; đổi thuế suất làm sai
   mọi dòng phí. Nghịch lý là chính nghiệp vụ dùng chúng lại được gác rất kỹ
   bằng finance_approver / finance_poster / finance_payment.

   Đặt chúng trên một router có dependency xác thực ở TẦNG ROUTER khiến việc gác
   quyền trở thành thuộc tính cấu trúc: một endpoint thêm vào file này được bảo
   vệ mặc định, không phụ thuộc vào việc người viết có nhớ gọi hàm kiểm tra hay
   không.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import AccountingPeriod, AccountMapping, TaxCode
from routes.shared import require_api_principal
from services.errors import DomainError, raise_http


# Dùng lại hàm chuẩn ở routes/shared.py thay vì viết bản thứ hai.
require_authenticated_principal = require_api_principal




router = APIRouter(dependencies=[Depends(require_authenticated_principal)])


# Các hàm phụ trợ cho master-data, chuyển từ main.py cùng nhóm endpoint dùng
# chúng. Chúng đều bật HTTP 422 với mã MASTER_DATA_INVALID, nên thông báo lỗi
# giữ nguyên như trước khi tách.
def _parse_iso_datetime(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(
            status_code=422,
            detail={"code": "MASTER_DATA_INVALID", "message": f"Vui lòng nhập {field} hợp lệ."},
        )
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"code": "MASTER_DATA_INVALID", "message": f"Vui lòng nhập {field} đúng định dạng ngày giờ."},
        )


def _parse_iso_date(value: str, field: str):
    if isinstance(value, str) and len(value.strip()) == 10:
        value = f"{value.strip()}T00:00:00"
    return _parse_iso_datetime(value, field).date()


def _clean_master_string(data: dict, key: str, label: str, max_len: int = 100) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_len:
        raise HTTPException(
            status_code=422,
            detail={"code": "MASTER_DATA_INVALID", "message": f"Vui lòng nhập {label} hợp lệ."},
        )
    return value.strip()


def _master_saved(entity):
    return {"message": "Đã lưu cấu hình Master Data vào CSDL.", "data": entity}


@router.post("/api/master-data/tax-codes")
def save_tax_code(data: dict = Body(...), db: Session = Depends(get_db)):
    code = _clean_master_string(data, "code", "mã thuế", 50).upper()
    try:
        rate = Decimal(str(data.get("rate")))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Vui lòng nhập thuế suất hợp lệ."})
    if rate < 0:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Thuế suất không được âm."})
    mode = str(data.get("mode") or "exclusive").strip().lower()
    if mode not in {"exclusive", "inclusive", "exempt"}:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Kiểu tính thuế không hợp lệ."})
    effective_from = _parse_iso_date(data.get("effective_from"), "ngày hiệu lực")
    tax = db.query(TaxCode).filter(TaxCode.code == code, TaxCode.effective_from == effective_from).first()
    if not tax:
        tax = TaxCode(code=code, effective_from=effective_from)
        db.add(tax)
    tax.rate = rate
    tax.mode = mode
    tax.effective_to = _parse_iso_date(data["effective_to"], "ngày hết hiệu lực") if data.get("effective_to") else None
    tax.is_active = bool(data.get("is_active", True))
    tax.updated_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(tax)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "MASTER_DATA_DUPLICATE", "message": "Mã thuế đã tồn tại hoặc dữ liệu không hợp lệ."})
    return _master_saved(tax)


@router.put("/api/master-data/tax-codes/{code}")
def update_tax_code(code: str, data: dict = Body(...), db: Session = Depends(get_db)):
    payload = dict(data or {})
    payload["code"] = code
    return save_tax_code(payload, db)


@router.post("/api/master-data/tax-codes/{code}/status")
def set_tax_code_status(code: str, data: dict = Body(default={}), db: Session = Depends(get_db)):
    is_active = bool((data or {}).get("is_active", True))
    rows = db.query(TaxCode).filter(func.upper(TaxCode.code) == str(code).upper()).all()
    if not rows:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy mã thuế cần cập nhật."})
    for row in rows:
        row.is_active = is_active
        row.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Đã cập nhật trạng thái mã thuế.", "data": {"code": code, "is_active": is_active}}


@router.delete("/api/master-data/tax-codes/{code}")
def delete_tax_code(code: str, db: Session = Depends(get_db)):
    rows = db.query(TaxCode).filter(func.upper(TaxCode.code) == str(code).upper()).all()
    if not rows:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy mã thuế cần xóa."})
    for row in rows:
        db.delete(row)
    db.commit()
    return {"message": "Đã xóa mã thuế khỏi Master Data.", "data": {"code": code}}


@router.post("/api/master-data/accounting-periods")
def save_accounting_period(data: dict = Body(...), db: Session = Depends(get_db)):
    period_id = _clean_master_string(data, "id", "mã kỳ kế toán", 50)
    starts_at = _parse_iso_datetime(data.get("starts_at"), "ngày bắt đầu kỳ")
    ends_at = _parse_iso_datetime(data.get("ends_at"), "ngày kết thúc kỳ")
    if starts_at > ends_at:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Ngày bắt đầu kỳ không được sau ngày kết thúc kỳ."})
    status = str(data.get("status") or "open").strip().lower()
    if status not in {"open", "closed"}:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Trạng thái kỳ kế toán chỉ được là mở hoặc đã khóa."})
    period = db.get(AccountingPeriod, period_id) or AccountingPeriod(id=period_id)
    db.add(period)
    period.starts_at = starts_at
    period.ends_at = ends_at
    period.status = status
    try:
        db.commit()
        db.refresh(period)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "MASTER_DATA_DUPLICATE", "message": "Kỳ kế toán đã tồn tại hoặc dữ liệu không hợp lệ."})
    return _master_saved(period)


@router.put("/api/master-data/accounting-periods/{period_id}")
def update_accounting_period(period_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    payload = dict(data or {})
    payload["id"] = period_id
    return save_accounting_period(payload, db)


@router.post("/api/master-data/accounting-periods/{period_id}/status")
def set_accounting_period_status(period_id: str, data: dict = Body(default={}), db: Session = Depends(get_db)):
    period = db.get(AccountingPeriod, period_id)
    if not period:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy kỳ kế toán cần cập nhật."})
    status = str((data or {}).get("status") or "open").strip().lower()
    if status not in {"open", "closed"}:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Trạng thái kỳ kế toán chỉ được là mở hoặc đã khóa."})
    period.status = status
    period.closed_at = datetime.utcnow() if status == "closed" else None
    period.closed_by = "ui" if status == "closed" else None
    db.commit()
    return {"message": "Đã cập nhật trạng thái kỳ kế toán.", "data": {"id": period_id, "status": status}}


@router.delete("/api/master-data/accounting-periods/{period_id}")
def delete_accounting_period(period_id: str, db: Session = Depends(get_db)):
    period = db.get(AccountingPeriod, period_id)
    if not period:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy kỳ kế toán cần xóa."})
    db.delete(period)
    db.commit()
    return {"message": "Đã xóa kỳ kế toán khỏi Master Data.", "data": {"id": period_id}}


@router.post("/api/master-data/account-mappings")
def save_account_mapping(data: dict = Body(...), db: Session = Depends(get_db)):
    mapping_key = _clean_master_string(data, "mapping_key", "khóa mapping", 120)
    account_code = _clean_master_string(data, "account_code", "tài khoản GL", 50)
    mapping = db.get(AccountMapping, mapping_key) or AccountMapping(mapping_key=mapping_key)
    db.add(mapping)
    mapping.account_code = account_code
    mapping.effective_from = _parse_iso_datetime(data["effective_from"], "ngày hiệu lực") if data.get("effective_from") else None
    mapping.effective_to = _parse_iso_datetime(data["effective_to"], "ngày hết hiệu lực") if data.get("effective_to") else None
    if mapping.effective_from and mapping.effective_to and mapping.effective_from > mapping.effective_to:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Ngày hiệu lực mapping không hợp lệ."})
    try:
        db.commit()
        db.refresh(mapping)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "MASTER_DATA_DUPLICATE", "message": "Mapping tài khoản đã tồn tại hoặc dữ liệu không hợp lệ."})
    return _master_saved(mapping)


@router.put("/api/master-data/account-mappings/{mapping_key}")
def update_account_mapping(mapping_key: str, data: dict = Body(...), db: Session = Depends(get_db)):
    payload = dict(data or {})
    payload["mapping_key"] = mapping_key
    return save_account_mapping(payload, db)


@router.post("/api/master-data/account-mappings/{mapping_key}/status")
def set_account_mapping_status(mapping_key: str, data: dict = Body(default={}), db: Session = Depends(get_db)):
    mapping = db.get(AccountMapping, mapping_key)
    if not mapping:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy mapping tài khoản cần cập nhật."})
    status = str((data or {}).get("status") or "active").strip().lower()
    if status not in {"active", "inactive"}:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Trạng thái mapping chỉ được là hoạt động hoặc ngưng hoạt động."})
    if status == "inactive" and not mapping.effective_to:
        mapping.effective_to = datetime.utcnow()
    if status == "active":
        mapping.effective_to = None
    db.commit()
    return {"message": "Đã cập nhật trạng thái mapping tài khoản.", "data": {"mapping_key": mapping_key, "status": status}}


@router.delete("/api/master-data/account-mappings/{mapping_key}")
def delete_account_mapping(mapping_key: str, db: Session = Depends(get_db)):
    mapping = db.get(AccountMapping, mapping_key)
    if not mapping:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy mapping tài khoản cần xóa."})
    db.delete(mapping)
    db.commit()
    return {"message": "Đã xóa mapping tài khoản khỏi Master Data.", "data": {"mapping_key": mapping_key}}
