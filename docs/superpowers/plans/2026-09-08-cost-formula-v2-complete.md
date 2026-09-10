# Cost Formula V2 Implementation Plan

**Goal:** Implement the approved cost-formula-v2 design with persisted pricing and stable dimensions across currencies.

**Architecture:** Extend existing fleet pricing services and currency infrastructure. Keep the type formula as the source and store only vehicle differences. Use additive API fields and isolated frontend modules; preserve concurrent unrelated work.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, vanilla JavaScript, CSS, pytest and Playwright.

## Approved Amendment

Changing display currency must not change zoom, font scale, panel dimensions or table column tracks. Validate the same viewport before and after each currency switch, including long formatted values.

## Tasks

- [x] Add failing service tests for dynamic components, effective expressions, and invalid replacement preserving existing overrides.
- [x] Extend `backend/app/services/vehicle_cost_service.py`; keep legacy components compatible and return effective terms/expressions for shared evaluation.
- [x] Test and implement inline vehicle selection/editing in the formula workbench, including inherited source, reset, save, cancellation and failure states.
- [ ] Audit currency APIs and implement the reference toolbar with stable layout, real rates and explicit missing-rate errors.
- [ ] Add immutable price revisions, effective-date resolution, audit and concurrency validation using migration conventions already present in the repository.
- [ ] Connect quote and settlement consumers with snapshot protection; test approved historical documents and new effective prices.
- [ ] Implement validated import preview and transactional application using existing import infrastructure where possible.
- [ ] Complete reference comparison, history and pending-change bar; no mock success handlers.
- [ ] Run frontend and focused backend suites plus browser desktop/mobile and currency layout checks; record remaining differences honestly.

## Verification

Use isolated test databases, never demo mutations against the user's data. Browser tests may evaluate and cancel drafts; persistence assertions run against isolated API test fixtures. Compare the reference and implementation at matching viewport sizes. Keep edits limited to pricing integration points.

## First Increment Evidence

- Added `cost-vehicle-inline.js` and a jsdom interaction test: source reset, cancellation, API failure retaining input.
- Browser checks on port 8005: equal panel widths, positions and fonts across VND/THB/USD/LAK at 1600px; inline vehicle editing; mobile horizontal overflow check at 390px.
- Additional regression covers legacy duplicate formulas: vehicle pricing must choose the same entry as the current catalog, not its first matching record.
- This increment does not yet implement price effective dates, immutable document snapshots, currency conversion toolbar or Excel imports. Do not describe the complete design as finished.
- Formula save now sends `expected_updated_at`, returns 409 for a stale editor, uses a conditional database UPDATE, and records the actor. This is concurrency protection, not effective-dated versioning.
