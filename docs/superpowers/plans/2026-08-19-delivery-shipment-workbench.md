# Delivery Shipment Workbench Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Giao hàng & vận chuyển screen so it reads as one clear workbench instead of several unrelated forms in one tab.

**Architecture:** Keep existing backend/API calls and existing renderers, but reorganize the frontend shell. The default view shows DO queue and Trip overview; longer Dispatch Calendar and Kho/POD views are behind a single segmented control.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, existing Fiori-style components.

---

### Task 1: Add Guard Tests

**Files:**
- Create: `scripts/check_delivery_workbench_ui.js`

- [ ] Verify the new delivery screen has one workbench shell and three panels.
- [ ] Verify old four-panel flow ids are removed.
- [ ] Verify only one visible create Trip action exists in the delivery section.

### Task 2: Rebuild Delivery Shipment HTML

**Files:**
- Modify: `frontend/index.html`

- [ ] Replace the current four-card/tab delivery layout with a compact header.
- [ ] Add `delivery-workbench-tabs` with `board`, `schedule`, and `warehouse`.
- [ ] Move DO queue and Trip cockpit into the default `board` panel.
- [ ] Keep Dispatch Calendar in `schedule`.
- [ ] Keep Shipment/Kho/POD content in `warehouse`.

### Task 3: Update JS Switching

**Files:**
- Modify: `frontend/js/app.js`

- [ ] Add `switchDeliveryWorkbenchView`.
- [ ] Keep a compatibility alias for old calls.
- [ ] Load relevant data when each panel is shown.
- [ ] Disable old enterprise tab config for `view-delivery-shipment`.

### Task 4: Verify

**Commands:**
- `node scripts/check_delivery_workbench_ui.js`
- `node --check frontend/js/app.js`

Expected: both pass.
