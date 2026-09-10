from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import datetime as dt

from sqlalchemy import func

from models import CurrencyDefinition, CurrencyRateHistory, FinanceControlConfig
from services.errors import DomainError


def _decimal(value, field="giá trị", precision=None, scale=None):
    if isinstance(value, bool) or isinstance(value, float) or not isinstance(value, (Decimal, int, str)):
        raise DomainError("INVALID_DECIMAL", f"{field} phải là số Decimal hữu hạn.", 422)
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DomainError("INVALID_DECIMAL", f"{field} phải là số Decimal hữu hạn.", 422) from None
    if not result.is_finite():
        raise DomainError("INVALID_DECIMAL", f"{field} phải là số Decimal hữu hạn.", 422)
    if precision is not None:
        exponent = result.as_tuple().exponent
        fractional_digits = max(-exponent, 0)
        integer_digits = max(result.adjusted() + 1, 0) if result else 0
        if fractional_digits > scale or integer_digits > precision - scale:
            raise DomainError("DECIMAL_OUT_OF_RANGE", f"{field} vượt quá Numeric({precision},{scale}).", 422)
    return result


def _quantum(minor_units):
    if isinstance(minor_units, bool) or not isinstance(minor_units, int) or not 0 <= minor_units <= 6:
        raise DomainError("INVALID_MINOR_UNITS", "Số chữ số thập phân của tiền tệ phải từ 0 đến 6.", 422)
    return Decimal(1).scaleb(-minor_units)


def _quantize(value, minor_units):
    try:
        raw = _decimal(value)
        if raw and max(raw.adjusted() + 1, 0) > 18:
            raise DomainError("DECIMAL_OUT_OF_RANGE", "Số tiền vượt quá Numeric(24,6).", 422)
        result = raw.quantize(_quantum(minor_units), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise DomainError("DECIMAL_OUT_OF_RANGE", "Số tiền vượt quá Numeric(24,6).", 422) from None
    return _decimal(result, precision=24, scale=6)


def quantize_currency(db, amount, currency_code):
    currency = require_currency(db, currency_code)
    return _quantize(amount, currency.minor_units)


def calculate_charge_line(db, quantity, unit_price, tax_code=None, tax_mode=None):
    """Mot dong phi = so luong x don gia, KHONG THUE.

    Module thue (bang tax_codes) da xoa 10/09 cung module ke toan: thue do he cong
    no cua dong nghiep tinh luc phat hanh hoa don. Giu chu ky cu (tax_code,
    tax_mode) de ben goi khong phai doi, nhung ket qua luon la exempt / 0.
    """
    quantity = _decimal(quantity, "Số lượng", 18, 4)
    unit_price = _decimal(unit_price, "Đơn giá", 24, 6)
    config = require_finance_config(db)
    currency = require_currency(db, config.functional_currency)
    minor_units = currency.minor_units
    if quantity < 0:
        raise DomainError("INVALID_DECIMAL", "Số lượng không được âm.", 422)
    gross = _quantize(quantity * unit_price, minor_units)
    return {
        "net_amount": gross,
        "tax_amount": _quantize(Decimal(0), minor_units),
        "total_amount": gross,
        "tax_code": "EXEMPT",
        "tax_rate": Decimal(0),
        "tax_mode": "exempt",
    }


def allocate_rounding_residual(lines, residual, minor_units):
    quantum = _quantum(minor_units)
    residual = _decimal(residual, "Chênh lệch làm tròn")
    if residual != residual.quantize(quantum):
        raise DomainError("INVALID_ROUNDING_RESIDUAL", "Chênh lệch phải theo đơn vị nhỏ nhất của tiền tệ.", 422)
    normalized = []
    id_kind = None
    seen_ids = set()
    for line in lines:
        line_id, amount = (line["id"], line["amount"]) if isinstance(line, dict) else line
        if isinstance(line_id, bool):
            kind = None
        elif isinstance(line_id, (int, Decimal)):
            kind = "numeric"
        elif isinstance(line_id, str):
            kind = "string"
        else:
            kind = None
        if kind is None or (id_kind is not None and kind != id_kind):
            raise DomainError("INCOMPARABLE_ROUNDING_LINE_IDS", "Mã dòng phải cùng kiểu số hoặc cùng kiểu chuỗi.", 422)
        id_kind = kind
        if line_id in seen_ids:
            raise DomainError("DUPLICATE_ROUNDING_LINE_ID", "Mã dòng phân bổ không được trùng nhau.", 422)
        seen_ids.add(line_id)
        normalized.append((line_id, _decimal(amount, "Số tiền dòng")))
    if residual and not normalized:
        raise DomainError("ROUNDING_LINE_REQUIRED", "Cần ít nhất một dòng để phân bổ chênh lệch.", 422)
    adjustments = {line_id: Decimal(0).quantize(quantum) for line_id, _ in normalized}
    if residual:
        winner = min(normalized, key=lambda item: (-abs(item[1]), item[0]))[0]
        adjustments[winner] = residual
    return adjustments


def to_functional(db, amount, currency_code, rate_date):
    amount = _decimal(amount, "Số tiền giao dịch", 24, 6)
    transaction_currency = require_currency(db, currency_code)
    transaction_amount = _quantize(amount, transaction_currency.minor_units)
    config = require_finance_config(db)
    functional_currency = require_currency(db, config.functional_currency)
    if transaction_currency.code == functional_currency.code:
        rate = Decimal(1)
        snapshot_date = rate_date.date() if isinstance(rate_date, dt.datetime) else rate_date
        source = "IDENTITY"
    else:
        snapshot = resolve_exchange_rate(db, transaction_currency.code, functional_currency.code, rate_date)
        rate = _decimal(snapshot.rate, "Tỷ giá", 18, 8)
        snapshot_date = snapshot.rate_date
        source = snapshot.source
    if rate <= 0:
        raise DomainError("INVALID_EXCHANGE_RATE", "Tỷ giá phải lớn hơn 0.", 422)
    return {
        "transaction_amount": transaction_amount,
        "transaction_currency": transaction_currency.code,
        "functional_amount": _quantize(transaction_amount * rate, functional_currency.minor_units),
        "functional_currency": functional_currency.code,
        "exchange_rate_snapshot": rate,
        "rate_date": snapshot_date,
        "source": source,
    }


def require_currency(db, currency_code):
    code = str(currency_code or "").strip().upper()
    currency = db.query(CurrencyDefinition).filter(CurrencyDefinition.code == code, CurrencyDefinition.is_active.is_(True)).first()
    if not currency:
        raise DomainError("MISSING_CURRENCY", f"Thiếu tiền tệ {code}. Vui lòng vào Master Data để cấu hình trước khi tiếp tục luồng.", 422, ["master-data/currencies"])
    return currency


def require_finance_config(db):
    configs = db.query(FinanceControlConfig).all()
    if len(configs) != 1 or configs[0].id != "GLOBAL":
        raise DomainError("MISSING_FINANCE_CONFIG", "Thiếu cấu hình kiểm soát tài chính. Vui lòng vào Master Data để cấu hình trước khi tiếp tục luồng.", 422, ["master-data/finance-controls"])
    return configs[0]


def resolve_exchange_rate(db, currency_code, functional_currency, rate_date):
    currency = str(currency_code or "").strip().upper()
    functional = str(functional_currency or "").strip().upper()
    on_date = rate_date.date() if isinstance(rate_date, dt.datetime) else rate_date
    if not isinstance(on_date, dt.date):
        raise DomainError("INVALID_RATE_DATE", "Ngày tỷ giá không hợp lệ.", 422)
    require_currency(db, currency)
    require_currency(db, functional)
    snapshot = db.query(CurrencyRateHistory).filter(
        CurrencyRateHistory.currency_code == currency,
        CurrencyRateHistory.functional_currency == functional,
        CurrencyRateHistory.rate_date <= on_date,
        CurrencyRateHistory.is_active.is_(True),
    ).order_by(
        CurrencyRateHistory.rate_date.desc(),
        CurrencyRateHistory.source.asc(),
        CurrencyRateHistory.id.desc(),
    ).first()
    if not snapshot:
        raise DomainError("MISSING_EXCHANGE_RATE", f"Thiếu tỷ giá {currency}/{functional}. Vui lòng vào Master Data để cấu hình trước khi tiếp tục luồng.", 422, ["master-data/exchange-rates"])
    return snapshot
