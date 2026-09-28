# Luồng nghiệp vụ EPL Lào từ A đến Z — trang điều xe và trang kế toán

Viết cho anh (chủ dự án), cập nhật **28/09/2026**, sau khi làm xong đợt 6: kho, lệnh sửa chữa và bán hàng đã dời sang trang kế toán. Tài liệu đi từ lúc Bãi lập **phiếu gom** ở mỏ cho tới lúc mọi tờ chứng từ của chuyến đã **vào sổ kế toán**. Mỗi bước ghi rõ: **ai làm**, làm ở **trang nào**, **màn nào**, **bấm nút nào** (đúng chữ trên nút), máy tự làm gì, máy chặn gì, sinh ra tờ gì, và **ai làm tiếp**.

**Cách đọc:** Phần 1–3 là bức tranh chung và cách đi lại giữa hai trang, đọc một lần. Phần 4 là luồng chính một chuyến, đi từng bước, chính là phần anh sẽ bấm theo khi test tay. Phần 5–9 là bảng tra cứu: ai làm tiếp, việc ngoài chuyến, danh mục chứng từ, khi mất nối, và những gì đã dời.

**Quy ước chữ trong tài liệu:** tên nút và ô viết **đậm** đúng như trên màn hình (bản tiếng Việt). Đường đi viết dạng Menu → Màn → Nút. Mật khẩu mọi tài khoản demo là `1234`.

## Mục lục

- **1.** Bức tranh chung: hai trang, mỗi trang giữ gì
- **2.** Tài khoản và đăng nhập
- **3.** Đi lại giữa hai trang: nút bấm, máy tự gọi, cài đặt nối, khi một trang tắt
- **4.** Luồng chính A → Z: phiếu GOM mỏ → bãi, phiếu GIAO bãi → cảng, rồi tới sổ kế toán
- **5.** Bảng "ai làm tiếp"
- **6.** Việc ngoài chuyến: kho, lệnh sửa chữa, bán hàng, thẻ cao tốc
- **7.** Danh mục chứng từ: sinh lúc nào, ở trang nào, về sổ bằng đường nào
- **8.** Khi mất mạng hoặc một trang tắt
- **9.** Đã dời những gì sang trang kế toán, và đợt 7 sẽ dời gì

## 1. Bức tranh chung

### 1.1. Hai trang web

EPL Lào chạy trên **hai trang web riêng**, hai cơ sở dữ liệu riêng, nói chuyện với nhau qua đường liên thông có khoá:

| Trang | Tên trong mã | Máy của anh | Giữ những gì |
|---|---|---|---|
| **Trang điều xe** | EPL_LAO_REAL · DB `epl_lao` | cổng **8020** | Việc của **chuyến xe**: Tổng quan, Theo dõi phiếu vận chuyển, Theo dõi tuyến, **Phiếu xuất xe**, Phiếu của tôi (tài xế), danh mục Xe · Tài xế · Tuyến đường · Khách hàng · Thẻ cao tốc · Tỷ giá, Quy trình, Tài khoản. Màn **Phiếu chi · Phiếu thu** còn in phiếu chi tạm ứng, phiếu lĩnh và giữ sổ chứng từ của phiếu. Màn **Xe liên kết** chỉ còn danh mục chủ xe (điều khoản) và hợp đồng thuê xe. **Tạm thời vẫn giữ các màn tiền** Tiền chuyến & tiền nước tài xế, Tất toán tài xế, Theo dõi nhà cung cấp cho tới các phần sau của đợt 7 |
| **Trang kế toán** | EPL_KETOAN · DB `epl_ketoan` | cổng **8030** | Nhóm **Kho** (Kho hàng, Cấp phát, Kho nhiên liệu, Điểm đổ nhiên liệu, Kho phụ tùng, Lệnh sửa chữa, Bán hàng), nhóm **Tiền vận chuyển** (Hóa đơn vận chuyển, Hoá đơn gộp tháng — từ đợt 7a; Xe liên kết — trả chủ xe, từ đợt 7b) và **Sổ kế toán** (nhận chứng từ, Kế toán, Ghi tay, Thu chi, Công nợ, Quỹ & TK, Chuyến xe, Kho, Báo cáo, Cài đặt) |

Nguyên tắc anh chốt ngày 28/09: **trang điều xe không xem được kho**. Kho và (từ đợt 7) tiền nằm ở trang kế toán. Riêng việc **kiểm và duyệt từng mục trên phiếu xuất xe vẫn làm ngay trên phiếu** ở trang điều xe, vì phiếu là DO đang mở của chuyến.

### 1.2. Một chuyến đi qua những ai

Tóm tắt một chuyến trọn luồng (chi tiết từng bước ở Phần 4):

1. **Admin Thà Bốc** lập phiếu xuất xe (gom hoặc giao), ghi dầu, tiền đi đường, in phiếu lĩnh dầu và phiếu tạm ứng, gửi kiểm.
2. **Kế toán Viêng Chăn** kiểm từng mục và nhập giá: KT Thu/Chi kiểm mục I–II, KT kho xăng dầu mục III, KT Chi phí mục IV–VI.
3. **Thủ kho** cấp dầu theo phiếu lĩnh; **quỹ** chi tiền tạm ứng cho tài xế (cả hai ở màn **Cấp phát** trang kế toán).
4. **Tài xế** xuất phát, báo mốc, đổ dầu dọc đường, báo hỏng, giao hàng và ký nhận trên điện thoại.
5. **Admin Thà Bốc** báo xe tới, nhập cân cuối. Phiếu gom thì hàng vào **kho bãi**; phiếu giao thì hàng ra khỏi kho bãi.
6. **KT Thu/Chi** kiểm lại toàn phiếu rồi **khoá**.
7. **KT Doanh thu** lập hoá đơn, ghi thu tiền khách (ở **trang kế toán**). **Quỹ** trả chủ xe liên kết (cũng ở **trang kế toán**). **KT Chi phí** tất toán tài xế.
8. **KT Thu/Chi** đẩy chứng từ sang sổ; **trang kế toán** nhận tờ và tự ghi bút toán. **Kế toán trưởng** duyệt bút toán ghi tay nếu có.

### 1.3. Tờ chứng từ về sổ bằng hai đường

- **Đường 1 — tờ sinh ở trang điều xe** (DO, phiếu lĩnh, tạm ứng, phiếu chi mục IV–VI, tất toán…): nằm ở màn **Phiếu chi · Phiếu thu** với trạng thái *chưa đẩy*, tới khi KT Thu/Chi bấm **Đẩy hết tờ chưa đẩy**. Sổ nhận tờ nào thì tự sinh bút toán tờ đó.
- **Đường 2 — tờ sinh ngay ở trang kế toán** (mọi tờ kho: nhập / xuất / chuyển dầu, phụ tùng, kho hàng; tờ của lệnh sửa chữa và bán hàng; từ đợt 7a cả **hoá đơn HD** và **phiếu thu tiền khách PT**, từ đợt 7b **phiếu chi trả chủ xe PC_CX**): vào sổ **ngay lúc làm việc**, không cần đẩy. Trong sổ, các bút toán này mang nguồn *Sinh ở kho (trang kế toán)* hoặc *Sinh ở tiền vận chuyển (trang kế toán)*.

## 2. Tài khoản và đăng nhập

Hai trang dùng **cùng tên đăng nhập và cùng mật khẩu**, nhưng **đăng nhập riêng từng trang**: vào trang điều xe không tự đăng nhập trang kế toán. Mẹo khi làm: mở trang điều xe ở một tab, trang kế toán ở tab bên cạnh. Muốn làm hai vai cùng lúc thì mở thêm một **cửa sổ ẩn danh** (Ctrl+Shift+N), mỗi cửa sổ một người.

| Tên đăng nhập | Vai | Ở trang điều xe làm gì | Ở trang kế toán làm gì |
|---|---|---|---|
| `admin` | Sếp | Mọi việc, cấu hình, tài khoản, mở khoá mục | Mọi việc, cấu hình liên thông, duyệt |
| `thabok` | Admin Thà Bốc | Lập phiếu, dầu, đi đường, gửi kiểm, báo mốc, báo tới, đổi xe | Kho hàng (xem), Cấp phát (xem), Kho nhiên liệu (xem lít, không thấy giá), Điểm đổ (sửa), Kho phụ tùng (xem, không giá). Không mở sổ |
| `ketoan` | KT Thu/Chi Viêng Chăn | Kiểm mục I–II, nhập số phiếu quặng và giá cước, khoá phiếu, đẩy chứng từ, điều khoản chủ xe | Vai sổ **kế toán** (xem sổ, lập bút toán ghi tay); Kho hàng (điều chỉnh tồn), Kho nhiên liệu (nhập, chuyển), Bán hàng (lập), Điểm đổ |
| `ketoancp` | KT Chi phí VC | Nhập giá, kiểm, ghi sổ mục IV, V, VI; tất toán tài xế; nhà cung cấp | Xem sổ; Lệnh sửa chữa (kiểm, ghi sổ, trả lại) |
| `khonl` | KT kho xăng dầu VC | Nhập giá dầu mua ngoài, kiểm, ghi sổ mục III; duyệt khai đổ dầu dọc đường | Xem sổ; Kho nhiên liệu (nhập, chuyển, xuất tay), Cấp phát (cấp dầu mọi kho), Điểm đổ, Bán hàng (lập) |
| `khotb` · `khovc` | Thủ kho nhiên liệu (một kho: Thà Bốc · Viêng Chăn) | Không có màn nào — vào sẽ thấy nút **Mở trang kế toán** | Cấp phát (chỉ phiếu lĩnh của kho mình), Kho nhiên liệu (xem) |
| `khopt` | Thủ kho phụ tùng Thà Bốc | Màn Xe | Kho phụ tùng (thêm, nhập, xuất, sửa) |
| `totsua` | Tổ sửa chữa Thà Bốc | Theo dõi tuyến (duyệt báo hỏng), Phiếu xuất xe (mục V), Xe | Lệnh sửa chữa (lập, thêm dòng), Kho phụ tùng (xem) |
| `quytb` | Quỹ tiền mặt cảng cạn | Chi mục IV, V, VI; tất toán | Xem sổ; Cấp phát (chi tạm ứng), Lệnh sửa chữa (chi), Bán hàng (ghi thu); **Xe liên kết** (trả chủ xe) |
| `quyvc` | Thủ quỹ VC | Chi mục III (dầu mua ngoài); tất toán | Xem sổ; Cấp phát (chi tạm ứng), Bán hàng (ghi thu); **Xe liên kết** (trả chủ xe) |
| `doanhthu` | KT Doanh thu VC | Ghi cấn trừ tháng (Theo dõi nhà cung cấp); xem phiếu, công nợ khách | Xem sổ; **Hóa đơn vận chuyển**, **Hoá đơn gộp tháng** (lập hoá đơn, ghi thu, xoá lần thu); Bán hàng (lập, ghi thu) |
| `tx01` · `tx02` · `tx03` | Tài xế | Chỉ màn **Phiếu của tôi** trên điện thoại | Không có tài khoản |
| `ketoantruong` | Kế toán trưởng | — | Duyệt bút toán ghi tay |
| `xem` | Chỉ xem sổ | — | Xem sổ |

**Đăng nhập trang điều xe:** mở `http://<máy chủ>:8020`, bấm vào tên người ở danh sách hoặc gõ tên đăng nhập, mật khẩu `1234`, bấm **Đăng nhập**. Người thường vào thẳng màn đầu tiên của mình; tài xế vào **Phiếu của tôi**.

**Đăng nhập trang kế toán:** mở `http://<máy chủ>:8030`, gõ tên và mật khẩu, bấm đăng nhập. Người có vai sổ vào thẳng **Kế toán** (Sổ kế toán, Nhật ký chung); người vận hành (thủ kho, tổ sửa chữa, Admin Thà Bốc) vào thẳng màn đầu tiên của mình trong nhóm **Kho**, không thấy sổ.

## 3. Đi lại giữa hai trang

### 3.1. Bằng nút bấm

| Đang ở | Bấm | Mở ra |
|---|---|---|
| Trang điều xe, tài khoản thủ kho dầu (`khotb`, `khovc`) | **Mở trang kế toán** (màn duy nhất của họ bên này) | Trang kế toán, thẻ mới |
| Trang điều xe → **Tổng quan** → ô **Việc của tôi** | Ô việc thuộc trang kế toán (ví dụ phiếu lĩnh chờ cấp) | Đúng màn đó ở trang kế toán (Cấp phát…), thẻ mới |
| Trang điều xe → **Theo dõi tuyến** → một xe | **Cấp phiếu lĩnh nhiên liệu** | Màn **Cấp phát** ở trang kế toán |
| Trang điều xe → **Quy trình & trách nhiệm** | Bước có nhãn *ở trang kế toán* | Chỉ là nhãn: bước đó làm ở trang kế toán |
| Trang kế toán → **Kho → Cấp phát** → chọn một phiếu lĩnh | **Mở phiếu** | Phiếu xuất xe của chuyến đó ở trang điều xe, thẻ mới |
| Trang kế toán → **Kho → Kho hàng** | Bấm một dòng lô hoặc dòng sổ | Màn **Theo dõi phiếu vận chuyển** ở trang điều xe, đã lọc theo số phiếu |
| Trang kế toán → **Kho → Bán hàng** | **Sổ chứng từ** ở một phiếu bán | Sổ kế toán (Nhật ký chung) lọc theo số phiếu bán |
| Trang điều xe → **Phiếu xuất xe** (phiếu đã khoá, vai KT Doanh thu) | **Lập hóa đơn thu ↗** · **Ghi một lần thu ↗** | Màn **Hóa đơn vận chuyển** ở trang kế toán, mở đúng phiếu này |
| Trang điều xe → **Phiếu xuất xe** (khách gộp tháng) | **Gộp hoá đơn tháng ↗** · **Thuộc hoá đơn HDT-… ↗** | Màn **Hoá đơn gộp tháng** ở trang kế toán (đúng tháng, đúng tờ) |
| Trang điều xe → **Phiếu xuất xe** → khung **Sổ thu tiền** | **Mở trang kế toán ↗** | Hoá đơn / tờ gộp của phiếu ở trang kế toán |
| Trang điều xe → **Phiếu xuất xe** → thanh nút trên cùng | **Hóa đơn vận chuyển** | Bản in hoá đơn của phiếu ở trang kế toán |
| Trang điều xe → **Danh mục → Khách hàng** → Công nợ khách | Số tờ gộp (có dấu ↗) | Tờ gộp đó ở trang kế toán |
| Trang kế toán → **Tiền vận chuyển → Hoá đơn gộp tháng** → một tờ | Số phiếu trong bảng *Dòng phiếu trong hoá đơn* | Màn **Hóa đơn vận chuyển** của phiếu đó |
| Trang điều xe → **Phiếu xuất xe** (phiếu xe liên kết đã khoá, vai quỹ) | **Trả chủ xe · <số tiền> ↗** | Màn **Xe liên kết** ở trang kế toán, đúng tháng của phiếu, dòng phiếu tô sáng |
| Trang điều xe → **Vận tải → Xe liên kết** | **Trả chủ xe · bảng xe liên kết ↗** | Màn **Xe liên kết** ở trang kế toán |
| Trang kế toán → **Tiền vận chuyển → Xe liên kết** → bảng *Xe liên kết* | Bấm một dòng phiếu | Màn **Hóa đơn vận chuyển** của phiếu đó |

Mở sang trang kia thì **đăng nhập bên đó** nếu chưa đăng nhập (cùng tên, cùng mật khẩu).

### 3.2. Hai trang tự gọi nhau (người dùng không phải bấm gì)

| Việc người dùng làm | Ở trang | Máy gọi sang trang kia để | Nếu trang kia tắt |
|---|---|---|---|
| Lập / sửa phiếu có dầu **kho** | Điều xe | Lấy giá bình quân của kho dầu | Chưa lưu được dòng dầu kho |
| Ghi sổ mục III (dầu kho chưa cấp) | Điều xe | Xuất dầu khỏi kho, sinh PXK_NL | Chặn, báo rõ |
| Sự cố mục V lấy phụ tùng kho, duyệt báo hỏng | Điều xe | Xuất phụ tùng, sinh PXK_PT | Chặn, báo rõ |
| Phiếu giao chọn lô, lưu phiếu giao | Điều xe | Hỏi lô còn hàng, xuất khỏi kho bãi, sinh PXK_HH | Chặn, báo rõ; lưu việc khác vẫn được |
| Xe gom tới bãi | Điều xe | Nhập hàng vào kho bãi, sinh PNK_HH | Chưa báo tới được |
| Xoá phiếu (Sếp) | Điều xe | Trả dầu, phụ tùng, hàng về kho; rút tờ kho | Chưa xoá được |
| Mở màn Xe → tab Sửa chữa | Điều xe | Lấy lịch sử lệnh sửa chữa của xe | Vẫn mở, ghi rõ phần thiếu |
| Cấp dầu / chi tạm ứng ở **Cấp phát** | Kế toán | Đọc phiếu lĩnh, ghi "đã cấp" lên phiếu bên điều xe | Việc vào **hàng đợi trong máy**, tự gửi khi nối lại |
| Thêm / sửa **Điểm đổ**, **phụ tùng** | Kế toán | Ghi bản chép danh mục bên điều xe | Không lưu, báo rõ |
| Lập **lệnh sửa chữa**, chi lệnh | Kế toán | Lấy danh mục xe, báo xe vào / ra xưởng | Không lập được lệnh mới |
| Lập **phiếu bán** | Kế toán | Lấy danh mục khách, chủ xe, tỷ giá, mã giá vốn | Không lập được phiếu mới |
| Nhập dầu bằng ngoại tệ không ghi tỷ giá | Kế toán | Lấy tỷ giá hiện hành | Phải tự ghi tỷ giá |
| Mở **Hóa đơn vận chuyển**, bảng *Chờ gộp* | Kế toán | Đọc phiếu (bản in, số cước) từ trang điều xe | Không mở được phiếu, báo rõ |
| **Lập hóa đơn thu**, **Gộp hoá đơn tháng**, **Huỷ tờ hoá đơn** | Kế toán | Kiểm lại phiếu (đã khoá, mục II đã kiểm) và ghi bản chép *đã xuất hoá đơn* lên phiếu | Chặn, báo rõ; không có hoá đơn nửa vời |
| **Ghi một lần thu**, xoá lần thu | Kế toán | Ghi bản chép *đã thu bao nhiêu*, trạng thái thu lên phiếu | Chặn, báo rõ |
| Mở **Xe liên kết** (bảng chủ xe, bảng tháng, hộp **Trả gộp**) | Kế toán | Đọc danh mục chủ xe, phiếu xe liên kết và số trả chủ xe của từng phiếu (tính ở trang điều xe) | Chặn, báo rõ; không hiện nửa số |
| **Trả gộp**, **Trả chủ xe**, **Huỷ đợt trả** | Kế toán | Kiểm lại phiếu (xe liên kết, đã khoá, chưa trả) và ghi bản chép *đã trả chủ xe* lên phiếu | Chặn, báo rõ; không có đợt trả nửa vời |
| Xem **Công nợ khách** (Danh mục → Khách hàng) | Điều xe | Lấy các tờ hoá đơn và số đã thu | Chặn, báo rõ |
| **Ghi cấn trừ tháng** (Theo dõi nhà cung cấp) | Điều xe | Trang kế toán ghi phiếu thu cấn trừ vào hoá đơn của khách | Chặn, báo rõ |
| Bảng Cấn trừ cuối tháng | Điều xe | Lấy phần đã ghi cấn trừ | Vẫn mở; ô *đã ghi* để trống, nút ghi ẩn |

### 3.3. Cài đặt nối hai trang (Sếp làm một lần)

Trên máy chủ thật, Sếp làm theo thứ tự này, rồi bấm **Kiểm kết nối** ở cả hai bên:

1. Trang kế toán, đăng nhập `admin` → **Cài đặt** → thẻ **Token nhận chứng từ**: bấm **Chép** để lấy token.
2. Trang điều xe, đăng nhập `admin` → **Hệ thống → Tài khoản** → tab **Liên thông trang kế toán**.
3. Ô **Địa chỉ trang kế toán**: địa chỉ API trang kế toán (ví dụ `http://<máy chủ>:8030`).
4. Ô **Địa chỉ mở trang kế toán (trình duyệt · mã QR)**: địa chỉ mà điện thoại, máy thủ kho mở được. Để trống thì dùng ô trên. Mã QR in trên phiếu lĩnh dẫn tới địa chỉ này.
5. Ô **Khoá đẩy chứng từ (trang kế toán cấp)**: dán token vừa chép ở bước 1.
6. Bấm **Tạo khoá cho trang kế toán**, chép khoá hiện ra (khoá mới thay khoá cũ ngay), lưu.
7. Sang trang kế toán → **Cài đặt** → thẻ **Liên thông trang điều xe**: ô **Địa chỉ trang điều xe** (ví dụ `http://<máy chủ>:8020`), ô **Khoá do trang điều xe cấp** dán khoá ở bước 6, bấm **Lưu liên thông**.
8. Bấm **Kiểm kết nối** ở trang kế toán: phải hiện *Nối được trang điều xe · … ms · tài khoản … bên đó*. Bấm **Kiểm kết nối** ở tab Liên thông trang điều xe: phải hiện *Nối được trang kế toán · … ms*.

### 3.4. Khi một trang tắt

Quy tắc anh chốt: việc nào **đụng kho hoặc tiền** mà trang kia tắt thì **chặn và báo rõ** (*Chưa nối được trang kế toán — thử lại sau* hoặc *Chưa nối được trang điều xe — thử lại sau*). Không ghi nửa vời, không xếp hàng gửi sau, để hai bên không bao giờ lệch số. Việc **không đụng kho, tiền** vẫn chạy bình thường. Hai ngoại lệ dùng ngoài hiện trường được giữ hàng đợi trong máy: **Cấp phát** ở kho dầu và **ký nhận giao hàng** trên điện thoại tài xế. Bảng đầy đủ ở Phần 8.

## 4. Luồng chính A → Z

### 4.0. Ví dụ dùng xuyên suốt

Khách **ຄຳຕຸ້ຍ** thuê chở quặng sắt từ mỏ về bãi Thà Bốc, rồi từ bãi ra cảng. Chuyến tách **hai chặng** (anh Khampla B1–B4):

- **Phiếu GOM** `G4-xxxx-09/EPL`: xe **341** (xe nhà), tài xế `tx01`, chở **40 tấn** từ mỏ (ກາສີ) về bãi Thà Bốc (ທ່າບົກ).
- **Phiếu GIAO** `T4-xxxx-09/EPL`: xe **342**, tài xế `tx02`, lấy **25 tấn** từ lô của phiếu gom, chở từ bãi ra cảng.

Mỗi phiếu đi qua cùng một chuỗi mục I–VI. Bước 1–13 làm cho **phiếu gom**. Bước 14–16 là phần riêng của **phiếu giao**; các bước dầu, tạm ứng, kiểm, trên đường (2–11) làm lại y như phiếu gom. Bước 17–23 là khoá, doanh thu, cuối kỳ, sổ kế toán, làm cho cả hai phiếu. Muốn thử chuyến **một chặng** (xe đi thẳng mỏ → cảng) thì lập một phiếu loại **Giao** không lấy từ lô và bỏ qua bước 12–14.

**Sáu mục của một phiếu và chuỗi trạng thái:** mỗi mục đi theo chuỗi **Chờ → Đã nhập → Đã kiểm → Đã ghi sổ → Đã chi**. Nút của từng mục hiện ngay trên đầu mục, chỉ người đúng vai mới thấy nút:

| Mục | Nội dung | Nhập | Kiểm (**Xác nhận kiểm tra**) | Ghi sổ (**Ghi sổ kế toán**) | Chi (**Xác nhận đã chi**) |
|---|---|---|---|---|---|
| I | Thông tin xe vận chuyển | Admin Thà Bốc | KT Thu/Chi VC | — (không có tiền) | — |
| II | Thông tin vận chuyển & doanh thu | Admin Thà Bốc | KT Thu/Chi VC | — | — |
| III | Chi phí nhiên liệu | Admin Thà Bốc | KT kho xăng dầu | KT kho xăng dầu | Thủ quỹ VC |
| IV | Chi phí đi đường | Admin Thà Bốc | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt cảng cạn |
| V | Chi phí sửa chữa | Tổ sửa chữa | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt cảng cạn |
| VI | Chi phí khác | Admin Thà Bốc | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt cảng cạn |

Người kiểm mục thấy thêm nút **Trả lại sửa** (trả về cho người nhập). Sếp có **Mở khóa (admin)** để mở lại mục đã kiểm. Lưu ý: nút **Ghi sổ kế toán** trên phiếu là **một bước duyệt của phiếu** (kế toán xác nhận khoản chi đã đúng để chi). Bút toán thật trong sổ kế toán sinh ra khi tờ chứng từ tới trang kế toán (Phần 1.3).

### Bước 1. Bãi lập phiếu GOM — mục I và II

**Ai:** Admin Thà Bốc (`thabok`). **Trang:** điều xe. **Màn:** Vận tải → **Phiếu xuất xe** (hoặc Tổng quan → **Tạo phiếu xuất xe**).

**Thao tác:**

1. Bấm **Phiếu mới**. Máy gợi ý số phiếu, đổi theo loại phiếu.
2. Mục I — **Thông tin xe vận chuyển**: ô **Loại phiếu** chọn **Gom (mỏ → bãi)**. Chọn **Số xe** 341; biển đầu kéo, biển rơ-moóc, hãng xe tự điền. Chọn **Tài xế** `tx01`. Ghi **Ngày lập phiếu**, **Ngày xe đi**, km **Lúc đi**; **Km về ước tính** tự tính theo tuyến.
3. Mục II — **Thông tin vận chuyển & doanh thu**: **Chọn tuyến** (điểm đi, điểm đến tự điền); chọn **Khách hàng**; **Loại hàng** Quặng sắt; **Cân đầu (tấn)** 40 theo phiếu cân ở mỏ.
4. Khung **Hàng trên phiếu** → **Thêm dòng**: **Mặt hàng** ແຮ່ເຫຼັກ (quặng sắt), **Số tấn** 40.
5. **Phiếu quặng đính kèm**: có ảnh phiếu quặng thì bấm **Thêm ảnh · PDF** (lưu phiếu rồi mới đính kèm được). Không có ảnh cũng được; kế toán gõ số phiếu quặng ở bước 5.
6. Bấm **Lưu**. Máy báo *Đã lưu*.

**Máy tự làm:** cấp số `G4-xxxx-MM/EPL`; giá cước theo **bảng giá khách × tuyến** (Bãi không thấy); tỷ giá USD · THB · VND · CNY **khoá vào phiếu** lúc lập; xe chủ xe liên kết thì phiếu tự thành phiếu xe liên kết, điền phí và ngưỡng tấn theo hồ sơ chủ xe; sinh tờ **DO** (phiếu xuất xe).

**Máy chặn:** Bãi không nhập được giá cước, giá thuê xe, phí, ngưỡng tấn, số phiếu quặng.

**Trạng thái sau bước:** phiếu *Đã xuất xe*; mục I, II *Chờ*. Phiếu gom **chưa đụng kho bãi** — hàng chỉ vào kho khi xe về tới bãi (bước 12).

**Ai làm tiếp:** chính Admin Thà Bốc làm bước 2–4.

### Bước 2. Mục III — dầu, và in phiếu lĩnh nhiên liệu

**Ai:** Admin Thà Bốc. **Trang:** điều xe. **Màn:** Phiếu xuất xe, mục III **Chi phí nhiên liệu**.

**Thao tác:**

1. Bấm **Thêm dòng** ở mục III. Mỗi dòng ghi **Lít** và **Nơi đổ**: chọn kho trong nhóm **Kho của EPL (lĩnh)** (ví dụ kho Thà Bốc), hoặc trạm trong nhóm **Trạm bán dầu (mua)**.
2. Xe liên kết: ô **Ai chi** chọn **EPL ứng** hay **Chủ xe tự trả**. Đổ ở trạm Việt Nam mà trạm cho ghi nợ: tick **Ghi nợ tại trạm**.
3. Bấm **Lưu**.
4. Bấm **Phiếu lĩnh nhiên liệu** (thanh nút trên cùng của phiếu). Máy lập mỗi kho một tờ phiếu lĩnh có **mã QR**, rồi mở màn **Phiếu chi · Phiếu thu** ở tờ đó. Bấm **In**, đưa tài xế cầm tới kho.

**Máy tự làm:** dòng đổ ở **kho EPL** lấy **giá bình quân của đúng kho đó** (hỏi trang kế toán, không ai gõ); dòng đổ ở trạm là nguồn mua, gắn nhà cung cấp của trạm; định khoản gợi ý 625/1371 (kho), 625/4021 (mua), 4022/… (xe liên kết). Tờ **PLNL** sinh lúc bấm phiếu lĩnh.

**Máy chặn:** Bãi không thấy và không nhập đơn giá dầu, thành tiền, mã tài khoản.

**Ai làm tiếp:** tài xế cầm phiếu lĩnh tới kho → **thủ kho** cấp dầu (bước 8).

### Bước 3. Mục IV đi đường, mục VI chi khác, và in phiếu tạm ứng

**Ai:** Admin Thà Bốc. **Trang:** điều xe. **Màn:** Phiếu xuất xe, mục IV **Chi phí đi đường** và mục VI **Chi phí khác**.

**Thao tác:**

1. Mục IV → **Thêm dòng**: chọn **Khoản mục** (tiền ăn, tiền nước, chi phí sang Việt Nam, điện thoại, chipping…) và **SL**. Không có trong danh sách thì chọn **Khác (tự gõ)…**.
2. Phí cao tốc: tuyến có BOT thì máy tự thêm dòng. Chọn **Trả tiền mặt (không dùng thẻ)** hoặc chọn thẻ cao tốc để trừ thẻ.
3. Mục VI (nếu có) → **Thêm dòng** tương tự. Bấm **Lưu**.
4. Bấm **Phiếu chi tạm ứng**: mở màn **Phiếu chi · Phiếu thu** ở tờ tạm ứng của phiếu này, có mã QR. Bấm **In**, tài xế cầm tới quỹ.

**Máy tự làm:** gom mọi khoản tiền mặt EPL ứng (mục IV, VI, dầu mua ngoài) thành số tạm ứng. Tờ **PTU** sinh ở bước này.

**Máy chặn:** Bãi không nhập đơn giá; người kiểm mục nhập ở bước 6–7.

**Ai làm tiếp:** tài xế cầm phiếu tạm ứng tới **quỹ** (bước 9) sau khi kế toán ghi sổ mục IV.

### Bước 4. Bãi gửi kiểm từng mục

**Ai:** Admin Thà Bốc. **Trang:** điều xe. **Màn:** Phiếu xuất xe.

**Thao tác:** ở đầu mỗi mục I, II, III, IV, VI bấm **Gửi kiểm tra**. Mục V là của tổ sửa chữa. Mục trống không có nút.

**Lưu ý:** nút **Gửi kiểm tra** chỉ hiện khi phiếu đã **Lưu** ít nhất một lần — dòng *Trạng thái phiếu* dưới cùng không còn ghi *Phiếu mới*. Phiếu mới chưa lưu thì chưa có mục nào để gửi.

**Sau bước:** các mục *Đã nhập · chờ kiểm*. Bãi vẫn sửa được cho tới khi kế toán kiểm.

**Ai làm tiếp:** ba người ở Viêng Chăn, làm song song được: KT Thu/Chi (mục I–II), KT kho xăng dầu (mục III), KT Chi phí (mục IV, VI). Họ thấy việc ở **Tổng quan → Việc của tôi** trên trang điều xe.

### Bước 5. KT Thu/Chi kiểm mục I, II

**Ai:** KT Thu/Chi VC (`ketoan`). **Trang:** điều xe. **Màn:** Phiếu xuất xe. Chọn phiếu ở ô **Số phiếu** trên cùng, hoặc bấm từ **Việc của tôi**.

**Thao tác:**

1. Đối chiếu xe, tài xế, cân đầu với phiếu quặng (xem ảnh đính kèm nếu có).
2. Mục II: gõ **Số phiếu quặng** và **Ngày phiếu quặng** (gõ tay được, không bắt ảnh). Sửa giá cước nếu chuyến này khác hợp đồng. Xe liên kết: nhập **Giá thuê họ mỗi tấn**, phí, **Tải cho phép (tấn)**.
3. Bấm **Lưu**, rồi **Xác nhận kiểm tra** ở mục I và mục II. Sai thì bấm **Trả lại sửa** để trả về cho Bãi.

**Máy chặn:** mục đã kiểm là khoá, muốn sửa phải trả lại; KT Thu/Chi không kiểm mục III–VI.

**Sau bước:** mục I, II *Đã kiểm*.

### Bước 6. KT kho xăng dầu kiểm và ghi sổ mục III

**Ai:** KT kho xăng dầu VC (`khonl`). **Trang:** điều xe. **Màn:** Phiếu xuất xe, mục III.

**Thao tác:**

1. Dòng dầu **mua ngoài**: nhập **Đơn giá** (thường VND, quy Kíp theo tỷ giá khoá trên phiếu). Dòng dầu **kho**: giá là bình quân của kho, máy tự điền, gõ tay bị bỏ qua.
2. Bấm **Xác nhận kiểm tra** ở mục III (máy lưu giá trước rồi mới kiểm).
3. Bấm **Ghi sổ kế toán** ở mục III.
4. Nếu có khoản dầu mua ngoài EPL chi tiền mặt: **Thủ quỹ VC** (`quyvc`) mở phiếu, bấm **Xác nhận đã chi** ở mục III.

**Máy tự làm khi ghi sổ mục III:** dòng dầu **kho** nào chưa được thủ kho cấp theo phiếu lĩnh thì **xuất kho luôn** ở trang kế toán, theo giá bình quân lúc xuất, sinh tờ **PXK_NL**. Mỗi dòng dầu kho chỉ xuất **một lần**: hoặc lúc thủ kho cấp (bước 8), hoặc lúc ghi sổ mục III.

**Máy chặn:** dòng EPL trả mà đơn giá 0 thì không kiểm được; kế toán chỉ nhập giá, không thêm / xoá dòng; trang kế toán tắt thì chưa ghi sổ được mục III có dầu kho.

### Bước 7. KT Chi phí kiểm và ghi sổ mục IV, VI

**Ai:** KT Chi phí VC (`ketoancp`). **Trang:** điều xe. **Màn:** Phiếu xuất xe, mục IV và VI.

**Thao tác:** nhập **Đơn giá** từng dòng mục IV, VI → **Xác nhận kiểm tra** → **Ghi sổ kế toán**, ở từng mục.

**Máy tự làm:** ghi sổ mục IV thì dòng trả bằng **thẻ cao tốc** trừ số dư thẻ đúng một lần.

**Sau bước:** mục IV, VI *Đã ghi sổ · chờ chi*. **Ai làm tiếp:** quỹ chi tạm ứng (bước 9).

### Bước 8. Thủ kho cấp dầu theo phiếu lĩnh — trang kế toán

**Ai:** thủ kho của đúng kho ghi trên phiếu lĩnh (`khotb` cho kho Thà Bốc), hoặc KT kho xăng dầu. **Trang:** **kế toán**. **Màn:** Kho → **Cấp phát**.

**Thao tác:**

1. Đăng nhập trang kế toán. Thủ kho vào thẳng màn **Cấp phát**, bảng **Chờ cấp** chỉ có phiếu lĩnh của kho mình.
2. Tài xế đưa tờ phiếu lĩnh: bấm vào ô **Nhập mã QR**, quét mã bằng máy quét (hoặc gõ mã in trên phiếu), Enter. Hoặc bấm thẳng vào dòng trong bảng.
3. Khung **Đối chiếu trước khi cấp** hiện số xe, biển đầu kéo, biển rơ-moóc, tài xế, khách, tuyến, các dòng dầu. Đối chiếu đúng xe, đúng tài xế.
4. Bấm **Cấp dầu** (hoặc **Cấp** ở dòng trong bảng). Hộp cấp dầu: ô **Số lít duyệt** (chỉ xem), ô **Số lít cấp thật** (sửa nếu cấp lệch), ô **Lý do cấp lệch số duyệt** (bắt buộc khi cấp lệch). Bấm **Cấp dầu**.
5. Muốn xem cả phiếu xuất xe: bấm **Mở phiếu** (mở trang điều xe, thẻ mới).

**Máy tự làm:** trừ tồn đúng kho ngay; dòng dầu trên phiếu xuất xe mang **giá bình quân của kho lúc cấp**; trang điều xe ghi phiếu lĩnh *Đã cấp* kèm tên người cấp; sinh **PXK_NL** ngay ở sổ.

**Mất mạng ở kho:** màn vẫn hiện danh sách và chi tiết từ **bản lưu trong máy** (dải vàng *Đang ngoại tuyến*); quét mã vẫn tra được; bấm Cấp thì việc vào **hàng đợi**, dòng đó hiện *Chờ gửi*. Có mạng lại (hoặc trang điều xe bật lại) thì máy **tự gửi**; muốn gửi ngay bấm **Gửi lại ngay**. Việc nào bị máy chủ từ chối thì máy báo rõ để xem lại.

**Máy chặn:** thủ kho kho khác không cấp được; cấp lệch không ghi lý do; cấp hai lần.

### Bước 9. Quỹ chi tạm ứng cho tài xế

**Ai:** Quỹ tiền mặt cảng cạn (`quytb`) hoặc Thủ quỹ VC (`quyvc`). Làm ở **một trong hai chỗ**, máy tự loại chỗ kia:

- **Cách 1 — trang kế toán:** Kho → **Cấp phát** → tab **Phiếu tạm ứng đi đường** → quét QR phiếu tạm ứng (hoặc bấm dòng) → đối chiếu → **Chi tiền**.
- **Cách 2 — trang điều xe:** mở Phiếu xuất xe → mục IV → **Xác nhận đã chi**.

**Máy tự làm:** mục IV thành *Đã chi*; sinh tờ **PC_TU** (phiếu chi tạm ứng, ở trang điều xe, chờ đẩy sổ); dòng trả bằng thẻ cao tốc không tính vào tiền mặt. Tài xế ký nhận tiền trên tờ phiếu tạm ứng.

**Máy chặn:** mục IV chưa *Đã ghi sổ* thì không chi được; tài xế không tự chi cho mình; chi rồi thì chỗ kia báo sai bước, không ra hai tờ.

**Ai làm tiếp:** tài xế xuất phát.

### Bước 10. Tài xế xuất phát, chia sẻ vị trí, báo mốc

**Ai:** tài xế (`tx01`) trên điện thoại; hoặc Admin Thà Bốc thay. **Trang:** điều xe. **Màn:** **Phiếu của tôi** (tài xế) · Theo dõi tuyến (Bãi).

**Thao tác:**

1. Tài xế mở **Phiếu của tôi**, chọn phiếu đang chạy, bấm **Xuất phát**, cho phép chia sẻ vị trí (GPS).
2. Bãi làm thay thì mở Phiếu xuất xe → **Xe đã lăn bánh**.
3. Tới từng mốc trên tuyến: Bãi mở Vận tải → **Theo dõi tuyến**, chọn xe, bấm **Xác nhận tới điểm n**. Có chuyện cần ghi thì **Ghi chú diễn biến**.

**Máy chặn:** mục IV chưa *Đã chi* (tài xế chưa cầm tiền) thì không xuất phát được — nút hiện *Chưa nhận tiền tạm ứng thì chưa xuất phát*.

**Sau bước:** *Đang vận chuyển*; vị trí xe hiện trên bản đồ Theo dõi tuyến.

### Bước 11. Chuyện dọc đường: đổ dầu, xe hỏng, đổi xe

**Đổ dầu dọc đường (Việt Nam):**

1. Tài xế: Phiếu của tôi → **Khai đổ nhiên liệu** → ghi **số lít** và trạm (không nhập giá).
2. KT kho xăng dầu (hoặc Bãi): Theo dõi tuyến → sự cố của xe → **Duyệt** (hoặc **Từ chối** kèm lý do). Dòng thành dòng mục III nguồn mua; mục III mở lại *Đã nhập*; KT kho nhập giá khi kiểm lại (như bước 6).
3. Khai đổ ở **kho** của EPL thì máy bảo dùng phiếu lĩnh.

**Xe hỏng — mục V:**

1. Tài xế: Phiếu của tôi → **Báo hỏng / sự cố**: hỏng gì, số tiền dự kiến. Hoặc Bãi: Theo dõi tuyến → **Báo sự cố / sửa xe**.
2. Tổ sửa chữa (`totsua`): Theo dõi tuyến → sự cố → **Duyệt**, chọn **Nguồn**: **Lấy từ kho (xuất kho)** thì chọn **Phụ tùng trong kho** và số lượng; **Mua ngoài / garage (chi tiền)** thì ghi khoản mục, đơn giá.
3. Lấy kho: trừ tồn phụ tùng ngay ở trang kế toán, giá bình quân, sinh **PXK_PT**. Mục V mở lại *Đã nhập*, chờ KT Chi phí kiểm (bước 16). Hỏng nặng thì xe chuyển *đang sửa*.
4. Chỉ tổ sửa chữa duyệt báo hỏng; kho không đủ phụ tùng thì chặn.

**Đổi xe giữa đường (xe hỏng nặng):** Bãi mở Phiếu xuất xe → **Đổi xe** → chọn xe thay, tài xế (**Giữ nguyên tài xế** hay đổi), xe cũ **Vào xưởng sửa** hay **Về rảnh**, ghi **Lý do đổi xe**. Máy giữ nguyên chuyến, dòng chi, hàng; mục I phải kiểm lại. Phiếu đã tới nơi thì không đổi xe được.

### Bước 12. Xe gom về tới bãi — hàng vào kho bãi

**Ai:** Admin Thà Bốc (tài xế đã bấm **Báo đã về** trên điện thoại thì ngày về, km về điền sẵn). **Trang:** điều xe. **Màn:** Phiếu xuất xe (hoặc Theo dõi tuyến).

**Thao tác:**

1. Bấm **Xe đã tới · nhập cân cuối**.
2. Hộp nhập: **Cân cuối (tấn)** — với phiếu gom là **cân tại bãi**, ví dụ 39,6; **Ngày xe về**; **Km về (công-tơ-mét)**. Bấm **Đồng ý**.

**Máy tự làm (phiếu GOM):** hàng vào **kho bãi** ở trang kế toán thành một **LÔ** (lô = phiếu gom này) theo **số cân tại bãi** 39,6 t; sinh tờ **PNK_HH** ở sổ (ngoài bảng, tính bằng tấn, không có tiền); trên phiếu tự ghi **một dòng hao hụt** 0,4 t (cân mỏ − cân bãi); xe và tài xế rảnh lại; công-tơ-mét của xe cập nhật.

**Máy chặn:** chưa nhận tạm ứng thì không báo tới được; **trang kế toán tắt** thì chưa báo tới được (không biết hàng đã vào kho hay chưa); đã nhập kho rồi thì **không sửa dòng hàng và cân** của phiếu gom nữa — muốn khác thì kế toán lập điều chỉnh (bước 13).

**Ai làm tiếp:** lô nằm bãi chờ phiếu giao lấy (bước 14); KT Thu/Chi khoá phiếu gom khi các mục xong (bước 17).

### Bước 13. Lô nằm bãi — xem tồn, điều chỉnh

**Ai:** ai cũng xem được (trừ tài xế, thủ kho, tổ sửa chữa); **điều chỉnh** chỉ KT Thu/Chi VC hoặc Sếp. **Trang:** **kế toán**. **Màn:** Kho → **Kho hàng**.

**Thao tác xem:** ba ô số trên cùng (tồn tổng, số lô còn hàng, số dòng sổ); bảng **Lô hàng trong kho** (lô nào, ngày, mặt hàng, khách, xe, nhập, điều chỉnh, còn lại); bảng **Sổ nhập xuất** (mới nhất trên cùng, tồn cộng dồn). Bấm một dòng thì mở phiếu đó ở trang điều xe.

**Thao tác điều chỉnh** (cân lại, hàng ẩm hụt, rơi vãi): ở dòng lô bấm **Điều chỉnh tồn** → **Số tấn điều chỉnh (dương tăng, âm giảm)**, ví dụ −0,6 → **Lý do (bắt buộc)** → **Lưu**. Sinh tờ **DC_HH** ở sổ. Không sửa lịch sử nhập / xuất, chỉ thêm một dòng có dấu.

**Máy chặn:** Bãi không tự điều chỉnh (Bãi báo, kế toán ghi); không có lý do; giảm quá tồn (hàng đã xuất cho phiếu giao).

### Bước 14. Bãi lập phiếu GIAO lấy hàng từ lô

**Ai:** Admin Thà Bốc. **Trang:** điều xe. **Màn:** Phiếu xuất xe.

**Thao tác:**

1. **Phiếu mới** → **Loại phiếu**: **Giao (bãi → khách)**. Chọn xe **342**, tài xế `tx02`, tuyến bãi → cảng, khách, ngày.
2. Khung **Hàng trên phiếu** → **Thêm dòng**: **Mặt hàng**, ô **Lấy từ lô (phiếu gom)** chọn lô `G4-…` (danh sách hiện lô còn hàng và số tấn còn — hỏi trang kế toán), **Số tấn** 25.
3. Bấm **Lưu**.
4. Làm tiếp y như phiếu gom: dầu và phiếu lĩnh (bước 2), đi đường và tạm ứng (bước 3), gửi kiểm (4), kiểm (5–7), cấp dầu (8), chi tạm ứng (9), xuất phát (10), dọc đường (11).

**Máy tự làm:** hàng xuất khỏi kho bãi ngay khi lưu: trang kế toán kiểm tồn lô và ghi dòng xuất, sinh **PXK_HH**; tồn lô còn 39,6 − 25 = 14,6 t; **Cân đầu** của phiếu giao = tổng tấn lấy khỏi kho (25). Sửa lại số tấn thì phần xuất được **thay** theo số mới, không cộng dồn. Dòng hàng của phiếu giao ghi rõ lấy từ phiếu gom nào — đó là dây nối hai phiếu.

**Máy chặn:** phiếu giao có dòng hàng mà không chỉ rõ lô; lấy quá số tấn còn trong lô (kể cả khi hai dòng cùng lô cộng lại quá tồn); **trang kế toán tắt** thì không lưu được phiếu giao có lấy lô (lưu việc khác của phiếu vẫn được); xoá phiếu gom khi lô đã có phiếu giao lấy.

### Bước 15. Xe giao tới nơi — ký nhận giao hàng, cân cuối

**Ai:** tài xế (`tx02`) rồi Admin Thà Bốc. **Trang:** điều xe.

**Thao tác của tài xế (Phiếu của tôi, trên điện thoại):**

1. Bấm **Giao hàng hoàn tất · ký nhận**: người nhận **ký lên màn hình**, bấm **Thêm ảnh biên bản · phiếu cân** để chụp ảnh, bấm **Gửi**. Mất mạng thì bản ký vào hàng đợi, có mạng tự gửi. Ký sai thì **Ký lại**; xem lại bằng **Xem biên bản**.
2. Về tới thì bấm **Báo đã về**: **Ngày xe về**, **Km về (công-tơ-mét)**.

**Thao tác của Admin Thà Bốc (Phiếu xuất xe):** bấm **Xe đã tới · nhập cân cuối** → **Cân cuối (tấn)** (cân ở cảng, ví dụ 24,7), ngày về, km về (đã điền sẵn theo tài xế), **Số POD** và **Người ký nhận** (phiếu giao mới có hai ô này) → **Đồng ý**. Khung **Biên bản giao nhận hàng (POD)** trên phiếu có **In biên bản giao nhận**.

**Máy tự làm (phiếu GIAO):** ghi **dòng hao hụt** chặng giao (25 − 24,7 = 0,3 t). Sửa cân cuối sau khi đã tới thì dòng hao hụt tính lại theo số mới.

### Bước 16. Mục V, VI: kiểm, ghi sổ, chi

**Ai:** KT Chi phí VC kiểm và ghi sổ; Quỹ tiền mặt cảng cạn chi. **Trang:** điều xe. **Màn:** Phiếu xuất xe.

**Thao tác:** KT Chi phí: mục V (và VI nếu chưa làm) → nhập đơn giá dòng mua ngoài → **Xác nhận kiểm tra** → **Ghi sổ kế toán**. Quỹ: mục V, VI → **Xác nhận đã chi**.

**Máy tự làm:** một tờ **PC_SC** cho cả mục (trang điều xe, chờ đẩy sổ); dòng lấy kho không tính (đã có PXK_PT).

### Bước 17. KT Thu/Chi kiểm lại toàn phiếu và khoá

**Ai:** KT Thu/Chi VC. **Trang:** điều xe. **Màn:** Phiếu xuất xe (nút chỉ hiện khi xe đã tới).

**Thao tác:**

1. Bấm **🔒 Khoá phiếu**.
2. Máy rà và hiện danh sách cảnh báo: km về lệch ước tính quá 10 %, hao hụt quá 1,5 %, thiếu cân cuối, thiếu km về, thiếu phiếu quặng (không có cả ảnh lẫn số phiếu), mục có chi mà chưa kiểm. Đọc từng điểm; đúng thì bấm **Đồng ý** để khoá. Không có điểm lệch thì máy báo phiếu sạch.
3. Cần sửa lại thì bấm **Mở khoá phiếu** (chỉ khi chưa xuất hoá đơn).

**Sau bước:** phiếu *Đã khoá 🔒*. Bãi và tài xế không ghi thêm gì; kế toán, quỹ, kho vẫn kiểm và chi tiếp.

**Ai làm tiếp:** KT Doanh thu (hoá đơn), quỹ (trả chủ xe nếu xe liên kết), KT Chi phí (tất toán cuối tháng).

### Bước 18. KT Doanh thu lập hoá đơn và ghi thu — trang kế toán

**Ai:** KT Doanh thu VC (`doanhthu`). **Trang:** **kế toán** (từ đợt 7a). **Màn:** nhóm **Tiền vận chuyển** → **Hóa đơn vận chuyển** · **Hoá đơn gộp tháng**.

**Đi từ phiếu:** trên trang điều xe, phiếu đã khoá hiện nút **Lập hóa đơn thu ↗** (hoặc **Gộp hoá đơn tháng ↗** với khách hợp đồng). Bấm nút là mở trang kế toán ở đúng phiếu, đúng tháng. Chưa đăng nhập trang kế toán thì đăng nhập một lần (cùng tên, cùng mật khẩu).

**Khách theo phiếu (không hợp đồng tháng):**

1. Trang kế toán → **Tiền vận chuyển → Hóa đơn vận chuyển**. Vào thẳng từ menu thì màn **chưa mở phiếu nào**: gõ vào ô **Chọn phiếu** (tìm số phiếu, xe, tài xế, khách hàng) rồi chọn ở ô bên cạnh. Đi từ nút ↗ bên điều xe thì phiếu đã mở sẵn.
2. Màn hiện bản in hoá đơn của phiếu (đầu phiếu, các mục chi, phần trả chủ xe nếu xe liên kết) và khung **Sổ thu tiền**. Bấm **Lập hóa đơn thu** → xác nhận. Sinh tờ **HD** (Nợ 1211 / Có 70) và **vào sổ ngay**. Bên điều xe, phiếu tự hiện *Đã lập hóa đơn*.
3. Khách trả tiền: khung **Sổ thu tiền** → **Ghi một lần thu** → điền **Ngày thu**, **Tiền tệ**, **Số tiền khách trả**, **Tỷ giá ngày thu** (để trống thì máy dùng tỷ giá khoá trên phiếu, ô ghi sẵn con số đó), **Cách thu** (Chuyển khoản, Tiền mặt, Cấn trừ công nợ, Khác), **Số uỷ nhiệm chi · biên lai**, **Ghi chú** → **Lưu**. Mỗi lần thu sinh một tờ **PT**, vào sổ ngay. Thu nhiều lần, nhiều loại tiền đều được.
4. Ghi nhầm: bấm **×** ở dòng thu đó → xác nhận. Tờ PT rút khỏi sổ, trạng thái thu tự lùi lại.
5. In: **In** (bản in hoá đơn) và **Phiếu thu** (phiếu thu tiền khách, định khoản 1211/70) mở tờ trong hộp; bấm **In** trong hộp.

**Khách hợp đồng (gộp tháng):** trang kế toán → **Tiền vận chuyển → Hoá đơn gộp tháng** → chọn **Tháng**. Bảng **Chờ gộp** liệt kê từng khách × từng loại tiền còn phiếu đã khoá chưa lên hoá đơn → bấm **Gộp hoá đơn tháng** ở dòng khách → ghi **Ngày hoá đơn**, **Ghi chú** → **Gộp hoá đơn tháng**. Sinh một tờ HD cho mọi phiếu của dòng đó. Trong **Các tờ hoá đơn gộp** bấm **Xem** để mở tờ; ghi thu ở tờ bằng **Ghi một lần thu** — tiền thu tự phân bổ về từng phiếu theo thứ tự ngày, phiếu cũ trả trước. Sai thì **Huỷ tờ hoá đơn** (chỉ khi chưa thu đồng nào; các phiếu quay lại *chưa xuất hoá đơn*).

**Cấn trừ cuối tháng:** vẫn bấm ở **trang điều xe** → Vận tải → **Theo dõi nhà cung cấp** → khung **Cấn trừ cuối tháng** → **Ghi cấn trừ tháng** ở dòng khách. Máy tính phần khách đã trả hộ (thẻ cao tốc của khách, trạm dầu Việt Nam ghi nợ) rồi nhờ trang kế toán ghi thành phiếu thu cách thu *cấn trừ*: hoá đơn gộp cũ trước, rồi hoá đơn lẻ cũ trước.

**Máy tự làm:** tiền = cân (tấn tới, hoặc khoán trọn chuyến) × đơn giá, theo tiền tệ hợp đồng — số lấy từ phiếu bên điều xe, không gõ tay; trạng thái tự suy: chưa thu · thu một phần · đã thu, hiện ở cả hai trang. **Phiếu gom cũng có cước riêng** (B4) nếu khách trả theo từng chặng: lập hoá đơn như phiếu giao.

**Máy chặn:** phiếu chưa kiểm mục II hoặc chưa khoá chưa lập hoá đơn; khách gộp tháng không lập hoá đơn lẻ; thu dư (máy hỏi **Thu nhiều hơn số còn lại của hoá đơn** → **Vẫn ghi (thu dư)**); dòng thu do tờ gộp phân bổ xuống không xoá lẻ ở phiếu; lần thu, hoá đơn đã vào sổ **từ trang điều xe trước ngày dời (28/09)** không xoá được — ghi bút toán đảo ở **Ghi tay**; **trang điều xe tắt** thì chặn, không lưu gì. Bãi, thủ kho, tổ sửa chữa không có màn này.

**Sếp gỡ hoá đơn lập nhầm:** trên màn Hóa đơn vận chuyển, Sếp (`admin`) có nút **Huỷ tờ hoá đơn** khi phiếu chưa thu đồng nào. Phiếu còn hoá đơn thì trang điều xe **không cho xoá phiếu**, kể cả Sếp.

### Bước 19. Trả chủ xe liên kết — trang kế toán (chỉ phiếu xe thuê ngoài)

**Ai:** Quỹ tiền mặt cảng cạn (`quytb`) hoặc Thủ quỹ VC (`quyvc`); Sếp cũng trả được. **Trang:** **kế toán** (từ đợt 7b). **Màn:** nhóm **Tiền vận chuyển** → **Xe liên kết**.

**Đi từ phiếu:** trên trang điều xe, phiếu xe liên kết đã khoá hiện nút **Trả chủ xe · <số tiền> ↗** (chỉ vai quỹ thấy). Bấm là mở trang kế toán ở màn Xe liên kết, đúng tháng của phiếu, dòng phiếu tô sáng. Ở màn **Vận tải → Xe liên kết** bên điều xe (danh mục chủ xe) có nút **Trả chủ xe · bảng xe liên kết ↗**.

**Thao tác:**

1. Trang kế toán → **Tiền vận chuyển → Xe liên kết** → ô **Tháng** chọn tháng của phiếu. Màn có hai bảng: **Chủ xe liên kết** (điều khoản từng chủ xe, cột **Chờ trả**) và **Xe liên kết** (mỗi dòng một phiếu xe ngoài: tiền thuê, cắt phí, cắt quá tải, trừ EPL đã ứng, còn phải trả chủ xe, lãi EPL).
2. **Trả từng phiếu** (chủ xe có cách trả *Từng phiếu, sau khi khoá*): bảng **Xe liên kết** → dòng phiếu → cột **Trả chủ xe** → bấm **Trả chủ xe**. Hộp hiện tên chủ xe, số phiếu, số tiền và cách tính (tiền thuê − phí − quá tải − EPL đã ứng) → bấm **Trả chủ xe**.
3. **Trả nhiều phiếu một lần** (chủ xe *Gộp cuối tháng* hay *Theo đợt thoả thuận* — dòng phiếu ghi *Trả gộp ở bảng Chủ xe*): bảng **Chủ xe liên kết** → **Trả gộp** ở dòng chủ xe → tích các phiếu trả trong đợt (dòng **Tổng** tự tính lại) → xem khung **Hàng mua ở quầy chờ trừ** nếu có → điền **Ngày thu**, **Cách thu** (Tiền mặt, Chuyển khoản, Cấn trừ công nợ, Khác), **Số uỷ nhiệm chi · biên lai**, **Ghi chú** → bấm **Trả chủ xe**.
4. Trả xong: dòng phiếu hiện *Đã trả chủ xe*; bên trang điều xe phiếu tự hiện đã trả, nút trả biến mất.

**Máy tự làm:** phải trả = tiền thuê − phí quản lý % − cắt quá tải − mọi khoản EPL đã ứng (dầu kho, đi đường…) — số tính ở trang điều xe, không gõ tay; **tự trừ tiếp** phiếu bán hàng chủ xe mua ở quầy chưa trừ (phiếu cũ trước, vừa tiền thì trừ), phiếu bán thành *Đã trừ*; phiếu chi ghi số **thực chi** sau khi trừ. Một tờ **PC_CX** (Nợ 4022 / Có tiền) cho cả đợt, **vào sổ ngay** — không còn nằm chờ đẩy ở trang điều xe.

**Máy chặn:** phiếu chưa khoá; phiếu xe nhà; trả hai lần; các phiếu khác tiền thuê phải tách đợt; **trang điều xe tắt** thì màn không hiện số, không trả được. Kế toán khác (KT Thu/Chi, KT Chi phí, KT Doanh thu, KT kho xăng dầu) xem được hai bảng nhưng không có nút trả; Bãi không có màn này.

**Sếp gỡ đợt trả lập nhầm:** bảng Xe liên kết, phiếu đã trả có nút **Huỷ đợt trả** (chỉ `admin`) → xác nhận. Tờ PC_CX rút khỏi sổ, hàng mua ở quầy về lại chờ trừ, mọi phiếu của đợt quay lại *chưa trả*. Đợt trả có tờ PC_CX đã đẩy từ trang điều xe **trước ngày dời (28/09)** thì không huỷ được — ghi bút toán đảo ở **Ghi tay**. Phiếu đã trả chủ xe thì trang điều xe **không cho xoá phiếu**, kể cả Sếp.

### Bước 20. Tất toán tài xế theo tháng

**Ai:** KT Chi phí VC (chốt); quỹ chi bù hoặc thu lại. **Trang:** điều xe. **Màn:** Vận tải → **Tất toán tài xế**.

**Thao tác:** chọn tháng → xem từng tài xế: đã ứng bao nhiêu, chi thật bao nhiêu, chênh → bấm **Tất toán**. Làm lại thì **Bỏ chốt**.

**Máy tự làm:** chi thật lớn hơn ứng thì công ty chi bù (**TT_CHI**); ngược lại tài xế nộp lại (**TT_THU**). Chốt hai lần một kỳ bị chặn.

### Bước 21. KT Thu/Chi đẩy chứng từ sang sổ

**Ai:** KT Thu/Chi VC (hoặc Sếp). **Trang:** điều xe. **Màn:** Vận tải → **Phiếu chi · Phiếu thu** → tab **Sổ chứng từ**.

**Thao tác:** xem danh sách tờ *chưa đẩy* (lọc theo loại, theo phiếu) → bấm **Đẩy hết tờ chưa đẩy**, hoặc **Đẩy** ở từng tờ. Máy báo đẩy được bao nhiêu tờ, hỏng bao nhiêu.

**Máy tự làm:** mỗi tờ đẩy đúng một lần; sổ đã có tờ đó thì coi như xong, không gửi trùng; hỏng thì giữ tờ, ghi câu lỗi lên tờ để đẩy lại.

**Máy chặn:** chưa cấu hình địa chỉ sổ kế toán thì báo rõ (Phần 3.3).

**Lưu ý:** tờ kho, tờ lệnh sửa chữa, tờ bán hàng, từ đợt 7a **hoá đơn HD, phiếu thu PT** và từ đợt 7b **phiếu chi trả chủ xe PC_CX** **không nằm ở đây** — chúng sinh ngay ở trang kế toán (Phần 1.3).

### Bước 22. Bên sổ: nhận tờ, ghi bút toán, xem số

**Ai:** kế toán (`ketoan`), kế toán trưởng (`ketoantruong`), Sếp; người xem sổ (`xem`, KT Chi phí, KT kho, quỹ, KT Doanh thu) chỉ xem. **Trang:** **kế toán**.

**Máy tự làm khi nhận tờ:** tờ có định khoản và có tiền thì sinh ngay **bút toán đã ghi sổ** (nguồn *Đẩy từ EPL_LAO_REAL*); tờ chỉ có một vế (ngoài bảng, chờ mã) thì ghi đơn; tờ không có tiền (DO, phiếu lĩnh…) chỉ lưu. Muốn sửa bút toán sinh từ tờ thì **sửa tờ ở trang điều xe rồi đẩy lại** — tờ đã nhận không sửa ở sổ.

**Xem số (menu trang kế toán):**

- **Kế toán** (Sổ kế toán): **Nhật ký chung** (lọc theo kỳ, nguồn, tài khoản, ô tìm), **Sổ cái** từng tài khoản, **Cân đối phát sinh** (dòng **Nợ = Có, cân đối**), **Hệ thống tài khoản**.
- **Công nợ**: phải thu khách (1211) theo từng khách, phải trả nhà cung cấp (4021), phải trả chủ xe liên kết (4022).
- **Thu chi** và **Quỹ & TK**: tiền mặt Kíp 1011, ngoại tệ 1012, ngân hàng 1021, 1022.
- **Chuyến xe**: từng phiếu xe — doanh thu, chi phí theo loại, lãi, còn phải thu, tấn hàng nhập / xuất kho bãi.
- **Kho**: nhập / xuất / tồn theo kho nhiên liệu, phụ tùng (đối chiếu với 1371) và hàng khách gửi (tấn, ngoài bảng).
- **Báo cáo**; mỗi màn có nút xuất Excel / PDF.

**Bút toán ghi tay** (khoản không đến từ tờ nào, số dư đầu kỳ): **Ghi tay** → kế toán lập → trạng thái *chờ duyệt* (chưa vào sổ) → **kế toán trưởng** bấm duyệt → *đã ghi sổ*; trả lại thì về *chờ duyệt*; huỷ thì giữ vết.

### Bước 23. Khi nào một chuyến coi là "hoàn tất"

Một phiếu (gom hay giao) hoàn tất khi đủ các điều sau:

1. Trên trang điều xe: mọi mục có chi đã *Đã chi*, phiếu *Đã khoá 🔒*, đã có hoá đơn (lẻ hoặc gộp tháng) và *đã thu* đủ; xe liên kết thì *đã trả chủ xe*.
2. Ở màn **Phiếu chi · Phiếu thu** không còn tờ *chưa đẩy* của phiếu đó.
3. Trên trang kế toán: màn **Chuyến xe** của phiếu đó hiện đủ doanh thu, chi phí, lãi, còn phải thu = 0; **Công nợ** của khách không còn phần của phiếu; **Cân đối phát sinh** vẫn *Nợ = Có*.
4. Riêng phiếu gom: lô trong **Kho hàng** đã được phiếu giao lấy hết, hoặc phần còn lại đã điều chỉnh có lý do.

## 5. Bảng "ai làm tiếp"

Người nhận việc kế tiếp thấy việc ở **Tổng quan → Việc của tôi** (trang điều xe) hoặc ở màn đầu tiên của họ (trang kế toán: Cấp phát có bảng *Chờ cấp*, Lệnh sửa chữa lọc theo trạng thái).

| Sau khi | Trạng thái | Người làm tiếp | Làm ở |
|---|---|---|---|
| Bãi lập phiếu, gửi kiểm | Mục *Đã nhập* | KT Thu/Chi (I–II), KT kho xăng dầu (III), KT Chi phí (IV, VI) | Điều xe · Phiếu xuất xe |
| Bãi in phiếu lĩnh | Phiếu lĩnh *Chờ cấp* | Thủ kho đúng kho | Kế toán · Cấp phát |
| KT Chi phí ghi sổ mục IV | Mục IV *Đã ghi sổ* | Quỹ tiền mặt / Thủ quỹ chi tạm ứng | Kế toán · Cấp phát, hoặc Điều xe · mục IV |
| Quỹ chi tạm ứng | Mục IV *Đã chi* | Tài xế xuất phát | Điều xe · Phiếu của tôi |
| Tài xế khai đổ dầu | Sự cố chờ duyệt | KT kho xăng dầu (hoặc Bãi) | Điều xe · Theo dõi tuyến |
| Tài xế báo hỏng | Sự cố chờ duyệt | Tổ sửa chữa | Điều xe · Theo dõi tuyến |
| Tổ sửa chữa duyệt báo hỏng | Mục V *Đã nhập* | KT Chi phí kiểm, ghi sổ; rồi Quỹ chi | Điều xe · Phiếu xuất xe |
| Xe gom tới bãi | Lô trong kho bãi | Bãi lập phiếu giao lấy lô; kế toán điều chỉnh nếu cần | Điều xe · Phiếu xuất xe; Kế toán · Kho hàng |
| Xe tới nơi, các mục xong | *Đã giao hàng* | KT Thu/Chi khoá phiếu | Điều xe · Phiếu xuất xe |
| Phiếu khoá | *Đã khoá 🔒* | KT Doanh thu (hoá đơn, thu); Quỹ (trả chủ xe); KT Chi phí (tất toán) | Hoá đơn, thu, trả chủ xe: Kế toán · Tiền vận chuyển. Tất toán: Điều xe |
| Tất toán xong | Tờ *chưa đẩy* | KT Thu/Chi đẩy chứng từ | Điều xe · Phiếu chi · Phiếu thu |
| Đẩy xong | Bút toán *đã ghi sổ* | Kế toán, kế toán trưởng xem sổ, duyệt ghi tay | Kế toán · Kế toán, Công nợ, Chuyến xe |

## 6. Việc ngoài chuyến

### 6.1. Kho nhiên liệu — trang kế toán, Kho → Kho nhiên liệu

**Ai:** KT kho xăng dầu, KT Thu/Chi (nhập, chuyển, xuất). Admin Thà Bốc xem số lít, không thấy giá. Thủ kho xem.

- **Nhập dầu vào một kho:** **Nhập kho** → chọn kho, nhà cung cấp, số đơn mua, số lít, đơn giá, tiền tệ, tỷ giá lúc nhập → lưu. Giá nhập quy Kíp theo tỷ giá **lúc nhập**; giá bình quân của kho tính lại. Sinh **PNK_NL** (Nợ 1371 / Có 4021).
- **Chuyển kho:** **Chuyển kho** → kho đi, kho nhận, số lít → lưu. Hai dòng sổ cùng một số `CK-YYMM-###`, mang giá bình quân của kho đi. Sinh **CK_NL** (không định khoản — dầu chỉ đổi chỗ). Chặn: chuyển quá tồn, kho đi trùng kho nhận.
- **Xuất tay cho xe (ngoài phiếu):** **Xuất cho xe** → kho, số xe, số lít. Giá = bình quân kho. Chặn: xuất quá tồn của đúng kho.
- **Mua dầu Việt Nam qua KHO XE (A3):** nhập 1.000 L vào kho xe (VND) → phiếu xuất xe lấy 600 L với nơi đổ = kho xe → chuyển 400 L còn lại về Thà Bốc hay một kho hiện trường.
- **Xem:** bảng **Tồn theo kho** (bấm một kho để lọc sổ), sổ dầu từng dòng; ô chọn **Kho** trên cùng.

### 6.2. Điểm đổ nhiên liệu — trang kế toán, Kho → Điểm đổ nhiên liệu

**Ai:** Admin Thà Bốc, KT Thu/Chi, KT kho xăng dầu. Thêm, sửa kho của EPL và trạm bán dầu (gắn nhà cung cấp). Lưu thì bản chép bên trang điều xe đổi theo ngay (ô **Nơi đổ** trên phiếu). Kho đã có trong sổ dầu hay đã dùng trên phiếu thì chỉ được **ngưng dùng**, không xoá.

### 6.3. Kho phụ tùng — trang kế toán, Kho → Kho phụ tùng

**Ai:** thủ kho phụ tùng (`khopt`). **Thêm** phụ tùng mới; ở từng dòng **Nhập kho** (số lượng + đơn giá, giá bình quân tính lại, sinh PNK_PT), **Xuất cho xe** (sinh PXK_PT), **Sửa**. Tồn dưới mức tối thiểu tô đỏ. Admin Thà Bốc, tổ sửa chữa xem được, không có nút.

### 6.4. Lệnh sửa chữa (xe nằm xưởng, bảo dưỡng định kỳ) — trang kế toán, Kho → Lệnh sửa chữa

Không gắn phiếu xuất xe nào, nhưng đi đúng chuỗi duyệt của mục V.

1. **Tổ sửa chữa** (`totsua`): bấm **+ Lệnh sửa chữa** → chọn **Số xe** (danh mục xe lấy từ trang điều xe), **Loại** (sửa chữa / bảo dưỡng), ngày, km, gara (trống = làm tại Thà Bốc), ghi chú → **Lưu**. Máy báo xe **vào xưởng** bên trang điều xe (xe *đang sửa*; xe đang chạy chuyến thì giữ nguyên).
2. Máy mở ngay hộp **Thêm dòng chi**: **Nguồn** = **Lấy từ kho** thì chọn **Phụ tùng trong kho** (trừ tồn ngay, sinh PXK_PT Nợ 614 / Có 1371); **Mua ngoài** thì ghi khoản mục, số lượng, đơn giá, tiền tệ → **Lưu**. Thêm dòng nữa: mở lệnh bằng **Xem** → **+ Thêm dòng chi**.
3. **KT Chi phí** (`ketoancp`): **Xem** lệnh → **Xác nhận kiểm tra** → **Ghi sổ kế toán**; sai thì **Trả lại sửa**.
4. **Quỹ tiền mặt** (`quytb`): **Xem** lệnh → **Xác nhận đã chi**. Sinh **PC_SC** chỉ gồm khoản **mua ngoài** (Nợ 614 / Có 1011), vào sổ ngay. Hết lệnh mở của xe thì xe **về rảnh** bên trang điều xe.

Chặn: chỉ tổ sửa chữa lập, sửa lệnh; lệnh đã kiểm thì phải trả lại mới sửa; dòng đã xuất kho không xoá được; trang điều xe tắt thì không lập được lệnh mới.

### 6.5. Bán hàng (phụ tùng, dầu cho bên ngoài) — trang kế toán, Kho → Bán hàng

1. **Lập phiếu** (KT Thu/Chi, KT Doanh thu, KT kho xăng dầu): **Lập phiếu bán** → ngày → **Người mua**: **Khách hàng** (chọn khách hoặc gõ tên) hay **Chủ xe liên kết — trừ vào tiền trả** (chọn chủ xe) → tiền tệ → **+ Phụ tùng** / **+ Dầu kho** (chọn phụ tùng hay kho dầu, số lượng, đơn giá bán) → **Lập phiếu · xuất kho**.
2. Máy xuất kho theo **giá vốn bình quân** và sinh cùng lúc **PXK_BAN** (Nợ 607 / Có 1371) và **HD_BAN** (Nợ 1211 / Có 70; chủ xe mua thì Nợ 4022). Một dòng hỏng (hết hàng) thì cả phiếu không lập, không trừ kho oan.
3. **Thu tiền** (KT Doanh thu, quỹ): **Đã thu** → xác nhận → **PT_BAN** (Nợ 1011 / Có 1211).
4. Phiếu **chủ xe mua ở quầy**: không thu tiền mặt; đợt trả chủ xe kế tiếp tự trừ (bước 19), phiếu thành *Đã trừ*.
5. **Xoá** phiếu chưa thu: hàng về kho, tờ rút theo. Đã thu hay đã trừ thì không xoá được. **Sổ chứng từ**: mở Nhật ký chung lọc theo số phiếu bán.

### 6.6. Việc còn ở trang điều xe

- **Thẻ cao tốc** (Danh mục → Thẻ cao tốc): KT Thu/Chi lập thẻ (của khách hay của EPL), quỹ / kế toán nạp tiền; thẻ trừ đúng một lần lúc ghi sổ mục IV; thẻ của khách cuối tháng cấn trừ vào cước khách đó. Điều chỉnh số dư phải có lý do.
- **Trạm dầu Việt Nam ghi nợ, trả nhà cung cấp** (Vận tải → Theo dõi nhà cung cấp): gắn trạm với khách được cấn trừ; cuối tháng trả trạm (**PC_NCC**) hoặc cấn trừ vào cước khách.
- **Tỷ giá** (Danh mục → Tỷ giá), **bảng giá khách × tuyến** (Danh mục → Khách hàng), **điều khoản chủ xe** và **hợp đồng thuê xe** (Vận tải → Xe liên kết — tiền trả chủ xe ở trang kế toán, bước 19).

## 7. Danh mục chứng từ

| Mã | Tên | Sinh lúc | Sinh ở trang | Về sổ | Định khoản chính |
|---|---|---|---|---|---|
| DO | Phiếu xuất xe | Lập phiếu | Điều xe | Đẩy | Không (chỉ lưu) |
| PLNL | Phiếu lĩnh nhiên liệu | Bấm Phiếu lĩnh nhiên liệu | Điều xe | Đẩy | Không |
| PTU | Phiếu tạm ứng đi đường | Bấm Phiếu chi tạm ứng | Điều xe | Đẩy | Không |
| PC_TU | Phiếu chi tạm ứng | Quỹ chi mục IV | Điều xe | Đẩy | Nợ chi phí 625 (xe liên kết 4022) / Có tiền |
| PC_SC | Phiếu chi sửa chữa · chi khác | Quỹ chi mục V, VI | Điều xe | Đẩy | Nợ 614 · 625 / Có tiền |
| PC_SC | (của lệnh sửa chữa) | Quỹ chi lệnh sửa chữa | Kế toán | Ngay | Nợ 614 / Có tiền |
| PXK_NL | Xuất kho nhiên liệu | Thủ kho cấp, hoặc ghi sổ mục III | Kế toán | Ngay | Nợ 625 (4022) / Có 1371 |
| PNK_NL | Nhập kho nhiên liệu | Nhập kho dầu | Kế toán | Ngay | Nợ 1371 / Có 4021 |
| CK_NL | Chuyển kho nhiên liệu | Chuyển kho | Kế toán | Ngay | Không (đổi chỗ trong 1371) |
| PXK_PT | Xuất kho phụ tùng | Mục V lấy kho, lệnh sửa chữa, xuất tay | Kế toán | Ngay | Nợ 614 (4022 · 625) / Có 1371 |
| PNK_PT | Nhập kho phụ tùng | Nhập kho phụ tùng | Kế toán | Ngay | Nợ 1371 / Có 4021 |
| PNK_HH | Nhập kho hàng (quặng khách gửi) | Xe gom tới bãi | Kế toán | Ngay | Ngoài bảng, tính bằng tấn |
| PXK_HH | Xuất kho hàng | Lưu phiếu giao lấy lô | Kế toán | Ngay | Ngoài bảng, tính bằng tấn |
| DC_HH | Điều chỉnh kho hàng | Kế toán điều chỉnh lô | Kế toán | Ngay | Ngoài bảng |
| HD | Hoá đơn vận chuyển | Lập hoá đơn (lẻ, gộp tháng) | Kế toán (từ đợt 7a) | Ngay | Nợ 1211 / Có 70 |
| PT | Phiếu thu | Mỗi lần thu, cấn trừ | Kế toán (từ đợt 7a) | Ngay | Nợ tiền / Có 1211 |
| PC_CX | Trả chủ xe liên kết | Quỹ trả (một tờ mỗi đợt) | Kế toán (từ đợt 7b) | Ngay | Nợ 4022 / Có tiền |
| TT_CHI · TT_THU | Tất toán tài xế | Chốt tất toán | Điều xe | Đẩy | Chi bù / thu lại |
| PC_NCC | Trả nhà cung cấp | Trả nhà cung cấp | Điều xe | Đẩy | Nợ 4021 / Có tiền |
| PXK_BAN | Xuất kho bán hàng | Lập phiếu bán | Kế toán | Ngay | Nợ 607 / Có 1371 |
| HD_BAN | Hoá đơn bán hàng | Lập phiếu bán | Kế toán | Ngay | Nợ 1211 (chủ xe: 4022) / Có 70 |
| PT_BAN | Phiếu thu bán hàng | Bấm Đã thu | Kế toán | Ngay | Nợ tiền / Có 1211 |

Mã tiền: tiền mặt Kíp 1011, tiền mặt ngoại tệ 1012, ngân hàng Kíp 1021, ngân hàng ngoại tệ 1022. Mã hàng khách gửi và mã giá vốn khác 607 là hai ô cấu hình, Sếp đặt ở trang điều xe: Phiếu chi · Phiếu thu → **Cấu hình**. Trang Quy trình & trách nhiệm (Hệ thống) có tab danh mục chứng từ với đủ mọi trường hợp định khoản, tính bằng chính hàm ghi sổ.

## 8. Khi mất mạng hoặc một trang tắt

| Việc | Nếu trang kia tắt |
|---|---|
| Thủ kho cấp dầu, quỹ chi tạm ứng ở Cấp phát (trang kế toán) | Vẫn làm: dùng bản lưu trong máy, việc vào hàng đợi, tự gửi khi nối lại |
| Tài xế ký nhận giao hàng trên điện thoại | Vẫn làm: bản ký vào hàng đợi, có mạng tự gửi |
| Lập / sửa phiếu không đụng kho (ghi chú, xe, tài xế…) | Vẫn làm bình thường |
| Lưu phiếu giao có lấy lô; báo xe gom tới bãi | Chặn, báo rõ; không có phiếu hay dòng kho nửa vời |
| Ghi sổ mục III có dầu kho; mục V lấy phụ tùng kho | Chặn, báo rõ |
| Xoá phiếu có dầu, phụ tùng, hàng đã xuất | Chưa xoá được |
| Mở phiếu gom | Vẫn mở, chỉ thiếu số tồn lô |
| Màn Xe → tab Sửa chữa | Vẫn mở, ghi rõ phần lệnh sửa chữa chưa lấy được |
| Màn Xe liên kết, trả chủ xe, huỷ đợt trả (trang kế toán) | Chặn, báo rõ; không lưu gì |
| Danh mục chủ xe, hợp đồng thuê xe (trang điều xe) | Vẫn mở — không cần trang kế toán |
| Thêm / sửa điểm đổ, phụ tùng (trang kế toán) | Không lưu, báo rõ |
| Lập lệnh sửa chữa, lập phiếu bán (trang kế toán) | Không lập được phiếu mới; vẫn xem được danh sách |
| Lập hoá đơn, gộp tháng, ghi thu, xoá lần thu (trang kế toán) | Chặn, báo rõ; không lưu gì |
| Công nợ khách, ghi cấn trừ tháng (trang điều xe) | Chặn, báo rõ |
| Bảng cấn trừ, phiếu, báo cáo bên điều xe | Vẫn mở — đọc bản chép *đã xuất hoá đơn · đã thu · đã trả chủ xe* trên phiếu |
| Đẩy chứng từ | Tờ giữ nguyên *chưa đẩy*, ghi câu lỗi; đẩy lại sau |

## 9. Đã dời những gì, và đợt 7 sẽ dời gì

| Đợt | Nội dung | Dữ liệu |
|---|---|---|
| 1 | Nền móng: vai điều xe ở trang kế toán, bộ nạp module, đường liên thông | Tài khoản chép sang, cùng tên |
| 2 | Điểm đổ nhiên liệu | Bản gốc ở kế toán, bên điều xe còn bản chép |
| 3 | Kho phụ tùng | Tồn, giá, sổ ở kế toán; bên điều xe còn danh mục |
| 4 | Kho nhiên liệu, Cấp phát | Sổ dầu ở kế toán; phiếu lĩnh vẫn ở điều xe |
| 5 | Kho hàng | Sổ kho hàng ở kế toán; dòng hàng vẫn trên phiếu |
| 6a | Lệnh sửa chữa | Lệnh ở kế toán; mục V vẫn trên phiếu |
| 6b | Bán hàng | Phiếu bán ở kế toán; đợt trả chủ xe hỏi sang |
| 7a | Hóa đơn vận chuyển, Hoá đơn gộp tháng, sổ thu tiền, in phiếu thu | Hoá đơn, lần thu ở kế toán; phiếu bên điều xe giữ bản chép (đã xuất hoá đơn, số tờ gộp, đã thu, ngày thu) |
| 7b | Xe liên kết: chờ trả theo chủ xe, Trả gộp, Trả chủ xe từng phiếu, bảng xe liên kết theo tháng; Sếp huỷ đợt trả | Đợt trả ở kế toán (cùng mã); phiếu bên điều xe giữ bản chép *đã trả chủ xe*; danh mục chủ xe, hợp đồng thuê xe ở lại điều xe |

**Phần còn lại của đợt 7:** 7c Tiền chuyến & tiền nước tài xế và Tất toán tài xế, 7d Theo dõi nhà cung cấp — dời sang trang kế toán, dữ liệu dời hẳn. Khi đó bước 20–21 của Phần 4 cũng làm ở trang kế toán; tài liệu này sẽ cập nhật lại.

**Một chỗ khác trước (7a):** trên dòng thời gian của báo cáo xu hướng, phiếu nằm trong **hoá đơn gộp tháng** nay có đủ mốc *Hoá đơn* và *Thanh toán* (trước đây để trống vì tờ gộp không gắn với phiếu nào).
