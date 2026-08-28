# EPL Foundation Recovery Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Làm cho EPL khởi động, audit, lưu PostgreSQL và phản ánh UI trung thực; loại bỏ duplicate/mock/mojibake gây sai luồng hiện tại.

**Architecture:** FastAPI import được khi database/AI integration lỗi; readiness phản ánh PostgreSQL và migration thật. Workflow router có một chủ sở hữu. Frontend dùng utility testable cho command policy và route segment policy, không mutate trước server commit.

**Tech Stack:** Python/FastAPI/SQLAlchemy/PostgreSQL/pytest, PowerShell, vanilla JavaScript/Node.

**Repository note:** `D:\Demo_Lao\EPL_System` hiện không có `.git`. Mỗi “checkpoint” dưới đây phải ghi lại danh sách file và kết quả test; nếu repository được khởi tạo trước lúc thực thi thì checkpoint được thay bằng commit tương ứng.

---

## Chunk 1: Trustworthy runtime and audit

### Task 1: Extract a testable PowerShell audit runner

**Files:**
- Create: `scripts/audit-lib.ps1`
- Modify: `RUN_AZ_AUDIT.ps1`
- Create: `backend/tests/test_audit_runner_contract.py`

- [ ] **Step 1: RED — native failure propagation**

Write `test_native_failure_exits_with_same_code_and_never_prints_pass`. It invokes `RUN_AZ_AUDIT.ps1 -ContractProbeExitCode 7`, asserts process return code `7`, output contains `A-Z AUDIT FAILED`, and excludes both `A-Z AUDIT PASSED` and the old green `A-Z AUDIT FINISHED`.

- [ ] **Step 2: Run RED**

Run `python -m pytest backend\tests\test_audit_runner_contract.py::test_native_failure_exits_with_same_code_and_never_prints_pass -q`.
Expected: FAIL because the current script has no probe seam and returns success.

- [ ] **Step 3: GREEN — checked native helper and guarded entry point**

Create `Invoke-CheckedNative` in `scripts/audit-lib.ps1`. `RUN_AZ_AUDIT.ps1` accepts the hidden probe parameter for contract testing, dot-sources the library, invokes a process that exits with the requested code, and exits immediately on failure. Production execution uses the same helper for every Node/Python command.

- [ ] **Step 4: Verify GREEN**

Run the focused test. Expected: `1 passed` and process exit 0 for pytest.

- [ ] **Step 5: RED — explicit interpreter override**

Add tests that valid absolute `EPL_PYTHON` wins, while relative/nonexistent explicit values fail without fallback.

- [ ] **Step 6: RED — environment/PATH precedence**

Add tests that valid `VIRTUAL_ENV\Scripts\python.exe` is second, PATH `python` is third, and all sources absent/invalid fails.

- [ ] **Step 7: RED — forbidden fallback/source scan**

Add a test proving `py` and hardcoded `miniconda3\python.exe` do not appear in either script.

- [ ] **Step 8: Run RED**

Run the whole audit contract file. Expected: interpreter tests FAIL on the current hardcoded executable.

- [ ] **Step 9: GREEN — implement resolver**

Implement `Resolve-EplPython` with the exact precedence above. Validate absolute candidate path and `--version`. If an explicitly supplied `EPL_PYTHON` is invalid, stop; do not silently select another interpreter. Use the resolved executable for Python compile, backend pytest and PostgreSQL audit, in that order, with `EPL_ENV_FILE` preserved.

Expose a tested script entry parameter `scripts\audit-lib.ps1 -ResolvePython` that prints only the resolved absolute executable path and exits nonzero on resolution failure.

- [ ] **Step 10: Verify GREEN**

Run `python -m pytest backend\tests\test_audit_runner_contract.py -q`. Expected: all pass. Record changed files and output in the implementation log.

- [ ] **Step 11: Commit/checkpoint**

If `.git` exists, run `git add RUN_AZ_AUDIT.ps1 scripts/audit-lib.ps1 backend/tests/test_audit_runner_contract.py` and `git commit -m "fix: make A-Z audit fail truthfully"`. Otherwise record the same file list and test output in the implementation handoff.

### Task 2: Make application liveness independent of PostgreSQL and OpenCV

**Files:**
- Modify: `backend/app/database.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/routes/health_routes.py`
- Create: `backend/tests/test_app_liveness.py`

- [ ] **Step 1: RED — import while database and cv2 are unavailable**

Write `test_main_import_does_not_connect_database_or_import_cv2`. Patch SQLAlchemy connection and Python import for `cv2` to raise if called, clear app modules, import `main`, and assert `/api/health` returns `200 {"status":"ok"}`.

- [ ] **Step 2: Run RED**

Run `python -m pytest backend\tests\test_app_liveness.py::test_main_import_does_not_connect_database_or_import_cv2 -q`.
Expected: FAIL at current module-scope `cv2` import or database initialization.

- [ ] **Step 3: GREEN — defer external dependencies**

Remove module-scope `cv2`/NumPy imports. Ensure `database.py` builds an engine without opening a connection. Register a liveness router that has no database dependency.

- [ ] **Step 4: Verify GREEN**

Run focused test. Expected: `1 passed`.

- [ ] **Step 5: RED — AI dependency error contract**

Add `test_checkpoint_returns_503_vietnamese_error_when_cv2_is_unavailable`. Post a small file, force lazy import failure, assert HTTP 503 and `detail.code == "AI_DEPENDENCY_UNAVAILABLE"`; assert Vietnamese `detail.message` and no stack trace/path.

- [ ] **Step 6: Run RED**

Run `python -m pytest backend\tests\test_app_liveness.py::test_checkpoint_returns_503_vietnamese_error_when_cv2_is_unavailable -q`. Expected: FAIL with current 500.

- [ ] **Step 7: GREEN — sanitize unavailable AI dependency**

Change checkpoint loading to catch dependency import/ABI errors and return the specified sanitized 503.

- [ ] **Step 8: Verify GREEN**

Run `python -m pytest backend\tests\test_app_liveness.py -q`. Expected: `2 passed`.

- [ ] **Step 9: Commit/checkpoint**

Commit `fix: isolate optional AI dependencies` if Git exists; otherwise record files/output.

### Task 3: Add PostgreSQL migration-aware readiness

**Files:**
- Create: `backend/app/runtime_state.py`
- Modify: `backend/app/routes/health_routes.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/migrations/runner.py`
- Create: `backend/tests/test_database_readiness.py`

- [ ] **Step 1: RED — exact readiness success contract**

Write `test_database_readiness_requires_connection_head_and_core_tables`. Using isolated SQLite/test connection or injected checker, assert success only when `SELECT 1`, required migration head and all seven core tables (`customers`, `routes`, `vehicles`, `drivers`, `quotations`, `sales_orders`, `delivery_orders`) exist. Expected payload is exactly `{status:"ok", database:"postgresql"}` in PostgreSQL mode.

- [ ] **Step 2: Run RED**

Run `python -m pytest backend\tests\test_database_readiness.py::test_database_readiness_requires_connection_head_and_core_tables -q`. Expected: `1 failed` with HTTP 404 because the endpoint is absent.

- [ ] **Step 3: GREEN — readiness checker**

Implement a checker with injected engine/dialect for tests and route `/api/health/database`. Query `schema_migrations` for the required head from the migration runner plus table inspection.

- [ ] **Step 4: Verify GREEN**

Run `python -m pytest backend\tests\test_database_readiness.py::test_database_readiness_requires_connection_head_and_core_tables -q`. Expected: `1 passed`.

- [ ] **Step 5: RED — database failure classification**

Add parameterized timeout/unavailable, authentication and missing migration/table tests; every result is HTTP 503 with stable code and Vietnamese `detail.message`.

- [ ] **Step 6: Run classification RED**

Run `python -m pytest backend\tests\test_database_readiness.py -k "classification" -q`. Expected: the new cases fail.

- [ ] **Step 7: GREEN — exception mapping**

Map database exceptions to `DATABASE_TIMEOUT`, `DATABASE_AUTH_FAILED`, `DATABASE_SCHEMA_INVALID`, `DATABASE_UNAVAILABLE`; make classification cases pass.

- [ ] **Step 7a: Verify classification GREEN**

Run `python -m pytest backend\tests\test_database_readiness.py -k "classification" -q`. Expected: all selected classification cases pass.

- [ ] **Step 8: RED — sanitized correlated startup failure**

Add a test asserting response/log share a correlation ID and neither contains SQL, URL nor password.

- [ ] **Step 9: Run correlated logging RED**

Run `python -m pytest backend\tests\test_database_readiness.py::test_startup_failure_log_and_response_share_sanitized_correlation_id -q`. Expected: `1 failed` because the correlation/sanitization contract is absent.

- [ ] **Step 10: GREEN — correlated sanitized logging**

Implement sanitized startup/readiness logging.

- [ ] **Step 11: Verify correlated logging GREEN**

Run `python -m pytest backend\tests\test_database_readiness.py::test_startup_failure_log_and_response_share_sanitized_correlation_id -q`. Expected: `1 passed`.

- [ ] **Step 12: RED — migration failure memory**

Add tests that successful connection/readiness does not clear remembered migration failure, while successful `auto_migrate_db()` does.

- [ ] **Step 13: Run memory RED**

Run `python -m pytest backend\tests\test_database_readiness.py -k "migration_failure" -q`. Expected: new memory cases fail.

- [ ] **Step 14: GREEN — runtime migration state**

Implement `RuntimeState` with explicit `remember_migration_failure` and `clear_after_successful_migration` operations.

- [ ] **Step 15: GREEN — startup migration lifecycle**

Have startup set/clear runtime state around a real `auto_migrate_db()` call into the migration runner; connectivity checks only read the flag.

- [ ] **Step 16: Verify GREEN**

Run `python -m pytest backend\tests\test_app_liveness.py backend\tests\test_database_readiness.py -q`; expected all pass.

- [ ] **Step 17: Commit/checkpoint**

Commit `feat: add migration-aware database readiness` if Git exists; otherwise record files/output. Do not claim readiness against real PostgreSQL until final audit connects.

## Chunk 2: One canonical workflow backend

### Task 4: Characterize every public workflow route and detect duplicates

**Files:**
- Create: `backend/tests/test_route_uniqueness.py`
- Create: `backend/tests/test_workflow_api_contract.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: RED — normalized route uniqueness**

Write `test_every_method_and_normalized_path_is_unique`: normalize trailing slash and replace every `{parameter_name}` with `{param}`; group `app.routes` and assert duplicate groups equal `[]`. Add `test_workflow_routes_are_owned_by_workflow_module`, asserting every enumerated endpoint function has `__module__ == "routes.workflow_routes"`.

- [ ] **Step 2: Run RED**

Run `python -m pytest backend\tests\test_route_uniqueness.py::test_every_method_and_normalized_path_is_unique backend\tests\test_route_uniqueness.py::test_workflow_routes_are_owned_by_workflow_module -q`. Expected: FAIL listing duplicates/incorrect owners, not import error.

- [ ] **Step 3: RED — characterize public contracts**

First add isolated reusable builders to `backend/tests/conftest.py` for customer, route, quotation, SO, DO, vehicle and driver. Then create named tests per entity. GET collections/POD return JSON list/entity. POST/PUT commands return string `message` and object `data` with matching `id`/`do_id`. DELETE returns string `message` plus `data: {id: <deleted-id>}`. Enumerate GET/POST quotations; PUT quotation approve/status; DELETE quotation; GET/POST SO; PUT SO confirm/status; DELETE SO; GET/POST DO; PUT DO status/dispatch; DELETE DO; GET/POST POD. Include `GET /api/pod/{do_id}` and `PUT /api/quotations/{qt_id}/status`.

- [ ] **Step 4: Run characterization tests**

Run `python -m pytest backend\tests\test_workflow_api_contract.py -q`. Expected: supported routes pass; missing/inconsistent routes fail with the named shape assertion.

### Task 5: Make workflow router the only owner

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/routes/workflow_routes.py`
- Modify: `backend/app/services/workflow_service.py`
- Modify: `backend/app/services/errors.py`
- Modify: `backend/tests/test_workflow_delete_guards.py`

- [ ] **Step 1: GREEN — migrate compatibility endpoints**

Add `GET /api/pod/{do_id}` and quotation status compatibility to `workflow_routes.py`, delegating to service/query functions. Preserve the characterized public URLs and success shapes.

- [ ] **Step 2: Remove duplicate registrations**

Delete workflow handlers from `main.py`, delete route-list mutation in `install_workflow_routes`, and include the router normally once. Run uniqueness test; expected pass with zero duplicates.

- [ ] **Step 3: RED — exact lock error and non-mutation cases**

Update/add tests: approved quotation DELETE, confirmed SO DELETE, approved DO DELETE and in-transit DO DELETE each return 409 with `detail.code == LOCKED_RECORD`, Vietnamese `detail.message`, and `navigation_targets`. Invalid transitions return 409 and a fresh DB query confirms status/version unchanged.

- [ ] **Step 4: Run RED**

Run `python -m pytest backend\tests\test_workflow_delete_guards.py -q`. Expected: FAIL where current errors return 400 or shape differs.

- [ ] **Step 5: GREEN — normalize domain conflicts**

Set `LOCKED_RECORD`, `INVALID_TRANSITION`, busy-resource and version/state conflicts to HTTP 409 in the centralized error mapping. Ensure rollback happens before response.

- [ ] **Step 5a: GREEN — preserve DELETE response contract**

Update quotation, SO and DO DELETE handlers to return `{message, data: {id: deleted_id}}` after successful commit; keep locked failures at 409 without deletion.

- [ ] **Step 6: Verify and checkpoint**

Run:

```powershell
python -m pytest backend\tests\test_route_uniqueness.py backend\tests\test_workflow_api_contract.py backend\tests\test_workflow_delete_guards.py -q
python -m py_compile backend\app\main.py backend\app\routes\workflow_routes.py backend\app\services\workflow_service.py backend\app\services\errors.py
```

Expected: all tests pass and compile exits 0. Run `backend/tests/az_postgres_audit.py`; success requires exit 0 and `bad_rows: 0`; unavailable PostgreSQL is a blocked result, never a pass. Record checkpoint.

Exact PostgreSQL command: `$env:EPL_ENV_FILE='D:\Demo_Lao\.env'; $auditPython = & powershell -NoProfile -File scripts\audit-lib.ps1 -ResolvePython; & $auditPython backend\tests\az_postgres_audit.py`. If Git exists commit `refactor: consolidate canonical workflow routes`; otherwise record the same file set and outputs.

## Chunk 3: Frontend integrity and truthful commands

### Task 6: Add broad duplicate detection and remove collisions

**Files:**
- Create: `frontend/tests/frontend-uniqueness.test.js`
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`

- [ ] **Step 1: RED — duplicate IDs and effective globals**

Test all HTML IDs. For JavaScript, detect collisions across `function name()`, `async function name()`, `window.name = function`, `window.name = async function`, and top-level `const/let/var name = function`. Assert known collisions including `submitPOD`, `approveSO`, `approveQuotation`, `saveOracleQT`, `saveRouteConfig`, `optimizeMasterForm`, `addSOLineRow`, `calcSOLineTotal` and any collision discovered by the scanner.

- [ ] **Step 2: Run RED**

Run `node frontend\tests\frontend-uniqueness.test.js`. Expected: FAIL listing current duplicate IDs/globals.

- [ ] **Step 3: GREEN — namespace DOM IDs**

Rename overview, CRM and modal IDs with `overview-`, `crm-`, `modal-`; update every JS/HTML selector.

- [ ] **Step 4: Verify ID GREEN**

Run `node frontend\tests\frontend-uniqueness.test.js --ids-only`. Expected: duplicate ID count 0.

- [ ] **Step 5: GREEN — consolidate global implementations**

Keep the implementation that calls real APIs and applies workflow locks; remove placeholders/overrides. Re-run full uniqueness test; expected pass.

- [ ] **Step 6: Verify globals and regression**

Run `node frontend\tests\frontend-uniqueness.test.js`, `node --check frontend\js\app.js`, `node frontend\tests\workflow-ui-utils.test.js`, `node frontend\tests\route-map-utils.test.js`, and `node frontend\tests\vietnamese-source-clean.test.js`. Expected each exit 0.

- [ ] **Step 7: Commit/checkpoint**

If Git exists commit `refactor: remove frontend identifier collisions`; otherwise record modified files and exact outputs.

### Task 7: Extract and enforce route-segment integrity

**Files:**
- Create: `frontend/js/route-segment-policy.js`
- Create: `frontend/js/workflow-presentation.js`
- Create: `frontend/tests/route-segment-policy.test.js`
- Create: `frontend/tests/workflow-presentation.test.js`
- Modify: `frontend/js/app.js`
- Modify: `frontend/index.html`
- Modify: `frontend/tests/route-segment-distance-realtime.test.js`
- Create: `frontend/tests/operational-data-integrity.test.js`

- [ ] **Step 1: RED — routing failure policy**

Define wished-for API `validateManualDistance({km, confirmed, source, verifier, now})` and `resolveSegment({from,to,manual,routingClient,persist})`. Test routing 503 returns `{ok:false}` and never invokes `persist`; caller test verifies DOM adapter receives no segment and total remains unchanged.

- [ ] **Step 2: RED — manual distance and persistence**

Test km must be >0 and <=5000, confirmed is true, source is one of `odometer`, `carrier_document`, `map_measurement`, `other`; valid result contains injected verifier/time. Define and test `serializeSegments(segments)` plus `deserializeSegments(json)` for the metadata round trip.

- [ ] **Step 3: Run RED**

Run `node frontend\tests\route-segment-policy.test.js`. Expected: FAIL because module is absent.

- [ ] **Step 4: GREEN — implement pure route policy**

Implement the four pure exports and make policy tests pass.

- [ ] **Step 5: GREEN — wire route UI adapter**

Make `addRouteSegment` pass a DOM append callback as `persist`; remove random fallback. On `{ok:false}`, show CTA and leave DOM/total unchanged. Add manual confirmation/source fields only when manual distance is entered. Obtain verifier from the current UI actor helper/header, falling back to explicit `system` only when authentication is not configured.

- [ ] **Step 6: GREEN — persist route metadata**

Change `saveRouteConfig` to call `serializeSegments`, preserving distance source/verifier/time in `segments_json`. Change route load/render to call `deserializeSegments` and restore the same metadata. Run the metadata round-trip and existing realtime distance tests; expected pass.

- [ ] **Step 7: RED — operational hardcode and presentation rules**

Test named dashboard/dispatch/tracking/accounting/detail containers contain no hardcoded operational `DEMO-*` row/card/value or 200 km. Test business IDs are not generated by `Math.random()` (including vehicle type); placeholders use “Ví dụ”, not `VD:`. In `workflow-presentation.test.js`, test pure `presentRecord(record)` adds `is_demo` and label “Dữ liệu demo” for `DEMO-*`, and pure `actionsForStatus(entity,status)` keeps view but removes/disables edit/delete for locked states.

- [ ] **Step 8: Run RED**

Run `node frontend\tests\operational-data-integrity.test.js` and `node frontend\tests\workflow-presentation.test.js`. Expected: failures for hardcoded markup/missing module.

- [ ] **Step 9: GREEN — implement presentation helpers**

Implement `presentRecord` and `actionsForStatus`; make `workflow-presentation.test.js` pass before wiring DOM renderers.

- [ ] **Step 10: GREEN — dashboard and dispatch empty/API renderers**

Remove hardcoded rows from dashboard/dispatch containers and render empty/API states using `presentRecord`.

- [ ] **Step 11: GREEN — tracking, accounting and detail renderers**

Remove hardcoded rows/cards from tracking/accounting/detail containers, update placeholders to “Ví dụ”, use backend-generated business IDs, and wire demo badges/actions.

- [ ] **Step 12: Verify GREEN**

Run `node frontend\tests\route-segment-policy.test.js`, `node frontend\tests\route-segment-distance-realtime.test.js`, `node frontend\tests\operational-data-integrity.test.js`, and `node frontend\tests\workflow-presentation.test.js`. Expected each exit 0.

- [ ] **Step 13: Commit/checkpoint**

Commit `fix: remove fake operational route data` if Git exists; otherwise record files/output.

### Task 8: Centralize server-confirmed command policy

**Files:**
- Create: `frontend/js/command-policy.js`
- Create: `frontend/js/workflow-command-adapters.js`
- Create: `frontend/tests/command-state-consistency.test.js`
- Create: `frontend/tests/workflow-command-adapters.test.js`
- Modify: `frontend/js/app.js`
- Modify: `frontend/index.html`

- [ ] **Step 1: RED — command result matrix**

Test `executeCommand({request,applySuccess,reload,onError})`: HTTP 4xx, 5xx and network failure never call `applySuccess`/reload; 2xx calls `applySuccess(payload)` then reload exactly once. Cover `detail.message`, string `detail`, Vietnamese next action, and `navigation_targets` CTA model.

- [ ] **Step 2: Run RED**

Run `node frontend\tests\command-state-consistency.test.js`. Expected: FAIL because module is absent.

- [ ] **Step 3: GREEN — implement pure command policy**

Implement error normalization and server-confirmed `applySuccess`/reload. Make policy tests pass.

- [ ] **Step 4: RED — workflow adapters cannot pre-mutate**

Test exported adapters for quotation create/edit/approve, SO create/edit/confirm, DO create/edit/approve, dispatch, shipment step and POD with a frozen initial state. For 4xx/5xx/network errors assert deep equality with initial state; for 2xx assert state derives from returned payload/reload. These adapters must contain all call-site state changes.

- [ ] **Step 5: Run adapter RED**

Run `node frontend\tests\workflow-command-adapters.test.js`. Expected: FAIL because module is absent/current handlers mutate directly.

- [ ] **Step 6: GREEN — quotation adapters**

Implement quotation create/edit/approve adapters using `executeCommand`; make matching `app.js` handlers delegate without assigning business status outside adapters. Run quotation adapter cases; expected pass.

- [ ] **Step 7: GREEN — sales-order adapters**

Implement SO create/edit/confirm adapters and wire handlers. Run SO adapter cases; expected pass.

- [ ] **Step 8: GREEN — delivery-order adapters**

Implement DO create/edit/approve adapters and wire handlers. Run DO adapter cases; expected pass.

- [ ] **Step 9: GREEN — dispatch and shipment adapters**

Implement dispatch and shipment-step adapters, removing optimistic assignments and temporary-success messages. Run corresponding adapter cases; expected pass.

- [ ] **Step 10: GREEN — POD adapter**

Implement POD adapter and wire submit handler; state changes only from server payload/reload. Run POD adapter cases; expected pass.

- [ ] **Step 11: GREEN — locked action presentation**

Use the already-tested `actionsForStatus` helper so approved/confirmed/in-transit entities hide or disable edit/delete while view remains available.

- [ ] **Step 12: Verify GREEN**

Run `node frontend\tests\command-state-consistency.test.js`, `node frontend\tests\workflow-command-adapters.test.js`, `node frontend\tests\workflow-presentation.test.js`, `node frontend\tests\workflow-ui-utils.test.js`, `node frontend\tests\frontend-uniqueness.test.js`, and `node --check frontend\js\app.js`. Expected each exit 0.

- [ ] **Step 13: Commit/checkpoint**

Commit `fix: make workflow commands server-confirmed` if Git exists; otherwise record files/output.

## Chunk 4: UTF-8, full audit and browser acceptance

### Task 9: Repair and relabel the runner

**Files:**
- Modify: `frontend/test_15_button_flow_runner.html`
- Modify: `frontend/tests/stress-runner-config.test.js`
- Modify: `frontend/tests/vietnamese-source-clean.test.js`
- Modify: `backend/tests/test_test_runner_page.py`

- [ ] **Step 1: RED — exact Vietnamese and honest coverage label**

Assert runner contains correctly encoded “Kịch bản”, “Kiểm thử”, “Mở màn hình”, “Tạm dừng”, “Tiếp tục”, “Dừng” and notice “Kiểm thử API, không thay thế kiểm thử giao diện”. Assert known mojibake byte patterns are absent.

- [ ] **Step 2: Run RED**

Run `node frontend\tests\vietnamese-source-clean.test.js` and `node frontend\tests\stress-runner-config.test.js`. Expected: at least one exits nonzero and reports current mojibake/missing coverage notice.

- [ ] **Step 3: GREEN — repair UTF-8 without altering controls**

Convert visible text to UTF-8, preserve 5,000/2,000ms configuration, pause/resume/stop and `E2E-STRESS-*` isolation.

- [ ] **Step 4: Verify GREEN**

Run `node frontend\tests\vietnamese-source-clean.test.js`, `node frontend\tests\stress-runner-config.test.js`, and `python -m pytest backend\tests\test_test_runner_page.py -q`. Expected: both Node commands exit 0 and pytest reports `2 passed`.

- [ ] **Step 5: Commit/checkpoint**

Record source encoding verification and tests.

### Task 10: Run real PostgreSQL and browser acceptance

**Files:**
- Modify: `backend/tests/az_postgres_audit.py` only if a failing test proves contract defect
- Modify: `backend/requirements-dev.txt`
- Create: `backend/tests/foundation_browser_acceptance.py` using Python Playwright sync API
- Create: `backend/tests/cleanup_foundation_e2e_data.py`
- Create: `backend/tests/test_cleanup_foundation_e2e_data.py`
- Update: `KICH_BAN_THAO_TAC_A_Z.md`

- [ ] **Step 1: Install deterministic browser harness**

Add exact pin `playwright==1.55.0` to `backend/requirements-dev.txt`. Resolve `$auditPython = powershell -NoProfile -File scripts\audit-lib.ps1 -ResolvePython`; run `& $auditPython -m pip install -r backend\requirements-dev.txt`, `& $auditPython -m playwright install chromium`, then `& $auditPython -c "from playwright.sync_api import sync_playwright; print('PLAYWRIGHT_OK')"`; expected `PLAYWRIGHT_OK`.

- [ ] **Step 2: RED — create isolated full workflow fixture**

In `foundation_browser_acceptance.py`, generate one prefix and create customer, route with manual 10 km `map_measurement`, quotation→approved, SO→confirmed, DO→approved, plus vehicle/driver when an in-transit case is used. Record every owned table/ID in a JSON manifest under the pytest temp directory. Never query/select an existing business record for mutation.

- [ ] **Step 3: RED — implement safe cleanup contract**

Create cleanup script accepting `--manifest <absolute-json>` and optional `--apply`. Manifest stores typed selectors, not an assumption that every primary key is textual: business tables use exact prefixed `id`/`do_id`/`invoice_id`; `audit_logs` use exact prefixed `record_id` plus allowed table name; auto-increment dependent rows use foreign-key selectors traced only from the owned IDs. Validate every user-supplied textual business selector starts with `E2E-FOUNDATION-`, every table/column is from a hardcoded allowlist, and never accept arbitrary SQL. Dry-run prints dependency-order counts. Apply deletes only manifest-owned rows in dependency order including `journal_lines`, `journal_batches`, `gl_transactions`, `ar_invoices`, `pod`, `vehicle_tracking`, `incidents`, `shipment_costs`, `delivery_order_details`, `delivery_orders`, `sales_orders`, `quotation_details`, `quotations`, `audit_logs`, `routes`, `drivers`, `vehicles`, `customers`; skip a table only when schema inspection proves it absent.

- [ ] **Step 3a: RED/GREEN — cleanup safety tests**

In `test_cleanup_foundation_e2e_data.py`, test invalid/non-prefixed business selector aborts, audit selector uses `record_id` rather than numeric PK, foreign-key selector cannot escape owned parents, dry-run performs zero DELETE statements, dependency order, absent optional tables and apply limited to manifest selectors. Run `& $auditPython -m pytest backend\tests\test_cleanup_foundation_e2e_data.py -q`; expected RED before implementation, then `7 passed` after implementation.

- [ ] **Step 4: Start PostgreSQL-backed server deterministically**

`foundation_browser_acceptance.py` is the sole process controller. Before spawn, bind-test `127.0.0.1:8000` and `:8001`; if either is occupied, fail before touching data. Its session fixture copies `os.environ`, sets `EPL_ENV_FILE=D:\Demo_Lao\.env` and `DATABASE_MODE=postgres` only in `postgres_env`, then calls `subprocess.Popen([sys.executable,"-m","uvicorn","main:app","--host","127.0.0.1","--port","8000"], cwd=BACKEND_APP, env=postgres_env, creationflags=CREATE_NO_WINDOW)`. During every poll first assert `process.poll() is None`; only then accept `/api/health`. Poll every 0.5 seconds for at most 20 seconds; require `/api/health/database` JSON equals `{status:"ok",database:"postgresql"}`. The fixture yields process/URL/environment and in `finally` calls `terminate()`, waits 5 seconds, then `kill()`/wait if needed.

- [ ] **Step 5: Start database-down server in isolation**

The same pytest fixture creates a second independent `down_env = os.environ.copy()` with `EPL_ENV_FILE` pointing to its pytest-temp nonexistent path, `DATABASE_MODE=postgres`, and `DATABASE_URL=postgresql+psycopg2://invalid:invalid@127.0.0.1:1/epl_unavailable`. Start via `subprocess.Popen` with the same arguments except port 8001. During polling require `down_process.poll() is None`; poll only `/api/health` for 20 seconds. Yield both processes; the same `finally` terminates each using terminate→5-second wait→kill. Parent `os.environ` is never modified.

- [ ] **Step 6: RED — browser scenarios**

Use Chromium headless. Against port 8000, create the owned fixture through UI/API setup, reload route, assert 10 km and metadata persist; intercept Nominatim/OSRM and assert no segment/total change plus CTA; assert direct locked DELETE calls return 409; open `/test-runner` and assert correct UTF-8 notice. Against port 8001 assert database error deadline. Run `& $auditPython -m pytest backend\tests\foundation_browser_acceptance.py -q`; expected failures until all production behavior is wired.

- [ ] **Step 7: Implement only evidence-backed acceptance fixes**

For each failing scenario, follow its focused RED/GREEN cycle in the owning earlier task; do not weaken assertions or add new scope here.

- [ ] **Step 8: Verify browser GREEN with guaranteed teardown**

Run `& $auditPython -m pytest backend\tests\foundation_browser_acceptance.py -q`. Expected: all five scenarios pass. Pytest owns every process; fixture finalizers close browser/context, run cleanup dry-run/apply as subprocesses with the exact same `postgres_env` used by port 8000 and the exact manifest, then stop both child processes even on assertion failure. Cleanup failure is collected and makes session teardown fail after evidence is saved.

- [ ] **Step 9: Run full audit**

Run `powershell -NoProfile -ExecutionPolicy Bypass -File .\RUN_AZ_AUDIT.ps1`. Expected: exit 0 and final `A-Z AUDIT PASSED`; backend/frontend have zero failures and PostgreSQL audit reports `bad_rows: 0`.

- [ ] **Step 10: Update operator guide and final checkpoint**

Document exact server/audit/health commands, runner scope, fixture cleanup and PostgreSQL/OpenCV troubleshooting in Vietnamese. Re-run full audit after docs/static checks. Record all changed files and final evidence; do not mark release complete if any required infrastructure or scenario is blocked.
