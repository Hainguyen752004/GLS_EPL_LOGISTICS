from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TripCostLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: Optional[str] = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=500)
    original_amount: Decimal = Field(ge=0, max_digits=24, decimal_places=6)
    actual_amount: Decimal = Field(ge=0, max_digits=24, decimal_places=6)
    note: Optional[str] = Field(default=None, max_length=2000)
    # Ma costindex cua EPL. Tuy chon: man khong gui thi may chu tu suy tu cong
    # thuc gia thanh cua loai xe dang chay chuyen — ma phai co san o dong chi
    # phi, khong duoc phu thuoc vao viec giao dien co nho gui hay khong.
    cost_index: Optional[str] = Field(default=None, max_length=32)
    charge_type: Optional[str] = Field(default=None, max_length=32)
    key: Optional[str] = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def actual_must_not_be_below_original(self):
        if self.actual_amount < self.original_amount:
            raise ValueError("Giá thực tế không được nhỏ hơn giá ban đầu.")
        return self


class TripActualCostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: Optional[str] = Field(default=None, max_length=128)
    currency_code: str = Field(default="VND", min_length=3, max_length=3)
    carrier_id: Optional[str] = Field(default=None, max_length=128)
    lines: List[TripCostLineRequest] = Field(min_length=1, max_length=100)
