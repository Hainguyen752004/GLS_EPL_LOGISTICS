import datetime

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TripDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vehicle_id: str = Field(min_length=1, max_length=128)
    driver_id: str = Field(min_length=1, max_length=128)
    co_driver_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    expected_version: int = Field(ge=1)
    assignment_start: datetime.datetime
    assignment_end: datetime.datetime

    @field_validator("assignment_start", "assignment_end")
    @classmethod
    def require_timezone(cls, value: datetime.datetime) -> datetime.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Thời gian điều phối phải kèm múi giờ, ví dụ +07:00 hoặc Z.")
        return value.astimezone(datetime.timezone.utc)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.assignment_start >= self.assignment_end:
            raise ValueError("Thời gian kết thúc điều phối phải sau thời gian bắt đầu.")
        if self.co_driver_id and self.co_driver_id == self.driver_id:
            raise ValueError("Tài xế chính và phụ xe phải là hai người khác nhau.")
        return self
