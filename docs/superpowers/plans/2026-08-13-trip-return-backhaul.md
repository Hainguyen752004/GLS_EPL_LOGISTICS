# Trip & Return/Backhaul Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bổ sung lớp thực thi Trip/Trip Leg và kế hoạch quay về/backhaul để EPL phân biệt đúng DO là yêu cầu vận chuyển, Trip là lần chạy thực tế, đồng thời hỗ trợ một DO có nhiều Trip và một Trip có nhiều chặng.

**Architecture:** Thêm `TransportTrip`, `TripDeliveryOrder` và `TransportTripLeg` thành lớp thực thi nằm giữa Freight Order/DO và Event/POD/Finance. Trip bắt buộc có `freight_order_id`; ResourceAssignment, TransportEvent, DeliveryPODRecord và FreightActualCost nhận lineage `trip_id/leg_id` để toàn bộ luồng truy vết được từ yêu cầu đến settlement. API mới nằm trong router TMS Planning, bắt buộc principal tin cậy, quyền theo command và idempotency scope `(actor, method, path, key)`. UI thêm Trip & Return Cockpit và tích hợp vào Shipment 360°; không tạo mock data và không ghi PostgreSQL thật trong test.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL/SQLite migration runner, JavaScript thuần, Node contract tests, pytest.

---

## Chunk 1: Domain, API và migration

### Task 1: Mô hình Trip, membership và lineage A-Z

**Files:**
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_trip_return_flow.py`

- [ ] Viết test RED khẳng định Trip có `freight_order_id`, `trip_type`, trạng thái, xe/tài xế, ETA đi/về, version; Leg có thứ tự, loại chặng, DO tùy chọn, khoảng cách, ETA, actual và phân bổ cost/revenue.
- [ ] `TripDeliveryOrder` dùng PK `(trip_id, do_id)` và tuyệt đối không unique riêng `do_id`; `TransportTripLeg` unique `(trip_id, sequence_no)` và loaded leg dùng composite FK `(trip_id, do_id)` tới membership.
- [ ] `ResourceAssignment.trip_id`, `TransportEvent.trip_id/leg_id`, `DeliveryPODRecord.trip_id/leg_id` và `FreightActualCost.trip_id` là nullable để tương thích dữ liệu cũ; command Trip mới luôn ghi lineage.
- [ ] Thay unique cũ `ResourceAssignment.freight_order_id` bằng: legacy partial unique khi `trip_id IS NULL`, và unique `(trip_id)`/active interval cho assignment Trip. Thay active-cost unique theo FO bằng legacy partial unique `freight_order_id WHERE trip_id IS NULL AND is_active`, cộng Trip-scoped unique `(trip_id) WHERE is_active`.
- [ ] POD mới unique `(trip_id, leg_id, do_id, vehicle_id, stop_no)`; legacy POD nullable Trip vẫn giữ unique cũ bằng partial index/dialect-compatible validation.
- [ ] Chạy `python -m pytest backend/tests/test_trip_return_flow.py -q`, mong đợi lỗi import model.
- [ ] Thêm ba model `TransportTrip`, `TransportTripLeg`, `TripDeliveryOrder` với unique/check/FK cần thiết.
- [ ] Chạy lại test, mong đợi phần metadata/model đạt.

### Task 2: State machine, ETA và command contracts

**Files:**
- Create: `backend/app/services/tms_trip_service.py`
- Modify: `backend/app/routes/tms_planning_routes.py`
- Test: `backend/tests/test_trip_return_flow.py`

- [ ] Trạng thái hợp lệ: `draft → planned → dispatched → in_transit → completed → settled`; `draft|planned` có thể `cancelled`; không reopen. Dispatch cần assignment hợp lệ, complete cần mọi leg hoàn tất và mọi loaded delivery leg có POD, settled chỉ do Finance service gọi khi toàn bộ settlement liên quan đã paid/closed.
- [ ] Viết test RED cho tạo Trip từ nhiều DO, thêm chặng, tính ETA tuần tự, chọn `one_way|round_trip|backhaul|multi_stop`.
- [ ] Viết test RED khẳng định một DO có thể nằm ở nhiều Trip; một Trip có nhiều DO/Leg.
- [ ] Viết test RED cho return leg: `empty_return` không cần DO, `backhaul` bắt buộc DO chiều về.
- [ ] Event state machine chạy độc lập theo `(trip_id, leg_id)`: mỗi loaded leg có thể `check_in → pickup → departure → arrival → unloading → delivered`; return leg có `departure → arrival`. Event type được lặp ở leg khác. Event `departure` đầu tiên chuyển Trip `dispatched → in_transit`; mọi leg completed + POD bắt buộc mới cho Trip completed. FreightOrder chỉ completed khi toàn bộ Trip không-cancelled của nó completed/settled.
- [ ] ETA dùng `DateTime(timezone=True)` UTC. Với từng leg: `departure=max(previous_arrival+dwell, planned_departure)`, `arrival=departure+distance_km/avg_speed_kmh`; tốc độ hữu hạn >0, distance ≥0, dwell ≥0. `planned_return_at` là arrival của return leg cuối. Event actual cập nhật actual departure/arrival và tính lại các leg chưa chạy.
- [ ] Viết test RED cho CAS version, concurrent leg insert, khóa Trip đã `completed/settled`, audit và lỗi tiếng Việt ổn định.
- [ ] Mọi POST/PUT yêu cầu `Idempotency-Key`; same hash replay nguyên response, khác hash 409; payload typed/bounded, unknown field 422. Quyền: reads `trip_read`, plan/edit `trip_plan`, dispatch `trip_dispatch`, complete `trip_execute`; principal/permission thiếu thì fail closed.
- [ ] Cài service với Decimal/quãng đường hữu hạn, row lock PostgreSQL, SQLite `BEGIN IMMEDIATE`, CAS và DB unique làm hàng rào cuối.
- [ ] Thêm API có phân trang/filter: `GET/POST /api/tms/trips`, `GET/PUT /api/tms/trips/{id}`, `POST/PUT/DELETE /api/tms/trips/{id}/legs`, `POST /dispatch`, `POST /complete`.
- [ ] Chạy focused tests, mong đợi toàn bộ PASS.

### Task 3: Event, POD và Finance lineage

**Files:**
- Modify: `backend/app/services/tms_execution_service.py`
- Modify: `backend/app/routes/tms_planning_routes.py`
- Modify: `backend/app/services/tms_cost_service.py`
- Modify: `backend/app/services/tms_settlement_service.py`
- Test: `backend/tests/test_trip_return_integration.py`

- [ ] Viết RED integration: DO nằm ở Trip A/xe A và Trip B/xe B; event/POD cùng DO vẫn truy đúng Trip/Leg/xe và không đè nhau.
- [ ] Ghi event yêu cầu `trip_id/leg_id` cho Trip mới, xác thực leg thuộc trip/DO/vehicle assignment; source/device/actor giữ nguyên event-store contract.
- [ ] Sửa uniqueness/event lookup từ global FreightOrder sang `(trip_id, leg_id, event_type, idempotency_key)`; giữ nhánh legacy khi `trip_id/leg_id IS NULL`. Test hai leg cùng Trip đều ghi pickup/arrival hợp lệ và duplicate trong cùng leg bị từ chối/replay.
- [ ] POD idempotent theo Trip/Leg/DO/xe/stop; delivered leg thiếu POD không complete được.
- [ ] Actual Cost tạo theo FreightOrder + Trip snapshot, charge item có leg allocation; hai Trip cùng FO có hai active cost độc lập. AP/Settlement vẫn theo cost nhưng truy ngược được Trip.
- [ ] Khi settlement cuối paid/closed, Finance service khóa Trip và chuyển `completed → settled`; thất bại bất kỳ rollback event/POD/cost/audit/status cùng transaction.
- [ ] Integration A-Z: DO → Trip/legs → assignment → events → POD → complete → cost → AP → post GL journal → settlement/payment → Trip settled; assert JournalBatch/JournalLine cân bằng và query reporting truy vết `DO → Trip → Leg → Cost → AP → Settlement → Journal`, đồng thời AuditLog đủ actor/IP.
- [ ] Bổ sung read model/service `trip_financial_trace(trip_id)` và API GET read-only cho Reporting/Shipment 360; trả ledger/document ids, leg cost/revenue/profit và không fallback sang hồ sơ không liên quan.

### Task 4: Migration v011 và readiness

**Files:**
- Create: `backend/app/migrations/v011_transport_trips.py`
- Modify: `backend/app/migrations/runner.py`
- Modify: `backend/app/routes/health_routes.py`
- Test: `backend/tests/test_migration_v011_transport_trips.py`
- Test: `backend/tests/test_database_readiness.py`

- [ ] Viết test RED cho SQLite upgrade/repeat/rollback và PostgreSQL dry-run.
- [ ] Tạo đủ ba bảng, lineage columns, thay unique assignment/cost cũ bằng partial indexes legacy + Trip-scoped, đổi event uniqueness theo Trip/Leg, composite FK/unique, exact enum/range CHECK và indexes theo Trip/DO/status/event/POD/cost.
- [ ] Đăng ký head `011`, readiness validate columns/types/nullability/FK/check/index của ba bảng và lineage, rollback guard phát hiện dữ liệu ở cả bảng Trip/Leg/link và bảng lineage.
- [ ] Chạy SQLite migration upgrade/repeat/refusal/authorized rollback; PostgreSQL dry-run và fake-catalog validation. Nếu biến `EPL_TEST_POSTGRES_URL` được cấp, chạy disposable PostgreSQL upgrade/repeat/constraint/rollback; tuyệt đối không dùng `DATABASE_URL` production.

## Chunk 2: UI Trip & Return Cockpit

### Task 5: Trip Planning và Return/Backhaul Form

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`
- Modify: `frontend/js/tms-cockpit-utils.js`
- Create: `frontend/tests/trip-return-cockpit.test.js`

- [ ] Viết test RED cho panel, form và trường: loại trip, danh sách DO, xe/tài xế, outbound legs, return type, return DO, tốc độ, ETA.
- [ ] Tạo cockpit có ba cột: Trip queue, hồ sơ Trip/Leg, guidance/cảnh báo.
- [ ] Nút Tạo Trip/Lưu chặng/Dispatch/Hoàn tất gọi API thật với bearer principal, permission, idempotency/version; thiếu master data điều hướng đúng tab.
- [ ] Shipment 360° hiển thị mọi Trip liên quan DO, từng leg, ETA đi/về, trạng thái return/backhaul và POD đúng Trip/Leg/xe; mở đúng Trip form.
- [ ] Chạy toàn bộ frontend tests và syntax checks.

### Task 6: Kiểm thử A-Z và checklist đối chiếu hình

**Files:**
- Modify: `KICH_BAN_DEMO_3_GIO_TMS.md`
- Create: `docs/TRANSPORTATION_FLOW_CHECKLIST.md`

- [ ] Chạy focused backend Trip + workflow + execution + finance tests.
- [ ] Chạy toàn bộ frontend tests.
- [ ] Import app với `.env` PostgreSQL nhưng không chạy mutation dữ liệu thật.
- [ ] Ghi checklist Có/Một phần/Thiếu cho sáu cột trong hình và hướng dẫn demo One-way, Round-trip, Empty Return, Backhaul, Multi-stop.
