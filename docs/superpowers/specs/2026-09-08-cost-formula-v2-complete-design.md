# Công thức giá thành v2: thiết kế hoàn thiện

## Mục tiêu

Lấy `nhap_UI__duan/cost-formula-v2.html` làm chuẩn cho toàn bộ màn Công thức giá thành: bố cục ba cột, tỷ lệ, cây loại xe/xe, bảng cấu phần, sửa biểu thức ngay trong trang, xem trước, so sánh, lịch sử và thanh lưu thay đổi. Dữ liệu và thao tác phải đi qua backend thật. Không thay giao diện toàn ứng dụng hoặc các phân hệ đang được người khác sửa.

## Hiện trạng đã kiểm tra

- Có API đọc/lưu công thức và đánh giá biểu thức an toàn.
- Có bảng `CostFormula`, `VehicleCostOverride` và dịch vụ kế thừa giá theo loại xe.
- Ghi đè hiện chỉ chấp nhận năm khóa cố định: fuel, driver, toll, wh, rate. Cấu phần thêm mới chưa được hỗ trợ đầy đủ ở tầng xe.
- Công thức đang lưu biểu thức và lịch sử trong JSON; chưa có cơ chế bộ giá theo ngày hiệu lực được kiểm chứng xuyên suốt luồng nghiệp vụ.
- Có mô hình tiền tệ, lịch sử tỷ giá và trường snapshot tỷ giá trong hệ thống. Phải tái sử dụng, không tạo hệ thống tỷ giá song song.
- Mẫu HTML dùng dữ liệu cứng cho nhiều thao tác. Thông báo lưu, lấy tuyến và đồng bộ tỷ giá trong mẫu không chứng minh đã có backend.

## Phương án chọn

Mở rộng tương thích backend hiện có, thay phần trình bày bằng giao diện mẫu. Không viết lại toàn backend; cũng không nhúng nguyên trang mẫu chứa dữ liệu giả vào ứng dụng.

So với chỉ đổi CSS, phương án này xử lý được kế thừa, lịch sử và ngày hiệu lực thật. So với thay toàn bộ hệ thống giá, phạm vi nhỏ hơn và giữ được dữ liệu hiện tại.

## Hợp đồng nghiệp vụ

1. Công thức chuẩn thuộc loại xe. Xe riêng kế thừa biểu thức, chỉ ghi đè những đơn giá cần khác, kèm lý do. Bỏ ghi đè trả về giá chuẩn đang hiệu lực, không lưu một bản sao giá chuẩn vào xe.
2. Cấu phần động phải có khóa ổn định, nhãn, loại chi/thu và đơn vị tính. Chỉ cho ghi đè khóa thuộc công thức của loại xe đó; không nhận khóa tùy ý hoặc khóa thuộc loại xe khác.
3. Backend trả đủ cấu phần chuẩn, giá hiệu lực, nguồn chuẩn/ghi đè, lý do và biểu thức. Preview, báo giá và tính giá theo xe phải sử dụng cùng quy tắc phân giải.
4. Tách giá thành, cước khách và lợi nhuận. Không cộng chi và thu thành giá thành.
5. Chuyến mẫu chỉ thay ngữ cảnh xem trước. Chọn tuyến thật lấy dữ liệu tuyến thật và số chặng thật, không gán cứng km/tải trọng từ mẫu.
6. Đổi tiền hiển thị không được tự thay đơn vị của số đang lưu. Giá trị lưu, tỷ giá, ngày và nguồn tỷ giá phải xác định rõ. Không có tỷ giá thì báo thiếu, không giả lập đồng bộ thành công.
7. Bộ giá có phiên bản và thời điểm hiệu lực. Ghi đè theo xe cũng phải phân giải nhất quán theo phiên bản/thời điểm; không để giá tương lai vô tình áp dụng ngay.
8. Chứng từ đã chốt giữ snapshot giá, biểu thức, ngữ cảnh tính và tỷ giá đã sử dụng. Đổi giá chuẩn không tự sửa báo giá đã duyệt hoặc số tiền đã chốt. Muốn tính lại phải là thao tác rõ ràng có kiểm tra trạng thái và lịch sử.
9. Chỉ thông báo lưu thành công sau khi server commit và trả bản lưu hợp lệ. Lỗi 4xx/5xx giữ bản nháp; không nuốt lỗi hoặc hiển thị số 0 thay lỗi tải dữ liệu.
10. Lưu có kiểm tra phiên bản để tránh hai người ghi đè âm thầm. Nhập Excel phải xem trước, kiểm lỗi từng dòng và lưu theo giao dịch; không báo thành công một phần như thành công toàn bộ.

## Giao diện theo mẫu

- Trái: tìm loại xe/biển số, thống kê thật, chọn công thức chuẩn hoặc xe ngay trong cây. Xe được chọn hiển thị ngay giữa trang, không bật modal chỉnh xe cũ.
- Giữa: breadcrumb, bộ giá hiệu lực, bảng chi/thu, đơn giá chỉnh trực tiếp, nguồn giá, bỏ ghi đè, thêm/bỏ cấu phần, phần biểu thức với ba chế độ và trình sửa inline.
- Phải: ngữ cảnh chuyến mẫu, tuyến thật, kết quả, so sánh và lịch sử thật. Không để số liệu hard-code từ mẫu.
- Đầu trang: các đồng tiền có dữ liệu, tỷ giá, nhập giá, lịch sử, thêm loại xe. Chức năng thiếu backend phải được triển khai trước khi coi hoàn tất.
- Thanh thay đổi: lưu/hủy, số thay đổi, cảnh báo rời màn khi còn nháp. Hủy không ghi database.
- Responsive: đối chiếu cùng kích thước viewport với mẫu; máy nhỏ cuộn bảng có kiểm soát, không tràn cả trang hoặc chồng chữ.
- khi mà chuyển đơn vị tiền tệ hay làm cái gì đó đừng có salce zom ra zom vào nhé giữ 1 thiết kế 1 form thoi hiểu hong ví dự vnd thì nó bị nhảy nhỏ lại tự nhiên bath thái thì to ra thống nhât 1 form nhé

## Phạm vi backend

Ưu tiên giữ URL và các trường hiện có, bổ sung trường thay vì đổi nghĩa âm thầm. Dùng dịch vụ giá tập trung cho cấu phần động và biểu thức. Bổ sung phiên bản/hiệu lực và audit có migration bảo toàn dữ liệu, tái sử dụng hạ tầng tỷ giá và nhập file hiện có khi phù hợp.

Trước khi chốt migration, kiểm tra các consumer của `effective_cost`, các tuyến lưu báo giá/chuyển SO và tính giá đối soát. Không gắn toàn bộ việc nâng cấp vào `app.js` hoặc nhân bản bộ tính giá riêng cho từng màn.

## Thứ tự thực hiện

1. Cấu phần động và dữ liệu hiệu lực theo xe: test kế thừa, ghi đè, bỏ ghi đè, cô lập loại xe, biểu thức đúng.
2. Phiên bản bộ giá, hiệu lực, audit và kiểm tra ghi đồng thời; migration và test dữ liệu cũ.
3. Tiền tệ/tỷ giá và nhập giá có kiểm lỗi; không nhân bản bảng/API sẵn có.
4. Chuyển chọn xe và chỉnh giá sang inline, hoàn thiện toolbar, lịch sử, lưu/hủy theo mẫu.
5. Nối consumer nghiệp vụ, kiểm tra snapshot chứng từ, lỗi API và quyền truy cập.
6. Chạy test hồi quy, đối chiếu screenshot desktop/mobile và thao tác đọc lại sau lưu.

## Tiêu chí nghiệm thu

- Hai xe cùng loại: sửa chuẩn chỉ đổi phần kế thừa; giá ghi đè của xe kia giữ nguyên.
- Cấu phần thêm mới tính được ở cả chuẩn và xe, không chỉ hiện trên UI.
- Bộ giá trước/sau ngày hiệu lực trả đúng kết quả, chứng từ chốt trước đó không đổi tiền.
- Lưu rồi tải lại vẫn đúng; hủy hoặc API lỗi không tạo thay đổi database.
- Preview frontend và backend khớp cả biểu thức min/max và các đơn vị tính.
- Không có nút giả, dữ liệu mẫu hard-code, thông báo thành công giả hoặc modal chỉnh công thức/xe cũ.
- So sánh với file mẫu ở cùng viewport và ghi rõ mọi khác biệt còn lại; chưa đủ thì không tuyên bố giống 100%.

## Trạng thái

Người dùng đã duyệt ngày 08/09/2026, gồm phần bổ sung giữ nguyên kích thước form khi đổi tiền tệ. Đây là thiết kế được duyệt, không phải báo cáo đã triển khai toàn bộ. Tiến độ kiểm thử và phần còn lại được theo dõi trong tài liệu kế hoạch.
