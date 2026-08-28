# Delivery Completion and DO Tracking Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real database-backed Delivery Completion module that atomically stores POD evidence and customer surcharges, calculates the final DO selling price, and simplify Tracking into a DO-to-live-map workspace without changing Incidents or Event Timeline behavior.

**Architecture:** Add normalized closeout, customer adjustment, and POD document tables through migration v016. A dedicated backend service owns the atomic `complete-delivery` transaction and extends the existing closeout response; frontend orchestration calls that single endpoint while a small pure UI module owns surcharge calculations and rendering. Existing Incident and Event Timeline code remains untouched except for moving its enclosing tabs.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, SQLite/PostgreSQL migrations, vanilla JavaScript, Leaflet, Node assertion tests, pytest.

**Constraint:** `D:\Demo_Lao\EPL_System` is not a Git repository, so worktree creation and commit steps are unavailable. Use focused test checkpoints and inspect changed files after every task.

**Design spec:** `docs/superpowers/specs/2026-08-22-delivery-completion-and-tracking-redesign.md`

---

## File Structure

**Create**

- `backend/app/migrations/v016_delivery_completion_closeout.py`: cross-database schema for closeouts, customer adjustments, and binary POD documents.
- `backend/app/schemas/delivery_completion.py`: multipart JSON payload validation and customer surcharge rules.
- `backend/app/services/delivery_completion_service.py`: atomic completion transaction, price snapshots, idempotency, Trip/DO transition rules, and response serialization helpers.
- `backend/tests/test_migration_v016_delivery_completion.py`: SQLite/PostgreSQL migration contract tests.
- `backend/tests/test_delivery_completion_api.py`: aggregate endpoint, rollback, idempotency, multi-DO Trip, file persistence, and price tests.
- `frontend/js/delivery-completion-ui.js`: pure calculation/render/state helpers for the new module.
- `frontend/tests/delivery-completion-ui.test.js`: DOM/source contract and pure calculation tests.
- `frontend/tests/tracking-do-workspace-ui.test.js`: tracking-only UI contract and regression guards for Incidents/Event Timeline.

**Modify**

- `backend/app/migrations/runner.py`: register v016.
- `backend/tests/test_migration_v001.py`: update expected migration head/list for v016.
- `backend/tests/test_migration_v005_dispatch.py`: update expected migration head.
- `backend/tests/test_migration_v006_execution_events.py`: update expected migration head.
- `backend/tests/test_migration_v007_freight_settlement.py`: update expected migration head.
- `backend/tests/test_migration_v008_driver_vehicle_images.py`: update expected migration head.
- `backend/tests/test_migration_v011_transport_trips.py`: update expected migration head.
- `backend/tests/test_migration_v012_vehicle_speed_profile.py`: update expected migration head.
- `backend/tests/test_migration_v013_demo_stabilization.py`: update expected migration head.
- `backend/tests/test_migration_v014_trip_cost_rows.py`: update expected head while preserving v014 assertions.
- `backend/tests/test_database_readiness.py`: require the three new tables and v016 head.
- `backend/app/models.py`: map the three new tables and relationships.
- `backend/app/schemas/__init__.py`: export completion schemas.
- `backend/app/routes/workflow_routes.py`: add multipart completion and POD document download endpoints.
- `backend/app/services/ar_invoice_service.py`: source AR amount from completed final selling price when available.
- `backend/app/main.py`: extend closeout output with base price source, customer adjustments, final selling price, actual cost, and margin.
- `backend/app/routes/health_routes.py`: include the new required tables.
- `frontend/index.html`: add the navigation module and new views; remove POD/closeout cards from Tracking while preserving Incident/Event markup.
- `frontend/css/styles.css`: responsive workbench, table, modal/form, tracking list/map, and toast tone styles.
- `frontend/js/app.js`: navigation registration, data adapters, atomic submission, tracking selection, and explicit toast severity.
- `frontend/tests/toast-overlay-ui.test.js`: warning/error/loading/success behavior.
- `frontend/tests/tracking-closeout-ui.test.js`: update legacy assertions to point to the new completion module.
- `backend/tests/test_delivery_order_closeout_api.py`: assert final commercial fields.
- `backend/tests/test_az_real_workflow_audit.py`: exercise the new aggregate completion command in the A-Z workflow.

---

## Chunk 1: Database and Domain Model

### Task 1: Add migration v016

**Files:**
- Create: `backend/app/migrations/v016_delivery_completion_closeout.py`
- Modify: `backend/app/migrations/runner.py`
- Modify: `backend/tests/test_migration_v001.py`
- Modify: `backend/tests/test_migration_v005_dispatch.py`
- Modify: `backend/tests/test_migration_v006_execution_events.py`
- Modify: `backend/tests/test_migration_v007_freight_settlement.py`
- Modify: `backend/tests/test_migration_v008_driver_vehicle_images.py`
- Modify: `backend/tests/test_migration_v011_transport_trips.py`
- Modify: `backend/tests/test_migration_v012_vehicle_speed_profile.py`
- Modify: `backend/tests/test_migration_v013_demo_stabilization.py`
- Modify: `backend/tests/test_migration_v014_trip_cost_rows.py`
- Modify: `backend/tests/test_database_readiness.py`
- Test: `backend/tests/test_migration_v016_delivery_completion.py`

- [ ] **Step 1: Write failing migration tests**

Test that upgrade creates:

```text
delivery_order_closeouts
  id, do_id, base_selling_price_snapshot, base_price_source,
  base_price_source_id, surcharge_total, final_selling_price,
  currency_code, completed_at, completed_by, created_at

delivery_order_charge_adjustments
  id, closeout_id, line_no, name, original_amount,
  actual_amount, increase_amount, note, created_at, created_by

delivery_pod_documents
  id, pod_record_id, file_name, mime_type, file_size,
  checksum, content, created_at, created_by

delivery_pod_records additions
  delivery_result, cargo_condition
```

Assert `UNIQUE(do_id)` for exactly one closeout per DO, nonnegative amount constraints, checksum uniqueness per POD, foreign keys, POD field additions, and v016 migration head.

- [ ] **Step 2: Run migration tests and verify RED**

Run:

```powershell
C:\Users\zinnn\miniconda3\python.exe -m pytest backend/tests/test_migration_v016_delivery_completion.py -q
```

Expected: FAIL because v016 and the new tables are missing.

- [ ] **Step 3: Implement v016 and register it**

Follow the `statements`, `upgrade_sqlite`, `validate_sqlite`, and `validate_postgresql` pattern in `v014_trip_cost_rows.py`. Use `NUMERIC(24,6)` for money and `BYTEA` on PostgreSQL / `BLOB` on SQLite for document content.

Update the existing migration-head/readiness assertions from v015 to v016 and include the new required tables without weakening their earlier checks.

- [ ] **Step 4: Run migration tests and verify GREEN**

Expected: all v016 tests PASS and `required_migration_head()` returns `016_delivery_completion_closeout`.

- [ ] **Step 5: Run all migration regressions**

Run:

```powershell
C:\Users\zinnn\miniconda3\python.exe -m pytest backend/tests/test_migration_v001.py backend/tests/test_migration_v005_dispatch.py backend/tests/test_migration_v006_execution_events.py backend/tests/test_migration_v007_freight_settlement.py backend/tests/test_migration_v008_driver_vehicle_images.py backend/tests/test_migration_v011_transport_trips.py backend/tests/test_migration_v012_vehicle_speed_profile.py backend/tests/test_migration_v013_demo_stabilization.py backend/tests/test_migration_v014_trip_cost_rows.py backend/tests/test_migration_v016_delivery_completion.py backend/tests/test_database_readiness.py -q
```

Expected: PASS.

### Task 2: Map models and request schemas

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/schemas/delivery_completion.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_delivery_completion_api.py`

- [ ] **Step 1: Write failing schema tests**

Cover these rules:

```python
assert line.actual_amount >= line.original_amount
assert payload.currency_code == payload.currency_code.upper()
assert 1 <= len(payload.pod_entries) <= 100
assert 0 <= len(payload.charge_adjustments) <= 100
assert each leg_id is unique
assert each file token in multipart metadata maps to exactly one POD entry
```

- [ ] **Step 2: Run schema tests and verify RED**

Run:

```powershell
C:\Users\zinnn\miniconda3\python.exe -m pytest backend/tests/test_delivery_completion_api.py -k schema -q
```

Expected: import failure for `schemas.delivery_completion`.

- [ ] **Step 3: Implement SQLAlchemy models**

Add `DeliveryOrderCloseout`, `DeliveryOrderChargeAdjustment`, and `DeliveryPODDocument`. Keep customer surcharges separate from `FreightActualCost` and `FreightChargeItem`.

- [ ] **Step 4: Implement Pydantic schemas**

The JSON part of multipart must validate this shape:

```json
{
  "trip_id": "TRIP-...",
  "currency_code": "VND",
  "pod_entries": [{
    "leg_id": "LEG-...",
    "vehicle_id": "51C-268.89",
    "stop_no": 1,
    "location_text": "Cảng Cát Lái",
    "receiver_name": "Nguyễn Văn An",
    "receiver_phone": "0908123456",
    "delivery_time": "2026-08-22T14:30:00+07:00",
    "delivery_result": "delivered_full",
    "cargo_condition": "Nguyên niêm phong, không móp vỡ",
    "file_field": "pod_file_LEG-...",
    "note": "Nguyên niêm phong"
  }],
  "charge_adjustments": [{
    "name": "Phí chờ bốc dỡ",
    "original_amount": "0",
    "actual_amount": "350000",
    "note": "Chờ thêm 90 phút"
  }]
}
```

- [ ] **Step 5: Run schema tests and verify GREEN**

Run the same focused pytest command from Step 2.

Expected: schema cases PASS.

---

## Chunk 2: Atomic Completion API and Commercial Closeout

### Task 3: Implement the atomic completion service

**Files:**
- Create: `backend/app/services/delivery_completion_service.py`
- Test: `backend/tests/test_delivery_completion_api.py`

- [ ] **Step 1: Write failing happy-path API service test**

Build one `in_transit` DO/Trip/leg with a valid active assignment and SO amount `4_200_000`. Submit POD plus adjustments `350_000` and `120_000`. Assert:

```python
assert result["commercials"]["base_selling_price"] == 4_200_000
assert result["commercials"]["customer_surcharge_total"] == 470_000
assert result["commercials"]["final_selling_price"] == 4_670_000
assert do.canonical_status == "delivered"
assert trip.status == "completed"
assert stored_document.content == uploaded_bytes
```

In a separate test, submit one adjustment with `original_amount=100_000` and `actual_amount=160_000`; assert surcharge is `60_000` and final selling price is `4_260_000`. In both tests assert counts for `FreightActualCost` and `FreightChargeItem` are unchanged before and after completion.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
C:\Users\zinnn\miniconda3\python.exe -m pytest backend/tests/test_delivery_completion_api.py -k "happy_path or customer_surcharge" -q
```

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement price snapshot and replacement semantics**

Use `SalesOrder.total_amount`; fallback only when empty/nonpositive to `Quotation.selling_price`. Persist source and source ID. Calculate all amounts with `Decimal` and currency quantization helpers from `services/tms_money.py`.

- [ ] **Step 4: Implement transactional POD and state transitions**

Lock DO, Trip, legs, assignment, and closeout rows. Validate lineage and vehicle. Store binary files and `DeliveryPODRecord` rows. POD payload may target only `leg_type == "delivery"`; complete only those delivery legs. Do not mutate `outbound`, `pickup`, `empty_return`, `backhaul`, or `warehouse_transfer` legs. Complete the DO after all of its delivery legs have POD. Complete Trip only after every noncancelled operational leg and linked DO is complete; therefore an open empty-return or backhaul keeps Trip `in_transit` after the DO becomes Delivered.

- [ ] **Step 5: Implement request-level idempotency in the completion service only**

Hash normalized JSON plus each file checksum. Reuse the repository's `IdempotencyRecord` table, but do not call `workflow_routes._execute` because it hashes JSON without file bytes. The completion service is the only owner of request idempotency. Commit the idempotency result only with the successful transaction. Retry after rollback is allowed; replay after success returns the cached closeout; changed JSON or changed file bytes with the same key returns `IDEMPOTENCY_CONFLICT`.

- [ ] **Step 6: Run happy-path test and verify GREEN**

Run the focused command from Step 2. Expected: PASS.

- [ ] **Step 7: Add failing rollback and multi-DO Trip tests**

Test invalid currency, missing file, duplicate leg, changed JSON with the same idempotency key, changed file bytes with the same JSON/key, storage >10 MB, and a Trip containing another incomplete DO. Add a delivery-leg plus empty-return case: DO becomes Delivered after delivery POD while Trip remains `in_transit` until the empty-return completes. Inject one failure after POD/document flush and another inside AR/journal creation. Assert no POD/document/closeout/adjustment/invoice/journal survives either failure and the other DO keeps the Trip in transit.

Add idempotency success tests:

- Same key, normalized JSON, and file bytes replays the cached response and does not add duplicate POD, document, closeout, invoice, or journal rows.
- First call fails after an injected flush and rolls back; a second call with the same key/payload succeeds because the failed idempotency record was not committed.

Add AR semantics tests:

- Happy path creates exactly one posted invoice with `invoice.amount == final_selling_price`, `invoice.vat_amount == quantized(final_selling_price * vat_pct / 100)`, and `invoice.total == invoice.amount + invoice.vat_amount`. Assert the journal debit equals invoice total and the revenue plus VAT credits equal the same total.
- Existing posted invoice with the same amount is reused with no duplicate journal.
- Existing posted invoice with a different amount returns `AR_ALREADY_POSTED_DIFFERENT_AMOUNT` and rolls back all completion rows and state changes.

- [ ] **Step 8: Add transaction-local AR creation before GREEN**

Add or adapt an `ar_invoice_service` function that accepts the current SQLAlchemy session and never commits internally. Completion creates the final AR invoice directly in the existing `posted` lifecycle and creates its journal in the same transaction using `final_selling_price`. On idempotent replay, reuse the invoice created by the same successful completion. If a posted active invoice already exists with the same amount, reuse it; if its amount differs, return `AR_ALREADY_POSTED_DIFFERENT_AMOUNT` and roll back instead of mutating posted accounting data. Call this function inside `complete_delivery` before the outer commit.

- [ ] **Step 9: Implement minimal validation needed for GREEN**

Return stable domain errors such as `POD_FILE_REQUIRED`, `POD_FILE_TOO_LARGE`, `POD_LINEAGE_INVALID`, `CURRENCY_MISMATCH`, and `TRIP_HAS_OPEN_DELIVERIES` only where appropriate.

- [ ] **Step 10: Run full service tests**

Run:

```powershell
C:\Users\zinnn\miniconda3\python.exe -m pytest backend/tests/test_delivery_completion_api.py -q
```

Expected: all completion service tests PASS.

### Task 4: Expose endpoint, document download, closeout, and AR pricing

**Files:**
- Modify: `backend/app/routes/workflow_routes.py`
- Modify: `backend/app/services/ar_invoice_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/routes/health_routes.py`
- Test: `backend/tests/test_delivery_completion_api.py`
- Test: `backend/tests/test_delivery_order_closeout_api.py`
- Test: `backend/tests/test_az_real_workflow_audit.py`

- [ ] **Step 1: Write failing HTTP tests**

Assert `POST /api/delivery-orders/{do_id}/complete-delivery` accepts multipart JSON/files and requires `Idempotency-Key`. Assert `GET /api/pod-documents/{document_id}` streams the stored MIME type and bytes with authorization.

- [ ] **Step 2: Run focused HTTP tests and verify RED**

Run:

```powershell
C:\Users\zinnn\miniconda3\python.exe -m pytest backend/tests/test_delivery_completion_api.py -k "http or document_download" -q
```

Expected: 404 for both new routes.

- [ ] **Step 3: Add routes and one explicit transaction boundary**

Parse the JSON `payload` form field into `DeliveryCompletionRequest`; map file fields without loading more than 10 MB per file; call one service function; commit once in a completion-specific route wrapper. Do not call `workflow_routes._execute`; the service owns idempotency because its payload hash includes file checksums. Roll back once on any domain or unexpected error.

- [ ] **Step 4: Extend closeout response**

Return:

```json
{
  "commercials": {
    "base_selling_price": 4200000,
    "base_price_source": "sales_order",
    "customer_surcharge_total": 470000,
    "final_selling_price": 4670000,
    "actual_cost_total": 0,
    "margin_amount": 4670000,
    "margin_is_provisional": true
  },
  "customer_charge_adjustments": [],
  "pod_records": []
}
```

- [ ] **Step 5: Verify AR invoice uses final selling price inside completion**

The service change from Task 3 creates a posted AR invoice and journal inside the same transaction using `final_selling_price`. Keep `/api/invoices/post` compatible for legacy flows: when a completed closeout exists it uses the final amount; otherwise it retains the SO fallback. A same-amount posted invoice may be reused; a different-amount posted invoice is a conflict. Avoid duplicate active invoices on idempotent replay.

- [ ] **Step 6: Update health table requirements**

Add all three v016 tables to health readiness.

- [ ] **Step 7: Run backend focused tests**

Run:

```powershell
$env:TEMP='D:\Demo_Lao\EPL_System\.tmp_pytest'
$env:TMP='D:\Demo_Lao\EPL_System\.tmp_pytest'
C:\Users\zinnn\miniconda3\python.exe -m pytest backend/tests/test_delivery_completion_api.py backend/tests/test_delivery_order_closeout_api.py backend/tests/test_az_real_workflow_audit.py -q
```

Expected: PASS with no failed tests.

---

## Chunk 3: Frontend Module, Tracking, and Feedback

### Task 5: Add the Delivery Completion UI module

**Files:**
- Create: `frontend/js/delivery-completion-ui.js`
- Modify: `frontend/index.html`
- Modify: `frontend/css/styles.css`
- Modify: `frontend/js/app.js`
- Test: `frontend/tests/delivery-completion-ui.test.js`
- Modify: `frontend/tests/tracking-closeout-ui.test.js`

- [ ] **Step 1: Write failing pure calculation tests**

Test:

```javascript
calculateCustomerCloseout(4200000, [
  { original_amount: 0, actual_amount: 350000 },
  { original_amount: 0, actual_amount: 120000 }
])
// => { surchargeTotal: 470000, finalSellingPrice: 4670000 }
```

Also test line deletion, nonnegative validation, currency formatting, and no floating-point drift.

Add worklist eligibility tests that exclude an `in_transit` DO when it has no Trip, no active assignment, a mismatched assigned vehicle, or no remaining delivery leg. Include only a DO whose status, Trip lineage, leg, vehicle, and assignment are all valid.

Add history/read-only tests: the module exposes `Chờ hoàn tất` and `Đã hoàn tất` tabs; a Delivered DO with a completed closeout appears in history and opens the same form in read-only mode with no add/delete/submit controls.

- [ ] **Step 2: Run test and verify RED**

Run:

```powershell
node frontend/tests/delivery-completion-ui.test.js
```

Expected: FAIL because the module and markup do not exist.

- [ ] **Step 3: Implement the pure UI module**

Expose `window.DeliveryCompletionUI` with calculation, escaping, row rendering, summary rendering, and serializing helpers. Keep fetch calls and application state in `app.js`.

- [ ] **Step 4: Add navigation and module markup**

Add a top-level `delivery-completion` view with `Chờ hoàn tất` and `Đã hoàn tất` tabs. The pending tab renders eligible DOs with search/reload, View DO, and Complete Delivery. The completed tab lists Delivered DOs with closeouts and opens the same accessible full-width form in read-only mode. Build the approved two-column POD/price layout, a back button, row add/delete controls, stable responsive dimensions, and one completion button only in editable mode.

- [ ] **Step 5: Integrate real API calls**

Add functions to load eligible `canonical_status === "in_transit"` DOs and reject entries without matching Trip, remaining leg, active assignment, and vehicle lineage. Load completed closeouts separately for history/read-only viewing. Resolve Trip/legs, preview closeout pricing, assemble `FormData`, generate one idempotency key per logical submission, disable the button while pending, call the aggregate endpoint, refresh app state, and render returned closeout.

- [ ] **Step 6: Run frontend test and verify GREEN**

Run:

```powershell
node frontend/tests/delivery-completion-ui.test.js
```

Expected: `DELIVERY_COMPLETION_UI_OK`.

### Task 6: Redesign Tracking around DO selection

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/css/styles.css`
- Modify: `frontend/js/app.js`
- Create: `frontend/tests/tracking-do-workspace-ui.test.js`

- [ ] **Step 1: Write failing tracking layout tests**

Assert Tracking has a searchable DO list and map detail container, filters only `canonical_status === 'in_transit'`, updates map summary from the selected DO, and contains no POD entry or closeout form.

Add regression assertions that existing Incident and Event Timeline element IDs and handler names remain present.

- [ ] **Step 2: Run test and verify RED**

Run:

```powershell
node frontend/tests/tracking-do-workspace-ui.test.js
```

Expected: FAIL against the current three-column GPS/POD/closeout layout.

- [ ] **Step 3: Implement master-detail Tracking**

Move the current live map and metrics into the detail side. Add DO cards on the left and reuse `onTrackingSelectChange`, Leaflet layers, GPS refresh, route deviation, speed, distance, and ETA logic. Remove only POD/closeout markup from Tracking.

- [ ] **Step 4: Preserve Incidents and Event Timeline**

Do not rename or rewrite their API calls, IDs, data arrays, or event handlers. Verify tab switching still opens exactly one group.

- [ ] **Step 5: Run tracking tests and verify GREEN**

Run:

```powershell
node frontend/tests/tracking-do-workspace-ui.test.js
node frontend/tests/tracking-closeout-ui.test.js
```

Expected: `TRACKING_DO_WORKSPACE_UI_OK` and updated `TRACKING_CLOSEOUT_UI_OK`.

### Task 7: Make toast severity explicit

**Files:**
- Modify: `frontend/js/app.js`
- Modify: `frontend/css/styles.css`
- Modify: `frontend/tests/toast-overlay-ui.test.js`

- [ ] **Step 1: Write failing toast API tests**

Require `showToast(message, { type: 'warning' })` or an equivalent explicit API. Assert a missing DO uses warning, backend validation uses error, pending uses loading, and only confirmed completion uses success.

- [ ] **Step 2: Run toast test and verify RED**

Run:

```powershell
node frontend/tests/toast-overlay-ui.test.js
```

Expected: FAIL because `showToast` currently infers severity from message text.

- [ ] **Step 3: Implement explicit tones with legacy fallback**

Keep existing one-argument callers working, but all new Delivery Completion flows must pass an explicit type. Use centered overlay, modal-safe z-index, close button, progress bar, and longer timeout for warning/error.

- [ ] **Step 4: Run toast test and verify GREEN**

Run the same toast test command from Step 2.

Expected: `TOAST_OVERLAY_UI_OK`.

---

## Chunk 4: End-to-End Verification

### Task 8: Verify backend, frontend, and visual behavior

**Files:**
- Modify only if a verification failure exposes a requirement gap.

- [ ] **Step 1: Run all frontend tests**

```powershell
Get-ChildItem frontend/tests -Filter *.test.js | ForEach-Object {
  node $_.FullName
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

Expected: every frontend test exits 0.

- [ ] **Step 2: Parse application JavaScript**

```powershell
node -e "const fs=require('fs'); new Function(fs.readFileSync('frontend/js/app.js','utf8')); new Function(fs.readFileSync('frontend/js/delivery-completion-ui.js','utf8')); console.log('FRONTEND_JS_SYNTAX_OK')"
```

Expected: `FRONTEND_JS_SYNTAX_OK`.

- [ ] **Step 3: Run focused backend workflow tests**

```powershell
$env:TEMP='D:\Demo_Lao\EPL_System\.tmp_pytest'
$env:TMP='D:\Demo_Lao\EPL_System\.tmp_pytest'
C:\Users\zinnn\miniconda3\python.exe -m pytest backend/tests/test_delivery_completion_api.py backend/tests/test_delivery_order_closeout_api.py backend/tests/test_az_real_workflow_audit.py backend/tests/test_delivery_pod_eta_flow.py -q
```

Expected: all tests PASS.

- [ ] **Step 4: Run full backend test suite**

```powershell
C:\Users\zinnn\miniconda3\python.exe -m pytest backend/tests -q
```

Expected: 0 failures. Record any pre-existing unrelated failure separately rather than hiding it.

- [ ] **Step 5: Start the application server**

From `D:\Demo_Lao\EPL_System`, run:

```powershell
C:\Users\zinnn\miniconda3\python.exe -m uvicorn main:app --app-dir backend/app --host 127.0.0.1 --port 8000
```

If port 8000 is occupied, retry with 8001. Report the actual URL.

- [ ] **Step 6: Verify desktop visually**

At approximately 1440×900 verify:

- New module is visible in primary navigation.
- DO table actions fit without wrapping.
- Completion form displays POD and pricing side by side.
- Add/delete surcharge updates totals instantly.
- Loading/error/success toast appears above the dialog with correct tone.
- Tracking list selection updates the map and metrics.
- Incident and Event Timeline tabs still open and render.

- [ ] **Step 7: Verify mobile visually**

At approximately 390×844 verify navigation scroll/wrap behavior, stacked completion sections, non-overlapping buttons, table/card fallback, map dimensions, and no horizontal page overflow.

- [ ] **Step 8: Perform one database-backed demo transaction**

Use demo data or a test-scoped DO. Submit POD plus a known surcharge, reload the page, and verify the stored closeout and AR invoice retain the same final amount. Do not mutate irreplaceable user data.

- [ ] **Step 9: Final evidence summary**

Report changed files, exact test counts, server URL, the DO used for the demo transaction, stored base/surcharge/final amounts, and any residual risk.
