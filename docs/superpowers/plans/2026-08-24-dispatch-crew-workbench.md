# Dispatch Crew Workbench Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist vehicle, main-driver and co-driver dispatch assignments and expose an idle-vehicle timeline that accepts pending DOs.

**Architecture:** Extend existing DO/Trip assignment records with an optional co-driver ID, centralize crew availability validation in the dispatch services, then render every vehicle as a Dispatch lane. Drag/drop only prepares the assignment; the right-side confirmation sends the real API command.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, SQLite/PostgreSQL migrations, vanilla JavaScript/CSS, pytest, Node contract tests.

---

### Task 1: Backend crew contract

- [ ] Write failing API tests for co-driver persistence, role validation, overlap and release.
- [ ] Run focused pytest tests and verify the expected failures.
- [ ] Add migration 018 and model/schema fields.
- [ ] Implement shared ready-status and crew validation helpers.
- [ ] Update direct DO and Trip dispatch plus completion release.
- [ ] Run focused tests until green.

### Task 2: Vehicle-lane calendar

- [ ] Write failing Node tests for idle vehicle lanes and DO drop contracts.
- [ ] Run the focused Node test and verify failure.
- [ ] Extend `buildDispatchCalendar` to include all vehicle lanes and shift-derived crew hints.
- [ ] Make pending DO cards draggable and lanes droppable, with tap-to-assign fallback.
- [ ] Populate the detail form from the selected lane and filter crew by role/availability.
- [ ] Send only fields accepted by the dispatch API.
- [ ] Run frontend tests until green.

### Task 3: Responsive verification and demo guide

- [ ] Add responsive CSS for three-column desktop and stacked mobile workflow.
- [ ] Run all backend and frontend tests.
- [ ] Start the app and inspect desktop/mobile screenshots.
- [ ] Update `DEMO_TEST_A_Z.md` with drag/drop, crew lock and release checks.
