# 🚀 KỊCH BẢN THAO TÁC NGHIỆP VỤ LOGISTICS TỪ A ĐẾN Z (END-TO-END DEMO SCRIPT)
**Hệ Thống Quản Lý Logistics Doanh Nghiệp EPL System - Production Standard**

---

### 📌 QUY TRÌNH THAO TÁC CƠ BẢN (8 BƯỚC THỜI GIAN THỰC)

Dưới đây là kịch bản chuẩn để sếp tự tay thao tác hoặc trình diễn (Demo) trọn vẹn 1 Đơn Hàng từ khi báo giá cho đến khi lên Sổ Cái Kế Toán:

---

#### 🟢 BƯỚC 0: KHỞI TẠO DỮ LIỆU GỐC (MASTER DATA)
1. **Truy cập:** Bấm vào thẻ **`0. Master Data`** trên thanh Tracker trên cùng (hoặc Menu Trái).
2. **Khai báo Xe & Tài xế:** Xem danh sách xe `51C-123.45` hoặc bấm nút *+ Thêm Xe Mới*.
3. **Thiết lập Công thức Cước:** Chọn `Mẫu 1` hoặc `Mẫu 2` trong mục *Cấu Hình Công Thức Tính Cước Master Data*, tùy chỉnh đơn giá Xăng dầu/BOT rồi bấm **`Lưu Cấu Hình Công Thức`**.

---

#### 🟢 BƯỚC 1: BÁO GIÁ VẬN TẢI (QUOTATION)
1. **Truy cập:** Bấm vào nút **`1. QT`** trên thanh Tracker top.
2. **Tạo Báo Giá:** Bấm **`+ Tạo Báo Giá Mới`**.
3. **Điền thông tin:** 
   - Chọn Tuyến Đường: `RT-001: Bình Dương ➔ Cát Lái Port`
   - Chọn Loại Xe: `Container 20FT`
   - *Hệ thống tự động áp dụng công thức Master Data tính ra tổng tiền: 2,587,500 VNĐ*.
4. **Lưu Báo Giá:** Bấm **`Lưu Báo Giá`** ➔ Thông báo thành công & **tự động chuyển thanh Tracker sang Bước 2**.

---

#### 🟢 BƯỚC 2: ĐƠN HÀNG BÁN (SALES ORDER - SO)
1. **Truy cập:** Bấm vào nút **`2. SO`** ➔ Màn hình tự động cuộn mượt xuống thẳng Bảng Đơn Hàng Bán.
2. **Tạo Đơn Hàng:** Bấm **`+ Tạo Đơn Hàng Mới`**.
3. **Xác nhận Đơn:** Chọn Khách hàng `Tập đoàn Điện máy Xanh`, Tuyến đường `RT-001`.
4. **Lưu Đơn Hàng:** Bấm **`Lưu Đơn Hàng`** ➔ Lưu CSDL SQLite & **tự động đẩy sang Bước 3**.

---

#### 🟢 BƯỚC 3: LỆNH GIAO HÀNG (DELIVERY ORDER - DO)
1. **Truy cập:** Bấm vào nút **`3. DO`** ➔ Cuộn mượt đến Bảng Lệnh Giao Hàng `DO`.
2. **Xuất Lệnh Kho:** Kiểm tra mã đơn `DO-2026-001` (hoặc `DO-2026-002`) có trạng thái *Sẵn sàng điều phối*.
3. **Xác nhận:** Đơn tự động được đẩy vào Bảng Chờ Điều Phối Nguồn Lực ➔ **Tự động chuyển sang Bước 4**.

---

#### 🟢 BƯỚC 4: KẾ HOẠCH TUYẾN ĐƯỜNG (ROUTE PLANNING)
1. **Truy cập:** Bấm nút **`4. Route`**.
2. **Tải lộ trình OSRM:** Màn hình tự động nạp Bản đồ GPS Leaflet Map, nối đường từ `Bình Dương ➔ Cát Lái Port` (200 km / 4 giờ).

---

#### 🟢 BƯỚC 5: LẬP LỊCH & ĐIỀU PHỐI (DISPATCHING)
1. **Truy cập:** Bấm nút **`5. Dispatch`**.
2. **Chọn Lệnh DO:** Nhấp chọn `DO-2026-002` (hoặc `DO-2026-001`) bên danh sách Chờ Xử Lý.
3. **Phân bổ Nguồn lực:**
   - Chọn Xe: `51C-123.45 - Container 20FT`
   - Chọn Tài xế: `DRV-002 - Trần Văn Minh`
4. **Xuất bến:** Bấm **`Xác Nhận Điều Phối 🚀`** ➔ Ghi nhận CSDL status `In Transit` & **tự động nhảy thẳng sang Màn hình GPS Tracking Bước 6!**

---

#### 🟢 BƯỚC 6: GIÁM SÁT GPS REALTIME & KÝ NHẬN POD
1. **Theo dõi GPS:** Xe chạy hiển thị trực quan trên bản đồ sống động.
2. **Báo sự cố (Nếu có):** Bấm nút **`+ Báo Sự Cố Mới`** ➔ Chọn loại sự cố *Nổ lốp xe* ➔ Bấm *Gửi Báo Cáo* (Thẻ Sự Cố trên Dashboard lập tức tăng nhảy số).
3. **Ký nhận POD:** Nhấp đính kèm file biên bản ➔ Bấm **`XÁC NHẬN HOÀN TẤT GIAO HÀNG (SUBMIT POD)`** ➔ **Tự động nhảy sang Bước 7**.

---

#### 🟢 BƯỚC 7: HÓA ĐƠN & SỔ CÁI KẾ TOÁN (INVOICE & GL)
1. **Truy cập:** Bấm nút **`7. Invoice`**.
2. **Phát hành Hóa đơn:** Bấm **`Phát Hành Hóa Đơn & Định Khoản Sổ Cái (GL Posting)`**.
3. **Kiểm tra Sổ Cái Kế Toán:** 
   - Hóa đơn `INV-2026-001` xuất hiện bên bảng AR Invoices.
   - Bảng **Nhật Ký Sổ Cái Kế Toán (GL)** tự động xuất hiện 2 dòng định khoản thật:
     - 🟢 **Nợ TK 131 (Phải Thu Khách Hàng):** `+2,587,500 VNĐ`
     - 🔴 **Có TK 511 (Doanh Thu Vận Tải):** `+2,587,500 VNĐ`

---
✨ **HOÀN THÀNH TRỌN VẸN VÒNG ĐỜI NGHIỆP VỤ LOGISTICS TỪ A ĐẾN Z 100% CSDL THỰC TẾ!**
