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
| **Nút dư thật sự** | **1** — bốn khối cũ có 25 nút, nhưng 24 nút thuộc ba tính năng CÒN CHẠY (xem §4) |
| **Hồi quy tìm ra khi dọn** | **1** — màn Báo giá mới thiếu cửa chặn tải trọng (§4.1) |
| Nút nói dối đã bỏ trong lần rà này | 3 (+ 8 nút "Lưu" đã bỏ ở lần trước) |
| Bước luồng bị thiếu đã thêm | 1 — "Xác nhận xe đã về bãi" |

**Việc nên làm, theo thứ tự tôi đề nghị:**

1. **Chuyển cửa chặn tải trọng sang màn Báo giá mới, và thêm một cửa ở máy chủ.**
   Xem §4.1 — đây là hồi quy đang tồn tại: báo giá được một lô 20 tấn trên xe
   5 tấn, lỗi chỉ lộ ra tận bước điều phối. Việc lớn nhất còn lại.
2. **Bỏ `qtv2-khoi-cu` (7 nút)** ngay sau khi chuyển xong cửa chặn ở việc 1.
3. **Chốt phận cho module đấu thầu.** 8 điểm cuối đã viết xong ở máy chủ, 5 bảng
   đang 0 dòng, chưa bao giờ có màn. Chủ dự án đã chốt: **để lại sau demo**.

**Đã làm xong trong lần rà này:**

- **Màn khai bằng lái tài xế** — cửa chặn điều phối trước đây khoá cổng mà không
  phát chìa. Xem §3.
- **Cửa cho biểu mẫu hồ sơ tài xế** — trước đây không nút nào mở được nó. §4.2.
- **Bỏ khung POD chết** ở màn Theo dõi. §4.

---

## 2. Luồng chính — có liền không

Luồng của hệ thống hiện nay là:

```
Dữ liệu gốc → Báo giá (QT) → duyệt → khách chấp nhận → Lệnh giao hàng (DO) SINH TỰ ĐỘNG
   → lập Chuyến (Trip) → điều phối xe → các mốc giao hàng
   → POD → Hoàn tất & chốt giá → Hoá đơn AR → Phiếu chi phí thực tế → Báo cáo
```

**Không còn bước Đơn hàng (SO), và không còn bước tách tay.** Bước SO đã bỏ ở
mốc `7c445d1`. Từ 09/09, **ghi nhận khách chấp nhận là bước sinh DO**: máy chủ
tạo N lệnh giao hàng ngay trong cùng giao dịch, kế thừa tuyến, giá khoá và khung
giờ của báo giá (N = tổng số lượng ở bảng Hàng hoá, mỗi cont/xe một DO). Không
còn đường tạo DO bằng tay — một DO không có báo giá chống lưng thì bước quyết
toán không có giá nào để lấy.

Luồng này đã chạy trọn A→Z trên dữ liệu thật: **173 điểm kiểm, 0 điểm đỏ** (đo
09/09), và bộ **19 case demo** hiện có (`docs/du-lieu-luong-demo.md`) đi hết từ
báo giá tới báo cáo. Doanh thu 12.270.600 đ · giá thành đã duyệt 7.850.758 đ ·
lãi gộp 36,02%.

**Một bước từng bị thiếu và đã thêm:** chuyến xe giao xong không có đường nào ghi
nhận "xe đã về bãi", nên chuyến treo mãi ở trạng thái đang chạy và xe không bao
giờ rảnh lại để điều phối tiếp. Đã thêm nút **"Xác nhận xe đã về bãi"** cùng hàm
`xacNhanXeDaVe`.

---

## 3. Đã sửa trong lần rà này

| Nút / chỗ | Vấn đề | Đã làm |
|---|---|---|
| **Cửa chặn bằng lái tài xế** | Điều phối chặn khi bằng lái thiếu / hết hạn / lệch hạng, và cửa chặn còn trả về gợi ý `["master-data/drivers"]` — nhưng **không có màn nào khai được bằng lái**, nên điều phối bị chặn chỉ sửa được bằng tệp lệnh | Thêm thẻ **"5. Tài Xế & Bằng Lái"**; kết luận trên màn sao lại đúng năm điều kiện của cửa chặn; có ô "Xét theo ngày"; đổi hạng thì ghi cả hai bảng. Mốc `eaa8abb` |
| **Biểu mẫu hồ sơ tài xế** | Có đủ ô nhưng **không nút nào trong toàn bộ trang mở nó** | Nút "Hồ sơ" trên từng dòng và "Thêm tài xế" ở đầu màn. §4.2 |
| Khung POD cũ ở màn Theo dõi | Đường tắt sang màn Hoàn tất, bị che từ lâu nên đã chết | Bỏ hẳn 27 dòng, 1 nút |
| "Post" trên thẻ minh hoạ ở Bảng điều khiển | Ghi **một hoá đơn thật** cùng bút toán sổ cái, cho lệnh giao hàng nó **tự chọn** bằng "lệnh đã giao đầu tiên tìm thấy" | Bỏ nút, rồi bỏ luôn hàm `postInvoice` (mốc `ddcf882`) và chốt bằng bài kiểm |
| "Print" trên thẻ đó | Không nối gì | Bỏ, kèm chú thích vì sao |
| "Submit" trên thẻ "BÁO CÁO SỰ CỐ" | Ghi một sự cố **thật**, nhưng đọc giá trị từ form sự cố ở **màn khác** — mọi ô của thẻ này đều `disabled`, nên bấm là ghi một sự cố rỗng | Thay bằng nút đi tới màn thật |
| Thẻ "SALES ORDER" ở Bảng điều khiển | Bước SO đã bỏ khỏi luồng | Bỏ thẻ, dọn khoá `lbl_form_2_so` trong `lang.json` |
| 8 thẻ ở Bảng điều khiển | Chỉ 5 trong 8 thẻ có nút mở màn thật → người xem không suy ra được thẻ nào mở được | 7 thẻ còn lại, **mỗi thẻ đúng một nút** |
| `switchView('crm-sales')` | Gọi `loadQuotations()` của màn báo giá **cũ** | Bỏ lệnh gọi; màn mới tự nạp danh sách của nó |

Hai mốc liên quan: `a65c69f` (rà soát nút, bỏ hai nút nói dối, thêm bước xác nhận
xe về) và `ddcf882` (bỏ `postInvoice`, thêm hai bài kiểm).

---

## 4. Nút dư — con số đếm đúng, kết luận ban đầu SAI

**Bản đầu của mục này nói 25 nút dư trong bốn khối cũ, và đề nghị bỏ cả bốn.**
Khi bắt tay bỏ thì tám bài kiểm đỏ, và đọc ra lý do: **hai trong bốn khối không
phải rác.** Chúng chứa tính năng còn chạy được, chỉ bị `hidden` che vì bước hoặc
màn của chúng đã rời khỏi luồng. Ghi lại nguyên chỗ sai này, vì bài học của nó
quan trọng hơn con số: **"bị `hidden` che" không đồng nghĩa với "chết".**

Cách kiểm đúng, và từ giờ phải làm trước mỗi lần bỏ một khối:

1. Khối có chứa **ô chọn tệp, FormData, hay điểm cuối riêng** nào không?
2. **Bài kiểm nào** đang chốt các `id` bên trong? (Kể cả bài dựng tên `id` bằng
   chuỗi ghép — `grep` một tên cụ thể sẽ không thấy chúng.)
3. Năng lực mà khối đó cung cấp, **màn đang chạy có bản tương đương chưa?**

| Khối | Nút | Kết luận | Vì sao |
|---|---|---|---|
| `so-khoi-cu` | 9 | **GIỮ** | Chứa tính năng đính kèm chứng từ đang chạy thật: gửi FormData, chặn tệp trên 25 MB, bảng `sales_order_documents`, 4 điểm cuối, kèm bộ kiểm riêng. |
| `qtv2-khoi-cu` | 7 | **ĐÃ BỎ** | Từng phải giữ vì chứa **cửa chặn tải trọng** duy nhất của bước báo giá. Nay cả màn mới lẫn máy chủ đều đã chặn thật, nên bản mẫu không còn cần — xem §4.1. |
| `ssv5-khoi-cu` | 8 | **GIỮ** | Chứa `driver-modal-dialog`, biểu mẫu duy nhất sửa được hồ sơ tài xế. Nay đã có cửa mở nó — xem §4.2. |
| `legacy-tracking-pod-panel` | 1 | **ĐÃ BỎ** | Đường tắt từ màn Theo dõi sang màn Hoàn tất, bị che từ lâu nên đã chết. Màn Hoàn tất tự liệt kê và tự mở bảng soạn nên không mất đường nào. |

Vậy thực tế: bỏ được **1 nút ngay**, không phải 25 — và **7 nút nữa sau khi**
chuyển cửa chặn tải trọng sang màn mới. Điều kiện đó nay đã đủ, nên `qtv2-khoi-cu`
**đã bỏ hẳn**: 20.085 ký tự HTML, cùng `oracle-qt-form` khỏi danh sách hộp thoại
toàn màn.

Hai chỗ **vỡ thật** mà việc bỏ khối làm lộ ra, cả hai đều là neo trỏ vào phần đã
xoá và cả hai đều đã sửa:

- Nút **"Thao Tác Ở Bước Này"** của bước 1 trong sơ đồ luồng A→Z gọi
  `switchView('crm-sales', 'oracle-qt-list')` — neo đó nằm trong khối vừa xoá.
  Nay trỏ `#qtv2-root`.
- `selectEnterpriseTabForTarget` ánh xạ `oracle-qt-list` → thẻ "Báo giá cước".
  Bỏ sót chỗ này thì nút trên nhảy sang màn Kinh doanh mà không mở thẻ Báo giá —
  và vì thẻ đó tình cờ là thẻ đầu, lỗi chỉ lộ ra khi người dùng vừa xem thẻ
  Khách hàng rồi bấm nút đó.

**Ba hàm KHÔNG bỏ**, vì màn khác còn gọi — đây đúng là chỗ mà "khối ẩn nên hàm
chết" sẽ lại sai:

| Hàm | Ai còn gọi |
|---|---|
| `autoCalculateMasterDataCost` | Màn **Công thức giá thành** gọi mỗi lần đổi đơn giá (`oninput`, 5 chỗ), và `cost-formula-builder.js` gọi sau khi sửa công thức. |
| `renderCostBreakdown` | Màn **Đơn vận chuyển** vẽ bảng chi phí của nó (`so-cost-breakdown`). |
| `loadQuotations` | `refreshWorkflowCommandData` nạp `appState.quotations` từ đó sau mỗi lệnh báo giá. |

**Còn nợ, đã đo:** chuỗi hàm cũ của màn báo giá (`openOracleQTForm`,
`closeOracleQTForm`, `saveOracleQT`, `approveQuotation`, `filterQuotations`,
`renderOracleQTList`, `refreshQuotationVehicleRecommendations`, cùng
`editOracleQT` / `deleteOracleQT` / `convertQTToSO`) giờ **không có đường nào bấm
tới**, khoảng 600 dòng trong `app.js`. Chúng vô hại — mọi hàm trong chuỗi đều đã
có `if (!el) return` nên mất vật chứa thì không nổ — nhưng chúng là mã chết. Bỏ
chuỗi này là một việc riêng: nó lan tới bốn bộ điều phối dùng chung
(`saveMasterForm`, `approveMasterForm`, `sendMasterForm`, `submitMasterForm` —
các nhánh `'so'` / `'do'` / `'route'` / `'dispatch'` vẫn sống), nên phải bỏ theo
nhánh chứ không bỏ cả hàm. Cùng đó là **CSS chết** `#oracle-qt-form` và
`.oracle-qt-table` trong `index.html`; chưa bỏ vì vùng `<style>` đó đang có người
khác sửa, và bốn luật `.qt-cost-*` cạnh nó thì **vẫn còn dùng** cho màn Đơn vận
chuyển.

### 4.1 Hồi quy: màn Báo giá mới thiếu cửa chặn tải trọng

Đây là phát hiện đáng giá nhất của lần dọn này, và nó không phải chuyện dọn dẹp.

Màn Báo giá **cũ** có `refreshQuotationVehicleRecommendations`: đọc khối lượng /
thể tích / số pallet, đánh giá loại xe nào chở được, **làm mờ** loại xe không đủ
tải, giải thích khi loại xe chưa khai sức chở (`CAPACITY_NOT_CONFIGURED`), nói rõ
khi **không loại xe đơn lẻ nào đủ tải** (gợi ý tách chuyến hoặc thuê ngoài), và
**chặn lưu** báo giá khi loại xe đang chọn không phù hợp. Có bài kiểm riêng:
`tests/quotation-capacity-recommendation-ui.test.js`.

Màn Báo giá **mới** lúc đó không có cửa chặn đó — nó chỉ đọc `max_weight` và
`volume_capacity_m3` vào mô hình loại xe rồi thôi. Và **máy chủ cũng không chặn**
ở bước báo giá: `workflow_service` và `bao_gia_service` đều không kiểm sức chở.

**Hệ quả lúc đó:** báo giá được một lô 20 tấn trên xe 5 tấn, và lỗi chỉ lộ ra tận
bước điều phối — nơi `_require_dispatch_eligibility` mới kiểm sức chở so với lệnh
vận chuyển. Người bán đã gửi giá cho khách rồi mới biết chuyến không chở được.

**ĐÃ SỬA, ở cả hai bên** — và phải là cả hai, vì một cửa chặn chỉ nằm ở trình
duyệt thì gọi API trực tiếp là đi qua được:

- **Màn mới** (`bao-gia-v2.js`): chặn ngay lúc **bấm** vào thẻ loại xe
  (`if (n.dataset.hong)`), không chỉ đổi màu. Và thông báo nói rõ **chiều nào**
  vượt cùng con số vượt (`lyDoKhongDu`) — nói "không đủ tải" cho một lô nhẹ mà
  khối lớn là nói sai, người bán đổi sang xe nặng hơn rồi vẫn vướng. Dùng chung
  bộ đánh giá ba chiều `WorkflowUIUtils.evaluateVehicleCapacity` với máy chủ, nên
  hai bên không thể nói hai câu khác nhau.
- **Máy chủ** (`bao_gia_service.xem_truoc_gia`): trả `tinh_duoc: False` kèm việc
  còn thiếu khi loại xe không đủ năng lực — tức **không tính ra giá** cho lô vượt
  tải, chứ không phải cảnh báo rồi vẫn trả số. Chốt bởi
  `backend/tests/test_bao_gia_cua_chan_tai_trong.py`.

Nửa phía giao diện của cửa chặn nay được chốt bởi phần dưới của
`tests/quotation-capacity-recommendation-ui.test.js` — phần chốt màn cũ trong bài
kiểm đó đã bỏ cùng khối.

### 4.2 Đã nối cửa cho biểu mẫu hồ sơ tài xế

`driver-modal-dialog` có đủ ô — tên, số điện thoại, vai trò, hạng bằng, ca làm —
và lúc nạp trang `duaHopThoaiRaNgoaiKhungMan()` chuyển nó ra ngoài khung màn nên
nó không bị khối ẩn giam. Nhưng dò cả trang thì **không có một nút nào mở nó**,
nên hồ sơ tài xế không sửa được từ giao diện.

Nay màn "Tài xế & Bằng lái" có nút **"Hồ sơ"** trên từng dòng và **"Thêm tài xế"**
ở đầu màn. Hai chỗ phải cẩn thận, và bài kiểm chốt cả hai:

- `editDriverById` đọc từ mảng `fioriDrivers` của `app.js`, không đọc từ dữ liệu
  của màn này. Mảng rỗng thì hàm **im lặng thoát ngay** — đúng dạng nút nói dối
  mà cả lần rà soát này đi dọn. Nên phải gọi `loadFioriDrivers()` trước, và nếu
  vẫn không mở được thì **nói ra**.
- `saveDriverModal` không biết gì về màn này, nên phải bọc nó để màn tự nạp lại.

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

### 5.2 Cửa bị chặn mà không có khoá — 1 đường · **ĐÃ SỬA**

```
GET,POST /api/tms/driver-qualifications
```

Điều phối xe **kiểm giấy phép tài xế** trước khi cho xuất bến: tài xế không có
hạng giấy phép phù hợp với loại xe thì điều phối bị chặn. Nhưng **không có màn
nào khai được giấy phép**. Hệ quả thực tế: khi điều phối bị chặn vì lý do này,
người vận hành **không có cách nào tự sửa** — phải gọi người viết mã chạy tệp
lệnh, hoặc sửa thẳng vào cơ sở dữ liệu.

Đây là dạng lỗi tệ nhất trong một hệ thống vận hành: một cái cổng khoá mà không
phát chìa. **Đã sửa ở mốc `eaa8abb`** — xem §3 và §4.2. Đề nghị làm một khu nhỏ trong màn Dữ liệu gốc, cạnh danh mục tài xế:
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

**Rà lại từng đường thì bảy con số này rút xuống một.** Ghi lại cả chỗ tôi đếm
sai, vì cách đếm sai đó sẽ lặp lại nếu không nói ra.

**Hai đường KHÔNG hề thiếu màn — lỗi của phép rà, không phải của mã.** Màn Bãi xe
đã có sẵn cả hai nút **"In tem kiện"** và **"In Packing List"**
(`parking-list.js:233`), và hai hàm `printLabels` / `printPackingList` đã dựng
xong, có ghi nhận lần in. Và `qr.svg` **đang được dùng**: `printLabels` đọc
`label.qr_path`, mà `parking_list_service._label_dict` đặt trường đó bằng
`/api/parking-labels/{id}/qr.svg`.

> **Vì sao phép rà không thấy:** nó tìm **chuỗi URL viết trong JS**. Một điểm
> cuối mà giao diện đi tới bằng **đường do máy chủ trả về** thì không có chuỗi
> nào để tìm. Từ giờ, trước khi kết luận "không màn nào gọi", phải tìm thêm cả
> tên **trường dữ liệu** dẫn tới nó (`*_path`, `*_url`, `href`).

**Bốn đường là cửa thứ hai cho việc đã có cửa** — không phải tính năng thiếu màn:

| Đường | Việc đó đã đi qua cửa nào |
|---|---|
| `GET /api/vehicle-types/recommendations` | Độ vừa tải của từng loại xe đã theo `/api/quotations/price-preview` về màn báo giá (`cac_loai_xe[].do_vua_tai`), và máy khách dùng chung bộ đánh giá `WorkflowUIUtils.evaluateVehicleCapacity`. |
| `GET /api/tms/freight-orders/{id}/latest-position` | Vị trí GPS đã về **theo lô** qua `/api/tracking/control-tower`, kèm bốn trạng thái GPS và bản đồ. |
| `GET /api/parking-lists/{id}/packing-list` | Trả đúng dữ liệu mà lời gọi GET chính đã trả. |
| `POST /api/tms/freight-orders/{id}/legacy-link` | Cầu nối dữ liệu cũ, không có bước nghiệp vụ nào trong luồng hiện tại. |

**Một đường là lỗi thật, và đã sửa: `GET /api/tms/finance/dashboard`.**
`/api/data/all` **cố tình bôi trắng** ba tập `freight_actual_costs` /
`ap_invoices` / `settlements` thành `[]` (dữ liệu tài chính chỉ phát qua endpoint
có kiểm quyền), nhưng màn Finance Cockpit lại đếm bốn thẻ số liệu của nó **ngay
trên ba mảng đó**. Đo trên PostgreSQL thật: **ba hồ sơ chi phí đang ở `submitted`
chờ duyệt mà thẻ ghi 0**, và ba danh sách dưới nói "không có … đang chờ xử lý" —
ba việc cần duyệt biến mất khỏi tầm mắt người làm tài chính. Đúng họ lỗi với
`dashboard-load-honesty`: một con số 0 sai trông y hệt một con số 0 đúng.

Đã sửa cả bốn phần:

1. Bốn thẻ lấy số **đếm toàn bảng** từ máy chủ, và bộ lọc **trùng với nhãn**
   người dùng đọc (`chờ duyệt` = draft + submitted, `chờ hạch toán` = chưa post,
   `còn mở` = chưa trả xong).
2. Ba mảng bị bôi trắng được **nạp bổ sung** từ ba đường có kiểm quyền, nên ba
   danh sách việc cần xử lý hiện ra thật.
3. Tiền cộng theo **cột quy đổi** (`functional_total_amount`,
   `functional_amount`), không theo `total_amount` gốc — bản cũ cộng thẳng rồi
   màn hình dán nhãn "VND" lên kết quả của hai loại tiền. Và mọi phép đếm lọc
   `is_active` để không cộng dòng đã đảo.
4. `list_row_cap` nói ra giới hạn 100 của ba đường liệt kê, để thẻ ghi được
   "xem được 100 mới nhất" thay vì lặng lẽ hiện 100.

Chốt bởi `frontend/tests/so-lieu-tai-chinh-tu-may-chu.test.js` (kiểm cả tên
trường hai bên có trùng — đổi tên một bên thì màn hình lặng lẽ quay về số cũ) và
hai bài mới trong `backend/tests/test_tms_finance_read_endpoints.py`.

`POST /api/cost-formulas/evaluate` có thể sẽ được dùng bởi việc cost-formula v2
đang làm dở (xem §8), nên chưa nên tính là dư.

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

`legacy-tracking-pod-panel` (1 nút) từng nằm ở màn này và **đã bỏ** — xem §4.

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

### 6.11 Dữ liệu gốc (`master-data`) — 20 nút + 12 tab

12 tab: Setup A-Z, Tuyến đường, Công thức giá thành, Loại phương tiện, Sắp lịch,
**Tài xế & Bằng lái** (mới), Tỷ giá, Khách hàng, Thuế, Kỳ kế toán, Carrier/Vendor,
Mapping tài khoản. Thẻ mới đặt cạnh thẻ Sắp lịch vì đó là nơi người dùng đang làm
việc với tài xế; các thẻ sau nó đã được đánh số lại từ 5 lên 6..11 trong cả ba thứ
tiếng.

Tab Tuyến đường có sơ đồ lộ trình vẽ trên bản đồ. Toạ độ điểm là **dữ liệu gốc
sửa được** (`locations.latitude/longitude`), tự tra từ máy chủ khi có địa điểm
mới và ghi lại, có đường khai bằng tay làm chốt cuối, và giá trị người khai
**không bị máy ghi đè**. Toạ độ máy đoán ra được đối chiếu với số km người dùng
khai để loại kết quả vô lý.

`ssv5-khoi-cu` (8 nút) nằm ở tab Sắp lịch của màn này, và **được giữ** vì nó chứa
biểu mẫu hồ sơ tài xế — xem §4.2.

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
| ~~Màn khai giấy phép tài xế~~ | **ĐÃ XONG** — mốc `eaa8abb`, xem §3 |
| Chốt phận module đấu thầu | §5.1 — cần anh quyết, tôi không tự quyết |
| Chuyển cửa chặn tải trọng sang màn Báo giá mới + thêm cửa ở máy chủ | §4.1 — hồi quy đang tồn tại, việc lớn nhất còn lại |
| Bỏ `qtv2-khoi-cu` (7 nút) | chỉ bỏ được sau khi chuyển xong cửa chặn ở dòng trên |
| Nút in phiếu đóng hàng và nhãn QR | §5.4 — máy chủ đã xong, thiếu nút |
| Mẫu in PDF báo giá | §8 bản thiết kế để mở |
| Bảng giá khách hàng | dấu giá `hop_dong` chưa có nguồn dữ liệu |
| Nhắc khách qua email | chưa làm |
| Chạy mốc 031→039 lên PostgreSQL và đối chiếu | đang làm trên SQLite vì máy chứa PostgreSQL không tới được từ nhà |
