# Thiết kế chuẩn hóa luồng EPL A–Z

## Mục tiêu

Chuẩn hóa hệ thống EPL trên kiến trúc FastAPI, SQLAlchemy, SQLite/PostgreSQL và frontend JavaScript hiện tại. Hệ thống phải vận hành theo một chuỗi nghiệp vụ duy nhất, không tự tạo dữ liệu giả khi thiếu cấu hình, giữ đúng tiếng Việt UTF-8 và ngăn dữ liệu mất liên kết.

## Phạm vi dữ liệu và runbook dọn dữ liệu

Gốc của một chuỗi cần giữ là Quotation có mã đúng mẫu `QT-YYYY-NNN`, với `NNN` từ `001` đến `020`. SO, DO, hóa đơn, GL, POD, tracking, chi phí và chi tiết chỉ được giữ khi liên kết hợp lệ với một gốc này. Mã không đúng mẫu, hậu tố lớn hơn `020` và bản ghi nghiệp vụ không truy ngược được đến gốc hợp lệ được đưa vào manifest xóa. Customer, Route, VehicleType, Vehicle, Driver, Currency và các bảng Master Data khác không thuộc quy tắc hậu tố này.

Runbook bắt buộc:

1. Xác định backend database đang được cấu hình; không tự chuyển môi trường khi chưa cho phép.
2. Thu thập số lượng trước dọn và sinh manifest dry-run theo từng bảng, ID, lý do giữ/xóa/sửa.
3. Với SQLite, dừng ghi và dùng SQLite backup API để tạo bản sao có dấu thời gian, sau đó chạy `integrity_check` trên bản sao. Với PostgreSQL, yêu cầu đường dẫn/tiện ích backup được cấu hình và xác minh backup trước khi apply; nếu chưa có thì dừng dọn.
4. Chuỗi `001–020` bị thiếu Master Data được sửa liên kết chỉ khi ánh xạ nguồn là rõ ràng. Nếu không rõ, đưa vào quarantine/export và xóa khỏi database hoạt động; không tự đoán khách hàng hoặc tuyến.
5. Xác định thứ tự phụ thuộc từ metadata khóa ngoại thực tế. Xóa trong một transaction; audit/history được giữ hoặc ẩn danh theo quan hệ thực tế, không bị bỏ sót vì danh sách hard-code.
6. Chỉ giải phóng xe/tài xế nếu không còn DO hoạt động khác tham chiếu cùng tài nguyên.
7. Đối soát số lượng từng bảng, kiểm tra `foreign_key_check`, cân đối hóa đơn/GL và ghi báo cáo sau dọn.
8. Thử restore bản backup vào database tạm và chạy kiểm tra toàn vẹn trước khi coi migration hoàn tất.

## Luồng nghiệp vụ chuẩn

Luồng duy nhất là:

`Quotation Draft → Quotation Approved → Sales Order Confirmed → Delivery Order Planned → Delivery Order Approved → In Transit → Arrived → Delivered → Invoice Posted → GL Posted`

Đây là chuỗi nhiều thực thể, không phải một cột trạng thái chung. Quotation dùng `Draft|Approved|Rejected|Expired`; SalesOrder dùng `Draft|Confirmed|Cancelled`; DeliveryOrder dùng `Planned|Approved|In Transit|Arrived|Delivered|Cancelled`; Invoice dùng `Draft|Posted|Reversed`; trạng thái GL được xác định bằng journal batch `Pending|Posted|Reversed`. Mỗi lần chuyển trạng thái lưu thời gian, tác nhân và audit log. SO được xác nhận bằng endpoint tường minh, không tự xác nhận khi tạo.

Quy tắc chuyển bước:

1. Báo giá chỉ được tạo khi khách hàng, tuyến đường và loại hàng/loại xe đã có trong Master Data.
2. Chỉ báo giá `Approved` mới được chuyển thành Sales Order. Sales Order lưu liên kết nguồn tới báo giá.
3. Chỉ Sales Order `Confirmed` mới được tạo Delivery Order. DO kế thừa khách hàng, tuyến, số tiền, quy cách và thể tích; người dùng không nhập lại các trường nguồn.
4. DO `Planned` chỉ được duyệt khi có ngày nhận dự kiến, ngày giao dự kiến không sớm hơn ngày nhận, địa điểm đi/đến khác rỗng, `weight_kg > 0`, `volume_m3 > 0` và `packaging_spec` là chuỗi sau khi trim có ít nhất 2 ký tự.
5. Chỉ DO `Approved` mới được điều phối. Xe, tài xế chính và phụ xế (nếu có) phải tồn tại, đang rảnh và phù hợp tải trọng/thể tích.
6. Điều phối thành công chuyển DO thành `In Transit` và khóa xe/tài xế trong cùng transaction.
7. `In Transit` chỉ chuyển sang `Arrived`; `Arrived` chỉ chuyển sang `Delivered` khi POD có thời gian nhận, họ tên người nhận và ít nhất một bằng chứng là chữ ký hoặc ảnh giao hàng.
8. Khi `Delivered`, hệ thống giải phóng xe/tài xế. Việc lập hóa đơn là thao tác có kiểm soát, dùng đúng khách hàng và số tiền từ chuỗi nghiệp vụ.
9. Mỗi DO chỉ có tối đa một hóa đơn không bị reverse. Mỗi hóa đơn chỉ được post GL một lần; tổng Nợ phải bằng tổng Có. Các ràng buộc unique quotation→SO, SO→DO, DO→invoice và invoice→journal được thực thi ở database.
10. Mọi yêu cầu nhảy bước, thiếu dữ liệu hoặc lặp thao tác trả lỗi HTTP phù hợp cùng thông báo tiếng Việt có hướng dẫn.

## Master Data và hướng dẫn cấu hình

Hệ thống không dùng các giá trị mặc định giả như `CUS01`, `RT01`, `DO-2026-004`, “Khách Hàng Lẻ” hoặc số tiền `3.500.000`.

Khi thiếu dữ liệu, API trả JSON `{error_code, message, field_errors, required_master_data, navigation_targets}`. `field_errors` là map trường→thông báo; hai trường cuối là mảng để báo nhiều thiếu sót một lần. Mã lỗi ổn định gồm `VALIDATION_ERROR` (422), `MISSING_MASTER_DATA` (409), `INVALID_TRANSITION` (409), `RESOURCE_BUSY` (409), `NOT_FOUND` (404), `DUPLICATE_OPERATION` (409), `DATABASE_UNAVAILABLE` (503). Frontend hiển thị thông báo cùng nút hoặc hướng dẫn đến đúng nơi:

- Thiếu khách hàng → `master-data/customers`.
- Thiếu tuyến hoặc chặng → `master-data/routes`.
- Thiếu loại xe hoặc định mức → `master-data/vehicle-types`.
- Thiếu xe → `master-data/vehicles`.
- Thiếu tài xế/phụ xế → `master-data/drivers`.
- Thiếu tiền tệ/tỷ giá → `master-data/currencies`.
- Thiếu công thức hoặc dữ liệu tính giá → `ai-data/cost-settings`.
- Thiếu cấu hình AI hoặc model → `ai-data/config`; luồng nghiệp vụ thông thường vẫn hoạt động nếu chức năng AI không bắt buộc.

Dropdown chỉ hiển thị bản ghi Master Data thực tế. Khi danh sách rỗng, giao diện không cho lưu và hiển thị đường dẫn cấu hình thay vì tự điền dữ liệu mẫu.

## Backend và dữ liệu

- Loại bỏ các route FastAPI trùng và giữ một triển khai duy nhất cho mỗi method/path.
- Tách quy tắc chuyển trạng thái và nghiệp vụ tạo chứng từ thành các hàm/service có thể kiểm thử.
- Sinh mã bằng sequence/ID allocator có khóa transaction; không dùng `count() + 1` hoặc chỉ lấy max mà không khóa.
- Endpoint ghi nhận `Idempotency-Key`; database unique constraints là lớp bảo vệ cuối. Điều phối khóa hàng DO/Vehicle/Driver (hoặc optimistic version trên SQLite) để hai request không giữ cùng tài nguyên.
- Bật SQLite foreign keys trên mọi kết nối; PostgreSQL tiếp tục dùng ràng buộc schema.
- Mọi thao tác nhiều bảng chạy trong một transaction và rollback khi có lỗi.
- Endpoint xóa kiểm tra quan hệ, giải phóng tài nguyên vận hành và xóa dữ liệu phụ thuộc theo thứ tự xác định.
- Seed chỉ chạy bằng lệnh quản trị tường minh trên database rỗng; startup không tự seed hoặc tự thay đổi dữ liệu.
- PostgreSQL lỗi thì trả `DATABASE_UNAVAILABLE` và fail fast. Chỉ dùng SQLite khi `DATABASE_MODE=sqlite` được cấu hình tường minh; tuyệt đối không silent fallback từ PostgreSQL.
- Endpoint reset toàn bộ không được dùng cho thao tác dọn một phần và phải có xác nhận rõ ràng.

## Frontend và tiếng Việt

- Giữ bố cục hiện tại, sửa các lời gọi API để tuân theo luồng trạng thái chuẩn.
- Không dùng fallback hard-code cho mã chứng từ, khách hàng, tuyến, phương tiện hoặc số tiền.
- Mọi response lỗi phải được đọc và hiển thị; không chỉ báo “có lỗi xảy ra”.
- Nội dung nguồn, JSON, HTML response và database dùng UTF-8. Console Windows được cấu hình/ghi log theo cách không crash khi gặp tiếng Việt hoặc emoji.
- Dữ liệu đưa vào `innerHTML` phải được escape hoặc dựng bằng DOM API ở các vị trí nhận dữ liệu người dùng.

## Kế toán

Sales Order lưu currency và tỷ giá tại ngày xác nhận. Invoice lấy net amount từ SO, VAT theo cấu hình khách hàng/thuế tại ngày lập và làm tròn đến đơn vị nhỏ nhất của currency. Posting date mặc định là ngày nghiệp vụ hiện tại nhưng phải nằm trong kỳ mở. Account mapping (phải thu, doanh thu, thuế) là Master Data bắt buộc; thiếu tỷ giá/thuế trả `master-data/currencies`, thiếu tài khoản hoặc mapping trả `master-data/chart-of-accounts`, thiếu công thức giá trả `ai-data/cost-settings`.

Hai bước posting tách biệt. Thao tác thứ nhất tạo và post Invoice trong một transaction, chỉ khi DO đã `Delivered`. Thao tác thứ hai post GL trong transaction riêng, chỉ khi Invoice đang `Posted` và chưa có journal `Posted`; nếu lỗi thì rollback riêng journal và Invoice vẫn ở `Posted` để người dùng thử lại. Hủy sau posting dùng Invoice/Journals reversal liên kết chứng từ gốc, không xóa hoặc sửa bút toán đã post.

## Kiểm thử và tiêu chí hoàn thành

Các test tự động dùng database tạm, không chạm database thật, bao gồm:

- Không còn method/path trùng trong FastAPI.
- Luồng thành công đầy đủ từ báo giá đến GL.
- Từng chuyển trạng thái sai bị từ chối.
- Thiếu từng nhóm Master Data trả hướng dẫn điều hướng đúng.
- Không thể điều phối xe/tài xế đang bận hoặc quá tải.
- POD không được cập nhật nhầm DO.
- Delivered giải phóng tài nguyên đúng một lần.
- Không tạo trùng hóa đơn hoặc bút toán khi gửi lại request.
- Hai request đồng thời không thể cấp cùng mã hoặc giữ cùng xe/tài xế.
- Tổng Nợ bằng tổng Có và số tiền lấy từ đơn thực tế.
- Xóa chuỗi đơn không để lại bản ghi mồ côi.
- PostgreSQL lỗi làm backend fail fast rõ ràng; SQLite chỉ khởi động khi được chọn tường minh. Console Windows không crash vì Unicode.
- Các chuỗi tiếng Việt trọng yếu trả về đúng Unicode, không mojibake.
- Sau khi dọn dữ liệu, kiểm tra foreign key trả về 0 lỗi đối với tập dữ liệu được giữ.
- Dry-run/apply/rollback/restore cho kết quả đúng; manifest khớp chính xác ID và số lượng, kể cả mã sai định dạng.
- Lỗi giữa transaction không để lại dữ liệu một phần; chia sẻ tài nguyên giữa các DO được kiểm tra trước khi giải phóng.
- Frontend điều hướng đúng mọi `navigation_targets` và hiển thị đồng thời nhiều điều kiện còn thiếu.
- Mọi file văn bản được decode nghiêm ngặt bằng UTF-8; bộ kiểm tra phát hiện các dấu mojibake phổ biến như `Ã`, `Ä`, `á»` trong nội dung hiển thị.

Hoàn thành khi toàn bộ test mới, kiểm tra cú pháp Python/JavaScript và một bài kiểm thử A–Z qua HTTP đều đạt; bản sao database và báo cáo dữ liệu đã xóa được lưu lại để phục hồi khi cần.
