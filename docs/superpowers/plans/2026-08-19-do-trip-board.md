# DO Trip Board Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the DO planning screen with three operational tabs and a cleaner view-only table action.

**Architecture:** Keep the existing single-file frontend structure. Update `frontend/index.html` for layout and add small helper functions in `frontend/js/app.js` for DO stage classification, sorting, tab switching, count refresh, and row rendering.

**Tech Stack:** Static HTML/CSS, vanilla JavaScript, existing Fiori-style classes and API state.

---

## Chunk 1: DO Board Layout

**Files:**
- Modify: `frontend/index.html`

- [ ] Replace the old DO list card area with a polished board header, three DO stage tabs, search, table, and route context panel.
- [ ] Keep existing element IDs used by JavaScript: `do-search-input`, `fiori-do-tbody`, `fiori-route-tbody`.
- [ ] Add new IDs for counters: `do-count-pending`, `do-count-active`, `do-count-completed`.

## Chunk 2: DO Stage Logic

**Files:**
- Modify: `frontend/js/app.js`

- [ ] Add `activeDOStage` state.
- [ ] Add helpers to classify DO statuses into pending, active, completed.
- [ ] Add date sort helpers using pickup/delivery windows.
- [ ] Update `renderDeliveryOrders` to filter by active stage, update counters, and render only the `Xem` action.
- [ ] Update `filterDeliveryOrders` to preserve current stage.
- [ ] Expose `switchDeliveryOrderStage`.

## Chunk 3: Verification

**Files:**
- Check: `frontend/js/app.js`

- [ ] Run `node --check frontend\js\app.js`.
- [ ] Search visible DO/Trip labels for obvious mojibake in the edited area.
