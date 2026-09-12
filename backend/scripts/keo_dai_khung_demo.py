# -*- coding: utf-8 -*-
"""Làm tươi mốc thời gian của bộ dữ liệu demo — chạy lại được, nên chạy sáng ngày demo.

    python backend/scripts/keo_dai_khung_demo.py --den 2026-09-30          # xem trước
    python backend/scripts/keo_dai_khung_demo.py --den 2026-09-30 --ghi    # ghi thật

Làm HAI việc khác hẳn nhau, và phân biệt được hai việc này là toàn bộ điểm của script:

  1. KÉO DÀI thứ chỉ có ý nghĩa KỸ THUẬT — khung của lệnh vận chuyển và khung phân công xe,
     tài xế — tới mốc `--den`. Máy chủ chặn mọi sự kiện nằm ngoài khung phân công
     (`ASSIGNMENT_TIME_INVALID`) và mọi phân công nằm ngoài khung lệnh vận chuyển
     (`ASSIGNMENT_OUTSIDE_WINDOW`), nên khung hết hạn là tài xế bấm "Ghi mốc" ăn lỗi dù xe
     vẫn đang trên đường. Hai khung này người dùng không nhìn thấy, đẩy xa bao nhiêu cũng được.

  2. RẢI thứ mang ý nghĩa NGHIỆP VỤ — hạn giao trên lệnh giao hàng — quanh thời điểm hiện tại.
     Hạn giao là cam kết với khách và là cột người điều độ nhìn để biết việc nào gấp. Đẩy hết
     về một ngày xa là cả bảng chỉ còn một con số, hỏng đúng thứ màn hình đó sinh ra để nói.
     Bản đầu của script này đã mắc lỗi đó: dồn 19 lệnh đang chạy về cùng ngày 30/09.

VÌ SAO PHẢI SỬA THẲNG DỮ LIỆU. Không có đường API nào nới khung của một chuyến đang chạy:
`PUT /api/tms/trips/{id}/dispatch` chỉ nhận chuyến còn `planned` (`INVALID_TRANSITION`).

VÌ SAO AN TOÀN KHI THU HẠN GIAO LẠI. Hạn giao trên DO chỉ dùng để HIỆN và để tính trễ hạn
(`_han_giao_cua_chuyen` trong `tms_trip_service`). Cửa gác điều phối đọc khung của LỆNH VẬN
CHUYỂN, còn ghi mốc đọc KHUNG PHÂN CÔNG — cả hai vẫn kéo tới mốc xa. Đã kiểm bằng đường thật:
thu hạn giao về rồi ghi mốc vẫn trả 200.

CHỈ ĐỘNG VÀO BẢN GHI CÒN SỐNG. Chuyến đã hoàn tất hoặc đã huỷ giữ nguyên mốc thật của nó —
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


def rai_han_giao(c, ghi):
    """Rải hạn giao của các lệnh ĐANG CHẠY, tính theo THỜI ĐIỂM CHẠY LỆNH NÀY.

    Vì sao không để chung một mốc xa. Hạn giao là cam kết với khách và là cột người điều độ
    nhìn để biết việc nào gấp. Đẩy hết về một ngày — dù là 16/09 như bộ gieo vẫn làm, hay
    30/09 như bản đầu của script này — thì cả bảng chỉ còn một con số, không ai đọc ra được
    nên chạy chuyến nào trước. Đó là làm hỏng đúng thứ màn hình đó sinh ra để nói.

    Vì sao không tính thẳng từ ngày lấy hàng. Bộ dữ liệu demo đứng yên còn ngày thì trôi:
    các chuyến gieo ngày 11/09 mà mở ra xem ngày 15/09 thì hạn tự nhiên nào cũng đã trôi qua,
    16 trên 19 lệnh hiện TRỄ HẠN — đọc lên như công ty sắp phá sản.

    Nên rải TƯƠNG ĐỐI với hiện tại: lệnh đang có sự cố chưa xử lý thì hạn nằm ở quá khứ gần
    (xe kẹt thì trễ là đúng, và để màn hình có cái mà cảnh báo thật), còn lại rải đều từ vài
    giờ tới sang những ngày sau. Chạy lại lệnh này sáng ngày demo là bảng tươi lại.

    An toàn: hạn giao trên DO chỉ dùng để HIỆN và để tính trễ hạn. Cửa gác điều phối đọc
    khung của LỆNH VẬN CHUYỂN, còn ghi mốc đọc KHUNG PHÂN CÔNG — hai thứ đó vẫn kéo tới mốc
    xa, nên thu hạn giao lại không chặn tài xế bấm mốc.
    """
    hang = c.execute(text("""
        SELECT d.id, d.pickup_window_start,
               (SELECT count(*) FROM incidents i
                 WHERE i.do_id = d.id
                   AND lower(coalesce(i.status, '')) NOT IN ('resolved', 'closed', 'completed')) AS su_co
          FROM delivery_orders d
         WHERE d.canonical_status IN ('in_transit', 'arrived')
         ORDER BY d.pickup_window_start, d.id
    """)).mappings().all()
    if not hang:
        print("  %-46s %4d bản ghi" % ("Rải hạn giao của lệnh ĐANG CHẠY", 0))
        return 0

    bay_gio = dt.datetime.now(VN)
    co_su_co = [h for h in hang if h["su_co"]]
    binh_thuong = [h for h in hang if not h["su_co"]]
    moi = {}
    for i, h in enumerate(co_su_co):                       # trễ thật: 3, 8, 13… giờ trước
        moi[h["id"]] = bay_gio - dt.timedelta(hours=3 + i * 5)
    for i, h in enumerate(binh_thuong):                    # rải từ +5 giờ, mỗi lệnh cách 8 giờ
        moi[h["id"]] = bay_gio + dt.timedelta(hours=5 + i * 8)

    print("  %-46s %4d bản ghi  (%d trễ do sự cố)"
          % ("Rải hạn giao của lệnh ĐANG CHẠY", len(moi), len(co_su_co)))
    if ghi:
        for ma, gio in moi.items():
            c.execute(text("UPDATE delivery_orders SET delivery_window_end = :g WHERE id = :m"),
                      {"g": gio.replace(minute=0, second=0, microsecond=0), "m": ma})
    return len(moi)


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
        tong += rai_han_giao(c, a.ghi)
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
