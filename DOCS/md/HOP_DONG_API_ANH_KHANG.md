# Nối EPL Lào với module kế toán — đề nghị hợp đồng API gửi anh Khang

> **Đã thay (30/09/2026).** Anh Khang không làm phần này nữa; phần kế toán nay là của anh Tune, phần kho của anh Toàn.
> Xem `HOP_DONG_API_KE_TOAN_ANH_TUNE.md` và `HOP_DONG_API_KHO_ANH_TOAN.md`. Định khoản trong tệp này (PC_TU 625, HD 1211/70, TT 625…)
> là bản CŨ — bảng đúng sau đợt rà 30/09 nằm ở hợp đồng với anh Tune, mục 7.

Viết cho anh Khang (Golden SME) và người bảo trì phần kế toán. Cập nhật 21/09/2026.

Phần mềm vận tải EPL Lào **không có sổ kế toán**. Mỗi bước nghiệp vụ (chi tạm ứng, xuất kho dầu, nhập
kho hàng, hoá đơn, thu tiền khách…) sinh ra **một tờ chứng từ có số**, và bên em muốn **đẩy tờ đó sang
module kế toán của anh** để anh vào sổ. Bên em cần anh cho **ba thứ**, xếp theo mức cần:

| # | Cần gì | Để làm gì | Bên em đã làm sẵn |
|---|---|---|---|
| 1 | **Một đường nhận chứng từ** (`POST`) | Đẩy phiếu thu / chi / nhập kho / xuất kho / hoá đơn sang | Lớp đẩy, nút đẩy, thử lại khi lỗi, chống gửi trùng — chỉ chờ địa chỉ và token |
| 2 | **Danh mục mã tài khoản** (`GET`) | Ô chọn định khoản trên phiếu | Đang gọi `…/api/v1/common/country-accounts?tryAutoId=11` như EPL_System; có bản dự phòng khi chưa nối |
| 3 | *(nếu có)* **Công nợ phải thu / phải trả** (`GET`) | Hiện số nợ của khách và nhà cung cấp ngay trên màn vận tải | Chưa làm, chờ anh cho biết có hay không |

---

## 1. Đường nhận chứng từ — cái cần nhất

### 1.1 Gọi thế nào

```
POST {ĐỊA_CHỈ_GỐC}/api/v1/epl-lao/vouchers
Authorization: Bearer <token anh cấp>
Content-Type: application/json; charset=utf-8
```

Địa chỉ gốc và token do Sếp bên EPL đặt trong màn hình (không cần khởi động lại), hoặc đặt biến môi
trường `EPL_KE_TOAN_API`, `EPL_KE_TOAN_TOKEN`. Đường `/api/v1/epl-lao/vouchers` là **đề nghị** của bên
em — anh muốn tên khác thì báo, bên em đổi một dòng.

### 1.2 Gói tin gửi sang

Mỗi lần gọi là **một tờ**. Ví dụ một phiếu chi tạm ứng đi đường:

```json
{
  "source": "EPL_LAO",
  "ref": "PC_TU/2609/0003",
  "type": "PC_TU",
  "type_name": "Phiếu chi tạm ứng",
  "group": "payment",
  "date": "2026-09-16",
  "trip_no": "T4-0433-09/EPL",
  "party": { "kind": "tai_xe", "name": "ທ້າວ ບຸນມີ" },
  "amount": { "value": 640000, "currency": "LAK", "lak": 640000 },
  "entry": { "debit": "625", "debit_name": "Chi phí vận chuyển", "credit": "1011", "credit_name": "Tiền mặt bằng Kíp" },
  "memo": "Tạm ứng chi phí chuyến T4-0433-09/EPL",
  "lines": { "dong": [ { "item_key": "x_vn", "qty": 1, "unit_price": 430000, "currency": "LAK" }, { "item_key": "x_phone", "qty": 1, "unit_price": 150000, "currency": "LAK" } ] },
  "created_by": "ສົມໄຊ (Somchai)",
  "created_at": "2026-09-16T08:12:40"
}
```

| Trường | Nghĩa |
|---|---|
| `source` | Luôn `"EPL_LAO"` — để anh phân biệt với EPL_System bên Việt Nam |
| `ref` | **Số chứng từ bên em, duy nhất.** Xin anh dùng làm khoá chống trùng: cùng `ref` gửi hai lần thì bên anh chỉ có một phiếu |
| `type` · `type_name` | Mã và tên loại tờ — bảng ở mục 1.4 |
| `group` | Nhóm nghiệp vụ để anh rẽ phiếu: `receipt` (thu) · `payment` (chi) · `stock_in` · `stock_out` · `stock_adjust` · `invoice` · `other` |
| `date` | Ngày chứng từ, `YYYY-MM-DD` |
| `trip_no` | Số phiếu xuất xe liên quan, có thể `null` (bán hàng ngoài, tất toán) |
| `party.kind` | `khach` · `ncc` (nhà cung cấp) · `tai_xe` · `kho` · `chu_xe` (chủ xe liên kết) |
| `amount.value` · `currency` | Số tiền theo **tiền tệ gốc** trên tờ: `USD` · `LAK` · `CNY` · `THB` · `VND`. Cước bên Lào ký bằng tiền nào thì hoá đơn và phiếu thu mang tiền đó — đừng giả định USD |
| `amount.lak` | Đã quy về LAK theo tỷ giá khoá trên phiếu lúc lập — để anh khỏi tra tỷ giá |
| `entry.debit` · `credit` | Hai vế định khoản **gợi ý** theo quy trình bên Lào và mã anh Khampla cấp 22/09 (kho `1371`, NCC `4021`, tiền `1011/1012/1021/1022` chọn theo cách thu/chi × tiền tệ). Vế nào chưa có mã thì `null` kèm tên; anh là người quyết mã cuối |
| `lines` | Chi tiết dòng (JSON), tuỳ loại tờ; anh không cần đọc nếu chỉ vào sổ tổng |

### 1.3 Anh trả về thế nào

| Anh trả | Bên em hiểu |
|---|---|
| `200` hoặc `201` + `{"id": "<mã phiếu bên anh>"}` | Đã nhận. Bên em đánh tờ "đã đẩy" và **lưu mã của anh** để đối chiếu |
| `409` + `{"id": …}` | `ref` này anh đã có từ trước. Bên em cũng coi là đã đẩy |
| `4xx` khác | Gói tin sai — bên em ghi câu lỗi lên tờ, người dùng thấy và sửa |
| `5xx` hoặc không nối được | Bên em **giữ tờ chưa đẩy**, ghi lỗi, đếm lần thử; người dùng bấm đẩy lại sau |

Câu lỗi anh trả trong `message` hoặc `error` sẽ hiện nguyên lên màn của kế toán bên em, nên xin anh viết
câu người đọc hiểu.

### 1.4 Các loại tờ sẽ gửi

| `type` | Tờ | `group` | Nợ / Có gợi ý |
|---|---|---|---|
| `PC_TU` | Chi tạm ứng đi đường cho tài xế | payment | 625 / 1011·1012 |
| `PC_SC` | Chi sửa chữa, chi khác — từ mục V/VI của phiếu (`trip_no` có) **hoặc từ lệnh sửa chữa riêng** (`trip_no` = null, `lines.doc_no` = số lệnh `LSC-…`) | payment | 614 hoặc 625 / 1011·1012 |
| `PC_NCC` | Chi trả nhà cung cấp | payment | 4021 / 1011·1012 |
| `PC_CX` | Chi trả chủ xe liên kết | payment | 4022 / 1011·1012 |
| `TT_CHI` · `TT_THU` | Tất toán tài xế cuối tháng: chi bù · thu hoàn | payment · receipt | 625 / 1011 · 1011 / 625 |
| `HD` | Hoá đơn vận chuyển cho khách | invoice | 1211 / 70 |
| `PT` | Thu tiền khách | receipt | 1011·1012·1021·1022 / 1211 — chọn theo *cách thu* (mặt · ngân hàng) và *tiền tệ* (Kíp · khác) trên từng lần thu |

**Một hoá đơn có thể có NHIỀU tờ `PT`.** Khách trả làm mấy lần thì bấy nhiêu tờ, mỗi tờ một `ref` riêng,
và tiền của tờ `PT` **có thể khác tiền của tờ `HD`** — hoá đơn ghi USD mà khách chuyển Kíp là chuyện
thường ở đây. `payload` của tờ `PT` mang thêm `hoa_don_ccy`, `hoa_don`, `hoa_don_lak` để anh đối chiếu
về đúng hoá đơn, và `rate_to_lak` là tỷ giá ngày thu. Phần chênh lệch tỷ giá bên em **không hạch toán** —
để anh quyết.

**Một tờ `HD` có thể gồm NHIỀU phiếu xuất xe.** Khách có hợp đồng nhận **một hoá đơn gộp cả tháng**
(anh Khampla C8.2). Tờ `HD` khi đó **không gắn phiếu nào**, nên `trip_no` là `null`, còn `lines` mang
`inv_no` (`"HDT-202609-01"`), `period` (`"2026-09"`), `so_phieu`, và mảng `phieu[]` — mỗi phần tử có
`doc_no`, `doc_date`, `tan_tinh`, `don_gia`, `cach_tinh`, `thanh_tien`, `thanh_tien_lak`, `rate_to_lak`.
Tờ `PT` của hoá đơn gộp cũng có `trip_no = null`, `lines` thêm `inv_no`, `period` và `phan_bo[]`
(`doc_no` + `phan_bo_lak`) để anh thấy tiền được rải về phiếu nào. Khách vãng lai thì vẫn như cũ: một
tờ `HD` cho một phiếu, `trip_no` là số phiếu đó.

| `PXK_NL` · `PNK_NL` | Xuất · nhập kho nhiên liệu | stock_out · stock_in | 625 hoặc 4022 / 1371 · 1371 / 4021 |
| `PXK_PT` · `PNK_PT` | Xuất · nhập kho phụ tùng. Xuất cho lệnh sửa chữa riêng thì `trip_no` = null và `lines.repair_order` = số lệnh | stock_out · stock_in | 614 / 1371 · 1371 / 4021 |
| `PNK_HH` · `PXK_HH` | Nhập · xuất kho **hàng của khách** nằm bãi (quặng chờ đi cảng) — **ngoài bảng, ghi đơn**: nhập Nợ *hàng khách gửi*, xuất Có *hàng khách gửi*; **không đụng 1371** | stock_in · stock_out | *hàng khách gửi* / — · — / *hàng khách gửi* |
| `DC_HH` | Điều chỉnh kho hàng (có lý do) — chiều tăng/giảm ghi trong `lines` | stock_adjust | *hàng khách gửi* (ghi đơn) |
| `PXK_BAN` · `HD_BAN` · `PT_BAN` | Bán phụ tùng, xăng dầu ra ngoài | stock_out · invoice · receipt | *giá vốn* / 1371 · 1211 / 70 · 1011·1012 / 1211 |
| `DO` · `PLNL` · `PTU` | Phiếu xuất xe · phiếu lĩnh dầu · phiếu tạm ứng | other | không định khoản — gửi để anh có ngữ cảnh, anh bỏ qua được |

*Hàng khách gửi* và *giá vốn* là hai chỗ **bên em chưa có mã** — xem mục 4. Mã kho, nhà cung cấp và bốn mã tiền
do anh Khampla (EPL) cấp ngày 22/09 theo sá-la-ban kế toán doanh nghiệp Lào; bên em ghi theo **mã con** (1371, 4021).

---

## 2. Danh mục mã tài khoản — đang dùng

Bên em gọi `GET {ĐỊA_CHỈ_GỐC}/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true` với token,
giống EPL_System, đọc `Result[]` lấy `code`, `name`, `description`, giữ bộ nhớ 10 phút. Không nối được thì
dùng bản dự phòng gồm các mã đã thấy trong Excel của họ và **ghi rõ trên màn là đang dùng bản tạm**.

Nếu đường này với bên Lào khác (mã quốc gia không phải 11, hay danh mục riêng cho EPL Lào), anh cho biết
là bên em đổi cấu hình, không phải sửa mã.

---

## 3. Công nợ — nếu anh có sẵn

Màn vận tải muốn hiện "khách này đang nợ bao nhiêu" và "mình đang nợ nhà cung cấp này bao nhiêu" để
người điều xe biết trước khi nhận chuyến. Bên em **chỉ đọc và hiện**, không tính lại. Nếu anh có đường
dạng:

```
GET {ĐỊA_CHỈ_GỐC}/api/v1/epl-lao/balances?party_kind=khach&party_name=...
→ { "receivable": 3384.96, "currency": "USD", "as_of": "2026-09-21" }
```

thì bên em nối; chưa có thì thôi, không chặn gì.

---

## 4. Hai mã bên em còn thiếu — đã chốt logic, chỉ chờ anh cho MÃ

Bên em đã phân tích lại (22/09) và **chốt cách ghi**; anh chỉ cần cho hai con mã. Có mã thì **Sếp gõ
vào màn Chứng từ → Cấu hình**, mọi tờ sinh sau đó mang mã ngay — không phải sửa mã nguồn, không phải
chờ bên em.

### 4.1 Quặng của khách nằm bãi — NGOÀI BẢNG, không phải tồn kho EPL

Quặng đi hai chặng: xe gom từ mỏ về bãi Thà Bốc, nằm đó vài ngày, rồi xe khác chở ra cảng. Trong lúc
nằm bãi nó là **hàng của khách gửi giữ hộ**, EPL không mua, không bán, không sở hữu. Trước đây bên em
ghi Nợ kho **1371** khi nhập — thế là tồn kho của EPL phình lên bằng hàng của người khác, và bảng cân
đối kế toán nói sai về tài sản công ty. Nay bên em **bỏ 1371 khỏi ba tờ này**.

Cách ghi đề nghị (giống tài khoản ngoài bảng *"vật tư, hàng hoá nhận giữ hộ"* trong hệ Việt Nam, TK 002):

| Tờ | Ghi đơn | `lines` mang gì |
|---|---|---|
| `PNK_HH` nhập kho hàng | **Nợ** *mã anh cấp* | `tan`, `boc_len`, `hao_hut`, lô, số phiếu gom |
| `PXK_HH` xuất kho hàng đi giao | **Có** *mã anh cấp* | `tan`, từng lô lấy ra, số phiếu giao |
| `DC_HH` điều chỉnh kho | Nợ hoặc Có theo chiều trong `lines` | `chieu`, `tan`, lý do |

Số lượng tấn luôn đi đủ trong `lines` — nếu bên anh chỉ theo dõi ngoài bảng theo tấn (không tiền) thì
`amount` của ba tờ này anh bỏ qua được. Nếu bên anh **không** theo dõi hàng giữ hộ trên sổ, anh nói một
câu, bên em vẫn gửi để anh có ngữ cảnh, anh bỏ qua như tờ `DO`.

**Anh cần cho:** một mã tài khoản ngoài bảng cho *hàng khách gửi giữ hộ* (ô cấu hình `ma_hang_khach_gui`).

### 4.2 Giá vốn hàng bán — chỉ khi bán phụ tùng, dầu ra ngoài

EPL thỉnh thoảng bán phụ tùng hoặc dầu cho bên ngoài. Tờ `PXK_BAN` là xuất kho bán: **Có 1371** (kho
giảm — đúng, đây là hàng của EPL) và **Nợ *giá vốn***. Bên em không tự đặt mã lớp 6 theo Lào vì không
chắc bên anh dùng mã nào cho *giá vốn / biến động tồn kho*.

**Anh cần cho:** mã tài khoản *giá vốn hàng bán* (ô cấu hình `ma_gia_von`).

### 4.3 Đã có từ anh Khampla (22/09), anh xem có khớp danh mục bên anh không

Kho **1371** (mẹ 137) · nhà cung cấp **4021** (mẹ 402, tách theo NCC) · tiền mặt Kíp **1011** · tiền mặt
ngoại tệ **1012** · ngân hàng Kíp **1021** · ngân hàng ngoại tệ **1022**. Anh muốn ghi theo mã mẹ thay mã
con thì báo, bên em đổi một bảng.

### 4.4 Một loại tờ `PT` mới về nội dung, không mới về hình dạng: cấn trừ

Khách trả hộ EPL hai thứ — quẹt **thẻ cao tốc** khách tự nạp, và **trạm dầu bên Việt Nam ghi nợ** rồi
khách trả — cuối tháng bên em bù vào cước phải thu của chính khách đó. Trên gói tin đó là tờ `PT`
bình thường, chỉ khác `lines.method = "offset"` và `lines.ref = "CT-YYYYMM"`; vế Có vẫn `1211`, vế Nợ
theo cách thu *offset* (bên em để `1011`; anh muốn tài khoản trung gian khác thì cho mã, bên em đổi).

---

## 5. Cách thử với nhau

Bên em có sẵn `kiem/thu_day_ke_toan.py`: nó dựng một máy nhận giả đóng vai API của anh, đẩy 38 tờ mẫu
qua, thử cả trường hợp anh trả 500 và 409. Khi anh có đường thật ở môi trường thử, chỉ cần Sếp bên EPL
đặt địa chỉ và token trong màn Sổ chứng từ → bấm *Đẩy hết* → anh kiểm phiếu bên anh, bên em kiểm cột
"Mã phiếu bên kế toán" bên này. Tờ nào anh từ chối sẽ hiện câu lỗi của anh ngay trên dòng đó.

**Cập nhật 22/09/2026 — đã có bên nhận chạy thật.** Dự án `EPL_KETOAN` (cổng 8030, DB `epl_ketoan`) nhận đúng
gói tin ở mục 1, chống trùng theo `ref`, sinh một bút toán cho một tờ với hai vế lấy nguyên trên tờ, dựng Nhật ký
chung · Sổ cái · Cân đối phát sinh. Đã đẩy thật 57/57 tờ mẫu từ EPL_LAO_REAL sang, sổ cân (Nợ = Có). Anh có thể
lấy nó làm mẫu bên nhận, hoặc đối chiếu: cùng một gói JSON, bên anh trả gì thì bên em hiện đúng như vậy.
Một điểm hợp đồng rút ra khi thử thật: lỗi 4xx bên nhận nên trả thân **phẳng** `{ma, loi, message}` (không bọc
trong `detail`) thì màn kế toán bên em mới hiện được câu lỗi thay vì chỉ "HTTP 422".

Liên hệ kỹ thuật bên em: [tên · điện thoại].
