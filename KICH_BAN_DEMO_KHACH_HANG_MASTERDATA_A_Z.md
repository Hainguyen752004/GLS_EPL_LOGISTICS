                     # Kịch Bản Demo Khách Hàng: EPL Logistics A-Z Từ Master Data Đến Kế Toán

Mục tiêu: trình diễn hệ thống EPL vận hành một đơn logistics trọn vẹn từ dữ liệu nền, báo giá, đơn hàng, lệnh giao hàng, điều phối, POD, hóa đơn đến sổ cái. Kịch bản này dùng dữ liệu nhập tay trên Master Data và giao diện, không dùng mock data.

## 0. Chuẩn Bị Trước Khi Demo

Người demo mở hệ thống, kiểm tra các điều kiện sau:

1. Database đang dùng SQLite/PostgreSQL thật, không dùng seed/reset tự động.
2. Không mở các trang stress test như `test_100_scenarios.html`, `test_1000_scenarios.html`, `test_5000_scenarios.html`.
3. Mở màn hình Master Data trước, vì toàn bộ luồng sau sẽ phụ thuộc vào dữ liệu nền.
4. Nếu API báo thiếu dữ liệu, đọc `navigation_targets` hoặc thông báo tiếng Việt để quay đúng màn hình cấu hình.

Lời mở demo gợi ý:

> "Em sẽ bắt đầu từ dữ liệu nền. EPL không tự bịa khách hàng, tuyến, xe hay tài xế. Nếu thiếu cấu hình, hệ thống sẽ yêu cầu quay lại Master Data trước khi cho đi tiếp luồng nghiệp vụ."

## 1. Setup Master Data Ban Đầu

### 1.1. Khách Hàng

Vào `Master Data -> Customers`, tạo khách hàng:

- Mã khách hàng: `CUS-DEMO-001`
- Tên khách hàng: `Công ty TNHH Demo Retail Việt Nam`
- Loại: `Account`
- Người liên hệ: `Nguyễn Minh Anh`
- Điện thoại: `0908123456`
- Địa chỉ: `KCN Sóng Thần 1, Dĩ An, Bình Dương`

Điểm nhấn nói với khách:

> "Khách hàng được quản lý ở Master Data. Khi lập báo giá, người bán chỉ chọn khách đã có trong hệ thống, tránh nhập sai tên hoặc tạo dữ liệu trôi nổi."

### 1.2. Tuyến Đường

Vào `Master Data -> Routes`, tạo tuyến:

- Mã tuyến: `RT-DEMO-001`
- Tên tuyến: `Bình Dương - Cảng Cát Lái`
- Khoảng cách: `42`
- Chặng 1: `KCN Sóng Thần 1 -> Xa lộ Hà Nội`, `18 km`
- Chặng 2: `Xa lộ Hà Nội -> Cảng Cát Lái`, `24 km`

Điểm nhấn:

> "Tuyến đường là dữ liệu nền dùng cho báo giá, điều phối và báo cáo vận hành. Một lần cấu hình có thể tái sử dụng cho nhiều khách hàng/đơn hàng."

### 1.3. Loại Phương Tiện

Vào `Master Data -> Vehicle Types`, tạo loại xe:

- Mã loại: `VT-DEMO-20FT`
- Tên loại: `Container 20FT`
- Tải trọng tối đa: `15000`
- Thể tích: `30`
- Định mức nhiên liệu: `28`
- Cước cơ bản: `9500`
- Ghi chú: `Dùng cho tuyến ngắn nội vùng và hàng pallet/carton`

Điểm nhấn:

> "Loại phương tiện giúp chuẩn hóa năng lực vận tải. Khi báo giá hoặc điều phối, hệ thống có thể kiểm tra xe phù hợp tải trọng/thể tích."

### 1.4. Xe

Vào `Master Data -> Fleet/Vehicles`, tạo xe:

- Biển số: `51D-DEMO-01`
- Hãng xe: `Hyundai`
- Loại xe: `Container 20FT`
- Tải trọng: `15000`
- Thể tích: `30`
- Định mức nhiên liệu: `28`
- Trạng thái: `Sẵn sàng`

Điểm nhấn:

> "Xe chỉ điều phối được khi ở trạng thái Sẵn sàng. Khi xuất bến, xe sẽ chuyển sang trạng thái đang vận chuyển; khi giao xong, hệ thống trả xe về trạng thái sẵn sàng."

### 1.5. Tài Xế

Vào `Master Data -> Drivers`, tạo tài xế:

- Mã tài xế: `DRV-DEMO-01`
- Họ tên: `Trần Văn Demo`
- Vai trò: `Lái xe chính`
- Bằng lái: `Hạng FC`
- Điện thoại: `0912345678`
- Xe phân công: `Chưa gán`
- Ca làm việc: `Ca Sáng (06:00 - 14:00)`
- Trạng thái: `🟢 Rảnh (Sẵn sàng)`

Tạo phụ xế nếu muốn demo đầy đủ:

- Mã tài xế: `DRV-DEMO-02`
- Họ tên: `Lê Phụ Xe Demo`
- Vai trò: `Phụ xe`
- Bằng lái: `Hạng C`
- Trạng thái: `🟢 Rảnh (Sẵn sàng)`

Điểm nhấn:

> "Tài xế là nguồn lực vận hành. Hệ thống không cho dùng tài xế đang bận cho một chuyến khác."

### 1.6. Hàng Hóa Và Đơn Vị Tính

Vào `Master Data -> Items/UOM`, tạo:

- Mã hàng: `ITM-DEMO-001`
- Tên hàng: `Thiết bị điện tử đóng thùng`
- Loại hàng: `Carton`
- Đơn vị mặc định: `BOX`
- Khối lượng mỗi kiện: `25`

Tạo UOM:

- Mã UOM: `BOX`
- Mô tả: `Thùng carton`

Điểm nhấn:

> "Hàng hóa và đơn vị tính giúp báo giá/đơn hàng có số lượng, trọng lượng và doanh thu rõ ràng."

### 1.7. Tiền Tệ Và Tài Khoản Kế Toán

Vào `Master Data -> Currency`, tạo:

- Mã tiền tệ: `VND`
- Tỷ giá: `1`

Vào `Master Data -> Chart of Accounts`, tạo ít nhất:

- `131` - Phải thu khách hàng
- `511` - Doanh thu dịch vụ logistics
- `3331` - Thuế GTGT phải nộp

Nếu có màn hình Account Mapping, cấu hình:

- `AR_RECEIVABLE -> 131`
- `LOGISTICS_REVENUE -> 511`
- `VAT_OUTPUT -> 3331`

Điểm nhấn:

> "Phần kế toán không tự bịa tài khoản. Nếu thiếu sơ đồ tài khoản hoặc mapping, hệ thống phải yêu cầu cấu hình Master Data kế toán trước khi post GL."

## 2. Luồng Demo Nghiệp Vụ A-Z

### Bước 1. Lập Báo Giá

Vào phân hệ `Quotation/Báo Giá`, bấm tạo mới:

- Khách hàng: `CUS-DEMO-001`
- Tuyến: `RT-DEMO-001`
- Loại hàng: `Thiết bị điện tử đóng thùng`
- Ngày hiệu lực đến: chọn ngày sau ngày demo
- Chi phí nhiên liệu: `1,200,000`
- Chi phí tài xế: `800,000`
- Phí cầu đường: `350,000`
- Tổng chi phí: `2,350,000`
- Giá bán: `3,500,000`
- Quy cách đóng gói: `Thùng Carton (Tiêu chuẩn)`
- Thể tích: `18.5`

Kết quả mong đợi:

- Hệ thống tạo mã báo giá dạng `QT-YYYY-xxx`.
- Trạng thái ban đầu là bản nháp.
- Không có khách hàng/tuyến mặc định tự sinh.

Lời thoại:

> "Đây là bước sales lập giá dựa trên tuyến và chi phí vận hành. Mã báo giá được hệ thống cấp, nhưng dữ liệu nghiệp vụ phải đến từ Master Data hoặc người dùng nhập."

### Bước 2. Duyệt Báo Giá

Chọn báo giá vừa tạo, bấm duyệt.

Kết quả mong đợi:

- Trạng thái báo giá chuyển sang `Đã duyệt`.
- Audit log ghi nhận thao tác duyệt.
- Báo giá chưa duyệt không được tạo SO.

Lời thoại:

> "Luồng có kiểm soát phê duyệt. Sales Order chỉ được tạo từ báo giá đã duyệt, tránh bỏ qua bước kiểm soát giá."

### Bước 3. Tạo Sales Order Từ Báo Giá

Vào `Sales Orders`, tạo SO từ báo giá đã duyệt:

- Chọn báo giá nguồn vừa duyệt.
- Khách hàng, giá bán, quy cách, thể tích được kế thừa từ báo giá.
- Nhập ngày đặt hàng và ngày giao dự kiến nếu giao diện yêu cầu.

Kết quả mong đợi:

- Hệ thống tạo mã `SO-YYYY-xxx`.
- SO ở trạng thái bản nháp.
- `quotation_id` liên kết đúng về báo giá nguồn.

Lời thoại:

> "SO không phải một dòng rời rạc. Nó có nguồn từ báo giá đã duyệt, nên sau này truy xuất được giá nào sinh ra đơn hàng nào."

### Bước 4. Xác Nhận Sales Order

Chọn SO vừa tạo, bấm `Confirm/Xác nhận`.

Kết quả mong đợi:

- SO chuyển sang `Đã xác nhận`.
- Nếu SO chưa xác nhận, hệ thống không cho tạo DO.

Lời thoại:

> "Đây là điểm chốt giữa sales và vận hành. Khi SO được xác nhận, đội vận hành mới có cơ sở phát hành lệnh giao hàng."

### Bước 5. Tạo Delivery Order

Vào `Delivery Orders`, tạo DO từ SO đã xác nhận:

- SO nguồn: chọn SO vừa xác nhận.
- Tuyến: `RT-DEMO-001`
- Ngày lấy hàng: ngày/giờ demo
- Ngày giao hàng dự kiến: cùng ngày hoặc ngày kế tiếp

Kết quả mong đợi:

- Hệ thống tạo mã `DO-YYYY-xxx`.
- DO kế thừa khách hàng, tuyến, quy cách, thể tích từ SO.
- Trạng thái ban đầu: `Đã lập kế hoạch`.

Lời thoại:

> "Delivery Order là lệnh vận hành. Nó kế thừa dữ liệu từ SO để tránh người điều phối sửa nhầm khách hàng, giá hoặc hàng hóa."

### Bước 6. Duyệt Delivery Order

Chọn DO, bấm duyệt.

Kết quả mong đợi:

- DO chuyển sang `Đã duyệt`.
- Chỉ DO đã duyệt mới được điều phối xe/tài xế.

Lời thoại:

> "Điều phối không được chạy trực tiếp trên DO bản nháp. Đây là kiểm soát trước khi tiêu thụ nguồn lực đội xe."

### Bước 7. Điều Phối Xe Và Tài Xế

Vào màn hình `Dispatch/Điều phối`:

- Chọn DO vừa duyệt.
- Chọn xe `51D-DEMO-01`.
- Chọn tài xế `DRV-DEMO-01`.
- Chọn phụ xế `DRV-DEMO-02` nếu có.
- Bấm điều phối/xuất bến.

Kết quả mong đợi:

- DO chuyển sang `Đang vận chuyển`.
- Xe chuyển từ `Sẵn sàng` sang trạng thái đang vận chuyển đơn này.
- Tài xế chuyển từ `Rảnh` sang trạng thái bận.
- Nếu chọn xe/tài xế đang bận, hệ thống trả lỗi tiếng Việt và yêu cầu chọn nguồn lực khác.

Lời thoại:

> "Nguồn lực được khóa theo chuyến. Đây là điểm quan trọng cho khách vận tải: một xe/tài xế không thể bị phân công trùng nếu đang chạy đơn khác."

### Bước 8. Theo Dõi GPS

Mở màn hình tracking của DO.

Kết quả mong đợi:

- Nếu đã có tracking, hệ thống hiển thị dữ liệu GPS thật.
- Nếu chưa có tracking, hệ thống báo chưa có dữ liệu GPS và hướng người dùng quay lại điều phối/xe, không hiển thị tọa độ giả.

Lời thoại:

> "Màn hình tracking không vẽ vị trí giả. Khi chưa có dữ liệu thiết bị, hệ thống báo rõ để vận hành biết cần kiểm tra GPS."

### Bước 9. Cập Nhật Đã Đến Nơi

Trong màn hình vận hành hoặc POD, chuyển DO sang `Đã đến nơi`.

Kết quả mong đợi:

- DO chuyển từ `Đang vận chuyển` sang `Đã đến nơi`.
- Hệ thống chưa cho hoàn tất nếu chưa có POD.

Lời thoại:

> "Đến nơi là trạng thái vận hành. Giao hàng hoàn tất cần chứng từ POD, không chỉ là một nút bấm."

### Bước 10. Cập Nhật POD

Vào màn hình POD:

- Chọn đúng DO.
- Nhập thời gian giao hàng.
- Nhập người nhận: `Nguyễn Minh Anh`
- Thêm ghi chú: `Đã nhận đủ hàng, bao bì nguyên vẹn`
- Đính kèm ảnh/chữ ký nếu giao diện hỗ trợ.

Kết quả mong đợi:

- POD được lưu theo đúng DO.
- Không có fallback sang DO demo.

Lời thoại:

> "POD là bằng chứng giao hàng. Hóa đơn chỉ nên phát hành khi có đủ dữ liệu giao hàng."

### Bước 11. Hoàn Tất Giao Hàng

Sau khi có POD, chuyển DO sang `Đã giao hàng`.

Kết quả mong đợi:

- DO chuyển sang `Đã giao hàng`.
- Xe `51D-DEMO-01` trở về `Sẵn sàng`.
- Tài xế `DRV-DEMO-01` trở về `🟢 Rảnh (Sẵn sàng)`.

Lời thoại:

> "Hoàn tất chuyến không chỉ đổi trạng thái DO. Hệ thống còn giải phóng nguồn lực để đội điều phối tiếp tục dùng xe và tài xế cho chuyến sau."

### Bước 12. Lập Hóa Đơn

Vào `Invoices/Kế toán`, lập hóa đơn từ DO đã giao hàng.

Kết quả mong đợi:

- Hóa đơn lấy `customer_id` và số tiền từ SO/DO nguồn.
- Không dùng khách hàng lẻ hoặc số tiền mặc định.
- Nếu thiếu DO hoặc số tiền, API báo lỗi tiếng Việt và hướng về SO/DO.

Lời thoại:

> "Hóa đơn không nhập rời. Nó truy xuất về DO và SO, nên kế toán biết hóa đơn này phát sinh từ chuyến nào, khách nào, giá nào."

### Bước 13. Post GL

Post GL cho hóa đơn:

- Nợ `131`: tổng tiền phải thu.
- Có `511`: doanh thu dịch vụ.
- Có `3331`: VAT nếu có.

Kết quả mong đợi:

- Bút toán cân bằng.
- Có thể truy xuất từ GL về invoice, DO, SO, quotation.
- Nếu thiếu tài khoản/mapping, hệ thống yêu cầu cấu hình Master Data kế toán.

Lời thoại:

> "Điểm chốt cuối là tài chính. Một đơn logistics đi từ báo giá đến sổ cái, và mọi mắt xích đều có nguồn gốc."

## 3. Tình Huống Demo Lỗi Có Kiểm Soát

Nên demo thêm 2 lỗi để khách tin hệ thống không bịa dữ liệu:

1. Tạo báo giá nhưng bỏ trống khách hàng.
   - Kỳ vọng: hệ thống báo thiếu khách hàng và hướng về `Master Data -> Customers`.

2. Điều phối DO nhưng chọn xe đang bận.
   - Kỳ vọng: hệ thống báo xe đang bận, yêu cầu chọn xe khác trong Master Data/Dispatch.

Lời thoại:

> "Các lỗi này là lỗi có kiểm soát. Hệ thống không tự điền tạm dữ liệu để đi tiếp, vì như vậy sẽ làm sai vận hành và sai kế toán."

## 4. Checklist Cho Sếp Trước Khi Gặp Khách

- Đã có ít nhất 1 khách hàng thật trong Master Data.
- Đã có ít nhất 1 tuyến đường.
- Đã có ít nhất 1 loại xe.
- Đã có ít nhất 1 xe trạng thái `Sẵn sàng`.
- Đã có ít nhất 1 tài xế trạng thái `🟢 Rảnh (Sẵn sàng)`.
- Đã có tiền tệ `VND`.
- Đã có tài khoản kế toán `131`, `511`, `3331`.
- Không chạy trang stress test.
- Không reset/seed dữ liệu ngay trước demo.
- Nếu cần khôi phục DB trước buổi demo, dùng backup trong `backend/backups`.

## 5. Thông Điệp Chốt Demo

> "EPL không chỉ quản lý từng màn hình rời rạc. Hệ thống nối toàn bộ chuỗi logistics từ Master Data, báo giá, đơn hàng, giao hàng, POD đến kế toán. Điểm quan trọng nhất là dữ liệu không bị bịa: thiếu dữ liệu thì hệ thống chặn và hướng người dùng cấu hình đúng nơi."
