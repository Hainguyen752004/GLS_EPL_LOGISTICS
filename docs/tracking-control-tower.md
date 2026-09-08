# Theo dõi và kiểm soát

## Giao diện

Mẫu tham chiếu: `nhap_UI__duan/tracking-control-tower.html`.
Màn hình giữ menu của ứng dụng, gồm bộ lọc KPI, danh sách DO theo Trip,
bản đồ và hồ sơ bên phải. Trên màn nhỏ, các vùng chuyển thành một cột.
Tìm kiếm và bộ lọc áp dụng đồng thời cho danh sách và bản đồ.

Một DO có nhiều Trip đang mở xuất hiện thành nhiều dòng để không gộp nhầm xe.
Số xe là số mã xe khác nhau; số dòng là số phân bổ DO/Trip, không phải số xe.

## API

`GET /api/tracking/control-tower`

Yêu cầu xác thực theo cơ chế chung của ứng dụng. API chỉ đọc, không đổi trạng
thái chuyến hoặc tạo GPS. Không cần migration hay bảng mới.

- `generated_at`: thời gian máy chủ tạo kết quả, UTC có múi giờ.
- `gps_stale_after_seconds`: ngưỡng GPS cũ, hiện là 900 giây.
- `items`: DO đang vận chuyển/đã đến, hoặc DO còn Trip đã điều phối/đang chạy.
  DO bị hủy bị loại; DO đã giao nhưng Trip chưa kết thúc vẫn được giữ.
- Mỗi dòng chứa DO, Trip, xe, tổ lái, khách, tuyến, hạn giao, chặng, sự kiện,
  sự cố theo DO/xe và POD theo đúng Trip. Chứng từ chỉ trả metadata, không
  tải nội dung nhị phân vào bảng tổng hợp.
- `gps.status`: `fresh`, `stale`, `missing`. Ưu tiên vị trí có sự kiện gắn
  đúng Trip. Vị trí cũ cấp DO chỉ dùng khi không mơ hồ giữa nhiều Trip, đúng
  xe và không có mốc trước giờ xuất phát thực tế.
- `predicted_eta`, `deviation_km`: chưa có nguồn dự báo/thuật toán được xác
  thực nên trả `null`. Không dùng giờ kế hoạch như ETA GPS.
- `kpis`: tổng số dòng, số xe, quá hạn, GPS thiếu/cũ, chờ POD, có sự cố mở,
  đã giao nhưng Trip còn mở.

`POST /api/incidents`: form dùng API hiện có. Bắt buộc DO, xe, loại sự cố,
vị trí, người báo cáo. Kiểm tra DO/xe tồn tại và xe thuộc điều phối của DO.
Lỗi không đóng form và không xóa nội dung đã nhập.

`GET /api/pod-documents/{id}`: tải chứng từ POD qua fetch có cơ chế xác thực
chung, sau đó tải tệp bằng blob. Không hiển thị HTML từ tên tệp/người nhận.

## Ý nghĩa dữ liệu

- Tiến độ là số chặng đã hoàn tất, không giả làm phần trăm km đã đi.
- Giờ đến kế hoạch và tổng tuyến kế hoạch được ghi nhãn riêng.
- Quá hạn nghĩa là quá hạn giao trên DO nhưng chưa ghi nhận giao hoàn tất.
- Bản đồ chỉ vẽ tọa độ hợp lệ; tọa độ rỗng không biến thành `0,0`.
- Tuyến nét đứt nối điểm tham chiếu, không phải đường GPS đã thực hiện.
- Thiếu GPS không đồng nghĩa xe đã dừng; tốc độ bằng 0 chỉ hiển thị khi có
  vị trí kèm dữ liệu nguồn. Tốc độ trên GPS cũ được ghi là lần cuối.
- Báo sự cố chưa tự gửi tin nhắn cho khách hoặc tự điều chỉnh ETA.
- Nền đường phố dùng OpenStreetMap; khi lỗi tải, chuyển sang Esri World Imagery
  kèm thông báo. Người dùng có thể đổi nền bằng bộ chọn. Các nguồn này cần
  Internet; lỗi tải nền được báo riêng với lỗi API.

## Kiểm thử

1. Mở Vận hành → Theo dõi và kiểm soát; đối chiếu các mã DO/Trip với Điều phối.
2. Bấm từng KPI, tìm theo DO/xe/tài xế; danh sách và bản đồ phải cùng bộ lọc.
3. Chọn hai chuyến liên tiếp; hồ sơ và sự kiện không được giữ dữ liệu chuyến cũ.
4. Chuyến thiếu GPS vẫn hiện trong danh sách, không có marker xe giả.
5. GPS quá 15 phút có nhãn cũ; vị trí mới từ sự kiện Trip dùng đúng xe/chuyến.
6. Chọn Tuyến đang chọn; đường kế hoạch không mang nhãn lệch tuyến/đã đi.
7. Mở Báo sự cố, điền đủ dữ liệu và gửi trên dữ liệu thử; tải lại để xác nhận
   bản ghi tồn tại. Khi API trả lỗi, form phải giữ nguyên dữ liệu.
8. Chuyến có POD phải có thông tin người nhận và nút tải tệp được lưu thật.
9. Bật tự cập nhật, chuyển sang màn khác; không tiếp tục thăm dò khi màn ẩn.
10. Kiểm tra ở 390px, 1280px và 1600px: không tràn ngang bên trong module.

Kiểm thử tự động: `backend/tests/test_tracking_control_tower.py`,
`frontend/tests/tracking-control-tower.test.js`.
