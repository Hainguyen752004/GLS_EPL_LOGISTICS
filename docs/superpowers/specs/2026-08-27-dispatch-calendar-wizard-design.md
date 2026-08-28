# Dispatch Calendar Wizard

## Mục tiêu

Làm rõ luồng điều phối theo thứ tự: chọn ngày lấy hàng, chọn DO của ngày, chọn xe phù hợp, chọn nhân sự trong ca, kiểm tra xung đột rồi chốt xuất bến.

## Luồng giao diện

1. Màn hình mở ở bước `Chọn ngày & DO`.
2. Ngày được chọn lọc các DO `Chờ điều phối` theo ngày địa phương của `pickup_window_start`, dùng múi giờ `Asia/Bangkok`. Cửa sổ qua đêm vẫn thuộc ngày bắt đầu lấy hàng. DO thiếu ngày lấy hàng nằm trong nhóm cảnh báo riêng, không tự gán vào ngày bất kỳ.
3. Danh sách DO dùng combobox/thẻ giàu thông tin thay cho `<select>` thuần. Mỗi mục hiển thị mã, khách hàng, tuyến, hàng hóa, tải trọng, pallet, giờ lấy/giao và nhãn `Đã có Trip` hoặc `Chưa có Trip`; rê chuột, focus bàn phím hoặc chạm sẽ mở mô tả chi tiết.
4. Chọn DO mới mở wizard toàn màn hình. Không hiển thị sẵn khối chi tiết khi chưa chọn DO.
5. DO bắt buộc có Trip trước khi điều phối. Nếu chưa có Trip, wizard mở form `Tạo Trip từ DO/FO`, điền sẵn DO, FO, Route, checkpoint và cửa sổ thời gian; lưu thành công mới mở bước chọn xe. Chỉ Trip `planned` được chọn để điều phối. Nếu DO có đúng một Trip `planned`, hệ thống chọn Trip đó; nếu có nhiều Trip `planned`, người dùng bắt buộc chọn một Trip; Trip `draft` có nút mở để hoàn tất kế hoạch, còn Trip đã dispatch/in-transit/completed/cancelled không được dùng lại. Nếu Trip chứa nhiều DO, wizard hiển thị toàn bộ DO liên kết và tính tải tổng của Trip.
6. Bước `Chọn xe` hiển thị thông tin Trip/DO và các xe đạt tải trọng, pallet, thể tích, pháp lý, bảo dưỡng và không trùng lịch trong toàn bộ khoảng chuyến.
7. Bước `Nhân sự & xuất bến` chỉ hiển thị tài xế/phụ xe đúng vai trò, có lịch làm việc bao phủ khoảng chuyến, không nghỉ/ốm và không trùng phân công.
8. Form chốt gồm: mã Trip/DO, khách hàng, tuyến và checkpoint, cửa sổ lấy/giao, tải trọng/pallet/thể tích, xe, tài xế chính, phụ xe, quy cách đóng gói, cảnh báo và nút chốt.
9. Bỏ các khối `Đổi xe`, `Đổi tài xế`, `Mở Shipment 360°`, `Mở điều phối` khỏi form tạo phân công.

## Vai trò Master Data

- Lịch ca là kế hoạch khả dụng của con người: làm ca nào, nghỉ phép, nghỉ bệnh hoặc không sẵn sàng.
- Xe gán mặc định cho tài xế chỉ là gợi ý, không khóa cứng xe với người đó.
- Điều phối là giao dịch vận hành thật: gán DO + xe + tài xế + phụ xe trong một khoảng thời gian.
- Khi chốt, hệ thống tạo/cập nhật `ResourceAssignment`; lịch xe và lịch nhân sự được suy ra từ bản ghi này cùng Trip, không sao chép hoặc biến ca làm việc thành chuyến.

## Khóa lịch

- Bắt đầu khóa theo `planned_departure` của Trip; nếu Trip chưa có giá trị này thì dùng `pickup_window_start`. Thời điểm bắt đầu phải nằm trong cửa sổ lấy hàng của DO.
- Kết thúc khóa dự kiến là thời điểm muộn nhất trong: `assignment_end` người dùng xác nhận, `Trip.planned_arrival_at`, `Trip.planned_return_at` và `planned_arrival_at` của chặng cuối. Chặng backhaul/empty return đã cấu hình luôn được tính vào khoảng khóa.
- Hoàn tất thực tế dùng `actual_return_at` nếu Trip có chặng về; với Trip một chiều dùng `actual_arrival_at`. Nếu chưa có thời gian thực tế thì giữ thời điểm khóa dự kiến.
- Trong phạm vi vòng này, Trip chưa có chặng về không được tự động ghép chuyến kế tiếp dựa trên địa chỉ tự do. Hệ thống yêu cầu tạo backhaul/empty return; việc ghép theo checkpoint/vị trí chính xác được chuyển sang thiết kế Trip kế tiếp.
- Không cho chốt khi xe, tài xế hoặc phụ xe trùng bất kỳ phần nào của khoảng thời gian khóa.
- Hai khoảng liền nhau được phép khi `kết thúc chuyến trước == bắt đầu chuyến sau`; mọi giao nhau có thời lượng đều bị chặn.
- Tài xế chính và phụ xe đều phải được bao phủ toàn bộ khoảng khóa bởi một ca hoặc nhiều ca làm việc liên tiếp; bất kỳ lịch nghỉ/ốm giao nhau đều ưu tiên chặn.
- Sau hoàn tất giao hàng/chặng về, trạng thái và lịch được tính lại từ dữ liệu Trip, `ResourceAssignment` và bảo dưỡng; không sửa tay. Hoàn tất sớm rút ngắn khóa theo giờ thực tế, hủy chuyến giải phóng khóa sau khi giao dịch hủy thành công.
- API chốt phải kiểm tra lại nguyên tử tải trọng, pháp lý, bảo dưỡng, ca, nghỉ và trùng lịch. Giao dịch khóa hàng Trip, Freight Order, xe, tài xế chính và phụ xe bằng `SELECT ... FOR UPDATE` theo thứ tự cố định trước khi kiểm tra/chèn `ResourceAssignment`; hai yêu cầu cùng nguồn lực vì vậy được tuần tự hóa. Nếu dữ liệu thay đổi trong lúc wizard đang mở, trả xung đột và giữ nguyên nội dung form để người dùng chọn lại.
- Nút chốt chống bấm lặp; cùng khóa yêu cầu không được tạo hai phân công.

## Phạm vi vòng này

- Sửa UI/UX Điều phối và logic lọc/khóa nguồn lực liên quan.
- Giữ nguyên thanh quy trình dọc.
- Chưa thiết kế lại màn hình Trip; Trip sẽ là vòng tiếp theo.

## Kiểm thử tối thiểu

- Đổi ngày làm thay đổi đúng danh sách DO.
- DO thiếu ngày không xuất hiện sai ngày.
- Chọn DO mới mở wizard; DO chưa có Trip mở bước tạo Trip, DO đã có Trip đi tiếp.
- Trip nhiều DO hiển thị đủ DO và dùng tải tổng.
- Xe không đủ tải hoặc trùng lịch không thể chọn.
- Nhân sự ngoài ca, nghỉ hoặc trùng lịch không thể chọn.
- Chốt thành công tạo phân công và cập nhật lịch xe/nhân sự.
- Tải lại trang vẫn giữ phân công và khoảng khóa.
- Kiểm tra cửa sổ qua đêm, hai khoảng liền nhau, bảo dưỡng giao nhau, hủy/hoàn tất sớm, hai yêu cầu chốt đồng thời và thao tác bấm lặp.
