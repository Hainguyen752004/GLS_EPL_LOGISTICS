# POD & ETA Flow Correction Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:test-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sửa lát cắt nghiệp vụ giao hàng để 1 DO có thể có nhiều POD theo xe/điểm giao và ETA/quay đầu được tính từ tuyến, tốc độ, thời gian bốc/dỡ.

**Architecture:** Giữ tương thích bảng `pod` cũ để demo không vỡ dữ liệu, thêm bảng POD nhiều dòng làm nguồn hiển thị mới. Tính ETA bằng utility thuần trong service workflow và chiếu ra `VehicleTracking`/Shipment 360. Không đụng PostgreSQL thật nếu không cần; migration SQLite/PostgreSQL phải idempotent.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, vanilla JS frontend.

---

### Task 1: Backend POD nhiều dòng và ETA kế hoạch

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/services/workflow_service.py`
- Modify: `backend/app/routes/workflow_routes.py`
- Modify: `backend/app/migrations/runner.py`
- Create/Modify: `backend/app/migrations/v008_delivery_pod_eta.py`
- Test: `backend/tests/test_delivery_pod_eta_flow.py`

- [ ] **Step 1: Write failing tests**

Tests:
- Dispatch tính `VehicleTracking.remaining_distance_km`, `eta`, `planned_return_at` từ route distance + avg speed.
- Một DO lưu được nhiều POD records, mỗi POD có `vehicle_id`, `driver_id`, `stop_no`.
- `GET /api/pod/{do_id}` trả danh sách `records` và `completion`.
- Delivered chỉ cho qua khi có ít nhất một POD hợp lệ cho xe đang giao.
- Chuỗi tiếng Việt `POSITION_NOT_FOUND` không bị mojibake.

Run:
`python -m pytest backend/tests/test_delivery_pod_eta_flow.py -q`

Expected: FAIL vì model/API chưa có.

- [ ] **Step 2: Minimal implementation**

Add `DeliveryPODRecord` model/table, migration v008, service helpers:
- `estimate_delivery_timing(route_distance_km, departure_at, avg_speed_kmh, unload_minutes, return_speed_kmh)`
- `save_pod_record(db, do_id, data, actor)`
- `list_pod_records(db, do_id)`

- [ ] **Step 3: Verify focused backend**

Run:
`python -m pytest backend/tests/test_delivery_pod_eta_flow.py backend/tests/test_workflow_api_contract.py -q`

Expected: PASS.

### Task 2: Frontend Shipment 360 hiển thị POD/ETA/quay đầu

**Files:**
- Modify: `frontend/js/tms-cockpit-utils.js`
- Modify: `frontend/js/app.js`
- Test: existing frontend scripts if available.

- [ ] **Step 1: Write/update frontend test**

Assert Shipment 360 detail can show:
- số POD đã nhận / tổng POD,
- ETA đến,
- ETA quay đầu,
- vehicle/driver trên POD.

- [ ] **Step 2: Implement minimal UI**

Use `pods` array from `/api/data/all`; support both legacy `pod` and new `delivery_pod_records`.

- [ ] **Step 3: Verify**

Run existing frontend test command/script discovered in repo.

### Task 3: Checklist and Vietnamese audit

**Files:**
- Modify: `KICH_BAN_DEMO_3_GIO_TMS.md` or add checklist note if needed.
- Scan backend/frontend for mojibake `Ã|Æ|Ä`.

- [ ] **Step 1: Run scan**

Run:
`rg -n "Ã|Æ|Ä" backend frontend`

- [ ] **Step 2: Fix user-facing Vietnamese strings in touched flow**

- [ ] **Step 3: Final verify**

Run focused backend tests and frontend tests.
