"""Điều xe không được đặt một xe vào hai chuyến chồng thời gian.

Kiểm tra chồng lịch trong dispatch_trip là thao tác đọc-rồi-ghi. Trên SQLite,
SELECT ... FOR UPDATE bị bỏ qua trong im lặng, nên hai phiên song song cùng đọc
"chưa có ai đặt", cùng ghi, và một chiếc xe nằm trên hai chuyến đang chạy.
"""

import importlib

import pytest


def test_dispatch_takes_the_sqlite_write_lock_before_reading(monkeypatch):
    """Trên SQLite phải lấy BEGIN IMMEDIATE trước mọi thao tác đọc.

    Đây là điều duy nhất khiến hai phiên cạnh tranh bị tuần tự hóa: nếu không,
    cả hai cùng thấy lịch trống rồi cùng ghi.
    """
    dispatch = importlib.import_module("services.tms_dispatch_service")

    executed = []

    class FakeConnection:
        def exec_driver_sql(self, sql):
            executed.append(sql)

    class FakeDialect:
        name = "sqlite"

    class FakeBind:
        dialect = FakeDialect()

    class FakeSession:
        def get_bind(self):
            return FakeBind()

        def in_transaction(self):
            return False

        def connection(self):
            return FakeConnection()

        def query(self, *_args, **_kwargs):
            raise RuntimeError("dừng lại sau khi đã lấy khóa")

    with pytest.raises(RuntimeError):
        dispatch.dispatch_trip(FakeSession(), "TRIP-X", {})

    assert executed == ["BEGIN IMMEDIATE"], (
        "phải lấy khóa ghi của SQLite TRƯỚC khi đọc, nếu không hai phiên song "
        f"song đều thấy lịch trống; thực tế đã chạy: {executed}"
    )


def test_postgres_relies_on_row_locks_not_begin_immediate():
    """Trên PostgreSQL không được phát BEGIN IMMEDIATE.

    Đó là cú pháp riêng của SQLite. PostgreSQL đã có khóa hàng thật qua
    FOR UPDATE trên xe và tài xế — đúng những tài nguyên xuất hiện trong điều
    kiện kiểm chồng lịch — nên phiên thứ hai phải chờ rồi đọc được bản ghi đã
    commit của phiên thứ nhất.
    """
    dispatch = importlib.import_module("services.tms_dispatch_service")

    executed = []

    class FakeDialect:
        name = "postgresql"

    class FakeBind:
        dialect = FakeDialect()

    class FakeSession:
        def get_bind(self):
            return FakeBind()

        def in_transaction(self):
            return False

        def connection(self):
            raise AssertionError("không được chạm connection trên PostgreSQL")

        def query(self, *_args, **_kwargs):
            raise RuntimeError("dừng lại")

    with pytest.raises(RuntimeError):
        dispatch.dispatch_trip(FakeSession(), "TRIP-X", {})

    assert executed == []


def test_lock_is_not_taken_twice_inside_an_existing_transaction():
    """Đang trong giao dịch rồi thì không phát lại BEGIN IMMEDIATE."""
    dispatch = importlib.import_module("services.tms_dispatch_service")

    class FakeDialect:
        name = "sqlite"

    class FakeBind:
        dialect = FakeDialect()

    class FakeSession:
        def get_bind(self):
            return FakeBind()

        def in_transaction(self):
            return True

        def connection(self):
            raise AssertionError("đã ở trong giao dịch, không được lấy khóa lại")

        def query(self, *_args, **_kwargs):
            raise RuntimeError("dừng lại")

    with pytest.raises(RuntimeError):
        dispatch.dispatch_trip(FakeSession(), "TRIP-X", {})
