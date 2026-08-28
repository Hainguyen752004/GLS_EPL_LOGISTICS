# Thiết kế module Hoàn tất giao hàng và màn Tracking theo DO

Ngày: 2026-08-22

## Mục tiêu

Tách nghiệp vụ hoàn tất giao hàng ra khỏi màn GPS/POD hiện tại để người dùng thao tác theo đúng trình tự:

1. DO có giá ban đầu từ SO và được điều xe.
2. Trong lúc vận chuyển, người dùng chọn DO để theo dõi vị trí xe.
3. Khi xe đã giao thực tế, người dùng mở module Hoàn tất giao hàng.
4. Người dùng nộp POD, nhập khoản khách hàng phải trả thêm và xem giá bán cuối cùng.
5. Hệ thống lưu dữ liệu backend, chuyển DO sang Delivered và mở hồ sơ closeout.

## Phạm vi giao diện

### Module mới: Hoàn tất giao hàng

Thêm một mục cấp phân hệ trên thanh điều hướng chính, đặt gần Điều phối & Thực thi và Theo dõi & Kiểm soát.

Màn đầu tiên là bảng DO chờ hoàn tất. Bảng hiển thị DO đang vận chuyển có Trip và phân công nguồn lực hợp lệ. Trạng thái này chỉ cho phép mở hồ sơ; DO chỉ được hoàn tất khi payload có POD hợp lệ cho toàn bộ chặng giao còn lại. Bảng có các cột:

- Mã DO và trạng thái.
- Xe và tài xế.
- Khách nhận và điểm giao.
- Giá SO ban đầu lấy từ `SalesOrder.total_amount`; dữ liệu cũ thiếu giá SO mới fallback sang giá bán của Quotation.
- Hai thao tác: Xem DO và Hoàn tất giao.

Xem DO mở thông tin gốc ở chế độ chỉ đọc. Hoàn tất giao mở form toàn màn hình của đúng DO.

### Form Hoàn tất giao

Phần đầu form hiển thị dữ liệu tham chiếu, không cho sửa:

- Mã DO.
- SO nguồn.
- Xe và tài xế.
- Tuyến và điểm giao.
- Giá ban đầu và đơn vị tiền tệ.

Nội dung form chia hai cột trên desktop và xếp dọc trên mobile.

Cột POD gồm:

- Thời gian giao thực tế.
- Kết quả giao hàng.
- Tên người nhận.
- Số điện thoại người nhận.
- File biên bản, chữ ký hoặc ảnh POD.
- Tình trạng hàng hóa và ghi chú.

Cột quyết toán giá bán gồm bảng nhiều dòng khoản khách hàng phải trả thêm:

- Tên khoản phát sinh.
- Giá ban đầu của khoản, mặc định bằng 0 với khoản phát sinh mới.
- Giá thực tế khách hàng phải trả cho khoản đó.
- Số tiền tăng thêm, được tính bằng giá thực tế trừ giá ban đầu của dòng.
- Ghi chú nếu backend hỗ trợ trên dòng chi phí.
- Nút xóa từng dòng.
- Nút thêm khoản phí.

Cuối bảng hiển thị ba tổng số:

- Giá SO ban đầu (`base_selling_price_snapshot`), không phải tổng `original_amount` của các dòng phát sinh.
- Tổng khoản khách hàng phải trả thêm.
- Giá bán cuối cùng khách hàng phải trả.

Giá SO ban đầu chỉ đọc. Giá bán cuối cùng được tính bằng giá SO ban đầu cộng tổng các số tiền tăng thêm và cập nhật ngay khi người dùng thay đổi dòng. Mọi giá trị được lưu bằng đơn vị tiền tệ của SO, lượng tử hóa theo cấu hình tiền tệ backend; không quy đổi hoặc trộn nhiều tiền tệ trong một hồ sơ.

Nút chính là Hoàn tất giao hàng & chốt giá. Nút phụ là Quay lại danh sách.

## Màn Theo dõi & Kiểm soát

Màn GPS/POD cũ được đổi thành màn theo dõi vận chuyển. Loại bỏ card POD và vùng closeout khỏi màn này.

Tab GPS Live theo DO có bố cục master-detail:

- Bên trái là danh sách và ô tìm kiếm DO đang vận chuyển.
- Mỗi DO hiển thị mã, xe, tài xế, tuyến và trạng thái.
- Bên phải là thông tin DO được chọn, bản đồ GPS, tốc độ, khoảng cách còn lại, ETA, thời gian cập nhật cuối và cảnh báo lệch tuyến.
- Chỉ DO có `canonical_status == "in_transit"` mới được đưa vào danh sách tracking. Không suy diễn từ nhãn hiển thị và không đưa `pending`, `delivered`, `completed` hoặc `cancelled` vào danh sách.

Hai nhóm Sự cố và Chuỗi sự kiện được giữ nguyên hành vi, dữ liệu, API và nội dung hiện tại. Chỉ điều chỉnh bao ngoài nếu cần để đồng bộ bố cục, không thay đổi nghiệp vụ.

## Mô hình dữ liệu thương mại

Khoản khách hàng trả thêm không được lưu vào FreightActualCost. Actual cost là chi phí nội bộ của chuyến và vẫn thuộc phân hệ tài chính.

Thêm hồ sơ thương mại sau giao gồm hai bảng:

- `delivery_order_closeouts`: một bản ghi hoàn tất cho mỗi DO, lưu `base_selling_price_snapshot`, `base_price_source`, `base_price_source_id`, `surcharge_total`, `final_selling_price`, `currency_code`, người và thời gian hoàn tất.
- `delivery_order_charge_adjustments`: nhiều dòng thuộc closeout, lưu tên khoản, `original_amount`, `actual_amount`, `increase_amount`, ghi chú và thứ tự hiển thị.
- `delivery_pod_documents`: file POD thật lưu trong cùng database transaction, gồm nội dung binary tối đa 10 MB, tên file, MIME type, kích thước, checksum, người và thời gian tạo. `DeliveryPODRecord` tham chiếu document và trả URL tải qua API có kiểm soát.

`increase_amount = actual_amount - original_amount` và không được âm. `surcharge_total` là tổng `increase_amount`. `final_selling_price = base_selling_price_snapshot + surcharge_total`.

API hoàn tất dùng semantics thay thế toàn bộ danh sách dòng trong transaction đang tạo closeout. Dòng bị xóa trên form không xuất hiện trong payload và không được lưu. Không có chức năng lưu draft ở phạm vi này; dữ liệu chưa submit chỉ nằm trên form. Hồ sơ đã hoàn tất chỉ được xem; việc sửa sau đó cần một luồng điều chỉnh/đảo riêng, ngoài phạm vi thay đổi này.

Giá ban đầu lấy duy nhất từ `SalesOrder.total_amount`; nếu dữ liệu cũ thiếu giá SO thì fallback sang `Quotation.selling_price`. Backend lưu `base_price_source` và `base_price_source_id` cùng snapshot, đồng thời trả các trường này trong response. Closeout giữ snapshot để giá gốc không thay đổi nếu master data hoặc báo giá được sửa về sau.

Closeout API trả đồng thời:

- Giá SO ban đầu, tổng khách hàng trả thêm và giá bán cuối.
- Actual cost nội bộ hiện có nếu đã được lập riêng.
- Margin sau giao bằng giá bán cuối trừ actual cost nội bộ; nếu chưa có actual cost thì margin được đánh dấu tạm tính.

Hóa đơn AR tạo sau giao phải lấy `final_selling_price`, không lấy lại `SalesOrder.total_amount`.

## Luồng dữ liệu và trạng thái

Khi mở module Hoàn tất giao hàng, frontend dùng danh sách DO thật đã tải từ backend và lọc theo trạng thái đủ điều kiện.

Khi chọn Hoàn tất giao:

1. Frontend xác định đúng DO, Trip và SO nguồn.
2. Frontend tải dữ liệu closeout preview để lấy giá SO ban đầu, nguồn giá và tiền tệ. Nếu DO đã có closeout hoàn tất, giao diện chuyển sang chỉ đọc thay vì mở form mới.
3. Form hiển thị dữ liệu gốc ở chế độ chỉ đọc.
4. Người dùng nhập POD và các dòng phát sinh.
5. Frontend kiểm tra đủ trường bắt buộc trước khi gọi API.
6. Frontend gửi một lệnh hoàn tất duy nhất dạng `multipart/form-data` tới `POST /api/delivery-orders/{do_id}/complete-delivery` với header `Idempotency-Key`. Một phần JSON chứa dữ liệu nghiệp vụ và các phần file chứa chứng từ POD.
7. Backend khóa DO, Trip, chặng, phân công và closeout trong cùng transaction; kiểm tra lineage, trạng thái `in_transit`, POD bắt buộc và tiền tệ.
8. Backend lưu file POD binary và checksum trong database, lưu POD, lưu toàn bộ dòng khách hàng trả thêm, tính giá bán cuối, hoàn tất các chặng thuộc DO và chuyển DO sang Delivered khi tất cả chặng bắt buộc của DO đã đủ POD.
9. Backend chỉ chuyển Trip sang completed khi toàn bộ chặng không bị hủy của Trip đã completed và toàn bộ DO gắn với Trip đã Delivered. Các DO khác trên cùng Trip không bị thay đổi bởi lần hoàn tất này.
10. Backend tạo hoặc cập nhật hóa đơn AR của DO từ giá bán cuối.
11. Nếu bất kỳ bước nào lỗi, transaction rollback cả file, POD, giá và trạng thái. Bản ghi idempotency chỉ được commit cùng transaction thành công, vì vậy cùng key có thể retry sau lỗi rollback. Sau thành công, gửi lại cùng key và cùng payload trả kết quả đã cache; cùng key nhưng payload khác trả lỗi xung đột.
12. Backend trả response closeout hoàn chỉnh; frontend render trực tiếp và có thể tải lại bằng `GET /api/delivery-orders/{do_id}/closeout`.

Payload JSON hoàn tất gồm `trip_id`, thông tin POD gắn với `leg_id`, `vehicle_id`, `stop_no`, địa điểm, người nhận, điện thoại, thời gian giao, ghi chú, tiền tệ và mảng `charge_adjustments`. File POD được gửi ở phần multipart tương ứng với từng `leg_id`. Với DO nhiều điểm giao, payload phải có POD cho từng chặng giao chưa hoàn tất; backend chỉ chuyển Delivered khi tất cả chặng bắt buộc đã đủ POD.

Nút hoàn tất phải chống bấm lặp trong lúc xử lý. Nếu backend lỗi, form vẫn giữ dữ liệu người dùng, nút được mở lại và thông báo hiển thị mã lỗi cùng bước kiểm tra cần làm. Không hiển thị thành công trước khi endpoint aggregate trả closeout thành công.

Luồng POD độc lập `POST /api/pod/{do_id}`, trạng thái `PUT /api/delivery-orders/{do_id}/status` và actual cost `PUT /api/tms/finance/trips/{trip_id}/actual-cost` vẫn được giữ cho các nghiệp vụ riêng. Form mới không gọi nối tiếp ba endpoint này vì không bảo đảm tính nguyên tử.

## Thông báo thao tác

Hàm toast nhận loại thông báo rõ ràng thay vì đoán hoàn toàn từ câu chữ:

- success: xanh lá.
- warning: cam.
- error: đỏ.
- loading: xanh dương và có trạng thái đang xử lý.

Các cảnh báo như chưa chọn DO, thiếu POD hoặc thiếu người nhận phải dùng warning và không được mang tiêu đề Thao tác thành công.

Toast nằm giữa màn hình, nổi trên modal, có nút đóng, nội dung ngắn và tự ẩn. Thông báo lỗi quan trọng phải có thời gian hiển thị dài hơn thông báo thành công.

## Khả năng tương thích

- Không thay đổi schema hoặc API của Sự cố và Chuỗi sự kiện.
- Giữ các API POD, actual cost, trạng thái DO hiện có; bổ sung endpoint aggregate hoàn tất giao hàng và bảng điều chỉnh giá bán cho khách.
- Giữ hỗ trợ tiếng Việt hiện tại và không đưa mojibake mới vào source.
- Bố cục desktop ưu tiên thao tác nghiệp vụ; mobile xếp các cột theo chiều dọc và không để bảng tràn khỏi viewport.

## Kiểm thử chấp nhận

- Thanh điều hướng có module Hoàn tất giao hàng riêng.
- Module mới chỉ hiển thị DO đủ điều kiện hoàn tất.
- Xem DO không cho sửa giá ban đầu.
- Hoàn tất giao mở đúng DO và đúng Trip.
- Có thể thêm và xóa nhiều khoản khách hàng trả thêm; lưu lại phải thay thế đúng danh sách backend.
- Tổng khách hàng trả thêm và giá bán cuối được tính đúng theo tiền tệ của SO.
- Thiếu DO hoặc thiếu POD hiển thị warning, không hiển thị success.
- Endpoint hoàn tất là atomic và idempotent: lỗi giữa chừng không để lại POD, giá hoặc trạng thái nửa chừng.
- Thành công lưu POD, điều chỉnh giá bán, trạng thái Delivered và hóa đơn AR bằng API thật.
- Closeout sau lưu phản ánh giá SO ban đầu, khoản khách hàng trả thêm, giá bán cuối, actual cost nội bộ và margin.
- Tracking chỉ liệt kê DO đang vận chuyển và chọn DO sẽ cập nhật bản đồ/thông tin xe.
- Sự cố và Chuỗi sự kiện vẫn hoạt động như trước.
- Các kiểm thử frontend hiện có và kiểm thử backend luồng A-Z vẫn vượt qua.
