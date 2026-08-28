import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ARInvoicePostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    do_id: str = Field(min_length=1, max_length=128)
    posted_at: Optional[datetime.datetime] = None

    @field_validator("posted_at")
    @classmethod
    def require_timezone(cls, value: Optional[datetime.datetime]):
        if value is None:
            return value
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Thời điểm lập hóa đơn phải kèm múi giờ, ví dụ +07:00 hoặc Z.")
        return value.astimezone(datetime.timezone.utc)
