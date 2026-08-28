# Dispatch Week Calendar Design

## Mục tiêu

Tách màn hình điều phối thành hai lớp: TKB tuần để quan sát và chọn ngày; form theo ngày để xử lý DO, Trip, xe và nhân sự.

## Luồng

1. TKB tuần từ Thứ 2 đến Chủ nhật hiển thị số DO cần xếp, xe rảnh, xe bận, bảo dưỡng và xung đột.
2. DO được nhóm theo ngày lấy hàng. DO thiếu ngày nằm trong cảnh báo `Chưa có lịch`.
3. Bấm một ngày mở form riêng gồm danh sách DO của ngày bên trái và vùng xử lý bên phải.
4. DO chưa có Trip mở form tạo Trip đã điền sẵn DO và tuyến.
5. Trip nháp mở hồ sơ Trip hiện có; Trip đã lập kế hoạch mở cấu hình xe, tài xế, phụ xe và xuất bến.
6. Xe/tài xế được lọc bằng lịch Trip, bảo dưỡng, ca làm và nghỉ phép trong Master Data. Điều phối thành công cập nhật lại các lịch này.

## UI

- Không hiển thị danh sách xe hoặc nút `Chọn xe phù hợp` trên TKB chính.
- TKB tuần dùng toàn bộ chiều ngang.
- Mỗi ô ngày có số DO cần xếp và mức độ khẩn theo ngày lấy hàng.
- Form theo ngày dùng bố cục hai cột và có thể đóng để quay lại TKB.

