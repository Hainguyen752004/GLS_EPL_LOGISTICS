# -*- coding: utf-8 -*-
"""Gieo thêm 9 case ĐA TIỀN TỆ, ưu tiên Lào: 5 LAK · 2 VNĐ · 1 THB · 1 USD.

    python backend/scripts/gieo_case_da_tien_te.py           # xem kế hoạch
    python backend/scripts/gieo_case_da_tien_te.py --gieo    # gieo thật

Đi ĐÚNG luồng như bộ gieo chính: cơ hội → báo giá → khách chấp nhận → DO sinh tự động →
lập chuyến → điều phối → mốc thực thi → hoàn tất. Không ghi thẳng vào cơ sở dữ liệu, và
không có con số tiền nào gõ tay — giá lấy từ chính công thức giá thành qua `price-preview`.

Năm case Lào chạy trên tuyến THẬT Viêng Chăn → Cảng Cửa Lò (475 km, 2 chặng), để lúc demo
ở Lào mở màn nào cũng thấy tuyến của nước sở tại chứ không phải toàn tuyến Việt Nam.

PHẢI THÊM XE VÀ TÀI XẾ TRƯỚC. Đội đang 0 xe rảnh (12 xe giữ 12 chuyến chưa đóng), mà một xe
đang giữ chuyến chưa đóng thì không điều thêm được (`RESOURCE_BUSY`). Bốn case dưới đây cần
xe được giữ, nên thêm 4 xe và 4 tài xế chính người Lào — cũng để màn Điều phối thôi hiện
"0 xe rảnh", một con số đọc lên nghe như công ty hết xe.

Case đã hoàn tất thì TRẢ LẠI xe khi đóng chuyến, nên một xe chạy được nhiều case nối tiếp;
thứ tự gieo ở `CAC_CASE` đã tính điều đó.
"""
import argparse
import datetime as dt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dung_lai_du_lieu_demo as M                              # noqa: E402

VN = M.VN
HOM_NAY = dt.datetime.now(VN).date()
HAN_MOI = dt.datetime(2026, 9, 30, 23, 59, tzinfo=VN)

# ---------------------------------------------------------------- tuyến Lào
TUYEN_LAO = "DEMO-RT-VIENGCHAN-CUALO"

# ---------------------------------------------------------------- xe và tài xế thêm
XE_THEM = [
    ("DEMO-51C-141.04", "DEMO-VT-TRUCK15", 15000, 60.0),
    ("DEMO-51C-252.05", "DEMO-VT-TRACTOR40", 30000, 67.0),
    ("DEMO-61H-363.06", "DEMO-VT-20FT", 28000, 33.2),
    ("DEMO-50H-474.07", "DEMO-VT-TRACTOR20", 24000, 33.0),
]
TAI_XE_THEM = [
    ("DEMO-DRV-017", "Bounmy Sisavath", "0205551217"),
    ("DEMO-DRV-018", "Thongdy Keomany", "0205551218"),
    ("DEMO-DRV-019", "Souksavanh Inthavong", "0205551219"),
    ("DEMO-DRV-020", "Viengsavanh Douangchak", "0205551220"),
]

# (nhãn, khách, tuyến, loại xe, xe, tài xế, ngày, tiền, tỷ giá, giai đoạn, biên)
#
# Ngày có chủ ý: case đã hoàn tất đặt ở quá khứ (lịch sử thật), case đang chạy đặt hôm nay
# hoặc hôm qua (máy chủ chặn mốc ở tương lai bằng `EVENT_TIME_FUTURE`), còn case chờ điều
# phối và báo giá rải ra 20–28/09 để lịch có việc tới hết tháng.
CAC_CASE = [
    ("L1", "DEMO-CUS-LOTTE",    TUYEN_LAO,                 "DEMO-VT-TRUCK15",  "DEMO-51C-141.04", "DEMO-DRV-017", -4, "LAK", 1.18, "hoan_tat", 0.30),
    ("L2", "DEMO-CUS-VINAMILK", TUYEN_LAO,                 "DEMO-VT-TRACTOR40","DEMO-51C-252.05", "DEMO-DRV-018", -1, "LAK", 1.18, "dang_chay", 0.27),
    ("L3", "DEMO-CUS-ACECOOK",  TUYEN_LAO,                 "DEMO-VT-20FT",     "DEMO-61H-363.06", "DEMO-DRV-019",  0, "LAK", 1.18, "den_noi", 0.26),
    ("L4", "DEMO-CUS-THACO",    TUYEN_LAO,                 "DEMO-VT-TRUCK15",  None,              None,           10, "LAK", 1.18, "do", 0.28),
    ("L5", "DEMO-CUS-TAEKWANG", TUYEN_LAO,                 "DEMO-VT-TRACTOR20",None,              None,           14, "LAK", 1.18, "bao_gia", 0.25),

    ("V1", "DEMO-CUS-BIDRICO",  "DEMO-RT-SONGTHAN-CATLAI", "DEMO-VT-TRUCK15",  "DEMO-51C-141.04", "DEMO-DRV-017", -3, "VND", 1.0,  "hoan_tat", 0.29),
    ("V2", "DEMO-CUS-UNILEVER", "DEMO-RT-VSIP2A-CATLAI",   "DEMO-VT-TRUCK10",  None,              None,           12, "VND", 1.0,  "do", 0.28),

    ("T1", "DEMO-CUS-DUCGIANG", "DEMO-RT-LONGAN-CAIMEP",   "DEMO-VT-TRACTOR20","DEMO-50H-474.07", "DEMO-DRV-020", -1, "THB", 710.0, "dang_chay", 0.27),

    # Biên 12% — dưới ngưỡng công ty (15%), nên báo giá này dừng ở "chờ duyệt nội bộ".
    # Có một phiếu như vậy thì màn Báo giá mới có cái để nói về đường duyệt.
    ("U1", "DEMO-CUS-SAMSUNG",  "DEMO-RT-VSIP2A-CAIMEP",   "DEMO-VT-TRACTOR40",None,              None,           16, "USD", 26173.5, "cho_duyet", 0.12),
]


def chuan_bi():
    """Khai tuyến Lào vào bảng tra của bộ gieo, và nới hạn demo tới 30/09."""
    M.TUYEN_DEMO[TUYEN_LAO] = (475.0, "VIENGCHAN", "CUALO")
    M.TOA_DO["VIENGCHAN"] = (17.9757, 102.6331)
    M.TOA_DO["CUALO"] = (18.8273, 105.7070)
    M.SO_CHANG[TUYEN_LAO] = 2
    M.HANG_THEO_KHACH.setdefault("DEMO-CUS-LOTTE", "Hàng bán lẻ siêu thị")
    M.HAN_DEMO = HAN_MOI                      # khung phân công của case đang chạy kéo tới đây


def them_nguon_luc():
    M._in("[1] Thêm 4 xe và 4 tài xế chính người Lào")
    for ma, loai, tai, tt in XE_THEM:
        M.goi("POST", "/api/vehicles", {
            "id": ma, "type": loai, "weight_capacity": tai, "volume_capacity_m3": tt,
            "brand": "Hyundai", "status": "Sẵn sàng", "depot_code": "DEMO-DEPOT-SONGTHAN",
            "inspection_exp": "2027-12-31", "insurance_date": "2027-12-31",
            "maintenance_date": "2027-08-31", "fuel_norm": 30.0,
        }, cho_phep=(200, 201, 409))
    for ma, ten, dien_thoai in TAI_XE_THEM:
        M.goi("POST", "/api/drivers", {
            "id": ma, "name": ten, "role": "Lái xe chính", "license_type": "FC",
            "phone": dien_thoai, "shift": "Ca Sáng (06:00 - 14:00)",
        }, cho_phep=(200, 201, 409))
        # Không có bằng còn hạn thì điều phối chặn ngay bằng `DRIVER_LICENSE_INVALID`,
        # và hạng bằng phải KHỚP hồ sơ tài xế, lệch hạng cũng bị coi như không có bằng.
        M.goi("POST", "/api/tms/driver-qualifications", {
            "driver_id": ma, "license_type": "FC",
            "valid_from": "2025-01-01", "valid_to": "2028-12-31", "status": "active",
        }, cho_phep=(200, 201, 409))
        # Ca làm việc phải phủ TRỌN khung chuyến, nếu không bị chặn bằng
        # `DRIVER_WORK_SCHEDULE_REQUIRED`. Khai một dải rộng cho cả đợt demo.
        M.ca_truc("CA-DEMO-T9T12-" + ma, ma,
                  dt.datetime(2026, 8, 1, 0, 0, tzinfo=VN),
                  dt.datetime(2026, 12, 31, 23, 58, tzinfo=VN))


def gieo():
    M._in("\n[2] Gieo %d case" % len(CAC_CASE))
    ket = []
    for i, (nhan, khach, tuyen, loai, xe, tai_xe, lech, tien, ty_gia, giai_doan, bien) in enumerate(CAC_CASE):
        ngay = HOM_NAY + dt.timedelta(days=lech)
        M._in("\n  --- %s · %s · %s · %s · %s ---" % (nhan, tien, giai_doan, khach.split("-")[-1], ngay))
        qid, ds, ma_trip = M._mot_case(
            700 + i, khach, tuyen, loai, xe, tai_xe, ngay, tien, ty_gia, giai_doan, bien=bien)
        ket.append((nhan, tien, giai_doan, qid, ds, ma_trip))
    return ket


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--gieo", action="store_true", help="gieo thật; không có thì chỉ in kế hoạch")
    a = p.parse_args()

    print("Kế hoạch: %d case · hạn dữ liệu %s" % (len(CAC_CASE), HAN_MOI.date()))
    dem = {}
    for c in CAC_CASE:
        dem[c[7]] = dem.get(c[7], 0) + 1
    print("  Tiền tệ: " + " · ".join("%s %d" % (k, v) for k, v in sorted(dem.items(), key=lambda x: -x[1])))
    for nhan, khach, tuyen, loai, xe, tai_xe, lech, tien, ty_gia, giai_doan, bien in CAC_CASE:
        print("  %-3s %-4s %-10s %-28s %-26s %s  biên %.0f%%"
              % (nhan, tien, giai_doan, tuyen.replace("DEMO-RT-", ""), khach.replace("DEMO-CUS-", ""),
                 HOM_NAY + dt.timedelta(days=lech), bien * 100))
    if not a.gieo:
        print("\n  (chưa gieo — thêm --gieo để thực hiện)")
        return
    if not M.TOKEN:
        sys.exit("Thiếu EPL_TMS_API_TOKEN trong .env")

    chuan_bi()
    them_nguon_luc()
    ket = gieo()

    M._in("\n[3] Kết quả")
    for nhan, tien, giai_doan, qid, ds, ma_trip in ket:
        M._in("  %-3s %-4s %-10s báo giá %-14s DO %-24s chuyến %s"
              % (nhan, tien, giai_doan, qid or "—", ", ".join(ds) or "—", ma_trip or "—"))


if __name__ == "__main__":
    main()
