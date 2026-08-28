import sqlite3


def test_v018_adds_optional_co_driver_columns():
    from migrations import v018_dispatch_crew

    connection = sqlite3.connect(":memory:")
    connection.executescript("""
        CREATE TABLE drivers (id TEXT PRIMARY KEY);
        CREATE TABLE delivery_orders (id TEXT PRIMARY KEY, co_driver TEXT);
        CREATE TABLE transport_trips (id TEXT PRIMARY KEY);
        CREATE TABLE resource_assignments (
            id INTEGER PRIMARY KEY,
            assignment_start TEXT NOT NULL,
            assignment_end TEXT NOT NULL
        );
    """)

    v018_dispatch_crew.upgrade_sqlite(connection)

    trip_columns = {row[1] for row in connection.execute('PRAGMA table_info("transport_trips")')}
    assignment_columns = {row[1] for row in connection.execute('PRAGMA table_info("resource_assignments")')}
    assert "co_driver_id" in trip_columns
    assert "co_driver_id" in assignment_columns
