# Responsive Driver Scheduling Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sua workbench sap ca bi trang va lam giao dien tu thich nghi tren desktop, tablet va dien thoai.

**Architecture:** Giu nguyen backend va API scheduling hien tai. Sua frontend loader de co kha nang chiu loi tung API, dung dung utility UMD global, va bo sung responsive CSS theo breakpoint voi overflow cuc bo cho lich.

**Tech Stack:** HTML, CSS Grid/Flexbox, JavaScript, Node static tests.

---

### Task 1: Khoa hanh vi bang test

**Files:**
- Modify: `frontend/tests/driver-shift-planner-ui.test.js`

- [x] Them assertion cho viewport, UMD global, loader chiu loi va breakpoint responsive.
- [x] Chay test va xac nhan test moi dang fail.

### Task 2: Sua loader va render lich

**Files:**
- Modify: `frontend/js/app.js`
- Modify: `frontend/index.html`

- [x] Doi utility reference sang `window.TmsCockpit`.
- [x] Tai cac API bang `Promise.allSettled`, giu du lieu cua API thanh cong va hien loi neu du lieu cot loi.
- [x] Tang static asset version.
- [x] Chay test muc tieu va xac nhan pass.

### Task 3: Responsive desktop, tablet va mobile

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/css/styles.css`

- [x] Bo sung responsive foundation cho shell va container.
- [x] Sua workbench ba cot desktop, hai hang tablet va mot cot mobile.
- [x] Gioi han overflow trong lich/bang thay vi tran viewport.
- [x] Chay toan bo frontend tests.

### Task 4: Xac minh

**Files:**
- Test: `frontend/tests/*.test.js`

- [x] Chay tat ca frontend tests.
- [x] Kiem tra server health va static asset version dang phuc vu.
