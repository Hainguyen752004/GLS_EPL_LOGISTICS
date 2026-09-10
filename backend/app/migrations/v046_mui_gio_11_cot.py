"""Doi 11 cot moc thoi gian sang TIMESTAMPTZ cho khop voi models.py.

VI SAO. Bai kiem khop schema (`test_schema_postgres_khop_voi_models.py`) truoc
day tim chu "timezone=true" trong `str(kieu)` — chuoi do KHONG BAO GIO co, nen
11 cot duoi day lech ma bai kiem lang le cho qua suot. Ngay 10/09 bai kiem doi
sang doc thuoc tinh `timezone` va 11 cot lo ra: models.py khai
`DateTime(timezone=True)`, PostgreSQL that lai la `timestamp without time zone`.

VI SAO LECH LA LOI THAT, khong phai chuyen hinh thuc. Cung mot moc `datetime` co
mui gio ghi vao cot tran thi PostgreSQL BO PHAN MUI GIO va giu gio dong ho — moc
ghi 23:11+07 doc ra thanh 23:11 khong mui, roi `_utc()` coi no la UTC: lech dung
7 gio. Du an da vap dung loi nay o `freight_orders` (xem ghi chu dai trong
`tms_trip_service.create_trip_from_delivery_orders`). Quy uoc cua du an la LUU
UTC, nen `USING <cot> AT TIME ZONE 'UTC'` la phep doi dung: gia tri tran dang
co duoc hieu la UTC, khong bi dich them lan nao.

Sua xong thi XOA 11 ten nay khoi `LECH_MUI_GIO_DA_BIET` — de nguyen la bai kiem
lai lang le cho qua.
"""

VERSION = "046_mui_gio_11_cot"

COT = (
    ("delivery_pod_records", "created_at"),
    ("parking_events", "occurred_at"),
    ("parking_labels", "printed_at"),
    ("parking_lists", "created_at"),
    ("parking_lists", "updated_at"),
    ("transport_demands", "created_at"),
    ("transport_demands", "updated_at"),
    ("vehicle_maintenance_requests", "planned_start"),
    ("vehicle_maintenance_requests", "planned_end"),
    ("vehicle_maintenance_requests", "actual_start"),
    ("vehicle_maintenance_requests", "actual_end"),
)


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        return [
            "ALTER TABLE %s ALTER COLUMN %s TYPE TIMESTAMP WITHOUT TIME ZONE USING %s AT TIME ZONE 'UTC'"
            % (b, c, c) for b, c in COT
        ]
    # Chi doi khi cot con la kieu tran — chay lai mot moc da ap thi khong dich
    # gia tri them lan nua.
    return [
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = '%s' "
        "AND column_name = '%s' AND data_type = 'timestamp without time zone') THEN "
        "ALTER TABLE %s ALTER COLUMN %s TYPE TIMESTAMP WITH TIME ZONE USING %s AT TIME ZONE 'UTC'; "
        "END IF; END $$;" % (b, c, b, c, c)
        for b, c in COT
    ]


def upgrade_sqlite(connection):
    # SQLite khong co kieu thoi gian that; du an da ngung SQLite. Khong lam gi.
    return None

def rollback_sqlite(connection):
    # Khong doi gi o buoc nang cap nen cung khong co gi de lui.
    return


def validate_sqlite(connection):
    return
