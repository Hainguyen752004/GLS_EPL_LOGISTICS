# EPL Foundation Recovery Design

**Date:** 2026-08-10

**Goal:** Làm cho bản EPL hiện tại khởi động, kiểm tra, báo lỗi và lưu PostgreSQL một cách trung thực; loại bỏ các nguyên nhân trực tiếp gây UI sai dữ liệu trước khi thêm nghiệp vụ mới.

**In scope:** audit runner, dependency isolation, PostgreSQL health, duplicate API/JS/DOM identifiers, random/demo operational data, truthful command UI, UTF-8 runner và test coverage cho các lỗi này.

**Out of scope:** thêm demand/freight unit/tender/AP/KPI, thay toàn bộ UI, tối ưu nhiều điểm, authentication mới, object storage production và stress performance certification. Các phần này thuộc release sau trong program charter.

## 1. Release boundaries

### Application shell

`main.py` tạo FastAPI, middleware, lifecycle và include routers. Import ứng dụng không được phụ thuộc OpenCV. AI checkpoint tự import OpenCV/NumPy khi endpoint được gọi; nếu dependency không dùng được, chỉ endpoint đó trả lỗi `503 AI_DEPENDENCY_UNAVAILABLE` bằng tiếng Việt.

### Workflow API ownership

`routes/workflow_routes.py` là chủ sở hữu duy nhất của quotation, sales order, delivery order, dispatch và POD command/list endpoints. Endpoint trùng trong `main.py` được gỡ sau khi characterization tests chứng minh router chính giữ response contract frontend đang dùng. Các endpoint master data, dashboard, tracking, accounting và incident vẫn ở `main.py` trong release này.

### Frontend ownership

Các hàm workflow chỉ có một implementation có hiệu lực. Trong release này chưa tách toàn bộ `app.js`; thay vào đó tạo kiểm tra tĩnh cấm function assignment trùng và DOM ID trùng. ID đổi tên phải cập nhật đồng thời HTML, JavaScript và test.

## 2. Audit runner contract

`RUN_AZ_AUDIT.ps1` chọn Python theo thứ tự xác định: (1) đường dẫn tuyệt đối trong `EPL_PYTHON`; (2) `$env:VIRTUAL_ENV\Scripts\python.exe`; (3) executable đầu tiên từ `Get-Command python`. Mỗi candidate phải tồn tại và chạy được `--version`. Không có candidate hợp lệ thì audit dừng với mã khác 0; không tự dùng `py` hoặc đường dẫn Miniconda hardcode.

Sau đó script chạy tuần tự:

1. JavaScript syntax và frontend unit/static tests.
2. Python compile và backend tests bằng chính interpreter đang chạy script, ưu tiên active virtual environment; cho phép override qua `EPL_PYTHON`.
3. PostgreSQL health/data audit sử dụng `EPL_ENV_FILE`.

Sau mỗi native command, script kiểm tra `$LASTEXITCODE`. Khi khác 0, script dừng, in tên bước lỗi màu đỏ và `exit` đúng mã khác 0. Dòng `A-Z AUDIT PASSED` chỉ xuất hiện khi cả ba nhóm đạt. Không dùng từ “FINISHED” màu xanh cho một run lỗi.

PostgreSQL audit timeout hoặc authentication/schema failure phải làm audit thất bại. Secret và password không được xuất log.

## 3. Dependency and database health

- Import `main` và các test không import `cv2` ở module scope.
- Endpoint `/api/health` trả `200` khi process sống. `/api/health/database` thực hiện `SELECT 1`, đọc `schema_migrations` và xác minh migration head mà code hiện tại yêu cầu đã được áp dụng, đồng thời kiểm tra các bảng lõi `customers`, `routes`, `vehicles`, `drivers`, `quotations`, `sales_orders`, `delivery_orders`. Endpoint trả:
  - `200 {status: "ok", database: "postgresql"}` khi kết nối được.
  - `503` với code `DATABASE_TIMEOUT`, `DATABASE_AUTH_FAILED`, `DATABASE_SCHEMA_INVALID` hoặc `DATABASE_UNAVAILABLE` tùy nguyên nhân.
- Startup lưu trạng thái migration failure gần nhất. Một lần health check kết nối thành công không xóa cờ này; chỉ một lần chạy migration thành công trong cùng process mới xóa cờ. Khi cờ còn tồn tại, readiness trả `DATABASE_SCHEMA_INVALID` kèm correlation ID, không lộ SQL/credential.
- Không tự fallback SQLite khi `DATABASE_MODE=postgres`.
- Startup migration lỗi được ghi log có correlation ID; readiness database vẫn `503`, không được hiển thị dashboard như đã sẵn sàng.

## 4. Truthful workflow and UI behavior

Command tạo/sửa/duyệt/dispatch/POD chỉ cập nhật state frontend sau response HTTP 2xx và sau đó reload entity từ API. Khi lỗi:

- Giữ nguyên state trước command.
- Hiển thị thông báo tiếng Việt gồm nguyên nhân và hành động tiếp theo.
- Nếu lỗi missing master data có `navigation_targets`, hiển thị nút đi đến tab tương ứng.
- Không có câu “đã cập nhật tạm thời trên giao diện”.

Backend là lớp bắt buộc khóa sửa/xóa record đã duyệt/xác nhận/đang chạy. Frontend ẩn hoặc disable action tương ứng nhưng không được xem đó là kiểm soát duy nhất.

## 5. Removal of fake operational data

- Khi geocoding/routing không xác định được distance, `addRouteSegment` không thêm row và không lưu route. UI yêu cầu kiểm tra địa điểm/tọa độ Master Data hoặc nhập khoảng cách thủ công có xác nhận.
- Khoảng cách thủ công dùng km, lớn hơn 0 và không quá 5.000 km cho một segment; người dùng phải đánh dấu xác nhận “Khoảng cách nhập thủ công” và chọn nguồn `odometer`, `carrier_document`, `map_measurement` hoặc `other`. Segment lưu `distance_source`, `distance_verified_by` và `distance_verified_at`; release này có thể lưu ba trường trong `segments_json` để tránh migration phá vỡ.
- Không dùng `Math.random()` để tạo distance, ETA, GPS progress, utilization hay số nghiệp vụ. ID do backend sinh; ID tạm UI dùng `crypto.randomUUID` chỉ cho correlation/client key, không làm dữ liệu nghiệp vụ.
- Bảng/card vận hành trong `index.html` không chứa record `DEMO-*`, số 200 km hoặc xe/tài xế cụ thể. Empty state được render cho đến khi API trả dữ liệu.
- Placeholder ví dụ trong input được phép nếu có tiền tố “Ví dụ” và không được tính/lưu như giá trị.
- Bản ghi `DEMO-*` đã tồn tại trong PostgreSQL được giữ nguyên để không phá dữ liệu. API operational vẫn trả chúng như dữ liệu bình thường nhưng frontend gắn nhãn “Dữ liệu demo” dựa trên prefix. Release này không tự xóa, quarantine hay ẩn chúng; cleanup chỉ thực hiện bằng script dry-run/`--apply` được người dùng chủ động chạy.

## 6. UTF-8 and Vietnamese

Tất cả HTML/JS/Python/Markdown thuộc release lưu UTF-8. Static test quét các mẫu mojibake thường gặp trong cả main UI và test runner. Runner hiển thị đúng “Kịch bản”, “Kiểm thử”, “Mở màn hình”, “Tạm dừng”, “Tiếp tục” và “Dừng”. Trạng thái workflow dùng mapping tiếng Việt hiện có; API giữ canonical status machine-readable.

## 7. Duplicate prevention

Static tests thất bại khi:

- Một HTML document có hai phần tử cùng `id`.
- `app.js` gán cùng `window.functionName = function` hoặc `window.functionName = async function` nhiều hơn một lần.
- FastAPI có trùng method + normalized path sau khi application được import. Normalization bỏ trailing slash (trừ `/`) và thay mọi path parameter `{name}` bằng `{param}`, vì `/x/{id}` và `/x/{item_id}` là cùng route đối với matching.

Các modal/form legacy có ID trùng được đổi theo namespace màn hình, ví dụ `overview-*`, `crm-*`, `modal-*`; selector JavaScript phải dùng đúng namespace.

## 8. API/error compatibility

Workflow success response trong release này giữ `{message, data}`. Error chuẩn hóa dưới `detail`:

```json
{
  "detail": {
    "code": "LOCKED_RECORD",
    "message": "Báo giá đã duyệt chỉ được xem, không được xóa.",
    "navigation_targets": []
  }
}
```

Frontend hỗ trợ cả `detail.message` và chuỗi `detail` trong thời gian chuyển đổi. Không đổi URL public đang được UI và runner sử dụng.

## 9. Test design and acceptance scenarios

### Automated tests

1. Audit-failure test chạy một native command giả trả exit 7 và xác minh wrapper trả exit 7, không chứa `A-Z AUDIT PASSED`.
2. App-import test trong environment OpenCV hỏng vẫn import `main` và gọi health được.
3. Database-health tests bao phủ ok, timeout/unavailable và không lộ URL/password.
4. Route-distance test chứng minh API bản đồ lỗi không thêm segment và không gọi save.
5. Workflow failure test chứng minh API 4xx/5xx không mutate local status.
6. Delete/transition integration tests chứng minh approved quotation, confirmed SO và approved/in-transit DO không xóa được.
7. Static uniqueness tests chứng minh không còn duplicate route, global function assignment hoặc DOM ID.
8. UTF-8 source test bao phủ chính xác `frontend/index.html`, `frontend/js/app.js`, `frontend/test_15_button_flow_runner.html`, `backend/app/main.py`, `backend/app/routes/workflow_routes.py` và `backend/app/services/workflow_service.py`.
9. Operational-hardcode test quét các container dashboard, dispatch, tracking, accounting và modal chi tiết trong `index.html`; cấm row/card/value mặc định `DEMO-*` và cấm random fallback distance trong `app.js`. Placeholder có chữ “Ví dụ” và các script seed/test nằm ngoài phạm vi.

### Manual/browser acceptance

- PostgreSQL bật: dùng fixture có prefix `E2E-FOUNDATION-<timestamp>`, mở `/`, dashboard hết loading, tạo route với segment nhập thủ công 10 km và nguồn `map_measurement`, reload vẫn còn; cleanup fixture theo script riêng sau khi ghi nhận kết quả.
- PostgreSQL tắt hoặc URL test trỏ tới port không lắng nghe: dashboard rời loading sang error state trong tối đa 12 giây; không hiển thị số liệu cũ như thật.
- OSRM/Nominatim thất bại: browser E2E intercept hai domain và trả lỗi 503; người dùng thấy lỗi và CTA cấu hình, tổng distance không đổi.
- Record đã duyệt: nút sửa/xóa bị khóa và gọi DELETE trực tiếp cũng trả 409.
- `/test-runner` hiển thị tiếng Việt đúng, nhưng nhãn mô tả rõ đây là API scenario runner, không phải UI E2E coverage.

## 10. Measurable definition of done

- `RUN_AZ_AUDIT.ps1` trả 0 chỉ khi tất cả bước pass; test cố ý gây lỗi chứng minh trả khác 0.
- Backend tests có 0 failure/error với interpreter được audit sử dụng.
- PostgreSQL audit kết nối database cấu hình thật và có `bad_rows=0`, hoặc release được báo blocked rõ ràng nếu hạ tầng không truy cập được; không được tuyên bố pass.
- Duplicate counts: API method/path = 0, window function assignment = 0, DOM ID = 0.
- Random operational fallback count = 0; hardcoded operational `DEMO-*` row/card count = 0.
- Browser acceptance ở trên có bằng chứng log/screenshot hoặc test automation.
- Không xóa dữ liệu hiện có. Nếu cần đổi schema, migration chỉ expand và có kiểm tra rollback/restore trên bản sao.

## 11. Implementation order

1. Characterization/static tests cho audit, import, route uniqueness, JS function uniqueness, DOM IDs, mojibake và fake distance.
2. Sửa audit/interpreter và lazy dependency.
3. Hợp nhất workflow routes và xác minh delete/state guards.
4. Đổi DOM IDs và hợp nhất JavaScript implementations.
5. Loại bỏ fake distance/demo operational markup và optimistic-success.
6. Sửa runner UTF-8 và nhãn coverage.
7. Chạy full audit với PostgreSQL, sau đó browser acceptance.
