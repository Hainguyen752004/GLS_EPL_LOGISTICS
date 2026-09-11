# Tham chiếu API — EPL Logistics (module vận tải)

Sinh từ mã nguồn đang chạy ngày 2026-09-11 bằng `backend/scripts/sinh_tai_lieu.py`. Bản có mẫu request/response sống: mở `/docs` (Swagger) trên máy chủ.

## Cách gọi API

- **Địa chỉ**: `http://<máy chủ>:8001` (máy demo: `http://127.0.0.1:8001`).
- **Xác thực**: mọi đường đều cần header `Authorization: Bearer <EPL_TMS_API_TOKEN>` (token cấu hình trong `.env` của máy chủ; danh tính ghi nhật ký lấy từ `EPL_TMS_API_PRINCIPAL`). Thiếu hoặc sai → `401 AUTHENTICATION_REQUIRED`. Ngoại lệ công khai: `/`, `/api/health`, `/api/health/database`, `/api/parking-qr/*`, `/uploads/*`, `/static/*`.
- **Phong bì trả về**: thành công `{"message": "…", "data": …}` (danh sách phân trang: `data.items`, `data.total`, `data.page`, `data.page_size`). Lỗi nghiệp vụ: `{"detail": {"code": "MÃ_LỖI", "message": "câu tiếng Việt", "navigation_targets": ["màn cần mở"]}}` — đọc `code` để xử lý, `message` để hiện cho người dùng.
- **Mã trạng thái**: 200 xong · 201 tạo mới · 401 chưa xác thực · 403 thiếu quyền tài chính · 404 không có · 409 sai bước / bị khoá / trùng lịch / phiên bản cũ · 422 thiếu hoặc sai dữ liệu · 503 lược đồ/DB chưa sẵn sàng.
- **Idempotency-Key**: các lệnh ghi quan trọng (lập chuyến, điều phối, mốc thực thi, hoàn tất, chi phí) nhận header `Idempotency-Key: <chuỗi duy nhất>`; gọi lặp cùng khoá trả lại đúng kết quả cũ, không tạo hai lần. Cùng khoá mà nội dung khác → `409 IDEMPOTENCY_CONFLICT`.
- **expected_version**: lệnh đổi trạng thái chuyến/chi phí/cơ hội bắt buộc gửi `expected_version` đọc từ bản ghi hiện tại; lệch → `409 VERSION_CONFLICT` (ai đó vừa sửa, tải lại rồi gửi lại).
- **Thời gian**: ISO 8601 có múi giờ (`2026-09-10T08:30:00+07:00`); máy chủ lưu UTC. Tiền: số (VND không lẻ), `currency_code` ISO 3 chữ.
- **Phân trang**: `page` (từ 1), `page_size` (mặc định 50, tối đa 200 tuỳ đường).

## Luồng gọi theo nghiệp vụ (tóm tắt)

1. Dữ liệu gốc: khách → tuyến (km, toạ độ) → loại xe → công thức giá thành (khoản mục + Acc code) → xe (mã loại, hạn pháp lý) → tài xế (bằng lái, ca trực).
2. `POST /api/crm/opportunities` → `POST /api/crm/opportunities/{ma}/quotation` (báo giá nháp) → `POST /api/quotations/price-preview` (xem giá thành) → `PUT /api/quotations/{qid}/items` → `POST /api/quotations/{qid}/send` (biên mỏng → chờ `internal-approve`) → `POST /api/quotations/{qid}/accept` **→ DO sinh tự động**.
3. `POST /api/tms/trips/from-delivery-orders` → `PUT /api/tms/trips/{trip_id}/dispatch` → `POST /api/tms/freight-orders/{order_id}/events` (check_in, pickup, departure, arrival) → `POST /api/delivery-orders/{do_id}/complete-delivery` (POD + chốt giá) → `PUT /api/tms/finance/trips/{trip_id}/actual-cost` → `submit` → `approve` (người khác).
4. Hệ công nợ: `GET /api/handover/delivery-orders` (danh sách) → `GET /api/handover/delivery-orders/{do_id}` (header + chi tiết có Acc code).

---

## ★ DÀNH CHO BÊN CÔNG NỢ (anh Khang): HAI API BÀN GIAO

> Hai đường này là **toàn bộ** những gì hệ kế toán cần móc vào. Mọi con số đọc từ hồ sơ hoàn tất đã chốt (cùng nguồn với khối "Hồ sơ đã hoàn tất" trên màn), nên không có hai con số khác nhau cho cùng một DO. Chỉ DO đã `delivered` mới được trả — hệ này không nhả số chưa chốt.

### ★ API 1 — DANH SÁCH DO đã hoàn tất

`GET /api/handover/delivery-orders`

| Tham số truy vấn | Kiểu | Ý nghĩa |
|---|---|---|
| `customer_id` | chuỗi | Chỉ lấy DO của một khách (tuỳ chọn) |
| `completed_from` | `YYYY-MM-DD` | Hoàn tất từ ngày này, gồm cả ngày đó (tuỳ chọn) |
| `completed_to` | `YYYY-MM-DD` | Hoàn tất đến ngày này, gồm cả ngày đó (tuỳ chọn) |
| `page` | số nguyên ≥ 1 | Trang, mặc định 1 |
| `page_size` | 1–200 | Kích cỡ trang, mặc định 50 |

Trả `data.items[]` (mới hoàn tất trước), `data.total`, `data.page`, `data.page_size`. Mỗi dòng:

| Trường | Ý nghĩa |
|---|---|
| `do_id` | Mã lệnh giao hàng — dùng để gọi API 2 |
| `status` | Luôn `delivered` |
| `customer_id`, `quotation_id`, `route_id`, `vehicle_id`, `driver_id` | Khách, báo giá gốc, tuyến, xe, tài xế |
| `selling_price` | Cước theo báo giá (giá gốc đã khoá) |
| `customer_surcharge_total` | Khách trả thêm lúc giao |
| `final_selling_price` | **Giá bán cuối** = cước + khách trả thêm |
| `currency` | Tiền tệ của CƯỚC KHÁCH TRẢ, theo báo giá (VND, USD, LAK…) |
| `completed_at`, `completed_by` | Lúc chốt hồ sơ, người chốt |
| `detail_url` | Đường gọi API 2 cho DO này |

Ví dụ: `GET /api/handover/delivery-orders?completed_from=2026-09-01&completed_to=2026-09-30&page_size=100`

### ★ API 2 — HEADER + CHI TIẾT một DO

`GET /api/handover/delivery-orders/{do_id}`

Trả `data.header` và `data.details[]`.

**`header`** — DO là gì và các con số tổng:

| Trường | Ý nghĩa |
|---|---|
| `do_id`, `status` | Mã DO, trạng thái (luôn `delivered`) |
| `customer_id`, `quotation_id` | Khách, báo giá gốc |
| `route` {`id`,`name`,`origin`,`destination`,`distance_km`} | Tuyến |
| `origin`, `destination`, `weight_kg`, `volume_m3`, `pallet_count` | Điểm và lô hàng |
| `pickup_window_*`, `delivery_window_*` | Khung lấy/giao đã hẹn với khách |
| `trip_id`, `trip_status`, `vehicle_id`, `driver_id`, `co_driver_id` | Chuyến và tổ lái đã chạy |
| `actual_departure_at`, `actual_arrival_at` | Giờ đi/đến thực tế |
| `pod_count`, `pod_signed_at`, `pod_receiver` | POD: số bản, giờ ký cuối, người nhận |
| `price_basis` | Đơn vị cước: `per_trip` mỗi chuyến · `per_kg` · `per_tonne` · `per_m3` · `per_km` |
| `unit_price`, `billed_qty` | Đơn giá theo `price_basis`, và số lượng tính tiền — dùng để dựng dòng hoá đơn |
| `selling_price` | Cước báo khách (giá gốc khoá theo báo giá), bằng `currency_thu` |
| `customer_surcharge_total` | Tổng khách trả thêm, bằng `currency_thu` |
| `final_selling_price` | **Giá bán cuối** — số lập phiếu thu, bằng `currency_thu` |
| `quoted_cost`, `quoted_cost_currency` | Giá thành kế hoạch theo báo giá, và đơn vị của nó |
| `actual_cost_total`, `actual_cost_total_currency` | Giá thành thực tế đã chốt, và đơn vị của nó (thường VND) |
| `actual_cost_total_quy_doi` | Giá thành thực tế QUY ĐỔI về `currency_thu`; `null` nếu chưa có tỷ giá |
| `margin_amount`, `margin_percent`, `margin_currency` | Lợi nhuận và biên, tính trong `currency_thu` |
| `margin_unavailable_reason` | Chuỗi rỗng khi tính được; có chữ khi hai đơn vị khác nhau mà chưa có tỷ giá |
| `ledger_totals` {`tong_thu`,`tong_chi`,`tong_chi_quy_doi`,`lai_gop`,`currency_thu`,`currency_chi`,`fx_rate`,`khop_gia_cuoi`,`khop_gia_thanh`,`so_dong_thieu_ma`} | Tổng sổ thu–chi và cờ đối chiếu |
| `cost_formula` {`id`,`name`,`currency`} | Công thức giá thành đã dùng |

**HAI ĐƠN VỊ TIỀN TRONG MỘT HỒ SƠ — đọc kỹ chỗ này.** Cước khách trả ghi bằng tiền của
BÁO GIÁ (khách Lào trả LAK, khách FDI trả USD), còn chi phí thực tế của chuyến ghi bằng
tiền CHỨC NĂNG của công ty là VND, vì dầu, BOT, phụ cấp đều chi bằng đồng. Nên:

| Trường | Ý nghĩa |
|---|---|
| `currency` | Giữ nghĩa cũ = `currency_thu`. Để mã đang đọc trường này không phải sửa |
| `currency_thu` | Đơn vị của MỌI số phía THU: `selling_price`, `customer_surcharge_total`, `final_selling_price`, `margin_amount` |
| `currency_chi` | Đơn vị của MỌI số phía CHI: `actual_cost_total` và các dòng `kind = "chi"` |
| `fx_rate` | Tỷ giá đã dùng: số VND cho MỘT đơn vị `currency_thu`. `null` khi hai bên cùng đơn vị |
| `fx_rate_source` | `quotation` (tỷ giá báo giá đã khoá với khách — ưu tiên) hoặc `currency_table` |

Quy tắc: **không cộng hay trừ hai số khác `currency`**. Muốn một con số duy nhất thì dùng
`actual_cost_total_quy_doi` và `ledger_totals.tong_chi_quy_doi`, cả hai đã về `currency_thu`.
Khi hai đơn vị khác nhau mà không có tỷ giá, hệ trả `null` cho các trường quy đổi và ghi lý
do ở `margin_unavailable_reason` — KHÔNG bịa một con số lãi.

**`details[]`** — TỪNG DÒNG thu / chi để lập phiếu:

| Trường | Ý nghĩa |
|---|---|
| `line_no` | Số dòng |
| `kind` | `thu` (tiền thu của khách) hoặc `chi` (chi phí công ty) |
| `currency` | Đơn vị tiền CỦA DÒNG NÀY: dòng `thu` theo báo giá, dòng `chi` theo phiếu chi phí |
| `acc_code` | **Acc code** — mã tài khoản kế toán bên công nợ, chọn trên khoản mục công thức |
| `missing_acc_code` | `true` nếu dòng chưa có Acc code (phải bổ sung ở Dữ liệu gốc → Công thức) |
| `charge_type` | Loại khoản: `fuel`, `driver`, `toll`, `yard`, `freight_revenue`, `customer_surcharge`… |
| `name` | Tên khoản mục |
| `planned_amount` | Số kế hoạch (theo công thức / báo giá) |
| `actual_amount` | Số thực tế đã chốt |
| `customer_extra` | Phần khách trả thêm (dòng thu) |
| `variance` | Chênh lệch thực tế − kế hoạch |
| `source` | Nguồn: `vehicle` (đơn giá của xe), `cost_formula`, `actual_cost`, `quotation`, `customer_surcharge` |
| `calculation` | Cách tính (ví dụ `96.5 km × 7.728 VND`) |
| `ref_id` | Mã dòng chi phí / khoản trả thêm gốc để đối soát |

Lỗi: `404 DELIVERY_ORDER_NOT_FOUND`; `409 DO_NOT_COMPLETED` khi DO chưa hoàn tất — hãy đợi DO `delivered` (xem API 1) rồi gọi lại.

Ví dụ rút gọn:

```json
{"message": "Hồ sơ bàn giao của DO-2026-0008-DO01.",
 "data": {"header": {"do_id": "DO-2026-0008-DO01", "status": "delivered",
                     "currency": "USD", "currency_thu": "USD", "currency_chi": "VND",
                     "fx_rate": 26173.5, "fx_rate_source": "quotation",
                     "customer_id": "DEMO-CUS-POUYUEN", "quotation_id": "QT-2026-009",
                     "trip_id": "TRIP-PY-USD-01", "vehicle_id": "DEMO-51C-129.03", "driver_id": "DEMO-DRV-005",
                     "price_basis": "per_trip", "unit_price": 120.0,
                     "selling_price": 120.0, "customer_surcharge_total": 15.0, "final_selling_price": 135.0,
                     "actual_cost_total": 851000.0, "actual_cost_total_currency": "VND",
                     "actual_cost_total_quy_doi": 32.51,
                     "margin_amount": 102.49, "margin_percent": 75.92, "margin_currency": "USD",
                     "margin_unavailable_reason": ""},
          "details": [{"line_no": 1, "kind": "chi", "currency": "VND", "acc_code": "1091", "missing_acc_code": false, "charge_type": "fuel",
                       "name": "Chi phí xăng dầu /km", "planned_amount": 344520.0, "actual_amount": 361746.0,
                       "customer_extra": 0.0, "variance": 17226.0, "source": "actual_cost", "calculation": "44.7 km × 7.708 VND", "ref_id": "…"},
                      {"line_no": 5, "kind": "thu", "acc_code": "1211", "missing_acc_code": false, "charge_type": "freight_revenue",
                       "name": "Cước vận chuyển theo báo giá", "planned_amount": 2486000.0, "actual_amount": 2486000.0,
                       "customer_extra": 0.0, "variance": 0.0, "source": "quotation", "calculation": "QT-2026-001", "ref_id": ""}]}}
```

---

## 1. BÀN GIAO CHO BÊN CÔNG NỢ — hai API dành cho hệ kế toán của anh Khang

### `GET /api/handover/delivery-orders`

**API DANH SÁCH DO** đã hoàn tất cho hệ công nợ: mỗi dòng là header rút gọn của một lệnh giao hàng đã chốt hồ sơ (`delivered`), mới hoàn tất trước.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `customer_id` | truy vấn | chuỗi |  |
| `completed_from` | truy vấn | chuỗi |  |
| `completed_to` | truy vấn | chuỗi |  |
| `page` | truy vấn | int |  |
| `page_size` | truy vấn | int |  |

*Ghi chú:* Lọc `customer_id`, `completed_from`, `completed_to` (ISO `YYYY-MM-DD`, gồm cả hai đầu). Phân trang `page`/`page_size` (tối đa 200). Mỗi dòng có `detail_url` để gọi tiếp API chi tiết. Chỉ DO đã chốt hồ sơ mới xuất hiện — không nhả số chưa chốt.

### `GET /api/handover/delivery-orders/{do_id}`

**API HEADER + CHI TIẾT DO**: một mã DO → khối `header` (khách, tuyến, báo giá gốc, chuyến, xe, tài xế, mốc giao, POD, tổng cước/giá thành/lợi nhuận) và khối `details` (TỪNG DÒNG thu/chi, mỗi dòng có `acc_code`).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

*Ghi chú:* Trả 404 `DELIVERY_ORDER_NOT_FOUND` nếu không có DO; 409 `DO_NOT_COMPLETED` nếu DO chưa `delivered` (không bàn giao số chưa chốt). Số liệu đọc cùng nguồn với khối 'Hồ sơ đã hoàn tất' trên màn, nên không lệch.

## 2. Khách hàng và cơ hội (CRM)

### `GET /api/crm/customers`

Danh sách khách kèm số cơ hội, số báo giá, số DO (hồ sơ 360° rút gọn).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `q` | truy vấn | chuỗi |  |

*Ghi chú:* `q` tìm theo tên/mã.

### `GET /api/crm/customers/{customer_id}/profile`

Hồ sơ một khách: cơ hội, báo giá gần nhất, DO, doanh thu đã chốt.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `customer_id` | đường dẫn | chuỗi | có |

### `GET /api/crm/opportunities`

Danh sách cơ hội khách hàng (bảng Kanban).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `stage` | truy vấn | chuỗi |  |
| `owner` | truy vấn | chuỗi |  |
| `customer_id` | truy vấn | chuỗi |  |
| `q` | truy vấn | chuỗi |  |

*Ghi chú:* Lọc `stage` (new|contacted|negotiating|quoted|won|lost), `owner`, `customer_id`, `q` (tìm chữ).

### `POST /api/crm/opportunities`

Tạo cơ hội mới: khách có mã hoặc khách tiềm năng chưa có mã (`prospect_name`).

*Ghi chú:* Thân: `customer_id` hoặc `prospect_name`, `contact_name/phone/email`, `source`, `route_id` hoặc `origin_text`/`destination_text`, `cargo_type`, `est_weight_kg`, `est_trips_per_month`, `expected_start`, `expected_price`, `owner`, `notes`.

### `GET /api/crm/opportunities/summary`

Số cơ hội theo từng giai đoạn cho dải KPI.

### `GET /api/crm/opportunities/{ma}`

Chi tiết một cơ hội, kèm cờ `quotation_expired` nếu báo giá gắn theo đã hết hạn.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `ma` | đường dẫn | chuỗi | có |

### `PUT /api/crm/opportunities/{ma}`

Sửa thông tin cơ hội (chưa won/lost).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `ma` | đường dẫn | chuỗi | có |

### `POST /api/crm/opportunities/{ma}/quotation`

Từ cơ hội, sinh BÁO GIÁ NHÁP kế thừa khách, tuyến, hàng, sản lượng; cơ hội sang `quoted`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `ma` | đường dẫn | chuỗi | có |

*Ghi chú:* Sau bước này mọi việc tiếp theo làm ở API Báo giá. Khách chấp nhận báo giá → cơ hội tự `won`; khách từ chối → tự `lost` với lý do trên phiếu.

### `PUT /api/crm/opportunities/{ma}/stage`

Kéo cơ hội sang giai đoạn khác trên Kanban.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `ma` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `expected_version`, `lost_reason`, `stage`.

*Ghi chú:* Thân `{stage, expected_version, lost_reason?}`. KHÔNG đặt tay `quoted`/`won` — hai giai đoạn đó do hệ đặt khi lập báo giá và khi khách chấp nhận. Kéo về `lost` phải có `lost_reason`.

## 3. Báo giá cước — màn Báo giá mới

### `GET /api/customers/{cid}/price-history`

Vài báo giá gần nhất đã báo cho khách này (mốc gợi ý 'Lần trước').

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `cid` | đường dẫn | chuỗi | có |
| `route_id` | truy vấn | chuỗi |  |
| `limit` | truy vấn | int |  |
| `exclude` | truy vấn | chuỗi |  |

*Ghi chú:* `route_id`, `limit`, `exclude` (mã báo giá đang soạn).

### `GET /api/quotations/board`

Bảng báo giá cho màn Báo giá cước: mỗi dòng có biên lợi nhuận, số ngày còn hiệu lực, số DO đã tách.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `status` | truy vấn | str |  |
| `customer_id` | truy vấn | chuỗi |  |
| `route_id` | truy vấn | chuỗi |  |
| `owner` | truy vấn | chuỗi |  |
| `q` | truy vấn | chuỗi |  |

*Ghi chú:* Lọc `status` (all|draft|pending_approval|sent|accepted|split|rejected|expired), `customer_id`, `route_id`, `owner`, `q`.

### `POST /api/quotations/price-preview`

TÍNH GIÁ THÀNH cho một tổ hợp tuyến + loại xe + tải trọng — đây là chỗ tính giá duy nhất, màn hình chỉ hiển thị.

*Ghi chú:* Thân `{route_id, vehicle_type_id, weight_kg, volume_m3?, pallet_count?, cargo_value?, target_margin?}`. Trả `tinh_duoc`, `viec_con_thieu[]` (nói rõ thiếu km, thiếu công thức, xe không đủ tải…), `cac_dong[]` (từng khoản mục chi/thu), `gia_thanh`, `km`, `cac_loai_xe[]` (độ vừa tải từng loại), `goi_y_gia{theo_cong_thuc, bien_muc_tieu, hop_dong, lan_truoc}`.

### `GET /api/quotations/summary`

Sáu con số dải KPI của màn Báo giá (đang mở, chờ khách, hết hạn trong 7 ngày, đã chấp nhận chưa tách, tiền đã chấp nhận, biên dưới ngưỡng).

### `POST /api/quotations/{qid}/accept`

**KHÁCH CHẤP NHẬN → SINH LỆNH GIAO HÀNG NGAY**, cùng một giao dịch. Báo giá sang `split`, mỗi DO mang `quotation_id` và giá khoá `unit_price`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

*Ghi chú:* Thân rỗng `{}` → số DO = tổng số lượng ở bảng hàng hoá. Hoặc truyền `dos: [{id?, quantity, pickup_window_start?, ..., seal_no?}]` để tự đặt mã/giờ từng DO. Cơ hội CRM gắn theo tự `won`. Lỗi: `QUOTATION_EXPIRED`, `QUOTATION_ALREADY_SPLIT`, `INVALID_TRANSITION` (chưa gửi khách).

### `POST /api/quotations/{qid}/attachments`

Đính kèm chứng từ (multipart: `file`, `doc_type`, `note`) — được phép ngay khi còn nháp.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

Thân yêu cầu (multipart/form-data):

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `doc_type` | chuỗi |  |
| `note` | chuỗi |  |
| `file` | chuỗi | có |

### `DELETE /api/quotations/{qid}/attachments/{aid}`

Xoá một đính kèm.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |
| `aid` | đường dẫn | chuỗi | có |

### `GET /api/quotations/{qid}/attachments/{aid}/file`

Tải tệp đính kèm.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |
| `aid` | đường dẫn | chuỗi | có |

### `GET /api/quotations/{qid}/detail`

Một báo giá kèm mọi thứ màn chi tiết cần: dòng hàng, đính kèm, phiên bản giá, DO đã sinh, biên, mốc.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

### `POST /api/quotations/{qid}/extend`

Gia hạn hiệu lực (`valid_to`), kể cả báo giá đã hết hạn.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

### `POST /api/quotations/{qid}/internal-approve`

Trưởng phòng duyệt bán dưới ngưỡng biên → báo giá được gửi khách (`sent`).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

### `PUT /api/quotations/{qid}/items`

Ghi lại TOÀN BỘ bảng hàng hoá của báo giá (mỗi dòng: `line_no, name, quantity, uom, note`).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `items`.

*Ghi chú:* Tổng `quantity` quyết định số DO sẽ sinh khi khách chấp nhận (1 cont = 1 DO). Chỉ sửa khi còn nháp/chờ duyệt.

### `POST /api/quotations/{qid}/reject`

Khách từ chối, kèm `reason` — báo giá sang `rejected`, cơ hội CRM sang `lost`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

### `POST /api/quotations/{qid}/return-to-draft`

Trả báo giá đang chờ duyệt về nháp, kèm `reason`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

### `POST /api/quotations/{qid}/send`

GỬI KHÁCH: cấp mã hiện cho khách (`quote_no`), chốt phiên bản giá, khoá sửa.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

*Ghi chú:* Nếu biên < ngưỡng 15% (hoặc biên mục tiêu riêng của khách) thì KHÔNG gửi mà chuyển sang `pending_approval` — chờ trưởng phòng duyệt nội bộ. Lỗi thường gặp: `PRICE_REQUIRED` (chưa có đơn giá), `ITEMS_REQUIRED`, `VALIDITY_IN_PAST`.

### `POST /api/quotations/{qid}/split`

Đường tách DO thủ công cho báo giá đã `accepted` từ trước khi có tách tự động (hiếm dùng).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

*Ghi chú:* Luồng mới KHÔNG cần gọi: `accept` đã sinh DO.

## 4. Báo giá (đường CRUD chung), Lệnh giao hàng và POD

### `GET /api/delivery-orders`

Danh sách lệnh giao hàng (phân trang). Mỗi dòng có `canonical_status`, `quotation_id`, `unit_price`, khung giờ, `cancel_reason`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `page` | truy vấn | int |  |
| `page_size` | truy vấn | int |  |

### `GET /api/delivery-orders/analysis`

Thống kê DO theo trạng thái/tuyến cho bảng phân tích.

### `DELETE /api/delivery-orders/{do_id}`

Xoá DO ở `pending` hoặc `cancelled`. Đang chạy/đã giao → 409 `LOCKED_RECORD`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

### `PUT /api/delivery-orders/{do_id}`

Sửa DO còn `pending` (khung giờ, khối lượng, seal…).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `DeliveryOrderUpdateRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `route_id` | chuỗi | trống |  |
| `origin` | chuỗi | trống |  |
| `destination` | chuỗi | trống |  |
| `pickup_window_start` | chuỗi | trống |  |
| `pickup_window_end` | chuỗi | trống |  |
| `delivery_window_start` | chuỗi | trống |  |
| `delivery_window_end` | chuỗi | trống |  |
| `pickup_date` | chuỗi | trống |  |
| `delivery_date` | chuỗi | trống |  |
| `weight_kg` | số nguyên | số | trống |  |
| `pallet_count` | số nguyên | trống |  |
| `notes` | chuỗi | trống |  |
| `packaging_spec` | chuỗi | trống |  |
| `seal_no` | chuỗi | trống |  |
| `volume_m3` | số nguyên | số | trống |  |

*Ghi chú:* Đổi `route_id` bị chặn khi DO sinh từ báo giá — muốn đổi tuyến thì sửa báo giá và sinh lại.

### `POST /api/delivery-orders/{do_id}/complete-delivery`

**HOÀN TẤT GIAO HÀNG**: nộp POD + chữ ký từng chặng, ghi khách trả thêm, CHỐT GIÁ CUỐI — tất cả trong một giao dịch (multipart).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

*Ghi chú:* Trường `payload` (JSON): `{trip_id, currency_code, pod_entries:[{leg_id, stop_no, delivery_time, receiver_name, receiver_phone, delivery_result, cargo_condition, file_field, signature_file_field}], charge_adjustments:[{name, original_amount, actual_amount, note}]}` + các tệp ảnh/PDF theo `file_field`. Header `Idempotency-Key` bắt buộc. Kết quả: DO `delivered`, tạo `delivery_order_closeouts`, chuyến tự `completed` khi mọi DO đã POD. Không lập hoá đơn ở đây — hoá đơn là việc của hệ công nợ qua API bàn giao.

### `PUT /api/delivery-orders/{do_id}/dispatch`

Điều phối trực tiếp một DO (đường cũ). Luồng chuẩn là tạo Trip rồi `PUT /api/tms/trips/{trip_id}/dispatch`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `DeliveryOrderDispatchRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `vehicle_id` | chuỗi | có |
| `driver_id` | chuỗi | có |
| `co_driver_id` | chuỗi | trống |  |
| `packaging_spec` | chuỗi | trống |  |
| `volume_m3` | số nguyên | số | trống |  |
| `departure_at` | chuỗi | trống |  |
| `planned_departure_at` | chuỗi | trống |  |
| `avg_speed_kmh` | số nguyên | số | trống |  |
| `max_speed_kmh` | số nguyên | số | trống |  |
| `return_speed_kmh` | số nguyên | số | trống |  |
| `return_distance_km` | số nguyên | số | trống |  |
| `load_minutes` | số nguyên | trống |  |
| `unload_minutes` | số nguyên | trống |  |

### `PUT /api/delivery-orders/{do_id}/status`

Đổi trạng thái DO. Dùng chính cho HUỶ: `{status: 'Cancelled', reason}`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `DeliveryOrderStatusRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `status` | chuỗi | có |
| `reason` | chuỗi | trống |  |

*Ghi chú:* Huỷ mà thiếu `reason` → 422 `CANCEL_REASON_REQUIRED`. DO đang có chuyến hoạt động → 409 `ACTIVE_TRIP_EXISTS`.

### `GET /api/pod-documents/{document_id}`

Tải một chứng từ POD (ảnh/PDF) đã nộp.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `document_id` | đường dẫn | chuỗi | có |

### `GET /api/pod-records`

POD của NHIỀU DO trong một lời gọi: `do_ids=DO-1,DO-2` (tối đa 200).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_ids` | truy vấn | str |  |

*Ghi chú:* Không 404 khi không có POD — trả rỗng.

### `GET /api/pod/{do_id}`

POD của một DO (chỉ đọc).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

### `POST /api/pod/{do_id}`

Ghi POD đơn lẻ (đường cũ, chỉ để đọc lại; hoàn tất DO phải qua `complete-delivery`).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `DeliveryPODRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `trip_id` | chuỗi | có |
| `leg_id` | chuỗi | có |
| `vehicle_id` | chuỗi | có |
| `stop_no` | số nguyên | có |
| `delivery_time` | chuỗi | có |
| `location_text` | chuỗi |  |
| `receiver_name` | chuỗi |  |
| `receiver_phone` | chuỗi |  |
| `photo_url` | chuỗi |  |
| `signature_url` | chuỗi |  |
| `note` | chuỗi |  |
| `status` | chuỗi |  |

### `GET /api/quotations`

Danh sách báo giá dạng phân trang (`page`, `page_size`) — dùng cho các màn cũ và đối soát.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `page` | truy vấn | int |  |
| `page_size` | truy vấn | int |  |

### `POST /api/quotations`

Tạo báo giá nháp. Thân theo `QuotationCreateRequest` (khách, tuyến, loại xe, tải trọng, khung giờ, `price_basis` + `unit_price`, `total_cost`, tiền tệ, ghi chú…).

Thân yêu cầu — `QuotationCreateRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `id` | chuỗi | trống |  |
| `customer_id` | chuỗi | có |
| `route_id` | chuỗi | có |
| `origin` | chuỗi | trống |  |
| `destination` | chuỗi | trống |  |
| `pickup_window_start` | chuỗi | trống |  |
| `pickup_window_end` | chuỗi | trống |  |
| `delivery_window_start` | chuỗi | trống |  |
| `delivery_window_end` | chuỗi | trống |  |
| `weight_kg` | số nguyên | số | trống |  |
| `pallet_count` | số nguyên | trống |  |
| `cargo_type` | chuỗi | trống |  |
| `valid_to` | chuỗi | trống |  |
| `fuel_cost` | số nguyên | số | trống |  |
| `driver_cost` | số nguyên | số | trống |  |
| `toll_fee` | số nguyên | số | trống |  |
| `total_cost` | số nguyên | số | trống |  |
| `selling_price` | số nguyên | số | trống |  |
| `notes` | chuỗi | trống |  |
| `packaging_spec` | chuỗi | trống |  |
| `volume_m3` | số nguyên | số | trống |  |
| `carrier_name` | chuỗi | trống |  |
| `delivery_method` | chuỗi | trống |  |
| `seal_weight` | chuỗi | trống |  |
| `temperature_requirement` | chuỗi | trống |  |
| `cargo_insurance` | chuỗi | trống |  |
| `warehouse_owner` | chuỗi | trống |  |
| `vehicle_type_id` | chuỗi | trống |  |
| `price_basis` | chuỗi | trống |  |
| `unit_price` | số nguyên | số | trống |  |
| `min_qty_per_trip` | số nguyên | số | trống |  |
| `currency_code` | chuỗi | trống |  |
| `fx_rate` | số nguyên | số | trống |  |
| `payment_terms` | chuỗi | trống |  |
| `waiting_surcharge` | số nguyên | số | trống |  |
| `sales_rep` | chuỗi | trống |  |
| `trips_per_month` | số nguyên | trống |  |
| `cargo_value` | số nguyên | số | trống |  |
| `stacking` | chuỗi | trống |  |
| `sealing` | chuỗi | trống |  |
| `recipient_contact` | chuỗi | trống |  |
| `notes_customer` | chuỗi | trống |  |
| `notes_ops` | chuỗi | trống |  |
| `notes_internal` | chuỗi | trống |  |
| `target_margin` | số nguyên | số | trống |  |
| `competitor_price` | số nguyên | số | trống |  |
| `discount_percent` | số nguyên | số | trống |  |

*Ghi chú:* `selling_price` do máy chủ suy từ `unit_price × số lượng theo đơn vị cước` — không gửi. Đơn giá cước là giá CUỐI; `discount_percent` (0..1) chỉ để phiếu gửi khách in 'giá gốc'.

### `DELETE /api/quotations/{qid}`

Xoá báo giá còn nháp. Báo giá đã gửi/đã tách thì 409 `LOCKED_RECORD`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

### `PUT /api/quotations/{qid}`

Sửa báo giá còn nháp/chờ duyệt.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

Thân yêu cầu — `QuotationUpdateRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `id` | chuỗi | trống |  |
| `customer_id` | chuỗi | trống |  |
| `route_id` | chuỗi | trống |  |
| `origin` | chuỗi | trống |  |
| `destination` | chuỗi | trống |  |
| `pickup_window_start` | chuỗi | trống |  |
| `pickup_window_end` | chuỗi | trống |  |
| `delivery_window_start` | chuỗi | trống |  |
| `delivery_window_end` | chuỗi | trống |  |
| `weight_kg` | số nguyên | số | trống |  |
| `pallet_count` | số nguyên | trống |  |
| `cargo_type` | chuỗi | trống |  |
| `valid_to` | chuỗi | trống |  |
| `fuel_cost` | số nguyên | số | trống |  |
| `driver_cost` | số nguyên | số | trống |  |
| `toll_fee` | số nguyên | số | trống |  |
| `total_cost` | số nguyên | số | trống |  |
| `selling_price` | số nguyên | số | trống |  |
| `notes` | chuỗi | trống |  |
| `packaging_spec` | chuỗi | trống |  |
| `volume_m3` | số nguyên | số | trống |  |
| `carrier_name` | chuỗi | trống |  |
| `delivery_method` | chuỗi | trống |  |
| `seal_weight` | chuỗi | trống |  |
| `temperature_requirement` | chuỗi | trống |  |
| `cargo_insurance` | chuỗi | trống |  |
| `warehouse_owner` | chuỗi | trống |  |
| `vehicle_type_id` | chuỗi | trống |  |
| `price_basis` | chuỗi | trống |  |
| `unit_price` | số nguyên | số | trống |  |
| `min_qty_per_trip` | số nguyên | số | trống |  |
| `currency_code` | chuỗi | trống |  |
| `fx_rate` | số nguyên | số | trống |  |
| `payment_terms` | chuỗi | trống |  |
| `waiting_surcharge` | số nguyên | số | trống |  |
| `sales_rep` | chuỗi | trống |  |
| `trips_per_month` | số nguyên | trống |  |
| `cargo_value` | số nguyên | số | trống |  |
| `stacking` | chuỗi | trống |  |
| `sealing` | chuỗi | trống |  |
| `recipient_contact` | chuỗi | trống |  |
| `notes_customer` | chuỗi | trống |  |
| `notes_ops` | chuỗi | trống |  |
| `notes_internal` | chuỗi | trống |  |
| `target_margin` | số nguyên | số | trống |  |
| `competitor_price` | số nguyên | số | trống |  |
| `discount_percent` | số nguyên | số | trống |  |

*Ghi chú:* Không đổi được tuyến khi đã có DO.

### `PUT /api/quotations/{qid}/approve`

Duyệt nội bộ (đường cũ, tương đương `internal-approve`).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

### `PUT /api/quotations/{qid}/status`

Đổi trạng thái thô (đường cũ). Ưu tiên dùng `send/accept/reject/extend`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `qid` | đường dẫn | chuỗi | có |

Thân yêu cầu — `WorkflowStatusRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `status` | chuỗi | có |

## 5. Chuyến, điều phối, sắp lịch, mốc thực thi

### `GET /api/tms/carriers`

Nhà vận chuyển (đội xe nội bộ hoặc thuê ngoài).

### `POST /api/tms/carriers`

Thêm nhà vận chuyển `{id, name, tax_code, contact_person, phone, email, is_internal, status}`.

### `DELETE /api/tms/carriers/{carrier_id}`

Xoá nhà vận chuyển chưa dùng.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `carrier_id` | đường dẫn | chuỗi | có |

### `PUT /api/tms/carriers/{carrier_id}`

Sửa nhà vận chuyển.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `carrier_id` | đường dẫn | chuỗi | có |

### `POST /api/tms/carriers/{carrier_id}/status`

Đổi trạng thái active/inactive.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `carrier_id` | đường dẫn | chuỗi | có |

### `GET /api/tms/demands`

Nhu cầu vận chuyển (mô-đun TMS gốc, không nằm trong luồng Báo giá → DO).

### `POST /api/tms/demands`

Tạo nhu cầu vận chuyển (TMS gốc).

### `PUT /api/tms/demands/{demand_id}/submit`

Trình nhu cầu (TMS gốc).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `demand_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `expected_version`.

### `GET /api/tms/driver-qualifications`

Bằng lái đã khai (phân trang).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `paginated` | truy vấn | bool |  |
| `page` | truy vấn | int |  |
| `page_size` | truy vấn | int |  |

### `POST /api/tms/driver-qualifications`

Khai bằng lái: `{driver_id, license_type, valid_from, valid_to, status}`. Điều phối chặn tài xế không có bằng còn hạn.

### `GET /api/tms/freight-orders`

Danh sách Freight Order (đơn vận chuyển nội bộ sinh cùng chuyến).

### `POST /api/tms/freight-orders`

Tạo Freight Order thô (đường TMS gốc).

### `PUT /api/tms/freight-orders/{order_id}/dispatch`

Điều phối ở mức Freight Order (đường TMS gốc).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `order_id` | đường dẫn | chuỗi | có |

### `GET /api/tms/freight-orders/{order_id}/events`

Chuỗi mốc của một Freight Order.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `order_id` | đường dẫn | chuỗi | có |

### `POST /api/tms/freight-orders/{order_id}/events`

**GHI MỐC THỰC THI** của chuyến: `event_type` check_in | pickup | departure | arrival | unloading | delivered | route_deviation …, kèm `event_time`, `lat/lng`, `speed_kmh`, `distance_km`, `eta`, `note`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `order_id` | đường dẫn | chuỗi | có |

*Ghi chú:* Header `Idempotency-Key`. Mốc `arrival` tự chuyển DO sang `arrived` (đã đến, chờ POD). Đây là chỗ GPS/thiết bị đổ dữ liệu vào.

### `GET /api/tms/freight-orders/{order_id}/latest-position`

Vị trí GPS mới nhất.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `order_id` | đường dẫn | chuỗi | có |

### `POST /api/tms/freight-orders/{order_id}/legacy-link`

Nối Freight Order với DO cũ (di trú dữ liệu).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `order_id` | đường dẫn | chuỗi | có |

### `GET /api/tms/freight-units`

Đơn vị hàng (TMS gốc).

### `POST /api/tms/freight-units/from-demand/{demand_id}`

Tách nhu cầu thành đơn vị hàng (TMS gốc).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `demand_id` | đường dẫn | chuỗi | có |

### `GET /api/tms/resource-assignments`

Các phân công xe/tổ lái đang có (để xem trùng lịch).

### `GET /api/tms/scheduling/board`

Toàn bộ dữ liệu màn Sắp lịch xe & tài xế: `start`, `days`, `depot`, `team`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `start` | truy vấn | str | có |
| `days` | truy vấn | int |  |
| `depot` | truy vấn | chuỗi |  |
| `team` | truy vấn | chuỗi |  |

### `GET /api/tms/scheduling/driver-shifts`

Ca trực trong khoảng `start..end`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `start` | truy vấn | str | có |
| `end` | truy vấn | str | có |

### `POST /api/tms/scheduling/driver-shifts`

Tạo ca trực: `{id, driver_id, shift_type, availability_kind: work|leave, shift_start, shift_end, work_location, status, notes}`.

*Ghi chú:* Điều phối đòi ca trực PHỦ TRỌN thời gian chuyến (kể cả chặng về).

### `POST /api/tms/scheduling/driver-shifts/weekly-schedule`

Tạo ca theo tuần cho nhiều tài xế một lượt.

### `DELETE /api/tms/scheduling/driver-shifts/{shift_id}`

Xoá ca trực chưa gắn chuyến.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `shift_id` | đường dẫn | chuỗi | có |

### `PUT /api/tms/scheduling/driver-shifts/{shift_id}`

Sửa ca trực.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `shift_id` | đường dẫn | chuỗi | có |

### `PUT /api/tms/scheduling/drivers/{driver_id}/assignment`

Gán bãi (`depot_code`), tổ (`team_code`), mẫu xoay cho tài xế.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `driver_id` | đường dẫn | chuỗi | có |

### `GET /api/tms/scheduling/fill-candidates`

Ai có thể nhận một ca đang thiếu: `date`, `shift`, `depot`, `team`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `date` | truy vấn | str | có |
| `shift` | truy vấn | str | có |
| `depot` | truy vấn | chuỗi |  |
| `team` | truy vấn | chuỗi |  |

### `POST /api/tms/scheduling/generate-from-pattern`

Sinh ca cho cả tổ từ mẫu xoay (`rotation_pattern`) của từng người.

### `GET /api/tms/scheduling/vehicle-availability`

Xe rảnh/bận trong khoảng `start..end` (kể cả bảo dưỡng).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `start` | truy vấn | str | có |
| `end` | truy vấn | str | có |

### `GET /api/tms/tenders`

Đấu thầu thuê ngoài (TMS gốc).

### `POST /api/tms/tenders`

Mở thầu cho Freight Order (TMS gốc).

### `PUT /api/tms/tenders/{tender_id}/award`

Trao thầu `{offer_id, expected_version}`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `tender_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `expected_version`, `offer_id`.

### `GET /api/tms/tenders/{tender_id}/offers`

Các chào giá của thầu.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `tender_id` | đường dẫn | chuỗi | có |

### `POST /api/tms/tenders/{tender_id}/offers`

Nhà vận chuyển chào giá.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `tender_id` | đường dẫn | chuỗi | có |

### `GET /api/tms/trips`

Danh sách chuyến: `status`, `freight_order_id`, phân trang. Mỗi chuyến kèm ETA, `delivery_due_at`, `is_late`, `late_minutes`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `status` | truy vấn | chuỗi |  |
| `freight_order_id` | truy vấn | chuỗi |  |
| `page` | truy vấn | int |  |
| `page_size` | truy vấn | int |  |

### `POST /api/tms/trips`

Tạo chuyến thô cho Freight Order (đường TMS gốc; luồng chuẩn dùng `from-delivery-orders`).

Thân yêu cầu — `TripCreateRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `id` | chuỗi | có |
| `freight_order_id` | chuỗi | có |
| `trip_type` | chuỗi | có |
| `do_ids` | mảng<chuỗi> | có |
| `vehicle_id` | chuỗi | trống |  |
| `driver_id` | chuỗi | trống |  |

### `POST /api/tms/trips/from-delivery-orders`

**LẬP CHUYẾN TỪ DO**: tạo Trip + Freight Order + các chặng theo tuyến của DO.

Thân yêu cầu — `TripFromDeliveryOrdersRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `id` | chuỗi | có |
| `do_ids` | mảng<chuỗi> | có |
| `trip_type` | chuỗi |  |
| `planned_departure_at` | chuỗi | có |
| `avg_speed_kmh` | số | chuỗi | có |
| `dwell_minutes` | số nguyên |  |
| `stop_plan` | mảng<TripStopPlanItem> |  |
| `return_purpose` | chuỗi |  |
| `return_route_id` | chuỗi | trống |  |
| `return_do_id` | chuỗi | trống |  |

*Ghi chú:* Thân `{id, do_ids[], trip_type: one_way|round_trip, planned_departure_at, avg_speed_kmh, dwell_minutes, stop_plan?, return_purpose, return_route_id?, return_do_id?}`. Header `Idempotency-Key`. Quy ước 1 DO = 1 chuyến (tuyến một chặng chỉ có một chặng giao).

### `GET /api/tms/trips/{trip_id}`

Chi tiết một chuyến: chặng, DO, xe/tổ lái, mốc kế hoạch và thực tế.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `trip_id` | đường dẫn | chuỗi | có |

### `POST /api/tms/trips/{trip_id}/cancel`

Huỷ chuyến: trả xe/tổ lái, DO về `pending`. Chuyến đã có POD thì không huỷ được.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `trip_id` | đường dẫn | chuỗi | có |

### `POST /api/tms/trips/{trip_id}/complete-return`

Xác nhận xe về bãi sau chặng về (chuyến khứ hồi).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `trip_id` | đường dẫn | chuỗi | có |

### `PUT /api/tms/trips/{trip_id}/dispatch`

**ĐIỀU PHỐI**: gán xe + tài xế (+ phụ xe) cho chuyến trong khung `assignment_start..assignment_end`; DO sang `in_transit`, xe/tổ lái bị khoá lịch trọn hành trình.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `trip_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `TripDispatchRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `vehicle_id` | chuỗi | có |
| `driver_id` | chuỗi | có |
| `co_driver_id` | chuỗi | trống |  |
| `expected_version` | số nguyên | có |
| `assignment_start` | chuỗi | có |
| `assignment_end` | chuỗi | có |
| `confirm_vehicle_type_mismatch` | đúng/sai |  |

*Ghi chú:* Thân `TripDispatchRequest` (bắt buộc `expected_version`). Các cửa chặn: `READY_VEHICLE` (xe phải 'Sẵn sàng'), `VEHICLE_LEGAL_EXPIRED` (đăng kiểm/bảo hiểm/bảo dưỡng), `DRIVER_LICENSE_INVALID`, `SHIFT_NOT_COVERING` (ca trực phải phủ trọn chuyến), `RESOURCE_TIME_OVERLAP`, `ASSIGNMENT_OUTSIDE_WINDOW` (phải nằm trong khung lấy–giao), `VEHICLE_TYPE_MISMATCH` (xe khác loại báo giá → gửi lại với `confirm_vehicle_type_mismatch=true` để cố ý ghi đè, có nhật ký).

### `POST /api/tms/trips/{trip_id}/legs`

Thêm một chặng vào chuyến (điểm dừng thêm).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `trip_id` | đường dẫn | chuỗi | có |

### `GET /api/tms/warehouse-appointments`

Lịch hẹn kho (TMS gốc).

### `POST /api/tms/warehouse-appointments`

Đặt lịch hẹn lấy/giao tại kho (TMS gốc).

## 6. Bãi xe và packing list

### `GET /api/parking-labels/{label_id}/qr.svg`

Ảnh QR của một nhãn.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `label_id` | đường dẫn | chuỗi | có |

### `GET /api/parking-lists`

Phiếu bãi xe / packing list: `q`, `status`, phân trang.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `q` | truy vấn | str | None |  |
| `status` | truy vấn | str | None |  |
| `page` | truy vấn | int |  |
| `page_size` | truy vấn | int |  |

### `POST /api/parking-lists/auto-from-do/{do_id}`

Tự chia một DO thành `list_count` phiếu, chia kiện/khối lượng đều.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `ParkingListAutoCreateRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `list_count` | số nguyên |  |

### `POST /api/parking-lists/from-do/{do_id}`

Tạo phiếu bãi cho một DO: `{store_id, store_name, wave, gate, box_count}`. Dòng hàng lấy từ dòng hàng hoá của BÁO GIÁ.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `ParkingListCreateRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `store_id` | chuỗi | trống |  |
| `store_name` | chuỗi | trống |  |
| `wave` | chuỗi | trống |  |
| `gate` | chuỗi | trống |  |
| `box_count` | số nguyên |  |

*Ghi chú:* Gọi lặp cùng DO thì trả lại phiếu đã có (idempotent).

### `GET /api/parking-lists/{parking_id}`

Chi tiết phiếu: dòng hàng, nhãn QR, lịch sử sự kiện.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `parking_id` | đường dẫn | chuỗi | có |

### `GET /api/parking-lists/{parking_id}/label`

Nhãn kiện (HTML in).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `parking_id` | đường dẫn | chuỗi | có |

### `GET /api/parking-lists/{parking_id}/packing-list`

Packing list (HTML in).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `parking_id` | đường dẫn | chuỗi | có |

### `POST /api/parking-lists/{parking_id}/print`

Ghi nhận đã in `{document_type: label|packing_list}` — sinh mã QR cho từng kiện.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `parking_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `ParkingListPrintRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `document_type` | chuỗi | có |

### `POST /api/parking-lists/{parking_id}/status`

Đổi trạng thái phiếu tay `{status, note}` (draft→ready→parked→gate_in→loaded→dispatched→delivered).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `parking_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `ParkingListStatusRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `status` | chuỗi | có |
| `note` | chuỗi | trống |  |

*Ghi chú:* Bình thường trạng thái đi theo quét QR và theo chuyến; chỉ đặt tay khi cần sửa.

### `GET /api/parking-qr/{token}`

Trang quét QR công khai của một kiện (điện thoại bãi xe).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `token` | đường dẫn | chuỗi | có |

*Ghi chú:* Công khai, không cần token.

### `POST /api/parking-qr/{token}/scan`

Quét kiện: `{action: gate_in|loaded|delivered, note}`. Đủ kiện thì phiếu tự lên trạng thái.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `token` | đường dẫn | chuỗi | có |

Thân yêu cầu — `ParkingQrScanRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `action` | chuỗi | có |
| `note` | chuỗi | trống |  |

*Ghi chú:* Công khai theo thiết kế (thiết bị bãi).

## 7. Hoàn tất giao hàng và theo dõi

### `GET /api/delivery-orders/{do_id}/closeout`

HỒ SƠ HOÀN TẤT của một DO: DO, chuyến, POD + chứng từ, `commercials` (giá gốc, khách trả thêm, giá cuối, giá thành chốt/thực tế, lợi nhuận), `ledger_lines` (sổ thu–chi từng dòng có Acc code), `ledger_totals`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

*Ghi chú:* Đây là nguồn của khối 'Hồ sơ đã hoàn tất' trên màn và của API bàn giao. DO chưa hoàn tất vẫn trả được (giá tạm) nhưng cờ `margin_is_provisional=true`.

### `GET /api/tracking/control-tower`

THÁP KIỂM SOÁT: mọi chuyến đang chạy với GPS mới nhất, ETA, trễ hạn khách (`delivery_due_at`, `is_late`), POD, sự cố.

*Ghi chú:* Thiếu GPS không loại chuyến khỏi bảng — hiện 'chưa có GPS'.

### `GET /api/tracking/{do_id}`

Vết GPS và mốc của một DO.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `do_id` | đường dẫn | chuỗi | có |

## 8. Chi phí phát sinh của chuyến

### `GET /api/tms/finance/costs`

100 bảng chi phí gần nhất (quyền `finance_read`).

### `GET /api/tms/finance/costs/{cost_id}`

Một bảng chi phí.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `cost_id` | đường dẫn | chuỗi | có |

### `POST /api/tms/finance/costs/{cost_id}/approve`

DUYỆT bảng chi phí `{expected_version}` (quyền `finance_approver`). Quy tắc bốn mắt: người tạo không được tự duyệt → 403.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `cost_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `expected_version`.

*Ghi chú:* Chỉ chi phí ĐÃ DUYỆT mới vào giá thành của báo cáo doanh thu.

### `POST /api/tms/finance/costs/{cost_id}/documents`

Gắn chứng từ (URL https, checksum) vào bảng chi phí.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `cost_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `expected_version`.

### `DELETE /api/tms/finance/costs/{cost_id}/documents/{document_id}`

Xoá chứng từ.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `cost_id` | đường dẫn | chuỗi | có |
| `document_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `expected_version`.

### `PUT /api/tms/finance/costs/{cost_id}/documents/{document_id}`

Sửa chứng từ.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `cost_id` | đường dẫn | chuỗi | có |
| `document_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `expected_version`.

### `POST /api/tms/finance/costs/{cost_id}/items`

Thêm dòng phí vào bảng còn `draft` (`quantity`, `unit_price`, `charge_type`…). Không có thuế: mọi dòng tính `số lượng × đơn giá`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `cost_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `expected_version`.

### `DELETE /api/tms/finance/costs/{cost_id}/items/{item_id}`

Xoá dòng phí (bảng còn `draft`).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `cost_id` | đường dẫn | chuỗi | có |
| `item_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `expected_version`.

### `POST /api/tms/finance/costs/{cost_id}/reverse`

ĐẢO một bảng đã duyệt (tạo bảng âm đối ứng), kèm `reason`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `cost_id` | đường dẫn | chuỗi | có |

### `POST /api/tms/finance/costs/{cost_id}/submit`

TRÌNH bảng chi phí `{expected_version}` (quyền `finance_creator`).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `cost_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `expected_version`.

### `POST /api/tms/finance/freight-orders/{order_id}/costs`

Tạo bảng chi phí theo Freight Order (đường gốc; luồng chuẩn dùng `trips/{id}/actual-cost`).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `order_id` | đường dẫn | chuỗi | có |

### `GET /api/tms/finance/trips/{trip_id}/actual-cost`

Bảng chi phí phát sinh đang hiệu lực của chuyến.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `trip_id` | đường dẫn | chuỗi | có |

### `PUT /api/tms/finance/trips/{trip_id}/actual-cost`

**CHỐT CHI PHÍ PHÁT SINH** của chuyến đã hoàn tất: từng dòng `{name, original_amount (kế hoạch), actual_amount (thực), note, cost_index?, charge_type?}`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `trip_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `TripActualCostRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `id` | chuỗi | trống |  |
| `currency_code` | chuỗi |  |
| `carrier_id` | chuỗi | trống |  |
| `lines` | mảng<TripCostLineRequest> | có |

*Ghi chú:* Header `Idempotency-Key`. Dòng nào trùng khoản mục công thức thì tự mang Acc code của khoản mục đó. Tạo bảng chi phí ở `draft`.

## 9. Báo cáo

### `GET /api/tms/reporting/expense-vouchers`

Danh sách phiếu chi vận tải đã lập.

### `GET /api/tms/reporting/expense-vouchers/{identifier}`

Một phiếu chi (theo mã phiếu hoặc mã chuyến).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `identifier` | đường dẫn | chuỗi | có |

### `GET /api/tms/reporting/transport-revenue`

BÁO CÁO DOANH THU VẬN TẢI theo chuyến đã hoàn tất: doanh thu = giá bán cuối của hồ sơ hoàn tất, giá thành = kế hoạch báo giá + phát sinh đã duyệt, lãi gộp, biên; biểu đồ theo ngày/khách/tuyến/loại hàng/tiền tệ.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `date_from` | truy vấn | chuỗi |  |
| `date_to` | truy vấn | chuỗi |  |
| `customer_id` | truy vấn | chuỗi |  |
| `vehicle_id` | truy vấn | chuỗi |  |
| `currency_code` | truy vấn | chuỗi |  |

*Ghi chú:* Lọc `date_from`, `date_to`, `customer_id`, `vehicle_id`, `currency_code`. `exceptions[]` liệt kê DO đã giao mà chưa có hồ sơ hoàn tất (`CLOSEOUT_MISSING`).

### `GET /api/tms/reporting/transport-revenue/export.csv`

Cùng báo cáo, xuất CSV.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `date_from` | truy vấn | chuỗi |  |
| `date_to` | truy vấn | chuỗi |  |
| `customer_id` | truy vấn | chuỗi |  |
| `vehicle_id` | truy vấn | chuỗi |  |
| `currency_code` | truy vấn | chuỗi |  |

### `PUT /api/tms/reporting/trips/{trip_id}/expense-voucher`

Lập/sửa phiếu chi cho chuyến từ các dòng chi phí đã duyệt.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `trip_id` | đường dẫn | chuỗi | có |

Thân yêu cầu — `ExpenseVoucherRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `id` | chuỗi | trống |  |
| `currency_code` | chuỗi |  |
| `carrier_id` | chuỗi | trống |  |
| `lines` | mảng<TripCostLineRequest> | có |
| `voucher_no` | chuỗi | có |
| `voucher_date` | chuỗi | có |
| `do_id` | chuỗi | trống |  |
| `vehicle_manager` | chuỗi | trống |  |
| `payment_method` | chuỗi |  |
| `contract_no` | chuỗi | trống |  |
| `machine_numbers` | chuỗi | trống |  |
| `checked_by` | chuỗi | trống |  |
| `note` | chuỗi | trống |  |

## 10. Dữ liệu gốc: loại xe, xe, tài xế, bãi, công thức giá thành, Acc code

### `GET /api/acc-codes`

Danh mục Acc code (mã tài khoản kế toán) lấy từ API bên công nợ, cache 10 phút; `refresh=1` để nạp lại.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `refresh` | truy vấn | bool |  |

*Ghi chú:* Cấu hình bằng biến môi trường `EPL_ACC_CODE_API`, `EPL_ACC_CODE_TOKEN`, `EPL_ACC_CODE_COUNTRY`. Không cấu hình → trả rỗng kèm thông báo, không bịa mã.

### `GET /api/cost-formulas`

Mọi công thức giá thành theo loại xe: `terms[]` (khoản mục: `key, label, kind cost|revenue, factor per_km|per_kg|per_tonne|per_trip, rate, cost_index`), `expressions`.

### `POST /api/cost-formulas`

Lưu công thức của một loại xe `{vehicle_type_id, currency, terms[], expressions?, expected_updated_at?}`.

Thân yêu cầu (JSON) — các trường máy chủ đọc: `currency`, `driver`, `expressions`, `freight_rate`, `fuel`, `id`, `name`, `rate`, `terms`, `toll`, `vehicle_type_id`, `warehouse`, `wh`.

*Ghi chú:* Acc code (`cost_index`) DÙNG CHUNG theo khoản mục: dòng trống tự kế thừa mã chung; dòng có mã ghi vào Mapping tài khoản (`khoan_muc::<key>`) và lan sang loại xe khác cùng khoản mục. 409 nếu người khác vừa sửa (`expected_updated_at`).

### `POST /api/cost-formulas/evaluate`

Chạy thử công thức với một chuyến giả `{formula_id | terms+expressions, trip:{km, kg, …}}`.

Thân yêu cầu (JSON) — các trường máy chủ đọc: `formula_id`, `trip`.

### `GET /api/cost-formulas/fleet-overview`

Giá hiệu lực từng xe và lịch sử ghi đè để so sánh.

### `GET /api/depots`

Danh mục bãi/chi nhánh (từ bảng `locations`).

### `POST /api/depots`

Thêm/sửa bãi `{id, name, type, address}`.

Thân yêu cầu (JSON) — các trường máy chủ đọc: `address`, `id`, `name`, `type`.

### `GET /api/drivers`

Tài xế/phụ xe kèm trạng thái nhân sự và vận hành.

### `POST /api/drivers`

Thêm/sửa tài xế `{id, name, role: 'Tài xế chính'|'Phụ xe', license_type, phone, shift, depot_code, team_code, photo_url}`.

Thân yêu cầu (JSON) — các trường máy chủ đọc: `assigned_vehicle`, `id`, `image_url`, `license_type`, `name`, `phone`, `photo_url`, `role`, `shift`.

### `DELETE /api/drivers/{did}`

Xoá tài xế chưa gắn chuyến.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `did` | đường dẫn | chuỗi | có |

### `PUT /api/drivers/{driver_id}/operational-status`

Đặt tay trạng thái nhân sự `{status: available|on_leave|sick|…, note}`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `driver_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `note`, `status`.

### `GET /api/vehicle-maintenance-requests`

Bảo dưỡng của mọi xe giao với khoảng `start..end`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `start` | truy vấn | str | có |
| `end` | truy vấn | str | có |

### `POST /api/vehicle-maintenance-requests/{request_id}/approve`

Duyệt phiếu bảo dưỡng.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `request_id` | đường dẫn | chuỗi | có |

### `POST /api/vehicle-maintenance-requests/{request_id}/cancel`

Huỷ phiếu bảo dưỡng.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `request_id` | đường dẫn | chuỗi | có |

### `POST /api/vehicle-maintenance-requests/{request_id}/complete`

Hoàn tất bảo dưỡng (đặt `next_maintenance_date`).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `request_id` | đường dẫn | chuỗi | có |

### `POST /api/vehicle-maintenance-requests/{request_id}/start`

Bắt đầu bảo dưỡng.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `request_id` | đường dẫn | chuỗi | có |

### `GET /api/vehicle-types`

Loại xe: tải trọng, thể tích, số pallet, định mức dầu, tốc độ, khấu hao/km.

### `POST /api/vehicle-types`

Thêm/sửa loại xe `{id, name, max_weight, volume_capacity_m3, pallet_capacity, fuel_norm, avg_speed_kmh, dep_cost_per_km, dims, fuel_type, icon, notes}`.

Thân yêu cầu (JSON) — các trường máy chủ đọc: `baseRate`, `base_rate`, `dims`, `fuelNorm`, `fuelType`, `fuel_norm`, `fuel_type`, `icon`, `id`, `maintCost`, `maint_cost`, `maxWeight`, `max_weight`, `name`, `notes`, `palletCapacity`, `pallet_capacity`, `special`.

### `GET /api/vehicle-types/recommendations`

Loại xe nào đủ tải cho `weight_kg`, `volume_m3`, `pallet_count` (ba chiều).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `weight_kg` | truy vấn | float |  |
| `volume_m3` | truy vấn | float |  |
| `pallet_count` | truy vấn | int |  |

### `DELETE /api/vehicle-types/{vid}`

Xoá loại xe chưa có xe/báo giá dùng (409 `LOCKED_RECORD` nếu đang dùng).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `vid` | đường dẫn | chuỗi | có |

### `GET /api/vehicles`

Đội xe: `paginated`, `page`, `page_size`, `depot_code`. Mỗi xe kèm trạng thái vận hành và loại xe.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `paginated` | truy vấn | bool |  |
| `page` | truy vấn | int |  |
| `page_size` | truy vấn | int |  |
| `depot_code` | truy vấn | chuỗi |  |

### `POST /api/vehicles`

Thêm/sửa xe `{id (biển số), brand, type (MÃ loại xe), weight_capacity, volume_capacity_m3, pallet_capacity, inspection_exp, insurance_date, maintenance_date, depot_code, status, image_url…}`.

Thân yêu cầu (JSON) — các trường máy chủ đọc: `depot_code`, `id`.

*Ghi chú:* `type` phải là MÃ loại xe (vd `DEMO-VT-20FT`), không phải tên.

### `GET /api/vehicles/{vehicle_id}/cost`

Giá thành THỰC của một xe: công thức loại xe + đơn giá ghi đè của xe.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `vehicle_id` | đường dẫn | chuỗi | có |

### `PUT /api/vehicles/{vehicle_id}/cost-overrides`

Ghi đè đơn giá vài khoản mục cho riêng xe này `{overrides:[{component, value, note}]}` (xe cũ tốn dầu hơn…).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `vehicle_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `overrides`.

### `GET /api/vehicles/{vehicle_id}/maintenance-requests`

Phiếu bảo dưỡng của một xe.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `vehicle_id` | đường dẫn | chuỗi | có |

### `POST /api/vehicles/{vehicle_id}/maintenance-requests`

Lập phiếu bảo dưỡng `{category, priority, planned_start, planned_end, description, workshop, estimated_total…}`. Xe trong lịch bảo dưỡng không điều phối được.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `vehicle_id` | đường dẫn | chuỗi | có |

### `PUT /api/vehicles/{vehicle_id}/operational-status`

Đặt tay trạng thái vận hành xe `{status, note}`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `vehicle_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `note`, `status`.

### `DELETE /api/vehicles/{vid}`

Xoá xe không còn gắn chuyến.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `vid` | đường dẫn | chuỗi | có |

## 11. Dữ liệu gốc: khách hàng, tuyến, địa điểm

### `GET /api/customers`

Khách hàng.

### `POST /api/customers`

Thêm khách `{id, name, type, contact_person, phone, address}`.

Thân yêu cầu (JSON) — các trường máy chủ đọc: `address`, `contact_person`, `id`, `name`, `phone`, `type`.

### `DELETE /api/customers/{customer_id}`

Xoá khách chưa có báo giá/DO (409 nếu đang dùng).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `customer_id` | đường dẫn | chuỗi | có |

### `PUT /api/customers/{customer_id}`

Sửa khách.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `customer_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `address`, `contact_person`, `name`, `phone`, `type`.

### `GET /api/locations/coordinates`

Địa điểm kèm toạ độ, và danh sách địa điểm CHƯA có toạ độ.

### `PUT /api/locations/{location_id}/coordinates`

Khai tay toạ độ `{latitude, longitude}`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `location_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `latitude`, `longitude`.

### `GET /api/routes`

Tuyến đường: `distance_km`, các chặng `segments_json`, BOT theo tuyến, cờ có hình đường bộ.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `paginated` | truy vấn | bool |  |
| `page` | truy vấn | int |  |
| `page_size` | truy vấn | int |  |

### `POST /api/routes`

Thêm/sửa tuyến `{id, name, distance_km, segments_json:[{origin, destination, distance_km}]}`.

Thân yêu cầu — `RouteCreateRequest`:

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `id` | chuỗi | trống |  |
| `name` | chuỗi | trống |  |
| `distance_km` | số nguyên | số | trống |  |
| `segments_json` | chuỗi | trống |  |

*Ghi chú:* Số km của tuyến là đầu vào của MỌI công thức giá thành; tuyến 0 km thì báo giá không tính được.

### `DELETE /api/routes/{route_id}`

Xoá tuyến chưa có báo giá/DO dùng.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `route_id` | đường dẫn | chuỗi | có |

### `GET /api/routes/{route_id}/geo`

Tuyến kèm toạ độ điểm và hình đường bộ (được phép gọi dịch vụ bản đồ ngoài).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `route_id` | đường dẫn | chuỗi | có |

## 12. Mapping tài khoản

### `POST /api/master-data/account-mappings`

Thêm mapping `{mapping_key, account_code, effective_from?, effective_to?}`. Các khoá `khoan_muc::*` là Acc code dùng chung của khoản mục công thức.

Thân yêu cầu (JSON) — các trường máy chủ đọc: `effective_from`, `effective_to`.

### `DELETE /api/master-data/account-mappings/{mapping_key}`

Xoá mapping.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `mapping_key` | đường dẫn | chuỗi | có |

### `PUT /api/master-data/account-mappings/{mapping_key}`

Sửa mapping.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `mapping_key` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `mapping_key`.

### `POST /api/master-data/account-mappings/{mapping_key}/status`

Bật/tắt `{status: active|inactive}`.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `mapping_key` | đường dẫn | chuỗi | có |

## 13. Tiền tệ và tỷ giá

### `GET /api/currencies`

Tiền tệ và tỷ giá về VND (bảng `currencies`).

### `POST /api/currencies`

Thêm/sửa tỷ giá `{id: 'USD', exchange_rate}`.

### `GET /api/currencies/history`

Lịch sử tỷ giá.

### `GET /api/currencies/reference-rates`

Tỷ giá tham chiếu lấy từ nguồn ngoài (nếu cấu hình).

### `POST /api/currencies/reference-rates/refresh`

Nạp lại tỷ giá tham chiếu.

## 14. Bảng điều khiển và sự cố

### `GET /api/dashboard/stats`

Chỉ số bảng điều khiển: `revenue_ytd` = tổng giá bán cuối các hồ sơ hoàn tất, `completed_deliveries`, `total_deliveries`, `in_transit_orders`, `active_vehicles`, `incidents_count`.

### `GET /api/incidents`

Sự cố trên đường.

### `POST /api/incidents`

Báo sự cố `{do_id, vehicle_id, incident_type, severity, location, description, reporter}`. Xe phải thuộc DO/chuyến đó.

Thân yêu cầu (JSON) — các trường máy chủ đọc: `description`, `do_id`, `incident_type`, `location`, `reporter`, `severity`, `vehicle_id`.

### `PUT /api/incidents/{incident_id}/status`

Đổi trạng thái một sự cố: đang xử lý, đã xử lý (đóng), hoặc mở lại.

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `incident_id` | đường dẫn | chuỗi | có |

Thân yêu cầu (JSON) — các trường máy chủ đọc: `note`, `status`.

*Ghi chú:* Thân: `status` nhận `Open` | `In Progress` | `Resolved`, và `note` (ghi chú xử lý). Đóng sự cố (`Resolved`) BẮT BUỘC có `note` — đóng mà không nói đã xử lý thế nào thì người đọc sổ sau này không biết gì. Gửi lại đúng trạng thái đang có mà không kèm ghi chú thì trả về nguyên trạng, không ghi thêm lịch sử.

## 15. Dữ liệu tổng cho giao diện

### `GET /api/data/all`

Ảnh chụp mọi danh mục cho giao diện nạp một lần (khách, tuyến, xe, tài xế, báo giá, DO, chuyến, phiếu…). Dữ liệu người dùng/vai trò/nhật ký được che.

## 16. Trợ lý AI và tải ảnh

### `POST /api/agent/action`

Nhờ trợ lý AI thực hiện thao tác `{prompt}` (có xác nhận).

Thân yêu cầu (JSON) — các trường máy chủ đọc: `prompt`.

### `POST /api/agent/query`

Hỏi trợ lý AI về dữ liệu vận hành `{prompt}` (đọc, không ghi).

Thân yêu cầu (JSON) — các trường máy chủ đọc: `prompt`.

### `POST /api/ai/checkpoint/scan`

Trạm kiểm soát AI: nhận ảnh, đọc biển số/chứng từ (multipart `file`).

Thân yêu cầu (multipart/form-data):

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `file` | chuỗi | có |

### `POST /api/uploads/images`

Tải ảnh xe/tài xế (multipart `entity_type`, `file`).

Thân yêu cầu (multipart/form-data):

| Trường | Kiểu | Bắt buộc |
|---|---|---|
| `entity_type` | chuỗi | có |
| `file` | chuỗi | có |

### `POST /api/v1/ai/chat`

Chat AI hai bước `{prompt, draft_data?, is_confirmed?}`.

Thân yêu cầu (JSON) — các trường máy chủ đọc: `draft_data`, `is_confirmed`, `prompt`.

### `GET /uploads/{asset_path:path}`

Ảnh đã tải (công khai, tên tệp uuid).

| Tham số | Vị trí | Kiểu | Bắt buộc |
|---|---|---|---|
| `asset_path` | đường dẫn | chuỗi | có |

## 17. Kiểm tra sức khoẻ

### `GET /api/health`

Sống hay chưa (không chạm DB).

*Ghi chú:* Công khai.

### `GET /api/health/database`

Sẵn sàng: DB nối được, mốc nâng cấp đủ, lược đồ đủ bảng/cột.

*Ghi chú:* Công khai. `DATABASE_SCHEMA_INVALID` khi lược đồ lệch.

## 18. Trang tĩnh

### `GET /`

Trang giao diện.

### `GET /favicon.ico`

Biểu tượng.

### `GET /kich-ban-test`

Kịch bản kiểm.

### `GET /test-runner`

Trang chạy bộ kiểm giao diện.

### `GET /tongquan.jpg`

Ảnh sơ đồ tổng quan.

