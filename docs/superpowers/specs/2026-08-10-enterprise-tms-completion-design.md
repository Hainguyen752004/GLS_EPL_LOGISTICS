# EPL Enterprise TMS Completion Program Charter

**Date:** 2026-08-10

**Goal:** Nâng cấp EPL Logistics từ bản demo 0→7 thành hệ thống điều vận giao hàng nhất quán từ dữ liệu nền đến đối soát, sử dụng PostgreSQL làm nguồn dữ liệu duy nhất và không còn mock/hardcode trong luồng vận hành.

**Document role:** Đây là kiến trúc đích và thứ tự chương trình, không phải một implementation plan duy nhất. Mỗi đợt là một release độc lập, có design/spec, migration, acceptance scenarios và kế hoạch riêng. Release đầu tiên được đặc tả tại `2026-08-10-foundation-recovery-design.md`.

## 1. Phạm vi và chiến lược

Hệ thống được nâng cấp cuốn chiếu, giữ giao diện và dữ liệu hiện có. Mỗi đợt phải tạo migration tương thích ngược, test lỗi trước khi sửa, xác minh API, PostgreSQL và giao diện trước khi chuyển đợt tiếp theo.

Không viết lại toàn bộ ứng dụng trong một lần. Các phần đang hoạt động được giữ lại sau khi có characterization test; các phần trùng lặp hoặc placeholder được thay bằng module có trách nhiệm rõ ràng.

## 2. Luồng nghiệp vụ đích

1. Master Data: khách hàng, nhà cung cấp vận tải, địa điểm, hàng hóa, đơn vị tính, xe, loại xe, tài xế, giấy phép, thiết bị GPS, tuyến, bảng giá, công thức chi phí, tiền tệ, tài khoản kế toán, người dùng và vai trò.
2. Transportation Demand: ghi nhận nhu cầu, địa điểm lấy/giao, time window, hàng hóa, khối lượng, thể tích, pallet, yêu cầu dịch vụ.
3. Quotation/Contract/Rate: tính giá từ bảng giá và phụ phí có version; duyệt báo giá; giữ provenance đến nhu cầu và hợp đồng.
4. Sales Order: tạo từ báo giá đã duyệt và giữ liên kết nguồn.
5. Freight Unit: tách hoặc gom các dòng hàng thành đơn vị lập kế hoạch có tải trọng, thể tích, pallet và time window.
6. Planning/Consolidation: ghép freight unit, kiểm tra sức chứa, thời gian, tuyến và tối ưu có kết quả giải thích được.
7. Carrier/Tender: mời/đề xuất nhà vận tải, ghi nhận giá, chấp nhận/từ chối/hết hạn và chọn carrier.
8. Shipment/Freight Order: tạo chuyến vận tải gồm stops, freight units, phương tiện, tài xế, carrier và chi phí kế hoạch.
9. Warehouse Scheduling: appointment, check-in, loading, pickup và departure.
10. Dispatch: kiểm tra điều kiện pháp lý và lịch tài nguyên, khóa phân công đồng thời, phát lệnh.
11. Execution Events: GPS và sự kiện check-in, pickup, departure, arrival, unloading, delivery, failed/partial delivery, return.
12. POD/Exception/Claim: chứng từ, ảnh, chữ ký, người nhận, tình trạng hàng, sự cố và khiếu nại.
13. Actual Cost/Settlement: chi phí thực tế, AR invoice, AP invoice, đối soát carrier và bút toán cân bằng.
14. SLA/KPI: on-time pickup/delivery, ETA variance, planned/actual distance, utilization, incident rate, revenue, cost và margin.

## 3. Kiến trúc backend

### 3.1 Module boundaries

- `api/`: router HTTP mỏng; parse request, gọi service, chuẩn hóa response/error.
- `domain/`: trạng thái, transition policy, capacity/time-window rules và business errors; không phụ thuộc FastAPI.
- `services/`: use cases và transaction boundary cho từng bounded context.
- `repositories/`: truy vấn SQLAlchemy; không chứa quy tắc nghiệp vụ.
- `models/`: persistence models và quan hệ.
- `migrations/`: migration tăng dần, có kiểm tra trước/sau và không phá dữ liệu.
- `integrations/`: OSRM/Nominatim, GPS provider, file storage; có timeout và lỗi rõ ràng, không sinh dữ liệu giả.

`main.py` chỉ khởi tạo ứng dụng, middleware, lifecycle và gắn router. OpenCV/AI checkpoint được lazy-load trong router AI để lỗi thư viện AI không làm chết toàn bộ TMS.

### 3.2 Transaction and concurrency

Mỗi command nghiệp vụ chạy trong một transaction. Record thay đổi nghiệp vụ dùng trường `version`; client gửi expected version. Nếu version không khớp, API trả `409 VERSION_CONFLICT`, không ghi đè dữ liệu người khác.

Dispatch khóa hoặc kiểm tra nguyên tử xe, tài xế và time range. Một tài nguyên không được thuộc hai shipment có khoảng thời gian chồng lấn ở trạng thái active.

### 3.3 State machines

- Demand: `draft → submitted → quoted/planned → fulfilled`, có `cancelled`.
- Quotation: `draft → submitted → approved/rejected/expired`, chỉ draft/submitted được sửa theo quyền.
- Sales Order: `draft → confirmed → allocated → fulfilled`, có `cancelled` trước thực thi.
- Freight Unit: `open → planned → assigned → in_execution → completed`, có `cancelled`.
- Tender: `draft → published → offered → accepted/rejected/expired → awarded`.
- Shipment: `planned → approved → dispatched → checked_in → loading → picked_up → in_transit → arrived → unloading → delivered/partially_delivered/failed → closed`; nhánh `returning → returned`.
- Invoice/Settlement: `draft → validated → posted → partially_paid/paid`; điều chỉnh bằng reversal/credit note, không sửa bút toán đã post.

Mọi transition đi qua domain service, kiểm tra quyền và precondition, tăng version, ghi status event và audit log bất biến.

## 4. Mô hình dữ liệu bổ sung

Các bảng lõi mới: `transport_demands`, `demand_items`, `contracts`, `rate_cards`, `rate_rules`, `freight_units`, `freight_unit_items`, `carriers`, `tenders`, `tender_offers`, `shipments`, `shipment_stops`, `shipment_freight_units`, `resource_assignments`, `warehouse_appointments`, `execution_events`, `gps_devices`, `pod_documents`, `claims`, `actual_costs`, `ap_invoices`, `settlements`, `status_history`, `sla_definitions`, `kpi_snapshots`.

File POD/ảnh xe không lưu base64 tùy tiện trong bản ghi nghiệp vụ. Database lưu metadata, checksum, MIME type, kích thước và storage key. Local storage có thể dùng cho demo; interface cho phép chuyển sang object storage mà không đổi domain.

GPS/event dùng các trường tối thiểu: entity/object, event type, event time, record time, latitude, longitude, location, business step, disposition/status, source device/provider, actor, payload và idempotency key. Đây là mô hình tương thích tinh thần what/when/where/why/how của EPCIS, không tuyên bố chứng nhận EPCIS nếu chưa triển khai schema/interface chuẩn đầy đủ.

## 5. Quy tắc dispatch và planning

Dispatch bị từ chối nếu thiếu bất kỳ điều kiện nào:

- Shipment chưa được duyệt hoặc không có freight unit/stop.
- Xe không sẵn sàng, vượt tải trọng/thể tích/pallet hoặc trùng lịch.
- Đăng kiểm, bảo hiểm, bảo dưỡng đã quá hạn tại thời điểm chuyến.
- Tài xế không sẵn sàng, trùng ca/chuyến, bằng lái không phù hợp hoặc hết hạn.
- Thiếu tuyến/địa điểm/time window bắt buộc.
- Carrier/tender bắt buộc nhưng chưa awarded.

Tối ưu hóa không được trả số giả. Khi dịch vụ bản đồ lỗi, UI giữ dữ liệu chưa lưu, hiển thị lỗi và dẫn người dùng tới cấu hình địa điểm/tọa độ hoặc nhập khoảng cách có nguồn và quyền phù hợp.

## 6. Tài chính và đối soát

- Planned charge được snapshot từ rate card/rule tại thời điểm duyệt.
- Actual cost lấy từ distance, toll, fuel, handling, carrier invoice và adjustment có chứng từ.
- AR chỉ lập từ delivery/partial delivery đủ điều kiện theo hợp đồng.
- AP chỉ lập cho carrier/nhà cung cấp có shipment và settlement source.
- GL posting phải cân bằng debit/credit, gắn invoice/settlement và accounting period.
- Bản ghi posted không xóa/sửa; dùng reversal hoặc credit/debit adjustment.

## 7. Frontend và UX

Frontend được tách dần khỏi `app.js` và `index.html` thành module theo bounded context. Không để hai hàm global hoặc hai DOM ID cùng tên. Event handler được gắn bằng JavaScript module thay cho inline `onclick` ở phần được nâng cấp.

Mỗi màn hình có bốn trạng thái chuẩn: loading, success, empty và error. Không optimistic-success với command nghiệp vụ: chỉ cập nhật trạng thái thành công sau response commit từ backend. Lỗi dependency trả CTA cụ thể đến đúng tab Master Data.

Form có label liên kết bằng `for`, trường bắt buộc, validation tại trường, summary lỗi và quản lý focus. Modal có `role="dialog"`, `aria-modal`, tiêu đề, focus trap và trả focus khi đóng. Toast/status region dùng `aria-live`. Trạng thái nghiệp vụ hiển thị tiếng Việt thống nhất; thuật ngữ quốc tế chỉ đặt trong ngoặc khi cần cho người dùng nghiệp vụ.

Màn chi tiết shipment cung cấp timeline bất biến từ demand đến settlement, planned/actual route, tài nguyên, chứng từ, sự cố và tài chính.

## 8. Loại bỏ lỗi nền hiện tại

- Audit script phải dừng ngay khi lệnh native trả exit code khác 0 và không in PASS/FINISHED màu xanh khi có lỗi.
- Chuẩn hóa interpreter/venv; xử lý tương thích NumPy/OpenCV hoặc cô lập dependency AI.
- PostgreSQL health check phải phân biệt timeout, authentication, missing schema và migration failure.
- Xóa function assignment trùng, DOM ID trùng, dữ liệu DEMO trong màn vận hành, random distance và placeholder thành công giả.
- Trang test runner phải là UTF-8 thật và phân biệt API stress với browser E2E.
- Khóa sửa/xóa luôn được backend thực thi; frontend chỉ phản ánh quyền và trạng thái.

## 9. API và lỗi

Response lỗi thống nhất: `code`, `message_vi`, `field_errors`, `navigation_targets`, `correlation_id`. Các nhóm lỗi gồm validation 422, missing master data 422, unauthorized 401, forbidden 403, not found 404, state/version/resource conflict 409, integration unavailable 503.

Command hỗ trợ idempotency key để retry không tạo trùng. List API có phân trang, lọc, sắp xếp. Upload kiểm tra MIME, kích thước, checksum và quyền truy cập.

## 10. Kiểm thử và tiêu chí hoàn thành

### Test layers

- Domain unit tests cho mọi transition, capacity, time window, legal eligibility và finance balancing.
- API integration tests chạy database cô lập và chứng minh transaction rollback, idempotency, permission và version conflict.
- PostgreSQL audit chỉ đọc dữ liệu thật, kiểm tra orphan, trạng thái sai, overlap tài nguyên, distance inconsistency và bút toán mất cân bằng.
- Browser E2E click các nút/form/tab/modal thật; kiểm tra validation, keyboard, loading/error/empty, responsive và tiếng Việt.
- Stress test tách riêng; 5.000 scenario có seed/cleanup, concurrency profile và metrics, không được gọi là UI coverage.

### Definition of done per increment

Một increment chỉ hoàn thành khi test mới đã được quan sát thất bại trước implementation, sau đó pass; regression suite pass; migration pass trên PostgreSQL; không có mock/hardcode mới; UI xác nhận dữ liệu sau reload; audit script trả exit code đúng; và có hướng dẫn setup/demo tiếng Việt cập nhật.

## 11. Các đợt triển khai

1. Foundation recovery: audit, environment, PostgreSQL health, duplicate code/IDs, mock/hardcode, UTF-8 và truthful UI errors.
2. Workflow core: canonical states, immutable history, RBAC, versioning, backend locks và resource overlap.
3. Planning and execution: demand, freight unit, capacity/time windows, consolidation, carrier/tender, shipment, stops và warehouse events.
4. Visibility and finance: GPS/event, POD storage, exceptions/claims/returns, actual cost, AR/AP/settlement và KPI.
5. UX and assurance: modular frontend, accessibility, responsive behavior, browser E2E, stress profiles và demo documentation.

Không lập một kế hoạch code bao trùm cả năm đợt. Chỉ bắt đầu đợt kế tiếp sau khi release hiện tại đạt definition of done và đặc tả đợt kế tiếp được duyệt.

## 12. An toàn dữ liệu và triển khai

Không xóa dữ liệu sản xuất/demo hiện có bằng migration. Dữ liệu không ánh xạ được được đưa vào quarantine có lý do. Mọi cleanup destructive phải có dry-run, danh sách đích rõ ràng và cờ `--apply`. Backup/restore rehearsal được thực hiện trước migration lớn. Không ghi secret hoặc connection string vào log, test hoặc tài liệu.
