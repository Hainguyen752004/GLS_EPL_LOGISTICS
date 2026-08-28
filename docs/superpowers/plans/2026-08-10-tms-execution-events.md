# TMS Core 4 Execution Events Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng event store vận tải/GPS bất biến cho Freight Order, có state machine, idempotency, projection tương thích GPS/POD và migration PostgreSQL `006`.

**Architecture:** `TransportEvent` và `TransportEventDocument` là nguồn sự thật chỉ ghi thêm. Service khóa Freight Order, kiểm tra version/thứ tự/assignment, ghi event và cập nhật projection cũ trong cùng transaction; router chỉ điều phối HTTP và chuẩn hóa lỗi.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL production, SQLite test cô lập, pytest.

---

## Chunk 1: Event domain và state machine

### Task 1: Model và hành vi ghi sự kiện

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/services/tms_execution_service.py`
- Create: `backend/tests/test_tms_execution_events.py`

- [ ] Viết test fail cho event đầu tiên chỉ được là `check_in` khi Freight Order đang `dispatched` và có assignment active.
- [ ] Viết riêng các RED tests: bỏ bước trả `EVENT_SEQUENCE_INVALID`; lặp event chính trả `EVENT_ALREADY_RECORDED`; thời gian lùi trả `EVENT_TIME_REGRESSION`; exception chỉ được ghi khi FO đang thực thi và bắt buộc có `reason`; source `manual` dùng principal tin cậy.
- [ ] Chạy `python -m pytest backend/tests/test_tms_execution_events.py -q`; expected FAIL do thiếu `TransportEvent`/service, không phải lỗi fixture.
- [ ] Thêm `TransportEvent` với các trường `id`, `freight_order_id`, `event_type`, `event_time`, `lat`, `lng`, `speed_kmh`, `distance_km`, `location_text`, `source`, `device_id`, `reason`, `note`, `idempotency_key`, `payload_hash`, `recorded_at`, `recorded_by`; unique `(freight_order_id, idempotency_key)`.
- [ ] Thêm `TransportEventDocument` với metadata chứng từ và quan hệ tới event; thêm `FreightOrderLegacyLink(freight_order_id PK/FK, delivery_order_id UNIQUE/FK)` làm cầu nối projection xác định.
- [ ] Cài state sequence `check_in, pickup, departure, arrival, unloading, delivered`; event ngoại lệ không đổi trạng thái.
- [ ] Kiểm tra `expected_version`, row lock Freight Order, assignment active, vehicle/driver khớp, thời gian không lùi và event chính không lặp.
- [ ] Mỗi event thành công tạo đúng một `AuditLog`; event bị từ chối không tạo audit và không đổi FO/version.
- [ ] Chạy `python -m pytest backend/tests/test_tms_execution_events.py -q`; expected PASS.
- [ ] Checkpoint: ghi lại RED/GREEN trong output; workspace không có Git nên không tạo commit.

### Task 2: Validation GPS, nguồn và POD

**Files:**
- Modify: `backend/app/services/tms_execution_service.py`
- Modify: `backend/tests/test_tms_execution_events.py`

- [ ] Viết test fail cho NaN/vượt biên tọa độ, tốc độ/quãng đường âm, source `device` thiếu `device_id`.
- [ ] Viết test fail cho `delivered` thiếu document `pod` và document thiếu URL/checksum.
- [ ] Viết test fail cho exception thiếu reason, manual source thiếu actor và event vượt ngưỡng tương lai `TMS_EVENT_FUTURE_TOLERANCE_SECONDS` (mặc định 300 giây).
- [ ] Chạy `python -m pytest backend/tests/test_tms_execution_events.py -k "validation or pod or source" -q`; expected FAIL với mã mong đợi.
- [ ] Cài validation hữu hạn/biên, cấu hình ngưỡng tương lai đọc từ environment, source và metadata POD; thông báo lỗi tiếng Việt ổn định, không ghép exception/SQL vào response.
- [ ] Chạy lại đúng lệnh; expected PASS.

## Chunk 2: Idempotency, projection và API

### Task 3: Idempotency và projection tương thích

**Files:**
- Modify: `backend/app/services/tms_execution_service.py`
- Modify: `backend/tests/test_tms_execution_events.py`

- [ ] Viết test fail: cùng key+cùng payload trả event cũ, không tăng version/audit; cùng key+payload khác trả `IDEMPOTENCY_KEY_REUSED`.
- [ ] Viết test hai session/thread cùng gửi một key: đúng một event/audit, request còn lại replay; hai key cùng expected_version: đúng một transition, request còn lại `VERSION_CONFLICT`.
- [ ] Viết test fail: GPS event cập nhật `vehicle_tracking`; delivered tạo/cập nhật `pod` sau khi event/document hợp lệ.
- [ ] Fixture tạo rõ `FreightOrderLegacyLink(FO-EXEC-1, DO-LEGACY-1)`; khi thiếu link, assert không ghi bảng cũ nhưng latest-position vẫn trả event mới.
- [ ] Chạy RED: `python -m pytest backend/tests/test_tms_execution_events.py -k "idempotency or concurrent or projection or rollback" -q`; expected FAIL do chưa có savepoint/projection và atomic rollback.
- [ ] Viết test rollback cưỡng bức sau flush: event/document/audit, FO status/version, `vehicle_tracking` và `pod` đều không được lưu một phần.
- [ ] Cài canonical payload hash trên event. Dùng savepoint (`begin_nested`) cho insert idempotency; sau unique conflict rollback savepoint rồi re-read theo key/hash, không rollback transaction đã commit của request khác.
- [ ] Mapping projection: tra `FreightOrderLegacyLink` theo FO; event GPS mới nhất ghi `VehicleTracking.do_id=link.delivery_order_id`, assignment.vehicle, lat/lng/speed, remaining distance, ETA và last_update; delivered document `pod` ghi `POD.do_id=link.delivery_order_id`, delivery_time/photo_url/signature_url/note. Nếu chưa có link thì latest-position vẫn đọc trực tiếp event store.
- [ ] Latest-position chọn event có tọa độ theo `event_time DESC, recorded_at DESC, id DESC`; projection chỉ chạy sau `db.flush()` event/document thành công và không có đường ghi ngược event.
- [ ] Xác nhận event store không có hàm/API sửa hoặc xóa.
- [ ] Chạy `python -m pytest backend/tests/test_tms_execution_events.py -k "idempotency or concurrent or projection or rollback" -q`; expected PASS.
- [ ] Compile query PostgreSQL trong test và assert SQL của transition chứa `FOR UPDATE`; assert migration SQL có unique key. Không kết nối PostgreSQL remote đang tắt. Ghi chú rõ SQLite thread test chứng minh transaction/idempotency ở mức service, còn PostgreSQL row-lock được chứng minh bằng SQL compile.

### Task 4: API contract

**Files:**
- Modify: `backend/app/routes/tms_planning_routes.py`
- Modify: `backend/tests/test_tms_execution_events.py`

- [ ] Viết API tests fail cho GET history, POST event yêu cầu `Idempotency-Key`, latest-position và actor từ principal; assert response/log không chứa URL DB, SQL hay exception.
- [ ] Thêm routes `/api/tms/freight-orders/{id}/events` và `/latest-position`, dùng transaction envelope hiện có nhưng không commit trước refresh.
- [ ] Assert lịch sử sắp theo `event_time, recorded_at`, response `{message,data}`, 409/422 có mã và tiếng Việt.
- [ ] Chạy `python -m pytest backend/tests/test_tms_execution_events.py -k api backend/tests/test_route_uniqueness.py -q`; expected PASS và không có POST/PUT/PATCH/DELETE nào sửa event đã lưu.

## Chunk 3: Migration và regression

### Task 5: Migration PostgreSQL 006 và readiness

**Files:**
- Create: `backend/app/migrations/v006_tms_execution_events.py`
- Modify: `backend/app/migrations/runner.py`
- Modify: `backend/app/routes/health_routes.py`
- Create: `backend/tests/test_migration_v006_execution_events.py`
- Modify: `backend/tests/test_migration_v001.py`
- Modify: `backend/tests/test_database_readiness.py`

- [ ] Viết migration tests fail cho bảng, unique/check constraints, indexes, head `006` và required tables.
- [ ] Migration schema chứa đủ ba bảng, `payload_hash`, unique `(freight_order_id,idempotency_key)`, unique legacy link, FK, event/source checks và indexes `(freight_order_id,event_time,recorded_at)`.
- [ ] Cài PostgreSQL SQL với identity/indexes/check constraints; SQLite upgrade idempotent và rollback có kiểm soát. Test rollback xóa đủ ba bảng theo thứ tự phụ thuộc `transport_event_documents → transport_events → freight_order_legacy_links` và xóa migration marker khi đã cấp `restore_from`.
- [ ] Thêm v006 vào runner/readiness và cập nhật expected migration lists.
- [ ] Chạy `python -m pytest backend/tests/test_migration_v006_execution_events.py backend/tests/test_migration_v001.py backend/tests/test_database_readiness.py -q`; expected PASS, head `006`.
- [ ] Chạy `python -m migrations.runner upgrade --database-url postgresql://not-connected/epl --dry-run` từ `backend/app`; expected chỉ in SQL PostgreSQL có v006, không mở kết nối mạng.

### Task 6: Verification cuối

**Files:**
- Modify: `docs/superpowers/plans/2026-08-10-tms-execution-events.md` để đánh dấu checklist.

- [ ] Chạy `python -m py_compile backend/app/models.py backend/app/services/tms_execution_service.py backend/app/routes/tms_planning_routes.py backend/app/migrations/v006_tms_execution_events.py backend/app/migrations/runner.py`.
- [ ] Chạy `python -m pytest backend/tests/test_tms_execution_events.py backend/tests/test_migration_v006_execution_events.py backend/tests/test_migration_v001.py backend/tests/test_database_readiness.py backend/tests/test_route_uniqueness.py -q`.
- [ ] Chạy `python -m pytest backend/tests -q` và ghi nhận chính xác số test.
- [ ] Xác nhận `.env` không đổi và không có kết nối tới PostgreSQL Linux.
- [ ] Báo cáo phạm vi hoàn thành, cảnh báo còn lại và bước Core 5; không tuyên bố thành công nếu lệnh kiểm chứng không exit 0.

## Interfaces và test shapes bắt buộc

Service public:

```python
def record_event(db, freight_order_id: str, data: dict, idempotency_key: str, actor: str) -> TransportEvent: ...
def list_events(db, freight_order_id: str) -> list[TransportEvent]: ...
def latest_position(db, freight_order_id: str) -> TransportEvent: ...
def link_legacy_delivery_order(db, freight_order_id: str, delivery_order_id: str, actor: str) -> FreightOrderLegacyLink: ...
```

POST body:

```json
{
  "event_type": "check_in",
  "event_time": "2026-08-11T07:55:00",
  "expected_version": 2,
  "lat": 10.8231,
  "lng": 106.6297,
  "speed_kmh": 0,
  "distance_km": 0,
  "location_text": "Kho A",
  "source": "device",
  "device_id": "GPS-51C-001",
  "reason": null,
  "note": null,
  "documents": []
}
```

Response: `{"message":"Đã ghi nhận sự kiện vận tải.","data":<event>}`. Trạng thái FO sau từng event lần lượt là `checked_in`, `picked_up`, `departed`, `arrived`, `unloading`, `delivered`. Audit dùng action `RECORD_TRANSPORT_EVENT`, table `transport_events`, record ID là event ID, actor/IP từ request context.

Ví dụ test state machine:

```python
def test_cannot_skip_pickup(db, execution_service, dispatched_order):
    with pytest.raises(DomainError) as error:
        execution_service.record_event(db, dispatched_order.id, departure_payload(version=2), "key-2", "dispatcher")
    assert error.value.code == "EVENT_SEQUENCE_INVALID"
    assert db.get(FreightOrder, dispatched_order.id).version == 1
```

Router phải lấy `Idempotency-Key` bằng `Header(...)`; thiếu header trả 422. `GET latest-position` trả 404 `POSITION_NOT_FOUND` khi chưa có event tọa độ. Mọi `DomainError` đi qua `raise_http`; IntegrityError không được trả raw 500.
