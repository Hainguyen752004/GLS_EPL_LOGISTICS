# Analysis Workspace Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tách P&L/Trung tâm Doanh thu và Chi phí khỏi Báo cáo & Phân tích, đặt trong không gian Tóm tắt & Phân tích có sidebar responsive.

**Architecture:** Giữ nguyên API và `TransportReporting`; chỉ đổi ownership của DOM từ `view-reporting` sang `view-lab-summary`. Một hàm điều hướng workspace mới quản lý bốn pane, trong khi enterprise tabs hiện tại tiếp tục quản lý riêng SLA/KPI và Tender/Carrier.

**Tech Stack:** HTML/CSS thuần, JavaScript thuần, Chart.js, Node assertion tests, FastAPI/pytest regression suite.

---

## Chunk 1: Hợp đồng giao diện và cấu trúc trang

### Task 1: Viết test cấu trúc workspace mới

**Files:**
- Create: `frontend/tests/analysis-workspace-ui.test.js`
- Modify: `frontend/tests/transport-reporting-ui.test.js`

- [ ] Viết assertion yêu cầu `view-lab-summary` chứa `analysis-workspace` và `transport-reporting-center`.
- [ ] Viết assertion yêu cầu sidebar có bốn mục `overview`, `panorama`, `revenue`, `expenses`.
- [ ] Viết assertion yêu cầu `view-reporting` không còn chứa `transport-reporting-center` và vẫn có SLA/Tender.
- [ ] Viết assertion responsive yêu cầu sidebar đổi thành selector dưới 760px.
- [ ] Chạy `node frontend/tests/analysis-workspace-ui.test.js` và xác nhận FAIL do workspace chưa tồn tại.

### Task 2: Di chuyển markup và tạo sidebar

**Files:**
- Modify: `frontend/index.html`

- [ ] Đổi nhãn menu `Tóm tắt phân tích` thành `Tóm tắt & Phân tích`.
- [ ] Bọc `view-lab-summary` bằng header, bộ lọc dùng chung, sidebar và vùng pane.
- [ ] Đặt nội dung toàn cảnh hiện có vào pane `panorama`.
- [ ] Di chuyển `transport-reporting-center` vào workspace, chia nội dung thành pane `overview`, `revenue`, `expenses`.
- [ ] Loại bỏ header KPI/P&L và report center khỏi `view-reporting`; giữ nguyên SLA/KPI và Tender/Carrier.
- [ ] Chạy test cấu trúc và sửa tối thiểu đến khi PASS.

## Chunk 2: Điều hướng và responsive

### Task 3: Nối điều hướng sidebar

**Files:**
- Modify: `frontend/js/transport-reporting.js`
- Modify: `frontend/js/app.js`

- [ ] Thay `selectTab` bằng hoặc ủy quyền sang `selectWorkspacePane(name)` nhưng giữ alias `selectTab` để không phá caller cũ.
- [ ] Đồng bộ trạng thái active giữa nút sidebar, selector mobile và pane nội dung.
- [ ] Khi mở `lab-summary`, gọi `TransportReporting.load()` và render dữ liệu toàn cảnh hiện có.
- [ ] Khi chọn `overview`, resize Chart.js sau khi pane hiện ra.
- [ ] Bảo toàn giá trị bộ lọc khi chuyển pane.
- [ ] Chạy test frontend mục tiêu và xác nhận PASS.

### Task 4: Hoàn thiện CSS responsive

**Files:**
- Modify: `frontend/css/styles.css`

- [ ] Tạo grid sidebar 180px + nội dung `minmax(0,1fr)`.
- [ ] Giới hạn overflow ở bảng 23 cột, không để toàn trang cuộn ngang.
- [ ] Dưới 760px, ẩn sidebar desktop, hiện selector mobile và xếp KPI/bộ lọc phù hợp.
- [ ] Dùng kích thước ổn định cho chart và button để không nhảy layout.
- [ ] Chạy toàn bộ `frontend/tests/*.test.js`.

## Chunk 3: Tài liệu và xác minh

### Task 5: Cập nhật kịch bản A-Z

**Files:**
- Modify: `DEMO_TEST_A_Z.md`

- [ ] Đổi đường dẫn thao tác sang `Tổng quan → Tóm tắt & Phân tích`.
- [ ] Mô tả bốn mục sidebar và kiểm tra responsive desktop/mobile.
- [ ] Ghi rõ Báo cáo & Phân tích chỉ còn SLA/KPI và Tender/Carrier.

### Task 6: Chạy regression

**Files:**
- Test: `frontend/tests/*.test.js`
- Test: `backend/tests/test_tms_transport_reporting.py`

- [ ] Chạy toàn bộ frontend test và xác nhận không có failure.
- [ ] Chạy `node --check frontend/js/app.js` và `node --check frontend/js/transport-reporting.js`.
- [ ] Chạy reporting backend tests và xác nhận PASS.
- [ ] Khởi động server ở cổng trống, kiểm tra `/api/health` và cung cấp URL bản mới.

> Repository hiện không có Git metadata tại workspace nên kế hoạch không thực hiện các bước commit tự động.
