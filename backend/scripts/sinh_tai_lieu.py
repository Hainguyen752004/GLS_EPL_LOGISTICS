# -*- coding: utf-8 -*-
"""Sinh hai tài liệu kỹ thuật từ MÃ NGUỒN ĐANG CHẠY:

    docs/API_REFERENCE_VI.md      — toàn bộ API: phương thức, đường dẫn, xác thực, tham số,
                                    thân yêu cầu, mục đích, ghi chú cách dùng, lỗi hay gặp.
    docs/DATABASE_SCHEMA_VI.md    — toàn bộ bảng: chức năng, cột, kiểu, khoá, ghi chú.

Cách chạy (không cần cơ sở dữ liệu, chỉ nạp ứng dụng):

    cd backend/app && python ../scripts/sinh_tai_lieu.py

Mô tả tiếng Việt nằm trong hai bảng `MO_TA_API` và `MO_TA_BANG` ngay dưới đây. Thêm
API hay bảng mới thì thêm một dòng ở đó; thiếu dòng thì tài liệu vẫn sinh được nhưng
đánh dấu "(chưa có mô tả)" để người đọc biết chỗ nào còn thiếu, không tự bịa.
"""
import datetime
import inspect
import io
import os
import re
import sys

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(GOC, "backend", "app")
sys.path.insert(0, APP)
os.chdir(APP)

import main  # noqa: E402
import models  # noqa: E402  (đăng ký metadata)
from database import Base  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402

HOM_NAY = datetime.date.today().isoformat()

# =============================================================================
# 1. MÔ TẢ API  — khoá: "METHOD path"
#    Giá trị: (mục đích, ghi chú cách dùng / lỗi hay gặp). Ghi chú có thể rỗng.
# =============================================================================
MO_TA_API = {
    # ---- Bàn giao cho bên công nợ -------------------------------------------------
    "GET /api/handover/delivery-orders": (
        "**API DANH SÁCH DO** đã hoàn tất cho hệ công nợ: mỗi dòng là header rút gọn của một lệnh giao hàng đã chốt hồ sơ (`delivered`), mới hoàn tất trước.",
        "Lọc `customer_id`, `completed_from`, `completed_to` (ISO `YYYY-MM-DD`, gồm cả hai đầu). Phân trang `page`/`page_size` (tối đa 200). Mỗi dòng có `detail_url` để gọi tiếp API chi tiết. Chỉ DO đã chốt hồ sơ mới xuất hiện — không nhả số chưa chốt."),
    "GET /api/handover/delivery-orders/{do_id}": (
        "**API HEADER + CHI TIẾT DO**: một mã DO → khối `header` (khách, tuyến, báo giá gốc, chuyến, xe, tài xế, mốc giao, POD, tổng cước/giá thành/lợi nhuận) và khối `details` (TỪNG DÒNG thu/chi, mỗi dòng có `acc_code`).",
        "Trả 404 `DELIVERY_ORDER_NOT_FOUND` nếu không có DO; 409 `DO_NOT_COMPLETED` nếu DO chưa `delivered` (không bàn giao số chưa chốt). Số liệu đọc cùng nguồn với khối 'Hồ sơ đã hoàn tất' trên màn, nên không lệch."),

    # ---- CRM ---------------------------------------------------------------------
    "GET /api/crm/opportunities": ("Danh sách cơ hội khách hàng (bảng Kanban).", "Lọc `stage` (new|contacted|negotiating|quoted|won|lost), `owner`, `customer_id`, `q` (tìm chữ)."),
    "POST /api/crm/opportunities": ("Tạo cơ hội mới: khách có mã hoặc khách tiềm năng chưa có mã (`prospect_name`).", "Thân: `customer_id` hoặc `prospect_name`, `contact_name/phone/email`, `source`, `route_id` hoặc `origin_text`/`destination_text`, `cargo_type`, `est_weight_kg`, `est_trips_per_month`, `expected_start`, `expected_price`, `owner`, `notes`."),
    "GET /api/crm/opportunities/summary": ("Số cơ hội theo từng giai đoạn cho dải KPI.", ""),
    "GET /api/crm/opportunities/{ma}": ("Chi tiết một cơ hội, kèm cờ `quotation_expired` nếu báo giá gắn theo đã hết hạn.", ""),
    "PUT /api/crm/opportunities/{ma}": ("Sửa thông tin cơ hội (chưa won/lost).", ""),
    "PUT /api/crm/opportunities/{ma}/stage": ("Kéo cơ hội sang giai đoạn khác trên Kanban.", "Thân `{stage, expected_version, lost_reason?}`. KHÔNG đặt tay `quoted`/`won` — hai giai đoạn đó do hệ đặt khi lập báo giá và khi khách chấp nhận. Kéo về `lost` phải có `lost_reason`."),
    "POST /api/crm/opportunities/{ma}/quotation": ("Từ cơ hội, sinh BÁO GIÁ NHÁP kế thừa khách, tuyến, hàng, sản lượng; cơ hội sang `quoted`.", "Sau bước này mọi việc tiếp theo làm ở API Báo giá. Khách chấp nhận báo giá → cơ hội tự `won`; khách từ chối → tự `lost` với lý do trên phiếu."),
    "GET /api/crm/customers": ("Danh sách khách kèm số cơ hội, số báo giá, số DO (hồ sơ 360° rút gọn).", "`q` tìm theo tên/mã."),
    "GET /api/crm/customers/{customer_id}/profile": ("Hồ sơ một khách: cơ hội, báo giá gần nhất, DO, doanh thu đã chốt.", ""),

    # ---- Báo giá (màn mới) ---------------------------------------------------------
    "GET /api/quotations/board": ("Bảng báo giá cho màn Báo giá cước: mỗi dòng có biên lợi nhuận, số ngày còn hiệu lực, số DO đã tách.", "Lọc `status` (all|draft|pending_approval|sent|accepted|split|rejected|expired), `customer_id`, `route_id`, `owner`, `q`."),
    "GET /api/quotations/summary": ("Sáu con số dải KPI của màn Báo giá (đang mở, chờ khách, hết hạn trong 7 ngày, đã chấp nhận chưa tách, tiền đã chấp nhận, biên dưới ngưỡng).", ""),
    "POST /api/quotations/price-preview": ("TÍNH GIÁ THÀNH cho một tổ hợp tuyến + loại xe + tải trọng — đây là chỗ tính giá duy nhất, màn hình chỉ hiển thị.", "Thân `{route_id, vehicle_type_id, weight_kg, volume_m3?, pallet_count?, cargo_value?, target_margin?}`. Trả `tinh_duoc`, `viec_con_thieu[]` (nói rõ thiếu km, thiếu công thức, xe không đủ tải…), `cac_dong[]` (từng khoản mục chi/thu), `gia_thanh`, `km`, `cac_loai_xe[]` (độ vừa tải từng loại), `goi_y_gia{theo_cong_thuc, bien_muc_tieu, hop_dong, lan_truoc}`."),
    "GET /api/quotations/{qid}/detail": ("Một báo giá kèm mọi thứ màn chi tiết cần: dòng hàng, đính kèm, phiên bản giá, DO đã sinh, biên, mốc.", ""),
    "PUT /api/quotations/{qid}/items": ("Ghi lại TOÀN BỘ bảng hàng hoá của báo giá (mỗi dòng: `line_no, name, quantity, uom, note`).", "Tổng `quantity` quyết định số DO sẽ sinh khi khách chấp nhận (1 cont = 1 DO). Chỉ sửa khi còn nháp/chờ duyệt."),
    "POST /api/quotations/{qid}/attachments": ("Đính kèm chứng từ (multipart: `file`, `doc_type`, `note`) — được phép ngay khi còn nháp.", ""),
    "GET /api/quotations/{qid}/attachments/{aid}/file": ("Tải tệp đính kèm.", ""),
    "DELETE /api/quotations/{qid}/attachments/{aid}": ("Xoá một đính kèm.", ""),
    "POST /api/quotations/{qid}/send": ("GỬI KHÁCH: cấp mã hiện cho khách (`quote_no`), chốt phiên bản giá, khoá sửa.", "Nếu biên < ngưỡng 15% (hoặc biên mục tiêu riêng của khách) thì KHÔNG gửi mà chuyển sang `pending_approval` — chờ trưởng phòng duyệt nội bộ. Lỗi thường gặp: `PRICE_REQUIRED` (chưa có đơn giá), `ITEMS_REQUIRED`, `VALIDITY_IN_PAST`."),
    "POST /api/quotations/{qid}/internal-approve": ("Trưởng phòng duyệt bán dưới ngưỡng biên → báo giá được gửi khách (`sent`).", ""),
    "POST /api/quotations/{qid}/return-to-draft": ("Trả báo giá đang chờ duyệt về nháp, kèm `reason`.", ""),
    "POST /api/quotations/{qid}/accept": ("**KHÁCH CHẤP NHẬN → SINH LỆNH GIAO HÀNG NGAY**, cùng một giao dịch. Báo giá sang `split`, mỗi DO mang `quotation_id` và giá khoá `unit_price`.", "Thân rỗng `{}` → số DO = tổng số lượng ở bảng hàng hoá. Hoặc truyền `dos: [{id?, quantity, pickup_window_start?, ..., seal_no?}]` để tự đặt mã/giờ từng DO. Cơ hội CRM gắn theo tự `won`. Lỗi: `QUOTATION_EXPIRED`, `QUOTATION_ALREADY_SPLIT`, `INVALID_TRANSITION` (chưa gửi khách)."),
    "POST /api/quotations/{qid}/reject": ("Khách từ chối, kèm `reason` — báo giá sang `rejected`, cơ hội CRM sang `lost`.", ""),
    "POST /api/quotations/{qid}/extend": ("Gia hạn hiệu lực (`valid_to`), kể cả báo giá đã hết hạn.", ""),
    "POST /api/quotations/{qid}/split": ("Đường tách DO thủ công cho báo giá đã `accepted` từ trước khi có tách tự động (hiếm dùng).", "Luồng mới KHÔNG cần gọi: `accept` đã sinh DO."),
    "GET /api/customers/{cid}/price-history": ("Vài báo giá gần nhất đã báo cho khách này (mốc gợi ý 'Lần trước').", "`route_id`, `limit`, `exclude` (mã báo giá đang soạn)."),

    # ---- Báo giá (đường CRUD chung) -----------------------------------------------
    "GET /api/quotations": ("Danh sách báo giá dạng phân trang (`page`, `page_size`) — dùng cho các màn cũ và đối soát.", ""),
    "POST /api/quotations": ("Tạo báo giá nháp. Thân theo `QuotationCreateRequest` (khách, tuyến, loại xe, tải trọng, khung giờ, `price_basis` + `unit_price`, `total_cost`, tiền tệ, ghi chú…).", "`selling_price` do máy chủ suy từ `unit_price × số lượng theo đơn vị cước` — không gửi. Đơn giá cước là giá CUỐI; `discount_percent` (0..1) chỉ để phiếu gửi khách in 'giá gốc'."),
    "PUT /api/quotations/{qid}": ("Sửa báo giá còn nháp/chờ duyệt.", "Không đổi được tuyến khi đã có DO."),
    "PUT /api/quotations/{qid}/approve": ("Duyệt nội bộ (đường cũ, tương đương `internal-approve`).", ""),
    "PUT /api/quotations/{qid}/status": ("Đổi trạng thái thô (đường cũ). Ưu tiên dùng `send/accept/reject/extend`.", ""),
    "DELETE /api/quotations/{qid}": ("Xoá báo giá còn nháp. Báo giá đã gửi/đã tách thì 409 `LOCKED_RECORD`.", ""),

    # ---- Lệnh giao hàng, POD -------------------------------------------------------
    "GET /api/delivery-orders": ("Danh sách lệnh giao hàng (phân trang). Mỗi dòng có `canonical_status`, `quotation_id`, `unit_price`, khung giờ, `cancel_reason`.", ""),
    "GET /api/delivery-orders/analysis": ("Thống kê DO theo trạng thái/tuyến cho bảng phân tích.", ""),
    "PUT /api/delivery-orders/{do_id}": ("Sửa DO còn `pending` (khung giờ, khối lượng, seal…).", "Đổi `route_id` bị chặn khi DO sinh từ báo giá — muốn đổi tuyến thì sửa báo giá và sinh lại."),
    "PUT /api/delivery-orders/{do_id}/status": ("Đổi trạng thái DO. Dùng chính cho HUỶ: `{status: 'Cancelled', reason}`.", "Huỷ mà thiếu `reason` → 422 `CANCEL_REASON_REQUIRED`. DO đang có chuyến hoạt động → 409 `ACTIVE_TRIP_EXISTS`."),
    "DELETE /api/delivery-orders/{do_id}": ("Xoá DO ở `pending` hoặc `cancelled`. Đang chạy/đã giao → 409 `LOCKED_RECORD`.", ""),
    "PUT /api/delivery-orders/{do_id}/dispatch": ("Điều phối trực tiếp một DO (đường cũ). Luồng chuẩn là tạo Trip rồi `PUT /api/tms/trips/{trip_id}/dispatch`.", ""),
    "POST /api/delivery-orders/{do_id}/complete-delivery": ("**HOÀN TẤT GIAO HÀNG**: nộp POD + chữ ký từng chặng, ghi khách trả thêm, CHỐT GIÁ CUỐI — tất cả trong một giao dịch (multipart).", "Trường `payload` (JSON): `{trip_id, currency_code, pod_entries:[{leg_id, stop_no, delivery_time, receiver_name, receiver_phone, delivery_result, cargo_condition, file_field, signature_file_field}], charge_adjustments:[{name, original_amount, actual_amount, note}]}` + các tệp ảnh/PDF theo `file_field`. Header `Idempotency-Key` bắt buộc. Kết quả: DO `delivered`, tạo `delivery_order_closeouts`, chuyến tự `completed` khi mọi DO đã POD. Không lập hoá đơn ở đây — hoá đơn là việc của hệ công nợ qua API bàn giao."),
    "GET /api/delivery-orders/{do_id}/closeout": ("HỒ SƠ HOÀN TẤT của một DO: DO, chuyến, POD + chứng từ, `commercials` (giá gốc, khách trả thêm, giá cuối, giá thành chốt/thực tế, lợi nhuận), `ledger_lines` (sổ thu–chi từng dòng có Acc code), `ledger_totals`.", "Đây là nguồn của khối 'Hồ sơ đã hoàn tất' trên màn và của API bàn giao. DO chưa hoàn tất vẫn trả được (giá tạm) nhưng cờ `margin_is_provisional=true`."),
    "GET /api/pod/{do_id}": ("POD của một DO (chỉ đọc).", ""),
    "POST /api/pod/{do_id}": ("Ghi POD đơn lẻ (đường cũ, chỉ để đọc lại; hoàn tất DO phải qua `complete-delivery`).", ""),
    "GET /api/pod-records": ("POD của NHIỀU DO trong một lời gọi: `do_ids=DO-1,DO-2` (tối đa 200).", "Không 404 khi không có POD — trả rỗng."),
    "GET /api/pod-documents/{document_id}": ("Tải một chứng từ POD (ảnh/PDF) đã nộp.", ""),

    # ---- Chuyến, điều phối, thực thi ------------------------------------------------
    "POST /api/tms/trips/from-delivery-orders": ("**LẬP CHUYẾN TỪ DO**: tạo Trip + Freight Order + các chặng theo tuyến của DO.", "Thân `{id, do_ids[], trip_type: one_way|round_trip, planned_departure_at, avg_speed_kmh, dwell_minutes, stop_plan?, return_purpose, return_route_id?, return_do_id?}`. Header `Idempotency-Key`. Chặng: các chặng giữa của tuyến là `outbound` (xe đi ngang, KHÔNG đòi POD), chặng cuối là `delivery`; chuyến nhiều DO thì mỗi DO còn lại có một chặng hạ hàng riêng 0 km tại điểm cuối, nên mọi DO đều nộp được POD và ETA không đổi. Muốn chuyến NHIỀU ĐIỂM GIAO thật thì khai `stop_plan[].do_id` (hàng DO nào hạ ở điểm dừng nào); khai thiếu DO → `409 TRIP_DO_KHONG_CO_CHANG`, khai mã lạ → `422 TRIP_DO_INVALID`."),
    "GET /api/tms/trips": ("Danh sách chuyến: `status`, `freight_order_id`, phân trang. Mỗi chuyến kèm ETA, `delivery_due_at`, `is_late`, `late_minutes`.", ""),
    "GET /api/tms/trips/{trip_id}": ("Chi tiết một chuyến: chặng, DO, xe/tổ lái, mốc kế hoạch và thực tế.", ""),
    "POST /api/tms/trips": ("Tạo chuyến thô cho Freight Order (đường TMS gốc; luồng chuẩn dùng `from-delivery-orders`).", ""),
    "PUT /api/tms/trips/{trip_id}/dispatch": ("**ĐIỀU PHỐI**: gán xe + tài xế (+ phụ xe) cho chuyến trong khung `assignment_start..assignment_end`; DO sang `in_transit`, xe/tổ lái bị khoá lịch trọn hành trình.", "Thân `TripDispatchRequest` (bắt buộc `expected_version`). Các cửa chặn: `READY_VEHICLE` (xe phải 'Sẵn sàng'), `VEHICLE_LEGAL_EXPIRED` (đăng kiểm/bảo hiểm/bảo dưỡng), `DRIVER_LICENSE_INVALID`, `SHIFT_NOT_COVERING` (ca trực phải phủ trọn chuyến), `RESOURCE_TIME_OVERLAP`, `ASSIGNMENT_OUTSIDE_WINDOW` (phải nằm trong khung lấy–giao), `VEHICLE_TYPE_MISMATCH` (xe khác loại báo giá → gửi lại với `confirm_vehicle_type_mismatch=true` để cố ý ghi đè, có nhật ký)."),
    "POST /api/tms/trips/{trip_id}/legs": ("Thêm một chặng vào chuyến (điểm dừng thêm).", ""),
    "POST /api/tms/trips/{trip_id}/cancel": ("Huỷ chuyến: trả xe/tổ lái, DO về `pending`. Chuyến đã có POD thì không huỷ được.", ""),
    "POST /api/tms/trips/{trip_id}/complete-return": ("Xác nhận xe về bãi sau chặng về (chuyến khứ hồi).", ""),
    "GET /api/tms/freight-orders": ("Danh sách Freight Order (đơn vận chuyển nội bộ sinh cùng chuyến).", ""),
    "POST /api/tms/freight-orders": ("Tạo Freight Order thô (đường TMS gốc).", ""),
    "PUT /api/tms/freight-orders/{order_id}/dispatch": ("Điều phối ở mức Freight Order (đường TMS gốc).", ""),
    "POST /api/tms/freight-orders/{order_id}/events": ("**GHI MỐC THỰC THI** của chuyến: `event_type` check_in | pickup | departure | arrival | unloading | delivered | route_deviation …, kèm `event_time`, `lat/lng`, `speed_kmh`, `distance_km`, `eta`, `note`.", "Header `Idempotency-Key`. Mốc `arrival` tự chuyển DO sang `arrived` (đã đến, chờ POD). Đây là chỗ GPS/thiết bị đổ dữ liệu vào."),
    "GET /api/tms/freight-orders/{order_id}/events": ("Chuỗi mốc của một Freight Order.", ""),
    "GET /api/tms/freight-orders/{order_id}/latest-position": ("Vị trí GPS mới nhất.", ""),
    "POST /api/tms/freight-orders/{order_id}/legacy-link": ("Nối Freight Order với DO cũ (di trú dữ liệu).", ""),
    "GET /api/tms/resource-assignments": ("Các phân công xe/tổ lái đang có (để xem trùng lịch).", ""),
    "GET /api/tms/scheduling/board": ("Toàn bộ dữ liệu màn Sắp lịch xe & tài xế: `start`, `days`, `depot`, `team`.", ""),
    "GET /api/tms/scheduling/driver-shifts": ("Ca trực trong khoảng `start..end`.", ""),
    "POST /api/tms/scheduling/driver-shifts": ("Tạo ca trực: `{id, driver_id, shift_type, availability_kind: work|leave, shift_start, shift_end, work_location, status, notes}`.", "Điều phối đòi ca trực PHỦ TRỌN thời gian chuyến (kể cả chặng về)."),
    "PUT /api/tms/scheduling/driver-shifts/{shift_id}": ("Sửa ca trực.", ""),
    "DELETE /api/tms/scheduling/driver-shifts/{shift_id}": ("Xoá ca trực chưa gắn chuyến.", ""),
    "POST /api/tms/scheduling/driver-shifts/weekly-schedule": ("Tạo ca theo tuần cho nhiều tài xế một lượt.", ""),
    "POST /api/tms/scheduling/generate-from-pattern": ("Sinh ca cho cả tổ từ mẫu xoay (`rotation_pattern`) của từng người.", ""),
    "PUT /api/tms/scheduling/drivers/{driver_id}/assignment": ("Gán bãi (`depot_code`), tổ (`team_code`), mẫu xoay cho tài xế.", ""),
    "GET /api/tms/scheduling/fill-candidates": ("Ai có thể nhận một ca đang thiếu: `date`, `shift`, `depot`, `team`.", ""),
    "GET /api/tms/scheduling/vehicle-availability": ("Xe rảnh/bận trong khoảng `start..end` (kể cả bảo dưỡng).", ""),
    "GET /api/tms/driver-qualifications": ("Bằng lái đã khai (phân trang).", ""),
    "POST /api/tms/driver-qualifications": ("Khai bằng lái: `{driver_id, license_type, valid_from, valid_to, status}`. Điều phối chặn tài xế không có bằng còn hạn.", ""),
    "GET /api/tms/carriers": ("Nhà vận chuyển (đội xe nội bộ hoặc thuê ngoài).", ""),
    "POST /api/tms/carriers": ("Thêm nhà vận chuyển `{id, name, tax_code, contact_person, phone, email, is_internal, status}`.", ""),
    "PUT /api/tms/carriers/{carrier_id}": ("Sửa nhà vận chuyển.", ""),
    "POST /api/tms/carriers/{carrier_id}/status": ("Đổi trạng thái active/inactive.", ""),
    "DELETE /api/tms/carriers/{carrier_id}": ("Xoá nhà vận chuyển chưa dùng.", ""),
    "GET /api/tms/demands": ("Nhu cầu vận chuyển (mô-đun TMS gốc, không nằm trong luồng Báo giá → DO).", ""),
    "POST /api/tms/demands": ("Tạo nhu cầu vận chuyển (TMS gốc).", ""),
    "PUT /api/tms/demands/{demand_id}/submit": ("Trình nhu cầu (TMS gốc).", ""),
    "GET /api/tms/freight-units": ("Đơn vị hàng (TMS gốc).", ""),
    "POST /api/tms/freight-units/from-demand/{demand_id}": ("Tách nhu cầu thành đơn vị hàng (TMS gốc).", ""),
    "GET /api/tms/tenders": ("Đấu thầu thuê ngoài (TMS gốc).", ""),
    "POST /api/tms/tenders": ("Mở thầu cho Freight Order (TMS gốc).", ""),
    "GET /api/tms/tenders/{tender_id}/offers": ("Các chào giá của thầu.", ""),
    "POST /api/tms/tenders/{tender_id}/offers": ("Nhà vận chuyển chào giá.", ""),
    "PUT /api/tms/tenders/{tender_id}/award": ("Trao thầu `{offer_id, expected_version}`.", ""),
    "GET /api/tms/warehouse-appointments": ("Lịch hẹn kho (TMS gốc).", ""),
    "POST /api/tms/warehouse-appointments": ("Đặt lịch hẹn lấy/giao tại kho (TMS gốc).", ""),

    # ---- Bãi xe / packing list ------------------------------------------------------
    "GET /api/parking-lists": ("Phiếu bãi xe / packing list: `q`, `status`, phân trang.", ""),
    "POST /api/parking-lists/from-do/{do_id}": ("Tạo phiếu bãi cho một DO: `{store_id, store_name, wave, gate, box_count}`. Dòng hàng lấy từ dòng hàng hoá của BÁO GIÁ.", "Gọi lặp cùng DO thì trả lại phiếu đã có (idempotent)."),
    "POST /api/parking-lists/auto-from-do/{do_id}": ("Tự chia một DO thành `list_count` phiếu, chia kiện/khối lượng đều.", ""),
    "GET /api/parking-lists/{parking_id}": ("Chi tiết phiếu: dòng hàng, nhãn QR, lịch sử sự kiện.", ""),
    "GET /api/parking-lists/{parking_id}/label": ("Nhãn kiện (HTML in).", ""),
    "GET /api/parking-lists/{parking_id}/packing-list": ("Packing list (HTML in).", ""),
    "POST /api/parking-lists/{parking_id}/print": ("Ghi nhận đã in `{document_type: label|packing_list}` — sinh mã QR cho từng kiện.", ""),
    "POST /api/parking-lists/{parking_id}/status": ("Đổi trạng thái phiếu tay `{status, note}` (draft→ready→parked→gate_in→loaded→dispatched→delivered).", "Bình thường trạng thái đi theo quét QR và theo chuyến; chỉ đặt tay khi cần sửa."),
    "GET /api/parking-qr/{token}": ("Trang quét QR công khai của một kiện (điện thoại bãi xe).", "Công khai, không cần token."),
    "POST /api/parking-qr/{token}/scan": ("Quét kiện: `{action: gate_in|loaded|delivered, note}`. Đủ kiện thì phiếu tự lên trạng thái.", "Công khai theo thiết kế (thiết bị bãi)."),
    "GET /api/parking-labels/{label_id}/qr.svg": ("Ảnh QR của một nhãn.", ""),

    # ---- Hoàn tất, theo dõi -------------------------------------------------------
    "GET /api/tracking/control-tower": ("THÁP KIỂM SOÁT: mọi chuyến đang chạy với GPS mới nhất, ETA, trễ hạn khách (`delivery_due_at`, `is_late`), POD, sự cố.", "Thiếu GPS không loại chuyến khỏi bảng — hiện 'chưa có GPS'."),
    "GET /api/tracking/{do_id}": ("Vết GPS và mốc của một DO.", ""),

    # ---- Chi phí phát sinh của chuyến ---------------------------------------------
    "PUT /api/tms/finance/trips/{trip_id}/actual-cost": ("**CHỐT CHI PHÍ PHÁT SINH** của chuyến đã hoàn tất: từng dòng `{name, original_amount (kế hoạch), actual_amount (thực), note, cost_index?, charge_type?}`.", "Header `Idempotency-Key`. Dòng nào trùng khoản mục công thức thì tự mang Acc code của khoản mục đó. Tạo bảng chi phí ở `draft`."),
    "GET /api/tms/finance/trips/{trip_id}/actual-cost": ("Bảng chi phí phát sinh đang hiệu lực của chuyến.", ""),
    "GET /api/tms/finance/costs": ("100 bảng chi phí gần nhất (quyền `finance_read`).", ""),
    "GET /api/tms/finance/costs/{cost_id}": ("Một bảng chi phí.", ""),
    "POST /api/tms/finance/costs/{cost_id}/submit": ("TRÌNH bảng chi phí `{expected_version}` (quyền `finance_creator`).", ""),
    "POST /api/tms/finance/costs/{cost_id}/approve": ("DUYỆT bảng chi phí `{expected_version}` (quyền `finance_approver`). Quy tắc bốn mắt: người tạo không được tự duyệt → 403.", "Chỉ chi phí ĐÃ DUYỆT mới vào giá thành của báo cáo doanh thu."),
    "POST /api/tms/finance/costs/{cost_id}/reverse": ("ĐẢO một bảng đã duyệt (tạo bảng âm đối ứng), kèm `reason`.", ""),
    "POST /api/tms/finance/costs/{cost_id}/items": ("Thêm dòng phí vào bảng còn `draft` (`quantity`, `unit_price`, `charge_type`…). Không có thuế: mọi dòng tính `số lượng × đơn giá`.", ""),
    "DELETE /api/tms/finance/costs/{cost_id}/items/{item_id}": ("Xoá dòng phí (bảng còn `draft`).", ""),
    "POST /api/tms/finance/costs/{cost_id}/documents": ("Gắn chứng từ (URL https, checksum) vào bảng chi phí.", ""),
    "PUT /api/tms/finance/costs/{cost_id}/documents/{document_id}": ("Sửa chứng từ.", ""),
    "DELETE /api/tms/finance/costs/{cost_id}/documents/{document_id}": ("Xoá chứng từ.", ""),
    "POST /api/tms/finance/freight-orders/{order_id}/costs": ("Tạo bảng chi phí theo Freight Order (đường gốc; luồng chuẩn dùng `trips/{id}/actual-cost`).", ""),

    # ---- Báo cáo ----------------------------------------------------------------
    "GET /api/tms/reporting/transport-revenue": ("BÁO CÁO DOANH THU VẬN TẢI theo chuyến đã hoàn tất: doanh thu = giá bán cuối của hồ sơ hoàn tất, giá thành = kế hoạch báo giá + phát sinh đã duyệt, lãi gộp, biên; biểu đồ theo ngày/khách/tuyến/loại hàng/tiền tệ.", "Lọc `date_from`, `date_to`, `customer_id`, `vehicle_id`, `currency_code`. `exceptions[]` liệt kê DO đã giao mà chưa có hồ sơ hoàn tất (`CLOSEOUT_MISSING`)."),
    "GET /api/tms/reporting/transport-revenue/export.csv": ("Cùng báo cáo, xuất CSV.", ""),
    "GET /api/tms/reporting/expense-vouchers": ("Danh sách phiếu chi vận tải đã lập.", ""),
    "GET /api/tms/reporting/expense-vouchers/{identifier}": ("Một phiếu chi (theo mã phiếu hoặc mã chuyến).", ""),
    "PUT /api/tms/reporting/trips/{trip_id}/expense-voucher": ("Lập/sửa phiếu chi cho chuyến từ các dòng chi phí đã duyệt.", ""),

    # ---- Dữ liệu gốc: đội xe ---------------------------------------------------------
    "GET /api/vehicle-types": ("Loại xe: tải trọng, thể tích, số pallet, định mức dầu, tốc độ, khấu hao/km.", ""),
    "POST /api/vehicle-types": ("Thêm/sửa loại xe `{id, name, max_weight, volume_capacity_m3, pallet_capacity, fuel_norm, avg_speed_kmh, dep_cost_per_km, dims, fuel_type, icon, notes}`.", ""),
    "DELETE /api/vehicle-types/{vid}": ("Xoá loại xe chưa có xe/báo giá dùng (409 `LOCKED_RECORD` nếu đang dùng).", ""),
    "GET /api/vehicle-types/recommendations": ("Loại xe nào đủ tải cho `weight_kg`, `volume_m3`, `pallet_count` (ba chiều).", ""),
    "GET /api/vehicles": ("Đội xe: `paginated`, `page`, `page_size`, `depot_code`. Mỗi xe kèm trạng thái vận hành và loại xe.", ""),
    "POST /api/vehicles": ("Thêm/sửa xe `{id (biển số), brand, type (MÃ loại xe), weight_capacity, volume_capacity_m3, pallet_capacity, inspection_exp, insurance_date, maintenance_date, depot_code, status, image_url…}`.", "`type` phải là MÃ loại xe (vd `DEMO-VT-20FT`), không phải tên."),
    "DELETE /api/vehicles/{vid}": ("Xoá xe không còn gắn chuyến.", ""),
    "GET /api/vehicles/{vehicle_id}/cost": ("Giá thành THỰC của một xe: công thức loại xe + đơn giá ghi đè của xe.", ""),
    "PUT /api/vehicles/{vehicle_id}/cost-overrides": ("Ghi đè đơn giá vài khoản mục cho riêng xe này `{overrides:[{component, value, note}]}` (xe cũ tốn dầu hơn…).", ""),
    "PUT /api/vehicles/{vehicle_id}/operational-status": ("Đặt tay trạng thái vận hành xe `{status, note}`.", ""),
    "GET /api/vehicles/{vehicle_id}/maintenance-requests": ("Phiếu bảo dưỡng của một xe.", ""),
    "POST /api/vehicles/{vehicle_id}/maintenance-requests": ("Lập phiếu bảo dưỡng `{category, priority, planned_start, planned_end, description, workshop, estimated_total…}`. Xe trong lịch bảo dưỡng không điều phối được.", ""),
    "GET /api/vehicle-maintenance-requests": ("Bảo dưỡng của mọi xe giao với khoảng `start..end`.", ""),
    "POST /api/vehicle-maintenance-requests/{request_id}/approve": ("Duyệt phiếu bảo dưỡng.", ""),
    "POST /api/vehicle-maintenance-requests/{request_id}/start": ("Bắt đầu bảo dưỡng.", ""),
    "POST /api/vehicle-maintenance-requests/{request_id}/complete": ("Hoàn tất bảo dưỡng (đặt `next_maintenance_date`).", ""),
    "POST /api/vehicle-maintenance-requests/{request_id}/cancel": ("Huỷ phiếu bảo dưỡng.", ""),
    "GET /api/drivers": ("Tài xế/phụ xe kèm trạng thái nhân sự và vận hành.", ""),
    "POST /api/drivers": ("Thêm/sửa tài xế `{id, name, role: 'Tài xế chính'|'Phụ xe', license_type, phone, shift, depot_code, team_code, photo_url}`.", ""),
    "DELETE /api/drivers/{did}": ("Xoá tài xế chưa gắn chuyến.", ""),
    "PUT /api/drivers/{driver_id}/operational-status": ("Đặt tay trạng thái nhân sự `{status: available|on_leave|sick|…, note}`.", ""),
    "GET /api/depots": ("Danh mục bãi/chi nhánh (từ bảng `locations`).", ""),
    "POST /api/depots": ("Thêm/sửa bãi `{id, name, type, address}`.", ""),

    # ---- Dữ liệu gốc: công thức giá thành, Acc code --------------------------------
    "GET /api/cost-formulas": ("Mọi công thức giá thành theo loại xe: `terms[]` (khoản mục: `key, label, kind cost|revenue, factor per_km|per_kg|per_tonne|per_trip, rate, cost_index`), `expressions`.", ""),
    "POST /api/cost-formulas": ("Lưu công thức của một loại xe `{vehicle_type_id, currency, terms[], expressions?, expected_updated_at?}`.", "Acc code (`cost_index`) DÙNG CHUNG theo khoản mục: dòng trống tự kế thừa mã chung; dòng có mã ghi vào Mapping tài khoản (`khoan_muc::<key>`) và lan sang loại xe khác cùng khoản mục. 409 nếu người khác vừa sửa (`expected_updated_at`)."),
    "POST /api/cost-formulas/evaluate": ("Chạy thử công thức với một chuyến giả `{formula_id | terms+expressions, trip:{km, kg, …}}`.", ""),
    "GET /api/cost-formulas/fleet-overview": ("Giá hiệu lực từng xe và lịch sử ghi đè để so sánh.", ""),
    "GET /api/acc-codes": ("Danh mục Acc code (mã tài khoản kế toán) lấy từ API bên công nợ, cache 10 phút; `refresh=1` để nạp lại.", "Cấu hình bằng biến môi trường `EPL_ACC_CODE_API`, `EPL_ACC_CODE_TOKEN`, `EPL_ACC_CODE_COUNTRY`. Không cấu hình → trả rỗng kèm thông báo, không bịa mã."),

    # ---- Dữ liệu gốc: khách, tuyến, địa điểm -----------------------------------------
    "GET /api/customers": ("Khách hàng.", ""),
    "POST /api/customers": ("Thêm khách `{id, name, type, contact_person, phone, address}`.", ""),
    "PUT /api/customers/{customer_id}": ("Sửa khách.", ""),
    "DELETE /api/customers/{customer_id}": ("Xoá khách chưa có báo giá/DO (409 nếu đang dùng).", ""),
    "GET /api/routes": ("Tuyến đường: `distance_km`, các chặng `segments_json`, BOT theo tuyến, cờ có hình đường bộ.", ""),
    "POST /api/routes": ("Thêm/sửa tuyến `{id, name, distance_km, segments_json:[{origin, destination, distance_km}]}`.", "Số km của tuyến là đầu vào của MỌI công thức giá thành; tuyến 0 km thì báo giá không tính được."),
    "DELETE /api/routes/{route_id}": ("Xoá tuyến chưa có báo giá/DO dùng.", ""),
    "GET /api/routes/{route_id}/geo": ("Tuyến kèm toạ độ điểm và hình đường bộ (được phép gọi dịch vụ bản đồ ngoài).", ""),
    "GET /api/locations/coordinates": ("Địa điểm kèm toạ độ, và danh sách địa điểm CHƯA có toạ độ.", ""),
    "PUT /api/locations/{location_id}/coordinates": ("Khai tay toạ độ `{latitude, longitude}`.", ""),

    # ---- Mapping tài khoản, tiền tệ ----------------------------------------------------
    "POST /api/master-data/account-mappings": ("Thêm mapping `{mapping_key, account_code, effective_from?, effective_to?}`. Các khoá `khoan_muc::*` là Acc code dùng chung của khoản mục công thức.", ""),
    "PUT /api/master-data/account-mappings/{mapping_key}": ("Sửa mapping.", ""),
    "POST /api/master-data/account-mappings/{mapping_key}/status": ("Bật/tắt `{status: active|inactive}`.", ""),
    "DELETE /api/master-data/account-mappings/{mapping_key}": ("Xoá mapping.", ""),
    "GET /api/currencies": ("Tiền tệ và tỷ giá về VND (bảng `currencies`).", ""),
    "POST /api/currencies": ("Thêm/sửa tỷ giá `{id: 'USD', exchange_rate}`.", ""),
    "GET /api/currencies/history": ("Lịch sử tỷ giá.", ""),
    "GET /api/currencies/reference-rates": ("Tỷ giá tham chiếu lấy từ nguồn ngoài (nếu cấu hình).", ""),
    "POST /api/currencies/reference-rates/refresh": ("Nạp lại tỷ giá tham chiếu.", ""),

    # ---- Bảng điều khiển, sự cố, dữ liệu tổng ----------------------------------------
    "GET /api/dashboard/stats": ("Chỉ số bảng điều khiển: `revenue_ytd` = tổng giá bán cuối các hồ sơ hoàn tất, `completed_deliveries`, `total_deliveries`, `in_transit_orders`, `active_vehicles`, `incidents_count`.", ""),
    "GET /api/incidents": ("Sự cố trên đường.", ""),
    "PUT /api/incidents/{incident_id}/status": (
        "Đổi trạng thái một sự cố: đang xử lý, đã xử lý (đóng), hoặc mở lại.",
        "Thân: `status` nhận `Open` | `In Progress` | `Resolved`, và `note` (ghi chú xử lý). "
        "Đóng sự cố (`Resolved`) BẮT BUỘC có `note` — đóng mà không nói đã xử lý thế nào thì "
        "người đọc sổ sau này không biết gì. Gửi lại đúng trạng thái đang có mà không kèm ghi "
        "chú thì trả về nguyên trạng, không ghi thêm lịch sử."),
    "POST /api/incidents": ("Báo sự cố `{do_id, vehicle_id, incident_type, severity, location, description, reporter}`. Xe phải thuộc DO/chuyến đó.", ""),
    "GET /api/data/all": ("Ảnh chụp mọi danh mục cho giao diện nạp một lần (khách, tuyến, xe, tài xế, báo giá, DO, chuyến, phiếu…). Dữ liệu người dùng/vai trò/nhật ký được che.", ""),

    # ---- AI, upload, health, trang tĩnh --------------------------------------------------
    "POST /api/agent/query": ("Hỏi trợ lý AI về dữ liệu vận hành `{prompt}` (đọc, không ghi).", ""),
    "POST /api/agent/action": ("Nhờ trợ lý AI thực hiện thao tác `{prompt}` (có xác nhận).", ""),
    "POST /api/v1/ai/chat": ("Chat AI hai bước `{prompt, draft_data?, is_confirmed?}`.", ""),
    "POST /api/ai/checkpoint/scan": ("Trạm kiểm soát AI: nhận ảnh, đọc biển số/chứng từ (multipart `file`).", ""),
    "POST /api/uploads/images": ("Tải ảnh xe/tài xế (multipart `entity_type`, `file`).", ""),
    "GET /uploads/{asset_path:path}": ("Ảnh đã tải (công khai, tên tệp uuid).", ""),
    "GET /api/health": ("Sống hay chưa (không chạm DB).", "Công khai."),
    "GET /api/health/database": ("Sẵn sàng: DB nối được, mốc nâng cấp đủ, lược đồ đủ bảng/cột.", "Công khai. `DATABASE_SCHEMA_INVALID` khi lược đồ lệch."),
    "GET /": ("Trang giao diện.", ""), "GET /favicon.ico": ("Biểu tượng.", ""), "GET /tongquan.jpg": ("Ảnh sơ đồ tổng quan.", ""),
    "GET /test-runner": ("Trang chạy bộ kiểm giao diện.", ""), "GET /kich-ban-test": ("Kịch bản kiểm.", ""),
}

TEN_NHOM = [
    ("routes.handover_routes", "1. BÀN GIAO CHO BÊN CÔNG NỢ — hai API dành cho hệ kế toán của anh Khang"),
    ("routes.crm_routes", "2. Khách hàng và cơ hội (CRM)"),
    ("routes.bao_gia_routes", "3. Báo giá cước — màn Báo giá mới"),
    ("routes.workflow_routes", "4. Báo giá (đường CRUD chung), Lệnh giao hàng và POD"),
    ("routes.tms_planning_routes", "5. Chuyến, điều phối, sắp lịch, mốc thực thi"),
    ("routes.parking_list_routes", "6. Bãi xe và packing list"),
    ("routes.delivery_routes", "7. Hoàn tất giao hàng và theo dõi"),
    ("routes.tms_finance_routes", "8. Chi phí phát sinh của chuyến"),
    ("routes.tms_reporting_routes", "9. Báo cáo"),
    ("routes.fleet_routes", "10. Dữ liệu gốc: loại xe, xe, tài xế, bãi, công thức giá thành, Acc code"),
    ("routes.master_data_routes", "11. Dữ liệu gốc: khách hàng, tuyến, địa điểm"),
    ("routes.finance_master_routes", "12. Mapping tài khoản"),
    ("routes.currency_routes", "13. Tiền tệ và tỷ giá"),
    ("routes.operations_routes", "14. Bảng điều khiển và sự cố"),
    ("routes.data_export_routes", "15. Dữ liệu tổng cho giao diện"),
    ("routes.ai_upload_routes", "16. Trợ lý AI và tải ảnh"),
    ("routes.health_routes", "17. Kiểm tra sức khoẻ"),
    ("main", "18. Trang tĩnh"),
]

# =============================================================================
# 2. MÔ TẢ BẢNG — khoá: tên bảng → (nhóm, chức năng, ghi chú)
# =============================================================================
MO_TA_BANG = {
    "customers": ("Dữ liệu gốc", "Khách hàng (chủ hàng). Mọi báo giá, DO, cơ hội đều trỏ về đây.", ""),
    "routes": ("Dữ liệu gốc", "Tuyến đường: số km, các chặng (`segments_json`), hình đường bộ thật (`road_geometry_json`), phí BOT theo tuyến.", "Số km là đầu vào của công thức giá thành."),
    "locations": ("Dữ liệu gốc", "Địa điểm: bãi/chi nhánh, kho, cảng; toạ độ để vẽ tuyến và tính ETA.", ""),
    "vehicle_types": ("Dữ liệu gốc", "Loại xe: tải trọng, thể tích, pallet, định mức dầu, tốc độ, khấu hao/km. Báo giá chốt theo LOẠI xe.", ""),
    "vehicles": ("Dữ liệu gốc", "Từng chiếc xe: biển số, loại (MÃ loại xe), năng lực, ba hạn pháp lý (đăng kiểm, bảo hiểm, bảo dưỡng), bãi, trạng thái vận hành.", "Điều phối chỉ nhận xe 'Sẵn sàng' và còn hạn pháp lý."),
    "vehicle_cost_overrides": ("Dữ liệu gốc", "Đơn giá ghi đè của riêng một xe cho vài khoản mục (xe cũ tốn dầu hơn…).", "Công thức hai tầng: loại xe → xe."),
    "vehicle_maintenance_requests": ("Dữ liệu gốc", "Phiếu bảo dưỡng xe: kế hoạch, thực tế, xưởng, chi phí; xe trong lịch bảo dưỡng không điều phối được.", ""),
    "vehicle_maintenance_cost_lines": ("Dữ liệu gốc", "Dòng chi phí của phiếu bảo dưỡng.", ""),
    "drivers": ("Dữ liệu gốc", "Tài xế và phụ xe: bằng lái, bãi, tổ, mẫu xoay ca, trạng thái nhân sự và vận hành.", ""),
    "driver_qualifications": ("Dữ liệu gốc", "Bằng lái và hiệu lực; điều phối chặn tài xế không có bằng còn hạn.", ""),
    "driver_shift_assignments": ("Sắp lịch", "Ca trực / ca nghỉ của tài xế; điều phối đòi ca phủ trọn thời gian chuyến.", ""),
    "carriers": ("Dữ liệu gốc", "Nhà vận chuyển: đội xe nội bộ hoặc thuê ngoài.", ""),
    "cost_formulas": ("Dữ liệu gốc", "Công thức giá thành theo loại xe (JSON trong `formula_expression`): khoản mục chi/thu, đơn giá, hệ số nhân, Acc code, lịch sử.", "Một loại xe một công thức VND."),
    "account_mappings": ("Dữ liệu gốc", "Mapping tài khoản. Các khoá `khoan_muc::<key>` là Acc code DÙNG CHUNG của từng khoản mục công thức.", ""),
    "currencies": ("Dữ liệu gốc", "Tiền tệ và tỷ giá về VND dùng cho báo giá ngoại tệ.", ""),
    "currency_definitions": ("Dữ liệu gốc", "Định nghĩa tiền tệ (số lẻ) cho tính tiền chính xác.", ""),
    "currency_rate_history": ("Dữ liệu gốc", "Lịch sử tỷ giá theo ngày để quy đổi báo cáo về tiền tệ chức năng.", ""),
    "finance_control_config": ("Dữ liệu gốc", "Cấu hình tài chính toàn cục: tiền tệ chức năng, bốn mắt bật/tắt, ngưỡng lệch km.", "Một dòng `GLOBAL`."),
    "roles": ("Phân quyền", "Vai trò và danh sách quyền (JSON): `finance_read`, `finance_creator`, `finance_approver`…", "Đăng nhập do hệ thống cha lo."),
    "users": ("Phân quyền", "Người dùng → vai trò. Danh tính đến từ token của hệ thống cha.", ""),
    "crm_opportunities": ("Kinh doanh", "Cơ hội khách hàng (CRM-01): khách/khách tiềm năng, tuyến, hàng, sản lượng, giai đoạn, chủ, lý do mất; gắn báo giá khi đã lập.", "Giai đoạn: new, contacted, negotiating, quoted, won, lost."),
    "quotations": ("Kinh doanh", "BÁO GIÁ — thoả thuận với khách: tuyến, loại xe, tải trọng, khung giờ, đơn vị cước + đơn giá (giá CUỐI), tổng giá thành, biên mục tiêu, giá đối thủ, chiết khấu, hiệu lực, ba ô ghi chú, trạng thái.", "Trạng thái: draft, pending_approval, sent, approved, accepted, split, rejected, expired."),
    "quotation_items": ("Kinh doanh", "Dòng hàng hoá của báo giá (tên, số lượng, ĐVT). Tổng số lượng = số DO sinh khi khách chấp nhận.", ""),
    "quotation_attachments": ("Kinh doanh", "Chứng từ đính kèm báo giá.", ""),
    "quotation_versions": ("Kinh doanh", "Phiên bản giá mỗi lần gửi khách (giá, đơn vị, tiền tệ, tỷ giá).", ""),
    "delivery_orders": ("Vận hành", "LỆNH GIAO HÀNG (DO) — yêu cầu cụ thể của khách, sinh tự động khi khách chấp nhận báo giá; mang `quotation_id`, giá khoá `unit_price`, khung lấy/giao, xe/tài xế đã điều, lý do huỷ.", "Trạng thái: pending, in_transit, arrived, delivered, cancelled."),
    "delivery_order_closeouts": ("Vận hành", "HỒ SƠ HOÀN TẤT của DO: giá gốc, khách trả thêm, GIÁ BÁN CUỐI, tiền tệ, lúc hoàn tất. Nguồn doanh thu của báo cáo và của API bàn giao.", ""),
    "delivery_order_charge_adjustments": ("Vận hành", "Các khoản khách trả thêm ghi lúc hoàn tất (kèm Acc code).", ""),
    "delivery_pod_records": ("Vận hành", "POD từng chặng: người nhận, giờ giao, kết quả, tình trạng hàng, số lượng thực.", ""),
    "delivery_pod_documents": ("Vận hành", "Ảnh POD / ảnh chữ ký / PDF (lưu nội dung nhị phân, checksum).", ""),
    "freight_orders": ("Vận hành", "Đơn vận chuyển nội bộ sinh cùng chuyến (điểm lấy/giao, khung giờ, tổng tải).", ""),
    "freight_order_legacy_links": ("Vận hành", "Nối Freight Order ↔ DO.", ""),
    "transport_trips": ("Vận hành", "CHUYẾN XE — cách công ty thực hiện DO: loại chuyến, xe, tài xế, phụ xe, mốc kế hoạch và thực tế.", "Trạng thái: planned, ready, in_transit, arrived, completed, cancelled."),
    "trip_delivery_orders": ("Vận hành", "Chuyến ↔ DO (một chuyến có thể chở nhiều DO).", ""),
    "transport_trip_legs": ("Vận hành", "Chặng của chuyến: điểm đi/đến, km, tốc độ, dừng, người nhận, mốc.", ""),
    "resource_assignments": ("Vận hành", "Phân công xe/tổ lái cho chuyến trong một khung giờ — cơ sở để khoá lịch và phát hiện trùng.", ""),
    "transport_events": ("Vận hành", "Mốc thực thi: check_in, pickup, departure, arrival, unloading, delivered, lệch tuyến… kèm GPS, ETA.", ""),
    "transport_event_documents": ("Vận hành", "Chứng từ gắn vào mốc thực thi.", ""),
    "vehicle_tracking": ("Vận hành", "Vị trí GPS mới nhất theo DO/xe, km còn lại, ETA.", ""),
    "incidents": ("Vận hành", "Sự cố trên đường theo DO/xe.", ""),
    "parking_lists": ("Bãi xe", "Phiếu bãi xe / packing list của một DO: kiện, khối lượng, khối, trạng thái.", "Trạng thái: draft, ready, parked, gate_in, loaded, dispatched, delivered, cancelled."),
    "parking_list_items": ("Bãi xe", "Dòng hàng của phiếu (từ dòng hàng hoá báo giá).", ""),
    "parking_labels": ("Bãi xe", "Nhãn từng kiện với mã QR.", ""),
    "parking_events": ("Bãi xe", "Lịch sử quét QR / đổi trạng thái của phiếu.", ""),
    "freight_actual_costs": ("Chi phí", "Bảng CHI PHÍ PHÁT SINH của một chuyến đã hoàn tất: tiền tệ, tỷ giá, km kế hoạch/thực, trạng thái, người tạo/duyệt, đảo.", "Trạng thái: draft, submitted, approved, reversed. Chỉ `approved` vào báo cáo."),
    "freight_charge_items": ("Chi phí", "Dòng chi phí: khoản mục, Acc code, kế hoạch, thực tế, phần vượt. Không thuế (thuế do hệ công nợ tính).", ""),
    "freight_cost_documents": ("Chi phí", "Chứng từ của bảng chi phí (URL, checksum, số hoá đơn nhà cung cấp).", ""),
    "epl_expense_vouchers": ("Báo cáo", "Phiếu chi vận tải lập từ chi phí đã duyệt (số phiếu, ngày, hình thức thanh toán).", ""),
    "transport_demands": ("TMS gốc", "Nhu cầu vận chuyển (mô-đun TMS gốc, ngoài luồng Báo giá → DO).", ""),
    "freight_units": ("TMS gốc", "Đơn vị hàng tách từ nhu cầu.", ""),
    "freight_order_units": ("TMS gốc", "Freight Order ↔ đơn vị hàng.", ""),
    "tenders": ("TMS gốc", "Đấu thầu thuê ngoài cho Freight Order.", ""),
    "tender_offers": ("TMS gốc", "Chào giá của nhà vận chuyển.", ""),
    "warehouse_appointments": ("TMS gốc", "Lịch hẹn lấy/giao tại kho.", ""),
    "audit_logs": ("Hệ thống", "Nhật ký kiểm toán: ai làm gì, bảng nào, bản ghi nào, lúc nào, từ IP nào.", ""),
    "idempotency_records": ("Hệ thống", "Cache trả lời theo `Idempotency-Key` để lệnh gọi lặp không tạo hai lần.", ""),
    "schema_migrations": ("Hệ thống", "Các mốc nâng cấp lược đồ đã áp.", "Đầu mốc hiện tại ghi ở đầu tài liệu."),
    "migration_quarantine": ("Hệ thống", "Bản ghi bị cách ly khi nâng cấp không chuyển được.", ""),
}

NHOM_BANG_THU_TU = ["Dữ liệu gốc", "Phân quyền", "Kinh doanh", "Vận hành", "Bãi xe", "Chi phí", "Báo cáo", "Sắp lịch", "TMS gốc", "Hệ thống"]


# =============================================================================
# 3. Sinh tài liệu API
# =============================================================================
def _routes(app):
    for r in app.routes:
        if isinstance(r, APIRoute):
            yield r
        elif hasattr(r, "original_router"):
            for x in r.original_router.routes:
                if isinstance(x, APIRoute):
                    yield x


def _kieu(p):
    if "$ref" in p:
        return p["$ref"].split("/")[-1]
    if "anyOf" in p:
        return " | ".join(_kieu(x) for x in p["anyOf"])
    t = p.get("type", "?")
    if t == "array":
        return "mảng<%s>" % _kieu(p.get("items", {}))
    return {"string": "chuỗi", "integer": "số nguyên", "number": "số", "boolean": "đúng/sai", "null": "trống", "object": "đối tượng"}.get(t, t)


def _khoa_than(src):
    return sorted(set(re.findall(r'(?:data|payload|body|than)(?:\.get\(|\[)"([a-zA-Z_]+)"', src)))


def sinh_api():
    spec = main.app.openapi()
    schemas = spec.get("components", {}).get("schemas", {})
    theo_nhom = {}
    for r in _routes(main.app):
        theo_nhom.setdefault(r.endpoint.__module__, []).append(r)

    out = []
    w = out.append
    w("# Tham chiếu API — EPL Logistics (module vận tải)")
    w("")
    w("Sinh từ mã nguồn đang chạy ngày %s bằng `backend/scripts/sinh_tai_lieu.py`. Bản có mẫu request/response sống: mở `/docs` (Swagger) trên máy chủ." % HOM_NAY)
    w("")
    w("## Cách gọi API")
    w("")
    w("- **Địa chỉ**: `http://<máy chủ>:8001` (máy demo: `http://127.0.0.1:8001`).")
    w("- **Xác thực**: mọi đường đều cần header `Authorization: Bearer <EPL_TMS_API_TOKEN>` (token cấu hình trong `.env` của máy chủ; danh tính ghi nhật ký lấy từ `EPL_TMS_API_PRINCIPAL`). Thiếu hoặc sai → `401 AUTHENTICATION_REQUIRED`. Ngoại lệ công khai: `/`, `/api/health`, `/api/health/database`, `/api/parking-qr/*`, `/uploads/*`, `/static/*`.")
    w("- **Phong bì trả về**: thành công `{\"message\": \"…\", \"data\": …}` (danh sách phân trang: `data.items`, `data.total`, `data.page`, `data.page_size`). Lỗi nghiệp vụ: `{\"detail\": {\"code\": \"MÃ_LỖI\", \"message\": \"câu tiếng Việt\", \"navigation_targets\": [\"màn cần mở\"]}}` — đọc `code` để xử lý, `message` để hiện cho người dùng.")
    w("- **Mã trạng thái**: 200 xong · 201 tạo mới · 401 chưa xác thực · 403 thiếu quyền tài chính · 404 không có · 409 sai bước / bị khoá / trùng lịch / phiên bản cũ · 422 thiếu hoặc sai dữ liệu · 503 lược đồ/DB chưa sẵn sàng.")
    w("- **Idempotency-Key**: các lệnh ghi quan trọng (lập chuyến, điều phối, mốc thực thi, hoàn tất, chi phí) nhận header `Idempotency-Key: <chuỗi duy nhất>`; gọi lặp cùng khoá trả lại đúng kết quả cũ, không tạo hai lần. Cùng khoá mà nội dung khác → `409 IDEMPOTENCY_CONFLICT`.")
    w("- **expected_version**: lệnh đổi trạng thái chuyến/chi phí/cơ hội bắt buộc gửi `expected_version` đọc từ bản ghi hiện tại; lệch → `409 VERSION_CONFLICT` (ai đó vừa sửa, tải lại rồi gửi lại).")
    w("- **Thời gian**: ISO 8601 có múi giờ (`2026-09-10T08:30:00+07:00`); máy chủ lưu UTC. Tiền: số (VND không lẻ), `currency_code` ISO 3 chữ.")
    w("- **Phân trang**: `page` (từ 1), `page_size` (mặc định 50, tối đa 200 tuỳ đường).")
    w("")
    w("## Luồng gọi theo nghiệp vụ (tóm tắt)")
    w("")
    w("1. Dữ liệu gốc: khách → tuyến (km, toạ độ) → loại xe → công thức giá thành (khoản mục + Acc code) → xe (mã loại, hạn pháp lý) → tài xế (bằng lái, ca trực).")
    w("2. `POST /api/crm/opportunities` → `POST /api/crm/opportunities/{ma}/quotation` (báo giá nháp) → `POST /api/quotations/price-preview` (xem giá thành) → `PUT /api/quotations/{qid}/items` → `POST /api/quotations/{qid}/send` (biên mỏng → chờ `internal-approve`) → `POST /api/quotations/{qid}/accept` **→ DO sinh tự động**.")
    w("3. `POST /api/tms/trips/from-delivery-orders` → `PUT /api/tms/trips/{trip_id}/dispatch` → `POST /api/tms/freight-orders/{order_id}/events` (check_in, pickup, departure, arrival) → `POST /api/delivery-orders/{do_id}/complete-delivery` (POD + chốt giá) → `PUT /api/tms/finance/trips/{trip_id}/actual-cost` → `submit` → `approve` (người khác).")
    w("4. Hệ công nợ: `GET /api/handover/delivery-orders` (danh sách) → `GET /api/handover/delivery-orders/{do_id}` (header + chi tiết có Acc code).")
    w("")

    # Mục dành riêng cho bên công nợ — viết tay, đầy đủ trường và ví dụ.
    w("---")
    w("")
    w("## ★ DÀNH CHO BÊN CÔNG NỢ (anh Khang): HAI API BÀN GIAO")
    w("")
    w("> Hai đường này là **toàn bộ** những gì hệ kế toán cần móc vào. Mọi con số đọc từ hồ sơ hoàn tất đã chốt (cùng nguồn với khối \"Hồ sơ đã hoàn tất\" trên màn), nên không có hai con số khác nhau cho cùng một DO. Chỉ DO đã `delivered` mới được trả — hệ này không nhả số chưa chốt.")
    w("")
    w("### ★ API 1 — DANH SÁCH DO đã hoàn tất")
    w("")
    w("`GET /api/handover/delivery-orders`")
    w("")
    w("| Tham số truy vấn | Kiểu | Ý nghĩa |")
    w("|---|---|---|")
    w("| `customer_id` | chuỗi | Chỉ lấy DO của một khách (tuỳ chọn) |")
    w("| `completed_from` | `YYYY-MM-DD` | Hoàn tất từ ngày này, gồm cả ngày đó (tuỳ chọn) |")
    w("| `completed_to` | `YYYY-MM-DD` | Hoàn tất đến ngày này, gồm cả ngày đó (tuỳ chọn) |")
    w("| `page` | số nguyên ≥ 1 | Trang, mặc định 1 |")
    w("| `page_size` | 1–200 | Kích cỡ trang, mặc định 50 |")
    w("")
    w("Trả `data.items[]` (mới hoàn tất trước), `data.total`, `data.page`, `data.page_size`. Mỗi dòng:")
    w("")
    w("| Trường | Ý nghĩa |")
    w("|---|---|")
    w("| `do_id` | Mã lệnh giao hàng — dùng để gọi API 2 |")
    w("| `status` | Luôn `delivered` |")
    w("| `customer_id`, `quotation_id`, `route_id`, `vehicle_id`, `driver_id` | Khách, báo giá gốc, tuyến, xe, tài xế |")
    w("| `selling_price` | Cước theo báo giá (giá gốc đã khoá) |")
    w("| `customer_surcharge_total` | Khách trả thêm lúc giao |")
    w("| `final_selling_price` | **Giá bán cuối** = cước + khách trả thêm |")
    w("| `currency` | Tiền tệ của CƯỚC KHÁCH TRẢ, theo báo giá (VND, USD, LAK…) |")
    w("| `completed_at`, `completed_by` | Lúc chốt hồ sơ, người chốt |")
    w("| `detail_url` | Đường gọi API 2 cho DO này |")
    w("")
    w("Ví dụ: `GET /api/handover/delivery-orders?completed_from=2026-09-01&completed_to=2026-09-30&page_size=100`")
    w("")
    w("### ★ API 2 — HEADER + CHI TIẾT một DO")
    w("")
    w("`GET /api/handover/delivery-orders/{do_id}`")
    w("")
    w("Trả `data.header` và `data.details[]`.")
    w("")
    w("**`header`** — DO là gì và các con số tổng:")
    w("")
    w("| Trường | Ý nghĩa |")
    w("|---|---|")
    w("| `do_id`, `status` | Mã DO, trạng thái (luôn `delivered`) |")
    w("| `customer_id`, `quotation_id` | Khách, báo giá gốc |")
    w("| `route` {`id`,`name`,`origin`,`destination`,`distance_km`} | Tuyến |")
    w("| `origin`, `destination`, `weight_kg`, `volume_m3`, `pallet_count` | Điểm và lô hàng |")
    w("| `pickup_window_*`, `delivery_window_*` | Khung lấy/giao đã hẹn với khách |")
    w("| `trip_id`, `trip_status`, `vehicle_id`, `driver_id`, `co_driver_id` | Chuyến và tổ lái đã chạy |")
    w("| `actual_departure_at`, `actual_arrival_at` | Giờ đi/đến thực tế |")
    w("| `pod_count`, `pod_signed_at`, `pod_receiver` | POD: số bản, giờ ký cuối, người nhận |")
    w("| `price_basis` | Đơn vị cước: `per_trip` mỗi chuyến · `per_kg` · `per_tonne` · `per_m3` · `per_km` |")
    w("| `unit_price`, `billed_qty` | Đơn giá theo `price_basis`, và số lượng tính tiền — dùng để dựng dòng hoá đơn |")
    w("| `selling_price` | Cước báo khách (giá gốc khoá theo báo giá), bằng `currency_thu` |")
    w("| `customer_surcharge_total` | Tổng khách trả thêm, bằng `currency_thu` |")
    w("| `final_selling_price` | **Giá bán cuối** — số lập phiếu thu, bằng `currency_thu` |")
    w("| `quoted_cost`, `quoted_cost_currency` | Giá thành kế hoạch theo báo giá, và đơn vị của nó |")
    w("| `actual_cost_total`, `actual_cost_total_currency` | Giá thành thực tế đã chốt, và đơn vị của nó (thường VND) |")
    w("| `actual_cost_total_quy_doi` | Giá thành thực tế QUY ĐỔI về `currency_thu`; `null` nếu chưa có tỷ giá |")
    w("| `margin_amount`, `margin_percent`, `margin_currency` | Lợi nhuận và biên, tính trong `currency_thu` |")
    w("| `margin_unavailable_reason` | Chuỗi rỗng khi tính được; có chữ khi hai đơn vị khác nhau mà chưa có tỷ giá |")
    w("| `ledger_totals` {`tong_thu`,`tong_chi`,`tong_chi_quy_doi`,`lai_gop`,`currency_thu`,`currency_chi`,`fx_rate`,`khop_gia_cuoi`,`khop_gia_thanh`,`so_dong_thieu_ma`} | Tổng sổ thu–chi và cờ đối chiếu |")
    w("| `cost_formula` {`id`,`name`,`currency`} | Công thức giá thành đã dùng |")
    w("")
    w("**HAI ĐƠN VỊ TIỀN TRONG MỘT HỒ SƠ — đọc kỹ chỗ này.** Cước khách trả ghi bằng tiền của")
    w("BÁO GIÁ (khách Lào trả LAK, khách FDI trả USD), còn chi phí thực tế của chuyến ghi bằng")
    w("tiền CHỨC NĂNG của công ty là VND, vì dầu, BOT, phụ cấp đều chi bằng đồng. Nên:")
    w("")
    w("| Trường | Ý nghĩa |")
    w("|---|---|")
    w("| `currency` | Giữ nghĩa cũ = `currency_thu`. Để mã đang đọc trường này không phải sửa |")
    w("| `currency_thu` | Đơn vị của MỌI số phía THU: `selling_price`, `customer_surcharge_total`, `final_selling_price`, `margin_amount` |")
    w("| `currency_chi` | Đơn vị của MỌI số phía CHI: `actual_cost_total` và các dòng `kind = \"chi\"` |")
    w("| `fx_rate` | Tỷ giá đã dùng: số VND cho MỘT đơn vị `currency_thu`. `null` khi hai bên cùng đơn vị |")
    w("| `fx_rate_source` | `quotation` (tỷ giá báo giá đã khoá với khách — ưu tiên) hoặc `currency_table` |")
    w("")
    w("Quy tắc: **không cộng hay trừ hai số khác `currency`**. Muốn một con số duy nhất thì dùng")
    w("`actual_cost_total_quy_doi` và `ledger_totals.tong_chi_quy_doi`, cả hai đã về `currency_thu`.")
    w("Khi hai đơn vị khác nhau mà không có tỷ giá, hệ trả `null` cho các trường quy đổi và ghi lý")
    w("do ở `margin_unavailable_reason` — KHÔNG bịa một con số lãi.")
    w("")
    w("**`details[]`** — TỪNG DÒNG thu / chi để lập phiếu:")
    w("")
    w("| Trường | Ý nghĩa |")
    w("|---|---|")
    w("| `line_no` | Số dòng |")
    w("| `kind` | `thu` (tiền thu của khách) hoặc `chi` (chi phí công ty) |")
    w("| `currency` | Đơn vị tiền CỦA DÒNG NÀY: dòng `thu` theo báo giá, dòng `chi` theo phiếu chi phí |")
    w("| `acc_code` | **Acc code** — mã tài khoản kế toán bên công nợ, chọn trên khoản mục công thức |")
    w("| `missing_acc_code` | `true` nếu dòng chưa có Acc code (phải bổ sung ở Dữ liệu gốc → Công thức) |")
    w("| `charge_type` | Loại khoản: `fuel`, `driver`, `toll`, `yard`, `freight_revenue`, `customer_surcharge`… |")
    w("| `name` | Tên khoản mục |")
    w("| `planned_amount` | Số kế hoạch (theo công thức / báo giá) |")
    w("| `actual_amount` | Số thực tế đã chốt |")
    w("| `customer_extra` | Phần khách trả thêm (dòng thu) |")
    w("| `variance` | Chênh lệch thực tế − kế hoạch |")
    w("| `source` | Nguồn: `vehicle` (đơn giá của xe), `cost_formula`, `actual_cost`, `quotation`, `customer_surcharge` |")
    w("| `calculation` | Cách tính (ví dụ `96.5 km × 7.728 VND`) |")
    w("| `ref_id` | Mã dòng chi phí / khoản trả thêm gốc để đối soát |")
    w("")
    w("Lỗi: `404 DELIVERY_ORDER_NOT_FOUND`; `409 DO_NOT_COMPLETED` khi DO chưa hoàn tất — hãy đợi DO `delivered` (xem API 1) rồi gọi lại.")
    w("")
    w("Ví dụ rút gọn:")
    w("")
    w("```json")
    w('{"message": "Hồ sơ bàn giao của DO-2026-0008-DO01.",')
    w(' "data": {"header": {"do_id": "DO-2026-0008-DO01", "status": "delivered",')
    w('                     "currency": "USD", "currency_thu": "USD", "currency_chi": "VND",')
    w('                     "fx_rate": 26173.5, "fx_rate_source": "quotation",')
    w('                     "customer_id": "DEMO-CUS-POUYUEN", "quotation_id": "QT-2026-009",')
    w('                     "trip_id": "TRIP-PY-USD-01", "vehicle_id": "DEMO-51C-129.03", "driver_id": "DEMO-DRV-005",')
    w('                     "price_basis": "per_trip", "unit_price": 120.0,')
    w('                     "selling_price": 120.0, "customer_surcharge_total": 15.0, "final_selling_price": 135.0,')
    w('                     "actual_cost_total": 851000.0, "actual_cost_total_currency": "VND",')
    w('                     "actual_cost_total_quy_doi": 32.51,')
    w('                     "margin_amount": 102.49, "margin_percent": 75.92, "margin_currency": "USD",')
    w('                     "margin_unavailable_reason": ""},')
    w('          "details": [{"line_no": 1, "kind": "chi", "currency": "VND", "acc_code": "1091", "missing_acc_code": false, "charge_type": "fuel",')
    w('                       "name": "Chi phí xăng dầu /km", "planned_amount": 344520.0, "actual_amount": 361746.0,')
    w('                       "customer_extra": 0.0, "variance": 17226.0, "source": "actual_cost", "calculation": "44.7 km × 7.708 VND", "ref_id": "…"},')
    w('                      {"line_no": 5, "kind": "thu", "acc_code": "1211", "missing_acc_code": false, "charge_type": "freight_revenue",')
    w('                       "name": "Cước vận chuyển theo báo giá", "planned_amount": 2486000.0, "actual_amount": 2486000.0,')
    w('                       "customer_extra": 0.0, "variance": 0.0, "source": "quotation", "calculation": "QT-2026-001", "ref_id": ""}]}}')
    w("```")
    w("")
    w("---")
    w("")

    thieu = []
    for mod, tieu_de in TEN_NHOM:
        ds = theo_nhom.get(mod, [])
        if not ds:
            continue
        w("## %s" % tieu_de)
        w("")
        for r in sorted(ds, key=lambda x: (x.path, sorted(x.methods)[0])):
            m = sorted(r.methods)[0]
            khoa = "%s %s" % (m, r.path)
            mo_ta, ghi_chu = MO_TA_API.get(khoa, (None, None))
            src = ""
            try:
                src = inspect.getsource(r.endpoint)
            except Exception:
                pass
            if mo_ta is None:
                doc = (inspect.getdoc(r.endpoint) or "").strip().split("\n\n")[0].replace("\n", " ")
                mo_ta = doc or "(chưa có mô tả)"
                ghi_chu = ""
                thieu.append(khoa)
            w("### `%s %s`" % (m, r.path))
            w("")
            w(mo_ta)
            w("")
            # tham số
            duong = [p.name for p in r.dependant.path_params]
            truy_van = r.dependant.query_params
            if duong or truy_van:
                w("| Tham số | Vị trí | Kiểu | Bắt buộc |")
                w("|---|---|---|---|")
                for p in duong:
                    w("| `%s` | đường dẫn | chuỗi | có |" % p)
                for p in truy_van:
                    ann = getattr(getattr(p, "field_info", None), "annotation", None)
                    kieu = getattr(ann, "__name__", str(ann)).replace("Optional", "").replace("typing.", "")
                    fi = getattr(p, "field_info", None)
                    bat_buoc = fi.is_required() if fi is not None and hasattr(fi, "is_required") else bool(getattr(p, "required", False))
                    w("| `%s` | truy vấn | %s | %s |" % (p.name, kieu.strip("[]") or "chuỗi", "có" if bat_buoc else ""))
                w("")
            # thân
            op = spec.get("paths", {}).get(r.path, {}).get(m.lower(), {})
            body = op.get("requestBody", {})
            noi_dung = body.get("content", {}) if body else {}
            schema_ref = None
            for ct, c in noi_dung.items():
                sch = c.get("schema", {})
                if "$ref" in sch:
                    schema_ref = sch["$ref"].split("/")[-1]
                elif sch.get("type") == "object" and sch.get("properties"):
                    schema_ref = None
                    # inline
                    w("Thân yêu cầu (%s):" % ct)
                    w("")
                    w("| Trường | Kiểu | Bắt buộc |")
                    w("|---|---|---|")
                    req = set(sch.get("required", []))
                    for k, v in sch["properties"].items():
                        w("| `%s` | %s | %s |" % (k, _kieu(v), "có" if k in req else ""))
                    w("")
            if schema_ref and schema_ref in schemas and not schema_ref.startswith("Body_"):
                sch = schemas[schema_ref]
                req = set(sch.get("required", []))
                w("Thân yêu cầu — `%s`:" % schema_ref)
                w("")
                w("| Trường | Kiểu | Bắt buộc |")
                w("|---|---|---|")
                for k, v in (sch.get("properties") or {}).items():
                    w("| `%s` | %s | %s |" % (k, _kieu(v), "có" if k in req else ""))
                w("")
            elif schema_ref and schema_ref.startswith("Body_"):
                sch = schemas.get(schema_ref, {})
                req = set(sch.get("required", []))
                w("Thân yêu cầu (multipart/form-data):")
                w("")
                w("| Trường | Kiểu | Bắt buộc |")
                w("|---|---|---|")
                for k, v in (sch.get("properties") or {}).items():
                    w("| `%s` | %s | %s |" % (k, "tệp" if v.get("format") == "binary" else _kieu(v), "có" if k in req else ""))
                w("")
            elif body and not schema_ref:
                khoa_than = _khoa_than(src)
                if khoa_than:
                    w("Thân yêu cầu (JSON) — các trường máy chủ đọc: " + ", ".join("`%s`" % k for k in khoa_than) + ".")
                    w("")
            if ghi_chu:
                w("*Ghi chú:* " + ghi_chu)
                w("")
    if thieu:
        w("---")
        w("")
        w("Các đường chưa có mô tả tay (đang dùng chú thích trong mã): " + ", ".join("`%s`" % k for k in thieu))
        w("")
    return "\n".join(out) + "\n"


# =============================================================================
# 4. Sinh tài liệu lược đồ
# =============================================================================
def sinh_schema():
    from migrations.runner import required_migration_head
    bang = {t.name: t for t in Base.metadata.tables.values()}
    out = []
    w = out.append
    w("# Lược đồ cơ sở dữ liệu — EPL Logistics")
    w("")
    w("Sinh từ `backend/app/models.py` ngày %s bằng `backend/scripts/sinh_tai_lieu.py`. Cơ sở dữ liệu: **PostgreSQL** (duy nhất). Đầu mốc nâng cấp: `%s`. Tổng %d bảng." % (HOM_NAY, required_migration_head(), len(bang)))
    w("")
    w("## Mô hình ba tầng")
    w("")
    w("- **Báo giá (`quotations`)** = thoả thuận với khách: tuyến nào, loại xe gì, giá bao nhiêu. Mọi con số tiền khách thấy có gốc ở đây.")
    w("- **Lệnh giao hàng (`delivery_orders`)** = yêu cầu cụ thể của khách; sinh TỰ ĐỘNG khi khách chấp nhận báo giá, mang giá khoá `unit_price`. Công nợ khách đi theo DO — hồ sơ hoàn tất (`delivery_order_closeouts`) và sổ thu–chi bàn giao theo DO.")
    w("- **Chuyến (`transport_trips`)** = cách công ty thực hiện DO: xe nào, tài xế nào, chạy lúc nào. Chi phí phát sinh (`freight_actual_costs`) ghi ở tầng chuyến rồi phân bổ về DO.")
    w("")
    w("## Những bảng đã xoá (10/09/2026) — không còn trong lược đồ")
    w("")
    w("- Bước Đơn hàng (SO): `sales_orders`, `sales_order_lines`, `sales_order_documents`, cột `so_id` (mốc 049). Báo giá được chấp nhận tách thẳng thành DO.")
    w("- Module kế toán, thuế, kỳ kế toán: `ar_invoices`, `gl_transactions`, `chart_of_accounts`, `journal_batches`, `journal_lines`, `ap_invoices`, `ap_invoice_lines`, `freight_settlements`, `settlement_payments`, `tax_codes`, `accounting_periods` (mốc 051). Hoá đơn và hạch toán là việc của hệ công nợ; hệ này bàn giao qua `GET /api/handover/delivery-orders[/{do_id}]`.")
    w("- Bảng di sản rỗng: `delivery_order_details`, `quotation_details`, `pod`, `shipment_costs` (051), `items`, `uoms`, `price_lists` (052).")
    w("")
    w("## Danh sách bảng theo nhóm")
    w("")
    theo_nhom = {}
    for ten in sorted(bang):
        nhom, chuc_nang, _ = MO_TA_BANG.get(ten, ("Khác", "(chưa có mô tả)", ""))
        theo_nhom.setdefault(nhom, []).append((ten, chuc_nang))
    for nhom in NHOM_BANG_THU_TU + [n for n in theo_nhom if n not in NHOM_BANG_THU_TU]:
        if nhom not in theo_nhom:
            continue
        w("### %s" % nhom)
        w("")
        w("| Bảng | Chức năng | Số cột |")
        w("|---|---|---|")
        for ten, chuc_nang in theo_nhom[nhom]:
            w("| `%s` | %s | %d |" % (ten, chuc_nang, len(bang[ten].columns)))
        w("")
    w("## Chi tiết từng bảng")
    w("")
    for ten in sorted(bang):
        t = bang[ten]
        nhom, chuc_nang, ghi_chu = MO_TA_BANG.get(ten, ("Khác", "(chưa có mô tả)", ""))
        w("### `%s` — %s" % (ten, nhom))
        w("")
        w(chuc_nang + ((" " + ghi_chu) if ghi_chu else ""))
        w("")
        w("| Cột | Kiểu | Bắt buộc | Khoá / tham chiếu |")
        w("|---|---|---|---|")
        for c in t.columns:
            khoa = []
            if c.primary_key:
                khoa.append("PK")
            for fk in c.foreign_keys:
                khoa.append("FK → `%s`" % fk.target_fullname)
            if c.unique:
                khoa.append("duy nhất")
            w("| `%s` | %s | %s | %s |" % (c.name, str(c.type)[:40], "có" if not c.nullable else "", ", ".join(khoa)))
        rang_buoc = [str(getattr(ck, "sqltext", "")) for ck in t.constraints if ck.__class__.__name__ == "CheckConstraint"]
        if rang_buoc:
            w("")
            w("Ràng buộc: " + "; ".join("`%s`" % r[:120] for r in rang_buoc))
        w("")
    return "\n".join(out) + "\n"


def main_():
    docs = os.path.join(GOC, "docs")
    api = sinh_api()
    io.open(os.path.join(docs, "API_REFERENCE_VI.md"), "w", encoding="utf-8").write(api)
    sch = sinh_schema()
    io.open(os.path.join(docs, "DATABASE_SCHEMA_VI.md"), "w", encoding="utf-8").write(sch)
    print("API_REFERENCE_VI.md: %d dòng · DATABASE_SCHEMA_VI.md: %d dòng" % (api.count("\n"), sch.count("\n")))


if __name__ == "__main__":
    main_()
