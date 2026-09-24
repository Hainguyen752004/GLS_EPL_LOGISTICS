# Kịch bản test tay EPL Lào — nhập vai từng người, thử hết chức năng

Viết cho anh (chủ dự án) tự test trước khi bàn giao, hoặc đưa bạn anh cùng test. Cập nhật 24/09/2026, sau các đợt: trả lời
của anh Khampla (Bãi không thấy tiền, giá vốn bình quân, chuyển kho, chủ xe mua ở quầy), sửa UI phần 1–18, rà toàn dự án,
xuất Excel/PDF, và chốt "Bãi không thấy tiền" ở Tiền chuyến & nước, Theo dõi NCC.

Tài liệu này **thay** `HUONG_DAN_THU_TUNG_VAI.md` (22/09). Bản cũ còn ghi Bãi thấy tiền chi, và bảo gieo lại bằng lệnh
`seed.py --dung-lai`, lệnh đó **không được chạy** trên DB `epl_lao` nữa.

**Cách đọc:** mỗi dòng là một việc cần thử. Cột **Phải thấy** là kết quả đúng. Thấy khác thì ghi lỗi theo mẫu ở **Phần
H**, không cần dừng lại, cứ đi tiếp. Mỗi dòng có ô ☐ để tick.

**Thời gian ước chừng:**
- Phần A (chuẩn bị): 10 phút.
- Phần C (từng vai): 3–4 giờ.
- Phần D (luồng xuyên vai): 2–3 giờ.
- Phần E, F, G: 1–2 giờ.

Không cần làm một mạch. Mỗi vai, mỗi luồng là một khối riêng.

---

## Mục lục

- **A.** Chuẩn bị trước khi test
- **B.** Bản đồ tài khoản và dữ liệu mẫu có sẵn
- **C.** Test từng vai (13 tài khoản)
  - C1 Admin Thà Bốc
  - C2 KT Thu/Chi Viêng Chăn
  - C3 KT Chi phí
  - C4 KT kho xăng dầu
  - C5 Thủ quỹ VC
  - C6 Quỹ tiền mặt cảng cạn
  - C7 KT Doanh thu
  - C8 Thủ kho nhiên liệu
  - C9 Thủ kho phụ tùng
  - C10 Tổ sửa chữa
  - C11 Tài xế
  - C12 Sếp
- **D.** Luồng xuyên vai (13 kịch bản ngoài đời, D13 là hợp đồng và POD)
- **E.** Những chỗ PHẢI bị chặn (phân quyền)
- **F.** Kiểm chung giao diện: ngôn ngữ, zoom, in, Excel/PDF, điện thoại, mất mạng
- **G.** Sổ kế toán EPL_KETOAN (cổng 8030)
- **H.** Mẫu ghi lỗi và việc sau khi test

---

## A. Chuẩn bị trước khi test

| ☐ | Việc | Ghi chú |
|---|---|---|
| ☐ | **Khởi động lại máy chủ 8020** | Chưa khởi động lại thì anh đang test mã cũ, các sửa hôm 23/09 chưa có |
| ☐ | Mở `http://<máy chủ>:8020` trên Chrome (hoặc Edge) | Mật khẩu mọi tài khoản demo là `1234` |
| ☐ | Mở thêm `http://<máy chủ>:8030` ở một tab khác | Sổ kế toán, dùng cho Phần G |
| ☐ | **Sao lưu DB trước khi test** (nhờ em chạy, hoặc anh dùng pg_dump) | Test tay sẽ ghi thật vào DB `epl_lao`, dùng chung với máy chủ của anh |
| ☐ | Mở sẵn một tệp ghi lỗi (Word, Excel hoặc giấy) theo mẫu ở Phần H | Mỗi lỗi một dòng, kèm ảnh chụp màn hình |

**Đổi vai nhanh:**
1. Bấm tên người dùng ở góc dưới thanh bên, hoặc góc trên phải nếu đang ở kiểu thanh trên.
2. Chọn **Đổi tài khoản**.
3. Màn đăng nhập hiện các thẻ tài khoản demo. **Bấm một thẻ là vào thẳng**, khỏi gõ mật khẩu.

**Mẹo:** mở hai cửa sổ Chrome, một cửa sổ thường và một cửa sổ ẩn danh (Ctrl+Shift+N). Mỗi cửa sổ đăng nhập một vai,
ví dụ Bãi bên trái, kế toán bên phải, để thấy việc bên này mở khoá cho bên kia mà khỏi đổi vai liên tục.

---

## B. Bản đồ tài khoản và dữ liệu mẫu

### B1. 15 tài khoản và màn của từng vai

| Tài khoản | Người | Vai | Màn thấy trên thanh bên |
|---|---|---|---|
| `thabok` | ສົມໄຊ | **Admin Thà Bốc** (Bãi): lập phiếu, điều xe, nhập số lượng. **Không thấy tiền** | Tổng quan · Theo dõi phiếu · Theo dõi tuyến · Phiếu xuất xe · Phiếu chi·Phiếu thu · Cấp phát · Theo dõi NCC · Kho hàng · Kho nhiên liệu · Điểm đổ · Kho phụ tùng · Khách hàng · Xe · Tài xế · Thẻ cao tốc · Tuyến đường · Quy trình |
| `ketoan` | ນາງ ພອນ | **KT Thu/Chi Viêng Chăn**: kiểm mục I–II, bảng giá, số phiếu quặng | Gần hết (không có Tất toán, Tài khoản) |
| `ketoancp` | ນາງ ວິໄລວັນ | **KT Chi phí VC**: nhập giá và kiểm, ghi sổ mục IV–VI, tất toán tài xế, lệnh sửa chữa | Gần hết + **Tất toán tài xế** |
| `khonl` | ທ້າວ ວິໄລ | **KT kho xăng dầu VC**: nhập giá, kiểm, ghi sổ mục III; nhập kho, chuyển kho dầu | Gần hết (không có Hoá đơn gộp, Tỷ giá) |
| `quyvc` | ນາງ ມະນີ | **Thủ quỹ VC**: chi mục III (dầu) | Gần hết + Tất toán |
| `quytb` | ນາງ ດາວ | **Quỹ tiền mặt cảng cạn**: chi mục IV–VI, cấp tiền tạm ứng, trả chủ xe | Gần hết + Tất toán |
| `doanhthu` | ທ້າວ ຄຳ | **KT Doanh thu VC**: hoá đơn, thu tiền, cấn trừ, công nợ khách | Gần hết (không có Cấp phát, Điểm đổ, Tất toán) |
| `khotb` | ທ້າວ ບຸນມາ | **Thủ kho nhiên liệu Thà Bốc** | Cấp phát · Kho nhiên liệu |
| `khovc` | ນາງ ສີດາ | **Thủ kho nhiên liệu Viêng Chăn** | Cấp phát · Kho nhiên liệu |
| `khopt` | ທ້າວ ແກ້ວ | **Thủ kho phụ tùng Thà Bốc** | Kho phụ tùng · Xe |
| `totsua` | ທ້າວ ສຸກ | **Tổ sửa chữa Thà Bốc**: mục V, lệnh sửa chữa, duyệt báo hỏng | Theo dõi tuyến · Phiếu xuất xe · Kho phụ tùng · Lệnh sửa chữa · Xe |
| `tx01` | ທ້າວ ທັດສະດາພອນ | **Tài xế** | Phiếu của tôi |
| `tx02` | ທ້າວ ບຸນມີ | **Tài xế** | Phiếu của tôi |
| `tx03` | ທ້າວ ສົມພອນ | **Tài xế** | Phiếu của tôi |
| `admin` | Admin | **Sếp**: xem tất cả, mở khoá, cấu hình | Tất cả 27 màn |

> Bảng đầy đủ "ai nhập, ai kiểm, ai ghi sổ, ai chi từng mục" nằm trong màn **Quy trình & trách nhiệm**, tab **Vai × mục**.
> Khi phân vân một việc có phải của vai đó không, mở tab này ra so.

### B2. Dữ liệu mẫu có sẵn (15 phiếu)

| Phiếu | Xe · tài xế | Khách | Trạng thái | Dùng để test gì |
|---|---|---|---|---|
| `T4-0428-08/EPL` | 341 · tx01 | ຄຳຕຸ້ຍ | Đang đi, chưa thu | Có dòng dầu **ghi nợ trạm Việt Nam** |
| `T4-0429-08/EPL` | 342 · tx02 | ຄຳຕຸ້ຍ | Đã tới, **chưa khoá** | Cước bằng **CNY**, thử khoá phiếu |
| `T4-0430-08/EPL` | ຮ່ວມ-07 (xe liên kết) | ຄຳຕຸ້ຍ | Khoá, đã thu | Bán USD, thuê xe LAK |
| `T4-0431-08/EPL` | 341 · tx01 | ນາງ ວັນນາ | Khoá, đã thu | Hoá đơn USD, khách trả bằng Kíp |
| `T4-0432-08/EPL` | 342 · tx02 | ຄຳຕຸ້ຍ | Đã xuất phát | Có **phiếu tạm ứng chờ cấp** |
| `T4-0440-09/EPL`, `T4-0441-09/EPL` | 341 / 342 | ລາວ-ຈີນ ມີເນີໂຣ (khách hợp đồng) | Khoá, trong **HĐ gộp `HDT-202609-01`** (thu một phần) | Hoá đơn gộp tháng |
| `G4-0101-09/EPL` | 341 | ຄຳຕຸ້ຍ | Phiếu **gom** đã về bãi | Lô hàng trong kho bãi |
| `T4-0433-09/EPL` | 342 | ຄຳຕຸ້ຍ | Đang đi | Phiếu **giao** lấy 30 t từ lô G4-0101 |
| **A** `T4-0442-09/EPL` | 342 · tx03 | ນາງ ວັນນາ | Trọn luồng tới **đã thu đủ** | Xem một phiếu hoàn chỉnh |
| **B** `T4-0443-09/EPL` | ຮ່ວມ-07 | ຄຳຕຸ້ຍ | Đã thu, **đã trả chủ xe có trừ tiền chủ xe mua dầu ở quầy** | Xe liên kết |
| **C** `T4-0444-09/EPL` | 341 · tx03 | ລາວ-ຈີນ ມີເນີໂຣ | Đang đi | Lấy 600 L ở **kho xe** (dầu mua ở Việt Nam) |
| **D** `G4-0102-09/EPL` | 342 | ຄຳຕຸ້ຍ | Gom đã về (39,5 → 39,3 t) | Tách chặng gom → giao |
| **E** `T4-0445-09/EPL` | 341 · tx02 | ຄຳຕຸ້ຍ | **Bãi đã gửi kiểm 4 mục, chờ kế toán nhập giá**; có phiếu tạm ứng chờ cấp | **Phiếu tốt nhất để test các vai kế toán** |
| **F** `T4-0446-09/EPL` | 341 | ຄຳຕຸ້ຍ | Khoá, có hoá đơn, **chưa thu** | Phí cao tốc trừ **thẻ ETC-8801**, chờ cấn trừ |

**Danh mục khác có sẵn:**
- **Khách:** ນາງ ວັນນາ và ຄຳຕຸ້ຍ (hoá đơn từng phiếu); ລາວ-ຈີນ ມີເນີໂຣ (gộp tháng).
- **Tuyến:** `ກາສີ → ກາລໍ`, `ກາສີ → ທ່າເຮືອກະລໍ`.
- **Xe:** 341, 342 (xe nhà); ຮ່ວມ-07 (xe liên kết của chủ xe ທ້າວ ຄຳຫລ້າ). 4 rơ-moóc.
- **Thẻ cao tốc:** `ETC-8801` (khách cấp, còn 3.166.500 LAK); `ETC-9902` (của EPL, 3.000.000 LAK).
- **Lệnh sửa chữa:** `LSC-2609-01` (đã nhập, chờ kiểm); `LSC-2609-02` (đã kiểm, chờ ghi sổ).
- **Phiếu bán:** `BH-2609-0001` (chủ xe mua, đã trừ khi trả chủ xe); `BH-2609-0002` (khách mua ở quầy, đã thu).
- **Tỷ giá:** 1 USD = 22.000 · 1 THB = 700 · 1 VND = 1,2 · 1 CNY = 3.000 LAK.
- **Cấn trừ tháng 8** của ຄຳຕຸ້ຍ còn **8.761.050 LAK chờ ghi**, dùng cho luồng D5.
- **Hợp đồng** (thêm 24/09):
  - `HDVC-2026-001`: hợp đồng vận chuyển với ຄຳຕຸ້ຍ, còn hạn tới 31/12/2026.
  - `HDVC-2026-002`: với ລາວ-ຈີນ ມີເນີໂຣ, **sắp hết hạn** 15/10/2026.
  - `HDTX-2026-001`: hợp đồng thuê xe với chủ xe ທ້າວ ຄຳຫລ້າ.
  - 13 phiếu đã mang số hợp đồng. ນາງ ວັນນາ đi khoán chuyến nên **không có** hợp đồng.
- **POD (biên bản giao nhận hàng)**: 7 phiếu đã giao và đã khoá có sẵn số POD. `T4-0429-08` cố ý **để trống POD**, dùng để thử
  cảnh báo lúc khoá.

---

## C. Test từng vai

Mỗi vai làm theo cùng một nếp:
1. Đăng nhập, xem **menu có đúng** không.
2. Đi qua **từng màn** của vai đó.
3. Làm **việc chính** của vai.
4. Thử làm việc của vai khác, việc đó **phải bị chặn**.
5. Bấm **Excel · PDF** ở một vài màn.

### C1. Admin Thà Bốc — thabok

> Nguyên tắc của vai này (anh Khampla A2): **Bãi nhập số lượng, nơi đổ, ai trả. Không thấy và không nhập bất kỳ số tiền
> nào**, trừ phí cao tốc BOT của tuyến đường (biểu phí công khai). Đăng nhập lần đầu trên máy chưa chọn ngôn ngữ thì
> giao diện tự sang **tiếng Lào**.

**Menu và Tổng quan**

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Nhìn thanh bên | Đúng 17 màn như bảng B1. **Không có** Hoá đơn, HĐ gộp, Xe liên kết, Tiền chuyến & nước, Tất toán, Bán hàng, Lệnh sửa chữa, Tỷ giá, Tài khoản |
| ☐ | Mở **Tổng quan** | 3 ô số: *Phiếu tháng này · Khối lượng đã chở · Xe đang trên đường*. **Không có** doanh thu, chi phí, "chưa thu", biểu đồ tiền |
| ☐ | Bấm các chip (Đang chạy, Đi lâu, Việc của tôi, Phiếu lĩnh chờ cấp…) | Mỗi chip mở đúng màn, đã lọc sẵn |
| ☐ | Đổi tháng ở Tổng quan | Ô chọn tháng dạng `MM/YYYY`; số liệu đổi theo |

**Phiếu xuất xe: lập phiếu mới (việc chính)**

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Bấm **Phiếu xuất xe** trên menu | Mở ra **phiếu MỚI trắng** với số mới. **Không** tự mở phiếu cũ ra sửa |
| ☐ | Mục I: đổi **Loại phiếu** giữa *Đi giao hàng* và *Đi gom hàng* | Số phiếu đổi tiền tố **T4-** ↔ **G4-** |
| ☐ | Chọn xe 342, tài xế, ngày | Biển đầu kéo và biển rơ-moóc tự điền |
| ☐ | Chọn một tài xế **bằng lái đã hết hạn** (ທ້າວ ສົມພອນ) | Bị cảnh báo hoặc chặn điều xe |
| ☐ | Mục II: chọn khách ຄຳຕຸ້ຍ, tuyến `ກາສີ → ກາລໍ`, cân tại mỏ 40 | Nơi đi, nơi đến tự điền theo tuyến. **Không có** ô đơn giá cước, thành tiền |
| ☐ | Mục II: ô **Hợp đồng vận chuyển** sau khi Lưu | Tự điền số hợp đồng còn hạn của khách (ຄຳຕຸ້ຍ → `HDVC-2026-001`) kèm nhãn *Còn hạn*. Bãi **không đổi được** |
| ☐ | Lập phiếu với xe **ຮ່ວມ-07** | Hiện thêm ô **Hợp đồng thuê xe** = `HDTX-2026-001` |
| ☐ | Mục II: ô **Số phiếu quặng** | Ô khoá, có dòng nhắc: *kế toán nhập khi nhận giấy · Bãi đính kèm ảnh*. Không bắt buộc ảnh |
| ☐ | Mục II: **đính kèm ảnh** phiếu quặng (tệp .jpg / .png / .pdf) | Tải lên được. Thử tệp `.exe` thì bị từ chối |
| ☐ | Mục III: thêm dòng dầu 150 L, **Nơi đổ** = Kho dầu Thà Bốc | **Không có** ô đơn giá, tiền tệ, thành tiền |
| ☐ | Mục III: thêm dòng dầu ở **trạm Việt Nam** | Hiện ô tích **Ghi nợ tại trạm** (kho của mình thì không hiện ô này) |
| ☐ | Mục IV: thêm tiền ăn 2, tiền nước 2, **phí cao tốc** 1 | Không có ô tiền. Dòng phí cao tốc có ô chọn **thẻ cao tốc** |
| ☐ | Mục V (Sửa chữa) | **Không có** nút nhập, không có nút gửi kiểm. Mục V là của tổ sửa chữa |
| ☐ | Bấm **Lưu** | Báo đã lưu. Tải lại trang (F5) rồi mở lại phiếu, các dòng vẫn còn |
| ☐ | Bấm **Gửi kiểm tra** ở mục I, II, III, IV | Từng mục chuyển trạng thái *đã nhập / chờ kiểm* |
| ☐ | Sửa một mục **đã được kế toán kiểm** | Bị khoá, báo *mục đã khoá* |
| ☐ | Bấm **Phiếu lĩnh nhiên liệu** | Sinh phiếu lĩnh có **mã QR** cho kho đã chọn |
| ☐ | Bấm **Phiếu chi tạm ứng** | Sinh phiếu tạm ứng có QR. **Không có** số tiền trên màn của Bãi |
| ☐ | Bấm **In** | Bản in sạch, không nút, không thanh bên. **Không có** số tiền |

**Theo dõi, điều xe, xe tới**

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | **Theo dõi phiếu vận chuyển**: nhìn các cột | Có số phiếu, xe, khách, tấn, trạng thái. **Không có** cột cước, thành tiền, lãi, chi phí |
| ☐ | Lọc theo trạng thái, tháng, ô tìm | Bảng lọc đúng |
| ☐ | **Theo dõi tuyến**: bấm một chuyến đang chạy | Thanh chi tiết trượt ra, bản đồ có đường tuyến và chấm xe, có các mốc chặng |
| ☐ | Bấm **Xe tới điểm** trên một chặng | Mốc chặng sáng lên, diễn biến có dòng mới |
| ☐ | Bấm **Báo sự cố** (không kèm tiền) | Ghi được sự cố. **Không có** ô "có khoản sửa chữa" hay số tiền |
| ☐ | Mở phiếu E `T4-0445-09` → **Xuất phát** | **Bị chặn** vì chưa chi tạm ứng: *tài xế chưa nhận tiền thì chưa xuất phát* |
| ☐ | Mở phiếu đang đi → **Xe đã tới · nhập cân cuối** (cân cuối, ngày về, km về) | Nhập km về nhỏ hơn km đi thì bị chặn. Nhập đúng thì có **dòng hao hụt** tự tính |
| ☐ | Trong hộp **Xe đã tới**: gõ **Số POD** và **Người ký nhận** | Khối **Biên bản giao nhận hàng (POD)** ở mục II hiện đúng số, ngày ký nhận = ngày về |
| ☐ | Khối POD → **+ Thêm ảnh · PDF** (chụp biên bản) | Ảnh hiện trong khối POD, **tách riêng** với ảnh phiếu quặng |
| ☐ | Phiếu **đã khoá** → sửa ô POD | Ô khoá (chỉ kế toán bổ sung được) |
| ☐ | Mở phiếu **chưa tới nơi** → **Đổi xe** (xem D10) | Phải ghi lý do. Không đổi chéo xe nhà ↔ xe liên kết |

**Các màn khác của Bãi**

| ☐ | Màn | Phải thấy |
|---|---|---|
| ☐ | **Phiếu chi · Phiếu thu** | Thấy danh sách phiếu tạm ứng, phiếu lĩnh. **Không có** số tiền, không có tab phiếu thu |
| ☐ | **Cấp phát** | Thấy phiếu lĩnh và tạm ứng đang chờ; cột tiền là "—" |
| ☐ | **Theo dõi NCC** | Chỉ có tên nhà cung cấp, dịch vụ, số dòng, kỳ trả. **Không có** tiền, mã tài khoản, nút *Các lần trả*, bảng cấn trừ |
| ☐ | **Kho hàng** | Thấy lô và tồn. **Không có** nút Điều chỉnh |
| ☐ | **Kho nhiên liệu** | Thấy tồn từng kho theo lít, sổ nhập xuất. **Không có** giá bình quân, cột đơn giá, nút Nhập kho / Chuyển kho / Xuất cho xe |
| ☐ | **Điểm đổ nhiên liệu** → **Thêm điểm đổ** / **Sửa** | Thêm, sửa được. Thêm xong có mã QR của điểm |
| ☐ | **Kho phụ tùng** | Thấy tồn. **Không có** đơn giá, không có nút Nhập / Xuất |
| ☐ | **Khách hàng** → Thêm / Sửa | Được. **Không có** nút Bảng giá, Công nợ |
| ☐ | **Khách hàng** → cột **Hợp đồng vận chuyển** · nút **Hợp đồng** | Thấy số hợp đồng, ngày, trạng thái. **Không có** nút Thêm / Sửa, **không thấy** bản scan (giấy có giá) |
| ☐ | **Xe** → **+ Thêm** một xe thử, bấm đúp mở hồ sơ | Hộp hồ sơ 7 tab. Tab Rơ-moóc: **Thay rơ-moóc** được. Thêm được ảnh xe |
| ☐ | **Tài xế** → **+ Thêm tài xế**, mở hồ sơ → tab Bằng lái → **+ Gia hạn** | Gia hạn xong cột Kết luận đổi màu; có lịch sử bằng |
| ☐ | **Thẻ cao tốc** | Thấy số dư thẻ. **Không có** Thêm thẻ, Nạp tiền, bảng cấn trừ |
| ☐ | **Tuyến đường** → Thêm / Sửa, nhập **phí cao tốc (BOT) cả tuyến** | Nhập được và thấy được (ngoại lệ có chủ đích) |
| ☐ | **Quy trình & trách nhiệm**: 4 tab | Tab *Luồng một chuyến* ghi rõ mỗi công đoạn sinh phiếu gì, chứng từ gì |
| ☐ | Bấm **Excel** ở Theo dõi phiếu, Kho nhiên liệu, Theo dõi NCC | Tải tệp `.xlsx`. Mở bằng Excel: **không có cột tiền nào** |

### C2. KT Thu/Chi Viêng Chăn — ketoan

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Bấm **Phiếu xuất xe** trên menu | **Không** tự mở tờ nào; ô chọn trống kèm câu nhắc. Chọn tờ thì mở đúng tờ đó |
| ☐ | Mở phiếu E `T4-0445-09` | Mở sẵn đúng tab của vai (mục I–II). Thấy **đơn giá cước, thành tiền** |
| ☐ | Mục II: nhập **số phiếu quặng** và ngày → Lưu | Lưu được (Bãi thì không) |
| ☐ | Bấm **Xác nhận kiểm tra** mục I, mục II | Hai mục sang *đã kiểm*, Bãi hết sửa được |
| ☐ | Bấm **Trả lại sửa** một mục rồi kiểm lại | Mục mở lại cho Bãi sửa, kiểm lại được |
| ☐ | Thử kiểm **mục IV** | **Không có** nút (việc của KT Chi phí) |
| ☐ | Sửa **đơn giá cước** khác hợp đồng trên một phiếu chưa khoá | Sửa được; thành tiền tính lại |
| ☐ | **Khách hàng** → **Bảng giá**: thêm giá 39 USD/t cho khách × tuyến, ngày hiệu lực | Lưu được. Giá 0 bị từ chối |
| ☐ | Lập một phiếu mới đúng khách × tuyến đó (bằng `thabok`), mở lại bằng `ketoan` | Đơn giá tự điền 39 USD |
| ☐ | Khách ນາງ ວັນນາ tuyến `ກາສີ → ທ່າເຮືອກະລໍ` | Cước **khoán trọn chuyến** (ví dụ 1.800 USD), không nhân tấn |
| ☐ | Khách hàng → **Sửa** → ô **Cách xuất hoá đơn** | Có hai lựa chọn: *Mỗi phiếu một hoá đơn* · *Gộp một tờ cuối tháng* |
| ☐ | Khách hàng → nút **Hợp đồng** ở ຄຳຕຸ້ຍ → **+ Thêm**: số, ngày ký, áp dụng từ, ngày hết hạn | Thêm được. Trùng số, hoặc hết hạn trước ngày áp dụng → bị chặn |
| ☐ | Trên dòng hợp đồng → **+ Thêm ảnh · PDF** (bản scan) → bấm tên tệp | Mở được bản scan |
| ☐ | Hợp đồng còn ≤ 30 ngày (`HDVC-2026-002`) | Nhãn vàng **Sắp hết hạn · còn n ngày** |
| ☐ | Mở một phiếu của ຄຳຕຸ້ຍ → mục II → ô chọn **Hợp đồng vận chuyển** | Đổi được sang hợp đồng khác của **cùng khách**, hoặc *Không có hợp đồng*; Lưu xong Bãi lưu lại **không điền đè** |
| ☐ | Xoá hợp đồng **đã có phiếu** chạy theo | Bị chặn, nhắc *Ngưng dùng* thay vì xoá |
| ☐ | **Xe liên kết** → bảng Chủ xe → nút **Hợp đồng** | Quản lý hợp đồng thuê xe (chỉ KT Thu/Chi và Sếp sửa) |
| ☐ | Phiếu `T4-0429-08` → **Khoá phiếu** | Bảng cảnh báo có dòng **Chưa có biên bản giao nhận hàng (POD)**; vẫn khoá được sau khi xác nhận |
| ☐ | Phiếu `T4-0429-08` (đã tới, chưa khoá) → **Khoá phiếu** | Hiện **bảng cảnh báo**: hao hụt, km lệch, thiếu phiếu quặng… Phải tích xác nhận mới khoá được |
| ☐ | Sau khi khoá, đăng nhập `thabok` mở phiếu đó | Bãi không sửa được gì |
| ☐ | **Kho hàng** → **Điều chỉnh tồn** một lô: −0,5 t kèm lý do | Tồn giảm; sổ có dòng *Điều chỉnh*; chứng từ có tờ **DC_HH** |
| ☐ | Điều chỉnh **không lý do**, hoặc giảm **quá tồn** | Bị từ chối |
| ☐ | **Kho nhiên liệu** → **Nhập kho** (kho VC, 1.000 L, 29.800 LAK/L, nhà cung cấp) | Tồn tăng; **giá bình quân** kho VC tính lại |
| ☐ | **Tỷ giá**: gõ USD = 23.000, **chưa Lưu**, nhìn máy tính quy đổi | Kết quả đổi ngay; bấm **Bỏ thay đổi** thì về số cũ |
| ☐ | Lưu tỷ giá mới rồi mở phiếu cũ `T4-0428` | Phiếu cũ **giữ** tỷ giá cũ. **Nhớ trả tỷ giá về 22.000** |
| ☐ | **Thẻ cao tốc** → Thêm thẻ; **Điều chỉnh số dư** bỏ trống lý do | Thêm được; điều chỉnh không lý do bị từ chối |
| ☐ | **Bán hàng** → lập phiếu bán cho **khách** (2 lọc dầu + 50 L dầu) | Tồn giảm; chứng từ có **HD_BAN** và **PXK_BAN (Nợ 607 / Có 1371)**; giá vốn dầu = giá bình quân kho |
| ☐ | Bán **quá tồn** | Bị chặn *không đủ* |
| ☐ | **Phiếu chi · Phiếu thu** → **Sổ chứng từ** | Có tờ của mọi loại, mỗi tờ đủ Nợ / Có. Lọc được theo loại, ngày |
| ☐ | **Excel** ở Theo dõi phiếu, Kho hàng; **PDF** ở Xe liên kết | Tệp mở được; ô tiền là số, **đúng tiền tệ từng phiếu** (USD là USD, LAK là LAK) |

### C3. KT Chi phí VC — ketoancp

> Quyết định 23/09: **đơn giá chi phí do người KIỂM nhập**, không phải Bãi. Dòng nào còn đơn giá 0 thì không kiểm được.

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Mở phiếu E `T4-0445-09` → mục IV | Các dòng tiền ăn, tiền nước **chưa có đơn giá**, ô giá được tô nhắc |
| ☐ | Bấm **Xác nhận kiểm tra** khi còn dòng giá 0 | Bị chặn, câu báo chỉ đúng dòng: *"dòng 1 (số lượng 3) chưa có đơn giá"* |
| ☐ | Nhập đơn giá (tiền ăn 120.000 LAK, tiền nước 60.000 LAK) → Kiểm | Lưu giá rồi kiểm luôn; mục sang *đã kiểm* |
| ☐ | Bấm **Ghi sổ kế toán** mục IV | Mục sang *đã ghi sổ*. Có dòng phí cao tốc trả bằng thẻ thì số dư thẻ bị trừ **đúng một lần** |
| ☐ | Thử kiểm **mục I** | Không có nút (việc của KT Thu/Chi) |
| ☐ | Mục V của một phiếu có dòng sửa chữa do tổ sửa nhập | Kiểm và ghi sổ được |
| ☐ | **Lệnh sửa chữa** → `LSC-2609-01` → **Kiểm** | Sang *đã kiểm* |
| ☐ | `LSC-2609-02` → **Ghi sổ** | Sang *đã ghi sổ*, chờ quỹ chi |
| ☐ | **Tất toán tài xế**: chọn kỳ, xem từng tài xế *đã ứng · đã chi thật · chênh* | Số tiền có LAK; bấm **Tất toán** một người thì chốt kỳ đó |
| ☐ | **Theo dõi NCC**: cột *Phát sinh · Ghi nợ tại trạm · Đã trả · Còn nợ* | Trạm dầu Việt Nam chỉ cộng dòng **ghi nợ**, không cộng dòng tài xế trả tiền mặt |
| ☐ | Theo dõi NCC → **Sửa** trạm dầu VN → *Cấn trừ vào cước khách* | Chọn được khách đứng ra với trạm |
| ☐ | Bấm **Các lần trả** một nhà cung cấp | Hiện lịch sử trả |

### C4. KT kho xăng dầu VC — khonl

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Mở phiếu E → mục III | Chỉ **mục III có nút**; mục khác chỉ đọc |
| ☐ | Dòng dầu lấy **từ kho** | Đơn giá tự lấy **giá bình quân của kho** lúc xuất, không ai gõ |
| ☐ | Dòng dầu đổ ở **trạm ngoài** (Việt Nam) | Nhập đơn giá + tiền tệ (VND) + tỷ giá. Thiếu giá thì không kiểm được |
| ☐ | **Kiểm** → **Ghi sổ** mục III | Tồn kho trừ ngay; sổ chứng từ có tờ **Phiếu xuất kho nhiên liệu** mang giá bình quân |
| ☐ | **Kho nhiên liệu** → chọn **từng kho** trong ô chọn | Tồn và **giá bình quân riêng của kho đó**. Để "Tất cả kho" thì ô giá ghi *Chọn một kho để xem* |
| ☐ | **Nhập kho** vào **Kho xe · dầu mua Việt Nam**: 1.000 L, 26.500 **VND**, tỷ giá 1,2 | Giá nhập quy ra LAK **tại lúc nhập** (31.800 LAK/L) |
| ☐ | **Chuyển kho**: kho xe → Thà Bốc 300 L | Hai dòng (ra / vào) cùng số chuyển; **không** sinh bút toán (CK_NL chỉ là chuyển chỗ) |
| ☐ | Chuyển **quá tồn** | Bị chặn |
| ☐ | **Xuất cho xe** (xuất lẻ không theo phiếu) | Có ô số xe; tồn giảm |
| ☐ | **Điểm đổ nhiên liệu** → Thêm / Sửa | Được |
| ☐ | Mở **Hoá đơn** | Xem được (vai này được xem hoá đơn) |

### C5. Thủ quỹ VC — quyvc

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Phiếu E → mục III (đã ghi sổ ở C4) → **Xác nhận đã chi** | Sang *đã chi*; sổ chứng từ có **phiếu chi** |
| ☐ | Bấm **Xác nhận đã chi** ở mục **chưa ghi sổ** | Bị chặn *sai bước* |
| ☐ | Thử chi mục IV | Không có nút (việc của quỹ tiền mặt `quytb`) |
| ☐ | **Tất toán tài xế** | Xem được |
| ☐ | **Tỷ giá** | Xem được, **không** có nút Lưu |

### C6. Quỹ tiền mặt cảng cạn — quytb

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | **Cấp phát** → phiếu tạm ứng `PTU-T4-0445-09/EPL` → **Cấp** | Phiếu sang *đã cấp*. Bây giờ `thabok` / tài xế **Xuất phát** được |
| ☐ | Phiếu E → mục IV (đã ghi sổ ở C3) → **Xác nhận đã chi** | Sang *đã chi*, có phiếu chi |
| ☐ | Thử chi mục III | Không có nút (việc của thủ quỹ VC) |
| ☐ | **Lệnh sửa chữa** `LSC-2609-02` (đã ghi sổ) → **Đã chi** | Phiếu chi **chỉ gồm phần mua ngoài** (công thợ), phần lấy kho không chi tiền. Xe về *Rảnh* nếu không đang chạy chuyến khác |
| ☐ | **Xe liên kết** → bảng Chủ xe → **Trả gộp** (xem D3) | Trừ tiền chủ xe mua ở quầy; một tờ **PC_CX** cho cả đợt |
| ☐ | **Thẻ cao tốc** → Xem thẻ → **Nạp tiền** (số tiền, biên lai) | Số dư tăng; có dòng *Nạp tiền* kèm số dư sau |
| ☐ | **Bán hàng** → một phiếu bán chưa thu → **Thu tiền** | Sang *đã thu*; có tờ **PT_BAN** |

### C7. KT Doanh thu VC — doanhthu

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | **Tổng quan** → ô **Việc của tôi** | Đếm *phiếu đã khoá chưa hoá đơn* + *hoá đơn chưa thu đủ*; bấm vào mở phiếu đầu tiên đang chờ |
| ☐ | Mở phiếu đã khoá, chưa hoá đơn → **Lập hóa đơn thu** | Có tờ **HD** trong sổ chứng từ |
| ☐ | Lập hoá đơn khi phiếu **chưa khoá** | Bị chặn *chưa khoá* |
| ☐ | **Ghi một lần thu**: hoá đơn USD, khách trả **LAK**, trả một phần | Sổ thu tiền có 1 dòng; phiếu *Thu một phần*; còn lại quy đúng về USD |
| ☐ | Ghi thu lần hai hết phần còn lại | Tự đổi **Đã thu đủ** (không có nút đánh dấu tay) |
| ☐ | Ghi thu **nhiều hơn** phần còn lại | Bị hỏi xác nhận |
| ☐ | Xoá một lần thu ghi nhầm (chưa đẩy kế toán) | Xoá được; trạng thái lùi lại. Tờ đã đẩy kế toán thì **không xoá được** |
| ☐ | **Hoá đơn gộp tháng** tháng 09/2026 → `HDT-202609-01` → **Xem** | Chi tiết từng phiếu; phiếu cũ thu trước |
| ☐ | Ghi thu ở tờ gộp | Tiền rải về từng phiếu; **một** tờ phiếu thu cho cả tờ gộp |
| ☐ | Mở phiếu lẻ `T4-0440-09` → tìm nút ghi thu | Bị chặn, câu nhắc chỉ sang tờ gộp |
| ☐ | **Theo dõi NCC** → bảng **Cấn trừ cuối tháng** (xem D5) | Ghi được cấn trừ, không ghi trùng |
| ☐ | **Khách hàng** → **Công nợ** một khách | Số tờ, đã xuất theo từng tiền, đã thu, **còn nợ** |
| ☐ | **Xe liên kết** | Xem được bảng lãi từng chuyến |
| ☐ | **Tỷ giá** | Sửa được (vai này được đặt tỷ giá) |

### C8. Thủ kho nhiên liệu — khotb, khovc

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Nhìn menu | Chỉ **Cấp phát** và **Kho nhiên liệu** |
| ☐ | Cấp phát: danh sách phiếu lĩnh chờ **của kho mình** | `khotb` không thấy phiếu lĩnh của kho Viêng Chăn và ngược lại |
| ☐ | Gõ / quét **mã QR** phiếu lĩnh | Hiện khối đối chiếu: số phiếu, xe, **biển số**, tài xế, số lít |
| ☐ | **Cấp** đúng số lít | Tồn trừ ngay; sinh tờ xuất kho nhiên liệu; phiếu thành *đã cấp* (ghi tên người cấp) |
| ☐ | Cấp **lệch nhiều** so với phiếu | Bắt ghi lý do |
| ☐ | Cấp phiếu lĩnh của **kho khác** | Bị chặn |
| ☐ | **Mất mạng** (xem F9) | Vẫn thấy danh sách, vẫn quét, vẫn cấp; có mạng lại thì tự gửi |

### C9. Thủ kho phụ tùng — khopt

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Menu | Chỉ **Kho phụ tùng** và **Xe** |
| ☐ | **Nhập kho** 4 lốp giá 3.300.000 | Tồn tăng; **đơn giá bình quân** tính lại; có tờ nhập kho phụ tùng |
| ☐ | **Xuất cho xe** 1 lốp cho xe 342 | Tồn giảm; ghi xe, ngày xuất |
| ☐ | Xuất **quá tồn** | Bị chặn |
| ☐ | Thêm phụ tùng mới, đặt **tồn tối thiểu** | Tồn ≤ tối thiểu thì trạng thái *sắp hết* |

### C10. Tổ sửa chữa — totsua

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Menu | Theo dõi tuyến · Phiếu xuất xe · Kho phụ tùng · Lệnh sửa chữa · Xe |
| ☐ | **Theo dõi tuyến** → chọn chuyến đang chạy → **Báo sự cố / sửa xe** → tích *có khoản sửa chữa* → **lấy từ kho** 1 phụ tùng | Dòng vào **mục V** của phiếu; tồn phụ tùng **giảm ngay**; phiếu ghi sự cố vào mục V (phiếu như DO đang mở) |
| ☐ | Cùng việc nhưng chọn **mua ngoài** (gara, số tiền) | Dòng mục V định khoản **…/4021**, chờ quỹ chi |
| ☐ | Xoá dòng đã xuất kho | Bị chặn *đã xuất kho* |
| ☐ | Tài xế báo hỏng (làm ở C11) → màn của tổ sửa có nút **Duyệt** | Duyệt xong thành dòng mục V |
| ☐ | **Lệnh sửa chữa** → **+ Lệnh sửa chữa**: xe 341, *Bảo dưỡng định kỳ*, số km → thêm dòng lấy kho + dòng mua ngoài | Lấy kho trừ tồn ngay; tờ ở trạng thái *đã nhập* |
| ☐ | Tìm nút Kiểm / Ghi sổ / Đã chi trên lệnh của mình | **Không có**: tổ sửa không tự kiểm, không tự chi |
| ☐ | **Xe** → xe đó → tab **Sửa chữa & chi phí** | Thấy cả dòng từ phiếu lẫn dòng từ lệnh sửa chữa |

### C11. Tài xế — tx01, tx02, tx03 (test bằng điện thoại)

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Đăng nhập `tx02` trên điện thoại | Chỉ có **Phiếu của tôi**; chữ đọc được, nút đủ to, không phải kéo ngang |
| ☐ | Phiếu E `T4-0445-09` → **Phiếu chi tạm ứng** | Hiện mã QR để ra quỹ nhận tiền; **thấy số tiền tạm ứng của mình** |
| ☐ | Bấm **Xuất phát** khi quỹ **chưa** cấp tạm ứng | Không bấm được / bị chặn |
| ☐ | Sau khi `quytb` cấp (C6) → **Xuất phát** | Được; phiếu sang *đang đi* |
| ☐ | **Khai đổ nhiên liệu** dọc đường (trạm Việt Nam) | **Chỉ nhập số lít**, không có ô giá; chờ KT kho duyệt |
| ☐ | **Báo hỏng / sự cố** kèm số tiền dự kiến | Chờ tổ sửa chữa duyệt |
| ☐ | **Chia sẻ vị trí** (cho phép GPS) | Theo dõi tuyến (bằng `thabok`) thấy chấm xe mới, *GPS mới vài phút* |
| ☐ | **Báo đã về**: ngày về, km về | `thabok` bấm *Xe đã tới* thì hai ô đó điền sẵn |
| ☐ | Gõ thẳng địa chỉ `#/tai-khoan` hoặc `#/theo-doi` | Tự chuyển về Phiếu của tôi |
| ☐ | `tx01` mở phiếu của `tx02` | Không thấy phiếu của người khác |

### C12. Sếp — admin

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Menu | Đủ 27 màn |
| ☐ | **Tổng quan** | Doanh thu, chi phí, khối lượng, chưa thu (M LAK); dòng nhỏ chia theo từng tiền; biểu đồ theo ngày, cơ cấu chi phí, hao hụt, hiệu suất xe; Gantt chuyến |
| ☐ | Mở một phiếu đã khoá **chưa có hoá đơn** → **Mở khoá** | Chỉ Sếp có nút; mở xong vai khác sửa lại được |
| ☐ | Mở khoá phiếu **đã có hoá đơn** | Bị chặn *đã hoá đơn* |
| ☐ | **Phiếu chi · Phiếu thu** → **Cấu hình**: địa chỉ sổ kế toán + token, mã TK giá vốn | Chỉ Sếp thấy. Đừng xoá token đang dùng |
| ☐ | Bấm **Đẩy hết tờ chưa đẩy** | Báo *n tờ xong, 0 lỗi*. Tờ bị bên kia từ chối thì hiện câu lỗi ngay trên dòng |
| ☐ | **Tài khoản**: danh sách, tab **Vai** | Mỗi vai ghi màn thấy, việc được làm |
| ☐ | **Quy trình & trách nhiệm** → 4 tab | *Luồng một chuyến* · *Ngoài chuyến* · *Vai × mục* · *Danh mục chứng từ* (mỗi tờ ghi Nợ / Có) |
| ☐ | Xoá một phiếu thử **đã cấp dầu** | Xoá được; **dầu trả về kho** (Bãi thì bị chặn) |

---

## D. Luồng xuyên vai — 12 kịch bản ngoài đời

Mỗi kịch bản đi qua nhiều vai theo đúng thứ tự ngoài đời. **Ghi lại số phiếu anh tạo** để dọn sau.

### D1. Một chuyến xe nhà trọn luồng (cốt lõi, làm đầu tiên)

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `thabok` | Lập phiếu giao mới: xe 342, tài xế tx02, khách ຄຳຕຸ້ຍ, tuyến `ກາສີ → ກາລໍ`, cân mỏ 41; dầu 150 L kho Thà Bốc; tiền ăn 2, tiền nước 2 → Lưu → Gửi kiểm 4 mục | 4 mục *chờ kiểm*; không có số tiền nào trên màn |
| ☐ | 2 | `thabok` | Bấm **Phiếu lĩnh nhiên liệu** và **Phiếu chi tạm ứng** | Hai phiếu có QR |
| ☐ | 3 | `ketoan` | Nhập số phiếu quặng; kiểm mục I, II | Thấy cước tự điền theo bảng giá |
| ☐ | 4 | `khonl` | Kiểm, ghi sổ mục III | Giá dầu = bình quân kho Thà Bốc |
| ☐ | 5 | `khotb` | Cấp phát → quét phiếu lĩnh → Cấp 150 L | Tồn Thà Bốc giảm 150 |
| ☐ | 6 | `ketoancp` | Mục IV: nhập giá, kiểm, ghi sổ | Tổng tạm ứng hiện ra |
| ☐ | 7 | `quytb` | Cấp phát → cấp tạm ứng; chi mục IV | Phiếu tạm ứng *đã cấp* |
| ☐ | 8 | `quyvc` | Chi mục III | Có phiếu chi |
| ☐ | 9 | `tx02` | Xuất phát → chia sẻ vị trí → báo đã về | Theo dõi tuyến thấy xe di chuyển |
| ☐ | 10 | `thabok` | Xe tới điểm từng chặng → **Xe đã tới · nhập cân cuối** 40,6 t | Dòng hao hụt 0,4 t |
| ☐ | 11 | `ketoan` | **Khoá phiếu** (đọc bảng cảnh báo, xác nhận) | Đã khoá |
| ☐ | 12 | `doanhthu` | Lập hoá đơn → ghi thu đủ | *Đã thu đủ* |
| ☐ | 13 | `ketoan` | **Sổ chứng từ** lọc theo số phiếu | Đủ: DO · PLNL · PTU · PXK_NL · phiếu chi · HD · PT |
| ☐ | 14 | `admin` / 8030 | Đẩy sang sổ kế toán, mở EPL_KETOAN xem các bút toán | Có đủ bút toán, sổ vẫn cân |

### D2. Tách chặng: gom mỏ → bãi, giao bãi → cảng bằng xe khác

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `thabok` | Phiếu mới, **Đi gom hàng**, xe 341, dòng hàng quặng 40 t | Số phiếu **G4-**; ô cân mỏ tự = 40 |
| ☐ | 2 | `thabok` | (sau khi các mục qua duyệt) Xe tới bãi, cân bãi 39,6 | Hao hụt 0,4 t; dòng hàng + cân **khoá**; **Kho hàng** có lô mới 39,6 t |
| ☐ | 3 | `thabok` | Phiếu mới **Đi giao hàng**, **xe 342**, dòng hàng **Lấy từ lô** vừa tạo 25 t | Lô còn 14,6 t |
| ☐ | 4 | `thabok` | Sửa số tấn lấy thành 100 | Bị chặn *lô chỉ còn … t* |
| ☐ | 5 | `thabok` | Xoá phiếu gom đã có phiếu giao lấy hàng | Bị chặn |
| ☐ | 6 | `ketoan` | Sổ chứng từ | Có **PNK_HH** (nhập kho hàng) và **PXK_HH** (xuất kho hàng) |

### D3. Xe liên kết + chủ xe mua dầu ở quầy (deal 1tr6 − mua 3 trăm = trả 1tr3)

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `thabok` | Lập phiếu với xe **ຮ່ວມ-07** | Phí 2%/phiếu, ngưỡng tấn tự điền theo hợp đồng chủ xe |
| ☐ | 2 | `ketoan` | Nhập **giá thuê xe** (ví dụ 38,5 USD/t) | Thấy lãi EPL trên chuyến |
| ☐ | 3 | … | Đi hết luồng tới khoá (như D1) | |
| ☐ | 4 | `ketoan` | **Bán hàng** → người mua = **chủ xe ທ້າວ ຄຳຫລ້າ**, 10 L dầu × 31.000 LAK | Phiếu bán mang cờ *trừ vào tiền trả chủ xe* |
| ☐ | 5 | `quytb` | **Xe liên kết** → **Trả gộp** chủ xe đó | Hộp hiện **tiền thuê − tiền chủ xe mua = thực trả** |
| ☐ | 6 | `ketoan` | Sổ chứng từ | **PC_CX** ghi số **thực trả**; phiếu bán cho chủ xe hạch toán **Nợ 4022 / Có 70** |
| ☐ | 7 | `quytb` | Trả lần hai | Bị chặn *đã trả* |
| ☐ | 8 | `thabok` | Mở **Xe liên kết** | Không có trong menu |

### D4. Dầu mua Việt Nam → kho xe → cấp cho chuyến → phần dư chuyển về Thà Bốc

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `khonl` | Nhập 800 L vào **Kho xe · dầu mua VN**, 27.000 VND, tỷ giá 1,2 | Giá quy LAK lúc nhập = 32.400 |
| ☐ | 2 | `thabok` | Phiếu mới, mục III lấy 500 L **từ kho xe** | |
| ☐ | 3 | `khonl` | Kiểm, ghi sổ mục III | Dầu mang giá bình quân của **kho xe**, không phải của Thà Bốc |
| ☐ | 4 | `khonl` | **Chuyển kho** 300 L kho xe → Thà Bốc | Tồn kho xe về 0; Thà Bốc tăng 300; giá bình quân Thà Bốc tính lại |
| ☐ | 5 | `ketoan` | Sổ chứng từ | PNK_NL (Có 4021 trạm VN), PXK_NL, **CK_NL không định khoản** |

### D5. Thẻ cao tốc + cấn trừ cuối tháng

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `ketoan` | Thẻ cao tốc → ghi lại số dư `ETC-8801` | |
| ☐ | 2 | `thabok` | Phiếu mới, mục IV dòng **Phí cao tốc** → chọn thẻ ETC-8801 | Số dư thẻ **chưa** đổi |
| ☐ | 3 | `ketoancp` | Nhập giá, kiểm, **ghi sổ** mục IV | Số dư thẻ giảm đúng một lần; sổ thẻ có dòng *Qua trạm* ghi số phiếu |
| ☐ | 4 | `doanhthu` | Theo dõi NCC → **Cấn trừ cuối tháng**, tháng 08/2026 → ຄຳຕຸ້ຍ → **Ghi cấn trừ tháng · 8.761.050** | Ghi vào hoá đơn còn nợ (phiếu F `T4-0446-09`); phiếu có dòng thu cách *Cấn trừ*, mã `CT-202608` |
| ☐ | 5 | `doanhthu` | Bấm lại lần nữa | Báo không còn gì để ghi, **không ghi trùng** |
| ☐ | 6 | `doanhthu` | Tháng 09/2026: xem dòng ຄຳຕຸ້ຍ | *Khách trả hộ qua thẻ* có số tiền cao tốc tháng 9 (1.833.500) |

### D6. Sửa chữa: tài xế báo hỏng → tổ sửa duyệt → lấy kho / mua ngoài → kiểm → chi

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `tx01` | Trên phiếu đang đi → **Báo hỏng** "nổ lốp", 3.500.000 | Chờ duyệt |
| ☐ | 2 | `thabok` | Tìm nút Duyệt | **Không có** (việc của tổ sửa) |
| ☐ | 3 | `totsua` | Duyệt → chọn **lấy 1 lốp từ kho** | Mục V có dòng; tồn lốp giảm 1 |
| ☐ | 4 | `ketoancp` → `quytb` | Kiểm, ghi sổ mục V; quỹ chi | Phần lấy kho có **PXK_PT**, không chi tiền mặt |
| ☐ | 5 | `totsua` | Lệnh sửa chữa riêng cho xe 342 (bảo dưỡng) | Như C10 |

### D7. Bán hàng ở quầy (xăng, phụ tùng) cho khách

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `ketoan` | Bán hàng → khách ນາງ ວັນນາ: 1 bố thắng + 30 L dầu | HD_BAN + PXK_BAN; giá vốn = **bình quân**, TK **607** |
| ☐ | 2 | `quytb` | Thu tiền | PT_BAN |
| ☐ | 3 | `ketoan` | Bỏ một phiếu **chưa thu** | Hàng về kho; chứng từ rút |
| ☐ | 4 | `ketoan` | Bỏ phiếu **đã thu** | Bị chặn |

### D8. Hoá đơn gộp tháng (khách hợp đồng)

Làm theo C7 (các dòng HĐ gộp). Thêm một bước: lập phiếu mới tháng này cho ລາວ-ຈີນ ມີເນີໂຣ, đi tới khoá → `doanhthu` vào
**Hoá đơn gộp tháng**: bảng **Chờ gộp** hiện phiếu đó → **Gộp hoá đơn tháng** → ra tờ mới.

### D9. Tất toán tài xế cuối kỳ

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `ketoancp` | Tất toán tài xế → kỳ tháng 9 | Mỗi tài xế: đã ứng · đã chi thật · chênh (LAK) |
| ☐ | 2 | `ketoancp` | **Tất toán** một tài xế | Chốt kỳ; có chứng từ |
| ☐ | 3 | `ketoancp` | Bỏ chốt | Chứng từ rút (khi chưa đẩy kế toán) |

### D10. Đổi xe giữa đường

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `thabok` | Phiếu đang đi → **Đổi xe** sang xe nhà khác, lý do "gãy nhíp", xe cũ *vào xưởng* | Phiếu mang biển xe mới; diễn biến ghi *Đổi xe … → … · lý do*; **mục I về "đã nhập"** để kiểm lại |
| ☐ | 2 | `thabok` | Mở **Xe** | Xe cũ *Sửa chữa*, xe mới *Đang chạy* |
| ☐ | 3 | `thabok` | Đổi sang **ຮ່ວມ-07** | Bị chặn: không đổi chéo xe nhà ↔ xe liên kết |
| ☐ | 4 | `thabok` | Đổi xe trên phiếu **đã tới nơi** | Bị chặn |
| ☐ | 5 | `ketoan` | Kiểm lại mục I | Được |

### D11. Nhiều tiền tệ và tỷ giá

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | `ketoan` Theo dõi phiếu: cột Tiền | `T4-0428` USD · `T4-0429` **CNY** · `T4-0432` LAK |
| ☐ | Dòng tổng cuối bảng | Cộng **riêng từng tiền**, không dồn một số |
| ☐ | Ô **Quy đổi** → LAK / USD | Cả bảng về một tiền |
| ☐ | Mọi màn có tiền | Số tiền luôn đi kèm mã tiền **của chính chứng từ** (không có chỗ nào số trơn không tiền tệ) |
| ☐ | Excel xuất ra | Ô tiền là số, định dạng mang đúng tiền tệ của phiếu |

### D12. Mất mạng ở kho dầu

| ☐ | Bước | Làm | Phải thấy |
|---|---|---|---|
| ☐ | 1 | `thabok` lập phiếu lĩnh 20 L ở kho Thà Bốc | |
| ☐ | 2 | `khotb` mở **Cấp phát** khi **còn mạng** | Thấy phiếu lĩnh |
| ☐ | 3 | **Tắt Wi-Fi** / rút mạng, chuyển màn rồi quay lại Cấp phát | Vẫn thấy danh sách; có **dải báo mất mạng** |
| ☐ | 4 | Quét mã → **Cấp** | Dòng hiện *chờ gửi* |
| ☐ | 5 | Bật mạng lại | Tự gửi; phiếu thành *đã cấp* trên máy chủ |

### D13. Hợp đồng và POD (thêm 24/09)

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `ketoan` | Khách hàng → ນາງ ວັນນາ → **Hợp đồng** → thêm `HD-THU-01`, **đã hết hạn** (hết hạn 31/01/2026) | Nhãn đỏ **Hết hạn** |
| ☐ | 2 | `thabok` | Lập phiếu giao cho ນາງ ວັນນາ → Lưu | Ô hợp đồng: **Chưa có hợp đồng** (hết hạn thì không tự điền) |
| ☐ | 3 | `thabok` | Đi luồng tới **Xe đã tới**, **không** gõ POD | Khối POD trống |
| ☐ | 4 | `ketoan` | **Khoá phiếu** | Cảnh báo **thiếu POD** và **hợp đồng HD-THU-01 đã hết hạn**, chỉ cảnh báo, xác nhận vẫn khoá được |
| ☐ | 5 | `ketoan` | Phiếu đã khoá → gõ số POD → Lưu | Kế toán bổ sung được; Bãi thì không |
| ☐ | 6 | `ketoan` | In phiếu | Bản in có **số hợp đồng** và **khối POD** |
| ☐ | 7 | `ketoan` | Xoá hợp đồng thử `HD-THU-01` | Bị chặn vì đã có phiếu, **Ngưng dùng** thay vì xoá |

---

## E. Những chỗ PHẢI bị chặn (phân quyền)

Khách hay hỏi nhất phần này. Mỗi dòng: đăng nhập đúng vai rồi cố làm việc của người khác.

| ☐ | Vai | Thử | Phải thấy |
|---|---|---|---|
| ☐ | `thabok` | Tìm Hoá đơn, HĐ gộp, Xe liên kết, Tiền chuyến & nước, Tất toán, Bán hàng, Tỷ giá, Tài khoản | Không có trên menu; gõ thẳng địa chỉ thì tự chuyển màn |
| ☐ | `thabok` | Tìm bất kỳ số tiền nào (trừ phí BOT tuyến) | Không có: tổng quan, theo dõi, phiếu, kho dầu, kho phụ tùng, NCC, chứng từ, Excel xuất ra |
| ☐ | `thabok` | Gõ số phiếu quặng | Ô khoá |
| ☐ | `thabok` | Nhập mục V, nhập kho phụ tùng | Không có nút |
| ☐ | `thabok` | Kiểm bất kỳ mục nào | Không có nút |
| ☐ | `thabok` | Khoá phiếu, lập hoá đơn, trả chủ xe, ghi cấn trừ | Không có nút / bị chặn |
| ☐ | `thabok` | Xoá phiếu đã có mục được kiểm, hoặc đã cấp dầu | Bị chặn |
| ☐ | `ketoan` | Kiểm mục IV–VI, chi tiền | Không có nút |
| ☐ | `ketoan` | Lập phiếu xuất xe mới | Bị chặn (việc của Bãi) |
| ☐ | `ketoan` | Mở Cấu hình sổ chứng từ | Không có (chỉ Sếp) |
| ☐ | `thabok` | Thêm / sửa hợp đồng; mở bản scan hợp đồng; đổi hợp đồng trên phiếu | Không có nút / bị chặn |
| ☐ | `doanhthu` | Thêm hợp đồng **thuê xe** | Bị chặn (chỉ KT Thu/Chi) |
| ☐ | `ketoancp` | Kiểm mục I–II, mục III | Không có nút |
| ☐ | `khonl` | Nút ở mục khác mục III | Không có |
| ☐ | `quyvc` | Chi mục IV–VI | Không có nút |
| ☐ | `quytb` | Chi mục III; chi mục chưa ghi sổ | Không có nút; *sai bước* |
| ☐ | `doanhthu` | Kiểm, chi bất kỳ mục nào | Không có nút |
| ☐ | `khotb` | Cấp phiếu lĩnh kho Viêng Chăn | Bị chặn |
| ☐ | `khopt` | Mở Phiếu xuất xe | Không có trên menu |
| ☐ | `totsua` | Tự kiểm / ghi sổ / chi lệnh sửa của mình | Không có nút |
| ☐ | `tx01` | Xem phiếu người khác; tự cấp tạm ứng cho mình | Không thấy; bị chặn |
| ☐ | mọi vai trừ Sếp | Mở khoá phiếu đã khoá | Không có nút |
| ☐ | Sếp | Mở khoá phiếu đã có hoá đơn | Bị chặn |

---

## F. Kiểm chung giao diện

| ☐ | # | Việc | Phải thấy |
|---|---|---|---|
| ☐ | F1 | Nút ngôn ngữ → **ພາສາລາວ · English · Tiếng Việt · VI + ລາວ** trên 5–6 màn bất kỳ | Chữ đổi hết; **không** chỗ nào lòi mã kiểu `nav_dash`, `undefined`, `NaN`; không câu nửa Việt nửa Lào |
| ☐ | F2 | **Ctrl + lăn chuột** phóng to 150%, thu nhỏ 80% | Cả trang co giãn theo, không vỡ khung, không phải kéo ngang, không phải thu nhỏ mới xem hết |
| ☐ | F3 | Tên người dùng → **Cài đặt giao diện** → thanh bên ↔ thanh trên | Đổi kiểu điều hướng; máy nhớ lựa chọn |
| ☐ | F4 | Ô **Tìm chức năng (Ctrl K)** | Gõ vài chữ, lọc ra đúng màn |
| ☐ | F5 | Nút **Excel** trên thanh đầu trang ở 10 màn bất kỳ | Tải `.xlsx`; **mở bằng Microsoft Excel thật không báo lỗi**; đầu tệp có tên báo cáo · bộ lọc · người xuất · giờ; cột tiền là số, cộng được bằng `=SUM` |
| ☐ | F6 | Nút **PDF** → hộp in → chọn **Lưu thành PDF** | Báo cáo khổ ngang có đầu trang; phiếu / hoá đơn giữ mẫu tờ phiếu; chữ Lào in đúng dấu |
| ☐ | F7 | Nút **In** ở phiếu xuất xe, hoá đơn, chứng từ, lệnh sửa chữa | Bản in sạch, có chỗ ký |
| ☐ | F8 | Mọi hộp hỏi xác nhận (xoá, khoá, trả…) | Là hộp **trong ứng dụng**, không phải hộp "127.0.0.1 says" của trình duyệt |
| ☐ | F9 | Tắt mạng rồi chuyển vài màn | Màn đã mở vẫn xem được; Cấp phát xếp hàng đợi |
| ☐ | F10 | Điện thoại (tài xế, thủ kho) | Không cuộn ngang; nút bấm được bằng ngón tay |
| ☐ | F11 | Mở mỗi màn lần đầu | Có dải *Đang tải…* rồi mới hiện; không màn nào trắng trơn |
| ☐ | F12 | Bảng dài (Theo dõi phiếu, Kho nhiên liệu) | Cột không chồng chữ; ô chọn tháng dạng `MM/YYYY` |
| ☐ | F13 | Mọi ngày tháng | Dạng `dd/mm/yyyy` |
| ☐ | F14 | Nhìn chung từng màn | Ghi lại **chỗ nào xấu, rối, khó hiểu** với người bên Lào (họ quen Excel năm 2016) |

---

## G. Sổ kế toán EPL_KETOAN — cổng 8030

Đăng nhập `admin` / `1234` (hoặc `ketoantruong`, `ketoan`, `xem`). **Kế toán trưởng** (`ketoantruong`, thêm 24/09): duyệt / trả lại
bút toán ghi tay, xem hết sổ, **không** thấy token, không sửa cấu hình, không quản người dùng.

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | **Tổng quan** | KPI khớp sổ cái; chuông có việc cần biết |
| ☐ | **Sổ kế toán** → Nhật ký chung | Có bút toán của các chứng từ anh vừa tạo ở Phần D (sau khi Sếp bấm Đẩy) |
| ☐ | **Cân đối phát sinh** | **Nợ = Có** |
| ☐ | **Công nợ** phải thu | Còn phải thu từng khách = màn Công nợ khách bên EPL_LAO |
| ☐ | **Kho** | Số dư 1371 khớp sổ cái |
| ☐ | **Ghi tay** → `ketoan` lập một bút toán → `ketoantruong` duyệt | Vào sổ; `ketoan` tự duyệt thì bị chặn; bút toán sinh từ EPL_LAO thì không sửa được |
| ☐ | `ketoantruong` mở **Cài đặt** | Không thấy token, không sửa được thông tin công ty, không có danh sách người dùng |
| ☐ | Mỗi trang có nút **Xuất Excel** và **PDF** | Tệp `.xlsx` mở được; PDF khổ ngang |

---

## H. Mẫu ghi lỗi và việc sau khi test

### H1. Mẫu ghi lỗi (mỗi lỗi một dòng)

| # | Vai | Màn | Làm gì | Thấy gì | Mong thấy gì | Mức | Ảnh |
|---|---|---|---|---|---|---|---|
| 1 | `thabok` | Phiếu xuất xe | Bấm Lưu khi chưa chọn xe | Không báo gì | Báo "chưa chọn xe" | Nhỏ | anh1.png |

**Mức:**
- **Chặn**: không làm tiếp được luồng.
- **Sai**: số, quyền hoặc tiền sai.
- **Nhỏ**: chữ, bố cục, màu.
- **Góp ý**: nên đổi cho dễ dùng.

Gửi em cả bảng, em sửa theo đợt, **Chặn** và **Sai** trước.

### H2. Sau khi test xong

| ☐ | Việc |
|---|---|
| ☐ | Trả **tỷ giá** về như cũ nếu đã đổi (USD 22.000 · THB 700 · VND 1,2 · CNY 3.000) |
| ☐ | Nhờ em **dọn dữ liệu thử**: sao lưu hai DB → chạy `python tools/don_rac_bo_kiem.py` (xem trước sẽ xoá gì) → `python tools/don_rac_bo_kiem.py that`. Công cụ **giữ 15 phiếu mẫu**, xoá phiếu anh tạo thêm và dọn luôn bên sổ kế toán |
| ☐ | **Không** chạy `backend\app\seed.py --dung-lai` trên DB `epl_lao` |
| ☐ | Muốn máy tự kiểm lại sau khi sửa: nhờ em chạy bộ kiểm (`kiem/…`), mất khoảng 30–40 phút |
