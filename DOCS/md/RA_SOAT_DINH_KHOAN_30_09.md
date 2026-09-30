# Rà soát định khoản Nợ / Có — 30/09/2026

Anh dặn: *"kiểm tra kỹ càng các định khoản nhé, nó là nợ và có, phải là số thật nhé theo file excel và theo cái API anh
Tune gửi á, tra cứu kỹ nhé, đúng luật pháp nhé"*. Anh gửi kèm ảnh tờ đề nghị tạm ứng, trên đó dòng tiền mặt tài xế ghi
**625/4021**.

## 1. Kết luận ngắn

- **Anh nói đúng: 625/4021 trên tờ tạm ứng là sai.** 4021 là *phải trả nhà cung cấp*, nhưng tài xế là nhân viên, và
  tiền ứng là tiền EPL còn đòi lại. Danh mục thật có tài khoản riêng cho việc này: **1601 — tạm ứng nhân viên**. Nay các
  dòng đó ghi **625/1601**.
- Rà hết thì thấy **ba mã không có trong danh mục thật của bên kế toán**: 1371, 4021, 4022. Đây là mã con anh Khampla
  đặt, anh đã chốt giữ ngày 23/09. Em giữ nguyên, ghi rõ trên màn là "chưa mở", và cần anh chọn (mục 6).
- **Mã "70" mà Excel và quy trình của khách dùng cho doanh thu là mã nhóm, không ghi sổ được.** Nay cước vận chuyển ghi
  **708**, bán dầu và phụ tùng ghi **707**.
- **Tên sai:** hệ thống gọi 625 là "chi phí vận chuyển". Theo danh mục thật, 625 là *đi lại, công tác phí, hội họp, tiếp
  khách*. "Chi phí vận chuyển" là **621**. Em đã sửa tên ở cả hai trang.
- Khi rà, em tìm thêm **5 lỗi về tiền** và đã sửa cả 5 (mục 5).
- **Số đã ghi trên sổ kế toán thật chưa đổi.** Em đã soạn công cụ lập hai bút toán điều chỉnh chờ duyệt. Công cụ mới
  chạy thử, chưa ghi; chờ anh cho phép (mục 7).

## 2. Nguồn đối chiếu

| Nguồn | Nội dung dùng để đối chiếu |
|---|---|
| Excel của khách — `DOCS/ຂົນສົ່ງ EPL.xlsx`, tờ ໃບບິນອອກລົດ, cột ເດີນບັນຊີ | 1211/70 cước · 625/371 dầu qua kho · 625/402 mọi khoản đi đường · 614/402 lốp · 614/371 phụ tùng kho |
| Quy trình kế toán của khách — `EPL flow of Logistics.docx` | 625/37 · 4022/37 dầu kho · 614/4021 · 4022/4021 sửa ngoài · 614/37 · 4022/37 phụ tùng kho · 1211/70 hoá đơn |
| Danh mục THẬT của bên kế toán — API `country-accounts` quốc gia 11 (Lào), cùng hệ QLSX với API tạo đơn bán anh Tune viết 11/09 | 494 mã, chụp ngày 30/09 vào `backend/app/services/danh_muc_tai_khoan_lao.json` (cả hai trang) |

Hai điểm đọc từ danh mục thật:

- "37" / "371" trong giấy tờ cũ của khách là **137** (hàng hoá tồn kho) của danh mục hiện hành.
- 137, 402 và 70 trong danh mục thật **không có tài khoản con 1371, 4021, 4022**. Nhóm 40 chỉ có 401 (nhà cung cấp hàng
  hoá, vật tư) và 402 (nhà cung cấp dịch vụ).

## 3. Định khoản từng dòng chi trên phiếu xuất xe

Vế Nợ theo loại xe và mục. Vế Có theo **cách trả**, vì mỗi cách trả là một đối tượng nợ khác nhau.

| Dòng chi | Xe nhà — trước | Xe nhà — nay | Xe liên kết — trước | Xe liên kết — nay | Vì sao |
|---|---|---|---|---|---|
| III dầu lấy kho EPL | 625/1371 | 625/1371 | 4022/1371 | **4022/707** | xe thuê: dầu là xuất BÁN theo giá bán riêng (chốt 29/09). Giá vốn 607/1371 do tờ xuất kho ghi |
| III dầu trạm ngoài, trạm ghi nợ | 625/4021 | 625/4021 | 4022/4021 | 4022/4021 | nợ trạm dầu |
| III dầu trạm ngoài, tài xế trả tiền mặt | 625/4021 | **625/1601** | 4022/4021 | **4022/1011** | tiền đó nằm trong tạm ứng, không phải nợ trạm |
| IV · VI tài xế cầm tiền mặt đi | 625/4021 | **625/1601** | 4022/4021 | **4022/1011** | xe nhà: tạm ứng nhân viên, quyết toán lúc tất toán · xe thuê: EPL chi hộ bằng tiền mặt, trừ tiền trả chủ xe |
| IV trả cùng lương (tiền nước, tiền chuyến) | 625/4021 | **625/4201** | — | (xe thuê không có) | phải trả nhân viên, không phải nhà cung cấp |
| IV · VI ghi nợ nhà cung cấp, trừ thẻ cao tốc | 625/4021 | 625/4021 | 4022/4021 | 4022/4021 | đúng Excel: ຕິດໜີ້ຜູ້ສະໜອງ |
| V phụ tùng lấy kho | 614/1371 | 614/1371 | 4022/1371 | 4022/1371 | đúng quy trình |
| V sửa ngoài, garage | 614/4021 | 614/4021 | 4022/4021 | 4022/4021 | đúng quy trình |
| Chủ xe tự chi | có mã | **không định khoản** | có mã | **không định khoản** | không phải tiền của EPL |

Dòng cũ đang mang mã theo luật cũ **tự hiện đúng theo luật mới**, không phải sửa dữ liệu. Mã người dùng tự chọn trong ô
Định khoản thì giữ nguyên.

## 4. Định khoản từng loại tờ

| Tờ | Trước | Nay | Vì sao |
|---|---|---|---|
| PC_TU chi tạm ứng — xe nhà | Nợ 625 / Có 1011 | **Nợ 1601 / Có 1011** | tiền chưa tiêu thì chưa phải chi phí |
| PC_TU chi tạm ứng — xe thuê | Nợ 4022 / Có 1011 | Nợ 4022 / Có 1011 | ghi công nợ chủ xe |
| QT_TU quyết toán tạm ứng (**tờ mới**, sinh lúc tất toán) | — | **Nợ 625 / Có 1601** | số tài xế đã chi thật mới sang chi phí |
| TT_CHI tất toán, công ty chi bù | Nợ 625 / Có 1011 | **Nợ 1601 / Có 1011** | đối ứng tạm ứng |
| TT_THU tất toán, tài xế nộp lại | Nợ 1011 / Có 625 | **Nợ 1011 / Có 1601** | đối ứng tạm ứng |
| HD hoá đơn vận chuyển | Nợ 1211 / Có 70 | **Nợ 1211 / Có 708** | 70 là mã nhóm |
| HD_BAN bán dầu, phụ tùng | Nợ 1211 (chủ xe: 4022) / Có 70 | **Có 707** | 70 là mã nhóm |
| PT phiếu thu — bản in | ghi "1211/70" | **Nợ tiền / Có 1211** | 1211/70 là định khoản của hoá đơn, không phải của phiếu thu |
| PXK · PNK kho, PC_NCC, PC_CX, PC_SC, PXK_BAN | — | không đổi mã, chỉ sửa tên theo danh mục thật | |

Sau khi tất toán một tài xế trong một kỳ, 1601 của tài xế đó về 0: đã ứng − đã chi thật ± chênh lệch = 0.

## 5. Lỗi khác tìm thấy khi rà — đã sửa

| # | Lỗi | Hậu quả | Đã sửa |
|---|---|---|---|
| 1 | Quỹ bấm "Chi tiền" mục IV thì PC_TU chỉ cộng mục IV, nhưng lại đánh dấu cả tờ tạm ứng (gồm III, IV, VI) là đã cấp | sổ ghi ít hơn số tiền tài xế cầm đi | PC_TU = đúng số trên tờ tạm ứng |
| 2 | Quỹ chi mục VI thì PC_SC cộng cả dòng tiền mặt đã nằm trong tạm ứng | cùng một khoản chi hai lần | PC_SC không còn dòng của tờ tạm ứng; mục VI không sinh PC_SC |
| 3 | PC_SC mục V trả tiền mặt cả khoản lốp, trong khi lốp là nợ nhà cung cấp trả theo đợt (Excel: ຕິດໜີ້ຜູ້ສະໜອງ ຈ່າຍເປັນງວດ) | trả hai lần: tiền mặt và theo đợt | PC_SC bỏ khoản mà Theo dõi NCC đã tính là nợ |
| 4 | Bản in phiếu thu ghi "1211/70" | sai định khoản, lại dùng mã nhóm | Nợ tiền theo cách thu / Có 1211 |
| 5 | Bảng cân đối bên kế toán hiện **hai dòng cùng mã 70** khi 70 vừa có bút toán riêng vừa có tài khoản con | dòng cha thiếu 299 triệu | gộp làm một dòng |

**Chưa sửa, đưa vào hợp đồng API với anh Tune.** Theo dõi NCC cộng phát sinh theo khoản mục, không xét cách trả. Vì vậy:

- mọi dòng dầu mang khoản mục "diesel" (kể cả dầu lấy kho) đang bị tính vào phát sinh của trạm dầu Việt Nam;
- dòng chipping mà người lập đổi sang tiền mặt vẫn bị tính là nợ nhà cung cấp.

Đề nghị: nợ nhà cung cấp = các dòng có vế **Có 4021**, đúng bảng ở mục 3.

## 6. Việc cần anh quyết

1. **1371 · 4021 · 4022 chưa có trong danh mục bên kế toán.** Chưa có thì sổ của anh Tune không ghi được các dòng này.
   - **Cách A (em đề nghị):** nhờ anh Tune mở ba mã con trong danh mục của EPL: 1371 dưới 137, 4021 và 4022 dưới 402.
     Cách này giữ đúng cách anh Khampla làm và đúng quyết định 23/09. Luật kế toán Lào cho doanh nghiệp mở tài khoản chi
     tiết dưới tài khoản cấp 3.
     Lưu ý: nhà cung cấp **hàng hoá** (trạm dầu, cửa hàng phụ tùng) đúng ra phải nằm dưới **401**, không phải 402. Nên
     hỏi anh Khampla có muốn thêm một mã con dưới 401 không.
   - **Cách B:** dùng thẳng mã đang có: 137 · 401 (nhà cung cấp hàng hoá) · 402 (dịch vụ và chủ xe, tách theo đối
     tượng). Đổi ở một chỗ duy nhất: `backend/app/services/tai_khoan.py`.
2. **Phải thu cước: 1211 hay 1213?** Excel ghi 1211 (*khách hàng — hàng hoá*). Vận chuyển là dịch vụ, và danh mục có
   1213 (*khách hàng — dịch vụ*). Em đang giữ 1211 theo Excel. Đổi thì chỉ một dòng.
3. **Dầu xe chạy ghi vào 625?** 625 là đi lại, công tác phí. Nếu xếp theo bản chất thì có thể là 602 (vật liệu phục vụ
   sản xuất). Đây là chính sách của anh Khampla, em giữ nguyên, chỉ nêu ra để anh hỏi.
4. **Phụ tùng kho lắp cho xe thuê:** theo quy trình thì ghi 4022/1371 theo giá vốn. Có phải xuất bán giống dầu
   (4022/707, giá bán riêng) không?

## 7. Việc chờ anh cho phép (DB thật)

Công cụ `EPL_KETOAN/tools/dieu_chinh_dinh_khoan_3009.py`. Không có `that` thì chỉ chạy thử. Công cụ **không sửa bút
toán đã ghi**. Nó chỉ thêm tài khoản, sửa tên, và lập hai bút toán ở trạng thái **chờ duyệt**. Sếp duyệt ở màn Ghi tay
thì mới vào sổ.

Kết quả chạy thử trên DB kế toán thật (chưa ghi gì):

| Việc | Chi tiết |
|---|---|
| Thêm tài khoản | 160 · 1601 · 420 · 4201 · 707 · 708 (tên theo danh mục thật) |
| Sửa tên | 1211 · 137 · 402 · 614 · 625 ("chi phí vận chuyển" → đi lại, công tác phí) · 607 · 70 (→ mã nhóm) |
| Bút toán điều chỉnh doanh thu | Nợ 70 **299.203.600** / Có 708 296.423.600 · Có 707 2.780.000 |
| Bút toán điều chỉnh tạm ứng | Nợ 1601 / Có 625 **161.487.500**: 13 tờ PC_TU xe nhà cũ, chưa kỳ nào tất toán |

Trên bản sao DB thử em đã chạy thật và duyệt thử:

- 70 về 0, doanh thu nằm ở 708 và 707;
- 625 giảm đúng 183.642.500 (số của DB thử), 1601 tăng đúng chừng đó;
- bảng cân đối vẫn cân.

Máy chủ 8020 / 8030 cần khởi động lại để nạp mã mới.

## 8. Xem ở đâu trên màn

- **Quy trình → tab "Danh mục chứng từ"** → bảng *"Định khoản từng dòng chi trên phiếu xuất xe"*. Mã con của khách mang
  nhãn vàng "chưa mở". Dòng cuối ghi nguồn: 494 mã, chụp 30/09.
- **Phiếu xuất xe → mục III / IV / V / VI → cột "Mã kế toán".** Rê chuột lên mã thì hiện tên hai vế. Đổi *cách trả*,
  *ghi nợ tại trạm* hay *thẻ cao tốc* thì mã đổi theo ngay.
- **Phiếu đề nghị chi →** chọn một tờ tạm ứng → cột *Định khoản (Nợ / Có)*: 625 / 1601.

## 9. Đã kiểm

Mọi bài đều chạy trên máy thử 8011 / 8031 (bản sao DB), từng bài một, ở tiền cảnh:

- **Bài mới `thu_dinh_khoan`:**
  - mọi mã in ra đều có trong danh mục thật, trừ ba mã con của khách;
  - bảng dòng chi đúng 18 trường hợp;
  - dòng mang mã luật cũ tự sửa, mã tự chọn thì giữ;
  - tờ tạm ứng ra 625/1601;
  - PC_TU ghi 1601/1011 đúng số tờ;
  - PC_SC không trả tiền mặt cho lốp;
  - xe thuê ra 4022/1011 · 4022/4021 · 4022/707.
- **Bài cũ, đã sửa theo luật mới và đạt:** lo_hong_23_09, cach_tra, ban_hang, chu_xe, sua_chua, luong_api, phieu_linh,
  de_nghi, quyen_de_nghi_kho, kho_xem, giao_dien (20 màn, 4 ngôn ngữ) · bên kế toán: tat_toan (có tờ QT_TU), dot2 (sổ
  đối chiếu sau điều chỉnh), nhan_chung_tu, doanh_thu_giao_dien.
