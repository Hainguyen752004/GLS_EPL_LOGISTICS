"""Cột bãi / chi nhánh của phương tiện.

Chủ dự án vận hành khoảng 500 xe nằm ở nhiều bãi và nhiều chi nhánh. Bảng
`vehicles` trước đó không có trường nào cho việc đó — chỉ có `inspection_place`,
vốn là nơi đăng kiểm chứ không phải nơi xe đậu. Ở quy mô 500 xe thì bãi là bộ
lọc chính, nên thiếu cột này là thiếu ở mô hình dữ liệu chứ không phải ở giao
diện.
"""
import sqlite3

import pytest
from sqlalchemy import create_engine

from migrations import v025_vehicle_depot as v025
from migrations.runner import MIGRATIONS, required_migration_head, upgrade
from models import Base


def _fleet_db():
    """Kết nối sqlite3 thuần — đúng loại đối tượng mà runner truyền vào."""
    connection = sqlite3.connect(':memory:')
    connection.execute(
        'CREATE TABLE vehicles ('
        ' id VARCHAR PRIMARY KEY, brand VARCHAR, type VARCHAR,'
        ' inspection_place VARCHAR)'
    )
    return connection


def _columns(connection):
    return {row[1] for row in connection.execute('PRAGMA table_info("vehicles")')}


def test_v025_is_the_registered_head():
    assert required_migration_head() == v025.VERSION
    assert MIGRATIONS[-1] is v025


def test_upgrade_adds_both_columns_and_is_idempotent():
    connection = _fleet_db()
    v025.upgrade_sqlite(connection)
    v025.upgrade_sqlite(connection)  # chạy lại không được vỡ
    assert {'depot', 'depot_code'} <= _columns(connection)
    connection.close()


def test_existing_vehicles_are_left_unassigned():
    """Không bịa ra một bãi mặc định.

    Đặt sẵn "Bãi trung tâm" cho 500 xe cũ sẽ làm chúng trông như đã được khai
    báo, trong khi thật ra chưa ai gán — rồi bộ lọc bãi sẽ nói dối ngay từ ngày
    đầu.
    """
    connection = _fleet_db()
    connection.execute("INSERT INTO vehicles (id, brand) VALUES ('51C-123.45', 'Hyundai')")
    v025.upgrade_sqlite(connection)
    assert connection.execute('SELECT depot, depot_code FROM vehicles').fetchone() == (None, None)
    connection.close()


def test_rollback_removes_the_columns():
    connection = _fleet_db()
    v025.upgrade_sqlite(connection)
    v025.rollback_sqlite(connection)
    assert not ({'depot', 'depot_code'} & _columns(connection))
    connection.close()


def test_validator_flags_a_half_applied_schema():
    """Chạy nửa chừng thì phải kêu, không im lặng cho qua."""
    connection = _fleet_db()
    connection.execute('ALTER TABLE vehicles ADD COLUMN depot VARCHAR')
    with pytest.raises(RuntimeError, match='depot'):
        v025.validate_sqlite(connection)
    connection.close()


def test_migration_skips_a_database_without_the_vehicles_table():
    """Cơ sở dữ liệu trống thì không có gì để làm, và cũng không có gì để kiểm.

    Bắt lỗi ở đây sẽ chặn đúng lúc khởi tạo một cơ sở dữ liệu mới.
    """
    connection = sqlite3.connect(':memory:')
    v025.upgrade_sqlite(connection)
    v025.validate_sqlite(connection)
    v025.rollback_sqlite(connection)
    connection.close()


def test_postgres_statements_are_reversible_and_guarded():
    up = v025.statements('postgresql')
    down = v025.statements('postgresql', direction='rollback')

    # IF NOT EXISTS / IF EXISTS: chạy lại trên cơ sở dữ liệu đã nâng cấp không vỡ.
    assert all('IF NOT EXISTS' in sql for sql in up)
    assert all('IF EXISTS' in sql for sql in down)

    # Lọc theo bãi là thao tác thường xuyên nhất trên đội 500 xe, nên phải có index.
    assert any('CREATE INDEX' in sql and 'depot_code' in sql for sql in up)

    # Gỡ phải theo thứ tự ngược lại với thêm.
    assert down[0].endswith('depot_code')
    assert down[1].endswith('depot')


def test_full_upgrade_chain_reaches_v025(tmp_path):
    """Chay het chuoi migration tren mot co so du lieu da o v024.

    Khong dung mot tep sqlite trong: v001 mong doi mot luoc do cu san co. Co so
    du lieu hoan toan moi di theo duong baseline trong database.py, khong phai
    duong nay.
    """
    database = tmp_path / 'chain.sqlite3'
    engine = create_engine(f'sqlite:///{database}')
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()

    with sqlite3.connect(database) as connection:
        connection.execute(
            'CREATE TABLE schema_migrations (version TEXT PRIMARY KEY,'
            ' applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)'
        )
        connection.executemany(
            'INSERT INTO schema_migrations(version) VALUES (?)',
            [(m.VERSION,) for m in MIGRATIONS if m.VERSION < v025.VERSION],
        )
        # Bỏ hai cột đi để v025 thật sự có việc để làm. Phải bỏ index trước:
        # models.py khai depot_code là index=True nên create_all đã dựng sẵn
        # ix_vehicles_depot_code, và sqlite từ chối bỏ cột mà một index đang dùng.
        connection.execute('DROP INDEX IF EXISTS ix_vehicles_depot_code')
        connection.execute('ALTER TABLE vehicles DROP COLUMN depot_code')
        connection.execute('ALTER TABLE vehicles DROP COLUMN depot')
        connection.commit()

    assert upgrade(str(database)) == [v025.VERSION]
    assert upgrade(str(database)) == [], 'chay lai khong duoc lam gi nua'

    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute('PRAGMA table_info("vehicles")')}
    assert {'depot', 'depot_code'} <= columns
