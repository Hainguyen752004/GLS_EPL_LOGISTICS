# Biểu thức công thức giá thành

Trên màn Công thức giá thành, nút Sửa công thức mở trình soạn nội tuyến. Ba biểu thức gồm `COST` (giá thành), `REV` (cước thu khách) và `PROFIT` (lợi nhuận). Áp dụng cập nhật bản nháp; nút Lưu cấu hình ghi dữ liệu vào cơ sở dữ liệu.

Biểu thức hỗ trợ số, tên cấu phần, `+ - * /`, dấu ngoặc, `min`, `max`, `abs`. Các biến chuyến gồm `km`, `kg`, `tonnes`, `legs`, `stops`, `value`. Không thực thi mã người dùng. Tham chiếu vòng, biến không tồn tại, chia cho 0 và kết quả vượt giới hạn đều bị từ chối.

Ví dụ cước tối thiểu: `max(rate * kg, 2500000)`.

## API

- `POST /api/cost-formulas`: lưu `vehicle_type_id`, `currency`, `terms`, `expressions`. `expressions` phải gồm đủ ba khóa `COST`, `REV`, `PROFIT`. Backend kiểm tra trước khi ghi. Lỗi trả HTTP 422 và giữ nguyên dữ liệu đã lưu.
- `GET /api/cost-formulas`: trả danh sách công thức, bao gồm `expressions`, `updated_at`, `history`.
- `POST /api/cost-formulas/evaluate`: nhận `formula_id` của công thức đã lưu và `trip`, hoặc nhận trực tiếp `terms`, `expressions`, `trip` để kiểm tra. Trả `data.cost`, `data.revenue`, `data.profit`, `data.perKm`, `data.marginPct`. Không ghi dữ liệu.

Các endpoint ghi/đánh giá sử dụng xác thực hiện có của ứng dụng.

## Lưu trữ

Các trường mới nằm trong JSON `cost_formulas.formula_expression`, sử dụng cơ sở dữ liệu hiện hành của dự án. Không tạo database khác. Công thức cũ chưa có `expressions` vẫn dùng mô hình cấu phần. Lịch sử giữ tối đa 100 lần lưu từ khi tính năng được bổ sung; không dựng lịch sử cho dữ liệu cũ.

## Kiểm thử

1. Chọn loại xe và mở Sửa công thức. Trình soạn xuất hiện dưới bảng, không mở modal.
2. Chọn Cước, nhập `max(rate * kg, 2500000)`, Áp dụng. Đặt hàng bằng 0: cước vẫn là 2.500.000.
3. Nhập `fuel / 0`: hiện lỗi và nút Áp dụng bị khóa.
4. Sửa rồi Hủy: biểu thức đã áp dụng không đổi.
5. Lưu cấu hình và tải lại: biểu thức vẫn còn, lịch sử ghi lần lưu.
6. Chọn loại xe khác: không mang công thức của loại trước sang.
7. Tạo báo giá dùng loại xe đã lưu: dùng km tuyến và tải trọng thật. Biểu thức đòi số chặng/giá trị hàng mà dữ liệu còn thiếu sẽ chặn tính giá.
# Kiểm tra ghi đồng thời

## So sánh xe và lịch sử ghi đè

`GET /api/cost-formulas/fleet-overview` yêu cầu đăng nhập, trả `data.vehicles` (cấu phần/biểu thức hiệu lực theo xe) và `data.history` (100 thao tác ghi đè gần nhất). Dữ liệu được đọc theo lô, không gọi API riêng cho từng xe. Giao diện tính cùng chuyến mẫu cho tất cả hàng so sánh, chỉ so cùng tiền tệ; công thức chưa hợp lệ không được giả thành giá 0.

Thao tác lưu giá riêng ghi lịch sử vào `audit_logs` trong cùng giao dịch với giá xe. Lịch sử gồm xe, cấu phần, giá ghi đè trước/sau, lý do, người sửa và thời gian. Dữ liệu có từ trước thay đổi này không có lịch sử chi tiết hồi tố; giao diện không dựng lịch sử giả.

Ở màn xe, nút `Thêm cấu phần vào loại xe` chuyển tới công thức chuẩn và mở form thêm cấu phần. Nó không tự thêm chi phí chỉ dành cho một xe và không tự ghi database. Mô hình cấu phần riêng cho một chiếc vẫn cần xác nhận phạm vi.

Giao diện gửi `expected_updated_at` từ lần tải gần nhất khi lưu công thức. Nếu bộ giá đã được sửa ở phiên khác, API trả HTTP 409 và giữ nguyên dữ liệu server; giao diện giữ bản nháp. Lệnh UPDATE còn so sánh nguyên tài liệu cũ để chặn hai yêu cầu ghi đồng thời. Trường này là tùy chọn cho client cũ; các client tích hợp cần bổ sung để được bảo vệ trước dữ liệu đã cũ từ lúc mở form.

Lịch sử lưu mới có trường `actor`. Đây là kiểm tra xung đột và lịch sử thao tác, **chưa phải** bộ giá theo ngày hiệu lực hoặc snapshot bất biến của chứng từ.
