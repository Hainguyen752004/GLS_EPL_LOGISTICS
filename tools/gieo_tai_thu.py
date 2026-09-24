# -*- coding: utf-8 -*-
"""Dựng DB THỬ TẢI `epl_lao_tai` — 1 năm dữ liệu giả để đo tốc độ (chủ dự án chốt 24/09: nghìn chuyến / ngày).

    python tools/gieo_tai_thu.py chep           dựng lại DB thử: chép epl_lao → epl_lao_tai (15 phiếu mẫu)
    python tools/gieo_tai_thu.py nhan trips     nhân bản MỘT bảng (chạy lần lượt: trips, trip_sections, trip_expenses,
                                                trip_goods, trip_payments, trip_events, vouchers, chung_tu) — mỗi lệnh
                                                dưới 10 phút, in tiến độ từng đợt 2.000 bản
    python tools/gieo_tai_thu.py them <bang> [tu] [den]   thêm 3 NĂM trước năm đầu (4 năm vận hành); tu–den = chỉ số bản
                                                trong phần thêm (0 … 73.002) — chia lượt cho mỗi lệnh dưới 10 phút
    python tools/gieo_tai_thu.py xe [YYYY-MM]   3 xe mẫu → 500 xe · 500 tài xế, chia phiếu đều cho các xe
    python tools/gieo_tai_thu.py gps            GPS 30 ngày gần nhất (150 điểm / phiếu, 25 giây một điểm)
    python tools/gieo_tai_thu.py gps_cu YYYY-MM YYYY-MM   GPS các tháng cũ ĐÃ THƯA (13 điểm / phiếu) như luật thật
    python tools/gieo_tai_thu.py cu             phiếu lĩnh của phiếu cũ hơn 7 ngày → đã cấp; gỡ phiếu nhân bản khỏi hoá đơn gộp mẫu;
                                                phiếu liên kết cũ hơn 35 ngày → đã trả chủ xe
    python tools/gieo_tai_thu.py xong           ANALYZE + in dung lượng
    python tools/gieo_tai_thu.py xoa            xoá DB thử khi đo xong

Chỉ đụng DB tên `epl_lao_tai` — tên khác thì từ chối. Không sửa .env: đọc chuỗi kết nối trong .env, thay tên DB.
Nhân bản chạy NGAY TRONG PostgreSQL (INSERT … SELECT … generate_series) nên không đẩy hàng triệu dòng qua mạng:
15 phiếu mẫu × ~24.334 bản = 365.000 phiếu rải đều 365 ngày (1.000 / ngày), kèm dòng chi, mục duyệt, dòng hàng,
lần thu, chứng từ, phiếu lĩnh, sự kiện. Phiếu cũ hơn 7 ngày coi như xong (đã tới · khoá · đã thu) — đúng như ngoài
đời, không phải 1/4 số phiếu cả năm vẫn "đang chạy".
"""
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_THU = "epl_lao_tai"
PG = r"C:\Program Files\PostgreSQL\18\bin"
SO_PHIEU = 365000
NGAY_DAU = "2025-09-25"


def url_goc():
    s = open(os.path.join(GOC, ".env"), encoding="utf-8").read()
    return re.search(r"^DATABASE_URL\s*=\s*(\S+)", s, re.M).group(1).strip("\"'")


def url_db(ten):
    u = url_goc()
    return u.rsplit("/", 1)[0] + "/" + ten


def pg_env():
    u = urllib.parse.urlparse(url_goc().replace("+psycopg2", ""))
    return u, dict(os.environ, PGPASSWORD=urllib.parse.unquote(u.password or ""))


def lenh_pg(cong_cu, *thamso):
    u, e = pg_env()
    r = subprocess.run([os.path.join(PG, cong_cu), "-h", u.hostname, "-p", str(u.port), "-U", urllib.parse.unquote(u.username), *thamso],
                       env=e, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("%s lỗi: %s" % (cong_cu, r.stderr[-600:]))
    return r


def tao_lai():
    from sqlalchemy import create_engine, text
    e = create_engine(url_db("postgres"), isolation_level="AUTOCOMMIT")
    with e.connect() as c:
        c.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :d AND pid <> pg_backend_pid()"), {"d": DB_THU})
        c.execute(text('DROP DATABASE IF EXISTS "%s"' % DB_THU))
        c.execute(text('CREATE DATABASE "%s"' % DB_THU))
    print("✓ tạo DB trống %s" % DB_THU, flush=True)
    tep = os.path.join(tempfile.gettempdir(), "epl_lao_goc.dump")
    lenh_pg("pg_dump.exe", "-d", "epl_lao", "-Fc", "-f", tep)
    lenh_pg("pg_restore.exe", "-d", DB_THU, "--no-owner", tep)
    os.remove(tep)
    print("✓ chép epl_lao → %s (15 phiếu mẫu + danh mục)" % DB_THU, flush=True)


def nhan_ban(cac_bang, doan=None):
    """Nhân bản năm đầu (25/09/2025 → 24/09/2026). `doan=(tu, den)` chỉ làm các bản từ tu tới den-1 (chia lượt)."""
    _nhan(cac_bang, 0, None, NGAY_DAU, 365, doan)


# 24/09 · thêm 3 NĂM trước năm đầu — DB thử thành 4 năm vận hành (25/09/2022 → 24/09/2026), vẫn 1.000 chuyến / ngày.
# Bản số g nối tiếp năm đầu (g từ SO_BAN tới 4·SO_BAN − 1) nên mã phiếu, số chứng từ, token không trùng năm đầu.
NAM_THEM, DAU_THEM = 3, "2022-09-25"


def them_nam(cac_bang, doan=None):
    """Thêm 3 năm (bản g ∈ [SO_BAN, 4·SO_BAN)) rải đều 1.095 ngày từ 25/09/2022. `doan=(tu, den)`: chỉ số bản TRONG
    phần thêm (0 … 3·SO_BAN) — mỗi lượt vừa dưới 10 phút."""
    _nhan(cac_bang, None, NAM_THEM, DAU_THEM, 365 * NAM_THEM, doan)


def _nhan(cac_bang, g_goc, so_nam, dau, so_ngay, doan):
    from sqlalchemy import create_engine, text
    e = create_engine(url_db(DB_THU))
    with e.begin() as c:
        # _mau = 15 phiếu gốc, ghi MỘT lần lúc chưa nhân bản (sau đó bảng trips đã có 365.000 dòng)
        c.execute(text("CREATE TABLE IF NOT EXISTS _mau (id varchar PRIMARY KEY)"))
        if not c.execute(text("SELECT count(*) FROM _mau")).scalar():
            c.execute(text("INSERT INTO _mau SELECT id FROM trips"))
        mau = [r[0] for r in c.execute(text("SELECT id FROM _mau")).fetchall()]
    so_ban = -(-SO_PHIEU // len(mau))                 # bản / năm
    if g_goc is None:                                  # phần thêm năm: nối tiếp sau năm đầu
        g_goc, ban = so_ban, so_ban * so_nam
    else:
        ban = so_ban
    tu0, den0 = doan if doan else (0, ban)
    den0 = min(den0, ban)
    print("✓ %d phiếu mẫu × bản %d–%d (trong %d) = %d phiếu · từ %s, rải %d ngày"
          % (len(mau), tu0, den0 - 1, ban, len(mau) * (den0 - tu0), dau, so_ngay), flush=True)
    NGAY = "(DATE '%s' + ((g - %d) %% %d))" % (dau, g_goc, so_ngay)     # ngày của bản g

    def cot(c, bang):
        return c.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = :b ORDER BY ordinal_position"),
                         {"b": bang}).fetchall()

    DUY_NHAT = {("chung_tu", "so"): "x.so || '~' || g", ("vouchers", "token"): "md5(x.token || ':' || g)",
                ("trips", "doc_no"): "'L' || to_char(%s, 'YYMMDD') || '-' || g || '-' || substr(x.id, 1, 4)" % NGAY}
    XONG = "%s < CURRENT_DATE - 7" % NGAY      # phiếu cũ hơn 7 ngày: đã xong
    GHI_DE_PHIEU = {"transport_status": "CASE WHEN %s THEN 'arrived' ELSE x.transport_status END" % XONG,
                    "finance_status": "CASE WHEN %s THEN 'paid' ELSE x.finance_status END" % XONG,
                    "locked": "CASE WHEN %s THEN true ELSE x.locked END" % XONG,
                    "invoiced": "CASE WHEN %s THEN true ELSE x.invoiced END" % XONG,
                    "contract_id": "x.contract_id", "pod_ref": "NULL"}

    def mot_bang(bang, dieu_kien="x.trip_id IS NOT NULL"):
        with e.connect() as c:
            cs = cot(c, bang)
        chon = []
        for ten, kieu in cs:
            if ten == "id":
                chon.append("substr(md5(x.id || ':' || g), 1, 12)")
            elif ten in ("trip_id", "nguon_id", "expense_id"):     # cùng quy tắc đổi mã với bảng gốc → vẫn khớp nhau
                chon.append("CASE WHEN x.{0} IS NULL THEN NULL ELSE substr(md5(x.{0} || ':' || g), 1, 12) END".format(ten))
            elif (bang, ten) in DUY_NHAT:
                chon.append(DUY_NHAT[(bang, ten)])
            elif bang == "trips" and ten in GHI_DE_PHIEU:
                chon.append(GHI_DE_PHIEU[ten])
            elif kieu == "date":
                chon.append("x.%s + (%s - t.doc_date)" % (ten, NGAY))
            elif kieu.startswith("timestamp"):
                chon.append("x.%s + ((%s - t.doc_date) * INTERVAL '1 day')" % (ten, NGAY))
            else:
                chon.append("x.%s" % ten)
        noi = "trips x JOIN trips t ON t.id = x.id" if bang == "trips" else "%s x JOIN trips t ON t.id = x.trip_id" % bang
        t0 = time.time(); tong = 0
        buoc = 2000
        for tu in range(tu0, den0, buoc):
            den = min(den0, tu + buoc) - 1
            sql = ("INSERT INTO %s (%s) SELECT %s FROM %s JOIN _mau m ON m.id = t.id CROSS JOIN generate_series(%d, %d) g WHERE %s"
                   % (bang, ", ".join(c for c, _ in cs), ", ".join(chon), noi, g_goc + tu, g_goc + den,
                      dieu_kien if bang != "trips" else "true"))
            with e.begin() as c:
                tong += c.execute(text(sql)).rowcount
            print("  %-15s bản %6d–%6d · +%d dòng · %.0f s" % (bang, tu, den, tong, time.time() - t0), flush=True)
        return tong

    for bang in cac_bang:
        n = mot_bang(bang)
        print("✓ %-15s +%d dòng" % (bang, n), flush=True)


SO_XE = 500
GPS_NGAY = 30             # GPS cho phiếu 30 ngày gần nhất
GPS_DIEM = 150            # mỗi phiếu 150 điểm, cách nhau 25 giây (nhịp app tài xế)


def xe_tai_xe():
    """3 xe mẫu → 500 xe · 500 tài xế (kèm bằng lái), rồi chia 365.000 phiếu đều cho 500 xe."""
    from sqlalchemy import create_engine, text
    e = create_engine(url_db(DB_THU))
    t0 = time.time()
    with e.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS _xe AS
            WITH v AS (SELECT row_number() OVER (ORDER BY id) - 1 AS k, * FROM vehicles),
                 d AS (SELECT row_number() OVER (ORDER BY id) - 1 AS k, * FROM drivers)
            SELECT n, v.id AS v_goc, d.id AS d_goc,
                   CASE WHEN n < (SELECT count(*) FROM vehicles) THEN v.id ELSE substr(md5(v.id || '#xe' || n), 1, 12) END AS v_id,
                   CASE WHEN n < (SELECT count(*) FROM drivers) THEN d.id ELSE substr(md5(d.id || '#tx' || n), 1, 12) END AS d_id
            FROM generate_series(0, %d) n
            JOIN v ON v.k = n %% (SELECT count(*) FROM vehicles)
            JOIN d ON d.k = n %% (SELECT count(*) FROM drivers)""" % (SO_XE - 1)))
        cv = [r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='vehicles' ORDER BY ordinal_position"))]
        doi_v = {"id": "m.v_id", "truck_no": "(400 + m.n)::text", "trailer_id": "NULL",
                 "plate_head": "'T' || lpad(m.n::text, 4, '0') || '-HD'", "plate_trailer": "'T' || lpad(m.n::text, 4, '0') || '-HM'"}
        n = c.execute(text("INSERT INTO vehicles (%s) SELECT %s FROM _xe m JOIN vehicles x ON x.id = m.v_goc WHERE m.v_id <> m.v_goc ON CONFLICT DO NOTHING"
                           % (", ".join(cv), ", ".join(doi_v.get(k, "x." + k) for k in cv)))).rowcount
        cd = [r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='drivers' ORDER BY ordinal_position"))]
        doi_d = {"id": "m.d_id", "driver_code": "'TX' || lpad(m.n::text, 4, '0')", "name": "x.name || ' ' || m.n",
                 "phone": "'020' || lpad(m.n::text, 8, '0')", "id_card": "'CC' || m.n", "license_no": "'BL' || m.n",
                 "default_vehicle_id": "m.v_id"}
        n2 = c.execute(text("INSERT INTO drivers (%s) SELECT %s FROM _xe m JOIN drivers x ON x.id = m.d_goc WHERE m.d_id <> m.d_goc ON CONFLICT DO NOTHING"
                            % (", ".join(cd), ", ".join(doi_d.get(k, "x." + k) for k in cd)))).rowcount
        cl = [r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='driver_licenses' ORDER BY ordinal_position"))]
        doi_l = {"id": "substr(md5(x.id || '#bl' || m.n), 1, 12)", "driver_id": "m.d_id", "license_no": "'BL' || m.n"}
        c.execute(text("INSERT INTO driver_licenses (%s) SELECT %s FROM _xe m JOIN driver_licenses x ON x.driver_id = m.d_goc WHERE m.d_id <> m.d_goc ON CONFLICT DO NOTHING"
                       % (", ".join(cl), ", ".join(doi_l.get(k, "x." + k) for k in cl))))
    print("✓ +%d xe · +%d tài xế (tổng %d) · %.0f s" % (n, n2, SO_XE, time.time() - t0), flush=True)
    with e.connect() as c:
        lo, hi = c.execute(text("SELECT min(doc_date), max(doc_date) FROM trips")).one()
    t_lo, t_hi = lo.year * 12 + lo.month - 1, hi.year * 12 + hi.month - 1
    for thang in range(t_hi - t_lo + 1):  # chia phiếu theo từng tháng một cho mỗi lệnh UPDATE vừa phải
        tt = t_lo + thang
        if len(sys.argv) > 2 and sys.argv[2] and "%04d-%02d" % (tt // 12, tt % 12 + 1) < sys.argv[2]:
            continue                      # `xe YYYY-MM`: chỉ chia từ tháng đó trở đi (chia lượt)
        with e.begin() as c:
            k = c.execute(text("""UPDATE trips t SET vehicle_id = m.v_id, driver_id = m.d_id, truck_no = v.truck_no,
                    plate_head = v.plate_head, plate_trailer = v.plate_trailer, driver_name = d.name
                FROM _xe m JOIN vehicles v ON v.id = m.v_id JOIN drivers d ON d.id = m.d_id
                WHERE m.n = abs(hashtext(t.id)) % :sx AND t.doc_date >= CAST(:tu AS date) AND t.doc_date < CAST(:tu AS date) + INTERVAL '1 month'
                  AND t.id NOT IN (SELECT id FROM _mau)"""),
                {"sx": SO_XE, "tu": "%04d-%02d-01" % (tt // 12, tt % 12 + 1)}).rowcount
        print("  chia phiếu cho xe · %04d-%02d · %d phiếu · %.0f s" % (tt // 12, tt % 12 + 1, k, time.time() - t0), flush=True)
    with e.begin() as c:
        c.execute(text("UPDATE vouchers x SET driver_id = t.driver_id, truck_no = t.truck_no FROM trips t WHERE t.id = x.trip_id AND x.trip_id NOT IN (SELECT id FROM _mau)"))
    print("✓ phiếu lĩnh theo xe mới · %.0f s" % (time.time() - t0), flush=True)


def gps():
    """GPS: phiếu 30 ngày gần nhất × 150 điểm / phiếu, 25 giây một điểm, chạy dọc tuyến Thà Bốc → Viêng Chăn."""
    from sqlalchemy import create_engine, text
    e = create_engine(url_db(DB_THU))
    t0 = time.time(); tong = 0
    for lui in range(GPS_NGAY, -1, -1):
        with e.begin() as c:
            tong += c.execute(text("""INSERT INTO vehicle_positions (id, trip_id, vehicle_id, driver_id, ts, lat, lng, accuracy_m, speed_kmh, heading, source, by_user)
                SELECT substr(md5(t.id || '#gps' || i), 1, 12), t.id, t.vehicle_id, t.driver_id,
                       t.doc_date + TIME '06:00' + (abs(hashtext(t.id)) % 43200) * INTERVAL '1 second' + i * INTERVAL '25 second',
                       18.44 - i * 0.0012 + (random() - 0.5) * 0.0004, 103.15 - i * 0.0020 + (random() - 0.5) * 0.0004,
                       5 + random() * 10, 40 + random() * 30, NULL, 'driver_app', t.driver_name
                FROM trips t CROSS JOIN generate_series(0, :nd - 1) i
                WHERE t.doc_date = CURRENT_DATE - :lui AND t.id NOT IN (SELECT id FROM _mau)"""),
                {"nd": GPS_DIEM, "lui": lui}).rowcount
        print("  GPS ngày -%2d · tổng %d điểm · %.0f s" % (lui, tong, time.time() - t0), flush=True)
    print("✓ vehicle_positions +%d điểm" % tong, flush=True)


def gps_cu(tu, den):
    """GPS của các tháng CŨ đúng như sau khi luật thật đã chạy (tools/gps_thang.py thua · xoa): chỉ giữ 24 tháng, và điểm
    cũ hơn 30 ngày đã thưa còn 1 điểm / 5 phút / chuyến — tức mỗi chuyến ~13 điểm thay vì 150. `tu`, `den` là 'YYYY-MM'
    (gồm cả hai đầu) — mỗi lượt vài tháng cho dưới 10 phút. Tự dựng bảng con của từng tháng."""
    from sqlalchemy import create_engine, text
    import datetime as dt
    e = create_engine(url_db(DB_THU))
    t0, tong = time.time(), 0
    y, m = int(tu[:4]), int(tu[5:7])
    while "%04d-%02d" % (y, m) <= den:
        a = dt.date(y, m, 1)
        b = dt.date(y + (m == 12), m % 12 + 1, 1)
        with e.begin() as c:
            c.execute(text("CREATE TABLE IF NOT EXISTS vehicle_positions_%04d_%02d PARTITION OF vehicle_positions "
                           "FOR VALUES FROM ('%s') TO ('%s')" % (y, m, a.isoformat(), b.isoformat())))
            n = c.execute(text("""INSERT INTO vehicle_positions (id, trip_id, vehicle_id, driver_id, ts, lat, lng, accuracy_m, speed_kmh, heading, source, by_user)
                SELECT substr(md5(t.id || '#gpc' || i), 1, 12), t.id, t.vehicle_id, t.driver_id,
                       t.doc_date + TIME '06:00' + (abs(hashtext(t.id)) % 43200) * INTERVAL '1 second' + i * INTERVAL '5 minute',
                       18.44 - i * 0.0144 + (random() - 0.5) * 0.0004, 103.15 - i * 0.0240 + (random() - 0.5) * 0.0004,
                       5 + random() * 10, 40 + random() * 30, NULL, 'driver_app', t.driver_name
                FROM trips t CROSS JOIN generate_series(0, 12) i
                WHERE t.doc_date >= :a AND t.doc_date < :b AND t.id NOT IN (SELECT id FROM _mau)
                ON CONFLICT DO NOTHING"""), {"a": a, "b": b}).rowcount
        tong += n
        print("  GPS đã thưa · %04d-%02d · +%d điểm · tổng %d · %.0f s" % (y, m, n, tong, time.time() - t0), flush=True)
        y, m = (y + (m == 12), m % 12 + 1)
    print("✓ GPS cũ +%d điểm" % tong, flush=True)


def cu():
    """Phiếu lĩnh của phiếu cũ hơn 7 ngày: đã cấp (bản mẫu đang "chờ" — nhân nguyên ra thì cả năm còn 48.000 tờ chờ)."""
    from sqlalchemy import create_engine, text
    e = create_engine(url_db(DB_THU))
    with e.begin() as c:
        n = c.execute(text("""UPDATE vouchers v SET status = 'da_cap', granted_at = coalesce(v.issued_at, t.doc_date::timestamp),
                granted_qty = coalesce(v.granted_qty, v.qty_l), granted_by = coalesce(v.granted_by, 'thu tai')
            FROM trips t WHERE t.id = v.trip_id AND v.status = 'cho' AND t.doc_date < CURRENT_DATE - 7""")).rowcount
    print("✓ %d phiếu lĩnh cũ → đã cấp" % n, flush=True)
    with e.begin() as c:     # hoá đơn gộp không nhân bản — phiếu nhân bản không được dính vào tờ hoá đơn mẫu
        n = c.execute(text("UPDATE trips SET invoice_id = NULL WHERE invoice_id IS NOT NULL AND id NOT IN (SELECT id FROM _mau)")).rowcount
    print("✓ %d phiếu nhân bản gỡ khỏi hoá đơn gộp mẫu" % n, flush=True)
    with e.begin() as c:     # chủ xe được trả đều: phiếu liên kết cũ hơn 35 ngày nằm trong một đợt trả / chủ xe / tháng
        c.execute(text("""INSERT INTO owner_payments (id, owner_id, pay_date, amount, currency, rate_to_lak, amount_lak, method, note, by_user, created_at)
            SELECT substr(md5(owner_id || '#dot' || to_char(doc_date, 'YYYY-MM')), 1, 12), owner_id,
                   (date_trunc('month', doc_date) + INTERVAL '1 month')::date, 0, 'USD', 1, 0, 'bank', 'thu tai', 'thu tai', now()
            FROM trips WHERE company = 'joint' AND owner_id IS NOT NULL AND owner_payment_id IS NULL
                         AND doc_date < CURRENT_DATE - 35 AND id NOT IN (SELECT id FROM _mau)
            GROUP BY owner_id, to_char(doc_date, 'YYYY-MM'), date_trunc('month', doc_date)
            ON CONFLICT (id) DO NOTHING"""))
        n = c.execute(text("""UPDATE trips SET owner_payment_id = substr(md5(owner_id || '#dot' || to_char(doc_date, 'YYYY-MM')), 1, 12),
                owner_paid = true
            WHERE company = 'joint' AND owner_id IS NOT NULL AND owner_payment_id IS NULL
              AND doc_date < CURRENT_DATE - 35 AND id NOT IN (SELECT id FROM _mau)""")).rowcount
    print("✓ %d phiếu liên kết cũ → đã trả chủ xe (đợt theo tháng)" % n, flush=True)


def xong():
    from sqlalchemy import create_engine, text
    e = create_engine(url_db(DB_THU))
    with e.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        c.execute(text("ANALYZE"))
        print("✓ ANALYZE · dung lượng %s: %s" % (DB_THU, c.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()))


def xoa():
    from sqlalchemy import create_engine, text
    e = create_engine(url_db("postgres"), isolation_level="AUTOCOMMIT")
    with e.connect() as c:
        c.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :d AND pid <> pg_backend_pid()"), {"d": DB_THU})
        c.execute(text('DROP DATABASE IF EXISTS "%s"' % DB_THU))
    print("✓ đã xoá DB thử %s" % DB_THU)


if __name__ == "__main__":
    lenh = sys.argv[1] if len(sys.argv) > 1 else ""
    if lenh == "chep":
        tao_lai()
    elif lenh == "nhan":
        nhan_ban(sys.argv[2:])
    elif lenh == "them":                 # them <bang> [tu] [den]
        them_nam([sys.argv[2]], (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else None)
    elif lenh == "xe":
        xe_tai_xe()
    elif lenh == "gps":
        gps()
    elif lenh == "cu":
        cu()
    elif lenh == "gps_cu":               # gps_cu YYYY-MM YYYY-MM
        gps_cu(sys.argv[2], sys.argv[3])
    elif lenh == "xong":
        xong()
    elif lenh == "xoa":
        xoa()
    else:
        print(__doc__)
