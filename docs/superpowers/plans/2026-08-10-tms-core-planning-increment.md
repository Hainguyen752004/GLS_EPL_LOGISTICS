# TMS Core Planning Increment

## Mục tiêu

Tạo lát cắt nghiệp vụ thật `Transportation Demand → Freight Unit → Freight Order`, tương thích PostgreSQL và không thay thế dữ liệu QT/SO/DO hiện có.

## Phạm vi increment

1. Migration `003_tms_core_planning` tạo `transport_demands`, `freight_units`, `freight_orders`, `freight_order_units`.
2. Demand có điểm lấy/giao, time window, trọng lượng, thể tích, pallet, trạng thái và version.
3. Chỉ Demand đã submit mới sinh Freight Unit; một Demand chỉ sinh một Freight Unit trong increment này.
4. Freight Order ghép nhiều Freight Unit và tính tổng năng lực.
5. Từ chối ghép khi khác tuyến, time window không giao nhau hoặc vượt tải trọng/thể tích/pallet khai báo.
6. Mọi command ghi AuditLog và trả lỗi nghiệp vụ tiếng Việt ổn định.
7. API dưới namespace `/api/tms`; router gắn một lần trong `main.py`.

## TDD và kiểm chứng

- Quan sát test đỏ trước khi tạo model/service/router.
- Domain/service tests: transition, provenance, capacity, time window và rollback.
- API tests: response envelope, 409/422 và route uniqueness.
- Migration tests cho SQLite cô lập và SQL PostgreSQL dry-run.
- Chạy toàn bộ backend regression trước khi sang carrier/tender.

## Ngoài phạm vi increment

Carrier/tender, warehouse appointment, execution event EPCIS, AP/settlement và KPI sẽ dùng ID của Freight Order/Freight Unit từ increment này trong các increment kế tiếp.
