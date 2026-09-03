"""Tỷ giá tham chiếu và tỷ giá do người dùng duyệt.

Tách trọn một mối quan tâm ra khỏi main.py: state trong bộ nhớ, luồng làm mới
định kỳ, hàm gọi nhà cung cấp, và 5 endpoint — tất cả ở cùng một chỗ thay vì
rải trên 250 dòng giữa các nhóm nghiệp vụ khác.

Đây là nhóm TÀI CHÍNH: tỷ giá nuôi mọi phép quy đổi tiền tệ qua
services/tms_money.resolve_exchange_rate, và POST /api/currencies ghi bản ghi
với source="APPROVED_UI" — mà resolve_exchange_rate sắp theo source tăng dần
nên tỷ giá ghi ở đây LUÔN THẮNG. Đặt tỷ giá bằng 1 là định giá lại toàn bộ sổ
AR/AP. Endpoint này từng không kiểm quyền một dòng nào.

Vì vậy router mang dependency xác thực ở TẦNG ROUTER: một endpoint thêm vào file
này được bảo vệ mặc định.

LƯU Ý về nhiều worker: currency_reference_state là biến trong bộ nhớ TIẾN TRÌNH.
Với --workers N thì mỗi worker giữ một bản riêng, nên hai client có thể nhận hai
tỷ giá tham chiếu khác nhau từ cùng một API, và luồng làm mới chạy N lần trên
cùng một quota của nhà cung cấp. Muốn đúng thì phải đưa cache này ra ngoài
(database hoặc Redis) và chạy lịch làm mới như một tiến trình riêng.
"""

import os
import threading
import urllib.parse
import urllib.request
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from threading import Event, Thread
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from database import get_db
from models import Currency, CurrencyDefinition, CurrencyRateHistory
from routes.finance_master_routes import require_authenticated_principal


router = APIRouter(dependencies=[Depends(require_authenticated_principal)])

currency_reference_lock = threading.Lock()
currency_reference_fetch_lock = threading.Lock()
currency_reference_scheduler_started = False
currency_reference_refresh_hours = max(
    1, int(os.getenv("EXCHANGE_RATE_REFRESH_HOURS", "12") or "12")
)
currency_reference_state = {
    "status": "not_configured",
    "provider": "openexchangerates.org",
    "base": "VND",
    "rates": {},
    "fetched_at": None,
    "provider_timestamp": None,
    "next_refresh_at": None,
    "refresh_interval_hours": currency_reference_refresh_hours,
    "applied": False,
    "error": None,
}

# 2.5 Currencies API
def _currency_reference_snapshot():
    with currency_reference_lock:
        snapshot = dict(currency_reference_state)
        snapshot["rates"] = dict(currency_reference_state.get("rates") or {})
    if not os.getenv("OPEN_EXCHANGE_RATES_APP_ID", "").strip() and not snapshot["rates"]:
        snapshot["status"] = "not_configured"
    return snapshot


def _request_open_exchange_rates(app_id: str):
    query = urllib.parse.urlencode({
        "app_id": app_id,
        "symbols": "USD,VND,THB,LAK",
    })
    request = urllib.request.Request(
        f"https://openexchangerates.org/api/latest.json?{query}",
        headers={"Accept": "application/json", "User-Agent": "EPL-Logistics/1.0"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_currency_reference_rates():
    app_id = os.getenv("OPEN_EXCHANGE_RATES_APP_ID", "").strip()
    if not app_id:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "EXCHANGE_RATE_PROVIDER_NOT_CONFIGURED",
                "message": "Chưa cấu hình OPEN_EXCHANGE_RATES_APP_ID; tỷ giá đang giữ theo cấu hình thủ công.",
            },
        )

    try:
        payload = _request_open_exchange_rates(app_id)
        source_rates = payload.get("rates") or {}
        usd_to_vnd = float(source_rates["VND"])
        usd_to_thb = float(source_rates["THB"])
        usd_to_lak = float(source_rates["LAK"])
        if min(usd_to_vnd, usd_to_thb, usd_to_lak) <= 0:
            raise ValueError("Provider returned a non-positive exchange rate")
    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        with currency_reference_lock:
            currency_reference_state["status"] = "error"
            currency_reference_state["error"] = "Provider response is missing USD/VND/THB/LAK rates."
        raise HTTPException(
            status_code=502,
            detail={
                "code": "EXCHANGE_RATE_PROVIDER_INVALID_RESPONSE",
                "message": "Nhà cung cấp trả dữ liệu tỷ giá không đầy đủ hoặc không hợp lệ.",
            },
        ) from exc
    except Exception as exc:
        with currency_reference_lock:
            currency_reference_state["status"] = "error"
            currency_reference_state["error"] = str(exc)
        raise HTTPException(
            status_code=502,
            detail={
                "code": "EXCHANGE_RATE_PROVIDER_UNAVAILABLE",
                "message": "Không thể cập nhật tỷ giá tham chiếu; tỷ giá vận hành hiện tại không thay đổi.",
            },
        ) from exc

    now = datetime.now(timezone.utc)
    provider_timestamp = payload.get("timestamp")
    provider_time = None
    if provider_timestamp:
        try:
            provider_time = datetime.fromtimestamp(float(provider_timestamp), timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            provider_time = None
    rates = {
        "USD": usd_to_vnd,
        "THB": usd_to_vnd / usd_to_thb,
        "LAK": usd_to_vnd / usd_to_lak,
    }
    with currency_reference_lock:
        currency_reference_state.update({
            "status": "ready",
            "rates": rates,
            "fetched_at": now.isoformat(),
            "provider_timestamp": provider_time,
            "next_refresh_at": (now + timedelta(hours=currency_reference_refresh_hours)).isoformat(),
            "refresh_interval_hours": currency_reference_refresh_hours,
            "applied": False,
            "error": None,
        })
    return _currency_reference_snapshot()


def _refresh_currency_reference_rates():
    with currency_reference_fetch_lock:
        cached = _currency_reference_snapshot()
        next_refresh_at = cached.get("next_refresh_at")
        if cached.get("status") == "ready" and next_refresh_at:
            try:
                if datetime.fromisoformat(next_refresh_at) > datetime.now(timezone.utc):
                    return cached
            except (TypeError, ValueError):
                pass
        return _fetch_currency_reference_rates()


def _start_currency_reference_scheduler():
    global currency_reference_scheduler_started
    if currency_reference_scheduler_started or not os.getenv("OPEN_EXCHANGE_RATES_APP_ID", "").strip():
        return
    currency_reference_scheduler_started = True

    def refresh_loop():
        wait_seconds = currency_reference_refresh_hours * 60 * 60
        while True:
            try:
                _refresh_currency_reference_rates()
                delay = wait_seconds
            except Exception:
                delay = min(wait_seconds, 60 * 60)
            threading.Event().wait(delay)

    threading.Thread(
        target=refresh_loop,
        name="currency-reference-refresh",
        daemon=True,
    ).start()


@router.get("/api/currencies/reference-rates")
async def get_currency_reference_rates():
    return _currency_reference_snapshot()


@router.post("/api/currencies/reference-rates/refresh")
async def refresh_currency_reference_rates():
    return await run_in_threadpool(_refresh_currency_reference_rates)


@router.get("/api/currencies")
async def list_currencies(db: Session = Depends(get_db)):
    from models import Currency
    return db.query(Currency).all()


def _serialize_currency_history(db: Session):
    from models import Currency

    output = []
    for code in ("USD", "THB", "LAK"):
        current = db.get(Currency, code)
        rows = db.query(CurrencyRateHistory).filter(
            CurrencyRateHistory.currency_code == code,
            CurrencyRateHistory.functional_currency == "VND",
            CurrencyRateHistory.is_active.is_(True),
        ).order_by(
            CurrencyRateHistory.rate_date.desc(),
            CurrencyRateHistory.id.desc(),
        ).limit(30).all()
        current_rate = float(current.exchange_rate) if current else None
        approved = next((row for row in rows if row.source == "APPROVED_UI" and float(row.rate) == current_rate), None)
        previous = next((row for row in rows if current_rate is not None and float(row.rate) != current_rate), None)
        history = []
        if current_rate is not None:
            history.append({
                "rate": current_rate,
                "rate_date": (approved.rate_date if approved else datetime.now().date()).isoformat(),
                "source": approved.source if approved else "LEGACY_CURRENT",
                "created_at": approved.created_at.isoformat() if approved and approved.created_at else None,
            })
        for row in rows:
            if approved and row.id == approved.id:
                continue
            history.append({
                "rate": float(row.rate),
                "rate_date": row.rate_date.isoformat(),
                "source": row.source,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })
        previous_rate = float(previous.rate) if previous else None
        change = current_rate - previous_rate if current_rate is not None and previous_rate is not None else None
        change_percent = change / previous_rate * 100 if change is not None and previous_rate else None
        output.append({
            "code": code,
            "current_rate": current_rate,
            "previous_rate": previous_rate,
            "change": change,
            "change_percent": change_percent,
            "source": approved.source if approved else ("LEGACY_CURRENT" if current else None),
            "applied_at": approved.created_at.isoformat() if approved and approved.created_at else None,
            "history": history,
        })
    return {"functional_currency": "VND", "currencies": output}


@router.get("/api/currencies/history")
async def list_currency_history(db: Session = Depends(get_db)):
    return _serialize_currency_history(db)


@router.post("/api/currencies")
async def save_currency_rates(data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    from models import Currency
    required_codes = ("USD", "THB", "LAK")
    parsed_rates = {}
    invalid_codes = []
    for code in required_codes:
        try:
            rate = Decimal(str(data.get(code)))
            if not rate.is_finite() or rate <= 0:
                raise ValueError
            parsed_rates[code] = rate
        except (InvalidOperation, TypeError, ValueError):
            invalid_codes.append(code)
    if invalid_codes or set(data) - set(required_codes):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_EXCHANGE_RATE",
                "message": "Tỷ giá USD, THB và LAK phải là số hợp lệ lớn hơn 0.",
                "fields": invalid_codes or sorted(set(data) - set(required_codes)),
            },
        )

    today = datetime.now().date()
    minor_units = {"VND": 0, "USD": 2, "THB": 2, "LAK": 2}
    for code, units in minor_units.items():
        definition = db.get(CurrencyDefinition, code)
        if not definition:
            db.add(CurrencyDefinition(code=code, minor_units=units, is_active=True))
    db.flush()

    for code, rate in parsed_rates.items():
        current = db.get(Currency, code)
        old_rate = Decimal(str(current.exchange_rate)) if current else None
        approved = db.query(CurrencyRateHistory).filter(
            CurrencyRateHistory.currency_code == code,
            CurrencyRateHistory.functional_currency == "VND",
            CurrencyRateHistory.rate_date == today,
            CurrencyRateHistory.source == "APPROVED_UI",
        ).first()
        previous = db.query(CurrencyRateHistory).filter(
            CurrencyRateHistory.currency_code == code,
            CurrencyRateHistory.functional_currency == "VND",
            CurrencyRateHistory.rate_date == today,
            CurrencyRateHistory.source == "PREVIOUS_UI",
        ).first()
        if old_rate is not None and old_rate != rate:
            if previous:
                previous.rate = old_rate
            else:
                db.add(CurrencyRateHistory(
                    currency_code=code,
                    functional_currency="VND",
                    rate_date=today,
                    rate=old_rate,
                    source="PREVIOUS_UI",
                    is_active=True,
                ))
        if approved:
            approved.rate = rate
            approved.is_active = True
        else:
            db.add(CurrencyRateHistory(
                currency_code=code,
                functional_currency="VND",
                rate_date=today,
                rate=rate,
                source="APPROVED_UI",
                is_active=True,
            ))
        db.merge(Currency(id=code, exchange_rate=float(rate)))
    db.commit()
    return {"message": "Đã cập nhật tỷ giá tiền tệ vào CSDL", "data": _serialize_currency_history(db)}

# 3. Customers API
