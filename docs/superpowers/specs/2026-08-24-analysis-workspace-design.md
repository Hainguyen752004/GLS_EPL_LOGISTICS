# Thiết kế Không gian Tóm tắt & Phân tích

## Mục tiêu

Tách Trung tâm Doanh thu và Chi phí Vận tải khỏi trang `Báo cáo & Phân tích`. Tạo một không gian phân tích riêng, dễ xem trên máy tính và điện thoại, dùng dữ liệu thật hiện có và không thay đổi nghiệp vụ backend.

## Điều hướng

- Menu `Tổng quan` giữ chức năng `Tóm tắt & Phân tích`.
- Khi mở chức năng này, thanh chọn góc nhìn nằm ngang ngay dưới header và dùng toàn bộ chiều rộng trên cả desktop lẫn mobile.
- Mục mặc định là `Tổng quan P&L`.
- Các mục trong thanh chọn:
  - `Tổng quan P&L`: KPI doanh thu, chi phí, lợi nhuận, biên lợi nhuận và các biểu đồ.
  - `Bức tranh toàn cảnh`: nội dung tổng hợp hệ thống hiện có của `view-lab-summary`.
  - `Doanh thu theo chuyến`: bảng doanh thu 23 cột và xuất CSV.
  - `Phiếu chi phí`: danh sách, tạo và xem phiếu chi phí.
- Trang `Báo cáo & Phân tích` chỉ còn hai nhóm `SLA/KPI` và `Tender / Carrier`.

## Bố cục

- Header trang chứa tên chức năng, kỳ dữ liệu đang xem và nút tải lại.
- Bộ lọc `Từ ngày`, `Đến ngày`, `Khách hàng`, `Xe` nằm trên vùng nội dung và dùng chung cho các mục tài chính.
- Thanh chọn hiển thị tên góc nhìn hiện tại; hover/focus hoặc bấm sẽ mở bốn lựa chọn và đánh dấu mục đang chọn rõ ràng.
- Khu KPI dùng bốn chỉ tiêu: doanh thu, chi phí, lợi nhuận gộp và biên lợi nhuận.
- Biểu đồ và bảng sử dụng chiều rộng còn lại, không tạo trang cuộn ngang ở cấp toàn màn hình. Chỉ bảng 23 cột được cuộn ngang trong vùng bảng.
- Trên màn hình nhỏ hơn 760px, menu xổ xuống xếp một cột; KPI xếp một cột hoặc hai cột tùy chiều rộng; nút và bộ lọc xuống dòng đầy đủ.

## Tái sử dụng và di chuyển

- Di chuyển nguyên `transport-reporting-center` ra khỏi `view-reporting` và đặt trong không gian `view-lab-summary`.
- Giữ các ID DOM, API và đối tượng `TransportReporting` hiện có để tránh thay đổi hành vi dữ liệu.
- Chuyển ba pane hiện tại thành các mục trong thanh chọn góc nhìn thay vì tab ngang.
- Nội dung `Bức tranh toàn cảnh` hiện có được bọc thành một pane riêng, không sao chép dữ liệu hoặc markup.
- `reporting-folder-tabs` chỉ quản lý SLA/KPI và Tender/Carrier; không quản lý P&L.

## Dữ liệu và trạng thái

- P&L tiếp tục đọc doanh thu từ AR Invoice `Posted` và chi phí từ Actual Cost `Approved`.
- Bộ lọc giữ nguyên khi chuyển giữa `Tổng quan P&L`, `Doanh thu theo chuyến` và `Phiếu chi phí`.
- Khi chuyển sang `Bức tranh toàn cảnh`, dữ liệu tổng hợp hệ thống được tải bằng luồng hiện có.
- Trạng thái đang chọn được giữ trong JavaScript của phiên hiện tại; tải lại trang quay về `Tổng quan P&L`.
- Không thay đổi schema database hoặc hợp đồng API.

## Lỗi và trạng thái rỗng

- Lỗi tải báo cáo hiển thị trong vùng nội dung, không làm mất thanh chọn hoặc bộ lọc.
- Không có dữ liệu phải hiển thị trạng thái rỗng riêng cho KPI, biểu đồ, bảng chuyến và phiếu chi phí.
- Xuất CSV chỉ khả dụng khi có dữ liệu doanh thu theo chuyến.

## Kiểm thử chấp nhận

- `transport-reporting-center` không còn nằm trong `view-reporting`.
- `view-reporting` vẫn chuyển đúng giữa SLA/KPI và Tender/Carrier.
- `Tóm tắt & Phân tích` mở mặc định tại `Tổng quan P&L`.
- Thanh chọn chuyển đúng bốn mục, cập nhật đúng tên mục hiện tại và chỉ hiển thị một pane tại một thời điểm.
- Bộ lọc và tải lại tiếp tục gọi API báo cáo hiện có.
- CSV và phiếu chi phí vẫn hoạt động như trước khi di chuyển.
- Desktop 1366px không bị che nội dung; mobile 390px không có cuộn ngang toàn trang.
- Các bài test frontend và backend hiện có tiếp tục qua; bổ sung test cấu trúc điều hướng mới.
