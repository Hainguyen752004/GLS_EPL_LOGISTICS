import datetime as dt
from typing import List, Optional

from pydantic import ConfigDict, Field

from schemas.cost import TripActualCostRequest, TripCostLineRequest


class ExpenseVoucherRequest(TripActualCostRequest):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    voucher_no: str = Field(min_length=1, max_length=128)
    voucher_date: dt.date
    do_id: Optional[str] = Field(default=None, max_length=128)
    vehicle_manager: Optional[str] = Field(default=None, max_length=255)
    payment_method: str = Field(default="cash", pattern="^(cash|bank_transfer|credit|other)$")
    contract_no: Optional[str] = Field(default=None, max_length=128)
    machine_numbers: Optional[str] = Field(default=None, max_length=500)
    checked_by: Optional[str] = Field(default=None, max_length=255)
    note: Optional[str] = Field(default=None, max_length=4000)
    lines: List[TripCostLineRequest] = Field(min_length=1, max_length=100)
