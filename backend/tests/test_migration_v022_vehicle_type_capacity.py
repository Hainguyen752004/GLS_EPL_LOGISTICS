import sqlite3

from migrations import v022_vehicle_type_capacity


def test_v022_adds_vehicle_type_volume_and_pallet_capacity():
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE vehicle_types (id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL, max_weight FLOAT DEFAULT 0)')

    v022_vehicle_type_capacity.upgrade_sqlite(connection)

    columns = {row[1] for row in connection.execute('PRAGMA table_info("vehicle_types")')}
    assert {'volume_capacity_m3', 'pallet_capacity'} <= columns
    v022_vehicle_type_capacity.upgrade_sqlite(connection)
    connection.close()


def test_v022_skips_legacy_database_without_vehicle_type_table():
    connection = sqlite3.connect(':memory:')
    v022_vehicle_type_capacity.upgrade_sqlite(connection)
    v022_vehicle_type_capacity.validate_sqlite(connection)
    v022_vehicle_type_capacity.rollback_sqlite(connection)
    connection.close()
