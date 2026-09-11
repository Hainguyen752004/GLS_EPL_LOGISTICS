# Hướng dẫn luồng nghiệp vụ và cấu hình dữ liệu gốc — EPL Logistics

Tài liệu này viết cho người **chưa biết gì** về hệ thống: đọc xong biết hệ làm gì, phải cấu hình
những gì trước, rồi một đơn vận chuyển đi qua từng màn như thế nào, con số tiền ở đâu ra, và cuối
cùng dữ liệu bàn giao cho hệ công nợ ở đâu. Tài liệu kỹ thuật đi kèm: [API](API_REFERENCE_VI.md),
[cơ sở dữ liệu](DATABASE_SCHEMA_VI.md).

---

## 1. Hệ thống này làm gì

EPL Logistics là **module vận tải** (TMS) nằm trong hệ thống lớn hơn của công ty. Nó lo trọn phần
vận tải đường bộ: báo giá cước cho khách, nhận lệnh giao hàng, xếp xe và tài xế, theo dõi chuyến,
ký nhận hàng, chốt giá thành và giá bán cuối. Nó **không** lập hoá đơn, không hạch toán — phần đó
là việc của hệ công nợ (đồng nghiệp anh Khang), hệ này chỉ **bàn giao** hồ sơ đã chốt qua hai API.

Đăng nhập do hệ thống cha lo. Module này nhận token qua header `Authorization: Bearer …`.

### Ba tầng phải nắm trước khi đọc tiếp

| Tầng | Nó là gì | Thuộc về ai | Ví dụ |
|---|---|---|---|
| **Báo giá (QT)** | Thoả thuận với khách: tuyến nào, loại xe gì, giá bao nhiêu | Khách và giá | "Tuyến Bình Dương → Cát Lái, xe cont 20FT, 2.486.000 đ/chuyến, 3 cont" |
| **Lệnh giao hàng (DO)** | Một lô hàng cụ thể khách yêu cầu: lấy lúc nào, giao trước giờ nào | Nhu cầu của khách | 3 cont → 3 DO, mỗi DO một cont |
| **Chuyến (Trip)** | Một chuyến xe thật: xe nào, tài xế nào, chạy lúc nào | Cách công ty thực hiện | DO 1 chạy xe 51C-556.12, tài xế Nguyễn Văn A, 08:00 ngày 12/09 |

Ba quy tắc rút ra từ ba tầng:

1. **DO sinh TỰ ĐỘNG khi khách chấp nhận báo giá.** Không có nút "tạo DO tay", không có bước Đơn
   hàng (SO) ở giữa. Số DO = tổng số lượng ở bảng Hàng hoá của báo giá (1 cont = 1 xe = 1 DO), tối
   thiểu 1.
2. **Giá đã khoá thì không đổi.** DO kế thừa tuyến, báo giá gốc và đơn giá đã khoá. Không đổi được
   tuyến của DO sinh từ báo giá; muốn đổi thì sửa báo giá và sinh lại.
3. **Công nợ đi theo DO, không theo chuyến.** Chi phí chung của chuyến (dầu, BOT) ghi ở chuyến rồi
   phân bổ về từng DO. Hồ sơ hoàn tất và bàn giao đều tính theo DO.

### Tám bước trên thanh điều hướng

| Bước | Màn | Việc chính |
|---|---|---|
| 0 | Master Data & thiết lập nền | Cấu hình dữ liệu gốc (mục 2) |
| 1 | Khách hàng & cơ hội | Ghi cơ hội, theo giai đoạn Kanban |
| 2 | Báo giá cước | Lập giá, duyệt nội bộ, gửi khách, ghi nhận chấp nhận → DO sinh ra |
| 3 | Lệnh giao hàng | Xem DO, bổ sung số niêm phong, lập chuyến |
| 4 | Kế hoạch tuyến đường | Xem tuyến, chặng, đường bộ thật, bãi |
| 5 | Lập lịch & điều phối | Gán xe, tài xế, giờ đi cho chuyến; hệ chặn nếu vi phạm |
| 6 | Giám sát GPS & ký nhận POD | Ghi mốc thực thi, nộp POD |
| 7 | Hoàn tất & bàn giao công nợ | Chốt giá cuối, đối soát chi phí thực tế, hồ sơ bàn giao |

---

## 2. Cấu hình dữ liệu gốc — làm theo đúng thứ tự này

Dữ liệu gốc là thứ **nhập một lần, dùng lâu**. Không có nó thì không báo giá được. Thứ tự dưới đây
là thứ tự phụ thuộc: bước sau cần bước trước.

### 2.1 Khách hàng (`customers`) — tab Khách hàng

Mỗi chủ hàng một mã. Tối thiểu: mã, tên, người liên hệ, điện thoại, địa chỉ. Mọi cơ hội, báo giá,
DO đều trỏ về đây. Khách chưa có mã vẫn ghi cơ hội được (điền `prospect_name`), lúc chốt báo giá
mới bắt buộc có mã.

### 2.2 Địa điểm và tuyến (`locations`, `routes`) — tab Tuyến đường

- **Địa điểm**: bãi xe, kho, cảng, có **toạ độ** (kinh/vĩ độ) để vẽ tuyến và tính giờ đến dự kiến.
- **Tuyến**: điểm đi, điểm đến, **số km**, danh sách chặng (`segments_json`), phí BOT của tuyến.
  Số km là đầu vào quan trọng nhất của giá thành — mọi đơn giá chi phí trong hệ đều quy về **trên 1
  km**. Hệ có thể lấy hình đường bộ thật để vẽ; nếu không có thì vẽ thẳng và ghi rõ.
- Không cho hai tuyến cùng đầu đi–đầu đến trùng nhau (hệ báo trùng).

### 2.3 Loại xe (`vehicle_types`) — tab Loại xe

Báo giá **chốt theo LOẠI xe**, không theo từng chiếc. Mỗi loại: tải trọng tối đa (kg), thể tích
(m³), số pallet, định mức dầu, tốc độ trung bình, khấu hao/km. Ví dụ: Container 20FT, Xe tải thùng
10 tấn, Xe tải 5 tấn.

### 2.4 Công thức giá thành (`cost_formulas`) — tab Công thức

Mỗi **loại xe** có một công thức gồm nhiều **khoản mục**. Mỗi khoản mục có:

| Trường | Ý nghĩa | Ví dụ |
|---|---|---|
| Tên | Tên khoản mục | Chi phí xăng dầu /km |
| Loại (`kind`) | `cost` = chi phí công ty; `revenue` = cước thu của khách | cost |
| Hệ số (`factor`) | `per_km` mỗi km · `per_kg` mỗi kg · `per_tonne` mỗi tấn · `per_trip` mỗi chuyến · `per_stop` mỗi điểm giao | per_km |
| Đơn giá (`rate`) | Số tiền cho một đơn vị hệ số | 7.708 đ |
| **Acc code** | Mã tài khoản kế toán bên công nợ, **chọn từ danh mục** do API bên công nợ cấp | 1091 |

Năm khoản mục có sẵn: xăng dầu /km (`fuel`), phụ cấp tài xế (`driver`), cầu đường BOT (`toll`),
phí bãi/kho (`wh`) — bốn khoản này là **chi phí**; và "Cước phí vận chuyển /kg" (`rate`) là **giá
bán**, không cộng vào giá thành. Có thể thêm khoản mục tự do (vệ sinh thùng, bảo hiểm hàng…).

**Giá thành của một báo giá = tổng các dòng `cost`** sau khi nhân hệ số với số km, số kg, số
chuyến của báo giá đó. Dòng `revenue` chỉ dùng để gợi ý mức giá "Theo công thức".

**Acc code dùng chung theo khoản mục.** Gán Acc code 1091 cho "Chi phí xăng dầu /km" ở Container
20FT thì sang Xe tải 10 tấn, khoản mục cùng tên tự nhận 1091. Đổi mã ở một loại thì mọi loại đổi
theo (một khoản mục = một mã). Bảng dùng chung nằm ở tab Mapping tài khoản, khoá `khoan_muc::…`.
Khoản mục mới (tên khác) thì phải chọn mã mới. Dòng chưa có Acc code sẽ bị đánh dấu
`missing_acc_code` trong hồ sơ bàn giao — bên công nợ không lập phiếu được cho dòng đó.

### 2.5 Xe (`vehicles`, `vehicle_cost_overrides`) — tab Xe

Từng chiếc: biển số, **mã loại xe** (phải trùng một loại ở 2.3), bãi, năng lực, và **ba hạn pháp
lý**: đăng kiểm, bảo hiểm, bảo dưỡng. Xe hết hạn bất kỳ mục nào sẽ **bị chặn điều phối**
(`VEHICLE_LEGAL_EXPIRED`). Xe đang trong phiếu bảo dưỡng cũng không điều phối được.

Công thức giá thành là **hai tầng**: công thức theo loại xe, từng chiếc chỉ **ghi đè vài con số**
(xe cũ tốn dầu hơn → đơn giá dầu riêng). Ghi đè nằm ở `vehicle_cost_overrides`; lúc chốt hồ sơ,
dòng chi ghi `source = vehicle` nghĩa là lấy đơn giá của xe đó.

### 2.6 Tài xế (`drivers`, `driver_qualifications`) — tab Tài xế

Tài xế và phụ xe: bằng lái (hạng, hiệu lực), bãi, tổ, mẫu xoay ca, trạng thái. Bằng hết hạn hoặc
sai hạng → chặn điều phối (`DRIVER_LICENSE_INVALID`). Tài xế phải có **ca trực** trong khung giờ
chuyến (`DRIVER_WORK_SCHEDULE_REQUIRED`), và không được trùng giờ với chuyến khác
(`RESOURCE_TIME_OVERLAP`).

### 2.7 Tiền tệ, nhà vận chuyển, cấu hình tài chính

- **Tiền tệ**: VND là tiền chức năng; báo giá USD/LAK/THB dùng tỷ giá ở tab Tiền tệ, có lịch sử theo
  ngày.
- **Nhà vận chuyển** (`carriers`): đội xe nội bộ hoặc thuê ngoài; dùng khi đấu thầu chuyến (tender).
- **Cấu hình tài chính** (`finance_control_config`): bật/tắt "bốn mắt" (người lập ≠ người duyệt chi
  phí), ngưỡng lệch km cho phép.

### 2.8 Vai trò và người dùng

`roles` giữ danh sách quyền (`finance_read`, `finance_creator`, `finance_approver`…), `users` gắn
người vào vai trò. Người duyệt chi phí thực tế phải khác người lập nếu bốn mắt đang bật.

**Kiểm tra đã đủ dữ liệu gốc chưa:** tab "Thiết lập nền" hiện từng mục còn thiếu; API
`GET /api/health` cũng liệt kê.

---

## 3. Luồng nghiệp vụ từ đầu đến cuối

### Bước 1 — Cơ hội (CRM)

Nhân viên kinh doanh ghi **cơ hội**: khách (hoặc khách tiềm năng), tuyến hoặc điểm đi/đến tự do,
loại hàng, sản lượng dự kiến, giá mong đợi. Cơ hội đi qua các giai đoạn
`new → contacted → negotiating → quoted → won / lost`. Từ cơ hội bấm **Lập báo giá** → hệ tạo báo
giá nháp kế thừa khách, tuyến, sản lượng; cơ hội sang `quoted`. Khi khách chấp nhận báo giá, cơ
hội **tự** sang `won` — không bấm tay.

### Bước 2 — Báo giá cước

Phiếu báo giá gồm: khách, tuyến, loại xe, tải trọng/thể tích/pallet, khung giờ lấy và giao, bảng
Hàng hoá (tên, số lượng, ĐVT), đơn vị cước và đơn giá, hiệu lực, chiết khấu, ba ô ghi chú (nội
bộ, cho khách, cho vận hành).

**Xem trước giá** (`POST /api/quotations/price-preview`): chọn tuyến + loại xe + tải → hệ tính
từng dòng chi phí theo công thức, cho ra **giá thành**, và ba mốc gợi ý giá bán:

- **Biên mục tiêu** (mặc định 20%): giá thành ÷ (1 − 20%).
- **Theo công thức**: tổng dòng `revenue` × số lượng (nếu công thức có dòng thu).
- **Giá đối thủ**, nếu nhập.

Người bán tự điền giá; hệ không tự chảy số vào ô giá. **Biên** = (giá bán − giá thành) ÷ giá bán.

Trạng thái báo giá và cách chuyển:

| Trạng thái | Nghĩa | Chuyển tiếp |
|---|---|---|
| `draft` | Nháp | Gửi khách |
| `pending_approval` | Biên **dưới 15%** → phải duyệt nội bộ trước khi gửi | Trưởng phòng bấm Duyệt nội bộ → `sent`; hoặc Trả về nháp |
| `sent` | Đã gửi khách, có số báo giá (`quote_no`) | Khách chấp nhận → `accepted` + DO sinh; Khách từ chối → `rejected`; quá hiệu lực → `expired` (Gia hạn để quay lại `sent`) |
| `accepted` → `split` | Khách chấp nhận; hệ **sinh N DO ngay trong cùng giao dịch** và ghi `split` | Kết thúc tầng báo giá |
| `rejected` / `expired` | Đã đóng | — |

Ngưỡng 15% và mục tiêu 20% là cấu hình công ty; cột `target_margin` trên báo giá ghi đè theo khách.
Chiết khấu (`discount_percent`) giảm doanh thu nhưng không đổi giá thành.

**Hai bản in:** bản **nội bộ** (đủ giá thành, biên, gợi ý, ghi chú nội bộ) và **phiếu khách** chỉ có
các trường của hệ thống cha: trọng lượng, tiền tệ, giá gốc, doanh thu dự kiến, giá gốc sau chiết
khấu, doanh thu có chiết khấu, ngày nhập.

### Bước 3 — Lệnh giao hàng (DO) sinh tự động

Khi bấm "Khách chấp nhận" (`POST /api/quotations/{qid}/accept`), hệ:

1. Kiểm tra báo giá đang `sent` và còn hiệu lực (hết hạn → `QUOTATION_EXPIRED`).
2. Sinh N DO, N = tổng số lượng bảng Hàng hoá. Mỗi DO kế thừa: khách, tuyến, báo giá gốc, đơn giá
   khoá (`unit_price`), hàng hoá, khung giờ. Giờ lấy DO thứ i lệch 2 giờ trong khung lấy (một đội
   xe không lấy hai cont cùng lúc), hạn giao là cuối khung giao.
3. DO ở trạng thái `pending` ("Chờ vận chuyển"). Mã DO dạng `DO-<năm>-<số>-DO01…`.

Người ở bãi bổ sung **số niêm phong** (`seal_no`) và ghi chú tài xế trước điều phối. Không đổi
tuyến của DO; chỉ huỷ DO khi khách rút (huỷ từng DO, không đóng báo giá đã tách).

### Bước 4 — Lập chuyến (Trip)

Mỗi DO đi tới điều phối **phải có chuyến**. Từ màn Lệnh giao hàng chọn một hoặc nhiều DO **cùng
khách, cùng tuyến, cùng loại xe** → "Lập chuyến" (`POST /api/tms/trips/from-delivery-orders`). Hệ
tạo chuyến `planned` với các chặng (leg) lấy–giao theo tuyến; DO khác nhau về tuyến/loại xe không
ghép được (`DELIVERY_ORDERS_INCOMPATIBLE`). Có thể thêm chặng về (backhaul) nếu có DO chiều về.

### Bước 5 — Điều phối

Màn Điều phối xếp **xe + tài xế (+ phụ xe) + giờ xuất bến** cho chuyến
(`PUT /api/tms/trips/{trip_id}/dispatch`). Hệ chặn, không cho lách:

| Điều kiện | Mã lỗi |
|---|---|
| Xe đúng loại xe của báo giá | `VEHICLE_TYPE_MISMATCH` (ghi đè có lý do thì cho phép) |
| Xe còn hạn đăng kiểm, bảo hiểm, bảo dưỡng | `VEHICLE_LEGAL_EXPIRED` |
| Tải trọng/thể tích/pallet của các DO không vượt xe | `CAPACITY_EXCEEDED`, `VEHICLE_CAPACITY_UNDECLARED` |
| Tài xế có bằng đúng hạng còn hiệu lực | `DRIVER_LICENSE_INVALID` |
| Tài xế có ca trực trong khung giờ, đúng xe của ca | `DRIVER_WORK_SCHEDULE_REQUIRED`, `SHIFT_VEHICLE_MISMATCH` |
| Xe và tài xế không trùng giờ chuyến khác | `RESOURCE_TIME_OVERLAP`, `VEHICLE_SHIFT_OVERLAP` |
| Không xếp cùng người hai vai | `CREW_DUPLICATE` |
| Kho có lịch hẹn (nếu tuyến yêu cầu) | `WAREHOUSE_APPOINTMENT_REQUIRED` |

Điều phối xong: chuyến `in_transit`, các DO `in_transit`, lệnh vận chuyển `dispatched`. Lệnh ghi
cần `Idempotency-Key` (bấm hai lần không tạo hai lần) và `expected_version` (ai sửa trước thì
người sau phải tải lại).

Màn còn có **Sắp lịch** (gợi ý xe/tài xế rảnh theo bãi và ca), **Đấu thầu** (mời nhà vận chuyển
ngoài chào giá khi đội xe không đủ) và **Danh sách đỗ xe / QR bãi** (quét vào–ra bãi).

### Bước 6 — Thực thi và theo dõi

Tài xế hoặc điều phối ghi **mốc thực thi** theo đúng thứ tự
(`POST /api/tms/freight-orders/{order_id}/events`):

`check_in` (vào bãi) → `pickup` (lấy hàng) → `departure` (xuất bến) → `arrival` (đến) →
`unloading` (dỡ) → `delivered` (giao xong)

Sai thứ tự → `EVENT_SEQUENCE_INVALID`; giờ lùi → `EVENT_TIME_REGRESSION`; giờ tương lai →
`EVENT_TIME_FUTURE`. Mốc có thể kèm ảnh chứng từ. Vị trí GPS ghi vào `vehicle_tracking`, màn Theo
dõi vẽ trên bản đồ, so với hình tuyến, tính lệch giờ. Sự cố ghi ở `incidents`.

**POD** (phiếu giao hàng có chữ ký người nhận) nộp ở bước hoàn tất bên dưới, cho **từng chặng
giao** của DO; xe trên POD phải khớp xe đã điều. Tối đa 10 MB, JPG/PNG/PDF. Xem lại POD đã nộp:
`GET /api/pod/{do_id}`, `GET /api/pod-records`.

### Bước 7 — Hoàn tất giao hàng và chốt giá

`POST /api/delivery-orders/{do_id}/complete-delivery` — gửi dạng **multipart form**: ô `payload` là
JSON, các ô còn lại là file. DO phải `in_transit`, chuyến phải `in_transit`. Trong `payload`:

- `trip_id`, `currency_code`.
- `pod_entries[]`: mỗi chặng giao một dòng {`leg_id`, `file_field` (tên ô file POD),
  `signature_file_field` (tên ô ảnh chữ ký), người nhận, giờ ký}. Thiếu chặng nào → `POD_LINEAGE_INVALID`.
- `charge_adjustments[]`: **khách trả thêm** (chờ bãi, bốc xếp thêm…), mỗi dòng có tên, lý do,
  `increase_amount`.

Hệ tạo **hồ sơ hoàn tất** (`delivery_order_closeouts`): giá gốc khoá theo báo giá
(`base_selling_price_snapshot`), tổng khách trả thêm, **giá bán cuối** = gốc + trả thêm, tiền tệ,
người và giờ chốt. Đây là **con số duy nhất** bên công nợ dùng để lập phiếu thu. DO sang
`delivered`; khi mọi DO của chuyến đã giao, chuyến sang `completed`.

Hồ sơ không có giá gốc (DO gõ tay, không có báo giá) → `BASE_PRICE_MISSING`, không chốt được. Đó là
lý do không có đường tạo DO tay.

### Bước 8 — Chi phí thực tế của chuyến (đối soát giá thành)

`PUT /api/tms/finance/trips/{trip_id}/actual-cost` tạo phiếu chi phí thực tế `draft`: từng dòng
khoản mục (dầu, BOT, phụ cấp, bãi…) với số tiền thật, chứng từ đính kèm. Người lập **gửi duyệt**
(`submitted`), người **khác** duyệt (`approved`) nếu bốn mắt bật. Chi phí chung của chuyến phân bổ
về từng DO theo tỷ lệ. Số đã duyệt là `actual_cost_total` trong hồ sơ; chưa duyệt thì hồ sơ dùng
giá thành kế hoạch theo công thức (`quoted_cost`) và ghi rõ nguồn.

Phiếu chi nội bộ nhỏ (`epl_expense_vouchers`) gắn theo DO cũng nằm ở tầng này.

### Bước 9 — Bàn giao cho hệ công nợ

Khối **"Hồ sơ đã hoàn tất"** ở màn Hoàn tất liệt kê từng dòng thu/chi. Cùng dữ liệu đó, hệ công nợ
lấy qua hai API (chi tiết ở đầu [API_REFERENCE_VI.md](API_REFERENCE_VI.md)):

1. **`GET /api/handover/delivery-orders`** — danh sách DO đã `delivered`, lọc theo khách và khoảng
   ngày hoàn tất, phân trang. Quét định kỳ (ví dụ mỗi đêm lấy `completed_from` = hôm qua).
2. **`GET /api/handover/delivery-orders/{do_id}`** — `header` (khách, tuyến, báo giá, chuyến, xe, tài
   xế, POD, giá bán cuối, giá thành, biên) + `details[]` từng dòng `thu`/`chi`, mỗi dòng có
   `acc_code`, số kế hoạch, số thực tế, chênh lệch, nguồn, cách tính.

Chỉ DO đã chốt mới trả; DO chưa `delivered` → `409 DO_NOT_COMPLETED`. Dòng thiếu Acc code có
`missing_acc_code = true` — quay lại tab Công thức chọn mã rồi gọi lại, không sửa tay số.

---

## 4. Con số tiền: ở đâu ra và ai được đổi

| Con số | Sinh ở | Ai đổi được | Khoá khi |
|---|---|---|---|
| Giá thành kế hoạch (`quoted_cost`) | Xem trước giá: công thức loại xe × km/kg/chuyến, cộng ghi đè của xe | Người sửa công thức (ảnh hưởng báo giá mới) | Báo giá gửi khách |
| Giá bán (`unit_price`) | Người bán điền, tham chiếu ba mốc gợi ý | Người bán khi `draft` | Khách chấp nhận → DO kế thừa |
| Biên | (giá bán − giá thành) ÷ giá bán | — | Dưới 15% phải duyệt nội bộ |
| Chiết khấu | Người bán | Người bán khi `draft` | Gửi khách |
| Khách trả thêm | Lúc hoàn tất DO | Điều phối lúc hoàn tất | Hồ sơ chốt |
| **Giá bán cuối** | Hồ sơ hoàn tất = gốc + trả thêm | Không ai | Ngay khi chốt |
| Chi phí thực tế | Phiếu chi phí chuyến | Người lập → người duyệt | `approved` |

---

## 5. Câu hỏi thường gặp

**Sao màn Lệnh giao hàng trống?** Chưa có báo giá nào được khách chấp nhận. DO không tạo tay.

**Sao không điều phối được?** Đọc `code` trong lỗi: xe hết hạn pháp lý, tài xế không có ca, trùng
giờ, vượt tải… Sửa dữ liệu gốc (xe/tài xế/ca) rồi bấm lại, không có đường bỏ qua.

**Sao hồ sơ bàn giao có dòng "thiếu Acc code"?** Khoản mục trong công thức chưa chọn mã. Vào tab
Công thức chọn mã một lần; mọi loại xe cùng khoản mục nhận theo, và hồ sơ đọc lại sẽ đủ.

**Sao báo giá không gửi được mà nằm ở "chờ duyệt"?** Biên dưới 15%. Trưởng phòng duyệt nội bộ
(quyết định bán dưới ngưỡng) hoặc trả về nháp để sửa giá.

**Sao hai con số giá bán ở màn và ở API bàn giao luôn giống nhau?** Vì cả hai đọc cùng một bảng
`delivery_order_closeouts`, không tính lại.

**Muốn đổi tuyến của DO?** Không được. Đổi tuyến là đổi giá đã gửi khách. Sửa báo giá (trả về nháp
nếu chưa gửi, hoặc lập báo giá mới), khách chấp nhận lại → DO mới; huỷ DO cũ.

**Muốn dựng lại dữ liệu demo?** Chạy `backend/scripts/dung_lai_du_lieu_demo.py` (xem chú thích đầu
script): bước 1 xoá sạch dữ liệu vận hành nhưng giữ dữ liệu gốc; bước 2 gieo các case đi trọn luồng
**qua API thật** của máy chủ đang chạy, nên mọi cửa chặn và mọi con số đều là của luồng thật.

---

## 6. Sơ đồ tóm tắt

```
Dữ liệu gốc: Khách → Địa điểm/Tuyến(km) → Loại xe → Công thức(khoản mục + Acc code) → Xe(hạn pháp lý) → Tài xế(bằng, ca)
                                                        │
Cơ hội (new…quoted) ──Lập báo giá──► Báo giá draft ──gửi──► [biên <15%? pending_approval → duyệt nội bộ] ──► sent
                                                        │
                                          Khách chấp nhận (cùng giao dịch) ──► accepted/split + N DO (pending)
                                                        │
                            Chọn DO cùng khách/tuyến/loại xe ──► Trip planned ──điều phối (xe, tài xế, giờ; các cửa chặn)──► in_transit
                                                        │
                    check_in → pickup → departure → arrival → unloading → delivered ; POD từng chặng ; GPS
                                                        │
                            Hoàn tất DO (khách trả thêm) ──► Hồ sơ hoàn tất: giá bán cuối ; DO delivered ; Trip completed
                                                        │
                            Chi phí thực tế chuyến draft → submitted → approved (bốn mắt) → phân bổ về DO
                                                        │
                      Hệ công nợ: GET /api/handover/delivery-orders  →  GET /api/handover/delivery-orders/{do_id}
```
