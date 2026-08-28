# Dispatch Calendar Wizard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Dispatch date-first, explain each DO clearly, require a usable Trip before choosing a vehicle, and open focused modal steps for vehicle and crew assignment.

**Architecture:** Reuse the existing Dispatch calendar, Trip modal, and dispatch API. Add small pure UI helpers for date filtering and Trip-state resolution, then drive the current full-screen step modal from those results without introducing a second dispatch workflow.

**Tech Stack:** Vanilla HTML/CSS/JavaScript, Node built-in test runner, FastAPI/SQLAlchemy existing services.

---

### Task 1: Date-first DO queue and readable DO cards

**Files:**
- Modify: `frontend/js/app.js`
- Modify: `frontend/index.html`
- Test: `frontend/tests/dispatch-workbench-ui.test.js`

- [ ] Add failing tests for pickup-date filtering and rich DO information.
- [ ] Run the focused Node test and confirm the new assertions fail.
- [ ] Filter pending DOs by the selected local pickup date and show undated DOs as warnings.
- [ ] Render customer, route, cargo, load, pickup/delivery time, and Trip status on each DO card.
- [ ] Run the focused test and confirm it passes.

### Task 2: Trip gate before vehicle selection

**Files:**
- Modify: `frontend/js/app.js`
- Modify: `frontend/index.html`
- Test: `frontend/tests/dispatch-workbench-ui.test.js`

- [ ] Add failing tests for missing, draft, planned, and non-reusable Trip states.
- [ ] Run the focused test and confirm failure.
- [ ] Reuse the existing Trip form with the selected DO/FO prefilled when Trip is missing or draft.
- [ ] Allow vehicle selection only for a single usable planned Trip; require a choice when several exist.
- [ ] Run the focused test and confirm it passes.

### Task 3: Focused vehicle and crew modals

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`
- Test: `frontend/tests/dispatch-workbench-ui.test.js`

- [ ] Add failing UI contract assertions for four steps and hidden detail before a DO is selected.
- [ ] Run the focused test and confirm failure.
- [ ] Change the workflow to Date/DO, Trip, Vehicle, and Crew/Departure.
- [ ] Remove the redundant change-vehicle, change-driver, Shipment 360, and reopen-dispatch blocks from this workflow.
- [ ] Run syntax and focused UI tests.

### Task 4: Demo guide and light verification

**Files:**
- Modify: `DEMO_TEST_A_Z.md`

- [ ] Update the dispatch test instructions to match the new date-first and Trip-gated flow.
- [ ] Run `node --check frontend/js/app.js`.
- [ ] Run the focused Dispatch test and related Trip UI test.
- [ ] Verify the health endpoint if the local server is running.
