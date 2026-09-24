# -*- coding: utf-8 -*-
"""GPS THEO THÁNG — chia bảng, thưa điểm, xoá điểm quá hạn (chủ dự án chốt 24/09: nghìn chuyến / ngày).

Điện thoại tài xế gửi 25 giây một điểm: 300 xe chạy 10 giờ / ngày là ~430.000 điểm / ngày, ~13 triệu / tháng.
Để nguyên một bảng thì vài năm là hàng trăm triệu dòng, xoá điểm cũ là DELETE hàng triệu dòng khoá bảng cả tiếng.

    python tools/gps_thang.py <db> xem            các tháng đang có · số điểm · dung lượng
    python tools/gps_thang.py <db> chia           đổi vehicle_positions sang bảng CHIA THEO THÁNG (mỗi tháng một bảng
                                                  con); chạy lại không sao — đã chia thì thôi. Sao lưu DB trước khi chạy.
    python tools/gps_thang.py <db> thua [ngay]    điểm cũ hơn `ngay` ngày (mặc định 30): mỗi chuyến giữ 1 điểm / 5 phút
                                                  (điểm cuối mỗi khoảng) — vẫn vẽ lại được vệt đường, bảng nhẹ ~12 lần
    python tools/gps_thang.py <db> xoa [thang]    xoá hẳn điểm cũ hơn `thang` tháng (mặc định 24): bảng đã chia thì
                                                  DROP cả bảng con của tháng đó — xong ngay, không khoá gì

<db> là tên DB (epl_lao · epl_lao_tai). Chuỗi kết nối đọc trong .env, chỉ thay tên DB. Lịch chạy gợi ý: `thua` và
`xoa` mỗi đêm (Task Scheduler của Windows). Máy chủ khi khởi động tự dựng sẵn bảng con cho tháng này + 2 tháng tới
(database.tao_chi_muc) nên không bao giờ thiếu chỗ ghi điểm mới.
"""
import datetime as dt
import os
import re
import sys
import time

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANG = "vehicle_positions"


def engine(db):
    from sqlalchemy import create_engine
    u = re.search(r"^DATABASE_URL\s*=\s*(\S+)", open(os.path.join(GOC, ".env"), encoding="utf-8").read(), re.M).group(1).strip("\"'")
    return create_engine(u.rsplit("/", 1)[0] + "/" + db)


def da_chia(c):
    from sqlalchemy import text
    return c.execute(text("SELECT relkind FROM pg_class WHERE relname = :b AND relnamespace = 'public'::regnamespace"),
                     {"b": BANG}).scalar() == "p"


def ten_thang(d):
    return "%s_%04d_%02d" % (BANG, d.year, d.month)


def dau_thang(d, cong=0):
    t = d.year * 12 + d.month - 1 + cong
    return dt.date(t // 12, t % 12 + 1, 1)


def tao_thang(c, d):
    """Bảng con của tháng chứa ngày d (đã có thì thôi)."""
    from sqlalchemy import text
    a, b = dau_thang(d), dau_thang(d, 1)
    c.execute(text("CREATE TABLE IF NOT EXISTS %s PARTITION OF %s FOR VALUES FROM ('%s') TO ('%s')"
                   % (ten_thang(a), BANG, a.isoformat(), b.isoformat())))


def xem(e):
    from sqlalchemy import text
    with e.connect() as c:
        if not da_chia(c):
            n = c.execute(text("SELECT count(*) FROM %s" % BANG)).scalar()
            kc = c.execute(text("SELECT pg_size_pretty(pg_total_relation_size('%s'))" % BANG)).scalar()
            print("bảng %s CHƯA chia theo tháng · %d điểm · %s" % (BANG, n, kc))
            return
        rows = c.execute(text("""SELECT c.relname, pg_get_expr(c.relpartbound, c.oid), pg_total_relation_size(c.oid)
            FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid WHERE i.inhparent = '%s'::regclass ORDER BY 1""" % BANG)).all()
        print("bảng %s ĐÃ chia theo tháng · %d bảng con" % (BANG, len(rows)))
        for ten, bien, kc in rows:
            n = c.execute(text("SELECT count(*) FROM %s" % ten)).scalar()
            print("  %-30s %10d điểm · %8.1f MB" % (ten, n, kc / 1048576))


def chia(e):
    from sqlalchemy import text
    t0 = time.time()
    with e.begin() as c:
        if da_chia(c):
            print("✓ đã chia theo tháng từ trước — không làm gì")
            return
        n = c.execute(text("SELECT count(*) FROM %s" % BANG)).scalar()
        c.execute(text("UPDATE %s SET ts = now() AT TIME ZONE 'UTC' WHERE ts IS NULL" % BANG))
        # 1. bảng cũ đổi tên, kèm tên khoá / chỉ mục để bảng mới dùng lại đúng tên cũ
        c.execute(text("ALTER TABLE %s RENAME TO %s_cu" % (BANG, BANG)))
        for (ten,) in c.execute(text("SELECT conname FROM pg_constraint WHERE conrelid = '%s_cu'::regclass" % BANG)).all():
            c.execute(text('ALTER TABLE %s_cu RENAME CONSTRAINT "%s" TO "%s_cu"' % (BANG, ten, ten[:55])))
        for (ten,) in c.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = '%s_cu' AND indexname NOT LIKE '%%\\_cu'" % BANG)).all():
            c.execute(text('ALTER INDEX "%s" RENAME TO "%s_cu"' % (ten, ten[:55])))
        # 2. bảng mới chia theo tháng: khoá chính phải chứa cột chia (id, ts)
        c.execute(text("CREATE TABLE %s (LIKE %s_cu INCLUDING DEFAULTS) PARTITION BY RANGE (ts)" % (BANG, BANG)))
        c.execute(text("ALTER TABLE %s ALTER COLUMN ts SET NOT NULL" % BANG))
        c.execute(text("ALTER TABLE %s ADD CONSTRAINT %s_pkey PRIMARY KEY (id, ts)" % (BANG, BANG)))
        c.execute(text("ALTER TABLE %s ADD CONSTRAINT %s_trip_id_fkey FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE" % (BANG, BANG)))
        c.execute(text("ALTER TABLE %s ADD CONSTRAINT %s_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)" % (BANG, BANG)))
        c.execute(text("ALTER TABLE %s ADD CONSTRAINT %s_driver_id_fkey FOREIGN KEY (driver_id) REFERENCES drivers(id)" % (BANG, BANG)))
        # 3. một bảng con mỗi tháng có dữ liệu + tháng này + 2 tháng tới; bảng DEFAULT hứng điểm lạc (giờ máy sai…)
        lo = c.execute(text("SELECT min(ts)::date FROM %s_cu" % BANG)).scalar() or dt.date.today()
        d = dau_thang(lo)
        while d <= dau_thang(dt.date.today(), 2):
            tao_thang(c, d)
            d = dau_thang(d, 1)
        c.execute(text("CREATE TABLE IF NOT EXISTS %s_khac PARTITION OF %s DEFAULT" % (BANG, BANG)))
        # 4. chép dữ liệu, dựng chỉ mục trên bảng mẹ (tự xuống từng bảng con), bỏ bảng cũ
        cot = ", ".join('"%s"' % r[0] for r in c.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = '%s_cu' ORDER BY ordinal_position" % BANG)))
        c.execute(text("INSERT INTO %s (%s) SELECT %s FROM %s_cu" % (BANG, cot, cot, BANG)))
        c.execute(text("CREATE INDEX ix_vp_phieu_luc ON %s (trip_id, ts DESC)" % BANG))
        c.execute(text("CREATE INDEX ix_vp_xe_luc ON %s (vehicle_id, ts DESC)" % BANG))
        c.execute(text("CREATE INDEX ix_vehicle_positions_ts ON %s (ts)" % BANG))
        m = c.execute(text("SELECT count(*) FROM %s" % BANG)).scalar()
        if m != n:
            raise SystemExit("✗ chép thiếu: %d → %d điểm — huỷ, bảng cũ còn nguyên" % (n, m))
        c.execute(text("DROP TABLE %s_cu" % BANG))
    print("✓ đã chia theo tháng · %d điểm chép đủ · %.0f s" % (n, time.time() - t0))


def thua(e, ngay=30):
    """Mỗi chuyến, mỗi khoảng 5 phút giữ đúng MỘT điểm (điểm mới nhất trong khoảng) — với điểm cũ hơn `ngay` ngày.
    Làm theo từng tháng một để mỗi lượt vừa phải; chạy lại không đổi gì (đã thưa thì mỗi khoảng chỉ còn một)."""
    from sqlalchemy import text
    moc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(days=ngay)   # cột ts ghi giờ UTC trần
    t0, tong = time.time(), 0
    with e.connect() as c:
        lo = c.execute(text("SELECT min(ts) FROM %s" % BANG)).scalar()
    if not lo or lo >= moc:
        print("✓ không có điểm nào cũ hơn %d ngày" % ngay)
        return
    d = dau_thang(lo.date())
    while dt.datetime.combine(d, dt.time()) < moc:
        a, b = dt.datetime.combine(d, dt.time()), min(dt.datetime.combine(dau_thang(d, 1), dt.time()), moc)
        with e.begin() as c:
            n = c.execute(text("""DELETE FROM %s v USING (
                    SELECT id, ts, row_number() OVER (PARTITION BY trip_id, date_bin('5 minutes', ts, TIMESTAMP '2000-01-01')
                                                     ORDER BY ts DESC) AS rn
                    FROM %s WHERE ts >= :a AND ts < :b) x
                WHERE v.id = x.id AND v.ts = x.ts AND x.rn > 1 AND v.ts >= :a AND v.ts < :b""" % (BANG, BANG)),
                {"a": a, "b": b}).rowcount
        tong += n
        print("  %s · bỏ %d điểm · %.0f s" % (d.strftime("%Y-%m"), n, time.time() - t0), flush=True)
        d = dau_thang(d, 1)
    print("✓ thưa điểm GPS cũ hơn %d ngày: bỏ %d điểm (giữ 1 điểm / 5 phút / chuyến)" % (ngay, tong))


def xoa(e, thang=24):
    from sqlalchemy import text
    moc = dau_thang(dt.date.today(), -thang)
    with e.begin() as c:
        if da_chia(c):
            bo = []
            for ten, bien in c.execute(text("""SELECT c.relname, pg_get_expr(c.relpartbound, c.oid) FROM pg_inherits i
                    JOIN pg_class c ON c.oid = i.inhrelid WHERE i.inhparent = '%s'::regclass""" % BANG)).all():
                m = re.search(r"TO \('(\d{4}-\d{2}-\d{2})", bien or "")
                if m and dt.date.fromisoformat(m.group(1)) <= moc:
                    c.execute(text("DROP TABLE %s" % ten)); bo.append(ten)
            print("✓ bỏ %d bảng con cũ hơn %d tháng%s" % (len(bo), thang, (": " + ", ".join(sorted(bo))) if bo else ""))
        else:
            n = c.execute(text("DELETE FROM %s WHERE ts < :m" % BANG), {"m": moc}).rowcount
            print("✓ xoá %d điểm cũ hơn %d tháng" % (n, thang))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    e, lenh = engine(sys.argv[1]), sys.argv[2]
    so = int(sys.argv[3]) if len(sys.argv) > 3 else None
    if lenh == "xem":
        xem(e)
    elif lenh == "chia":
        chia(e)
    elif lenh == "thua":
        thua(e, 30 if so is None else so)
    elif lenh == "xoa":
        xoa(e, 24 if so is None else so)
    else:
        raise SystemExit(__doc__)
