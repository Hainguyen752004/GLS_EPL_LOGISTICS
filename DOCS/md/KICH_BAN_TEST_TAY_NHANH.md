# Kịch bản test tay NHANH EPL Lào — trước khi nối sổ kế toán thật

Viết cho anh (chủ dự án) tự test nhanh trong khoảng **2 giờ**. Cập nhật 28/09/2026, sau đợt chuẩn bị dữ liệu lớn (25/09)
và đợt UAT tự động từ A đến Z, **đạt hết**. Test tay xong mà ổn thì nối sang **API kế toán thu chi thật của anh Tune**
(Phần G). Anh Tune làm thay anh Khang trong tuần anh Khang nghỉ.

Bản đầy đủ theo từng vai vẫn là `KICH_BAN_TEST_TAY_THEO_VAI.docx` (24/09, mất 6–8 giờ). Bản này **không thay** bản đó,
chỉ gom lại những chỗ quan trọng nhất và những chỗ **mới đổi từ 25/09**. Muốn soi kỹ vai nào thì mở bản đầy đủ: các mục
C1–C12, D1–D13 bên đó vẫn đúng.

**Cách đọc:** mỗi dòng là một việc cần thử. Cột **Phải thấy** là kết quả đúng. Thấy khác thì ghi lỗi theo mẫu ở **Phần
H**, không cần dừng lại, cứ đi tiếp. Mỗi dòng có ô ☐ để tick.

**Thời gian ước chừng:**
- Phần A (chuẩn bị): 5 phút.
- Phần B (một chuyến trọn luồng): 40 phút.
- Phần C (mỗi vai một phút): 25 phút.
- Phần D (chỗ mới đổi từ 25/09): 15 phút.
- Phần E (đẩy sổ và EPL_KETOAN): 20 phút.
- Phần F (giao diện chung): 10 phút.

---

## Mục lục

- **A.** Chuẩn bị: phần em đã làm sẵn, phần anh bật máy
- **B.** Một chuyến xe nhà trọn luồng (cốt lõi, làm đầu tiên)
- **C.** Mỗi vai một phút: những chỗ dễ sai nhất
- **D.** Những chỗ mới đổi từ 25/09 (dữ liệu lớn)
- **E.** Đẩy chứng từ và Sổ kế toán EPL_KETOAN (cổng 8030)
- **F.** Giao diện chung
- **G.** Test ổn rồi: nối API kế toán thu chi thật của anh Tune
- **H.** Mẫu ghi lỗi và việc sau khi test

---

## A. Chuẩn bị

### A1. Em đã làm sẵn (28/09, sáng)

| ✔ | Việc | Kết quả |
|---|---|---|
| ✔ | **Sao lưu hai DB** | `D:\Demo_Lao\saoluu\saoluu_epl_lao_20260928_0846.dump` và `saoluu_epl_ketoan_20260928_0846.dump`. Test hỏng gì cũng khôi phục được |
| ✔ | **Kiểm dữ liệu mẫu** | Đủ **15 phiếu mẫu**, đúng trạng thái như bảng B2 của bản đầy đủ. Phiếu E `T4-0445-09` vẫn *chờ kế toán nhập giá*, tạm ứng *chờ cấp* |
| ✔ | Danh mục mẫu | Thẻ `ETC-8801` còn 3.166.500 LAK, `ETC-9902` 3.000.000 LAK. `LSC-2609-01` *đã nhập*, `LSC-2609-02` *đã kiểm*. Tỷ giá USD 22.000 · THB 700 · VND 1,2 · CNY 3.000 |
| ✔ | **Sổ kế toán** | 81 tờ, 50 bút toán, **Nợ = Có = 992.085.645 LAK**. Bên EPL Lào không còn tờ nào chưa đẩy |
| ✔ | Cấu hình đẩy chứng từ | Đang trỏ `http://127.0.0.1:8030` (sổ của anh) |
| ✔ | UAT tự động | Bộ kiểm API, 43 màn xuất Excel/PDF, 6 bộ kiểm giao diện, kiểm hai đầu, 8 bộ kiểm Sổ kế toán: **đạt hết** |
| ✔ | Lỗi UAT tìm ra | Tổng quan: bấm Excel ngay lúc vừa mở màn thì báo "không có gì để xuất". **Đã sửa** (commit `808f049`) |

### A2. Anh làm trước khi test

| ☐ | Việc | Ghi chú |
|---|---|---|
| ☐ | **Bật máy chủ EPL Lào cổng 8020** (hiện đang tắt) | Phải chạy **mã mới nhất** (commit `808f049`). Mã cũ thì chưa có các sửa từ 25/09 |
| ☐ | **Bật Sổ kế toán cổng 8030**: chạy `EPL_KETOAN\chay.bat` (hiện đang tắt) | Không bật thì bước đẩy ở Phần B, E báo *không nối được sổ kế toán* |
| ☐ | Mở `http://<máy chủ>:8020` trên Chrome, thêm một tab `:8030` | Mật khẩu mọi tài khoản demo là `1234` |
| ☐ | Mở thêm một **cửa sổ ẩn danh** (Ctrl+Shift+N) | Mỗi cửa sổ một vai, ví dụ Bãi bên trái, kế toán bên phải, khỏi đổi vai liên tục |
| ☐ | Mở sẵn một tệp ghi lỗi theo mẫu ở Phần H | Mỗi lỗi một dòng, kèm ảnh chụp màn hình |

**Đổi vai nhanh:**
1. Bấm tên người dùng ở góc dưới thanh bên.
2. Chọn **Đổi tài khoản**.
3. **Bấm một thẻ tài khoản là vào thẳng**, khỏi gõ mật khẩu.

### A3. 15 tài khoản

| Tài khoản | Vai | Việc chính |
|---|---|---|
| `thabok` | Admin Thà Bốc (Bãi) | Lập phiếu, điều xe, nhập số lượng. **Không thấy tiền** |
| `ketoan` | KT Thu/Chi Viêng Chăn | Kiểm mục I–II, bảng giá, số phiếu quặng, khoá phiếu |
| `ketoancp` | KT Chi phí VC | Nhập giá, kiểm, ghi sổ mục IV–VI, tất toán tài xế |
| `khonl` | KT kho xăng dầu VC | Nhập giá, kiểm, ghi sổ mục III; nhập kho, chuyển kho dầu |
| `quyvc` | Thủ quỹ VC | Chi mục III |
| `quytb` | Quỹ tiền mặt cảng cạn | Chi mục IV–VI, cấp tạm ứng, trả chủ xe |
| `doanhthu` | KT Doanh thu VC | Hoá đơn, thu tiền, cấn trừ |
| `khotb` · `khovc` | Thủ kho nhiên liệu Thà Bốc · Viêng Chăn | Cấp dầu theo phiếu lĩnh |
| `khopt` | Thủ kho phụ tùng | Nhập, xuất phụ tùng |
| `totsua` | Tổ sửa chữa | Mục V, lệnh sửa chữa |
| `tx01` · `tx02` · `tx03` | Tài xế | Phiếu của tôi (test bằng điện thoại) |
| `admin` | Sếp | Xem tất cả, mở khoá, cấu hình, đẩy sổ |

---

## B. Một chuyến xe nhà trọn luồng

Làm phần này **đầu tiên**. Nó đi qua gần hết các vai theo đúng thứ tự ngoài đời. **Ghi lại số phiếu anh tạo** để dọn sau.

| ☐ | Bước | Vai | Làm | Phải thấy |
|---|---|---|---|---|
| ☐ | 1 | `thabok` | Bấm **Phiếu xuất xe** trên menu | Mở ra **phiếu MỚI trắng** với số mới. **Không** tự mở phiếu cũ ra sửa |
| ☐ | 2 | `thabok` | Xe 342, tài xế tx02, khách ຄຳຕຸ້ຍ, tuyến `ກາສີ → ກາລໍ`, cân mỏ 41; mục III dầu 150 L kho Thà Bốc; mục IV tiền ăn 2, tiền nước 2 → **Lưu** | Biển đầu kéo, biển rơ-moóc, nơi đi, nơi đến tự điền. Ô hợp đồng tự điền `HDVC-2026-001` · *Còn hạn*. **Không có ô tiền nào** |
| ☐ | 3 | `thabok` | **Gửi kiểm tra** mục I, II, III, IV | 4 mục *chờ kiểm* |
| ☐ | 4 | `thabok` | Bấm **Phiếu lĩnh nhiên liệu** và **Phiếu chi tạm ứng** | Hai phiếu có mã QR; không có số tiền |
| ☐ | 5 | `ketoan` | Mở đúng phiếu vừa lập → nhập **số phiếu quặng** → **Xác nhận kiểm tra** mục I, II | Cước tự điền theo bảng giá khách × tuyến; hai mục *đã kiểm*; Bãi hết sửa được |
| ☐ | 6 | `khonl` | Mục III → **Kiểm** → **Ghi sổ** | Đơn giá dầu tự lấy **giá bình quân kho Thà Bốc**, không ai gõ |
| ☐ | 7 | `khotb` | **Cấp phát** → quét / gõ mã phiếu lĩnh → **Cấp** 150 L | Khối đối chiếu có biển số, tài xế, số lít; tồn Thà Bốc giảm 150 |
| ☐ | 8 | `ketoancp` | Mục IV: bấm **Kiểm** khi còn giá 0 | Bị chặn, câu báo chỉ đúng dòng chưa có đơn giá |
| ☐ | 9 | `ketoancp` | Nhập giá (tiền ăn 120.000 LAK, tiền nước 60.000 LAK) → **Kiểm** → **Ghi sổ** | Mục IV *đã ghi sổ* |
| ☐ | 10 | `tx02` | Bấm **Xuất phát** khi quỹ **chưa** cấp tạm ứng | Bị chặn: *tài xế chưa nhận tiền thì chưa xuất phát* |
| ☐ | 11 | `quytb` | **Cấp phát** → cấp tạm ứng của phiếu; mục IV → **Xác nhận đã chi** | Tạm ứng *đã cấp*; có phiếu chi |
| ☐ | 12 | `quyvc` | Mục III → **Xác nhận đã chi** | Có phiếu chi |
| ☐ | 13 | `tx02` | **Xuất phát** → **Chia sẻ vị trí** → **Báo đã về** (ngày về, km về) | Theo dõi tuyến (bằng `thabok`) thấy chấm xe mới |
| ☐ | 14 | `thabok` | **Theo dõi tuyến** → chuyến đó → **Xe tới điểm** từng chặng | Mốc chặng sáng lên, diễn biến có dòng mới |
| ☐ | 15 | `thabok` | **Xe đã tới · nhập cân cuối** 40,6 t, gõ **Số POD** và **Người ký nhận** | Ngày về, km về điền sẵn từ tài xế; dòng hao hụt 0,4 t; khối POD hiện đúng số |
| ☐ | 16 | `ketoan` | **Khoá phiếu** → đọc bảng cảnh báo → tích xác nhận | Đã khoá; `thabok` mở lại thì không sửa được gì |
| ☐ | 17 | `doanhthu` | **Lập hóa đơn thu** → ghi thu **một phần** bằng LAK → ghi thu nốt phần còn lại | Lần một: *Thu một phần*. Lần hai: tự đổi **Đã thu đủ** |
| ☐ | 18 | `ketoan` | **Phiếu chi · Phiếu thu** → **Sổ chứng từ** → tìm số phiếu | Đủ: DO · PLNL · PTU · PXK_NL · phiếu chi · HD · PT; mỗi tờ đủ Nợ / Có |
| ☐ | 19 | `admin` | Mở **Tổng quan** ngay sau bước 17 | Doanh thu, chi phí tháng này **đã cộng** chuyến vừa làm, không phải chờ (xem thêm D8) |

Bước đẩy các tờ này sang sổ kế toán làm tiếp ở **Phần E**.

---

## C. Mỗi vai một phút

Mỗi dòng là chỗ **dễ sai nhất** của vai đó: quyền, tiền, hoặc bước bị chặn. Đăng nhập đúng vai rồi làm.

| ☐ | Vai | Thử | Phải thấy |
|---|---|---|---|
| ☐ | `thabok` | Nhìn thanh bên, mở **Tổng quan** | 17 màn, **không có** Hoá đơn, Xe liên kết, Tiền chuyến & nước, Tất toán, Bán hàng, Tỷ giá, Tài khoản. Tổng quan chỉ 3 ô số, **không có tiền** |
| ☐ | `thabok` | Bấm **Excel** ở Theo dõi phiếu, Kho nhiên liệu, Theo dõi NCC | Tệp mở được, **không có cột tiền nào** |
| ☐ | `thabok` | Phiếu E `T4-0445-09` → **Xuất phát** | Bị chặn vì chưa chi tạm ứng |
| ☐ | `thabok` | Gõ thẳng địa chỉ `#/hoa-don` | Tự chuyển sang màn khác, màn mới có nội dung |
| ☐ | `ketoan` | Bấm **Phiếu xuất xe** trên menu | **Không** tự mở tờ nào; chọn tờ thì mở đúng tờ đó |
| ☐ | `ketoan` | `T4-0429-08` (đã tới, chưa khoá) → **Khoá phiếu** | Bảng cảnh báo có dòng **Chưa có biên bản giao nhận hàng (POD)**; xác nhận thì vẫn khoá được |
| ☐ | `ketoan` | **Theo dõi phiếu**: cột Tiền và dòng tổng | `T4-0428` USD · `T4-0429` **CNY**; dòng tổng cộng **riêng từng tiền**, không dồn một số |
| ☐ | `ketoancp` | **Tất toán tài xế** → kỳ tháng 9 → bấm một tài xế | Bảng tóm tắt hiện trước; bấm vào mới hiện chi tiết *đã ứng · đã chi thật · chênh* (LAK) |
| ☐ | `khonl` | **Kho nhiên liệu** → chọn **từng kho** | Mỗi kho một **giá bình quân riêng**; để "Tất cả kho" thì ô giá ghi *Chọn một kho để xem* |
| ☐ | `quyvc` | Chi một mục **chưa ghi sổ** | Bị chặn *sai bước* |
| ☐ | `quytb` | **Cấp phát** → `PTU-T4-0445-09/EPL` → **Cấp** | *Đã cấp*; lúc này `thabok` bấm Xuất phát phiếu E được |
| ☐ | `doanhthu` | **Theo dõi NCC** → **Cấn trừ cuối tháng** 08/2026 → ຄຳຕຸ້ຍ → **Ghi cấn trừ** (8.761.050 LAK) → bấm lại lần nữa | Lần đầu ghi vào hoá đơn còn nợ `T4-0446-09`; lần hai **không ghi trùng** |
| ☐ | `khotb` | Menu; cấp một phiếu lĩnh của **kho Viêng Chăn** | Chỉ Cấp phát và Kho nhiên liệu; cấp kho khác bị chặn |
| ☐ | `khopt` | **Xuất cho xe** nhiều hơn tồn | Bị chặn |
| ☐ | `totsua` | **Lệnh sửa chữa** → lệnh của mình | **Không có** nút Kiểm / Ghi sổ / Đã chi |
| ☐ | `tx02` (điện thoại) | Đăng nhập; gõ thẳng `#/theo-doi` | Chỉ có **Phiếu của tôi**; gõ địa chỉ khác thì tự về Phiếu của tôi; không phải kéo ngang |
| ☐ | `tx01` | Tìm phiếu của `tx02` | Không thấy |
| ☐ | `admin` | Menu; **Mở khoá** một phiếu **đã có hoá đơn** | Đủ 27 màn; mở khoá bị chặn *đã hoá đơn* |

---

## D. Những chỗ mới đổi từ 25/09 (dữ liệu lớn)

Đợt 25/09 em đổi cách lấy dữ liệu để hệ thống chạy được khi có **nhiều năm phiếu** (đã thử 4 năm, 1,46 triệu phiếu: mọi
danh sách dưới nửa giây, báo cáo dưới 2 giây). Trên DB thật hiện chỉ có 15 phiếu nên **anh sẽ không thấy nhanh chậm khác
gì**. Phần này để chắc cách làm mới **không làm hỏng thao tác quen**: tìm vẫn ra, lọc vẫn đúng, số vẫn khớp.

| ☐ | # | Màn · việc | Phải thấy |
|---|---|---|---|
| ☐ | D1 | **Phiếu xuất xe** (vai kế toán): ô tìm cạnh ô chọn số phiếu, chữ mờ *Tìm số phiếu, xe, tài xế, khách hàng*. Gõ `0445` | Ô chọn chỉ còn `T4-0445-09/EPL`. Gõ biển xe, tên tài xế, tên khách cũng ra đúng phiếu |
| ☐ | D2 | Xoá chữ trong ô tìm | Ô chọn về lại danh sách phiếu mới nhất (tối đa 50; phiếu cũ hơn thì tìm) |
| ☐ | D3 | **Theo dõi phiếu vận chuyển** | 100 phiếu một trang, có nút **‹ Trang trước** · **Trang sau ›** và chữ *Trang 1/1*. Lọc tháng, trạng thái, ô tìm vẫn đúng |
| ☐ | D4 | Theo dõi phiếu → **Excel** | Xuất **mọi phiếu khớp bộ lọc**, không chỉ trang đang xem; dòng tổng khớp màn hình |
| ☐ | D5 | **Tổng quan** (`admin`): mở màn rồi **bấm Excel ngay** | Vẫn ra tệp (lỗi tìm thấy lúc UAT, đã sửa) |
| ☐ | D6 | **Theo dõi tuyến**: gõ ô tìm; bỏ tích **Chỉ phiếu chưa xong** | Lọc đúng; bỏ tích thì hiện cả chuyến đã xong. Bấm ô số trên đầu vẫn lọc được |
| ☐ | D7 | **Xe liên kết** · **Tiền chuyến & nước** · **Theo dõi NCC** · **Tất toán**: đổi tháng qua lại | Số hiện ngay. Xe liên kết **không còn** lựa chọn "tất cả các tháng", chọn từng tháng |
| ☐ | D8 | Sửa một con số có tiền (ví dụ ghi thêm một lần thu ở `doanhthu`), rồi mở lại **Tổng quan**, **Theo dõi phiếu** bằng `admin` | Số **đổi ngay** theo thay đổi. Báo cáo có lưu sẵn để mở nhanh, nhưng tự làm mới khi có ghi. **Không có chỗ nào hiện số cũ** |
| ☐ | D9 | **Phiếu của tôi** (tài xế) | Hiện mọi phiếu đang chạy và 15 phiếu gần nhất |
| ☐ | D10 | Các số đếm "tổng cộng" (danh sách tài xế, hợp đồng, Sổ chứng từ) | Số phiếu từng tài xế, từng hợp đồng đúng như trước; Sổ chứng từ báo *n tờ chưa đẩy · n lỗi* |

> Khi dữ liệu nhiều hơn 10.000 dòng khớp bộ lọc, chỗ đếm sẽ hiện **10.000+** thay vì đếm hết. Trên DB thật không gặp
> (mới 15 phiếu), nên không cần thử.

---

## E. Đẩy chứng từ và Sổ kế toán EPL_KETOAN (cổng 8030)

| ☐ | Vai | Làm | Phải thấy |
|---|---|---|---|
| ☐ | `admin` (8020) | **Phiếu chi · Phiếu thu** → **Sổ chứng từ** | Dòng trạng thái báo có tờ **chưa đẩy** (các tờ anh tạo ở Phần B, C) và 0 lỗi |
| ☐ | `admin` (8020) | Bấm **Đẩy hết tờ chưa đẩy** | Báo *n tờ xong, 0 lỗi*. Bấm lại thì không còn gì để đẩy |
| ☐ | `admin` (8030) | Đăng nhập Sổ kế toán | Menu **chia nhóm** |
| ☐ | `admin` (8030) | Nút **Cài đặt giao diện** → **Thanh bên** ↔ **Thanh trên**; tải lại trang | Đổi kiểu điều hướng giống EPL Lào; tải lại vẫn **nhớ** kiểu đã chọn |
| ☐ | `admin` (8030) | Mở **Thu chi** | Có dải báo *Phiếu thu, phiếu chi không lập ở đây: kế toán lập và duyệt trên EPL_LAO_REAL…*; các tờ mang nhãn **Tờ nhận từ EPL_LAO_REAL**; có nút **Ghi tay**. **Không có** nút lập phiếu thu / chi |
| ☐ | `admin` (8030) | **Sổ kế toán** → Nhật ký chung | Có bút toán của chuyến Phần B, nguồn *Đẩy từ EPL_LAO_REAL*, **không sửa được** |
| ☐ | `admin` (8030) | **Cân đối phát sinh** | **Nợ = Có** |
| ☐ | `admin` (8030) | **Công nợ** phải thu | Còn phải thu từng khách **bằng** màn Công nợ khách bên EPL Lào |
| ☐ | `ketoan` (8030) | **Ghi tay** → lập một bút toán → thử **tự duyệt** | Tự duyệt bị chặn |
| ☐ | `ketoantruong` (8030) | Duyệt bút toán đó; mở **Cài đặt** | Duyệt được, vào sổ. Cài đặt **không** thấy token, không sửa thông tin công ty |
| ☐ | `doanhthu` (8020) | Xoá **một lần thu đã đẩy** sang sổ | Bị chặn: tờ đã sang sổ thì không xoá được. Lần thu **chưa** đẩy thì xoá được |
| ☐ | mọi trang 8030 | **Xuất Excel** · **PDF** | Tệp `.xlsx` mở được, số là số; PDF khổ ngang |

---

## F. Giao diện chung

| ☐ | # | Việc | Phải thấy |
|---|---|---|---|
| ☐ | F1 | Nút ngôn ngữ → **ພາສາລາວ · English · Tiếng Việt · VI + ລາວ** trên 4–5 màn | Chữ đổi hết; **không** chỗ nào lòi mã (`nav_dash`, `undefined`, `NaN`); không câu nửa Việt nửa Lào |
| ☐ | F2 | **Ctrl + lăn chuột** 150%, rồi 80% | Cả trang co giãn theo, không vỡ khung, không phải kéo ngang |
| ☐ | F3 | Mọi hộp hỏi xác nhận (xoá, khoá, trả) | Hộp **trong ứng dụng**, không phải hộp "… says" của trình duyệt |
| ☐ | F4 | **Excel** ở 5 màn bất kỳ, mở bằng Microsoft Excel thật | Không báo lỗi; cột tiền là số, **đúng tiền tệ từng phiếu**, `=SUM` cộng được |
| ☐ | F5 | **Tắt Wi-Fi** ở máy `khotb` → Cấp phát → cấp một phiếu → bật mạng lại | Có dải báo mất mạng; dòng *chờ gửi*; có mạng lại thì tự gửi, máy chủ ghi *đã cấp* |
| ☐ | F6 | Điện thoại (tài xế): **Giao hàng hoàn tất · ký nhận** → ký bằng ngón tay → Gửi | Thẻ hiện *✓ Đã ký nhận*; `ketoan` mở phiếu thấy chữ ký ở khối POD |
| ☐ | F7 | Nhìn chung từng màn | Ghi lại **chỗ nào xấu, rối, khó hiểu** với người bên Lào (họ quen Excel năm 2016) |

---

## G. Test ổn rồi: nối API kế toán thu chi thật của anh Tune

Phần này làm **sau khi** Phần B–F không còn lỗi **Chặn** hay **Sai**. Anh Tune làm thay anh Khang (anh Khang nghỉ một
tuần). Ranh giới giữ nguyên: **sổ nằm bên anh Tune, bên mình chỉ đẩy chứng từ và xem**, không dựng sổ thứ hai.

### G1. Cần xin anh Tune

| ☐ | Cần | Vì sao |
|---|---|---|
| ☐ | **Địa chỉ API**, và nếu có thì một **môi trường thử** | Nên nối môi trường thử trước, đẩy vài tờ, đối chiếu xong mới sang sổ thật |
| ☐ | **Token** | Anh dán thẳng vào màn Cấu hình (vai Sếp), hoặc đưa em đặt vào tệp `.env`. **Đừng gửi token qua chat** |
| ☐ | Anh Tune đọc **`HOP_DONG_API_ANH_KHANG.docx`**: đường nhận chứng từ, gói tin gửi sang, cách trả về, các loại tờ | Bên anh Tune nhận đúng dạng đó thì bên mình **không phải sửa gì**. Khác dạng thì em viết lớp chuyển đổi, không đổi luồng |
| ☐ | **Các mã tài khoản còn chờ**: `1371`, `4021`, `4022` và mã giá vốn (ô `ma_gia_von`, mục 4 của tài liệu trên) | Có mã thì Sếp gõ vào Cấu hình, tờ sinh sau đó mang mã ngay |
| ☐ | Bên anh Tune có cho **đọc lại tờ đã nhận** không | Có thì em chạy được bộ kiểm hai đầu (mỗi tờ bên mình có đúng một tờ bên kia, khớp từng ô) |

### G2. Trước khi bấm nối — quyết dữ liệu

- 81 tờ hiện có là **dữ liệu mẫu**, đã đẩy sang sổ 8030. Chúng đã mang dấu *đã đẩy* nên **không tự sang** sổ anh Tune.
- Chỉ những tờ **lập sau lúc nối** mới sang sổ thật. Vì vậy phải **dọn hết phiếu test tay** (Phần H2) **trước** khi nối,
  kẻo phiếu thử của anh chạy vào sổ thật.
- 15 phiếu mẫu vẫn nằm trong `epl_lao`. Khi dùng thật cho khách Lào, có giữ 15 phiếu mẫu này hay không thì anh chốt.

### G3. Cách nối (em làm cùng anh)

1. Sao lưu hai DB.
2. Sếp → **Phiếu chi · Phiếu thu** → **Cấu hình**: địa chỉ sổ kế toán = địa chỉ của anh Tune, dán token → **Lưu**.
3. Lập **một** phiếu thử nhỏ, đi tới phiếu chi → **Đẩy hết tờ chưa đẩy** → hỏi anh Tune đã thấy tờ đó chưa, đúng Nợ / Có chưa.
4. Đúng thì dọn phiếu thử đó ở cả hai bên, rồi mới dùng thật. Sai thì trả Cấu hình về `http://127.0.0.1:8030`, em sửa.

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
| ☐ | Nhờ em **dọn dữ liệu thử**: em sao lưu hai DB → chạy xem trước `python tools/don_rac_bo_kiem.py` → xoá thật `python tools/don_rac_bo_kiem.py that`. Công cụ **giữ 15 phiếu mẫu**, xoá phiếu anh tạo thêm và dọn luôn bên sổ kế toán |
| ☐ | Cần quay lại đúng như sáng 28/09 thì em khôi phục từ bản sao lưu ở `D:\Demo_Lao\saoluu\` |
| ☐ | **Không** chạy `backend\app\seed.py --dung-lai` trên DB `epl_lao` |
| ☐ | Sửa xong lỗi anh ghi, em chạy lại toàn bộ bộ kiểm tự động (khoảng 30–40 phút, chạy từng nhóm cho anh thấy) |
