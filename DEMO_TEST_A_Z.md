# Hướng dẫn mở app và test luồng thật A-Z

## 1. Mở ứng dụng

Mở PowerShell mới và chạy:

```powershell
cd D:\Demo_Lao\EPL_System
C:\Users\zinnn\miniconda3\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
```

Giữ cửa sổ PowerShell này mở, sau đó truy cập:

```text
http://127.0.0.1:8001
```

Kiểm tra backend trước khi demo:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/health
```

Kết quả bắt buộc:

```text
status
------
ok
```

Nếu cần nạp lại bộ dữ liệu demo chuẩn:

```powershell
cd D:\Demo_Lao\EPL_System
C:\Users\zinnn\miniconda3\python.exe backend\scripts\seed_demo_workflow.py
```

Lưu ý: lệnh seed làm mới các chứng từ có tiền tố `DEMO-*-2026-*`.

## 2. Dữ liệu dùng trong bài test

| Dữ liệu | Giá trị |
|---|---|
| Khách hàng | `DEMO-CUS-SGNFOOD` |
| Tuyến | `DEMO-RT-VSIP2A-CATLAI` |
| Loại xe | `DEMO-VT-20FT`, 28.000 kg, 22 pallet, 33,2 m3 |
| Xe | `DEMO-61H-112.34` |
| Tài xế | `DEMO-DRV-002` - Lê Hoàng Nam |
| Phụ xe | `DEMO-DRV-003` - Trần Quốc Huy |
| QT | `DEMO-QT-2026-001` |
| SO | `DEMO-SO-2026-001` |
| DO | `DEMO-DO-2026-001` |
| Hàng | 8.500 kg, 18 pallet, 24 m3 |
| Giá SO ban đầu | 3.600.000 VNĐ |
| Người nhận | Nguyễn Văn An - 0908123456 |
| Điểm giao | Cảng Cát Lái, TP. Thủ Đức |

## 3. Kịch bản tự thao tác một hồ sơ mới từ A đến Z

Phần này là kịch bản chính để anh tự bấm toàn bộ luồng. Không mở thẳng hồ sơ `001`, `002` hoặc `003` đã hoàn thành sẵn, trừ khi cần đối chiếu.

### 3.1 Chuẩn bị trước khi bấm

1. Mở một tờ ghi chú và ghi lại bốn mã hệ thống sẽ tạo:
   - QT: `TEST-QT-2026-001`.
   - SO: `TEST-SO-2026-001`.
   - DO: `TEST-DO-2026-001`.
   - Trip: ghi mã hệ thống sinh ra sau khi lưu Trip.
2. Nếu mã `TEST-...-001` đã tồn tại, đổi số cuối thành `002`, `003` hoặc số chưa sử dụng.
3. Dùng dữ liệu nền đã có:
   - Khách hàng `DEMO-CUS-SGNFOOD`.
   - Tuyến `DEMO-RT-VSIP2A-CATLAI`.
   - Loại xe `DEMO-VT-20FT`.
   - Xe `DEMO-61H-112.34`.
   - Tài xế `DEMO-DRV-002`.
4. Chọn thời gian lấy hàng là ngày demo, thời gian giao dự kiến muộn hơn giờ lấy hàng ít nhất 4 giờ.
5. Sau mỗi nút `Lưu`, `Duyệt`, `Xác nhận`, `Tạo` hoặc `Hoàn tất`, phải tải lại danh sách và tìm lại mã vừa thao tác.

### 3.2 Bước 1 - kiểm tra xe và tài xế sẵn sàng

1. Vào `Master Data` → `Đội xe / Biển số`.
2. Tìm `DEMO-61H-112.34`, bấm `Chỉnh sửa`.
3. Kiểm tra loại xe là `DEMO-VT-20FT`, tải trọng tối đa `28.000 kg`, thể tích `33,2 m3`, sức chứa `22 pallet`.
4. Kiểm tra ngày đăng kiểm, bảo hiểm và bảo dưỡng chưa hết hạn.
5. Để trạng thái xe là `Sẵn sàng`, sau đó bấm `Lưu`.
6. Vào `Tài xế, phụ xe & ca làm việc`, tìm `DEMO-DRV-002`.
7. Kiểm tra bằng lái phù hợp, ca làm việc bao phủ thời gian chuyến và trạng thái `Rảnh (Sẵn sàng)`.
8. Mở form chỉnh sửa tài xế và kiểm tra `Trạng thái vận hành` là thông tin chỉ đọc, không có danh sách cho chọn tay `Rảnh` hoặc `Bận`.
9. Thử sửa tên hoặc số điện thoại rồi bấm `Lưu`, tải lại trang và mở lại xe và tài xế.

Điều kiện được đi tiếp: cả xe và tài xế vẫn tồn tại sau khi tải lại và đều sẵn sàng. Việc sửa hồ sơ không được thay đổi trạng thái vận hành hoặc xe của một tài xế đang thực hiện Trip.

### 3.2A - xếp ca và kiểm tra lịch quay đầu

1. Ngay tại `Master Data` → `Quản lý Tài xế & Sắp ca`, mở tab `Lịch tài xế`.
2. Kiểm tra hai ca demo ngày `24/08/2026` đã được đọc từ database:
   - `DEMO-DRV-001` gắn xe `DEMO-51C-268.89`.
   - `DEMO-DRV-002` gắn xe `DEMO-61H-112.34`.
3. Trên máy tính, kéo tài xế từ danh sách bên trái vào ô ca/ngày; trên điện thoại, chạm chọn tài xế rồi chạm ô ca.
4. Mở ca vừa tạo ở bảng bên phải, gán xe, nhập địa điểm/ghi chú rồi bấm `Lưu ca`.
5. Tải lại trang và mở lại đúng tuần. Ca vừa tạo phải còn nguyên.
6. Mở tab `Lịch xe 7 ngày` và kiểm tra từng Trip được tính từ chặng trong Route Master/Trip, không nhập khoảng cách tự do.
7. Kiểm tra thứ tự nguồn vận tốc: GPS live → vận tốc xe → vận tốc loại xe → vận tốc chặng Trip.
8. Sau khi xe giao tại B, xe phải hiển thị `Sẵn sàng tại B` để ưu tiên ghép đơn backhaul.
9. Chỉ khi Trip có chặng `empty_return` trong cấu hình tuyến/Trip, hệ thống mới tính giờ chạy rỗng về A. Nếu chưa có chặng về, tab `Cảnh báo` phải hiện `RETURN_ROUTE_REQUIRED`, tuyệt đối không tự đoán quãng đường.
10. Thử gán cùng tài xế hoặc cùng xe vào hai ca trùng giờ. Hệ thống phải chặn và không ghi ca thứ hai vào database.
11. Tạo một ô lịch `Nghỉ phép`, `Nghỉ bệnh`, `Nghỉ ca` hoặc `Không sẵn sàng` cho tài xế. Các ô này phải lưu vào database nhưng không được gán xe hoặc Trip.
12. Mở lại `Lịch xe 7 ngày`: xe trước đó của tài xế nghỉ vẫn phải hiện `Rảnh` nếu xe không có Trip hay lịch bảo dưỡng. Điều phối được phép chọn tài xế thay thế cho chính xe đó.
13. Chọn một tài xế rồi bấm `Lịch mặc định`. Chọn nhiều ngày trong tuần, giờ bắt đầu, giờ kết thúc và khoảng áp dụng, sau đó lưu.
14. Kiểm tra các ca lặp được tạo thành từng ô lịch thật; có thể mở từng ô để sửa hoặc xóa mà không ảnh hưởng các tuần khác.
15. Thử ca qua đêm: chọn bắt đầu `22:00`, kết thúc `06:00`, `Kết thúc sau 1 ngày`. Ca phải phủ từ tối ngày đầu đến sáng ngày kế tiếp.
16. Thử lịch kéo dài: chọn bắt đầu Thứ Hai `08:00`, kết thúc `17:00`, `Kết thúc sau 1 ngày`. Hệ thống phải hiểu nhân sự làm đến Thứ Ba `17:00`.
17. Tạo Trip nằm ngoài hoàn toàn lịch làm việc hoặc dài hơn giờ kết thúc ca rồi thử điều phối. API phải trả `DRIVER_WORK_SCHEDULE_REQUIRED` và không đổi trạng thái Trip, DO, xe hay nhân sự.
18. Gán cả tài xế chính và phụ xe: lịch của từng người phải phủ toàn bộ thời gian từ xuất phát đến khi xe rảnh lại. Chỉ một người thiếu lịch cũng phải bị chặn.

Kết quả bắt buộc: lịch ca tồn tại sau khi tải lại; tài xế nghỉ/ốm bị chặn điều phối nhưng xe không bị khóa theo; Dispatch dùng cùng lịch này; xe ở B được ưu tiên ghép chiều về trước khi lập chạy rỗng về A.

### 3.2B - lập phiếu sửa chữa và kiểm tra khóa xe

1. Vào `Master Data` → `Đội xe / Biển số`, mở xe cần kiểm tra.
2. Kiểm tra ảnh xe nằm ở đầu hồ sơ và `Trạng thái vận hành` là thông tin chỉ đọc do hệ thống tính; người dùng không được chọn tay `Rảnh`, `Bận` hoặc `Đang sửa`.
3. Mở tab `Sửa chữa & bảo dưỡng`, bấm `Lập phiếu yêu cầu`.
4. Nhập khoảng thời gian sửa, xưởng, nội dung và từng dòng chi phí dự kiến rồi bấm `Lưu phiếu yêu cầu`.
5. Tải lại hồ sơ. Phiếu phải còn nguyên ở trạng thái `Chờ duyệt`; giai đoạn này chưa khóa xe.
6. Bấm `Duyệt`, sau đó mở màn hình điều phối và thử xếp một DO có thời gian trùng với lịch sửa.
7. Hệ thống phải trả `VEHICLE_MAINTENANCE_OVERLAP`; không tạo phân công và không thay đổi xe, tài xế hoặc DO.
8. Bấm `Bắt đầu sửa`. Xe phải hiển thị `Đang sửa chữa` trong đúng khoảng thời gian của phiếu.
9. Bấm `Hoàn tất`, nhập đơn giá thực tế riêng cho từng dòng chi phí và ngày bảo dưỡng tiếp theo.
10. Tải lại hồ sơ xe và mở lại phiếu.

Kết quả bắt buộc: quy trình đi đúng `Chờ duyệt` → `Đã duyệt` → `Đang sửa` → `Hoàn tất`; tổng chi phí thực tế bằng tổng các dòng đã nhập; ngày bảo dưỡng tiếp theo được cập nhật vào hồ sơ xe; xe chỉ trở về rảnh khi không còn Trip, bảo dưỡng hoặc phiếu sửa đang hoạt động.

### 3.3 Bước 2 - tự tạo và duyệt Quotation

1. Vào `Quản lý quan hệ khách hàng & Bán hàng` → tab `Quotation`.
2. Bấm `Tạo Báo Giá Mới`.
3. Nhập mã `TEST-QT-2026-001` hoặc mã anh đã chọn ở bước chuẩn bị.
4. Chọn khách hàng `DEMO-CUS-SGNFOOD`.
5. Chọn tuyến `DEMO-RT-VSIP2A-CATLAI` và loại xe `DEMO-VT-20FT`.
6. Ngay sau khi chọn tuyến, kiểm tra `Điểm đi` tự điền từ checkpoint đầu, `Điểm đến` tự điền từ checkpoint cuối và dải hành trình hiển thị đủ mọi checkpoint theo đúng thứ tự trong Route Master.
7. Với tuyến demo, hành trình bắt buộc hiển thị `Kho VSIP II-A, Bình Dương` → `Vành đai 3` → `Cảng Cát Lái, TP. Thủ Đức`; không nhập tay hoặc tự đoán checkpoint.
8. Chọn tiền tệ `VND`.
9. Nhập thông tin hàng: `8.500 kg`, `18 pallet`, `24 m3`.
10. Kiểm tra khối `Loại xe phù hợp đề xuất`: `DEMO-VT-20FT` phải được phép chọn vì đủ cả tải trọng, thể tích và pallet. Thẻ đề xuất phải hiển thị mức sử dụng và số xe thực tế đang sẵn sàng tại thời điểm báo giá.
11. Nhập hoặc nạp công thức giá; đặt giá bán cuối của QT là `3.600.000 VNĐ`.
12. Bấm `Lưu báo giá` và chờ thông báo máy chủ xác nhận.
13. Đóng form, tải lại danh sách và tìm đúng mã QT.
14. Mở QT vừa tạo, bấm `Duyệt báo giá`.
15. Tải lại lần nữa và mở lại QT.

Kết quả bắt buộc: QT có trạng thái `Đã duyệt`, đúng khách hàng, tuyến, tiền tệ, toàn bộ checkpoint và giá `3.600.000 VNĐ`. QT đã duyệt chỉ được xem, không được sửa trực tiếp.

### 3.4 Bước 3 - tạo Sales Order từ QT

1. Tại QT vừa duyệt, bấm `Tạo SO từ Báo giá đã duyệt`.
2. Nếu hệ thống cho nhập mã, dùng `TEST-SO-2026-001`; nếu hệ thống tự sinh mã, ghi lại mã được sinh.
3. Kiểm tra SO đã kế thừa đúng QT nguồn, khách hàng, tuyến và giá `3.600.000 VNĐ`.
4. Không nhập lại giá khác với QT đã duyệt.
5. Bấm `Lưu SO`.
6. Đóng form, tải lại danh sách và tìm lại SO.
7. Mở SO vừa tạo, bấm `Xác nhận SO`.
8. Tải lại danh sách và mở lại SO.

Kết quả bắt buộc: SO có trạng thái `Đã xác nhận` và tham chiếu đúng QT nguồn. SO đã xác nhận không được sửa giá thương mại trực tiếp.

### 3.5 Bước 4 - tạo Delivery Order từ SO

1. Tại SO vừa xác nhận, bấm `Tạo Lệnh DO`.
2. Nếu được nhập mã, dùng `TEST-DO-2026-001`; nếu hệ thống tự sinh mã, ghi lại mã DO thực tế.
3. Kiểm tra DO tham chiếu đúng SO nguồn và khách hàng `DEMO-CUS-SGNFOOD`.
4. Chọn tuyến `DEMO-RT-VSIP2A-CATLAI`.
5. Nhập điểm đi `Kho VSIP II-A, Bình Dương`.
6. Nhập điểm đến `Cảng Cát Lái, TP. Thủ Đức`.
7. Nhập cửa sổ lấy hàng và giao hàng theo thời gian đã chuẩn bị.
8. Nhập tải trọng `8.500 kg`, số pallet `18`, thể tích `24 m3`.
9. Bấm `Lưu DO` hoặc nút tạo DO trên form.
10. Tải lại danh sách, tìm DO vừa tạo và bấm `Xem DO`.

Kết quả bắt buộc: nguyên form DO mở lại đúng dữ liệu và trạng thái là `Chờ vận chuyển`.

### 3.6 Bước 5 - tạo Trip và các điểm giao

1. Vào `Lập kế hoạch vận hành` → `Trip/Return`.
2. Bấm `Tạo Trip từ DO/FO`.
3. Chọn đúng DO vừa tạo.
4. Chọn loại Trip `Nhiều điểm dừng` nếu muốn thử nhiều điểm giao.
5. Chọn tuyến nguồn `DEMO-RT-VSIP2A-CATLAI` để hệ thống lấy chặng từ Master Data.
6. Chọn giờ khởi hành phù hợp cửa sổ lấy hàng.
7. Ở điểm giao Cát Lái, nhập người nhận `Nguyễn Văn An`, số `0908123456`.
8. Nếu thêm điểm giao thứ hai, nhập đầy đủ địa chỉ, người nhận và số điện thoại riêng cho điểm đó.
9. Bấm `Lưu Trip/Chặng`.
10. Ghi lại mã Trip vừa tạo, tải lại danh sách rồi mở lại Trip.

Kết quả bắt buộc: Trip có đúng DO, đúng tuyến, đúng số điểm giao, đúng người nhận và thời gian dự kiến.

### 3.7 Bước 6 - điều xe và xuất bến

1. Vào `Điều phối`.
2. Chọn ngày dự kiến lấy hàng. Danh sách bên trái chỉ được hiển thị các DO chờ điều phối của đúng ngày đó.
3. Mở thẻ DO vừa tạo và kiểm tra khách hàng, tuyến, loại hàng, tải trọng, pallet, giờ lấy, giờ giao và trạng thái Trip.
4. Nếu DO chưa có Trip, bấm thẻ DO. Hệ thống phải mở form `Tạo Trip vận chuyển từ DO/FO`, tự chọn đúng DO và nạp tuyến từ Master Data.
5. Nếu Trip còn `Bản nháp`, hệ thống phải mở khu vực Trip hiện có để hoàn thiện, không tạo thêm Trip trùng.
6. Chỉ khi Trip ở trạng thái đã lập kế hoạch, chuyển sang bước `Xếp lịch xe`.
7. Chọn ngày và xe `DEMO-61H-112.34`; xe bận, bảo dưỡng, quá tải hoặc trùng lịch phải bị khóa.
8. Chuyển sang bước `Nhân sự & xuất bến`.
9. Chọn tài xế chính `DEMO-DRV-002`.
10. Chọn phụ xe `DEMO-DRV-003` để kiểm tra đủ luồng nhân sự; chỉ để trống khi chuyến không yêu cầu phụ xe.
11. Chọn quy cách đóng gói phù hợp.
12. Kiểm tra hệ thống không báo quá tải: `8.500/28.000 kg`, `18/22 pallet`, `24/33,2 m3`.
13. Bấm `Chốt điều phối & xuất bến` rồi tải lại đúng ngày vừa chọn.

Thao tác nhanh trên bảng điều phối:

- Máy tính: chọn thẻ DO, hoàn thiện Trip, sau đó chọn ô ngày và xe đang rảnh.
- Điện thoại/máy tính bảng: chạm DO rồi thực hiện lần lượt bốn bước trên form.
- Sau khi chọn xe, bảng bên phải chỉ còn việc xác nhận tài xế chính, phụ xe và quy cách đóng gói rồi chốt xuất bến.
- Danh sách tài xế chính chỉ hiện nhân sự có vai trò `Lái xe chính`; danh sách phụ xe chỉ hiện nhân sự có vai trò `Phụ xe`.
- Tài xế hoặc phụ xe có lịch nghỉ/ốm/trùng ca không được xuất hiện như nguồn lực sẵn sàng.
- Xe được tính độc lập với người lái mặc định: tài xế nghỉ vẫn có thể dùng xe nếu chọn tài xế khác hợp lệ.
- Chế độ `Ngày` dùng để chốt điều phối chi tiết; chế độ `Tuần` dùng để nhìn tải xe, ngày rảnh và ngày đã có chuyến. Màn hình hiện tại chưa cung cấp chế độ tháng/năm.
- Màn hình mặc định mở `Tuần`, từ `Thứ 2` đến `Chủ nhật`; mỗi xe là một hàng và mỗi chuyến hiển thị giờ bắt đầu, giờ kết thúc, mã Trip/DO cùng trạng thái.
- Chọn DO trước, sau đó bấm ô `Rảnh cả ngày` của đúng xe/ngày. Hệ thống phải tự điền ngày điều phối và xe, rồi chuyển sang bước chọn tài xế chính, phụ xe và quy cách đóng gói.
- Ô có chuyến chỉ mở chi tiết chuyến, không được ghi đè lịch. Ô `Bảo dưỡng định kỳ` không được phép nhận DO.
- Khi cần xem vị trí chuyến chi tiết theo giờ `06:00 - 22:00`, chuyển sang chế độ `Ngày`; quay lại `Tuần` không được làm mất DO hoặc xe đang chọn.

Kết quả bắt buộc: DO và Trip chuyển sang `Đang vận chuyển`; xe, tài xế chính và phụ xe chuyển sang bận; phân công lưu đủ ba nguồn lực; lịch xe và lịch nhân sự tự cập nhật từ phân công thật.

Mở lại hồ sơ tài xế chính và phụ xe ngay sau khi xuất bến. `Trạng thái vận hành` phải tự hiển thị Trip đang thực hiện và không cho sửa tay. Sau khi hoàn tất giao hàng ở bước 10, mở lại lần nữa và kiểm tra cả hai tự trở về `Rảnh (Sẵn sàng)`.

### 3.8 Bước 7 - xem tracking

1. Vào `Theo dõi và kiểm soát` → `GPS / POD`.
2. Trong danh sách theo dõi, chọn đúng DO đang vận chuyển.
3. Bấm `Cập nhật GPS`.
4. Kiểm tra mã DO, xe, tài xế, tuyến, khoảng cách còn lại và ETA.
5. Mở `Chuỗi sự kiện` để xem các mốc theo thứ tự.
6. Có thể mở `Sự cố` để nhập một sự cố thử, nhưng không chuyển DO sang đã giao tại đây.

Lưu ý quan trọng: nút `Cập nhật GPS` chỉ đọc dữ liệu tracking mới nhất, không tự tạo tọa độ GPS giả. Nếu chuyến mới chưa có thiết bị gửi tọa độ, tốc độ có thể là `0` và bản đồ chỉ thể hiện tuyến/kế hoạch. Khi cần trình chiếu tracking có sẵn, dùng `DEMO-DO-2026-002` để xem dữ liệu GPS mẫu.

### 3.9 Bước 8 - hoàn tất từng điểm giao và ký nhận

1. Vào module `Hoàn tất giao hàng`.
2. Ở tab `Chờ hoàn tất`, tìm đúng DO đang vận chuyển.
3. Bấm `Xem DO` để kiểm tra nguyên form DO nguồn.
4. Đóng form xem và bấm `Hoàn tất giao`.
5. Mở `Điểm giao 1`; các điểm khác giữ thu gọn để dễ thao tác.
6. Nhập thời gian giao thực tế.
7. Chọn kết quả `Giao đủ hàng`.
8. Kiểm tra hoặc nhập người nhận `Nguyễn Văn An`, số `0908123456`.
9. Nhập tình trạng `Nguyên niêm phong, không móp vỡ`.
10. Chọn file POD định dạng JPG, PNG hoặc PDF.
11. Yêu cầu người nhận ký trong khung chữ ký: máy tính dùng chuột, điện thoại dùng cảm ứng.
12. Nếu có nhiều điểm giao, thu gọn điểm 1, mở điểm 2 và nhập đủ bộ POD cùng chữ ký cho điểm 2.

Điều kiện được chốt: mọi điểm giao đều có giờ giao, kết quả, người nhận, số điện thoại, tình trạng hàng, file POD và chữ ký.

### 3.10 Bước 9 - nhập phát sinh và chốt giá cuối

1. Kiểm tra hệ thống đã nạp các dòng chi phí ban đầu từ cấu hình loại xe.
2. Với khoản đã có trong cấu hình, giữ nguyên `Giá ban đầu` và chỉ sửa `Giá thực tế`.
3. Với khoản hoàn toàn mới, bấm `Thêm khoản phí`.
4. Nhập `Phí chờ bốc dỡ`, giá ban đầu `0`, giá thực tế `350.000`.
5. Thêm `Phí cầu đường bổ sung`, giá ban đầu `0`, giá thực tế `120.000`.
6. Kiểm tra `Khách hàng trả thêm` bằng `470.000 VNĐ`.
7. Kiểm tra `Giá cuối DO` bằng `4.070.000 VNĐ` = `3.600.000 + 470.000`.
8. Bấm `Hoàn tất giao hàng & chốt giá` đúng một lần và chờ phản hồi máy chủ.

Không đóng trang khi hệ thống đang lưu. Nếu API lỗi, form phải giữ nguyên và DO không được chuyển trạng thái một phần.

### 3.11 Bước 10 - kiểm tra kết quả sau chữ ký

1. Sau thông báo thành công, hệ thống chuyển sang tab `Đã hoàn tất`.
2. Mở lại đúng DO vừa giao.
3. Kiểm tra biên nhận `Đã cập nhật vào hệ thống`.
4. Kiểm tra DO là `Delivered`.
5. Kiểm tra Trip là `Completed`.
6. Kiểm tra Freight Order là `Delivered`.
7. Kiểm tra POD có đúng người nhận, thời gian, file và chữ ký của từng điểm giao.
8. Kiểm tra Closeout có giá đầu `3.600.000`, khách trả thêm `470.000`, giá cuối `4.070.000 VNĐ`.
9. Kiểm tra AR Invoice là `Posted` và số tiền bằng giá cuối DO.
10. Kiểm tra phân công là `Completed`.
11. Kiểm tra xe trở về `Sẵn sàng`, tài xế trở về `Rảnh (Sẵn sàng)`.
12. Nhấn `Ctrl + F5`, vào lại tab `Đã hoàn tất` và mở lại DO lần cuối.

Kết luận đạt: toàn bộ dữ liệu vẫn còn sau khi tải lại. Khi đó hồ sơ đã đi trọn luồng QT → SO → DO → Trip → Dispatch → Tracking → POD/chữ ký → Closeout → Invoice.

## 4. Test Master Data: xe và tài xế

1. Vào `Master Data` → `Danh mục loại xe`.
2. Mở `DEMO-VT-20FT`, kiểm tra tải trọng `28.000 kg`, sức chứa `22 pallet`, thể tích `33,2 m3`.
3. Vào `Đội xe / Biển số`, mở `DEMO-61H-112.34`.
4. Kiểm tra xe còn đăng kiểm, bảo hiểm, bảo dưỡng và đang `Sẵn sàng`.
5. Vào `Tài xế, phụ xe & ca làm việc`, mở `DEMO-DRV-002`.
6. Kiểm tra bằng lái phù hợp, ca làm việc hợp lệ và trạng thái `Rảnh (Sẵn sàng)`.
7. Thử sửa một ghi chú hoặc số điện thoại, bấm `Lưu`, tải lại trang và mở lại bản ghi.

Kết quả bắt buộc: giá trị vừa sửa vẫn còn sau khi tải lại. Nếu mất dữ liệu thì dừng demo, không tiếp tục luồng.

### 4.1 Kiểm tra cấu hình chi phí tách biệt theo loại xe

1. Vào `Master Data` → phần cấu hình `Danh mục loại xe` và `Cấu thành chi phí vận tải`.
2. Chọn `Xe tải thùng 10 tấn`, ghi lại các giá trị hiện tại rồi đổi riêng `Fuel Rate / 1 km` thành một số dễ nhận biết, ví dụ `4.800 VND`.
3. Bấm `Lưu cấu hình giá thành`, chờ máy chủ xác nhận thành công.
4. Chọn `Container 20FT`. Tiêu đề loại xe và các trường chi phí phải chuyển đúng sang cấu hình Container; `Fuel Rate / 1 km` không được tự đổi thành `4.800 VND`.
5. Đổi riêng `Fuel Rate / 1 km` của `Container 20FT` thành `6.250 VND` rồi lưu.
6. Chuyển qua lại giữa hai loại xe và kiểm tra:
   - `Xe tải thùng 10 tấn` vẫn là `4.800 VND`.
   - `Container 20FT` vẫn là `6.250 VND`.
7. Nhấn `Ctrl + F5`, mở lại đúng màn hình và kiểm tra hai giá trị vẫn tách biệt.

Kết quả bắt buộc: mỗi cấu hình được liên kết bằng đúng mã loại xe trong database, không phụ thuộc vị trí thẻ trong danh sách. Việc thêm, xóa hoặc đổi thứ tự loại xe không được làm cấu hình của xe này nhảy sang xe khác.

### 4.2 Kiểm tra cấu hình chi phí độc lập theo tiền tệ

1. Chọn `Container 20FT` và tiền tệ `VND`, nhập `Fuel Rate / 1 km = 6.250` rồi lưu.
2. Chuyển sang `LAK`, nhập một giá khác dễ nhận biết, ví dụ `12.000`, rồi lưu.
3. Chuyển sang `USD`, nhập `0,30`, rồi lưu.
4. Chuyển sang `THB`, nhập `10,50`, rồi lưu.
5. Chuyển qua lại giữa `VND`, `LAK`, `USD`, `THB`. Mỗi đồng tiền phải đọc lại đúng bộ giá riêng và không tự quy đổi.
6. Sửa một giá trị nhưng chưa lưu, sau đó thử đổi tiền tệ hoặc đổi loại xe. Hộp cảnh báo phải có ba lựa chọn:
   - `Lưu thay đổi và chuyển`.
   - `Bỏ thay đổi`.
   - `Ở lại`.
7. Chọn `Ở lại`: form giữ nguyên bản nháp. Chọn `Bỏ thay đổi`: hệ thống bỏ bản nháp và tải bộ được chọn. Chọn `Lưu thay đổi và chuyển`: chỉ chuyển sau khi API lưu thành công.
8. Nhấn `Ctrl + F5` rồi kiểm tra lại cả bốn đồng tiền.

Kết quả bắt buộc: khóa cấu hình có dạng `vehicle-type::<mã loại xe>::<tiền tệ>`; cùng một loại xe có thể có bốn bộ giá độc lập. Nếu closeout của SO dùng LAK, hệ thống phải dùng đúng cấu hình LAK; thiếu cấu hình phải báo `COST_FORMULA_REQUIRED`, không lấy VND thay thế.

### 4.3 Thử cập nhật tỷ giá tham chiếu 12 giờ

Tỷ giá từ API chỉ là số tham chiếu. Hệ thống không tự ghi đè tỷ giá vận hành đang dùng cho cước phí và hóa đơn.

1. Đăng ký API key thử nghiệm tại Open Exchange Rates.
2. Trong đúng cửa sổ PowerShell dùng để mở app, cấu hình biến môi trường trước khi chạy Uvicorn:

```powershell
$env:OPEN_EXCHANGE_RATES_APP_ID="API_KEY_CUA_ANH"
$env:EXCHANGE_RATE_REFRESH_HOURS="12"
C:\Users\zinnn\miniconda3\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
```

3. Vào `Master Data` → `Quản lý tỷ giá tiền tệ ngoại tệ`.
4. Kiểm tra dòng trạng thái có nguồn `Open Exchange Rates`, thời gian cập nhật và nhãn `Tham chiếu chưa áp dụng`.
5. Bấm `Cập nhật tham chiếu`. Hệ thống nạp đề xuất cho `USD`, `THB`, `LAK` theo đơn vị VND nhưng chưa lưu vào database.
6. Bấm nút cập nhật thêm nhiều lần trong vòng 12 giờ. Backend phải trả dữ liệu cache và không gọi nhà cung cấp thêm.
7. Tải lại trang trước khi bấm lưu. Tỷ giá vận hành cũ phải còn nguyên.
8. Bấm `Cập nhật tham chiếu`, kiểm tra số liệu rồi bấm `Lưu tỷ giá mới` để duyệt áp dụng.
9. Nhấn `Ctrl + F5`; các tỷ giá đã duyệt phải được đọc lại từ database.
10. Dừng app, bỏ biến `OPEN_EXCHANGE_RATES_APP_ID`, mở lại và thử cập nhật. Hệ thống phải cảnh báo chưa cấu hình API key nhưng vẫn giữ nguyên tỷ giá vận hành.

Kết quả bắt buộc: lịch nền tối đa một request mỗi 12 giờ trong một tiến trình; thao tác lặp đọc cache; lỗi mạng, thiếu key hoặc dữ liệu nhà cung cấp không đầy đủ không được ghi đè tỷ giá đã duyệt.

### 4.4 Kiểm tra định dạng số và lịch sử tỷ giá

1. Tại ô USD, nhập `26.173,50`; tại máy tính quy đổi nhập `1.000` VND.
2. Kiểm tra kết quả USD là khoảng `$0,04`, không được hiển thị `$38,21`.
3. Thử lần lượt `26,173.50` và `25,450`. Hệ thống phải hiểu tương ứng là `26.173,50` và `25.450` VND cho một USD.
4. Kiểm tra ký hiệu Baht hiển thị là `฿`, không xuất hiện chuỗi lỗi mã hóa `à¸¿`.
5. Bấm `Lưu tỷ giá mới`, tải lại trang và kiểm tra nhóm `Đang áp dụng` đọc đúng giá vừa lưu từ database.
6. Lưu thêm một bộ tỷ giá hợp lệ khác. Kiểm tra nhóm `Lần áp dụng trước` giữ bộ giá cũ và bảng `Lịch sử tỷ giá đã duyệt` có cả hai lần.
7. Nhập `0`, số âm hoặc ký tự không hợp lệ ở một trong ba đồng tiền rồi thử lưu.

Kết quả bắt buộc: hệ thống chặn toàn bộ lần lưu không hợp lệ, không cập nhật một phần; `Đang áp dụng`, `Tham chiếu API` và `Lần áp dụng trước` luôn được phân biệt rõ. Máy tính quy đổi dùng tỷ giá đang nhập nhưng chỉ tỷ giá đã bấm lưu mới được dùng làm tỷ giá vận hành trong database.

## 5. Test QT → SO → DO

### 4.1 Báo giá QT

1. Vào `Quản lý quan hệ khách hàng & Bán hàng` → `Quotation`.
2. Tìm và mở `DEMO-QT-2026-001`.
3. Kiểm tra khách hàng, tuyến, loại xe, tiền tệ VND và giá bán.
4. Nếu QT đang ở bản nháp, bấm `Lưu` rồi `Duyệt báo giá`.
5. Tải lại danh sách và tìm lại QT.

Kết quả bắt buộc: QT có trạng thái `Đã duyệt`; giá và version được đọc lại từ database.

### 4.2 Sales Order

1. Từ QT đã duyệt, bấm `Tạo SO` hoặc mở tab `Sales Order`.
2. Mở `DEMO-SO-2026-001`.
3. Kiểm tra SO tham chiếu đúng `DEMO-QT-2026-001`, đúng khách hàng, tuyến và giá `3.600.000 VNĐ`.
4. Bấm `Xác nhận SO` nếu SO chưa xác nhận.
5. Tải lại trang và mở lại SO.

Kết quả bắt buộc: SO có trạng thái `Đã xác nhận`; giá nguồn không thay đổi.

### 4.3 Delivery Order

1. Từ SO đã xác nhận, bấm `Tạo lệnh DO`.
2. Mở `DEMO-DO-2026-001` bằng nút `Xem DO`.
3. Kiểm tra nguyên form DO: SO nguồn, khách hàng, tuyến, điểm đi, điểm đến, thời gian, tải trọng, pallet và thể tích.
4. Tải lại danh sách DO và tìm lại mã DO.

Kết quả bắt buộc: DO tồn tại trong database và ở trạng thái `Chờ vận chuyển`.

## 6. Test giới hạn tải xe

### Ca hợp lệ

- Hàng: `8.500 kg`, `18 pallet`, `24 m3`.
- Xe: tối đa `28.000 kg`, `22 pallet`, `33,2 m3`.
- Kết quả: được phép điều xe.

### Ca quá tải bắt buộc bị chặn

Tạo một DO test hoặc chỉnh dữ liệu bản nháp thành một trong các trường hợp:

- `28.001 kg`; hoặc
- `23 pallet`; hoặc
- `33,3 m3`.

Sau đó thử điều `DEMO-61H-112.34`.

Kết quả bắt buộc: API trả `CAPACITY_EXCEEDED`; không tạo phân công, không đổi trạng thái DO, xe hoặc tài xế.

### Kiểm tra gợi ý loại xe ngay trên Báo giá

1. Tạo QT nháp với hàng `30.000 kg`, `20 m3`, `10 pallet`.
2. Kiểm tra loại xe `20.000 kg` và `28.000 kg` bị vô hiệu hóa, không cho lưu QT với loại xe đó.
3. Nếu có loại xe `35.000 kg` hoặc lớn hơn và đồng thời đủ thể tích/pallet, loại xe vừa đủ nhất phải đứng đầu danh sách đề xuất.
4. Kiểm tra thẻ đề xuất hiển thị số lượng và tối đa ba biển số đang rảnh để tham khảo.
5. Xóa cấu hình pallet của một loại xe rồi nhập lô hàng có pallet. Hệ thống phải báo `CAPACITY_NOT_CONFIGURED`, không được coi giá trị `0` là không giới hạn.
6. Sang Điều phối và thử gán một chiếc xe thực tế không đủ tải dù loại xe đã phù hợp. API vẫn phải kiểm tra lại đúng biển số và trả `CAPACITY_EXCEEDED`.

Kết quả bắt buộc: QT gợi ý theo cấu hình `Loại xe`; Điều phối xác nhận lại theo năng lực và lịch của `chiếc xe thực tế`. Gợi ý không được bỏ qua rào tải ở backend.

## 7. Tạo Trip và điều xe

1. Vào `Lập kế hoạch vận hành` → `Trip`.
2. Chọn `DEMO-DO-2026-001` và bấm `Tạo Trip từ DO/FO`.
3. Chọn tuyến `DEMO-RT-VSIP2A-CATLAI`.
4. Kiểm tra các chặng được lấy từ Route Master, không nhập tuyến tự do.
5. Tại điểm giao Cát Lái, nhập người nhận `Nguyễn Văn An`, số điện thoại `0908123456`.
6. Bấm `Lưu Trip/Chặng`.
7. Tải lại trang và mở lại Trip vừa tạo.
8. Vào `Điều phối`, chọn xe `DEMO-61H-112.34` và tài xế `DEMO-DRV-002`.
9. Bấm `Chốt điều phối & xuất bến`.
10. Tải lại màn hình điều phối.

Kết quả bắt buộc:

- DO chuyển sang `Đang vận chuyển`.
- Trip chuyển sang `in_transit`.
- Phân công tài nguyên ở trạng thái hoạt động.
- Xe và tài xế chuyển sang trạng thái bận.
- Xe xuất hiện có lịch trong kế hoạch 7 ngày.

## 8. Tracking và sự kiện

1. Vào module `Theo dõi và kiểm soát` → `GPS / POD`.
2. Chọn đúng DO/Trip đang `Đang vận chuyển`.
3. Bấm `Cập nhật GPS` và kiểm tra bản đồ, xe, tài xế, tuyến, tốc độ và khoảng cách còn lại.
4. Mở `Chuỗi sự kiện`, kiểm tra check-in, pickup, arrival và POD theo thứ tự thời gian.
5. Mở `Sự cố` để xác nhận chức năng vẫn hoạt động độc lập.

Kết quả bắt buộc: DO `Chờ vận chuyển` không được đưa vào GPS live; chỉ DO đang vận chuyển mới được tracking.

## 9. Giao hàng, ký nhận và chốt giá

1. Vào module `Hoàn tất giao hàng`.
2. Ở tab `Chờ hoàn tất`, tìm DO đang vận chuyển.
3. Bấm `Xem DO` và kiểm tra toàn bộ form DO.
4. Bấm `Hoàn tất giao` để mở hồ sơ giao hàng.
5. Mở lần lượt từng điểm giao; không cần bung tất cả điểm giao cùng lúc.
6. Tại mỗi điểm giao, nhập:
   - Thời gian giao thực tế.
   - Kết quả `Giao đủ hàng`.
   - Người nhận `Nguyễn Văn An`.
   - Số điện thoại `0908123456`.
   - Tình trạng `Nguyên niêm phong, không móp vỡ`.
   - File POD JPG, PNG hoặc PDF.
7. Người nhận ký trực tiếp trong khung chữ ký: máy tính dùng chuột, điện thoại dùng cảm ứng.
8. Kiểm tra các dòng chi phí ban đầu được nạp từ cấu hình giá xe.
9. Sửa giá thực tế của dòng có thay đổi; dùng `Thêm khoản phí` cho chi phí mới ngoài cấu hình.
10. Ví dụ thêm:
    - Phí chờ bốc dỡ: `350.000 VNĐ`.
    - Phí cầu đường bổ sung: `120.000 VNĐ`.
11. Kiểm tra phép tính:
    - Giá SO ban đầu: `3.600.000 VNĐ`.
    - Khách hàng trả thêm: `470.000 VNĐ`.
    - Giá cuối DO: `4.070.000 VNĐ`.
12. Bấm `Hoàn tất giao hàng & chốt giá` đúng một lần.

## 10. Kiểm tra dữ liệu sau khi ký

Sau thông báo thành công, vào tab `Đã hoàn tất`, mở lại DO và kiểm tra biên nhận cập nhật:

| Đối tượng | Trạng thái bắt buộc |
|---|---|
| DO | `Delivered` |
| Trip | `Completed` |
| Freight Order | `Delivered` |
| POD | Có người nhận, thời gian, file và chữ ký |
| Closeout | Có giá ban đầu, phát sinh và giá cuối |
| AR Invoice | `Posted`, bằng giá cuối DO |
| Phân công | `Completed` |
| Xe | `Sẵn sàng` |
| Tài xế | `Rảnh (Sẵn sàng)` |
| Phụ xe | `Rảnh (Sẵn sàng)` |

Tải lại toàn bộ trang và mở lại DO lần nữa. Tất cả dữ liệu vẫn phải còn. Đây là bước chứng minh thao tác đã ghi thật vào database.

## 11. Kiểm tra Trung tâm Doanh thu và Chi phí Vận tải

Phần này thực hiện sau khi DO đã giao, POD đã ký, giá cuối đã chốt và hóa đơn AR đã được ghi sổ. Báo cáo chỉ lấy dữ liệu thật từ database; không tính DO đang chờ hoặc chuyến chưa hoàn tất vào doanh thu.

### 11.1 Mở báo cáo và chọn kỳ

1. Vào `Tổng quan` → `Tóm tắt & Phân tích`.
2. Mở thanh `Chọn góc nhìn` ngay dưới tiêu đề rồi chọn `Tổng quan P&L`. Trên điện thoại, bấm thanh này để mở danh sách một cột.
3. Chọn khoảng ngày bao phủ ngày ghi nhận của DO vừa hoàn tất.
4. Nếu cần, lọc theo khách hàng hoặc biển số xe.
5. Bấm `Tải lại dữ liệu`.

Kết quả bắt buộc:

- Số chuyến chỉ đếm Trip đã hoàn tất và có hóa đơn AR `Posted`.
- Doanh thu bằng tổng hóa đơn AR đã ghi sổ trong kỳ.
- Chi phí bằng tổng Actual Cost ở trạng thái `Approved`.
- Lợi nhuận gộp bằng `Doanh thu - Chi phí`.
- Biên lợi nhuận bằng `Lợi nhuận gộp / Doanh thu × 100%`.
- Biểu đồ đường hiển thị doanh thu, chi phí và lợi nhuận theo ngày.
- Biểu đồ cột hiển thị doanh thu theo khách hàng.
- Biểu đồ tròn hiển thị cơ cấu loại hàng hóa.

Với bộ dữ liệu demo chuẩn trong tháng `08/2026`, kết quả đối chiếu là:

| Chỉ tiêu | Giá trị kỳ vọng |
|---|---:|
| Số chuyến hoàn tất | `1` |
| Doanh thu ghi nhận | `4.670.000 VNĐ` |
| Chi phí đã duyệt | `2.380.000 VNĐ` |
| Lợi nhuận gộp | `2.290.000 VNĐ` |
| Biên lợi nhuận | `49,04%` |

### 11.2 Kiểm tra bảng doanh thu theo chuyến

1. Mở thanh `Chọn góc nhìn` và chọn mục `Doanh thu theo chuyến`.
2. Tìm dòng của `DEMO-DO-2026-003` hoặc DO vừa hoàn tất.
3. Kiểm tra các nhóm thông tin:
   - Ngày đi, số lệnh điều xe, ngày ghi nhận và số hóa đơn.
   - Điểm đi, điểm đến và công ty đại lý.
   - Tài xế, biển số đầu kéo, biển số rơ-moóc và mã số xe.
   - Khách hàng, loại hàng hóa, số chuyến, đơn vị tính và trọng lượng tấn.
   - Đơn giá và tổng tiền theo `KIP`, `THB`, `USD`, `CNY` và `VND`.
   - Ghi chú và các trường dữ liệu còn thiếu.
4. Các ngoại tệ chưa có tỷ giá phải để trống và xuất hiện trong cảnh báo dữ liệu thiếu; hệ thống không được tự đoán tỷ giá.
5. Bấm `Xuất CSV`.
6. Mở file `bao-cao-doanh-thu-van-tai.csv` và kiểm tra có đủ `23` cột, đúng mã DO và đúng tổng tiền.

Kết quả bắt buộc: dữ liệu trên bảng và file CSV giống nhau; tải lại trang vẫn cho cùng kết quả.

### 11.3 Kiểm tra Phiếu chi phí

1. Mở thanh `Chọn góc nhìn` và chọn mục `Phiếu chi phí`.
2. Tìm phiếu `T4-0428-08-EPL-DEMO` hoặc phiếu của Trip vừa hoàn tất.
3. Bấm `Xem phiếu` và kiểm tra:
   - Số phiếu, ngày lập, Trip và DO liên kết.
   - Loại xe, biển số xe, số máy và người quản lý xe.
   - Tài xế, khách hàng, điểm nhận hàng và điểm giao hàng.
   - Hình thức thanh toán, số hợp đồng và người kiểm tra.
   - Các dòng nhiên liệu và chi phí khác.
   - Tổng tiền và đơn vị tiền tệ.
4. Thử sửa ghi chú hoặc thông tin quản lý được phép sửa rồi bấm `Lưu phiếu`.
5. Đóng form, tải lại danh sách và mở lại phiếu.

Kết quả bắt buộc:

- Phiếu vẫn còn sau khi tải lại và giữ đúng nội dung vừa lưu.
- Phiếu liên kết đúng một Actual Cost đang hoạt động của Trip.
- Tổng phiếu bằng tổng các dòng Actual Cost đã duyệt.
- Thao tác lưu lặp lại với cùng khóa không tạo phiếu trùng.
- Người không có quyền tài chính phải bị từ chối và không thay đổi database.

### 11.4 Đối chiếu DO vừa hoàn tất với báo cáo

Đối với hồ sơ anh vừa tự tạo trong phần 3, kiểm tra chuỗi đối chiếu sau:

1. `QT đã duyệt` cung cấp giá bán ban đầu cho SO.
2. `SO đã xác nhận` giữ giá thương mại nguồn.
3. `DO Delivered` chứa giá cuối sau khoản khách hàng trả thêm.
4. `AR Invoice Posted` bằng giá cuối DO.
5. `Actual Cost Approved` bằng tổng chi phí vận hành thực tế.
6. Báo cáo ghi nhận doanh thu từ AR Invoice và chi phí từ Actual Cost.
7. Phiếu chi phí tham chiếu đúng Trip, DO, xe và tài xế của hồ sơ.

Ví dụ nếu giá SO ban đầu là `3.600.000 VNĐ`, khách trả thêm `470.000 VNĐ` và Actual Cost được duyệt là `2.380.000 VNĐ` thì:

- Doanh thu báo cáo: `4.070.000 VNĐ`.
- Chi phí báo cáo: `2.380.000 VNĐ`.
- Lợi nhuận gộp: `1.690.000 VNĐ`.

Nhấn `Ctrl + F5`, chọn lại đúng khoảng ngày và lọc theo DO/xe vừa thao tác. Kết luận đạt khi bảng, biểu đồ, CSV và phiếu chi phí vẫn đọc lại đúng dữ liệu từ database.

### 11.5 Kiểm tra bố cục phân tích và phân tách chức năng

1. Chọn lần lượt bốn mục `Tổng quan P&L`, `Bức tranh toàn cảnh`, `Doanh thu theo chuyến` và `Phiếu chi phí`; mỗi lần chỉ một vùng nội dung được hiển thị.
2. Chuyển qua lại giữa các mục và kiểm tra khoảng ngày, khách hàng, xe đã nhập vẫn được giữ nguyên.
3. Thu cửa sổ xuống kích thước điện thoại: thanh chọn vẫn hiển thị đủ tên mục hiện tại, menu xổ xuống xếp một cột và trang không được cuộn ngang toàn bộ.
4. Mở `Báo cáo & Phân tích`: trang này chỉ còn `SLA/KPI` và `Tender/Carrier`, không còn P&L, doanh thu theo chuyến hoặc phiếu chi phí.
5. Quay lại `Tóm tắt & Phân tích`, chọn `Bức tranh toàn cảnh` và kiểm tra các biểu đồ CRM, DO, xe, tài chính cùng biểu đồ tỷ trọng vẫn hiển thị.

Kết quả bắt buộc: desktop và điện thoại dùng cùng dữ liệu, chuyển mục không tải lại toàn trang và không làm mất bộ lọc đang chọn.

## 12. Quy tắc dừng bài test

Dừng ngay và ghi nhận lỗi nếu gặp một trong các trường hợp:

- Thông báo thành công nhưng tải lại không thấy dữ liệu.
- Quá tải nhưng vẫn điều xe được.
- DO đã giao nhưng Trip hoặc FO chưa hoàn tất.
- Đã ký nhưng không xem lại được chữ ký/POD.
- Giá cuối DO không bằng giá SO ban đầu cộng khoản khách hàng trả thêm.
- Hóa đơn chưa được ghi sổ hoặc khác giá cuối DO.
- Xe/tài xế vẫn bận sau khi hoàn tất giao hàng.
- Báo cáo có doanh thu của DO chưa giao hoặc hóa đơn chưa `Posted`.
- Báo cáo lấy chi phí `Draft` hoặc `Rejected` thay vì chỉ lấy Actual Cost `Approved`.
- Bảng, biểu đồ, CSV và phiếu chi phí cho số liệu không khớp nhau.
- Thông báo lưu phiếu thành công nhưng tải lại không còn dữ liệu.

## 13. Demo full luồng `demo_26_8_p3`

Script chạy thử hồ sơ độc lập từ Master Data đến báo cáo:

```powershell
$env:EPL_API_BASE = "http://127.0.0.1:8001"
C:\Users\zinnn\miniconda3\python.exe backend\scripts\run_demo_26_8_p3.py
```

Script tạo hoặc đọc lại loại xe, xe, tài xế chính, phụ xe, route đi/chiều về và công thức giá VND; sau đó thực hiện QT → SO → DO → Trip → điều phối → giao hàng/POD → quay đầu → Actual Cost → phiếu chi phí. Hồ sơ dùng mã `demo_26_8_p3-*`, không xóa hoặc làm mới dữ liệu `DEMO-*` cũ.

Kết quả lần chạy kiểm chứng ngày `26/08/2026`: DO `delivered`, Trip `completed`, có 3 chặng gồm 2 chặng giao hàng và 1 chặng `empty_return`, giá ban đầu `3.600.000 VNĐ`, phụ thu khách hàng `470.000 VNĐ`, giá cuối `4.070.000 VNĐ`, chi phí thực tế `1.550.000 VNĐ`, Actual Cost `approved`. Xe và hai nhân sự được cập nhật lại trạng thái sẵn sàng sau khi hoàn tất.

## 14. Kiểm tra Parking List, Packing List và tem QR kiện hàng

Phần này thực hiện sau khi SO và DO đã có đầy đủ dòng hàng. Parking List phải chụp dữ liệu thật từ DO/SO tại thời điểm tạo; không tự sinh tên hàng, barcode hoặc mã hàng chưa có trong dữ liệu nguồn.

### 14.1 Tự động tạo nhiều Packing List từ một DO

1. Vào `Nghiệp vụ` → `Parking List / Tem QR`.
2. Bấm `Tạo Parking List` và chọn đúng DO cần đóng hàng.
3. Kiểm tra phần xem trước đã hiện đúng khách hàng, tuyến, điểm giao, dòng hàng và tổng số kiện lấy từ DO/SO.
4. Nhập `Số Packing List cần tạo`. Ví dụ DO có `4` kiện thì có thể tạo `2` Packing List, mỗi hồ sơ nhận `2` kiện.
5. Bấm `Tạo tự động & sinh QR` đúng một lần.
6. Tải lại trang, tìm theo mã DO rồi mở lần lượt các Packing List vừa tạo.

Kết quả bắt buộc:

- Một DO được phép có nhiều Packing List; mỗi lần tạo sinh các version tiếp theo và không ghi đè hồ sơ cũ.
- Mỗi Packing List tham chiếu đúng DO, SO, Trip, khách hàng và tuyến nguồn mà không yêu cầu nhập lại thủ công.
- Hệ thống tự chia số kiện, số lượng hàng, khối lượng và thể tích giữa các Packing List; phần dư được phân bổ nhưng tổng cuối vẫn phải bằng đúng DO nguồn.
- Trong từng Packing List, danh sách hàng giữ đúng SKU, mô tả và đơn vị từ DO/SO.
- Tổng số tem QR của tất cả Packing List vừa tạo bằng tổng số kiện của DO; mỗi tem có token QR riêng.
- Không được nhập số Packing List lớn hơn tổng số kiện. API phải trả `PACKING_LIST_COUNT_EXCEEDS_PACKAGES` và không tạo hồ sơ dở dang.
- Barcode, Item ID Laos hoặc Item ID Thai chưa có ở nguồn phải để trống, không được tự đoán.

Ca đối chiếu đề nghị:

| Dữ liệu DO | Giá trị |
|---|---:|
| Tổng số kiện | `4` |
| Tổng số lượng hàng | `24` |
| Tổng khối lượng | `120 kg` |
| Tổng thể tích | `8 m3` |
| Số Packing List cần tạo | `2` |

Kết quả kỳ vọng: tạo `2` Packing List, mỗi hồ sơ có `2` kiện, `12` đơn vị hàng, `60 kg`, `4 m3` và `2` tem QR. Cộng hai hồ sơ phải khớp hoàn toàn với DO nguồn.

### 14.2 In tem và Packing List

1. Bấm `Tem QR` và kiểm tra mỗi tem có Store, Route, Wave, Gate, DO, số kiện, khối lượng, thể tích và QR riêng.
2. Bấm `Packing List` và kiểm tra bảng hàng có barcode, Item ID Laos, Item ID Thai, mô tả, Case, Piece và tổng khối lượng.
3. In tem hai lần, sau đó tải lại hồ sơ.
4. Kiểm tra lần in đầu có `printed_at`; lần in tiếp theo tăng `reprint_count`.
5. Quét QR bằng điện thoại hoặc mở đường dẫn QR trên trình duyệt.

Kết quả bắt buộc: QR mở đúng DO và đúng số kiện, chỉ trả dữ liệu vận hành tối thiểu; không lộ giá bán, chi phí, người dùng hoặc dữ liệu tài chính.

### 14.3 Đi qua trạng thái kho thật

Trạng thái không được chỉnh tay. Nhân viên chỉ quét QR; backend tự kiểm tra thứ tự và ghi lịch sử thật vào database.

1. Mở hồ sơ vừa tạo. Trạng thái ban đầu phải là `Sẵn sàng in tem`.
2. Bấm `Quét QR vào bãi chờ`, quét một tem bất kỳ thuộc hồ sơ rồi kiểm tra trạng thái tự chuyển thành `Đã vào bãi chờ`.
3. Bấm `Quét QR qua cổng`, quét một tem bất kỳ rồi kiểm tra trạng thái tự chuyển thành `Đã qua cổng`.
4. Bấm `Quét tem kiện đã bốc`, quét lần lượt từng tem của Packing List.
5. Sau tem đầu tiên, trạng thái hồ sơ vẫn phải là `Đã qua cổng`; tiến độ hiển thị `1/n kiện`.
6. Quét lại đúng tem đầu tiên. Tiến độ vẫn phải là `1/n kiện`, không được cộng trùng.
7. Quét hết các tem còn lại. Chỉ khi đủ `n/n kiện`, hồ sơ mới tự chuyển thành `Đã bốc hàng`.
8. Tải lại trang và mở tab `Lịch sử`. Các mốc phải còn nguyên, có thời gian và người thao tác.

### 14.4 Đối chiếu với Điều phối và giao hàng

1. Tạo Packing List cho DO thử nghiệm nhưng chỉ quét đến `Đã qua cổng`, chưa quét đủ kiện.
2. Vào `Điều phối`, chọn đúng DO/Trip, xe và nhân sự rồi thử `Chốt điều phối & xuất bến`.
3. Hệ thống phải chặn với mã `PACKING_LIST_NOT_LOADED`; DO, Trip, xe và nhân sự không được đổi trạng thái một phần.
4. Quay lại Parking List, quét đủ toàn bộ tem để hồ sơ chuyển thành `Đã bốc hàng`.
5. Chốt điều phối lại. Lần này được phép xuất bến và Packing List phải tự chuyển thành `Đã xuất bãi`; người dùng không có nút sửa tay mốc này.
6. Hoàn tất giao hàng, tải POD và ký nhận theo phần 3.9.
7. Sau khi DO chuyển thành `Delivered`, Packing List phải tự chuyển thành `Đã giao`.
8. Nhấn `Ctrl + F5`, mở lại Parking List và kiểm tra toàn bộ trạng thái, tem và lịch sử vẫn còn.

Lưu ý tương thích: DO chưa từng tạo Packing List vẫn đi theo luồng Điều phối cũ. Khi DO đã có Packing List đang hoạt động, tất cả Packing List của DO phải đạt `Đã bốc hàng` trước khi xuất bến.

Dừng bài test nếu gặp một trong các trường hợp:

- Thông báo tạo/in/chuyển trạng thái thành công nhưng tải lại không còn dữ liệu.
- Số tem khác số kiện hoặc hai kiện dùng chung QR/token.
- QR của kiện này mở sang DO hay kiện khác.
- Cho phép nhảy trạng thái kho không đúng thứ tự.
- Quét trùng một tem nhưng số kiện đã bốc vẫn tăng.
- Cho xuất bến khi Packing List chưa quét đủ kiện.
- Điều phối hoặc hoàn tất giao hàng thành công nhưng Packing List không tự chuyển sang `Đã xuất bãi` hoặc `Đã giao`.
- Packing List trên màn hình khác dữ liệu bản in hoặc khác dòng hàng DO/SO.
- In lại nhưng không lưu thời điểm in và số lần in lại vào database.
