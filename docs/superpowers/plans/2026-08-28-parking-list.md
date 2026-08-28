# Parking List Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real Parking List/Packing List workflow linked to SO/DO records, with QR labels, printable output, status history and a searchable UI.

**Architecture:** Add versioned Parking List tables and service logic beside the existing workflow services. Expose paginated authenticated APIs and render a dedicated operations page using the existing single-page frontend patterns. QR values are opaque tokens that resolve to read-only shipment/package details.

**Tech Stack:** FastAPI, SQLAlchemy, existing migration runner, PostgreSQL/SQLite compatibility, vanilla frontend JavaScript/CSS, existing test harness.

---

### Task 1: Database and domain model

**Files:**
- Create: `backend/app/migrations/v023_parking_list.py`
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_parking_list_model_contract.py`

- [ ] Add the four tables, foreign keys, indexes and one-active-version constraint with PostgreSQL and SQLite branches.
- [ ] Add SQLAlchemy models and relationships for lists, items, labels and events.
- [ ] Add canonical status validation and opaque token uniqueness.
- [ ] Run focused model/migration tests.

### Task 2: Service and API

**Files:**
- Create: `backend/app/services/parking_list_service.py`
- Create: `backend/app/routes/parking_list_routes.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_parking_list_api.py`

- [ ] Implement source loading from DO, SO and `DeliveryOrderDetail`, rejecting incomplete source data.
- [ ] Implement idempotent generation, label creation, search pagination and detail serialization.
- [ ] Implement valid status transitions and append-only events.
- [ ] Add authenticated mutation handling and register the router.
- [ ] Run API tests for lineage, isolation, authorization and idempotency.

### Task 3: Printable outputs

**Files:**
- Modify: `backend/app/routes/parking_list_routes.py`
- Create: `backend/tests/test_parking_list_print_contract.py`

- [ ] Return print-ready JSON/HTML-compatible payloads for compact labels and detailed packing lists.
- [ ] Add QR generation using an available project dependency or a deterministic server-side fallback.
- [ ] Test totals, package numbering, QR uniqueness and missing-field behavior.

### Task 4: Frontend page

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`
- Modify: `frontend/css/*.css` (use the existing stylesheet location)
- Create or modify: `frontend/tests/parking-list-ui.test.js`

- [ ] Add navigation entry and dedicated page with search/filter controls.
- [ ] Add detail drawer, item table, event history, print buttons and status actions.
- [ ] Add loading, empty, error and permission states; preserve existing responsive shell.
- [ ] Run focused frontend tests and a browser smoke test.

### Task 5: Regression verification

**Files:**
- Modify: `DEMO_TEST_A_Z.md`

- [ ] Add Parking List checks after DO creation and before dispatch.
- [ ] Run the full backend suite and focused frontend tests.
- [ ] Confirm existing SO -> DO -> Trip -> Dispatch -> POD behavior is unchanged.

