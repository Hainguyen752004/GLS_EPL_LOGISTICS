# Tham chiếu API — EPL_System

Sinh từ OpenAPI của ứng dụng lúc 2026-09-10 (sau đợt xoá module Đơn hàng SO, kế toán AR/AP, thuế, kỳ kế toán, Shipment 360 — 10/09).
Bản đầy đủ có tham số/mẫu trả về: mở `/docs` (Swagger) trên máy chủ đang chạy.

| Phương thức | Đường dẫn | Tóm tắt |
|---|---|---|
| GET | `/` | Serve Frontend |
| GET | `/api/acc-codes` | Danh Muc Acc Code |
| POST | `/api/agent/action` | Action Agent Api |
| POST | `/api/agent/query` | Query Agent Api |
| POST | `/api/ai/checkpoint/scan` | Scan Checkpoint |
| GET | `/api/cost-formulas` | List Cost Formulas |
| POST | `/api/cost-formulas` | Save Cost Formula |
| POST | `/api/cost-formulas/evaluate` | Evaluate Cost Formula |
| GET | `/api/cost-formulas/fleet-overview` | Cost Formula Fleet Overview |
| GET | `/api/crm/customers` | Danh Sach Khach |
| GET | `/api/crm/customers/{customer_id}/profile` | Ho So Khach |
| GET | `/api/crm/opportunities` | Danh Sach |
| POST | `/api/crm/opportunities` | Tao |
| GET | `/api/crm/opportunities/summary` | Dai So Lieu |
| GET | `/api/crm/opportunities/{ma}` | Chi Tiet |
| PUT | `/api/crm/opportunities/{ma}` | Sua |
| POST | `/api/crm/opportunities/{ma}/quotation` | Lap Bao Gia |
| PUT | `/api/crm/opportunities/{ma}/stage` | Doi Giai Doan |
| GET | `/api/currencies` | List Currencies |
| POST | `/api/currencies` | Save Currency Rates |
| GET | `/api/currencies/history` | List Currency History |
| GET | `/api/currencies/reference-rates` | Get Currency Reference Rates |
| POST | `/api/currencies/reference-rates/refresh` | Refresh Currency Reference Rates |
| GET | `/api/customers` | List Customers |
| POST | `/api/customers` | Create Customer |
| GET | `/api/customers/{cid}/price-history` | Gia Da Bao |
| DELETE | `/api/customers/{customer_id}` | Delete Customer |
| PUT | `/api/customers/{customer_id}` | Update Customer |
| GET | `/api/dashboard/stats` | Get Dashboard Stats |
| GET | `/api/data/all` | Get All Data |
| GET | `/api/delivery-orders` | List Delivery Orders |
| GET | `/api/delivery-orders/analysis` | Analyze Delivery Orders |
| DELETE | `/api/delivery-orders/{do_id}` | Delete Delivery Order |
| PUT | `/api/delivery-orders/{do_id}` | Update Delivery Order |
| GET | `/api/delivery-orders/{do_id}/closeout` | Get Delivery Order Closeout |
| POST | `/api/delivery-orders/{do_id}/complete-delivery` | Complete Delivery Order |
| PUT | `/api/delivery-orders/{do_id}/dispatch` | Dispatch Delivery Order |
| PUT | `/api/delivery-orders/{do_id}/status` | Update Delivery Order Status |
| GET | `/api/depots` | List Depots |
| POST | `/api/depots` | Create Depot |
| GET | `/api/drivers` | List Drivers |
| POST | `/api/drivers` | Create Driver |
| DELETE | `/api/drivers/{did}` | Delete Driver |
| PUT | `/api/drivers/{driver_id}/operational-status` | Dat Trang Thai Tai Xe |
| GET | `/api/handover/delivery-orders/{do_id}` | Ban Giao Do |
| GET | `/api/health` | Health |
| GET | `/api/health/database` | Database Health |
| GET | `/api/incidents` | List Incidents |
| POST | `/api/incidents` | Create Incident |
| GET | `/api/locations/coordinates` | List Location Coordinates |
| PUT | `/api/locations/{location_id}/coordinates` | Set Location Coordinates |
| POST | `/api/master-data/account-mappings` | Save Account Mapping |
| DELETE | `/api/master-data/account-mappings/{mapping_key}` | Delete Account Mapping |
| PUT | `/api/master-data/account-mappings/{mapping_key}` | Update Account Mapping |
| POST | `/api/master-data/account-mappings/{mapping_key}/status` | Set Account Mapping Status |
| GET | `/api/parking-labels/{label_id}/qr.svg` | Parking Qr Svg |
| GET | `/api/parking-lists` | List Parking Lists |
| POST | `/api/parking-lists/auto-from-do/{do_id}` | Auto Create From Do |
| POST | `/api/parking-lists/from-do/{do_id}` | Create From Do |
| GET | `/api/parking-lists/{parking_id}` | Get Parking List |
| GET | `/api/parking-lists/{parking_id}/label` | Get Label Data |
| GET | `/api/parking-lists/{parking_id}/packing-list` | Get Packing List Data |
| POST | `/api/parking-lists/{parking_id}/print` | Record Print |
| POST | `/api/parking-lists/{parking_id}/status` | Update Status |
| GET | `/api/parking-qr/{token}` | Scan Parking Qr |
| POST | `/api/parking-qr/{token}/scan` | Record Parking Qr Scan |
| GET | `/api/pod-documents/{document_id}` | Download Pod Document |
| GET | `/api/pod-records` | List Pod Records Bulk |
| GET | `/api/pod/{do_id}` | Get Pod |
| POST | `/api/pod/{do_id}` | Save Pod |
| GET | `/api/quotations` | List Quotations |
| POST | `/api/quotations` | Create Quotation |
| GET | `/api/quotations/board` | Bang Bao Gia |
| POST | `/api/quotations/price-preview` | Xem Truoc Gia |
| GET | `/api/quotations/summary` | Dai So Lieu |
| DELETE | `/api/quotations/{qid}` | Delete Quotation |
| PUT | `/api/quotations/{qid}` | Update Quotation |
| POST | `/api/quotations/{qid}/accept` | Khach Chap Nhan |
| PUT | `/api/quotations/{qid}/approve` | Approve Quotation |
| POST | `/api/quotations/{qid}/attachments` | Them Chung Tu |
| DELETE | `/api/quotations/{qid}/attachments/{aid}` | Xoa Chung Tu |
| GET | `/api/quotations/{qid}/attachments/{aid}/file` | Tai Chung Tu |
| GET | `/api/quotations/{qid}/detail` | Chi Tiet |
| POST | `/api/quotations/{qid}/extend` | Gia Han |
| POST | `/api/quotations/{qid}/internal-approve` | Duyet Noi Bo |
| PUT | `/api/quotations/{qid}/items` | Ghi Dong Hang Hoa |
| POST | `/api/quotations/{qid}/reject` | Khach Tu Choi |
| POST | `/api/quotations/{qid}/return-to-draft` | Tra Ve Nhap |
| POST | `/api/quotations/{qid}/send` | Gui Khach |
| POST | `/api/quotations/{qid}/split` | Tach Do |
| PUT | `/api/quotations/{qid}/status` | Quotation Status Compat |
| GET | `/api/routes` | List Routes |
| POST | `/api/routes` | Create Route |
| DELETE | `/api/routes/{route_id}` | Delete Route |
| GET | `/api/routes/{route_id}/geo` | Route Geo |
| GET | `/api/tms/carriers` | List Carriers |
| POST | `/api/tms/carriers` | Create Carrier |
| DELETE | `/api/tms/carriers/{carrier_id}` | Delete Carrier |
| PUT | `/api/tms/carriers/{carrier_id}` | Update Carrier |
| POST | `/api/tms/carriers/{carrier_id}/status` | Set Carrier Status |
| GET | `/api/tms/demands` | List Demands |
| POST | `/api/tms/demands` | Create Demand |
| PUT | `/api/tms/demands/{demand_id}/submit` | Submit Demand |
| GET | `/api/tms/driver-qualifications` | List Driver Qualifications |
| POST | `/api/tms/driver-qualifications` | Save Driver Qualification |
| GET | `/api/tms/finance/costs` | List Costs |
| GET | `/api/tms/finance/costs/{cost_id}` | Get Cost |
| POST | `/api/tms/finance/costs/{cost_id}/approve` | Approve Cost |
| POST | `/api/tms/finance/costs/{cost_id}/documents` | Save Cost Document |
| DELETE | `/api/tms/finance/costs/{cost_id}/documents/{document_id}` | Delete Cost Document |
| PUT | `/api/tms/finance/costs/{cost_id}/documents/{document_id}` | Update Cost Document |
| POST | `/api/tms/finance/costs/{cost_id}/items` | Save Cost Item |
| DELETE | `/api/tms/finance/costs/{cost_id}/items/{item_id}` | Delete Cost Item |
| POST | `/api/tms/finance/costs/{cost_id}/reverse` | Reverse Cost |
| POST | `/api/tms/finance/costs/{cost_id}/submit` | Submit Cost |
| POST | `/api/tms/finance/freight-orders/{order_id}/costs` | Create Cost |
| GET | `/api/tms/finance/trips/{trip_id}/actual-cost` | Get Trip Actual Cost |
| PUT | `/api/tms/finance/trips/{trip_id}/actual-cost` | Save Trip Actual Cost |
| GET | `/api/tms/freight-orders` | List Freight Orders |
| POST | `/api/tms/freight-orders` | Create Freight Order |
| PUT | `/api/tms/freight-orders/{order_id}/dispatch` | Dispatch Freight Order |
| GET | `/api/tms/freight-orders/{order_id}/events` | List Transport Events |
| POST | `/api/tms/freight-orders/{order_id}/events` | Record Transport Event |
| GET | `/api/tms/freight-orders/{order_id}/latest-position` | Get Latest Transport Position |
| POST | `/api/tms/freight-orders/{order_id}/legacy-link` | Link Legacy Delivery Order |
| GET | `/api/tms/freight-units` | List Freight Units |
| POST | `/api/tms/freight-units/from-demand/{demand_id}` | Create Freight Unit |
| GET | `/api/tms/reporting/expense-vouchers` | Expense Vouchers |
| GET | `/api/tms/reporting/expense-vouchers/{identifier}` | Expense Voucher |
| GET | `/api/tms/reporting/transport-revenue` | Transport Revenue |
| GET | `/api/tms/reporting/transport-revenue/export.csv` | Export Transport Revenue |
| PUT | `/api/tms/reporting/trips/{trip_id}/expense-voucher` | Save Expense Voucher |
| GET | `/api/tms/resource-assignments` | List Resource Assignments |
| GET | `/api/tms/scheduling/board` | Scheduling Board |
| GET | `/api/tms/scheduling/driver-shifts` | List Driver Shifts |
| POST | `/api/tms/scheduling/driver-shifts` | Create Driver Shift |
| POST | `/api/tms/scheduling/driver-shifts/weekly-schedule` | Create Weekly Driver Schedule |
| DELETE | `/api/tms/scheduling/driver-shifts/{shift_id}` | Delete Driver Shift |
| PUT | `/api/tms/scheduling/driver-shifts/{shift_id}` | Update Driver Shift |
| PUT | `/api/tms/scheduling/drivers/{driver_id}/assignment` | Assign Driver Team |
| GET | `/api/tms/scheduling/fill-candidates` | Scheduling Fill Candidates |
| POST | `/api/tms/scheduling/generate-from-pattern` | Generate Shifts From Pattern |
| GET | `/api/tms/scheduling/vehicle-availability` | Vehicle Availability |
| GET | `/api/tms/tenders` | List Tenders |
| POST | `/api/tms/tenders` | Publish Tender |
| PUT | `/api/tms/tenders/{tender_id}/award` | Award Tender |
| GET | `/api/tms/tenders/{tender_id}/offers` | List Tender Offers |
| POST | `/api/tms/tenders/{tender_id}/offers` | Submit Tender Offer |
| GET | `/api/tms/trips` | List Trips |
| POST | `/api/tms/trips` | Create Trip |
| POST | `/api/tms/trips/from-delivery-orders` | Create Trip From Delivery Orders |
| GET | `/api/tms/trips/{trip_id}` | Get Trip |
| POST | `/api/tms/trips/{trip_id}/cancel` | Cancel Trip |
| POST | `/api/tms/trips/{trip_id}/complete-return` | Complete Trip Return |
| PUT | `/api/tms/trips/{trip_id}/dispatch` | Dispatch Trip |
| POST | `/api/tms/trips/{trip_id}/legs` | Add Trip Leg |
| GET | `/api/tms/warehouse-appointments` | List Warehouse Appointments |
| POST | `/api/tms/warehouse-appointments` | Book Warehouse Appointment |
| GET | `/api/tracking/control-tower` | Bảng theo dõi chuyến, GPS, POD và sự cố |
| GET | `/api/tracking/{do_id}` | Get Tracking |
| POST | `/api/uploads/images` | Upload Master Data Image |
| POST | `/api/v1/ai/chat` | Gateway Chat |
| GET | `/api/vehicle-maintenance-requests` | Get Vehicle Maintenance Requests In Period |
| POST | `/api/vehicle-maintenance-requests/{request_id}/approve` | Approve Vehicle Maintenance Request |
| POST | `/api/vehicle-maintenance-requests/{request_id}/cancel` | Cancel Vehicle Maintenance Request |
| POST | `/api/vehicle-maintenance-requests/{request_id}/complete` | Complete Vehicle Maintenance Request |
| POST | `/api/vehicle-maintenance-requests/{request_id}/start` | Start Vehicle Maintenance Request |
| GET | `/api/vehicle-types` | List Vehicle Types |
| POST | `/api/vehicle-types` | Save Vehicle Type |
| GET | `/api/vehicle-types/recommendations` | Get Vehicle Type Recommendations |
| DELETE | `/api/vehicle-types/{vid}` | Delete Vehicle Type |
| GET | `/api/vehicles` | List Vehicles |
| POST | `/api/vehicles` | Create Vehicle |
| GET | `/api/vehicles/{vehicle_id}/cost` | Get Vehicle Effective Cost |
| PUT | `/api/vehicles/{vehicle_id}/cost-overrides` | Put Vehicle Cost Overrides |
| GET | `/api/vehicles/{vehicle_id}/maintenance-requests` | Get Vehicle Maintenance Requests |
| POST | `/api/vehicles/{vehicle_id}/maintenance-requests` | Post Vehicle Maintenance Request |
| PUT | `/api/vehicles/{vehicle_id}/operational-status` | Dat Trang Thai Xe |
| DELETE | `/api/vehicles/{vid}` | Delete Vehicle |
| GET | `/favicon.ico` | Serve Favicon |
| GET | `/kich-ban-test` | Serve Test Runner Vietnamese Alias |
| GET | `/test-runner` | Serve Test Runner |
| GET | `/tongquan.jpg` | Serve Overview Image |
| GET | `/uploads/{asset_path}` | Get Uploaded Asset |
