import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2, ge=0)]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DeliveryCompletionPODEntry(StrictRequest):
    leg_id: str = Field(min_length=1, max_length=128)
    vehicle_id: str = Field(min_length=1, max_length=128)
    stop_no: int = Field(ge=1)
    location_text: str = Field(min_length=1, max_length=500)
    receiver_name: str = Field(min_length=1, max_length=255)
    receiver_phone: str = Field(min_length=1, max_length=50)
    delivery_time: datetime.datetime
    delivery_result: Literal["delivered_full"]
    cargo_condition: str = Field(min_length=1, max_length=1000)
    file_field: str = Field(min_length=1, max_length=255)
    signature_file_field: str = Field(min_length=1, max_length=255)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("delivery_time")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("delivery_time must include a timezone")
        return value


class DeliveryChargeAdjustmentInput(StrictRequest):
    name: str = Field(min_length=1, max_length=255)
    original_amount: Money = Decimal("0")
    actual_amount: Money
    note: str | None = Field(default=None, max_length=2000)
    # Ma costindex cua EPL — khoan khach tra them la mot dong THU can lap phieu,
    # nen no mang ma nhu dong chi phi. Tuy chon: thieu thi may chu suy tu cong
    # thuc gia thanh theo ten khoan muc.
    cost_index: str | None = Field(default=None, max_length=32)

    @computed_field
    @property
    def increase_amount(self) -> Decimal:
        return max(Decimal("0"), self.actual_amount - self.original_amount)


class DeliveryCompletionRequest(StrictRequest):
    trip_id: str = Field(min_length=1, max_length=128)
    currency_code: str = Field(min_length=3, max_length=3)
    pod_entries: list[DeliveryCompletionPODEntry] = Field(min_length=1, max_length=100)
    charge_adjustments: list[DeliveryChargeAdjustmentInput] = Field(
        default_factory=list, max_length=100
    )

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, value):
        return value.upper()

    @model_validator(mode="after")
    def validate_unique_pod_mappings(self):
        leg_ids = [entry.leg_id for entry in self.pod_entries]
        if len(leg_ids) != len(set(leg_ids)):
            raise ValueError("Each leg_id may appear only once")
        file_fields = [entry.file_field for entry in self.pod_entries]
        if len(file_fields) != len(set(file_fields)):
            raise ValueError("Each file_field must map to exactly one POD entry")
        signature_fields = [entry.signature_file_field for entry in self.pod_entries]
        if len(signature_fields) != len(set(signature_fields)):
            raise ValueError("Each signature_file_field must map to exactly one POD entry")
        if set(file_fields) & set(signature_fields):
            raise ValueError("POD and signature must use different upload fields")
        return self
