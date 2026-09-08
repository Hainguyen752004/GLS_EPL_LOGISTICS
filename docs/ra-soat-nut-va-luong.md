# Rà soát toàn bộ luồng, từng module, từng nút

Ngày rà: 09/09/2026 · rà trên mốc `ddcf882`

Bản này trả lời ba câu: **luồng có liền không**, **nút nào nói dối hoặc không làm
gì**, và **chức năng nào đã viết ở máy chủ mà không có màn nào gọi tới**.

Mọi con số dưới đây **đo được**, không đọc bằng mắt. Cách đo: nạp `index.html`
cùng toàn bộ 12 tệp JS vào một trình duyệt giả (jsdom), gọi `switchView` cho từng
màn, rồi hỏi từng nút một. Chỗ nào không chắc thì **bấm thật vào nút** và đo xem
có gọi máy chủ, có đổi DOM, hay có ném lỗi. Đọc mã bằng mắt đã cho tôi kết quả
sai ba lần trong lần rà này, nên tôi bỏ hẳn cách đó.

---

## 1. Kết luận trong một trang

| Hạng mục | Kết quả |
|---|---|
| Số màn | 13 |
| Nút tĩnh người dùng thấy được | **142** |
| Nút do JS vẽ ra khi có dữ liệu | **211** thuộc tính `onclick` (287 chuỗi `<button` ở 12 tệp) |
| Tên hàm xử lý phân biệt | **122**, tất cả đều có thật trên `window` |
| **Nút trỏ vào hàm không tồn tại** | **0** |
| **Nút không nối gì cả** | **0** |
| Lỗi JS khi mở lần lượt 13 màn | **0** |
| Điểm cuối máy chủ | **200** trên 17 module |
| **Điểm cuối không màn nào gọi** | **20** |
| **Nút dư (khối cũ đã bị thay mà còn nằm lại)** | **25** trong 4 khối |
| Nút nói dối đã bỏ trong lần rà này | 3 (+ 8 nút "Lưu" đã bỏ ở lần trước) |
| Bước luồng bị thiếu đã thêm | 1 — "Xác nhận xe đã về bãi" |

**Ba việc nên làm, theo thứ tự tôi đề nghị:**

1. **Làm màn khai giấy phép tài xế.** Đây là lỗ nặng nhất tìm được — xem §5.2.
   Giấy phép **chặn điều phối**, mà không có màn nào khai được nó. Điều phối bị
   chặn hiện chỉ sửa được bằng tệp lệnh hoặc sửa thẳng cơ sở dữ liệu.
2. **Bỏ 4 khối cũ (25 nút).** Xem §4. Không mất tính năng nào.
3. **Chốt phận cho module đấu thầu.** 8 điểm cuối đã viết xong ở máy chủ, chưa
   bao giờ có màn. Xem §5.1 — tôi nêu cả phương án **bỏ**, không mặc định giữ.

---

## 2. Luồng chính — có liền không

Luồng của hệ thống hiện nay là:

```
Dữ liệu gốc → Báo giá (QT) → duyệt → tách thành Lệnh giao hàng (DO)
   → lập Chuyến (Trip) → điều phối xe → các mốc giao hàng
   → POD → Hoàn tất & chốt giá → Hoá đơn AR → Phiếu chi phí thực tế → Báo cáo
```

**Không còn bước Đơn hàng (SO).** Bước đó đã bỏ ở mốc `7c445d1`; báo giá tách
thẳng ra lệnh giao hàng.

Luồng này đã chạy trọn A→Z trên dữ liệu thật: **68 điểm kiểm, 0 điểm đỏ**, và bộ
10 case demo hiện có (`docs/du-lieu-luong-demo.md`) đi hết từ báo giá tới báo
cáo. Doanh thu 8.081.400 đ · giá thành 5.298.531 đ · lãi gộp 34,44%.

**Một bước từng bị thiếu và đã thêm:** chuyến xe giao xong không có đường nào ghi
nhận "xe đã về bãi", nên chuyến treo mãi ở trạng thái đang chạy và xe không bao
giờ rảnh lại để điều phối tiếp. Đã thêm nút **"Xác nhận xe đã về bãi"** cùng hàm
`xacNhanXeDaVe`.

---

## 3. Đã sửa trong lần rà này

| Nút / chỗ | Vấn đề | Đã làm |
|---|---|---|
| "Post" trên thẻ minh hoạ ở Bảng điều khiển | Ghi **một hoá đơn thật** cùng bút toán sổ cái, cho lệnh giao hàng nó **tự chọn** bằng "lệnh đã giao đầu tiên tìm thấy" | Bỏ nút, rồi bỏ luôn hàm `postInvoice` (mốc `ddcf882`) và chốt bằng bài kiểm |
| "Print" trên thẻ đó | Không nối gì | Bỏ, kèm chú thích vì sao |
| "Submit" trên thẻ "BÁO CÁO SỰ CỐ" | Ghi một sự cố **thật**, nhưng đọc giá trị từ form sự cố ở **màn khác** — mọi ô của thẻ này đều `disabled`, nên bấm là ghi một sự cố rỗng | Thay bằng nút đi tới màn thật |
| Thẻ "SALES ORDER" ở Bảng điều khiển | Bước SO đã bỏ khỏi luồng | Bỏ thẻ, dọn khoá `lbl_form_2_so` trong `lang.json` |
| 8 thẻ ở Bảng điều khiển | Chỉ 5 trong 8 thẻ có nút mở màn thật → người xem không suy ra được thẻ nào mở được | 7 thẻ còn lại, **mỗi thẻ đúng một nút** |
| `switchView('crm-sales')` | Gọi `loadQuotations()` của màn báo giá **cũ** | Bỏ lệnh gọi; màn mới tự nạp danh sách của nó |

Hai mốc liên quan: `a65c69f` (rà soát nút, bỏ hai nút nói dối, thêm bước xác nhận
xe về) và `ddcf882` (bỏ `postInvoice`, thêm hai bài kiểm).

---

## 4. Nút dư — 25 nút trong 4 khối cũ

Đây là **phát hiện chính** của phần rà soát nút. Bốn khối này là giao diện **đã
bị thay**, nhưng phần markup cũ vẫn nằm trong `index.html`, chỉ bị `hidden` che
đi. Người dùng không thấy chúng, nên chúng không gây lỗi — nhưng chúng làm tệp
phình ra, và nguy hiểm hơn: **lần sau có người bỏ `hidden` đi là cả một màn cũ
hiện lại**, ghi vào cùng cơ sở dữ liệu bằng luồng đã bỏ.

Cần phân biệt rõ với **khối bị che có chủ đích** — hộp thoại, bảng chi tiết mở
theo yêu cầu, tab chưa mở (`trip-return-action-modal`, `dispatch-detail`,
`completion-editor`, `md-tab-*`…). Những khối đó **bình thường**, không phải nút
dư, và tôi không tính vào 25.

### 4.1 `qtv2-khoi-cu` — 7 nút · màn Báo giá cũ

Đã bị thay hẳn bởi `#qtv2-root` (`bao-gia-v2.js`) ở mốc `629b80e`.

| Nút | Hàm |
|---|---|
| Làm Mới | `loadQuotations` |
| + Tạo Báo Giá Cước | `openOracleQTForm` |
| Tìm Kiếm | `filterQuotations` |
| (nút đóng) · Hủy bỏ | `closeOracleQTForm` |
| Duyệt Báo Giá Cước | `approveQuotation` |
| Lưu Báo Giá Cước | `saveOracleQT` |

Bảy hàm này vẫn còn được nhắc ở chỗ khác trong `app.js`, nên **bỏ được markup
trước, hàm dọn sau** — phải lần từng chỗ nhắc để biết chỗ nào là đường sống,
chỗ nào chỉ là mã chết nhắc mã chết.

### 4.2 `so-khoi-cu` — 9 nút · bước Đơn hàng (SO) đã bỏ

Bước SO không còn trong luồng (`7c445d1`). Cả 9 nút thuộc một bước không tồn tại:
`loadSalesOrders`, `closeOracleSOForm`, `applySOCostToLine`, `addSOLineRow`,
`approveSO`, `saveOracleSO`, nút chọn tệp hợp đồng, và một nút "Tìm Kiếm" **không
có `onclick`** (nút này chết từ trước, nay nằm trong khối đã bỏ nên vô hại).

Đây là khối đáng bỏ nhất: **JS không nhắc tới id của nó một lần nào**.

### 4.3 `ssv5-khoi-cu` — 8 nút · màn Sắp lịch cũ

Đã bị thay bởi `.ssv5` (`sap-lich-v5.js`). **7 trong 8 hàm CHỈ khối này gọi** —
`switchDriverShiftTab`, `openWeeklyDriverSchedule`, `moveDriverShiftWeek`. Nghĩa
là bỏ khối này thì **bỏ được luôn cả hàm**, gọn nhất trong bốn khối. Hàm còn lại
`loadDriverShiftPlanner` còn nơi khác gọi, giữ.

### 4.4 `legacy-tracking-pod-panel` — 1 nút

Nút "Mở hồ sơ" gọi `openPODFormForSelectedDO`, và **chỉ khối này gọi**. Khối bị
che bằng `display:none` viết thẳng trong `style`, không phải `hidden`.

### 4.5 Đề nghị

Bỏ theo thứ tự này, mỗi khối một mốc chốt riêng để dễ lùi:

1. `so-khoi-cu` — JS không nhắc id, bước đã bỏ khỏi luồng. Rủi ro thấp nhất.
2. `ssv5-khoi-cu` — bỏ kèm 7 hàm chỉ nó gọi.
3. `legacy-tracking-pod-panel` — bỏ kèm 1 hàm.
4. `qtv2-khoi-cu` — bỏ markup, để lại hàm cho một lần dọn riêng.

Sau mỗi bước chạy `node tests/chay-tat-ca.js`; bài kiểm
`moi-man-phai-hien-noi-dung` sẽ bắt ngay nếu một màn mất nội dung.

---

## 5. Điểm cuối máy chủ không màn nào gọi — 20 đường

Cách dò: với mỗi đường, tìm **đoạn đặc trưng** của nó (kể cả khi đường bị ghép
động bằng `${}`) trong `index.html` và cả 12 tệp JS. Không một dấu vết nào thì
đường đó thật sự không có màn nào gọi.

### 5.1 Module đấu thầu / nhu cầu — 8 đường, **chưa bao giờ có màn**

```
GET,POST /api/tms/demands
PUT      /api/tms/demands/{id}/submit
GET      /api/tms/freight-units
POST     /api/tms/freight-units/from-demand/{id}
GET,POST /api/tms/tenders/{id}/offers
PUT      /api/tms/tenders/{id}/award
GET,POST /api/tms/warehouse-appointments
GET      /api/tms/resource-assignments
```

Cả một module: khách nêu nhu cầu → tách thành đơn vị hàng → mời thầu → nhà xe
chào giá → chấm thầu → hẹn kho. Máy chủ làm xong, giao diện chưa có gì. (Riêng
`GET /api/tms/tenders` **có** được gọi từ `tms-cockpit-utils.js` — danh sách gói
thầu hiện ra được, nhưng chào giá và chấm thầu thì không.)

**Cần anh chốt, và tôi nêu cả hai đường:**

- **Bỏ** — nếu buổi demo và nghiệp vụ thật không có bước đấu thầu, thì 8 điểm
  cuối này là gánh nặng: chúng vẫn phải được bảo trì theo mỗi lần đổi schema, mà
  không ai dùng.
- **Làm màn** — nếu nghiệp vụ có thật. Ước lượng: một màn với 4 bảng và khoảng
  12 nút.

Tôi **không tự quyết** việc này vì nó là câu hỏi nghiệp vụ, không phải kỹ thuật.

### 5.2 Cửa bị chặn mà không có khoá — 1 đường · **ưu tiên cao nhất**

```
GET,POST /api/tms/driver-qualifications
```

Điều phối xe **kiểm giấy phép tài xế** trước khi cho xuất bến: tài xế không có
hạng giấy phép phù hợp với loại xe thì điều phối bị chặn. Nhưng **không có màn
nào khai được giấy phép**. Hệ quả thực tế: khi điều phối bị chặn vì lý do này,
người vận hành **không có cách nào tự sửa** — phải gọi người viết mã chạy tệp
lệnh, hoặc sửa thẳng vào cơ sở dữ liệu.

Đây là dạng lỗi tệ nhất trong một hệ thống vận hành: một cái cổng khoá mà không
phát chìa. Đề nghị làm một khu nhỏ trong màn Dữ liệu gốc, cạnh danh mục tài xế:
bảng liệt kê giấy phép, nút thêm, nút sửa hạn.

### 5.3 Đường đã bị thay thế — 4 đường

| Đường | Bị thay bởi |
|---|---|
| `GET /api/quotations/summary` | `GET /api/quotations/board` — màn báo giá mới dùng `/board` |
| `PUT /api/sales-orders/{id}/confirm` | bước SO đã bỏ khỏi luồng |
| `POST /api/parking-lists/from-do/{id}` | `POST /api/parking-lists/auto-from-do` (cùng việc) |
| `POST /api/invoices/post` | hoá đơn AR được phát hành **ngay trong** bước hoàn tất giao hàng, cùng giao dịch với POD và giá cuối |

Bốn đường này nên **bỏ hoặc đánh dấu là đường cũ**. Riêng `POST /api/invoices/post`
tôi đề nghị **giữ ở máy chủ** làm cửa lập hoá đơn thủ công cho đơn cũ chưa đi qua
đường hoàn tất — nhưng đã bỏ hẳn hàm `postInvoice` ở giao diện, vì để một hàm ghi
hoá đơn thật mà không ai gọi là đặt sẵn một cái bẫy.

### 5.4 Viết xong mà chưa đưa lên màn — 7 đường

```
GET  /api/tms/finance/dashboard              bảng số liệu tài chính
GET  /api/vehicle-types/recommendations      gợi ý loại xe theo lô hàng
GET  /api/tms/freight-orders/{id}/latest-position   vị trí GPS mới nhất
POST /api/tms/freight-orders/{id}/legacy-link       nối đơn cũ
POST /api/cost-formulas/evaluate             thử công thức giá thành
GET  /api/parking-lists/{id}/packing-list    in phiếu đóng hàng
GET  /api/parking-labels/{id}/qr.svg         in mã QR nhãn
```

Hai đường in cuối đáng đưa lên trước: màn Bãi xe đã có nút tạo và nút quét, chỉ
thiếu nút **in**. `POST /api/cost-formulas/evaluate` có thể sẽ được dùng bởi việc
cost-formula v2 đang làm dở (xem §8), nên chưa nên tính là dư.

---

## 6. Rà soát từng màn

Mỗi màn: nó làm gì trong luồng, gọi những đường nào, có bao nhiêu nút thấy được,
và có gì đáng nói.

### 6.1 Bảng điều khiển (`dashboard`) — 16 nút

Dải 8 bước luồng cùng 7 thẻ chức năng. Gọi `/api/dashboard/stats`, `/api/data/all`.

- 8 nút "Thao Tác Ở Bước Này ➔" — `updateActiveFlowStep` + `switchView`, chạy đúng.
- 7 nút "Mở …" — mỗi thẻ đúng một nút. Nút "Mở Tuyến đường" trỏ vào **một tab của
  màn Dữ liệu gốc** (`openMasterSetupStep('md-tab-routes')`) chứ không phải một
  màn, vì tuyến đường là dữ liệu gốc, không phải bước vận hành. Đúng chỗ.
- Đây là màn từng chứa nhiều nút nói dối nhất: 8 nút "Lưu", "Post", "Print",
  "Submit". Nay đã sạch. Bài kiểm `dead-ui-cleanup` chốt lại: mọi ô nhập trong
  khối minh hoạ phải `disabled`, và không nút nào trong khối được ghi cơ sở dữ liệu.

### 6.2 Kinh doanh & Báo giá (`crm-sales`) — 11 nút

Màn dựng lại hoàn toàn theo bản thiết kế (`bao-gia-v2.js`, ~2.100 dòng). Gọi
`/api/quotations`, `/api/quotations/board`, `/api/quotations/price-preview`,
`/api/customers`, `/api/routes`, `/api/vehicle-types`, `/api/currencies`.

Toàn bộ nút nối bằng **uỷ nhiệm sự kiện**, không dùng `onclick` — nên bảng kê tĩnh
thấy "không có onclick". Tôi đã bấm thật để xác nhận chúng sống. Hai nút tab
(`Báo giá cước` / `Khách hàng và cơ hội`) chuyển qua lại đúng.

Còn thiếu so với bản thiết kế: **mẫu in PDF** (§8 bản thiết kế để mở), **bảng giá
khách hàng** (dấu giá `hop_dong` chưa có nguồn dữ liệu), **nhắc khách qua email**.

### 6.3 Kế hoạch vận hành (`ops-planning`) — 6 nút

Lệnh giao hàng cần lập kế hoạch. `switchOpsPlanningFolder`,
`switchDeliveryOrderSubtab`, `chonNhomDO` ×3. Gọi `/api/delivery-orders`,
`/api/delivery-orders/analysis`. Không có gì bất thường.

### 6.4 Chuyến & chặng về (`delivery-shipment`) — 14 nút

Dải 5 thẻ số liệu + 5 tab trạng thái + tạo Trip + ghi chú + làm mới + xoá lọc.
`openTripReturnAction`, `setTripKpiFilter`, `setTripReturnStatusTab`,
`clearTripReturnFilters`.

Đáng ghi nhận: thẻ số liệu nào **không có chuyến nào** thì tự `disabled` kèm chú
giải "Không có chuyến nào trong nhóm này", thay vì cho bấm rồi hiện bảng trống.
Đây là cách làm đúng và nên giữ làm khuôn cho các màn khác.

### 6.5 Điều phối xe (`dispatch`) — 15 nút thấy được + 12 nút trong bảng chi tiết

Màn dựng lại theo bản mẫu `dispatch-v2-crew.html`. Lịch theo ngày, cột DO chờ xếp,
cột xe ứng viên, bảng chi tiết mở theo yêu cầu.

Hai thẻ cuối của dải số liệu ("Xe rảnh / tổng", "Tài xế trong ca") là **chỉ để
đọc**: chúng nói về xe và người, không lọc được cột DO, nên được đặt `disabled`
kèm chú giải "Chỉ để xem". Đúng — cho bấm rồi không có gì xảy ra thì tệ hơn.

Cửa chặn điều phối đang có: hạn kiểm định / bảo hiểm / bảo dưỡng của xe, **giấy
phép tài xế** (xem §5.2), ca làm phải phủ hết chuyến, trạng thái xe phải đúng
"Sẵn sàng", và kiểm soát đóng hàng / niêm phong / khối lượng.

### 6.6 Theo dõi & Sự cố (`tracking`) — 21 nút

Nhiều nút nhất trong một màn. 18 nút nối uỷ nhiệm qua `#tracking-control-tower`
(`tracking-control-tower.js`), 3 nút còn lại `onclick` trực tiếp. Gọi
`/api/tracking/control-tower`, `/api/tms/freight-orders`, `/api/incidents`,
`/api/pod-documents`.

`legacy-tracking-pod-panel` (1 nút) nằm ở màn này — xem §4.4.

### 6.7 Hoàn tất giao hàng (`delivery-completion`) — 3 nút + 4 nút trong bảng soạn

Bước chốt giá và phát hành hoá đơn. Bảng soạn mở theo yêu cầu, có nút "Hoàn tất
giao hàng & chốt giá" (`submitDeliveryCompletion`) và "Thêm khoản phí".

Đây là chỗ hoá đơn AR **thật sự** được phát hành, trong cùng một giao dịch với
POD và giá cuối — lý do `POST /api/invoices/post` ở §5.3 là đường cũ.

Có một cửa chặn đáng nói: nếu ảnh POD và ảnh chữ ký là **cùng một tệp**, hệ thống
trả về 422 kèm tên chặng, chứ không lặng lẽ nhận.

### 6.8 Bãi xe (`parking-list`) — 8 nút

Tạo danh sách bãi từ DO, sinh QR, quét QR. Hai nút chính
("Tạo tự động & sinh QR", "Ghi nhận quét") là `type="submit"` trong form có
`onsubmit`, nên bảng kê tĩnh không thấy `onclick` — đã xác nhận là **nối đúng**,
không phải nút chết.

Thiếu: **nút in** phiếu đóng hàng và nhãn QR, dù máy chủ đã có hai đường đó (§5.4).

### 6.9 Trạm kiểm soát AI (`ai-checkpoint`) — 2 nút

"Tải ảnh lên để quét" là nút bấm hộ ô chọn tệp đang ẩn
(`document.getElementById('ai-file-input').click()`) — cách làm chuẩn, không phải
handler chết. "Mở barie (check-in)" gọi `confirmAICheckin`.

Lưu ý: `confirmAICheckin` từng gọi một hàm vẽ bảng đã chết để "làm mới màn hình",
nên thông báo "Đã mở barrier" hiện ra mà không có gì trên màn đổi. Đã sửa và có
bài kiểm chốt.

### 6.10 Kế toán & Tài chính (`accounting`) — 7 nút + 4 tab con

Hai luồng: Actual Cost / AP / Settlement và AR / GL. Gọi 4 đường
`/api/tms/finance/*`, `/api/tms/carriers`, `/api/tms/tenders`, và 3 đường
`/api/master-data/*`.

Quy tắc bốn mắt đang có hiệu lực: **người lập phiếu chi phí không được tự duyệt**.
Đây là lý do bộ dữ liệu demo cần một tệp lệnh duyệt bằng người thứ hai.

`GET /api/tms/finance/dashboard` chưa được gọi (§5.4).

### 6.11 Dữ liệu gốc (`master-data`) — 20 nút + 11 tab

11 tab: Setup A-Z, Tuyến đường, Công thức giá thành, Loại phương tiện, Sắp lịch,
Tỷ giá, Khách hàng, Thuế, Kỳ kế toán, Carrier/Vendor, Mapping tài khoản.

Tab Tuyến đường có sơ đồ lộ trình vẽ trên bản đồ. Toạ độ điểm là **dữ liệu gốc
sửa được** (`locations.latitude/longitude`), tự tra từ máy chủ khi có địa điểm
mới và ghi lại, có đường khai bằng tay làm chốt cuối, và giá trị người khai
**không bị máy ghi đè**. Toạ độ máy đoán ra được đối chiếu với số km người dùng
khai để loại kết quả vô lý.

`ssv5-khoi-cu` (8 nút, §4.3) nằm ở tab Sắp lịch của màn này.

### 6.12 Báo cáo vận tải (`lab-summary`) — 15 nút

`TransportReporting.*`: 5 góc nhìn, xuất CSV, tải lại, lập phiếu chi phí. Gọi 5
đường `/api/tms/reporting/*`.

Đã sửa một lỗi số học nặng ở đây: báo cáo từng hiện lãi gộp 99% vì lấy **chênh
lệch** chi phí làm **tổng** chi phí. Nay là kế hoạch + chênh lệch, và mỗi dòng có
thêm hai cột `planned_cost_functional`, `cost_variance_functional`.

### 6.13 Hồ sơ chuyến 360 (`operations-360`) — 4 nút

3 tab (Tổng quan · Hành trình & POD · Chi phí & đối soát) + nút "Mở Dispatch".
Màn tổng hợp, không tự ghi dữ liệu.

---

## 7. 13 nút "trông như im lặng" — và vì sao không phải lỗi

Ghi lại phần này để lần sau không có ai (kể cả tôi) báo lỗi giả. Khi bấm thử,
13 nút không làm gì cả. Tra từng nút thì cả 13 đều đúng:

| Nhóm | Số nút | Vì sao im lặng |
|---|---|---|
| Thẻ số liệu ở màn Chuyến và Điều phối | 9 | `disabled` vì nhóm không có dữ liệu, hoặc thẻ chỉ để đọc — **có chú giải nói rõ lý do**. Bấm nút `disabled` thì không có sự kiện nào. |
| Hai nút chính của màn Bãi xe | 2 | `type="submit"` trong form có `onsubmit` — trình duyệt giả không thực hiện gửi form |
| Hai nút tab đang mở sẵn | 2 | Bấm lại tab đang mở thì đúng ra không đổi gì. Bấm sang tab khác rồi bấm quay lại: cả hai lần DOM đều đổi. |

Bài học của phần này: **"không có `onclick`" không có nghĩa là chết**, và **"bấm
vào không thấy gì" cũng không có nghĩa là chết**. Phải tra tới lý do.

---

## 8. Việc của người khác đang làm dở — không rà

Trong cây làm việc hiện có một mảng thay đổi **chưa chốt** thuộc một việc khác:
công thức giá thành v2 (`backend/app/services/cost_expression.py`,
`frontend/js/cost-formula-builder.js`, `cost-expression.js`, `cost-comparison.js`,
`cost-vehicle-inline.js`, `jsep.min.js`, `css/cost-formula-v2.css`,
`docs/superpowers/…`), kèm khoảng 15 nút mới ở `md-tab-formulas` và
`cfv2-workbench`.

Tôi **không rà và không sửa** phần đó — nó đang giữa đường, và mọi kết luận về nó
lúc này đều sẽ sai. Các con số ở §1 tính trên mốc `ddcf882`; nếu anh muốn con số
tính cả phần đang làm dở thì rà lại sau khi việc đó chốt.

---

## 9. Bộ kiểm chốt lại những gì rà được

Rà soát chỉ có giá trị nếu lần sau không phải rà lại từ đầu. Hai bài kiểm giữ kết
quả này:

- **`tests/dead-ui-cleanup.test.js`** — chặn 8 hàm vẽ bảng chết sống lại, đòi mọi
  ô nhập trong khối minh hoạ phải `disabled`, chặn 8 tên hàm ghi cơ sở dữ liệu
  bị gọi từ khối minh hoạ (`saveMasterForm`, `submitIncident`, `postInvoice`…),
  đòi **mỗi thẻ đúng một nút** mở màn thật, và đòi "SALES ORDER" đã biến mất.
  Mục 1b mới thêm chặn riêng `postInvoice` — đã kiểm chứng ngược: thêm hàm vào là
  bài kiểm đỏ.
- **`tests/moi-man-phai-hien-noi-dung.test.js`** (mới) — mở lần lượt cả 13 màn và
  đòi mỗi màn hiện nội dung chính, có **ít nhất một nút bấm được**, và không lỗi
  JS. Bài này bắt được dạng lỗi nặng nhất mà mọi bài kiểm đọc-văn-bản đều bỏ qua:
  một màn mở ra trắng trơn.

Toàn bộ bộ kiểm giao diện: **85/85 xanh**, đo hôm nay.

Bộ kiểm máy chủ lần chạy đầy đủ gần nhất: **896 bài qua**. Lần đo đó trước khi việc công thức giá thành v2 (§8) vào cây làm việc, nên con số này chỉ đúng cho mốc `ddcf882`; tôi chưa chạy lại bộ kiểm chín phút giữa lúc cây đang có việc chưa chốt của người khác.

---

## 10. Còn nợ

| Việc | Vì sao còn nợ |
|---|---|
| Màn khai giấy phép tài xế | §5.2 — cần làm, ưu tiên cao nhất |
| Chốt phận module đấu thầu | §5.1 — cần anh quyết, tôi không tự quyết |
| Bỏ 4 khối cũ, 25 nút | §4.5 — có thứ tự đề nghị |
| Nút in phiếu đóng hàng và nhãn QR | §5.4 — máy chủ đã xong, thiếu nút |
| Mẫu in PDF báo giá | §8 bản thiết kế để mở |
| Bảng giá khách hàng | dấu giá `hop_dong` chưa có nguồn dữ liệu |
| Nhắc khách qua email | chưa làm |
| Chạy mốc 031→039 lên PostgreSQL và đối chiếu | đang làm trên SQLite vì máy chứa PostgreSQL không tới được từ nhà |
