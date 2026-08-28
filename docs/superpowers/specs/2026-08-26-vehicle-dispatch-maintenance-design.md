# Thiết kế quản lý xe, điều phối và sửa chữa phương tiện

## 1. Mục tiêu

Làm rõ trách nhiệm của từng phần trong hệ thống và bổ sung quản lý sửa chữa có quy trình thật:

- Hồ sơ xe quản lý danh tính, năng lực, pháp lý, ảnh và thông số kỹ thuật.
- Lịch xe tổng hợp Trip, phân công và khoảng thời gian sửa chữa.
- Điều phối ghép DO/Trip với xe, tài xế chính và phụ xe theo thời gian thực tế.
- Trạng thái vận hành của xe được hệ thống suy ra, không cho người dùng sửa tay.
- Mỗi lần sửa chữa có phiếu yêu cầu, phê duyệt, khoảng khóa xe, nội dung, chi phí và chứng từ.

## 2. Cơ chế nguồn lực thống nhất

### 2.1 Hồ sơ xe

`Vehicle` là dữ liệu gốc của phương tiện: biển số, loại xe, tải trọng, thể tích, pallet, tốc độ, nhiên liệu, đăng kiểm, bảo hiểm, số máy, số khung và ảnh.

Xe gán mặc định cho tài xế chỉ là gợi ý. Tài xế nghỉ không làm xe bị khóa; Dispatch được phép chọn tài xế thay thế nếu người đó đủ điều kiện.

### 2.2 Lịch nguồn lực

Lịch xe được tổng hợp từ:

1. `TransportTrip` và `ResourceAssignment` đang có hiệu lực.
2. Phiếu sửa chữa đã duyệt hoặc đang sửa.
3. Lịch pháp lý và bảo dưỡng đến hạn.
4. Vị trí cuối của Trip để xác định xe rảnh tại đâu và khả năng ghép chiều về.

Lịch tài xế được tổng hợp độc lập từ ca làm việc, nghỉ phép/nghỉ bệnh và phân công Trip.

### 2.3 Điều phối

Khi người dùng kéo DO vào một xe, backend kiểm tra trong cùng giao dịch:

- DO/Trip có thời gian lấy và giao hợp lệ.
- Xe không có Trip hoặc lịch sửa chữa chồng lấn.
- Xe đủ tải trọng, thể tích và pallet.
- Đăng kiểm, bảo hiểm và bảo dưỡng còn hiệu lực.
- Tài xế chính và phụ xe đúng vai trò, không nghỉ và không trùng lịch.

Chốt xuất bến tạo `ResourceAssignment`, chuyển xe và tổ lái sang bận. Hoàn tất chuyến giải phóng nguồn lực và ghi nhận vị trí rảnh tại điểm cuối. Trạng thái này không được sửa từ form Master Data.

## 3. Dữ liệu sửa chữa

### 3.1 VehicleMaintenanceRequest

Mỗi phiếu gồm:

- Số phiếu duy nhất và `vehicle_id`.
- Ngày yêu cầu, người yêu cầu, mức ưu tiên và loại sửa chữa.
- Thời gian dự kiến bắt đầu/kết thúc để khóa lịch xe.
- Nội dung hư hỏng, nguyên nhân, số km hiện tại và nhà sửa chữa.
- Tiền tệ, tổng chi phí dự kiến và tổng chi phí thực tế.
- Trạng thái: `requested`, `approved`, `in_progress`, `completed`, `cancelled`.
- Người duyệt, thời gian duyệt, thời gian hoàn tất và ghi chú nghiệm thu.
- Ngày bảo dưỡng kế tiếp, phiên bản và dấu thời gian cập nhật.
- Thời gian bắt đầu/kết thúc thực tế để theo dõi trường hợp sửa quá hạn.

### 3.2 VehicleMaintenanceCostLine

Một phiếu có nhiều dòng chi phí:

- Nhóm chi phí: phụ tùng, nhân công, dầu nhớt, cứu hộ hoặc chi phí khác.
- Nội dung, số lượng, đơn vị tính.
- Đơn giá dự kiến, đơn giá thực tế và thành tiền.

Tổng phiếu được backend tính từ các dòng, không nhận tổng do frontend tự khai.

### 3.3 Chứng từ

Phiếu cho phép lưu danh sách ảnh hiện trạng, ảnh sau sửa chữa, hóa đơn và biên bản nghiệm thu. File sử dụng cơ chế upload hiện có; database chỉ giữ tham chiếu tài liệu và metadata.

## 4. Quy trình sửa chữa

1. `Lập yêu cầu`: lưu phiếu và chi phí dự kiến; chưa khóa xe cứng nhưng lịch xe hiển thị cảnh báo chờ duyệt.
2. `Duyệt`: kiểm tra xung đột với Trip và phiếu sửa khác. Nếu trùng lịch, từ chối và trả mã `MAINTENANCE_SCHEDULE_CONFLICT`. Nếu hợp lệ, khóa xe trong khoảng sửa.
3. `Bắt đầu sửa`: chuyển phiếu sang `in_progress`, ghi `actual_start`; trạng thái vận hành hiển thị `Đang sửa chữa`.
4. `Hoàn tất`: yêu cầu nội dung nghiệm thu, chi phí thực tế và ngày bảo dưỡng kế tiếp; ghi `actual_end`. Xe chỉ trở lại rảnh khi không còn Trip hoặc phiếu sửa đang hoạt động.
5. `Hủy`: phiếu `requested` hoặc `approved` được hủy. Phiếu `in_progress` chỉ được hủy bởi quản lý đội xe và bắt buộc có lý do; giải phóng lịch khóa nếu không còn phiếu khác.

Ma trận chuyển trạng thái:

| Trạng thái hiện tại | Thao tác hợp lệ | Trạng thái mới | Trường được sửa |
|---|---|---|---|
| `requested` | Sửa, duyệt, hủy | `requested`, `approved`, `cancelled` | Toàn bộ nội dung dự kiến và dòng chi phí dự kiến |
| `approved` | Bắt đầu, hủy | `in_progress`, `cancelled` | Nhà sửa chữa và chứng từ trước sửa; không đổi xe hoặc khoảng khóa |
| `in_progress` | Cập nhật thực tế, hoàn tất, hủy có quyền | `in_progress`, `completed`, `cancelled` | Dòng chi phí thực tế, chứng từ, nghiệm thu |
| `completed` | Xem | `completed` | Không sửa; điều chỉnh tài chính phải dùng chứng từ điều chỉnh riêng |
| `cancelled` | Xem | `cancelled` | Không sửa |

Mỗi lệnh chuyển trạng thái bắt buộc có `idempotency_key`. Cùng actor, endpoint, phiếu và key trả lại kết quả đã lưu mà không kiểm tra lại version và không ghi thêm chi phí/audit. Key mới với `expected_version` cũ trả `VERSION_CONFLICT`. Backend lưu khóa và response chuẩn trong Operation Log hoặc command receipt có unique constraint.

Khoảng thời gian sử dụng quy tắc nửa mở `[start, end)` và bắt buộc `end > start`: một Trip kết thúc đúng lúc lịch sửa bắt đầu không bị coi là chồng lấn. Tất cả thời gian lưu UTC và hiển thị theo múi giờ cấu hình của đơn vị. Phiếu `approved` trong tương lai làm lịch xe bị khóa trong khoảng đã duyệt nhưng trạng thái hiện tại vẫn có thể là `Rảnh`; phiếu `in_progress` hoặc phiếu đã quá giờ kết thúc mà chưa hoàn tất hiển thị `Đang sửa chữa/Quá hạn sửa chữa`.

Dispatch gặp phiếu `approved` hoặc `in_progress` chồng lấn phải trả `VEHICLE_MAINTENANCE_OVERLAP` và không thay đổi DO, Trip, xe hoặc tổ lái.

### 4.1 Khóa giao dịch và chống điều phối đồng thời

Mọi lệnh làm thay đổi lịch xe gồm Approve/Start/Complete/Cancel Maintenance và Dispatch DO/FO/Trip phải đi qua một `VehicleScheduleLock` dùng chung.

Thứ tự khóa bắt buộc là:

1. Khóa advisory theo `vehicle_id` trong PostgreSQL, sau đó `SELECT Vehicle ... FOR UPDATE`.
2. Khóa phiếu sửa hoặc Trip/FO/DO mục tiêu.
3. Khóa tài xế chính, phụ xe và các `ResourceAssignment` liên quan.
4. Kiểm tra lại overlap trên dữ liệu vừa khóa.
5. Ghi toàn bộ thay đổi và Operation Log trong một transaction; mọi lỗi rollback toàn bộ.

Các service Dispatch hiện có phải được đưa về cùng thứ tự khóa này để tránh deadlock. Môi trường SQLite test dùng transaction ghi tuần tự; PostgreSQL production dùng transaction-level advisory lock kết hợp row lock. Hai yêu cầu duyệt sửa cùng xe cũng phải đi qua khóa chung nên không thể cùng vượt qua kiểm tra overlap.

Approve đọc snapshot `vehicle_id` và version từ phiếu, khóa advisory/Vehicle theo snapshot, sau đó khóa phiếu và đọc lại. Nếu `vehicle_id` hoặc version đã đổi trong lúc chờ khóa, lệnh trả `VERSION_CONFLICT` và client tải lại; không tự khóa sang xe khác.

Update phiếu `requested` đọc snapshot trước, xác định tập Vehicle cũ/mới, khóa advisory và các Vehicle theo thứ tự ID ổn định, sau đó mới khóa phiếu và đọc lại snapshot/version. Nếu dữ liệu đã đổi thì trả `VERSION_CONFLICT`; không tiếp tục với tập khóa cũ. Như vậy Update và Approve đều giữ thứ tự Vehicle trước, phiếu sau.

Start chỉ hợp lệ khi thời điểm hiện tại không sớm hơn `planned_start`. Sau khi giữ `VehicleScheduleLock`, service kiểm tra lại xe không có Trip/Assignment active và không có phiếu `in_progress` khác. Phiếu sửa quá hạn trước đó vẫn được coi là active nên chặn Start. Nếu cần bắt đầu sớm, quản lý phải sửa khoảng dự kiến khi phiếu còn `requested` rồi duyệt lại, không bỏ qua kiểm tra bằng nút Start.

## 5. Thiết kế giao diện

### 5.1 Phần đầu form xe

Ảnh phương tiện được đưa lên đầu form, cạnh khối nhận diện gồm biển số, hãng, loại xe và trạng thái vận hành chỉ đọc. Bên dưới là tải trọng, thể tích, pallet, lịch gần nhất, ngày bảo dưỡng kế tiếp và vị trí hiện tại.

`Vehicle.lifecycle_status` quản lý vòng đời Master Data với các giá trị `active`, `inactive`, `retired`. `operational_status` là giá trị chỉ đọc được backend suy ra từ phân công, lịch sửa và pháp lý. Cột `Vehicle.status` cũ được giữ tạm trong migration để tương thích nhưng client không được gửi khi tạo/cập nhật xe; dữ liệu cũ được ánh xạ sang `lifecycle_status` và trạng thái vận hành được dựng lại từ các bảng nghiệp vụ. Sau khi các luồng cũ chuyển đổi xong mới loại bỏ cột cache này.

### 5.2 Thanh chức năng

Form sử dụng thanh chọn ngang tương tự Master Data:

- `Thông tin chung`
- `Pháp lý & đăng kiểm`
- `Lịch xe`
- `Sửa chữa & bảo dưỡng`
- `Chi phí xe`

Trên điện thoại thanh này cuộn ngang; nội dung chuyển thành một cột và ảnh giữ ở đầu.

### 5.3 Tab sửa chữa

Tab gồm:

- Chỉ số tổng chi phí năm, phiếu chờ duyệt, phiếu đang sửa và ngày sẵn sàng kế tiếp.
- Danh sách phiếu theo ngày, nội dung, nhà sửa chữa, chi phí, trạng thái và chứng từ.
- Nút `Lập phiếu yêu cầu sửa chữa` mở form chi tiết.
- Bộ lọc thời gian, trạng thái và nhóm sửa chữa.
- Thao tác xem, duyệt, bắt đầu sửa, hoàn tất hoặc hủy theo quyền.

### 5.4 Lịch xe

Lịch xe hiển thị Trip và sửa chữa trên cùng trục thời gian. Khoảng sửa chữa dùng trạng thái riêng, không thể kéo DO vào. Phiếu chờ duyệt chỉ hiển thị cảnh báo để điều phối viên biết rủi ro.

Không thay đổi contract availability cũ trong lần triển khai này. Bổ sung endpoint mới `GET /api/vehicle-schedule-events?start=&end=&vehicle_id=&event_type=&page=&page_size=` trả envelope `{items, total, page, page_size}` với danh sách event thống nhất:

```json
{
  "event_type": "trip|maintenance|legal_warning",
  "resource_id": "vehicle-id",
  "start_at": "UTC datetime",
  "end_at": "UTC datetime",
  "blocking": true,
  "status": "approved|in_progress|...",
  "reference_id": "Trip hoặc số phiếu",
  "label": "Nhãn hiển thị"
}
```

Client lịch xe được chuyển sang endpoint mới sau khi backend có test contract; endpoint availability cũ tiếp tục phục vụ màn hình chưa chuyển đổi. API dùng cùng quy tắc `[start, end)`. UI không cho thả DO lên event có `blocking=true`; trên điện thoại thao tác chạm xe cũng áp dụng cùng điều kiện.

Quy tắc `blocking`:

| Loại event/trạng thái | `blocking` | Ý nghĩa |
|---|---:|---|
| Maintenance `requested` | `false` | Cảnh báo rủi ro, chưa giữ xe |
| Maintenance `approved` | `true` trong khoảng duyệt | Giữ xe cho lịch sửa tương lai |
| Maintenance `in_progress` hoặc quá hạn chưa hoàn tất | `true` | Khóa xe đến khi hoàn tất/hủy hợp lệ |
| Maintenance `completed/cancelled` | `false` | Chỉ hiển thị lịch sử |
| Trip/Assignment active | `true` | Xe đã có chuyến trong khoảng đó |
| Legal warning chưa đến hạn | `false` | Cảnh báo chuẩn bị gia hạn |
| Pháp lý hết hạn tại ngày Trip | `true` | Không cho Dispatch |
| Vehicle `inactive/retired` | `true` toàn kỳ | Không phải nguồn lực điều phối |

## 6. API và quyền

Các API mới:

- `GET /api/vehicles/{vehicle_id}/maintenance-requests`
- `POST /api/vehicles/{vehicle_id}/maintenance-requests`
- `GET /api/vehicle-maintenance-requests/{request_id}`
- `PUT /api/vehicle-maintenance-requests/{request_id}`
- `POST /api/vehicle-maintenance-requests/{request_id}/approve`
- `POST /api/vehicle-maintenance-requests/{request_id}/start`
- `POST /api/vehicle-maintenance-requests/{request_id}/complete`
- `POST /api/vehicle-maintenance-requests/{request_id}/cancel`
- `POST /api/vehicle-maintenance-requests/{request_id}/documents/stage`
- `GET /api/vehicle-maintenance-requests/{request_id}/documents/{document_id}`
- `DELETE /api/vehicle-maintenance-requests/{request_id}/documents/{document_id}`

Nhân viên vận hành được lập phiếu; quản lý đội xe được duyệt và bắt đầu; quản lý đội xe hoặc người nghiệm thu được hoàn tất; người không có quyền chỉ được xem.

Mọi chuyển trạng thái ghi Operation Log và dùng `expected_version` để chặn lưu đè.

Chứng từ hỗ trợ JPG, PNG, WebP và PDF, tối đa 10 MB/file. Upload staging phải lưu file hoàn chỉnh, checksum và metadata trước khi trả token. Lệnh `complete` nhận danh sách token, xác minh token/checksum/quyền, promote file sang vùng bất biến, rồi gắn metadata trong transaction hoàn tất phiếu. Nếu promote thất bại thì chưa mở transaction và phiếu không đổi. Nếu transaction rollback sau promote, file trở thành orphan và được compensation/cleanup xóa; không có phiếu completed tham chiếu file thiếu. Token/file không gắn hoặc hết hạn cũng được cleanup. Download/delete luôn kiểm tra quyền theo phiếu, không cho truy cập bằng đường dẫn trực tiếp. Chứng từ của phiếu `completed` không được xóa trực tiếp; phải tạo chứng từ điều chỉnh có audit.

`Vehicle.maintenance_date` tiếp tục là nguồn chuẩn cho ngày bảo dưỡng kế tiếp mà Dispatch kiểm tra. Lệnh Complete bắt buộc cập nhật trường này từ `next_maintenance_date` trong cùng transaction với phiếu và chi phí. Lịch sử các ngày trước nằm trên từng phiếu completed.

## 7. Chi phí và báo cáo

Chi phí sửa chữa là chi phí phương tiện, không tự động cộng vào Closeout, Actual Cost hoặc giá bán của DO. Phiếu có thể tham chiếu Incident hoặc Trip nếu hư hỏng phát sinh trong chuyến, nhưng tham chiếu này chỉ phục vụ truy vết.

Trong phạm vi triển khai này không có thao tác chuyển dòng sửa chữa sang Actual Cost của chuyến. Vì vậy báo cáo chi phí xe luôn tính các dòng sửa chữa hoàn tất, còn P&L chuyến không tính chúng và không có khả năng ghi nhận hai lần. Việc phân bổ chi phí sửa chữa vào chuyến là giai đoạn riêng sau này; khi triển khai phải dùng `source_type`, `source_id`, `source_line_id`, unique constraint theo dòng nguồn, trạng thái `posted/reversed` và tỷ giá tại ngày posting.

Tab `Chi phí xe` tổng hợp chi phí sửa chữa theo tháng/năm, nhóm chi phí và số km. Báo cáo P&L vận tải giữ nguyên quy tắc hiện tại.

## 8. Xử lý lỗi và tính toàn vẹn

- Không cho duyệt phiếu có thời gian kết thúc nhỏ hơn hoặc bằng thời gian bắt đầu.
- Không cho thay đổi xe của phiếu sau khi đã duyệt.
- Không cho xóa xe đang có lịch sử sửa chữa; chỉ cho ngừng hoạt động.
- Hoàn tất hoặc hủy lặp lại phải idempotent, không tạo thêm chi phí.
- Nếu staging hoặc promote file thất bại, phiếu không chuyển trạng thái; file orphan do rollback được cleanup và không xuất hiện như chứng từ hợp lệ.
- Mọi tổng tiền được tính lại ở backend.

## 9. Kiểm thử bắt buộc

- CRUD phiếu và dòng chi phí tồn tại sau tải lại.
- Chuyển trạng thái đúng thứ tự và chặn thao tác sai quyền.
- Duyệt phiếu trùng Trip bị chặn nguyên tử.
- Hai phiếu sửa cùng xe chồng lấn không thể cùng được duyệt.
- Approve Maintenance và Dispatch chạy đồng thời chỉ một lệnh thành công; lệnh còn lại rollback sạch.
- Start Maintenance chạy đồng thời với Dispatch hoặc khi phiếu sửa trước quá hạn phải bị chặn nguyên tử.
- Dispatch trùng lịch sửa bị chặn và không đổi trạng thái nguồn lực.
- Kiểm tra rollback đồng thời cho DO/FO/Trip, assignment, xe, tổ lái, phiếu và Operation Log ở cả luồng Dispatch DO và Dispatch Trip.
- Tài xế nghỉ vẫn cho phép dùng xe với tài xế thay thế.
- Hoàn tất sửa giải phóng xe khi không còn khóa khác.
- Complete/Cancel lặp lại cùng `idempotency_key` không tạo chi phí hoặc audit trùng; key mới với version cũ bị chặn.
- Khoảng thời gian tiếp giáp không bị báo overlap; timezone được chuyển đúng.
- Khoảng sửa có `end == start` bị từ chối.
- Phiếu sửa quá hạn tiếp tục khóa xe và hiện cảnh báo.
- Chứng từ staging thất bại hoặc hết hạn được cleanup; người không có quyền không tải/xóa được.
- Migration dữ liệu trạng thái xe cũ không làm mất assignment đang hoạt động.
- Update `vehicle_id` và Approve chạy đồng thời không thể khóa nhầm xe.
- Ảnh xe ở đầu form và các tab hiển thị đúng trên desktop/mobile.
- Tổng chi phí trên giao diện, API và báo cáo khớp tổng dòng chi phí thực tế.
