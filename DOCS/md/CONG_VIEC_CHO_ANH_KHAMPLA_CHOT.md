# Việc đang chờ chốt — EPL Lào

Cập nhật **22/09/2026**. Ngày 21/09 sếp chốt câu quan trọng nhất (một chuyến đi qua **hai DO**); ngày
22/09 **anh Khampla trả lời bộ câu hỏi** (`DOCS/word/traloituanhkhamplar.docx`, 32/36 câu). Kế hoạch sửa
theo phản hồi đó, chia ba đợt, nằm ở `KE_HOACH_SAU_PHAN_HOI_KHAMPLA.md`. Tệp này ghi lại **đã chốt gì,
làm gì rồi, và còn chờ ai cái gì**.

Bộ câu hỏi gửi bên EPL: `CAU_HOI_NGHIEP_VU_EPL.md` (bản Lào `ຄຳຖາມວິຊາການ_EPL.md`, bản Anh
`EPL_BUSINESS_QUESTIONS.md`). Mô tả hệ thống đầy đủ: `NGHIEP_VU_DB_API.md`.

---

## Phần 1. Đã chốt và đã làm xong (21/09)

### 1.1 Một chuyến đi qua HAI DO — sếp chốt

> *"Mình phải làm 2 phiếu. Một phiếu là DO đi gom hàng… một phiếu đi giao hàng là như hiện tại. Hai cái
> phiếu này tuy 2 mà 1 — cái Thabok là như gọi là cái bưu cục. DO lấy hàng mang về sẽ lên chứng từ nhập
> kho, và khi DO giao lấy thì phải có chứng từ xuất kho. Xe đi lấy hàng và xe đi giao hàng có thể khác
> nhau. Trong DO phải biết có mặt hàng gì, bao nhiêu kg, để insert thêm một dòng hao hụt cho rõ ràng."*

Đã làm đúng như vậy:

| Việc | Cách làm |
|---|---|
| Hai loại phiếu | `trips.kind` = `gom` (mỏ → bãi) hoặc `giao` (bãi → khách). Chọn ngay ở mục I khi lập phiếu |
| Dòng hàng | Bảng `trip_goods`: mặt hàng, số tấn. DO gom ghi hàng bốc ở mỏ; DO giao ghi hàng lấy khỏi kho |
| Bưu cục Thà Bốc | Bảng `goods_moves` = sổ kho hàng. DO gom về bãi → **nhập kho** (chứng từ `PNK_HH`); DO giao lấy đi → **xuất kho** (chứng từ `PXK_HH`) |
| Dây nối hai DO | Mỗi dòng hàng của DO giao ghi `tu_phieu_id` = DO gom mang lô đó về. Nhìn phiếu nào cũng tra ngược được |
| Xe khác nhau | Không ràng buộc gì giữa xe hai chặng |
| Dòng hao hụt | Máy tự ghi một dòng `loai = 'hao_hut'`: chặng gom là *cân mỏ − cân bãi*, chặng giao là *tấn xuất kho − cân nơi giao* |
| Chạy thẳng mỏ → cảng | Vẫn được: lập DO giao và không chọn lô nào, nhập cân tay như trước |
| Màn Kho hàng | Mới: tồn theo từng lô, sổ nhập xuất, bấm một dòng là mở đúng phiếu |
| Sai số sau khi nhập kho | **Phiếu điều chỉnh kho** (chốt 21/09, thay cho việc xoá phiếu giao rồi làm lại): kế toán ghi một dòng +/− tấn có lý do vào lô, sinh chứng từ `DC_HH`, tồn không được âm, lịch sử nhập/xuất giữ nguyên. Phiếu gom đã nhập kho thì dòng hàng và cân đóng lại |

Máy chủ chặn ba chỗ: lấy quá tồn của lô, xuất hoá đơn cho DO gom, xoá DO gom mà hàng đã có người lấy.
Bộ kiểm `kiem/thu_hai_do.py` đi trọn luồng này.

### 1.2 Những câu sếp giao bên mình tự quyết

| Mã | Quyết định | Lý do |
|---|---|---|
| **B3, C8.2** | Mỗi DO một hoá đơn | **Anh Khampla 22/09:** khách **có hợp đồng** nhận một hoá đơn gộp tháng, khách vãng lai mỗi phiếu một hoá đơn → làm ở đợt 2 (mục 2.2 kế hoạch) |
| **B4** | ~~DO gom không có cước~~ → **DO gom CÓ cước riêng** | **Anh Khampla 22/09** tích "có cước riêng, khách trả cho chặng gom". Đã sửa đợt 1: phiếu gom có đơn giá, thành tiền, hoá đơn như phiếu giao |
| **A2** | Bãi thấy mọi khoản **chi**; không thấy **tiền bán** (cước, doanh thu, hoá đơn, giá thuê xe ngoài, lãi, mã TK) | Bãi là người chi nên phải thấy chi; chênh lệch giá bán và giá thuê là biên lợi nhuận |
| **C3.1** | Cân đầu = **cân của mỏ**, nhập trên DO gom | Đó là số trên phiếu quặng khách giao |
| **C3.2** | Cân cuối = **cân ở nơi giao**, nhập trên DO giao | Hoá đơn tính trên số này |
| **C3.3** | Tài xế chụp ảnh phiếu cân, **đính kèm vào phiếu**; máy nhắc khi khoá nếu còn thiếu | Giấy dễ mất, ảnh vào phiếu thì kế toán ở Viêng Chăn xem được ngay |
| **C3.4** | Hao hụt **chỉ theo dõi**, không tự trừ tiền khách; quá 1,5 % thì cờ đỏ và cảnh báo khi khoá | Hợp đồng chưa nói trừ; nhưng hao hụt đã có **dòng riêng** nên bật trừ tiền sau rất nhanh |
| **C3.5, C3.6** | Giá lấy từ **bảng giá khách × tuyến** (có ngày hiệu lực), tính trên **tấn ở điểm đến** | **Anh Khampla 22/09** xác nhận, thêm giá **khoán trọn chuyến** → đã làm 22/09 (`price_mode`: theo tấn · trọn chuyến, trên phiếu và bảng giá). Giá đổi theo mùa dùng `valid_from` có sẵn |
| **C3.7** | ~~Bãi nhập~~ → **Kế toán nhập khi nhận giấy**, Bãi chỉ đính kèm ảnh | **Anh Khampla 22/09.** Đã sửa đợt 1: hai ô này Bãi chỉ đọc, kế toán Thu/Chi VC gõ |
| **C4.1** | Giá thuê xe ngoài do **kế toán Viêng Chăn** nhập | Người ký với chủ xe; và Bãi không được thấy giá thuê |
| **C4.2** | ~~mặc định chung~~ → **theo từng chủ xe** | **Anh Khampla 22/09.** Đã làm 22/09: danh mục *Chủ xe liên kết* giữ phí %, ngưỡng tấn, mức trừ, tiền thuê; phiếu tự điền theo chủ xe, kế toán vẫn sửa được |
| **C4.3** | ~~chỉ từng phiếu~~ → **từng phiếu · gộp tháng · theo đợt** | **Anh Khampla 22/09.** Đã làm 22/09: mỗi chủ xe ghi cách trả; quỹ tích nhiều phiếu đã khoá rồi *Trả gộp*, một đợt một tờ `PC_CX`. Số tiền đợt = tổng các phiếu, không gõ tay — trả lẻ một phần cho một phiếu thì chưa có, chờ họ có nhu cầu thật |
| **C4.4** | Các khoản EPL ứng **trừ hết** vào tiền trả chủ xe | Đúng bảng tính trong Excel của họ |
| **C5.1** | Tài xế nhập **lít**, kế toán nhập giá | **Anh Khampla 22/09** xác nhận, ghi chú thêm: đổ ở Việt Nam là **ghi nợ tại trạm**, cuối tháng cấn trừ với cước khách → đợt 3, mục 3.3 |
| **C5.2** | ~~Hai kho~~ → **Bảy kho dầu** | **Anh Khampla 22/09** kể thêm năm: Km 28 Viêng Chăn · sân Thà Bốc Huay Lek · bản Thavai · sân Thakhek · Km 28 Thakhek (đường 8). Đã thêm đợt 1 |
| **C5.3** | Giá dầu xuất kho **bình quân** | **Anh Khampla 22/09** xác nhận |
| **C6.1** | Thẻ cao tốc ghi **như khoản chi thường**, chưa theo dõi số dư | **Anh Khampla 22/09: muốn theo dõi số dư thẻ**; khách cấp thẻ thì cấn trừ cước tháng, không thì quỹ Thà Bốc đưa tiền mặt → đợt 3, mục 3.2 |
| **C6.2** | Tiền chuyến, tiền nước tính **theo chuyến** | Theo ghi chú trong Excel |
| **C1.2, C7.1, C7.2** | Kho phụ tùng và tổ sửa chữa coi là **người của Bãi** | **Anh Khampla 22/09: là NGƯỜI RIÊNG, cần tài khoản riêng**; xe hỏng báo cả Bãi và tổ sửa; tổ sửa quyết kho hay gara → đợt 3, mục 3.1 |
| **C7.3** | Sửa xe tại bãi vẫn **gắn phiếu gần nhất** | **Anh Khampla 22/09:** cả hai — phiếu gần nhất, **và** lệnh sửa riêng khi xe nằm lâu / bảo dưỡng định kỳ → đợt 3, mục 3.5 |
| **C1.3** | Tài xế **có** dùng điện thoại: nhận phiếu, khai đổ dầu, báo hỏng, chia sẻ GPS | Đã làm xong màn tài xế |
| **C2.1** | ~~Bãi ghi~~ → **Tài xế tự báo ngày về, km về qua điện thoại** | **Anh Khampla 22/09.** Đã làm đợt 1: nút *Báo đã về* trên màn tài xế; Bãi bấm *Xe đã tới* thì hai ô đã điền sẵn |
| **C2.2** | Sau kiểm mục I Bãi không sửa gì | **Anh Khampla 22/09:** có — **đổi xe giữa đường** khi xe hỏng nặng → đợt 3, mục 3.4 |
| **C8.3** | Khách trả chuyển khoản hoặc tiền mặt, **có trả một phần** | Làm xong 21/09: **sổ thu tiền từng lần** — mỗi lần tiền về ghi ngày, số tiền, tiền tệ, tỷ giá, cách thu; trạng thái *chưa thu · một phần · đủ* tự suy từ tổng |
| **Tiền tệ cước** | EPL nhận cước bằng **USD · Kíp · Nhân dân tệ · Bath**, và khách trả bằng tiền khác tiền ghi trên hoá đơn vẫn được | Anh chủ dự án chốt 21/09. Đã làm: phiếu có ô *Tiền tệ cước*, bảng giá mang tiền tệ riêng, xe liên kết thuê được bằng tiền khác tiền bán, báo cáo cộng về Kíp kèm chia theo từng loại tiền |
| **C9.1** | Màn phiếu chia **tab theo mục**, mỗi vai mở đúng tab của mình | Đã làm xong |
| **C9.2** | Ngôn ngữ mặc định ở máy bãi: **tiếng Lào** | **Anh Khampla 22/09** xác nhận. Đã làm đợt 1: máy chưa chọn ngôn ngữ mà người vào là Bãi, thủ kho, tài xế → tự đặt tiếng Lào |

---

## Phần 1b. Mã tài khoản — anh Khampla đã cho (22/09), đã sửa đợt 1

| Mã | Anh Khampla trả lời | Bên mình ghi sổ theo |
|---|---|---|
| **C5.4** Kho | **137** tài khoản mẹ, **1371** tài khoản con (sá-la-ban kế toán doanh nghiệp Lào) | `1371` — mã con là cấp hạch toán |
| **C5.5** Nhà cung cấp | **402** mẹ, **4021** con, tách theo từng nhà cung cấp | `4021` |
| **C5.6** Tiền | Tiền mặt Kíp **1011** · tiền mặt ngoại tệ **1012** · ngân hàng Kíp **1021** · ngân hàng ngoại tệ **1022** | Chọn tự động theo *cách thu/chi* × *tiền tệ*; quỹ tiền mặt mặc định tiền mặt |

Tất cả nằm ở một chỗ: `services/chung_tu.py` (`KHO`, `NCC`, `MA_TIEN`). Anh Khang muốn dùng mã mẹ thay
mã con thì đổi ở đó.

## Phần 2. Vẫn phải chờ bên EPL trả lời

| Mã | Câu hỏi | Vì sao không tự quyết được |
|---|---|---|
| **C5.7** | Hoá đơn ghi USD mà khách chuyển Kíp: **chênh lệch tỷ giá hạch toán thế nào** | Bên mình chỉ hiện ra hai con số (hoá đơn và số tiền thật về), không tự hạch toán chênh lệch — đó là sổ kế toán, việc của anh Khang. Cần anh Khang cho mã tài khoản chênh lệch tỷ giá nếu muốn tờ phiếu thu mang sẵn |
| **C5.8** | Tỷ giá dùng lúc thu: **tỷ giá ngày thu** hay tỷ giá đã khoá trên phiếu | Hiện để mặc định là tỷ giá khoá trên phiếu, người ghi sửa được ngay trên hộp nhập. Cần bên EPL nói cách họ đang làm trên giấy |
| **C1.1** | Tên người giữ tài khoản *KT Thu/Chi VC* và *KT Chi phí VC* | Bỏ trống trong tệp trả lời 22/09 |
| **C8.1** | Những khoản hay rơi vào mục VI | Bỏ trống |
| **C3.4** | Hao hụt khách có phạt / trừ tiền không | **Đã trả lời 22/09 (nói miệng qua anh chủ dự án): chỉ theo dõi, không trừ.** Đúng như đang chạy — không phải sửa |
| **C9.1** | Màn phiếu chia tab theo mục có hợp lý không | Bỏ trống; giữ tab, họ dùng thử rồi góp ý |

---

## Phần 3. Nợ kỹ thuật bên mình tự biết — **đã dọn hết 22/09**

### 3.1 Máy chủ vẫn trả giá bán cho mọi vai ở các API khác — ☑ **XONG 22/09**

Trước đây `/api/trips` và `/api/bao-cao/theo-doi` vẫn trả đơn giá, thành tiền, lãi cho mọi vai; giao
diện có che nhưng mở công cụ trình duyệt là đọc được hết.

Đã sửa ở **một chỗ duy nhất**: `xuat_phieu()` nhận thêm vai người gọi, và vai không được thấy tiền bán
thì các khoá đó bị **bỏ hẳn** khỏi gói trả về (`price`, `price_ccy`, `hire_price`, `fee_pct`,
`over_limit_t`, `over_price`, và trong khối `tinh` là doanh thu, tiền thuê, phần trừ, lãi, đã thu, còn
lại). Phần **chi phí giữ nguyên** — chính họ nhập và chi, giấu đi là họ không kiểm được việc của mình.
Mọi đường gọi hàm đó đều truyền vai, kể cả báo cáo Theo dõi. Bộ kiểm `kiem/thu_no_ky_thuat.py` chặn ở
mức API: ba vai không được xem thì không có khoá nào, còn kế toán thì phải thấy đủ — nếu kế toán cũng
mất thì phép lọc đã cắt nhầm.

### 3.2 Ảnh xe chưa lưu được — ☑ **XONG 22/09**

Đã dùng lại **đúng chỗ chứa tệp của phiếu** (`EPL_LAO_TEP`), chỉ khác thư mục con `xe/<id>` — một chỗ
chứa thì một chỗ sao lưu. Bảng `vehicle_photos`; ảnh đầu tiên của xe tự thành ảnh đại diện; xoá ảnh đại
diện thì ảnh còn lại mới nhất lên thay. Danh sách xe mang sẵn ảnh đại diện (lấy một lượt cho cả danh
sách, 500 xe không thành 500 lượt hỏi). Ảnh chỉ mở được khi có phiên, y như tệp phiếu.

Ảnh **tài xế** thì vẫn chưa lưu — màn Tài xế nói rõ điều đó, không để nút bấm chết.

### 3.3 Lệnh sửa chữa không gắn chuyến — ☑ **XONG 22/09** (đợt 3.5)

Anh Khampla xác nhận có bảo dưỡng định kỳ (C7.3), nên đã làm: bảng `repair_orders` + `repair_lines`,
màn **Lệnh sửa chữa**, đi qua đúng chuỗi duyệt của mục V. Xem mục A9 trong `NGHIEP_VU_DB_API`.

### 3.4 Ô "Việc của tôi" của KT Doanh thu luôn là 0 — ☑ **XONG 22/09**

Ô này đếm mục I–VI đang chờ chính vai đó làm, mà KT Doanh thu không phụ trách mục nào — việc của họ
nằm ở **mức phiếu**. Nay với vai đó ô này đếm *phiếu đã khoá chưa xuất hoá đơn* cộng *hoá đơn chưa thu
đủ tiền*, và bấm vào mở thẳng phiếu đầu tiên đang chờ.

---

## Phần 3b. Bốn việc anh chủ dự án chốt chiều 22/09 — đã làm

| Việc | Anh chốt | Đã làm |
|---|---|---|
| Ảnh tài xế | Làm | Cùng bộ máy với ảnh xe (`routes/anh.py`), thư mục `tai-xe/<id>`; nút *+ Thêm ảnh* trong hộ sơ tài xế; ảnh đầu tự thành ảnh đại diện |
| Cấn trừ có ghi thành phiếu thu không | Em tự quyết nếu hợp lý | **Có nút "Ghi cấn trừ tháng"** (KT Doanh thu) ở bảng Cấn trừ: khoản khách trả hộ → phiếu thu cách thu *cấn trừ* trên hoá đơn còn nợ của khách (hoá đơn gộp cũ trước, phiếu lẻ cũ trước). Gọi đúng hàm ghi thu đang dùng, chỉ khác `method = offset`, nên sổ thu một kiểu dòng. "Đã ghi" đọc từ chính sổ thu (ref `CT-YYYYMM`), gọi lại không ghi trùng; khách trả hộ nhiều hơn cước còn phải thu thì phần dư để tháng sau, **không ghi thu dư** |
| Đổi xe nhà ↔ xe liên kết giữa đường | Theo em: chặn | Chặn `KHAC_LOAI_XE` — chứng từ đã sinh trước lúc đổi mang mã của loại xe cũ (625/614 với 4022), không ghi lại được; chuyện đổi chéo hiếm, lập phiếu mới |
| Tên demo cho hai tài khoản mới | Em đặt | `khopt` — ທ້າວ ແກ້ວ (Keo), thủ kho phụ tùng · `totsua` — ທ້າວ ສຸກ (Souk), tổ sửa chữa. Hai kế toán (C1.1) vẫn tên mẫu ນາງ ພອນ (Phone) · ນາງ ວິໄລວັນ (Vilayvanh) cho tới khi anh Khampla cho tên thật |

---

## Phần 4. Chờ bên khác

| Việc | Chờ ai | Hiện đang làm gì |
|---|---|---|
| Khoá Google Routes / Geocoding | Anh cấp khoá | Tuyến và km nhập tay; bản đồ vẽ từ toạ độ trong CSDL |
| **Đường nhận chứng từ** | Anh Khang | **Bên mình đã làm xong lớp đẩy** (21/09): nút Đẩy, thử lại khi lỗi, chống gửi trùng, Sếp đặt địa chỉ và token trong màn hình. Hợp đồng JSON đề nghị ở `HOP_DONG_API_ANH_KHANG.md`. Chỉ chờ anh Khang cho địa chỉ + token, và chốt tên đường nếu muốn khác `/api/v1/epl-lao/vouchers` |
| Mã tài khoản còn thiếu: **hàng khách gửi**, **giá vốn** | Anh Khang — **chỉ còn chờ con mã** | Đã chốt logic 22/09 (mục 4 `HOP_DONG_API_ANH_KHANG`): hàng khách gửi là **ngoài bảng**, bỏ hẳn kho 1371 khỏi ba tờ PNK_HH/PXK_HH/DC_HH; giá vốn Nợ *mã anh cấp* / Có 1371. Hai mã là **ô cấu hình** ở màn Chứng từ → Cấu hình (Sếp gõ), tờ sinh sau đó mang mã ngay |
| API công nợ phải thu / phải trả | Anh Khang | Chưa làm; chỉ đọc và hiện nếu anh có đường sẵn |
| Danh mục Acc code | Anh Khang | Ô chọn định khoản đang dùng danh mục dự phòng, mã lạ thì ghi rõ "không có trong danh mục" |
