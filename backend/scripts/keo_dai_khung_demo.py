# -*- coding: utf-8 -*-
"""Kéo dài khung giờ của dữ liệu demo ĐANG SỐNG tới một mốc mới.

    python backend/scripts/keo_dai_khung_demo.py --den 2026-09-30          # xem trước
    python backend/scripts/keo_dai_khung_demo.py --den 2026-09-30 --ghi    # ghi thật

VÌ SAO PHẢI SỬA THẲNG DỮ LIỆU. Máy chủ chặn mọi sự kiện vận tải nằm ngoài khung phân công
(`ASSIGNMENT_TIME_INVALID`) và mọi phân công nằm ngoài khung của lệnh vận chuyển
(`ASSIGNMENT_OUTSIDE_WINDOW`). Khi khung hết hạn, tài xế mở trang lên bấm "Ghi mốc" là ăn lỗi
dù xe vẫn đang trên đường. Mà KHÔNG có đường API nào nới khung của một chuyến đang chạy:
`PUT /api/tms/trips/{id}/dispatch` chỉ nhận chuyến còn `planned` (`INVALID_TRANSITION`).

CHỈ ĐỘNG VÀO BẢN GHI CÒN SỐNG. Chuyến đã hoàn tất hoặc đã huỷ giữ nguyên khung thật của nó —
đó là lịch sử, sửa vào là làm sai số liệu báo cáo và hồ sơ đã chốt.

Lưu ý kiểu dữ liệu: `freight_orders` dùng DateTime KHÔNG múi giờ (lưu UTC trần), còn
`delivery_orders` và `resource_assignments` dùng DateTime có múi giờ. Ghi nhầm kiểu thì
so sánh giờ lệch 7 tiếng mà không báo lỗi gì.
"""
import argparse
import datetime as dt
import os
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "app"))
os.chdir(os.path.join(GOC, "app"))

from dotenv import load_dotenv                                    # noqa: E402
load_dotenv(os.path.join(os.path.dirname(GOC), ".env"))
from sqlalchemy import create_engine, text                        # noqa: E402

VN = dt.timezone(dt.timedelta(hours=7))

SONG_TRIP = "status NOT IN ('completed', 'cancelled')"
SONG_DO = "canonical_status IN ('pending', 'in_transit', 'arrived')"

# (nhãn, câu đếm, câu ghi) — mỗi câu chỉ chạm bản ghi CÒN SỐNG và CHƯA phủ tới mốc mới.
VIEC = [
    # CHỈ lệnh đang nằm trên chuyến chưa đóng. KHÔNG đụng lệnh còn chờ điều phối: hạn giao
    # của chúng CHÍNH LÀ lịch làm việc sắp tới, dồn hết về một ngày là bảng điều phối mất
    # hẳn thứ tự ưu tiên — đã lỡ làm thế một lần ngày 12/09 và phải khôi phục bằng mục dưới.
    ("Khung giao của lệnh giao hàng ĐANG CHẠY",
     """SELECT count(*) FROM delivery_orders
         WHERE canonical_status IN ('in_transit', 'arrived')
           AND delivery_window_end < :moc_tz""",
     """UPDATE delivery_orders SET delivery_window_end = :moc_tz
         WHERE canonical_status IN ('in_transit', 'arrived')
           AND delivery_window_end < :moc_tz"""),

    # Lệnh chờ điều phối: hạn giao đặt về CUỐI NGÀY LẤY HÀNG của chính nó (18:00 giờ VN) —
    # đúng hình dạng bộ gieo vẫn sinh ra. Câu này idempotent: chạy bao nhiêu lần cũng ra
    # một kết quả, và không bao giờ làm phẳng lịch.
    ("Hạn giao của lệnh CHỜ ĐIỀU PHỐI (đặt về cuối ngày lấy hàng)",
     """SELECT count(*) FROM delivery_orders
         WHERE canonical_status = 'pending' AND pickup_window_start IS NOT NULL
           AND delivery_window_end IS DISTINCT FROM
               (date_trunc('day', pickup_window_start AT TIME ZONE 'Asia/Ho_Chi_Minh')
                + interval '18 hours') AT TIME ZONE 'Asia/Ho_Chi_Minh'""",
     """UPDATE delivery_orders SET delivery_window_end =
               (date_trunc('day', pickup_window_start AT TIME ZONE 'Asia/Ho_Chi_Minh')
                + interval '18 hours') AT TIME ZONE 'Asia/Ho_Chi_Minh'
         WHERE canonical_status = 'pending' AND pickup_window_start IS NOT NULL
           AND delivery_window_end IS DISTINCT FROM
               (date_trunc('day', pickup_window_start AT TIME ZONE 'Asia/Ho_Chi_Minh')
                + interval '18 hours') AT TIME ZONE 'Asia/Ho_Chi_Minh'"""),

    ("Khung giao của lệnh vận chuyển (freight order)",
     """SELECT count(*) FROM freight_orders
         WHERE {song_trip} AND delivery_window_end < :moc_tran""",
     """UPDATE freight_orders SET delivery_window_end = :moc_tran
         WHERE {song_trip} AND delivery_window_end < :moc_tran"""),

    # `transport_trips` KHÔNG có cột hạn giao — API tính nó từ DO, nên nới khung DO là đủ.
    ("Khung phân công xe và tài xế",
     """SELECT count(*) FROM resource_assignments a
         WHERE a.assignment_end < :moc_tz
           AND EXISTS (SELECT 1 FROM transport_trips t
                        WHERE t.id = a.trip_id AND t.{song_trip})""",
     """UPDATE resource_assignments SET assignment_end = :moc_tz
         WHERE assignment_end < :moc_tz
           AND EXISTS (SELECT 1 FROM transport_trips t
                        WHERE t.id = resource_assignments.trip_id AND t.{song_trip})"""),

    ("Hạn hiệu lực của báo giá còn mở",
     """SELECT count(*) FROM quotations
         WHERE canonical_status IN ('draft', 'pending_approval', 'sent')
           AND valid_to IS NOT NULL AND valid_to < :moc_ngay""",
     """UPDATE quotations SET valid_to = :moc_ngay
         WHERE canonical_status IN ('draft', 'pending_approval', 'sent')
           AND valid_to IS NOT NULL AND valid_to < :moc_ngay"""),
]


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--den", required=True, help="mốc mới, dạng YYYY-MM-DD (lấy 23:59 giờ VN)")
    p.add_argument("--ghi", action="store_true", help="ghi thật; không có thì chỉ xem trước")
    a = p.parse_args()

    ngay = dt.date.fromisoformat(a.den)
    moc_tz = dt.datetime.combine(ngay, dt.time(23, 59), tzinfo=VN)
    moc_tran = moc_tz.astimezone(dt.timezone.utc).replace(tzinfo=None)   # freight_orders lưu UTC trần
    tham = {"moc_tz": moc_tz, "moc_tran": moc_tran, "moc_ngay": ngay.isoformat()}
    thay = {"song_trip": SONG_TRIP, "song_do": SONG_DO}

    print("Kéo dài tới %s (UTC trần %s)" % (moc_tz.isoformat(), moc_tran.isoformat()))
    print("Chế độ: %s\n" % ("GHI THẬT" if a.ghi else "chỉ xem trước"))

    e = create_engine(os.environ["DATABASE_URL"])
    tong = 0
    with e.begin() as c:
        for nhan, dem, ghi in VIEC:
            so = c.execute(text(dem.format(**thay)), tham).scalar() or 0
            tong += so
            print("  %-46s %4d bản ghi" % (nhan, so))
            if a.ghi and so:
                c.execute(text(ghi.format(**thay)), tham)
        if not a.ghi:
            print("\n  (chưa ghi gì — thêm --ghi để thực hiện)")

    if a.ghi:
        print("\nĐã cập nhật %d bản ghi." % tong)
        with e.connect() as c:
            print("\nKiểm lại — mốc muộn nhất của dữ liệu còn sống:")
            for nhan, sql in [
                ("Lệnh giao hàng", "SELECT max(delivery_window_end) FROM delivery_orders WHERE " + SONG_DO),
                ("Lệnh vận chuyển", "SELECT max(delivery_window_end) FROM freight_orders WHERE " + SONG_TRIP),
                ("Phân công", """SELECT max(a.assignment_end) FROM resource_assignments a
                                  JOIN transport_trips t ON t.id = a.trip_id WHERE t.""" + SONG_TRIP),
            ]:
                print("  %-18s %s" % (nhan, c.execute(text(sql)).scalar()))
    else:
        print("Tổng: %d bản ghi sẽ được cập nhật." % tong)


if __name__ == "__main__":
    main()
