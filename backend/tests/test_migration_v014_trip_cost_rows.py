import sqlite3

from sqlalchemy import create_engine

from migrations.runner import MIGRATIONS, required_migration_head, upgrade
from models import Base


def test_v014_adds_delivery_cost_row_columns_and_is_idempotent(tmp_path):
    database = tmp_path / "v014.db"
    engine = create_engine(f"sqlite:///{database}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()

    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.executemany(
            "INSERT INTO schema_migrations(version) VALUES (?)",
            [(migration.VERSION,) for migration in MIGRATIONS if migration.VERSION < "014_trip_cost_rows"],
        )
        for column in ("note", "increase_amount", "actual_amount", "original_amount"):
            connection.execute(f'ALTER TABLE freight_charge_items DROP COLUMN "{column}"')
        connection.commit()

    # Khong ghim TEN moc cuoi: y cua phep kiem la "chay het chuoi thi toi dung
    # moc ma `required_migration_head()` khai", chu khong phai "moc cuoi la 031".
    # Ghim ten thi them mot moc moi la bai do ngay, vi mot ly do khong lien quan
    # gi toi dieu no muon giu.
    da_ap = upgrade(str(database))
    assert da_ap[0] == "014_trip_cost_rows"
    assert da_ap[-1] == required_migration_head()
    # Va chuoi phai LIEN TUC, khong nhay moc: so thu tu tang dung mot moi buoc.
    so = [int(x.split("_")[0]) for x in da_ap]
    assert so == list(range(so[0], so[0] + len(so))), da_ap
    assert upgrade(str(database)) == []

    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute('PRAGMA table_info("freight_charge_items")')}
    assert {"original_amount", "actual_amount", "increase_amount", "note"} <= columns
