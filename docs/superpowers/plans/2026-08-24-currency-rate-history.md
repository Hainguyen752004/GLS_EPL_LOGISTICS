# Currency Rate History Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct locale-sensitive exchange-rate calculations and expose approved, proposed, and previous rates with database-backed history.

**Architecture:** A small frontend utility owns numeric parsing. FastAPI validates and atomically stores operational snapshots plus daily history, while the Master Data UI renders a comparison and history view.

**Tech Stack:** JavaScript, FastAPI, SQLAlchemy, Node contract tests, pytest.

---

### Task 1: Locale-safe numeric parsing

**Files:** `frontend/js/currency-rate-utils.js`, `frontend/tests/currency-rate-utils.test.js`, `frontend/index.html`, `frontend/js/app.js`

- [ ] Write failing tests for `26.173,50`, `26,173.50`, `1.18`, and `1.000`.
- [ ] Implement one parser and use it in preview, workflow conversion, and save.
- [ ] Verify the Baht symbol and conversion result.

### Task 2: Approved rate history API

**Files:** `backend/app/main.py`, `backend/tests/test_currency_history_api.py`

- [ ] Write failing API tests for current/previous values and invalid atomic saves.
- [ ] Persist `APPROVED_UI` and `PREVIOUS_UI` snapshots in `currency_rate_history`.
- [ ] Add a read endpoint returning comparison summaries and history.

### Task 3: Comparison UI and regression verification

**Files:** `frontend/index.html`, `frontend/js/app.js`, `frontend/tests/currency-reference-ui.test.js`, `DEMO_TEST_A_Z.md`

- [ ] Add current, previous, reference, delta, timestamp, and history hooks.
- [ ] Load approved history independently from provider reference state.
- [ ] Run all frontend tests and relevant backend suites.
