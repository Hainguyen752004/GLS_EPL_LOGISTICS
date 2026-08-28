# 15 Test Case Kiểm Tra Button, Cột, Form Và Luồng EPL Logistics

Ngày lập: 05/08/2026  
Mục tiêu: kiểm thử thao tác tay để demo luồng từ Master Data → Báo Giá → Đơn Hàng → Lệnh Giao Hàng → Điều Phối → GPS/POD → Hóa Đơn, đồng thời kiểm tra khóa sửa/xóa sau khi duyệt.

## Điều kiện trước khi test

- Backend chạy bằng PostgreSQL:

```powershell
cd D:\Demo_Lao\EPL_System\backend\app
$env:EPL_ENV_FILE="D:\Demo_Lao\.env"
$env:DATABASE_MODE="postgres"
C:\Users\zinnn\miniconda3\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

- Trình duyệt mở `http://127.0.0.1:8000`, sau khi có sửa code thì bấm `Ctrl + F5`.
- Không dùng dữ liệu mock. Tất cả dữ liệu lưu/đọc từ PostgreSQL qua API.

---

## TC01 - Master Data / Tuyến Đường: thêm chặng và lưu tuyến

Mục tiêu: kiểm tra button `Thêm Chặng` và `Hoàn Tất & Lưu Tuyến Đường`.

Các bước:

1. Vào `Dữ Liệu Gốc (Master Data)` → `Cấu Hình Tuyến Đường Cố Định`.
2. Bấm `Thêm Tuyến Đường Mới`.
3. Nhập `Route Code`: `TEST-RT-001`.
4. Nhập `Route Name`: `Kho VSIP II-A → Cảng Cát Lái`.
5. Nhập chặng:
   - From: `Kho VSIP II-A, Tân Uyên, Bình Dương`
   - To: `Cảng Cát Lái, TP. Thủ Đức`
   - Distance: `45`
6. Bấm `Thêm Chặng`.
7. Kiểm tra cột `From`, `To`, `Distance`, `Thao Tác`.
8. Bấm `Hoàn Tất & Lưu Tuyến Đường`.

Kết quả mong đợi:

- Tổng quãng đường hiển thị `45 km`.
- Dropdown tuyến đã lưu có `TEST-RT-001`.
- API `/api/routes` trả về tuyến mới.
- Không tự sinh quãng đường 200 km nếu chưa nhập chặng.

---

## TC02 - Master Data / Tuyến Đường: chọn tuyến đã lưu và vẽ bản đồ

Mục tiêu: kiểm tra dropdown `Xem & Chọn Tuyến Đường Đã Lưu Trong CSDL`.

Các bước:

1. Vào tab tuyến đường.
2. Chọn `TEST-RT-001` hoặc tuyến demo đang có.
3. Quan sát bảng `Route Segments`.
4. Quan sát khung `Sơ Đồ Lộ Trình Đa Chặng Tương Tác`.

Kết quả mong đợi:

- Form tự điền `Route Code`, `Route Name`.
- Bảng chặng hiển thị đúng dữ liệu từ PostgreSQL.
- Bản đồ vẽ tuyến theo tọa độ lưu trong CSDL hoặc geocode từ tên điểm.
- Không hiện map rỗng nếu route có chặng/tọa độ hợp lệ.

---

## TC03 - Master Data / Phương Tiện: thêm xe và tải ảnh xe

Mục tiêu: kiểm tra form `Thêm Mới Phương Tiện Vận Tải` và nút tải ảnh.

Các bước:

1. Vào `Master Data` → `Loại Phương Tiện / Phương Tiện`.
2. Bấm `Thêm Mới Phương Tiện`.
3. Nhập biển số `TEST-51C-000.01`.
4. Nhập hãng xe, loại phương tiện, tải trọng, định mức nhiên liệu.
5. Tải ảnh xe lên nếu có nút/file upload.
6. Bấm `Lưu Thông Tin Phương Tiện`.

Kết quả mong đợi:

- Xe xuất hiện trong bảng.
- Cột ảnh xe hiển thị ảnh hoặc icon placeholder.
- API `/api/vehicles` trả xe mới.
- Tiếng Việt trên form không bị lỗi dấu.

---

## TC04 - Master Data / Tài Xế: thêm tài xế sẵn sàng

Mục tiêu: kiểm tra form nhân sự tài xế/phụ xế.

Các bước:

1. Vào `Quản Lý Tài Xế & Sắp Ca`.
2. Bấm thêm nhân sự.
3. Nhập mã `TEST-DRV-001`, tên tài xế, bằng lái, số điện thoại.
4. Chọn trạng thái `Rảnh / Sẵn sàng`.
5. Bấm lưu.

Kết quả mong đợi:

- Tài xế hiển thị trong bảng.
- Tài xế có thể xuất hiện ở màn hình điều phối.
- Trạng thái hiển thị tiếng Việt chuẩn.

---

## TC05 - Báo Giá: tạo báo giá bản nháp từ Master Data

Mục tiêu: kiểm tra button `Lưu Báo Giá`.

Các bước:

1. Vào phân hệ `CRM & Sales`.
2. Bấm tạo báo giá mới.
3. Chọn khách hàng từ Master Data.
4. Chọn tuyến đường từ Master Data.
5. Nhập loại hàng, chi phí, giá bán.
6. Bấm `Lưu Báo Giá`.

Kết quả mong đợi:

- Báo giá xuất hiện trong bảng.
- Cột trạng thái là `Bản nháp`.
- Có nút `Sửa`, `Chuyển thành SO` bị disabled hoặc không cho chạy nếu chưa duyệt, và `Xóa`.
- API `/api/quotations` có bản ghi mới.

---

## TC06 - Báo Giá: duyệt báo giá

Mục tiêu: kiểm tra button `Duyệt Báo Giá`.

Các bước:

1. Mở một báo giá `Bản nháp`.
2. Bấm `Duyệt Báo Giá`.
3. Đóng/mở lại danh sách báo giá.

Kết quả mong đợi:

- Trạng thái chuyển thành `Đã duyệt`.
- Nút `Sửa` đổi thành `Xem`.
- Nút `Xóa` không còn hiển thị.
- API DELETE `/api/quotations/{id}` bị chặn với code `LOCKED_RECORD`.

---

## TC07 - Báo Giá đã duyệt: kiểm tra không sửa/xóa

Mục tiêu: đảm bảo khóa chứng từ sau duyệt.

Các bước:

1. Bấm vào mã báo giá đã duyệt.
2. Kiểm tra các input trong form.
3. Kiểm tra footer form.
4. Tìm nút `Lưu Báo Giá` và `Xóa`.

Kết quả mong đợi:

- Form chỉ xem, input disabled.
- Không thấy nút lưu/sửa/xóa.
- Nếu gọi hàm save/delete trực tiếp, hệ thống báo: `Báo giá đã duyệt chỉ được xem...`.

---

## TC08 - Chuyển Báo Giá đã duyệt thành Sales Order

Mục tiêu: kiểm tra button `Chuyển thành SO`.

Các bước:

1. Ở bảng báo giá, chọn báo giá `Đã duyệt`.
2. Bấm `Chuyển thành SO`.
3. Kiểm tra form Sales Order.
4. Bấm `Lưu Đơn Hàng`.

Kết quả mong đợi:

- Form SO tự kế thừa khách hàng, tuyến, giá trị từ báo giá.
- Frontend gửi `quotation_id` về backend.
- Backend tạo SO ở trạng thái `Bản nháp`.
- API `/api/sales-orders` có SO mới liên kết báo giá nguồn.

---

## TC09 - Sales Order: chốt/xác nhận đơn hàng

Mục tiêu: kiểm tra button `Chốt Đơn` hoặc `Duyệt Đơn Hàng`.

Các bước:

1. Mở SO trạng thái `Bản nháp`.
2. Bấm `Chốt Đơn` hoặc `Duyệt Đơn Hàng`.
3. Quay lại danh sách SO.

Kết quả mong đợi:

- Trạng thái SO là `Đã xác nhận`.
- Nút `Xem / Sửa` đổi thành `Xem`.
- Nút `Xóa` không còn.
- API DELETE `/api/sales-orders/{id}` bị chặn với code `LOCKED_RECORD`.

---

## TC10 - Sales Order đã xác nhận: tạo Lệnh Giao Hàng DO

Mục tiêu: kiểm tra button `Tạo Lệnh DO`.

Các bước:

1. Ở danh sách SO, chọn SO `Đã xác nhận`.
2. Bấm `Tạo Lệnh DO`.
3. Kiểm tra form DO.
4. Bấm lưu DO.

Kết quả mong đợi:

- DO kế thừa `so_id`, khách hàng, tuyến từ SO.
- DO tạo ở trạng thái `Đã lập kế hoạch`.
- DO xuất hiện trong `Lập Kế Hoạch Vận Hành Logistics`.

---

## TC11 - Delivery Order: duyệt lệnh giao hàng

Mục tiêu: kiểm tra button `Duyệt Lệnh`.

Các bước:

1. Mở DO trạng thái `Đã lập kế hoạch`.
2. Bấm `Duyệt Lệnh`.
3. Quay lại danh sách DO.

Kết quả mong đợi:

- Trạng thái DO chuyển thành `Đã duyệt`.
- DO xuất hiện ở màn hình điều phối.
- Nút `Chỉnh sửa` đổi thành `Xem`.
- Nút `Xóa` không còn.
- API DELETE `/api/delivery-orders/{id}` bị chặn với code `LOCKED_RECORD`.

---

## TC12 - Điều Phối: chọn DO, xe, tài xế và xuất bến

Mục tiêu: kiểm tra các button chọn nguồn lực và xác nhận điều phối.

Các bước:

1. Vào phân hệ `Điều Phối`.
2. Chọn DO đã duyệt.
3. Bấm chọn xe từ `View Toàn Cảnh`.
4. Bấm chọn tài xế chính.
5. Bấm chọn phụ xế nếu có.
6. Bấm xác nhận điều phối/xuất bến.

Kết quả mong đợi:

- DO chuyển sang `Đang vận chuyển`.
- Xe chuyển trạng thái bận/đang giao đơn.
- Tài xế chuyển trạng thái bận.
- Bảng `Xe & Tài Xế Bận` tăng số.
- GPS có tracking cho DO.

---

## TC13 - GPS: theo dõi DO đang vận chuyển

Mục tiêu: kiểm tra ô nhập mã DO và button `Theo Dõi`.

Các bước:

1. Vào phân hệ `GPS`.
2. Nhập mã DO đang vận chuyển.
3. Bấm `Theo Dõi`.
4. Quan sát map, tốc độ, khoảng cách còn lại, ETA.

Kết quả mong đợi:

- Bản đồ hiển thị xe/tuyến.
- Thông tin xe/DO đúng dữ liệu đã điều phối.
- Nếu nhập DO chưa điều phối, hệ thống báo cần điều phối/GPS trước, không dùng dữ liệu giả.

---

## TC14 - POD: cập nhật bằng chứng giao hàng

Mục tiêu: kiểm tra form `Bằng Chứng Giao Hàng (POD)`.

Các bước:

1. Ở màn hình GPS, chọn DO đang vận chuyển.
2. Nhập thời gian giao hàng thực tế.
3. Nhập người nhận/số điện thoại.
4. Tải ảnh biên bản hoặc chữ ký POD.
5. Nhập ghi chú tình trạng hàng hóa.
6. Bấm `Xác Nhận Hoàn Tất Giao Hàng`.

Kết quả mong đợi:

- POD được lưu vào PostgreSQL.
- DO chuyển sang `Đã giao hàng`.
- Xe và tài xế được trả về trạng thái sẵn sàng nếu không còn đơn active khác.
- Hệ thống chuyển tiếp hoặc tạo dữ liệu hóa đơn.

---

## TC15 - Hóa Đơn & Báo Cáo: tạo hóa đơn sau giao hàng

Mục tiêu: kiểm tra bước cuối luồng kế toán.

Các bước:

1. Hoàn tất POD cho một DO.
2. Chờ hệ thống tự đẩy sang kế toán hoặc bấm chức năng tạo/post hóa đơn nếu có.
3. Vào phân hệ `Tài chính & Khác` hoặc `Invoice`.
4. Kiểm tra bảng hóa đơn và GL.

Kết quả mong đợi:

- Có hóa đơn AR cho DO đã giao.
- Có dòng hạch toán GL tương ứng.
- Dashboard KPI cập nhật doanh thu/công nợ.
- Trạng thái hóa đơn hiển thị tiếng Việt chuẩn, không lỗi dấu.

---

## Checklist khóa sau duyệt

Áp dụng cho các bảng có cột `Thao Tác`:

- `Bản nháp`: cho `Sửa`, `Xóa`, `Duyệt`.
- `Đã duyệt`: chỉ cho `Xem`, không cho `Sửa/Xóa`.
- `Đã xác nhận`: chỉ cho `Xem`, có thể cho tạo bước sau nếu đúng luồng.
- `Đang vận chuyển`: chỉ theo dõi/GPS/POD, không sửa/xóa DO.
- `Đã giao hàng`: chỉ xem và kế toán, không sửa/xóa.

## API cần kiểm nhanh khi demo

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/routes
Invoke-RestMethod http://127.0.0.1:8000/api/quotations
Invoke-RestMethod http://127.0.0.1:8000/api/sales-orders
Invoke-RestMethod http://127.0.0.1:8000/api/delivery-orders
Invoke-RestMethod http://127.0.0.1:8000/api/invoices
```
