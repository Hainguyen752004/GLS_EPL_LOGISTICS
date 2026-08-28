# Tài liệu cơ sở dữ liệu EPL Logistics

> Tài liệu này được sinh từ SQLAlchemy metadata của ứng dụng. Hệ thống production sử dụng PostgreSQL qua `DATABASE_URL`.

Tổng số bảng: **71**.

## Quy ước

- `PK`: khóa chính.
- `FK`: khóa ngoại theo định dạng `bảng.cột`.
- `Bắt buộc`: cột không chấp nhận NULL.
- Dữ liệu thực tế phải được thay đổi qua service/API, không sửa trực tiếp trong PostgreSQL nếu không có quy trình migration.

## Danh sách bảng

- [`account_mappings`](#account-mappings) - Anh xa nghiep vu sang tai khoan ke toan.
- [`accounting_periods`](#accounting-periods) - Ky ke toan va trang thai mo/khoa so.
- [`ap_invoice_lines`](#ap-invoice-lines) - Chi tiet hang muc tren hoa don phai tra.
- [`ap_invoices`](#ap-invoices) - Hoa don phai tra cho nha cung cap/carrier.
- [`ar_invoices`](#ar-invoices) - Hoa don phai thu sinh tu DO da giao.
- [`audit_logs`](#audit-logs) - Nhat ky thao tac phuc vu truy vet.
- [`carriers`](#carriers) - Danh muc nha van chuyen thue ngoai.
- [`chart_of_accounts`](#chart-of-accounts) - He thong tai khoan ke toan.
- [`cost_formulas`](#cost-formulas) - Cong thuc va cau thanh chi phi theo loai xe/tien te.
- [`currencies`](#currencies) - Danh muc tien te cua luong du lieu goc.
- [`currency_definitions`](#currency-definitions) - Danh muc tien te va ty gia van hanh hien tai.
- [`currency_rate_history`](#currency-rate-history) - Lich su thay doi ty gia de doi chieu va audit.
- [`customers`](#customers) - Ho so khach hang va thong tin lien he.
- [`delivery_order_charge_adjustments`](#delivery-order-charge-adjustments) - Cac khoan tang/giam gia khi chot DO.
- [`delivery_order_closeouts`](#delivery-order-closeouts) - Ket qua chot gia cuoi sau khi giao hang.
- [`delivery_order_details`](#delivery-order-details) - Danh sach hang hoa cua tung lenh giao hang.
- [`delivery_orders`](#delivery-orders) - Lenh giao hang va cua so lay/giao hang.
- [`delivery_pod_documents`](#delivery-pod-documents) - Tep anh/PDF POD cua tung diem giao.
- [`delivery_pod_records`](#delivery-pod-records) - Thong tin giao nhan va chu ky theo diem giao.
- [`driver_qualifications`](#driver-qualifications) - Bang cap/chung chi va dieu kien cua tai xe.
- [`driver_shift_assignments`](#driver-shift-assignments) - Ca lam viec, lich nghi va chuyen da khoa cua nhan su.
- [`drivers`](#drivers) - Ho so tai xe, phu xe, bang lai va trang thai nguon luc.
- [`epl_expense_vouchers`](#epl-expense-vouchers) - Phieu chi phi EPL lien ket Trip va Actual Cost.
- [`finance_control_config`](#finance-control-config) - Cau hinh kiem soat nghiep vu tai chinh.
- [`freight_actual_costs`](#freight-actual-costs) - Chi phi van hanh thuc te cua Freight Order/Trip.
- [`freight_charge_items`](#freight-charge-items) - Dong chi phi chi tiet cua ho so chi phi thuc te.
- [`freight_cost_documents`](#freight-cost-documents) - Chung tu dinh kem cho chi phi van tai.
- [`freight_order_legacy_links`](#freight-order-legacy-links) - Lien ket Freight Order voi ma ho so he thong cu.
- [`freight_order_units`](#freight-order-units) - Lien ket Freight Order voi cac don vi hang.
- [`freight_orders`](#freight-orders) - Lenh van tai chuan dung cho lap ke hoach va tai chinh.
- [`freight_settlements`](#freight-settlements) - Ho so doi soat cac khoan phai tra.
- [`freight_units`](#freight-units) - Don vi hang van tai duoc gom tu nhu cau.
- [`gl_transactions`](#gl-transactions) - But toan so cai phat sinh tu hoa don va nghiep vu tai chinh.
- [`idempotency_records`](#idempotency-records) - Khoa chong tao trung khi goi lai API.
- [`incidents`](#incidents) - Su co phat sinh trong qua trinh van chuyen.
- [`items`](#items) - Danh muc hang hoa.
- [`journal_batches`](#journal-batches) - Lo but toan de kiem soat ghi so.
- [`journal_lines`](#journal-lines) - Dong no/co cua tung lo but toan.
- [`locations`](#locations) - Danh muc kho, bai, cong va diem giao/nhan.
- [`migration_quarantine`](#migration-quarantine) - Du lieu khong hop le duoc cach ly khi migration.
- [`parking_events`](#parking-events) - Lich su quet QR va chuyen trang thai Parking List.
- [`parking_labels`](#parking-labels) - Tem QR duy nhat cho tung kien hang.
- [`parking_list_items`](#parking-list-items) - Dong hang hoa duoc phan bo vao Parking List.
- [`parking_lists`](#parking-lists) - Ho so gom kien hang sinh tu DO/SO de quan ly vao bai va boc hang.
- [`pod`](#pod) - Ban ghi POD tuong thich voi luong cu.
- [`price_lists`](#price-lists) - Bang gia dich vu theo doi tuong ap dung.
- [`quotation_details`](#quotation-details) - Hang muc va so lieu chi tiet cua bao gia.
- [`quotations`](#quotations) - Phan dau bao gia van tai cho khach hang.
- [`resource_assignments`](#resource-assignments) - Phan cong xe, tai xe va nguon luc cho lenh van tai.
- [`roles`](#roles) - Danh muc vai tro phan quyen.
- [`routes`](#routes) - Tuyen van tai nguon dung de tao bao gia va Trip.
- [`sales_orders`](#sales-orders) - Don ban hang duoc tao tu bao gia da duyet.
- [`settlement_payments`](#settlement-payments) - Cac lan thanh toan cua mot ho so doi soat.
- [`shipment_costs`](#shipment-costs) - Chi phi chuyen hang cua luong nghiep vu cu.
- [`tax_codes`](#tax-codes) - Danh muc ma thue dung cho hoa don va but toan.
- [`tender_offers`](#tender-offers) - Bao gia cua carrier trong mot dot thau.
- [`tenders`](#tenders) - Dot moi thau van tai.
- [`transport_demands`](#transport-demands) - Nhu cau van tai dau vao truoc khi tao Freight Unit/Order.
- [`transport_event_documents`](#transport-event-documents) - Chung tu dinh kem theo su kien van tai.
- [`transport_events`](#transport-events) - Su kien tracking, check-in, pickup, arrival va POD.
- [`transport_trip_legs`](#transport-trip-legs) - Cac chang giao, backhaul hoac chay rong cua Trip.
- [`transport_trips`](#transport-trips) - Chuyen van tai thuc te lien ket DO/FO va ke hoach quay dau.
- [`trip_delivery_orders`](#trip-delivery-orders) - Bang lien ket nhieu-nhieu giua Trip va DO.
- [`uoms`](#uoms) - Danh muc don vi tinh.
- [`users`](#users) - Tai khoan nguoi dung he thong.
- [`vehicle_maintenance_cost_lines`](#vehicle-maintenance-cost-lines) - Chi tiet chi phi cua tung phieu sua chua/bao duong.
- [`vehicle_maintenance_requests`](#vehicle-maintenance-requests) - Phieu yeu cau sua chua, thay the va bao duong xe.
- [`vehicle_tracking`](#vehicle-tracking) - Du lieu vi tri/toc do GPS cua xe.
- [`vehicle_types`](#vehicle-types) - Danh muc loai xe va gioi han tai trong, pallet, the tich.
- [`vehicles`](#vehicles) - Ho so tung xe, thong so ky thuat va trang thai van hanh.
- [`warehouse_appointments`](#warehouse-appointments) - Lich hen kho cho lay/giao hang.

## `account_mappings`

Anh xa nghiep vu sang tai khoan ke toan.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `mapping_key` | `VARCHAR` | PK; Bắt buộc | `-` | Trường mapping key của bảng `account_mappings`. |
| `account_code` | `VARCHAR` | Bắt buộc | `-` | Trường account code của bảng `account_mappings`. |
| `effective_from` | `DATETIME` | - | `-` | Trường effective from của bảng `account_mappings`. |
| `effective_to` | `DATETIME` | - | `-` | Trường effective to của bảng `account_mappings`. |

## `accounting_periods`

Ky ke toan va trang thai mo/khoa so.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `accounting_periods`. |
| `starts_at` | `DATETIME` | Bắt buộc | `-` | Trường starts at của bảng `accounting_periods`. |
| `ends_at` | `DATETIME` | Bắt buộc | `-` | Trường ends at của bảng `accounting_periods`. |
| `status` | `VARCHAR` | Bắt buộc | `-` | Trường status của bảng `accounting_periods`. |
| `closed_at` | `DATETIME` | - | `-` | Trường closed at của bảng `accounting_periods`. |
| `closed_by` | `VARCHAR` | - | `-` | Trường closed by của bảng `accounting_periods`. |

## `ap_invoice_lines`

Chi tiet hang muc tren hoa don phai tra.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `ap_invoice_lines`. |
| `ap_invoice_id` | `VARCHAR` | Bắt buộc; FK -> `ap_invoices.id` | `-` | Trường ap invoice id của bảng `ap_invoice_lines`. |
| `charge_item_id` | `VARCHAR` | Bắt buộc; FK -> `freight_charge_items.id` | `-` | Trường charge item id của bảng `ap_invoice_lines`. |
| `charge_type` | `VARCHAR(32)` | Bắt buộc | `-` | Trường charge type của bảng `ap_invoice_lines`. |
| `description` | `VARCHAR(500)` | - | `-` | Trường description của bảng `ap_invoice_lines`. |
| `quantity` | `NUMERIC(18, 4)` | Bắt buộc | `-` | Trường quantity của bảng `ap_invoice_lines`. |
| `unit_price` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường unit price của bảng `ap_invoice_lines`. |
| `currency_code` | `VARCHAR(3)` | Bắt buộc | `-` | Trường currency code của bảng `ap_invoice_lines`. |
| `tax_code` | `VARCHAR(50)` | Bắt buộc | `-` | Trường tax code của bảng `ap_invoice_lines`. |
| `tax_rate_snapshot` | `NUMERIC(18, 8)` | Bắt buộc | `-` | Trường tax rate snapshot của bảng `ap_invoice_lines`. |
| `tax_mode` | `VARCHAR(20)` | Bắt buộc | `-` | Trường tax mode của bảng `ap_invoice_lines`. |
| `account_mapping_key` | `VARCHAR(128)` | Bắt buộc | `-` | Trường account mapping key của bảng `ap_invoice_lines`. |
| `account_code_snapshot` | `VARCHAR` | - | `-` | Trường account code snapshot của bảng `ap_invoice_lines`. |
| `net_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường net amount của bảng `ap_invoice_lines`. |
| `tax_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường tax amount của bảng `ap_invoice_lines`. |
| `total_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường total amount của bảng `ap_invoice_lines`. |
| `rounding_adjustment` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường rounding adjustment của bảng `ap_invoice_lines`. |

## `ap_invoices`

Hoa don phai tra cho nha cung cap/carrier.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `ap_invoices`. |
| `cost_id` | `VARCHAR` | Bắt buộc; FK -> `freight_actual_costs.id` | `-` | Trường cost id của bảng `ap_invoices`. |
| `carrier_id` | `VARCHAR` | Bắt buộc; FK -> `carriers.id` | `-` | Trường carrier id của bảng `ap_invoices`. |
| `carrier_name_snapshot` | `VARCHAR` | Bắt buộc | `-` | Trường carrier name snapshot của bảng `ap_invoices`. |
| `carrier_tax_code_snapshot` | `VARCHAR` | - | `-` | Trường carrier tax code snapshot của bảng `ap_invoices`. |
| `vendor_invoice_no` | `VARCHAR(128)` | Bắt buộc | `-` | Trường vendor invoice no của bảng `ap_invoices`. |
| `normalized_vendor_invoice_no` | `VARCHAR(128)` | Bắt buộc | `-` | Trường normalized vendor invoice no của bảng `ap_invoices`. |
| `document_kind` | `VARCHAR(20)` | Bắt buộc | `invoice` | Trường document kind của bảng `ap_invoices`. |
| `invoice_date` | `DATE` | Bắt buộc | `-` | Trường invoice date của bảng `ap_invoices`. |
| `due_date` | `DATE` | - | `-` | Trường due date của bảng `ap_invoices`. |
| `currency_code` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `-` | Trường currency code của bảng `ap_invoices`. |
| `functional_currency` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `-` | Trường functional currency của bảng `ap_invoices`. |
| `exchange_rate_snapshot` | `NUMERIC(18, 8)` | Bắt buộc | `-` | Trường exchange rate snapshot của bảng `ap_invoices`. |
| `exchange_rate_date` | `DATE` | Bắt buộc | `-` | Trường exchange rate date của bảng `ap_invoices`. |
| `exchange_rate_source` | `VARCHAR(100)` | Bắt buộc | `-` | Trường exchange rate source của bảng `ap_invoices`. |
| `subtotal_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường subtotal amount của bảng `ap_invoices`. |
| `tax_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường tax amount của bảng `ap_invoices`. |
| `total_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường total amount của bảng `ap_invoices`. |
| `functional_subtotal_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường functional subtotal amount của bảng `ap_invoices`. |
| `functional_tax_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường functional tax amount của bảng `ap_invoices`. |
| `functional_total_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường functional total amount của bảng `ap_invoices`. |
| `status` | `VARCHAR(20)` | Bắt buộc | `draft` | Trường status của bảng `ap_invoices`. |
| `is_active` | `BOOLEAN` | Bắt buộc | `True` | Trường is active của bảng `ap_invoices`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `ap_invoices`. |
| `reversal_of_ap_id` | `VARCHAR` | Unique; FK -> `ap_invoices.id` | `-` | Trường reversal of ap id của bảng `ap_invoices`. |
| `reversed_by_ap_id` | `VARCHAR` | Unique; FK -> `ap_invoices.id` | `-` | Trường reversed by ap id của bảng `ap_invoices`. |
| `reversal_reason` | `TEXT` | - | `-` | Trường reversal reason của bảng `ap_invoices`. |
| `posting_reference` | `VARCHAR` | - | `-` | Trường posting reference của bảng `ap_invoices`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E9630153A0>` | Trường created at của bảng `ap_invoices`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E963015440>` | Trường updated at của bảng `ap_invoices`. |
| `submitted_at` | `DATETIME` | - | `-` | Trường submitted at của bảng `ap_invoices`. |
| `approved_at` | `DATETIME` | - | `-` | Trường approved at của bảng `ap_invoices`. |
| `posted_at` | `DATETIME` | - | `-` | Trường posted at của bảng `ap_invoices`. |
| `reversed_at` | `DATETIME` | - | `-` | Trường reversed at của bảng `ap_invoices`. |
| `created_by` | `VARCHAR` | Bắt buộc | `-` | Trường created by của bảng `ap_invoices`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `-` | Trường updated by của bảng `ap_invoices`. |
| `submitted_by` | `VARCHAR` | - | `-` | Trường submitted by của bảng `ap_invoices`. |
| `approved_by` | `VARCHAR` | - | `-` | Trường approved by của bảng `ap_invoices`. |
| `posted_by` | `VARCHAR` | - | `-` | Trường posted by của bảng `ap_invoices`. |
| `reversed_by` | `VARCHAR` | - | `-` | Trường reversed by của bảng `ap_invoices`. |

Chỉ mục: `uq_active_ap_cost`.

## `ar_invoices`

Hoa don phai thu sinh tu DO da giao.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `ar_invoices`. |
| `canonical_status` | `VARCHAR` | Bắt buộc | `posted` | Trường canonical status của bảng `ar_invoices`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962DE1760>` | Trường created at của bảng `ar_invoices`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962DE1800>` | Trường updated at của bảng `ar_invoices`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `ar_invoices`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `system` | Trường updated by của bảng `ar_invoices`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `ar_invoices`. |
| `is_active` | `BOOLEAN` | Bắt buộc | `True` | Trường is active của bảng `ar_invoices`. |
| `reversal_of_invoice_id` | `VARCHAR` | FK -> `ar_invoices.id` | `-` | Trường reversal of invoice id của bảng `ar_invoices`. |
| `currency_code` | `VARCHAR` | Bắt buộc | `VND` | Trường currency code của bảng `ar_invoices`. |
| `exchange_rate_snapshot` | `NUMERIC` | Bắt buộc | `1` | Trường exchange rate snapshot của bảng `ar_invoices`. |
| `tax_rate_snapshot` | `NUMERIC` | - | `-` | Trường tax rate snapshot của bảng `ar_invoices`. |
| `do_id` | `VARCHAR` | FK -> `delivery_orders.id` | `-` | Trường do id của bảng `ar_invoices`. |
| `customer_id` | `VARCHAR` | FK -> `customers.id` | `-` | Trường customer id của bảng `ar_invoices`. |
| `invoice_date` | `VARCHAR` | - | `-` | Trường invoice date của bảng `ar_invoices`. |
| `amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường amount của bảng `ar_invoices`. |
| `vat_pct` | `NUMERIC(18, 8)` | Bắt buộc | `10` | Trường vat pct của bảng `ar_invoices`. |
| `vat_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường vat amount của bảng `ar_invoices`. |
| `total` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường total của bảng `ar_invoices`. |
| `status` | `VARCHAR` | - | `Posted` | Trường status của bảng `ar_invoices`. |

Chỉ mục: `uq_active_invoice_do`.

## `audit_logs`

Nhat ky thao tac phuc vu truy vet.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `audit_logs`. |
| `user_id` | `VARCHAR` | - | `-` | Trường user id của bảng `audit_logs`. |
| `action` | `VARCHAR` | - | `-` | Trường action của bảng `audit_logs`. |
| `table_name` | `VARCHAR` | - | `-` | Trường table name của bảng `audit_logs`. |
| `record_id` | `VARCHAR` | - | `-` | Trường record id của bảng `audit_logs`. |
| `timestamp` | `DATETIME` | - | `<function datetime.utcnow at 0x000001E962E14CC0>` | Trường timestamp của bảng `audit_logs`. |
| `ip_address` | `VARCHAR` | - | `-` | Trường ip address của bảng `audit_logs`. |

## `carriers`

Danh muc nha van chuyen thue ngoai.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `carriers`. |
| `name` | `VARCHAR` | Bắt buộc | `-` | Trường name của bảng `carriers`. |
| `tax_code` | `VARCHAR` | - | `-` | Trường tax code của bảng `carriers`. |
| `contact_person` | `VARCHAR` | - | `-` | Trường contact person của bảng `carriers`. |
| `phone` | `VARCHAR` | - | `-` | Trường phone của bảng `carriers`. |
| `email` | `VARCHAR` | - | `-` | Trường email của bảng `carriers`. |
| `status` | `VARCHAR` | Bắt buộc | `active` | Trường status của bảng `carriers`. |
| `is_internal` | `BOOLEAN` | Bắt buộc | `False` | Trường is internal của bảng `carriers`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F079C0>` | Trường created at của bảng `carriers`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `carriers`. |

## `chart_of_accounts`

He thong tai khoan ke toan.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `account_code` | `VARCHAR` | PK; Bắt buộc | `-` | Trường account code của bảng `chart_of_accounts`. |
| `account_name` | `VARCHAR` | - | `-` | Trường account name của bảng `chart_of_accounts`. |
| `type` | `VARCHAR` | - | `-` | Trường type của bảng `chart_of_accounts`. |

## `cost_formulas`

Cong thuc va cau thanh chi phi theo loai xe/tien te.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `cost_formulas`. |
| `name` | `VARCHAR` | - | `-` | Trường name của bảng `cost_formulas`. |
| `formula_expression` | `TEXT` | - | `-` | Trường formula expression của bảng `cost_formulas`. |

## `currencies`

Danh muc tien te cua luong du lieu goc.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `currencies`. |
| `exchange_rate` | `FLOAT` | - | `1.0` | Trường exchange rate của bảng `currencies`. |

## `currency_definitions`

Danh muc tien te va ty gia van hanh hien tai.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `code` | `VARCHAR(3)` | PK; Bắt buộc | `-` | Trường code của bảng `currency_definitions`. |
| `minor_units` | `INTEGER` | Bắt buộc | `-` | Trường minor units của bảng `currency_definitions`. |
| `is_active` | `BOOLEAN` | Bắt buộc | `True` | Trường is active của bảng `currency_definitions`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962BD7B00>` | Trường created at của bảng `currency_definitions`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962BD7E20>` | Trường updated at của bảng `currency_definitions`. |

## `currency_rate_history`

Lich su thay doi ty gia de doi chieu va audit.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `currency_rate_history`. |
| `currency_code` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `-` | Trường currency code của bảng `currency_rate_history`. |
| `functional_currency` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `-` | Trường functional currency của bảng `currency_rate_history`. |
| `rate_date` | `DATE` | Bắt buộc | `-` | Trường rate date của bảng `currency_rate_history`. |
| `rate` | `NUMERIC(18, 8)` | Bắt buộc | `-` | Trường rate của bảng `currency_rate_history`. |
| `source` | `VARCHAR(100)` | Bắt buộc | `-` | Trường source của bảng `currency_rate_history`. |
| `is_active` | `BOOLEAN` | Bắt buộc | `True` | Trường is active của bảng `currency_rate_history`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962BF9EE0>` | Trường created at của bảng `currency_rate_history`. |

## `customers`

Ho so khach hang va thong tin lien he.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `customers`. |
| `name` | `VARCHAR` | Bắt buộc | `-` | Trường name của bảng `customers`. |
| `type` | `VARCHAR` | - | `Account` | Trường type của bảng `customers`. |
| `contact_person` | `VARCHAR` | - | `-` | Trường contact person của bảng `customers`. |
| `phone` | `VARCHAR` | - | `-` | Trường phone của bảng `customers`. |
| `address` | `VARCHAR` | - | `-` | Trường address của bảng `customers`. |
| `vendor_type` | `VARCHAR` | - | `-` | Trường vendor type của bảng `customers`. |

## `delivery_order_charge_adjustments`

Cac khoan tang/giam gia khi chot DO.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(128)` | PK; Bắt buộc | `-` | Trường id của bảng `delivery_order_charge_adjustments`. |
| `closeout_id` | `VARCHAR(128)` | Bắt buộc; FK -> `delivery_order_closeouts.id` | `-` | Trường closeout id của bảng `delivery_order_charge_adjustments`. |
| `line_no` | `INTEGER` | Bắt buộc | `-` | Trường line no của bảng `delivery_order_charge_adjustments`. |
| `name` | `VARCHAR(255)` | Bắt buộc | `-` | Trường name của bảng `delivery_order_charge_adjustments`. |
| `original_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường original amount của bảng `delivery_order_charge_adjustments`. |
| `actual_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường actual amount của bảng `delivery_order_charge_adjustments`. |
| `increase_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường increase amount của bảng `delivery_order_charge_adjustments`. |
| `note` | `TEXT` | - | `-` | Trường note của bảng `delivery_order_charge_adjustments`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function DeliveryOrderChargeAdjustment.<lambda> at 0x000001E962DB3880>` | Trường created at của bảng `delivery_order_charge_adjustments`. |
| `created_by` | `VARCHAR(255)` | Bắt buộc | `-` | Trường created by của bảng `delivery_order_charge_adjustments`. |

## `delivery_order_closeouts`

Ket qua chot gia cuoi sau khi giao hang.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(128)` | PK; Bắt buộc | `-` | Trường id của bảng `delivery_order_closeouts`. |
| `do_id` | `VARCHAR` | Bắt buộc; Unique; FK -> `delivery_orders.id` | `-` | Trường do id của bảng `delivery_order_closeouts`. |
| `base_selling_price_snapshot` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường base selling price snapshot của bảng `delivery_order_closeouts`. |
| `base_price_source` | `VARCHAR(32)` | Bắt buộc | `-` | Trường base price source của bảng `delivery_order_closeouts`. |
| `base_price_source_id` | `VARCHAR(128)` | Bắt buộc | `-` | Trường base price source id của bảng `delivery_order_closeouts`. |
| `surcharge_total` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường surcharge total của bảng `delivery_order_closeouts`. |
| `final_selling_price` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường final selling price của bảng `delivery_order_closeouts`. |
| `currency_code` | `VARCHAR(3)` | Bắt buộc | `-` | Trường currency code của bảng `delivery_order_closeouts`. |
| `completed_at` | `DATETIME` | Bắt buộc | `-` | Trường completed at của bảng `delivery_order_closeouts`. |
| `completed_by` | `VARCHAR(255)` | Bắt buộc | `-` | Trường completed by của bảng `delivery_order_closeouts`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function DeliveryOrderCloseout.<lambda> at 0x000001E962DB2660>` | Trường created at của bảng `delivery_order_closeouts`. |

## `delivery_order_details`

Danh sach hang hoa cua tung lenh giao hang.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `delivery_order_details`. |
| `so_id` | `VARCHAR` | FK -> `sales_orders.id` | `-` | Trường so id của bảng `delivery_order_details`. |
| `sku` | `VARCHAR` | - | `-` | Trường sku của bảng `delivery_order_details`. |
| `description` | `VARCHAR` | - | `-` | Trường description của bảng `delivery_order_details`. |
| `qty` | `INTEGER` | - | `1` | Trường qty của bảng `delivery_order_details`. |
| `uom` | `VARCHAR` | - | `PCS` | Trường uom của bảng `delivery_order_details`. |
| `unit_price` | `FLOAT` | - | `0.0` | Trường unit price của bảng `delivery_order_details`. |
| `amount` | `FLOAT` | - | `0.0` | Trường amount của bảng `delivery_order_details`. |
| `weight_kg` | `FLOAT` | - | `0.0` | Trường weight kg của bảng `delivery_order_details`. |

## `delivery_orders`

Lenh giao hang va cua so lay/giao hang.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `delivery_orders`. |
| `canonical_status` | `VARCHAR` | Bắt buộc | `pending` | Trường canonical status của bảng `delivery_orders`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962CDC900>` | Trường created at của bảng `delivery_orders`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962CDC860>` | Trường updated at của bảng `delivery_orders`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `delivery_orders`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `system` | Trường updated by của bảng `delivery_orders`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `delivery_orders`. |
| `so_id` | `VARCHAR` | Unique; FK -> `sales_orders.id` | `-` | Trường so id của bảng `delivery_orders`. |
| `customer_id` | `VARCHAR` | FK -> `customers.id` | `-` | Trường customer id của bảng `delivery_orders`. |
| `route_id` | `VARCHAR` | FK -> `routes.id` | `-` | Trường route id của bảng `delivery_orders`. |
| `origin` | `VARCHAR` | - | `-` | Trường origin của bảng `delivery_orders`. |
| `destination` | `VARCHAR` | - | `-` | Trường destination của bảng `delivery_orders`. |
| `pickup_window_start` | `DATETIME` | - | `-` | Trường pickup window start của bảng `delivery_orders`. |
| `pickup_window_end` | `DATETIME` | - | `-` | Trường pickup window end của bảng `delivery_orders`. |
| `delivery_window_start` | `DATETIME` | - | `-` | Trường delivery window start của bảng `delivery_orders`. |
| `delivery_window_end` | `DATETIME` | - | `-` | Trường delivery window end của bảng `delivery_orders`. |
| `weight_kg` | `FLOAT` | - | `0.0` | Trường weight kg của bảng `delivery_orders`. |
| `pallet_count` | `INTEGER` | - | `0` | Trường pallet count của bảng `delivery_orders`. |
| `vehicle_id` | `VARCHAR` | FK -> `vehicles.id` | `-` | Trường vehicle id của bảng `delivery_orders`. |
| `driver_id` | `VARCHAR` | FK -> `drivers.id` | `-` | Trường driver id của bảng `delivery_orders`. |
| `co_driver` | `VARCHAR` | - | `-` | Trường co driver của bảng `delivery_orders`. |
| `status` | `VARCHAR` | - | `Chờ vận chuyển` | Trường status của bảng `delivery_orders`. |
| `pickup_date` | `DATETIME` | - | `-` | Trường pickup date của bảng `delivery_orders`. |
| `delivery_date` | `DATETIME` | - | `-` | Trường delivery date của bảng `delivery_orders`. |
| `planned_departure_at` | `DATETIME` | - | `-` | Trường planned departure at của bảng `delivery_orders`. |
| `planned_arrival_at` | `DATETIME` | - | `-` | Trường planned arrival at của bảng `delivery_orders`. |
| `planned_return_at` | `DATETIME` | - | `-` | Trường planned return at của bảng `delivery_orders`. |
| `avg_speed_kmh` | `FLOAT` | - | `-` | Trường avg speed kmh của bảng `delivery_orders`. |
| `max_speed_kmh` | `FLOAT` | - | `-` | Trường max speed kmh của bảng `delivery_orders`. |
| `return_speed_kmh` | `FLOAT` | - | `-` | Trường return speed kmh của bảng `delivery_orders`. |
| `load_minutes` | `INTEGER` | - | `0` | Trường load minutes của bảng `delivery_orders`. |
| `unload_minutes` | `INTEGER` | - | `0` | Trường unload minutes của bảng `delivery_orders`. |
| `return_distance_km` | `FLOAT` | - | `-` | Trường return distance km của bảng `delivery_orders`. |
| `packaging_spec` | `VARCHAR` | - | `Thùng Carton` | Trường packaging spec của bảng `delivery_orders`. |
| `volume_m3` | `FLOAT` | - | `5.0` | Trường volume m3 của bảng `delivery_orders`. |

## `delivery_pod_documents`

Tep anh/PDF POD cua tung diem giao.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(128)` | PK; Bắt buộc | `-` | Trường id của bảng `delivery_pod_documents`. |
| `pod_record_id` | `INTEGER` | Bắt buộc; FK -> `delivery_pod_records.id` | `-` | Trường pod record id của bảng `delivery_pod_documents`. |
| `file_name` | `VARCHAR(255)` | Bắt buộc | `-` | Trường file name của bảng `delivery_pod_documents`. |
| `mime_type` | `VARCHAR(128)` | Bắt buộc | `-` | Trường mime type của bảng `delivery_pod_documents`. |
| `file_size` | `INTEGER` | Bắt buộc | `-` | Trường file size của bảng `delivery_pod_documents`. |
| `checksum` | `VARCHAR(128)` | Bắt buộc | `-` | Trường checksum của bảng `delivery_pod_documents`. |
| `content` | `BLOB` | Bắt buộc | `-` | Trường content của bảng `delivery_pod_documents`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function DeliveryPODDocument.<lambda> at 0x000001E962DE0900>` | Trường created at của bảng `delivery_pod_documents`. |
| `created_by` | `VARCHAR(255)` | Bắt buộc | `-` | Trường created by của bảng `delivery_pod_documents`. |

## `delivery_pod_records`

Thong tin giao nhan va chu ky theo diem giao.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `delivery_pod_records`. |
| `idempotency_key` | `VARCHAR(128)` | - | `-` | Trường idempotency key của bảng `delivery_pod_records`. |
| `do_id` | `VARCHAR` | Bắt buộc; FK -> `delivery_orders.id` | `-` | Trường do id của bảng `delivery_pod_records`. |
| `trip_id` | `VARCHAR(128)` | FK -> `transport_trips.id` | `-` | Trường trip id của bảng `delivery_pod_records`. |
| `leg_id` | `VARCHAR(128)` | FK -> `transport_trip_legs.id` | `-` | Trường leg id của bảng `delivery_pod_records`. |
| `vehicle_id` | `VARCHAR` | Bắt buộc; FK -> `vehicles.id` | `-` | Trường vehicle id của bảng `delivery_pod_records`. |
| `driver_id` | `VARCHAR` | FK -> `drivers.id` | `-` | Trường driver id của bảng `delivery_pod_records`. |
| `stop_no` | `INTEGER` | Bắt buộc | `1` | Trường stop no của bảng `delivery_pod_records`. |
| `location_text` | `VARCHAR` | - | `-` | Trường location text của bảng `delivery_pod_records`. |
| `receiver_name` | `VARCHAR` | - | `-` | Trường receiver name của bảng `delivery_pod_records`. |
| `receiver_phone` | `VARCHAR` | - | `-` | Trường receiver phone của bảng `delivery_pod_records`. |
| `delivery_time` | `DATETIME` | - | `-` | Trường delivery time của bảng `delivery_pod_records`. |
| `photo_url` | `VARCHAR` | - | `-` | Trường photo url của bảng `delivery_pod_records`. |
| `signature_url` | `VARCHAR` | - | `-` | Trường signature url của bảng `delivery_pod_records`. |
| `delivery_result` | `VARCHAR(32)` | - | `-` | Trường delivery result của bảng `delivery_pod_records`. |
| `cargo_condition` | `TEXT` | - | `-` | Trường cargo condition của bảng `delivery_pod_records`. |
| `note` | `TEXT` | - | `-` | Trường note của bảng `delivery_pod_records`. |
| `status` | `VARCHAR` | Bắt buộc | `completed` | Trường status của bảng `delivery_pod_records`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function DeliveryPODRecord.<lambda> at 0x000001E962D645E0>` | Trường created at của bảng `delivery_pod_records`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `delivery_pod_records`. |

Chỉ mục: `uq_delivery_pod_idempotency`, `uq_legacy_delivery_pod_vehicle_stop`, `uq_trip_delivery_pod_vehicle_stop`.

## `driver_qualifications`

Bang cap/chung chi va dieu kien cua tai xe.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `driver_id` | `VARCHAR` | PK; Bắt buộc; FK -> `drivers.id` | `-` | Trường driver id của bảng `driver_qualifications`. |
| `license_type` | `VARCHAR` | Bắt buộc | `-` | Trường license type của bảng `driver_qualifications`. |
| `valid_from` | `DATETIME` | Bắt buộc | `-` | Trường valid from của bảng `driver_qualifications`. |
| `valid_to` | `DATETIME` | Bắt buộc | `-` | Trường valid to của bảng `driver_qualifications`. |
| `status` | `VARCHAR` | Bắt buộc | `active` | Trường status của bảng `driver_qualifications`. |
| `verified_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F36E80>` | Trường verified at của bảng `driver_qualifications`. |
| `verified_by` | `VARCHAR` | Bắt buộc | `system` | Trường verified by của bảng `driver_qualifications`. |

## `driver_shift_assignments`

Ca lam viec, lich nghi va chuyen da khoa cua nhan su.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(128)` | PK; Bắt buộc | `-` | Trường id của bảng `driver_shift_assignments`. |
| `driver_id` | `VARCHAR` | Bắt buộc; FK -> `drivers.id` | `-` | Trường driver id của bảng `driver_shift_assignments`. |
| `vehicle_id` | `VARCHAR` | FK -> `vehicles.id` | `-` | Trường vehicle id của bảng `driver_shift_assignments`. |
| `trip_id` | `VARCHAR(128)` | FK -> `transport_trips.id` | `-` | Trường trip id của bảng `driver_shift_assignments`. |
| `shift_type` | `VARCHAR(20)` | Bắt buộc | `custom` | Trường shift type của bảng `driver_shift_assignments`. |
| `availability_kind` | `VARCHAR(20)` | Bắt buộc | `work` | Trường availability kind của bảng `driver_shift_assignments`. |
| `shift_start` | `DATETIME` | Bắt buộc | `-` | Trường shift start của bảng `driver_shift_assignments`. |
| `shift_end` | `DATETIME` | Bắt buộc | `-` | Trường shift end của bảng `driver_shift_assignments`. |
| `work_location` | `VARCHAR(500)` | - | `-` | Trường work location của bảng `driver_shift_assignments`. |
| `notes` | `TEXT` | - | `-` | Trường notes của bảng `driver_shift_assignments`. |
| `status` | `VARCHAR(20)` | Bắt buộc | `planned` | Trường status của bảng `driver_shift_assignments`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `driver_shift_assignments`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962C5F560>` | Trường created at của bảng `driver_shift_assignments`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962C5F600>` | Trường updated at của bảng `driver_shift_assignments`. |
| `created_by` | `VARCHAR(128)` | Bắt buộc | `system` | Trường created by của bảng `driver_shift_assignments`. |
| `updated_by` | `VARCHAR(128)` | Bắt buộc | `system` | Trường updated by của bảng `driver_shift_assignments`. |

Chỉ mục: `ix_driver_shift_driver_period`, `ix_driver_shift_vehicle_period`.

## `drivers`

Ho so tai xe, phu xe, bang lai va trang thai nguon luc.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `drivers`. |
| `name` | `VARCHAR` | Bắt buộc | `-` | Trường name của bảng `drivers`. |
| `role` | `VARCHAR` | - | `Lái xe chính` | Trường role của bảng `drivers`. |
| `license_type` | `VARCHAR` | - | `Hạng FC` | Trường license type của bảng `drivers`. |
| `phone` | `VARCHAR` | - | `-` | Trường phone của bảng `drivers`. |
| `assigned_vehicle` | `VARCHAR` | - | `Chưa gán` | Trường assigned vehicle của bảng `drivers`. |
| `shift` | `VARCHAR` | - | `Ca Sáng (06:00 - 14:00)` | Trường shift của bảng `drivers`. |
| `status` | `VARCHAR` | - | `🟢 Rảnh (Sẵn sàng)` | Trường status của bảng `drivers`. |
| `photo_url` | `TEXT` | - | `-` | Trường photo url của bảng `drivers`. |

## `epl_expense_vouchers`

Phieu chi phi EPL lien ket Trip va Actual Cost.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(128)` | PK; Bắt buộc | `-` | Trường id của bảng `epl_expense_vouchers`. |
| `trip_id` | `VARCHAR(128)` | Bắt buộc; FK -> `transport_trips.id` | `-` | Trường trip id của bảng `epl_expense_vouchers`. |
| `cost_id` | `VARCHAR(128)` | Bắt buộc; FK -> `freight_actual_costs.id` | `-` | Trường cost id của bảng `epl_expense_vouchers`. |
| `do_id` | `VARCHAR` | FK -> `delivery_orders.id` | `-` | Trường do id của bảng `epl_expense_vouchers`. |
| `voucher_no` | `VARCHAR(128)` | Bắt buộc | `-` | Trường voucher no của bảng `epl_expense_vouchers`. |
| `voucher_date` | `DATE` | Bắt buộc | `-` | Trường voucher date của bảng `epl_expense_vouchers`. |
| `vehicle_manager` | `VARCHAR(255)` | - | `-` | Trường vehicle manager của bảng `epl_expense_vouchers`. |
| `payment_method` | `VARCHAR(32)` | Bắt buộc | `cash` | Trường payment method của bảng `epl_expense_vouchers`. |
| `contract_no` | `VARCHAR(128)` | - | `-` | Trường contract no của bảng `epl_expense_vouchers`. |
| `machine_numbers` | `VARCHAR(500)` | - | `-` | Trường machine numbers của bảng `epl_expense_vouchers`. |
| `checked_by` | `VARCHAR(255)` | - | `-` | Trường checked by của bảng `epl_expense_vouchers`. |
| `note` | `TEXT` | - | `-` | Trường note của bảng `epl_expense_vouchers`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `epl_expense_vouchers`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962FCF560>` | Trường created at của bảng `epl_expense_vouchers`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962FCF600>` | Trường updated at của bảng `epl_expense_vouchers`. |
| `created_by` | `VARCHAR(128)` | Bắt buộc | `-` | Trường created by của bảng `epl_expense_vouchers`. |
| `updated_by` | `VARCHAR(128)` | Bắt buộc | `-` | Trường updated by của bảng `epl_expense_vouchers`. |

## `finance_control_config`

Cau hinh kiem soat nghiep vu tai chinh.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(20)` | PK; Bắt buộc | `GLOBAL` | Trường id của bảng `finance_control_config`. |
| `functional_currency` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `VND` | Trường functional currency của bảng `finance_control_config`. |
| `enforce_creator_approver_sod` | `BOOLEAN` | Bắt buộc | `True` | Trường enforce creator approver sod của bảng `finance_control_config`. |
| `require_distinct_poster` | `BOOLEAN` | Bắt buộc | `True` | Trường require distinct poster của bảng `finance_control_config`. |
| `distance_variance_threshold` | `NUMERIC(18, 8)` | Bắt buộc | `0` | Trường distance variance threshold của bảng `finance_control_config`. |
| `document_https_hosts` | `TEXT` | Bắt buộc | `` | Trường document https hosts của bảng `finance_control_config`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962C24360>` | Trường created at của bảng `finance_control_config`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962C24400>` | Trường updated at của bảng `finance_control_config`. |

## `freight_actual_costs`

Chi phi van hanh thuc te cua Freight Order/Trip.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `freight_actual_costs`. |
| `freight_order_id` | `VARCHAR` | Bắt buộc; FK -> `freight_orders.id` | `-` | Trường freight order id của bảng `freight_actual_costs`. |
| `trip_id` | `VARCHAR(128)` | FK -> `transport_trips.id` | `-` | Trường trip id của bảng `freight_actual_costs`. |
| `leg_id` | `VARCHAR(128)` | FK -> `transport_trip_legs.id` | `-` | Trường leg id của bảng `freight_actual_costs`. |
| `carrier_id` | `VARCHAR` | Bắt buộc; FK -> `carriers.id` | `-` | Trường carrier id của bảng `freight_actual_costs`. |
| `currency_code` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `-` | Trường currency code của bảng `freight_actual_costs`. |
| `functional_currency` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `-` | Trường functional currency của bảng `freight_actual_costs`. |
| `exchange_rate_snapshot` | `NUMERIC(18, 8)` | Bắt buộc | `1` | Trường exchange rate snapshot của bảng `freight_actual_costs`. |
| `exchange_rate_date` | `DATE` | Bắt buộc | `-` | Trường exchange rate date của bảng `freight_actual_costs`. |
| `exchange_rate_source` | `VARCHAR(100)` | Bắt buộc | `-` | Trường exchange rate source của bảng `freight_actual_costs`. |
| `planned_distance_km` | `NUMERIC(18, 3)` | Bắt buộc | `0` | Trường planned distance km của bảng `freight_actual_costs`. |
| `actual_distance_km` | `NUMERIC(18, 3)` | Bắt buộc | `0` | Trường actual distance km của bảng `freight_actual_costs`. |
| `distance_status` | `VARCHAR(32)` | Bắt buộc | `insufficient_gps_data` | Trường distance status của bảng `freight_actual_costs`. |
| `distance_variance_percent` | `NUMERIC(18, 8)` | - | `-` | Trường distance variance percent của bảng `freight_actual_costs`. |
| `distance_variance_warning` | `BOOLEAN` | Bắt buộc | `False` | Trường distance variance warning của bảng `freight_actual_costs`. |
| `subtotal_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường subtotal amount của bảng `freight_actual_costs`. |
| `tax_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường tax amount của bảng `freight_actual_costs`. |
| `total_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường total amount của bảng `freight_actual_costs`. |
| `status` | `VARCHAR(16)` | Bắt buộc | `draft` | Trường status của bảng `freight_actual_costs`. |
| `is_active` | `BOOLEAN` | Bắt buộc | `True` | Trường is active của bảng `freight_actual_costs`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `freight_actual_costs`. |
| `reversal_of_cost_id` | `VARCHAR` | Unique; FK -> `freight_actual_costs.id` | `-` | Trường reversal of cost id của bảng `freight_actual_costs`. |
| `reversed_by_cost_id` | `VARCHAR` | Unique; FK -> `freight_actual_costs.id` | `-` | Trường reversed by cost id của bảng `freight_actual_costs`. |
| `reversal_reason` | `TEXT` | - | `-` | Trường reversal reason của bảng `freight_actual_costs`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F8E200>` | Trường created at của bảng `freight_actual_costs`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F8E2A0>` | Trường updated at của bảng `freight_actual_costs`. |
| `submitted_at` | `DATETIME` | - | `-` | Trường submitted at của bảng `freight_actual_costs`. |
| `approved_at` | `DATETIME` | - | `-` | Trường approved at của bảng `freight_actual_costs`. |
| `reversed_at` | `DATETIME` | - | `-` | Trường reversed at của bảng `freight_actual_costs`. |
| `created_by` | `VARCHAR` | Bắt buộc | `-` | Trường created by của bảng `freight_actual_costs`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `-` | Trường updated by của bảng `freight_actual_costs`. |
| `submitted_by` | `VARCHAR` | - | `-` | Trường submitted by của bảng `freight_actual_costs`. |
| `approved_by` | `VARCHAR` | - | `-` | Trường approved by của bảng `freight_actual_costs`. |
| `reversed_by` | `VARCHAR` | - | `-` | Trường reversed by của bảng `freight_actual_costs`. |

Chỉ mục: `uq_active_cost_trip`, `uq_legacy_active_cost_freight_order`.

## `freight_charge_items`

Dong chi phi chi tiet cua ho so chi phi thuc te.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `freight_charge_items`. |
| `cost_id` | `VARCHAR` | Bắt buộc; FK -> `freight_actual_costs.id` | `-` | Trường cost id của bảng `freight_charge_items`. |
| `charge_type` | `VARCHAR(32)` | Bắt buộc | `-` | Trường charge type của bảng `freight_charge_items`. |
| `description` | `VARCHAR(500)` | - | `-` | Trường description của bảng `freight_charge_items`. |
| `original_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường original amount của bảng `freight_charge_items`. |
| `actual_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường actual amount của bảng `freight_charge_items`. |
| `increase_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường increase amount của bảng `freight_charge_items`. |
| `note` | `TEXT` | - | `-` | Trường note của bảng `freight_charge_items`. |
| `quantity` | `NUMERIC(18, 4)` | Bắt buộc | `-` | Trường quantity của bảng `freight_charge_items`. |
| `unit_price` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường unit price của bảng `freight_charge_items`. |
| `tax_code` | `VARCHAR(50)` | Bắt buộc | `-` | Trường tax code của bảng `freight_charge_items`. |
| `tax_rate_snapshot` | `NUMERIC(18, 8)` | Bắt buộc | `-` | Trường tax rate snapshot của bảng `freight_charge_items`. |
| `tax_mode` | `VARCHAR(20)` | Bắt buộc | `-` | Trường tax mode của bảng `freight_charge_items`. |
| `net_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường net amount của bảng `freight_charge_items`. |
| `tax_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường tax amount của bảng `freight_charge_items`. |
| `total_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường total amount của bảng `freight_charge_items`. |
| `rounding_adjustment` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường rounding adjustment của bảng `freight_charge_items`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962FCCA40>` | Trường created at của bảng `freight_charge_items`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962FCCAE0>` | Trường updated at của bảng `freight_charge_items`. |
| `created_by` | `VARCHAR` | Bắt buộc | `-` | Trường created by của bảng `freight_charge_items`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `-` | Trường updated by của bảng `freight_charge_items`. |

## `freight_cost_documents`

Chung tu dinh kem cho chi phi van tai.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `freight_cost_documents`. |
| `cost_id` | `VARCHAR` | Bắt buộc; FK -> `freight_actual_costs.id` | `-` | Trường cost id của bảng `freight_cost_documents`. |
| `document_type` | `VARCHAR(64)` | Bắt buộc | `-` | Trường document type của bảng `freight_cost_documents`. |
| `storage_url` | `TEXT` | Bắt buộc | `-` | Trường storage url của bảng `freight_cost_documents`. |
| `file_name` | `VARCHAR(255)` | - | `-` | Trường file name của bảng `freight_cost_documents`. |
| `mime_type` | `VARCHAR(128)` | - | `-` | Trường mime type của bảng `freight_cost_documents`. |
| `checksum` | `VARCHAR(128)` | Bắt buộc | `-` | Trường checksum của bảng `freight_cost_documents`. |
| `vendor_invoice_no` | `VARCHAR(128)` | - | `-` | Trường vendor invoice no của bảng `freight_cost_documents`. |
| `document_date` | `DATE` | - | `-` | Trường document date của bảng `freight_cost_documents`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962FCE0C0>` | Trường created at của bảng `freight_cost_documents`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962FCE160>` | Trường updated at của bảng `freight_cost_documents`. |
| `created_by` | `VARCHAR` | Bắt buộc | `-` | Trường created by của bảng `freight_cost_documents`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `-` | Trường updated by của bảng `freight_cost_documents`. |

## `freight_order_legacy_links`

Lien ket Freight Order voi ma ho so he thong cu.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `freight_order_id` | `VARCHAR` | PK; Bắt buộc; FK -> `freight_orders.id` | `-` | Trường freight order id của bảng `freight_order_legacy_links`. |
| `delivery_order_id` | `VARCHAR` | Bắt buộc; Unique; FK -> `delivery_orders.id` | `-` | Trường delivery order id của bảng `freight_order_legacy_links`. |

## `freight_order_units`

Lien ket Freight Order voi cac don vi hang.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `freight_order_id` | `VARCHAR` | PK; Bắt buộc; FK -> `freight_orders.id` | `-` | Trường freight order id của bảng `freight_order_units`. |
| `freight_unit_id` | `VARCHAR` | PK; Bắt buộc; Unique; FK -> `freight_units.id` | `-` | Trường freight unit id của bảng `freight_order_units`. |

## `freight_orders`

Lenh van tai chuan dung cho lap ke hoach va tai chinh.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `freight_orders`. |
| `pickup_location_id` | `VARCHAR` | Bắt buộc; FK -> `locations.id` | `-` | Trường pickup location id của bảng `freight_orders`. |
| `delivery_location_id` | `VARCHAR` | Bắt buộc; FK -> `locations.id` | `-` | Trường delivery location id của bảng `freight_orders`. |
| `pickup_window_start` | `DATETIME` | Bắt buộc | `-` | Trường pickup window start của bảng `freight_orders`. |
| `pickup_window_end` | `DATETIME` | Bắt buộc | `-` | Trường pickup window end của bảng `freight_orders`. |
| `delivery_window_start` | `DATETIME` | Bắt buộc | `-` | Trường delivery window start của bảng `freight_orders`. |
| `delivery_window_end` | `DATETIME` | Bắt buộc | `-` | Trường delivery window end của bảng `freight_orders`. |
| `total_weight_kg` | `FLOAT` | Bắt buộc | `0` | Trường total weight kg của bảng `freight_orders`. |
| `total_volume_m3` | `FLOAT` | Bắt buộc | `0` | Trường total volume m3 của bảng `freight_orders`. |
| `total_pallet_count` | `INTEGER` | Bắt buộc | `0` | Trường total pallet count của bảng `freight_orders`. |
| `max_weight_kg` | `FLOAT` | Bắt buộc | `-` | Trường max weight kg của bảng `freight_orders`. |
| `max_volume_m3` | `FLOAT` | Bắt buộc | `-` | Trường max volume m3 của bảng `freight_orders`. |
| `max_pallet_count` | `INTEGER` | Bắt buộc | `-` | Trường max pallet count của bảng `freight_orders`. |
| `status` | `VARCHAR` | Bắt buộc | `planned` | Trường status của bảng `freight_orders`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `freight_orders`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962ED5EE0>` | Trường created at của bảng `freight_orders`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962ED5F80>` | Trường updated at của bảng `freight_orders`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `freight_orders`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `system` | Trường updated by của bảng `freight_orders`. |

## `freight_settlements`

Ho so doi soat cac khoan phai tra.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `freight_settlements`. |
| `ap_invoice_id` | `VARCHAR` | Bắt buộc; Unique; FK -> `ap_invoices.id` | `-` | Trường ap invoice id của bảng `freight_settlements`. |
| `settlement_period` | `VARCHAR(32)` | Bắt buộc | `-` | Trường settlement period của bảng `freight_settlements`. |
| `currency_code` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `-` | Trường currency code của bảng `freight_settlements`. |
| `functional_currency` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `-` | Trường functional currency của bảng `freight_settlements`. |
| `approved_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường approved amount của bảng `freight_settlements`. |
| `paid_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường paid amount của bảng `freight_settlements`. |
| `remaining_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường remaining amount của bảng `freight_settlements`. |
| `status` | `VARCHAR(20)` | Bắt buộc | `open` | Trường status của bảng `freight_settlements`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `freight_settlements`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E96304D3A0>` | Trường created at của bảng `freight_settlements`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E96304D440>` | Trường updated at của bảng `freight_settlements`. |
| `created_by` | `VARCHAR` | Bắt buộc | `-` | Trường created by của bảng `freight_settlements`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `-` | Trường updated by của bảng `freight_settlements`. |

## `freight_units`

Don vi hang van tai duoc gom tu nhu cau.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `freight_units`. |
| `demand_id` | `VARCHAR` | Bắt buộc; Unique; FK -> `transport_demands.id` | `-` | Trường demand id của bảng `freight_units`. |
| `pickup_location_id` | `VARCHAR` | Bắt buộc; FK -> `locations.id` | `-` | Trường pickup location id của bảng `freight_units`. |
| `delivery_location_id` | `VARCHAR` | Bắt buộc; FK -> `locations.id` | `-` | Trường delivery location id của bảng `freight_units`. |
| `pickup_window_start` | `DATETIME` | Bắt buộc | `-` | Trường pickup window start của bảng `freight_units`. |
| `pickup_window_end` | `DATETIME` | Bắt buộc | `-` | Trường pickup window end của bảng `freight_units`. |
| `delivery_window_start` | `DATETIME` | Bắt buộc | `-` | Trường delivery window start của bảng `freight_units`. |
| `delivery_window_end` | `DATETIME` | Bắt buộc | `-` | Trường delivery window end của bảng `freight_units`. |
| `weight_kg` | `FLOAT` | Bắt buộc | `0` | Trường weight kg của bảng `freight_units`. |
| `volume_m3` | `FLOAT` | Bắt buộc | `0` | Trường volume m3 của bảng `freight_units`. |
| `pallet_count` | `INTEGER` | Bắt buộc | `0` | Trường pallet count của bảng `freight_units`. |
| `status` | `VARCHAR` | Bắt buộc | `open` | Trường status của bảng `freight_units`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `freight_units`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962E9BBA0>` | Trường created at của bảng `freight_units`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `freight_units`. |

## `gl_transactions`

But toan so cai phat sinh tu hoa don va nghiep vu tai chinh.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `gl_transactions`. |
| `invoice_id` | `VARCHAR` | FK -> `ar_invoices.id` | `-` | Trường invoice id của bảng `gl_transactions`. |
| `date` | `VARCHAR` | - | `-` | Trường date của bảng `gl_transactions`. |
| `account_code` | `VARCHAR` | - | `-` | Trường account code của bảng `gl_transactions`. |
| `debit` | `FLOAT` | - | `0.0` | Trường debit của bảng `gl_transactions`. |
| `credit` | `FLOAT` | - | `0.0` | Trường credit của bảng `gl_transactions`. |

## `idempotency_records`

Khoa chong tao trung khi goi lai API.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `idempotency_records`. |
| `actor` | `VARCHAR(128)` | Bắt buộc | `-` | Trường actor của bảng `idempotency_records`. |
| `method` | `VARCHAR(16)` | Bắt buộc | `-` | Trường method của bảng `idempotency_records`. |
| `path` | `VARCHAR(500)` | Bắt buộc | `-` | Trường path của bảng `idempotency_records`. |
| `idempotency_key` | `VARCHAR(128)` | Bắt buộc | `-` | Trường idempotency key của bảng `idempotency_records`. |
| `operation` | `VARCHAR` | Bắt buộc | `` | Trường operation của bảng `idempotency_records`. |
| `request_hash` | `VARCHAR` | Bắt buộc | `-` | Trường request hash của bảng `idempotency_records`. |
| `response_json` | `TEXT` | Bắt buộc | `-` | Trường response json của bảng `idempotency_records`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962E71300>` | Trường created at của bảng `idempotency_records`. |

## `incidents`

Su co phat sinh trong qua trinh van chuyen.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `incidents`. |
| `do_id` | `VARCHAR` | - | `-` | Trường do id của bảng `incidents`. |
| `vehicle_id` | `VARCHAR` | - | `-` | Trường vehicle id của bảng `incidents`. |
| `incident_type` | `VARCHAR` | - | `-` | Trường incident type của bảng `incidents`. |
| `severity` | `VARCHAR` | - | `Medium` | Trường severity của bảng `incidents`. |
| `location` | `VARCHAR` | - | `-` | Trường location của bảng `incidents`. |
| `description` | `TEXT` | - | `-` | Trường description của bảng `incidents`. |
| `reporter` | `VARCHAR` | - | `Tài xế / Điều phối` | Trường reporter của bảng `incidents`. |
| `reported_at` | `VARCHAR` | - | `-` | Trường reported at của bảng `incidents`. |
| `status` | `VARCHAR` | - | `Pending` | Trường status của bảng `incidents`. |

## `items`

Danh muc hang hoa.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `items`. |
| `name` | `VARCHAR` | Bắt buộc | `-` | Trường name của bảng `items`. |
| `cargo_type` | `VARCHAR` | - | `-` | Trường cargo type của bảng `items`. |
| `default_uom` | `VARCHAR` | - | `-` | Trường default uom của bảng `items`. |
| `weight_kg` | `FLOAT` | - | `0.0` | Trường weight kg của bảng `items`. |

## `journal_batches`

Lo but toan de kiem soat ghi so.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `journal_batches`. |
| `invoice_id` | `VARCHAR` | Unique; FK -> `ar_invoices.id` | `-` | Trường invoice id của bảng `journal_batches`. |
| `source_type` | `VARCHAR(32)` | - | `-` | Trường source type của bảng `journal_batches`. |
| `source_id` | `VARCHAR` | - | `-` | Trường source id của bảng `journal_batches`. |
| `status` | `VARCHAR` | Bắt buộc | `-` | Trường status của bảng `journal_batches`. |
| `posted_at` | `DATETIME` | - | `-` | Trường posted at của bảng `journal_batches`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962E73420>` | Trường created at của bảng `journal_batches`. |

## `journal_lines`

Dong no/co cua tung lo but toan.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `journal_lines`. |
| `batch_id` | `VARCHAR` | Bắt buộc; FK -> `journal_batches.id` | `-` | Trường batch id của bảng `journal_lines`. |
| `account_code` | `VARCHAR` | Bắt buộc | `-` | Trường account code của bảng `journal_lines`. |
| `debit` | `NUMERIC` | Bắt buộc | `0` | Trường debit của bảng `journal_lines`. |
| `credit` | `NUMERIC` | Bắt buộc | `0` | Trường credit của bảng `journal_lines`. |
| `currency_code` | `VARCHAR` | Bắt buộc | `VND` | Trường currency code của bảng `journal_lines`. |
| `exchange_rate_snapshot` | `NUMERIC` | Bắt buộc | `1` | Trường exchange rate snapshot của bảng `journal_lines`. |
| `transaction_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường transaction amount của bảng `journal_lines`. |
| `transaction_currency` | `VARCHAR(3)` | Bắt buộc | `VND` | Trường transaction currency của bảng `journal_lines`. |
| `exchange_rate` | `NUMERIC(18, 8)` | Bắt buộc | `1` | Trường exchange rate của bảng `journal_lines`. |
| `functional_debit` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường functional debit của bảng `journal_lines`. |
| `functional_credit` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường functional credit của bảng `journal_lines`. |

## `locations`

Danh muc kho, bai, cong va diem giao/nhan.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `locations`. |
| `name` | `VARCHAR` | Bắt buộc | `-` | Trường name của bảng `locations`. |
| `type` | `VARCHAR` | - | `Warehouse` | Trường type của bảng `locations`. |
| `address` | `VARCHAR` | - | `-` | Trường address của bảng `locations`. |
| `capacity` | `FLOAT` | - | `0.0` | Trường capacity của bảng `locations`. |

## `migration_quarantine`

Du lieu khong hop le duoc cach ly khi migration.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `migration_quarantine`. |
| `migration_version` | `VARCHAR` | Bắt buộc | `-` | Trường migration version của bảng `migration_quarantine`. |
| `entity_type` | `VARCHAR` | Bắt buộc | `-` | Trường entity type của bảng `migration_quarantine`. |
| `entity_id` | `VARCHAR` | Bắt buộc | `-` | Trường entity id của bảng `migration_quarantine`. |
| `reason` | `VARCHAR` | Bắt buộc | `-` | Trường reason của bảng `migration_quarantine`. |
| `payload_json` | `TEXT` | Bắt buộc | `-` | Trường payload json của bảng `migration_quarantine`. |
| `quarantined_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962E99300>` | Trường quarantined at của bảng `migration_quarantine`. |

## `parking_events`

Lich su quet QR va chuyen trang thai Parking List.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `parking_events`. |
| `parking_list_id` | `VARCHAR(128)` | Bắt buộc; FK -> `parking_lists.id` | `-` | Trường parking list id của bảng `parking_events`. |
| `event_type` | `VARCHAR(32)` | Bắt buộc | `-` | Trường event type của bảng `parking_events`. |
| `occurred_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962D3C5E0>` | Trường occurred at của bảng `parking_events`. |
| `actor` | `VARCHAR(128)` | Bắt buộc | `system` | Trường actor của bảng `parking_events`. |
| `note` | `TEXT` | - | `-` | Trường note của bảng `parking_events`. |

Chỉ mục: `ix_parking_events_parking_list_id`.

## `parking_labels`

Tem QR duy nhat cho tung kien hang.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(128)` | PK; Bắt buộc | `-` | Trường id của bảng `parking_labels`. |
| `parking_list_id` | `VARCHAR(128)` | Bắt buộc; FK -> `parking_lists.id` | `-` | Trường parking list id của bảng `parking_labels`. |
| `package_no` | `INTEGER` | Bắt buộc | `-` | Trường package no của bảng `parking_labels`. |
| `package_total` | `INTEGER` | Bắt buộc | `-` | Trường package total của bảng `parking_labels`. |
| `qr_token` | `VARCHAR(128)` | Bắt buộc | `-` | Trường qr token của bảng `parking_labels`. |
| `status` | `VARCHAR(20)` | Bắt buộc | `ready` | Trường status của bảng `parking_labels`. |
| `printed_at` | `DATETIME` | - | `-` | Trường printed at của bảng `parking_labels`. |
| `reprint_count` | `INTEGER` | Bắt buộc | `0` | Trường reprint count của bảng `parking_labels`. |

Chỉ mục: `ix_parking_labels_parking_list_id`.

## `parking_list_items`

Dong hang hoa duoc phan bo vao Parking List.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `parking_list_items`. |
| `parking_list_id` | `VARCHAR(128)` | Bắt buộc; FK -> `parking_lists.id` | `-` | Trường parking list id của bảng `parking_list_items`. |
| `source_detail_id` | `INTEGER` | - | `-` | Trường source detail id của bảng `parking_list_items`. |
| `barcode` | `VARCHAR(128)` | - | `-` | Trường barcode của bảng `parking_list_items`. |
| `item_id_laos` | `VARCHAR(128)` | - | `-` | Trường item id laos của bảng `parking_list_items`. |
| `item_id_thai` | `VARCHAR(128)` | - | `-` | Trường item id thai của bảng `parking_list_items`. |
| `sku` | `VARCHAR(128)` | - | `-` | Trường sku của bảng `parking_list_items`. |
| `description` | `VARCHAR(500)` | - | `-` | Trường description của bảng `parking_list_items`. |
| `case_qty` | `INTEGER` | Bắt buộc | `0` | Trường case qty của bảng `parking_list_items`. |
| `piece_qty` | `INTEGER` | Bắt buộc | `0` | Trường piece qty của bảng `parking_list_items`. |
| `uom` | `VARCHAR(32)` | - | `-` | Trường uom của bảng `parking_list_items`. |
| `weight_kg` | `FLOAT` | Bắt buộc | `0` | Trường weight kg của bảng `parking_list_items`. |
| `cube_m3` | `FLOAT` | Bắt buộc | `0` | Trường cube m3 của bảng `parking_list_items`. |
| `note` | `TEXT` | - | `-` | Trường note của bảng `parking_list_items`. |

Chỉ mục: `ix_parking_list_items_parking_list_id`.

## `parking_lists`

Ho so gom kien hang sinh tu DO/SO de quan ly vao bai va boc hang.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(128)` | PK; Bắt buộc | `-` | Trường id của bảng `parking_lists`. |
| `do_id` | `VARCHAR` | Bắt buộc; FK -> `delivery_orders.id` | `-` | Trường do id của bảng `parking_lists`. |
| `so_id` | `VARCHAR` | FK -> `sales_orders.id` | `-` | Trường so id của bảng `parking_lists`. |
| `trip_id` | `VARCHAR(128)` | FK -> `transport_trips.id` | `-` | Trường trip id của bảng `parking_lists`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `parking_lists`. |
| `customer_id` | `VARCHAR` | FK -> `customers.id` | `-` | Trường customer id của bảng `parking_lists`. |
| `store_id` | `VARCHAR(128)` | - | `-` | Trường store id của bảng `parking_lists`. |
| `store_name` | `VARCHAR(255)` | - | `-` | Trường store name của bảng `parking_lists`. |
| `route_code` | `VARCHAR(128)` | - | `-` | Trường route code của bảng `parking_lists`. |
| `route_name` | `VARCHAR(500)` | - | `-` | Trường route name của bảng `parking_lists`. |
| `wave` | `VARCHAR(64)` | - | `-` | Trường wave của bảng `parking_lists`. |
| `gate` | `VARCHAR(64)` | - | `-` | Trường gate của bảng `parking_lists`. |
| `box_count` | `INTEGER` | Bắt buộc | `1` | Trường box count của bảng `parking_lists`. |
| `total_pieces` | `INTEGER` | Bắt buộc | `0` | Trường total pieces của bảng `parking_lists`. |
| `total_weight_kg` | `FLOAT` | Bắt buộc | `0` | Trường total weight kg của bảng `parking_lists`. |
| `total_cube_m3` | `FLOAT` | Bắt buộc | `0` | Trường total cube m3 của bảng `parking_lists`. |
| `status` | `VARCHAR(20)` | Bắt buộc | `ready` | Trường status của bảng `parking_lists`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962D084A0>` | Trường created at của bảng `parking_lists`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962D08540>` | Trường updated at của bảng `parking_lists`. |
| `created_by` | `VARCHAR(128)` | Bắt buộc | `system` | Trường created by của bảng `parking_lists`. |
| `updated_by` | `VARCHAR(128)` | Bắt buộc | `system` | Trường updated by của bảng `parking_lists`. |

Chỉ mục: `ix_parking_list_status_created`, `ix_parking_lists_do_id`.

## `pod`

Ban ghi POD tuong thich voi luong cu.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `do_id` | `VARCHAR` | PK; Bắt buộc; FK -> `delivery_orders.id` | `-` | Trường do id của bảng `pod`. |
| `delivery_time` | `VARCHAR` | - | `-` | Trường delivery time của bảng `pod`. |
| `photo_url` | `VARCHAR` | - | `-` | Trường photo url của bảng `pod`. |
| `signature_url` | `VARCHAR` | - | `-` | Trường signature url của bảng `pod`. |
| `note` | `TEXT` | - | `-` | Trường note của bảng `pod`. |

## `price_lists`

Bang gia dich vu theo doi tuong ap dung.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `price_lists`. |
| `customer_id` | `VARCHAR` | FK -> `customers.id` | `-` | Trường customer id của bảng `price_lists`. |
| `item_id` | `VARCHAR` | FK -> `items.id` | `-` | Trường item id của bảng `price_lists`. |
| `unit_price` | `FLOAT` | - | `0.0` | Trường unit price của bảng `price_lists`. |
| `valid_to` | `VARCHAR` | - | `-` | Trường valid to của bảng `price_lists`. |

## `quotation_details`

Hang muc va so lieu chi tiet cua bao gia.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `quotation_details`. |
| `quotation_id` | `VARCHAR` | FK -> `quotations.id` | `-` | Trường quotation id của bảng `quotation_details`. |
| `item_id` | `VARCHAR` | FK -> `items.id` | `-` | Trường item id của bảng `quotation_details`. |
| `qty` | `INTEGER` | - | `1` | Trường qty của bảng `quotation_details`. |
| `uom` | `VARCHAR` | - | `-` | Trường uom của bảng `quotation_details`. |
| `unit_price` | `FLOAT` | - | `0.0` | Trường unit price của bảng `quotation_details`. |
| `amount` | `FLOAT` | - | `0.0` | Trường amount của bảng `quotation_details`. |

## `quotations`

Phan dau bao gia van tai cho khach hang.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `quotations`. |
| `canonical_status` | `VARCHAR` | Bắt buộc | `draft` | Trường canonical status của bảng `quotations`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962E3E840>` | Trường created at của bảng `quotations`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962E3E8E0>` | Trường updated at của bảng `quotations`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `quotations`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `system` | Trường updated by của bảng `quotations`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `quotations`. |
| `customer_id` | `VARCHAR` | FK -> `customers.id` | `-` | Trường customer id của bảng `quotations`. |
| `route_id` | `VARCHAR` | FK -> `routes.id` | `-` | Trường route id của bảng `quotations`. |
| `origin` | `VARCHAR` | - | `-` | Trường origin của bảng `quotations`. |
| `destination` | `VARCHAR` | - | `-` | Trường destination của bảng `quotations`. |
| `pickup_window_start` | `VARCHAR` | - | `-` | Trường pickup window start của bảng `quotations`. |
| `pickup_window_end` | `VARCHAR` | - | `-` | Trường pickup window end của bảng `quotations`. |
| `delivery_window_start` | `VARCHAR` | - | `-` | Trường delivery window start của bảng `quotations`. |
| `delivery_window_end` | `VARCHAR` | - | `-` | Trường delivery window end của bảng `quotations`. |
| `weight_kg` | `FLOAT` | - | `0.0` | Trường weight kg của bảng `quotations`. |
| `pallet_count` | `INTEGER` | - | `0` | Trường pallet count của bảng `quotations`. |
| `cargo_type` | `VARCHAR` | - | `-` | Trường cargo type của bảng `quotations`. |
| `valid_to` | `VARCHAR` | - | `-` | Trường valid to của bảng `quotations`. |
| `fuel_cost` | `FLOAT` | - | `0.0` | Trường fuel cost của bảng `quotations`. |
| `driver_cost` | `FLOAT` | - | `0.0` | Trường driver cost của bảng `quotations`. |
| `toll_fee` | `FLOAT` | - | `0.0` | Trường toll fee của bảng `quotations`. |
| `total_cost` | `FLOAT` | - | `0.0` | Trường total cost của bảng `quotations`. |
| `selling_price` | `FLOAT` | - | `0.0` | Trường selling price của bảng `quotations`. |
| `packaging_spec` | `VARCHAR` | - | `Thùng Carton` | Trường packaging spec của bảng `quotations`. |
| `volume_m3` | `FLOAT` | - | `5.0` | Trường volume m3 của bảng `quotations`. |
| `status` | `VARCHAR` | - | `Draft` | Trường status của bảng `quotations`. |

## `resource_assignments`

Phan cong xe, tai xe va nguon luc cho lenh van tai.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `resource_assignments`. |
| `freight_order_id` | `VARCHAR` | Bắt buộc; FK -> `freight_orders.id` | `-` | Trường freight order id của bảng `resource_assignments`. |
| `trip_id` | `VARCHAR(128)` | FK -> `transport_trips.id` | `-` | Trường trip id của bảng `resource_assignments`. |
| `leg_id` | `VARCHAR(128)` | FK -> `transport_trip_legs.id` | `-` | Trường leg id của bảng `resource_assignments`. |
| `vehicle_id` | `VARCHAR` | Bắt buộc; FK -> `vehicles.id` | `-` | Trường vehicle id của bảng `resource_assignments`. |
| `driver_id` | `VARCHAR` | Bắt buộc; FK -> `drivers.id` | `-` | Trường driver id của bảng `resource_assignments`. |
| `co_driver_id` | `VARCHAR` | FK -> `drivers.id` | `-` | Trường co driver id của bảng `resource_assignments`. |
| `assignment_start` | `DATETIME` | Bắt buộc | `-` | Trường assignment start của bảng `resource_assignments`. |
| `assignment_end` | `DATETIME` | Bắt buộc | `-` | Trường assignment end của bảng `resource_assignments`. |
| `status` | `VARCHAR` | Bắt buộc | `active` | Trường status của bảng `resource_assignments`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F613A0>` | Trường created at của bảng `resource_assignments`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `resource_assignments`. |

Chỉ mục: `uq_active_assignment_trip`, `uq_legacy_assignment_freight_order`.

## `roles`

Danh muc vai tro phan quyen.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `roles`. |
| `permissions` | `TEXT` | - | `-` | Trường permissions của bảng `roles`. |

## `routes`

Tuyen van tai nguon dung de tao bao gia va Trip.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `routes`. |
| `name` | `VARCHAR` | Bắt buộc | `-` | Trường name của bảng `routes`. |
| `distance_km` | `FLOAT` | - | `0.0` | Trường distance km của bảng `routes`. |
| `segments_json` | `TEXT` | - | `-` | Trường segments json của bảng `routes`. |

## `sales_orders`

Don ban hang duoc tao tu bao gia da duyet.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `sales_orders`. |
| `quotation_id` | `VARCHAR` | Unique; FK -> `quotations.id` | `-` | Trường quotation id của bảng `sales_orders`. |
| `canonical_status` | `VARCHAR` | Bắt buộc | `draft` | Trường canonical status của bảng `sales_orders`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962CA6840>` | Trường created at của bảng `sales_orders`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962CA68E0>` | Trường updated at của bảng `sales_orders`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `sales_orders`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `system` | Trường updated by của bảng `sales_orders`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `sales_orders`. |
| `currency_code` | `VARCHAR` | Bắt buộc | `VND` | Trường currency code của bảng `sales_orders`. |
| `exchange_rate_snapshot` | `NUMERIC` | Bắt buộc | `1` | Trường exchange rate snapshot của bảng `sales_orders`. |
| `tax_rate_snapshot` | `NUMERIC` | - | `-` | Trường tax rate snapshot của bảng `sales_orders`. |
| `order_date` | `VARCHAR` | - | `-` | Trường order date của bảng `sales_orders`. |
| `delivery_date` | `VARCHAR` | - | `-` | Trường delivery date của bảng `sales_orders`. |
| `customer_id` | `VARCHAR` | FK -> `customers.id` | `-` | Trường customer id của bảng `sales_orders`. |
| `route_id` | `VARCHAR` | FK -> `routes.id` | `-` | Trường route id của bảng `sales_orders`. |
| `origin` | `VARCHAR` | - | `-` | Trường origin của bảng `sales_orders`. |
| `destination` | `VARCHAR` | - | `-` | Trường destination của bảng `sales_orders`. |
| `pickup_window_start` | `VARCHAR` | - | `-` | Trường pickup window start của bảng `sales_orders`. |
| `pickup_window_end` | `VARCHAR` | - | `-` | Trường pickup window end của bảng `sales_orders`. |
| `delivery_window_start` | `VARCHAR` | - | `-` | Trường delivery window start của bảng `sales_orders`. |
| `delivery_window_end` | `VARCHAR` | - | `-` | Trường delivery window end của bảng `sales_orders`. |
| `weight_kg` | `FLOAT` | - | `0.0` | Trường weight kg của bảng `sales_orders`. |
| `pallet_count` | `INTEGER` | - | `0` | Trường pallet count của bảng `sales_orders`. |
| `status` | `VARCHAR` | - | `Draft` | Trường status của bảng `sales_orders`. |
| `total_amount` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường total amount của bảng `sales_orders`. |
| `payment_terms` | `VARCHAR` | - | `30 Days` | Trường payment terms của bảng `sales_orders`. |
| `sales_rep` | `VARCHAR` | - | `-` | Trường sales rep của bảng `sales_orders`. |
| `packaging_spec` | `VARCHAR` | - | `Thùng Carton` | Trường packaging spec của bảng `sales_orders`. |
| `volume_m3` | `FLOAT` | - | `1.0` | Trường volume m3 của bảng `sales_orders`. |

## `settlement_payments`

Cac lan thanh toan cua mot ho so doi soat.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `settlement_payments`. |
| `settlement_id` | `VARCHAR` | Bắt buộc; FK -> `freight_settlements.id` | `-` | Trường settlement id của bảng `settlement_payments`. |
| `amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường amount của bảng `settlement_payments`. |
| `currency_code` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `-` | Trường currency code của bảng `settlement_payments`. |
| `functional_currency` | `VARCHAR(3)` | Bắt buộc; FK -> `currency_definitions.code` | `-` | Trường functional currency của bảng `settlement_payments`. |
| `exchange_rate_snapshot` | `NUMERIC(18, 8)` | Bắt buộc | `-` | Trường exchange rate snapshot của bảng `settlement_payments`. |
| `exchange_rate_date` | `DATE` | Bắt buộc | `-` | Trường exchange rate date của bảng `settlement_payments`. |
| `exchange_rate_source` | `VARCHAR(100)` | Bắt buộc | `-` | Trường exchange rate source của bảng `settlement_payments`. |
| `functional_amount` | `NUMERIC(24, 6)` | Bắt buộc | `-` | Trường functional amount của bảng `settlement_payments`. |
| `posting_date` | `DATE` | Bắt buộc | `-` | Trường posting date của bảng `settlement_payments`. |
| `payment_method` | `VARCHAR(32)` | Bắt buộc | `-` | Trường payment method của bảng `settlement_payments`. |
| `reference_no` | `VARCHAR(128)` | - | `-` | Trường reference no của bảng `settlement_payments`. |
| `status` | `VARCHAR(20)` | Bắt buộc | `posted` | Trường status của bảng `settlement_payments`. |
| `posting_reference` | `VARCHAR` | - | `-` | Trường posting reference của bảng `settlement_payments`. |
| `reversal_of_payment_id` | `VARCHAR` | Unique; FK -> `settlement_payments.id` | `-` | Trường reversal of payment id của bảng `settlement_payments`. |
| `reversed_by_payment_id` | `VARCHAR` | Unique; FK -> `settlement_payments.id` | `-` | Trường reversed by payment id của bảng `settlement_payments`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E96304ECA0>` | Trường created at của bảng `settlement_payments`. |
| `created_by` | `VARCHAR` | Bắt buộc | `-` | Trường created by của bảng `settlement_payments`. |

## `shipment_costs`

Chi phi chuyen hang cua luong nghiep vu cu.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `shipment_costs`. |
| `do_id` | `VARCHAR` | FK -> `delivery_orders.id` | `-` | Trường do id của bảng `shipment_costs`. |
| `fuel_cost` | `FLOAT` | - | `0.0` | Trường fuel cost của bảng `shipment_costs`. |
| `driver_cost` | `FLOAT` | - | `0.0` | Trường driver cost của bảng `shipment_costs`. |
| `toll_fee` | `FLOAT` | - | `0.0` | Trường toll fee của bảng `shipment_costs`. |
| `warehouse_fee` | `FLOAT` | - | `0.0` | Trường warehouse fee của bảng `shipment_costs`. |
| `total_cost` | `FLOAT` | - | `0.0` | Trường total cost của bảng `shipment_costs`. |
| `selling_price` | `FLOAT` | - | `0.0` | Trường selling price của bảng `shipment_costs`. |
| `margin_pct` | `FLOAT` | - | `15.0` | Trường margin pct của bảng `shipment_costs`. |

## `tax_codes`

Danh muc ma thue dung cho hoa don va but toan.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `tax_codes`. |
| `code` | `VARCHAR(50)` | Bắt buộc | `-` | Trường code của bảng `tax_codes`. |
| `rate` | `NUMERIC(18, 8)` | Bắt buộc | `-` | Trường rate của bảng `tax_codes`. |
| `mode` | `VARCHAR(20)` | Bắt buộc | `-` | Trường mode của bảng `tax_codes`. |
| `is_active` | `BOOLEAN` | Bắt buộc | `True` | Trường is active của bảng `tax_codes`. |
| `effective_from` | `DATE` | Bắt buộc | `-` | Trường effective from của bảng `tax_codes`. |
| `effective_to` | `DATE` | - | `-` | Trường effective to của bảng `tax_codes`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962BFAE80>` | Trường created at của bảng `tax_codes`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962BFAF20>` | Trường updated at của bảng `tax_codes`. |

Chỉ mục: `ix_tax_codes_code`.

## `tender_offers`

Bao gia cua carrier trong mot dot thau.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `tender_offers`. |
| `tender_id` | `VARCHAR` | Bắt buộc; FK -> `tenders.id` | `-` | Trường tender id của bảng `tender_offers`. |
| `carrier_id` | `VARCHAR` | Bắt buộc; FK -> `carriers.id` | `-` | Trường carrier id của bảng `tender_offers`. |
| `amount` | `NUMERIC(18, 2)` | Bắt buộc | `-` | Trường amount của bảng `tender_offers`. |
| `currency_code` | `VARCHAR` | Bắt buộc | `VND` | Trường currency code của bảng `tender_offers`. |
| `note` | `TEXT` | - | `-` | Trường note của bảng `tender_offers`. |
| `status` | `VARCHAR` | Bắt buộc | `offered` | Trường status của bảng `tender_offers`. |
| `submitted_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F35DA0>` | Trường submitted at của bảng `tender_offers`. |
| `submitted_by` | `VARCHAR` | Bắt buộc | `system` | Trường submitted by của bảng `tender_offers`. |

## `tenders`

Dot moi thau van tai.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `tenders`. |
| `freight_order_id` | `VARCHAR` | Bắt buộc; Unique; FK -> `freight_orders.id` | `-` | Trường freight order id của bảng `tenders`. |
| `response_deadline` | `DATETIME` | Bắt buộc | `-` | Trường response deadline của bảng `tenders`. |
| `status` | `VARCHAR` | Bắt buộc | `published` | Trường status của bảng `tenders`. |
| `awarded_offer_id` | `VARCHAR` | - | `-` | Trường awarded offer id của bảng `tenders`. |
| `awarded_carrier_id` | `VARCHAR` | FK -> `carriers.id` | `-` | Trường awarded carrier id của bảng `tenders`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `tenders`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F349A0>` | Trường created at của bảng `tenders`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F34A40>` | Trường updated at của bảng `tenders`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `tenders`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `system` | Trường updated by của bảng `tenders`. |

## `transport_demands`

Nhu cau van tai dau vao truoc khi tao Freight Unit/Order.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `transport_demands`. |
| `customer_id` | `VARCHAR` | Bắt buộc; FK -> `customers.id` | `-` | Trường customer id của bảng `transport_demands`. |
| `pickup_location_id` | `VARCHAR` | Bắt buộc; FK -> `locations.id` | `-` | Trường pickup location id của bảng `transport_demands`. |
| `delivery_location_id` | `VARCHAR` | Bắt buộc; FK -> `locations.id` | `-` | Trường delivery location id của bảng `transport_demands`. |
| `pickup_window_start` | `DATETIME` | Bắt buộc | `-` | Trường pickup window start của bảng `transport_demands`. |
| `pickup_window_end` | `DATETIME` | Bắt buộc | `-` | Trường pickup window end của bảng `transport_demands`. |
| `delivery_window_start` | `DATETIME` | Bắt buộc | `-` | Trường delivery window start của bảng `transport_demands`. |
| `delivery_window_end` | `DATETIME` | Bắt buộc | `-` | Trường delivery window end của bảng `transport_demands`. |
| `weight_kg` | `FLOAT` | Bắt buộc | `0` | Trường weight kg của bảng `transport_demands`. |
| `volume_m3` | `FLOAT` | Bắt buộc | `0` | Trường volume m3 của bảng `transport_demands`. |
| `pallet_count` | `INTEGER` | Bắt buộc | `0` | Trường pallet count của bảng `transport_demands`. |
| `service_requirements` | `TEXT` | - | `-` | Trường service requirements của bảng `transport_demands`. |
| `status` | `VARCHAR` | Bắt buộc | `draft` | Trường status của bảng `transport_demands`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `transport_demands`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function TransportDemand.<lambda> at 0x000001E962E9A2A0>` | Trường created at của bảng `transport_demands`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function TransportDemand.<lambda> at 0x000001E962E9A3E0>` | Trường updated at của bảng `transport_demands`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `transport_demands`. |
| `updated_by` | `VARCHAR` | Bắt buộc | `system` | Trường updated by của bảng `transport_demands`. |

## `transport_event_documents`

Chung tu dinh kem theo su kien van tai.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `transport_event_documents`. |
| `event_id` | `VARCHAR` | Bắt buộc; FK -> `transport_events.id` | `-` | Trường event id của bảng `transport_event_documents`. |
| `document_type` | `VARCHAR` | Bắt buộc | `-` | Trường document type của bảng `transport_event_documents`. |
| `storage_url` | `TEXT` | Bắt buộc | `-` | Trường storage url của bảng `transport_event_documents`. |
| `file_name` | `VARCHAR` | - | `-` | Trường file name của bảng `transport_event_documents`. |
| `mime_type` | `VARCHAR` | - | `-` | Trường mime type của bảng `transport_event_documents`. |
| `checksum` | `VARCHAR` | Bắt buộc | `-` | Trường checksum của bảng `transport_event_documents`. |
| `uploaded_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F8C720>` | Trường uploaded at của bảng `transport_event_documents`. |
| `uploaded_by` | `VARCHAR` | Bắt buộc | `-` | Trường uploaded by của bảng `transport_event_documents`. |

## `transport_events`

Su kien tracking, check-in, pickup, arrival va POD.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `transport_events`. |
| `freight_order_id` | `VARCHAR` | Bắt buộc; FK -> `freight_orders.id` | `-` | Trường freight order id của bảng `transport_events`. |
| `trip_id` | `VARCHAR(128)` | FK -> `transport_trips.id` | `-` | Trường trip id của bảng `transport_events`. |
| `leg_id` | `VARCHAR(128)` | FK -> `transport_trip_legs.id` | `-` | Trường leg id của bảng `transport_events`. |
| `event_type` | `VARCHAR` | Bắt buộc | `-` | Trường event type của bảng `transport_events`. |
| `event_time` | `DATETIME` | Bắt buộc | `-` | Trường event time của bảng `transport_events`. |
| `lat` | `FLOAT` | - | `-` | Trường lat của bảng `transport_events`. |
| `lng` | `FLOAT` | - | `-` | Trường lng của bảng `transport_events`. |
| `speed_kmh` | `FLOAT` | - | `-` | Trường speed kmh của bảng `transport_events`. |
| `distance_km` | `FLOAT` | - | `-` | Trường distance km của bảng `transport_events`. |
| `eta` | `VARCHAR` | - | `-` | Trường eta của bảng `transport_events`. |
| `location_text` | `VARCHAR` | - | `-` | Trường location text của bảng `transport_events`. |
| `source` | `VARCHAR` | Bắt buộc | `-` | Trường source của bảng `transport_events`. |
| `device_id` | `VARCHAR` | - | `-` | Trường device id của bảng `transport_events`. |
| `reason` | `TEXT` | - | `-` | Trường reason của bảng `transport_events`. |
| `note` | `TEXT` | - | `-` | Trường note của bảng `transport_events`. |
| `idempotency_key` | `VARCHAR` | Bắt buộc | `-` | Trường idempotency key của bảng `transport_events`. |
| `payload_hash` | `VARCHAR` | Bắt buộc | `-` | Trường payload hash của bảng `transport_events`. |
| `recorded_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F62E80>` | Trường recorded at của bảng `transport_events`. |
| `recorded_by` | `VARCHAR` | Bắt buộc | `-` | Trường recorded by của bảng `transport_events`. |

Chỉ mục: `ix_transport_events_order_time`.

## `transport_trip_legs`

Cac chang giao, backhaul hoac chay rong cua Trip.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(128)` | PK; Bắt buộc | `-` | Trường id của bảng `transport_trip_legs`. |
| `trip_id` | `VARCHAR(128)` | Bắt buộc; FK -> `transport_trips.id`; FK -> `trip_delivery_orders.trip_id` | `-` | Trường trip id của bảng `transport_trip_legs`. |
| `do_id` | `VARCHAR` | FK -> `trip_delivery_orders.do_id` | `-` | Trường do id của bảng `transport_trip_legs`. |
| `sequence_no` | `INTEGER` | Bắt buộc | `-` | Trường sequence no của bảng `transport_trip_legs`. |
| `leg_type` | `VARCHAR(30)` | Bắt buộc | `-` | Trường leg type của bảng `transport_trip_legs`. |
| `origin` | `VARCHAR(500)` | Bắt buộc | `-` | Trường origin của bảng `transport_trip_legs`. |
| `destination` | `VARCHAR(500)` | Bắt buộc | `-` | Trường destination của bảng `transport_trip_legs`. |
| `stop_name` | `VARCHAR(500)` | - | `-` | Trường stop name của bảng `transport_trip_legs`. |
| `receiver_name` | `VARCHAR(255)` | - | `-` | Trường receiver name của bảng `transport_trip_legs`. |
| `receiver_phone` | `VARCHAR(64)` | - | `-` | Trường receiver phone của bảng `transport_trip_legs`. |
| `delivery_note` | `TEXT` | - | `-` | Trường delivery note của bảng `transport_trip_legs`. |
| `distance_km` | `NUMERIC(18, 3)` | Bắt buộc | `0` | Trường distance km của bảng `transport_trip_legs`. |
| `avg_speed_kmh` | `NUMERIC(18, 8)` | Bắt buộc | `-` | Trường avg speed kmh của bảng `transport_trip_legs`. |
| `dwell_minutes` | `INTEGER` | Bắt buộc | `0` | Trường dwell minutes của bảng `transport_trip_legs`. |
| `planned_departure_at` | `DATETIME` | - | `-` | Trường planned departure at của bảng `transport_trip_legs`. |
| `planned_arrival_at` | `DATETIME` | - | `-` | Trường planned arrival at của bảng `transport_trip_legs`. |
| `actual_departure_at` | `DATETIME` | - | `-` | Trường actual departure at của bảng `transport_trip_legs`. |
| `actual_arrival_at` | `DATETIME` | - | `-` | Trường actual arrival at của bảng `transport_trip_legs`. |
| `status` | `VARCHAR(20)` | Bắt buộc | `planned` | Trường status của bảng `transport_trip_legs`. |
| `allocated_cost` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường allocated cost của bảng `transport_trip_legs`. |
| `allocated_revenue` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường allocated revenue của bảng `transport_trip_legs`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F060C0>` | Trường created at của bảng `transport_trip_legs`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F06160>` | Trường updated at của bảng `transport_trip_legs`. |

## `transport_trips`

Chuyen van tai thuc te lien ket DO/FO va ke hoach quay dau.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(128)` | PK; Bắt buộc | `-` | Trường id của bảng `transport_trips`. |
| `freight_order_id` | `VARCHAR` | Bắt buộc; FK -> `freight_orders.id` | `-` | Trường freight order id của bảng `transport_trips`. |
| `trip_type` | `VARCHAR(20)` | Bắt buộc | `one_way` | Trường trip type của bảng `transport_trips`. |
| `status` | `VARCHAR(20)` | Bắt buộc | `draft` | Trường status của bảng `transport_trips`. |
| `vehicle_id` | `VARCHAR` | FK -> `vehicles.id` | `-` | Trường vehicle id của bảng `transport_trips`. |
| `driver_id` | `VARCHAR` | FK -> `drivers.id` | `-` | Trường driver id của bảng `transport_trips`. |
| `co_driver_id` | `VARCHAR` | FK -> `drivers.id` | `-` | Trường co driver id của bảng `transport_trips`. |
| `planned_departure_at` | `DATETIME` | - | `-` | Trường planned departure at của bảng `transport_trips`. |
| `planned_arrival_at` | `DATETIME` | - | `-` | Trường planned arrival at của bảng `transport_trips`. |
| `planned_return_at` | `DATETIME` | - | `-` | Trường planned return at của bảng `transport_trips`. |
| `actual_departure_at` | `DATETIME` | - | `-` | Trường actual departure at của bảng `transport_trips`. |
| `actual_arrival_at` | `DATETIME` | - | `-` | Trường actual arrival at của bảng `transport_trips`. |
| `actual_return_at` | `DATETIME` | - | `-` | Trường actual return at của bảng `transport_trips`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `transport_trips`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962ED7B00>` | Trường created at của bảng `transport_trips`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962ED7BA0>` | Trường updated at của bảng `transport_trips`. |
| `created_by` | `VARCHAR(128)` | Bắt buộc | `system` | Trường created by của bảng `transport_trips`. |
| `updated_by` | `VARCHAR(128)` | Bắt buộc | `system` | Trường updated by của bảng `transport_trips`. |

Chỉ mục: `ix_transport_trips_freight_order_id`.

## `trip_delivery_orders`

Bang lien ket nhieu-nhieu giua Trip va DO.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `trip_id` | `VARCHAR(128)` | PK; Bắt buộc; FK -> `transport_trips.id` | `-` | Trường trip id của bảng `trip_delivery_orders`. |
| `do_id` | `VARCHAR` | PK; Bắt buộc; FK -> `delivery_orders.id` | `-` | Trường do id của bảng `trip_delivery_orders`. |
| `allocation_sequence` | `INTEGER` | Bắt buộc | `1` | Trường allocation sequence của bảng `trip_delivery_orders`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F053A0>` | Trường created at của bảng `trip_delivery_orders`. |
| `created_by` | `VARCHAR(128)` | Bắt buộc | `system` | Trường created by của bảng `trip_delivery_orders`. |

## `uoms`

Danh muc don vi tinh.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `uoms`. |
| `description` | `VARCHAR` | - | `-` | Trường description của bảng `uoms`. |

## `users`

Tai khoan nguoi dung he thong.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `users`. |
| `username` | `VARCHAR` | Bắt buộc | `-` | Trường username của bảng `users`. |
| `role_id` | `VARCHAR` | FK -> `roles.id` | `-` | Trường role id của bảng `users`. |

## `vehicle_maintenance_cost_lines`

Chi tiet chi phi cua tung phieu sua chua/bao duong.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `INTEGER` | PK; Bắt buộc | `-` | Trường id của bảng `vehicle_maintenance_cost_lines`. |
| `request_id` | `VARCHAR(128)` | Bắt buộc; FK -> `vehicle_maintenance_requests.id` | `-` | Trường request id của bảng `vehicle_maintenance_cost_lines`. |
| `category` | `VARCHAR(32)` | Bắt buộc | `other` | Trường category của bảng `vehicle_maintenance_cost_lines`. |
| `description` | `VARCHAR(500)` | Bắt buộc | `-` | Trường description của bảng `vehicle_maintenance_cost_lines`. |
| `quantity` | `NUMERIC(18, 4)` | Bắt buộc | `1` | Trường quantity của bảng `vehicle_maintenance_cost_lines`. |
| `unit` | `VARCHAR(32)` | Bắt buộc | `item` | Trường unit của bảng `vehicle_maintenance_cost_lines`. |
| `estimated_unit_cost` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường estimated unit cost của bảng `vehicle_maintenance_cost_lines`. |
| `estimated_total` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường estimated total của bảng `vehicle_maintenance_cost_lines`. |
| `actual_unit_cost` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường actual unit cost của bảng `vehicle_maintenance_cost_lines`. |
| `actual_total` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường actual total của bảng `vehicle_maintenance_cost_lines`. |

## `vehicle_maintenance_requests`

Phieu yeu cau sua chua, thay the va bao duong xe.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR(128)` | PK; Bắt buộc | `-` | Trường id của bảng `vehicle_maintenance_requests`. |
| `request_no` | `VARCHAR(128)` | Bắt buộc | `-` | Trường request no của bảng `vehicle_maintenance_requests`. |
| `vehicle_id` | `VARCHAR` | Bắt buộc; FK -> `vehicles.id` | `-` | Trường vehicle id của bảng `vehicle_maintenance_requests`. |
| `category` | `VARCHAR(32)` | Bắt buộc | `corrective` | Trường category của bảng `vehicle_maintenance_requests`. |
| `priority` | `VARCHAR(20)` | Bắt buộc | `normal` | Trường priority của bảng `vehicle_maintenance_requests`. |
| `planned_start` | `DATETIME` | Bắt buộc | `-` | Trường planned start của bảng `vehicle_maintenance_requests`. |
| `planned_end` | `DATETIME` | Bắt buộc | `-` | Trường planned end của bảng `vehicle_maintenance_requests`. |
| `actual_start` | `DATETIME` | - | `-` | Trường actual start của bảng `vehicle_maintenance_requests`. |
| `actual_end` | `DATETIME` | - | `-` | Trường actual end của bảng `vehicle_maintenance_requests`. |
| `description` | `TEXT` | Bắt buộc | `-` | Trường description của bảng `vehicle_maintenance_requests`. |
| `cause` | `TEXT` | - | `-` | Trường cause của bảng `vehicle_maintenance_requests`. |
| `odometer_km` | `FLOAT` | - | `-` | Trường odometer km của bảng `vehicle_maintenance_requests`. |
| `workshop` | `VARCHAR(255)` | - | `-` | Trường workshop của bảng `vehicle_maintenance_requests`. |
| `currency_code` | `VARCHAR(3)` | Bắt buộc | `VND` | Trường currency code của bảng `vehicle_maintenance_requests`. |
| `estimated_total` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường estimated total của bảng `vehicle_maintenance_requests`. |
| `actual_total` | `NUMERIC(24, 6)` | Bắt buộc | `0` | Trường actual total của bảng `vehicle_maintenance_requests`. |
| `next_maintenance_date` | `VARCHAR(10)` | - | `-` | Trường next maintenance date của bảng `vehicle_maintenance_requests`. |
| `status` | `VARCHAR(20)` | Bắt buộc | `requested` | Trường status của bảng `vehicle_maintenance_requests`. |
| `cancellation_reason` | `TEXT` | - | `-` | Trường cancellation reason của bảng `vehicle_maintenance_requests`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `vehicle_maintenance_requests`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962C268E0>` | Trường created at của bảng `vehicle_maintenance_requests`. |
| `updated_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962C26A20>` | Trường updated at của bảng `vehicle_maintenance_requests`. |
| `created_by` | `VARCHAR(128)` | Bắt buộc | `system` | Trường created by của bảng `vehicle_maintenance_requests`. |
| `updated_by` | `VARCHAR(128)` | Bắt buộc | `system` | Trường updated by của bảng `vehicle_maintenance_requests`. |
| `approved_at` | `DATETIME` | - | `-` | Trường approved at của bảng `vehicle_maintenance_requests`. |
| `approved_by` | `VARCHAR(128)` | - | `-` | Trường approved by của bảng `vehicle_maintenance_requests`. |
| `completed_at` | `DATETIME` | - | `-` | Trường completed at của bảng `vehicle_maintenance_requests`. |
| `completed_by` | `VARCHAR(128)` | - | `-` | Trường completed by của bảng `vehicle_maintenance_requests`. |

Chỉ mục: `ix_vehicle_maintenance_vehicle_period`.

## `vehicle_tracking`

Du lieu vi tri/toc do GPS cua xe.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `do_id` | `VARCHAR` | PK; Bắt buộc; FK -> `delivery_orders.id` | `-` | Trường do id của bảng `vehicle_tracking`. |
| `vehicle_id` | `VARCHAR` | FK -> `vehicles.id` | `-` | Trường vehicle id của bảng `vehicle_tracking`. |
| `lat` | `FLOAT` | - | `-` | Trường lat của bảng `vehicle_tracking`. |
| `lng` | `FLOAT` | - | `-` | Trường lng của bảng `vehicle_tracking`. |
| `speed_kmh` | `FLOAT` | - | `0.0` | Trường speed kmh của bảng `vehicle_tracking`. |
| `remaining_distance_km` | `FLOAT` | - | `0.0` | Trường remaining distance km của bảng `vehicle_tracking`. |
| `eta` | `VARCHAR` | - | `-` | Trường eta của bảng `vehicle_tracking`. |
| `planned_return_at` | `VARCHAR` | - | `-` | Trường planned return at của bảng `vehicle_tracking`. |
| `last_update` | `DATETIME` | - | `<function datetime.utcnow at 0x000001E962D3E480>` | Trường last update của bảng `vehicle_tracking`. |

## `vehicle_types`

Danh muc loai xe va gioi han tai trong, pallet, the tich.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `vehicle_types`. |
| `name` | `VARCHAR` | Bắt buộc | `-` | Trường name của bảng `vehicle_types`. |
| `icon` | `VARCHAR` | - | `🚛` | Trường icon của bảng `vehicle_types`. |
| `max_weight` | `FLOAT` | - | `0.0` | Trường max weight của bảng `vehicle_types`. |
| `volume_capacity_m3` | `FLOAT` | - | `30.0` | Trường volume capacity m3 của bảng `vehicle_types`. |
| `pallet_capacity` | `INTEGER` | - | `0` | Trường pallet capacity của bảng `vehicle_types`. |
| `fuel_norm` | `FLOAT` | - | `0.0` | Trường fuel norm của bảng `vehicle_types`. |
| `avg_speed_kmh` | `FLOAT` | - | `45.0` | Trường avg speed kmh của bảng `vehicle_types`. |
| `base_rate` | `FLOAT` | - | `0.0` | Trường base rate của bảng `vehicle_types`. |
| `maint_cost` | `FLOAT` | - | `0.0` | Trường maint cost của bảng `vehicle_types`. |
| `dims` | `VARCHAR` | - | `-` | Trường dims của bảng `vehicle_types`. |
| `fuel_type` | `VARCHAR` | - | `Diesel` | Trường fuel type của bảng `vehicle_types`. |
| `special` | `VARCHAR` | - | `-` | Trường special của bảng `vehicle_types`. |
| `notes` | `VARCHAR` | - | `-` | Trường notes của bảng `vehicle_types`. |

## `vehicles`

Ho so tung xe, thong so ky thuat va trang thai van hanh.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `vehicles`. |
| `brand` | `VARCHAR` | - | `Hyundai` | Trường brand của bảng `vehicles`. |
| `type` | `VARCHAR` | - | `-` | Trường type của bảng `vehicles`. |
| `weight_capacity` | `FLOAT` | - | `0.0` | Trường weight capacity của bảng `vehicles`. |
| `volume_capacity_m3` | `FLOAT` | - | `30.0` | Trường volume capacity m3 của bảng `vehicles`. |
| `pallet_capacity` | `INTEGER` | - | `0` | Trường pallet capacity của bảng `vehicles`. |
| `fuel_norm` | `FLOAT` | - | `0.0` | Trường fuel norm của bảng `vehicles`. |
| `min_speed_kmh` | `FLOAT` | - | `35.0` | Trường min speed kmh của bảng `vehicles`. |
| `avg_speed_kmh` | `FLOAT` | - | `45.0` | Trường avg speed kmh của bảng `vehicles`. |
| `max_speed_kmh` | `FLOAT` | - | `80.0` | Trường max speed kmh của bảng `vehicles`. |
| `maintenance_date` | `VARCHAR` | - | `-` | Trường maintenance date của bảng `vehicles`. |
| `status` | `VARCHAR` | - | `Sẵn sàng` | Trường status của bảng `vehicles`. |
| `engine_no` | `VARCHAR` | - | `-` | Trường engine no của bảng `vehicles`. |
| `chassis_no` | `VARCHAR` | - | `-` | Trường chassis no của bảng `vehicles`. |
| `insurance_date` | `VARCHAR` | - | `-` | Trường insurance date của bảng `vehicles`. |
| `inspection_date` | `VARCHAR` | - | `-` | Trường inspection date của bảng `vehicles`. |
| `inspection_place` | `VARCHAR` | - | `-` | Trường inspection place của bảng `vehicles`. |
| `inspection_exp` | `VARCHAR` | - | `-` | Trường inspection exp của bảng `vehicles`. |
| `engine_cap` | `VARCHAR` | - | `-` | Trường engine cap của bảng `vehicles`. |
| `dimensions` | `VARCHAR` | - | `-` | Trường dimensions của bảng `vehicles`. |
| `image_url` | `TEXT` | - | `-` | Trường image url của bảng `vehicles`. |

## `warehouse_appointments`

Lich hen kho cho lay/giao hang.

| Cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả kỹ thuật |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK; Bắt buộc | `-` | Trường id của bảng `warehouse_appointments`. |
| `freight_order_id` | `VARCHAR` | Bắt buộc; FK -> `freight_orders.id` | `-` | Trường freight order id của bảng `warehouse_appointments`. |
| `appointment_type` | `VARCHAR` | Bắt buộc | `-` | Trường appointment type của bảng `warehouse_appointments`. |
| `location_id` | `VARCHAR` | Bắt buộc; FK -> `locations.id` | `-` | Trường location id của bảng `warehouse_appointments`. |
| `scheduled_start` | `DATETIME` | Bắt buộc | `-` | Trường scheduled start của bảng `warehouse_appointments`. |
| `scheduled_end` | `DATETIME` | Bắt buộc | `-` | Trường scheduled end của bảng `warehouse_appointments`. |
| `status` | `VARCHAR` | Bắt buộc | `booked` | Trường status của bảng `warehouse_appointments`. |
| `version` | `INTEGER` | Bắt buộc | `1` | Trường version của bảng `warehouse_appointments`. |
| `created_at` | `DATETIME` | Bắt buộc | `<function datetime.utcnow at 0x000001E962F37CE0>` | Trường created at của bảng `warehouse_appointments`. |
| `created_by` | `VARCHAR` | Bắt buộc | `system` | Trường created by của bảng `warehouse_appointments`. |

---

Tái sinh tài liệu: `python backend/scripts/generate_system_docs.py` (chạy theo hướng dẫn trong `docs/README.md`).
