import sqlite3

import pytest

from migrations import v021_vehicle_maintenance
from migrations.runner import required_migration_head


def test_v021_creates_vehicle_maintenance_ledger_and_constraints(tmp_path):
    connection = sqlite3.connect(tmp_path / "v021.db")
    connection.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE vehicles (id TEXT PRIMARY KEY);
        INSERT INTO vehicles(id) VALUES ('VEH-01');
    """)
    v021_vehicle_maintenance.upgrade_sqlite(connection)
    connection.execute("""
        INSERT INTO vehicle_maintenance_requests(
            id, request_no, vehicle_id, planned_start, planned_end, description
        ) VALUES ('MR-1','REQ-1','VEH-01','2026-08-21 08:00','2026-08-21 12:00','Thay phanh')
    """)
    connection.execute("""
        INSERT INTO vehicle_maintenance_cost_lines(
            request_id, description, quantity, estimated_unit_cost, estimated_total
        ) VALUES ('MR-1','Bo phanh',2,750000,1500000)
    """)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("""
            INSERT INTO vehicle_maintenance_requests(
                id, request_no, vehicle_id, planned_start, planned_end, description
            ) VALUES ('MR-2','REQ-2','VEH-01','2026-08-21 12:00','2026-08-21 08:00','Sai khoang gio')
        """)
    assert required_migration_head() == "025_vehicle_depot"
    connection.close()
