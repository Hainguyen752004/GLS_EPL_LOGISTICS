 hinh# Tài liệu API EPL Logistics

> Tài liệu này được sinh trực tiếp từ OpenAPI của FastAPI đang chạy. Swagger UI: `/docs`; OpenAPI JSON: `/openapi.json`.

Tổng số endpoint: **170**.

## Xác thực và quy ước

- API nghiệp vụ được bảo vệ bằng token cấu hình tại `EPL_TMS_API_TOKEN`; không đưa token vào URL hoặc source code.
- Gửi `Content-Type: application/json` cho request JSON.
- Thời gian dùng ISO 8601 và kèm múi giờ khi có thể.
- Lỗi nghiệp vụ trả HTTP 4xx với thông điệp `detail`; lỗi hệ thống trả HTTP 5xx.
- Không đưa `.env`, token, chữ ký hoặc POD nhạy cảm vào log/repository.

## Mục lục theo nhóm

- **API ung dung chung**: 99 endpoint.
- **Lap ke hoach va dieu phoi van tai**: 40 endpoint.
- **Chi phi, cong no va doi soat**: 26 endpoint.
- **Bao cao van tai**: 5 endpoint.

## API ung dung chung

### `GET /`

Serve Frontend

- **Operation ID:** `serve_frontend__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `string` |

### `POST /api/agent/action`

Action Agent Api

- **Operation ID:** `action_agent_api_api_agent_action_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Payload`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/agent/query`

Query Agent Api

- **Operation ID:** `query_agent_api_api_agent_query_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Payload`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/ai/checkpoint/scan`

Scan Checkpoint

- **Operation ID:** `scan_checkpoint_api_ai_checkpoint_scan_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `multipart/form-data`.
- Schema: `Body_scan_checkpoint_api_ai_checkpoint_scan_post`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `file` | `string` | Có | `-` | File |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/cost-formulas`

List Cost Formulas

- **Operation ID:** `list_cost_formulas_api_cost_formulas_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/cost-formulas`

Save Cost Formula

- **Operation ID:** `save_cost_formula_api_cost_formulas_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/currencies`

List Currencies

- **Operation ID:** `list_currencies_api_currencies_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/currencies`

Save Currency Rates

- **Operation ID:** `save_currency_rates_api_currencies_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/currencies/history`

List Currency History

- **Operation ID:** `list_currency_history_api_currencies_history_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/currencies/reference-rates`

Doc/tra cuu currencies/reference rates.

- **Operation ID:** `get_currency_reference_rates_api_currencies_reference_rates_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/currencies/reference-rates/refresh`

Refresh Currency Reference Rates

- **Operation ID:** `refresh_currency_reference_rates_api_currencies_reference_rates_refresh_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/customers`

List Customers

- **Operation ID:** `list_customers_api_customers_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/customers`

Create Customer

- **Operation ID:** `create_customer_api_customers_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/customers/{customer_id}`

Update Customer

- **Operation ID:** `update_customer_api_customers__customer_id__put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `customer_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/customers/{customer_id}`

Xoa/huy customers/{customer id}.

- **Operation ID:** `delete_customer_api_customers__customer_id__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `customer_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/dashboard/stats`

Doc/tra cuu dashboard/stats.

- **Operation ID:** `get_dashboard_stats_api_dashboard_stats_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/data/all`

Doc/tra cuu data/all.

- **Operation ID:** `get_all_data_api_data_all_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/delivery-orders`

List Delivery Orders

- **Operation ID:** `list_delivery_orders_api_delivery_orders_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `page` | `query` | Không | `integer` | Tham số nghiệp vụ. |
| `page_size` | `query` | Không | `integer` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/delivery-orders`

Create Delivery Order

- **Operation ID:** `create_delivery_order_api_delivery_orders_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `DeliveryOrderCreateRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `id` | `string | null` | Không | `-` | Id |
| `so_id` | `string` | Có | `-` | So Id |
| `route_id` | `string | null` | Không | `-` | Route Id |
| `origin` | `string | null` | Không | `-` | Origin |
| `destination` | `string | null` | Không | `-` | Destination |
| `pickup_window_start` | `string | null` | Không | `-` | Pickup Window Start |
| `pickup_window_end` | `string | null` | Không | `-` | Pickup Window End |
| `delivery_window_start` | `string | null` | Không | `-` | Delivery Window Start |
| `delivery_window_end` | `string | null` | Không | `-` | Delivery Window End |
| `pickup_date` | `string | null` | Không | `-` | Pickup Date |
| `delivery_date` | `string | null` | Không | `-` | Delivery Date |
| `weight_kg` | `integer | number | null` | Không | `-` | Weight Kg |
| `pallet_count` | `integer | null` | Không | `-` | Pallet Count |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/delivery-orders/analysis`

Analyze Delivery Orders

- **Operation ID:** `analyze_delivery_orders_api_delivery_orders_analysis_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/delivery-orders/{delivery_order_id}/dossier`

Doc/tra cuu delivery orders/{delivery order id}/dossier.

- **Operation ID:** `get_delivery_order_dossier_api_delivery_orders__delivery_order_id__dossier_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `delivery_order_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/delivery-orders/{do_id}`

Update Delivery Order

- **Operation ID:** `update_delivery_order_api_delivery_orders__do_id__put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `DeliveryOrderUpdateRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `route_id` | `string | null` | Không | `-` | Route Id |
| `origin` | `string | null` | Không | `-` | Origin |
| `destination` | `string | null` | Không | `-` | Destination |
| `pickup_window_start` | `string | null` | Không | `-` | Pickup Window Start |
| `pickup_window_end` | `string | null` | Không | `-` | Pickup Window End |
| `delivery_window_start` | `string | null` | Không | `-` | Delivery Window Start |
| `delivery_window_end` | `string | null` | Không | `-` | Delivery Window End |
| `pickup_date` | `string | null` | Không | `-` | Pickup Date |
| `delivery_date` | `string | null` | Không | `-` | Delivery Date |
| `weight_kg` | `integer | number | null` | Không | `-` | Weight Kg |
| `pallet_count` | `integer | null` | Không | `-` | Pallet Count |
| `packaging_spec` | `string | null` | Không | `-` | Packaging Spec |
| `volume_m3` | `integer | number | null` | Không | `-` | Volume M3 |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/delivery-orders/{do_id}`

Xoa/huy delivery orders/{do id}.

- **Operation ID:** `delete_delivery_order_api_delivery_orders__do_id__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/delivery-orders/{do_id}/closeout`

Doc/tra cuu delivery orders/{do id}/closeout.

- **Operation ID:** `get_delivery_order_closeout_api_delivery_orders__do_id__closeout_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/delivery-orders/{do_id}/complete-delivery`

Complete Delivery Order

- **Operation ID:** `complete_delivery_order_api_delivery_orders__do_id__complete_delivery_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/delivery-orders/{do_id}/dispatch`

Dispatch Delivery Order

- **Operation ID:** `dispatch_delivery_order_api_delivery_orders__do_id__dispatch_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `DeliveryOrderDispatchRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `vehicle_id` | `string` | Có | `-` | Vehicle Id |
| `driver_id` | `string` | Có | `-` | Driver Id |
| `co_driver_id` | `string | null` | Không | `-` | Co Driver Id |
| `packaging_spec` | `string | null` | Không | `-` | Packaging Spec |
| `volume_m3` | `integer | number | null` | Không | `-` | Volume M3 |
| `departure_at` | `string | null` | Không | `-` | Departure At |
| `planned_departure_at` | `string | null` | Không | `-` | Planned Departure At |
| `avg_speed_kmh` | `integer | number | null` | Không | `-` | Avg Speed Kmh |
| `max_speed_kmh` | `integer | number | null` | Không | `-` | Max Speed Kmh |
| `return_speed_kmh` | `integer | number | null` | Không | `-` | Return Speed Kmh |
| `return_distance_km` | `integer | number | null` | Không | `-` | Return Distance Km |
| `load_minutes` | `integer | null` | Không | `-` | Load Minutes |
| `unload_minutes` | `integer | null` | Không | `-` | Unload Minutes |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/delivery-orders/{do_id}/status`

Update Delivery Order Status

- **Operation ID:** `update_delivery_order_status_api_delivery_orders__do_id__status_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `DeliveryOrderStatusRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `status` | `string` | Có | `-` | Status |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/drivers`

List Drivers

- **Operation ID:** `list_drivers_api_drivers_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/drivers`

Create Driver

- **Operation ID:** `create_driver_api_drivers_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/drivers/{did}`

Xoa/huy drivers/{did}.

- **Operation ID:** `delete_driver_api_drivers__did__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `did` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/gl-transactions`

List Gl Transactions

- **Operation ID:** `list_gl_transactions_api_gl_transactions_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/health`

Health

- **Operation ID:** `health_api_health_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/health/database`

Database Health

- **Operation ID:** `database_health_api_health_database_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/incidents`

List Incidents

- **Operation ID:** `list_incidents_api_incidents_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/incidents`

Create Incident

- **Operation ID:** `create_incident_api_incidents_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/invoices`

List Invoices

- **Operation ID:** `list_invoices_api_invoices_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/invoices/post`

Tao moi hoac thuc hien hanh dong tren invoices/post.

- **Operation ID:** `post_invoice_and_gl_api_invoices_post_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `ARInvoicePostRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `id` | `string | null` | Không | `-` | Id |
| `do_id` | `string` | Có | `-` | Do Id |
| `posted_at` | `string | null` | Không | `-` | Posted At |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/master-data/account-mappings`

Save Account Mapping

- **Operation ID:** `save_account_mapping_api_master_data_account_mappings_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/master-data/account-mappings/{mapping_key}`

Update Account Mapping

- **Operation ID:** `update_account_mapping_api_master_data_account_mappings__mapping_key__put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `mapping_key` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/master-data/account-mappings/{mapping_key}`

Xoa/huy master data/account mappings/{mapping key}.

- **Operation ID:** `delete_account_mapping_api_master_data_account_mappings__mapping_key__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `mapping_key` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/master-data/account-mappings/{mapping_key}/status`

Set Account Mapping Status

- **Operation ID:** `set_account_mapping_status_api_master_data_account_mappings__mapping_key__status_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `mapping_key` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Không.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/master-data/accounting-periods`

Save Accounting Period

- **Operation ID:** `save_accounting_period_api_master_data_accounting_periods_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/master-data/accounting-periods/{period_id}`

Update Accounting Period

- **Operation ID:** `update_accounting_period_api_master_data_accounting_periods__period_id__put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `period_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/master-data/accounting-periods/{period_id}`

Xoa/huy master data/accounting periods/{period id}.

- **Operation ID:** `delete_accounting_period_api_master_data_accounting_periods__period_id__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `period_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/master-data/accounting-periods/{period_id}/status`

Set Accounting Period Status

- **Operation ID:** `set_accounting_period_status_api_master_data_accounting_periods__period_id__status_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `period_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Không.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/master-data/tax-codes`

Save Tax Code

- **Operation ID:** `save_tax_code_api_master_data_tax_codes_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/master-data/tax-codes/{code}`

Update Tax Code

- **Operation ID:** `update_tax_code_api_master_data_tax_codes__code__put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `code` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/master-data/tax-codes/{code}`

Xoa/huy master data/tax codes/{code}.

- **Operation ID:** `delete_tax_code_api_master_data_tax_codes__code__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `code` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/master-data/tax-codes/{code}/status`

Set Tax Code Status

- **Operation ID:** `set_tax_code_status_api_master_data_tax_codes__code__status_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `code` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Không.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/parking-labels/{label_id}/qr.svg`

Parking Qr Svg

- **Operation ID:** `parking_qr_svg_api_parking_labels__label_id__qr_svg_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `label_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/parking-lists`

List Parking Lists

- **Operation ID:** `list_parking_lists_api_parking_lists_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `q` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `status` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `page` | `query` | Không | `integer` | Tham số nghiệp vụ. |
| `page_size` | `query` | Không | `integer` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/parking-lists/auto-from-do/{do_id}`

Auto Create From Do

- **Operation ID:** `auto_create_from_do_api_parking_lists_auto_from_do__do_id__post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `ParkingListAutoCreateRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `list_count` | `integer` | Không | `1` | List Count |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/parking-lists/from-do/{do_id}`

Create From Do

- **Operation ID:** `create_from_do_api_parking_lists_from_do__do_id__post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `ParkingListCreateRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `store_id` | `string | null` | Không | `-` | Store Id |
| `store_name` | `string | null` | Không | `-` | Store Name |
| `wave` | `string | null` | Không | `-` | Wave |
| `gate` | `string | null` | Không | `-` | Gate |
| `box_count` | `integer` | Không | `1` | Box Count |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/parking-lists/{parking_id}`

Doc/tra cuu parking lists/{parking id}.

- **Operation ID:** `get_parking_list_api_parking_lists__parking_id__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `parking_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/parking-lists/{parking_id}/label`

Doc/tra cuu parking lists/{parking id}/label.

- **Operation ID:** `get_label_data_api_parking_lists__parking_id__label_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `parking_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/parking-lists/{parking_id}/packing-list`

Doc/tra cuu parking lists/{parking id}/packing list.

- **Operation ID:** `get_packing_list_data_api_parking_lists__parking_id__packing_list_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `parking_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/parking-lists/{parking_id}/print`

Record Print

- **Operation ID:** `record_print_api_parking_lists__parking_id__print_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `parking_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `ParkingListPrintRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `document_type` | `labels | packing_list` | Có | `-` | Document Type |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/parking-lists/{parking_id}/status`

Update Status

- **Operation ID:** `update_status_api_parking_lists__parking_id__status_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `parking_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `ParkingListStatusRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `status` | `string` | Có | `-` | Status |
| `note` | `string | null` | Không | `-` | Note |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/parking-qr/{token}`

Scan Parking Qr

- **Operation ID:** `scan_parking_qr_api_parking_qr__token__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `token` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/parking-qr/{token}/scan`

Record Parking Qr Scan

- **Operation ID:** `record_parking_qr_scan_api_parking_qr__token__scan_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `token` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `ParkingQrScanRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `action` | `yard_arrival | gate_entry | load_package` | Có | `-` | Action |
| `note` | `string | null` | Không | `-` | Note |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/pod-documents/{document_id}`

Download Pod Document

- **Operation ID:** `download_pod_document_api_pod_documents__document_id__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `document_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/pod/{do_id}`

Doc/tra cuu pod/{do id}.

- **Operation ID:** `get_pod_api_pod__do_id__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/pod/{do_id}`

Save Pod

- **Operation ID:** `save_pod_api_pod__do_id__post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `DeliveryPODRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `trip_id` | `string` | Có | `-` | Trip Id |
| `leg_id` | `string` | Có | `-` | Leg Id |
| `vehicle_id` | `string` | Có | `-` | Vehicle Id |
| `stop_no` | `integer` | Có | `-` | Stop No |
| `delivery_time` | `string` | Có | `-` | Delivery Time |
| `location_text` | `string` | Không | `` | Location Text |
| `receiver_name` | `string` | Không | `` | Receiver Name |
| `receiver_phone` | `string` | Không | `` | Receiver Phone |
| `photo_url` | `string` | Không | `` | Photo Url |
| `signature_url` | `string` | Không | `` | Signature Url |
| `note` | `string` | Không | `` | Note |
| `status` | `completed | rejected` | Không | `completed` | Status |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/quotations`

List Quotations

- **Operation ID:** `list_quotations_api_quotations_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `page` | `query` | Không | `integer` | Tham số nghiệp vụ. |
| `page_size` | `query` | Không | `integer` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/quotations`

Create Quotation

- **Operation ID:** `create_quotation_api_quotations_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `QuotationCreateRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `id` | `string | null` | Không | `-` | Id |
| `customer_id` | `string` | Có | `-` | Customer Id |
| `route_id` | `string` | Có | `-` | Route Id |
| `origin` | `string | null` | Không | `-` | Origin |
| `destination` | `string | null` | Không | `-` | Destination |
| `pickup_window_start` | `string | null` | Không | `-` | Pickup Window Start |
| `pickup_window_end` | `string | null` | Không | `-` | Pickup Window End |
| `delivery_window_start` | `string | null` | Không | `-` | Delivery Window Start |
| `delivery_window_end` | `string | null` | Không | `-` | Delivery Window End |
| `weight_kg` | `integer | number | null` | Không | `-` | Weight Kg |
| `pallet_count` | `integer | null` | Không | `-` | Pallet Count |
| `cargo_type` | `string | null` | Không | `-` | Cargo Type |
| `valid_to` | `string | null` | Không | `-` | Valid To |
| `fuel_cost` | `integer | number | null` | Không | `-` | Fuel Cost |
| `driver_cost` | `integer | number | null` | Không | `-` | Driver Cost |
| `toll_fee` | `integer | number | null` | Không | `-` | Toll Fee |
| `total_cost` | `integer | number | null` | Không | `-` | Total Cost |
| `selling_price` | `integer | number | null` | Không | `-` | Selling Price |
| `packaging_spec` | `string | null` | Không | `-` | Packaging Spec |
| `volume_m3` | `integer | number | null` | Không | `-` | Volume M3 |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/quotations/{qid}`

Update Quotation

- **Operation ID:** `update_quotation_api_quotations__qid__put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `qid` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `QuotationUpdateRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `id` | `string | null` | Không | `-` | Id |
| `customer_id` | `string | null` | Không | `-` | Customer Id |
| `route_id` | `string | null` | Không | `-` | Route Id |
| `origin` | `string | null` | Không | `-` | Origin |
| `destination` | `string | null` | Không | `-` | Destination |
| `pickup_window_start` | `string | null` | Không | `-` | Pickup Window Start |
| `pickup_window_end` | `string | null` | Không | `-` | Pickup Window End |
| `delivery_window_start` | `string | null` | Không | `-` | Delivery Window Start |
| `delivery_window_end` | `string | null` | Không | `-` | Delivery Window End |
| `weight_kg` | `integer | number | null` | Không | `-` | Weight Kg |
| `pallet_count` | `integer | null` | Không | `-` | Pallet Count |
| `cargo_type` | `string | null` | Không | `-` | Cargo Type |
| `valid_to` | `string | null` | Không | `-` | Valid To |
| `fuel_cost` | `integer | number | null` | Không | `-` | Fuel Cost |
| `driver_cost` | `integer | number | null` | Không | `-` | Driver Cost |
| `toll_fee` | `integer | number | null` | Không | `-` | Toll Fee |
| `total_cost` | `integer | number | null` | Không | `-` | Total Cost |
| `selling_price` | `integer | number | null` | Không | `-` | Selling Price |
| `packaging_spec` | `string | null` | Không | `-` | Packaging Spec |
| `volume_m3` | `integer | number | null` | Không | `-` | Volume M3 |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/quotations/{qid}`

Xoa/huy quotations/{qid}.

- **Operation ID:** `delete_quotation_api_quotations__qid__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `qid` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/quotations/{qid}/approve`

Approve Quotation

- **Operation ID:** `approve_quotation_api_quotations__qid__approve_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `qid` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/quotations/{qid}/status`

Quotation Status Compat

- **Operation ID:** `quotation_status_compat_api_quotations__qid__status_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `qid` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `WorkflowStatusRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `status` | `string` | Có | `-` | Status |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/routes`

List Routes

- **Operation ID:** `list_routes_api_routes_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `paginated` | `query` | Không | `boolean` | Tham số nghiệp vụ. |
| `page` | `query` | Không | `integer` | Tham số nghiệp vụ. |
| `page_size` | `query` | Không | `integer` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/routes`

Create Route

- **Operation ID:** `create_route_api_routes_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `RouteCreateRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `id` | `string | null` | Không | `-` | Id |
| `name` | `string | null` | Không | `-` | Name |
| `distance_km` | `integer | number | null` | Không | `-` | Distance Km |
| `segments_json` | `string | null` | Không | `-` | Segments Json |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/routes/{route_id}`

Xoa/huy routes/{route id}.

- **Operation ID:** `delete_route_api_routes__route_id__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `route_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/sales-orders`

List Sales Orders

- **Operation ID:** `list_sales_orders_api_sales_orders_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `page` | `query` | Không | `integer` | Tham số nghiệp vụ. |
| `page_size` | `query` | Không | `integer` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/sales-orders`

Create Sales Order

- **Operation ID:** `create_sales_order_api_sales_orders_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `SalesOrderCreateRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `id` | `string | null` | Không | `-` | Id |
| `quotation_id` | `string` | Có | `-` | Quotation Id |
| `route_id` | `string | null` | Không | `-` | Route Id |
| `origin` | `string | null` | Không | `-` | Origin |
| `destination` | `string | null` | Không | `-` | Destination |
| `pickup_window_start` | `string | null` | Không | `-` | Pickup Window Start |
| `pickup_window_end` | `string | null` | Không | `-` | Pickup Window End |
| `delivery_window_start` | `string | null` | Không | `-` | Delivery Window Start |
| `delivery_window_end` | `string | null` | Không | `-` | Delivery Window End |
| `weight_kg` | `integer | number | null` | Không | `-` | Weight Kg |
| `pallet_count` | `integer | null` | Không | `-` | Pallet Count |
| `total_amount` | `integer | number | null` | Không | `-` | Total Amount |
| `order_date` | `string | null` | Không | `-` | Order Date |
| `currency_code` | `string | null` | Không | `-` | Currency Code |
| `packaging_spec` | `string | null` | Không | `-` | Packaging Spec |
| `volume_m3` | `integer | number | null` | Không | `-` | Volume M3 |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/sales-orders/{so_id}`

Update Sales Order

- **Operation ID:** `update_sales_order_api_sales_orders__so_id__put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `so_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `SalesOrderUpdateRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `route_id` | `string | null` | Không | `-` | Route Id |
| `origin` | `string | null` | Không | `-` | Origin |
| `destination` | `string | null` | Không | `-` | Destination |
| `pickup_window_start` | `string | null` | Không | `-` | Pickup Window Start |
| `pickup_window_end` | `string | null` | Không | `-` | Pickup Window End |
| `delivery_window_start` | `string | null` | Không | `-` | Delivery Window Start |
| `delivery_window_end` | `string | null` | Không | `-` | Delivery Window End |
| `weight_kg` | `integer | number | null` | Không | `-` | Weight Kg |
| `pallet_count` | `integer | null` | Không | `-` | Pallet Count |
| `total_amount` | `integer | number | null` | Không | `-` | Total Amount |
| `currency_code` | `string | null` | Không | `-` | Currency Code |
| `packaging_spec` | `string | null` | Không | `-` | Packaging Spec |
| `volume_m3` | `integer | number | null` | Không | `-` | Volume M3 |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/sales-orders/{so_id}`

Xoa/huy sales orders/{so id}.

- **Operation ID:** `delete_sales_order_api_sales_orders__so_id__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `so_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/sales-orders/{so_id}/confirm`

Confirm Sales Order

- **Operation ID:** `confirm_sales_order_api_sales_orders__so_id__confirm_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `so_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/sales-orders/{so_id}/status`

Sales Order Status Compat

- **Operation ID:** `sales_order_status_compat_api_sales_orders__so_id__status_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `so_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `WorkflowStatusRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `status` | `string` | Có | `-` | Status |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tracking/{do_id}`

Doc/tra cuu tracking/{do id}.

- **Operation ID:** `get_tracking_api_tracking__do_id__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `do_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/uploads/images`

Upload Master Data Image

- **Operation ID:** `upload_master_data_image_api_uploads_images_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `multipart/form-data`.
- Schema: `Body_upload_master_data_image_api_uploads_images_post`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `entity_type` | `string` | Có | `-` | Entity Type |
| `file` | `string` | Có | `-` | File |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `201` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/v1/ai/chat`

Gateway Chat

- **Operation ID:** `gateway_chat_api_v1_ai_chat_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Payload`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/vehicle-maintenance-requests/{request_id}/approve`

Approve Vehicle Maintenance Request

- **Operation ID:** `approve_vehicle_maintenance_request_api_vehicle_maintenance_requests__request_id__approve_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `request_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/vehicle-maintenance-requests/{request_id}/cancel`

Cancel Vehicle Maintenance Request

- **Operation ID:** `cancel_vehicle_maintenance_request_api_vehicle_maintenance_requests__request_id__cancel_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `request_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/vehicle-maintenance-requests/{request_id}/complete`

Complete Vehicle Maintenance Request

- **Operation ID:** `complete_vehicle_maintenance_request_api_vehicle_maintenance_requests__request_id__complete_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `request_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/vehicle-maintenance-requests/{request_id}/start`

Start Vehicle Maintenance Request

- **Operation ID:** `start_vehicle_maintenance_request_api_vehicle_maintenance_requests__request_id__start_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `request_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/vehicle-types`

List Vehicle Types

- **Operation ID:** `list_vehicle_types_api_vehicle_types_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/vehicle-types`

Save Vehicle Type

- **Operation ID:** `save_vehicle_type_api_vehicle_types_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/vehicle-types/recommendations`

Doc/tra cuu vehicle types/recommendations.

- **Operation ID:** `get_vehicle_type_recommendations_api_vehicle_types_recommendations_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `weight_kg` | `query` | Không | `number` | Tham số nghiệp vụ. |
| `volume_m3` | `query` | Không | `number` | Tham số nghiệp vụ. |
| `pallet_count` | `query` | Không | `integer` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/vehicle-types/{vid}`

Xoa/huy vehicle types/{vid}.

- **Operation ID:** `delete_vehicle_type_api_vehicle_types__vid__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `vid` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/vehicles`

List Vehicles

- **Operation ID:** `list_vehicles_api_vehicles_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `paginated` | `query` | Không | `boolean` | Tham số nghiệp vụ. |
| `page` | `query` | Không | `integer` | Tham số nghiệp vụ. |
| `page_size` | `query` | Không | `integer` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/vehicles`

Create Vehicle

- **Operation ID:** `create_vehicle_api_vehicles_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/vehicles/{vehicle_id}/maintenance-requests`

Doc/tra cuu vehicles/{vehicle id}/maintenance requests.

- **Operation ID:** `get_vehicle_maintenance_requests_api_vehicles__vehicle_id__maintenance_requests_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `vehicle_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/vehicles/{vehicle_id}/maintenance-requests`

Tao moi hoac thuc hien hanh dong tren vehicles/{vehicle id}/maintenance requests.

- **Operation ID:** `post_vehicle_maintenance_request_api_vehicles__vehicle_id__maintenance_requests_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `vehicle_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `201` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/vehicles/{vid}`

Xoa/huy vehicles/{vid}.

- **Operation ID:** `delete_vehicle_api_vehicles__vid__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `vid` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /favicon.ico`

Serve Favicon

- **Operation ID:** `serve_favicon_favicon_ico_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /kich-ban-test`

Serve Test Runner Vietnamese Alias

- **Operation ID:** `serve_test_runner_vietnamese_alias_kich_ban_test_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `string` |

### `GET /test-runner`

Serve Test Runner

- **Operation ID:** `serve_test_runner_test_runner_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `string` |

### `GET /tongquan.jpg`

Serve Overview Image

- **Operation ID:** `serve_overview_image_tongquan_jpg_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /uploads/{asset_path}`

Doc/tra cuu uploads/{asset path}.

- **Operation ID:** `get_uploaded_asset_uploads__asset_path__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `asset_path` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |


## Lap ke hoach va dieu phoi van tai

### `GET /api/tms/carriers`

List Carriers

- **Operation ID:** `list_carriers_api_tms_carriers_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/tms/carriers`

Create Carrier

- **Operation ID:** `create_carrier_api_tms_carriers_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/tms/carriers/{carrier_id}`

Update Carrier

- **Operation ID:** `update_carrier_api_tms_carriers__carrier_id__put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `carrier_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/tms/carriers/{carrier_id}`

Xoa/huy tms/carriers/{carrier id}.

- **Operation ID:** `delete_carrier_api_tms_carriers__carrier_id__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `carrier_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/carriers/{carrier_id}/status`

Set Carrier Status

- **Operation ID:** `set_carrier_status_api_tms_carriers__carrier_id__status_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `carrier_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Không.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/demands`

List Demands

- **Operation ID:** `list_demands_api_tms_demands_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/tms/demands`

Create Demand

- **Operation ID:** `create_demand_api_tms_demands_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/tms/demands/{demand_id}/submit`

Submit Demand

- **Operation ID:** `submit_demand_api_tms_demands__demand_id__submit_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `demand_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/driver-qualifications`

List Driver Qualifications

- **Operation ID:** `list_driver_qualifications_api_tms_driver_qualifications_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/tms/driver-qualifications`

Save Driver Qualification

- **Operation ID:** `save_driver_qualification_api_tms_driver_qualifications_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/freight-orders`

List Freight Orders

- **Operation ID:** `list_freight_orders_api_tms_freight_orders_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/tms/freight-orders`

Create Freight Order

- **Operation ID:** `create_freight_order_api_tms_freight_orders_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/tms/freight-orders/{order_id}/dispatch`

Dispatch Freight Order

- **Operation ID:** `dispatch_freight_order_api_tms_freight_orders__order_id__dispatch_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `order_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/freight-orders/{order_id}/events`

List Transport Events

- **Operation ID:** `list_transport_events_api_tms_freight_orders__order_id__events_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `order_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/freight-orders/{order_id}/events`

Record Transport Event

- **Operation ID:** `record_transport_event_api_tms_freight_orders__order_id__events_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `order_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/freight-orders/{order_id}/latest-position`

Doc/tra cuu tms/freight orders/{order id}/latest position.

- **Operation ID:** `get_latest_transport_position_api_tms_freight_orders__order_id__latest_position_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `order_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/freight-orders/{order_id}/legacy-link`

Link Legacy Delivery Order

- **Operation ID:** `link_legacy_delivery_order_api_tms_freight_orders__order_id__legacy_link_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `order_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/freight-units`

List Freight Units

- **Operation ID:** `list_freight_units_api_tms_freight_units_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/tms/freight-units/from-demand/{demand_id}`

Create Freight Unit

- **Operation ID:** `create_freight_unit_api_tms_freight_units_from_demand__demand_id__post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `demand_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/resource-assignments`

List Resource Assignments

- **Operation ID:** `list_resource_assignments_api_tms_resource_assignments_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/tms/scheduling/driver-shifts`

List Driver Shifts

- **Operation ID:** `list_driver_shifts_api_tms_scheduling_driver_shifts_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `start` | `query` | Có | `string` | Tham số nghiệp vụ. |
| `end` | `query` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/scheduling/driver-shifts`

Create Driver Shift

- **Operation ID:** `create_driver_shift_api_tms_scheduling_driver_shifts_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/scheduling/driver-shifts/weekly-schedule`

Create Weekly Driver Schedule

- **Operation ID:** `create_weekly_driver_schedule_api_tms_scheduling_driver_shifts_weekly_schedule_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/tms/scheduling/driver-shifts/{shift_id}`

Update Driver Shift

- **Operation ID:** `update_driver_shift_api_tms_scheduling_driver_shifts__shift_id__put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `shift_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/tms/scheduling/driver-shifts/{shift_id}`

Xoa/huy tms/scheduling/driver shifts/{shift id}.

- **Operation ID:** `delete_driver_shift_api_tms_scheduling_driver_shifts__shift_id__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `shift_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/scheduling/vehicle-availability`

Vehicle Availability

- **Operation ID:** `vehicle_availability_api_tms_scheduling_vehicle_availability_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `start` | `query` | Có | `string` | Tham số nghiệp vụ. |
| `end` | `query` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/tenders`

List Tenders

- **Operation ID:** `list_tenders_api_tms_tenders_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/tms/tenders`

Publish Tender

- **Operation ID:** `publish_tender_api_tms_tenders_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/tms/tenders/{tender_id}/award`

Award Tender

- **Operation ID:** `award_tender_api_tms_tenders__tender_id__award_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `tender_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/tenders/{tender_id}/offers`

List Tender Offers

- **Operation ID:** `list_tender_offers_api_tms_tenders__tender_id__offers_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `tender_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/tenders/{tender_id}/offers`

Submit Tender Offer

- **Operation ID:** `submit_tender_offer_api_tms_tenders__tender_id__offers_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `tender_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/trips`

List Trips

- **Operation ID:** `list_trips_api_tms_trips_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `status` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `freight_order_id` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `page` | `query` | Không | `integer` | Tham số nghiệp vụ. |
| `page_size` | `query` | Không | `integer` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/trips`

Create Trip

- **Operation ID:** `create_trip_api_tms_trips_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `TripCreateRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `id` | `string` | Có | `-` | Id |
| `freight_order_id` | `string` | Có | `-` | Freight Order Id |
| `trip_type` | `one_way | round_trip | backhaul | multi_stop` | Có | `-` | Trip Type |
| `do_ids` | `array<string>` | Có | `-` | Do Ids |
| `vehicle_id` | `string | null` | Không | `-` | Vehicle Id |
| `driver_id` | `string | null` | Không | `-` | Driver Id |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/trips/from-delivery-orders`

Create Trip From Delivery Orders

- **Operation ID:** `create_trip_from_delivery_orders_api_tms_trips_from_delivery_orders_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `TripFromDeliveryOrdersRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `id` | `string` | Có | `-` | Id |
| `do_ids` | `array<string>` | Có | `-` | Do Ids |
| `trip_type` | `one_way | round_trip | backhaul | multi_stop` | Không | `one_way` | Trip Type |
| `planned_departure_at` | `string` | Có | `-` | Planned Departure At |
| `avg_speed_kmh` | `number | string` | Có | `-` | Avg Speed Kmh |
| `dwell_minutes` | `integer` | Không | `0` | Dwell Minutes |
| `stop_plan` | `array<object>` | Không | `-` | Stop Plan |
| `return_purpose` | `none | empty_return | backhaul | returned_goods` | Không | `none` | Return Purpose |
| `return_route_id` | `string | null` | Không | `-` | Return Route Id |
| `return_do_id` | `string | null` | Không | `-` | Return Do Id |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/trips/{trip_id}`

Doc/tra cuu tms/trips/{trip id}.

- **Operation ID:** `get_trip_api_tms_trips__trip_id__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `trip_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/trips/{trip_id}/complete-return`

Complete Trip Return

- **Operation ID:** `complete_trip_return_api_tms_trips__trip_id__complete_return_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `trip_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/tms/trips/{trip_id}/dispatch`

Dispatch Trip

- **Operation ID:** `dispatch_trip_api_tms_trips__trip_id__dispatch_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `trip_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `TripDispatchRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `vehicle_id` | `string` | Có | `-` | Vehicle Id |
| `driver_id` | `string` | Có | `-` | Driver Id |
| `co_driver_id` | `string | null` | Không | `-` | Co Driver Id |
| `expected_version` | `integer` | Có | `-` | Expected Version |
| `assignment_start` | `string` | Có | `-` | Assignment Start |
| `assignment_end` | `string` | Có | `-` | Assignment End |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/trips/{trip_id}/legs`

Add Trip Leg

- **Operation ID:** `add_trip_leg_api_tms_trips__trip_id__legs_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `trip_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/warehouse-appointments`

List Warehouse Appointments

- **Operation ID:** `list_warehouse_appointments_api_tms_warehouse_appointments_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/tms/warehouse-appointments`

Book Warehouse Appointment

- **Operation ID:** `book_warehouse_appointment_api_tms_warehouse_appointments_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |


## Chi phi, cong no va doi soat

### `GET /api/tms/finance/ap-invoices`

List Ap Invoices

- **Operation ID:** `list_ap_invoices_api_tms_finance_ap_invoices_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/tms/finance/ap-invoices/{ap_id}`

Doc/tra cuu tms/finance/ap invoices/{ap id}.

- **Operation ID:** `get_ap_invoice_api_tms_finance_ap_invoices__ap_id__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `ap_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/ap-invoices/{ap_id}/approve`

Approve Ap

- **Operation ID:** `approve_ap_api_tms_finance_ap_invoices__ap_id__approve_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `ap_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/ap-invoices/{ap_id}/post`

Tao moi hoac thuc hien hanh dong tren tms/finance/ap invoices/{ap id}/post.

- **Operation ID:** `post_ap_api_tms_finance_ap_invoices__ap_id__post_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `ap_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/ap-invoices/{ap_id}/reverse`

Reverse Ap

- **Operation ID:** `reverse_ap_api_tms_finance_ap_invoices__ap_id__reverse_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `ap_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/ap-invoices/{ap_id}/settlements`

Create Settlement

- **Operation ID:** `create_settlement_api_tms_finance_ap_invoices__ap_id__settlements_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `ap_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Không.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/ap-invoices/{ap_id}/submit`

Submit Ap

- **Operation ID:** `submit_ap_api_tms_finance_ap_invoices__ap_id__submit_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `ap_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/finance/costs`

List Costs

- **Operation ID:** `list_costs_api_tms_finance_costs_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/tms/finance/costs/{cost_id}`

Doc/tra cuu tms/finance/costs/{cost id}.

- **Operation ID:** `get_cost_api_tms_finance_costs__cost_id__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `cost_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/costs/{cost_id}/ap-invoices`

Create Ap

- **Operation ID:** `create_ap_api_tms_finance_costs__cost_id__ap_invoices_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `cost_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/costs/{cost_id}/approve`

Approve Cost

- **Operation ID:** `approve_cost_api_tms_finance_costs__cost_id__approve_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `cost_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/costs/{cost_id}/documents`

Save Cost Document

- **Operation ID:** `save_cost_document_api_tms_finance_costs__cost_id__documents_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `cost_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/tms/finance/costs/{cost_id}/documents/{document_id}`

Update Cost Document

- **Operation ID:** `update_cost_document_api_tms_finance_costs__cost_id__documents__document_id__put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `cost_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `document_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/tms/finance/costs/{cost_id}/documents/{document_id}`

Xoa/huy tms/finance/costs/{cost id}/documents/{document id}.

- **Operation ID:** `delete_cost_document_api_tms_finance_costs__cost_id__documents__document_id__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `cost_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `document_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Không.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/costs/{cost_id}/items`

Save Cost Item

- **Operation ID:** `save_cost_item_api_tms_finance_costs__cost_id__items_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `cost_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /api/tms/finance/costs/{cost_id}/items/{item_id}`

Xoa/huy tms/finance/costs/{cost id}/items/{item id}.

- **Operation ID:** `delete_cost_item_api_tms_finance_costs__cost_id__items__item_id__delete`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `cost_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `item_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Không.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/costs/{cost_id}/reverse`

Reverse Cost

- **Operation ID:** `reverse_cost_api_tms_finance_costs__cost_id__reverse_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `cost_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/costs/{cost_id}/submit`

Submit Cost

- **Operation ID:** `submit_cost_api_tms_finance_costs__cost_id__submit_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `cost_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/finance/dashboard`

Dashboard

- **Operation ID:** `dashboard_api_tms_finance_dashboard_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `POST /api/tms/finance/freight-orders/{order_id}/costs`

Create Cost

- **Operation ID:** `create_cost_api_tms_finance_freight_orders__order_id__costs_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `order_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/settlement-payments/{payment_id}/reverse`

Reverse Payment

- **Operation ID:** `reverse_payment_api_tms_finance_settlement_payments__payment_id__reverse_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `payment_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/finance/settlements`

List Settlements

- **Operation ID:** `list_settlements_api_tms_finance_settlements_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/tms/finance/settlements/{settlement_id}`

Doc/tra cuu tms/finance/settlements/{settlement id}.

- **Operation ID:** `get_settlement_api_tms_finance_settlements__settlement_id__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `settlement_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /api/tms/finance/settlements/{settlement_id}/payments`

Tao moi hoac thuc hien hanh dong tren tms/finance/settlements/{settlement id}/payments.

- **Operation ID:** `post_payment_api_tms_finance_settlements__settlement_id__payments_post`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `settlement_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `Data`.
- Bắt buộc: Có.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/finance/trips/{trip_id}/actual-cost`

Doc/tra cuu tms/finance/trips/{trip id}/actual cost.

- **Operation ID:** `get_trip_actual_cost_api_tms_finance_trips__trip_id__actual_cost_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `trip_id` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/tms/finance/trips/{trip_id}/actual-cost`

Save Trip Actual Cost

- **Operation ID:** `save_trip_actual_cost_api_tms_finance_trips__trip_id__actual_cost_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `trip_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `TripActualCostRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `id` | `string | null` | Không | `-` | Id |
| `currency_code` | `string` | Không | `VND` | Currency Code |
| `carrier_id` | `string | null` | Không | `-` | Carrier Id |
| `lines` | `array<object>` | Có | `-` | Lines |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |


## Bao cao van tai

### `GET /api/tms/reporting/expense-vouchers`

Expense Vouchers

- **Operation ID:** `expense_vouchers_api_tms_reporting_expense_vouchers_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |

### `GET /api/tms/reporting/expense-vouchers/{identifier}`

Expense Voucher

- **Operation ID:** `expense_voucher_api_tms_reporting_expense_vouchers__identifier__get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `identifier` | `path` | Có | `string` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/reporting/transport-revenue`

Transport Revenue

- **Operation ID:** `transport_revenue_api_tms_reporting_transport_revenue_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `date_from` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `date_to` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `customer_id` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `vehicle_id` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `currency_code` | `query` | Không | `string | null` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /api/tms/reporting/transport-revenue/export.csv`

Export Transport Revenue

- **Operation ID:** `export_transport_revenue_api_tms_reporting_transport_revenue_export_csv_get`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `date_from` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `date_to` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `customer_id` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `vehicle_id` | `query` | Không | `string | null` | Tham số nghiệp vụ. |
| `currency_code` | `query` | Không | `string | null` | Tham số nghiệp vụ. |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /api/tms/reporting/trips/{trip_id}/expense-voucher`

Save Expense Voucher

- **Operation ID:** `save_expense_voucher_api_tms_reporting_trips__trip_id__expense_voucher_put`
- **Xác thực:** theo middleware/quyền của ứng dụng; xem `/docs` và cấu hình token khi triển khai.

**Tham số**

| Tên | Vị trí | Bắt buộc | Kiểu | Mô tả |
|---|---|---:|---|---|
| `trip_id` | `path` | Có | `string` | Tham số nghiệp vụ. |
| `Idempotency-Key` | `header` | Không | `string | null` | Tham số nghiệp vụ. |

**Request body**

- Content-Type: `application/json`.
- Schema: `ExpenseVoucherRequest`.
- Bắt buộc: Có.

| Trường | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---|---|---:|---|---|
| `id` | `string | null` | Không | `-` | Id |
| `currency_code` | `string` | Không | `VND` | Currency Code |
| `carrier_id` | `string | null` | Không | `-` | Carrier Id |
| `lines` | `array<object>` | Có | `-` | Lines |
| `voucher_no` | `string` | Có | `-` | Voucher No |
| `voucher_date` | `string` | Có | `-` | Voucher Date |
| `do_id` | `string | null` | Không | `-` | Do Id |
| `vehicle_manager` | `string | null` | Không | `-` | Vehicle Manager |
| `payment_method` | `string` | Không | `cash` | Payment Method |
| `contract_no` | `string | null` | Không | `-` | Contract No |
| `machine_numbers` | `string | null` | Không | `-` | Machine Numbers |
| `checked_by` | `string | null` | Không | `-` | Checked By |
| `note` | `string | null` | Không | `-` | Note |

**Phản hồi**

| HTTP | Ý nghĩa | Schema |
|---:|---|---|
| `200` | Successful Response | `object` |
| `422` | Validation Error | `HTTPValidationError` |

---

Tái sinh tài liệu: `python backend/scripts/generate_system_docs.py` (chạy theo hướng dẫn trong `docs/README.md`).
