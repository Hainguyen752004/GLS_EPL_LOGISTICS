import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DeliveryPODRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trip_id: str = Field(min_length=1, max_length=128)
    leg_id: str = Field(min_length=1, max_length=128)
    vehicle_id: str = Field(min_length=1, max_length=128)
    stop_no: int = Field(ge=1)
    delivery_time: datetime.datetime
    location_text: str = Field(default="", max_length=500)
    receiver_name: str = Field(default="", max_length=255)
    receiver_phone: str = Field(default="", max_length=50)
    photo_url: str = Field(default="", max_length=2048)
    signature_url: str = Field(default="", max_length=2048)
    note: str = Field(default="", max_length=4000)
    status: Literal["completed", "rejected"] = "completed"

    @field_validator("delivery_time")
    @classmethod
    def require_timezone(cls, value: datetime.datetime) -> datetime.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Thời gian giao hàng phải kèm múi giờ, ví dụ +07:00 hoặc Z.")
        return value.astimezone(datetime.timezone.utc)

    @model_validator(mode="after")
    def require_evidence(self):
        if self.status == "completed" and not (self.photo_url.strip() or self.signature_url.strip()):
            raise ValueError("POD hoàn thành phải có ảnh hoặc chữ ký người nhận.")
        return self
