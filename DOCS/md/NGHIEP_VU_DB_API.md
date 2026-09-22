# EPL Lào — nghiệp vụ, cơ sở dữ liệu và API

Viết cho người tiếp nhận hệ thống: lập trình viên bảo trì tiếp, và kế toán bên anh Khang cần biết lấy
dữ liệu ở đâu. Cập nhật 21/09/2026.

Ba phần: **A. Nghiệp vụ** (việc chạy thế nào ngoài đời) · **B. Cơ sở dữ liệu** (42 bảng) · **C. API**
(153 đường). Cuối cùng là phần **D. Chạy và kiểm**.

---

# A. Nghiệp vụ

## A0. Một chuyến hàng đi qua hai phiếu

Từ 21/09/2026, một chuyến quặng từ mỏ ra cảng đi qua **hai phiếu xuất xe (DO)**, nối nhau qua kho hàng
ở bãi Thà Bốc. Bãi đứng giữa như một bưu cục.

```
   MỎ (Kasi)                    BÃI THÀ BỐC                     CẢNG / KHÁCH
      │                              │                                │
      │ ── DO GOM (kind = gom) ────► │                                │
      │    cân tại mỏ                │  NHẬP KHO (PNK_HH)             │
      │    cước riêng cho chặng gom  │  lô hàng nằm bãi               │
      │                              │                                │
      │                              │ ── DO GIAO (kind = giao) ────► │
      │                              │  XUẤT KHO (PXK_HH)   cân tại cảng
      │                              │  chọn lấy từ lô nào   có cước → hoá đơn → thu tiền
```

Điểm cần nhớ:

- **Xe hai chặng có thể khác nhau.** Chặng gom xe 341 chở về, chặng giao xe 342 chở đi — bình thường.
- **Dây nối hai phiếu là lô hàng.** Mỗi dòng hàng của DO giao ghi rõ nó lấy của DO gom nào
  (`trip_goods.tu_phieu_id`). Nhìn một DO giao là biết hàng từ chuyến nào về; nhìn một DO gom là biết
  lô đó đã đi những chuyến nào.
- **Một DO gom có thể chia cho nhiều DO giao**, và một DO giao có thể gom hàng của nhiều lô.
- **Hao hụt ghi thành một dòng** trên phiếu (`trip_goods.loai = 'hao_hut'`) chứ không bắt người đọc trừ
  nhẩm: chặng gom là *cân mỏ − cân bãi*, chặng giao là *tấn xuất kho − cân nơi giao*.
- **Chỉ DO giao mới có cước và hoá đơn.** Xuất hoá đơn cho DO gom bị máy chủ từ chối.
- **Phiếu gom đã nhập kho thì dòng hàng và hai ô cân đóng lại** (mã lỗi `HANG_DA_NHAP_KHO`): sổ kho đã ghi
  theo số đó, sửa phiếu mà không sửa sổ là hai bên nói hai số. Phiếu giao đã tới vẫn sửa được cân cuối,
  sửa xong máy tính lại dòng hao hụt. Loại phiếu không đổi được khi đã có dòng hàng hay sổ kho
  (`KHONG_DOI_LOAI`).
- **Sai số sau khi đã nhập kho thì lập phiếu điều chỉnh kho**, không xoá phiếu giao để làm lại. Kế toán (KT
  Thu/Chi VC hoặc Sếp) ghi một dòng `adj` có dấu (+ tăng, − giảm) kèm lý do bắt buộc vào lô, sinh chứng từ
  `DC_HH`. Tồn lô không được âm sau điều chỉnh (`TON_AM`) — hàng đã xuất cho phiếu giao thì không thể
  "chưa từng có". Lịch sử nhập/xuất giữ nguyên, ai xem sổ cũng thấy đã sửa gì, vì sao, lúc nào.
- Vẫn cho phép **chạy thẳng mỏ → cảng** không qua kho: lập một DO giao và không chọn lô nào, nhập cân
  tay như cũ.

## A1. Sáu mục của một phiếu và chuỗi duyệt

Mỗi phiếu có sáu mục như tờ giấy của họ:

| Mục | Nội dung | Ai nhập | Ai kiểm | Ai ghi sổ | Ai chi |
|---|---|---|---|---|---|
| I | Thông tin xe | Kho Thabok | KT Thu/Chi VC | — | — |
| II | Khách hàng, vận chuyển, hàng, cân, giá | Kho Thabok | KT Thu/Chi VC | — | — |
| III | Chi phí xăng dầu | Kho Thabok | KT kho xăng dầu VC | KT kho xăng dầu VC | Thủ quỹ VC |
| IV | Chi phí đi lại | Kho Thabok | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt Thabok |
| V | Chi phí sửa chữa | Kho Thabok | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt Thabok |
| VI | Chi phí khác | Kho Thabok | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt Thabok |
| — | Hoá đơn, thu tiền khách | KT Doanh thu VC | — | KT Doanh thu VC | — |

Mỗi mục đi qua chuỗi `chờ → đã nhập → đã kiểm → đã ghi sổ → đã chi`. Người nhập chỉ sửa được khi mục
còn *chờ* hoặc *đã nhập*; kiểm rồi là khoá, muốn sửa phải **trả lại**. Chỉ Sếp mở khoá được.

Luật ở `services/phan_quyen.py`, một bảng duy nhất — sửa quyền thì sửa đúng chỗ đó.

## A1b. Hai vai riêng ở Thà Bốc và việc đổi xe

**Hai vai mới** (anh Khampla C1.2): *kho phụ tùng* và *tổ sửa chữa* ở Thà Bốc là **người riêng**, không
phải Admin Bãi. Nên từ 22/09:

| Vai | Làm gì | Rút khỏi ai |
|---|---|---|
| `parts` — Thủ kho phụ tùng Thà Bốc | Nhập · xuất kho phụ tùng (`/api/parts/…`) | Bãi và kế toán không còn sửa kho phụ tùng |
| `repair` — Tổ sửa chữa Thà Bốc | **Nhập mục V**, duyệt báo hỏng của tài xế, quyết lấy phụ tùng từ kho hay ra gara, lập **lệnh sửa chữa riêng** | Bãi không còn nhập mục V, không duyệt báo hỏng |

Chuỗi duyệt mục V vẫn như cũ: tổ sửa chữa nhập → **KT Chi phí VC** kiểm và ghi sổ → **Quỹ tiền mặt**
chi. Tổ sửa chữa không tự kiểm, không tự chi. Hai vai này xếp cùng nhóm với Bãi ở khoản **không thấy
tiền bán**.

**Đổi xe giữa đường** (C2.2): xe hỏng nặng thì đổi xe khác chở tiếp **trên chính tờ phiếu đang chạy** —
`POST /api/trips/{id}/doi-xe` (Bãi). Không lập phiếu mới, vì hàng, khách, tuyến và tiền đã chi vẫn là
của chuyến đó; lập phiếu mới là tách đôi một chuyến trong mọi báo cáo. Máy ghi xe mới vào phiếu, để lại
một dòng diễn biến *Đổi xe A → B · lý do*, kéo **mục I về "đã nhập"** để kế toán kiểm lại, cho xe cũ vào
xưởng và xe mới sang *đang chạy*. Đổi sang xe liên kết thì phiếu tự chuyển sang `company = joint` và lấy
phí của chủ xe đó.

## A2. Ai thấy tiền nào

**Kho Thabok thấy mọi khoản CHI** (dầu, đi đường, sửa chữa, giá nhập kho) vì chính họ chi và họ nhập.

**Kho Thabok không thấy TIỀN BÁN**: đơn giá cước, doanh thu, hoá đơn và tiền thu khách, giá thuê xe
liên kết, khấu trừ chủ xe, lãi chuyến, mã tài khoản. Đó là biên lợi nhuận của công ty (khách trả giá 2,
thuê lại xe ngoài giá 1).

Giao diện giấu bằng lớp CSS `tien` trên thân trang `vai-<vai>`; **máy chủ cũng bỏ hẳn các khoá đó** ở
hai báo cáo của màn Tổng quan (`thay_tien_ban()` trong `services/phan_quyen.py`). Các API khác còn trả
đủ — xem mục B1 trong `CONG_VIEC_CHO_ANH_KHAMPLA_CHOT.md`.

## A3. Nhiên liệu — hai đường

1. **Đổ ở kho dầu EPL**: Bãi khai số lít và nơi đổ → in **phiếu lĩnh có mã QR** → thủ kho quét mã, cấp
   dầu, nhập số lít thật → tồn kho trừ ngay, sinh **PXK_NL**, định khoản `625/1371` (xe nhà) hoặc
   `4022/1371` (xe liên kết).
2. **Đổ dọc đường bên Việt Nam**: tài xế khai trên điện thoại (lít, trạm, đơn giá VND) → KT kho xăng dầu
   duyệt → thành một dòng mua ngoài ở mục III, tự quy đổi LAK theo tỷ giá ghi trên phiếu.

## A4. Tiền đi đường trả đúng lúc

| Khoản | Cách trả | Phần mềm làm |
|---|---|---|
| Chi tiêu đi VN, điện thoại | Trả ngay khi xe xuất phát | **Phiếu tạm ứng có QR**, quỹ quét mã chi; chưa nhận tiền thì chưa bấm được *Xuất phát* |
| Tiền nước, tiền chuyến | Trả theo chuyến cùng lương | **Tất toán tài xế theo tháng**: đã ứng bao nhiêu, chi thật bao nhiêu, dương công ty trả thêm, âm tài xế nộp lại |
| Shipping Lào, Việt | Nợ nhà cung cấp | Màn **Theo dõi nhà cung cấp**, trả theo đợt |
| Cao tốc | Trả qua thẻ | Ghi như khoản chi thường (chưa theo dõi số dư thẻ) |

## A5. Xe về, khoá phiếu, hoá đơn, xe liên kết

- Xe tới nơi → Bãi bấm *Xe đã tới*, nhập cân cuối, km về, ngày về. **DO gom** thì hàng vào kho ngay lúc
  này; **DO giao** thì máy ghi dòng hao hụt.
- Kế toán bấm **Khoá phiếu**: máy rà km lệch quá 10 %, hao hụt quá 1,5 %, thiếu cân, thiếu phiếu quặng,
  thiếu dòng hàng, mục có chi mà chưa kiểm. Chỉ cảnh báo, kế toán xác nhận thì vẫn khoá được.
- **Chỉ phiếu đã khoá mới xuất hoá đơn** (`1211/70`) và mới ghi thu tiền.
- **Hai kiểu hoá đơn** (anh Khampla C8.2): khách vãng lai thì **mỗi phiếu một tờ** — bấm *Xuất hoá đơn*
  ngay trên phiếu như cũ; khách **có hợp đồng** thì cuối tháng gộp **một tờ cho cả tháng** ở màn
  *Hoá đơn gộp tháng*. Xem A8.
- **Xe liên kết**: EPL trả chủ xe = giá thuê × tấn (hoặc giá trọn chuyến) − phí %/phiếu − mức trừ mỗi tấn vượt
  ngưỡng − các khoản EPL đã ứng (quy về tiền thuê). **Phí, ngưỡng tấn, mức trừ là điều khoản của từng chủ xe**
  (danh mục *Chủ xe liên kết* trên màn Xe liên kết): lập phiếu cho xe của chủ nào thì tự điền theo chủ đó, kế
  toán vẫn sửa được trên phiếu. Lãi = tiền khách trả − tiền thuê, cùng quy về Kíp rồi trừ. **Trả chủ xe theo
  cách đã thoả thuận với từng chủ**: từng phiếu ngay sau khoá, gộp cuối tháng, hay theo đợt — quỹ tích các
  phiếu đã khoá chưa trả rồi bấm *Trả gộp*, một đợt sinh một tờ `PC_CX` và các phiếu trong đợt đánh *đã trả*.
  Các phiếu trong một đợt phải cùng tiền thuê. Xem A7 về tiền tệ.

## A7. Tiền tệ và thu tiền

EPL Lào **nhận cước bằng nhiều loại tiền**: USD, Kíp Lào (LAK), Nhân dân tệ (CNY), Bath Thái (THB) —
tuỳ hợp đồng từng khách. Chi phí dọc đường thì trộn LAK, VND, THB ngay trong cùng một phiếu. Nên
phần mềm đặt ba quy tắc:

**1. Kíp là tiền gốc.** Mọi tỷ giá ghi dạng *bao nhiêu Kíp cho một đơn vị tiền đó*, và được **khoá
vào phiếu lúc lập** (`rate_usd`, `rate_thb`, `rate_vnd`, `rate_cny`). Tỷ giá thị trường đổi về sau
không làm đổi con số trên phiếu đã lập — tờ giấy đã in phải đứng yên.

**Cách tính cước** (anh Khampla C3.6): `price_mode = ton` là đơn giá × tấn cân nơi giao (khách có hợp đồng);
`chuyen` là **giá trọn chuyến**, không nhân tấn (xe ngoài không hợp đồng). Bảng giá mang cách tính, phiếu tự
điền theo; giá thuê chủ xe đi theo cùng cách. Phần trừ quá tải vẫn theo tấn.

**2. Cước theo tiền của hợp đồng, không mặc định USD.** Phiếu có ô **Tiền tệ cước** (`price_ccy`) và
đơn giá `price` hiểu theo tiền đó. Bảng giá khách × tuyến cũng mang tiền tệ riêng, nên mở phiếu cho
khách Trung Quốc là máy tự điền Nhân dân tệ, không rơi về USD. Xe liên kết có thêm **tiền tệ thuê**
(`hire_ccy`) vì bán bằng USD mà thuê xe Lào trả bằng Kíp là chuyện bình thường; bỏ trống thì hiểu là
cùng tiền với cước.

**Đặt tỷ giá ở đâu**: màn **Tỷ giá** (`#/ty-gia`, nhóm Danh mục) — mỗi loại tiền một thẻ đọc là
*"1 đơn vị tiền đó ăn bao nhiêu Kíp"*, kèm số lần trước, mức thay đổi, người đặt, một máy tính quy
đổi chạy theo con số **đang gõ** (chưa lưu cũng thử được), và bảng lịch sử mọi lần đổi. Kế toán
Thu/Chi VC và Kế toán Doanh thu VC sửa được; các vai tiền khác chỉ xem; Bãi và tài xế không thấy màn
này nhưng vẫn **đọc** được tỷ giá qua `/api/rates` vì chi phí của họ có VND và THB.

**3. Mọi TỔNG quy về Kíp, kèm chia theo từng loại tiền.** Cộng thẳng USD với Nhân dân tệ là cộng táo
với cam, nên báo cáo trả `doanh_thu_lak` (một con số cộng được) và `doanh_thu_tien`
(`{"USD": 5059, "CNY": 12618, "LAK": 37710000}`) để người đọc thấy con số đó gồm những gì. Bảng
*Theo dõi phiếu vận chuyển* có thêm cột **Tiền** nói rõ từng dòng tính bằng tiền gì, dòng tổng cộng
riêng từng loại tiền, và ô **Quy đổi** để gom cả bảng về một tiền khi cần một con số duy nhất.

### Khách trả tiền — sổ thu từng lần

Trước 21/09/2026 chỗ này chỉ là một cái nút *đã thu* bật trạng thái phiếu sang `paid`. Nó không ghi
được khách trả bao nhiêu, bằng tiền gì, ngày nào — trong khi thực tế **hoá đơn ghi USD mà khách
chuyển Kíp**, và trả làm nhiều lần. Giờ mỗi lần tiền về là **một dòng** trong bảng `trip_payments`:

| Ô | Nghĩa |
|---|---|
| `pay_date` | Ngày tiền về |
| `amount` · `currency` | Số tiền và **tiền khách thật sự trả** — không bắt buộc trùng tiền hoá đơn |
| `rate_to_lak` | Tỷ giá **ngày thu**; không gửi thì lấy tỷ giá khoá trên phiếu làm mặc định |
| `amount_lak` | `amount × rate_to_lak`, tính sẵn để khỏi tính lại |
| `method` | `cash` tiền mặt · `bank` chuyển khoản · `offset` cấn trừ · `other` |
| `ref` | Số uỷ nhiệm chi hoặc biên lai bên khách |

Từ đó: **trạng thái tài chính của phiếu do tổng các dòng này quyết định**, không ai bấm tay nữa —
chưa có dòng nào là *chưa thu*, tổng bằng tiền hoá đơn (lệch dưới 1 Kíp) là *đã thu*, ở giữa là *thu
một phần*. Mỗi dòng thu để lại một chứng từ `PT` mang đúng số tiền và tiền tệ khách trả, nên khi đẩy
sang kế toán anh Khang thì con số khớp với tiền thật vào tài khoản.

Hai chỗ chặn: thu **nhiều hơn phần còn lại** của hoá đơn thì máy hỏi lại (`THU_QUA_HOA_DON`) rồi mới
ghi; xoá một lần thu mà tờ `PT` của nó **đã đẩy sang kế toán** thì từ chối (`DA_DAY_KE_TOAN`) — bên
kia đã vào sổ, xoá lặng lẽ bên này là hai bên nói hai số.

Phần chênh lệch tỷ giá (hoá đơn 1.693,30 USD quy 37.252.600 Kíp mà khách chuyển 37.000.000 Kíp) thì
phần mềm **chỉ hiện ra**, hạch toán chênh lệch tỷ giá là việc của bên kế toán — bên mình không dựng
sổ thứ hai.

## A8. Hoá đơn gộp tháng — một tờ nhiều phiếu

Anh Khampla trả lời 22/09 (C8.2, B3): **cả hai kiểu đều có**. Khách chạy lẻ vài chuyến thì lấy hoá đơn
từng phiếu; khách có hợp đồng chạy vài chục chuyến một tháng thì **cuối tháng nhận một tờ**, không ai
muốn cầm ba mươi tờ hoá đơn. Nên danh mục khách có ô **Cách xuất hoá đơn**:

| Giá trị | Nghĩa |
|---|---|
| `phieu` (mặc định) | Mỗi phiếu một hoá đơn — kế toán doanh thu bấm *Xuất hoá đơn* trên từng phiếu |
| `thang` | Gộp một tờ cuối tháng — nút trên phiếu bị chặn (`GOP_THANG`), làm ở màn *Hoá đơn gộp tháng* |

**Cách làm cuối tháng**: vào `#/hoa-don-gop`, chọn tháng. Bảng *Chờ gộp* liệt kê từng khách × từng loại
tiền cước còn phiếu **đã khoá, đã kiểm mục II, chưa lên hoá đơn**. Bấm *Gộp hoá đơn tháng* → một tờ
`HDT-YYYYMM-NN` mang nhiều dòng phiếu, và **một** chứng từ `HD` cho cả tờ (không phải mỗi phiếu một tờ).

Hai quy tắc giữ cho con số không bao giờ lệch:

1. **Tiền của tờ = cộng doanh thu từng phiếu**, máy tính, không gõ tay. Một tờ chỉ mang **một loại tiền**:
   khách ký tuyến này USD, tuyến kia Kíp thì cuối tháng là hai tờ, chứ không cộng hai thứ tiền vào nhau.
2. **Thu tiền ghi ở TỜ, nhưng phân bổ xuống từng phiếu.** Khách chuyển một cục cho cả tháng; nếu chỉ ghi
   ở tờ thì mọi phiếu trong tháng vẫn treo *chưa thu* và báo cáo theo phiếu sai hết. Nên mỗi lần thu sinh
   một dòng `invoice_payments` (một tờ `PT`) rồi **rải xuống `trip_payments` theo thứ tự ngày phiếu** —
   phiếu cũ trả trước, đúng cách họ đối chiếu công nợ. Trạng thái từng phiếu vẫn do tổng `trip_payments`
   quyết định như mọi phiếu khác, không có đường tính thứ hai.

Chặn đúng chỗ: ghi thu ở phiếu nằm trong tờ gộp → `THU_QUA_HD_GOP` (thu ở tờ); xoá lẻ dòng phân bổ ở
phiếu → `THUOC_HD_GOP` (xoá lần thu ở tờ); huỷ tờ khi đã thu → `DA_THU`; huỷ tờ mà chứng từ `HD` đã đẩy
sang kế toán → `DA_DAY_KE_TOAN`. Huỷ được thì các phiếu quay lại *chưa xuất hoá đơn*, gộp lại tháng khác.

## A9. Lệnh sửa chữa riêng — không gắn phiếu

Mục V trên phiếu chỉ ghi được cái sửa **trong một chuyến**. Xe nằm bãi cả tuần đại tu, hay bảo dưỡng
định kỳ theo số km, thì không có chuyến nào để gắn vào — trước đây tiền sửa đó không khai được ở đâu
(anh Khampla C7.3). Nên có tờ **lệnh sửa chữa** (`LSC-2609-01`) cho đúng việc đó, đi qua **cùng chuỗi
duyệt của mục V**, không đẻ luật mới:

    Tổ sửa chữa NHẬP → KT Chi phí KIỂM → KT Chi phí GHI SỔ → Quỹ tiền mặt CHI

Mỗi tờ gắn **một chiếc xe**, có loại (*sửa hỏng* · *bảo dưỡng định kỳ*), số công-tơ-mét lúc vào xưởng,
gara ngoài (để trống là làm tại Thà Bốc), và các dòng chi giống hệt dòng mục V. Quy tắc kho của họ giữ
nguyên: **lấy từ kho** thì trừ tồn **ngay lúc khai** và sinh tờ `PXK_PT` (định khoản `614/1371`);
**mua ngoài** thì tới bước chi mới sinh **một** tờ `PC_SC` gồm riêng phần mua ngoài (`614/4021`). Lập
lệnh thì xe sang *đang sửa*; chi xong thì xe về *rảnh*.

Màn **Xe → tab Sửa chữa** gom cả hai nguồn: dòng mục V từ phiếu và dòng từ lệnh sửa chữa, cùng một bảng
xếp theo ngày — người xem chi phí một chiếc xe không phải nhớ nó nằm ở đâu.

## A10. Khách trả hộ — thẻ cao tốc và nợ trạm dầu Việt Nam

Hai chỗ tiền chạy **ngược chiều với cước**, cả hai đều là "khách trả hộ EPL", nên cuối tháng đem cấn
trừ vào cước phải thu của chính khách đó.

**1. Thẻ cao tốc** (C6.1). Danh mục thẻ có số thẻ, ai giữ, gắn xe nào, tiền tệ và **số dư**. Hai kiểu:

| Kiểu | Ai bỏ tiền | Cuối tháng |
|---|---|---|
| `khach` | Khách cấp thẻ và nạp tiền | Phần EPL đã quẹt **trừ vào cước** của khách đó |
| `epl` | Quỹ Thà Bốc nạp | Là chi phí của EPL như mọi khoản đi đường |

Thẻ là một "kho tiền" nhỏ, ghi giống kho nhiên liệu: nạp tiền là một dòng; qua trạm là một dòng, và
**chỉ sinh khi kế toán GHI SỔ mục IV** — đúng lúc dòng xuất kho nhiên liệu được sinh. Trước đó dòng
chi còn sửa tới sửa lui, trừ sớm thì số dư nhảy loạn; `trip_expenses.card_move_id` bảo đảm không trừ
hai lần, và dòng đã trừ thẻ thì không xoá lặng lẽ khỏi phiếu được. Số dư sổ lệch với trạm (ai đó quẹt
mà không khai) thì ghi một dòng **điều chỉnh kèm lý do**, không sửa thẳng con số.

**2. Nợ trạm dầu Việt Nam** (C5.1). Tài xế đổ dầu bên Việt Nam có hai cách trả, và phần mềm phải phân
biệt được: **trả tiền mặt tại trạm** (EPL không nợ ai) hay **trạm ghi sổ** — ô *Ghi nợ tại trạm* trên
dòng chi. Dòng đổ ở trạm ngoài tự mang nhà cung cấp của trạm, nên công nợ tra được thẳng từ dòng chi;
công nợ trạm **chỉ gồm phần ghi nợ**. Trạm nào cuối tháng cấn trừ vào cước khách nào thì ghi khách đó
trong hồ sơ nhà cung cấp.

**Bảng cấn trừ cuối tháng** (màn *Theo dõi nhà cung cấp*, `GET /api/bao-cao/can-tru?thang=`) đặt ba
con số cạnh nhau cho từng khách: **cước phải thu** · **khách trả hộ qua thẻ** · **nợ trạm dầu VN** →
**còn phải thu**. Bên mình chỉ ghi và hiện; bút toán cấn trừ là việc của bên kế toán anh Khang.

## A6. Sổ chứng từ

Mỗi bước sinh tiền hoặc hàng để lại **một tờ có số** cho kế toán kéo về (`GET /api/chung-tu`), số dạng
`LOAI/YYMM/000n`:

| Mã | Tờ | Sinh khi |
|---|---|---|
| `DO` | Phiếu xuất xe | Lập phiếu |
| `PNK_HH` | **Phiếu nhập kho hàng** | DO gom về tới bãi |
| `PXK_HH` | **Phiếu xuất kho hàng** | DO giao lấy hàng khỏi lô |
| `DC_HH` | **Phiếu điều chỉnh kho hàng** | Kế toán sửa tồn một lô có lý do |
| `PLNL` | Phiếu lĩnh nhiên liệu | Bãi cấp phiếu QR cho tài xế |
| `PXK_NL` / `PNK_NL` | Xuất / nhập kho nhiên liệu | Thủ kho cấp dầu · nhập dầu |
| `PXK_PT` / `PNK_PT` | Xuất / nhập kho phụ tùng | Khai sửa chữa lấy kho · nhập phụ tùng |
| `PTU` / `PC_TU` | Phiếu tạm ứng · chi tạm ứng | Bãi lập · quỹ chi |
| `PC_SC` | Chi sửa chữa, chi khác | Quỹ chi mục V, VI |
| `PC_NCC` | Chi trả nhà cung cấp | Trả theo đợt |
| `PC_CX` | Chi trả chủ xe liên kết | Quỹ bấm trả chủ xe |
| `HD` / `PT` | Hoá đơn · phiếu thu khách | KT doanh thu |
| `TT_CHI` / `TT_THU` | Tất toán tài xế | Chốt tháng |
| `PXK_BAN` / `HD_BAN` / `PT_BAN` | Bán phụ tùng, xăng dầu ra ngoài | Màn Bán hàng |

**Đẩy sang kế toán**: mỗi tờ là một `POST {api}/api/v1/epl-lao/vouchers` với `ref` = số chứng từ làm khoá chống
trùng; bên kia trả `id` thì tờ đánh đã đẩy và giữ mã đó; trả lỗi thì tờ giữ nguyên, ghi câu lỗi lên dòng để bấm lại.
Hợp đồng JSON đầy đủ gửi anh Khang ở `HOP_DONG_API_ANH_KHANG.md`; lớp đẩy ở `services/day_ke_toan.py`.

Định khoản là **gợi ý** theo quy trình của họ, không phải sổ kế toán: bên mình không ghi bút toán,
không cộng sổ. Mã tài khoản (anh Khampla trả lời 22/09, theo sá-la-ban kế toán doanh nghiệp Lào): kho
`1371` (con của 137), nhà cung cấp `4021` (con của 402, tách theo NCC), tiền mặt Kíp `1011`, tiền mặt
ngoại tệ `1012`, ngân hàng Kíp `1021`, ngân hàng ngoại tệ `1022` — vế tiền chọn tự động theo cách thu/chi
và tiền tệ của tờ; phải thu `1211`, doanh thu `70`,
chi phí `625` (xe nhà) / `614` (sửa chữa) / `4022` (xe liên kết). **Mã tiền mặt và ngân hàng chưa có** —
để trống tên, chờ bên kế toán cấp (hàng khách gửi, giá vốn). Tất cả nằm ở `services/chung_tu.py`.

---

# B. Cơ sở dữ liệu

PostgreSQL, DB riêng **`epl_lao`**, khai trong `.env` (`DATABASE_URL`, không commit). Không có tầng
migration: `tao_bang()` trong `database.py` chạy `create_all` rồi **so cột model với cột thật và ALTER
TABLE ADD COLUMN** cho phần thiếu — chỉ thêm, không đổi kiểu, không xoá, nên không bao giờ mất dữ liệu.

42 bảng, nhóm theo việc:

## B1. Người dùng và danh mục

| Bảng | Giữ gì | Cột đáng chú ý |
|---|---|---|
| `users` | Tài khoản và vai | `role` (10 vai), `driver_id`, `place_id` (thủ kho gắn điểm đổ) |
| `customers` | Khách nhận quặng | `name`, `phone`, `active` |
| `customer_rates` | **Bảng giá khách × tuyến** | `price` + **`price_ccy`** + **`price_mode`** (`ton` theo tấn · `chuyen` trọn chuyến), `hire_price` + `hire_ccy`, `valid_from`, `goods_type` |
| `owners` | **Chủ xe liên kết** (anh Khampla C4.2 · C4.3) | `name`, `phone`, **`fee_pct`**, **`over_limit_t`**, **`over_price`**, `hire_ccy`, **`pay_mode`** (`phieu` từng phiếu · `thang` gộp tháng · `dot` theo đợt), `active`. Lập phiếu cho xe của chủ nào thì phí tự điền theo chủ đó |
| `owner_payments` | **Một đợt trả chủ xe** — một hay nhiều phiếu đã khoá, cùng tiền thuê | `owner_id`, `pay_date`, `amount` + `currency`, `amount_lak`, `method`, `ref`. Số tiền = tổng "trả chủ xe" của các phiếu trong đợt, máy tính; phiếu trỏ về đợt qua `trips.owner_payment_id` |
| `vehicles` | Đầu kéo | `truck_no`, `plate_head`, `owner_type` (EPL/joint), **`owner_id`** (chủ xe trong danh mục, tên chép sang `owner_name`), `trailer_id`, ba hạn giấy tờ, `odometer_km`, `next_service_km`, `fuel_norm`, `engine_cap`, `box_size`, `tyre` |
| `trailers` | Rơ-moóc (thực thể riêng) | `plate`, `trailer_type`, `capacity_t`, `status` |
| `trailer_assignments` | Lịch sử lắp/tháo | `attached_at`, `detached_at`, `reason` |
| `drivers` | Tài xế | `driver_code`, `name` + `name_latin`, `role`, bằng lái hiện hành (`license_no`, `license_type`, `license_status`, hai mốc hạn), **`license_class_hr`** (hạng ghi trong hồ sơ nhân sự — lệch với hạng trên bằng là dấu hiệu hồ sơ sai), `default_vehicle_id`, `status` |
| `driver_licenses` | Từng bằng lái và lần gia hạn | `license_no`, `valid_from`, `valid_to`, `issued_by`, `verified_by` |
| `routes`, `route_stops` | Tuyến và các chặng | `total_km`, `toll_lak`; mỗi chặng có `km_from_prev`, `lat`, `lng` |
| `suppliers`, `supplier_payments` | Nhà cung cấp và các đợt trả. **`customer_id`** = trạm này cuối tháng cấn trừ vào cước khách nào (C5.1) | |
| `exchange_rates` | Tỷ giá về LAK | USD, THB, VND, **CNY** — dùng làm mặc định cho phiếu mới; `by_user` ai đặt lần gần nhất |
| `exchange_rate_logs` | **Lịch sử tỷ giá** | Mỗi lần đổi một dòng: `rate_to_lak` số mới, `rate_cu` số cũ, `ap_dung_tu`, `nguon` (`tay`/`api`), `by_user`, `ghi_chu` |
| `fuel_places` | Điểm đổ dầu | `owner_type` (epl = kho mình, ngoài = mua) |

## B2. Phiếu xuất xe (DO) — trung tâm của hệ

| Bảng | Giữ gì |
|---|---|
| `trips` | Một phiếu. **`kind`** = `gom`/`giao`; số phiếu, ngày, xe và tài xế (chép giá trị vào phiếu, không chỉ khoá ngoại), khách, tuyến, cân đầu/cuối, **`price` + `price_ccy` + `price_mode`** (cước, tiền tệ, theo tấn hay trọn chuyến), phần xe liên kết (**`owner_id`**, `hire_price` + `hire_ccy`, `fee_pct`, `over_limit_t`, `over_price` — ba ô sau tự điền theo chủ xe, **`owner_payment_id`** = đã trả trong đợt nào), **bốn tỷ giá khoá trên phiếu** (`rate_usd`, `rate_thb`, `rate_vnd`, `rate_cny`), `locked`, `owner_paid` |
| `trip_goods` | **Dòng hàng**: `loai` = `hang`/`hao_hut`, `goods_name`, `qty_t`, **`tu_phieu_id`** = lô lấy từ DO gom nào |
| `goods_moves` | **Sổ kho hàng ở bãi**: `kind` = `in`/`out`/`adj` (điều chỉnh, `qty_t` có dấu), `qty_t`, `lo_trip_id` (lô = DO gom), `trip_id` (phiếu sinh ra dòng này), `note` (lý do điều chỉnh) |
| `trip_expenses` | Dòng chi của bốn mục III–VI: `section`, `item_key`, `qty`, `unit_price`, `currency`, `source` (kho/mua), `acct_code`, `paid_by_epl`, `stock_move_id` |
| `trip_sections` | Trạng thái duyệt từng mục I–VI |
| `trip_logs` | Nhật ký thao tác trên phiếu |
| `trip_events` | Diễn biến trên đường: tới điểm, sự cố, sửa xe, đổ dầu dọc đường (có `status` chờ duyệt) |
| `trip_payments` | **Sổ thu tiền**: mỗi lần khách trả một dòng — `pay_date`, `amount` + `currency`, `rate_to_lak`, `amount_lak`, `method`, `ref`. Trạng thái tài chính của phiếu suy ra từ tổng các dòng này |
| `trip_attachments` | Tệp đính kèm (phiếu quặng), tệp nằm trên đĩa `backend/tep`, bảng chỉ giữ tên |
| `vehicle_positions` | Vệt GPS do app tài xế gửi |

**Tồn kho hàng không có bảng riêng**: luôn cộng dồn từ `goods_moves`. Tồn của một lô = tấn nhập của lô
trừ tấn các DO giao đã lấy (`services/kho_hang.ton_lo`).

## B3. Kho, quỹ, chứng từ

| Bảng | Giữ gì |
|---|---|
| `fuel_moves` | Sổ kho nhiên liệu (nhập/xuất), tồn cộng dồn |
| `parts`, `part_moves` | Kho phụ tùng và sổ nhập xuất |
| `vouchers` | Phiếu lĩnh nhiên liệu và phiếu tạm ứng, có `token` cho mã QR, `status` chờ/đã cấp/huỷ |
| `driver_settlements` | Tất toán tài xế theo tháng |
| `chung_tu` | **Sổ chứng từ**: `loai`, `so`, `ngay`, `trip_id`, `tien_lak`, hai vế `no`/`co` gợi ý, `da_day`, `ma_ben_ke_toan` (mã phiếu bên anh Khang trả về), `loi_day` và `lan_thu` (đẩy hỏng vì sao, mấy lần), `payload` JSON chi tiết |
| `cau_hinh` | Cấu hình đặt trong màn hình: `ke_toan_api`, `ke_toan_token`; không có thì rơi về biến môi trường `EPL_<KHOA>` |
| `invoices` | **Hoá đơn gộp tháng** — một tờ nhiều phiếu: `inv_no` (`HDT-202609-01`), `customer_id`, `period` (`YYYY-MM`), `inv_date`, `currency`, `amount` + `amount_lak`, `so_phieu`. Phiếu trỏ về tờ qua `trips.invoice_id` |
| `invoice_payments` | **Một lần khách trả cho tờ gộp** — `pay_date`, `amount` + `currency` + `rate_to_lak` + `amount_lak`, `method`, `ref`. Phần rải xuống phiếu nằm ở `trip_payments.invoice_payment_id` |
| `repair_orders`, `repair_lines` | **Lệnh sửa chữa riêng** (C7.3): `doc_no` (`LSC-2609-01`), `vehicle_id`, `order_date`, `kind` (`sua_chua`/`bao_duong`), `odo_km`, `garage`, `status` (`entered`→`verified`→`booked`→`paid`); dòng chi có `source` (`kho`/`mua`), `part_id`, `stock_move_id`, `acct_code` |
| `toll_cards`, `toll_card_moves` | **Thẻ cao tốc** (C6.1): `card_no`, `kind` (`khach`/`epl`), `customer_id`, `driver_id`, `currency`, `balance`; mỗi dòng có `kind` (`nap`/`chi`/`dieu_chinh`), `amount`, `balance_after`, `trip_id` |
| `sales`, `sale_lines` | Bán phụ tùng, xăng dầu ra ngoài |

---

# C. API

153 đường, tất cả dưới `/api`, cùng cổng với giao diện. Xác thực: `POST /api/dang-nhap` trả token,
gửi lại ở `Authorization: Bearer <token>`. Vai nào gọi được gì ghi ngay dưới đây.

## C1. Đăng nhập và tài khoản — `routes/dang_nhap.py`

| Đường | Việc |
|---|---|
| `POST /api/dang-nhap` | Đăng nhập, trả token và thông tin người dùng |
| `GET /api/toi` | Người đang đăng nhập (khôi phục phiên) |
| `GET /api/tai-khoan-mau` | Danh sách tài khoản demo cho màn đăng nhập |
| `GET POST /api/users`, `PUT /api/users/{uid}` | Quản lý tài khoản (Sếp) |

## C2. Phiếu xuất xe — `routes/phieu.py`

| Đường | Việc |
|---|---|
| `GET /api/trips` | Danh sách phiếu (lọc `q`, `thang`…) |
| `GET /api/trips/{id}` | Một phiếu đầy đủ: dòng chi, **dòng hàng**, mục, nhật ký, diễn biến, chặng tuyến |
| `GET /api/trips-so-moi` | Cấp số phiếu kế tiếp |
| `POST /api/trips` | Lập phiếu. Nhận `kind` (`gom`/`giao`), `expenses[]`, **`goods[]`**. Chỉ Bãi và Sếp |
| `PUT /api/trips/{id}` | Sửa phiếu; chỉ ghi được ô của mục còn mở. Ô tiền của mục II do **người kiểm** mục đó sửa; **số và ngày phiếu quặng** cũng vậy (C3.7: kế toán nhập khi nhận giấy, Bãi chỉ đính kèm ảnh) |
| `DELETE /api/trips/{id}` | Xoá phiếu; chặn nếu đã có mục được kiểm, đã xuất kho, hoặc **lô đã có người lấy hàng** |
| `POST /api/trips/{id}/sections/{muc}/{hanh_dong}` | Chuyển bước một mục: `send`, `verify`, `return`, `book`, `pay`, `unlock` |
| `POST /api/trips/{id}/bao-ve` | **Tài xế báo đã về** (C2.1): ngày về, km về. Chỉ ghi hai số và đánh mốc tới điểm cuối, không tự chuyển "đã tới" — Bãi cân rồi mới xác nhận |
| `POST /api/trips/{id}/transport-status` | Xuất phát / tới nơi. Tới nơi: DO gom **nhập kho**, DO giao **ghi hao hụt** |
| `POST /api/trips/{id}/khoa`, `/mo-khoa`, `GET /kiem-lai` | Khoá phiếu sau khi xe về; Sếp mở khoá |
| `POST /api/trips/{id}/doi-xe` | **Đổi xe giữa đường** (C2.2, Bãi): `vehicle_id`, `ly_do` (bắt buộc), `driver_id`, `xe_cu_hong`. Ghi xe mới, để lại dòng diễn biến, mục I về *đã nhập*. Xe đã tới nơi → `PHIEU_DA_TOI` |
| `POST /api/trips/{id}/invoice` | Xuất hoá đơn **từng phiếu** — phiếu gom cũng xuất được (B4: khách trả cước riêng cho chặng gom). Khách để *gộp tháng* thì từ chối `GOP_THANG`, làm ở C8 |
| `GET POST /api/trips/{id}/thu-tien` · `DELETE /api/thu-tien/{id}` | **Sổ thu tiền**: xem, ghi một lần khách trả (tiền nào cũng được, có tỷ giá ngày thu), xoá dòng ghi nhầm. Thu dư phải xác nhận; tờ `PT` đã đẩy kế toán thì không xoá được. Phiếu nằm trong hoá đơn gộp thì ghi và xoá ở tờ gộp (`THU_QUA_HD_GOP`, `THUOC_HD_GOP`) |
| `POST /api/trips/{id}/tra-chu-xe` | Quỹ trả chủ xe **từng phiếu** → một đợt một phiếu, tờ `PC_CX`. Chủ xe trả gộp thì dùng `/api/owners/{id}/tra` |
| `GET POST DELETE /api/trips/{id}/tep`, `/api/tep/{aid}` | Tệp đính kèm (phiếu quặng) |
| `POST /api/trips/{id}/events`, `/bao-hong`, `/bao-nhien-lieu`, `/events/{eid}/duyet` | Diễn biến, báo hỏng, khai đổ dầu, duyệt |
| `GET /api/trips/{id}/phieu-chi`, `/phieu-thu` | Dữ liệu in phiếu chi, phiếu thu |
| `GET /api/khoan-muc` | Danh mục khoản chi và bảng định khoản mặc định |

## C3. Kho hàng ở bãi — `routes/kho_hang.py`

| Đường | Việc |
|---|---|
| `GET /api/kho-hang` | Tồn theo lô + sổ nhập xuất + tổng tồn |
| `GET /api/kho-hang/lo?tru_phieu=` | Các lô còn hàng, để DO giao chọn lấy từ đâu. `tru_phieu` = phiếu đang sửa, để nó không tự trừ mình |
| `POST /api/kho-hang/dieu-chinh` | Điều chỉnh tồn một lô `{lo_trip_id, qty_t (có dấu), ly_do}`. Chỉ KT Thu/Chi VC và Sếp |

## C4. Kho nhiên liệu, phụ tùng, phiếu lĩnh — `routes/kho.py`, `routes/phieu_linh.py`

| Đường | Việc |
|---|---|
| `GET POST DELETE /api/fuel-moves` | Sổ kho nhiên liệu |
| `GET POST PUT /api/parts`, `/api/parts/{id}/moves` | Kho phụ tùng |
| `GET POST /api/fuel-places`, `PUT DELETE /api/fuel-places/{id}` | Điểm đổ nhiên liệu |
| `POST GET /api/trips/{id}/vouchers`, `GET /api/vouchers` | Phiếu lĩnh và phiếu tạm ứng |
| `GET /api/vouchers/{id}/qr.png`, `GET /api/vouchers/tra-cuu/{token}` | Mã QR và tra cứu khi thủ kho quét |
| `POST /api/vouchers/{id}/cap`, `/huy` | Thủ kho cấp dầu · quỹ chi tiền · huỷ phiếu |

Kho phụ tùng (`POST PUT /api/parts`, `POST /api/parts/{id}/moves`) từ 22/09 chỉ **Thủ kho phụ tùng
Thà Bốc** và Sếp làm được (C1.2) — Bãi và kế toán chỉ xem.

## C5. Danh mục — `routes/danh_muc.py`, `routes/tuyen.py`

| Đường | Việc |
|---|---|
| `GET POST PUT /api/customers` | Khách hàng. Có **`invoice_mode`**: `phieu` mỗi phiếu một hoá đơn · `thang` gộp một tờ cuối tháng (C8.2) |
| `GET POST /api/customers/{id}/bang-gia`, `PUT DELETE /api/bang-gia/{id}` | **Bảng giá khách × tuyến**. Chỉ KT Thu/Chi VC và Sếp sửa; Bãi không xem được |
| `GET /api/bang-gia/tra?customer_id=&route_id=` | Hỏi giá hợp đồng — màn phiếu dùng để tự điền |
| `GET POST PUT /api/vehicles`, `GET /api/vehicles/{id}` | Xe đầu kéo, chi tiết kèm lịch sử rơ-moóc, chi phí sửa chữa, phiếu gần đây |
| `GET /api/vehicles/{id}/lich?tuan=` | **Lịch xe theo tuần** dựng từ phiếu và dòng sửa chữa |
| `POST /api/vehicles/{id}/trailer` | Lắp rơ-moóc; `trailer_id` rỗng là tháo. Máy chủ tự tháo khỏi xe cũ và ghi lịch sử |
| `GET POST PUT /api/trailers`, `GET /api/trailers/{id}` | Rơ-moóc, chi tiết kèm lịch sử lắp |
| `GET POST PUT /api/drivers`, `POST /api/drivers/{id}/licenses` | Tài xế và bằng lái |
| `GET PUT /api/rates` | Tỷ giá |
| `GET POST PUT /api/routes` | Tuyến đường và các chặng |

## C5a. Tài xế & bằng lái — `routes/danh_muc.py`

| Đường | Việc |
|---|---|
| `GET /api/drivers` | Danh sách, kèm **số phiếu đã chạy** và **phiếu đang cầm** (hai truy vấn gộp cho cả danh sách, không hỏi lại từng người) |
| `GET /api/drivers/{id}` | Hồ sơ đầy đủ: lịch sử bằng lái, mười phiếu gần đây |
| `POST PUT /api/drivers[/{id}]` | Thêm · sửa. Chỉ Bãi và Kế toán |
| `POST /api/drivers/{id}/licenses` | Ghi bằng mới / gia hạn: thêm một dòng lịch sử **và** cập nhật bằng hiện hành, đưa trạng thái bằng về `active` |
| `GET /api/drivers/{id}/lich?tuan=YYYY-MM-DD` | Lịch tuần, dựng từ chính các phiếu người này cầm — không có bảng lịch riêng |

**Cửa chặn điều phối.** Màn Tài xế tự trả lời "người này có được điều xe không, vì sao", sáu mức xếp
nặng dần: `missing` chưa có bằng · `inactive` bằng bị đình chỉ hoặc thu hồi · `expired` bằng hết hạn ·
`mismatch` hạng trên bằng khác hạng ghi trong hồ sơ · `soon` còn dưới 60 ngày · `ok`. Bốn mức đầu là
**chặn hẳn**, `soon` là cảnh báo cho chuyến xếp xa. Luật viết MỘT chỗ ở `frontend/modules/tai-xe/tai-xe.js`
và mở ra ngoài qua `EPL.taiXe.ketLuan` để màn Phiếu xuất xe dùng chung, không ai chép lại lần thứ hai.

## C5c. Chủ xe liên kết — `routes/chu_xe.py`

| Đường | Việc |
|---|---|
| `GET /api/owners` | Danh mục kèm xe của từng chủ; vai thấy tiền bán có thêm phí, mức trừ, và *chờ trả* (số phiếu đã khoá chưa trả, tổng theo tiền thuê). Bãi chỉ thấy tên và xe |
| `POST PUT /api/owners[/{id}]` | Thêm · sửa. Chỉ **KT Thu/Chi VC** và Sếp — phí, mức trừ, cách trả là điều khoản hợp đồng |
| `GET /api/owners/{id}/cong-no` | Phiếu đã khoá chưa trả (để tích vào một đợt) và các đợt đã trả |
| `POST /api/owners/{id}/tra` | **Quỹ trả một đợt**: `trip_ids[]`, `pay_date`, `method`, `ref`, `note`. Số tiền = tổng trả chủ xe của các phiếu, máy tính; các phiếu phải cùng chủ, đã khoá, chưa trả, cùng tiền thuê. Sinh một tờ `PC_CX` cho cả đợt |

## C5b. Tỷ giá — `routes/danh_muc.py`

| Đường | Việc |
|---|---|
| `GET /api/rates` | Dạng phẳng `{mã: tỷ giá}`, mọi màn đang gọi đường này. Phải đăng nhập; **mọi vai đều xem được** vì dòng chi có VND, THB |
| `GET /api/rates/chi-tiet` | Cho màn Tỷ giá: số đang áp dụng · số lần trước · mức đổi · ai đặt · lịch sử 200 dòng gần nhất |
| `PUT /api/rates` | Đặt tỷ giá mặc định cho phiếu **lập mới**. Chỉ KT Thu/Chi VC, KT Doanh thu VC và Sếp. Gõ lại đúng số cũ thì **không** ghi một dòng lịch sử rỗng; số ≤ 0 hoặc không phải số thì 422 |

Sửa tỷ giá **không bao giờ** làm đổi con số trên phiếu đã lập: phiếu khoá bốn tỷ giá của riêng nó
(`trips.rate_usd`…) ngay lúc lập. Màn hình nói thẳng câu đó ở đầu trang, vì hiểu nhầm chỗ này là
hiểu nhầm về tiền.

## C8. Hoá đơn gộp tháng — `routes/hoa_don.py`

Xem hoá đơn là **tiền bán**: Bãi, tài xế, thủ kho không gọi được (403). Lập tờ và thu tiền chỉ
**KT Doanh thu VC** và Sếp.

| Đường | Việc |
|---|---|
| `GET /api/hoa-don-gop/cho-gop?period=YYYY-MM` | Khách nào đang có phiếu chờ gộp trong tháng, **tách theo tiền cước**; kèm danh sách phiếu và tổng |
| `GET /api/hoa-don-gop?period=&customer_id=` | Các tờ đã gộp: tiền, số phiếu, đã thu, còn lại, trạng thái |
| `GET /api/hoa-don-gop/{id}` | Một tờ: từng dòng phiếu (tấn, đơn giá, thành tiền, đã thu, trạng thái) + sổ thu tiền + số chứng từ `HD` |
| `POST /api/hoa-don-gop` | **Gộp hoá đơn tháng**: `customer_id`, `period`, `currency` (bỏ trống = tiền của phiếu đầu), `inv_date`, `note`. Khách không để *gộp tháng* → `KHONG_GOP_THANG`; tháng không có phiếu nào đủ điều kiện → `KHONG_CO_PHIEU` |
| `DELETE /api/hoa-don-gop/{id}` | Huỷ tờ, các phiếu quay lại *chưa xuất hoá đơn*. Đã thu tiền → `DA_THU`; chứng từ đã đẩy kế toán → `DA_DAY_KE_TOAN` |
| `POST /api/hoa-don-gop/{id}/thu-tien` | Ghi một lần khách trả cho cả tờ (tiền nào cũng được, có tỷ giá ngày thu) → một tờ `PT`, **tự phân bổ xuống từng phiếu theo thứ tự ngày**. Thu dư phải xác nhận `cho_thu_du` |
| `DELETE /api/hoa-don-thu/{id}` | Xoá một lần thu — xoá luôn phần đã rải xuống các phiếu, trạng thái từng phiếu tính lại |

## C9. Lệnh sửa chữa riêng — `routes/sua_chua.py`

| Đường | Việc |
|---|---|
| `GET /api/lenh-sua-chua?vehicle_id=&thang=&status=` | Danh sách, lọc theo xe · tháng · bước |
| `GET /api/lenh-sua-chua/{id}` | Một tờ kèm từng dòng chi và số chứng từ |
| `POST /api/lenh-sua-chua` | **Tổ sửa chữa** lập: `vehicle_id`, `kind`, `order_date`, `odo_km`, `garage`, `note`, `lines[]`. Xe sang *đang sửa* |
| `PUT /api/lenh-sua-chua/{id}` | Sửa khi còn ở *đã nhập*. Gửi `lines[]` là ghi lại toàn bộ dòng; dòng **đã xuất kho** không sửa, không xoá (`DA_XUAT_KHO`) |
| `DELETE /api/lenh-sua-chua/{id}` | Xoá tờ chưa xuất kho phụ tùng |
| `POST /api/lenh-sua-chua/{id}/verify` · `/book` | **KT Chi phí VC** kiểm và ghi sổ |
| `POST /api/lenh-sua-chua/{id}/return` | KT Chi phí trả lại cho tổ sửa chữa (rút tờ chứng từ nếu đã ghi sổ) |
| `POST /api/lenh-sua-chua/{id}/pay` | **Quỹ tiền mặt** chi → một tờ `PC_SC` gồm riêng khoản mua ngoài; xe về *rảnh* |

## C10. Thẻ cao tốc — `routes/the_cao_toc.py`

| Đường | Việc |
|---|---|
| `GET /api/the-cao-toc` | Danh mục thẻ kèm số dư — mọi vai xem được (Bãi phải biết thẻ nào còn tiền) |
| `GET /api/the-cao-toc/{id}` | Một thẻ kèm 200 dòng gần nhất (nạp · qua trạm · điều chỉnh) |
| `POST PUT /api/the-cao-toc[/{id}]` | **KT Thu/Chi VC** lập và sửa. Thẻ `khach` bắt buộc ghi khách; trùng số thẻ → `TRUNG_SO_THE`. Số dư không sửa thẳng ở đây |
| `POST /api/the-cao-toc/{id}/nap` | **Quỹ** (hoặc kế toán) nạp tiền: `amount`, `move_date`, `ref` |
| `POST /api/the-cao-toc/{id}/dieu-chinh` | Chỉnh lệch với trạm — `amount` (± ) và **`note` bắt buộc** |
| `GET /api/the-cao-toc/cong-no?thang=` | Thẻ khách cấp: nạp · tiêu · số cấn trừ từng khách |

Trừ thẻ không có đường riêng: nó xảy ra khi **ghi sổ mục IV** của phiếu (`/sections/travel/book`).

## C6. Theo dõi, báo cáo, chứng từ

| Đường | Việc |
|---|---|
| `GET /api/theo-doi`, `/api/theo-doi/su-co` | Trung tâm điều hành: dải ô số, danh sách chuyến, sổ sự cố |
| `GET /api/bao-cao/tong-quan?thang=` | Bốn con số, tiến trình, cơ cấu chi, việc cần xử lý |
| `GET /api/bao-cao/xu-huong?thang=` | Sáu tháng, theo ngày, hao hụt, hiệu suất xe, vận hành, xem nhanh, dòng thời gian |
| `GET /api/bao-cao/theo-doi`, `/xe-lien-ket`, `/tien-tai-xe` | Ba bảng báo cáo trong Excel của họ. `/xe-lien-ket` là biên lợi nhuận nên chặn vai không thấy tiền bán |
| `GET /api/bao-cao/can-tru?thang=` | **Cấn trừ cuối tháng** (C5.1 · C6.1): từng khách — cước phải thu · trả hộ qua thẻ · nợ trạm dầu VN · còn phải thu |
| `GET /api/dem-viec` | Số việc đang chờ của từng màn, theo vai đang đăng nhập |
| `GET /api/chung-tu`, `/loai`, `/{id}`, `POST /{id}/da-day` | **Sổ chứng từ** cho bên kế toán kéo về hoặc đánh dấu tay |
| `POST /api/chung-tu/day`, `POST /api/chung-tu/{id}/day` | **Đẩy chứng từ sang kế toán anh Khang** (hết tờ chưa đẩy · một tờ). KT Thu/Chi VC và Sếp. Chưa cấu hình → `CHUA_CAU_HINH`; bên kia hỏng → `DAY_HONG`, tờ giữ nguyên kèm câu lỗi |
| `GET /api/ke-toan/trang-thai` | Đã nối chưa, bao nhiêu tờ đã/chưa/lỗi, lần đẩy gần nhất |
| `GET PUT /api/ke-toan/cau-hinh` | Sếp đặt địa chỉ API và token kế toán ngay trong màn hình, không cần khởi động lại; token không trả về trình duyệt |
| `GET /api/acc-codes` | Danh mục mã tài khoản (gọi API bên anh Khang, có danh mục dự phòng) |
| `GET POST DELETE /api/tat-toan` | Tất toán tài xế theo tháng |
| `GET POST /api/suppliers`, `/api/suppliers/{id}/payments` | Nhà cung cấp và các đợt trả |
| `GET POST DELETE /api/ban-hang`, `POST /api/ban-hang/{id}/thu` | Bán phụ tùng, xăng dầu ra ngoài |
| `POST /api/trips/{id}/vi-tri`, `GET /api/trips/{id}/vet` | GPS: app tài xế gửi vị trí, màn theo dõi lấy vệt |
| `GET /api/quy-trinh` | Sơ đồ quy trình và ma trận vai × mục (màn Quy trình đọc từ đây) |

## C7. Quy ước lỗi

Mọi lỗi trả JSON `{"detail": {"ma": "MA_LOI", "loi": "câu tiếng Việt cho người dùng"}}`.

| Mã | Nghĩa |
|---|---|
| `KHONG_CO_QUYEN` (403) | Vai này không được làm việc đó |
| `MUC_DA_KHOA` (409) | Mục đã kiểm, phải trả lại mới sửa |
| `SAI_BUOC` (409) | Chuyển bước không đúng thứ tự |
| `DA_KHOA` (409) | Phiếu đã khoá |
| `KHONG_DU_HANG` (409) | Lấy quá tồn của lô |
| `LO_DA_XUAT` (409) | Xoá DO gom mà hàng đã có người lấy |
| `HANG_DA_NHAP_KHO` (409) | Sửa dòng hàng hoặc cân của DO gom đã nhập kho |
| `KHONG_DOI_LOAI` (409) | Đổi loại gom/giao khi phiếu đã có dòng hàng hay sổ kho |
| `TON_AM` (409) | Điều chỉnh giảm quá tồn của lô |
| `THIEU_LY_DO` (422) | Điều chỉnh kho không ghi lý do |
| `THANG_SAI`, `TUAN_SAI`, `SO_SAI`… (422) | Dữ liệu gửi lên sai dạng |

---

# D. Chạy và kiểm

```
python backend\app\seed.py                       # dựng bảng + gieo dữ liệu mẫu (có sẵn một cặp DO gom/giao)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8010 --no-access-log
```

Chín bộ kiểm, chạy khi máy chủ đang bật:

| Lệnh | Kiểm gì |
|---|---|
| `python kiem\test_tinh_toan.py` | Phép tính phiếu và phân quyền (không cần máy chủ) |
| `python kiem\thu_hai_do.py` | **Luồng hai DO**: gom → nhập kho → giao lấy lô → xuất kho → hao hụt, và ba chỗ phải bị từ chối |
| `python kiem\thu_luong_api.py` | Trọn luồng: lập phiếu → kiểm → ghi sổ → chi → hoá đơn → thu tiền |
| `python kiem\thu_phieu_linh.py` | Phiếu lĩnh QR, thủ kho cấp dầu, khai đổ dọc đường, tất toán |
| `python kiem\thu_ban_hang.py` | Bán phụ tùng, xăng dầu ra ngoài |
| `python kiem\thu_vi_tri.py` | GPS: ai được gửi, lọc điểm dày, GPS cũ |
| `node kiem\ra_tai_xe.js` | **Rà màn Tài xế**: từng vai, cột Kết luận, ngăn trượt hồ sơ, năm tab, bốn ngôn ngữ (báo cáo, không phải đạt/hỏng) |
| `python kiem\thu_chu_xe.py` | **Chủ xe liên kết**: danh mục, phí riêng từng chủ tự điền vào phiếu, trả gộp hai phiếu một tờ PC_CX, chặn trả trùng, phân quyền xem/sửa/trả |
| `python kiem\thu_hoa_don_gop.py` | **Hoá đơn gộp tháng**: cờ khách, chặn hoá đơn lẻ, gộp một tờ nhiều phiếu, thu ở tờ **phân bổ đúng về từng phiếu theo ngày**, chặn thu/xoá lẻ, huỷ tờ lùi lại sạch |
| `python kiem\thu_vai_va_doi_xe.py` | **Hai vai mới ở Thà Bốc** (C1.2) và **đổi xe giữa đường** (C2.2): mục V và kho phụ tùng rút khỏi Bãi, tổ sửa chữa duyệt báo hỏng, đổi xe giữ nguyên chuyến và bắt kiểm lại mục I |
| `python kiem\thu_sua_chua.py` | **Lệnh sửa chữa riêng** (C7.3): chuỗi duyệt như mục V, lấy kho trừ tồn ngay kèm `PXK_PT`, chi chỉ phần mua ngoài, màn Xe gom cả hai nguồn |
| `python kiem\thu_the_cao_toc.py` | **Thẻ cao tốc** (C6.1): số dư, trừ ĐÚNG MỘT LẦN lúc ghi sổ mục IV, chặn xoá dòng đã trừ, điều chỉnh phải có lý do, cấn trừ cuối tháng |
| `python kiem\thu_no_tram_dau.py` | **Nợ trạm dầu Việt Nam** (C5.1): cờ ghi nợ tách khỏi dòng tài xế trả tiền mặt, công nợ trạm chỉ gồm phần ghi nợ, bảng cấn trừ cuối tháng |
| `python kiem\thu_ty_gia.py` | **Màn Tỷ giá**: ai xem ai sửa, lịch sử giữ số cũ, gõ lại số cũ không đẻ dòng rác, chặn số sai, phiếu cũ giữ tỷ giá của nó, phiếu mới lấy số mới |
| `python kiem\thu_tien_te.py` | **Nhiều tiền tệ và sổ thu tiền**: cước Nhân dân tệ, quy Kíp đúng tỷ giá khoá, thu nhiều lần bằng nhiều tiền, trạng thái tự suy, chặn thu dư, chặn xoá tờ đã đẩy |
| `python kiem\thu_day_ke_toan.py` | **Đẩy chứng từ sang kế toán** với máy nhận giả đóng vai API anh Khang: cấu hình, gói tin, bên kia hỏng, 409, đẩy hết, không gửi trùng |
| `node kiem\thu_giao_dien.js` | Toàn giao diện trên jsdom, nối máy chủ thật |
| `node kiem\thu_ngoai_tuyen.js` | Màn Cấp phát khi mất mạng |
| `node kiem\ra_vai.js` · `ra_tong_quan.js` · `ra_xe.js` | Báo cáo rà từng vai và từng màn (không phải đạt/hỏng) |

Từ điển ba thứ tiếng sinh tự động: sửa `tools/sinh_ngon_ngu.py` rồi chạy nó, **đừng sửa tay**
`frontend/js/ngon_ngu.js`.
