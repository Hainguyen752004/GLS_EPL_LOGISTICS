# Lược đồ cơ sở dữ liệu — EPL_System

Sinh từ `models.py` lúc 2026-09-10. Đầu mốc nâng cấp: `051_xoa_ke_toan_thue_ky_ke_toan`.
Các bảng đã xoá trong hai đợt 10/09: sales_orders, sales_order_lines, sales_order_documents (049); ar_invoices, gl_transactions, chart_of_accounts, tax_codes, accounting_periods, journal_batches, journal_lines, ap_invoices, ap_invoice_lines, freight_settlements, settlement_payments, delivery_order_details, quotation_details, pod, shipment_costs (051).

## `account_mappings`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| mapping_key | VARCHAR | có | PK |
| account_code | VARCHAR | có |  |
| effective_from | DATETIME |  |  |
| effective_to | DATETIME |  |  |

## `audit_logs`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| user_id | VARCHAR |  |  |
| action | VARCHAR |  |  |
| table_name | VARCHAR |  |  |
| record_id | VARCHAR |  |  |
| timestamp | DATETIME |  |  |
| ip_address | VARCHAR |  |  |

## `carriers`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| name | VARCHAR | có |  |
| tax_code | VARCHAR |  |  |
| contact_person | VARCHAR |  |  |
| phone | VARCHAR |  |  |
| email | VARCHAR |  |  |
| status | VARCHAR | có |  |
| is_internal | BOOLEAN | có |  |
| created_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |

## `cost_formulas`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| name | VARCHAR |  |  |
| formula_expression | TEXT |  |  |

## `crm_opportunities`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(64) | có | PK |
| customer_id | VARCHAR |  | FK→customers.id |
| prospect_name | VARCHAR(255) |  |  |
| contact_name | VARCHAR(255) |  |  |
| contact_phone | VARCHAR(64) |  |  |
| contact_email | VARCHAR(255) |  |  |
| source | VARCHAR(32) | có |  |
| route_id | VARCHAR |  | FK→routes.id |
| origin_text | VARCHAR(255) |  |  |
| destination_text | VARCHAR(255) |  |  |
| cargo_type | VARCHAR(255) |  |  |
| est_weight_kg | FLOAT | có |  |
| est_trips_per_month | INTEGER | có |  |
| expected_start | VARCHAR(32) |  |  |
| expected_price | NUMERIC(24, 6) |  |  |
| stage | VARCHAR(20) | có |  |
| owner | VARCHAR(128) |  |  |
| notes | TEXT |  |  |
| lost_reason | TEXT |  |  |
| quotation_id | VARCHAR |  | FK→quotations.id |
| next_action_at | DATETIME |  |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR(128) | có |  |
| updated_by | VARCHAR(128) | có |  |
| version | INTEGER | có |  |

## `currencies`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| exchange_rate | NUMERIC(24, 6) |  |  |

## `currency_definitions`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| code | VARCHAR(3) | có | PK |
| minor_units | INTEGER | có |  |
| is_active | BOOLEAN | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |

## `currency_rate_history`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| currency_code | VARCHAR(3) | có | FK→currency_definitions.code |
| functional_currency | VARCHAR(3) | có | FK→currency_definitions.code |
| rate_date | DATE | có |  |
| rate | NUMERIC(18, 8) | có |  |
| source | VARCHAR(100) | có |  |
| is_active | BOOLEAN | có |  |
| created_at | DATETIME | có |  |

## `customers`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| name | VARCHAR | có |  |
| type | VARCHAR |  |  |
| contact_person | VARCHAR |  |  |
| phone | VARCHAR |  |  |
| address | VARCHAR |  |  |
| vendor_type | VARCHAR |  |  |

## `delivery_order_charge_adjustments`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(128) | có | PK |
| closeout_id | VARCHAR(128) | có | FK→delivery_order_closeouts.id |
| line_no | INTEGER | có |  |
| name | VARCHAR(255) | có |  |
| cost_index | VARCHAR(32) |  |  |
| original_amount | NUMERIC(24, 6) | có |  |
| actual_amount | NUMERIC(24, 6) | có |  |
| increase_amount | NUMERIC(24, 6) | có |  |
| note | TEXT |  |  |
| created_at | DATETIME | có |  |
| created_by | VARCHAR(255) | có |  |

## `delivery_order_closeouts`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(128) | có | PK |
| do_id | VARCHAR | có | FK→delivery_orders.id |
| base_selling_price_snapshot | NUMERIC(24, 6) | có |  |
| base_price_source | VARCHAR(32) | có |  |
| base_price_source_id | VARCHAR(128) | có |  |
| surcharge_total | NUMERIC(24, 6) | có |  |
| final_selling_price | NUMERIC(24, 6) | có |  |
| currency_code | VARCHAR(3) | có |  |
| completed_at | DATETIME | có |  |
| completed_by | VARCHAR(255) | có |  |
| created_at | DATETIME | có |  |

## `delivery_orders`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| canonical_status | VARCHAR | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |
| updated_by | VARCHAR | có |  |
| version | INTEGER | có |  |
| quotation_id | VARCHAR |  | FK→quotations.id |
| unit_price | NUMERIC(24, 6) |  |  |
| price_basis | VARCHAR |  |  |
| billed_qty | FLOAT |  |  |
| driver_note | TEXT |  |  |
| customer_id | VARCHAR |  | FK→customers.id |
| route_id | VARCHAR |  | FK→routes.id |
| origin | VARCHAR |  |  |
| destination | VARCHAR |  |  |
| pickup_window_start | DATETIME |  |  |
| pickup_window_end | DATETIME |  |  |
| delivery_window_start | DATETIME |  |  |
| delivery_window_end | DATETIME |  |  |
| weight_kg | FLOAT |  |  |
| pallet_count | INTEGER |  |  |
| notes | TEXT |  |  |
| cancel_reason | TEXT |  |  |
| vehicle_id | VARCHAR |  | FK→vehicles.id |
| driver_id | VARCHAR |  | FK→drivers.id |
| co_driver | VARCHAR |  |  |
| status | VARCHAR |  |  |
| pickup_date | DATETIME |  |  |
| delivery_date | DATETIME |  |  |
| planned_departure_at | DATETIME |  |  |
| planned_arrival_at | DATETIME |  |  |
| planned_return_at | DATETIME |  |  |
| avg_speed_kmh | FLOAT |  |  |
| max_speed_kmh | FLOAT |  |  |
| return_speed_kmh | FLOAT |  |  |
| load_minutes | INTEGER |  |  |
| unload_minutes | INTEGER |  |  |
| return_distance_km | FLOAT |  |  |
| packaging_spec | VARCHAR |  |  |
| volume_m3 | FLOAT |  |  |
| seal_no | VARCHAR |  |  |

## `delivery_pod_documents`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(128) | có | PK |
| pod_record_id | INTEGER | có | FK→delivery_pod_records.id |
| file_name | VARCHAR(255) | có |  |
| mime_type | VARCHAR(128) | có |  |
| file_size | INTEGER | có |  |
| checksum | VARCHAR(128) | có |  |
| content | BLOB | có |  |
| created_at | DATETIME | có |  |
| created_by | VARCHAR(255) | có |  |

## `delivery_pod_records`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| idempotency_key | VARCHAR(128) |  |  |
| do_id | VARCHAR | có | FK→delivery_orders.id |
| trip_id | VARCHAR(128) |  | FK→transport_trips.id |
| leg_id | VARCHAR(128) |  | FK→transport_trip_legs.id |
| vehicle_id | VARCHAR | có | FK→vehicles.id |
| driver_id | VARCHAR |  | FK→drivers.id |
| stop_no | INTEGER | có |  |
| location_text | VARCHAR |  |  |
| receiver_name | VARCHAR |  |  |
| receiver_phone | VARCHAR |  |  |
| delivery_time | DATETIME |  |  |
| photo_url | VARCHAR |  |  |
| signature_url | VARCHAR |  |  |
| delivery_result | VARCHAR(32) |  |  |
| actual_qty | FLOAT |  |  |
| actual_qty_uom | VARCHAR |  |  |
| cargo_condition | TEXT |  |  |
| note | TEXT |  |  |
| status | VARCHAR | có |  |
| created_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |

## `driver_qualifications`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| driver_id | VARCHAR | có | PK |
| license_type | VARCHAR | có |  |
| valid_from | DATETIME | có |  |
| valid_to | DATETIME | có |  |
| status | VARCHAR | có |  |
| verified_at | DATETIME | có |  |
| verified_by | VARCHAR | có |  |

## `driver_shift_assignments`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(128) | có | PK |
| driver_id | VARCHAR | có | FK→drivers.id |
| vehicle_id | VARCHAR |  | FK→vehicles.id |
| trip_id | VARCHAR(128) |  | FK→transport_trips.id |
| shift_type | VARCHAR(20) | có |  |
| availability_kind | VARCHAR(20) | có |  |
| shift_start | DATETIME | có |  |
| shift_end | DATETIME | có |  |
| work_location | VARCHAR(500) |  |  |
| notes | TEXT |  |  |
| status | VARCHAR(20) | có |  |
| version | INTEGER | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR(128) | có |  |
| updated_by | VARCHAR(128) | có |  |

## `drivers`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| name | VARCHAR | có |  |
| role | VARCHAR |  |  |
| license_type | VARCHAR |  |  |
| phone | VARCHAR |  |  |
| assigned_vehicle | VARCHAR |  |  |
| shift | VARCHAR |  |  |
| status | VARCHAR |  |  |
| operational_status | VARCHAR(32) | có |  |
| operational_ref | VARCHAR(128) |  |  |
| operational_note | TEXT |  |  |
| operational_updated_at | DATETIME |  |  |
| photo_url | TEXT |  |  |
| depot_code | VARCHAR |  |  |
| team_code | VARCHAR |  |  |
| rotation_pattern | VARCHAR |  |  |

## `epl_expense_vouchers`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(128) | có | PK |
| trip_id | VARCHAR(128) | có | FK→transport_trips.id |
| cost_id | VARCHAR(128) | có | FK→freight_actual_costs.id |
| do_id | VARCHAR |  | FK→delivery_orders.id |
| voucher_no | VARCHAR(128) | có |  |
| voucher_date | DATE | có |  |
| vehicle_manager | VARCHAR(255) |  |  |
| payment_method | VARCHAR(32) | có |  |
| contract_no | VARCHAR(128) |  |  |
| machine_numbers | VARCHAR(500) |  |  |
| checked_by | VARCHAR(255) |  |  |
| note | TEXT |  |  |
| version | INTEGER | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR(128) | có |  |
| updated_by | VARCHAR(128) | có |  |

## `finance_control_config`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(20) | có | PK |
| functional_currency | VARCHAR(3) | có | FK→currency_definitions.code |
| enforce_creator_approver_sod | BOOLEAN | có |  |
| require_distinct_poster | BOOLEAN | có |  |
| distance_variance_threshold | NUMERIC(18, 8) | có |  |
| document_https_hosts | TEXT | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |

## `freight_actual_costs`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| freight_order_id | VARCHAR | có | FK→freight_orders.id |
| trip_id | VARCHAR(128) |  | FK→transport_trips.id |
| leg_id | VARCHAR(128) |  | FK→transport_trip_legs.id |
| carrier_id | VARCHAR | có | FK→carriers.id |
| currency_code | VARCHAR(3) | có | FK→currency_definitions.code |
| functional_currency | VARCHAR(3) | có | FK→currency_definitions.code |
| exchange_rate_snapshot | NUMERIC(18, 8) | có |  |
| exchange_rate_date | DATE | có |  |
| exchange_rate_source | VARCHAR(100) | có |  |
| planned_distance_km | NUMERIC(18, 3) | có |  |
| actual_distance_km | NUMERIC(18, 3) | có |  |
| distance_status | VARCHAR(32) | có |  |
| distance_variance_percent | NUMERIC(18, 8) |  |  |
| distance_variance_warning | BOOLEAN | có |  |
| subtotal_amount | NUMERIC(24, 6) | có |  |
| tax_amount | NUMERIC(24, 6) | có |  |
| total_amount | NUMERIC(24, 6) | có |  |
| status | VARCHAR(16) | có |  |
| is_active | BOOLEAN | có |  |
| version | INTEGER | có |  |
| reversal_of_cost_id | VARCHAR |  | FK→freight_actual_costs.id |
| reversed_by_cost_id | VARCHAR |  | FK→freight_actual_costs.id |
| reversal_reason | TEXT |  |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| submitted_at | DATETIME |  |  |
| approved_at | DATETIME |  |  |
| reversed_at | DATETIME |  |  |
| created_by | VARCHAR | có |  |
| updated_by | VARCHAR | có |  |
| submitted_by | VARCHAR |  |  |
| approved_by | VARCHAR |  |  |
| reversed_by | VARCHAR |  |  |

## `freight_charge_items`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| cost_id | VARCHAR | có | FK→freight_actual_costs.id |
| charge_type | VARCHAR(32) | có |  |
| cost_index | VARCHAR(32) |  |  |
| description | VARCHAR(500) |  |  |
| original_amount | NUMERIC(24, 6) | có |  |
| actual_amount | NUMERIC(24, 6) | có |  |
| increase_amount | NUMERIC(24, 6) | có |  |
| note | TEXT |  |  |
| quantity | NUMERIC(18, 4) | có |  |
| unit_price | NUMERIC(24, 6) | có |  |
| tax_code | VARCHAR(50) | có |  |
| tax_rate_snapshot | NUMERIC(18, 8) | có |  |
| tax_mode | VARCHAR(20) | có |  |
| net_amount | NUMERIC(24, 6) | có |  |
| tax_amount | NUMERIC(24, 6) | có |  |
| total_amount | NUMERIC(24, 6) | có |  |
| rounding_adjustment | NUMERIC(24, 6) | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |
| updated_by | VARCHAR | có |  |

## `freight_cost_documents`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| cost_id | VARCHAR | có | FK→freight_actual_costs.id |
| document_type | VARCHAR(64) | có |  |
| storage_url | TEXT | có |  |
| file_name | VARCHAR(255) |  |  |
| mime_type | VARCHAR(128) |  |  |
| checksum | VARCHAR(128) | có |  |
| vendor_invoice_no | VARCHAR(128) |  |  |
| document_date | DATE |  |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |
| updated_by | VARCHAR | có |  |

## `freight_order_legacy_links`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| freight_order_id | VARCHAR | có | PK |
| delivery_order_id | VARCHAR | có | FK→delivery_orders.id |

## `freight_order_units`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| freight_order_id | VARCHAR | có | PK |
| freight_unit_id | VARCHAR | có | PK |

## `freight_orders`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| pickup_location_id | VARCHAR | có | FK→locations.id |
| delivery_location_id | VARCHAR | có | FK→locations.id |
| pickup_window_start | DATETIME | có |  |
| pickup_window_end | DATETIME | có |  |
| delivery_window_start | DATETIME | có |  |
| delivery_window_end | DATETIME | có |  |
| total_weight_kg | FLOAT | có |  |
| total_volume_m3 | FLOAT | có |  |
| total_pallet_count | INTEGER | có |  |
| max_weight_kg | FLOAT | có |  |
| max_volume_m3 | FLOAT | có |  |
| max_pallet_count | INTEGER | có |  |
| status | VARCHAR | có |  |
| version | INTEGER | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |
| updated_by | VARCHAR | có |  |

## `freight_units`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| demand_id | VARCHAR | có | FK→transport_demands.id |
| pickup_location_id | VARCHAR | có | FK→locations.id |
| delivery_location_id | VARCHAR | có | FK→locations.id |
| pickup_window_start | DATETIME | có |  |
| pickup_window_end | DATETIME | có |  |
| delivery_window_start | DATETIME | có |  |
| delivery_window_end | DATETIME | có |  |
| weight_kg | FLOAT | có |  |
| volume_m3 | FLOAT | có |  |
| pallet_count | INTEGER | có |  |
| status | VARCHAR | có |  |
| version | INTEGER | có |  |
| created_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |

## `idempotency_records`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| actor | VARCHAR(128) | có |  |
| method | VARCHAR(16) | có |  |
| path | VARCHAR(500) | có |  |
| idempotency_key | VARCHAR(128) | có |  |
| operation | VARCHAR | có |  |
| request_hash | VARCHAR | có |  |
| response_json | TEXT | có |  |
| created_at | DATETIME | có |  |

## `incidents`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| do_id | VARCHAR |  |  |
| vehicle_id | VARCHAR |  |  |
| incident_type | VARCHAR |  |  |
| severity | VARCHAR |  |  |
| location | VARCHAR |  |  |
| description | TEXT |  |  |
| reporter | VARCHAR |  |  |
| reported_at | VARCHAR |  |  |
| status | VARCHAR |  |  |

## `items`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| name | VARCHAR | có |  |
| cargo_type | VARCHAR |  |  |
| notes | TEXT |  |  |
| default_uom | VARCHAR |  |  |
| weight_kg | FLOAT |  |  |

## `locations`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| name | VARCHAR | có |  |
| type | VARCHAR |  |  |
| address | VARCHAR |  |  |
| capacity | FLOAT |  |  |
| latitude | FLOAT |  |  |
| longitude | FLOAT |  |  |

## `migration_quarantine`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| migration_version | VARCHAR | có |  |
| entity_type | VARCHAR | có |  |
| entity_id | VARCHAR | có |  |
| reason | VARCHAR | có |  |
| payload_json | TEXT | có |  |
| quarantined_at | DATETIME | có |  |

## `parking_events`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| parking_list_id | VARCHAR(128) | có | FK→parking_lists.id |
| event_type | VARCHAR(32) | có |  |
| occurred_at | DATETIME | có |  |
| actor | VARCHAR(128) | có |  |
| note | TEXT |  |  |

## `parking_labels`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(128) | có | PK |
| parking_list_id | VARCHAR(128) | có | FK→parking_lists.id |
| package_no | INTEGER | có |  |
| package_total | INTEGER | có |  |
| qr_token | VARCHAR(128) | có |  |
| status | VARCHAR(20) | có |  |
| printed_at | DATETIME |  |  |
| reprint_count | INTEGER | có |  |

## `parking_list_items`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| parking_list_id | VARCHAR(128) | có | FK→parking_lists.id |
| source_detail_id | INTEGER |  |  |
| barcode | VARCHAR(128) |  |  |
| item_id_laos | VARCHAR(128) |  |  |
| item_id_thai | VARCHAR(128) |  |  |
| sku | VARCHAR(128) |  |  |
| description | VARCHAR(500) |  |  |
| case_qty | INTEGER | có |  |
| piece_qty | INTEGER | có |  |
| uom | VARCHAR(32) |  |  |
| weight_kg | FLOAT | có |  |
| cube_m3 | FLOAT | có |  |
| note | TEXT |  |  |

## `parking_lists`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(128) | có | PK |
| do_id | VARCHAR | có | FK→delivery_orders.id |
| trip_id | VARCHAR(128) |  | FK→transport_trips.id |
| version | INTEGER | có |  |
| customer_id | VARCHAR |  | FK→customers.id |
| store_id | VARCHAR(128) |  |  |
| store_name | VARCHAR(255) |  |  |
| route_code | VARCHAR(128) |  |  |
| route_name | VARCHAR(500) |  |  |
| wave | VARCHAR(64) |  |  |
| gate | VARCHAR(64) |  |  |
| box_count | INTEGER | có |  |
| total_pieces | INTEGER | có |  |
| total_weight_kg | FLOAT | có |  |
| total_cube_m3 | FLOAT | có |  |
| status | VARCHAR(20) | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR(128) | có |  |
| updated_by | VARCHAR(128) | có |  |

## `price_lists`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| customer_id | VARCHAR |  | FK→customers.id |
| item_id | VARCHAR |  | FK→items.id |
| unit_price | NUMERIC(24, 6) |  |  |
| valid_to | VARCHAR |  |  |

## `quotation_attachments`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| quotation_id | VARCHAR | có | FK→quotations.id |
| doc_type | VARCHAR | có |  |
| file_name | VARCHAR | có |  |
| storage_url | TEXT | có |  |
| mime_type | VARCHAR |  |  |
| size_bytes | INTEGER |  |  |
| note | VARCHAR |  |  |
| uploaded_at | DATETIME | có |  |
| uploaded_by | VARCHAR | có |  |

## `quotation_items`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| quotation_id | VARCHAR | có | FK→quotations.id |
| line_no | INTEGER | có |  |
| name | VARCHAR |  |  |
| quantity | NUMERIC(24, 6) | có |  |
| uom | VARCHAR | có |  |
| note | VARCHAR |  |  |
| created_at | DATETIME | có |  |

## `quotation_versions`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| quotation_id | VARCHAR | có | FK→quotations.id |
| version | INTEGER | có |  |
| selling_price | NUMERIC(24, 6) |  |  |
| unit_price | NUMERIC(24, 6) |  |  |
| price_basis | VARCHAR |  |  |
| total_cost | NUMERIC(24, 6) |  |  |
| currency_code | VARCHAR |  |  |
| fx_rate | FLOAT |  |  |
| note | TEXT |  |  |
| created_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |

## `quotations`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| canonical_status | VARCHAR | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |
| updated_by | VARCHAR | có |  |
| version | INTEGER | có |  |
| customer_id | VARCHAR |  | FK→customers.id |
| route_id | VARCHAR |  | FK→routes.id |
| origin | VARCHAR |  |  |
| destination | VARCHAR |  |  |
| pickup_window_start | VARCHAR |  |  |
| pickup_window_end | VARCHAR |  |  |
| delivery_window_start | VARCHAR |  |  |
| delivery_window_end | VARCHAR |  |  |
| weight_kg | FLOAT |  |  |
| pallet_count | INTEGER |  |  |
| cargo_type | VARCHAR |  |  |
| valid_to | VARCHAR |  |  |
| fuel_cost | NUMERIC(24, 6) |  |  |
| driver_cost | NUMERIC(24, 6) |  |  |
| toll_fee | NUMERIC(24, 6) |  |  |
| total_cost | NUMERIC(24, 6) |  |  |
| selling_price | NUMERIC(24, 6) |  |  |
| packaging_spec | VARCHAR |  |  |
| carrier_name | VARCHAR |  |  |
| delivery_method | VARCHAR |  |  |
| seal_weight | VARCHAR |  |  |
| temperature_requirement | VARCHAR |  |  |
| cargo_insurance | VARCHAR |  |  |
| warehouse_owner | VARCHAR |  |  |
| volume_m3 | FLOAT |  |  |
| notes | TEXT |  |  |
| status | VARCHAR |  |  |
| price_basis | VARCHAR |  |  |
| unit_price | NUMERIC(24, 6) |  |  |
| min_qty_per_trip | FLOAT |  |  |
| quote_no | VARCHAR |  |  |
| vehicle_type_id | VARCHAR |  | FK→vehicle_types.id |
| currency_code | VARCHAR |  |  |
| fx_rate | FLOAT |  |  |
| payment_terms | VARCHAR |  |  |
| sales_rep | VARCHAR |  |  |
| trips_per_month | INTEGER |  |  |
| waiting_surcharge | NUMERIC(24, 6) |  |  |
| cargo_value | NUMERIC(24, 6) |  |  |
| stacking | VARCHAR |  |  |
| sealing | VARCHAR |  |  |
| recipient_contact | VARCHAR |  |  |
| notes_customer | TEXT |  |  |
| notes_ops | TEXT |  |  |
| notes_internal | TEXT |  |  |
| bot_fee | NUMERIC(24, 6) |  |  |
| cost_breakdown_json | TEXT |  |  |
| target_margin | FLOAT |  |  |
| competitor_price | NUMERIC(18, 2) |  |  |
| discount_percent | FLOAT |  |  |
| sent_at | DATETIME |  |  |
| accepted_at | DATETIME |  |  |
| closed_at | DATETIME |  |  |
| close_reason | TEXT |  |  |

## `resource_assignments`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| freight_order_id | VARCHAR | có | FK→freight_orders.id |
| trip_id | VARCHAR(128) |  | FK→transport_trips.id |
| leg_id | VARCHAR(128) |  | FK→transport_trip_legs.id |
| vehicle_id | VARCHAR | có | FK→vehicles.id |
| driver_id | VARCHAR | có | FK→drivers.id |
| co_driver_id | VARCHAR |  | FK→drivers.id |
| assignment_start | DATETIME | có |  |
| assignment_end | DATETIME | có |  |
| status | VARCHAR | có |  |
| created_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |

## `roles`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| permissions | TEXT |  |  |

## `routes`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| name | VARCHAR | có |  |
| distance_km | FLOAT |  |  |
| segments_json | TEXT |  |  |
| road_geometry_json | TEXT |  |  |
| road_distance_km | FLOAT |  |  |
| bot_fee | NUMERIC(24, 6) |  |  |

## `tender_offers`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| tender_id | VARCHAR | có | FK→tenders.id |
| carrier_id | VARCHAR | có | FK→carriers.id |
| amount | NUMERIC(18, 2) | có |  |
| currency_code | VARCHAR | có |  |
| note | TEXT |  |  |
| status | VARCHAR | có |  |
| submitted_at | DATETIME | có |  |
| submitted_by | VARCHAR | có |  |

## `tenders`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| freight_order_id | VARCHAR | có | FK→freight_orders.id |
| response_deadline | DATETIME | có |  |
| status | VARCHAR | có |  |
| awarded_offer_id | VARCHAR |  |  |
| awarded_carrier_id | VARCHAR |  | FK→carriers.id |
| version | INTEGER | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |
| updated_by | VARCHAR | có |  |

## `transport_demands`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| customer_id | VARCHAR | có | FK→customers.id |
| pickup_location_id | VARCHAR | có | FK→locations.id |
| delivery_location_id | VARCHAR | có | FK→locations.id |
| pickup_window_start | DATETIME | có |  |
| pickup_window_end | DATETIME | có |  |
| delivery_window_start | DATETIME | có |  |
| delivery_window_end | DATETIME | có |  |
| weight_kg | FLOAT | có |  |
| volume_m3 | FLOAT | có |  |
| pallet_count | INTEGER | có |  |
| service_requirements | TEXT |  |  |
| status | VARCHAR | có |  |
| version | INTEGER | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |
| updated_by | VARCHAR | có |  |

## `transport_event_documents`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| event_id | VARCHAR | có | FK→transport_events.id |
| document_type | VARCHAR | có |  |
| storage_url | TEXT | có |  |
| file_name | VARCHAR |  |  |
| mime_type | VARCHAR |  |  |
| checksum | VARCHAR | có |  |
| uploaded_at | DATETIME | có |  |
| uploaded_by | VARCHAR | có |  |

## `transport_events`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| freight_order_id | VARCHAR | có | FK→freight_orders.id |
| trip_id | VARCHAR(128) |  | FK→transport_trips.id |
| leg_id | VARCHAR(128) |  | FK→transport_trip_legs.id |
| event_type | VARCHAR | có |  |
| event_time | DATETIME | có |  |
| lat | FLOAT |  |  |
| lng | FLOAT |  |  |
| speed_kmh | FLOAT |  |  |
| distance_km | FLOAT |  |  |
| eta | VARCHAR |  |  |
| location_text | VARCHAR |  |  |
| source | VARCHAR | có |  |
| device_id | VARCHAR |  |  |
| reason | TEXT |  |  |
| note | TEXT |  |  |
| idempotency_key | VARCHAR | có |  |
| payload_hash | VARCHAR | có |  |
| recorded_at | DATETIME | có |  |
| recorded_by | VARCHAR | có |  |

## `transport_trip_legs`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(128) | có | PK |
| trip_id | VARCHAR(128) | có | FK→trip_delivery_orders.trip_id, FK→transport_trips.id |
| do_id | VARCHAR |  | FK→trip_delivery_orders.do_id |
| sequence_no | INTEGER | có |  |
| leg_type | VARCHAR(30) | có |  |
| origin | VARCHAR(500) | có |  |
| destination | VARCHAR(500) | có |  |
| stop_name | VARCHAR(500) |  |  |
| receiver_name | VARCHAR(255) |  |  |
| receiver_phone | VARCHAR(64) |  |  |
| delivery_note | TEXT |  |  |
| distance_km | NUMERIC(18, 3) | có |  |
| avg_speed_kmh | NUMERIC(18, 8) | có |  |
| dwell_minutes | INTEGER | có |  |
| planned_departure_at | DATETIME |  |  |
| planned_arrival_at | DATETIME |  |  |
| actual_departure_at | DATETIME |  |  |
| actual_arrival_at | DATETIME |  |  |
| status | VARCHAR(20) | có |  |
| allocated_cost | NUMERIC(24, 6) | có |  |
| allocated_revenue | NUMERIC(24, 6) | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |

## `transport_trips`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(128) | có | PK |
| freight_order_id | VARCHAR | có | FK→freight_orders.id |
| trip_type | VARCHAR(20) | có |  |
| status | VARCHAR(20) | có |  |
| vehicle_id | VARCHAR |  | FK→vehicles.id |
| driver_id | VARCHAR |  | FK→drivers.id |
| co_driver_id | VARCHAR |  | FK→drivers.id |
| planned_departure_at | DATETIME |  |  |
| planned_arrival_at | DATETIME |  |  |
| planned_return_at | DATETIME |  |  |
| actual_departure_at | DATETIME |  |  |
| actual_arrival_at | DATETIME |  |  |
| actual_return_at | DATETIME |  |  |
| version | INTEGER | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR(128) | có |  |
| updated_by | VARCHAR(128) | có |  |

## `trip_delivery_orders`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| trip_id | VARCHAR(128) | có | PK |
| do_id | VARCHAR | có | PK |
| allocation_sequence | INTEGER | có |  |
| created_at | DATETIME | có |  |
| created_by | VARCHAR(128) | có |  |

## `uoms`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| description | VARCHAR |  |  |

## `users`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| username | VARCHAR | có |  |
| role_id | VARCHAR |  | FK→roles.id |

## `vehicle_cost_overrides`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| vehicle_id | VARCHAR | có | FK→vehicles.id |
| component | VARCHAR | có |  |
| value | NUMERIC(24, 6) | có |  |
| note | VARCHAR |  |  |
| updated_at | DATETIME |  |  |
| updated_by | VARCHAR |  |  |

## `vehicle_maintenance_cost_lines`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | INTEGER | có | PK |
| request_id | VARCHAR(128) | có | FK→vehicle_maintenance_requests.id |
| category | VARCHAR(32) | có |  |
| description | VARCHAR(500) | có |  |
| quantity | NUMERIC(18, 4) | có |  |
| unit | VARCHAR(32) | có |  |
| estimated_unit_cost | NUMERIC(24, 6) | có |  |
| estimated_total | NUMERIC(24, 6) | có |  |
| actual_unit_cost | NUMERIC(24, 6) | có |  |
| actual_total | NUMERIC(24, 6) | có |  |

## `vehicle_maintenance_requests`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR(128) | có | PK |
| request_no | VARCHAR(128) | có |  |
| vehicle_id | VARCHAR | có | FK→vehicles.id |
| category | VARCHAR(32) | có |  |
| priority | VARCHAR(20) | có |  |
| planned_start | DATETIME | có |  |
| planned_end | DATETIME | có |  |
| actual_start | DATETIME |  |  |
| actual_end | DATETIME |  |  |
| description | TEXT | có |  |
| cause | TEXT |  |  |
| odometer_km | FLOAT |  |  |
| workshop | VARCHAR(255) |  |  |
| currency_code | VARCHAR(3) | có |  |
| estimated_total | NUMERIC(24, 6) | có |  |
| actual_total | NUMERIC(24, 6) | có |  |
| next_maintenance_date | VARCHAR(10) |  |  |
| status | VARCHAR(20) | có |  |
| cancellation_reason | TEXT |  |  |
| version | INTEGER | có |  |
| created_at | DATETIME | có |  |
| updated_at | DATETIME | có |  |
| created_by | VARCHAR(128) | có |  |
| updated_by | VARCHAR(128) | có |  |
| approved_at | DATETIME |  |  |
| approved_by | VARCHAR(128) |  |  |
| completed_at | DATETIME |  |  |
| completed_by | VARCHAR(128) |  |  |

## `vehicle_tracking`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| do_id | VARCHAR | có | PK |
| vehicle_id | VARCHAR |  | FK→vehicles.id |
| lat | FLOAT |  |  |
| lng | FLOAT |  |  |
| speed_kmh | FLOAT |  |  |
| remaining_distance_km | FLOAT |  |  |
| eta | VARCHAR |  |  |
| planned_return_at | VARCHAR |  |  |
| last_update | DATETIME |  |  |

## `vehicle_types`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| name | VARCHAR | có |  |
| icon | VARCHAR |  |  |
| max_weight | FLOAT |  |  |
| volume_capacity_m3 | FLOAT |  |  |
| pallet_capacity | INTEGER |  |  |
| fuel_norm | FLOAT |  |  |
| avg_speed_kmh | FLOAT |  |  |
| base_rate | NUMERIC(24, 6) |  |  |
| maint_cost | NUMERIC(24, 6) |  |  |
| dep_cost_per_km | NUMERIC(24, 6) |  |  |
| dims | VARCHAR |  |  |
| fuel_type | VARCHAR |  |  |
| special | VARCHAR |  |  |
| notes | VARCHAR |  |  |

## `vehicles`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| brand | VARCHAR |  |  |
| type | VARCHAR |  |  |
| weight_capacity | FLOAT |  |  |
| volume_capacity_m3 | FLOAT |  |  |
| pallet_capacity | INTEGER |  |  |
| fuel_norm | FLOAT |  |  |
| min_speed_kmh | FLOAT |  |  |
| avg_speed_kmh | FLOAT |  |  |
| max_speed_kmh | FLOAT |  |  |
| maintenance_date | VARCHAR |  |  |
| status | VARCHAR |  |  |
| operational_status | VARCHAR(32) | có |  |
| operational_ref | VARCHAR(128) |  |  |
| operational_note | TEXT |  |  |
| operational_updated_at | DATETIME |  |  |
| engine_no | VARCHAR |  |  |
| chassis_no | VARCHAR |  |  |
| insurance_date | VARCHAR |  |  |
| inspection_date | VARCHAR |  |  |
| inspection_place | VARCHAR |  |  |
| depot | VARCHAR |  |  |
| depot_code | VARCHAR |  |  |
| inspection_exp | VARCHAR |  |  |
| odometer_km | FLOAT |  |  |
| next_service_odometer_km | FLOAT |  |  |
| engine_cap | VARCHAR |  |  |
| dimensions | VARCHAR |  |  |
| image_url | TEXT |  |  |

## `warehouse_appointments`

| Cột | Kiểu | Bắt buộc | Khoá |
|---|---|---|---|
| id | VARCHAR | có | PK |
| freight_order_id | VARCHAR | có | FK→freight_orders.id |
| appointment_type | VARCHAR | có |  |
| location_id | VARCHAR | có | FK→locations.id |
| scheduled_start | DATETIME | có |  |
| scheduled_end | DATETIME | có |  |
| status | VARCHAR | có |  |
| version | INTEGER | có |  |
| created_at | DATETIME | có |  |
| created_by | VARCHAR | có |  |

