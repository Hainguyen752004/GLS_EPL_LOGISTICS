import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TripCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    freight_order_id: str = Field(min_length=1, max_length=128)
    trip_type: Literal["one_way", "round_trip", "backhaul", "multi_stop"]
    do_ids: list[str] = Field(min_length=1)
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None


class TripStopPlanItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence_no: int = Field(gt=0)
    stop_name: Optional[str] = Field(default=None, max_length=500)
    receiver_name: Optional[str] = Field(default=None, max_length=255)
    receiver_phone: Optional[str] = Field(default=None, max_length=64)
    delivery_note: Optional[str] = Field(default=None, max_length=1000)
    dwell_minutes: Optional[int] = Field(default=None, ge=0)


class TripFromDeliveryOrdersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    do_ids: list[str] = Field(min_length=1)
    trip_type: Literal["one_way", "round_trip", "backhaul", "multi_stop"] = "one_way"
    planned_departure_at: datetime.datetime
    avg_speed_kmh: Decimal = Field(gt=0)
    dwell_minutes: int = Field(default=0, ge=0)
    stop_plan: list[TripStopPlanItem] = Field(default_factory=list)
    return_purpose: Literal["none", "empty_return", "backhaul", "returned_goods"] = "none"
    return_route_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    return_do_id: Optional[str] = Field(default=None, min_length=1, max_length=128)

    @field_validator("planned_departure_at")
    @classmethod
    def require_timezone(cls, value: datetime.datetime) -> datetime.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Thời gian khởi hành phải kèm múi giờ, ví dụ +07:00 hoặc Z.")
        return value.astimezone(datetime.timezone.utc)

    @field_validator("do_ids")
    @classmethod
    def normalize_do_ids(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(item.strip() for item in value if isinstance(item, str) and item.strip()))
        if len(normalized) != len(value):
            raise ValueError("Danh sách DO không hợp lệ hoặc bị trùng.")
        return normalized
