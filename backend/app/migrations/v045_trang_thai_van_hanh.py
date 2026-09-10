"""Trang thai van hanh cua XE va TAI XE la MA CHUAN, khong con la nhan chu.

VI SAO. Cot `vehicles.status` va `drivers.status` tu truoc den nay la mot chuoi
tieng Viet do MA GHI CUNG: "Sẵn sàng", "Đang thực hiện TRIP-…", "🟢 Rảnh (Sẵn
sàng)". Chu du an nhin vao va noi dung: *"cái nhãn thì hardcode quá"*. Ba dieu
sai voi nhan chu, ca ba da do duoc tren du lieu that:

  1. Nhan la de HIEN, khong phai de QUYET. Sua chu "Sẵn sàng" trong Du lieu goc
     la moi xe thanh khong dieu duoc; ban tieng Lao khong khop chuoi nao.
  2. Nhan khong co chieu thoi gian, nen khong tra loi duoc "xe nay co ranh sang
     mai 6h–14h khong".
  3. Nhan troi: mot duong ghi cu dat "Đang thực hiện X" roi khong tra lai, xe
     do roi khoi doi vinh vien du khong con phan cong nao.

Cua dieu phoi da chuyen sang doc LICH (`services/lich_xe.py`). Moc nay lam not
phan con lai: trang thai van hanh thanh MOT MA CHUAN, luu trong cot rieng, do
he thong cap nhat theo lich (dieu xe, xe ve, huy chuyen, lich xuong) VA nguoi
dung cap nhat duoc bang tay (dua xe ra khoi doi / dua lai; cho tai xe nghi
viec / lam lai). Chu hien ra thi lay tu `lang.json` theo ma — dich duoc.

    vehicles.operational_status : available | on_trip | maintenance | out_of_service
    drivers.operational_status  : available | on_trip | off_duty | inactive

`operational_ref` la ma chuyen / phieu xuong dang giu; `operational_note` la ly
do khi nguoi dung dat tay; `operational_updated_at` la moc ghi.

Cot `status` cu GIU LAI va van duoc chieu tu ma (cho nhung cho hien thi chua doi),
nhung khong con cho nao QUYET DINH dua vao no.

Backfill MOT LAN tu nhan cu, de du lieu dang co khong bat dau bang mot cot rong.
"""

VERSION = "045_trang_thai_van_hanh"

XE = (
    "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS operational_status VARCHAR(32) NOT NULL DEFAULT 'available'",
    "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS operational_ref VARCHAR(128)",
    "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS operational_note TEXT",
    "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS operational_updated_at TIMESTAMPTZ",
    # Backfill tu nhan cu, chi khi cot moi con o gia tri mac dinh.
    "UPDATE vehicles SET operational_status = CASE "
    "WHEN status ILIKE 'Bảo dưỡng%' OR status ILIKE '%bảo dưỡng%' OR status ILIKE '%sửa chữa%' THEN 'maintenance' "
    "WHEN status ILIKE 'Đang thực hiện%' OR status ILIKE 'Đang vận chuyển%' THEN 'on_trip' "
    "WHEN status ILIKE 'Ngưng%' OR status ILIKE '%ngoài đội%' OR status ILIKE 'inactive%' THEN 'out_of_service' "
    "ELSE 'available' END, "
    "operational_ref = CASE WHEN status ILIKE 'Đang thực hiện %' THEN NULLIF(TRIM(SUBSTRING(status FROM 16)), '') END "
    "WHERE operational_updated_at IS NULL",
    "ALTER TABLE vehicles DROP CONSTRAINT IF EXISTS ck_vehicles_operational_status",
    "ALTER TABLE vehicles ADD CONSTRAINT ck_vehicles_operational_status CHECK "
    "(operational_status IN ('available','on_trip','maintenance','out_of_service'))",
)

TAI_XE = (
    "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS operational_status VARCHAR(32) NOT NULL DEFAULT 'available'",
    "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS operational_ref VARCHAR(128)",
    "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS operational_note TEXT",
    "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS operational_updated_at TIMESTAMPTZ",
    "UPDATE drivers SET operational_status = CASE "
    "WHEN status ILIKE '%Đang thực hiện%' OR status ILIKE '%Đang vận chuyển%' OR status ILIKE '%theo xe%' THEN 'on_trip' "
    "WHEN status ILIKE '%Nghỉ%' THEN 'off_duty' "
    "WHEN status ILIKE '%nghỉ việc%' OR status ILIKE 'inactive%' THEN 'inactive' "
    "ELSE 'available' END "
    "WHERE operational_updated_at IS NULL",
    "ALTER TABLE drivers DROP CONSTRAINT IF EXISTS ck_drivers_operational_status",
    "ALTER TABLE drivers ADD CONSTRAINT ck_drivers_operational_status CHECK "
    "(operational_status IN ('available','on_trip','off_duty','inactive'))",
)

ROLLBACK = (
    "ALTER TABLE vehicles DROP CONSTRAINT IF EXISTS ck_vehicles_operational_status",
    "ALTER TABLE drivers DROP CONSTRAINT IF EXISTS ck_drivers_operational_status",
) + tuple(
    "ALTER TABLE %s DROP COLUMN IF EXISTS %s" % (b, c)
    for b in ("vehicles", "drivers")
    for c in ("operational_status", "operational_ref", "operational_note", "operational_updated_at")
)


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        return list(ROLLBACK)
    return list(XE + TAI_XE)


# --------------------------------------------------------------------- SQLite --
# Giu cho du hinh voi cac moc khac; du an da ngung SQLite hoan toan.

def _co_cot_sqlite(connection, bang, cot):
    return any(r[1] == cot for r in connection.execute('PRAGMA table_info("%s")' % bang))


def upgrade_sqlite(connection):
    for bang in ("vehicles", "drivers"):
        if not list(connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % bang)):
            continue
        for cot, kieu in (("operational_status", "VARCHAR(32) NOT NULL DEFAULT 'available'"),
                          ("operational_ref", "VARCHAR(128)"),
                          ("operational_note", "TEXT"),
                          ("operational_updated_at", "TIMESTAMP")):
            if not _co_cot_sqlite(connection, bang, cot):
                connection.execute("ALTER TABLE %s ADD COLUMN %s %s" % (bang, cot, kieu))

def rollback_sqlite(connection):
    # SQLite khong xoa cot don le mot cach an toan; du an da ngung SQLite.
    return


def validate_sqlite(connection):
    return
