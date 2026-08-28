# EPL Demo Stabilization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to execute this plan task-by-task with specification and quality reviews.

**Goal:** Stabilize the complete EPL demo path from quotation through invoice, remove Vietnamese encoding defects, and make every visible workflow action persist through a validated backend contract.

**Architecture:** Keep the existing FastAPI, SQLAlchemy, PostgreSQL, and vanilla HTML/JavaScript architecture. Consolidate business rules in backend services, expose strict command schemas at API boundaries, seed one coherent end-to-end dataset, and make the frontend consume those contracts without runtime text-repair patches or mock state.

**Tech Stack:** Python 3, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, pytest, HTML/CSS, vanilla JavaScript, Node.js syntax/source tests, Playwright browser verification.

---

## Task 1: Establish UTF-8 and test-runner safety rails

**Files:**
- Modify: `RUN_AZ_AUDIT.ps1`
- Modify: `backend/app/main.py`
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`
- Modify: `frontend/js/workflow-ui-utils.js`
- Create: `frontend/tests/vietnamese-source-clean.test.js`
- Create: `frontend/tests/workflow-ui-utils.test.js`
- Create: `frontend/tests/route-map-utils.test.js`
- Create: `frontend/tests/route-segment-distance-realtime.test.js`
- Create: `frontend/tests/stress-runner-config.test.js`
- Test: `backend/tests/test_app_liveness.py`
- Test: `backend/tests/test_test_runner_page.py`

1. Add failing source tests that reject common mojibake sequences, corrupted replacement characters, and the runtime DOM-wide Vietnamese repair observer.
2. Restore `/test-runner` and `/kich-ban-test` as valid application pages or redirects and make the root liveness assertion use clean UTF-8 text.
3. Repair static Vietnamese strings with deterministic source conversion plus targeted corrections; remove the MutationObserver/tree-walk encoding patch once the source passes.
4. Restore the five frontend test files referenced by `RUN_AZ_AUDIT.ps1`, keeping each test focused on a real helper or source invariant.
5. Run the focused backend and Node tests, then run the source scan over all frontend HTML/JS/CSS files.

**Verify:**
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe -m pytest backend\tests\test_app_liveness.py backend\tests\test_test_runner_page.py backend\tests\test_vietnamese_source_clean.py -q --basetemp .tmp_pytest_task1`
`node frontend/tests/vietnamese-source-clean.test.js; node frontend/tests/workflow-ui-utils.test.js; node frontend/tests/route-map-utils.test.js; node frontend/tests/route-segment-distance-realtime.test.js; node frontend/tests/stress-runner-config.test.js`

## Task 2: Normalize Delivery Order lifecycle and analysis

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/services/workflow_service.py`
- Modify: `backend/app/routes/workflow_routes.py`
- Modify: `backend/app/main.py`
- Create/Modify: `backend/app/schemas/workflow.py`
- Create: `backend/tests/test_do_lifecycle_contract.py`
- Modify: `backend/tests/test_workflow_api_contract.py`
- Modify: `frontend/js/app.js`

1. Write failing tests for the lifecycle `pending -> in_transit -> delivered` and `pending -> cancelled`, with incidents represented separately and no DO approval transition. Add a direct contract test for `Quotation approved -> SO confirmed -> DO pending`.
2. Add strict Pydantic command schemas (`extra='forbid'`) for DO create/update/status actions and reject unknown cost or approval fields.
3. Replace approval-dependent dispatch rules with dispatch from `pending`, preserving referential validation and transaction boundaries.
4. Make operational analysis timezone-aware: UTC persistence, Ho Chi Minh display, `near_late` only within the next 24 hours, and overdue as a separate marker.
5. Remove all DO approval buttons, labels, and frontend calls; render the five operational views from backend analysis: near late, waiting, in transit, completed, incident.
6. Run focused lifecycle tests and the existing workflow suite.

**Verify:**
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe -m pytest backend\tests\test_do_lifecycle_contract.py backend\tests\test_workflow_api_contract.py backend\tests\test_workflow_draft_update_api.py -q --basetemp .tmp_pytest_task2`

## Task 3: Add the canonical schema migration

**Files:**
- Create: `backend/app/migrations/v013_demo_stabilization.py`
- Modify: `backend/app/migrations/runner.py`
- Modify: `backend/app/models.py`
- Create: `backend/tests/test_migration_v013_demo_stabilization.py`
- Create: `backend/tests/test_demo_database_reset.py`

1. Write failing migration tests for forward/idempotent execution and a disposable-database reset test.
2. Add DO lifecycle constraints, timezone-aware operational timestamps, POD lineage/uniqueness constraints, one active actual-cost record per Trip, and `Numeric` monetary columns needed by the golden path.
3. Keep legacy POD/cost columns readable during the demo stabilization window, without dual writes.
4. Require every new Trip, Dispatch, POD, and Invoice datetime command to include an offset (HTTP 422 otherwise), persist UTC, and serialize with `Z`.
5. Verify SQLite-compatible model tests and PostgreSQL migration behavior before resetting demo data.

**Verify:**
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe -m pytest backend\tests\test_migration_v013_demo_stabilization.py backend\tests\test_demo_database_reset.py -q --basetemp .tmp_pytest_task3`

## Task 4: Make Trip creation from DO transactional and route-backed

**Files:**
- Modify: `backend/app/services/tms_trip_service.py`
- Modify: `backend/app/routes/tms_planning_routes.py`
- Modify: `backend/app/main.py`
- Create/Modify: `backend/app/schemas/trip.py`
- Modify: `backend/app/services/workflow_service.py`
- Create: `backend/tests/test_trip_from_do_command.py`
- Create: `backend/tests/test_route_segment_validation.py`
- Modify: `frontend/js/app.js`

1. Add failing tests for creating one Trip from one or more compatible DOs, automatic Freight Order creation/reuse, idempotency, and rejection of mixed Freight Orders or incompatible routes/time windows.
2. Implement one transactional command that validates all DOs, creates/reuses the Freight Order, creates Trip and legs from Master Data route segments, and rolls back completely on failure.
3. Validate route segment distance totals and reject malformed or inconsistent `segments_json` at the API boundary.
4. Replace the frontend's sequential Trip/leg writes with the single command and render the form immediately with a loading state while reference data arrives.
5. Reject Trip datetimes without an offset and serialize persisted timestamps as UTC `Z`.
6. Run focused Trip/route tests and relevant existing TMS tests.

**Verify:**
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe -m pytest backend\tests\test_trip_from_do_command.py backend\tests\test_route_segment_validation.py backend\tests\test_trip_return_flow.py backend\tests\test_tms_core_planning.py -q --basetemp .tmp_pytest_task4`

## Task 5: Implement Dispatch ownership and safety rules

**Files:**
- Modify: `backend/app/services/tms_dispatch_service.py`
- Modify: `backend/app/routes/tms_planning_routes.py`
- Create/Modify: `backend/app/schemas/dispatch.py`
- Create: `backend/tests/test_dispatch_command_contract.py`
- Modify: `backend/tests/test_tms_dispatch_eligibility.py`
- Modify: `frontend/js/app.js`

1. Write failing tests for strict dispatch payloads, vehicle/driver availability, overlap detection, capacity, and route/time eligibility.
2. Dispatch only a valid Trip; the first successful dispatch changes every linked pending DO to `in_transit` atomically.
3. Reject Dispatch datetimes without an offset and serialize persisted timestamps as UTC `Z`.
4. Reject conflicting resources with the standard error envelope `{error:{code,message,fields,links}}`.
5. Keep scheduling and assignment in Dispatch Execution; Delivery & Transport only monitors the result.

**Verify:**
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe -m pytest backend\tests\test_dispatch_command_contract.py backend\tests\test_tms_dispatch_eligibility.py -q --basetemp .tmp_pytest_task5`

## Task 6: Consolidate POD lineage and operational costs

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/services/tms_execution_service.py`
- Modify: `backend/app/services/tms_cost_service.py`
- Modify: `backend/app/routes/workflow_routes.py`
- Modify: `backend/app/routes/tms_finance_routes.py`
- Create/Modify: `backend/app/schemas/pod.py`
- Create/Modify: `backend/app/schemas/cost.py`
- Create: `backend/tests/test_pod_lineage_contract.py`
- Create: `backend/tests/test_delivery_actual_cost_contract.py`
- Modify: `frontend/js/app.js`

1. Add failing tests requiring POD lineage to Trip, leg, DO, vehicle, and stop; require unique/idempotent writes and forbid completion without valid lineage.
2. Make `DeliveryPODRecord` canonical and keep the legacy POD table read-only for compatibility; remove dual writes.
3. Persist user-defined delivery cost lines through `FreightActualCost` and `FreightChargeItem`, using Decimal values, one active actual-cost record per Trip, and transactional totals.
4. Expose strict APIs for adding arbitrary cost rows containing item name, original amount, actual amount, computed increase, and note.
5. Remove DO save/approve controls from read-only DO views and connect the cost table's Add Row and Save actions to the canonical finance API.
6. Mark a DO `delivered` only when all required stops across all non-cancelled Trips have completed POD; rejected/partial POD keeps it `in_transit` and creates an incident; cancelling a Trip never cancels the DO.
7. Reject POD datetimes without an offset and serialize persisted timestamps as UTC `Z`.
8. Run POD/cost tests and existing finance/execution tests.

**Verify:**
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe -m pytest backend\tests\test_pod_lineage_contract.py backend\tests\test_delivery_actual_cost_contract.py backend\tests\test_delivery_pod_eta_flow.py backend\tests\test_tms_execution_events.py backend\tests\test_tms_freight_finance.py -q --basetemp .tmp_pytest_task6`

## Task 7: Harden command, error, and pagination contracts

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/routes/workflow_routes.py`
- Modify: `backend/app/routes/tms_planning_routes.py`
- Modify: `backend/app/routes/tms_finance_routes.py`
- Create/Modify: `backend/app/schemas/workflow.py`
- Create/Modify: `backend/app/schemas/trip.py`
- Create/Modify: `backend/app/schemas/dispatch.py`
- Create: `backend/app/schemas/common.py`
- Create: `backend/tests/test_strict_command_contracts.py`
- Create: `backend/tests/test_pagination_contract.py`
- Create: `backend/tests/test_error_envelope_contract.py`

1. Add failing tests proving QT, SO, DO, Route, Trip, Dispatch, POD, Cost, and AR Invoice reject unknown fields.
2. Normalize domain/validation failures to `{error:{code,message,fields,links}}`.
3. Return QT/SO/DO/Trip lists as `{items,total,page,page_size}`, cap `page_size` at 200, and use stable ordering with a unique tie-breaker.
4. Update frontend adapters to consume the paginated shape without mock fallbacks.

**Verify:**
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe -m pytest backend\tests\test_strict_command_contracts.py backend\tests\test_pagination_contract.py backend\tests\test_error_envelope_contract.py -q --basetemp .tmp_pytest_task7`

## Task 8: Implement the AR Invoice end of the golden path

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/models.py`
- Create: `backend/app/services/ar_invoice_service.py`
- Create/Modify: `backend/app/schemas/invoice.py`
- Create: `backend/tests/test_ar_invoice_contract.py`
- Modify: `frontend/js/app.js`

1. Write failing tests for invoice creation from a delivered DO/SO, Decimal totals, strict payload validation, posting idempotency, and database read-back.
2. Move the raw `/api/invoices/post` dictionary logic into a transactional service and preserve one active AR Invoice per DO.
3. Calculate invoice totals from persisted contract and approved adjustments, then post the journal once.
4. Reject Invoice datetimes without an offset and serialize persisted timestamps as UTC `Z`.
5. Update the frontend to display the persisted invoice returned by the API.

**Verify:**
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe -m pytest backend\tests\test_ar_invoice_contract.py backend\tests\test_dashboard_payload_contract.py -q --basetemp .tmp_pytest_task8`

## Task 9: Reset and seed a coherent PostgreSQL demo dataset

**Files:**
- Modify: `backend/app/seed_full_demo.py`
- Modify/Create: `backend/app/services/demo_seed_service.py`
- Modify: `RUN_DEMO_3_GIO.ps1`
- Create: `backend/tests/test_demo_seed_golden_path.py`

1. Add a failing integration test that seeds and traverses Customer, Route with segments, Quotation, SO, DO, Trip, Dispatch, POD, Actual Cost, and AR Invoice.
2. Build an idempotent seed/reset transaction with stable demo codes and valid foreign keys; remove stale mock-only records and invalid zero-distance segments.
3. Reset the approved PostgreSQL demo database only after schema and seed tests pass, then run the seed twice to prove idempotency.
4. Query the key tables and verify expected counts, statuses, monetary totals, and lineage.

**Verify:**
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe -m pytest backend\tests\test_demo_seed_golden_path.py backend\tests\test_database_readiness.py -q --basetemp .tmp_pytest_task9`
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe backend\app\seed_full_demo.py --reset --verify; C:\Users\zinnn\miniconda3\python.exe backend\app\seed_full_demo.py --reset --verify`

## Task 10: Align frontend contracts, loading behavior, and Vietnamese copy

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`
- Modify: `frontend/js/workflow-ui-utils.js`
- Modify: `frontend/js/lang.json`
- Create: `frontend/tests/api-contract-ui.test.js`
- Create: `frontend/tests/loading-shell-ui.test.js`
- Modify: `frontend/tests/vietnamese-source-clean.test.js`

1. Add failing static/UI tests for strict request payloads, all required i18n keys, immediate form shells, icon-only view buttons with accessible labels, and absence of hidden mock fallbacks.
2. Render forms and table skeletons before fetch completion; update data asynchronously and show explicit retry/error states.
3. Make labels consistent across Quotation, SO, DO, Trip, Dispatch, POD, Cost, and Invoice; repair all remaining Vietnamese source defects.
4. Remove duplicate actions and duplicate workflow panels; keep each operation in its owning module and link to it instead of embedding another full form.
5. Run all frontend Node tests and JavaScript syntax checks.

**Verify:**
`node frontend/tests/api-contract-ui.test.js; node frontend/tests/loading-shell-ui.test.js; node frontend/tests/vietnamese-source-clean.test.js`
`node -e "const fs=require('fs'); for (const f of fs.readdirSync('frontend/js').filter(x=>x.endsWith('.js'))) new Function(fs.readFileSync('frontend/js/'+f,'utf8')); console.log('JS_OK')"`

## Task 11: Consolidate the delivery UI around the real workflow

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`
- Modify: `frontend/css/styles.css`
- Create: `frontend/tests/delivery-workflow-ui.test.js`

1. Add failing tests for a compact three-area delivery workspace: active/completed Trips, selected DO/POD detail, and operational incidents.
2. Keep waiting DOs and Trip planning in Operations Planning, dispatch/resource assignment in Dispatch Execution, and only monitoring/completed Trip/POD in Delivery & Transport.
3. Replace oversized empty panels with concise empty states and View actions; move explanatory notes into a modal opened from the header.
4. Ensure desktop and mobile layouts have no horizontal overflow, clipped labels, duplicated controls, or workflow/sidebar overlap.
5. Run focused UI tests and inspect browser screenshots at desktop and mobile sizes.

**Verify:**
`node frontend/tests/delivery-workflow-ui.test.js`

## Task 12: End-to-end verification and demo handoff

**Files:**
- Modify: `KICH_BAN_DEMO_3_GIO_TMS.md`
- Modify: `DEMO_CHEAT_SHEET_1_TRANG.md`
- Create: `KICH_BAN_THUYET_TRINH_SONG_NGU.md`
- Modify: `RUN_AZ_AUDIT.ps1`
- Create: `package.json`
- Create: `package-lock.json`
- Create: `playwright.config.js`
- Create: `frontend/tests/e2e/golden-path.spec.js`

1. Run all backend tests with a fresh pytest temp directory.
2. Run every frontend Node test, syntax check, and `RUN_AZ_AUDIT.ps1` without missing files.
3. Pin `@playwright/test` in the npm manifest/lockfile and install Chromium before the demo so E2E never relies on an implicit `npx` package download.
4. Start the application and run `frontend/tests/e2e/golden-path.spec.js` to execute QT -> SO -> DO -> Trip -> Dispatch -> POD -> Actual Cost -> AR Invoice against PostgreSQL; after every command, reload from the API/database before asserting the next screen.
5. Capture desktop/mobile screenshots and check browser console/network errors.
6. Update the Vietnamese demo script and one-page cheat sheet with the final statuses, ownership boundaries, and exact click path.
7. Create a bilingual presentation script with short English lines, Vietnamese meaning, Vietnamese-friendly pronunciation, expected screen action, and recovery lines for slow data or questions.
8. Report remaining non-critical risks separately; do not label the build ready unless all golden-path assertions pass.

**Verify:**
`$env:PYTHONPATH=(Resolve-Path backend\app); C:\Users\zinnn\miniconda3\python.exe -m pytest backend\tests -q --basetemp .tmp_pytest_final`
`powershell -ExecutionPolicy Bypass -File .\RUN_AZ_AUDIT.ps1`
`npm ci; npx playwright install chromium; npx playwright test frontend/tests/e2e/golden-path.spec.js`
