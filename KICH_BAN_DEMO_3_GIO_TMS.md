# Kịch bản demo 3 giờ - EPL Logistics TMS

Mục tiêu demo: cho khách thấy hệ thống đi được một luồng TMS rõ ràng từ Master Data → Control Tower → Báo giá/SO/DO → Dispatch → GPS/POD → Finance/Tender → Shipment 360°.

## 0. Chuẩn bị trước khi đứng demo

Chạy server:

```powershell
cd D:\Demo_Lao\EPL_System
.\RUN_DEMO_3_GIO.ps1 -StartServer
```

Nếu cần nạp dữ liệu mẫu:

```powershell
cd D:\Demo_Lao\EPL_System
.\RUN_DEMO_3_GIO.ps1 -SeedData -StartServer -OpenBrowser
```

Sau khi web mở, bấm `Ctrl + F5` để trình duyệt lấy bản JS mới.

Lời mở:

> “Em sẽ demo theo góc nhìn Control Tower. Hệ thống không chỉ có form nhập li viêtệu, mà có checklist cấu hình, điều phối, GPS/POD, tender thuê ngoài, tài chính vận tải và Shipment 360° để truy vết một chuyến từ A đến Z.”

## 1. Master Data Finance - chứng minh có CRUD thật

Vào `Dữ Liệu Gốc (Master Data)` → khu `Kế toán & Hệ thống`.

Demo 4 tab:

1. `7. Thuế (Tax Codes)`
   - Bấm `Thêm mã thuế`.
   - Nhập `VAT8`, thuế suất `0.08`, lưu.
   - Trên dòng vừa tạo, bấm `Sửa`, đổi thuế suất hoặc ngày hiệu lực.
   - Bấm `Khóa`, sau đó bấm `Mở`.
   - Nếu muốn chứng minh kiểm soát dữ liệu, bấm `Xóa` với một dòng test.

2. `8. Kỳ Kế Toán`
   - Tạo kỳ `2026-08`.
   - Bấm `Khóa` để giải thích: kỳ khóa thì không nên post AP/payment.
   - Bấm `Mở` lại để tiếp tục demo.

3. `9. Carrier / Vendor`
   - Tạo `EPL-INTERNAL-FLEET` và tick “Đây là đội xe nội bộ”.
   - Nói rõ:
     > “Nếu công ty tự vận chuyển, FO có thể đi Dispatch nội bộ. Nếu cần thuê ngoài, hệ thống đưa sang Tender Cockpit.”

4. `10. Mapping Tài Khoản`
   - Tạo mapping `carrier_expense:freight` → `6427`.
   - Nói:
     > “Finance không tự bịa tài khoản. Nếu thiếu mapping, hệ thống báo quay lại Master Data để cấu hình.”

Điểm nhấn với khách:

> “Các nút ở đây không còn là nút trang trí. Sửa/Khóa-Mở/Xóa đều gọi API thật và lưu vào CSDL.”

## 2. Overview / Control Tower

Vào `Tổng quan`.

Trình bày theo thứ tự:

1. `Setup Master Data ban đầu`
   - Chỉ các mục đã đủ/chưa đủ.
   - Nếu thiếu, click để đi về đúng Master Data.

2. `TMS Control Tower`
   - Đơn chờ dispatch.
   - Xe rảnh/bận.
   - Chuyến trễ SLA/ETA.
   - Thiếu POD.
   - Finance worklist.

Lời thoại:

> “Người vận hành không cần đi mò từng màn. Control Tower gom việc cần làm và đẩy user tới đúng nơi xử lý.”

## 3. Luồng đơn hàng: Báo giá → SO → DO

Vào `Nghiệp vụ`.

Demo nhanh:

1. Tạo hoặc mở báo giá demo.
2. Duyệt báo giá.
3. Tạo Sales Order từ báo giá.
4. Xác nhận SO.
5. Tạo Delivery Order.
6. Duyệt DO.

Điểm nhấn:

> “Sau khi duyệt/chốt, hệ thống khóa sửa/xóa nghiệp vụ để tránh thay đổi dữ liệu đã được kiểm soát.”

## 4. Dispatch / phân xe tài xế

Vào `Dispatch`.

Demo:

1. Mở Dispatch Calendar/Gantt.
2. Chọn DO demo.
3. Xem xe/tài xế đang rảnh/bận.
4. Nếu có cảnh báo trùng, giải thích hệ thống không cho phân tài nguyên chồng lịch.
5. Bấm `Mở Shipment 360°` từ Dispatch.

Lời thoại:

> “Dispatch không chỉ là gán xe. Nó kiểm tra trạng thái tài nguyên, lịch bận, và đưa về hồ sơ chuyến để theo dõi tiếp.”

## 5. GPS / POD / Event timeline

Vào `Theo Dõi GPS & Ký Nhận Hàng`.

Nhập hoặc dùng DO demo: `DEMO-DO-2026-001`.

Demo:

1. Bấm `Theo Dõi`.
2. Xem bản đồ, tốc độ, khoảng cách còn lại, ETA.
3. Xem chuỗi event GPS/POD.
4. Bổ sung POD nếu cần.
5. Báo sự cố vận chuyển nếu muốn demo exception.

Điểm nhấn:

> “Event được ghi theo thời điểm, vị trí, loại sự kiện và nguồn dữ liệu. Đây là nền để đối soát thực tế với kế hoạch.”

## 6. Shipment 360° - hồ sơ chuyến từ A đến Z

Vào `Tổng quan` → panel `Shipment 360° / Hồ sơ chuyến`.

Demo:

1. Chọn DO demo.
2. Xem summary: khách hàng, tuyến, xe, tài xế, ETA, khoảng cách.
3. Click từng bước timeline:
   - Báo giá/SO/DO → về màn nghiệp vụ.
   - Dispatch → về Dispatch và ghim đúng DO.
   - GPS/POD → về Tracking và tự điền đúng DO.
   - Finance → về Finance Cockpit.
4. Bấm các nút hành động:
   - `Mở Dispatch`
   - `GPS/POD`
   - `Mở tài chính`
   - `Xem timeline A-Z`

Lời thoại:

> “Shipment 360° là màn cho quản lý. Thay vì hỏi từng phòng ban, mình mở một hồ sơ chuyến và đi sâu xuống từng bước nghiệp vụ.”

## 7. Tender Cockpit - nội bộ hay thuê ngoài

Vào khu `Tender / Carrier`.

Demo theo 2 nhánh:

1. Nếu có đội xe nội bộ:
   - Chỉ KPI/wording `FO có thể đi Dispatch nội bộ`.
   - Nói: “Không bắt buộc tender nếu công ty tự vận chuyển.”

2. Nếu thiếu xe hoặc chọn thuê ngoài:
   - Chỉ `FO cần tender thuê ngoài`.
   - Mời carrier gửi offer.
   - So sánh offer.
   - Award carrier tốt nhất.

Lời thoại:

> “Hệ thống không ép mọi chuyến phải tender. Nó phân biệt đội xe nội bộ và carrier thuê ngoài, giống cách các TMS lớn vận hành.”

## 8. Finance Cockpit - Actual Cost → AP → Payment → Settlement

Vào `Kế toán & Tài chính`.

Demo:

1. Xem KPI tài chính vận tải.
2. Mở `Actual Cost chờ xử lý`.
3. Mở hồ sơ chi tiết.
4. Trình bày luồng:
   - Actual Cost
   - AP Invoice
   - GL Posting
   - Payment
   - Settlement
   - Reversal nếu sai

Nếu action báo thiếu token/quyền:

> “Phần tài chính có kiểm soát quyền. Demo hiện tại đang chặn thao tác nhạy cảm nếu chưa có token/quyền, và báo bằng tiếng Việt thay vì lỗi kỹ thuật.”

## 9. Kết demo

Tổng kết theo checklist:

| Nhóm | Mức demo hiện tại | Điểm nói với khách |
|---|---:|---|
| Master Data vận hành | 86-88% | Có checklist và CRUD finance nền |
| Báo giá → SO → DO | 86% | Luồng chính có kiểm soát duyệt/chốt |
| Dispatch | 84-86% | Có lịch, tài nguyên, chống trùng cơ bản |
| GPS/POD/Event | 84-86% | Có bản đồ, event, POD, exception |
| Tender/Carrier | 74-78% | Có phân biệt nội bộ/thuê ngoài và cockpit |
| Finance/AP/Settlement | 80-82% | Có cockpit, worklist và detail flow |
| Shipment 360° | 82-85% | Có hồ sơ chuyến và click sâu từng bước |
| UI/UX tổng thể | 75-78% | Đủ demo khách hiểu A-Z |

Lời kết:

> “Bản này đã đủ để demo định hướng TMS enterprise: có dữ liệu nền, luồng nghiệp vụ, điều phối, theo dõi thực tế, chứng từ, tender và tài chính. Các bước tiếp theo để lên production sâu hơn là role permission UI, finance posting thực chiến theo kỳ kế toán và báo cáo SLA drill-down nâng cao.”
