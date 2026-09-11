# Rà soát hardcode và tính đúng của luồng — 10/09/2026

Bản này trả lời câu của chủ dự án: *"em kiểm tra toàn bộ dự án có chỗ nào hardcode
và luồng mình sai các thứ không, kiểm tra kỹ giúp anh lại xong rùi mình đi sửa
lại UI UX"*.

Rà bốn mũi: hardcode phía giao diện, hardcode phía máy chủ, tính đúng của luồng,
và khớp hợp đồng giữa trình duyệt với máy chủ.

**Trạng thái:** mọi mục ghi **"ĐÃ SỬA"** hoặc **"ĐÃ ĐÓNG"** thì đã làm xong và có
bài kiểm khoá lại; phần còn lại để chủ dự án chọn thứ tự. Ba mục nặng nhất — đường
điều phối lẻ (§B1), đường huỷ chuyến (§B2) và cửa điều phối theo nhãn (§D2) — đã
sửa ngày 10/09 theo yêu cầu *"hoàn chỉnh sửa lỗi 2 cái lỗi này"*.

## Nền: bộ kiểm đang xanh tới đâu

| Bộ | Kết quả |
|---|---|
| Máy chủ, 31 tệp quanh Báo giá / DO / phân tích | 185 xanh · 1 bỏ qua · 0 đỏ |
| Máy chủ, 85 tệp còn lại | 766 xanh · 1 đỏ → **đã sửa**, xem A0 |
| Giao diện | 89 / 89 xanh |

Tổng: **951 bài xanh, 0 đỏ** trên PostgreSQL thật.

---

## A. Lỗi thật, đã sửa trong đợt rà này

### A0. Xoá được loại xe trong khi còn xe thuộc loại đó
`routes/fleet_routes.py` — cửa chặn xoá loại xe chỉ so `Vehicle.type` với **tên**
loại xe. Nhưng `POST /api/vehicles` đã được đổi để chuẩn hoá `type` về **mã**
(`veh.type = khop.id`), nên với mọi xe tạo sau thay đổi đó cửa chặn không khớp gì
cả và loại xe bị xoá tự do — đúng lỗ hổng mà nó được dựng để bịt. Bài kiểm cũ
vẫn xanh vì nó gửi tên, và tên được đổi thành mã trước khi lưu.

Đã sửa: so **cả hai** (mã cho xe mới, tên cho xe cũ). Thêm bài kiểm
`test_khong_xoa_duoc_loai_xe_khi_xe_ghi_theo_MA_loai`.

### A1. DO đã huỷ vẫn nằm trong hàng đợi điều phối
Xem `ra-soat-backend-tron-luong.md` §9.6. Đã thêm rổ riêng `cancelled`.

### A2. Nhãn còn gọi tên bước Đơn hàng đã bỏ
"Giá SO ban đầu" → "Cước theo báo giá"; bỏ ô "SO tham chiếu"; "Tham Chiếu Đơn
Hàng" → "Báo giá gốc (QT)". Sửa cả ba tiếng trong `lang.json`.

### A3. Đường điều phối lẻ tạo ngõ cụt — **ĐÃ ĐÓNG PHẦN GHI**
Xem §B1 bên dưới: mục đó giờ là mô tả lỗi cũ, không còn là việc phải làm.

### A4. Không có đường huỷ chuyến — **ĐÃ THÊM**
Xem §B2 bên dưới.

### A5. Cửa điều phối quyết theo nhãn tiếng Việt — **ĐÃ CHUYỂN SANG LỊCH XE**
Xem §D2 bên dưới.

### A6. Màn Hoàn tất giao hàng: "d is not defined" và hồ sơ đẩy xuống cuối trang — **ĐÃ SỬA**
Lỗi thứ nhất là một dòng tham chiếu `d.so_id` đặt lầm vào `renderDeliveryOrderCloseout`
(không có biến `d`) thay vì `khoiThongTinDOHoSo`; đã dời về đúng chỗ. Lỗi thứ hai
là cả hai khối hồ sơ (biên tập POD ở tab Chờ hoàn tất, hồ sơ ở tab Đã hoàn tất)
được chèn **dưới bảng** rồi cuộn trang xuống — bảng 200 dòng thì hồ sơ nằm đâu
không ai biết. Nay mở thành **hộp thoại nổi** cố định giữa màn, nền tối, cuộn
bên trong, chân khối dính đáy để nút "Hoàn tất giao hàng" luôn thấy, Esc để
đóng, đóng xong bảng còn nguyên chỗ cũ. Bài kiểm:
`frontend/tests/ho-so-hoan-tat-mo-noi.test.js`.

### A7. Màn Đội xe: loại xe hiện MÃ, ô chọn trống; bãi là ô gõ tự do — **ĐÃ SỬA**
Đo được: `GET /api/vehicles` trả `type = DEMO-VT-TRUCK10` (mã, sau khi máy chủ
chuẩn hoá), bảng hiện thẳng cột đó; ô chọn loại xe dựng giá trị theo **tên** nên
mở hồ sơ ra trống. "Bãi / Chi nhánh" và "Mã bãi" là **hai ô gõ tự do**, không có
điểm cuối liệt kê bãi nào; màn Điều phối gom "theo bãi" bằng chuỗi gõ tay —
không hardcode, nhưng gõ lệch một chữ là thành hai bãi.

Đã sửa: máy chủ trả thêm `vehicle_type_id`, `vehicle_type_name` (tra theo mã hoặc
tên — xe cũ còn lưu tên) và `depot_name` (tra danh mục theo mã bãi). Ô loại xe
chọn theo mã, bảng hiện tên. Thêm `GET /api/depots` (bãi = địa điểm loại
Depot/Branch/Warehouse/Yard trong `locations`, kèm số xe / tài xế) và
`POST /api/depots`; ô bãi trên hồ sơ xe là ô chọn từ danh mục, tên tự điền theo
mã; màn Điều phối gom và lọc theo tên bãi trong danh mục. Bãi mới thêm ở Dữ liệu
gốc → Địa điểm.

**Kèm một lỗi lịch xe lộ ra khi soi ảnh 4:** "Xe rảnh 0/9, 9 chạy" trong khi chỉ
6 xe có chuyến — lịch xe còn tính cả chuyến **đã hoàn tất**, và phép hỏi "bây giờ
xe có rảnh không" chỉ nhìn **khung giờ dự kiến**, nên sau một đêm 6 chuyến còn
đang chạy đọc ra thành rảnh. Đã sửa cả hai: chuyến hoàn tất rời khỏi lịch; phân
công còn mở trên chuyến chưa xong giữ xe **bất kể giờ dự kiến** (xe về trễ không
làm xe thành rảnh), và cửa điều phối chặn bằng `RESOURCE_BUSY` nêu tên chuyến.
Đo lại trên máy chủ sống: 6 xe `on_trip` kèm mã chuyến, 3 rảnh.

Bài kiểm: `test_danh_muc_bai_va_loai_xe_tren_ho_so_xe.py`,
`frontend/tests/loai-xe-va-bai-tren-ho-so-xe.test.js`.

### A8. Thiết kế lại màn "Loại xe & Đội xe" (ảnh 5) — **ĐÃ LÀM**
Bản cũ: hai thẻ thư mục to, dưới đó một tiêu đề dài lặp lại đúng chữ trên thẻ
(hai lớp tiêu đề cho một màn); bảng xe 4 cột, trạng thái so chuỗi nhãn; không
lọc theo bãi / loại xe; không số liệu. Bản mới, thay hẳn:

| Phần | Nội dung |
|---|---|
| Đầu trang | một dòng tiêu đề + bộ chuyển tab gọn "Loại xe · Đội xe" kèm số đếm |
| Dải số liệu | Tổng xe · Sẵn sàng · Đang chạy · Bảo dưỡng · Ngoài đội · Sắp hết hạn pháp lý — đếm từ **mã trạng thái thật**, bấm vào là lọc bảng |
| Bảng loại xe | Loại (kèm chip nhiên liệu, mã, kích thước) · Năng lực (tấn · kg · m³ · pallet) · Định mức · Tốc độ KH · Bảo dưỡng/tháng · **Xe thuộc loại** (bấm sang tab Đội xe đã lọc) · Thao tác |
| Bảng đội xe | Biển số (ảnh, hãng) · Loại (tên) · **Bãi** (từ danh mục, kèm mã) · Năng lực (kg · m³ · pallet, cảnh báo vượt chuẩn loại) · **Trạng thái theo mã** kèm chuyến đang giữ · **Hạn pháp lý** gần nhất (đăng kiểm/bảo hiểm, đỏ khi hết, vàng khi < 30 ngày) · Thao tác (ngưng/đưa lại · sửa · xoá) |
| Bộ lọc | tìm chữ · bãi (từ `/api/depots`, bãi lạ trên xe vẫn lọc được) · loại xe · trạng thái theo mã |

Không con số nào ghi cứng; 25 khoá dịch mới đủ Việt–Anh–Lào (tiếng Lào ráp từ
cụm sẵn có). Hai hộp thoại sửa loại xe / sửa xe giữ nguyên. Bài kiểm:
`frontend/tests/man-loai-xe-doi-xe-thiet-ke-lai.test.js`.

### A9. Module Trip: cảnh báo sai, bộ chọn lệnh lộ lệnh đã có chuyến, vận tốc ghi cứng — **ĐÃ SỬA**
- Bảng chuyến gắn "thiếu chặng về" lên **mọi** chuyến một chiều — một chiều không có
  chặng về theo định nghĩa. Nay chỉ xét với khứ hồi / backhaul.
- Hộp thoại Tạo chuyến liệt kê **mọi** lệnh, kể cả lệnh đã giao và lệnh **đã có
  chuyến sống**; chọn nhầm là lập chuyến thứ hai cho cùng một lệnh và tự điền FO
  của chuyến cũ (đo được: `FO-TRIP-…-C14-1` khi tạo chuyến mới cho DO-2026-0014-DO02).
  Nay chỉ đưa ra lệnh chờ điều phối chưa thuộc chuyến nào; không tự điền FO.
- Vận tốc **45 km/h ghi cứng** ở ô và ở payload. Nay lấy từ `avg_speed_kmh` của
  **loại xe trên báo giá** của lệnh, có ghi chú nguồn; không tra được thì để trống
  và chặn khi gửi.

### A10. Gỡ lối vào module Kế toán & tài chính — **ĐÃ GỠ**
Chủ dự án không dùng: bỏ mục menu, gợi ý tìm kiếm, nút bước 7 trong sơ đồ luồng,
nút "Mở Kế toán" trên thẻ mẫu, và hai nút "Qua hạch toán" / "Chuyển đối soát" trên
hồ sơ chuyến — điểm cuối của một chuyến nay là **Hồ sơ đã hoàn tất** (nơi bên công
nợ lấy sổ thu/chi). Màn `#view-accounting` và các điểm cuối máy chủ **vẫn còn**
(không vỡ tham chiếu, bộ kiểm còn dùng), chỉ không còn lối vào.

### A11. Hộp thoại Tạo chuyến — **THIẾT KẾ LẠI**
Đầu xanh trung tính (bỏ dải cam); hai cột: trái là bộ chọn lệnh (tìm được, thẻ đã
chọn), phải là thông số (mã chuyến, loại, chặng về, giờ khởi hành, vận tốc kèm
nguồn, dừng mỗi chặng); dưới là tuyến & chặng với điểm dừng / người nhận và xem
trước giờ dự kiến; chân dính đáy với nút "Tạo chuyến". Ô Freight Order và Version
thành ô ẩn. Chữ có dấu đủ. Bài kiểm: `frontend/tests/tao-trip-hop-thoai-va-logic.test.js`.

### A12. "Trễ hạn" của chuyến đo sai mốc — **ĐÃ SỬA**
Anh hỏi: *"một cái đã hoàn tất tại sao lại gán mác trễ hạn"*. Đo trên dữ liệu demo:
sáu chuyến hoàn tất giao xong 23:09, khách cho phép đến 06:29 sáng hôm sau — vẫn
đỏ. Vì `tripHanGiao` lấy `trip.planned_arrival_at` làm hạn; mốc đó là **kế hoạch
nội bộ** hệ thống tự tính lúc lập chuyến (xuất bến + km/vận tốc + giờ dừng), không
phải hạn với khách. Hạn với khách nằm trên DO: `delivery_window_end`.

Định nghĩa chuẩn từ nay (tính **một chỗ** ở `serialize_trip`, mọi màn đọc chung):
- `delivery_due_at` = khung giao muộn nhất của các DO trên chuyến (hạn khách);
- `is_late` = **đã tới nơi** và tới **sau hạn khách**; `late_minutes` số phút trễ;
- `behind_plan_minutes` = lệch so với kế hoạch nội bộ — chỉ là ghi chú vàng
  "lệch KH +n'" trên bảng, **không** phải trễ hạn.

Ba định nghĩa còn lại của dự án đã đúng và được giữ nguyên: rổ DO `overdue`
(server `_delivery_order_analysis_record`, client `do-board.js`) chỉ xét DO **chưa
lên đường** mà mốc lấy/giao đã qua; màn Theo dõi `overdue` = `delivery_window_end`
đã qua mà DO chưa `delivered/cancelled`; "nguy cơ trễ" = ETA GPS muộn hơn hạn
khách. Bài kiểm: `backend/tests/test_tre_han_theo_han_khach.py`,
`frontend/tests/tre-han-theo-han-khach.test.js`.

### A13. Bảng xếp ca khoá lịch chưa TRỌN hành trình — **ĐÃ SỬA**
Anh hỏi: chuyến 3 ngày (07:00 ngày 1 → về 15:00 ngày 3) có khoá lịch xe, tài xế,
phụ xe suốt khoảng đó không. Đo được: cửa **ghi** (lưu ca tay) đã chặn đúng theo
phân công `ResourceAssignment` [xuất bến, về bãi) cho cả xe, tài xế và phụ xe;
nhưng **bảng hiển thị** (`sap_lich_service.bang_sap_lich`) lấy `planned_arrival_at`
(giờ TỚI NƠI) làm mốc kết thúc → chặng về không tô khoá, xe trông "rảnh" khi đang
về. Sửa: mốc kết thúc = muộn nhất trong `planned_return_at`, `planned_arrival_at`,
`assignment_end` (`ket_thuc_hanh_trinh`). Bài kiểm dựng đúng ví dụ của anh:
`backend/tests/test_khoa_lich_tron_hanh_trinh_nhieu_ngay.py` (6 ca).

Cũng theo yêu cầu: bỏ nút "Thêm / cấu hình ngay" trên tab Xe, tài xế và sắp ca
(đã có nút riêng trên thanh xếp ca); "+ Tài xế / phụ xe" → "Thêm tài xế / phụ xe".

### A14. ETA và thời gian quay đầu — **ĐÃ CÓ, giữ nguyên**
`tms_trip_service._recalculate_eta`: từng chặng `đến = đi + km / vận tốc`, chặng
sau đi sau khi dừng `dwell_minutes`; `planned_arrival_at` = chặng giao cuối,
`planned_return_at` = chặng về cuối. `tms_scheduling_service.forecast_trip_turnaround`
trả `available_at_destination` / `available_at_origin` (xe rảnh ở đích / về bãi),
đọc qua `GET /api/tms/scheduling/vehicle-availability` và hiện ở làn giờ Điều
phối và khối quay đầu tài xế. Vận tốc lấy theo thứ tự **GPS thực → xe → loại xe →
chặng**: hôm nay chưa có GPS nên rơi về vận tốc trung bình cấu hình trên loại xe
(dữ liệu, không phải hằng trong mã); khi có GPS Google Maps chỉ cần đổ
`latest_speed_kmh` vào là ETA tự dùng, không phải sửa công thức.

### A15. Điều phối xe KHÁC loại xe của báo giá — **ĐÃ THÊM CỬA XÁC NHẬN**
Báo giá khoá giá theo *loại xe*; Điều phối chỉ kiểm *đủ tải*. Nên chiếc 40' điều
cho DO báo giá 20' đi qua im lặng: khách trả giá 20', hồ sơ hoàn tất tính chi
theo xe thật, công ty gánh phần lệch mà không ai thấy. Anh duyệt cách sửa: cảnh
báo + bắt xác nhận, **không chặn cứng** (có lúc cố ý lên loại to để gộp chuyến).
- Backend `tms_dispatch_service.loai_xe_lech_bao_gia`: so loại xe (theo mã hoặc
  tên) của xe với `quotation.vehicle_type_id` của các DO trên chuyến; lệch mà
  chưa xác nhận → 409 `VEHICLE_TYPE_MISMATCH` kèm câu giải thích; gửi lại với
  `confirm_vehicle_type_mismatch=true` thì điều được và ghi nhật ký
  `DISPATCH_TRIP_VEHICLE_TYPE_OVERRIDE`. Không đủ dữ liệu (DO tay, báo giá chưa
  chọn loại, xe chưa gán loại) thì không báo lệch.
- Frontend: `normalizeCommandError` giữ `code`; `dieuPhoiCoXacNhanLoaiXe` hỏi
  `confirm` rồi gửi lại — cả hai màn điều phối đi qua hàm này.
- Liên quan: hồ sơ hoàn tất **đã** dùng đơn giá của chiếc xe chạy chuyến
  (`vehicle_cost_overrides`, `rate_source = vehicle|vehicle_type`) — khoá bằng
  `test_ho_so_hoan_tat_dung_gia_cua_xe_chay_chuyen.py`. Cước khách không đổi khi
  chốt xe; chỉ biên lợi nhuận đổi → không có bước báo khách.
- Bài kiểm: `backend/tests/test_dieu_phoi_canh_bao_khac_loai_xe_bao_gia.py`,
  `frontend/tests/dieu-phoi-xac-nhan-khac-loai-xe.test.js`.

### A16. CRM-01 Cơ hội khách hàng & CRM-02 Hồ sơ khách — **MÀN MỚI**
Tài liệu phạm vi (`EPL_Logistics_Functional_Scope_EN.docx`) mở chuỗi bằng "Lead /
Customer → Quotation → …" và tách CRM-01 (Lead / Opportunity) với CRM-02
(Customer Profile). Hệ chưa có; Kanban cũ vẽ từ Đơn hàng (bước đã bỏ) nên đã ẩn.
Anh duyệt: **màn riêng, bảng riêng, đứng trước Báo giá**.
- Bảng `crm_opportunities` (migration 047, model `CoHoiKhach`): khách có mã hoặc
  tên khách tiềm năng, liên hệ, nguồn, tuyến (hoặc điểm đi/đến gõ tay), loại hàng,
  kg/chuyến, chuyến/tháng, giá khách mong muốn, người theo, hẹn liên hệ, ghi chú.
  `stage` là mã chuẩn `new|contacted|negotiating|quoted|won|lost`.
- Luật giai đoạn (`co_hoi_service.CHUYEN_TAY`): `quoted` chỉ do **Lập báo giá**
  đặt; `won` chỉ do **khách chấp nhận báo giá** đặt (móc trong
  `bao_gia_service.khach_chap_nhan`); `lost` phải có lý do.
- **Lập báo giá** (`POST /api/crm/opportunities/{id}/quotation`): sinh báo giá
  NHÁP kế thừa khách (tạo khách nếu chưa có mã), tuyến, kg, chuyến/tháng, ghi chú
  nội bộ "Từ cơ hội LEAD-…"; đòi có tuyến; không lập hai lần. Cơ hội KHÔNG sinh
  DO — không có đường đâm ngang.
- Hồ sơ khách (`GET /api/crm/customers`, `/api/crm/customers/{id}/profile`) gom từ
  bảng thật: cơ hội mở, báo giá theo trạng thái, DO theo trạng thái (kèm Trip),
  doanh thu đã chốt, hoạt động gần nhất — không lưu số tổng.
- Giao diện `#view-co-hoi` + `js/co-hoi.js` + `css/co-hoi.css`: dải KPI bấm để lọc
  (đang mở / cần liên hệ hôm nay / đã báo giá chờ khách / chốt 30 ngày), Kanban 5
  cột kéo-thả (hai mốc có bằng chứng không kéo được), hộp thoại cơ hội, tab Khách
  hàng với ngăn hồ sơ. Menu Kinh doanh: "Khách hàng và cơ hội" đứng trước "Báo
  giá cước" (nhãn cũ "CRM và Kinh doanh" đổi thành "Báo giá cước").
- Gieo demo: `backend/scripts/gieo_co_hoi_demo.py` (5 cơ hội LEAD-DEMO-xx).
- Bài kiểm: `backend/tests/test_co_hoi_khach_hang.py`,
  `frontend/tests/khach-hang-va-co-hoi-man-rieng.test.js`.

### A17. Sắp lại điều hướng, ẩn hai dải, đổi màu chủ đạo — **ĐÃ LÀM**
Theo lời anh (10/09): Vận hành xếp theo luồng **DO → Giao hàng & vận chuyển →
Điều phối → Theo dõi → Hoàn tất** (Packing list cuối); bỏ nhóm "Chuẩn bị nguồn
lực" (xếp ca về Dữ liệu gốc); Trạm kiểm soát AI sang "Báo cáo và khác". Bảng
chọn **Dữ liệu gốc** thành **hai cột, đủ 12 thẻ** (mẫu Golden Enterprise: biểu
tượng trong ô xanh nhạt + tên + một dòng mô tả, `.epl-menu-2col`). Ẩn dải "Danh
mục cấu hình Master Data" và dải gợi ý (Thêm/cấu hình ngay · Tải lại · ?) —
markup giữ lại vì `openMasterSetupStep` và `updateMasterDataGuidance` còn đọc.
Màu chủ đạo → **xanh nước biển**: `#0a6ed1→#2563eb`, `#096fbd→#1d4ed8`,
`#0958a8/#0b5fb5→#1e40af`, thanh trên `#0f1c2e→#0b2e5c`; token khung
`--epl-blue/-2/-3` và `--epl-nav*` đổi theo (426 chỗ trên css/js/html). Bài kiểm:
`frontend/tests/dieu-huong-sap-lai-va-mau-xanh-bien.test.js`.

### A18. Nối API Acc code của bên công nợ + điểm cuối bàn giao DO — **ĐÃ NỐI**
- **API anh Khang**: `GET {gốc}/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true`,
  Bearer JWT — trả 494 tài khoản kế toán Lào (4 cấp, 405 tài khoản được hạch toán).
  Cấu hình bằng ba biến môi trường trong `.env` (chủ dự án tự thêm, không ghi token
  vào mã): `EPL_ACC_CODE_API=https://demo-lao-api.goldensme.com`,
  `EPL_ACC_CODE_TOKEN=<JWT>`, `EPL_ACC_CODE_COUNTRY=11`. `GET /api/acc-codes` gọi sang,
  chuẩn hoá `{code, name (Lào), description (Việt), parent, postable, active}`, giữ bộ
  nhớ 10 phút (`?refresh=true` để tải lại); `Success:false` là lỗi, không phải rỗng.
- **Ô chọn có tìm** (`oChonAccCode` / `moBangChonAccCode`): ô hiện mã đậm + tên
  ngắn; bấm mở bảng có ô tìm theo mã (tiền tố) / tên / diễn giải, lọc "chi tiết"
  (postable) mặc định, Enter chọn dòng đầu, Esc/bấm ngoài đóng, nút Bỏ mã. Thay
  `<select>` 500 dòng.
- **Bàn giao**: `GET /api/handover/delivery-orders/{do_id}` → `{header, details}`
  của DO đã `delivered` (409 `DO_NOT_COMPLETED` nếu chưa); cùng nguồn với khối
  Hồ sơ đã hoàn tất; mỗi dòng detail có `acc_code`, `missing_acc_code`.
- Bài kiểm: `backend/tests/test_acc_code_api_ben_cong_no.py`,
  `backend/tests/test_ban_giao_do_hoan_tat.py`, `frontend/tests/o-chon-acc-code-co-tim.test.js`.

### A19. Huỷ DO phải ghi lý do; DO đã huỷ xoá được; chip Hoàn thành / Đã huỷ — **ĐÃ LÀM**
Anh hỏi "khi huỷ báo giá hay DO có ghi nhận lý do không": **báo giá có**
(`quotations.close_reason`, giờ trả trong `/detail`); **DO thì chưa** — huỷ trắng
qua `PUT /status`. Sửa: cột `delivery_orders.cancel_reason` (migration 048), schema
`DeliveryOrderStatusRequest.reason`, huỷ không lý do → 422 `CANCEL_REASON_REQUIRED`;
màn hỏi lý do bằng `prompt`, hiện "Lý do: …" dưới ô trạng thái. `DELETE
/api/delivery-orders/{id}` giờ cho cả DO **đã huỷ** (gỡ liên kết chuyến đã huỷ/xong;
còn chuyến đang mở thì 409); nút 🗑 chỉ hiện trên dòng đã huỷ. Bảng DO thêm hai chip
**Hoàn thành** và **Đã huỷ** (5 chip, đếm theo `NHOM_DO`). Bài kiểm:
`backend/tests/test_huy_do_co_ly_do_va_xoa_do_da_huy.py`, cập nhật
`huy-lenh-giao-hang-ui`, `lap-ke-hoach-giao-hang-ui`.

### A20. Danh mục Khoản mục ↔ Acc code — **ĐÃ LÀM RỒI HOÀN NGUYÊN**
Đã dựng bảng `cost_item_catalog` + trang Mapping mới + công thức chọn khoản mục, rồi
chủ dự án đổi ý: *"thôi anh thấy không cần thiết — quay về cái cũ"*. Hoàn nguyên trọn:
xoá dịch vụ/điểm cuối/model/migration 049 (đã DROP bảng và gỡ mốc trên DB demo), xoá
`khoan-muc-acc.js`, thẻ Mapping tài khoản về bảng cũ, công thức về **ô chọn Acc code
có tìm trên từng dòng** + "Thêm khoản mục" gõ tay. Giữ lại phần refactor nội bộ
`moBangChonAccCodeChung` (hành vi y cũ).

### A21. "Xem DO" hiện 0 đ, hồ sơ hoàn tất còn "SO nguồn", tiền tệ nhảy USD — **ĐÃ SỬA**
- Khối "Quyết toán chi phí" trong hộp Xem DO đọc giá từ **Đơn hàng (SO)** — DO sinh từ
  báo giá không có SO nên ra 0 đ. Sửa `setDOSettlementFromSource`: báo giá của DO
  (`quotation_id` → `selling_price`, `currency_code`) → `unit_price` của DO → SO chỉ
  cho dữ liệu cũ; nhãn "Theo báo giá QT-…", "Cước theo báo giá", "Xem báo giá".
- Màn Hoàn tất: "SO nguồn" → "Báo giá nguồn" (mã QT), "Theo SO:" → "Theo báo giá:".
- **Tiền tệ**: loại xe Container 20FT có hai công thức USD/VND; không có SO thì
  `_select_closeout_formula` nhận `None` và chọn USD (đứng đầu theo tên) → "1.118.000
  USD" cho báo giá VND. Sửa `delivery_routes`: tiền tệ nguồn = SO hoặc **báo giá**,
  dùng để chọn công thức và làm `currency` của hồ sơ. Bài kiểm:
  `backend/tests/test_closeout_tien_te_theo_bao_gia.py`,
  `frontend/tests/gia-goc-theo-bao-gia-khong-so.test.js`.

### A22. Đơn hàng (SO) — **ĐÃ TRỤC XUẤT KHỎI HỆ THỐNG** (cả hai đợt)
- Chủ dự án: *"SO vẫn còn tồn tại trong hệ thống à? trục xuất nó đi"* → *"dọn cả hai đợt"*.
  Đo trước khi dọn: 0 đơn hàng, 0/16 lệnh giao hàng còn `so_id` trên PostgreSQL demo.
- **Máy chủ**: bỏ mọi điểm cuối `/api/sales-orders*`, `/api/sales-order-documents/*` và
  `POST /api/delivery-orders` (DO chỉ sinh từ báo giá được chấp nhận); bỏ
  `SalesOrder`/`SalesOrderLine`/`SalesOrderDocument` trong `models.py`, cột `so_id` trên
  `delivery_orders`/`delivery_order_details`/`parking_lists`, dịch vụ
  `sales_order_document_service.py`, các nhánh SO trong workflow/closeout/report/AR/AI
  agent/seed. **Migration `049_truc_xuat_don_hang`** DROP ba bảng + ba cột — máy chủ
  8001 đã áp (kiểm `schema_migrations`: `049_truc_xuat_don_hang`, `sales_order%` = 0 bảng).
  Hóa đơn công nợ (AR) trước lấy % VAT từ SO; báo giá không có cột thuế nên VAT = 0 và
  mức thuế do kế toán chốt lúc phát hành (bài kiểm `test_ar_invoice_contract.py` đổi theo).
  Bộ dựng dữ liệu kiểm `workflow_builder.delivery_order(...)` giờ đi đúng đường thật:
  báo giá → duyệt → gửi → khách chấp nhận → DO.
  Packing list lấy dòng hàng từ `quotation_items` của báo giá (không còn
  `delivery_order_details` theo đơn; báo giá vận tải không có SKU nên cột `sku` trống).
  Nhãn `pending` của DO sinh từ báo giá thống nhất là "Chờ vận chuyển"; dữ liệu mẫu:
  có DO thì báo giá ở `accepted`, DO mang `quotation_id` + `unit_price`.
  `v010.validate_postgresql` không kiểm `sales_orders` nữa — trước đó máy chủ 8001 báo
  `DATABASE_SCHEMA_INVALID` ngay sau khi 049 DROP bảng; đã xanh lại.
- **Giao diện**: gỡ hẳn khối `#so-khoi-cu` (bảng + form Đơn vận chuyển), Kanban cơ hội
  chạy bằng SO, CSS kèm theo; ~40 hàm SO trong `app.js` (`saveOracleSO`, `approveSO`,
  `convertQTToSO`, `autoCalculateSOCost`, tài liệu SO…), bước SO trong
  `tms-cockpit-utils.js`, lệnh `salesOrder*` trong bộ thích ứng, 64 khoá `lang.json` mồ
  côi. Sơ đồ luồng: bước 1 = Khách hàng & cơ hội, bước 2 = Báo giá. Form DO cũ từ chối
  tạo mới (POST đã bỏ). Mọi ô "SO" còn lại đọc `quotation_id`.
- **Chưa đụng (không phải tệp của tôi)**: `backend/scripts/run_demo_26_8.py`,
  `run_demo_26_8_p3.py`, `xoa_du_lieu_demo_26_8.py`, `seed_demo_master_data.py`,
  `create_live_delivery_order.py`, `don_du_lieu_thu_nghiem.py`, `generate_system_docs.py`,
  `nang_moc_migration.py`, `don_va_gieo_10_case_demo.py` còn nhắc SO — chạy sẽ hỏng ở
  chỗ đó. Mốc nâng cấp cũ (v001…v030) giữ nguyên vì là lịch sử.

### A23. Báo giá có HAI bản in: nội bộ và phiếu gửi khách — **ĐÃ LÀM**
- Chủ dự án: xuất nội bộ = mọi thông tin để bên mình xem và chốt; gửi khách chỉ các trường
  của form hệ thống cha (trọng lượng, tiền tệ, giá gốc, doanh thu dự kiến, giá gốc sau chiết
  khấu, doanh thu có chiết khấu, ngày nhập). Trước chỉ có một nút "Xem PDF" in cả bảng giá
  thành (xăng dầu, phụ cấp, BOT) — đưa khách là lộ giá thành.
- Nút "In nội bộ" (`xemPdf`): thêm dòng thu của công thức, lợi nhuận + biên, biên mục tiêu,
  giá đối thủ, chiết khấu, hàng hoá, cả ba ô ghi chú; đóng dấu "BẢN NỘI BỘ — không gửi khách".
  Nút "Phiếu gửi khách" (`phieuKhach`): đúng các trường trên, không giá thành/biên/ghi chú nội bộ.
- **Chiết khấu** chưa có trong hệ → migration `050_chiet_khau_bao_gia` thêm
  `quotations.discount_percent` (0..1). Quy ước: `unit_price`/`selling_price` VẪN là giá cuối
  (DO khoá giá, biên, closeout, hoá đơn không đổi); giá gốc trên phiếu = giá cuối / (1 − ck).
  Ô nhập ở mục 5 màn Báo giá; 0 lưu thành null; ≥100% → 422. Bài kiểm:
  `backend/tests/test_chiet_khau_bao_gia.py`, `frontend/tests/phieu-gui-khach-va-ban-noi-bo.test.js`.
- Giải thích (ảnh bảng "5. Cước và giá thành"): "Cước phí vận chuyển /kg" là hàng tử
  `kind=revenue` của công thức — KHÔNG cộng vào giá thành, KHÔNG phải cước báo khách; khi
  hoàn tất DO chỉ mã Acc code của nó được dùng cho dòng thu "Cước vận chuyển theo báo giá", số
  tiền thu là `selling_price` của báo giá. "Cước báo khách" = đơn giá người bán nhập × số lượng
  theo đơn vị cước (gợi ý: giá thành / (1 − biên mục tiêu), hợp đồng, lần trước) — không do
  công thức sinh ra. Đề xuất chưa làm: bỏ dòng /kg khỏi bảng hoặc biến nó thành mốc gợi ý.

### A24. Acc code DÙNG CHUNG theo khoản mục — **ĐÃ LÀM**
- Chủ dự án (hai ảnh): gán 1091 cho "Chi phí xăng dầu /km" ở Container 20FT, sang Xe tải
  thùng 10 tấn cùng khoản mục lại trống, phải chọn lại. Gốc: Acc code được lưu trên từng
  dòng của từng công thức loại xe, không có chỗ dùng chung.
- Cách giải: Acc code là thuộc tính của KHOẢN MỤC. Khoá chung = `key` cho năm khoản mục
  có sẵn (`fuel/driver/toll/wh/rate`), = TÊN chuẩn hoá (bỏ dấu, thường) cho khoản mục tự
  thêm. Bảng chung nằm ở `account_mappings` với tiền tố `khoan_muc::` (không thêm bảng).
  Lúc lưu công thức: dòng trống kế thừa; dòng có mã ghi vào bảng chung và lan sang mọi
  công thức khác (dòng trống hoặc đang theo mã chung cũ). Một khoản mục = một mã; đổi ở
  đâu là đổi chung; chỉ khoản mục mới (tên khác) mới phải chọn. `services/acc_code_chung.py`,
  nối ở `POST /api/cost-formulas`; màn công thức nạp lại sau khi lưu.
- Đã chạy một lượt điền trên DB demo: gom mã đang có vào bảng chung rồi điền vào dòng
  trống của các loại xe khác. Bài kiểm: `backend/tests/test_acc_code_dung_chung_theo_khoan_muc.py`.

### A25. XOÁ HẲN backend bốn module ẩn: Kế toán (AR/AP/sổ cái/thanh toán), Thuế, Kỳ kế toán, Shipment 360 — **ĐÃ LÀM**
- Chủ dự án gật: "xoá thì xoá luôn backend". Migration `051_xoa_ke_toan_thue_ky_ke_toan` DROP 15 bảng
  (ar_invoices, gl_transactions, chart_of_accounts, tax_codes, accounting_periods, journal_*, ap_*,
  freight_settlements, settlement_payments + bốn bảng di sản rỗng delivery_order_details,
  quotation_details, pod, shipment_costs). 8001 đã áp; health xanh.
- Backend bỏ: routes/accounting_routes.py, schemas/invoice.py, services ar_invoice / tms_ap /
  tms_settlement / tms_journal, seed_db.py, seed_full_demo.py; tms_finance_routes chỉ còn chi phí
  phát sinh (/costs, /trips/{id}/actual-cost, items, documents, approve, reverse); finance_master_routes
  chỉ còn account-mappings; tms_money không còn mã thuế (dòng phí = số lượng × đơn giá, thuế do bên
  công nợ tính); dossier Shipment 360 bỏ khỏi operations_routes.
- Thay đổi nghiệp vụ: hoàn tất DO KHÔNG lập hoá đơn AR nữa (bàn giao qua handover API); báo cáo
  doanh thu vận tải đọc `delivery_order_closeouts.final_selling_price` (ngoại lệ `CLOSEOUT_MISSING`
  thay `AR_NOT_POSTED`, cột `closeout_id` thay `invoice_no`); `/api/dashboard/stats` (nay ở
  operations_routes) trả `revenue_ytd` = tổng giá bán cuối hồ sơ hoàn tất, thêm `completed_deliveries`,
  bỏ `booked_revenue_so`/`recognized_revenue_ar`.
- Frontend bỏ: màn `#view-accounting`, `#view-operations-360`, hai thẻ Thuế/Kỳ kế toán, modal thao
  tác tài chính, ~1.300 dòng app.js (Finance cockpit, Shipment 360, dossier), ~900 dòng
  tms-cockpit-utils.js, 12 khoá lang.json; thẻ Dữ liệu gốc đánh số lại 1–9. Bước 7 sơ đồ luồng =
  "Hoàn tất & bàn giao công nợ".
- Tài liệu `docs/API_REFERENCE_VI.md` và `DATABASE_SCHEMA_VI.md` sinh lại từ OpenAPI/models (script
  sinh cũ đã xoá cùng đợt dọn script).

### A26. Rà rác trên DB thật lần cuối — **ĐÃ DỌN**
- Dữ liệu vận hành sạch: 19 báo giá đều có giá; 16 DO đều có `quotation_id` + `unit_price`; 15
  chuyến đều gắn DO; không tuyến 0 km; không bản ghi treo khoá ngoại (xe, tài xế, tuyến, khách);
  không bản/đính kèm báo giá mồ côi; không hồ sơ hoàn tất gắn DO chưa giao.
- Đã xoá: mapping GL `carrier_expense:freight → 6427` (tàn dư AP đã bỏ); 20 bản ghi cache
  idempotency của lần gieo demo 09/09; ba bảng di sản `items`, `uoms`, `price_lists` (1/3/1 dòng,
  không route nào đọc) qua migration 052; công cụ `data_cleanup.py` chạy trên SQLite (+ stub
  `clear_sample_data.py`, bài kiểm) vì dự án chỉ dùng PostgreSQL và nó trỏ vào bảng đã DROP.
- Không đụng, nêu để anh quyết: hai tài xế cùng tên "Trần Quốc Huy" (DEMO-DRV-003 hạng C,
  DEMO-DRV-013 B2 — khác SĐT, khác xe, đều đang chạy chuyến → coi là hai người); 2.088 dòng
  `audit_logs` (1.802 do `demo-dispatcher` gieo 10 case qua API ngày 09/09 — là lịch sử thật của
  lần gieo, xoá hay giữ tuỳ anh); 10/17 địa điểm chưa có toạ độ (thiếu dữ liệu, không phải rác);
  13 bảng rỗng còn lại thuộc module đang có mã đọc/ghi (đấu thầu, đơn vị hàng, phiếu chi báo cáo…).

### A27. Dựng lại dữ liệu từ con số 0 qua API thật; API danh sách DO bàn giao; tài liệu — **ĐÃ LÀM** (11/09)

- Anh chốt: *"xóa hết dựng từ con số 0 … chỉ giữ lại dữ liệu gốc … import dữ liệu chuẩn … đa dạng
  loại và dữ liệu"*. Script `backend/scripts/dung_lai_du_lieu_demo.py`: `--xoa` TRUNCATE 40 bảng
  vận hành trong một giao dịch (848 dòng → 0), trả 9 xe / 14 tài xế về rảnh, xoá 312 tệp đính kèm
  cũ; `--gieo` đi **qua API của máy chủ 8001**, không ghi thẳng DB. Kết quả: 7 báo giá (4 đã tách
  DO, 1 chờ khách bằng USD, 1 bị từ chối, 1 nháp có đính kèm), 7 DO (4 đã giao, 1 đang chạy, 2 chờ
  điều phối), 6 chuyến (3 hoàn tất, 1 đang chạy, 1 kế hoạch, 1 đã huỷ), 3 phiếu chi phí thực tế
  (2 đã gửi duyệt, 1 nháp), 9 cơ hội đủ 6 giai đoạn, 1 Packing List quét đủ 3 bước, 1 sự cố.
- Gieo qua API bắt được **năm cửa chặn thật** đang hoạt động (đều đúng luật, không sửa): hàng nguyên
  khối phải có số niêm phong trước khi xuất bến; chuyến chở 2 DO thì mỗi DO chỉ nộp POD cho chặng
  giao của mình; điều phối phải nằm trong khung lấy–giao của DO; báo giá USD phải khai giá thành
  bằng USD (cửa "báo giá lỗ" so cùng đơn vị tiền); mốc `delivered` đòi chứng từ POD ngay trong sự
  kiện, nên luồng thật ghi mốc tới `unloading` rồi hoàn tất bằng bước POD.
- **Một lỗi thật đã sửa**: huỷ chuyến thiếu `Idempotency-Key` → máy chủ trả `500 Internal Server
  Error` trống, vì `DomainError` ném ở tầng route TRƯỚC khối `try` của `_trip_command` (cùng kiểu ở
  bảy chỗ khác). Bộ kiểm không thấy vì TestClient ném lại ngoại lệ thay vì trả 500. Sửa bằng bộ đón
  toàn cục `@app.exception_handler(DomainError)` trong `main.py` trả đúng phong bì `{error, detail}`;
  bài kiểm `test_domain_error_ngoai_try_thanh_phong_bi.py` đo với `raise_server_exceptions=False`.
- Chi phí thực tế dừng ở `submitted`: bốn mắt đang bật, máy chủ chạy một danh tính duy nhất
  (`EPL_TMS_API_PRINCIPAL` = demo-dispatcher) nên không tự duyệt được — đúng luật.
- Thêm `GET /api/handover/delivery-orders` (danh sách DO đã hoàn tất, lọc khách / ngày, phân trang)
  — API thứ nhất trong hai API anh Khang cần; API thứ hai (header + chi tiết) đã có từ trước.
- Tài liệu: `docs/API_REFERENCE_VI.md` và `DATABASE_SCHEMA_VI.md` sinh lại bằng
  `backend/scripts/sinh_tai_lieu.py` (mô tả tay mọi endpoint, phần ★ bàn giao đặt đầu);
  `docs/HUONG_DAN_LUONG_VA_CAU_HINH_VI.md` mới — thứ tự cấu hình dữ liệu gốc và trọn luồng cho
  người chưa biết hệ.

### A28. "Xem DO" treo 0 VNĐ ở mọi DO; máy chủ nghẹn khi 20 yêu cầu song song — **ĐÃ SỬA** (11/09)

- Anh mở "Xem DO" thấy spinner "Đang chuẩn bị form DO..." treo, mọi ô trống, 0 VNĐ, ở mọi
  trạng thái. Nguyên nhân: khi trục xuất SO, còn sót một vết đọc `id` của biến `so` (đã bị cắt
  định nghĩa) trong `setDOSettlementFromSource`; `moKhungFormDO()` gọi hàm này với nguồn rỗng →
  ReferenceError TRƯỚC khi lệnh tắt spinner được đặt. Bộ kiểm quét chữ không bắt được vì đó là mã
  hợp lệ. Sửa nhãn nguồn đọc `quotation_id`; bài kiểm `gia-goc-theo-bao-gia-khong-so.test.js` nay
  CHẠY THẬT hàm với ba nguồn (rỗng / có báo giá / báo giá không trong bộ nhớ).
- Anh trách *"kiểm tra không kỹ"* — đúng. Em dựng **bài bấm thử bằng máy**: nạp cả `index.html`
  trong jsdom, fetch nối vào 8001 thật, mở 13 màn, 7 DO, 7 báo giá, 9 xe, 14 tài xế, 5 tuyến, mọi
  tab dữ liệu gốc, điều phối, theo dõi, hoàn tất — 98 thao tác, gom mọi ngoại lệ và toast lỗi. Kết
  quả sau sửa: 0 lỗi; không `onclick` nào trong HTML trỏ tới hàm không tồn tại.
- Chính bài bấm thử đó lộ ra **lỗi backend nghiêm trọng hơn**: 20 yêu cầu GET song song → 17 hết
  giờ 45 s, health sau đó 17 s, máy chủ nghẹn vài phút (đo trên 8001 thật). 83 handler khai
  `async def` nhưng gọi SQLAlchemy đồng bộ trên vòng lặp sự kiện; pool 5 + 10 cạn → handler đứng
  chờ kết nối 30 s và chặn cả vòng lặp, coroutine đang giữ kết nối không trả được → kẹt dây chuyền.
  Trình duyệt mở tối đa 6 kết nối nên một người dùng chưa gặp; hai ba người là gặp. Sửa: đổi 83
  handler không có `await` sang `def` (FastAPI chạy trong threadpool), giữ 10 handler có `await`
  thật. Đo lại: 20 yêu cầu song song trả 200 hết trong 0,9 s. Bài kiểm AST
  `test_route_dong_bo_khong_chan_vong_lap.py` chặn tái phạm. Pool giữ 5 + 10 vì mã đã ghi rõ giới
  hạn 100 kết nối của Postgres thật cho ba tiến trình.

---

## B. Luồng có thể đi sai

Xếp theo mức nghiêm trọng. Mỗi mục ghi kịch bản hỏng cụ thể. **B1 và B2 đã sửa**;
từ B3 trở xuống chưa.

### B1. `PUT /api/delivery-orders/{id}/dispatch` đưa DO vào ngõ cụt — **ĐÃ SỬA 10/09**

**Cách sửa: đóng hẳn phần ghi, không vá thêm cửa.** Đường này đã từng được bổ
sung đủ 5 cửa kiểm của điều phối chuyến, nhưng nó vẫn không lập Chuyến và không
tạo phân công — nên vấn đề không phải thiếu cửa mà là nó tạo ra một bản ghi
thiếu xương sống. Chuyến là nơi giữ phân công, chặng và lệnh vận chuyển, tức là
nơi giữ **đường ra**.

Giờ đường này chỉ trả về một câu chỉ dẫn (`DISPATCH_VIA_TRIP_REQUIRED`), nêu
đúng hai bước phải làm và tên chuyến nếu lệnh đã có chuyến. Nó không ghi gì.

Giao diện vốn đã không gọi nó; nay có bài kiểm chặn để không ai gọi lại. Mười
bảy chỗ gọi trong bộ kiểm chuyển sang hàm dùng chung
`conftest.dieu_phoi_qua_chuyen` (đặt khung giờ → lập chuyến → điều phối chuyến).
Bài kiểm: `test_do_lifecycle_contract.py` (hai bài mới), `test_delivery_pod_eta_flow.py`,
`frontend/tests/huy-chuyen-va-dieu-phoi-qua-chuyen.test.js`.

Mô tả lỗi cũ, để sau này đọc lại hiểu vì sao:
`services/workflow_service.py:1338-1477`. Đường điều phối cũ đã được bổ sung 5
cửa kiểm, nhưng nó **không lập Trip và không tạo `ResourceAssignment`**. Nó chỉ
chặn khi Trip *đã* tồn tại.

DO sinh từ báo giá thì chưa có Trip, nên đường này mở đúng cho loại bản ghi mà
luồng mới sản ra. Qua được rồi thì DO ở `in_transit` với xe và tài xế đã gán, và
**không có đường nào ra**: nộp POD báo `POD_LINEAGE_INVALID`, đổi trạng thái sang
`delivered` báo `ATOMIC_COMPLETION_REQUIRED`, không chuyển được sang `cancelled`,
lập Trip thì đòi DO phải `pending`, ghi mốc thì đòi có `ResourceAssignment`.

Hệ quả nặng nhất: **xe và cả hai tài xế bị giữ vĩnh viễn**, và không có API nào
sửa `status` của xe để giải phóng.

*Kịch bản:* người điều phối mở màn DO cũ thay vì màn Chuyến, điều một DO lên xe.
Xe chạy, giao xong. Không ai nộp được POD, không lập được hoá đơn, không đóng
được DO, và xe đó không bao giờ rảnh lại.

### B2. Không có đường nào huỷ một Chuyến — **ĐÃ SỬA 10/09**

**Đã thêm `POST /api/tms/trips/{id}/cancel`.** Huỷ là một phép TRẢ VỀ, không
phải một phép xoá — ba thứ về đúng chỗ:

| Thứ | Về đâu |
|---|---|
| Lệnh giao hàng | `pending`, **không bị xoá** — hàng của khách vẫn còn đó |
| Xe và tổ lái | sẵn sàng, qua chính `release_resources` mà bước hoàn tất dùng |
| Phân công và chặng | `cancelled`, nên lịch xe sạch ngay |

Hai cửa không mở: chuyến **đã hoàn tất / đã quyết toán** thì không huỷ (đó là
sửa sổ sách), và chuyến có lệnh **đã nộp POD hoặc đã giao xong** thì không huỷ
(POD là bằng chứng của một lần giao thật). Lý do huỷ là **bắt buộc**.

Câu báo lỗi khi huỷ lệnh giao hàng cũng sửa theo: trước chỉ nói "không huỷ
được" rồi chỉ sang màn Chuyến — mà lúc đó màn Chuyến không có nút nào. Nay nó
nêu tên chuyến và đúng đường huỷ.

Giao diện: nút **"Huỷ chuyến"** trong khối việc của hồ sơ chuyến, chỉ hiện khi
chuyến còn huỷ được. Bài kiểm: `test_huy_chuyen_van_tai.py` (4 bài),
`frontend/tests/huy-chuyen-va-dieu-phoi-qua-chuyen.test.js`.

Mô tả lỗi cũ:
Không một chỗ nào trong mã ghi `trip.status = "cancelled"`, và không điểm cuối
nào cho phép. Nhưng cửa chặn huỷ DO lại từ chối khi còn Trip chưa `completed`
hoặc `cancelled` — nên nhánh `cancelled` của cửa đó **không bao giờ tới được**.

*Kịch bản:* lập Trip xong, khách huỷ. Huỷ DO → 409 và được chỉ sang màn Chuyến;
màn Chuyến không có nút huỷ. Đường duy nhất còn lại là **xoá cứng** DO (được
phép khi `pending`) trong khi `trip_delivery_orders` vẫn trỏ vào nó — vi phạm
khoá ngoại trên PostgreSQL, hoặc để lại một Chuyến mồ côi.

Trả lời câu "huỷ DO sau khi đã có Trip thì sao": **không có gì xảy ra, vì không
huỷ được**. Chuyến, lệnh vận chuyển, xe và tổ lái đứng nguyên.

### B3. Chuyến chở nhiều DO sinh ra DO không có chặng giao nào
`services/tms_trip_service.py:480` gán chặng cho `do_ids[0]` cho mọi phân đoạn
trừ phân đoạn cuối gán `do_ids[-1]`. Ba DO trên tuyến hai phân đoạn thì
**`do_ids[1]` không có chặng nào**.

Hệ quả: DO đó không nộp được POD (vĩnh viễn `POD_LINEAGE_INVALID`); Chuyến không
bao giờ `completed` nên không ghi được chi phí thực, không có hoá đơn AP, không
quyết toán; xe và tài xế bị tiêu vĩnh viễn.

### B4. `POST /api/tms/trips` bỏ qua toàn bộ cửa kiểm mà đường song song của nó bắt buộc
`create_trip` chỉ kiểm DO **có tồn tại**. Không kiểm `pending`, không kiểm cùng
tuyến, không kiểm khung giờ giao nhau, không kiểm DO đã thuộc Chuyến khác.

*Kịch bản:* gắn một DO đã giao và đã lập hoá đơn vào một Chuyến mới. Bước điều
phối sau đó từ chối, nên Chuyến mới đứng ở `planned` — và vì B2 nó không huỷ
được. DO giờ hiện hai Chuyến trên hồ sơ.

### B5. Báo cáo doanh thu và hồ sơ hoàn tất tính chi phí bằng hai công thức khác nhau
Hồ sơ: `cost_basis = tổng actual_amount`. Báo cáo:
`approved_cost = quotation.total_cost + _cost_total(cost)`.

Và `_cost_total` có một cú thoái lui hỏng: `total_amount` được ghi là **phần
chênh**, nên một dòng chạy đúng kế hoạch có chênh `0`, mà `0` là giá trị giả
trong phép `or`, nên nó thay bằng **toàn bộ số thực tế**. Một chuyến không vượt
khoản nào thì báo cáo cộng gấp đôi chi phí.

*Kịch bản:* chuyến sạch, kế hoạch 2.380.000. Hồ sơ báo lãi trên chi phí
2.380.000; báo cáo doanh thu báo chi phí 4.760.000 và lãi âm — cùng một chuyến.

### B6. `PUT /api/quotations/{id}/approve` bỏ qua bước khoá tỷ giá
Chỉ `POST .../send` đặt `fx_rate`. Đường duyệt cũ không đặt, mà `accept` lại nhận
cả báo giá ở `approved`. Hoá đơn AR sau đó lấy `fx_rate or 1`.

*Kịch bản:* báo giá 1.200 USD đi qua đường duyệt cũ, được chấp nhận, giao xong.
Hoá đơn ghi tỷ giá **1**, nên bút toán vào sổ là 1.200 đồng thay vì ~31.500.000
đồng. Âm thầm, và nó vào thẳng sổ kế toán.

Đường duyệt cũ còn thiếu hai thứ nữa: không cấp `quote_no`, và không ghi bản
lịch sử giá — thứ mà cả `send` và duyệt nội bộ đều ghi.

### B7. Còn nhiều mục mức trung bình
Đơn hàng (SO) vẫn sống ở tầng máy chủ và DO sinh từ nó không mang `quotation_id`
nên **không bị chặn đổi tuyến**; `PUT .../actual-cost` không có `expected_version`
nên hai người sửa cùng lúc thì mất dòng của người trước; không ghi được khoản
**tiêu ít hơn kế hoạch** (bị 422) nên nhân viên buộc phải gõ số kế hoạch; một mốc
`arrival` chuyển **mọi** DO của lệnh vận chuyển sang "đã đến"; `POST /api/incidents`
không đổi gì cả nên xe hỏng vẫn hiện đang chạy; hồ sơ `dossier` chỉ nhìn phía
SO nên với DO của luồng mới nó báo không có báo giá, không có mốc, không có chi
phí — trong khi `closeout` cùng dữ liệu lại trả đúng.

---

## C. Hardcode phía giao diện — chưa sửa

Tin tốt trước: **mọi nhánh bắt lỗi đều hiện trạng thái rỗng hoặc lỗi rõ ràng**,
không nhánh nào bịa số thay thế, và không có `Math.random` trong phần dựng số
liệu.

### C1. Số bịa vẫn hiện ra như số thật
- Cột kho của **mọi** dòng lô hàng là một chuỗi cố định "Kho Tổng Bình Dương",
  và chính chuỗi đó được ghi vào ô ẩn rồi **gửi lên máy chủ** — sai kho vào cơ
  sở dữ liệu.
- Sáu chỗ dùng `|| 30` m³ và `|| 15000` kg làm **mẫu số** cho phần trăm chiếm
  thùng xe và làm thông số xe. Xe thiếu số liệu vẫn hiện một phần trăm nghe rất
  chắc chắn, tính từ 30 m³ bịa ra. Chính tệp đó có một đoạn ghi chú dài nói lỗi
  này đã sửa — sáu chỗ bị bỏ sót.
- Xe không khai loại thì hiện là "Container 20FT".
- Một nút cây phép trên màn dữ liệu gốc tài chính **gửi thẳng lên máy chủ** thuế
  suất 8%, mã số thuế `0312345678` và tài khoản `6427` — dữ liệu gieo nằm trong
  mã giao diện, đúng trường hợp bị cấm.
- Biên lợi nhuận mặc định 15% và ngưỡng màu 20/15% viết cứng, bỏ qua ngưỡng máy
  chủ trả về. Khách đặt ngưỡng 25% vẫn thấy màu xanh trên một báo giá đang lỗ.
- Nhãn ô chọn khẳng định tải trọng: "Container 20FT (15 Tấn)", "40FT (30 Tấn)".

### C2. Ô chọn viết cứng, đáng ra phải đọc từ dữ liệu gốc
Đơn vị tính (**ba bản sao**, và hai bản viết khác nhau), tiền tệ (đã có sẵn
`GET /api/currencies` để nối), quy cách đóng gói, điều khoản thanh toán (hai
danh sách **không trùng nhau chút nào**: 30/60/Cash so với 15/30/45/trả trước),
loại sự cố (**ba bộ từ vựng khác nhau** cho cùng một cột), hạng bằng lái, ca làm
việc (**bốn bản sao**), vai trò tài xế (giá trị lọc "Lái xe" **không bao giờ
khớp** giá trị lưu "Lái xe chính"), loại nhiên liệu, loại hàng, xếp chồng, niêm
phong.

### C3. Số nghiệp vụ nằm cứng trong HTML
Khối Đơn hàng cũ có một dòng hàng đầy đủ giá: đơn giá `1079375`, thành tiền
`16.190.625 VNĐ`, tổng cước `3.500.000`. Hộp thoại DO cũ có sẵn số lượng 1 và
thể tích 33,2 m³ mà **không mã nào xoá**. Bảy thẻ tổng quan mang bảng chứng từ
bịa hoàn toàn (đã gắn nhãn "Mẫu minh họa", và một thẻ đã chuyển sang dữ liệu
thật — nên làm nốt sáu thẻ kia).

---

## D. Hardcode phía máy chủ (§D2 đã sửa)

Tin tốt: **không điểm cuối HTTP nào chạm tới bộ gieo**. Các tệp gieo chỉ được
gọi từ bộ kiểm và từ tệp lệnh dòng lệnh, và có `assert_demo_seed_allowed()`.

### D1. Số bịa ghi vào cơ sở dữ liệu hoặc hiện ra như số thật
- `POST /api/vehicles` ghi **45 km/h** và **30 m³** và hãng **"Hyundai"** vào dữ
  liệu gốc khi payload thiếu trường. Ba con số này sau đó chạy vào phép kiểm
  năng lực và giờ dự kiến như thể đã đo.
- Giờ dự kiến của Chuyến tính từ tốc độ **45 km/h** bịa ra. Đường song song
  (`tms_scheduling_service`) làm đúng: nó **báo lỗi đòi khai tốc độ**. Hai đường
  điều phối, hai chính sách trái nhau.
- Hồ sơ hoàn tất lấy công thức giá thành theo chuỗi thoái lui
  `"DEMO-COST-FORMULA-20FT"` → `"preset-1"` → **dòng đầu tiên bất kỳ**. Trên cơ
  sở dữ liệu của khách, hai cái đầu trượt và nó lấy một công thức ngẫu nhiên —
  âm thầm định giá một lô hàng bằng bảng giá của người khác.
- Hoá đơn AR lấy tỷ giá `or 1` (xem B6). VAT mặc định **10%** ở cột.

### D2. Cửa kiểm so theo NHÃN tiếng Việt — **ĐÃ CHUYỂN SANG LỊCH XE 10/09**

**Nhãn không trả lời được câu hỏi thật của người điều phối.** Ba lý do, và cả
ba đo được:

1. Nhãn là dữ liệu **hiển thị**. Sửa nhãn "Sẵn sàng" trong Dữ liệu gốc là mọi xe
   thành không bao giờ điều được. Bản **tiếng Lào** không khớp chuỗi nào.
2. Nhãn **không có chiều thời gian**. "Sẵn sàng" không trả lời được *xe này có
   rảnh sáng mai từ 6h đến 14h không* — một xe đang chạy hôm nay vẫn rảnh ngày
   mai; một xe rảnh hôm nay có thể đã được đặt cho chuyến chiều mai.
3. Nhãn **trôi khỏi sự thật**. Một đường ghi cũ đặt "Đang thực hiện X" rồi không
   trả lại thì chiếc xe đó rời khỏi đội vĩnh viễn dù không còn phân công nào.

Đã thêm `app/services/lich_xe.py` — một chỗ duy nhất trả lời "xe / tổ lái có
rảnh trong khung giờ này không", đọc **ba nguồn thật đã có sẵn** và đều có chiều
thời gian:

| Nguồn | Trả lời điều gì |
|---|---|
| `resource_assignments` | xe / tài xế đang thuộc chuyến nào, từ giờ nào tới giờ nào |
| `vehicle_maintenance_requests` | xe nằm xưởng (đã duyệt / đang làm) |
| `driver_shift_assignments` | ca làm việc của tổ lái, kèm loại ca (làm / nghỉ) |

Đã bỏ: hai cửa `vehicle.status != "Sẵn sàng"` trong điều phối chuyến và điều
phối lệnh vận chuyển; phép so nhãn rảnh trong `require_crew` (vai trò thì giữ —
`role` là dữ liệu gốc thật, không phụ thuộc giờ). Hai chỉ số của bảng điều khiển
cũng thôi liệt kê cách viết nhãn: số lệnh đang chạy đếm theo `canonical_status`,
số xe đang chạy đếm theo **phân công đang mở**.

**Bước hai (cùng ngày), theo câu của chủ dự án *"cái nhãn thì hardcode quá —
thay bằng loại gì có thể update được thông tin xe"*:** trạng thái vận hành thành
**mã chuẩn lưu trong cột riêng** (mốc `045_trang_thai_van_hanh`):

| Đối tượng | Mã | Ai cập nhật |
|---|---|---|
| Xe | `available` · `on_trip` · `maintenance` · `out_of_service` | hệ thống theo lịch (điều xe, xe về, huỷ chuyến, lịch xưởng); người dùng đặt tay `out_of_service` / `available` |
| Tài xế | `available` · `on_trip` · `off_duty` · `inactive` | hệ thống theo lịch; người dùng đặt tay `off_duty` / `inactive` / `available` |

Kèm `operational_ref` (chuyến / phiếu xưởng đang giữ), `operational_note` (lý do
đặt tay, bắt buộc khi đưa ra khỏi đội), `operational_updated_at`. Đặt tay
`on_trip` / `maintenance` bị từ chối — đó là thứ lịch nói. Không đưa ra khỏi đội
một xe đang chạy chuyến. Đưa lại hoạt động thì **tính lại từ lịch**, không ghi
cứng "available". Hai điểm cuối:
`PUT /api/vehicles/{id}/operational-status`, `PUT /api/drivers/{id}/operational-status`.

Giao diện đọc **mã** rồi tra `lang.json` (13 khoá mới, đủ Việt–Anh–Lào), có nút
"Ngưng hoạt động / Đưa lại hoạt động" trên dòng xe và "Cho nghỉ phép / Đưa lại
làm việc" trên dòng tài xế. Bộ đếm "Xe rảnh" ở màn Điều phối cũng theo mã. Nhãn
chữ cũ (`status`) **vẫn được chiếu từ mã** cho chỗ chưa đổi, nhưng không còn
cửa nào và không còn màn nào quyết định dựa vào chữ.

Backfill một lần từ nhãn cũ đã chạy trên cơ sở dữ liệu demo: 6 xe `on_trip` kèm
mã chuyến, 3 xe `available`, 10 tài xế `on_trip`. Bài kiểm:
`test_trang_thai_van_hanh_theo_ma.py` (5), `frontend/tests/trang-thai-van-hanh-theo-ma.test.js`.

**Phát hiện thêm khi làm, và đã sửa:** bài kiểm khớp schema trước đây tìm chữ
`timezone=true` trong `str(kiểu)` — chuỗi đó không bao giờ có, nên **11 cột lệch
múi giờ thật** (POD, phiếu bãi, phiếu xưởng, nhu cầu vận tải) bị che suốt. Nay
bài kiểm đọc thuộc tính `timezone`; mốc **`046_mui_gio_11_cot`** đổi 11 cột sang
`timestamptz` với `USING … AT TIME ZONE 'UTC'` (quy ước dự án lưu UTC, nên giá trị
trần đang có được hiểu là UTC, không dịch thêm lần nào); 11 tên đã **xoá** khỏi
`LECH_MUI_GIO_DA_BIET`. Đã áp lên cơ sở dữ liệu demo và kiểm lại.

**Cũng sửa cùng đợt:** dữ liệu thử của bài kiểm bảng điều khiển có một dòng
`canonical_status = delivered` nhưng nhãn "In Transit" — chính kiểu trôi giữa nhãn
và mã mà đợt này bỏ; nhãn đã sửa cho khớp mã.

Câu báo lỗi cũng cụ thể hơn: trước nói "đã được phân cho chuyến khác", nay nêu
đúng tên chuyến đang giữ xe.

**Còn lại (chưa sửa):** cửa kiểm xuất bến vẫn phân loại hàng bằng biểu thức
chính quy trên chữ tiếng Việt của quy cách đóng gói — trên bản tiếng Lào mọi đơn
rơi vào "phải quét đủ kiện". Và `crew_policy.is_ready_driver` còn tồn tại cho
vài chỗ hiển thị.

Mô tả lỗi cũ:

Điều kiện điều phối được quyết bằng cách **so chuỗi con nhãn tiếng Việt**: tài xế
rảnh là `"🟢 Rảnh (Sẵn sàng)"`, xe rảnh là `"Sẵn sàng"`, vai trò là
`"lai xe chinh"` / `"phu xe"`. Hai KPI của bảng điều khiển đếm bằng cách **liệt kê
các cách viết nhãn** — nhãn nào không có trong danh sách thì đếm bằng không, ngay
trong điểm cuối mà đầu tệp tự nhận là "100% REAL DYNAMIC CALCULATIONS FROM DB".

Sửa một nhãn thì tài xế thành không bao giờ rảnh. Trên bản tiếng Lào thì **không
một chuỗi nào khớp**. Cột trạng thái chuẩn đã có, kèm cả ràng buộc kiểm tra —
những cửa này bỏ qua nó.

Cùng nhóm: cửa kiểm xuất bến phân loại hàng bằng **biểu thức chính quy trên chữ
tiếng Việt** của quy cách đóng gói. Trên bản tiếng Lào mọi đơn rơi vào "phải quét
đủ kiện" và cửa đó không thể qua.

### D3. Toạ độ và biên giới viết cứng
20 cặp toạ độ của chính các điểm demo, **được ghi vào bảng `locations` khi dùng
lần đầu**, và so khớp bằng chuỗi con **cả hai chiều** — nên một điểm của khách
tên gần giống sẽ âm thầm thừa hưởng toạ độ của EPL. Kèm một **hộp giới hạn chỉ
cho Việt Nam** (8–24°N, 102–110°E) sẽ **loại thẳng toạ độ Lào hợp lệ**.

### D4. Tiền tệ bị đóng vào ba mã
`POST /api/currencies` **trả 422 với mọi tiền tệ ngoài USD/THB/LAK**, và số chữ
số thập phân viết cứng thay vì đọc từ danh mục. Khách giao dịch bằng CNY hay EUR
không nhập được tỷ giá. Đáng ghi nhận: **không có tỷ giá bịa** — thiếu cấu hình
thì nó trả 503, đúng.

### D5. Ngưỡng trùng lặp hai phía
Ngưỡng biên 0,15 / 0,20 có ở máy chủ **và bảy chỗ trong giao diện**. Trần
48 giờ/tuần có hai phía. Mốc "gần trễ" 24 giờ có hai phía. Mỗi cặp là một chỗ
trôi khỏi nhau.

### D6. Trần số dòng viết cứng, cắt im lặng
Khoảng 40 chỗ `.limit(100)` / `le=200`, trong đó có toàn bộ đường xuất dữ liệu.
Khách có hơn 100 hoá đơn xuất ra được 100 dòng và **không có cảnh báo nào**.

### D7. Địa chỉ dịch vụ ngoài viết cứng, không có biến môi trường
Bốn dịch vụ ngoài (tra toạ độ, dẫn đường, tỷ giá) nằm cứng trong mã nguồn, đều
là bậc miễn phí công cộng. Và **chuỗi kết nối cơ sở dữ liệu dạng thật nằm trong
một chuỗi tài liệu của `config.py`** — không chạy, nhưng nên đổi thành ví dụ.
Hai tệp sao lưu cơ sở dữ liệu đầy đủ (kèm tên khách, giá, công thức) đang nằm
trong `backend/scripts/`.

---

## E. Đa ngữ — chưa sửa, quan trọng cho đợt UI tới

| Đo | Số |
|---|---|
| Khoá trong `lang.json` | 1022, đủ cả ba tiếng, không khoá nào thiếu bản dịch |
| `data-i18n` trỏ vào khoá **không tồn tại** | 36 chỗ |
| Đoạn chữ tiếng Việt trong HTML **không có bản dịch nào khớp** | 541 |
| Khoá trong `lang.json` không chỗ nào dùng | 518 |

36 khoá thiếu không làm vỡ màn hình (hàm đổi ngôn ngữ bỏ qua khoá thiếu), nhưng
541 đoạn kia nghĩa là **chuyển sang tiếng Lào thì 541 chỗ vẫn là tiếng Việt**.

---

## F. Nút bấm và phần tử

- **Không nút nào gọi một hàm không tồn tại.** Đây là lớp lỗi khó thấy nhất vì
  người dùng bấm rồi không thấy gì, lỗi chỉ hiện trong console.
- Còn khoảng 40 mã phần tử được mã đọc mà không có trong HTML lẫn trong mã dựng
  — hầu hết là vết của màn báo giá cũ (`qt-*`, `oracle-qt-*`) đã bị thay. Mã
  chết, không gây lỗi, nhưng nên dọn.

---

## Thứ tự đề nghị

1. **B1 và B2** — hai ngõ cụt làm mất hẳn một xe và một tổ lái. Đây là thứ có
   thể xảy ra ngay trên buổi demo nếu ai bấm vào màn DO cũ.
2. **D2** — gom nhãn trạng thái về một mã chuẩn. Đây là điều kiện để hệ chạy
   được trên bản tiếng Lào, và nó chạm vào bảy tệp nên càng để lâu càng đắt.
3. **B5** và **D1 (chuỗi thoái lui công thức giá thành)** — hai chỗ cho ra con số
   tiền sai mà không báo gì.
4. **C1** — bỏ mọi `|| 30`, `|| 15000`, chuỗi kho cố định, và nút gieo dữ liệu
   tài chính.
5. **C2 và C3** — nối ô chọn vào dữ liệu gốc, bóc số nghiệp vụ khỏi HTML.
6. **E** — đa ngữ, làm cùng đợt sửa UI/UX.

Đề nghị thêm một chốt chặn hồi quy: mở rộng bài kiểm
`silent-failure-and-fake-numbers.test.js` để chặn `value="<số>"` trong HTML ngoài
một danh sách cho phép, và chặn `|| 30`, `|| 15000`, `|| 0.15`, `|| 0.20` trong
`app.js`.
