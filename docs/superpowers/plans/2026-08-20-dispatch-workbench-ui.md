# Dispatch Workbench UI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the Dispatch & Execution screen into a compact workbench that makes pending work, selected-trip actions, schedules, capacity, alerts, and the seven-day plan easy to scan.

**Architecture:** Preserve the existing DOM data targets and `TmsCockpit` data builders, while moving them into a progressive-disclosure layout. Add a small UI state for the active work queue and analysis tab; all backend and PostgreSQL behavior remains unchanged.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, Node.js source-structure tests.

---

## Chunk 1: Workbench Structure

### Task 1: Add a failing dispatch layout test

**Files:**
- Create: `frontend/tests/dispatch-workbench-ui.test.js`

- [x] Assert that the three work-state buttons and four analysis-tab buttons exist.
- [x] Assert that the legacy all-panels-visible layout is replaced by workbench regions.
- [x] Run `node frontend/tests/dispatch-workbench-ui.test.js` and confirm failure.

### Task 2: Build the workbench markup and styling

**Files:**
- Modify: `frontend/index.html`

- [x] Add a compact page header and three work-state buttons.
- [x] Place the pending DO list and resource assignment form in a two-column workbench.
- [x] Add analysis tabs for vehicle schedule, capacity, alerts, and seven-day planning.
- [x] Preserve IDs used by existing rendering functions.
- [x] Add responsive rules that stack the workbench below desktop widths.

## Chunk 2: Interaction and Verification

### Task 3: Add progressive-disclosure behavior

**Files:**
- Modify: `frontend/js/app.js`

- [x] Add active work-state and active analysis-tab state.
- [x] Add functions that switch visible panels and update accessible button state.
- [x] Refresh the active analysis panel without rendering unrelated panels visibly.

### Task 4: Verify frontend behavior

**Files:**
- Test: `frontend/tests/dispatch-workbench-ui.test.js`
- Test: `frontend/tests/vietnamese-source-clean.test.js`

- [x] Run the dispatch layout test.
- [x] Run the Vietnamese source test.
- [x] Run `node --check frontend/js/app.js`.
- [ ] Inspect the page at desktop and narrow viewport if the local frontend is available.
