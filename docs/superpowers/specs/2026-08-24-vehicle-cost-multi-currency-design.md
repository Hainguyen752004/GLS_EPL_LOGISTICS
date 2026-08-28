# Thiết kế cấu hình giá thành theo loại xe và tiền tệ

## Mục tiêu

Cho phép mỗi loại xe có một bộ cấu hình giá độc lập cho từng đồng tiền `VND`, `USD`, `THB` và `LAK`. Việc đổi tiền tệ chỉ chuyển bộ cấu hình đang xem; hệ thống không tự quy đổi và không ghi đè dữ liệu của đồng tiền khác.

## Mô hình dữ liệu

- Mỗi công thức được nhận diện bởi cặp `vehicle_type_id + currency`.
- ID lưu trữ ổn định có dạng `vehicle-type::<vehicle_type_id>::<currency>`.
- Một cặp chỉ có tối đa một công thức đang hoạt động. Backend tự tạo ID chuẩn từ cặp này và upsert theo chính khóa đó, vì vậy hai yêu cầu đồng thời không thể tạo hai bản ghi; nếu cùng cập nhật một cặp thì lần commit thành công sau cùng là dữ liệu hiện hành.
- Cấu hình cũ có `vehicle_type_id` nhưng chưa có ID chuẩn được xem là ứng viên VND. Nếu đã có cả bản chuẩn VND và bản legacy, bản chuẩn luôn thắng. Bản legacy không bị xóa tự động và bị bỏ qua; lần lưu tiếp theo chỉ upsert bản chuẩn để không làm hỏng dữ liệu hay tham chiếu cũ.
- API trả `configured: true` khi bản ghi chuẩn hoặc legacy hợp lệ thực sự tồn tại. Bộ chưa cấu hình có `configured: false`, các ô nhập ban đầu hiển thị `0`; vì vậy giá trị hợp lệ bằng `0` vẫn phân biệt được với chưa cấu hình.
- Các giá trị của đồng tiền này không được dùng làm mặc định cho đồng tiền khác.

## Hành vi giao diện

- Loại xe đang chọn và tiền tệ đang chọn cùng xác định bộ dữ liệu trên form.
- Đổi loại xe hoặc đổi tiền tệ sẽ tải đúng bộ cấu hình tương ứng.
- Sau khi người dùng sửa thành phần chi phí hoặc công thức, form được đánh dấu chưa lưu.
- Nếu đổi loại xe hoặc tiền tệ khi form chưa lưu, hệ thống mở hộp thoại với ba lệnh:
  - `Lưu thay đổi và chuyển`: lưu bộ hiện tại; chỉ chuyển khi API lưu thành công.
  - `Bỏ thay đổi`: bỏ bản nháp và chuyển sang bộ được chọn.
  - `Ở lại`: đóng cảnh báo và giữ nguyên form.
- Nếu API lưu lỗi, form giữ nguyên dữ liệu, giữ trạng thái chưa lưu và không chuyển loại xe/tiền tệ.
- Nhãn tiền tệ ở tiêu đề, hậu tố từng dòng và phần xem trước phải luôn đồng bộ với bộ cấu hình đang chọn.
- Thẻ loại xe có thể hiển thị giá định mức của đúng đồng tiền đang chọn; loại xe chưa cấu hình ở đồng tiền đó hiển thị `Chưa cấu hình`.
- Số tiền được nhập theo locale giao diện nhưng được chuẩn hóa trước khi gửi. API dùng chuỗi decimal chuẩn với dấu chấm làm phần thập phân, không có dấu phân cách hàng nghìn; backend xác thực bằng `Decimal`, tối đa 18 chữ số toàn phần. Scale là `VND: 0`, `LAK: 0`, `USD: 2`, `THB: 2`; phần lẻ vượt scale bị từ chối, không tự làm tròn. Backend cũng từ chối số âm, NaN và ký tự lạ. Giao diện định dạng lại theo locale và đúng scale này.

## Hợp đồng API

- `POST /api/cost-formulas` nhận `vehicle_type_id`, `currency`, các thành phần chi phí và tokens.
- Backend chuẩn hóa currency thành chữ hoa và chỉ chấp nhận `VND`, `USD`, `THB`, `LAK`.
- Backend tự tạo khóa chuẩn từ `vehicle_type_id + currency`; không tin ID tùy ý từ frontend khi đã có đủ hai trường này.
- `GET /api/cost-formulas` trả riêng từng bộ với đầy đủ `vehicle_type_id`, `currency` và `configured`.
- Dữ liệu legacy không có khóa tiền tệ chuẩn tiếp tục được đọc như VND; lần lưu kế tiếp chuyển sang khóa chuẩn mà không xóa dữ liệu ngoài phạm vi.

## Sử dụng trong vận hành và closeout

- Công thức chi phí được chọn theo `DeliveryOrder.vehicle_id` đã được Dispatch ghi nhận. Backend đọc `Vehicle.type`, ưu tiên khớp trực tiếp `VehicleType.id`, sau đó mới khớp chính xác tên loại xe để lấy `vehicle_type_id`. Fallback theo tên chỉ hợp lệ khi tìm thấy đúng một bản ghi; không có hoặc có nhiều tên trùng đều dừng bằng `VEHICLE_TYPE_REQUIRED`.
- Tiền tệ bắt buộc lấy từ `SalesOrder.currency_code` của SO nguồn gắn với Delivery Order. DO không có SO, SO thiếu tiền tệ hoặc tiền tệ ngoài danh sách được phép phải dừng bằng lỗi `COST_CURRENCY_REQUIRED`; không fallback sang tiền tệ khác.
- Nếu Actual Cost/Closeout đã tồn tại nhưng khác tiền tệ SO, hệ thống dừng bằng `COST_CURRENCY_CONFLICT` và không sửa bản ghi hiện hữu.
- Hệ thống chỉ dùng công thức khớp chính xác cả `vehicle_type_id` và `currency`.
- Nếu không có bộ phù hợp, endpoint trả HTTP `409` với mã nghiệp vụ `COST_FORMULA_REQUIRED`, kèm loại xe và tiền tệ bị thiếu. Closeout dừng hoàn toàn, rollback transaction và không tạo Actual Cost, dòng chi phí, closeout hay trạng thái một phần.
- Actual Cost và các dòng chi phí được tạo cùng tiền tệ của công thức đã chọn.

## Tính nhất quán và lỗi

- Không chuyển màn hình trước khi thao tác `Lưu thay đổi và chuyển` nhận phản hồi thành công.
- Hai lần lưu cùng cặp loại xe/tiền tệ phải có tính idempotent và không tăng số bản ghi.
- Không cho một công thức của loại xe khác hoặc đồng tiền khác tham gia closeout chỉ vì tên gần giống.
- Thông báo lỗi phải nêu rõ loại xe và tiền tệ còn thiếu cấu hình.

## Kiểm thử chấp nhận

- Lưu `Container 20FT + VND = 6250`, `Container 20FT + LAK = 12000`, `Container 20FT + USD = 0.30` và `Container 20FT + THB = 10.50`; chuyển qua lại vẫn đọc đúng từng giá trị và không tự quy đổi.
- VND/LAK có phần lẻ, USD/THB có hơn hai chữ số lẻ, số âm, NaN hoặc quá 18 chữ số phải bị từ chối và không thay đổi dữ liệu cũ.
- Lưu `Xe tải thùng 10 tấn + LAK` không làm thay đổi `Container 20FT + LAK`.
- Tải lại trang vẫn giữ đủ các bộ cấu hình độc lập.
- Sửa VND nhưng chưa lưu rồi chọn LAK phải xuất hiện đủ ba lựa chọn cảnh báo.
- Chọn `Ở lại` giữ nguyên bản nháp; chọn `Bỏ thay đổi` tải LAK; chọn `Lưu thay đổi và chuyển` lưu VND rồi mới tải LAK.
- Chuyển loại xe khi form dirty cũng phải kiểm tra đủ ba lựa chọn trên.
- API lỗi trong lúc lưu phải giữ nguyên form và không chuyển tiền tệ.
- Hai lần lưu và hai yêu cầu lưu đồng thời cùng cặp không tạo bản ghi trùng.
- Khi đồng thời tồn tại legacy VND và bản VND chuẩn, GET và closeout phải chọn bản chuẩn; dữ liệu legacy vẫn còn nguyên.
- Bộ có tất cả giá trị bằng `0` phải có `configured: true`; bộ chưa từng lưu phải có `configured: false`.
- Closeout của DO dùng SO tiền tệ LAK phải chọn đúng công thức LAK của loại xe đã điều phối.
- Thiếu công thức LAK phải trả HTTP 409/`COST_FORMULA_REQUIRED`, không dùng VND thay thế và không để lại dữ liệu một phần.
- Nếu chỉ có công thức LAK của loại xe khác, closeout vẫn phải trả `COST_FORMULA_REQUIRED`.
- Nếu `Vehicle.type` không phải ID và trùng tên với nhiều VehicleType, closeout phải trả `VEHICLE_TYPE_REQUIRED` thay vì tự chọn một bản ghi.
- Closeout phải bị chặn khi thiếu xe/loại xe, SO thiếu hoặc có tiền tệ không hợp lệ, hoặc Actual Cost hiện hữu khác tiền tệ SO.
- Kiểm thử hồi quy đảm bảo cấu hình theo loại xe hiện tại, hoàn tất giao hàng và báo cáo tài chính vẫn hoạt động.

## Không thuộc phạm vi

- Không tự động quy đổi giá cấu hình theo tỷ giá.
- Không thêm đồng tiền ngoài bốn mã hiện có trong thay đổi này.
- Không thay đổi quy trình phê duyệt tỷ giá hoặc cách ghi nhận doanh thu.
