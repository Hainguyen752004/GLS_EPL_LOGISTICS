# Dispatch Workbench Design

## Mục tiêu

Thiết kế lại màn Điều phối & Thực thi thành một bàn làm việc thống nhất, giúp điều phối viên nhìn thấy DO đang chờ, lịch xe theo thời gian và chi tiết đối tượng đang chọn trong cùng một ngữ cảnh.

## Phạm vi

- Chỉ thay đổi cấu trúc và hành vi hiển thị frontend.
- Giữ nguyên endpoint, payload ghi, dữ liệu PostgreSQL và trạng thái nghiệp vụ. Có thể tái sử dụng lời gọi GET Trip đã tồn tại ở module khác để đồng bộ lịch điều phối.
- Giữ các DOM ID mà `frontend/js/app.js` đang dùng để render dữ liệu.
- Không bổ sung dữ liệu mock vào màn thật và không tạo endpoint mới.
- Cho phép mở rộng các frontend builder trong `tms-cockpit-utils.js` để ghép dữ liệu đã có trong `appState`; không gọi thêm API.

## Thay thế cấu trúc cũ

- Gỡ ba tab trạng thái và bốn tab phân tích khỏi giao diện thường trực.
- `switchDispatchWorkState()` và `switchDispatchAnalysisTab()` không còn điều khiển việc ẩn/hiện hai workspace độc lập; chúng được loại bỏ hoặc giữ dưới dạng cầu nối tạm thời cho lời gọi cũ.
- `dispatch-primary-workspace` và `dispatch-calendar-panel` được hợp nhất thành một workbench desktop luôn có đủ ba vùng.

## Bố cục được duyệt

### Thanh đầu màn hình

- Tiêu đề `Bàn điều phối` và ngày làm việc.
- Ba chỉ số: DO chờ điều phối, chuyến đã lên lịch, xung đột cần xử lý.
- Các lệnh rõ ràng: làm mới và tạo lịch/điều phối.

### Cột trái: Hàng đợi DO

- Danh sách DO chưa được gán đủ xe, tài xế hoặc lịch xuất phát.
- Tìm kiếm ngắn gọn theo mã DO, khách hàng hoặc tuyến.
- Mỗi dòng chỉ hiển thị dữ liệu cần để ra quyết định: mã, tuyến, cửa sổ lấy/giao và lý do đang chờ.
- Chọn một DO cập nhật vùng chi tiết bên phải.
- Mỗi dòng DO là `<button type="button">` hoặc phần tử có semantics tương đương, hỗ trợ focus, `Enter` và `Space`; không dùng `div onclick`.
- Một DO nằm trong hàng đợi khi chưa thuộc Trip đã lên lịch và thỏa ít nhất một điều kiện: thiếu xe, thiếu tài xế, thiếu giờ bắt đầu/kết thúc hợp lệ hoặc trạng thái còn trước khi xuất phát.
- Thứ tự lý do: `xung đột tài nguyên` → `thiếu xe` → `thiếu tài xế` → `thiếu khung giờ` → `chờ điều phối`.
- Sắp xếp theo thời điểm lấy hàng sớm nhất; bản ghi không có thời điểm nằm cuối danh sách.

### Vùng giữa: Lịch xe theo khung giờ

- Mỗi hàng đại diện cho một xe/tài xế.
- Mỗi chuyến là một thanh thời gian trên lịch.
- Màu trạng thái dùng nhất quán; xung đột dùng màu cảnh báo.
- Chọn thanh chuyến cập nhật vùng chi tiết bên phải.
- Mỗi thanh chuyến là `<button type="button">`, có `aria-label` chứa mã chuyến, xe/tài xế, giờ bắt đầu/kết thúc và trạng thái.
- Trạng thái rỗng ngắn gọn, không sinh nút hoặc thông báo hành động giả.

### Cột phải: Chi tiết và thao tác

- Hiển thị DO/chuyến đang chọn, khung lấy/giao, tải trọng, tuyến/chặng, xe và tài xế.
- Chỉ hiện hành động phù hợp với đối tượng và trạng thái thực tế.
- Cảnh báo chỉ xuất hiện khi đã chọn một đối tượng.
- Trên màn hình hẹp, cột này trở thành drawer mở từ cạnh phải.

### Công cụ phụ

- Năng lực, cảnh báo và kế hoạch 7 ngày không còn là bốn tab ngang thường trực.
- Chúng được mở từ một menu/cụm công cụ phụ và hiển thị trong panel hoặc drawer theo ngữ cảnh.
- Bộ lọc chỉ xuất hiện khi lịch chính cần lọc, không chiếm một hàng trạng thái riêng.
- Nút `Công cụ` mở menu gồm Năng lực, Cảnh báo, Kế hoạch 7 ngày và Bộ lọc.
- Mỗi lần chỉ mở một panel phụ; nhấn lại mục đang mở, nút đóng hoặc `Escape` sẽ đóng panel.
- Nút có `aria-expanded`/`aria-controls`; panel phụ không thay đổi lựa chọn DO/chuyến hiện hành.
- Khi mở menu, focus chuyển vào mục đầu tiên; phím mũi tên di chuyển giữa các mục, `Enter`/`Space` chọn và `Escape` đóng rồi trả focus về nút `Công cụ`.
- Drawer dùng `role="dialog"`, `aria-modal="true"`, có tiêu đề được nối bằng `aria-labelledby`, khóa focus bên trong khi mở và trả focus về phần tử đã kích hoạt khi đóng.

## Dòng dữ liệu

1. `loadDispatchBoard()` tải DO, xe và tài xế như hiện tại, đồng thời tái sử dụng endpoint GET Trip và hàm chuẩn hóa Trip đã có trong ứng dụng để cập nhật `appState.transport_trips`. Đây là lời gọi đọc tới API hiện hữu, không thay đổi backend.
2. `renderDispatchCalendar()` lấy dữ liệu từ `window.TmsCockpit`, sử dụng ngày làm việc theo múi giờ trình duyệt; mặc định là ngày hiện tại.
3. Kết quả cập nhật ba chỉ số, hàng đợi, lane lịch và cảnh báo.
4. `selectedDispatchCalendarOrderId` chứa ID của đối tượng hiện hành, bất kể đối tượng là DO chưa xếp lịch hay Trip/chuyến đã xếp lịch. `selectDispatchDO()` và `selectDispatchCalendarItem()` đều cập nhật biến này.
5. Không tự chọn phần tử đầu tiên. Khi biến chọn rỗng hoặc đối tượng không còn trong dữ liệu, vùng chi tiết trở về trạng thái chưa chọn và không hiện hành động/cảnh báo.
6. `buildDispatchCalendarDetail()` trả thêm `kind`, DO liên quan và dữ liệu trình bày bằng cách ghép `delivery_orders`, `transport_trips` và dữ liệu tuyến trong `appState`. Trip nhiều DO hiển thị danh sách DO và tổng tải; tuyến/chặng lấy theo Trip, sau đó fallback về DO đầu tiên.
7. Vùng chi tiết và hành động render theo lựa chọn hiện hành.
8. Khi dữ liệu tải chậm, khung bàn điều phối xuất hiện trước; từng vùng dùng trạng thái skeleton/rỗng riêng.

## Lệnh

- `Làm mới` gọi luồng tải dữ liệu điều phối hiện có (`loadDispatchBoard()`), sau đó render lại. Nếu chỉ cần thay đổi bộ lọc hoặc lựa chọn, chỉ render lại từ `appState`.
- `Tạo lịch/Điều phối` mở đúng form gán tài nguyên hiện có cho DO đang chọn; bị vô hiệu hóa khi chưa chọn DO phù hợp.
- Không tạo endpoint, payload ghi hoặc quy tắc cập nhật PostgreSQL mới trong thay đổi này. Chỉ bổ sung lời gọi GET Trip tới endpoint đang được module khác sử dụng.

## Trạng thái và lỗi

- Chưa có dữ liệu: hiện cấu trúc màn hình và thông báo rỗng tại đúng vùng.
- Chưa chọn chuyến: ẩn hành động và cảnh báo dành cho chuyến.
- Thiếu xe/tài xế: hiển thị lý do tại DO và đưa thao tác gán tài nguyên vào cột phải.
- Trùng lịch: đánh dấu trực tiếp trên thanh lịch và trong chi tiết chuyến.
- Lỗi tải dữ liệu: giữ nguyên bố cục, hiện lỗi cục bộ cùng nút thử lại.
- Ba nguồn tải hiện có được xử lý độc lập: vùng nào có dữ liệu vẫn render; vùng lỗi giữ dữ liệu cũ nếu có và đánh dấu `Dữ liệu có thể chưa mới`.
- `Thử lại` gọi lại `loadDispatchBoard()`; skeleton kết thúc khi nguồn tương ứng thành công hoặc thất bại, không khóa toàn màn hình.

## Responsive

- Desktop từ `1280px`: ba vùng `260px / minmax(520px, 1fr) / 300px` cùng xuất hiện.
- Laptop `768px–1279px`: hàng đợi rộng `240px`, lịch chiếm phần còn lại; chi tiết mở dạng drawer bên phải rộng tối đa `360px`.
- Mobile dưới `768px`: hàng đợi là màn chính; lịch và chi tiết mở toàn màn hình theo lệnh, tránh bảng ngang.

## Kiểm tra chấp nhận

- Không còn hai tầng tab điều phối.
- Tại viewport `1440×900`, nhìn thấy đồng thời hàng đợi, lịch xe và chi tiết.
- Tại viewport `1024×768`, nhìn thấy hàng đợi và lịch; chi tiết mở/đóng bằng drawer và `Escape`.
- Tại viewport `390×844`, không có tràn ngang; lịch/chi tiết mở toàn màn hình.
- Chọn DO/chuyến cập nhật đúng một vùng chi tiết.
- Không tự chọn DO/chuyến đầu tiên sau render hoặc làm mới.
- Không có chữ chìm do thiếu tương phản.
- Không xuất hiện hành động hoặc cảnh báo chuyến khi chưa chọn chuyến.
- Các DOM ID dùng bởi renderer hiện tại vẫn duy nhất và tồn tại sau khi hợp nhất.
- Không có dữ liệu mock, không có endpoint mới và không có lời gọi ghi mới; chỉ cho phép thêm GET Trip hiện hữu vào luồng tải Dispatch.
- Các kiểm tra UI hiện có và kiểm tra nguồn tiếng Việt vẫn đạt.

## Kiểm tra thực thi

- Cập nhật `frontend/tests/dispatch-workbench-ui.test.js` để bỏ các assertion về `dispatch-state-*`, `dispatch-analysis-*`, `switchDispatchWorkState()` và `switchDispatchAnalysisTab()`.
- Static DOM assertions phải kiểm tra các selector: `#dispatch-workbench`, `#dispatch-queue`, `#dispatch-timeline`, `#dispatch-detail`, `#dispatch-tools-button`, `#dispatch-tools-panel` và xác nhận mỗi ID xuất hiện đúng một lần.
- Static JS assertions phải kiểm tra cả `selectDispatchDO()` và `selectDispatchCalendarItem()` cùng cập nhật `selectedDispatchCalendarOrderId`; `renderDispatchCalendar()` không fallback sang phần tử đầu tiên.
- Unit test frontend builder dùng fixture chỉ nằm trong file test để xác nhận: DO thiếu xe vào queue; Trip hợp lệ vào lane; Trip nhiều DO trả danh sách DO/tổng tải; không chọn đối tượng trả detail rỗng. Fixture không được đưa vào mã production.
- Không thêm dependency. Tạo test-local DOM harness tối thiểu ngay trong `dispatch-workbench-ui.test.js` (các stub `getElementById`, `querySelectorAll`, focus và keyboard event) để kiểm tra menu bằng phím mũi tên/`Escape`, drawer focus trap/return và action/cảnh báo ẩn khi chưa chọn.
- Static DOM test xác nhận hàng đợi và thanh timeline là `button`, có tên truy cập được và không còn `div onclick` cho hai loại đối tượng này.
- Chạy tối thiểu:
  - `node frontend/tests/dispatch-workbench-ui.test.js`
  - `node frontend/tests/workflow-status-ui.test.js`
  - `node frontend/tests/vietnamese-source-clean.test.js`
  - `node --check frontend/js/app.js`
- Kiểm tra viewport bằng công cụ trình duyệt hiện có tại `1440×900`, `1024×768`, `390×844`; nếu công cụ trình duyệt không khả dụng, báo rõ phần kiểm tra hình ảnh chưa thực hiện thay vì khẳng định đạt.
