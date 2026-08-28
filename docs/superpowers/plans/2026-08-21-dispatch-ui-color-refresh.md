# Dispatch UI Color Refresh Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the dispatch queue, alert drawer, and 7-day vehicle planner so action colors and status surfaces are visually distinct.

**Architecture:** Keep the existing single-page dispatch implementation. Add scoped CSS classes in `frontend/index.html`, replace brittle inline styles in `frontend/js/app.js`, and protect the visual contract with the existing static frontend test.

**Tech Stack:** Plain HTML, CSS, JavaScript, Node assert-based frontend tests.

---

## Chunk 1: Dispatch Visual Polish

### Task 1: Add UI Contract Test

**Files:**
- Modify: `frontend/tests/dispatch-workbench-ui.test.js`

- [ ] Add assertions for new dispatch queue/action/planner/alert CSS classes.
- [ ] Run `node frontend/tests/dispatch-workbench-ui.test.js` and confirm it fails before implementation.

### Task 2: Add Scoped Styles

**Files:**
- Modify: `frontend/index.html`

- [ ] Add dispatch-only classes for DO cards, eye action buttons, alert rows, week KPIs, planner grid, planner cells, and guidance rows.
- [ ] Keep styles scoped to `.dispatch-*` so other modules are not affected.

### Task 3: Update Render Markup

**Files:**
- Modify: `frontend/js/app.js`

- [ ] Replace the DO queue card inline style with the new class structure.
- [ ] Replace dispatch alert rows with semantic warning rows and severity modifiers.
- [ ] Replace week planner inline card/cell styles with the new class structure.

### Task 4: Verify

**Files:**
- Test: `frontend/tests/dispatch-workbench-ui.test.js`

- [ ] Run `node frontend/tests/dispatch-workbench-ui.test.js`.
- [ ] Run a JavaScript syntax check for `frontend/js/app.js`.
