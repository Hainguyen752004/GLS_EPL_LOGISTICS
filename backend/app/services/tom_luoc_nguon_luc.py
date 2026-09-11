# -*- coding: utf-8 -*-
"""Tóm lược NGUỒN LỰC cho màn chủ: xe rảnh / đang chạy, và giấy tờ sắp chặn điều phối.

VÌ SAO LÀ MỘT ENDPOINT RIÊNG, không để giao diện tự đếm. Đội xe thật cỡ ~500 chiếc và vài
trăm tài xế. `GET /api/vehicles` phân trang tối đa 200 dòng và mỗi dòng còn chạy thêm vài
truy vấn con để suy trạng thái theo lịch, nên đếm ở trang chủ sẽ là ba lượt gọi nặng mỗi lần
mở màn — chỉ để lấy ra bốn con số. Ở đây làm ngược lại: **năm truy vấn gọn, trả về số đã
đếm**, không nhả danh sách.

VÌ SAO ĐẾM GIẤY TỜ Ở ĐÂY MỚI ĐÚNG CHỖ. Hai cửa chặn điều phối là `VEHICLE_LEGAL_EXPIRED` và
`DRIVER_LICENSE_INVALID`. Người điều độ hiện chỉ gặp chúng ĐÚNG LÚC xếp xe — tức là lúc đã
có đơn cần chạy, đã chọn xe, và không còn thời gian đi gia hạn đăng kiểm. Đếm sớm ở màn chủ
là để biết trước vài tuần.

PHÉP ĐẾM PHẢI TRÙNG VỚI PHÉP GÁC, nếu không con số này nói dối. Nên:

* Xe: lấy y nguyên ba mốc của `_require_legal_vehicle` — đăng kiểm, bảo hiểm, bảo dưỡng.
  **Thiếu ngày cũng là chặn**, không phải "chưa khai nên bỏ qua": cửa gác coi `None` là hết
  hạn, nên màn hình cũng phải coi vậy.
* Tài xế: lấy y nguyên phép kiểm `DriverQualification` — phải có bằng, `status == "active"`,
  còn hiệu lực, và `license_type` phải KHỚP hạng ghi trên hồ sơ tài xế. Một người có bằng
  hạng C còn hạn mà hồ sơ khai hạng FC thì cửa vẫn chặn, nên vẫn phải đếm là thiếu.

Trạng thái vận hành thì suy từ LỊCH, cùng quy tắc `services/lich_xe.py`, nhưng viết thành
truy vấn gộp thay vì gọi vòng cho từng chiếc.
"""
import datetime as dt

from models import (Driver, DriverQualification, ResourceAssignment, TransportTrip, Vehicle,
                    VehicleMaintenanceRequest)
from services import lich_xe

#: Ngưỡng "sắp hết hạn". 30 ngày là thời gian thực tế đủ để đặt lịch đăng kiểm hoặc đổi bằng.
SAP_HET_NGAY = 30


def _ngay(gia_tri):
    """Ngày từ chuỗi ISO, hoặc None. Cùng cách đọc với `_parse_date` của cửa gác."""
    try:
        return dt.date.fromisoformat(str(gia_tri)[:10])
    except (TypeError, ValueError):
        return None


def _xe_dang_bi_giu(db, moc):
    """Hai tập id xe: đang nằm xưởng, và đang bị một chuyến giữ — theo lịch, không theo nhãn."""
    het = moc + dt.timedelta(minutes=1)
    xuong = {x[0] for x in db.query(VehicleMaintenanceRequest.vehicle_id).filter(
        VehicleMaintenanceRequest.status.in_(lich_xe.BAO_DUONG_CHAN),
        VehicleMaintenanceRequest.planned_start < het,
        VehicleMaintenanceRequest.planned_end > moc,
    ).distinct()}
    # `phan_cong_dang_giu`: chuyến chưa xong thì xe chưa rảnh, KHÔNG nhìn giờ dự kiến — xe về
    # trễ không làm xe thành rảnh. Cộng thêm phân công đang chồng khung giờ hiện tại.
    giu = {x[0] for x in db.query(ResourceAssignment.vehicle_id)
           .join(TransportTrip, TransportTrip.id == ResourceAssignment.trip_id)
           .filter(ResourceAssignment.status.in_(lich_xe.PHAN_CONG_CON_HIEU_LUC),
                   TransportTrip.status.in_(lich_xe.CHUYEN_DANG_CHAY),
                   ResourceAssignment.vehicle_id.isnot(None)).distinct()}
    giu |= {x[0] for x in db.query(ResourceAssignment.vehicle_id).filter(
        ResourceAssignment.status.in_(lich_xe.PHAN_CONG_CON_HIEU_LUC),
        ResourceAssignment.assignment_start < het,
        ResourceAssignment.assignment_end > moc,
        ResourceAssignment.vehicle_id.isnot(None),
    ).distinct()}
    return xuong, giu


def _to_lai_dang_chay(db, moc):
    """Id những người đang bị một chuyến giữ (lái chính hoặc phụ xe)."""
    het = moc + dt.timedelta(minutes=1)
    ra = set()
    for cot in (ResourceAssignment.driver_id, ResourceAssignment.co_driver_id):
        ra |= {x[0] for x in db.query(cot)
               .join(TransportTrip, TransportTrip.id == ResourceAssignment.trip_id)
               .filter(ResourceAssignment.status.in_(lich_xe.PHAN_CONG_CON_HIEU_LUC),
                       TransportTrip.status.in_(lich_xe.CHUYEN_DANG_CHAY),
                       cot.isnot(None)).distinct()}
        ra |= {x[0] for x in db.query(cot).filter(
            ResourceAssignment.status.in_(lich_xe.PHAN_CONG_CON_HIEU_LUC),
            ResourceAssignment.assignment_start < het,
            ResourceAssignment.assignment_end > moc,
            cot.isnot(None),
        ).distinct()}
    ra.discard(None)
    return ra


def tom_luoc(db, moc=None):
    """Số đếm nguồn lực tại `moc` (mặc định: bây giờ). Không trả danh sách bản ghi."""
    moc = moc or dt.datetime.now(dt.timezone.utc)
    if moc.tzinfo is None:
        moc = moc.replace(tzinfo=dt.timezone.utc)
    hom_nay, han = moc.date(), moc.date() + dt.timedelta(days=SAP_HET_NGAY)

    xuong, giu = _xe_dang_bi_giu(db, moc)
    xe = {"tong": 0, "ranh": 0, "dang_chay": 0, "bao_duong": 0, "ngung_chay": 0,
          "giay_to_het_han": 0, "giay_to_sap_het": 0}
    sap_xe = []
    for ma, tt, dang_kiem, bao_hiem, bao_duong in db.query(
            Vehicle.id, Vehicle.operational_status, Vehicle.inspection_exp,
            Vehicle.insurance_date, Vehicle.maintenance_date):
        xe["tong"] += 1
        if (tt or "") == "out_of_service":
            xe["ngung_chay"] += 1
        elif ma in xuong:
            xe["bao_duong"] += 1
        elif ma in giu:
            xe["dang_chay"] += 1
        else:
            xe["ranh"] += 1
        # Ba mốc của `_require_legal_vehicle`. Thiếu ngày cũng là chặn, y như cửa gác.
        moc_giay = [_ngay(dang_kiem), _ngay(bao_hiem), _ngay(bao_duong)]
        if any(d is None or d < hom_nay for d in moc_giay):
            xe["giay_to_het_han"] += 1
        elif min(moc_giay) <= han:
            xe["giay_to_sap_het"] += 1
            sap_xe.append({"id": ma, "het_han": min(moc_giay).isoformat(),
                           "con_ngay": (min(moc_giay) - hom_nay).days})

    # `driver_qualifications.driver_id` là khoá chính nên mỗi người nhiều nhất một dòng —
    # đúng dòng mà cửa gác đọc bằng `.first()`.
    bang = {q.driver_id: q for q in db.query(DriverQualification)}
    dang_chay = _to_lai_dang_chay(db, moc)
    tx = {"tong": 0, "ranh": 0, "dang_chay": 0, "nghi": 0, "bang_het_han": 0, "bang_sap_het": 0}
    sap_tx = []
    for ma, ten, tt, hang in db.query(Driver.id, Driver.name, Driver.operational_status,
                                      Driver.license_type):
        tx["tong"] += 1
        if (tt or "") in ("inactive", "off_duty"):
            tx["nghi"] += 1
        elif ma in dang_chay:
            tx["dang_chay"] += 1
        else:
            tx["ranh"] += 1
        q = bang.get(ma)
        den = _ngay(q.valid_to) if q is not None else None
        tu = _ngay(q.valid_from) if q is not None else None
        hop = (q is not None and q.status == "active" and den is not None and tu is not None
               and tu <= hom_nay and den >= hom_nay and q.license_type == hang)
        if not hop:
            tx["bang_het_han"] += 1
        elif den <= han:
            tx["bang_sap_het"] += 1
            sap_tx.append({"id": ma, "name": ten, "het_han": den.isoformat(),
                           "con_ngay": (den - hom_nay).days})

    sap_xe.sort(key=lambda x: x["con_ngay"])
    sap_tx.sort(key=lambda x: x["con_ngay"])
    return {
        "as_of": moc.isoformat(),
        "warn_within_days": SAP_HET_NGAY,
        "vehicles": xe,
        "drivers": tx,
        # Vài dòng đầu để màn chủ chỉ được đích danh chiếc nào / ai, khỏi phải mở màn khác.
        "vehicles_expiring_soon": sap_xe[:5],
        "drivers_expiring_soon": sap_tx[:5],
    }
