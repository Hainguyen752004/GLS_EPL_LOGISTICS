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
    # `total_cost` la tien CHI ra, `selling_price` la cuoc THU cua khach - hai
    # con so khac nhau, khong duoc cong chung. Man bao gia truoc day cong ca nam
    # cau phan vao mot so, nen no khong phai gia thanh cung khong phai gia ban.
    #
    # CO Y khong co `margin_pct`: bang quotations khong co cot do, va ti le loi
    # nhuan suy ra duoc tu hai con so tren. Luu them mot cot thu ba la tao ra
    # ba con so co the troi khoi nhau.
    # O Ghi chu tren man hinh. Truoc day khong bang nao co cot de chua va
    # khong payload nao gui len, nen go xong bam Luu la mat khong mot loi nao.
    notes: Optional[str] = None
    packaging_spec: Optional[str] = None
    volume_m3: Optional[Number] = None
    carrier_name: Optional[str] = None
    delivery_method: Optional[str] = None
    seal_weight: Optional[str] = None
    temperature_requirement: Optional[str] = None
    cargo_insurance: Optional[str] = None
    warehouse_owner: Optional[str] = None

    # ------------------------------------------------------------------
    # Truong cua ban thiet ke bao gia moi (SPEC-quotation-page.md).
    #
    # `model_config` cua `StrictRequest` la `extra="forbid"`, nen mot truong
    # khong khai o day thi may chu tra 422 chu khong lang le bo qua. Do la cach
    # dung: mot o nguoi dung go xong bam Luu roi mat khong mot loi nao la thu
    # kho phat hien nhat. Nhung no cung co nghia la MOI o cua man hinh phai co
    # ten trong danh sach nay.
    #
    # `unit_price` + `price_basis` la doi gia THAT ma khach doc; `selling_price`
    # duoc may chu SUY RA tu hai cai do (xem `workflow_service`), nen giao dien
    # khong tu tinh va hai cot khong troi khoi nhau.
    # ------------------------------------------------------------------
    vehicle_type_id: Optional[str] = None
    price_basis: Optional[str] = None
    unit_price: Optional[Number] = None
    min_qty_per_trip: Optional[Number] = None
    currency_code: Optional[str] = None
    fx_rate: Optional[Number] = None
    payment_terms: Optional[str] = None
    waiting_surcharge: Optional[Number] = None
    sales_rep: Optional[str] = None
    trips_per_month: Optional[int] = None
    cargo_value: Optional[Number] = None
    stacking: Optional[str] = None
    sealing: Optional[str] = None
    recipient_contact: Optional[str] = None
    notes_customer: Optional[str] = None
    notes_ops: Optional[str] = None
    notes_internal: Optional[str] = None
    target_margin: Optional[Number] = None
    competitor_price: Optional[Number] = None
    discount_percent: Optional[Number] = None


class QuotationUpdateRequest(QuotationCreateRequest):
    customer_id: Optional[str] = None
    route_id: Optional[str] = None


class WorkflowStatusRequest(StrictRequest):
    status: str


class RouteCreateRequest(StrictRequest):
    id: Optional[str] = None
    name: Optional[str] = None
    distance_km: Optional[Number] = None
    segments_json: Optional[str] = None


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
    # O Ghi chu tren man hinh. Truoc day khong bang nao co cot de chua va
    # khong payload nao gui len, nen go xong bam Luu la mat khong mot loi nao.
    notes: Optional[str] = None
    packaging_spec: Optional[str] = None
    # So niem phong thuc te chi biet duoc LUC KEP CHI o kho, tuc sau khi don da
    # tao — nen phai sua duoc ve sau, khong chi khai luc tao.
    seal_no: Optional[str] = None
    volume_m3: Optional[Number] = None

    _validate_operational_datetimes = field_validator(
        *DO_OPERATIONAL_DATETIME_FIELDS, mode="before"
    )(_aware_utc_iso)


class DeliveryOrderStatusRequest(StrictRequest):
    status: str
    # Ly do — bat buoc khi status = cancelled (may chu kiem), tuy chon cho cac chuyen khac.
    reason: Optional[str] = None


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
