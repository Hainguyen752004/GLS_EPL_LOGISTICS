# Hướng dẫn tự thử EPL Lào theo từng vai

Viết cho người thử phần mềm (anh chủ dự án, hoặc người demo cho khách). Cập nhật 21/09/2026.

Phần mềm chia việc theo vai, và **việc của vai này mở khoá cho vai sau**. Nên cách thử đúng không phải
là mở từng màn xem cho vui, mà là **đi trọn một chuyến hàng**, đổi vai theo đúng thứ tự ngoài đời. Tài
liệu này là kịch bản đó, mỗi bước ghi rõ: *đăng nhập ai · vào màn nào · bấm gì · phải thấy gì*.

---

## 0. Chuẩn bị

```
cd D:\Demo_Lao\EPL_LAO_REAL
python backend\app\seed.py --dung-lai      # gieo lại dữ liệu mẫu cho sạch (xoá hết, gieo lại)
chay.bat                                    # hoặc: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8010 --no-access-log
```

Mở **http://localhost:8010**. Mật khẩu mọi tài khoản demo là `1234`.

**Đổi vai nhanh:** bấm tên người dùng ở góc trên phải → *Đăng xuất* → màn đăng nhập hiện sẵn 13 thẻ tài
khoản, **bấm một thẻ là vào thẳng**, khỏi gõ. Cả ngày thử chỉ làm động tác này.

Dữ liệu gieo sẵn có: 5 phiếu cũ (T4-0428 → T4-0432) và **một cặp phiếu của luồng mới**:
`G4-0101-09/EPL` (đi gom hàng, đã về bãi, hàng đã vào kho) và `T4-0433-09/EPL` (đi giao hàng, đã lấy
30 t của lô đó). Cặp này để anh xem ngay hình dạng luồng mới mà không phải nhập gì.

---

## 1. Kịch bản chính — một chuyến hàng trọn vẹn qua 8 vai

Làm hết mất khoảng 20 phút. Mỗi bước có ô ☐ để anh tick.

### Bước 1 ☐ Admin Thà Bốc lập **phiếu đi gom hàng** — `thabok`

1. Vào **Phiếu xuất xe** → bấm **+ Phiếu mới**.
2. Mục **I**: ô **Loại phiếu** chọn **Đi gom hàng (mỏ → bãi)**. Chọn xe, tài xế, ngày.
   - *Phải thấy:* ô **đơn giá, tiền tệ, thành tiền vẫn có** (anh Khampla 22/09: khách trả cước riêng cho chặng gom),
     và cột *Lấy từ lô* trong bảng hàng cũng ẩn.
3. Mục **II**: chọn khách, tuyến; ở **Hàng trên phiếu** bấm **+ Thêm dòng**, gõ mặt hàng và **số tấn cân
   tại mỏ** (ví dụ 40).
   - *Phải thấy:* ô **Cân tại mỏ** tự điền 40 theo tổng dòng hàng.
4. Mục **III–VI**: thêm vài dòng chi cho thật (dầu, cầu đường…). Bấm **Lưu**.
5. Bấm **Gửi kiểm tra** ở từng mục để đẩy sang kế toán.

> Đang thử cái gì: Bãi nhập được mọi thứ, nhưng **không thấy một con số bán hàng nào**.

### Bước 2 ☐ Xe về bãi — hàng vào kho — `thabok`

1. *(Tuỳ chọn, đúng cách ngoài đời)* đăng nhập tài xế của phiếu → **Phiếu của tôi** → **Báo đã về**, gõ ngày về và km về.
   Quay lại `thabok`: bấm **Xe đã tới · nhập cân cuối** → hai ô ngày về, km về **đã điền sẵn** số tài xế báo; chỉ còn gõ **cân tại bãi** (ví dụ 39,6).
2. *Phải thấy:*
   - Bảng hàng có thêm **một dòng hao hụt 0,4 t** (máy tự ghi, chữ nghiêng nền vàng).
   - Dòng hàng và hai ô cân **khoá lại**, kèm câu: *"Hàng đã vào kho bãi — dòng hàng và cân của phiếu này không sửa nữa."*
3. Vào **Kho hàng**: lô mới hiện ra, **nhập 39,6 t · còn 39,6 t**, sổ nhập xuất có một dòng vào.

> Đang thử cái gì: bãi Thà Bốc là bưu cục; đã ghi sổ kho thì không sửa lịch sử được nữa.

### Bước 3 ☐ Lập **phiếu đi giao hàng**, lấy hàng của lô đó — `thabok`

1. **Phiếu xuất xe** → **+ Phiếu mới** → Loại phiếu **Đi giao hàng (bãi → khách)**. **Chọn xe khác** với
   chuyến gom (để thấy hai chặng hai xe là bình thường).
2. Mục II: ở **Hàng trên phiếu** bấm **+ Thêm dòng** → cột **Lấy từ lô** giờ **hiện ra**, chọn
   `THU-GOM…` hoặc lô anh vừa tạo (ô chọn ghi rõ *còn bao nhiêu tấn*), gõ số tấn lấy (ví dụ 25). Bấm **Lưu**.
3. *Phải thấy:* **Cân lấy khỏi kho** = 25; vào **Kho hàng** thấy lô còn **14,6 t** và sổ có dòng ra.
4. Thử sai cho vui: sửa số tấn thành **100** rồi Lưu → **phải bị từ chối**: *"Lô … chỉ còn … tấn"*.

> Đang thử cái gì: dây nối hai phiếu, và máy không cho lấy quá tồn.

### Bước 4 ☐ Kế toán Thu/Chi kiểm mục I–II — `ketoan`

1. Vào **Phiếu xuất xe**, chọn phiếu giao vừa lập. Màn tự mở đúng **tab của vai** (mục I hoặc II).
2. Bấm **Xác nhận kiểm tra** ở mục I và mục II.
   - *Phải thấy:* giờ vai này **thấy đơn giá cước, thành tiền** — thứ mà Bãi không thấy. Nếu chuyến này
     khác hợp đồng, sửa được đơn giá ngay tại đây.
3. Thử **Trả lại sửa** một mục rồi kiểm lại, để thấy cơ chế mở khoá.

### Bước 5 ☐ Kế toán kho xăng dầu và Kế toán chi phí — `khonl`, `ketoancp`

1. `khonl` (KT kho xăng dầu): vào phiếu → mục **III** → **Xác nhận kiểm tra** → **Ghi sổ kế toán**.
   - *Phải thấy:* dầu lấy ở kho EPL thì **tồn kho nhiên liệu trừ ngay**, và **Sổ chứng từ** có tờ
     *Phiếu xuất kho nhiên liệu*.
   - *Phải thấy:* vai này chỉ có nút ở **mục III**, các mục khác chỉ đọc.
2. `ketoancp` (KT Chi phí): mục **IV, V, VI** → **Xác nhận kiểm tra** → **Ghi sổ kế toán**.

### Bước 6 ☐ Quỹ chi tiền — `quyvc` (dầu), `quytb` (đi đường, sửa chữa, khác)

1. `quyvc` (Thủ quỹ VC): mục **III** → **Xác nhận đã chi**.
2. `quytb` (Quỹ tiền mặt Thabok): mục **IV, V, VI** → **Xác nhận đã chi**.
   - *Phải thấy:* Sổ chứng từ sinh các tờ *Phiếu chi*.

### Bước 7 ☐ Giao hàng xong, khoá phiếu — `thabok` rồi `ketoan`

1. `thabok`: mở phiếu giao → **Xe đã tới · nhập cân cuối**, nhập cân ở cảng (ví dụ 24,7).
   - *Phải thấy:* thêm **dòng hao hụt 0,3 t** trên phiếu.
2. `ketoan`: mở phiếu → bấm **🔒 Khoá phiếu**.
   - *Phải thấy:* hộp cảnh báo liệt kê những chỗ cần nhìn (hao hụt vượt 1,5 %, thiếu phiếu quặng, km lệch…).
     Đọc rồi xác nhận thì mới khoá. Khoá xong **Bãi không sửa gì được nữa**.

### Bước 8 ☐ Hoá đơn và thu tiền — `doanhthu`

1. Vào phiếu → bấm **Lập hóa đơn thu**.
2. Bấm **Ghi một lần thu**. Hộp hiện ra có: ngày thu, **tiền tệ**, số tiền (điền sẵn phần còn thiếu),
   tỷ giá ngày thu, cách thu, số uỷ nhiệm chi.
   - **Thử đúng chỗ hay gặp ngoài đời:** hoá đơn ghi USD thì đổi ô tiền tệ sang **LAK** và gõ một số
     nhỏ hơn phần còn lại, ví dụ 20.000.000.
   - *Phải thấy:* dưới phiếu hiện **Sổ thu tiền** với một dòng; trạng thái phiếu là **Thu một phần**;
     dòng tiêu đề ghi rõ *Thành tiền · Đã thu · Còn lại*.
3. Bấm **Ghi một lần thu** lần nữa, để nguyên số còn lại.
   - *Phải thấy:* trạng thái tự đổi thành **Đã thu đủ** — không có nút "đánh dấu đã thu" nào cả, số
     tiền quyết định trạng thái.
   - *Phải thấy:* Sổ chứng từ có *Hoá đơn vận chuyển* và **hai** tờ *Phiếu thu tiền khách*, mỗi tờ
     mang đúng số tiền và tiền tệ khách trả.
4. Thử sai: ghi thu một số lớn hơn phần còn lại → **phải bị hỏi lại** rồi mới ghi.
5. Mở **phiếu gom** `G4-0101`: phiếu này cũng **có cước và lập được hoá đơn** (6 USD/t cho chặng gom) — theo trả lời của anh Khampla 22/09.

### Bước 8b ☐ Hoá đơn **gộp tháng** cho khách hợp đồng — `doanhthu`

Khách mẫu `ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ` để **gộp một tờ cuối tháng** (anh Khampla C8.2), nên hai phiếu tháng 9
của khách này **không có nút Lập hoá đơn** trên phiếu.

1. Mở một phiếu của khách đó (`T4-0440-09` hoặc `T4-0441-09`) bằng `doanhthu`.
   - *Phải thấy:* chỗ nút hoá đơn là nút **Gộp hoá đơn tháng** (nếu chưa gộp) hoặc nút **Thuộc hoá đơn
     HDT-202609-01** (đã gộp) — bấm là sang màn hoá đơn gộp.
2. Vào **Hoá đơn gộp tháng** (nhóm Vận chuyển), chọn tháng **2026-09**.
   - *Phải thấy:* tờ `HDT-202609-01` với **2 phiếu**, tiền bằng tổng doanh thu hai phiếu, đã thu 60 %.
3. Bấm **Xem** → khối chi tiết hiện *từng dòng phiếu* (tấn, đơn giá, thành tiền, đã thu, trạng thái) và
   *sổ thu tiền của tờ*.
   - *Phải thấy:* phiếu **cũ hơn** đã thu đủ, phiếu sau mới một phần — tiền được rải theo thứ tự ngày.
4. Bấm **Ghi một lần thu**, để nguyên số còn lại → cả hai phiếu đổi sang **Đã thu đủ**.
   - *Phải thấy:* Sổ chứng từ chỉ thêm **một** tờ *Phiếu thu tiền khách* cho cả tờ hoá đơn, không phải
     mỗi phiếu một tờ.
5. Thử sai: mở lại phiếu lẻ, bấm ghi thu ở đó → **phải bị chặn**, câu nhắc chỉ sang tờ hoá đơn gộp.
6. Muốn xem cách bật/tắt: `ketoan` vào **Khách hàng** → **Sửa** → ô **Cách xuất hoá đơn** có hai lựa chọn
   *Mỗi phiếu một hoá đơn* · *Gộp một tờ cuối tháng*; cột mới trên bảng cũng hiện cờ đó.
7. Tháng nào chưa gộp thì bảng **Chờ gộp** ở đầu màn liệt kê khách × loại tiền còn phiếu chờ — bấm
   **Gộp hoá đơn tháng** là ra một tờ mới.

### Bước 9 ☐ Xe liên kết: trả tiền chủ xe — `quytb` hoặc `quyvc`

Chủ xe mẫu `ທ້າວ ຄຳຫລ້າ` ký **trả gộp cuối tháng bằng Kíp**, nên trên dòng phiếu không có nút trả từng
phiếu — thay vào đó:

1. Vào **Xe liên kết** → bảng **Chủ xe liên kết** phía trên: thấy cột *Chờ trả* ghi số phiếu và tổng.
2. Bấm **Trả gộp** → hộp liệt kê các phiếu đã khoá chưa trả, tích sẵn; tổng tự cộng theo ô đang tích;
   chọn cách chi (tiền mặt / chuyển khoản), số uỷ nhiệm chi → **Trả chủ xe**.
3. *Phải thấy:* Sổ chứng từ có **một** tờ *Phiếu chi trả chủ xe liên kết* cho cả đợt; các phiếu trong đợt
   đổi sang *Đã trả chủ xe*; cột *Chờ trả* về 0.
4. `ketoan`: bấm **Sửa** trên chủ xe → đổi được **phí %/phiếu, ngưỡng tấn, mức trừ quá tải, cách trả**.
   Lập phiếu mới bằng xe của chủ đó thì ba ô phí trên phiếu tự điền theo — anh Khampla nói mỗi chủ xe
   một hợp đồng khác nhau (C4.2).
5. `thabok`: mở **Xe liên kết** → bảng Chủ xe **không có** cột phí và cột chờ trả (là tiền).

---

### Bước 9b ☐ Hai vai mới ở Thà Bốc và lệnh sửa chữa — `totsua`, `khopt`

Anh Khampla nói kho phụ tùng và tổ sửa chữa là **người riêng** (C1.2), nên hai việc đó đã rút khỏi Bãi.

1. `thabok`: mở một phiếu đang chạy → mục **V. Sửa chữa** không còn nút nhập; màn **Theo dõi tuyến** →
   tab Chi phí không còn nút *Báo sự cố / sửa xe*.
   - *Phải thấy:* Bãi vẫn ghi được diễn biến và báo sự cố (không kèm tiền).
2. `totsua` (tổ sửa chữa): đăng nhập → menu chỉ có Theo dõi tuyến · Phiếu xuất xe · Lệnh sửa chữa ·
   Kho phụ tùng · Xe.
   - Mở **Theo dõi tuyến** → chọn một chuyến → tab Chi phí → **Báo sự cố / sửa xe**, tích *có khoản sửa
     chữa*, chọn phụ tùng trong kho → lưu. *Phải thấy:* dòng vào mục V của phiếu, tồn kho giảm ngay.
   - Tài xế báo hỏng (`tx01` bấm **Báo hỏng**) thì nút **Duyệt** nằm ở `totsua`, không phải ở Bãi.
3. `khopt` (thủ kho phụ tùng): menu chỉ có Kho phụ tùng và Xe; chỉ người này nhập/xuất kho phụ tùng.
   *Thử sai:* `thabok` mở Kho phụ tùng → không còn nút Thêm / Nhập kho / Xuất cho xe.
4. **Lệnh sửa chữa riêng** (C7.3) — `totsua` mở **Lệnh sửa chữa** (nhóm Kho):
   - Thấy sẵn `LSC-2609-01` của xe 342 (bảo dưỡng 10.000 km) đang chờ kiểm.
   - Bấm **+ Lệnh sửa chữa** → chọn xe, loại *Bảo dưỡng định kỳ*, số km → lưu → hộp **Thêm dòng chi**
     hiện ra ngay: chọn *Lấy từ kho* hoặc *Mua ngoài*.
   - *Phải thấy:* dòng lấy kho trừ tồn ngay và có phiếu xuất kho riêng; dòng mua ngoài chờ quỹ chi.
   - `ketoancp` bấm **Kiểm** rồi **Ghi sổ**; `quytb` bấm **Đã chi**. *Phải thấy:* Sổ chứng từ có **một**
     tờ *Phiếu chi sửa chữa* chỉ gồm phần **mua ngoài**, và xe quay về *Rảnh*.
5. Mở **Xe** → chọn xe đó → tab **Sửa chữa**: thấy cả dòng từ phiếu lẫn dòng từ lệnh sửa chữa.

### Bước 9c ☐ Đổi xe giữa đường — `thabok`

1. Mở một phiếu **chưa tới nơi** → bấm **Đổi xe**.
2. Chọn xe mới, có thể đổi luôn tài xế, **ghi lý do** (bắt buộc), chọn xe cũ *Vào xưởng sửa*.
   - *Phải thấy:* phiếu mang biển số xe mới; tab Diễn biến có dòng *Đổi xe 341 → 342 · lý do*;
     **mục I quay về "đã nhập"** để kế toán kiểm lại; danh mục Xe: xe cũ *Sửa chữa*, xe mới *Đang chạy*.
   - *Phải thấy:* các dòng chi đã khai của chuyến **còn nguyên** — không phải lập phiếu mới.
3. Thử sai: bấm **Đổi xe** trên phiếu đã tới nơi → không có nút; gọi thẳng API thì bị từ chối.

### Bước 9d ☐ Thẻ cao tốc — `ketoan`, `quytb`, `thabok`

1. `ketoan` mở **Thẻ cao tốc** (nhóm Danh mục): thấy sẵn hai thẻ — `ETC-8801` của khách ຄຳຕຸ້ຍ (khách
   cấp thẻ) và `ETC-9902` của EPL gắn xe 342, mỗi thẻ đã nạp sẵn tiền.
2. `quytb` bấm **Xem** một thẻ → **Nạp tiền**: ghi ngày, số tiền, số biên lai. *Phải thấy:* số dư tăng
   và có một dòng *Nạp tiền* kèm **số dư sau**.
3. `thabok` mở một phiếu chưa kiểm → mục **IV**: dòng *Phí cầu đường* (hoặc *Phí cầu*) có thêm ô chọn
   **thẻ** ngay dưới tên khoản; chọn thẻ rồi lưu.
   - *Phải thấy:* số dư thẻ **chưa đổi** — thẻ chỉ bị trừ khi kế toán ghi sổ.
4. `ketoancp` kiểm rồi **Ghi sổ** mục IV. *Phải thấy:* số dư thẻ giảm đúng số tiền dòng đó, và trong sổ
   thẻ có dòng *Qua trạm* nhắc đúng số phiếu. Ghi sổ mục khác không trừ thêm lần nữa.
5. Thử sai: `ketoan` bấm **Điều chỉnh số dư** mà bỏ trống lý do → bị từ chối.
6. `ketoan` xem bảng **Cấn trừ cuối tháng** ở cuối màn: khách cấp thẻ hiện số đã tiêu trong tháng —
   đó là số trừ vào cước của khách.

### Bước 9e ☐ Nợ trạm dầu Việt Nam — `thabok`, `ketoancp`

1. `thabok` mở phiếu → mục **III**, thêm một dòng dầu, chọn **Nơi đổ** là trạm bên Việt Nam.
   - *Phải thấy:* dưới ô Nơi đổ hiện ô tích **Ghi nợ tại trạm** (chỉ hiện với trạm ngoài, không hiện
     với kho của mình).
   - Tích ô đó = trạm ghi sổ, EPL trả sau. Không tích = tài xế trả tiền mặt ngay tại trạm.
2. `ketoancp` mở **Theo dõi nhà cung cấp**: trạm dầu Việt Nam có cột **Ghi nợ tại trạm** — chỉ cộng
   những dòng đã tích, không cộng dòng tài xế trả tiền mặt.
3. `ketoancp` bấm **Sửa** trạm dầu → ô **Cấn trừ vào cước khách**: chọn khách đứng ra với trạm.
4. Xem bảng **Cấn trừ cuối tháng** ở màn đó: từng khách có *Cước phải thu* · *Khách trả hộ qua thẻ* ·
   *Nợ trạm dầu Việt Nam* · **Còn phải thu**.
5. `thabok` mở cùng màn: **không thấy** cột cấn trừ và không thấy bảng cấn trừ (đó là tiền bán).

### Bước 9f ☐ Ảnh xe và hai chỗ đã dọn — `thabok`, `doanhthu`

1. `thabok` mở **Xe** → bấm đúp một xe để mở hộp hồ sơ → góc trên trái có khung ảnh và nút **+ Thêm ảnh**.
   - Chọn một ảnh từ máy. *Phải thấy:* khung ảnh hiện ngay ảnh vừa chọn, dòng dưới đổi thành *1 ảnh đã lưu*,
     và khi đóng hộp thì danh sách xe cũng hiện ảnh đó ở thẻ hồ sơ bên phải.
   - Ảnh đầu tiên tự thành **ảnh đại diện**, không phải bấm thêm nút nào.
2. `doanhthu` mở **Tổng quan**: ô **Việc của tôi** không còn là 0 — nó đếm *phiếu đã khoá chưa xuất hoá
   đơn* cộng *hoá đơn chưa thu đủ*; bấm vào mở thẳng phiếu đầu tiên đang chờ.
3. Thử chỗ đã dọn về tiền bán (không cần công cụ nào, chỉ cần nhìn): `thabok` mở **Theo dõi phiếu vận
   chuyển** — các cột cước, thành tiền, lãi không có; nay **máy chủ cũng không gửi** những con số đó nữa,
   nên mở công cụ trình duyệt cũng không đọc được. `ketoan` mở cùng màn thì vẫn thấy đủ.

---

## 2. Các vai còn lại

### ☐ Tài xế — `tx01`, `tx02`, `tx03` (thử bằng điện thoại càng tốt)

Chỉ thấy đúng một màn **Phiếu của tôi**:
- **Phiếu chi tạm ứng** → hiện mã QR để ra quỹ lấy tiền. **Chưa nhận tiền thì nút *Xuất phát* không bấm được** — đúng thứ tự thật.
- **Xuất phát** · **Báo hỏng / sự cố** · **Khai đổ nhiên liệu** (đổ dọc đường bên Việt Nam) · **Chia sẻ vị trí** (GPS).

### ☐ Thủ kho nhiên liệu — `khotb` (Thà Bốc), `khovc` (Viêng Chăn)

Chỉ thấy **Cấp phát** và **Kho nhiên liệu**:
- Danh sách phiếu lĩnh đang chờ → bấm **Cấp dầu**, nhập **số lít thật**. Lệch nhiều so với phiếu thì
  **bắt ghi lý do**.
- *Phải thấy:* tồn kho trừ ngay, sinh *Phiếu xuất kho nhiên liệu*.
- Thử mất mạng: tắt Wi-Fi rồi bấm cấp → phần mềm **xếp hàng đợi**, có mạng lại thì tự gửi.

### ☐ Sếp — `admin`

Thấy hết 23 màn. Hai việc riêng của Sếp:
- **Mở khoá phiếu** đã khoá (vai khác không có).
- **Chứng từ → Sổ chứng từ → Cấu hình**: đặt địa chỉ API và token kế toán của anh Khang.

---

## 3. Thử phân quyền — 8 chỗ phải bị chặn

Đây là phần khách hay hỏi nhất. Đăng nhập đúng vai rồi thử làm việc của người khác:

| ☐ | Đăng nhập | Thử làm | Phải thấy |
|---|---|---|---|
| ☐ | `thabok` | Tìm màn **Tài khoản**, **Hoá đơn**, **Xe liên kết** | Không có trong thanh điều hướng |
| ☐ | `thabok` | Vào **Khách hàng** tìm nút **Bảng giá** | Không có (giá là tiền bán) |
| ☐ | `thabok` | Mở phiếu, mục II, gõ vào **Số phiếu quặng** | Ô khoá, dưới có dòng *Kế toán nhập khi nhận giấy · Bãi đính kèm ảnh* |
| ☐ | `ketoan` | Cùng phiếu, gõ **Số phiếu quặng** rồi Lưu | Lưu được |
| ☐ | *(máy chưa chọn ngôn ngữ)* | Đăng nhập `thabok` lần đầu | Giao diện tự sang **tiếng Lào**; đăng nhập `ketoan` thì vẫn tiếng Việt |
| ☐ | `thabok` | Mở **Tổng quan** | Bốn ô là *Phiếu tháng này · Tổng chi phí · Khối lượng · Xe đang trên đường* — **không có doanh thu** |
| ☐ | `thabok` | Mở **Theo dõi phiếu** | Không có cột Cước, Thành tiền, Lãi; **vẫn có** các cột chi phí |
| ☐ | `khonl` | Mở phiếu, tìm nút ở mục IV | Chỉ mục III có nút; mục khác chỉ đọc |
| ☐ | `quytb` | Bấm **Xác nhận đã chi** ở mục chưa ghi sổ | Bị từ chối: *"sai bước"* |
| ☐ | `ketoan` | Vào **Chứng từ → Sổ chứng từ**, tìm nút **Cấu hình** | Không có (chỉ Sếp) |
| ☐ | `tx01` | Gõ thẳng địa chỉ `#/tai-khoan` | Tự chuyển về màn của tài xế, không vào được |

---

## 4. Thử kho hàng và điều chỉnh — `ketoan`

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | **Kho hàng** → bấm một dòng lô | Mở đúng phiếu gom đã mang lô đó về |
| ☐ | Bấm **Điều chỉnh tồn** trên một lô, nhập `-0.5` và lý do | Tồn giảm 0,5; sổ có dòng *Điều chỉnh* kèm lý do; Sổ chứng từ có tờ *Phiếu điều chỉnh kho hàng* |
| ☐ | Điều chỉnh **không ghi lý do** | Bị từ chối |
| ☐ | Điều chỉnh giảm **quá tồn** (ví dụ −999) | Bị từ chối: *hàng đã xuất cho phiếu giao* |
| ☐ | Đăng nhập `thabok` xem **Kho hàng** | Thấy tồn nhưng **không có nút Điều chỉnh** |

---

## 4b. Thử nhiều tiền tệ

Bên Lào nhận cước bằng USD, Kíp, Nhân dân tệ và Bath Thái. Dữ liệu mẫu đã có sẵn ba loại tiền để anh
xem ngay, không phải nhập gì.

| ☐ | Đăng nhập | Việc | Phải thấy |
|---|---|---|---|
| ☐ | `ketoan` | Mở **Theo dõi phiếu vận chuyển** | Có cột **Tiền**: `T4-0428` là USD · `T4-0429` là **CNY** · `T4-0432` là **LAK** |
| ☐ | `ketoan` | Nhìn dòng tổng cuối bảng | Cộng **riêng từng loại tiền**, mỗi loại một dòng — không dồn thành một con số |
| ☐ | `ketoan` | Đổi ô **Quy đổi** sang `LAK` rồi `USD` | Cả bảng về một tiền, dòng tổng còn một con số |
| ☐ | `ketoan` | Mở phiếu `T4-0429`, mục II | Ô **Tiền tệ cước** là CNY; *Thành tiền* ghi kèm `CNY`; ô dưới ghi số đã quy ra Kíp |
| ☐ | `ketoan` | Mở phiếu `T4-0430` (xe liên kết) | Bán bằng **USD** mà thuê xe trả bằng **LAK**: bảng thanh toán chủ xe ghi Kíp, bảng lãi ghi USD |
| ☐ | `ketoan` | Mở phiếu mới, chọn khách `ນາງ ວັນນາ` tuyến `ກາສີ → ທ່າເຮືອກະລໍ` | Ô **Cách tính cước** tự thành *Khoán trọn chuyến*, giá 1.800 USD; thành tiền = 1.800 dù cân bao nhiêu tấn |
| ☐ | `doanhthu` | Mở phiếu `T4-0431` (đã thu đủ) | **Sổ thu tiền** có một dòng: hoá đơn USD nhưng khách chuyển bằng Kíp |
| ☐ | `admin` | Mở **Tổng quan** | Bốn ô số là **M LAK**; dòng nhỏ dưới ô Doanh thu chia ra `USD … · CNY … · LAK …` |
| ☐ | `ketoan` | Vào **Khách hàng → Bảng giá** | Mỗi dòng giá có cột **Tiền**; thêm dòng mới thì chọn được tiền tệ |
| ☐ | `thabok` | Mở **Tổng quan** và **Theo dõi phiếu** | Vẫn **không** thấy cột Tiền của phần bán, không thấy doanh thu — quy tắc ẩn tiền bán không đổi |

### Màn Tỷ giá — `#/ty-gia`, nhóm Danh mục

| ☐ | Đăng nhập | Việc | Phải thấy |
|---|---|---|---|
| ☐ | `ketoan` | Mở **Tỷ giá** | Bốn thẻ USD · THB · VND · CNY, mỗi thẻ ghi *1 … sang Kíp*, kèm số đang áp dụng và người đặt |
| ☐ | `ketoan` | Gõ 1 USD = **30.000** nhưng **chưa bấm Lưu**, nhìn máy tính quy đổi bên dưới | Con số đổi theo ngay — thử trước rồi mới chốt |
| ☐ | `ketoan` | Bấm **Bỏ thay đổi** | Ô quay về số cũ |
| ☐ | `ketoan` | Gõ số mới rồi **Lưu tỷ giá mới**, điền ngày áp dụng và ghi chú | Thẻ hiện *Lần trước* và mức thay đổi; bảng **Lịch sử** có thêm một dòng giữ cả số cũ |
| ☐ | `ketoan` | Bấm Lưu lần nữa mà **không đổi gì** | Báo "Chưa đổi ô nào" — không đẻ dòng lịch sử rỗng |
| ☐ | `ketoan` | Mở lại một **phiếu cũ** (ví dụ `T4-0428`) | Số tiền **không đổi** theo tỷ giá mới — phiếu khoá tỷ giá riêng của nó |
| ☐ | `thabok` | Tìm màn **Tỷ giá** trong thanh điều hướng | **Không có** — Bãi không đặt tỷ giá |
| ☐ | `quytb` | Mở **Tỷ giá** | Xem được nhưng **không có** nút Lưu |
| ☐ | `ketoan` | Nhớ trả tỷ giá về số cũ sau khi thử | |

---

## 4c. Thử màn Xe và màn Tài xế

Hai màn danh mục này dựng theo bản thiết kế anh gửi: danh sách bên dưới, bấm một dòng thì **thẻ xem
nhanh trượt ra từ mép phải**, bấm đúp (hoặc bấm *Mở hồ sơ*) thì mở hộp hồ sơ đầy đủ có tab.

| ☐ | Đăng nhập | Việc | Phải thấy |
|---|---|---|---|
| ☐ | `ketoan` | **Xe** → bấm một dòng | Thẻ trượt ra từ mép phải, nền sau mờ đi |
| ☐ | `ketoan` | Bấm nút **×**, rồi bấm nền mờ, rồi bấm phím **Esc** | Cả ba cách đều đóng được thẻ |
| ☐ | `ketoan` | Bấm đúp một dòng | Hộp hồ sơ bảy tab; thẻ trượt tự thu lại, không chồng hai lớp |
| ☐ | `ketoan` | **Tài xế** → nhìn cột **Kết luận** | Ba mức khác nhau trên ba tài xế mẫu: *Đủ điều kiện* · *Sắp hết hạn* · *Hết hạn* |
| ☐ | `ketoan` | Bấm chip **Hết hạn / không hiệu lực** | Danh sách lọc còn đúng người bằng lái đã hết hạn |
| ☐ | `ketoan` | Mở thẻ người bằng hết hạn | Khối *cửa chặn* màu đỏ ghi rõ "Điều phối sẽ chặn"; nút **Tạo phiếu xuất** bị khoá |
| ☐ | `ketoan` | Mở hồ sơ → tab **Bằng lái & gia hạn** → **+ Gia hạn** | Ghi bằng mới xong: cột Kết luận đổi sang xanh, bảng lịch sử có thêm dòng, bằng cũ đánh *Bằng cũ* |
| ☐ | `ketoan` | Tab **Lịch tuần** | Bảy ô ngày, ngày nào có chuyến hiện số phiếu và tuyến |
| ☐ | `khonl` | Mở **Tài xế**, mở hồ sơ một người | Xem được nhưng **không có** nút Lưu, các ô đều khoá |
| ☐ | `tx01` | Tìm màn **Tài xế** | Không có — tài xế chỉ thấy *Phiếu của tôi* |

---

## 5. Thử nối kế toán (chưa có API anh Khang vẫn thử được)

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | `ketoan` → **Chứng từ → Sổ chứng từ** | Thanh *Kết nối kế toán* ghi **chưa đặt địa chỉ API**, và số tờ chưa đối chiếu |
| ☐ | `admin` → bấm **Cấu hình**, để trống rồi Lưu | Vẫn báo chưa nối — không có địa chỉ thì không đẩy được |
| ☐ | Bấm **Đã đối chiếu ✓** trên một tờ | Tờ chuyển trạng thái (đánh dấu tay, dùng khi chưa có API) |

Khi anh Khang cho địa chỉ thật: `admin` → **Cấu hình** → dán địa chỉ + token → nút **Đẩy hết tờ chưa
đẩy** hiện ra. Tờ nào bên kia từ chối sẽ hiện **câu lỗi của họ ngay trên dòng**.

---

## 6. Thử những thứ chung

| ☐ | Việc | Phải thấy |
|---|---|---|
| ☐ | Bấm nút **ngôn ngữ** góc trên phải, đổi qua **ພາສາລາວ**, **English**, **VI + ລາວ** | Mọi chữ đổi theo, không chỗ nào lòi mã kiểu `nav_dash` |
| ☐ | Nhấn **Ctrl** và lăn chuột để phóng to / thu nhỏ trình duyệt | Cả trang co giãn theo, không vỡ khung, không phải kéo ngang |
| ☐ | Bấm tên người dùng → **Cài đặt giao diện** → đổi **thanh bên ↔ thanh trên** | Đổi kiểu điều hướng, máy nhớ theo máy |
| ☐ | **Theo dõi tuyến** → bấm một chuyến | Thanh xem nhanh trượt ra, bản đồ co lại vừa khít, không méo |
| ☐ | Bấm **In** ở phiếu hoặc hoá đơn | Bản in sạch: không có thanh công cụ, không có nút |
| ☐ | Tắt Wi-Fi rồi chuyển vài màn | Vẫn xem được màn đã mở; màn Cấp phát xếp hàng đợi việc |

---

## 7. Nếu muốn làm lại từ đầu

```
python backend\app\seed.py --dung-lai
```

Xoá sạch và gieo lại đúng bộ dữ liệu mẫu ban đầu. Chạy bất cứ lúc nào, không sợ hỏng gì.

Muốn chắc chắn máy vẫn đúng sau khi nghịch, chạy bộ kiểm (cần máy chủ đang bật):

```
python kiem\thu_hai_do.py          python kiem\thu_luong_api.py
python kiem\thu_tien_te.py        python kiem\thu_ban_hang.py
python kiem\thu_ty_gia.py         node   kiem\ra_tai_xe.js
python kiem\thu_phieu_linh.py      python kiem\thu_day_ke_toan.py
node   kiem\thu_giao_dien.js       node kiem\ra_vai.js
```

`ra_vai.js` đăng nhập lần lượt **cả 13 tài khoản**, mở mọi màn của từng vai và báo cáo chỗ nào lỗi —
chạy cái này là biết ngay có gì hỏng, nhanh hơn bấm tay.
