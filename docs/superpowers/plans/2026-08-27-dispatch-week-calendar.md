# Dispatch Week Calendar Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến màn hình điều phối chính thành TKB tuần và chuyển thao tác DO/Trip/nguồn lực vào form theo ngày.

**Architecture:** Giữ các helper lịch và kiểm tra xung đột hiện có. Thêm bộ tổng hợp DO theo ngày và một modal workbench tái sử dụng danh sách DO, Trip gate và form điều phối hiện hành.

**Tech Stack:** Vanilla JavaScript, HTML/CSS, Node contract tests.

---

### Task 1: Khóa hợp đồng UI
- [ ] Viết test TKB không có nút chọn xe và ô ngày có số DO.
- [ ] Viết test form theo ngày có danh sách DO và vùng xử lý.
- [ ] Chạy test để xác nhận thất bại.

### Task 2: TKB tuần
- [ ] Tổng hợp DO theo ngày lấy hàng và mức độ khẩn.
- [ ] Phóng TKB tuần toàn chiều ngang.
- [ ] Bấm ngày mở form điều phối theo ngày.

### Task 3: Form điều phối theo ngày
- [ ] Lọc danh sách DO đúng ngày.
- [ ] Giữ Trip gate cho DO thiếu Trip, Trip nháp và Trip đã lập kế hoạch.
- [ ] Hiển thị form nguồn lực khi Trip sẵn sàng.

### Task 4: Xác minh
- [ ] Chạy kiểm tra cú pháp và contract test.
- [ ] Kiểm tra backend health.
