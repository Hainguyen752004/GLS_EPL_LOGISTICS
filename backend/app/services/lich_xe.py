# -*- coding: utf-8 -*-
"""Xe và tổ lái có rảnh trong một khung giờ hay không — hỏi LỊCH, không đọc nhãn.

VÌ SAO CÓ TỆP NÀY. Trước đây điều kiện điều phối được quyết bằng cách **so chuỗi
nhãn tiếng Việt**:

    READY_VEHICLE = "Sẵn sàng"
    if vehicle.status != READY_VEHICLE: ...            # tms_dispatch_service
    READY_DRIVER_STATUS = "🟢 Rảnh (Sẵn sàng)"
    busy_markers = ("ban", "dang theo xe", "dang thuc hien", ...)  # crew_policy

Ba điều sai với cách đó, và cả ba đã đo được:

1. **Nhãn là dữ liệu hiển thị, không phải sự thật.** Sửa một nhãn trong Master
   Data — đổi "Sẵn sàng" thành "Sẵn sàng chạy" chẳng hạn — là mọi xe thành không
   bao giờ điều được. Dự án này chạy cho một bản **tiếng Lào**; ở đó không một
   chuỗi nào trong danh sách trên khớp.
2. **Nhãn không có chiều thời gian.** "Sẵn sàng" không trả lời được câu hỏi thật
   của người điều phối: *xe này có rảnh SÁNG MAI TỪ 6H ĐẾN 14H không?* Một xe
   đang chạy hôm nay vẫn rảnh ngày mai; một xe rảnh hôm nay có thể đã bị đặt cho
   chuyến chiều mai. Cửa theo nhãn trả lời sai cả hai chiều.
3. **Nhãn trôi khỏi sự thật.** Một đường ghi cũ đặt `status = "Đang thực hiện X"`
   rồi không có đường nào trả lại, thì chiếc xe đó bị loại khỏi đội vĩnh viễn dù
   không có phân công nào đang mở.

BA NGUỒN THẬT, đều đã có sẵn trong cơ sở dữ liệu và đều có chiều thời gian:

  · `resource_assignments` — phân công đang mở: xe/tài xế đang thuộc chuyến nào,
    từ giờ nào tới giờ nào.
  · `vehicle_maintenance_requests` — xe nằm xưởng (đã duyệt / đang làm).
  · `driver_shift_assignments` — ca làm việc của tổ lái, kèm loại ca (làm / nghỉ).

Nhãn `vehicles.status` và `drivers.status` **vẫn được ghi** để màn hình đọc cho
nhanh, nhưng không còn một cửa nào quyết định dựa vào chúng.
"""
import datetime as dt

from sqlalchemy import or_

from models import (Driver, DriverShiftAssignment, ResourceAssignment,
                    TransportTrip, Vehicle, VehicleMaintenanceRequest)
from services.errors import DomainError, conflict

#: Phân công còn hiệu lực. `completed` là chuyến đã xong, `cancelled` là chuyến
#: đã huỷ — cả hai đều không giữ xe nữa.
PHAN_CONG_CON_HIEU_LUC = ("active",)

#: Lịch xưởng CHẶN điều phối. `requested` chưa chặn: nó chỉ là một đề nghị.
BAO_DUONG_CHAN = ("approved", "in_progress")


def _utc(gia_tri):
    if gia_tri is None:
        return None
    if isinstance(gia_tri, dt.datetime):
        return gia_tri if gia_tri.tzinfo else gia_tri.replace(tzinfo=dt.timezone.utc)
    return dt.datetime.fromisoformat(str(gia_tri)).replace(tzinfo=dt.timezone.utc) \
        if "+" not in str(gia_tri) and "Z" not in str(gia_tri) \
        else dt.datetime.fromisoformat(str(gia_tri).replace("Z", "+00:00"))


def phan_cong_chong_lich(db, start_at, end_at, vehicle_id=None, crew_ids=(),
                         bo_qua_trip=None):
    """Phân công đang mở nào chồng khung `[start_at, end_at)` của xe / tổ lái này.

    Trả về bản ghi `ResourceAssignment` đầu tiên tìm thấy, hoặc `None`.

    `bo_qua_trip` để bỏ chính chuyến đang xử lý ra khỏi phép so — dùng khi đổi
    xe cho một chuyến đã điều: phân công cũ của chính nó không phải xung đột.
    """
    start_at, end_at = _utc(start_at), _utc(end_at)
    if start_at is None or end_at is None:
        raise DomainError("ASSIGNMENT_WINDOW_REQUIRED",
                          "Thiếu khung giờ để kiểm lịch xe và tổ lái.", 422)
    dieu_kien = []
    if vehicle_id:
        dieu_kien.append(ResourceAssignment.vehicle_id == vehicle_id)
    ds_to_lai = [x for x in (crew_ids or []) if x]
    if ds_to_lai:
        dieu_kien.append(ResourceAssignment.driver_id.in_(ds_to_lai))
        dieu_kien.append(ResourceAssignment.co_driver_id.in_(ds_to_lai))
    if not dieu_kien:
        return None
    truy_van = db.query(ResourceAssignment).filter(
        ResourceAssignment.status.in_(PHAN_CONG_CON_HIEU_LUC),
        ResourceAssignment.assignment_start < end_at,
        ResourceAssignment.assignment_end > start_at,
        or_(*dieu_kien),
    )
    if bo_qua_trip:
        truy_van = truy_van.filter(or_(ResourceAssignment.trip_id.is_(None),
                                       ResourceAssignment.trip_id != bo_qua_trip))
    return truy_van.first()


#: Chuyen con DANG CHAY — phan cong tren no giu xe bat ke gio du kien.
CHUYEN_DANG_CHAY = ("dispatched", "in_transit")


def phan_cong_dang_giu(db, vehicle_id=None, crew_ids=(), bo_qua_trip=None):
    """Phan cong DANG GIU xe / to lai: con `active` VA chuyen cua no chua xong.

    KHAC voi `phan_cong_chong_lich`, ham nay KHONG nhin gio du kien. Ly do do
    duoc tren du lieu that: sau mot dem, 6 chuyen van `in_transit` nhung khung
    gio du kien cua phan cong da troi qua, nen phep hoi "bay gio xe co ranh
    khong" tra loi RANH cho ca 6 xe — trong khi xe van dang tren duong. Xe ve
    tre khong lam xe thanh ranh; chi hoan tat / xe-ve-bai / huy chuyen moi
    tra xe. Phan cong khong gan chuyen (duong lenh van chuyen cu) van theo gio.
    """
    dieu_kien = []
    if vehicle_id:
        dieu_kien.append(ResourceAssignment.vehicle_id == vehicle_id)
    ds = [x for x in (crew_ids or []) if x]
    if ds:
        dieu_kien.append(ResourceAssignment.driver_id.in_(ds))
        dieu_kien.append(ResourceAssignment.co_driver_id.in_(ds))
    if not dieu_kien:
        return None
    truy_van = (db.query(ResourceAssignment)
                .join(TransportTrip, TransportTrip.id == ResourceAssignment.trip_id)
                .filter(ResourceAssignment.status.in_(PHAN_CONG_CON_HIEU_LUC),
                        TransportTrip.status.in_(CHUYEN_DANG_CHAY),
                        or_(*dieu_kien)))
    if bo_qua_trip:
        truy_van = truy_van.filter(ResourceAssignment.trip_id != bo_qua_trip)
    return truy_van.first()


def bao_duong_chong_lich(db, vehicle_id, start_at, end_at):
    """Phiếu xưởng đã duyệt / đang làm nào chồng khung giờ này."""
    if not vehicle_id:
        return None
    start_at, end_at = _utc(start_at), _utc(end_at)
    return db.query(VehicleMaintenanceRequest).filter(
        VehicleMaintenanceRequest.vehicle_id == vehicle_id,
        VehicleMaintenanceRequest.status.in_(BAO_DUONG_CHAN),
        VehicleMaintenanceRequest.planned_start < end_at,
        VehicleMaintenanceRequest.planned_end > start_at,
    ).first()


def kiem_xe_ranh(db, vehicle_id, start_at, end_at, bo_qua_trip=None):
    """Ném lỗi nếu xe KHÔNG rảnh trong khung giờ này, kèm lý do cụ thể.

    Thứ tự hai phép kiểm có chủ ý: **xưởng trước, chuyến sau**. Một chiếc đang
    nằm xưởng thì người điều phối cần biết ngay là phải đổi xe; nói "đang chạy
    chuyến khác" trước rồi mới nói "à mà nó cũng đang sửa" là bắt họ thử hai lần.
    """
    xe = db.get(Vehicle, vehicle_id) if vehicle_id else None
    if xe is not None and (xe.operational_status or "") == "out_of_service":
        raise conflict(
            "VEHICLE_OUT_OF_SERVICE",
            "Xe %s đã được đưa ra khỏi đội%s — đưa lại hoạt động ở Dữ liệu gốc trước khi điều."
            % (vehicle_id, (" (%s)" % xe.operational_note) if xe.operational_note else ""),
            ["master-data/vehicles"],
        )
    phieu = bao_duong_chong_lich(db, vehicle_id, start_at, end_at)
    if phieu is not None:
        raise conflict(
            "VEHICLE_MAINTENANCE_OVERLAP",
            "Xe %s có lịch xưởng (%s) trùng khung giờ điều phối — chọn xe khác "
            "hoặc dời lịch xưởng." % (vehicle_id, phieu.request_no or phieu.id),
            ["master-data/vehicles"],
        )
    dang_giu = phan_cong_dang_giu(db, vehicle_id=vehicle_id, bo_qua_trip=bo_qua_trip)
    if dang_giu is not None:
        raise conflict(
            "RESOURCE_BUSY",
            "Xe %s đang chạy %s (chuyến chưa hoàn tất) — hoàn tất, xác nhận xe về bãi "
            "hoặc huỷ chuyến đó trước." % (vehicle_id, dang_giu.trip_id),
            ["dispatch"],
        )
    phan_cong = phan_cong_chong_lich(db, start_at, end_at, vehicle_id=vehicle_id,
                                    bo_qua_trip=bo_qua_trip)
    if phan_cong is not None:
        raise conflict(
            "RESOURCE_TIME_OVERLAP",
            "Xe %s đã được phân cho %s trong khung giờ này." % (
                vehicle_id, phan_cong.trip_id or phan_cong.freight_order_id),
            ["dispatch"],
        )


def kiem_to_lai_ranh(db, crew_ids, start_at, end_at, bo_qua_trip=None):
    """Ném lỗi nếu một người trong tổ lái KHÔNG rảnh trong khung giờ này.

    Hai phép kiểm, và cả hai đọc lịch thật:

      1. **Ca làm việc phải phủ trọn khung**, và không có ca nghỉ chen vào. Đây
         là quy tắc lao động, không phải một cờ trạng thái.
      2. **Không có phân công đang mở nào chồng khung.**
    """
    ds = [x for x in (crew_ids or []) if x]
    if not ds:
        return
    start_at, end_at = _utc(start_at), _utc(end_at)
    for ma in ds:
        nguoi = db.get(Driver, ma)
        if nguoi is not None and (nguoi.operational_status or "") in ("inactive", "off_duty"):
            raise conflict(
                "DRIVER_UNAVAILABLE",
                "Nhân sự %s đang %s%s — không điều được."
                % (ma, "nghỉ việc" if nguoi.operational_status == "inactive" else "nghỉ phép",
                   (" (%s)" % nguoi.operational_note) if nguoi.operational_note else ""),
                ["master-data/drivers"],
            )
        cac_ca = db.query(DriverShiftAssignment).filter(
            DriverShiftAssignment.status.in_(("planned", "confirmed")),
            DriverShiftAssignment.driver_id == ma,
            DriverShiftAssignment.shift_start < end_at,
            DriverShiftAssignment.shift_end > start_at,
        ).order_by(DriverShiftAssignment.shift_start,
                   DriverShiftAssignment.shift_end).all()
        if any((ca.availability_kind or "work") != "work" for ca in cac_ca):
            raise conflict(
                "DRIVER_UNAVAILABLE",
                "Nhân sự %s đang nghỉ hoặc không sẵn sàng trong thời gian chuyến." % ma,
                ["master-data/drivers"],
            )
        moc = start_at
        for ca in (x for x in cac_ca if (x.availability_kind or "work") == "work"):
            dau, cuoi = _utc(ca.shift_start), _utc(ca.shift_end)
            if dau > moc:
                break
            if cuoi > moc:
                moc = cuoi
            if moc >= end_at:
                break
        if moc < end_at:
            raise conflict(
                "DRIVER_WORK_SCHEDULE_REQUIRED",
                "Nhân sự %s chưa có lịch làm việc bao phủ toàn bộ thời gian chuyến." % ma,
                ["master-data/drivers"],
            )
    dang_giu = phan_cong_dang_giu(db, crew_ids=ds, bo_qua_trip=bo_qua_trip)
    if dang_giu is not None:
        raise conflict(
            "RESOURCE_BUSY",
            "Tài xế hoặc phụ xe đang chạy %s (chuyến chưa hoàn tất) — không điều thêm được."
            % dang_giu.trip_id,
            ["dispatch"],
        )
    phan_cong = phan_cong_chong_lich(db, start_at, end_at, crew_ids=ds,
                                     bo_qua_trip=bo_qua_trip)
    if phan_cong is not None:
        raise conflict(
            "RESOURCE_TIME_OVERLAP",
            "Tài xế hoặc phụ xe đã được phân cho %s trong khung giờ này." % (
                phan_cong.trip_id or phan_cong.freight_order_id),
            ["dispatch"],
        )


# ===========================================================================
# TRANG THAI VAN HANH — MA CHUAN, luu trong cot rieng (moc 045)
# ===========================================================================
#
# Nhan chu (`vehicles.status`, `drivers.status`) chi la BAN CHIEU cua ma nay,
# giu cho nhung cho hien thi chua doi. Khong cho nao quyet dinh dua vao nhan.

XE_TRANG_THAI = ("available", "on_trip", "maintenance", "out_of_service")
TAI_XE_TRANG_THAI = ("available", "on_trip", "off_duty", "inactive")

#: Trang thai nguoi dung DAT TAY duoc. `on_trip` va `maintenance` thi khong —
#: chung den tu lich (phan cong, phieu xuong), dat tay la noi doi lich.
XE_DAT_TAY = ("available", "out_of_service")
TAI_XE_DAT_TAY = ("available", "off_duty", "inactive")

#: Ban chieu sang nhan chu cu — CHI de hien o cho chua doi sang lang.json.
NHAN_XE = {
    "available": "Sẵn sàng",
    "on_trip": "Đang thực hiện %s",
    "maintenance": "Bảo dưỡng %s",
    "out_of_service": "Ngưng hoạt động",
}
NHAN_TAI_XE = {
    "available": "🟢 Rảnh (Sẵn sàng)",
    "on_trip": "Đang thực hiện %s",
    "off_duty": "Nghỉ phép",
    "inactive": "Nghỉ việc",
}


def _nhan(bang, ma, ref):
    mau = bang.get(ma, ma)
    return mau % (ref or "") if "%s" in mau else mau


def trang_thai_xe_theo_lich(db, xe, moc=None):
    """Ma trang thai cua mot xe tai `moc`, tinh tu LICH — khong doc nhan.

    Thu tu uu tien co chu y: **dat tay thang lich**. Mot chiec da bi dua ra khoi
    doi (`out_of_service`) thi du lich con phan cong cu cung khong duoc coi la
    "dang chay" — nguoi quan ly doi xe vua noi no khong chay nua.
    Tra ve (ma, ref).
    """
    if (xe.operational_status or "") == "out_of_service":
        return "out_of_service", None
    moc = _utc(moc) or dt.datetime.now(dt.timezone.utc)
    ket_thuc = moc + dt.timedelta(minutes=1)
    phieu = bao_duong_chong_lich(db, xe.id, moc, ket_thuc)
    if phieu is not None:
        return "maintenance", str(phieu.request_no or phieu.id)
    giu = phan_cong_dang_giu(db, vehicle_id=xe.id)
    if giu is not None:
        return "on_trip", str(giu.trip_id)
    phan_cong = phan_cong_chong_lich(db, moc, ket_thuc, vehicle_id=xe.id)
    if phan_cong is not None:
        return "on_trip", str(phan_cong.trip_id or phan_cong.freight_order_id)
    return "available", None


def trang_thai_tai_xe_theo_lich(db, nguoi, moc=None):
    """Ma trang thai cua mot tai xe tai `moc`, tinh tu LICH. Tra ve (ma, ref)."""
    hien = nguoi.operational_status or ""
    if hien in ("inactive", "off_duty"):
        # Dat tay thang lich, cung ly do voi xe.
        return hien, None
    moc = _utc(moc) or dt.datetime.now(dt.timezone.utc)
    ket_thuc = moc + dt.timedelta(minutes=1)
    giu = phan_cong_dang_giu(db, crew_ids=[nguoi.id])
    if giu is not None:
        return "on_trip", str(giu.trip_id)
    phan_cong = phan_cong_chong_lich(db, moc, ket_thuc, crew_ids=[nguoi.id])
    if phan_cong is not None:
        return "on_trip", str(phan_cong.trip_id or phan_cong.freight_order_id)
    return "available", None


def dong_bo_trang_thai_theo_lich(db, vehicle_id=None, crew_ids=(), moc=None):
    """Ghi lai MA trang thai (va nhan chieu) cua xe / to lai cho DUNG voi lich.

    Goi sau moi lan lich doi: dieu xe, xe ve bai, huy chuyen, hoan tat giao. Ma
    la thu man hinh doc; lich la thu quyet. Ham nay giu hai ben khop nhau.
    """
    bay_gio = dt.datetime.now(dt.timezone.utc)
    if vehicle_id:
        xe = db.get(Vehicle, vehicle_id)
        if xe is not None:
            ma, ref = trang_thai_xe_theo_lich(db, xe, moc)
            xe.operational_status = ma
            xe.operational_ref = ref
            xe.operational_updated_at = bay_gio
            xe.status = _nhan(NHAN_XE, ma, ref)
    for ma_nguoi in [x for x in (crew_ids or []) if x]:
        nguoi = db.get(Driver, ma_nguoi)
        if nguoi is None:
            continue
        ma, ref = trang_thai_tai_xe_theo_lich(db, nguoi, moc)
        nguoi.operational_status = ma
        nguoi.operational_ref = ref
        nguoi.operational_updated_at = bay_gio
        nguoi.status = _nhan(NHAN_TAI_XE, ma, ref)
        if ma == "on_trip":
            pc = phan_cong_dang_giu(db, crew_ids=[ma_nguoi]) or phan_cong_chong_lich(
                db, _utc(moc) or bay_gio, (_utc(moc) or bay_gio) + dt.timedelta(minutes=1),
                crew_ids=[ma_nguoi])
            nguoi.assigned_vehicle = pc.vehicle_id if pc is not None else nguoi.assigned_vehicle
        else:
            nguoi.assigned_vehicle = "Chưa gán"


# Ten cu, giu cho cho da goi.
dong_bo_nhan_theo_lich = dong_bo_trang_thai_theo_lich


def dat_trang_thai_xe(db, vehicle_id, trang_thai, ghi_chu="", actor="system"):
    """Nguoi dung DAT TAY trang thai xe: dua ra khoi doi, hoac dua lai.

    Chi nhan `available` / `out_of_service`. `on_trip` va `maintenance` la thu
    lich noi, dat tay la noi doi lich — tu choi 422 va chi sang dung man.
    Dua lai (`available`) thi KHONG ghi cung "available": tinh lai tu lich, vi
    xe co the dang co phan cong.
    """
    xe = db.query(Vehicle).filter(Vehicle.id == vehicle_id).with_for_update().first()
    if xe is None:
        raise DomainError("VEHICLE_NOT_FOUND", "Không tìm thấy xe %s." % vehicle_id, 404)
    if trang_thai not in XE_DAT_TAY:
        raise DomainError(
            "OPERATIONAL_STATUS_NOT_MANUAL",
            "Trạng thái \"%s\" do lịch quyết định (phân công / phiếu xưởng), không đặt tay được. "
            "Đặt tay chỉ nhận: %s." % (trang_thai, ", ".join(XE_DAT_TAY)), 422,
            ["dispatch", "master-data/vehicles"])
    if trang_thai == "out_of_service":
        # Khong dua ra khoi doi mot xe dang CHAY chuyen: phai huy / hoan tat
        # chuyen truoc, khong thi chuyen do mat xe giua duong.
        pc = phan_cong_dang_giu(db, vehicle_id=xe.id)
        if pc is not None:
            raise conflict(
                "VEHICLE_ON_TRIP",
                "Xe %s đang chạy %s — huỷ hoặc hoàn tất chuyến đó trước khi đưa xe ra khỏi đội."
                % (xe.id, pc.trip_id or pc.freight_order_id), ["dispatch"])
        if not str(ghi_chu or "").strip():
            raise DomainError("OPERATIONAL_NOTE_REQUIRED",
                              "Phải ghi lý do đưa xe ra khỏi đội.", 422)
        xe.operational_status = "out_of_service"
        xe.operational_ref = None
        xe.operational_note = str(ghi_chu).strip()
        xe.operational_updated_at = dt.datetime.now(dt.timezone.utc)
        xe.status = _nhan(NHAN_XE, "out_of_service", None)
        return xe
    # available: xoa dat tay roi tinh lai tu lich.
    xe.operational_status = "available"
    xe.operational_note = str(ghi_chu or "").strip() or None
    dong_bo_trang_thai_theo_lich(db, vehicle_id=xe.id)
    return xe


def dat_trang_thai_tai_xe(db, driver_id, trang_thai, ghi_chu="", actor="system"):
    """Nguoi dung DAT TAY trang thai tai xe: nghi phep, nghi viec, hoac lam lai."""
    nguoi = db.query(Driver).filter(Driver.id == driver_id).with_for_update().first()
    if nguoi is None:
        raise DomainError("DRIVER_NOT_FOUND", "Không tìm thấy nhân sự %s." % driver_id, 404)
    if trang_thai not in TAI_XE_DAT_TAY:
        raise DomainError(
            "OPERATIONAL_STATUS_NOT_MANUAL",
            "Trạng thái \"%s\" do lịch quyết định, không đặt tay được. Đặt tay chỉ nhận: %s."
            % (trang_thai, ", ".join(TAI_XE_DAT_TAY)), 422, ["master-data/drivers"])
    if trang_thai in ("off_duty", "inactive"):
        pc = phan_cong_dang_giu(db, crew_ids=[nguoi.id])
        if pc is not None:
            raise conflict(
                "DRIVER_ON_TRIP",
                "Nhân sự %s đang chạy %s — huỷ hoặc hoàn tất chuyến đó trước."
                % (nguoi.id, pc.trip_id or pc.freight_order_id), ["dispatch"])
        if trang_thai == "inactive" and not str(ghi_chu or "").strip():
            raise DomainError("OPERATIONAL_NOTE_REQUIRED",
                              "Phải ghi lý do cho nhân sự nghỉ việc.", 422)
        nguoi.operational_status = trang_thai
        nguoi.operational_ref = None
        nguoi.operational_note = str(ghi_chu or "").strip() or None
        nguoi.operational_updated_at = dt.datetime.now(dt.timezone.utc)
        nguoi.status = _nhan(NHAN_TAI_XE, trang_thai, None)
        nguoi.assigned_vehicle = "Chưa gán"
        return nguoi
    nguoi.operational_status = "available"
    nguoi.operational_note = str(ghi_chu or "").strip() or None
    dong_bo_trang_thai_theo_lich(db, crew_ids=[nguoi.id])
    return nguoi


# ===========================================================================
# NHAN HIEN THI CU — giu ten cho cho da goi
# ===========================================================================

NHAN_XE_RANH = NHAN_XE["available"]
NHAN_TAI_XE_RANH = NHAN_TAI_XE["available"]

def xe_dang_ranh(db, vehicle_id, moc=None):
    """Câu trả lời đọc-nhanh cho màn hình: xe này có rảnh ngay lúc này không.

    Dùng cho báo cáo và thẻ KPI. Cửa điều phối thì phải hỏi `kiem_xe_ranh` với
    ĐÚNG khung giờ của chuyến, không hỏi hàm này — "rảnh bây giờ" không có nghĩa
    là "rảnh sáng mai".
    """
    moc = _utc(moc) or dt.datetime.now(dt.timezone.utc)
    ket_thuc = moc + dt.timedelta(minutes=1)
    return (bao_duong_chong_lich(db, vehicle_id, moc, ket_thuc) is None
            and phan_cong_dang_giu(db, vehicle_id=vehicle_id) is None
            and phan_cong_chong_lich(db, moc, ket_thuc, vehicle_id=vehicle_id) is None)


def dem_xe_dang_chay(db, moc=None):
    """Số xe đang thực sự chạy tại `moc`, đếm theo PHÂN CÔNG, không theo nhãn.

    Thay cho phép đếm cũ ở bảng điều khiển, chỗ liệt kê các cách viết nhãn
    (`status.in_(["In Transit", "Đang vận chuyển", "Bận", ...])`) — nhãn nào
    không có trong danh sách thì đếm bằng không.
    """
    moc = _utc(moc) or dt.datetime.now(dt.timezone.utc)
    ket_thuc = moc + dt.timedelta(minutes=1)
    theo_gio = {r[0] for r in db.query(ResourceAssignment.vehicle_id)
                .filter(ResourceAssignment.status.in_(PHAN_CONG_CON_HIEU_LUC),
                        ResourceAssignment.assignment_start < ket_thuc,
                        ResourceAssignment.assignment_end > moc).all()}
    dang_giu = {r[0] for r in db.query(ResourceAssignment.vehicle_id)
                .join(TransportTrip, TransportTrip.id == ResourceAssignment.trip_id)
                .filter(ResourceAssignment.status.in_(PHAN_CONG_CON_HIEU_LUC),
                        TransportTrip.status.in_(CHUYEN_DANG_CHAY)).all()}
    return len(theo_gio | dang_giu)


def dem_xe_hoat_dong(db, moc=None):
    """Số xe ĐANG TRONG ĐỘI HOẠT ĐỘNG tại `moc`: không ngoài đội, không nằm xưởng.

    Đây là con số cho thẻ "Số xe hoạt động" trên bảng điều khiển. Nó KHÁC "số xe
    đang chạy chuyến" (`dem_xe_dang_chay`): một xe đậu ở bãi, sẵn sàng nhận
    chuyến, vẫn là xe đang hoạt động của đội. Bản cũ đếm bằng cách liệt kê nhãn
    và trộn cả "Sẵn sàng" với "Đang vận chuyển" — đúng ý này nhưng bằng chuỗi.
    """
    moc = _utc(moc) or dt.datetime.now(dt.timezone.utc)
    ket_thuc = moc + dt.timedelta(minutes=1)
    dem = 0
    for xe in db.query(Vehicle).all():
        if (xe.operational_status or "") == "out_of_service":
            continue
        if bao_duong_chong_lich(db, xe.id, moc, ket_thuc) is not None:
            continue
        dem += 1
    return dem


def dem_chuyen_dang_chay(db):
    """Số chuyến đang lăn bánh — đọc trạng thái CHUẨN của chuyến, không đọc nhãn."""
    return (db.query(TransportTrip.id)
            .filter(TransportTrip.status.in_(("dispatched", "in_transit")))
            .count())
