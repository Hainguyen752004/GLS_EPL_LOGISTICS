import datetime
from typing import Optional, Union, List

from pydantic import BaseModel, ConfigDict, field_validator


Number = Union[int, float]
DO_OPERATIONAL_DATETIME_FIELDS = (
    "pickup_window_start", "pickup_window_end",
    "delivery_window_start", "delivery_window_end",
    "pickup_date", "delivery_date",
)


def _aware_utc_iso(value):
    if value is None or value == "":
        return value
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Thời gian phải đúng định dạng ISO 8601 và kèm múi giờ.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Thời gian phải kèm múi giờ, ví dụ +07:00 hoặc Z.")
    return parsed.astimezone(datetime.timezone.utc).isoformat()


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuotationCreateRequest(StrictRequest):
    id: Optional[str] = None
    customer_id: str
    route_id: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    pickup_window_start: Optional[str] = None
    pickup_window_end: Optional[str] = None
    delivery_window_start: Optional[str] = None
    delivery_window_end: Optional[str] = None
    weight_kg: Optional[Number] = None
    pallet_count: Optional[int] = None
    cargo_type: Optional[str] = None
    valid_to: Optional[str] = None
    fuel_cost: Optional[Number] = None
    driver_cost: Optional[Number] = None
    toll_fee: Optional[Number] = None
    total_cost: Optional[Number] = None
    selling_price: Optional[Number] = None
    packaging_spec: Optional[str] = None
    volume_m3: Optional[Number] = None


class QuotationUpdateRequest(QuotationCreateRequest):
    customer_id: Optional[str] = None
    route_id: Optional[str] = None


class SalesOrderLineRequest(StrictRequest):
    """Mot dong hang hoa van chuyen.

    `uom` vua quyet dinh cach tinh cuoc, vua duoc quy doi ra khoi luong / the
    tich de chan dieu xe qua tai.
    """
    description: Optional[str] = None
    quantity: Optional[Number] = None
    uom: Optional[str] = None
    unit_price: Optional[Number] = None


class SalesOrderCreateRequest(StrictRequest):
    id: Optional[str] = None
    quotation_id: str
    route_id: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    pickup_window_start: Optional[str] = None
    pickup_window_end: Optional[str] = None
    delivery_window_start: Optional[str] = None
    delivery_window_end: Optional[str] = None
    weight_kg: Optional[Number] = None
    pallet_count: Optional[int] = None
    total_amount: Optional[Number] = None
    order_date: Optional[str] = None
    currency_code: Optional[str] = None
    lines: Optional[List[SalesOrderLineRequest]] = None
    packaging_spec: Optional[str] = None
    volume_m3: Optional[Number] = None


class SalesOrderUpdateRequest(StrictRequest):
    route_id: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    pickup_window_start: Optional[str] = None
    pickup_window_end: Optional[str] = None
    delivery_window_start: Optional[str] = None
    delivery_window_end: Optional[str] = None
    weight_kg: Optional[Number] = None
    pallet_count: Optional[int] = None
    total_amount: Optional[Number] = None
    currency_code: Optional[str] = None
    packaging_spec: Optional[str] = None
    volume_m3: Optional[Number] = None
    lines: Optional[List[SalesOrderLineRequest]] = None


class WorkflowStatusRequest(StrictRequest):
    status: str


class RouteCreateRequest(StrictRequest):
    id: Optional[str] = None
    name: Optional[str] = None
    distance_km: Optional[Number] = None
    segments_json: Optional[str] = None


class DeliveryOrderCreateRequest(StrictRequest):
    id: Optional[str] = None
    so_id: str
    route_id: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    pickup_window_start: Optional[str] = None
    pickup_window_end: Optional[str] = None
    delivery_window_start: Optional[str] = None
    delivery_window_end: Optional[str] = None
    pickup_date: Optional[str] = None
    delivery_date: Optional[str] = None
    weight_kg: Optional[Number] = None
    pallet_count: Optional[int] = None

    _validate_operational_datetimes = field_validator(
        *DO_OPERATIONAL_DATETIME_FIELDS, mode="before"
    )(_aware_utc_iso)


class DeliveryOrderUpdateRequest(StrictRequest):
    route_id: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    pickup_window_start: Optional[str] = None
    pickup_window_end: Optional[str] = None
    delivery_window_start: Optional[str] = None
    delivery_window_end: Optional[str] = None
    pickup_date: Optional[str] = None
    delivery_date: Optional[str] = None
    weight_kg: Optional[Number] = None
    pallet_count: Optional[int] = None
    packaging_spec: Optional[str] = None
    volume_m3: Optional[Number] = None

    _validate_operational_datetimes = field_validator(
        *DO_OPERATIONAL_DATETIME_FIELDS, mode="before"
    )(_aware_utc_iso)


class DeliveryOrderStatusRequest(StrictRequest):
    status: str


class DeliveryOrderDispatchRequest(StrictRequest):
    vehicle_id: str
    driver_id: str
    co_driver_id: Optional[str] = None
    packaging_spec: Optional[str] = None
    volume_m3: Optional[Number] = None
    departure_at: Optional[str] = None
    planned_departure_at: Optional[str] = None
    avg_speed_kmh: Optional[Number] = None
    max_speed_kmh: Optional[Number] = None
    return_speed_kmh: Optional[Number] = None
    return_distance_km: Optional[Number] = None
    load_minutes: Optional[int] = None
    unload_minutes: Optional[int] = None

    _validate_departure_datetimes = field_validator(
        "departure_at", "planned_departure_at", mode="before"
    )(_aware_utc_iso)
