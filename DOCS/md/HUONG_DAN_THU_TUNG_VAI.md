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
   - *Phải thấy:* toàn bộ phần **đơn giá cước, thành tiền, quy đổi biến mất** (phiếu gom không có cước),
     và cột *Lấy từ lô* trong bảng hàng cũng ẩn.
3. Mục **II**: chọn khách, tuyến; ở **Hàng trên phiếu** bấm **+ Thêm dòng**, gõ mặt hàng và **số tấn cân
   tại mỏ** (ví dụ 40).
   - *Phải thấy:* ô **Cân tại mỏ** tự điền 40 theo tổng dòng hàng.
4. Mục **III–VI**: thêm vài dòng chi cho thật (dầu, cầu đường…). Bấm **Lưu**.
5. Bấm **Gửi kiểm tra** ở từng mục để đẩy sang kế toán.

> Đang thử cái gì: Bãi nhập được mọi thứ, nhưng **không thấy một con số bán hàng nào**.

### Bước 2 ☐ Xe về bãi — hàng vào kho — `thabok`

1. Vẫn ở phiếu đó, dưới cùng bấm **Xe đã tới · nhập cân cuối**, nhập **cân tại bãi** (ví dụ 39,6), km về, ngày về.
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
5. Thử sai: mở **phiếu gom** rồi tìm nút hoá đơn → **không có**; gọi thẳng API cũng bị từ chối
   (*"Phiếu đi gom hàng không có cước"*).

### Bước 9 ☐ Xe liên kết: trả tiền chủ xe — `quytb` hoặc `quyvc`

Mở một phiếu **xe thuê ngoài đã khoá** (ví dụ `T4-0430-08/EPL`) → bấm **Trả chủ xe · … USD**.
*Phải thấy:* hộp tính rõ *tiền thuê − phí 2 % − quá tải − các khoản EPL đã ứng*; xong sinh tờ
*Phiếu chi trả chủ xe liên kết*.

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
| ☐ | `doanhthu` | Mở phiếu `T4-0431` (đã thu đủ) | **Sổ thu tiền** có một dòng: hoá đơn USD nhưng khách chuyển bằng Kíp |
| ☐ | `admin` | Mở **Tổng quan** | Bốn ô số là **M LAK**; dòng nhỏ dưới ô Doanh thu chia ra `USD … · CNY … · LAK …` |
| ☐ | `ketoan` | Vào **Khách hàng → Bảng giá** | Mỗi dòng giá có cột **Tiền**; thêm dòng mới thì chọn được tiền tệ |
| ☐ | `thabok` | Mở **Tổng quan** và **Theo dõi phiếu** | Vẫn **không** thấy cột Tiền của phần bán, không thấy doanh thu — quy tắc ẩn tiền bán không đổi |

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
python kiem\thu_phieu_linh.py      python kiem\thu_day_ke_toan.py
node   kiem\thu_giao_dien.js       node kiem\ra_vai.js
```

`ra_vai.js` đăng nhập lần lượt **cả 13 tài khoản**, mở mọi màn của từng vai và báo cáo chỗ nào lỗi —
chạy cái này là biết ngay có gì hỏng, nhanh hơn bấm tay.
