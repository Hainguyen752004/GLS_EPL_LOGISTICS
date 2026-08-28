from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ParkingListCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store_id: Optional[str] = None
    store_name: Optional[str] = None
    wave: Optional[str] = None
    gate: Optional[str] = None
    box_count: int = Field(default=1, ge=1, le=10000)


class ParkingListAutoCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    list_count: int = Field(default=1, ge=1, le=1000)


class ParkingListStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    note: Optional[str] = None


class ParkingQrScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["yard_arrival", "gate_entry", "load_package"]
    note: Optional[str] = Field(default=None, max_length=500)


class ParkingListPrintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: Literal["labels", "packing_list"]
