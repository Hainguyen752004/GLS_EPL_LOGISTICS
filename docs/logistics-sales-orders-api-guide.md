# Hướng dẫn Logistics gọi API tạo đơn hàng bán QLSX

Created by: Tune  
Created date: 2026-09-11  
Description: Hợp đồng tích hợp và hướng dẫn gọi POST /api/v1/integrations/logistics/sales-orders theo source hiện tại.

## 1. Mục đích và kết quả

Backend Logistics gọi API khi DO có trạng thái `delivered` và người dùng nhấn **Tạo đơn hàng bán QLSX**.

QLSX xử lý trong transaction:

1. Kiểm tra DO, số tiền, khách hàng và cấu hình.
2. Tìm khách hàng theo `header.customer_id = PUBOBJECT.OBJ_OBJECTNO`. Không so với OBJ_AUTOID, không tự tạo khách hàng.
3. Tìm/tạo một mặt hàng gộp theo khách + tuyến. Mã và tên mặt hàng là `customer_id + "_" + route.id`; tái sử dụng mặt hàng cho cùng cặp khách–tuyến. ĐVT Cái, nhóm Thành phẩm.
4. Tạo SO một dòng, số lượng 1, đơn giá và thành tiền bằng Tổng bán.
5. Tạo phiếu bán liên kết và dùng nghiệp vụ QLSX ghi công nợ, đóng phiếu/hoàn thành SO. Trạng thái thực hiện: 1 → 8 → 10 → 5.
6. Lưu liên kết DO–SO, JSON nguồn và kết quả để chống tạo trùng.

**Hoàn thành SO không phải đã thanh toán.** Luồng này chưa nhận trả trước: công nợ ban đầu bằng toàn bộ Tổng bán, không tạo phiếu thu. Không tạo sản xuất, chuyển động kho hoặc hóa đơn điện tử trong API này.

Chi nhánh hiện cố định **1368**, quốc gia kế toán **11**, người tạo nghiệp vụ **OBJ_AUTOID = 4**; ngày tạo lấy giờ server. Caller xác thực được lưu audit riêng. Logistics không truyền các giá trị này.

## 2. Endpoint và xác thực

```http
POST {QLSX_BASE_URL}/api/v1/integrations/logistics/sales-orders
Authorization: Bearer <QLSX_ACCESS_TOKEN>
Content-Type: application/json
Accept: application/json
Idempotency-Key: logistics:UAT-DO-LAK-20260911-102
```

- Local DEV: `https://localhost:44333`. Đây là máy chạy QLSX, không phải địa chỉ dùng từ server Logistics khác.
- DEV/UAT/Production từ xa: hai đội thống nhất hostname HTTPS QLSX thực tế. Không dùng địa chỉ API Logistics làm đích POST tạo SO.
- Dùng access token do **QLSX** xác thực; token Logistics không tự dùng được. Đội QLSX cấp/hướng dẫn cơ chế lấy và refresh token cho tài khoản tích hợp trước triển khai.
- Tài khoản phải có UserId/ObjectId hợp lệ và **UserId** nằm trong `LogisticsSalesPush.AllowedUserIds`. UserId không đồng nghĩa OBJ_AUTOID.
- Không gửi mật khẩu, actor/createdBy, branchId, TRY_AUTOID, CurrencyId hoặc cấu hình POS trong body.
- Token chỉ lưu ở backend/secret của Logistics, không nhúng vào trình duyệt hoặc commit source.
- Controller giới hạn request **1 MiB**; reverse proxy có thể có giới hạn riêng.
- QLSX phải bật `LogisticsSalesPush.Enabled`, cấu hình POS/quầy/bàn/khu vực/loại hình hợp lệ và deploy procedure mới hỗ trợ VND/LAK/USD. File config.example.json chỉ là mẫu, không tự được nạp làm cấu hình runtime.

## 3. Chuyển response DO thành body

Nếu GET DO của Logistics trả:

```json
{
  "message": "Hồ sơ bàn giao...",
  "data": {
    "header": {},
    "details": []
  }
}
```

Thì tạo request:

```javascript
const body = {
  schemaVersion: 1,
  header: logisticsResponse.data.header,
  details: logisticsResponse.data.details
};
```

Đối chiếu các trường bắt buộc ở mục 4 trước khi gửi. Không gửi nguyên envelope `message/data`. Chỉ có **ba thuộc tính cấp gốc** được chấp nhận: `schemaVersion`, `header`, `details`.

API không tự GET DO từ Logistics và không nhận URL hoặc chỉ do_id để tạo đơn. Logistics phải POST dữ liệu chi tiết.

## 4. Quy tắc request

Tên trường phân biệt hoa/thường. Giá trị tiền phải là JSON number, không phải chuỗi định dạng có dấu phân cách hàng nghìn.

| Trường | Bắt buộc | Quy tắc |
| --- | --- | --- |
| schemaVersion | Có | Số nguyên 1 |
| header | Có | Object |
| header.do_id | Có | Mã DO ổn định, tối đa 100 ký tự |
| header.status | Có | Chuỗi chính xác `delivered` |
| header.customer_id | Có | Mã khách đã có duy nhất trong PUBOBJECT.OBJ_OBJECTNO, tối đa 50 ký tự |
| header.route | Có | Object |
| header.route.id | Có | Mã tuyến ổn định, tối đa 50 ký tự |
| header.currency | Có | `VND`, `LAK` hoặc `USD`, viết hoa |
| header.currency_thu | Có | Phải bằng header.currency |
| header.selling_price | Có | Giá bán không âm |
| header.customer_surcharge_total | Có | Phụ thu khách không âm; không có phụ thu gửi 0 |
| header.final_selling_price | Có | Tổng bán > 0.01 |
| details | Có | Mảng không rỗng, phải có dòng thu để tổng khớp |
| details[].line_no | Có | Số nguyên dương, không trùng trong mảng |
| details[].kind | Có | `thu` hoặc `chi`, viết thường |
| details[].actual_amount | Có | Số không âm |
| details[].currency | Có với dòng thu | Dòng thu phải cùng currency_thu; nên gửi cho mọi dòng chi để hiển thị đầy đủ |
| details[].name | Nên có | Mô tả khoản thu/chi; nếu thiếu thì dùng charge_type khi dựng mô tả |

Mã do_id/customer_id/route.id chỉ gồm chữ ASCII, số, `_`, `-`, `.`; bắt đầu bằng chữ hoặc số. Không chứa khoảng trắng, dấu tiếng Việt hoặc ký tự `/`.

**Mã ghép customer_id + "_" + route.id không được vượt 50 ký tự**, dù từng thành phần riêng chưa vượt giới hạn.

Quy tắc tiền:

```text
selling_price + customer_surcharge_total = final_selling_price
SUM(details.actual_amount WHERE kind = "thu") = final_selling_price
```

- Tiền tối đa 5 chữ số thập phân, giá trị mỗi trường tiền từ 0 đến 9,999,999,999,999 theo validator hiện tại.
- So khớp tổng chính xác; không tự dung sai hoặc tự điều chỉnh chênh lệch. Dùng decimal ở backend Logistics để tính tiền.
- Ví dụ USD: 100.25 + 5.50 = 105.75. Không gửi `"105,75"`.
- `kind = "thu"` là khoản cấu thành doanh thu, **không phải khoản khách đã thanh toán**.
- Không cộng dòng chi vào tổng bán, cũng không lấy thu trừ chi để ghi công nợ.
- Không trộn tiền trên các dòng thu. Dòng chi khác tiền chỉ lưu nguồn, không được API này tự quy đổi.
- QLSX tra PUBCURRENCY.CUR_NAME để lấy ID; không hardcode ID phía Logistics.
- Quốc gia 11 không ép tiền thành LAK. DO VND/USD vẫn có thể tạo theo tiền nguồn.
- Rate=1 trong luồng này biểu diễn giữ nguyên số tiền nguồn, không phải tỷ giá quy đổi sang đồng tiền kế toán. Thu chéo loại tiền/quy đổi sổ cái nằm ngoài API này.

Trường bổ sung nên gửi nếu có: route.name, route.distance_km, origin, destination, quotation_id, trip_id, vehicle_id, driver_id, weight_kg, volume_m3, pickup_window_start/end, delivery_window_start/end, pod_receiver, pod_signed_at. Dữ liệu dùng hiển thị Thông tin DO nguồn và một phần thông tin SO. Giữ tên và kiểu dữ liệu nhất quán với contract DO; thời gian nên dùng ISO 8601 kèm múi giờ.

Các trường như billed_qty, currency_chi, customer_extra, missing_acc_code được lưu snapshot nhưng không thay đổi quy tắc tạo SO:
- Số lượng dòng SO vẫn là 1; billed_qty không quyết định số lượng.
- Không cộng customer_extra thêm lần nữa vào Tổng bán.
- missing_acc_code không dùng để sinh định khoản trong API tạo SO này.
- Chưa phân bổ thuế riêng; truyền Tổng bán đã chốt theo quy tắc trên, không tự thêm VAT lần nữa.

## 5. Request body mẫu

Các mẫu dưới đây đúng cấu trúc và phép cộng. Để chạy được, QLSX phải có khách DEMO-CUS-UNILEVER, danh mục và cấu hình hợp lệ. Thay mã DO bằng DO thực tế khi tích hợp; không dùng mã UAT giả trên Production.

### 5.1. VND — Tổng bán 2990000

Idempotency-Key: `logistics:UAT-DO-VND-20260911-101`

```json
{
  "schemaVersion": 1,
  "header": {
    "do_id": "UAT-DO-VND-20260911-101",
    "status": "delivered",
    "customer_id": "DEMO-CUS-UNILEVER",
    "route": {
      "id": "DEMO-RT-VSIP2A-CAIMEP",
      "name": "VSIP II-A → Cảng Cái Mép",
      "distance_km": 96.5
    },
    "currency": "VND",
    "currency_thu": "VND",
    "currency_chi": "VND",
    "selling_price": 2740000,
    "customer_surcharge_total": 250000,
    "final_selling_price": 2990000,
    "billed_qty": 0
  },
  "details": [
    {
      "line_no": 1,
      "kind": "chi",
      "name": "Chi phí vận chuyển",
      "actual_amount": 1500000,
      "currency": "VND"
    },
    {
      "line_no": 2,
      "kind": "thu",
      "name": "Cước vận chuyển",
      "actual_amount": 2740000,
      "currency": "VND"
    },
    {
      "line_no": 3,
      "kind": "thu",
      "name": "Phụ thu khách hàng",
      "actual_amount": 250000,
      "currency": "VND"
    }
  ]
}
```

### 5.2. LAK — Tổng bán 2200000

Idempotency-Key: `logistics:UAT-DO-LAK-20260911-102`

```json
{
  "schemaVersion": 1,
  "header": {
    "do_id": "UAT-DO-LAK-20260911-102",
    "status": "delivered",
    "customer_id": "DEMO-CUS-UNILEVER",
    "route": {
      "id": "DEMO-RT-VSIP2A-CAIMEP",
      "name": "VSIP II-A → Cảng Cái Mép",
      "distance_km": 96.5
    },
    "currency": "LAK",
    "currency_thu": "LAK",
    "currency_chi": "LAK",
    "selling_price": 2000000,
    "customer_surcharge_total": 200000,
    "final_selling_price": 2200000,
    "billed_qty": 0
  },
  "details": [
    {
      "line_no": 1,
      "kind": "chi",
      "name": "Chi phí vận chuyển",
      "actual_amount": 1300000,
      "currency": "LAK"
    },
    {
      "line_no": 2,
      "kind": "thu",
      "name": "Cước vận chuyển",
      "actual_amount": 2000000,
      "currency": "LAK"
    },
    {
      "line_no": 3,
      "kind": "thu",
      "name": "Phụ thu khách hàng",
      "actual_amount": 200000,
      "currency": "LAK"
    }
  ]
}
```

### 5.3. USD — Tổng bán 105.75

Idempotency-Key: `logistics:UAT-DO-USD-20260911-103`

```json
{
  "schemaVersion": 1,
  "header": {
    "do_id": "UAT-DO-USD-20260911-103",
    "status": "delivered",
    "customer_id": "DEMO-CUS-UNILEVER",
    "route": {
      "id": "DEMO-RT-VSIP2A-CAIMEP",
      "name": "VSIP II-A → Cảng Cái Mép",
      "distance_km": 96.5
    },
    "currency": "USD",
    "currency_thu": "USD",
    "currency_chi": "USD",
    "selling_price": 100.25,
    "customer_surcharge_total": 5.5,
    "final_selling_price": 105.75,
    "billed_qty": 0
  },
  "details": [
    {
      "line_no": 1,
      "kind": "chi",
      "name": "Chi phí vận chuyển",
      "actual_amount": 60.25,
      "currency": "USD"
    },
    {
      "line_no": 2,
      "kind": "thu",
      "name": "Cước vận chuyển",
      "actual_amount": 100.25,
      "currency": "USD"
    },
    {
      "line_no": 3,
      "kind": "thu",
      "name": "Phụ thu khách hàng",
      "actual_amount": 5.5,
      "currency": "USD"
    }
  ]
}
```

Không cần đủ sáu dòng như mẫu DO trước: số dòng tùy DO thực tế. Phải truyền đủ các dòng cần lưu mô tả; không bỏ dòng để né kiểm tra tổng hoặc giới hạn độ dài mô tả.

## 6. Gọi thử bằng cURL / Postman

Lưu một mẫu ở mục 5 vào file `do-lak.json`, thay dữ liệu phù hợp. Với cURL:

```bash
curl --request POST "https://<QLSX_HOST>/api/v1/integrations/logistics/sales-orders" \
  --header "Authorization: Bearer <QLSX_ACCESS_TOKEN>" \
  --header "Content-Type: application/json" \
  --header "Idempotency-Key: logistics:UAT-DO-LAK-20260911-102" \
  --data-binary "@do-lak.json"
```

Postman: Method POST → URL QLSX → Authorization Bearer Token → header Idempotency-Key → Body/raw/JSON, dán nguyên body mẫu. Không chọn form-data. Dùng chứng chỉ HTTPS tin cậy.

## 7. Response thành công

Tạo lần đầu: **201 Created**. Ví dụ minh họa; các ID/mã và ngày giờ thực tế do QLSX sinh:

```json
{
  "replayed": false,
  "data": {
    "doId": "UAT-DO-LAK-20260911-102",
    "orderId": 501,
    "orderCode": "SO-SAMPLE-501",
    "orderStatus": "5",
    "retkAutoId": 601,
    "retkCode": "SALE-SAMPLE-601",
    "customerId": 701,
    "itemId": 801,
    "itemCode": "DEMO-CUS-UNILEVER_DEMO-RT-VSIP2A-CAIMEP",
    "debtId": 901,
    "totalAmount": 2200000,
    "initialDebtAmount": 2200000,
    "currency": "LAK",
    "currencyId": 26,
    "branchId": 1368,
    "accountingCountryId": 11,
    "createdBy": 4,
    "createdAt": "2026-09-11T15:30:00"
  }
}
```

currencyId=26 chỉ minh họa môi trường đã đối chiếu, không phải ID dùng chung mọi DB. orderStatus là chuỗi. createdAt do SQL server tạo, response hiện không kèm timezone; không tự coi là UTC.

Gửi lại đúng yêu cầu đã thành công: **200 OK**, `replayed: true`, `data` là kết quả đã lưu. Đây không phải API lấy công nợ hiện tại: initialDebtAmount không giảm theo những lần thu tiền sau đó.

Logistics nên lưu doId, request key, orderId/orderCode, retkAutoId/retkCode, currency, totalAmount và trạng thái đồng bộ. Chỉ đánh dấu đã tạo SO khi nhận 200/201 cùng kết quả hợp lệ.

## 8. Chống trùng và retry

- Key dài 1–100 ký tự: bắt đầu chữ/số, phần còn lại cho phép chữ/số, `_`, `.`, `:`, `-`. Không bắt buộc UUID.
- Tạo một key ổn định cho một DO trước lần gửi đầu. Lưu cả body đã gửi để retry.
- Cùng doId + cùng key + cùng nội dung → trả kết quả cũ, không tạo SO/nợ/mặt hàng lần nữa.
- Cùng doId nhưng key khác, hoặc cùng key nhưng DO/nội dung khác → **409**, không tự cập nhật SO.
- Body đổi tiền, giá, tên, trường bổ sung, thứ tự dòng details đều có thể đổi hash. Validator chuẩn hóa thứ tự thuộc tính object và biểu diễn số, nhưng không sắp xếp lại mảng details.
- Timeout/mất mạng không chứng minh thất bại: DB có thể đã commit. Retry **cùng key và body**, không tạo key mới.
- Khuyến nghị backend Logistics retry có giới hạn/backoff cho lỗi tạm thời (timeout/503/52903), lưu yêu cầu chờ xử lý. Không retry vô hạn.
- Lỗi dữ liệu chưa tạo thành công: chỉnh dữ liệu sau khi xác định chưa có kết quả đã commit. Nếu bị 409 thì đối soát với QLSX, không lách bằng cách sửa mã DO.
- DO đã tạo SO không có API update/delete tại endpoint này. Nếu Logistics sửa DO sau đó, cần quy trình điều chỉnh riêng.
- Khóa doId hiện là duy nhất trong bảng tích hợp QLSX, không phân vùng tenant/source. Không để các nguồn dùng chung DB phát sinh trùng doId.

## 9. Lỗi và cách xử lý

Lỗi nghiệp vụ do controller trả thường có dạng:

```json
{
  "code": "INVALID_DO",
  "message": "Tổng actual_amount các dòng thu không khớp final_selling_price."
}
```

| HTTP | Code/trường hợp | Xử lý |
| --- | --- | --- |
| 400 | INVALID_DO | Kiểm tra envelope, trường bắt buộc, mã, tiền, tổng dòng |
| 400 | IDEMPOTENCY_KEY_REQUIRED | Bổ sung/sửa key đúng định dạng |
| 401 | Chưa xác thực | Kiểm tra token QLSX/hết hạn |
| 403 | Không đủ quyền | Kiểm tra UserId allowlist và claims; không sửa createdBy trong body |
| 409 | LOGISTICS_52901 | DO/key trùng nhưng không cùng yêu cầu hoặc liên kết cũ bị thay đổi; đối soát |
| 422 | LOGISTICS_52900 | Thiếu/sai điều kiện procedure nền; QLSX kiểm tra deploy |
| 422 | LOGISTICS_52902 | Dữ liệu không qua kiểm tra SQL; xem message |
| 422 | LOGISTICS_52903 | Luồng đang bận; retry có giới hạn cùng key/body |
| 422 | LOGISTICS_52904 | Tiền tệ/danh mục/cấu hình/người tạo/chi nhánh không hợp lệ; QLSX kiểm tra |
| 422 | LOGISTICS_52905 | Không tìm đúng một khách hợp lệ theo OBJ_OBJECTNO, tên thiếu/quá dài |
| 422 | LOGISTICS_52906 | ĐVT Cái hoặc nhóm Thành phẩm chưa hợp lệ |
| 422 | LOGISTICS_52907 | Mặt hàng khách–tuyến trùng/xung đột hoặc không khớp danh mục |
| 422 | LOGISTICS_52908 | Tạo SO/ghi công nợ/đóng phiếu không hoàn tất; QLSX kiểm tra nghiệp vụ |
| 422 | LOGISTICS_52909 | Mô tả quá sức chứa DB; không tự cắt mất dòng, cần QLSX xử lý |
| 503 | LOGISTICS_DISABLED | QLSX chưa bật tích hợp |
| 503 | LOGISTICS_CONFIG_REQUIRED | QLSX chưa cấu hình đủ context |
| 503 | LOGISTICS_DATABASE_ERROR | Đội QLSX kiểm tra log theo traceId; retry cùng key/body |
| 413 | Request quá lớn | Giới hạn controller/proxy; phối hợp điều chỉnh, không tự bỏ dữ liệu |

401/403, JSON sai cú pháp hoặc lỗi ở middleware/proxy có thể không có envelope code/message trên. Client phải đọc HTTP status trước và xử lý cả response không phải JSON. Không phụ thuộc chuỗi message để phân nhánh nghiệp vụ.

## 10. Checklist bàn giao / UAT

- [ ] Hai bên thống nhất QLSX_BASE_URL HTTPS và token tích hợp; không dùng localhost từ server khác.
- [ ] QLSX bật cấu hình runtime, allowlist, deploy SQL hỗ trợ VND/LAK/USD.
- [ ] customer_id tồn tại duy nhất, đang hoạt động; UOM/nhóm và mã tiền có đủ.
- [ ] Payload trực tiếp header/details, Tổng bán khớp, mã ghép ≤ 50 ký tự.
- [ ] Tạo DO VND: 201, SO hoàn thành, nợ nguyên tệ đúng Tổng bán.
- [ ] Tạo DO LAK: SO và công nợ hiển thị LAK, không chuyển thành VND.
- [ ] Tạo DO USD 105.75: không mất phần lẻ trên SO/công nợ.
- [ ] Retry cùng body/key: 200 replayed, chỉ một SO và một khoản nợ.
- [ ] Gửi cùng DO khác key/nội dung: 409.
- [ ] Sai tổng hoặc thu trộn tiền: bị chặn, không tạo dữ liệu dở dang.
- [ ] Xem chi tiết SO: một mặt hàng gộp, mô tả và Thông tin DO nguồn đủ dữ liệu.
- [ ] Thu nợ là bước riêng; chưa thanh toán vẫn còn dư nợ dù SO đã hoàn thành.

## 11. Source đối chiếu

- `GLS-QLSX-APIs/Backend.API/Modules/Sales/Sales/Api/V1/LogisticsPushController.cs`
- `GLS-QLSX-APIs/Backend.API/Modules/Sales/Sales/Application/LogisticsPushValidator.cs`
- `GLS-QLSX-APIs/Backend.API/Modules/Sales/Sales/Contracts/V1/LogisticsPushModels.cs`
- `GLS-QLSX-APIs/Backend.API/Database/Scripts/20260911_logistics_sales_push.sql`

Tài liệu mô tả source hiện tại, không khẳng định mọi môi trường đã deploy phiên bản này. Các request mẫu chưa được dùng để ghi chứng từ thật trong lần viết tài liệu.
