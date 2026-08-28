import sqlite3

from migrations import v019_driver_availability


def test_v019_adds_driver_availability_with_work_default():
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            "CREATE TABLE driver_shift_assignments (id TEXT PRIMARY KEY, driver_id TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO driver_shift_assignments(id, driver_id) VALUES ('SHIFT-1', 'DRV-1')"
        )

        v019_driver_availability.upgrade_sqlite(connection)

        columns = {
            row[1]: row for row in connection.execute(
                'PRAGMA table_info("driver_shift_assignments")'
            )
        }
        value = connection.execute(
            "SELECT availability_kind FROM driver_shift_assignments WHERE id = 'SHIFT-1'"
        ).fetchone()[0]

        assert "availability_kind" in columns
        assert value == "work"
    finally:
        connection.close()
