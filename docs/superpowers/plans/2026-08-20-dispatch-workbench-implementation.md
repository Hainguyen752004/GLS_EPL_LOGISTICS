# Dispatch Workbench Implementation Plan

> **For agentic workers:** Execute this plan with `superpowers:subagent-driven-development`. Keep production data paths intact; fixtures belong only in tests. Do not reset PostgreSQL or run unrelated backend suites.

**Goal:** Replace the crowded Dispatch tabs with the approved three-region workbench: DO queue, vehicle timeline, and contextual Trip/DO detail.

**Architecture:** Reuse `buildDispatchCalendar` and the existing dispatch state/API loading. Consolidate selection into `selectedDispatchCalendarOrderId`, render all primary actions as semantic buttons, and move capacity/alerts/7-day views into one secondary tools panel. Desktop shows all three regions; medium and mobile use an accessible detail drawer.

**Tech Stack:** Static HTML/CSS, vanilla JavaScript, Node-based source/unit tests.

---

### Task 1: Lock the new UI contract with failing tests

**Files:**
- Modify: `frontend/tests/dispatch-workbench-ui.test.js`
- Test: `frontend/tests/dispatch-workbench-ui.test.js`

1. Replace assertions for the old state/analysis tabs with unique-ID assertions for `dispatch-workbench`, `dispatch-queue`, `dispatch-timeline`, `dispatch-detail`, `dispatch-tools-button`, and `dispatch-tools-panel`.
2. Add source assertions that queue rows and timeline bars render as `<button type="button">`.
3. Assert both DO and calendar selectors update `selectedDispatchCalendarOrderId` and that no first-item fallback remains.
4. Add test-only fixtures covering a DO missing a vehicle in the queue, a valid Trip in a lane, a multi-DO Trip with linked DOs and total payload, and an empty detail when nothing is selected.
5. Add a minimal test-local DOM harness for tools keyboard/focus behavior and drawer semantics; do not add a production dependency.
6. Assert timeline buttons have an `aria-label` containing Trip code, vehicle/driver, start/end time, and status, and assert no timeline `div onclick` remains.
7. Run `node frontend/tests/dispatch-workbench-ui.test.js` and confirm it fails for the missing workbench contract.

### Task 2: Build the workbench shell and responsive layout

**Files:**
- Modify: `frontend/index.html`
- Test: `frontend/tests/dispatch-workbench-ui.test.js`

1. Replace the two old tab rows and fragmented dispatch panels with one `#dispatch-workbench` shell.
2. Add the left `#dispatch-queue`, center `#dispatch-timeline`, and right `#dispatch-detail` regions while preserving existing renderer IDs inside their new owners.
3. Add three operational KPI controls above the workbench and a compact secondary-tools command.
4. Implement desktop tracks `260px minmax(520px, 1fr) 300px`, tablet detail drawer behavior, and a stacked mobile layout without horizontal overflow.
5. Add immediate loading and local empty/error placeholders to each region.
6. Run the dispatch UI test, make the smallest shell/layout change that turns the relevant assertions green, and rerun it.

### Task 3: Unify queue, timeline, and detail selection

**Files:**
- Modify: `frontend/js/app.js`
- Modify: `frontend/js/tms-cockpit-utils.js`
- Test: `frontend/tests/dispatch-workbench-ui.test.js`

1. Make `selectDispatchDO()` and `selectDispatchCalendarItem()` assign the same selected ID before rerendering.
2. Remove implicit selection of the first Trip/DO.
3. Render queue rows and Gantt bars as keyboard-accessible buttons with selected state.
4. Implement queue reason precedence: conflict, missing vehicle, missing driver, missing time, waiting; sort by earliest pickup with missing times last.
5. Extend dispatch detail output to distinguish Trip from DO, list linked DOs, total payload, route, and time windows using current `appState` data.
6. Keep the detail empty until the user chooses a queue row or timeline item.
7. Give each timeline button an accessible label with Trip code, vehicle/driver, start/end time, and status.
8. Run the fixture tests, implement only the missing builder/selection behavior, then rerun until green.

### Task 4: Move secondary analysis into one tools panel

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/app.js`
- Test: `frontend/tests/dispatch-workbench-ui.test.js`

1. Add `#dispatch-tools-button` and `#dispatch-tools-panel` and move Capacity, Alerts, and 7-day content into this panel.
2. Allow only one secondary tool view at a time.
3. Support click toggling, Escape close, arrow-key menu navigation, focus transfer, and focus return.
4. Add drawer semantics, focus trapping, and close behavior for contextual detail on medium/mobile screens.
5. Maintain `aria-expanded`/`aria-controls`; use `role="dialog"`, `aria-modal`, and a labelled drawer at drawer breakpoints.
6. Add harness assertions first, run them red, implement the keyboard/focus behavior, and rerun green.

### Task 5: Reuse existing live Trip data loading

**Files:**
- Modify: `frontend/js/app.js`
- Test: `frontend/tests/dispatch-workbench-ui.test.js`

1. Locate and reuse the existing Trip GET request already used elsewhere in the frontend.
2. Include Trip loading in `loadDispatchBoard()` without adding endpoints or database writes.
3. Preserve prior data if one source fails, end each source's skeleton independently, and show a local “Dữ liệu có thể chưa mới” state with retry through `loadDispatchBoard()`.
4. Ensure `Làm mới` calls `loadDispatchBoard()`; ensure `Tạo lịch/Điều phối` opens the existing resource-assignment form and is disabled until a suitable DO is selected.
5. Add source/harness assertions first, run red, implement the reuse and command behavior, and rerun green.

### Task 6: Focused verification and visual review

**Files:**
- Verify: `frontend/index.html`
- Verify: `frontend/js/app.js`
- Verify: `frontend/js/tms-cockpit-utils.js`

1. Run `node frontend/tests/dispatch-workbench-ui.test.js`.
2. Run `node frontend/tests/workflow-status-ui.test.js`.
3. Run `node frontend/tests/vietnamese-source-clean.test.js`.
4. Run `node --check frontend/js/app.js`.
5. Open the local page at `1440x900`, `1024x768`, and `390x844`; verify the three desktop regions, drawer behavior, no horizontal overflow, readable contrast, selection behavior, tools panel, and visible loading/empty states.
6. Report any browser-tool limitation explicitly; do not substitute unrelated backend or PostgreSQL testing.
