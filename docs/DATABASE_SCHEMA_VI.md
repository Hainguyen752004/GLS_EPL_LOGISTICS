# Lược đồ cơ sở dữ liệu — EPL Logistics

Sinh từ `backend/app/models.py` ngày 2026-09-11 bằng `backend/scripts/sinh_tai_lieu.py`. Cơ sở dữ liệu: **PostgreSQL** (duy nhất). Đầu mốc nâng cấp: `052_bo_bang_di_san_items_uoms_price_lists`. Tổng 57 bảng.

## Mô hình ba tầng

- **Báo giá (`quotations`)** = thoả thuận với khách: tuyến nào, loại xe gì, giá bao nhiêu. Mọi con số tiền khách thấy có gốc ở đây.
- **Lệnh giao hàng (`delivery_orders`)** = yêu cầu cụ thể của khách; sinh TỰ ĐỘNG khi khách chấp nhận báo giá, mang giá khoá `unit_price`. Công nợ khách đi theo DO — hồ sơ hoàn tất (`delivery_order_closeouts`) và sổ thu–chi bàn giao theo DO.
- **Chuyến (`transport_trips`)** = cách công ty thực hiện DO: xe nào, tài xế nào, chạy lúc nào. Chi phí phát sinh (`freight_actual_costs`) ghi ở tầng chuyến rồi phân bổ về DO.

## Những bảng đã xoá (10/09/2026) — không còn trong lược đồ

- Bước Đơn hàng (SO): `sales_orders`, `sales_order_lines`, `sales_order_documents`, cột `so_id` (mốc 049). Báo giá được chấp nhận tách thẳng thành DO.
- Module kế toán, thuế, kỳ kế toán: `ar_invoices`, `gl_transactions`, `chart_of_accounts`, `journal_batches`, `journal_lines`, `ap_invoices`, `ap_invoice_lines`, `freight_settlements`, `settlement_payments`, `tax_codes`, `accounting_periods` (mốc 051). Hoá đơn và hạch toán là việc của hệ công nợ; hệ này bàn giao qua `GET /api/handover/delivery-orders[/{do_id}]`.
- Bảng di sản rỗng: `delivery_order_details`, `quotation_details`, `pod`, `shipment_costs` (051), `items`, `uoms`, `price_lists` (052).

## Danh sách bảng theo nhóm

### Dữ liệu gốc

| Bảng | Chức năng | Số cột |
|---|---|---|
| `account_mappings` | Mapping tài khoản. Các khoá `khoan_muc::<key>` là Acc code DÙNG CHUNG của từng khoản mục công thức. | 4 |
| `carriers` | Nhà vận chuyển: đội xe nội bộ hoặc thuê ngoài. | 10 |
| `cost_formulas` | Công thức giá thành theo loại xe (JSON trong `formula_expression`): khoản mục chi/thu, đơn giá, hệ số nhân, Acc code, lịch sử. | 3 |
| `currencies` | Tiền tệ và tỷ giá về VND dùng cho báo giá ngoại tệ. | 2 |
| `currency_definitions` | Định nghĩa tiền tệ (số lẻ) cho tính tiền chính xác. | 5 |
| `currency_rate_history` | Lịch sử tỷ giá theo ngày để quy đổi báo cáo về tiền tệ chức năng. | 8 |
| `customers` | Khách hàng (chủ hàng). Mọi báo giá, DO, cơ hội đều trỏ về đây. | 7 |
| `driver_qualifications` | Bằng lái và hiệu lực; điều phối chặn tài xế không có bằng còn hạn. | 7 |
| `drivers` | Tài xế và phụ xe: bằng lái, bãi, tổ, mẫu xoay ca, trạng thái nhân sự và vận hành. | 16 |
| `finance_control_config` | Cấu hình tài chính toàn cục: tiền tệ chức năng, bốn mắt bật/tắt, ngưỡng lệch km. | 8 |
| `locations` | Địa điểm: bãi/chi nhánh, kho, cảng; toạ độ để vẽ tuyến và tính ETA. | 7 |
| `routes` | Tuyến đường: số km, các chặng (`segments_json`), hình đường bộ thật (`road_geometry_json`), phí BOT theo tuyến. | 7 |
| `vehicle_cost_overrides` | Đơn giá ghi đè của riêng một xe cho vài khoản mục (xe cũ tốn dầu hơn…). | 7 |
| `vehicle_maintenance_cost_lines` | Dòng chi phí của phiếu bảo dưỡng. | 10 |
| `vehicle_maintenance_requests` | Phiếu bảo dưỡng xe: kế hoạch, thực tế, xưởng, chi phí; xe trong lịch bảo dưỡng không điều phối được. | 28 |
| `vehicle_types` | Loại xe: tải trọng, thể tích, pallet, định mức dầu, tốc độ, khấu hao/km. Báo giá chốt theo LOẠI xe. | 15 |
| `vehicles` | Từng chiếc xe: biển số, loại (MÃ loại xe), năng lực, ba hạn pháp lý (đăng kiểm, bảo hiểm, bảo dưỡng), bãi, trạng thái vận hành. | 29 |

### Phân quyền

| Bảng | Chức năng | Số cột |
|---|---|---|
| `roles` | Vai trò và danh sách quyền (JSON): `finance_read`, `finance_creator`, `finance_approver`… | 2 |
| `users` | Người dùng → vai trò. Danh tính đến từ token của hệ thống cha. | 3 |

### Kinh doanh

| Bảng | Chức năng | Số cột |
|---|---|---|
| `crm_opportunities` | Cơ hội khách hàng (CRM-01): khách/khách tiềm năng, tuyến, hàng, sản lượng, giai đoạn, chủ, lý do mất; gắn báo giá khi đã lập. | 26 |
| `quotation_attachments` | Chứng từ đính kèm báo giá. | 10 |
| `quotation_items` | Dòng hàng hoá của báo giá (tên, số lượng, ĐVT). Tổng số lượng = số DO sinh khi khách chấp nhận. | 8 |
| `quotation_versions` | Phiên bản giá mỗi lần gửi khách (giá, đơn vị, tiền tệ, tỷ giá). | 12 |
| `quotations` | BÁO GIÁ — thoả thuận với khách: tuyến, loại xe, tải trọng, khung giờ, đơn vị cước + đơn giá (giá CUỐI), tổng giá thành, biên mục tiêu, giá đối thủ, chiết khấu, hiệu lực, ba ô ghi chú, trạng thái. | 61 |

### Vận hành

| Bảng | Chức năng | Số cột |
|---|---|---|
| `delivery_order_charge_adjustments` | Các khoản khách trả thêm ghi lúc hoàn tất (kèm Acc code). | 11 |
| `delivery_order_closeouts` | HỒ SƠ HOÀN TẤT của DO: giá gốc, khách trả thêm, GIÁ BÁN CUỐI, tiền tệ, lúc hoàn tất. Nguồn doanh thu của báo cáo và của API bàn giao. | 11 |
| `delivery_orders` | LỆNH GIAO HÀNG (DO) — yêu cầu cụ thể của khách, sinh tự động khi khách chấp nhận báo giá; mang `quotation_id`, giá khoá `unit_price`, khung lấy/giao, xe/tài xế đã điều, lý do huỷ. | 42 |
| `delivery_pod_documents` | Ảnh POD / ảnh chữ ký / PDF (lưu nội dung nhị phân, checksum). | 9 |
| `delivery_pod_records` | POD từng chặng: người nhận, giờ giao, kết quả, tình trạng hàng, số lượng thực. | 22 |
| `freight_order_legacy_links` | Nối Freight Order ↔ DO. | 2 |
| `freight_orders` | Đơn vận chuyển nội bộ sinh cùng chuyến (điểm lấy/giao, khung giờ, tổng tải). | 19 |
| `incidents` | Sự cố trên đường theo DO/xe. | 10 |
| `resource_assignments` | Phân công xe/tổ lái cho chuyến trong một khung giờ — cơ sở để khoá lịch và phát hiện trùng. | 12 |
| `transport_event_documents` | Chứng từ gắn vào mốc thực thi. | 9 |
| `transport_events` | Mốc thực thi: check_in, pickup, departure, arrival, unloading, delivered, lệch tuyến… kèm GPS, ETA. | 20 |
| `transport_trip_legs` | Chặng của chuyến: điểm đi/đến, km, tốc độ, dừng, người nhận, mốc. | 23 |
| `transport_trips` | CHUYẾN XE — cách công ty thực hiện DO: loại chuyến, xe, tài xế, phụ xe, mốc kế hoạch và thực tế. | 18 |
| `trip_delivery_orders` | Chuyến ↔ DO (một chuyến có thể chở nhiều DO). | 5 |
| `vehicle_tracking` | Vị trí GPS mới nhất theo DO/xe, km còn lại, ETA. | 9 |

### Bãi xe

| Bảng | Chức năng | Số cột |
|---|---|---|
| `parking_events` | Lịch sử quét QR / đổi trạng thái của phiếu. | 6 |
| `parking_labels` | Nhãn từng kiện với mã QR. | 8 |
| `parking_list_items` | Dòng hàng của phiếu (từ dòng hàng hoá báo giá). | 14 |
| `parking_lists` | Phiếu bãi xe / packing list của một DO: kiện, khối lượng, khối, trạng thái. | 20 |

### Chi phí

| Bảng | Chức năng | Số cột |
|---|---|---|
| `freight_actual_costs` | Bảng CHI PHÍ PHÁT SINH của một chuyến đã hoàn tất: tiền tệ, tỷ giá, km kế hoạch/thực, trạng thái, người tạo/duyệt, đảo. | 34 |
| `freight_charge_items` | Dòng chi phí: khoản mục, Acc code, kế hoạch, thực tế, phần vượt. Không thuế (thuế do hệ công nợ tính). | 22 |
| `freight_cost_documents` | Chứng từ của bảng chi phí (URL, checksum, số hoá đơn nhà cung cấp). | 13 |

### Báo cáo

| Bảng | Chức năng | Số cột |
|---|---|---|
| `epl_expense_vouchers` | Phiếu chi vận tải lập từ chi phí đã duyệt (số phiếu, ngày, hình thức thanh toán). | 17 |

### Sắp lịch

| Bảng | Chức năng | Số cột |
|---|---|---|
| `driver_shift_assignments` | Ca trực / ca nghỉ của tài xế; điều phối đòi ca phủ trọn thời gian chuyến. | 16 |

### TMS gốc

| Bảng | Chức năng | Số cột |
|---|---|---|
| `freight_order_units` | Freight Order ↔ đơn vị hàng. | 2 |
| `freight_units` | Đơn vị hàng tách từ nhu cầu. | 15 |
| `tender_offers` | Chào giá của nhà vận chuyển. | 9 |
| `tenders` | Đấu thầu thuê ngoài cho Freight Order. | 11 |
| `transport_demands` | Nhu cầu vận chuyển (mô-đun TMS gốc, ngoài luồng Báo giá → DO). | 18 |
| `warehouse_appointments` | Lịch hẹn lấy/giao tại kho. | 10 |

### Hệ thống

| Bảng | Chức năng | Số cột |
|---|---|---|
| `audit_logs` | Nhật ký kiểm toán: ai làm gì, bảng nào, bản ghi nào, lúc nào, từ IP nào. | 7 |
| `idempotency_records` | Cache trả lời theo `Idempotency-Key` để lệnh gọi lặp không tạo hai lần. | 9 |
| `migration_quarantine` | Bản ghi bị cách ly khi nâng cấp không chuyển được. | 7 |

## Chi tiết từng bảng

### `account_mappings` — Dữ liệu gốc

Mapping tài khoản. Các khoá `khoan_muc::<key>` là Acc code DÙNG CHUNG của từng khoản mục công thức.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `mapping_key` | VARCHAR | có | PK |
| `account_code` | VARCHAR | có |  |
| `effective_from` | DATETIME |  |  |
| `effective_to` | DATETIME |  |  |

### `audit_logs` — Hệ thống

Nhật ký kiểm toán: ai làm gì, bảng nào, bản ghi nào, lúc nào, từ IP nào.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `user_id` | VARCHAR |  |  |
| `action` | VARCHAR |  |  |
| `table_name` | VARCHAR |  |  |
| `record_id` | VARCHAR |  |  |
| `timestamp` | DATETIME |  |  |
| `ip_address` | VARCHAR |  |  |

### `carriers` — Dữ liệu gốc

Nhà vận chuyển: đội xe nội bộ hoặc thuê ngoài.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `name` | VARCHAR | có |  |
| `tax_code` | VARCHAR |  |  |
| `contact_person` | VARCHAR |  |  |
| `phone` | VARCHAR |  |  |
| `email` | VARCHAR |  |  |
| `status` | VARCHAR | có |  |
| `is_internal` | BOOLEAN | có |  |
| `created_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |

### `cost_formulas` — Dữ liệu gốc

Công thức giá thành theo loại xe (JSON trong `formula_expression`): khoản mục chi/thu, đơn giá, hệ số nhân, Acc code, lịch sử. Một loại xe một công thức VND.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `name` | VARCHAR |  |  |
| `formula_expression` | TEXT |  |  |

### `crm_opportunities` — Kinh doanh

Cơ hội khách hàng (CRM-01): khách/khách tiềm năng, tuyến, hàng, sản lượng, giai đoạn, chủ, lý do mất; gắn báo giá khi đã lập. Giai đoạn: new, contacted, negotiating, quoted, won, lost.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(64) | có | PK |
| `customer_id` | VARCHAR |  | FK → `customers.id` |
| `prospect_name` | VARCHAR(255) |  |  |
| `contact_name` | VARCHAR(255) |  |  |
| `contact_phone` | VARCHAR(64) |  |  |
| `contact_email` | VARCHAR(255) |  |  |
| `source` | VARCHAR(32) | có |  |
| `route_id` | VARCHAR |  | FK → `routes.id` |
| `origin_text` | VARCHAR(255) |  |  |
| `destination_text` | VARCHAR(255) |  |  |
| `cargo_type` | VARCHAR(255) |  |  |
| `est_weight_kg` | FLOAT | có |  |
| `est_trips_per_month` | INTEGER | có |  |
| `expected_start` | VARCHAR(32) |  |  |
| `expected_price` | NUMERIC(24, 6) |  |  |
| `stage` | VARCHAR(20) | có |  |
| `owner` | VARCHAR(128) |  |  |
| `notes` | TEXT |  |  |
| `lost_reason` | TEXT |  |  |
| `quotation_id` | VARCHAR |  | FK → `quotations.id` |
| `next_action_at` | DATETIME |  |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR(128) | có |  |
| `updated_by` | VARCHAR(128) | có |  |
| `version` | INTEGER | có |  |

Ràng buộc: `stage IN ('new','contacted','negotiating','quoted','won','lost')`; `version > 0`

### `currencies` — Dữ liệu gốc

Tiền tệ và tỷ giá về VND dùng cho báo giá ngoại tệ.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `exchange_rate` | NUMERIC(24, 6) |  |  |

### `currency_definitions` — Dữ liệu gốc

Định nghĩa tiền tệ (số lẻ) cho tính tiền chính xác.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `code` | VARCHAR(3) | có | PK |
| `minor_units` | INTEGER | có |  |
| `is_active` | BOOLEAN | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |

Ràng buộc: `minor_units >= 0 AND minor_units <= 6`

### `currency_rate_history` — Dữ liệu gốc

Lịch sử tỷ giá theo ngày để quy đổi báo cáo về tiền tệ chức năng.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `currency_code` | VARCHAR(3) | có | FK → `currency_definitions.code` |
| `functional_currency` | VARCHAR(3) | có | FK → `currency_definitions.code` |
| `rate_date` | DATE | có |  |
| `rate` | NUMERIC(18, 8) | có |  |
| `source` | VARCHAR(100) | có |  |
| `is_active` | BOOLEAN | có |  |
| `created_at` | DATETIME | có |  |

Ràng buộc: `rate > 0`

### `customers` — Dữ liệu gốc

Khách hàng (chủ hàng). Mọi báo giá, DO, cơ hội đều trỏ về đây.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `name` | VARCHAR | có |  |
| `type` | VARCHAR |  |  |
| `contact_person` | VARCHAR |  |  |
| `phone` | VARCHAR |  |  |
| `address` | VARCHAR |  |  |
| `vendor_type` | VARCHAR |  |  |

### `delivery_order_charge_adjustments` — Vận hành

Các khoản khách trả thêm ghi lúc hoàn tất (kèm Acc code).

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(128) | có | PK |
| `closeout_id` | VARCHAR(128) | có | FK → `delivery_order_closeouts.id` |
| `line_no` | INTEGER | có |  |
| `name` | VARCHAR(255) | có |  |
| `cost_index` | VARCHAR(32) |  |  |
| `original_amount` | NUMERIC(24, 6) | có |  |
| `actual_amount` | NUMERIC(24, 6) | có |  |
| `increase_amount` | NUMERIC(24, 6) | có |  |
| `note` | TEXT |  |  |
| `created_at` | DATETIME | có |  |
| `created_by` | VARCHAR(255) | có |  |

Ràng buộc: `actual_amount >= original_amount`; `original_amount >= 0`; `increase_amount = actual_amount - original_amount`; `line_no > 0`

### `delivery_order_closeouts` — Vận hành

HỒ SƠ HOÀN TẤT của DO: giá gốc, khách trả thêm, GIÁ BÁN CUỐI, tiền tệ, lúc hoàn tất. Nguồn doanh thu của báo cáo và của API bàn giao.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(128) | có | PK |
| `do_id` | VARCHAR | có | FK → `delivery_orders.id`, duy nhất |
| `base_selling_price_snapshot` | NUMERIC(24, 6) | có |  |
| `base_price_source` | VARCHAR(32) | có |  |
| `base_price_source_id` | VARCHAR(128) | có |  |
| `surcharge_total` | NUMERIC(24, 6) | có |  |
| `final_selling_price` | NUMERIC(24, 6) | có |  |
| `currency_code` | VARCHAR(3) | có |  |
| `completed_at` | DATETIME | có |  |
| `completed_by` | VARCHAR(255) | có |  |
| `created_at` | DATETIME | có |  |

Ràng buộc: `final_selling_price >= 0`; `base_selling_price_snapshot >= 0`; `surcharge_total >= 0`; `final_selling_price = base_selling_price_snapshot + surcharge_total`

### `delivery_orders` — Vận hành

LỆNH GIAO HÀNG (DO) — yêu cầu cụ thể của khách, sinh tự động khi khách chấp nhận báo giá; mang `quotation_id`, giá khoá `unit_price`, khung lấy/giao, xe/tài xế đã điều, lý do huỷ. Trạng thái: pending, in_transit, arrived, delivered, cancelled.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `canonical_status` | VARCHAR | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |
| `updated_by` | VARCHAR | có |  |
| `version` | INTEGER | có |  |
| `quotation_id` | VARCHAR |  | FK → `quotations.id` |
| `unit_price` | NUMERIC(24, 6) |  |  |
| `price_basis` | VARCHAR |  |  |
| `billed_qty` | FLOAT |  |  |
| `driver_note` | TEXT |  |  |
| `customer_id` | VARCHAR |  | FK → `customers.id` |
| `route_id` | VARCHAR |  | FK → `routes.id` |
| `origin` | VARCHAR |  |  |
| `destination` | VARCHAR |  |  |
| `pickup_window_start` | DATETIME |  |  |
| `pickup_window_end` | DATETIME |  |  |
| `delivery_window_start` | DATETIME |  |  |
| `delivery_window_end` | DATETIME |  |  |
| `weight_kg` | FLOAT |  |  |
| `pallet_count` | INTEGER |  |  |
| `notes` | TEXT |  |  |
| `cancel_reason` | TEXT |  |  |
| `vehicle_id` | VARCHAR |  | FK → `vehicles.id` |
| `driver_id` | VARCHAR |  | FK → `drivers.id` |
| `co_driver` | VARCHAR |  |  |
| `status` | VARCHAR |  |  |
| `pickup_date` | DATETIME |  |  |
| `delivery_date` | DATETIME |  |  |
| `planned_departure_at` | DATETIME |  |  |
| `planned_arrival_at` | DATETIME |  |  |
| `planned_return_at` | DATETIME |  |  |
| `avg_speed_kmh` | FLOAT |  |  |
| `max_speed_kmh` | FLOAT |  |  |
| `return_speed_kmh` | FLOAT |  |  |
| `load_minutes` | INTEGER |  |  |
| `unload_minutes` | INTEGER |  |  |
| `return_distance_km` | FLOAT |  |  |
| `packaging_spec` | VARCHAR |  |  |
| `volume_m3` | FLOAT |  |  |
| `seal_no` | VARCHAR |  |  |

Ràng buộc: `canonical_status IN ('pending','in_transit','arrived','delivered','cancelled')`

### `delivery_pod_documents` — Vận hành

Ảnh POD / ảnh chữ ký / PDF (lưu nội dung nhị phân, checksum).

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(128) | có | PK |
| `pod_record_id` | INTEGER | có | FK → `delivery_pod_records.id` |
| `file_name` | VARCHAR(255) | có |  |
| `mime_type` | VARCHAR(128) | có |  |
| `file_size` | INTEGER | có |  |
| `checksum` | VARCHAR(128) | có |  |
| `content` | BLOB | có |  |
| `created_at` | DATETIME | có |  |
| `created_by` | VARCHAR(255) | có |  |

Ràng buộc: `file_size >= 0 AND file_size <= 10485760`

### `delivery_pod_records` — Vận hành

POD từng chặng: người nhận, giờ giao, kết quả, tình trạng hàng, số lượng thực.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `idempotency_key` | VARCHAR(128) |  |  |
| `do_id` | VARCHAR | có | FK → `delivery_orders.id` |
| `trip_id` | VARCHAR(128) |  | FK → `transport_trips.id` |
| `leg_id` | VARCHAR(128) |  | FK → `transport_trip_legs.id` |
| `vehicle_id` | VARCHAR | có | FK → `vehicles.id` |
| `driver_id` | VARCHAR |  | FK → `drivers.id` |
| `stop_no` | INTEGER | có |  |
| `location_text` | VARCHAR |  |  |
| `receiver_name` | VARCHAR |  |  |
| `receiver_phone` | VARCHAR |  |  |
| `delivery_time` | DATETIME |  |  |
| `photo_url` | VARCHAR |  |  |
| `signature_url` | VARCHAR |  |  |
| `delivery_result` | VARCHAR(32) |  |  |
| `actual_qty` | FLOAT |  |  |
| `actual_qty_uom` | VARCHAR |  |  |
| `cargo_condition` | TEXT |  |  |
| `note` | TEXT |  |  |
| `status` | VARCHAR | có |  |
| `created_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |

Ràng buộc: `stop_no > 0`

### `driver_qualifications` — Dữ liệu gốc

Bằng lái và hiệu lực; điều phối chặn tài xế không có bằng còn hạn.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `driver_id` | VARCHAR | có | PK, FK → `drivers.id` |
| `license_type` | VARCHAR | có |  |
| `valid_from` | DATETIME | có |  |
| `valid_to` | DATETIME | có |  |
| `status` | VARCHAR | có |  |
| `verified_at` | DATETIME | có |  |
| `verified_by` | VARCHAR | có |  |

### `driver_shift_assignments` — Sắp lịch

Ca trực / ca nghỉ của tài xế; điều phối đòi ca phủ trọn thời gian chuyến.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(128) | có | PK |
| `driver_id` | VARCHAR | có | FK → `drivers.id` |
| `vehicle_id` | VARCHAR |  | FK → `vehicles.id` |
| `trip_id` | VARCHAR(128) |  | FK → `transport_trips.id` |
| `shift_type` | VARCHAR(20) | có |  |
| `availability_kind` | VARCHAR(20) | có |  |
| `shift_start` | DATETIME | có |  |
| `shift_end` | DATETIME | có |  |
| `work_location` | VARCHAR(500) |  |  |
| `notes` | TEXT |  |  |
| `status` | VARCHAR(20) | có |  |
| `version` | INTEGER | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR(128) | có |  |
| `updated_by` | VARCHAR(128) | có |  |

Ràng buộc: `shift_end > shift_start`; `status IN ('planned','confirmed','cancelled')`; `availability_kind IN ('work','leave','sick','off','unavailable')`; `shift_type IN ('morning','afternoon','night','office','custom')`

### `drivers` — Dữ liệu gốc

Tài xế và phụ xe: bằng lái, bãi, tổ, mẫu xoay ca, trạng thái nhân sự và vận hành.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `name` | VARCHAR | có |  |
| `role` | VARCHAR |  |  |
| `license_type` | VARCHAR |  |  |
| `phone` | VARCHAR |  |  |
| `assigned_vehicle` | VARCHAR |  |  |
| `shift` | VARCHAR |  |  |
| `status` | VARCHAR |  |  |
| `operational_status` | VARCHAR(32) | có |  |
| `operational_ref` | VARCHAR(128) |  |  |
| `operational_note` | TEXT |  |  |
| `operational_updated_at` | DATETIME |  |  |
| `photo_url` | TEXT |  |  |
| `depot_code` | VARCHAR |  |  |
| `team_code` | VARCHAR |  |  |
| `rotation_pattern` | VARCHAR |  |  |

### `epl_expense_vouchers` — Báo cáo

Phiếu chi vận tải lập từ chi phí đã duyệt (số phiếu, ngày, hình thức thanh toán).

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(128) | có | PK |
| `trip_id` | VARCHAR(128) | có | FK → `transport_trips.id` |
| `cost_id` | VARCHAR(128) | có | FK → `freight_actual_costs.id` |
| `do_id` | VARCHAR |  | FK → `delivery_orders.id` |
| `voucher_no` | VARCHAR(128) | có |  |
| `voucher_date` | DATE | có |  |
| `vehicle_manager` | VARCHAR(255) |  |  |
| `payment_method` | VARCHAR(32) | có |  |
| `contract_no` | VARCHAR(128) |  |  |
| `machine_numbers` | VARCHAR(500) |  |  |
| `checked_by` | VARCHAR(255) |  |  |
| `note` | TEXT |  |  |
| `version` | INTEGER | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR(128) | có |  |
| `updated_by` | VARCHAR(128) | có |  |

Ràng buộc: `payment_method IN ('cash','bank_transfer','credit','other')`; `version > 0`

### `finance_control_config` — Dữ liệu gốc

Cấu hình tài chính toàn cục: tiền tệ chức năng, bốn mắt bật/tắt, ngưỡng lệch km. Một dòng `GLOBAL`.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(20) | có | PK |
| `functional_currency` | VARCHAR(3) | có | FK → `currency_definitions.code` |
| `enforce_creator_approver_sod` | BOOLEAN | có |  |
| `require_distinct_poster` | BOOLEAN | có |  |
| `distance_variance_threshold` | NUMERIC(18, 8) | có |  |
| `document_https_hosts` | TEXT | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |

Ràng buộc: `id = 'GLOBAL'`; `distance_variance_threshold >= 0`

### `freight_actual_costs` — Chi phí

Bảng CHI PHÍ PHÁT SINH của một chuyến đã hoàn tất: tiền tệ, tỷ giá, km kế hoạch/thực, trạng thái, người tạo/duyệt, đảo. Trạng thái: draft, submitted, approved, reversed. Chỉ `approved` vào báo cáo.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `freight_order_id` | VARCHAR | có | FK → `freight_orders.id` |
| `trip_id` | VARCHAR(128) |  | FK → `transport_trips.id` |
| `leg_id` | VARCHAR(128) |  | FK → `transport_trip_legs.id` |
| `carrier_id` | VARCHAR | có | FK → `carriers.id` |
| `currency_code` | VARCHAR(3) | có | FK → `currency_definitions.code` |
| `functional_currency` | VARCHAR(3) | có | FK → `currency_definitions.code` |
| `exchange_rate_snapshot` | NUMERIC(18, 8) | có |  |
| `exchange_rate_date` | DATE | có |  |
| `exchange_rate_source` | VARCHAR(100) | có |  |
| `planned_distance_km` | NUMERIC(18, 3) | có |  |
| `actual_distance_km` | NUMERIC(18, 3) | có |  |
| `distance_status` | VARCHAR(32) | có |  |
| `distance_variance_percent` | NUMERIC(18, 8) |  |  |
| `distance_variance_warning` | BOOLEAN | có |  |
| `subtotal_amount` | NUMERIC(24, 6) | có |  |
| `tax_amount` | NUMERIC(24, 6) | có |  |
| `total_amount` | NUMERIC(24, 6) | có |  |
| `status` | VARCHAR(16) | có |  |
| `is_active` | BOOLEAN | có |  |
| `version` | INTEGER | có |  |
| `reversal_of_cost_id` | VARCHAR |  | FK → `freight_actual_costs.id`, duy nhất |
| `reversed_by_cost_id` | VARCHAR |  | FK → `freight_actual_costs.id`, duy nhất |
| `reversal_reason` | TEXT |  |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `submitted_at` | DATETIME |  |  |
| `approved_at` | DATETIME |  |  |
| `reversed_at` | DATETIME |  |  |
| `created_by` | VARCHAR | có |  |
| `updated_by` | VARCHAR | có |  |
| `submitted_by` | VARCHAR |  |  |
| `approved_by` | VARCHAR |  |  |
| `reversed_by` | VARCHAR |  |  |

Ràng buộc: `planned_distance_km >= 0 AND actual_distance_km >= 0`; `reversal_of_cost_id IS NULL OR (status = 'reversed' AND is_active = false AND length(trim(reversal_reason)) > 0 AND subt`; `(status = 'reversed' AND is_active = false) OR (status <> 'reversed' AND is_active = true)`; `status <> 'reversed' OR reversal_of_cost_id IS NOT NULL OR reversed_by_cost_id IS NOT NULL`; `status IN ('draft','submitted','approved','reversed')`; `reversal_of_cost_id IS NULL OR reversal_of_cost_id <> id`; `version > 0`

### `freight_charge_items` — Chi phí

Dòng chi phí: khoản mục, Acc code, kế hoạch, thực tế, phần vượt. Không thuế (thuế do hệ công nợ tính).

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `cost_id` | VARCHAR | có | FK → `freight_actual_costs.id` |
| `charge_type` | VARCHAR(32) | có |  |
| `cost_index` | VARCHAR(32) |  |  |
| `description` | VARCHAR(500) |  |  |
| `original_amount` | NUMERIC(24, 6) | có |  |
| `actual_amount` | NUMERIC(24, 6) | có |  |
| `increase_amount` | NUMERIC(24, 6) | có |  |
| `note` | TEXT |  |  |
| `quantity` | NUMERIC(18, 4) | có |  |
| `unit_price` | NUMERIC(24, 6) | có |  |
| `tax_code` | VARCHAR(50) | có |  |
| `tax_rate_snapshot` | NUMERIC(18, 8) | có |  |
| `tax_mode` | VARCHAR(20) | có |  |
| `net_amount` | NUMERIC(24, 6) | có |  |
| `tax_amount` | NUMERIC(24, 6) | có |  |
| `total_amount` | NUMERIC(24, 6) | có |  |
| `rounding_adjustment` | NUMERIC(24, 6) | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |
| `updated_by` | VARCHAR | có |  |

Ràng buộc: `quantity >= 0`; `charge_type = 'discount' OR unit_price >= 0`; `charge_type IN ('fuel','toll','driver','yard','waiting','loading','unloading','carrier_base','surcharge','discount','oth`

### `freight_cost_documents` — Chi phí

Chứng từ của bảng chi phí (URL, checksum, số hoá đơn nhà cung cấp).

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `cost_id` | VARCHAR | có | FK → `freight_actual_costs.id` |
| `document_type` | VARCHAR(64) | có |  |
| `storage_url` | TEXT | có |  |
| `file_name` | VARCHAR(255) |  |  |
| `mime_type` | VARCHAR(128) |  |  |
| `checksum` | VARCHAR(128) | có |  |
| `vendor_invoice_no` | VARCHAR(128) |  |  |
| `document_date` | DATE |  |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |
| `updated_by` | VARCHAR | có |  |

### `freight_order_legacy_links` — Vận hành

Nối Freight Order ↔ DO.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `freight_order_id` | VARCHAR | có | PK, FK → `freight_orders.id` |
| `delivery_order_id` | VARCHAR | có | FK → `delivery_orders.id`, duy nhất |

### `freight_order_units` — TMS gốc

Freight Order ↔ đơn vị hàng.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `freight_order_id` | VARCHAR | có | PK, FK → `freight_orders.id` |
| `freight_unit_id` | VARCHAR | có | PK, FK → `freight_units.id`, duy nhất |

### `freight_orders` — Vận hành

Đơn vận chuyển nội bộ sinh cùng chuyến (điểm lấy/giao, khung giờ, tổng tải).

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `pickup_location_id` | VARCHAR | có | FK → `locations.id` |
| `delivery_location_id` | VARCHAR | có | FK → `locations.id` |
| `pickup_window_start` | DATETIME | có |  |
| `pickup_window_end` | DATETIME | có |  |
| `delivery_window_start` | DATETIME | có |  |
| `delivery_window_end` | DATETIME | có |  |
| `total_weight_kg` | FLOAT | có |  |
| `total_volume_m3` | FLOAT | có |  |
| `total_pallet_count` | INTEGER | có |  |
| `max_weight_kg` | FLOAT | có |  |
| `max_volume_m3` | FLOAT | có |  |
| `max_pallet_count` | INTEGER | có |  |
| `status` | VARCHAR | có |  |
| `version` | INTEGER | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |
| `updated_by` | VARCHAR | có |  |

### `freight_units` — TMS gốc

Đơn vị hàng tách từ nhu cầu.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `demand_id` | VARCHAR | có | FK → `transport_demands.id`, duy nhất |
| `pickup_location_id` | VARCHAR | có | FK → `locations.id` |
| `delivery_location_id` | VARCHAR | có | FK → `locations.id` |
| `pickup_window_start` | DATETIME | có |  |
| `pickup_window_end` | DATETIME | có |  |
| `delivery_window_start` | DATETIME | có |  |
| `delivery_window_end` | DATETIME | có |  |
| `weight_kg` | FLOAT | có |  |
| `volume_m3` | FLOAT | có |  |
| `pallet_count` | INTEGER | có |  |
| `status` | VARCHAR | có |  |
| `version` | INTEGER | có |  |
| `created_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |

### `idempotency_records` — Hệ thống

Cache trả lời theo `Idempotency-Key` để lệnh gọi lặp không tạo hai lần.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `actor` | VARCHAR(128) | có |  |
| `method` | VARCHAR(16) | có |  |
| `path` | VARCHAR(500) | có |  |
| `idempotency_key` | VARCHAR(128) | có |  |
| `operation` | VARCHAR | có |  |
| `request_hash` | VARCHAR | có |  |
| `response_json` | TEXT | có |  |
| `created_at` | DATETIME | có |  |

### `incidents` — Vận hành

Sự cố trên đường theo DO/xe.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `do_id` | VARCHAR |  |  |
| `vehicle_id` | VARCHAR |  |  |
| `incident_type` | VARCHAR |  |  |
| `severity` | VARCHAR |  |  |
| `location` | VARCHAR |  |  |
| `description` | TEXT |  |  |
| `reporter` | VARCHAR |  |  |
| `reported_at` | VARCHAR |  |  |
| `status` | VARCHAR |  |  |

### `locations` — Dữ liệu gốc

Địa điểm: bãi/chi nhánh, kho, cảng; toạ độ để vẽ tuyến và tính ETA.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `name` | VARCHAR | có |  |
| `type` | VARCHAR |  |  |
| `address` | VARCHAR |  |  |
| `capacity` | FLOAT |  |  |
| `latitude` | FLOAT |  |  |
| `longitude` | FLOAT |  |  |

### `migration_quarantine` — Hệ thống

Bản ghi bị cách ly khi nâng cấp không chuyển được.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `migration_version` | VARCHAR | có |  |
| `entity_type` | VARCHAR | có |  |
| `entity_id` | VARCHAR | có |  |
| `reason` | VARCHAR | có |  |
| `payload_json` | TEXT | có |  |
| `quarantined_at` | DATETIME | có |  |

### `parking_events` — Bãi xe

Lịch sử quét QR / đổi trạng thái của phiếu.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `parking_list_id` | VARCHAR(128) | có | FK → `parking_lists.id` |
| `event_type` | VARCHAR(32) | có |  |
| `occurred_at` | DATETIME | có |  |
| `actor` | VARCHAR(128) | có |  |
| `note` | TEXT |  |  |

### `parking_labels` — Bãi xe

Nhãn từng kiện với mã QR.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(128) | có | PK |
| `parking_list_id` | VARCHAR(128) | có | FK → `parking_lists.id` |
| `package_no` | INTEGER | có |  |
| `package_total` | INTEGER | có |  |
| `qr_token` | VARCHAR(128) | có |  |
| `status` | VARCHAR(20) | có |  |
| `printed_at` | DATETIME |  |  |
| `reprint_count` | INTEGER | có |  |

### `parking_list_items` — Bãi xe

Dòng hàng của phiếu (từ dòng hàng hoá báo giá).

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `parking_list_id` | VARCHAR(128) | có | FK → `parking_lists.id` |
| `source_detail_id` | INTEGER |  |  |
| `barcode` | VARCHAR(128) |  |  |
| `item_id_laos` | VARCHAR(128) |  |  |
| `item_id_thai` | VARCHAR(128) |  |  |
| `sku` | VARCHAR(128) |  |  |
| `description` | VARCHAR(500) |  |  |
| `case_qty` | INTEGER | có |  |
| `piece_qty` | INTEGER | có |  |
| `uom` | VARCHAR(32) |  |  |
| `weight_kg` | FLOAT | có |  |
| `cube_m3` | FLOAT | có |  |
| `note` | TEXT |  |  |

### `parking_lists` — Bãi xe

Phiếu bãi xe / packing list của một DO: kiện, khối lượng, khối, trạng thái. Trạng thái: draft, ready, parked, gate_in, loaded, dispatched, delivered, cancelled.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(128) | có | PK |
| `do_id` | VARCHAR | có | FK → `delivery_orders.id` |
| `trip_id` | VARCHAR(128) |  | FK → `transport_trips.id` |
| `version` | INTEGER | có |  |
| `customer_id` | VARCHAR |  | FK → `customers.id` |
| `store_id` | VARCHAR(128) |  |  |
| `store_name` | VARCHAR(255) |  |  |
| `route_code` | VARCHAR(128) |  |  |
| `route_name` | VARCHAR(500) |  |  |
| `wave` | VARCHAR(64) |  |  |
| `gate` | VARCHAR(64) |  |  |
| `box_count` | INTEGER | có |  |
| `total_pieces` | INTEGER | có |  |
| `total_weight_kg` | FLOAT | có |  |
| `total_cube_m3` | FLOAT | có |  |
| `status` | VARCHAR(20) | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR(128) | có |  |
| `updated_by` | VARCHAR(128) | có |  |

Ràng buộc: `status IN ('draft','ready','parked','gate_in','loaded','dispatched','delivered','cancelled')`

### `quotation_attachments` — Kinh doanh

Chứng từ đính kèm báo giá.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `quotation_id` | VARCHAR | có | FK → `quotations.id` |
| `doc_type` | VARCHAR | có |  |
| `file_name` | VARCHAR | có |  |
| `storage_url` | TEXT | có |  |
| `mime_type` | VARCHAR |  |  |
| `size_bytes` | INTEGER |  |  |
| `note` | VARCHAR |  |  |
| `uploaded_at` | DATETIME | có |  |
| `uploaded_by` | VARCHAR | có |  |

### `quotation_items` — Kinh doanh

Dòng hàng hoá của báo giá (tên, số lượng, ĐVT). Tổng số lượng = số DO sinh khi khách chấp nhận.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `quotation_id` | VARCHAR | có | FK → `quotations.id` |
| `line_no` | INTEGER | có |  |
| `name` | VARCHAR |  |  |
| `quantity` | NUMERIC(24, 6) | có |  |
| `uom` | VARCHAR | có |  |
| `note` | VARCHAR |  |  |
| `created_at` | DATETIME | có |  |

Ràng buộc: `quantity >= 0`

### `quotation_versions` — Kinh doanh

Phiên bản giá mỗi lần gửi khách (giá, đơn vị, tiền tệ, tỷ giá).

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `quotation_id` | VARCHAR | có | FK → `quotations.id` |
| `version` | INTEGER | có |  |
| `selling_price` | NUMERIC(24, 6) |  |  |
| `unit_price` | NUMERIC(24, 6) |  |  |
| `price_basis` | VARCHAR |  |  |
| `total_cost` | NUMERIC(24, 6) |  |  |
| `currency_code` | VARCHAR |  |  |
| `fx_rate` | FLOAT |  |  |
| `note` | TEXT |  |  |
| `created_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |

### `quotations` — Kinh doanh

BÁO GIÁ — thoả thuận với khách: tuyến, loại xe, tải trọng, khung giờ, đơn vị cước + đơn giá (giá CUỐI), tổng giá thành, biên mục tiêu, giá đối thủ, chiết khấu, hiệu lực, ba ô ghi chú, trạng thái. Trạng thái: draft, pending_approval, sent, approved, accepted, split, rejected, expired.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `canonical_status` | VARCHAR | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |
| `updated_by` | VARCHAR | có |  |
| `version` | INTEGER | có |  |
| `customer_id` | VARCHAR |  | FK → `customers.id` |
| `route_id` | VARCHAR |  | FK → `routes.id` |
| `origin` | VARCHAR |  |  |
| `destination` | VARCHAR |  |  |
| `pickup_window_start` | VARCHAR |  |  |
| `pickup_window_end` | VARCHAR |  |  |
| `delivery_window_start` | VARCHAR |  |  |
| `delivery_window_end` | VARCHAR |  |  |
| `weight_kg` | FLOAT |  |  |
| `pallet_count` | INTEGER |  |  |
| `cargo_type` | VARCHAR |  |  |
| `valid_to` | VARCHAR |  |  |
| `fuel_cost` | NUMERIC(24, 6) |  |  |
| `driver_cost` | NUMERIC(24, 6) |  |  |
| `toll_fee` | NUMERIC(24, 6) |  |  |
| `total_cost` | NUMERIC(24, 6) |  |  |
| `selling_price` | NUMERIC(24, 6) |  |  |
| `packaging_spec` | VARCHAR |  |  |
| `carrier_name` | VARCHAR |  |  |
| `delivery_method` | VARCHAR |  |  |
| `seal_weight` | VARCHAR |  |  |
| `temperature_requirement` | VARCHAR |  |  |
| `cargo_insurance` | VARCHAR |  |  |
| `warehouse_owner` | VARCHAR |  |  |
| `volume_m3` | FLOAT |  |  |
| `notes` | TEXT |  |  |
| `status` | VARCHAR |  |  |
| `price_basis` | VARCHAR |  |  |
| `unit_price` | NUMERIC(24, 6) |  |  |
| `min_qty_per_trip` | FLOAT |  |  |
| `quote_no` | VARCHAR |  |  |
| `vehicle_type_id` | VARCHAR |  | FK → `vehicle_types.id` |
| `currency_code` | VARCHAR |  |  |
| `fx_rate` | FLOAT |  |  |
| `payment_terms` | VARCHAR |  |  |
| `sales_rep` | VARCHAR |  |  |
| `trips_per_month` | INTEGER |  |  |
| `waiting_surcharge` | NUMERIC(24, 6) |  |  |
| `cargo_value` | NUMERIC(24, 6) |  |  |
| `stacking` | VARCHAR |  |  |
| `sealing` | VARCHAR |  |  |
| `recipient_contact` | VARCHAR |  |  |
| `notes_customer` | TEXT |  |  |
| `notes_ops` | TEXT |  |  |
| `notes_internal` | TEXT |  |  |
| `bot_fee` | NUMERIC(24, 6) |  |  |
| `cost_breakdown_json` | TEXT |  |  |
| `target_margin` | FLOAT |  |  |
| `competitor_price` | NUMERIC(18, 2) |  |  |
| `discount_percent` | FLOAT |  |  |
| `sent_at` | DATETIME |  |  |
| `accepted_at` | DATETIME |  |  |
| `closed_at` | DATETIME |  |  |
| `close_reason` | TEXT |  |  |

Ràng buộc: `canonical_status IN ('draft','pending_approval','sent','approved','accepted','rejected','split','expired','cancelled','u`

### `resource_assignments` — Vận hành

Phân công xe/tổ lái cho chuyến trong một khung giờ — cơ sở để khoá lịch và phát hiện trùng.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `freight_order_id` | VARCHAR | có | FK → `freight_orders.id` |
| `trip_id` | VARCHAR(128) |  | FK → `transport_trips.id` |
| `leg_id` | VARCHAR(128) |  | FK → `transport_trip_legs.id` |
| `vehicle_id` | VARCHAR | có | FK → `vehicles.id` |
| `driver_id` | VARCHAR | có | FK → `drivers.id` |
| `co_driver_id` | VARCHAR |  | FK → `drivers.id` |
| `assignment_start` | DATETIME | có |  |
| `assignment_end` | DATETIME | có |  |
| `status` | VARCHAR | có |  |
| `created_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |

### `roles` — Phân quyền

Vai trò và danh sách quyền (JSON): `finance_read`, `finance_creator`, `finance_approver`… Đăng nhập do hệ thống cha lo.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `permissions` | TEXT |  |  |

### `routes` — Dữ liệu gốc

Tuyến đường: số km, các chặng (`segments_json`), hình đường bộ thật (`road_geometry_json`), phí BOT theo tuyến. Số km là đầu vào của công thức giá thành.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `name` | VARCHAR | có |  |
| `distance_km` | FLOAT |  |  |
| `segments_json` | TEXT |  |  |
| `road_geometry_json` | TEXT |  |  |
| `road_distance_km` | FLOAT |  |  |
| `bot_fee` | NUMERIC(24, 6) |  |  |

### `tender_offers` — TMS gốc

Chào giá của nhà vận chuyển.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `tender_id` | VARCHAR | có | FK → `tenders.id` |
| `carrier_id` | VARCHAR | có | FK → `carriers.id` |
| `amount` | NUMERIC(18, 2) | có |  |
| `currency_code` | VARCHAR | có |  |
| `note` | TEXT |  |  |
| `status` | VARCHAR | có |  |
| `submitted_at` | DATETIME | có |  |
| `submitted_by` | VARCHAR | có |  |

### `tenders` — TMS gốc

Đấu thầu thuê ngoài cho Freight Order.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `freight_order_id` | VARCHAR | có | FK → `freight_orders.id`, duy nhất |
| `response_deadline` | DATETIME | có |  |
| `status` | VARCHAR | có |  |
| `awarded_offer_id` | VARCHAR |  |  |
| `awarded_carrier_id` | VARCHAR |  | FK → `carriers.id` |
| `version` | INTEGER | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |
| `updated_by` | VARCHAR | có |  |

### `transport_demands` — TMS gốc

Nhu cầu vận chuyển (mô-đun TMS gốc, ngoài luồng Báo giá → DO).

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `customer_id` | VARCHAR | có | FK → `customers.id` |
| `pickup_location_id` | VARCHAR | có | FK → `locations.id` |
| `delivery_location_id` | VARCHAR | có | FK → `locations.id` |
| `pickup_window_start` | DATETIME | có |  |
| `pickup_window_end` | DATETIME | có |  |
| `delivery_window_start` | DATETIME | có |  |
| `delivery_window_end` | DATETIME | có |  |
| `weight_kg` | FLOAT | có |  |
| `volume_m3` | FLOAT | có |  |
| `pallet_count` | INTEGER | có |  |
| `service_requirements` | TEXT |  |  |
| `status` | VARCHAR | có |  |
| `version` | INTEGER | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |
| `updated_by` | VARCHAR | có |  |

### `transport_event_documents` — Vận hành

Chứng từ gắn vào mốc thực thi.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `event_id` | VARCHAR | có | FK → `transport_events.id` |
| `document_type` | VARCHAR | có |  |
| `storage_url` | TEXT | có |  |
| `file_name` | VARCHAR |  |  |
| `mime_type` | VARCHAR |  |  |
| `checksum` | VARCHAR | có |  |
| `uploaded_at` | DATETIME | có |  |
| `uploaded_by` | VARCHAR | có |  |

### `transport_events` — Vận hành

Mốc thực thi: check_in, pickup, departure, arrival, unloading, delivered, lệch tuyến… kèm GPS, ETA.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `freight_order_id` | VARCHAR | có | FK → `freight_orders.id` |
| `trip_id` | VARCHAR(128) |  | FK → `transport_trips.id` |
| `leg_id` | VARCHAR(128) |  | FK → `transport_trip_legs.id` |
| `event_type` | VARCHAR | có |  |
| `event_time` | DATETIME | có |  |
| `lat` | FLOAT |  |  |
| `lng` | FLOAT |  |  |
| `speed_kmh` | FLOAT |  |  |
| `distance_km` | FLOAT |  |  |
| `eta` | VARCHAR |  |  |
| `location_text` | VARCHAR |  |  |
| `source` | VARCHAR | có |  |
| `device_id` | VARCHAR |  |  |
| `reason` | TEXT |  |  |
| `note` | TEXT |  |  |
| `idempotency_key` | VARCHAR | có |  |
| `payload_hash` | VARCHAR | có |  |
| `recorded_at` | DATETIME | có |  |
| `recorded_by` | VARCHAR | có |  |

### `transport_trip_legs` — Vận hành

Chặng của chuyến: điểm đi/đến, km, tốc độ, dừng, người nhận, mốc.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(128) | có | PK |
| `trip_id` | VARCHAR(128) | có | FK → `trip_delivery_orders.trip_id`, FK → `transport_trips.id` |
| `do_id` | VARCHAR |  | FK → `trip_delivery_orders.do_id` |
| `sequence_no` | INTEGER | có |  |
| `leg_type` | VARCHAR(30) | có |  |
| `origin` | VARCHAR(500) | có |  |
| `destination` | VARCHAR(500) | có |  |
| `stop_name` | VARCHAR(500) |  |  |
| `receiver_name` | VARCHAR(255) |  |  |
| `receiver_phone` | VARCHAR(64) |  |  |
| `delivery_note` | TEXT |  |  |
| `distance_km` | NUMERIC(18, 3) | có |  |
| `avg_speed_kmh` | NUMERIC(18, 8) | có |  |
| `dwell_minutes` | INTEGER | có |  |
| `planned_departure_at` | DATETIME |  |  |
| `planned_arrival_at` | DATETIME |  |  |
| `actual_departure_at` | DATETIME |  |  |
| `actual_arrival_at` | DATETIME |  |  |
| `status` | VARCHAR(20) | có |  |
| `allocated_cost` | NUMERIC(24, 6) | có |  |
| `allocated_revenue` | NUMERIC(24, 6) | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |

Ràng buộc: `status IN ('planned','ready','in_transit','arrived','completed','cancelled')`; `leg_type IN ('outbound','pickup','delivery','empty_return','backhaul','warehouse_transfer')`; `distance_km >= 0 AND avg_speed_kmh > 0 AND dwell_minutes >= 0`; `sequence_no > 0`

### `transport_trips` — Vận hành

CHUYẾN XE — cách công ty thực hiện DO: loại chuyến, xe, tài xế, phụ xe, mốc kế hoạch và thực tế. Trạng thái: planned, ready, in_transit, arrived, completed, cancelled.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(128) | có | PK |
| `freight_order_id` | VARCHAR | có | FK → `freight_orders.id` |
| `trip_type` | VARCHAR(20) | có |  |
| `status` | VARCHAR(20) | có |  |
| `vehicle_id` | VARCHAR |  | FK → `vehicles.id` |
| `driver_id` | VARCHAR |  | FK → `drivers.id` |
| `co_driver_id` | VARCHAR |  | FK → `drivers.id` |
| `planned_departure_at` | DATETIME |  |  |
| `planned_arrival_at` | DATETIME |  |  |
| `planned_return_at` | DATETIME |  |  |
| `actual_departure_at` | DATETIME |  |  |
| `actual_arrival_at` | DATETIME |  |  |
| `actual_return_at` | DATETIME |  |  |
| `version` | INTEGER | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR(128) | có |  |
| `updated_by` | VARCHAR(128) | có |  |

Ràng buộc: `version > 0`; `status IN ('draft','planned','dispatched','in_transit','completed','settled','cancelled')`; `trip_type IN ('one_way','round_trip','backhaul','multi_stop')`

### `trip_delivery_orders` — Vận hành

Chuyến ↔ DO (một chuyến có thể chở nhiều DO).

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `trip_id` | VARCHAR(128) | có | PK, FK → `transport_trips.id` |
| `do_id` | VARCHAR | có | PK, FK → `delivery_orders.id` |
| `allocation_sequence` | INTEGER | có |  |
| `created_at` | DATETIME | có |  |
| `created_by` | VARCHAR(128) | có |  |

### `users` — Phân quyền

Người dùng → vai trò. Danh tính đến từ token của hệ thống cha.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `username` | VARCHAR | có |  |
| `role_id` | VARCHAR |  | FK → `roles.id` |

### `vehicle_cost_overrides` — Dữ liệu gốc

Đơn giá ghi đè của riêng một xe cho vài khoản mục (xe cũ tốn dầu hơn…). Công thức hai tầng: loại xe → xe.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `vehicle_id` | VARCHAR | có | FK → `vehicles.id` |
| `component` | VARCHAR | có |  |
| `value` | NUMERIC(24, 6) | có |  |
| `note` | VARCHAR |  |  |
| `updated_at` | DATETIME |  |  |
| `updated_by` | VARCHAR |  |  |

### `vehicle_maintenance_cost_lines` — Dữ liệu gốc

Dòng chi phí của phiếu bảo dưỡng.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | INTEGER | có | PK |
| `request_id` | VARCHAR(128) | có | FK → `vehicle_maintenance_requests.id` |
| `category` | VARCHAR(32) | có |  |
| `description` | VARCHAR(500) | có |  |
| `quantity` | NUMERIC(18, 4) | có |  |
| `unit` | VARCHAR(32) | có |  |
| `estimated_unit_cost` | NUMERIC(24, 6) | có |  |
| `estimated_total` | NUMERIC(24, 6) | có |  |
| `actual_unit_cost` | NUMERIC(24, 6) | có |  |
| `actual_total` | NUMERIC(24, 6) | có |  |

Ràng buộc: `quantity > 0`; `actual_unit_cost >= 0`; `estimated_unit_cost >= 0`

### `vehicle_maintenance_requests` — Dữ liệu gốc

Phiếu bảo dưỡng xe: kế hoạch, thực tế, xưởng, chi phí; xe trong lịch bảo dưỡng không điều phối được.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR(128) | có | PK |
| `request_no` | VARCHAR(128) | có |  |
| `vehicle_id` | VARCHAR | có | FK → `vehicles.id` |
| `category` | VARCHAR(32) | có |  |
| `priority` | VARCHAR(20) | có |  |
| `planned_start` | DATETIME | có |  |
| `planned_end` | DATETIME | có |  |
| `actual_start` | DATETIME |  |  |
| `actual_end` | DATETIME |  |  |
| `description` | TEXT | có |  |
| `cause` | TEXT |  |  |
| `odometer_km` | FLOAT |  |  |
| `workshop` | VARCHAR(255) |  |  |
| `currency_code` | VARCHAR(3) | có |  |
| `estimated_total` | NUMERIC(24, 6) | có |  |
| `actual_total` | NUMERIC(24, 6) | có |  |
| `next_maintenance_date` | VARCHAR(10) |  |  |
| `status` | VARCHAR(20) | có |  |
| `cancellation_reason` | TEXT |  |  |
| `version` | INTEGER | có |  |
| `created_at` | DATETIME | có |  |
| `updated_at` | DATETIME | có |  |
| `created_by` | VARCHAR(128) | có |  |
| `updated_by` | VARCHAR(128) | có |  |
| `approved_at` | DATETIME |  |  |
| `approved_by` | VARCHAR(128) |  |  |
| `completed_at` | DATETIME |  |  |
| `completed_by` | VARCHAR(128) |  |  |

Ràng buộc: `status IN ('requested','approved','in_progress','completed','cancelled')`; `planned_end > planned_start`

### `vehicle_tracking` — Vận hành

Vị trí GPS mới nhất theo DO/xe, km còn lại, ETA.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `do_id` | VARCHAR | có | PK, FK → `delivery_orders.id` |
| `vehicle_id` | VARCHAR |  | FK → `vehicles.id` |
| `lat` | FLOAT |  |  |
| `lng` | FLOAT |  |  |
| `speed_kmh` | FLOAT |  |  |
| `remaining_distance_km` | FLOAT |  |  |
| `eta` | VARCHAR |  |  |
| `planned_return_at` | VARCHAR |  |  |
| `last_update` | DATETIME |  |  |

### `vehicle_types` — Dữ liệu gốc

Loại xe: tải trọng, thể tích, pallet, định mức dầu, tốc độ, khấu hao/km. Báo giá chốt theo LOẠI xe.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `name` | VARCHAR | có |  |
| `icon` | VARCHAR |  |  |
| `max_weight` | FLOAT |  |  |
| `volume_capacity_m3` | FLOAT |  |  |
| `pallet_capacity` | INTEGER |  |  |
| `fuel_norm` | FLOAT |  |  |
| `avg_speed_kmh` | FLOAT |  |  |
| `base_rate` | NUMERIC(24, 6) |  |  |
| `maint_cost` | NUMERIC(24, 6) |  |  |
| `dep_cost_per_km` | NUMERIC(24, 6) |  |  |
| `dims` | VARCHAR |  |  |
| `fuel_type` | VARCHAR |  |  |
| `special` | VARCHAR |  |  |
| `notes` | VARCHAR |  |  |

### `vehicles` — Dữ liệu gốc

Từng chiếc xe: biển số, loại (MÃ loại xe), năng lực, ba hạn pháp lý (đăng kiểm, bảo hiểm, bảo dưỡng), bãi, trạng thái vận hành. Điều phối chỉ nhận xe 'Sẵn sàng' và còn hạn pháp lý.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `brand` | VARCHAR |  |  |
| `type` | VARCHAR |  |  |
| `weight_capacity` | FLOAT |  |  |
| `volume_capacity_m3` | FLOAT |  |  |
| `pallet_capacity` | INTEGER |  |  |
| `fuel_norm` | FLOAT |  |  |
| `min_speed_kmh` | FLOAT |  |  |
| `avg_speed_kmh` | FLOAT |  |  |
| `max_speed_kmh` | FLOAT |  |  |
| `maintenance_date` | VARCHAR |  |  |
| `status` | VARCHAR |  |  |
| `operational_status` | VARCHAR(32) | có |  |
| `operational_ref` | VARCHAR(128) |  |  |
| `operational_note` | TEXT |  |  |
| `operational_updated_at` | DATETIME |  |  |
| `engine_no` | VARCHAR |  |  |
| `chassis_no` | VARCHAR |  |  |
| `insurance_date` | VARCHAR |  |  |
| `inspection_date` | VARCHAR |  |  |
| `inspection_place` | VARCHAR |  |  |
| `depot` | VARCHAR |  |  |
| `depot_code` | VARCHAR |  |  |
| `inspection_exp` | VARCHAR |  |  |
| `odometer_km` | FLOAT |  |  |
| `next_service_odometer_km` | FLOAT |  |  |
| `engine_cap` | VARCHAR |  |  |
| `dimensions` | VARCHAR |  |  |
| `image_url` | TEXT |  |  |

### `warehouse_appointments` — TMS gốc

Lịch hẹn lấy/giao tại kho.

| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |
|---|---|---|---|
| `id` | VARCHAR | có | PK |
| `freight_order_id` | VARCHAR | có | FK → `freight_orders.id` |
| `appointment_type` | VARCHAR | có |  |
| `location_id` | VARCHAR | có | FK → `locations.id` |
| `scheduled_start` | DATETIME | có |  |
| `scheduled_end` | DATETIME | có |  |
| `status` | VARCHAR | có |  |
| `version` | INTEGER | có |  |
| `created_at` | DATETIME | có |  |
| `created_by` | VARCHAR | có |  |

