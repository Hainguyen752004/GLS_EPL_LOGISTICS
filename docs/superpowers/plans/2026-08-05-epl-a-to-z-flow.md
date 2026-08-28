# EPL A-to-Z Flow Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dọn dữ liệu test có thể phục hồi và chuẩn hóa chuỗi EPL từ báo giá đến GL, không tạo dữ liệu giả và không lỗi tiếng Việt.

**Architecture:** Giữ FastAPI/SQLAlchemy/JavaScript, thêm service state-machine, versioned migration, error contract và idempotency. Mọi test dùng SQLite tạm; database thật chỉ được dọn sau backup đã restore thử và manifest có hash không đổi.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, SQLite/PostgreSQL, pytest, Node built-in test runner.

---

## Chunk 1: Test isolation and storage safety

### Task 1: Deterministic test environment and explicit database mode

**Files:** Create `backend/requirements-dev.txt`, `backend/tests/conftest.py`, `backend/tests/test_database_config.py`; modify `backend/app/config.py`, `backend/app/database.py`, `backend/app/main.py`.

- [ ] Add `pytest`, `httpx` to `backend/requirements-dev.txt`; install with `python -m pip install -r backend/requirements-dev.txt` (expected exit 0).
- [ ] In `conftest.py`, set `DATABASE_MODE=sqlite`, `DATABASE_URL=sqlite:///<pytest tmp_path>`, `DISABLE_STARTUP_SEED=1` before importing app; override DB dependency. Tests must assert the real DB mtime/counts never change.
- [ ] Write `test_postgres_failure_does_not_fallback`, `test_sqlite_requires_explicit_mode`, `test_sqlite_enables_foreign_keys`, `test_unicode_log_is_safe`, `test_import_does_not_seed_or_reset`.
- [ ] Run `$env:PYTHONPATH='backend/app'; pytest backend/tests/test_database_config.py -v`; expected RED because fallback and startup seed exist.
- [ ] Implement explicit `DATABASE_MODE=postgres|sqlite`; PostgreSQL errors raise `DATABASE_UNAVAILABLE`; SQLite connect event executes `PRAGMA foreign_keys=ON`; replace unsafe emoji prints; remove startup seed and protect reset as explicit admin operation.
- [ ] Re-run the same command; expected 5 passed. Run `pytest backend/tests -q`; expected exit 0.
- [ ] If Git exists commit `fix: make database selection explicit`; otherwise record `NO_GIT_REPOSITORY` in handoff.

### Task 2: Versioned migration foundation

**Files:** Create `backend/app/migrations/__init__.py`, `backend/app/migrations/runner.py`, `backend/app/migrations/v001_workflow.py`, `backend/tests/test_migration_v001.py`; modify `backend/app/models.py`.

- [ ] Write tests `test_upgrade_and_rollback_sqlite`, `test_upgrade_postgres_ddl_snapshot`, `test_backfill_valid_chain`, `test_quarantine_ambiguous_chain`, `test_schema_constraints`.
- [ ] Run `pytest backend/tests/test_migration_v001.py -v`; expected RED: migration package missing.
- [ ] Implement a `schema_migrations` runner. SQLite upgrade rebuilds affected tables inside a transaction; PostgreSQL path emits/executes dialect DDL. Add source quotation/SO links, canonical statuses, timestamps/actor/version, idempotency records, currency/tax snapshots, accounting periods, account mappings, invoice reversal link, journal batch/line and unique chain constraints. Ambiguous backfill goes to `migration_quarantine` JSON, never guessed.
- [ ] Add CLI `python -m migrations.runner upgrade|rollback --database-url <url> --dry-run`; rollback refuses if destructive data would be lost unless `--restore-from` is supplied.
- [ ] Re-run focused tests; expected all pass. Run `pytest backend/tests -q`; expected exit 0.
- [ ] If Git exists commit `feat: add versioned workflow schema migration`.

### Task 3: Dialect-safe cleanup tool (tests only; no real apply)

**Files:** Create `backend/app/data_cleanup.py`, `backend/tests/test_data_cleanup.py`; modify `backend/app/clear_sample_data.py`.

- [ ] Write named tests for numeric/malformed quotation roots, all FK metadata descendants, orphan roots, quarantine export, audit retention, shared vehicle/driver release, per-table reconciliation, injected rollback, backup verification, manifest SHA-256 drift refusal, PostgreSQL missing `pg_dump` hard stop, and pg_dump/pg_restore command construction.
- [ ] Run `pytest backend/tests/test_data_cleanup.py -v`; expected RED: cleanup API missing.
- [ ] Implement CLI `python -m data_cleanup dry-run|apply|restore --database-url ... --keep-root-max 20 --manifest ... --backup-dir ...`. Dry-run lists every kept/repaired/quarantined/deleted ID and table counts. Apply requires `--approved-sha256` matching a newly regenerated manifest.
- [ ] SQLite backup uses `Connection.backup()` with writes stopped by `BEGIN IMMEDIATE`, saves under `backend/backups/epl_logistics-YYYYMMDD-HHMMSS.db`, runs `integrity_check`, restores to a temp file and validates before apply. PostgreSQL requires configured `PG_DUMP_PATH`/`PG_RESTORE_PATH`, successful custom-format dump and restore to configured disposable verification DB; otherwise aborts without writes.
- [ ] Re-run focused tests; expected all pass. Run `pytest backend/tests -q`; expected exit 0.
- [ ] If Git exists commit `feat: add reversible data cleanup`.

## Chunk 2: Canonical backend workflow

### Task 4: State machine, IDs, errors, and Master Data prerequisites

**Files:** Create `backend/app/services/errors.py`, `backend/app/services/workflow_service.py`, `backend/tests/test_workflow_transitions.py`.

- [ ] Write tests for exact status vocabularies and every legal/illegal transition; quotation customer/route/vehicle-type prerequisites; explicit SO confirmation; inherited immutable DO fields; mandatory dates/origin/destination/weight/volume/packaging; all stable error codes/status codes; multiple `navigation_targets`, including `master-data/chart-of-accounts`; Unicode Vietnamese responses; concurrent ID allocation and optimistic-version conflict.
- [ ] Run `pytest backend/tests/test_workflow_transitions.py -v`; expected RED: services missing.
- [ ] Implement `DomainError`, target constants, transition maps, validators, locked `IdSequence`, and optimistic version update.
- [ ] Re-run focused/full tests; expected exit 0. Commit if Git exists: `feat: enforce canonical workflow transitions`.

### Task 5: Consolidated workflow API and dispatch/POD

**Files:** Create `backend/app/routes/__init__.py`, `backend/app/routes/workflow_routes.py`, `backend/tests/test_workflow_api.py`; modify `backend/app/main.py`.

- [ ] Write tests `test_no_duplicate_method_path`, `test_quote_to_so_to_do`, `test_do_source_fields_cannot_be_overridden`, `test_dispatch_requires_approved`, `test_busy_or_overcapacity_rejected`, `test_concurrent_dispatch_reserves_once`, `test_pod_updates_requested_do_only`, `test_delivered_requires_arrived_and_pod`, `test_release_checks_other_active_assignments`, `test_failure_rolls_back_all_rows`, `test_delete_chain_has_no_orphans`, `test_idempotency_replay_returns_original_result`.
- [ ] Run `pytest backend/tests/test_workflow_api.py -v`; expected RED from duplicate routes/current permissive transitions.
- [ ] Register one router per method/path, remove duplicate handlers and hard-coded defaults, add `Idempotency-Key`, transactional dispatch/POD/deletion and audit entries.
- [ ] Re-run focused/full tests; expected exit 0. Commit if Git exists: `refactor: consolidate workflow API`.

### Task 6: Invoice, GL, periods, mappings, and reversal

**Files:** Create `backend/app/services/accounting_service.py`, `backend/tests/test_accounting_flow.py`; modify `backend/app/routes/workflow_routes.py`.

- [ ] Write tests for Delivered-only invoice; amount/customer/currency/exchange-rate/tax snapshot from SO; smallest-currency-unit rounding; closed period rejection; missing mapping target; unique active invoice per DO; separate GL post; balanced journal; GL retry/idempotency; rollback after injected line failure; invoice and journal reversal links.
- [ ] Run `pytest backend/tests/test_accounting_flow.py -v`; expected RED because current endpoint hard-codes values and combines behavior.
- [ ] Implement separate `/invoices/post` and `/invoices/{id}/post-gl` transactions plus reversal endpoints and unique constraints from migration.
- [ ] Re-run focused/full tests; expected exit 0. Commit if Git exists: `feat: add traceable accounting posting`.

### Task 7: UTF-8 source cleanup

**Files:** Create `backend/tests/test_utf8_content.py`; modify `backend/app/main.py`, `backend/app/models.py`, `backend/app/database.py`, `frontend/js/app.js`, `frontend/index.html`, `frontend/js/lang.json`.

- [ ] Write scanner that strict-decodes user-visible UTF-8 and rejects mojibake tokens `Ã`, `Ä`, `á»`, `âœ`, `ðŸ`; include API Vietnamese assertions.
- [ ] Run `pytest backend/tests/test_utf8_content.py -v`; expected RED with current files listed.
- [ ] Correct user-visible strings, preserve identifiers, and use DOM/text escaping for API/user values.
- [ ] Re-run focused/full tests, `python -m compileall -q backend`, `node --check frontend/js/app.js`, and `python -m json.tool frontend/js/lang.json > $null`; expected exit 0. Commit if Git exists: `fix: normalize Vietnamese UTF-8`.

## Chunk 3: Frontend and full verification

### Task 8: Frontend API contract and screen navigation

**Files:** Create `frontend/package.json`, `frontend/js/api.js`, `frontend/js/workflow.js`, `frontend/tests/workflow.test.js`, `frontend/tests/page-integration.test.js`; modify `frontend/js/app.js`, `frontend/index.html`.

- [ ] Declare `jsdom` as a dev dependency and `test` script `node --test tests/*.test.js`; run `npm --prefix frontend install` (expected exit 0). Use Node `node:test`/`assert` for pure helpers. Test error rendering with multiple targets, all eight canonical navigation routes, XSS escaping, empty dropdown blocking, removal of fallback `DO-2026-004`/customer/amount, and endpoint order.
- [ ] Run `node --test frontend/tests/workflow.test.js`; expected RED: modules missing.
- [ ] Implement CommonJS-compatible pure helpers plus browser exports. Replace concrete call sites: quotation save/approve (around current lines 5107/5131), SO save/confirm (5153/5176), DO create/status/dispatch (2286/2955/5245), POD (5261), invoice (5314), dropdown sync (4762–4900), reset action (4567).
- [ ] Render user/API values with `textContent` or escaping. Map targets including `master-data/chart-of-accounts`.
- [ ] In jsdom load the actual `index.html` and scripts with mocked fetch; test real button/form wiring executes the canonical endpoint sequence, empty dropdown prevents fetch, multiple target buttons navigate correctly, and malicious API text is visible as text without creating DOM nodes.
- [ ] Run `npm --prefix frontend test`; expected helper and page integration tests pass. Run `node --check` on all JS files; expected exit 0. Commit if Git exists: `feat: connect frontend to canonical workflow`.

### Task 9: Isolated A-to-Z HTTP test

**Files:** Create `backend/tests/test_e2e_a_to_z.py`; modify `backend/app/seed_full_demo.py`.

- [ ] Test creates its own temporary SQLite DB and Master Data, never calls seed and asserts real DB hash/mtime unchanged. It performs Quotation Draft→Approved→SO Draft→Confirmed→DO Planned→Approved→dispatch→Arrived→POD→Delivered→Invoice Posted→GL Posted, checking audit timestamps/actors, resource states, one invoice, balanced GL and Vietnamese errors for an intentional invalid step.
- [ ] Run `$env:PYTHONPATH='backend/app'; pytest backend/tests/test_e2e_a_to_z.py -v`; expected RED at first missing integration.
- [ ] Make seed callable only via explicit admin CLI and add remaining integration glue.
- [ ] Re-run focused/full tests; expected exit 0. Commit if Git exists: `test: cover complete EPL workflow`.

### Task 10: Real SQLite cleanup gates and final evidence

**Files:** Create `docs/epl-data-cleanup-report-2026-08-05.md`; modify `KICH_BAN_THAO_TAC_A_Z.md`.

- [ ] Resolve the active DB using explicit `DATABASE_MODE=sqlite` and absolute URL; stop the running app/process holding the DB or abort. Do not clean PostgreSQL unless verified disposable restore DB and PG tools are configured.
- [ ] Create and integrity-check a pre-migration backup, restore it to a temporary DB and verify the restored copy before changing the active DB.
- [ ] Run `$env:PYTHONPATH='backend/app'; python -m migrations.runner upgrade --database-url 'sqlite:///D:/Demo_Lao/EPL_System/backend/app/epl_logistics.db'`; verify `schema_migrations`, all expected columns/constraints, backfill and quarantine counts. On failure, rollback the transaction and restore the verified pre-migration backup.
- [ ] Run dry-run: `$env:PYTHONPATH='backend/app'; python -m data_cleanup dry-run --database-url 'sqlite:///D:/Demo_Lao/EPL_System/backend/app/epl_logistics.db' --keep-root-max 20 --manifest 'docs/cleanup-manifest-2026-08-05.json' --backup-dir 'backend/backups'`; expected exit 0 and no DB hash change.
- [ ] Record manifest SHA-256 and verify it contains only business chains, never Master Data. Present the exact manifest path/hash plus per-table kept/repaired/quarantined/deleted counts and IDs to the user/operator. HARD STOP: require explicit approval of that exact hash; plan approval, silence, or approval of a different hash does not authorize apply.
- [ ] Run backup/restore verification through the apply preflight; expected `integrity_check=ok` and temp restore FK check result recorded before writes.
- [ ] Run apply with the exact SHA-256. Expected transaction commit, per-table reconciliation, quarantine export, and no unexpected IDs. If any assertion fails, automatic rollback and restore backup.
- [ ] Run `PRAGMA integrity_check` (expected `ok`) and `PRAGMA foreign_key_check` (expected zero rows); verify active `schema_migrations` and constraints; compare before/kept/repaired/quarantined/deleted totals against manifest.
- [ ] Run fresh verification from repository root: `python -m compileall -q backend`; `$env:PYTHONPATH='backend/app'; pytest backend/tests -v`; `npm --prefix frontend test`; `Get-ChildItem frontend -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName; if ($LASTEXITCODE -ne 0) { throw "JS syntax failed: $($_.FullName)" } }`; `Get-ChildItem frontend -Recurse -Filter *.json | ForEach-Object { python -m json.tool $_.FullName *> $null; if ($LASTEXITCODE -ne 0) { throw "JSON parse failed: $($_.FullName)" } }`; `pytest backend/tests/test_workflow_api.py::test_no_duplicate_method_path -v`; `pytest backend/tests/test_utf8_content.py -v`. All expected exit 0; npm output must include both `workflow.test.js` and `page-integration.test.js` with zero failures.
- [ ] Copy the resulting migrated/cleaned active DB to a temporary path. Start only against that copy with `$env:DATABASE_MODE='sqlite'`, `$env:DATABASE_URL='sqlite:///...temp...'`, `$env:DISABLE_STARTUP_SEED='1'`; run `pytest backend/tests/test_e2e_a_to_z.py -v`; stop process and delete only the validated temp copy.
- [ ] Write cleanup/restore paths, manifest hash, counts, verification output, canonical user steps and limitations into the report and A–Z guide. Commit if Git exists: `docs: document EPL cleanup and workflow`.

## Verification matrix

- SQLite: config, migration upgrade/rollback, backup/restore, cleanup dry-run/apply/drift/rollback, FK/integrity, complete HTTP flow.
- PostgreSQL: config fail-fast, DDL snapshot, pg_dump/pg_restore path/abort behavior; real apply is forbidden without a configured disposable restore database.
- Frontend: Node helper tests plus jsdom integration over the real page/scripts, syntax checks, actual event wiring, target mapping and XSS-safe rendering.
- Encoding: strict UTF-8 plus mojibake scanner across user-visible Python/HTML/JS/JSON.
