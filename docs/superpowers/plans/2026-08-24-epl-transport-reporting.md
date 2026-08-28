# EPL Transport Revenue And Expense Reporting Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a database-backed EPL transport revenue dashboard, detailed export table, and Trip-linked expense voucher workflow.

**Architecture:** Add a focused reporting service/router that projects existing workflow and finance records into report DTOs. Store only expense-voucher header metadata in a new table while reusing FreightActualCost, FreightChargeItem, FreightCostDocument, AP Invoice, and audit services as the financial source of truth. Render the feature in the existing Reporting view with Chart.js and responsive CSS.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, PostgreSQL/SQLite migrations, vanilla JavaScript, Chart.js, Node test runner, pytest.

---

## Chunk 1: Backend Contract And Persistence

### Task 1: Revenue reporting projection

**Files:**
- Create: `backend/app/services/tms_reporting_service.py`
- Create: `backend/app/routes/tms_reporting_routes.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_tms_transport_reporting.py`

- [ ] Write failing tests for one row per completed DO/Trip, posted-invoice recognition, approved-cost profit, filters, missing fields, and dated currency conversions.
- [ ] Run the focused pytest file and confirm failures are caused by missing reporting APIs.
- [ ] Implement the reporting query, totals, chart dimensions, and CSV export with fixed EPL column order.
- [ ] Run focused tests until green.

### Task 2: Expense voucher metadata

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/migrations/v020_epl_expense_vouchers.py`
- Modify: `backend/app/migrations/runner.py`
- Create: `backend/app/schemas/reporting.py`
- Modify: `backend/app/services/tms_reporting_service.py`
- Modify: `backend/app/routes/tms_reporting_routes.py`
- Test: `backend/tests/test_migration_v020_epl_expense_vouchers.py`
- Test: `backend/tests/test_tms_transport_reporting.py`

- [ ] Write failing migration and API tests for voucher number uniqueness, Trip/DO lineage, draft persistence, version conflicts, and protected transitions.
- [ ] Run focused tests and confirm the expected failures.
- [ ] Add the voucher metadata model/migration and atomic draft save that delegates cost rows to the existing Actual Cost logic.
- [ ] Implement list/detail endpoints and serialized printable structure.
- [ ] Run focused tests until green.

## Chunk 2: Frontend Module

### Task 3: Reporting UI contract

**Files:**
- Create: `frontend/tests/transport-reporting-ui.test.js`
- Create: `frontend/js/transport-reporting.js`
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`
- Modify: `frontend/css/styles.css`

- [ ] Write failing DOM/source tests for three tabs, all EPL columns, chart canvases, CSV export, voucher controls, and responsive overflow.
- [ ] Run the frontend test and confirm expected failures.
- [ ] Build the reporting layout and load it from the new APIs.
- [ ] Render KPI, line/bar/doughnut charts with lifecycle cleanup.
- [ ] Render the dense revenue table, filters, source detail drawer, and CSV download.
- [ ] Build the Trip/DO voucher worklist/editor and call real draft/submit/approve APIs with idempotency keys.
- [ ] Run focused frontend tests until green.

## Chunk 3: Integration And Verification

### Task 4: Demo data and documentation

**Files:**
- Modify: `backend/app/services/demo_seed_service.py`
- Modify: `EPL_System/DEMO_TEST_A_Z.md`
- Test: `backend/tests/test_demo_seed_golden_path.py`

- [ ] Write a failing seed assertion for a printable EPL expense voucher and reportable completed trip.
- [ ] Add deterministic demo voucher metadata without inventing missing trailer information.
- [ ] Add the reporting and voucher verification steps to the A-Z guide.
- [ ] Run focused seed tests until green.

### Task 5: Full verification

- [ ] Run all backend tests and confirm zero failures.
- [ ] Run all frontend tests and JavaScript syntax checks.
- [ ] Start/reuse the local server and verify health/readiness.
- [ ] Inspect desktop, tablet, and mobile layouts; verify charts render and tables/forms do not overlap.
- [ ] Verify create, reload, submit, approve, export, and source drill-down against persisted database records.
