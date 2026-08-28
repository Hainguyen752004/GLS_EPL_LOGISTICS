# Checklist đối chiếu Transportation Flow & Functional Forms

Ngày rà soát: 13/08/2026

Quy ước: **Có** = đã có backend và UI vận hành; **Một phần** = đã có nền hoặc một phía backend/UI; **Thiếu** = chưa đủ để dùng production.

## Cập nhật sau Trip/Return v011

| Nhóm | Trước | Sau | Ghi chú |
|---|---:|---:|---|
| Delivery Order / Trip | 88% | 91% | Một DO đã có thể liên kết nhiều Trip qua model/API. |
| Planning & Dispatch | 84% | 87% | Có Trip API, Trip/Leg và cockpit nền trong Operations Planning. |
| Trip Execution | 84% | 86% | Event/POD đã có cột lineage Trip/Leg; bước tiếp theo là bắt buộc ghi lineage ở mọi event mới. |
| Return / Backhaul | 55% | 68% | Có loại Trip, chặng empty return/backhaul và ETA lượt về; cockpit UI nền đã hiện. |
| Completion & Settlement | 78% | 80% | Cost đã có cột Trip/Leg để chuẩn bị phân bổ; settlement close Trip còn cần nối tiếp. |
| UI/UX vận hành | 72% | 76% | Có panel Trip & Return Cockpit để demo theo sơ đồ chuẩn rõ hơn. |

## Cập nhật sau Shipment 360 + Dispatch Resource Change

| Nhóm | Trước | Sau | Ghi chú |
|---|---:|---:|---|
| Shipment 360 / timeline | 76% | 82% | Click từng bước mở modal drill-down, hiện dữ liệu chính, checklist, hồ sơ liên quan và nút mở đúng form nghiệp vụ. |
| Dispatch / phân xe tài xế | 87% | 89% | Panel đổi xe/tài xế có mode, version kỳ vọng, lý do điều phối và idempotency key theo thao tác. |
| UI/UX vận hành | 76% | 78% | Giảm tình trạng “bấm nhận nhưng không hiện gì”; vẫn chưa gọi là thay toàn bộ UI 100%. |

## Cập nhật sau Settlement Readiness trong Shipment 360

| Nhóm | Trước | Sau | Ghi chú |
|---|---:|---:|---|
| Completion & Settlement | 80% | 83% | Shipment 360 đã có panel kiểm tra điều kiện chốt chuyến: trạng thái giao hàng, POD, Actual Cost, AP và đối soát km. |
| GPS / POD / Finance liên kết | 82% | 84% | Người dùng nhìn được thiếu POD/Cost/AP ở cùng một hồ sơ chuyến và mở đúng màn xử lý. |
| UI/UX vận hành | 78% | 79% | Demo dễ hiểu hơn ở bước cuối chuyến, nhưng chưa thay thế toàn bộ Finance Cockpit chi tiết. |

## 1. Delivery Order (DO) — 88%

| Chức năng trong sơ đồ | Trạng thái | Ghi chú EPL |
|---|---|---|
| Sales Order → Delivery Order | Có | Có luồng QT → SO → DO và khóa bản ghi sau duyệt/chốt. |
| Tuyến, hàng, số lượng, ngày yêu cầu | Có | Có route context, khung lấy/giao, tải trọng, thể tích, pallet. |
| Ước tính chi phí | Có | Có công thức giá, actual cost và snapshot tiền tệ/thuế. |
| Duyệt quản lý | Có | Có transition, version và audit. |
| Một DO có nhiều Trip | Một phần | Model `TripDeliveryOrder` đã hỗ trợ; API/UI và migration v011 đang hoàn thiện. |

## 2. Planning & Dispatch — 84%

| Chức năng trong sơ đồ | Trạng thái | Ghi chú EPL |
|---|---|---|
| Kiểm tra xe/tài xế | Có | Có tải trọng, thể tích, pallet, trạng thái và chống trùng thời gian. |
| Bảo dưỡng/đăng kiểm/bảo hiểm/bằng lái | Có | Backend kiểm tra trước dispatch; lỗi hướng về Master Data. |
| Phân xe và tài xế | Có | Có Resource Assignment và Dispatch Board. |
| Tạo Trip Plan nhiều chặng | Một phần | Model/service Trip + Leg và ETA tuần tự đã có; UI cockpit chưa hoàn tất. |
| Gửi tài xế/thông báo | Thiếu | Chưa có gateway notification/mobile production. |
| Calendar/Gantt phân bổ | Thiếu | Dispatch Board hiện chưa phải lịch kéo-thả theo thời gian. |

## 3. Trip Execution — 84%

| Chức năng trong sơ đồ | Trạng thái | Ghi chú EPL |
|---|---|---|
| Check-in, pickup, departure, arrival, unloading, delivered | Có | Event store đã có chuỗi sự kiện, actor, thời gian, vị trí, nguồn thiết bị. |
| GPS realtime/latest position | Có | Có API vị trí mới nhất và bản đồ; cần gắn bắt buộc theo Trip/Leg mới. |
| POD ảnh/chữ ký | Có | Một DO có nhiều POD theo xe/điểm dừng. |
| POD theo Trip/Leg/xe/stop | Một phần | Model lineage và unique theo Trip đã có; integration/API đang hoàn thiện. |
| Driver accepts trip | Thiếu | Chưa có command tài xế nhận/từ chối chuyến riêng. |

## 4. Return / Backhaul — 55%

| Chức năng trong sơ đồ | Trạng thái | Ghi chú EPL |
|---|---|---|
| One-way/Round-trip/Backhaul/Multi-stop | Một phần | Domain đã có đủ loại chuyến. |
| Empty Return | Một phần | Leg không cần DO và ETA về đã tính được. |
| Backhaul bằng DO chiều về | Một phần | Leg backhaul bắt buộc gắn DO thuộc Trip. |
| Warehouse Transfer/Another DO | Một phần | Domain hỗ trợ leg/DO; chưa có UI chọn và điều phối hoàn chỉnh. |
| ETA lượt đi/lượt về cập nhật | Một phần | Công thức tuần tự đã có; chưa nối actual GPS/event để tái dự báo liên tục. |
| Return Cockpit | Thiếu | Chưa mở ra UI production. |

## 5. Completion & Settlement — 78%

| Chức năng trong sơ đồ | Trạng thái | Ghi chú EPL |
|---|---|---|
| Actual km/cost/fuel/toll/driver | Có | Actual Cost và đối chiếu khoảng cách GPS đã có. |
| Cost allocation theo DO/Trip Leg | Một phần | Cột phân bổ trên Leg đã có; finance lineage theo Trip còn đang nối. |
| Profit theo Trip/DO | Một phần | Có P&L tổng quan; drill-down Trip/Leg chưa hoàn chỉnh. |
| Close Trip | Thiếu | State machine completed → settled đang được bổ sung. |

## 6. Accounting & Reporting — 82%

| Chức năng trong sơ đồ | Trạng thái | Ghi chú EPL |
|---|---|---|
| AR Invoice | Có | Luồng hóa đơn khách hàng hiện hữu. |
| AP/Expense | Có | Cost → AP, duyệt, hạch toán và reversal. |
| Payment/Settlement | Có | Thanh toán, settlement, bút toán và idempotency. |
| GL Posting | Có | Journal cân bằng, mapping tài khoản từ Master Data. |
| P&L/Reports | Một phần | Có dashboard; drill-down theo Trip/Leg/SLA còn thiếu. |

## Supporting Forms

| Form | Trạng thái |
|---|---|
| Vehicle Master + ảnh xe | Có |
| Driver Master + ảnh tài xế | Có |
| Route Master/Segments | Có |
| Cost Formula/Price List | Có |
| Incident Report | Có |
| Vehicle Assignment | Có |
| Driver mobile app/notification | Thiếu |
| Trip Planning form | Đang hoàn thiện |
| Return/Backhaul form | Đang hoàn thiện |
| Trip Settlement drill-down | Đang hoàn thiện |

## Kết luận hiện tại

EPL đã bao phủ tốt DO, dispatch, execution event, POD và tài chính. Khoảng cách lớn nhất so với sơ đồ chuẩn không phải là thêm một nút, mà là lớp thực thi **Trip/Trip Leg** xuyên suốt. Model và phép tính ETA lượt đi/lượt về đã được bổ sung; chỉ được nâng tỷ lệ Return/Backhaul và Trip Settlement lên mức production sau khi hoàn tất API có xác thực, migration PostgreSQL v011, lineage GPS/POD/Finance và cockpit UI.

## Cập nhật sau Finance Closeout Workbench

| Nhóm chức năng | Trước | Sau | Ghi chú |
|---|---:|---:|---|
| Chi phí/AP/settlement | 82% | 85% | Finance Cockpit đã có Closeout Workbench gom Actual Cost → AP → Payment/Settlement, chỉ rõ hồ sơ nào cần tạo AP, hạch toán AP hoặc thanh toán/đối soát. |
| UI/UX tài chính | 79% | 81% | Người dùng không còn chỉ thấy danh sách rời; có worklist hành động kế tiếp. Vẫn chưa phải màn kế toán chuyên sâu đầy đủ như SAP/Oracle. |
| Shipment 360 → tài chính | 76% | 79% | Shipment 360 đã có readiness settlement; Finance Cockpit có điểm mở hồ sơ tài chính để kiểm tra tiếp. |

### Việc còn yếu sau bước này

- Chưa có màn payment entry/phân bổ thanh toán nhiều AP thật đẹp.
- Chưa có drill-down bút toán GL theo từng dòng ngay trong cockpit.
- Chưa có calendar/Gantt điều phối xe.
- Tender/carrier cockpit vẫn cần nâng thành màn vận hành riêng nếu khách có thuê ngoài nhiều.
- Timeline 360 đã mở đúng ngữ cảnh hơn, nhưng từng bước vẫn cần nối sâu hơn tới form nghiệp vụ thật khi API hoàn thiện.

## Cập nhật quan hệ DO ↔ xe/chuyến và lượt quay đầu

| Hạng mục | Trước | Sau | Ghi chú |
|---|---:|---:|---|
| Quan hệ DO ↔ Trip/xe | 82% | 86% | API Trip trả `relationship_summary`: 1 xe/chuyến gom nhiều DO, và 1 DO có thể chia qua nhiều xe/chuyến. |
| POD theo trách nhiệm giao hàng | 84% | 86% | Quy ước nghiệp vụ rõ hơn: POD gắn theo từng DO/điểm giao trên từng xe/chuyến, không dùng một POD chung mơ hồ cho nhiều xe. |
| ETA lượt về/quay đầu | 76% | 82% | Trip trả `return_distance_km`, `total_distance_km`, `planned_return_at`; UI hiển thị “Quãng đường quay đầu” để điều phối biết xe rảnh lại khi nào. |
| UI Trip/Return Cockpit | 72% | 78% | Work item hiển thị “1 xe/chuyến đang gom N DO”, “DO chia nhiều xe/chuyến”, tổng quãng đường và quãng đường quay đầu. |

### Quy ước nghiệp vụ đã chốt

- **DO** là nhu cầu giao hàng.
- **Trip** là lần xe chạy thực tế.
- **1 Trip/xe có thể gom nhiều DO** nếu cùng tuyến, cùng khung giờ và còn đủ tải/trọng lượng/thể tích/pallet.
- **1 DO có thể chia nhiều Trip/xe** nếu hàng lớn, nhiều điểm giao, hoặc cần giao nhiều đợt.
- **POD phải gắn theo DO + xe/chuyến + điểm dừng**, vì trách nhiệm giao nhận nằm ở từng xe/tài xế và từng điểm giao.
- **Quãng đường quay đầu** nằm ở chặng `empty_return` hoặc `backhaul`; thời gian dừng trước khi quay đầu nhập bằng `dwell_minutes` trên chặng quay đầu.

## Cập nhật Dispatch Calendar/Gantt theo Trip và lượt quay đầu

| Hạng mục | Trước | Sau | Ghi chú |
|---|---:|---:|---|
| Dispatch / phân xe tài xế | 84% | 87% | Calendar/Gantt ưu tiên `transport_trips`, hiển thị xe/tài xế, DO gom/chia, giờ đi, giờ quay đầu và cảnh báo trùng lịch. |
| Lập lịch xe theo thời gian rảnh | 70% | 80% | Block lịch kết thúc ở `planned_return_at` nếu có, nên dispatcher biết xe rảnh lại lúc nào để xếp đơn kế tiếp. |
| UI/UX điều phối | 78% | 82% | Trên thanh Gantt có thêm “gom N DO”, “DO chia nhiều xe/chuyến”, “Quay đầu X km”, giúp người dùng hiểu nhanh thay vì phải mở chi tiết. |

### Việc còn thiếu để Dispatch giống app lớn hơn

- Chưa có kéo-thả đổi giờ trực tiếp trên Gantt.
- Đã có Week Planner 7 ngày cho từng xe; vẫn chưa có chế độ tháng/nhiều depot.
- Chưa có thuật toán tự tối ưu ghép tải theo khung giờ, tải trọng, thể tích và tuyến.
- Đã có cảnh báo bảo dưỡng/đăng kiểm/bảo hiểm/bằng lái hiển thị ngay trên block Gantt; vẫn cần đồng bộ sâu hơn với rule dispatch backend khi chốt production.

## Cập nhật cảnh báo điều kiện xe/tài xế trên Gantt

| Hạng mục | Trước | Sau | Ghi chú |
|---|---:|---:|---|
| Cảnh báo đăng kiểm/bảo hiểm/bảo dưỡng xe | 65% | 82% | Dispatch Calendar đọc `inspection_exp`, `insurance_date`, `maintenance_date` và cảnh báo hết hạn/sắp hết hạn ngay trên chuyến. |
| Cảnh báo bằng lái/trạng thái tài xế | 65% | 80% | Calendar đọc `license_exp`/trạng thái tài xế và đưa cảnh báo vào chi tiết chuyến. |
| UI/UX điều phối | 84% | 86% | Dispatcher không cần mở từng Master Data mới biết xe/tài xế có vấn đề; block Gantt và panel cảnh báo đã báo ngay. |

### Ghi chú kiểm chứng UI/UX

- Đã chạy bộ contract cho button/vùng UI chính.
- Đã chạy test tiếng Việt `vietnamese-source-clean`.
- Chưa thể gọi là review UI/UX 100% theo nghĩa người dùng thật click thủ công toàn bộ trình duyệt; phần đã kiểm chứng là bằng automated frontend tests và kiểm tra cú pháp JS.

## Cập nhật Vehicle Week Planner

| Hạng mục | Trước | Sau | Ghi chú |
|---|---:|---:|---|
| Calendar nhiều ngày/tuần | 45% | 70% | Dispatch có bảng 7 ngày theo từng xe, hiển thị ngày nào bận/rảnh và giờ xe rảnh lại sau chuyến/quay đầu. |
| Khả năng xếp đơn kế tiếp | 80% | 84% | Dispatcher nhìn được xe nào rảnh trong tuần để ưu tiên ghép đơn mới hoặc backhaul. |
| UI/UX điều phối | 82% | 84% | Daily Gantt xử lý chi tiết trong ngày; Week Planner cho góc nhìn năng lực xe theo tuần. |

## Cập nhật UI Health Checklist / Demo Readiness

| Hạng mục | Trước | Sau | Ghi chú |
|---|---:|---:|---|
| UI Health / sẵn sàng demo | 50% | 78% | Dashboard có checklist tổng thể theo nhóm nghiệp vụ và nút mở đúng màn/tab còn thiếu cấu hình. |
| Điều hướng “click là thấy form” | 72% | 80% | Các cảnh báo thiếu Master Data/Dispatch/GPS/Finance có action trỏ về đúng view, đúng tab hoặc đúng panel nghiệp vụ. |
| Kiểm soát lỗi tiếng Việt phần mới | 80% | 84% | Phần UI Health dùng chuỗi UTF-8 sạch và đã chạy kiểm tra `vietnamese-source-clean`. |

### Việc vẫn chưa gọi là 100%

- Chưa thay toàn bộ UI thành một shell mới hoàn toàn như SAP Fiori; hiện đang nâng từng cockpit/form theo hướng an toàn cho demo.
- Một số chuỗi cũ trong tài liệu/test lịch sử còn mojibake, cần một lượt chuẩn hóa encoding riêng nếu muốn làm sạch tuyệt đối.
- Vẫn cần thêm manual browser pass: mở từng view, click từng button nghiệp vụ, kiểm tra dữ liệu thật từ PostgreSQL và ảnh/form upload trên trình duyệt thật.
