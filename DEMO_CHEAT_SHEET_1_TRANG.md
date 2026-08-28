# Demo Cheat Sheet 1 Trang - EPL Logistics TMS

## 1. Câu mở demo

> “Em sẽ demo EPL theo góc nhìn TMS Control Tower: bắt đầu từ dữ liệu nền, đi qua báo giá, đơn hàng, điều phối, GPS/POD, tender thuê ngoài và tài chính vận tải. Điểm chính là hệ thống không để người dùng đi mò màn hình; thiếu dữ liệu thì báo vào đúng Master Data để cấu hình.”

## 2. Thứ tự click nhanh

1. `RUN_DEMO_3_GIO.ps1 -StartServer`, mở web và bấm `Ctrl + F5`.
2. Vào `Dữ Liệu Gốc (Master Data)` → kiểm tra Thuế, Kỳ kế toán, Carrier/Vendor, Mapping tài khoản.
3. Demo CRUD nhanh: `Thêm` → `Sửa` → `Khóa/Mở` trên 1 dòng Master Data Finance.
4. Vào `Tổng quan` → chỉ `Master Data Setup Checklist`.
5. Chỉ `Control Tower`: đơn chờ dispatch, xe rảnh/bận, thiếu POD, finance pending.
6. Vào `Dispatch` → chọn chuyến → mở `Shipment 360°`.
7. Trong `Shipment 360°`: click timeline, GPS/POD, Finance.
8. Vào `Tender Cockpit`: nói rõ nội bộ thì Dispatch, thuê ngoài thì Tender/Carrier.
9. Vào `Finance Cockpit`: Actual Cost → AP → Payment → Settlement.
10. Kết bằng `Shipment 360°` để khách thấy hồ sơ chuyến A-Z.

## 3. Câu nhấn mạnh khi demo

- “Nếu công ty tự vận chuyển, FO có thể đi Dispatch nội bộ; không bắt buộc tender.”
- “Nếu cần thuê ngoài, hệ thống đưa sang Tender Cockpit để mời carrier và chọn offer.”
- “Finance không tự bịa tài khoản/kỳ kế toán; thiếu cấu hình thì báo vào Master Data.”
- “Shipment 360° là hồ sơ chuyến: click một chỗ đi sâu về Dispatch, GPS/POD, Finance.”
- “Các nút Master Data Finance không còn là nút xem; đã có CRUD thật qua API.”

## 4. Nếu khách hỏi khó

**Hỏi: Có production được chưa?**  
Trả lời: “Bản demo đã có luồng enterprise TMS rõ: master data, execution, tender, finance, audit/idempotency nền. Để production thật cần chốt phân quyền người dùng, migration DB chính thức, và kiểm thử hiệu năng theo dữ liệu khách.”

**Hỏi: Sao có chỗ báo thiếu quyền/token?**  
Trả lời: “Đó là chủ đích với các thao tác nhạy cảm tài chính/tender. Hệ thống fail-closed, báo tiếng Việt, không cho post bừa.”

**Hỏi: Có dùng mock data không?**  
Trả lời: “Dữ liệu demo được seed vào DB thật để trình diễn. Khi vận hành, user cấu hình trong Master Data hoặc import từ hệ thống nguồn.”

**Hỏi: TMS này khác form nhập liệu thường ở đâu?**  
Trả lời: “Khác ở Control Tower, Shipment 360°, event GPS/POD, tender decision, finance settlement và cảnh báo thiếu cấu hình.”

## 5. Fallback khi có sự cố trong demo

- Nếu web không load: chạy `RUN_DEMO_HEALTH_CHECK.ps1`, kiểm `/api/health`.
- Nếu dữ liệu trống: chạy `RUN_DEMO_3_GIO.ps1 -SeedData`.
- Nếu JS cũ: bấm `Ctrl + F5`.
- Nếu Postgres tắt: nói “server DB đang ngắt”, dùng demo SQLite/tạm hoặc chỉ trình bày UI.
- Nếu finance action báo quyền: nói đây là kiểm soát role/permission của thao tác nhạy cảm.

## 6. Câu kết

> “EPL hiện đã đủ để demo một TMS end-to-end: từ cấu hình nền, vận hành chuyến, GPS/POD, tender carrier đến tài chính vận tải. Bước tiếp theo để lên production là hardening phân quyền, migration chính thức và dashboard KPI nâng cao theo dữ liệu khách.”
