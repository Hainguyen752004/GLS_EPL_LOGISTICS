import sqlite3

from migrations.runner import required_migration_head, upgrade


def test_v008_is_head_and_adds_driver_photo_url_without_losing_vehicle_images(tmp_path):
    path = tmp_path / "driver-images.db"
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE quotations (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE sales_orders (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE delivery_orders (id TEXT PRIMARY KEY, so_id TEXT, customer_id TEXT, status TEXT);
        CREATE TABLE ar_invoices (id TEXT PRIMARY KEY, do_id TEXT, customer_id TEXT, amount REAL, vat_pct REAL, vat_amount REAL, total REAL, status TEXT);
        CREATE TABLE gl_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT, date TEXT, account_code TEXT, debit REAL, credit REAL);
        CREATE TABLE vehicles (
            id TEXT PRIMARY KEY,
            brand TEXT,
            type TEXT,
            weight_capacity REAL,
            image_url TEXT
        );
        CREATE TABLE drivers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT,
            license_type TEXT,
            phone TEXT,
            assigned_vehicle TEXT,
            shift TEXT,
            status TEXT
        );
        INSERT INTO vehicles(id, image_url) VALUES ('51C-268.89', '/uploads/vehicles/51c.jpg');
        INSERT INTO drivers(id, name) VALUES ('DRV-001', 'Nguyá»…n VÄƒn Minh');
    """)
    connection.commit()
    connection.close()

    assert upgrade(str(path))[-1] == "022_vehicle_type_capacity"
    assert required_migration_head() == "022_vehicle_type_capacity"

    with sqlite3.connect(path) as migrated:
        driver_columns = {row[1] for row in migrated.execute('PRAGMA table_info("drivers")')}
        vehicle_columns = {row[1] for row in migrated.execute('PRAGMA table_info("vehicles")')}
        assert "photo_url" in driver_columns
        assert "image_url" in vehicle_columns
        assert migrated.execute("SELECT image_url FROM vehicles WHERE id='51C-268.89'").fetchone() == ("/uploads/vehicles/51c.jpg",)
        assert migrated.execute("SELECT photo_url FROM drivers WHERE id='DRV-001'").fetchone() == (None,)


def test_v008_sqlite_upgrade_is_idempotent_when_columns_already_exist(tmp_path):
    path = tmp_path / "driver-images-idempotent.db"
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE quotations (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE sales_orders (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE delivery_orders (id TEXT PRIMARY KEY, so_id TEXT, customer_id TEXT, status TEXT);
        CREATE TABLE ar_invoices (id TEXT PRIMARY KEY, do_id TEXT, customer_id TEXT, amount REAL, vat_pct REAL, vat_amount REAL, total REAL, status TEXT);
        CREATE TABLE gl_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT, date TEXT, account_code TEXT, debit REAL, credit REAL);
        CREATE TABLE vehicles (id TEXT PRIMARY KEY, image_url TEXT);
        CREATE TABLE drivers (id TEXT PRIMARY KEY, name TEXT NOT NULL, photo_url TEXT);
    """)
    connection.commit()
    connection.close()

    upgrade(str(path))
    assert upgrade(str(path)) == []

    with sqlite3.connect(path) as migrated:
        assert [row[1] for row in migrated.execute('PRAGMA table_info("drivers")')].count("photo_url") == 1
        assert [row[1] for row in migrated.execute('PRAGMA table_info("vehicles")')].count("image_url") == 1

