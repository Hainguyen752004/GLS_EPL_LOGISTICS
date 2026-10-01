# Luồng nghiệp vụ EPL Lào từ A đến Z — trang điều xe và trang kế toán

Viết cho anh (chủ dự án), cập nhật **30/09/2026** (sau buổi báo cáo sếp), trước đó 29/09 sau khi làm xong đợt 7: mọi màn kho và tiền đã dời sang trang kế toán, trang điều xe giữ việc của chuyến xe và các danh mục. Tài liệu đi từ lúc Bãi lập **phiếu gom** ở mỏ cho tới lúc mọi tờ chứng từ của chuyến đã **vào sổ kế toán**. Mỗi bước ghi rõ: **ai làm**, làm ở **trang nào**, **màn nào**, **bấm nút nào** (đúng chữ trên nút), máy tự làm gì, máy chặn gì, sinh ra tờ gì, và **ai làm tiếp**.

**Cách đọc:** Phần 1–3 là bức tranh chung và cách đi lại giữa hai trang, đọc một lần. Phần 4 là luồng chính một chuyến, đi từng bước. Phần 5–9 là bảng tra cứu: ai làm tiếp, việc ngoài chuyến, danh mục chứng từ, khi mất nối, và những gì đã dời. **Phần 10 là kịch bản test tay** theo đúng thứ tự luồng, mỗi ca một dòng (ai · bấm gì · thấy gì là đúng), có ô đánh dấu **Đạt** — bắt đầu test từ 10.0.

**Quy ước chữ trong tài liệu:** tên nút và ô viết **đậm** đúng như trên màn hình (bản tiếng Việt). Đường đi viết dạng Menu → Màn → Nút. Mật khẩu mọi tài khoản demo là `1234`.

**Đổi tên hai phiếu (29/09/2026):** phiếu của trang điều xe chỉ là phiếu **đề nghị** — *Phiếu lĩnh nhiên liệu* nay là **Phiếu đề nghị xuất nhiên liệu** (ໃບສະເໜີເບີກນໍ້າມັນ · Fuel issue request); nút *Phiếu chi tạm ứng* và tờ *Phiếu tạm ứng đi đường* nay là **Phiếu đề nghị tạm ứng** (ໃບສະເໜີເບີກເງິນລ່ວງໜ້າ · Advance request). Mã trên tờ giữ nguyên (`PLNL-…`, `PTU-…`). Trang kế toán đổi chữ theo (màn **Cấp phát**: tab **Phiếu đề nghị xuất nhiên liệu**, **Phiếu đề nghị tạm ứng**); tờ đã đẩy sang sổ trước ngày đổi vẫn mang tên cũ. Tiền **chi thật** cũng gọi theo phiếu đề nghị của nó: tờ quỹ chi **PC_TU** là **Phiếu chi theo đề nghị tạm ứng**; ở màn **Chuyến xe** (trang kế toán) hai nhóm chi phí là **Chi theo đề nghị tạm ứng** và **Dầu cấp theo đề nghị xuất nhiên liệu**.

**Sau buổi báo cáo sếp (30/09/2026):** bên mình **chỉ làm logistics** — phiếu của trang điều xe là phiếu **đề nghị**; việc kho thật (xuất, nhập, tồn) do bên kho (**anh Toàn**), công nợ · thu chi · phiếu thu do bên công nợ (**anh Tune**); hai bên nhả API, bên mình **xem**. Trang kế toán (8030) chạy **tạm** thay hai hệ đó cho tới khi có API. Trên trang điều xe:
- **Đề nghị chi** đi theo từng bước của chuyến (tạm ứng, xuất nhiên liệu, chi các mục); **đề nghị thu** sinh **một lần lúc khoá phiếu** (DO xong) — tờ mới **PDT · Phiếu đề nghị thu**, gửi bên công nợ lập SO, hoá đơn, thu tiền (bước 17, 18).
- Màn *Phiếu chi · Phiếu thu* tách thành **Phiếu đề nghị chi** và **Phiếu đề nghị thu**; sổ chứng từ nằm ở màn **Đề nghị theo DO** → tab **Hồ sơ gửi kế toán** (mỗi DO một dòng: đề nghị chi gì, đề nghị thu gì, trạng thái).
- Nhóm **Mô-đun kho** có màn **Xem kho** — chỉ xem, theo mặt hàng (6.7).
- Màn **Phiếu xuất xe** dàn **hai cột**: tờ phiếu bên trái; **cột bên phải** giữ nhãn **Gom / Giao**, danh sách mục **I … VI**, tiền tóm tắt, ba nút phiếu đề nghị, việc mức phiếu. Phiếu mới có **hai thẻ lớn** chọn Gom / Giao. Màn tài xế **Phiếu của tôi** thành **vé chuyến** (bước 10).

## Mục lục

- **1.** Bức tranh chung: hai trang, mỗi trang giữ gì
- **2.** Tài khoản và đăng nhập; **2.1** mở nhiều tab, mỗi tab một tài khoản
- **3.** Đi lại giữa hai trang: nút bấm, máy tự gọi, cài đặt nối, khi một trang tắt
- **4.** Luồng chính A → Z: phiếu GOM mỏ → bãi, phiếu GIAO bãi → cảng, rồi tới sổ kế toán
- **5.** Bảng "ai làm tiếp"
- **6.** Việc ngoài chuyến: kho, lệnh sửa chữa, bán hàng, nhà cung cấp, thẻ cao tốc
- **7.** Danh mục chứng từ: sinh lúc nào, ở trang nào, về sổ bằng đường nào
- **8.** Khi mất mạng hoặc một trang tắt
- **9.** Đã dời những gì sang trang kế toán, cái gì ở lại
- **10.** Kịch bản test tay: chuẩn bị, **10.0b đi thử một chuyến mới A → Z từng cú bấm**, **10.0c hai phiếu mẫu đã đi trọn để xem bằng nhiều vai và xem sổ**, rồi 69 ca theo thứ tự luồng

## 1. Bức tranh chung

### 1.1. Hai trang web

EPL Lào chạy trên **hai trang web riêng**, hai cơ sở dữ liệu riêng, nói chuyện với nhau qua đường liên thông có khoá:

| Trang | Tên trong mã | Máy của anh | Giữ những gì |
|---|---|---|---|
| **Trang điều xe** | EPL_LAO_REAL · DB `epl_lao` | cổng **8020** | Việc của **chuyến xe**: Tổng quan, Theo dõi phiếu vận chuyển, Theo dõi tuyến, **Phiếu xuất xe**, Phiếu của tôi (tài xế), danh mục Xe · Tài xế · Tuyến đường · Khách hàng · Thẻ cao tốc · Tỷ giá, Quy trình, Tài khoản. Ba màn phiếu đề nghị (30/09): **Phiếu đề nghị chi** (tìm, xem, in tờ đề nghị tạm ứng · đề nghị xuất nhiên liệu), **Phiếu đề nghị thu** (tờ đề nghị thu của DO đã khoá, trạng thái bên công nợ), **Đề nghị theo DO** (mỗi DO một dòng; tab **Hồ sơ gửi kế toán** là sổ chứng từ). Nhóm **Mô-đun kho** có màn **Xem kho** (chỉ xem). Màn **Xe liên kết** chỉ còn danh mục chủ xe (điều khoản) và hợp đồng thuê xe; màn **Nhà cung cấp** chỉ còn danh mục nhà cung cấp. **Không còn màn tiền nào** — từ đợt 7 mọi màn tiền ở trang kế toán |
| **Trang kế toán** | EPL_KETOAN · DB `epl_ketoan` | cổng **8030** | Nhóm **Kho** (Kho hàng, Cấp phát, Kho nhiên liệu, Điểm đổ nhiên liệu, Kho phụ tùng, Lệnh sửa chữa, Bán hàng), nhóm **Tiền vận chuyển** (Hóa đơn vận chuyển, Hoá đơn gộp tháng — đợt 7a; Xe liên kết — đợt 7b; Tiền chuyến & tiền nước tài xế, Tất toán tài xế — đợt 7c; Theo dõi nhà cung cấp — đợt 7d) và phần **sổ**: **Tổng quan**, **Tiền & công nợ** (Thu chi, Công nợ, Quỹ & TK), **Chuyến & kho** (Chuyến xe, Kho), **Sổ sách** (Kế toán, Ghi tay, Báo cáo), **Cài đặt**; tờ chứng từ trang điều xe đẩy sang được nhận tự động |

Ngày 28/09 anh chốt trang điều xe không xem được kho; **ngày 30/09 sếp đổi lại**: trang logistics có màn **Xem kho** — chỉ xem, theo mặt hàng; mọi **thao tác** kho và (từ đợt 7) tiền vẫn ở trang kế toán (tạm thay hệ của anh Toàn, anh Tune). Riêng việc **kiểm và duyệt từng mục trên phiếu xuất xe vẫn làm ngay trên phiếu** ở trang điều xe, vì phiếu là DO đang mở của chuyến.

### 1.2. Một chuyến đi qua những ai

Tóm tắt một chuyến trọn luồng (chi tiết từng bước ở Phần 4):

1. **Admin Thà Bốc** lập phiếu xuất xe (gom hoặc giao), ghi dầu, tiền đi đường, in phiếu đề nghị xuất nhiên liệu và phiếu đề nghị tạm ứng, gửi kiểm.
2. **Kế toán Viêng Chăn** kiểm từng mục và nhập giá: KT Thu/Chi kiểm mục I–II, KT kho xăng dầu mục III, KT Chi phí mục IV–VI.
3. **Thủ kho** cấp dầu theo phiếu đề nghị xuất nhiên liệu; **quỹ** chi tiền tạm ứng cho tài xế (cả hai ở màn **Cấp phát** trang kế toán).
4. **Tài xế** xuất phát, báo mốc, **báo cân ở mỏ** (phiếu gom), đổ dầu dọc đường, báo hỏng, giao hàng và ký nhận trên điện thoại.
5. **Admin Thà Bốc** báo xe tới, nhập cân cuối. Phiếu gom thì hàng vào **kho bãi**; phiếu giao thì hàng ra khỏi kho bãi.
6. **KT Thu/Chi** kiểm lại toàn phiếu rồi **khoá**.
7. Khoá xong máy lập **phiếu đề nghị thu**; bên công nợ (bây giờ là **KT Doanh thu** ở **trang kế toán** tạm) lập hoá đơn, ghi thu tiền khách. **Quỹ** trả chủ xe liên kết, **KT Chi phí** tất toán tài xế và trả nhà cung cấp — cũng ở **trang kế toán**.
8. **KT Thu/Chi** đẩy chứng từ sang sổ; **trang kế toán** nhận tờ và tự ghi bút toán. **Kế toán trưởng** duyệt bút toán ghi tay nếu có.

### 1.3. Tờ chứng từ về sổ bằng hai đường

- **Đường 1 — tờ sinh ở trang điều xe** (DO, phiếu đề nghị xuất nhiên liệu, phiếu đề nghị tạm ứng, **phiếu đề nghị thu**, phiếu chi mục IV–VI): nằm ở màn **Đề nghị theo DO** → tab **Hồ sơ gửi kế toán** với trạng thái *chưa đẩy*, tới khi KT Thu/Chi bấm **Đẩy hết tờ chưa đẩy**. Sổ nhận tờ nào thì tự sinh bút toán tờ đó.
- **Đường 2 — tờ sinh ngay ở trang kế toán** (mọi tờ kho: nhập / xuất / chuyển dầu, phụ tùng, kho hàng; tờ của lệnh sửa chữa và bán hàng; từ đợt 7a cả **hoá đơn HD** và **phiếu thu tiền khách PT**, từ đợt 7b **phiếu chi trả chủ xe PC_CX**, từ đợt 7c **tờ tất toán TT_CHI / TT_THU**, từ đợt 7d **phiếu chi trả nhà cung cấp PC_NCC**): vào sổ **ngay lúc làm việc**, không cần đẩy. Trong sổ, các bút toán này mang nguồn *Sinh ở kho (trang kế toán)* hoặc *Sinh ở tiền vận chuyển (trang kế toán)*.

## 2. Tài khoản và đăng nhập

Hai trang dùng **cùng tên đăng nhập và cùng mật khẩu**, nhưng **đăng nhập riêng từng trang**: vào trang điều xe không tự đăng nhập trang kế toán. Muốn mở nhiều người cùng lúc, mỗi tab một tài khoản: xem **2.1** ngay dưới bảng.

| Tên đăng nhập | Vai | Ở trang điều xe làm gì | Ở trang kế toán làm gì |
|---|---|---|---|
| `admin` | Sếp | Mọi việc, cấu hình, tài khoản, mở khoá mục | Mọi việc, cấu hình liên thông, duyệt |
| `thabok` | Admin Thà Bốc | Lập phiếu, dầu, đi đường, gửi kiểm, báo mốc, báo tới, đổi xe; duyệt báo chậm, bị giữ xe, việc khác của tài xế (mục VI, từ 01/10) | Kho hàng (xem), Cấp phát (xem), Kho nhiên liệu (xem lít, không thấy giá), Điểm đổ (sửa), Kho phụ tùng (xem, không giá). Không mở sổ |
| `ketoan` | KT Thu/Chi Viêng Chăn | Kiểm mục I–II, nhập số phiếu quặng và giá cước, khoá phiếu, đẩy chứng từ, điều khoản chủ xe | Vai sổ **kế toán** (xem sổ, lập bút toán ghi tay); Kho hàng (điều chỉnh tồn), Kho nhiên liệu (nhập, chuyển), Bán hàng (lập), Điểm đổ |
| `ketoancp` | KT Chi phí VC | Nhập giá, kiểm, ghi sổ mục IV, V, VI; danh mục nhà cung cấp (thêm, sửa, gắn trạm với khách) | Xem sổ; Lệnh sửa chữa (kiểm, ghi sổ, trả lại); **Tất toán tài xế** (chốt, bỏ chốt); **Theo dõi nhà cung cấp** (trả); Tiền chuyến & tiền nước (xem) |
| `khonl` | KT kho xăng dầu VC | Nhập giá dầu mua ngoài, kiểm, ghi sổ mục III; duyệt khai đổ dầu dọc đường | Xem sổ; Kho nhiên liệu (nhập, chuyển, xuất tay), Cấp phát (cấp dầu mọi kho), Điểm đổ, Bán hàng (lập) |
| `khotb` · `khovc` | Thủ kho nhiên liệu (một kho: Thà Bốc · Viêng Chăn) | Màn **Xem kho** (chỉ xem: tồn từng kho, đề nghị chờ cấp) — cấp dầu ở trang kế toán | Cấp phát (chỉ phiếu đề nghị xuất nhiên liệu của kho mình), Kho nhiên liệu (xem) |
| `khopt` | Thủ kho phụ tùng Thà Bốc | Màn Xe | Kho phụ tùng (thêm, nhập, xuất, sửa) |
| `totsua` | Tổ sửa chữa Thà Bốc | Theo dõi tuyến (duyệt báo hỏng xe, lốp, tai nạn → mục V), Phiếu xuất xe (mục V), Xe | Lệnh sửa chữa (lập, thêm dòng), Kho phụ tùng (xem) |
| `quytb` | Quỹ tiền mặt cảng cạn | Chi mục V, VI (mục IV — tạm ứng — chi ở hệ kế toán anh Tune từ 01/10, bước 9) | Xem sổ; Cấp phát (chi tạm ứng), Lệnh sửa chữa (chi), Bán hàng (ghi thu); **Xe liên kết** (trả chủ xe); **Tất toán tài xế** (chốt); **Theo dõi nhà cung cấp** (trả) |
| `quyvc` | Thủ quỹ VC | Chi mục III (dầu mua ngoài) | Xem sổ; Cấp phát (chi tạm ứng), Bán hàng (ghi thu); **Xe liên kết** (trả chủ xe); **Tất toán tài xế** (chốt); **Theo dõi nhà cung cấp** (trả) |
| `doanhthu` | KT Doanh thu VC | Xem phiếu, công nợ khách | Xem sổ; **Hóa đơn vận chuyển**, **Hoá đơn gộp tháng** (lập hoá đơn, ghi thu, xoá lần thu); **Theo dõi nhà cung cấp** (ghi cấn trừ tháng); Bán hàng (lập, ghi thu) |
| `tx01` · `tx02` · `tx03` | Tài xế | Chỉ màn **Phiếu của tôi** trên điện thoại | Không có tài khoản |
| `ketoantruong` | Kế toán trưởng | — | Duyệt bút toán ghi tay |
| `xem` | Chỉ xem sổ | — | Xem sổ |

**Đăng nhập trang điều xe:** mở `http://<máy chủ>:8020`, bấm vào tên người ở danh sách hoặc gõ tên đăng nhập, mật khẩu `1234`, bấm **Đăng nhập**. Người thường vào thẳng màn đầu tiên của mình; tài xế vào **Phiếu của tôi**.

**Đăng nhập trang kế toán:** mở `http://<máy chủ>:8030`, gõ tên và mật khẩu, bấm đăng nhập. Người có vai sổ vào thẳng **Kế toán** (Sổ kế toán, Nhật ký chung); người vận hành (thủ kho, tổ sửa chữa, Admin Thà Bốc) vào thẳng màn đầu tiên của mình trong nhóm **Kho**, không thấy sổ.

### 2.1. Mở nhiều tab, mỗi tab một tài khoản

**Mỗi lần đăng nhập, BỎ TICK ô *Ghi nhớ đăng nhập*** (ô này mặc định có tick, ở cả hai trang). Có tick thì phiên lưu chung cho cả trình duyệt: một tab đăng nhập tài khoản khác là **mọi tab của trang đó** chạy theo tài khoản mới — tab ghi tên "Bãi" bấm nút lại chạy bằng quyền kế toán. Bỏ tick thì mỗi tab giữ tài khoản của riêng nó.

- Mở tab mới bằng **Ctrl+T** rồi gõ địa chỉ; **đừng dùng *Nhân đôi thẻ*** (nhân đôi chép luôn phiên của tab cũ).
- Đổi người trong một tab: bấm tên người ở góc trên phải → **Đổi tài khoản** → đăng nhập lại, **bỏ tick lại**.
- Trang điều xe (8020) và trang kế toán (8030) là hai trang riêng: `ketoan` ở 8020 và `ketoan` ở 8030 là hai tab, không đụng nhau.
- Tài xế: dùng điện thoại là gọn nhất; không có điện thoại thì một tab như trên.
- Cách khác: mỗi người một **cửa sổ ẩn danh** (Ctrl+Shift+N) hoặc một trình duyệt khác.

**Tab này bấm, tab kia có thấy ngay không?** Dữ liệu vào máy chủ **ngay lúc bấm** — ví dụ thủ kho bấm **Cấp dầu** ở 8030 thì phiếu ở 8020 đã có dầu đã cấp. Nhưng tab đang mở **không tự vẽ lại**: sang tab kia bấm **F5** (hoặc bấm lại màn đó trên menu). Hai màn tự tải lại: **Tổng quan** (tick **Tự cập nhật 60 s**) và **Theo dõi tuyến** (tick **Tự cập nhật 30 giây**). Tờ chứng từ vào sổ lúc nào: xem hai đường ở **1.3**.

## 3. Đi lại giữa hai trang

### 3.1. Bằng nút bấm

| Đang ở | Bấm | Mở ra |
|---|---|---|
| Trang điều xe, tài khoản thủ kho dầu (`khotb`, `khovc`) | **Mở trang kế toán** (màn duy nhất của họ bên này) | Trang kế toán, thẻ mới |
| Trang điều xe → **Tổng quan** → ô **Việc của tôi** | Ô việc thuộc trang kế toán (ví dụ phiếu đề nghị xuất nhiên liệu chờ cấp) | Đúng màn đó ở trang kế toán (Cấp phát…), thẻ mới |
| Trang điều xe → **Theo dõi tuyến** → một xe | **Cấp dầu theo phiếu đề nghị** | Màn **Cấp phát** ở trang kế toán |
| Trang điều xe → **Quy trình & trách nhiệm** | Bước có nhãn *ở trang kế toán* | Chỉ là nhãn: bước đó làm ở trang kế toán |
| Trang kế toán → **Kho → Cấp phát** → chọn một phiếu đề nghị xuất nhiên liệu | **Mở phiếu** | Phiếu xuất xe của chuyến đó ở trang điều xe, thẻ mới |
| Trang kế toán → **Kho → Kho hàng** | Bấm một dòng lô hoặc dòng sổ | Màn **Theo dõi phiếu vận chuyển** ở trang điều xe, đã lọc theo số phiếu |
| Trang kế toán → **Kho → Bán hàng** | **Sổ chứng từ** ở một phiếu bán | Sổ kế toán (Nhật ký chung) lọc theo số phiếu bán |
| Trang điều xe → **Phiếu xuất xe** (phiếu đã khoá, vai KT Doanh thu) | **Lập hóa đơn thu ↗** · **Ghi một lần thu ↗** | Màn **Hóa đơn vận chuyển** ở trang kế toán, mở đúng phiếu này |
| Trang điều xe → **Phiếu xuất xe** (khách gộp tháng) | **Gộp hoá đơn tháng ↗** · **Thuộc hoá đơn HDT-… ↗** | Màn **Hoá đơn gộp tháng** ở trang kế toán (đúng tháng, đúng tờ) |
| Trang điều xe → **Phiếu xuất xe** → khung **Sổ thu tiền** | **Mở trang kế toán ↗** | Hoá đơn / tờ gộp của phiếu ở trang kế toán |
| Trang điều xe → **Phiếu xuất xe** → cột bên phải, khối **Phiếu đề nghị** | **Phiếu đề nghị thu** | Màn **Phiếu đề nghị thu** (trang điều xe) ở đúng DO: tờ đề nghị thu, trạng thái hoá đơn · thu bên công nợ |
| Trang điều xe → **Danh mục → Khách hàng** → Công nợ khách | Số tờ gộp (có dấu ↗) | Tờ gộp đó ở trang kế toán |
| Trang kế toán → **Tiền vận chuyển → Hoá đơn gộp tháng** → một tờ | Số phiếu trong bảng *Dòng phiếu trong hoá đơn* | Màn **Hóa đơn vận chuyển** của phiếu đó |
| Trang điều xe → **Phiếu xuất xe** (phiếu xe liên kết đã khoá, vai quỹ) | **Trả chủ xe · <số tiền> ↗** | Màn **Xe liên kết** ở trang kế toán, đúng tháng của phiếu, dòng phiếu tô sáng |
| Trang điều xe → **Vận tải → Xe liên kết** | **Trả chủ xe · bảng xe liên kết ↗** | Màn **Xe liên kết** ở trang kế toán |
| Trang kế toán → **Tiền vận chuyển → Xe liên kết** → bảng *Xe liên kết* | Bấm một dòng phiếu | Màn **Hóa đơn vận chuyển** của phiếu đó |
| Trang điều xe → **Vận tải → Nhà cung cấp** | **Công nợ · trả nhà cung cấp · cấn trừ cuối tháng ↗** | Màn **Theo dõi nhà cung cấp** ở trang kế toán |
| Trang kế toán → **Tiền vận chuyển → Theo dõi nhà cung cấp** (vai KT Chi phí) | **Thêm · sửa nhà cung cấp ↗** | Màn **Nhà cung cấp** (danh mục) ở trang điều xe, thẻ mới |

Mở sang trang kia thì **đăng nhập bên đó** nếu chưa đăng nhập (cùng tên, cùng mật khẩu).

### 3.2. Hai trang tự gọi nhau (người dùng không phải bấm gì)

| Việc người dùng làm | Ở trang | Máy gọi sang trang kia để | Nếu trang kia tắt |
|---|---|---|---|
| Lập / sửa phiếu có dầu **kho** | Điều xe | Lấy giá bình quân của kho dầu | Chưa lưu được dòng dầu kho |
| Ghi sổ mục III | Điều xe | Không gọi sang nữa (từ 30/09): dầu kho chỉ rời kho lúc thủ kho cấp theo phiếu đề nghị; còn dòng dầu kho chưa cấp thì chặn ghi sổ | — |
| Sự cố mục V lấy phụ tùng kho, duyệt báo hỏng | Điều xe | Xuất phụ tùng, sinh PXK_PT | Chặn, báo rõ |
| Phiếu giao chọn lô, lưu phiếu giao | Điều xe | Hỏi lô còn hàng, xuất khỏi kho bãi, sinh PXK_HH | Chặn, báo rõ; lưu việc khác vẫn được |
| Xe gom tới bãi | Điều xe | Nhập hàng vào kho bãi, sinh PNK_HH | Chưa báo tới được |
| Xoá phiếu (Sếp) | Điều xe | Trả dầu, phụ tùng, hàng về kho; rút tờ kho | Chưa xoá được |
| Mở màn Xe → tab Sửa chữa | Điều xe | Lấy lịch sử lệnh sửa chữa của xe | Vẫn mở, ghi rõ phần thiếu |
| Cấp dầu / chi tạm ứng ở **Cấp phát** | Kế toán | Đọc phiếu đề nghị xuất nhiên liệu, ghi "đã cấp" lên phiếu bên điều xe | Việc vào **hàng đợi trong máy**, tự gửi khi nối lại |
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
| Mở **Tiền chuyến & tiền nước tài xế**, **Tất toán tài xế**; **Tất toán**, **Bỏ chốt** | Kế toán | Đọc số từ phiếu (phiếu đề nghị tạm ứng đã cấp, dòng chi tài xế ứng, mục IV) — tính ở trang điều xe | Chặn, báo rõ; không có bản chốt nửa vời |
| Mở **Theo dõi nhà cung cấp** (công nợ, cấn trừ cuối tháng); **Trả nhà cung cấp**, **Ghi cấn trừ tháng** | Kế toán | Đọc danh mục nhà cung cấp, phần phát sinh từ phiếu, bảng cấn trừ (cước · thẻ cao tốc khách · trạm dầu VN) | Chặn, báo rõ; không lưu gì |
| Báo cáo cấn trừ bên điều xe (chỉ đọc) | Điều xe | Lấy phần đã ghi cấn trừ | Vẫn mở; ô *đã ghi* để trống |

### 3.3. Cài đặt nối hai trang (Sếp làm một lần)

Trên máy chủ thật, Sếp làm theo thứ tự này, rồi bấm **Kiểm kết nối** ở cả hai bên:

1. Trang kế toán, đăng nhập `admin` → **Cài đặt** → thẻ **Token nhận chứng từ**: bấm **Chép** để lấy token.
2. Trang điều xe, đăng nhập `admin` → **Hệ thống → Tài khoản** → tab **Liên thông trang kế toán**.
3. Ô **Địa chỉ trang kế toán**: địa chỉ API trang kế toán (ví dụ `http://<máy chủ>:8030`).
4. Ô **Địa chỉ mở trang kế toán (trình duyệt · mã QR)**: địa chỉ mà điện thoại, máy thủ kho mở được. Để trống thì dùng ô trên. Mã QR in trên phiếu đề nghị xuất nhiên liệu dẫn tới địa chỉ này.
5. Ô **Khoá đẩy chứng từ (trang kế toán cấp)**: dán token vừa chép ở bước 1.
6. Bấm **Tạo khoá cho trang kế toán**, chép khoá hiện ra (khoá mới thay khoá cũ ngay), lưu.
7. Sang trang kế toán → **Cài đặt** → thẻ **Liên thông trang điều xe**: ô **Địa chỉ trang điều xe** (ví dụ `http://<máy chủ>:8020`), ô **Khoá do trang điều xe cấp** dán khoá ở bước 6, bấm **Lưu liên thông**.
8. Bấm **Kiểm kết nối** ở trang kế toán: phải hiện *Nối được trang điều xe · … ms · tài khoản … bên đó*. Bấm **Kiểm kết nối** ở tab Liên thông trang điều xe: phải hiện *Nối được trang kế toán · … ms*.

### 3.4. Khi một trang tắt

Quy tắc anh chốt: việc nào **đụng kho hoặc tiền** mà trang kia tắt thì **chặn và báo rõ** (*Chưa nối được trang kế toán — thử lại sau* hoặc *Chưa nối được trang điều xe — thử lại sau*). Không ghi nửa vời, không xếp hàng gửi sau, để hai bên không bao giờ lệch số. Việc **không đụng kho, tiền** vẫn chạy bình thường. Ba việc ngoài hiện trường được giữ hàng đợi trong máy: **Cấp phát** ở kho dầu, **ký nhận giao hàng** và **báo cân ở mỏ** trên điện thoại tài xế. Bảng đầy đủ ở Phần 8.

## 4. Luồng chính A → Z

### 4.0. Ví dụ dùng xuyên suốt

Khách **ຄຳຕຸ້ຍ** thuê chở quặng sắt từ mỏ về bãi Thà Bốc, rồi từ bãi ra cảng. Chuyến tách **hai chặng** (anh Khampla B1–B4):

- **Phiếu GOM** `G4-xxxx-09/EPL`: xe **343** (xe nhà), tài xế `tx01`, tuyến **ກາສີ → ທ່າບົກ**: xe chạy rỗng từ bãi lên mỏ, chở **40 tấn** từ mỏ (ກາສີ) về bãi Thà Bốc (ທ່າບົກ) — 145 km chiều hàng + 145 km chiều về.
- **Phiếu GIAO** `T4-xxxx-09/EPL`: xe **344**, tài xế `tx02`, tuyến **ທ່າບົກ → ທ່າເຮືອກະລໍ**: lấy **25 tấn** từ lô của phiếu gom, chở từ bãi qua cửa khẩu ດ່ານ ນໍ້າພາວ ra cảng, rồi chạy rỗng về bãi — 360 km + 360 km.

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

**Tạm ứng và xuất dầu đi theo LOẠI XE của phiếu** (chủ dự án chốt 29/09). Cùng một phiếu đề nghị, bản chất khác nhau tuỳ xe của ai:

| Phiếu chạy bằng | Tạm ứng (mục IV, VI) | Dầu lấy từ kho (mục III) |
|---|---|---|
| **Xe nhà** (EPL) | **Tạm ứng nội bộ** — Nợ 625 / Có 1011; cuối tháng tất toán với tài xế (bước 20) | **Xuất nội bộ** — Nợ 625 / Có 1371 theo giá vốn bình quân kho |
| **Xe thuê**, dòng *EPL ứng* | **Tạm ứng ghi công nợ chủ xe** — Nợ 4022 / Có 1011; **trừ vào tiền trả chủ xe** (bước 19), **không** tất toán với tài xế | **Xuất bán cho chủ xe** theo **giá bán riêng** — KT kho xăng dầu gõ ở ô **Giá bán cho chủ xe** khi kiểm mục III (bước 6); tiền trừ chủ xe tính theo giá bán |
| **Xe thuê**, dòng *Chủ xe tự trả* | không có đề nghị | không có đề nghị |

Anh nói rõ thêm ngày 30/09: xe thuê **không có "trả cùng lương"** — EPL không trả lương cho tài xế của chủ xe. Mỗi dòng của xe thuê hoặc là *EPL ứng* (tiền mặt khi xe đi — kể cả tiền chuyến, tiền nước — hoặc nợ nhà cung cấp thay chủ xe; đều ghi công nợ chủ xe), hoặc là *Chủ xe tự trả* (không ghi gì). Ví dụ: thuê xe **200**, chủ xe lấy dầu của EPL **50** (xuất bán), EPL ứng tiền **100** → chủ xe nợ EPL **150**, EPL còn trả chủ xe **50** (trước khi trừ phí quản lý và quá tải, bước 19). Màn **Tiền chuyến & tiền nước tài xế** và màn **Tất toán tài xế** chỉ có xe nhà.

**Mọi lần xuất dầu kho phải có phiếu đề nghị đã cấp** (chủ dự án chốt 30/09): dầu kho chỉ rời kho khi thủ kho cấp theo phiếu đề nghị xuất nhiên liệu (bước 8). Ghi sổ mục III không tự xuất kho nữa — còn dòng dầu kho chưa cấp thì máy chặn ghi sổ.

Trên phiếu, đầu mục III và mục IV có một dòng chữ đậm nói bản chất (*Xuất nội bộ — xe công ty (EPL)*, *Xuất bán cho chủ xe · <tên chủ xe>*, *Tạm ứng nội bộ — xe công ty (EPL)*, *Tạm ứng ghi công nợ chủ xe · <tên chủ xe>*); hai tờ đề nghị in ra có đúng dòng đó dưới tiêu đề, và dữ liệu gửi sang hệ kho / tiền mang theo bản chất và chủ xe. Hạch toán **xuất bán** (Nợ 4022 / Có 70 theo giá bán, Nợ 607 / Có 1371 theo giá vốn) là việc bên kho / tiền của anh Toàn, anh Tune; trang kế toán mẫu hiện vẫn ghi PXK_NL xe thuê là Nợ 4022 / Có 1371 theo giá vốn.

### Bước 1. Bãi lập phiếu GOM — mục I và II

**Ai:** Admin Thà Bốc (`thabok`). **Trang:** điều xe. **Màn:** Vận tải → **Phiếu xuất xe** (hoặc Tổng quan → **Tạo phiếu xuất xe**).

**Thao tác:**

1. Bấm **Phiếu mới**. Màn chia **hai cột**: tờ phiếu bên trái; **cột bên phải** có nhãn loại to (**Gom** / **Giao**), số phiếu, danh sách sáu mục **I … VI** kèm chữ trạng thái (bấm mục nào tờ phiếu hiện mục đó; **Toàn phiếu** ở cuối danh sách hiện cả 6 mục một trang, để in), khối **Phiếu đề nghị**, việc mức phiếu. Ngay dưới đầu tờ phiếu có **hai thẻ lớn**: **Gom · Gom (mỏ → bãi)** — *Đi lấy quặng ở mỏ về bãi Thà Bốc — hàng vào kho bãi…* và **Giao · Giao (bãi → khách)** — *Lấy hàng từ kho bãi (hoặc chở thẳng) đi giao cho khách — xong có biên bản giao nhận (POD)*. Bấm thẻ **Gom**: thẻ tô xanh, ô **Loại phiếu** ở mục I đổi theo, số phiếu gợi ý đổi thành `G4-…`.
2. Mục I — **Thông tin xe vận chuyển**: ô **Loại phiếu** đã là **Gom (mỏ → bãi)** (bấm thẻ ở bước 1, hoặc chọn thẳng ở ô này). Chọn **Số xe** 343; biển đầu kéo, biển rơ-moóc, hãng xe tự điền. Chọn **Tài xế** `tx01`. Ghi **Ngày lập phiếu**, **Ngày xe đi**. Ô **Lúc đi** (km) **tự điền** ngay khi chọn xe: đúng số **Công-tơ-mét (km)** của xe ở màn **Xe** — tức km về của chuyến trước, vì mỗi lần Bãi bấm **Xe đã tới** máy ghi km về vào xe. Dưới ô ghi *Điền sẵn theo công-tơ-mét của xe — sửa được*: Bãi nhìn đồng hồ xe lúc lăn bánh, khớp thì để nguyên, lệch (xe chạy ngoài chuyến, đi sửa…) thì gõ lại; đã gõ tay thì đổi xe cũng không bị đè. Xe chưa có công-tơ-mét thì ô để trống, gõ tay. **Km về ước tính** tự tính = lúc đi + km chiều đi + km chiều về của tuyến. Hai ô **Ngày xe về** và **Lúc về** để xám, dưới ô ghi *Điền khi xe về: Báo đã về · Xe đã tới* — chúng có số ở bước 10–12, khi tài xế bấm **Báo đã về** hoặc Bãi bấm **Xe đã tới · nhập cân cuối**.
3. Bấm mục **II · Thông tin vận chuyển & doanh thu** ở danh sách mục (cột bên phải): **Chọn tuyến** **ກາສີ → ທ່າບົກ** — ô chọn ghi *ກາສີ → ທ່າບົກ · 145.0 km · ↩ 145.0 km* (km chiều hàng · km chiều về); điểm đi, điểm đến tự điền; chọn **Khách hàng**; **Loại hàng** Quặng sắt. Phiếu **Gom** lúc lập **chưa có cân** — xe chưa đi thì chưa có số (tờ Excel của họ cũng để trống hai dòng cân lúc lập): ô **Cân tại mỏ (t)** để trống, dưới ô ghi *Bốc xong ở mỏ mới ghi: tài xế bấm Báo cân ở mỏ, hoặc Admin Thà Bốc ghi theo phiếu quặng…*; ô **Cân tại bãi khi về** xám, ghi *Điền khi xe tới: Xe đã tới · nhập cân cuối*. Ô **Hợp đồng vận chuyển** ghi *Lưu phiếu rồi số hợp đồng còn hạn tự điền* — lưu xong máy điền hợp đồng còn hạn của khách lấy ở **Danh mục → Khách hàng** (ví dụ ຄຳຕຸ້ຍ → HDVC-2026-001), khách chưa có thì ghi *Chưa có hợp đồng*; Bãi chỉ xem, kế toán đổi được khi kiểm mục II. Ô **Số phiếu quặng**, **Ngày phiếu quặng** xám — kế toán gõ ở bước 5.
4. Khung **Hàng trên phiếu** chỉ có ở phiếu **Giao** — hàng lấy từ lô nào trong bãi, bao nhiêu tấn (bước 14). Phiếu **Gom** **không có khung này** (từ 29/09): một phiếu gom chở một mặt hàng, như một dòng trong tờ Excel của họ, nên chỉ cần **Loại hàng** và **Cân tại mỏ (t)** — máy tự ghi dòng hàng từ hai ô đó (bước 10b).
5. **Phiếu quặng đính kèm**: có ảnh phiếu quặng thì bấm **Thêm ảnh · PDF** (lưu phiếu rồi mới đính kèm được). Không có ảnh cũng được; kế toán gõ số phiếu quặng ở bước 5.
6. Bấm **Lưu** (nút xanh góc trên bên phải). Máy báo *Đã lưu*; khối *Trạng thái phiếu* ở cột bên phải không còn ghi *Phiếu mới*, đầu mỗi mục hiện nút **Gửi kiểm tra**.

**Máy tự làm:** cấp số `G4-xxxx-MM/EPL`; giá cước theo **bảng giá khách × tuyến** (Bãi không thấy); tỷ giá USD · THB · VND · CNY **khoá vào phiếu** lúc lập; xe chủ xe liên kết thì phiếu tự thành phiếu xe liên kết, điền phí và ngưỡng tấn theo hồ sơ chủ xe; sinh tờ **DO** (phiếu xuất xe). Phiếu gom: ô **Cân tại mỏ** có số thì máy ghi luôn một dòng hàng theo **Loại hàng** (đổi cân, đổi loại hàng thì dòng đổi theo).

**Máy chặn:** Bãi không nhập được giá cước, giá thuê xe, phí, ngưỡng tấn, số phiếu quặng; chưa ai nhập được ngày xe về, km về, cân cuối trước khi xe về.

**Trạng thái sau bước:** phiếu *Đã xuất xe*; mục I, II *Chờ*. Phiếu gom **chưa đụng kho bãi** — hàng chỉ vào kho khi xe về tới bãi (bước 12).

**Ai làm tiếp:** chính Admin Thà Bốc làm bước 2–4.

### Bước 2. Mục III — dầu, và in phiếu đề nghị xuất nhiên liệu

**Ai:** Admin Thà Bốc. **Trang:** điều xe. **Màn:** Phiếu xuất xe, mục III **Chi phí nhiên liệu**.

**Thao tác:**

1. Bấm **Thêm dòng** ở mục III. Mỗi dòng ghi **Lít** và **Nơi đổ**: chọn kho trong nhóm **Kho của EPL (lĩnh)** (ví dụ kho Thà Bốc), hoặc trạm trong nhóm **Trạm bán dầu (mua)**.
2. Xe liên kết: ô **Ai chi** chọn **EPL ứng** hay **Chủ xe tự trả**. Đổ ở trạm Việt Nam mà trạm cho ghi nợ: tick **Ghi nợ tại trạm**.
3. Bấm **Lưu**.
4. Bấm **Phiếu đề nghị xuất nhiên liệu** (cột bên phải, khối **Phiếu đề nghị**). Máy lập mỗi kho một tờ phiếu đề nghị xuất nhiên liệu có **mã QR**, rồi mở màn **Phiếu đề nghị chi** ở tờ đó: danh sách tờ bên trái (tờ đang chọn tô xanh, lọc **Tất cả · Tạm ứng · Nhiên liệu** và **Chờ cấp · Đã cấp · Đã huỷ · Tất cả**, ô tìm số đề nghị / DO / xe / tài xế), tờ in đúng khổ bên phải. Bấm **In**, đưa tài xế cầm tới kho — hoặc tài xế mở mã QR ngay trên **Phiếu của tôi** (bước 10).

**Máy tự làm:** dòng đổ ở **kho EPL** lấy **giá bình quân của đúng kho đó** (hỏi trang kế toán, không ai gõ); dòng đổ ở trạm là nguồn mua, gắn nhà cung cấp của trạm; định khoản gợi ý 625/1371 (kho), 625/4021 (mua), 4022/… (xe liên kết). Tờ **PLNL** sinh lúc bấm phiếu đề nghị xuất nhiên liệu. Phiếu **xe thuê**: dầu kho EPL ứng là **xuất bán cho chủ xe** — đầu mục III ghi rõ, giá bán do KT kho xăng dầu gõ ở bước 6 (bảng *Tạm ứng và xuất dầu theo loại xe* ở 4.0).

**Máy chặn:** Bãi không thấy và không nhập đơn giá dầu, thành tiền, mã tài khoản.

**Ai làm tiếp:** tài xế cầm phiếu đề nghị xuất nhiên liệu tới kho → **thủ kho** cấp dầu (bước 8).

### Bước 3. Mục IV đi đường, mục VI chi khác, và in phiếu đề nghị tạm ứng

**Ai:** Admin Thà Bốc. **Trang:** điều xe. **Màn:** Phiếu xuất xe, mục IV **Chi phí đi đường** và mục VI **Chi phí khác**.

**Thao tác:**

1. Mục IV → **Thêm dòng**: chọn **Khoản mục** (tiền ăn, tiền nước, chi phí sang Việt Nam, điện thoại, chipping…) và **SL**. Không có trong danh sách thì chọn **Khác (tự gõ)…**. SL đếm theo gì: xem bảng ngay dưới. Ngay dưới ô khoản mục là ô **cách trả** — đúng cột ghi chú trong Excel của anh Khampla: **Chi ngay khi xe đi** · **Trả theo chuyến cùng lương** · **Nợ NCC / trả theo đợt**. Máy chọn sẵn theo khoản mục như Excel (xem bảng *Cách trả* dưới); khác thì Bãi đổi.
2. Phí cao tốc: tuyến có BOT thì máy tự thêm dòng. Chọn **Trả tiền mặt (không dùng thẻ)** hoặc chọn thẻ cao tốc để trừ thẻ.
3. Mục VI (nếu có) → **Thêm dòng** tương tự. Bấm **Lưu**.
4. Bấm **Phiếu đề nghị tạm ứng** (cột bên phải, khối **Phiếu đề nghị**): máy **lập tờ đề nghị tạm ứng có mã QR** (`PTU-<số phiếu>`, đã có thì cập nhật) rồi mở màn **Phiếu đề nghị chi** ở tờ đó. Bấm **In**, tài xế cầm tới quỹ. Bãi in lúc kế toán **chưa nhập giá** cũng được: tờ chỉ có khoản mục và SL, số tiền quỹ thấy khi quét mã là số theo giá kế toán đã nhập **lúc chi**.

**SL đếm theo gì** — SL là **số lượng, không phải tiền**. Trên màn phiếu, cột mục IV, VI ghi **SL (lần / chuyến)**, dưới bảng mục IV, V, VI có một dòng nhắc nói đúng như bảng này:

| Mục | SL là | SL 1 nghĩa là | Đơn giá là |
|---|---|---|---|
| III · Nhiên liệu | **Lít** (cột ghi *Lít*) | 1 lít | giá một lít — dầu kho: bình quân của kho; dầu mua: KT kho xăng dầu nhập |
| IV · Đi đường | **Số lần trong chuyến** | cả chuyến có khoản đó **một lần** — không phải một ngày, không phải một buổi | **tiền trọn khoản cho cả chuyến** |
| V · Sửa chữa | **Số phụ tùng**, hoặc **số lần sửa** | 1 cái phụ tùng · sửa 1 lần | giá một cái / một lần — phụ tùng kho: bình quân của kho |
| VI · Chi khác | **Số lần trong chuyến** | như mục IV | như mục IV |

Đúng như tờ Excel của họ (*ໃບເບີກລົດອອກໄປຂົນສົ່ງ*, mục IV): mỗi khoản một dòng, **SL 1**, đơn giá là tiền trọn chuyến, cột ghi chú nói trả thế nào:

| Khoản (Excel) | SL | Đơn giá (LAK) | Ghi chú trong Excel |
|---|---|---|---|
| Tiền nước · ເງີນເຕີມນ້ຳ | 1 | 60.000 | trả theo chuyến cùng lương |
| Chi phí sang Việt Nam · ເງິນໃຊ້ຈ່າຍໄປຫວຽດນາມ | 1 | 430.000 | trả ngay khi tài xế xuất xe |
| Chipping Lào · ຄ່າຊີບປີງລາວ | 1 | 620.000 | ghi nợ nhà cung cấp, trả theo đợt |
| Chipping Việt · ຄ່າຊີບປີງຫວຽດ | 1 | 1.500.000 | ghi nợ nhà cung cấp, trả theo đợt |
| Phí cao tốc · ເງີນຄ່າທາງດ່ວນ | 1 | 1.833.500 | trả theo chuyến, qua thẻ (nạp 15 triệu kíp mỗi lần) |
| Tiền chuyến · ເງີນຖ້ຽວແກ່ແຮ່ | 1 | 1.800.000 | trả theo chuyến cùng lương |
| Điện thoại · ຄ່າເບີໂທ | 1 | 150.000 | trả ngay khi tài xế xuất xe |

Chỉ ghi SL 2 khi khoản đó **xảy ra hai lần thật** trong cùng một chuyến (ví dụ qua cầu hai lượt). Chuyến dài hơn thì **đơn giá** lớn hơn, SL vẫn là 1. Bãi chỉ ghi khoản mục và SL; không thấy cột đơn giá, thành tiền, nên dòng **Tổng** bên Bãi để trống — KT Chi phí nhập đơn giá khi kiểm (bước 7).

**Cách trả — mỗi dòng đi vào đúng một chỗ** (chủ dự án chốt 29/09: làm theo Excel anh Khampla). Ô cách trả dưới khoản mục, dưới bảng có dòng nhắc *Cách trả theo cột ghi chú Excel. Dòng «Chi ngay khi xe đi» vào tiền tạm ứng.*

| Cách trả (ô trên phiếu) | Excel ghi | Máy chọn sẵn cho | Tiền đi đâu |
|---|---|---|---|
| **Chi ngay khi xe đi** | ຈ່າຍເລີຍຕາມໂຊເຟີອອກລົດ | chi phí sang Việt Nam, điện thoại, tiền ăn, phí cầu / đỗ xe / cửa khẩu, khoản tự gõ | **Phiếu đề nghị tạm ứng**: quỹ đưa tiền mặt lúc xe đi (bước 9); tất toán so với đúng những dòng này (bước 20) |
| **Trả theo chuyến cùng lương** | ຈ່າຍຕາມຖ້ຽວພ້ອມເງິນເດືອນ | tiền nước, tiền chuyến — **chỉ xe nhà** | **Không** vào tạm ứng; cộng lên màn **Tiền chuyến & tiền nước tài xế** để trả cùng lương (bước 20). Phiếu **xe thuê** không có lựa chọn này: tiền nước, tiền chuyến EPL ứng tự thành *Chi ngay khi xe đi* (tạm ứng ghi công nợ chủ xe) |
| **Nợ NCC / trả theo đợt** | ຕິດໜີ້ຜູ້ສະໜອງ/ຊໍາລະເປັນງວດ | chipping Lào, chipping Việt | **Không** vào tạm ứng; thành công nợ nhà cung cấp, kế toán trả theo đợt (6.6) |
| (phí cao tốc, cầu đường) | ຈ່າຍຕາມຖ້ຽວ ຜ່ານບັດ | — ô thẻ thay cho ô cách trả | Chọn thẻ thì **trừ thẻ**, không vào tạm ứng; chọn *Trả tiền mặt* thì vào tạm ứng |

Theo đúng tờ Excel mẫu (bảng trên): tài xế cầm đi **580.000 LAK** tiền mặt (sang VN 430.000 + điện thoại 150.000); tiền nước + tiền chuyến 1.860.000 trả cùng lương; chipping 2.120.000 là nợ nhà cung cấp; phí cao tốc 1.833.500 trừ thẻ. Dầu mục III: dầu kho lĩnh theo phiếu đề nghị xuất nhiên liệu, dầu trạm **ghi nợ** không vào tạm ứng, dầu mua dọc đường trả tiền mặt thì vào tạm ứng.

**Máy tự làm:** số tạm ứng = các dòng EPL ứng có cách trả **Chi ngay khi xe đi** (mục IV, VI) + dầu mua dọc đường trả tiền mặt — không gồm khoản cùng lương, nợ nhà cung cấp, trừ thẻ, dầu kho, dầu ghi nợ. Tờ **PTU** sinh ở bước này; đổi cách trả trước khi quỹ chi thì số tạm ứng tự cập nhật.

**Máy chặn:** Bãi không nhập đơn giá; người kiểm mục nhập ở bước 6–7.

**Ai làm tiếp:** tài xế cầm phiếu đề nghị tạm ứng tới **quỹ** (bước 9) sau khi kế toán ghi sổ mục IV.

### Bước 4. Bãi gửi kiểm từng mục

**Ai:** Admin Thà Bốc. **Trang:** điều xe. **Màn:** Phiếu xuất xe.

**Thao tác:** trước khi xe đi, ở đầu mỗi mục **I, III, IV, VI** bấm **Gửi kiểm tra** — đủ để kế toán duyệt dầu và tạm ứng. **Mục II** của phiếu **Gom** gửi sau, khi đã có cân tại mỏ (bước 10b); phiếu **Giao** thì gửi luôn mục II vì hàng lấy từ lô đã có số tấn. Mục V là của tổ sửa chữa. Mục trống không có nút.

**Lưu ý:** nút **Gửi kiểm tra** chỉ hiện khi phiếu đã **Lưu** ít nhất một lần — dòng *Trạng thái phiếu* dưới cùng không còn ghi *Phiếu mới*. Phiếu mới chưa lưu thì chưa có mục nào để gửi.

**Sau bước:** các mục *Đã nhập · chờ kiểm*. Bãi vẫn sửa được cho tới khi kế toán kiểm.

**Ai làm tiếp:** ba người ở Viêng Chăn, làm song song được: KT Thu/Chi (mục I–II), KT kho xăng dầu (mục III), KT Chi phí (mục IV, VI). Họ thấy việc ở **Tổng quan → Việc của tôi** trên trang điều xe.

### Bước 5. KT Thu/Chi kiểm mục I, II

**Ai:** KT Thu/Chi VC (`ketoan`). **Trang:** điều xe. **Màn:** Phiếu xuất xe. Chọn phiếu ở ô **Số phiếu** trên cùng, hoặc bấm từ **Việc của tôi**.

**Thao tác:**

1. Đối chiếu xe, tài xế, cân đầu với phiếu quặng (xem ảnh đính kèm nếu có).
2. Mục II: gõ **Số phiếu quặng** và **Ngày phiếu quặng** (gõ tay được, không bắt ảnh). Sửa giá cước nếu chuyến này khác hợp đồng. Xe liên kết: nhập **Giá thuê họ mỗi tấn**, phí, **Tải cho phép (tấn)**.
3. Bấm **Lưu**, rồi **Xác nhận kiểm tra** ở mục I (trước khi xe đi) và mục II (khi Bãi đã gửi mục II — phiếu gom là sau bước 10b, thường lúc có tờ phiếu quặng). Sai thì bấm **Trả lại sửa** để trả về cho Bãi.

**Máy chặn:** mục đã kiểm là khoá, muốn sửa phải trả lại; KT Thu/Chi không kiểm mục III–VI.

**Sau bước:** mục I, II *Đã kiểm*.

### Bước 6. KT kho xăng dầu kiểm và ghi sổ mục III

**Ai:** KT kho xăng dầu VC (`khonl`). **Trang:** điều xe. **Màn:** Phiếu xuất xe, mục III.

**Thao tác:**

1. Dòng dầu **mua ngoài**: nhập **Đơn giá** (thường VND, quy Kíp theo tỷ giá khoá trên phiếu). Dòng dầu **kho**: giá là bình quân của kho, máy tự điền, gõ tay bị bỏ qua.
   Phiếu **xe thuê**, dòng dầu kho *EPL ứng*: dưới ô đơn giá (giá vốn bình quân, xám) có ô **Giá bán cho chủ xe** — gõ giá bán một lít (LAK). Cột **Thành tiền (LAK)** và tiền trừ chủ xe tính theo giá bán; giá vốn vẫn là bình quân kho. Đầu mục III ghi *Xuất bán cho chủ xe · <tên chủ xe>*.
2. Bấm **Xác nhận kiểm tra** ở mục III (máy lưu giá trước rồi mới kiểm).
3. Bấm **Ghi sổ kế toán** ở mục III — **sau khi thủ kho đã cấp dầu** theo phiếu đề nghị (bước 8). Kiểm thì làm trước được; ghi sổ thì phải chờ cấp.
4. Nếu có khoản dầu mua ngoài EPL chi tiền mặt: **Thủ quỹ VC** (`quyvc`) mở phiếu, bấm **Xác nhận đã chi** ở mục III.

**Ghi sổ mục III không xuất kho** (từ 30/09): dầu kho chỉ rời kho **một lần**, lúc thủ kho cấp theo phiếu đề nghị (bước 8) — lúc đó mới trừ tồn, mang giá bình quân lúc cấp, sinh tờ **PXK_NL**. Trước đây ghi sổ tự xuất dòng chưa cấp, nên có dầu rời kho mà không có tờ đề nghị nào; nay bỏ.

**Máy chặn:** dòng EPL trả mà đơn giá 0 thì không kiểm được; phiếu xe thuê có dòng dầu kho EPL ứng mà chưa có **giá bán** thì không kiểm được (*Xe thuê: dầu lấy từ kho là xuất bán cho chủ xe … chưa có giá bán*); còn dòng dầu kho EPL ứng **chưa được cấp theo phiếu đề nghị** thì không ghi sổ được (*Mục III: dòng 1 (200 lít) lấy từ kho chưa được cấp theo phiếu đề nghị xuất nhiên liệu. Bãi in phiếu đề nghị, thủ kho cấp dầu ở Cấp phát, rồi mới ghi sổ mục III.*); kế toán chỉ nhập giá, không thêm / xoá dòng. Bãi, tài xế, thủ kho không thấy giá bán.

### Bước 7. KT Chi phí kiểm và ghi sổ mục IV, VI

**Ai:** KT Chi phí VC (`ketoancp`). **Trang:** điều xe. **Màn:** Phiếu xuất xe, mục IV và VI.

**Thao tác:** nhập **Đơn giá** từng dòng mục IV, VI → **Xác nhận kiểm tra** → **Ghi sổ kế toán**, ở từng mục.

**Máy tự làm:** ghi sổ mục IV thì dòng trả bằng **thẻ cao tốc** trừ số dư thẻ đúng một lần.

**Sau bước:** mục IV, VI *Đã ghi sổ · chờ chi*. **Ai làm tiếp:** quỹ chi tạm ứng (bước 9).

### Bước 8. Thủ kho cấp dầu theo phiếu đề nghị xuất nhiên liệu — trang kế toán

**Ai:** thủ kho của đúng kho ghi trên phiếu đề nghị xuất nhiên liệu (`khotb` cho kho Thà Bốc), hoặc KT kho xăng dầu. **Trang:** **kế toán**. **Màn:** Kho → **Cấp phát**.

**Thao tác:**

1. Đăng nhập trang kế toán. Thủ kho vào thẳng màn **Cấp phát**, bảng **Chờ cấp** chỉ có phiếu đề nghị xuất nhiên liệu của kho mình.
2. Tài xế đưa tờ phiếu đề nghị xuất nhiên liệu: bấm vào ô **Nhập mã QR**, quét mã bằng máy quét (hoặc gõ mã in trên phiếu), Enter. Hoặc bấm thẳng vào dòng trong bảng.
3. Khung **Đối chiếu trước khi cấp** hiện số xe, biển đầu kéo, biển rơ-moóc, tài xế, khách, tuyến, các dòng dầu. Đối chiếu đúng xe, đúng tài xế.
4. Bấm **Cấp dầu** (hoặc **Cấp** ở dòng trong bảng). Hộp cấp dầu: ô **Số lít duyệt** (chỉ xem), ô **Số lít cấp thật** (sửa nếu cấp lệch), ô **Lý do cấp lệch số duyệt** (bắt buộc khi cấp lệch). Bấm **Cấp dầu**.
5. Muốn xem cả phiếu xuất xe: bấm **Mở phiếu** (mở trang điều xe, thẻ mới).

**Máy tự làm:** trừ tồn đúng kho ngay; dòng dầu trên phiếu xuất xe mang **giá bình quân của kho lúc cấp**; trang điều xe ghi phiếu đề nghị xuất nhiên liệu *Đã cấp* kèm tên người cấp; sinh **PXK_NL** ngay ở sổ.

**Mất mạng ở kho:** màn vẫn hiện danh sách và chi tiết từ **bản lưu trong máy** (dải vàng *Đang ngoại tuyến*); quét mã vẫn tra được; bấm Cấp thì việc vào **hàng đợi**, dòng đó hiện *Chờ gửi*. Có mạng lại (hoặc trang điều xe bật lại) thì máy **tự gửi**; muốn gửi ngay bấm **Gửi lại ngay**. Việc nào bị máy chủ từ chối thì máy báo rõ để xem lại.

**Máy chặn:** thủ kho kho khác không cấp được; cấp lệch không ghi lý do; cấp hai lần.

### Bước 9. Thủ quỹ chi tạm ứng cho tài xế — ở hệ kế toán anh Tune (từ 01/10)

**Chủ dự án chốt 01/10:** tiền tạm ứng chi thật ở hệ kế toán anh Tune, chi xong thì trạng thái về trang điều xe.

**Ai:** thủ quỹ (Quỹ tiền mặt Thà Bốc), làm **trong hệ kế toán anh Tune**.

1. Lúc KT Chi phí VC (`ketoancp`) bấm **Ghi sổ** mục IV ở bước trước, trang điều xe tự tạo **phiếu chi "Chi trước"** bên hệ kế toán:
   - chưa ghi sổ;
   - đứng tên tài xế;
   - số tham chiếu là số tờ đề nghị tạm ứng (`PTU-…`), đúng số tiền mặt trên tờ.
2. Thủ quỹ mở hệ kế toán → **Phiếu chi** → tìm phiếu theo số tham chiếu trên tờ tài xế cầm tới → chi tiền → **Ghi sổ**.
3. Trên trang điều xe, menu **Phiếu đề nghị chi** → bấm tờ PTU:
   - chưa chi: hiện *Chờ thủ quỹ chi ở hệ kế toán · 1368-CTR-…* và nút **Cập nhật**;
   - đã chi: hiện *Đã chi (kế toán)* kèm tên người ghi sổ.
   - Nút **Cập nhật chi ở kế toán** trên đầu màn hỏi lại cả danh sách.

**Máy tự làm:** hỏi lại hệ kế toán lúc mở tờ, lúc tài xế bấm **Xuất phát**, và khi bấm Cập nhật. Thấy bên đó đã ghi sổ thì:
- mục IV thành *Đã chi*;
- tờ đề nghị tạm ứng thành *Đã cấp* (Tất toán đếm "đã ứng" theo tờ này);
- nhật ký phiếu ghi tên người ghi sổ bên kế toán.

Gửi lại không tạo phiếu thứ hai. Số tạm ứng đổi khi bên kia chưa ghi sổ thì phiếu cũ bị thay bằng phiếu đúng số. Xoá phiếu xuất xe (hoặc huỷ tờ tạm ứng) khi bên kia chưa ghi sổ thì phiếu chi bên kia được rút.

**Máy chặn:**
- Quỹ bấm **Chi** mục IV hoặc quét QR tờ tạm ứng trên trang điều xe → báo *"Tạm ứng chi ở hệ kế toán…"*.
- Tài xế bấm **Xuất phát** khi thủ quỹ chưa ghi sổ → câu báo nói số phiếu chi đang chờ.
- Xoá phiếu đã chi ở hệ kế toán → chặn, đối soát bên kia trước.
- Sếp vẫn chi tay được, cho lúc hệ kế toán không vào được; khi đó máy rút phiếu chi còn chờ bên kia để không chi hai lần.

**Hỏng thì sao:** chưa tạo được phiếu chi (mất mạng, token hết hạn, xe thuê chưa có mã 4022…) thì tờ hiện *Chưa sang được kế toán* kèm câu lỗi; KT Chi phí bấm **Gửi phiếu chi sang kế toán**.

**Ai làm tiếp:** tài xế xuất phát.

### Bước 10. Tài xế xuất phát, chia sẻ vị trí, báo mốc

**Ai:** tài xế (`tx01`) trên điện thoại; hoặc Admin Thà Bốc thay. **Trang:** điều xe. **Màn:** **Phiếu của tôi** (tài xế) · Theo dõi tuyến (Bãi).

**Thao tác:**

1. Tài xế mở **Phiếu của tôi**: chuyến đang chạy là một **vé** lớn — số DO, nhãn **Giao / Gom**, **Điểm đi → Điểm đến** chữ to, thanh các bước **Nhận tạm ứng · Xuất phát · Báo cân** (gom) / **Giao · ký nhận** (giao) **· Về tới**, khung **Phiếu đề nghị tạm ứng** (số tiền; *Đã nhận tiền* hay *Chưa nhận tiền — chờ duyệt / chi* kèm nút **Mã QR** mở mã lớn cho quỹ quét), khung phiếu đề nghị xuất nhiên liệu (số lít, *Chờ cấp* / *Đã cấp*, nút **Mã QR** cho thủ kho). Dưới dòng **Bước tiếp theo** là **một nút lớn** — bấm **Xuất phát** → xác nhận. Rồi bấm ô **Chia sẻ vị trí**, cho phép GPS. Việc khác là các ô bấm to bên dưới: **Báo đã về**, **Báo hỏng / sự cố**, **Khai đổ nhiên liệu**, **Chia sẻ vị trí**, **Mã QR phiếu đề nghị**, **Xem biên bản**. Chuyến khác nằm ở cột **Phiếu gần đây** (điện thoại: dưới vé) — bấm là đổi vé.
2. Bãi làm thay thì mở Phiếu xuất xe → **Xe đã lăn bánh**.
3. Tới từng mốc trên tuyến: Bãi mở Vận tải → **Theo dõi tuyến**, chọn xe, bấm **Xác nhận tới điểm n**. Có chuyện cần ghi thì **Ghi chú diễn biến**.

**Máy chặn:** mục IV chưa *Đã chi* (tài xế chưa cầm tiền) thì không xuất phát được — nút lớn **Xuất phát** tắt, dưới nút ghi *Chưa nhận tiền tạm ứng thì chưa xuất phát*.

**Sau bước:** *Đang vận chuyển*; vị trí xe hiện trên bản đồ Theo dõi tuyến.

### Bước 10b. Xe bốc xong ở mỏ — báo cân tại mỏ, gửi kiểm mục II (phiếu GOM)

**Ai:** tài xế (`tx01`) báo ngay ở mỏ trên điện thoại; Admin Thà Bốc xem lại rồi gửi kiểm. Tài xế không báo được (không có điện thoại, quên) thì Bãi gõ thay — cách 2. **Trang:** điều xe.

**Cách 1 — tài xế báo trên điện thoại (tiện nhất, số đi thẳng từ người cầm phiếu cân):**

1. Tài xế mở **Phiếu của tôi** → vé phiếu gom đang chạy → nút lớn **Báo cân ở mỏ** dưới **Bước tiếp theo** (chỉ phiếu gom; báo rồi thì còn ô **Báo cân ở mỏ** bên dưới để báo lại).
2. Hộp **Báo cân ở mỏ**: ô **Cân tại mỏ (t)** gõ 40 theo phiếu cân; ô **Ghi chú** nếu cần (ví dụ số phiếu cân); bấm **Thêm ảnh phiếu cân · phiếu quặng** để chụp tờ phiếu — không bắt buộc (phiếu nhập tay được). Bấm **Gửi**.
3. Máy báo *Đã báo cân tại mỏ. Bãi sẽ xác nhận.*; trên vé dòng **Cân tại mỏ (t)** hiện 40,00 tấn, bước **Báo cân** thành ✓.
4. **Mất mạng ở mỏ** vẫn bấm Gửi được: máy báo *Chờ gửi — tự gửi khi có mạng lại*, vé có dòng vàng *Báo cân ở mỏ · Chờ gửi…* và nút tạm ẩn. Có mạng lại (hoặc mở lại màn) máy tự gửi và báo *Đã gửi xong 1 lần báo cân chờ gửi*.
5. Gõ nhầm thì bấm **Báo cân ở mỏ** lần nữa với số đúng — số mới thay số cũ, cho tới khi kế toán kiểm mục II.

**Bãi xác nhận:** Admin Thà Bốc mở **Phiếu xuất xe** → phiếu đó → thẻ **II**: ô **Cân tại mỏ (t)** đã có 40; ảnh nằm ở khung **Phiếu quặng đính kèm**; **Theo dõi tuyến** → xe đó → bảng diễn biến có dòng *Báo cân tại mỏ 40 t · 1 ảnh · …*. Đúng thì bấm **Gửi kiểm tra** ở đầu mục II. Sai thì sửa ô **Cân tại mỏ (t)** → **Lưu** → **Gửi kiểm tra**.

**Cách 2 — Bãi gõ thay** (tài xế gọi về báo số tấn, hoặc mang tờ phiếu quặng về): thẻ **II** → ô **Cân tại mỏ (t)** gõ 40 → có ảnh thì khung **Phiếu quặng đính kèm** → **Thêm ảnh · PDF** → **Lưu** → **Gửi kiểm tra** ở đầu mục II.

**Máy tự làm:** ô Cân tại mỏ có số thì máy ghi **một dòng hàng** trên phiếu: mặt hàng theo **Loại hàng** (Quặng sắt → ແຮ່ເຫຼັກ (quặng sắt)), số tấn = cân tại mỏ. Đổi cân hay đổi loại hàng thì dòng đổi theo. Máy gửi lại cùng một lần báo (mất mạng rồi có mạng) không ghi hai lần. Hàng **chưa vào kho** — chỉ vào kho bãi khi xe về tới (bước 12).

**Máy chặn:** tài xế khác, kế toán không báo cân được; số tấn 0; phiếu giao không có nút này; mục II **đã kiểm** thì tài xế không đổi được nữa (máy báo *Mục II đã kiểm với cân tại mỏ 40 t…* — Bãi nhờ kế toán **Trả lại sửa**); xe đã về tới bãi thì không báo cân mỏ nữa (hàng đã vào kho theo số cũ); ô **Cân tại bãi khi về** vẫn xám tới bước 12.

**Phiếu gom cũ có từ hai dòng hàng trở lên** (lập trước 29/09) vẫn hiện khung **Hàng trên phiếu** để sửa từng dòng; nút **Báo cân ở mỏ** trên điện thoại báo *Phiếu có nhiều dòng hàng — Bãi ghi số tấn từng dòng trên phiếu*.

**Ai làm tiếp:** KT Thu/Chi kiểm mục II (bước 5): gõ **Số phiếu quặng**, **Ngày phiếu quặng**, **Xác nhận kiểm tra**.

### Bước 11. Chuyện dọc đường: đổ dầu, xe hỏng, đổi xe

**Đổ dầu dọc đường (Việt Nam):**

1. Tài xế: Phiếu của tôi → ô **Khai đổ nhiên liệu** → ghi **số lít** và trạm (không nhập giá).
2. KT kho xăng dầu (hoặc Bãi): Theo dõi tuyến → sự cố của xe → **Duyệt** (hoặc **Từ chối** kèm lý do). Dòng thành dòng mục III nguồn mua; mục III mở lại *Đã nhập*; KT kho nhập giá khi kiểm lại (như bước 6).
3. Khai đổ ở **kho** của EPL thì máy bảo dùng phiếu đề nghị xuất nhiên liệu.

**Xe hỏng — mục V:**

1. Tài xế: Phiếu của tôi → ô **Báo hỏng / sự cố** (chữ đỏ): hỏng gì, số tiền dự kiến. Hoặc Bãi: Theo dõi tuyến → **Báo sự cố / sửa xe**.
2. Tổ sửa chữa (`totsua`): Theo dõi tuyến → sự cố → **Duyệt**, chọn **Nguồn**: **Lấy từ kho (xuất kho)** thì chọn **Phụ tùng trong kho** và số lượng; **Mua ngoài / garage (chi tiền)** thì ghi khoản mục, đơn giá.
3. Lấy kho: trừ tồn phụ tùng ngay ở trang kế toán, giá bình quân, sinh **PXK_PT**. Mục V mở lại *Đã nhập*, chờ KT Chi phí kiểm (bước 16). Hỏng nặng thì xe chuyển *đang sửa*.
4. Chỉ tổ sửa chữa duyệt báo hỏng; kho không đủ phụ tùng thì chặn.

**Đổi xe giữa đường (xe hỏng nặng):** Bãi mở Phiếu xuất xe → **Đổi xe** → chọn xe thay, tài xế (**Giữ nguyên tài xế** hay đổi), xe cũ **Vào xưởng sửa** hay **Về rảnh**, ghi **Lý do đổi xe**. Máy giữ nguyên chuyến, dòng chi, hàng; mục I phải kiểm lại. Phiếu đã tới nơi thì không đổi xe được.

### Bước 12. Xe gom về tới bãi — hàng vào kho bãi

**Ai:** Admin Thà Bốc (tài xế đã bấm **Báo đã về** trên điện thoại thì ngày về, km về điền sẵn). **Trang:** điều xe. **Màn:** Phiếu xuất xe (hoặc Theo dõi tuyến).

**Thao tác:**

1. Bấm **Xe đã tới · nhập cân cuối**.
2. Hộp nhập của phiếu gom: ô **Cân tại mỏ (t)** ở đầu — đã có số (tài xế báo ở bước 10b, hoặc Bãi đã ghi) thì điền sẵn, chỉ xem lại; còn trống thì phải gõ theo phiếu quặng. Rồi **Cân tại bãi khi về (t)**, ví dụ 39,6; **Ngày xe về**; **Km về (công-tơ-mét)**. Bấm **Đồng ý**. (Phiếu giao thì ô đầu là **Cân cuối (tấn)**, xem bước 15.)

**Máy tự làm (phiếu GOM):** hàng vào **kho bãi** ở trang kế toán thành một **LÔ** (lô = phiếu gom này) theo **số cân tại bãi** 39,6 t; sinh tờ **PNK_HH** ở sổ (ngoài bảng, tính bằng tấn, không có tiền); trên phiếu tự ghi **một dòng hao hụt** 0,4 t (cân mỏ − cân bãi); xe và tài xế rảnh lại; công-tơ-mét của xe cập nhật.

**Máy chặn:** trước bước này, ô **Ngày xe về**, **Lúc về** trên phiếu chỉ xem (nút **Lưu** không ghi được) — xe đã tới rồi thì Bãi sửa được như mọi ô mục I; phiếu gom **chưa có cân tại mỏ** thì không báo tới được (máy nhắc *Cân tại mỏ (t)?*) — không có số thì hàng không có gì để vào kho; mục II đã kiểm mà gõ cân tại mỏ khác số đã kiểm thì bị chặn, phải trả lại mục II; chưa nhận tạm ứng thì không báo tới được; **trang kế toán tắt** thì chưa báo tới được (không biết hàng đã vào kho hay chưa); đã nhập kho rồi thì **không sửa dòng hàng và cân** của phiếu gom nữa — muốn khác thì kế toán lập điều chỉnh (bước 13).

**Ai làm tiếp:** lô nằm bãi chờ phiếu giao lấy (bước 14); KT Thu/Chi khoá phiếu gom khi các mục xong (bước 17).

### Bước 13. Lô nằm bãi — xem tồn, điều chỉnh

**Ai:** ai cũng xem được (trừ tài xế, thủ kho, tổ sửa chữa); **điều chỉnh** chỉ KT Thu/Chi VC hoặc Sếp. **Trang:** **kế toán**. **Màn:** Kho → **Kho hàng**.

**Thao tác xem:** ba ô số trên cùng (tồn tổng, số lô còn hàng, số dòng sổ); bảng **Lô hàng trong kho** (lô nào, ngày, mặt hàng, khách, xe, nhập, điều chỉnh, còn lại); bảng **Sổ nhập xuất** (mới nhất trên cùng, tồn cộng dồn). Bấm một dòng thì mở phiếu đó ở trang điều xe.

**Thao tác điều chỉnh** (cân lại, hàng ẩm hụt, rơi vãi): ở dòng lô bấm **Điều chỉnh tồn** → **Số tấn điều chỉnh (dương tăng, âm giảm)**, ví dụ −0,6 → **Lý do (bắt buộc)** → **Lưu**. Sinh tờ **DC_HH** ở sổ. Không sửa lịch sử nhập / xuất, chỉ thêm một dòng có dấu.

**Máy chặn:** Bãi không tự điều chỉnh (Bãi báo, kế toán ghi); không có lý do; giảm quá tồn (hàng đã xuất cho phiếu giao).

### Bước 14. Bãi lập phiếu GIAO lấy hàng từ lô

**Ai:** Admin Thà Bốc. **Trang:** điều xe. **Màn:** Phiếu xuất xe.

**Thao tác:**

1. **Phiếu mới** → **Loại phiếu**: **Giao (bãi → khách)**. Chọn xe **344**, tài xế `tx02`, tuyến **ທ່າບົກ → ທ່າເຮືອກະລໍ**, khách, ngày.
2. Khung **Hàng trên phiếu** → **Thêm dòng**: **Mặt hàng**, ô **Lấy từ lô (phiếu gom)** chọn lô `G4-…` (danh sách hiện lô còn hàng và số tấn còn — hỏi trang kế toán), **Số tấn** 25.
3. Bấm **Lưu**.
4. Làm tiếp y như phiếu gom: dầu và phiếu đề nghị xuất nhiên liệu (bước 2), đi đường và tạm ứng (bước 3), gửi kiểm (4), kiểm (5–7), cấp dầu (8), chi tạm ứng (9), xuất phát (10), dọc đường (11).

**Máy tự làm:** hàng xuất khỏi kho bãi ngay khi lưu: trang kế toán kiểm tồn lô và ghi dòng xuất, sinh **PXK_HH**; tồn lô còn 39,6 − 25 = 14,6 t; **Cân đầu** của phiếu giao = tổng tấn lấy khỏi kho (25). Sửa lại số tấn thì phần xuất được **thay** theo số mới, không cộng dồn. Dòng hàng của phiếu giao ghi rõ lấy từ phiếu gom nào — đó là dây nối hai phiếu.

**Máy chặn:** phiếu giao có dòng hàng mà không chỉ rõ lô; lấy quá số tấn còn trong lô (kể cả khi hai dòng cùng lô cộng lại quá tồn); **trang kế toán tắt** thì không lưu được phiếu giao có lấy lô (lưu việc khác của phiếu vẫn được); xoá phiếu gom khi lô đã có phiếu giao lấy.

### Bước 15. Xe giao tới nơi — ký nhận giao hàng, cân cuối

**Ai:** tài xế (`tx02`) rồi Admin Thà Bốc. **Trang:** điều xe.

**Thao tác của tài xế (Phiếu của tôi, trên điện thoại):**

1. Nút lớn **Giao hàng hoàn tất · ký nhận** (dưới **Bước tiếp theo**): người nhận **ký lên màn hình**, bấm **Thêm ảnh biên bản · phiếu cân** để chụp ảnh, bấm **Gửi**. Mất mạng thì bản ký vào hàng đợi, có mạng tự gửi. Ký sai thì **Ký lại**; xem lại bằng **Xem biên bản**.
2. Về tới thì bấm **Báo đã về** (ký nhận xong thì đây là nút lớn): **Ngày xe về**, **Km về (công-tơ-mét)**.

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
2. Máy rà và hiện danh sách cảnh báo: km về lệch ước tính quá 10 % (ước tính = lúc đi + chiều đi + chiều về của tuyến; câu cảnh báo ghi rõ *tuyến … km + … km chiều về*), hao hụt quá 1,5 %, thiếu cân cuối, thiếu km về, thiếu phiếu quặng (không có cả ảnh lẫn số phiếu), mục có chi mà chưa kiểm. Đọc từng điểm; đúng thì bấm **Đồng ý** để khoá. Không có điểm lệch thì máy báo phiếu sạch.
3. Cần sửa lại thì bấm **Mở khoá phiếu** (chỉ khi chưa xuất hoá đơn và phiếu đề nghị thu chưa gửi).

Hai nút **🔒 Khoá phiếu**, **Mở khoá phiếu** nằm ở khối việc mức phiếu của **cột bên phải**, cùng chỗ với **Xe đã tới · nhập cân cuối**, **Đổi xe**.

**Máy tự làm:** khoá xong máy lập **Phiếu đề nghị thu** (tờ **PDT**, sếp 30/09): cước của DO theo **đúng tiền tệ của phiếu** (ví dụ 24,7 t × 30,5 USD = 753,35 USD) kèm số quy Kíp theo tỷ giá khoá trên phiếu; khách, số DO, hợp đồng, tuyến, xe, ngày đi / về, số POD, người ký nhận. Tờ vào màn **Phiếu đề nghị thu** trạng thái *Chờ gửi* và vào **Hồ sơ gửi kế toán**; không định khoản — bên công nợ (anh Tune) lập SO, hoá đơn, ghi công nợ. **Mở khoá** thì tờ **chưa gửi** được rút (khoá lại thì máy lập tờ mới theo số lúc đó); tờ **đã gửi** thì kế toán không mở khoá được — máy báo *Phiếu đề nghị thu … đã gửi bên công nợ — báo bên đó trước, rồi nhờ Sếp mở khoá*; Sếp mở được, tờ đã gửi ở lại.

**Sau bước:** phiếu *Đã khoá 🔒*, đề nghị thu *Chờ gửi*. Bãi và tài xế không ghi thêm gì; kế toán, quỹ, kho vẫn kiểm và chi tiếp.

**Ai làm tiếp:** KT Thu/Chi gửi phiếu đề nghị thu; bên công nợ lập hoá đơn, thu (bước 18); quỹ (trả chủ xe nếu xe liên kết), KT Chi phí (tất toán cuối tháng).

### Bước 18. KT Doanh thu lập hoá đơn và ghi thu — trang kế toán

**Ai:** KT Doanh thu VC (`doanhthu`). **Trang:** **kế toán** (từ đợt 7a). **Màn:** nhóm **Tiền vận chuyển** → **Hóa đơn vận chuyển** · **Hoá đơn gộp tháng**. Bên công nợ thật là hệ của **anh Tune** (sẽ nhả API) — hoá đơn lập theo **phiếu đề nghị thu** của DO; trong lúc chờ, trang kế toán tạm làm việc này như dưới.

**Xem và gửi phiếu đề nghị thu (trang điều xe, `ketoan`):**

1. **Vận tải → Phiếu đề nghị thu** → ô **Tháng**. Trên cùng là thanh **Chờ gửi · Đã gửi · Đã xuất hoá đơn · Đã thu đủ · Chờ khoá phiếu · Tất cả** (mỗi nút có số đếm) và dải số **Đề nghị thu trong tháng** (cộng **theo từng tiền tệ**, không quy đổi thầm), **Chờ gửi**, **Còn phải thu** (LAK, theo số bên công nợ chép sang).
2. Bấm một DO ở danh sách bên trái (viền trái màu theo trạng thái) → bên phải là tờ **PHIẾU ĐỀ NGHỊ THU** (ໃບສະເໜີຮັບເງິນ · Collection request): khách, số phiếu và loại, hợp đồng vận chuyển, tuyến, xe · biển số, tài xế, ngày xe đi / về, số POD (*đã ký trên máy tài xế* nếu có), người ký nhận; bảng **Cước vận chuyển** — tấn, đơn giá, số tiền (tiền của phiếu); **Tổng**; dòng *≈ … LAK · Tỷ giá khoá trên phiếu*; khung trạng thái (đã xuất hoá đơn, **Đã thu**, **Còn phải thu**, ai khoá). Bấm **In**.
3. Bấm **Gửi bên công nợ** (chỉ KT Thu/Chi, khi đã nối trang kế toán) → *Đã đẩy sang kế toán*; trạng thái thành *Đã gửi*, cạnh đó hiện **Mã phiếu bên kế toán**. Gửi cả loạt cùng các tờ khác thì dùng **Đẩy hết tờ chưa đẩy** (bước 21).
4. Phiếu khoá **trước 30/09** chưa có tờ: trạng thái *Chưa lập đề nghị* (đếm chung nút **Chờ gửi**) → bấm **Lập phiếu đề nghị thu**. Phiếu đã có hoá đơn hay đã thu thì trạng thái bên công nợ đi trước (*Đã xuất hoá đơn*, *Đã thu đủ*) — tờ là bản xem trước *Chưa có số*.
5. Màn chỉ vai thấy tiền bán (KT Thu/Chi, KT Chi phí, KT Doanh thu, KT kho xăng dầu, quỹ, Sếp); Bãi, tài xế, thủ kho không có.

**Đi từ phiếu:** trên trang điều xe, phiếu đã khoá hiện nút **Lập hóa đơn thu ↗** (hoặc **Gộp hoá đơn tháng ↗** với khách hợp đồng). Bấm nút là mở trang kế toán ở đúng phiếu, đúng tháng. Chưa đăng nhập trang kế toán thì đăng nhập một lần (cùng tên, cùng mật khẩu).

**Khách theo phiếu (không hợp đồng tháng):**

1. Trang kế toán → **Tiền vận chuyển → Hóa đơn vận chuyển**. Vào thẳng từ menu thì màn **chưa mở phiếu nào**: gõ vào ô **Chọn phiếu** (tìm số phiếu, xe, tài xế, khách hàng) rồi chọn ở ô bên cạnh. Đi từ nút ↗ bên điều xe thì phiếu đã mở sẵn.
2. Màn hiện bản in hoá đơn của phiếu (đầu phiếu, các mục chi, phần trả chủ xe nếu xe liên kết) và khung **Sổ thu tiền**. Bấm **Lập hóa đơn thu** → xác nhận. Sinh tờ **HD** (Nợ 1211 / Có 70) và **vào sổ ngay**. Bên điều xe, phiếu tự hiện *Đã lập hóa đơn*.
3. Khách trả tiền: khung **Sổ thu tiền** → **Ghi một lần thu** → điền **Ngày thu**, **Tiền tệ**, **Số tiền khách trả**, **Tỷ giá ngày thu** (để trống thì máy dùng tỷ giá khoá trên phiếu, ô ghi sẵn con số đó), **Cách thu** (Chuyển khoản, Tiền mặt, Cấn trừ công nợ, Khác), **Số uỷ nhiệm chi · biên lai**, **Ghi chú** → **Lưu**. Mỗi lần thu sinh một tờ **PT**, vào sổ ngay. Thu nhiều lần, nhiều loại tiền đều được.
4. Ghi nhầm: bấm **×** ở dòng thu đó → xác nhận. Tờ PT rút khỏi sổ, trạng thái thu tự lùi lại.
5. In: **In** (bản in hoá đơn) và **Phiếu thu** (phiếu thu tiền khách, định khoản 1211/70) mở tờ trong hộp; bấm **In** trong hộp.

**Khách hợp đồng (gộp tháng):** trang kế toán → **Tiền vận chuyển → Hoá đơn gộp tháng** → chọn **Tháng**. Bảng **Chờ gộp** liệt kê từng khách × từng loại tiền còn phiếu đã khoá chưa lên hoá đơn → bấm **Gộp hoá đơn tháng** ở dòng khách → ghi **Ngày hoá đơn**, **Ghi chú** → **Gộp hoá đơn tháng**. Sinh một tờ HD cho mọi phiếu của dòng đó. Trong **Các tờ hoá đơn gộp** bấm **Xem** để mở tờ; ghi thu ở tờ bằng **Ghi một lần thu** — tiền thu tự phân bổ về từng phiếu theo thứ tự ngày, phiếu cũ trả trước. Sai thì **Huỷ tờ hoá đơn** (chỉ khi chưa thu đồng nào; các phiếu quay lại *chưa xuất hoá đơn*).

**Cấn trừ cuối tháng** (từ đợt 7d ở **trang kế toán**): **Tiền vận chuyển → Theo dõi nhà cung cấp** → khung **Cấn trừ cuối tháng** → ô **Tháng** → ở dòng khách còn phần chưa ghi, bấm **Ghi cấn trừ tháng · <số> LAK** → hộp hỏi đúng tên khách và số → bấm **Ghi cấn trừ tháng**. Máy tính phần khách đã trả hộ (thẻ cao tốc của khách, trạm dầu Việt Nam ghi nợ — số lấy từ trang điều xe) rồi ghi thành phiếu thu cách thu *cấn trừ* (ref `CT-YYYYMM`): hoá đơn gộp cũ trước, rồi hoá đơn lẻ cũ trước; không còn hoá đơn để bù thì phần dư để lại tháng sau. Ghi xong, ô *đã ghi phiếu thu* hiện ngay dưới số tổng cấn trừ; ghi lại lần hai bị chặn.

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

**Máy tự làm:** phải trả = tiền thuê − phí quản lý % − cắt quá tải − mọi khoản EPL đã ứng (dầu kho **theo giá bán cho chủ xe**, tạm ứng đi đường…) — số tính ở trang điều xe, không gõ tay; **tự trừ tiếp** phiếu bán hàng chủ xe mua ở quầy chưa trừ (phiếu cũ trước, vừa tiền thì trừ), phiếu bán thành *Đã trừ*; phiếu chi ghi số **thực chi** sau khi trừ. Một tờ **PC_CX** (Nợ 4022 / Có tiền) cho cả đợt, **vào sổ ngay** — không còn nằm chờ đẩy ở trang điều xe.

**Máy chặn:** phiếu chưa khoá; phiếu xe nhà; trả hai lần; các phiếu khác tiền thuê phải tách đợt; **trang điều xe tắt** thì màn không hiện số, không trả được. Kế toán khác (KT Thu/Chi, KT Chi phí, KT Doanh thu, KT kho xăng dầu) xem được hai bảng nhưng không có nút trả; Bãi không có màn này.

**Sếp gỡ đợt trả lập nhầm:** bảng Xe liên kết, phiếu đã trả có nút **Huỷ đợt trả** (chỉ `admin`) → xác nhận. Tờ PC_CX rút khỏi sổ, hàng mua ở quầy về lại chờ trừ, mọi phiếu của đợt quay lại *chưa trả*. Đợt trả có tờ PC_CX đã đẩy từ trang điều xe **trước ngày dời (28/09)** thì không huỷ được — ghi bút toán đảo ở **Ghi tay**. Phiếu đã trả chủ xe thì trang điều xe **không cho xoá phiếu**, kể cả Sếp.

### Bước 20. Tất toán tài xế theo tháng — trang kế toán

**Ai:** KT Chi phí VC (`ketoancp`) chốt; Quỹ tiền mặt cảng cạn (`quytb`), Thủ quỹ VC (`quyvc`) cũng chốt được; **bỏ chốt** chỉ KT Chi phí và Sếp. **Trang:** **kế toán** (từ đợt 7c). **Màn:** nhóm **Tiền vận chuyển** → **Tất toán tài xế**.

**Thao tác:**

1. Trang kế toán → **Tiền vận chuyển → Tất toán tài xế**. Màn mở sẵn ở tháng có phiếu mới nhất (theo ngày xe đi); đổi ở ô **Kỳ (tháng)**.
2. Bốn ô trên cùng: **Đã ứng**, **Đã chi thật**, **Công ty chi bù**, **Tài xế nộp lại** (LAK). Bảng dưới: mỗi tài xế một dòng — **Phiếu trong kỳ**, **Đã ứng**, **Đã chi thật**, **Chênh lệch** (kèm chữ *Công ty chi bù* / *Tài xế nộp lại* / *Vừa đủ*), **Trạng thái** (*Chờ cấp* hay *Đã tất toán*).
3. Bấm vào một dòng → khung dưới cùng liệt kê các phiếu của tài xế đó trong kỳ: **Số phiếu**, **Ngày xe đi**, **Số xe**, **Tuyến đường**, **Đã chi thật**.
4. Bấm **Tất toán** ở dòng tài xế → hộp *Tất toán kỳ … cho …?* nói số chênh → bấm **Tất toán**. Dòng chuyển *Đã tất toán*.
5. Chốt nhầm: bấm **Bỏ chốt** ở dòng đó → xác nhận → chốt lại sau khi sửa phiếu.

**Xem tiền chuyến trả cùng lương:** **Tiền vận chuyển → Tiền chuyến & tiền nước tài xế** → ô **Tháng** → bảng theo tài xế — **chỉ phiếu xe nhà** (xe thuê không có trả cùng lương, 30/09) (chỉ cộng dòng cách trả **Trả theo chuyến cùng lương** — thường là tiền chuyến, tiền nước; khoản đã đưa tiền mặt lúc xe đi không cộng lần nữa): **Chuyến**, **Tiền chuyến**, **Tiền nước**, **Điện thoại**, **Chi phí VN**, **Tiền ăn tài xế**, **Tổng (LAK)**, **Kênh chi** (*Trả theo chuyến cùng lương*), **Trạng thái** chi mục IV. Bấm **In** → bản in trong hộp → bấm **In** trong hộp. KT Thu/Chi, KT Doanh thu, KT kho xăng dầu, hai quỹ và KT Chi phí xem được; Bãi không có màn này.

**Chỉ tài xế xe nhà:** phiếu **xe thuê** không vào Tất toán — tạm ứng xe thuê là công nợ chủ xe, đã trừ vào tiền trả chủ xe (bước 19); tất toán thêm là một khoản hai lần (chủ dự án 29/09).

**Máy tự làm:** chênh lệch = đã chi thật − đã ứng. *Đã ứng* là các phiếu đề nghị tạm ứng **đã cấp** trong kỳ; *đã chi thật* là **đúng những dòng đã vào tạm ứng** — cách trả **Chi ngay khi xe đi** ở mục IV, VI và dầu mua dọc đường trả tiền mặt (một luật với phiếu đề nghị tạm ứng, bước 3); khoản cùng lương, nợ nhà cung cấp, trừ thẻ không tính. Số tính từ phiếu bên trang điều xe, không gõ tay. (Trước 29/09 hai bên tính hai luật khác nhau: 11 phiếu trên máy thật lệch, có phiếu báo tài xế phải nộp lại ~27 triệu — nay hết.) Chênh dương → tờ **TT_CHI** (Nợ 625 / Có tiền mặt Kíp 1011); âm → **TT_THU** (Nợ 1011 / Có 625); dưới 1 Kíp là vừa đủ, không sinh tờ. Tờ **vào sổ ngay**. Bỏ chốt thì tờ rút khỏi sổ.

**Máy chặn:** chốt hai lần một kỳ; kỳ tài xế không có phiếu; **trang điều xe tắt** thì màn không hiện số, không chốt được. Kỳ có tờ tất toán đã đẩy từ trang điều xe **trước ngày dời (28/09)** thì không bỏ chốt được — ghi bút toán đảo ở **Ghi tay**. KT Thu/Chi, KT Doanh thu, Bãi không có màn Tất toán.

### Bước 21. KT Thu/Chi đẩy chứng từ sang sổ

**Ai:** KT Thu/Chi VC (hoặc Sếp). **Trang:** điều xe. **Màn:** Vận tải → **Đề nghị theo DO** → tab **Hồ sơ gửi kế toán** (sổ chứng từ cũ; lọc loại, ngày, *chưa đẩy*; khung **Kết nối kế toán** và nút **Cấu hình** ở đây).

**Thao tác:** xem danh sách tờ *chưa đẩy* (lọc theo loại, theo phiếu) → bấm **Đẩy hết tờ chưa đẩy**, hoặc **Đẩy** ở từng tờ. Máy báo đẩy được bao nhiêu tờ, hỏng bao nhiêu.

**Máy tự làm:** mỗi tờ đẩy đúng một lần; sổ đã có tờ đó thì coi như xong, không gửi trùng; hỏng thì giữ tờ, ghi câu lỗi lên tờ để đẩy lại.

**Máy chặn:** chưa cấu hình địa chỉ sổ kế toán thì báo rõ (Phần 3.3).

**Lưu ý:** tờ kho, tờ lệnh sửa chữa, tờ bán hàng, và mọi tờ tiền vận chuyển — **hoá đơn HD, phiếu thu PT** (7a), **PC_CX** (7b), **TT_CHI · TT_THU** (7c), **PC_NCC** (7d) — **không nằm ở đây** — chúng sinh ngay ở trang kế toán (Phần 1.3).

### Bước 22. Bên sổ: nhận tờ, ghi bút toán, xem số

**Ai:** kế toán (`ketoan`), kế toán trưởng (`ketoantruong`), Sếp; người xem sổ (`xem`, KT Chi phí, KT kho, quỹ, KT Doanh thu) chỉ xem. **Trang:** **kế toán**.

**Máy tự làm khi nhận tờ:** tờ có định khoản và có tiền thì sinh ngay **bút toán đã ghi sổ** (nguồn *Đẩy từ EPL_LAO_REAL*); tờ chỉ có một vế (ngoài bảng, chờ mã) thì ghi đơn; tờ không có tiền (DO, phiếu đề nghị xuất nhiên liệu…) chỉ lưu. Muốn sửa bút toán sinh từ tờ thì **sửa tờ ở trang điều xe rồi đẩy lại** — tờ đã nhận không sửa ở sổ.

**Xem số (menu trang kế toán):**

- **Sổ sách → Kế toán**: **Nhật ký chung** (lọc theo kỳ, nguồn, tài khoản, ô tìm), **Sổ cái** từng tài khoản, **Cân đối phát sinh** (dòng **Nợ = Có, cân đối**), **Hệ thống tài khoản**.
- **Tiền & công nợ → Công nợ**: phải thu khách (1211) theo từng khách, phải trả nhà cung cấp (4021), phải trả chủ xe liên kết (4022).
- **Tiền & công nợ → Thu chi** và **Quỹ & TK**: tiền mặt Kíp 1011, ngoại tệ 1012, ngân hàng 1021, 1022.
- **Chuyến & kho → Chuyến xe**: từng phiếu xe — doanh thu, chi phí theo loại, lãi, còn phải thu, tấn hàng nhập / xuất kho bãi.
- **Chuyến & kho → Kho**: nhập / xuất / tồn theo kho nhiên liệu, phụ tùng (đối chiếu với 1371) và hàng khách gửi (tấn, ngoài bảng).
- **Sổ sách → Báo cáo**; mỗi màn có nút xuất Excel / PDF.

**Bút toán ghi tay** (khoản không đến từ tờ nào, số dư đầu kỳ): **Sổ sách → Ghi tay** → kế toán lập → trạng thái *chờ duyệt* (chưa vào sổ) → **kế toán trưởng** bấm duyệt → *đã ghi sổ*; trả lại thì về *chờ duyệt*; huỷ thì giữ vết.

### Bước 23. Khi nào một chuyến coi là "hoàn tất"

Một phiếu (gom hay giao) hoàn tất khi đủ các điều sau:

1. Trên trang điều xe: mọi mục có chi đã *Đã chi*, phiếu *Đã khoá 🔒*, **phiếu đề nghị thu đã gửi**, đã có hoá đơn (lẻ hoặc gộp tháng) và *đã thu* đủ; xe liên kết thì *đã trả chủ xe*.
2. Màn **Đề nghị theo DO**, dòng của DO: chip **TU** và **NL** *Đã cấp*, bốn ô **III · IV · V · VI** xanh *Đã chi* (hoặc mờ — mục không có chi), cột **Đề nghị thu** *Đã thu đủ*, cột **Đã gửi kế toán** đủ (ví dụ 6/6); tab **Hồ sơ gửi kế toán** không còn tờ *chưa đẩy* của phiếu đó.
3. Trên trang kế toán: màn **Chuyến xe** của phiếu đó hiện đủ doanh thu, chi phí, lãi, còn phải thu = 0; **Công nợ** của khách không còn phần của phiếu; **Cân đối phát sinh** vẫn *Nợ = Có*.
4. Riêng phiếu gom: lô trong **Kho hàng** đã được phiếu giao lấy hết, hoặc phần còn lại đã điều chỉnh có lý do.

## 5. Bảng "ai làm tiếp"

Người nhận việc kế tiếp thấy việc ở **Tổng quan → Việc của tôi** (trang điều xe) hoặc ở màn đầu tiên của họ (trang kế toán: Cấp phát có bảng *Chờ cấp*, Lệnh sửa chữa lọc theo trạng thái). Mọi đề nghị của một DO xem một chỗ: **Vận tải → Đề nghị theo DO** (6.7).

| Sau khi | Trạng thái | Người làm tiếp | Làm ở |
|---|---|---|---|
| Bãi lập phiếu, gửi kiểm | Mục *Đã nhập* | KT Thu/Chi (I–II), KT kho xăng dầu (III), KT Chi phí (IV, VI) | Điều xe · Phiếu xuất xe |
| Bãi in phiếu đề nghị xuất nhiên liệu | Phiếu đề nghị xuất nhiên liệu *Chờ cấp* | Thủ kho đúng kho | Kế toán · Cấp phát |
| KT Chi phí ghi sổ mục IV | Mục IV *Đã ghi sổ* | Quỹ tiền mặt / Thủ quỹ chi tạm ứng | Kế toán · Cấp phát, hoặc Điều xe · mục IV |
| Quỹ chi tạm ứng | Mục IV *Đã chi* | Tài xế xuất phát | Điều xe · Phiếu của tôi |
| Tài xế khai đổ dầu | Sự cố chờ duyệt | KT kho xăng dầu (hoặc Bãi) | Điều xe · Theo dõi tuyến |
| Tài xế báo hỏng | Sự cố chờ duyệt | Tổ sửa chữa | Điều xe · Theo dõi tuyến |
| Tổ sửa chữa duyệt báo hỏng | Mục V *Đã nhập* | KT Chi phí kiểm, ghi sổ; rồi Quỹ chi | Điều xe · Phiếu xuất xe |
| Xe gom tới bãi | Lô trong kho bãi | Bãi lập phiếu giao lấy lô; kế toán điều chỉnh nếu cần | Điều xe · Phiếu xuất xe; Kế toán · Kho hàng |
| Xe tới nơi, các mục xong | *Đã giao hàng* | KT Thu/Chi khoá phiếu | Điều xe · Phiếu xuất xe |
| Phiếu khoá | *Đã khoá 🔒* · đề nghị thu *Chờ gửi* | KT Thu/Chi gửi phiếu đề nghị thu; bên công nợ (KT Doanh thu) hoá đơn, thu; Quỹ (trả chủ xe); KT Chi phí (tất toán cuối tháng) | Điều xe · Phiếu đề nghị thu; Kế toán · Tiền vận chuyển |
| Quỹ chi mục IV–VI, phiếu có tờ DO, phiếu đề nghị xuất nhiên liệu, tạm ứng, đề nghị thu | Tờ *chưa đẩy* | KT Thu/Chi đẩy chứng từ | Điều xe · Đề nghị theo DO → Hồ sơ gửi kế toán |
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

### 6.6. Theo dõi nhà cung cấp — trang kế toán, Tiền vận chuyển → Theo dõi nhà cung cấp

1. **Xem công nợ** (các vai kế toán, hai quỹ; Bãi không): bảng mỗi nhà cung cấp một dòng — **Nhà cung cấp**, **Dịch vụ**, **Mã kế toán**, **Chuyến** (số dòng chi trên phiếu), **Phát sinh (LAK)**, **Ghi nợ tại trạm**, **Cấn trừ vào cước khách**, **Đã trả**, **Còn nợ**, **Điều kiện**; dòng **Tổng** cuối bảng. Phát sinh tính từ phiếu bên trang điều xe (dòng chi EPL ứng đúng khoản mục, hoặc dầu **ghi nợ tại trạm** của nhà cung cấp đó); còn nợ = phát sinh − đã trả.
2. **Trả nhà cung cấp** (KT Chi phí, hai quỹ): bấm **Trả nhà cung cấp** ở dòng → hộp **Ngày thu** (hôm nay), **Thành tiền (LAK)** (điền sẵn số còn nợ, sửa được — trả theo đợt), **Ghi chú** → **Lưu**. Sinh tờ **PC_NCC** (Nợ 4021 / Có tiền mặt Kíp 1011), vào sổ ngay; đã trả, còn nợ đổi ngay.
3. **Các lần trả** ở dòng → khung dưới liệt kê ngày, số tiền, ghi chú, người chi tiền; **Đóng** để ẩn.
4. **Cấn trừ cuối tháng** (khung dưới, KT Doanh thu ghi): xem bước 18.
5. **Danh mục** (thêm, sửa, gắn trạm dầu Việt Nam với khách được cấn trừ) vẫn ở **trang điều xe → Vận tải → Nhà cung cấp** (KT Chi phí): bấm **Thêm · sửa nhà cung cấp ↗** để mở. Hộp **Thêm** / **Sửa**: **Nhà cung cấp**, **Dịch vụ**, **Mã kế toán**, **Điều kiện**, **Cấn trừ vào cước khách**, **Ghi chú**.

**Máy chặn:** số tiền không phải số hoặc bằng 0; ngày sai dạng; **trang điều xe tắt** thì chặn, không lưu gì. Lần trả không có nút xoá (như trước khi dời) — trả nhầm thì ghi bút toán đảo ở **Ghi tay**.

### 6.7. Việc còn ở trang điều xe

- **Thẻ cao tốc** (Danh mục → Thẻ cao tốc): KT Thu/Chi lập thẻ (của khách hay của EPL), quỹ / kế toán nạp tiền; thẻ trừ đúng một lần lúc ghi sổ mục IV; thẻ của khách cuối tháng cấn trừ vào cước khách đó. Điều chỉnh số dư phải có lý do.
- **Danh mục nhà cung cấp** (Vận tải → Nhà cung cấp): KT Chi phí thêm, sửa, gắn trạm dầu Việt Nam với khách được cấn trừ; Bãi xem danh sách, số dòng, kỳ trả (không có tiền). Trả trạm và cấn trừ vào cước khách làm ở trang kế toán (6.6, bước 18).
- **Tuyến đường** (Danh mục → Tuyến đường; Bãi và KT Thu/Chi sửa): bảng tuyến có cột **Tổng km** (chiều hàng đi) và **Km chiều về**. Bấm một tuyến → khung bên phải vẽ các điểm, cuối cùng là dòng **↩** quay lại điểm đi kèm km chiều về, và dòng tóm tắt *Tổng km · Km chiều về · Cả đi và về*. **Thêm** / **Sửa**: **Tên tuyến**, **Phí cao tốc (BOT) cả tuyến**, bảng **Các điểm trên tuyến** (tên điểm, **Km từ điểm trước**, toạ độ nếu có), **Thêm điểm**, rồi ô **Km chiều về** — nút **= … km** bên cạnh chép đúng tổng chiều đi (xe về đường cũ); để trống = xe không quay về. Các điểm là đường **hàng** đi (mỏ → bãi, bãi → cảng); chiều về là đoạn xe chạy không hàng — phiếu gom chạy rỗng từ bãi lên mỏ trước, phiếu giao chạy rỗng về bãi sau. **BOT** ghi số tiền **một chuyến** như Excel của họ (phí cao tốc 1 × 1.833.500, *trả theo chuyến*) — có chiều về cũng không nhân đôi; lập phiếu thì BOT tự thành một dòng phí cao tốc SL 1 ở mục IV.
  **Chi phí gợi ý theo tuyến** (sếp 30/09 — *"dựa vào Excel kê sẵn chi phí cho họ kiểu gợi ý"*): khung chi tiết của tuyến có bảng **Chi phí gợi ý theo tuyến** — số lít dầu và nơi đổ (mục III), các khoản mục IV / VI với SL, **Đơn giá gợi ý**, cách trả. Hộp **Sửa** có bảng sửa được: **+ Thêm dòng**, **×** xoá dòng, **Chép bộ chung (Excel)**. Chọn tuyến trên phiếu thì mục III, IV, VI **tự có các dòng này** (dưới ô **Chọn tuyến** ghi *Đã điền chi phí gợi ý theo tuyến … — thêm, bớt, sửa được*); người lập thêm, bớt, sửa như thường; mục nào đã có dòng người lập tự khai thì không bị đè. Tuyến chưa có bộ riêng thì dùng **bộ chung theo Excel**: 100 L kho Thà Bốc + 750 L dầu Việt Nam qua kho xe, tiền nước 60.000, sang Việt Nam 430.000, chipping Lào 620.000, chipping Việt 1.500.000, tiền chuyến 1.800.000, điện thoại 150.000 (phí cao tốc là ô BOT). **Bãi không thấy đơn giá gợi ý** — máy điền giá vào dòng lúc lưu, kế toán thấy sẵn và sửa khi kiểm; Bãi sửa bộ gợi ý thì giá kế toán đã đặt còn nguyên.
- **Tỷ giá** (Danh mục → Tỷ giá), **bảng giá khách × tuyến** (Danh mục → Khách hàng), **điều khoản chủ xe** và **hợp đồng thuê xe** (Vận tải → Xe liên kết — tiền trả chủ xe ở trang kế toán, bước 19).
- **Xem kho** (Mô-đun kho → **Xem kho**, sếp 30/09 — *"quản lý theo item, chỉ view"*): mọi vai trừ tài xế. Ba tab **Nhiên liệu · Phụ tùng · Kho hàng** (mỗi tab có số dòng), ô tìm mặt hàng / số phiếu / số xe, ô **Tháng**, nhãn **Chỉ xem**. Dải số: **Tổng tồn nhiên liệu** (lít, số kho), **Phiếu đề nghị xuất nhiên liệu chờ cấp** (lít, số tờ; kèm lít *đã khai, chưa có đề nghị*), **Phụ tùng dưới mức tối thiểu**, **Hàng khách gửi ở bãi** (tấn, số lô). Bảng trái mỗi mặt hàng một dòng — nhiên liệu: mỗi kho dầu EPL một dòng: **Tồn**, **Chờ cấp theo đề nghị**, **Đã khai, chưa có đề nghị**, **Còn lại** (= tồn − hai cột trước; âm thì đỏ) kèm thanh màu *xanh còn lại · vàng chờ cấp · sọc nâu đã khai*, **Nhập / Xuất trong tháng**, **Giá vốn bình quân** (vai thấy tiền chi; Bãi không có cột này); phụ tùng: **ĐVT**, **Tồn**, **Tồn tối thiểu** (đỏ *≤ mức*), **Trên phiếu, chờ xuất**, **Còn lại**, nhập / xuất tháng; kho hàng: mỗi loại hàng — **Tồn (tấn)**, số **Lô**, nhập / xuất tháng. Bấm một dòng → khung phải: **Phiếu đề nghị xuất nhiên liệu chờ cấp** (số đề nghị, **số phiếu** — bấm mở phiếu xuất xe, xe, tài xế, lít, ngày; xe thuê ghi *Xuất bán cho chủ xe*), **Dầu đã khai trên phiếu, chưa lập phiếu đề nghị**, **Các lô còn hàng** (kho hàng), **Nhập / xuất gần đây** (10 lần). **Không có nút thao tác kho nào** — nhập, xuất, chuyển kho, điều chỉnh ở bên kho. Nút **Excel** xuất ba sheet.
- **Đề nghị theo DO** (Vận tải → **Đề nghị theo DO**, thay màn *Phiếu chi · Phiếu thu*): tab **Theo DO** — ô **Tháng**, nút lọc **Tất cả · Chi còn chờ · Thu còn chờ** (có số đếm), ô tìm. Mỗi DO một dòng: số DO + nhãn **Giao / Gom** (+ **Xe thuê**), ngày, *Đã khoá*; xe · tài xế; khách · tuyến; cột **Đề nghị chi** — chip **TU · Chờ cấp / Đã cấp** (tạm ứng), **NL ×n · …** (đề nghị xuất nhiên liệu), bốn ô **III · IV · V · VI** màu theo chuỗi *Chưa gửi → Đã nhập · chờ kiểm → Đã kiểm → Đã ghi sổ → Đã chi* (ô mờ: mục không có chi; chú thích màu dưới bảng); cột **Đề nghị thu** (trạng thái, số cước theo tiền của phiếu); cột **Đã gửi kế toán** (x/y, ⚠ nếu có tờ đẩy hỏng). Bấm một DO → khung phải: **Phiếu đề nghị chi** (từng tờ, bấm số tờ mở màn in), **Chi theo mục III–VI** (số dòng, tiền, trạng thái), **Phiếu đề nghị thu**, **Hồ sơ gửi kế toán** của DO (từng tờ, *đã đối chiếu* hay *chưa đẩy*), **Mở phiếu →**. Bãi xem được, không có số tiền; tab **Hồ sơ gửi kế toán** chỉ vai kế toán, quỹ, kho, Sếp.

## 7. Danh mục chứng từ

| Mã | Tên | Sinh lúc | Sinh ở trang | Về sổ | Định khoản chính |
|---|---|---|---|---|---|
| DO | Phiếu xuất xe · đề nghị xuất xe | Lập phiếu | Điều xe | Đẩy | Không (chỉ lưu) |
| PLNL | Phiếu đề nghị xuất nhiên liệu | Bấm Phiếu đề nghị xuất nhiên liệu | Điều xe | Đẩy | Không |
| PTU | Phiếu đề nghị tạm ứng | Bấm Phiếu đề nghị tạm ứng | Điều xe | Đẩy | Không |
| PDT | Phiếu đề nghị thu | Khoá phiếu (DO xong, 30/09) | Điều xe | Đẩy, hoặc **Gửi bên công nợ** ở màn Phiếu đề nghị thu | Không — bên công nợ lập hoá đơn, ghi công nợ |
| PC_TU | Phiếu chi theo đề nghị tạm ứng | Quỹ chi mục IV | Điều xe | Đẩy | Xe nhà: tạm ứng nội bộ, Nợ chi phí 625 · xe thuê: ghi công nợ chủ xe, Nợ 4022 / Có tiền |
| PC_SC | Phiếu chi sửa chữa · chi khác | Quỹ chi mục V, VI | Điều xe | Đẩy | Nợ 614 · 625 / Có tiền |
| PC_SC | (của lệnh sửa chữa) | Quỹ chi lệnh sửa chữa | Kế toán | Ngay | Nợ 614 / Có tiền |
| PXK_NL | Xuất kho nhiên liệu | Thủ kho cấp theo phiếu đề nghị (đường duy nhất, từ 30/09) | Kế toán | Ngay | Xe nhà: xuất nội bộ, Nợ 625 / Có 1371 · xe thuê: **xuất bán** cho chủ xe (giá bán trên phiếu) — trang kế toán mẫu còn ghi Nợ 4022 / Có 1371 theo giá vốn, hạch toán bán là việc bên kho / tiền |
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
| TT_CHI · TT_THU | Tất toán tài xế | Chốt tất toán | Kế toán (từ đợt 7c) | Ngay | Chi bù: Nợ 625 / Có tiền · nộp lại: Nợ tiền / Có 625 |
| PC_NCC | Trả nhà cung cấp | Trả nhà cung cấp | Kế toán (từ đợt 7d) | Ngay | Nợ 4021 / Có tiền |
| PXK_BAN | Xuất kho bán hàng | Lập phiếu bán | Kế toán | Ngay | Nợ 607 / Có 1371 |
| HD_BAN | Hoá đơn bán hàng | Lập phiếu bán | Kế toán | Ngay | Nợ 1211 (chủ xe: 4022) / Có 70 |
| PT_BAN | Phiếu thu bán hàng | Bấm Đã thu | Kế toán | Ngay | Nợ tiền / Có 1211 |

Mã tiền: tiền mặt Kíp 1011, tiền mặt ngoại tệ 1012, ngân hàng Kíp 1021, ngân hàng ngoại tệ 1022. Mã hàng khách gửi và mã giá vốn khác 607 là hai ô cấu hình, Sếp đặt ở trang điều xe: **Đề nghị theo DO** → tab **Hồ sơ gửi kế toán** → **Cấu hình**. Trang Quy trình & trách nhiệm (Hệ thống) có tab danh mục chứng từ với đủ mọi trường hợp định khoản, tính bằng chính hàm ghi sổ.

## 8. Khi mất mạng hoặc một trang tắt

| Việc | Nếu trang kia tắt |
|---|---|
| Thủ kho cấp dầu, quỹ chi tạm ứng ở Cấp phát (trang kế toán) | Vẫn làm: dùng bản lưu trong máy, việc vào hàng đợi, tự gửi khi nối lại |
| Tài xế ký nhận giao hàng trên điện thoại | Vẫn làm: bản ký vào hàng đợi, có mạng tự gửi |
| Tài xế báo cân ở mỏ trên điện thoại (mất sóng ở mỏ) | Vẫn làm: lần báo vào hàng đợi, có mạng tự gửi; không cần trang kế toán |
| Lập / sửa phiếu không đụng kho (ghi chú, xe, tài xế…) | Vẫn làm bình thường |
| Lưu phiếu giao có lấy lô; báo xe gom tới bãi | Chặn, báo rõ; không có phiếu hay dòng kho nửa vời |
| Mục V lấy phụ tùng kho | Chặn, báo rõ |
| Xoá phiếu có dầu, phụ tùng, hàng đã xuất | Chưa xoá được |
| Mở phiếu gom | Vẫn mở, chỉ thiếu số tồn lô |
| Màn Xe → tab Sửa chữa | Vẫn mở, ghi rõ phần lệnh sửa chữa chưa lấy được |
| Màn Xe liên kết, trả chủ xe, huỷ đợt trả (trang kế toán) | Chặn, báo rõ; không lưu gì |
| Danh mục chủ xe, hợp đồng thuê xe (trang điều xe) | Vẫn mở — không cần trang kế toán |
| Thêm / sửa điểm đổ, phụ tùng (trang kế toán) | Không lưu, báo rõ |
| Lập lệnh sửa chữa, lập phiếu bán (trang kế toán) | Không lập được phiếu mới; vẫn xem được danh sách |
| Lập hoá đơn, gộp tháng, ghi thu, xoá lần thu (trang kế toán) | Chặn, báo rõ; không lưu gì |
| Tiền chuyến & tiền nước, Tất toán tài xế: chốt, bỏ chốt (trang kế toán) | Chặn, báo rõ; không lưu gì |
| Theo dõi nhà cung cấp: công nợ, trả, cấn trừ, ghi cấn trừ tháng (trang kế toán) | Chặn, báo rõ; không lưu gì |
| Danh mục nhà cung cấp (trang điều xe) | Vẫn mở — không cần trang kế toán |
| Công nợ khách (trang điều xe → Khách hàng) | Chặn, báo rõ |
| Phiếu, báo cáo bên điều xe | Vẫn mở — đọc bản chép *đã xuất hoá đơn · đã thu · đã trả chủ xe* trên phiếu |
| Đẩy chứng từ, **Gửi bên công nợ** (phiếu đề nghị thu) | Tờ giữ nguyên *chưa đẩy*, ghi câu lỗi; đẩy lại sau |
| Màn **Xem kho** (trang điều xe) | Không có số — màn báo *Chưa lấy được số tồn từ bên kho: …* |

## 9. Đã dời những gì, cái gì ở lại

| Đợt | Nội dung | Dữ liệu |
|---|---|---|
| 1 | Nền móng: vai điều xe ở trang kế toán, bộ nạp module, đường liên thông | Tài khoản chép sang, cùng tên |
| 2 | Điểm đổ nhiên liệu | Bản gốc ở kế toán, bên điều xe còn bản chép |
| 3 | Kho phụ tùng | Tồn, giá, sổ ở kế toán; bên điều xe còn danh mục |
| 4 | Kho nhiên liệu, Cấp phát | Sổ dầu ở kế toán; phiếu đề nghị xuất nhiên liệu vẫn ở điều xe |
| 5 | Kho hàng | Sổ kho hàng ở kế toán; dòng hàng vẫn trên phiếu |
| 6a | Lệnh sửa chữa | Lệnh ở kế toán; mục V vẫn trên phiếu |
| 6b | Bán hàng | Phiếu bán ở kế toán; đợt trả chủ xe hỏi sang |
| 7a | Hóa đơn vận chuyển, Hoá đơn gộp tháng, sổ thu tiền, in phiếu thu | Hoá đơn, lần thu ở kế toán; phiếu bên điều xe giữ bản chép (đã xuất hoá đơn, số tờ gộp, đã thu, ngày thu) |
| 7b | Xe liên kết: chờ trả theo chủ xe, Trả gộp, Trả chủ xe từng phiếu, bảng xe liên kết theo tháng; Sếp huỷ đợt trả | Đợt trả ở kế toán (cùng mã); phiếu bên điều xe giữ bản chép *đã trả chủ xe*; danh mục chủ xe, hợp đồng thuê xe ở lại điều xe |
| 7c | Tiền chuyến & tiền nước tài xế; Tất toán tài xế (chốt, bỏ chốt) | Bản chốt tất toán ở kế toán (cùng mã); số tính từ phiếu bên điều xe |
| 7d | Theo dõi nhà cung cấp: công nợ, trả nhà cung cấp, cấn trừ cuối tháng | Các lần trả ở kế toán (cùng mã); phát sinh tính từ phiếu, danh mục nhà cung cấp ở lại điều xe |

**Đợt 7 xong (7e dọn cuối):** mọi màn kho và tiền đã ở trang kế toán. **Ở lại trang điều xe** đúng như anh chốt: kiểm và duyệt từng mục ngay trên phiếu xuất xe; in phiếu đề nghị tạm ứng, phiếu đề nghị xuất nhiên liệu (từ 30/09 thêm phiếu đề nghị thu và màn **Xem kho** chỉ xem — ghi chú đầu tài liệu); sổ chứng từ và nút đẩy sang sổ (nay là tab **Hồ sơ gửi kế toán** của màn **Đề nghị theo DO**); danh mục khách hàng (bảng giá khách × tuyến), chủ xe (điều khoản), nhà cung cấp; hợp đồng thuê xe; thẻ cao tốc; tỷ giá. Các con số tiền mà trang kế toán hiện (phát sinh nhà cung cấp, tất toán, trả chủ xe, cước) vẫn **tính từ phiếu** bên điều xe — hai trang không giữ hai bản số.

**Một chỗ khác trước (7a):** trên dòng thời gian của báo cáo xu hướng, phiếu nằm trong **hoá đơn gộp tháng** nay có đủ mốc *Hoá đơn* và *Thanh toán* (trước đây để trống vì tờ gộp không gắn với phiếu nào).

## 10. Kịch bản test tay

Phần này đi **đúng thứ tự luồng** ở Phần 4: mỗi dòng là một ca bấm thử — ai đăng nhập, bấm gì, và **thấy gì là đúng** (ở cả hai trang nếu việc đó chạm trang kia). Thao tác chi tiết từng ô ở bước tương ứng của Phần 4 (cột **Bước**). Cột **Đạt** để anh đánh dấu khi in ra; chỗ nào giao diện chưa ổn thì ghi mã ca (ví dụ *T18*) rồi báo em sửa.

### 10.0. Chuẩn bị trước khi test

1. **Dữ liệu tiền đã dời sang trang kế toán — xong ngày 29/09/2026 lúc 10:47, không phải làm lại.** Em đã sao lưu hai DB ngay trước khi dời, chạy thử, rồi chạy thật cả năm bước (hoá đơn và thu tiền, bản chép trên phiếu, chủ xe, tất toán, nhà cung cấp). Chạy thử lại lần nữa thì mọi bước ra 0, tức là không còn gì chưa dời. Số đã sang, để anh đối chiếu khi test:

   | Trang kế toán, màn | Phải thấy |
   |---|---|
   | **Tiền vận chuyển → Hóa đơn vận chuyển** (`doanhthu`) | 7 phiếu đã lập hoá đơn (cộng hai phiếu mẫu 10.0c lập sau, đã thu đủ). Đã thu đủ: T4-0430-08, T4-0431-08, T4-0440-09, T4-0442-09, T4-0443-09. Thu một phần: **T4-0441-09** (đã thu 349,36 USD, còn 1.441,44 USD). Chưa thu đồng nào: **T4-0446-09** (1.689,20 USD) — dùng hai phiếu này để thử ghi thu |
   | **Tiền vận chuyển → Hoá đơn gộp tháng** | Tờ **HDT-202609-01**, 2 phiếu, 79.279.200 LAK; đã thu 47.567.520, còn 31.711.680 LAK |
   | **Tiền vận chuyển → Xe liên kết** (`ketoan`) | Một đợt trả ngày 23/09 cho ທ້າວ ຄຳຫລ້າ: 1.269,47 USD (tổng 1.297,65, 1 phiếu) |
   | **Tất toán tài xế**, **Theo dõi nhà cung cấp** | Chưa có kỳ chốt, chưa có lần trả — DB thật trước đây chưa ai chốt hay trả |

   Trên trang điều xe, các phiếu đó vẫn hiện *đã thu · còn lại* đúng như trên (bản chép). Bản sao lưu ngay trước khi dời: `D:\Demo_Lao\saoluu\saoluu_epl_lao_20260929_1046.dump` và `saoluu_epl_ketoan_20260929_1046.dump`.

2. **Máy chủ phải chạy bản 30/09:** khởi động lại **8020** và **8030** một lần sau các thay đổi ngày 30/09 (dầu kho chỉ rời kho theo đề nghị đã cấp, chi phí gợi ý theo tuyến, phiếu đề nghị thu, ba màn đề nghị, Xem kho, trang tài xế mới). Kiểm nhanh: menu trang điều xe có **Phiếu đề nghị chi**, **Phiếu đề nghị thu**, **Đề nghị theo DO** và **Mô-đun kho → Xem kho**. Rồi **Ctrl+F5** trên trình duyệt. Có máy mới thì chạy bộ chi phí gợi ý cho 5 tuyến mẫu: `python tools/mau_chi_phi_tuyen.py http://127.0.0.1:8020` (xem trước, không ghi) rồi thêm `that` để ghi.
3. **Kiểm kết nối hai chiều** (Phần 3.3 bước 8): trang kế toán, `admin` → **Cài đặt** → thẻ **Liên thông trang điều xe** → **Kiểm kết nối** phải hiện *Nối được trang điều xe*; trang điều xe, `admin` → **Hệ thống → Tài khoản** → tab **Liên thông trang kế toán** → **Kiểm kết nối** phải hiện *Nối được trang kế toán*.
4. Mở tab theo **2.1**: mỗi tab một tài khoản, mỗi lần đăng nhập **bỏ tick *Ghi nhớ đăng nhập***. Mật khẩu mọi tài khoản `1234`.
5. **Dữ liệu mẫu có sẵn:** xe nhà **341**, **342** (đang có phiếu mẫu cũ chưa về — test dùng xe **343**, **344**; **345**, **346** đã chạy cặp phiếu mẫu 10.0c) và 12 đầu kéo thêm ngày 29/09 **343–354** (HOWO, SHACMAN, SITRAK, FAW — mỗi xe đã lắp một rơ-moóc, có tài xế thường lái DRV-03 … DRV-14); xe liên kết **ຮ່ວມ-07**, **ຮ່ວມ-08**, **ຮ່ວມ-09** (chủ xe **ທ້າວ ຄຳຫລ້າ**, cách trả *Gộp cuối tháng*, thuê bằng LAK; tài xế DRV-LK-01 … 03); 4 rơ-moóc để rời **ບອ 3501**, **ບອ 3502**, **ນວ 5620** và **ບອ 3503** (*đang sửa*) để thử tháo / lắp rơ-moóc ở màn **Xe**; vài giấy tờ cố ý sắp hết hạn hay đã hết hạn (bảo hiểm xe 346, đăng kiểm xe 344, bằng lái DRV-06 sắp hết, DRV-09 đã hết) để thử cờ cảnh báo; khách **ຄຳຕຸ້ຍ** và **ນາງ ວັນນາ** (hoá đơn từng phiếu), **ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ** (gộp tháng); tài xế `tx01` = ທ້າວ ທັດສະດາພອນ, `tx02` = ທ້າວ ບຸນມີ, `tx03` = ທ້າວ ສົມພອນ (tài xế xe liên kết ở T27; cặp phiếu mẫu 10.0c cũng dùng tài xế này).
   **Tuyến** (Danh mục → Tuyến đường) — năm tuyến mẫu có **chiều về** thêm ngày 29/09, mỗi tuyến đã có giá cước cho cả 3 khách (theo tấn, USD, tỷ lệ theo km; giá thuê xe liên kết kém 0,5 USD/t):

   | Tuyến | Dùng cho | Chiều hàng | Chiều về | Cả chuyến | BOT | Giá · thuê (USD/t) |
   |---|---|---|---|---|---|---|
   | **ກາສີ → ທ່າບົກ** | Gom: mỏ ກາສີ → bãi | 145 km | 145 km | 290 km | — | 12,5 · 12 |
   | **ຊຽງຂວາງ → ທ່າບົກ** | Gom: mỏ ຊຽງຂວາງ → bãi | 260 km | 260 km | 520 km | — | 22 · 21,5 |
   | **ທ່າບົກ → ທ່າເຮືອກະລໍ** | Giao: bãi → ດ່ານ ນໍ້າພາວ → cảng | 360 km | 360 km | 720 km | 1.833.500 LAK (một chuyến, như Excel) | 30,5 · 30 |
   | **ທ່າບົກ → ດ່ານ ນໍ້າພາວ** | Giao: bãi → cửa khẩu | 210 km | 210 km | 420 km | — | 18 · 17,5 |
   | **ທ່າບົກ → ວຽງຈັນ** | Giao: bãi → khách ở Viêng Chăn | 95 km | 95 km | 190 km | — | 8 · 7,5 |

   Hai tuyến cũ **ກາສີ → ກາລໍ**, **ກາສີ → ທ່າເຮືອກະລໍ** là tuyến **một chặng** mỏ → bãi → cửa khẩu → cảng (41 và 43 USD/t), chưa có chiều về — giữ như cũ để thử chuyến một chặng. Km, BOT, giá là **số mẫu**, anh sửa ở màn Tuyến đường và bảng giá. Năm tuyến mẫu có **bộ chi phí gợi ý** (công cụ `tools/mau_chi_phi_tuyen.py`, chạy thử mặc định, `that` mới ghi, chỉ điền tuyến còn trống): tuyến ra cảng đúng tờ Excel (100 L kho Thà Bốc + 750 L kho xe Việt Nam, mục IV đủ 6 dòng có giá); tuyến gom / nội địa: dầu theo km (200 · 360 · 300 · 140 L — số mẫu), tiền nước, điện thoại (chipping Lào ở tuyến ra cửa khẩu), **tiền chuyến để trống giá** cho kế toán gõ. Hai tuyến một chặng cũ dùng bộ chung.
6. **Test trên DB thật thì những gì bấm sẽ ở lại.** Cách gỡ nếu cần:
   - Phiếu thử: nút **Xoá** trên Phiếu xuất xe chỉ có khi các mục còn *Chờ* / *Đã nhập* (chưa ai kiểm). Đã kiểm rồi thì phiếu ở lại như một chuyến mẫu.
   - Hoá đơn: Sếp **Huỷ tờ hoá đơn** khi phiếu chưa thu đồng nào. Lần thu: bấm **×** ở dòng thu.
   - Đợt trả chủ xe: Sếp **Huỷ đợt trả**. Tất toán: **Bỏ chốt**.
   - **Trả nhà cung cấp không có nút xoá** → thử với số nhỏ (ví dụ 1.000 LAK); gỡ bằng bút toán đảo ở **Ghi tay**.

### 10.0b. Đi thử một chuyến mới từ A đến Z — bấm theo thứ tự này

Một chuyến trọn vẹn làm từ đầu: phiếu **GOM** mỏ → bãi, rồi phiếu **GIAO** lấy hàng từ lô đó ra cảng, tới hoá đơn và sổ. Mỗi bước ghi **ai** (đăng nhập tài khoản nào), **trang** nào, **bấm gì** (đúng chữ trên nút), và **thấy gì là đúng** — số đã tính sẵn theo đúng số em cho ở đây. Mã ca ở cuối mỗi bước (T…) là dòng tương ứng trong bảng 10.1–10.6 để đánh dấu **Đạt**.

**Chuẩn bị (một lần):** Ctrl+F5 cả hai trang. Trong bài này *thẻ I … VI* là **danh sách mục ở cột bên phải** màn Phiếu xuất xe (từ 30/09 thay hàng thẻ ngang). Mở tab theo **2.1** (mỗi tab một tài khoản, bỏ tick *Ghi nhớ đăng nhập*): trang điều xe `http://<máy chủ>:8020`, trang kế toán `http://<máy chủ>:8030`. Tài xế `tx01` (sau này `tx02`) dùng điện thoại hoặc một tab riêng.

#### A. Phiếu GOM — Bãi lập (trang điều xe, `thabok`)

1. **Vận tải → Phiếu xuất xe** → bấm **Phiếu mới** → bấm thẻ lớn **Gom** ngay dưới đầu tờ phiếu. *(T00)*
2. Thẻ **I**: **Loại phiếu** đã là **Gom (mỏ → bãi)** (số phiếu đổi thành `G4-…`, cột phải hiện nhãn **Gom · Gom (mỏ → bãi)**). **Số xe** = **343** → biển đầu kéo, rơ-moóc, hãng tự điền; ô **Lúc đi** tự điền **61200**, dưới ô ghi *Điền sẵn theo công-tơ-mét của xe — sửa được*. **Tài xế** = **ທ້າວ ທັດສະດາພອນ** (`tx01`). **Ngày lập phiếu**, **Ngày xe đi** = hôm nay. *(T01, T01b)*
3. Thẻ **II**: **Chọn tuyến** = *ກາສີ → ທ່າບົກ · 145.0 km · ↩ 145.0 km* → điểm đi, điểm đến tự điền; **Km về ước tính** (thẻ I) thành **61.490** (61.200 + 145 + 145). **Khách hàng** = **ຄຳຕຸ້ຍ**. **Loại hàng** = **Quặng sắt**. Ô **Cân tại mỏ (t)** để **trống**. Không có khung *Hàng trên phiếu* (phiếu gom). *(T01)*
4. Thẻ **III**: chọn tuyến ở bước 3 là máy **đã điền sẵn** dòng **Lít** 200, **Nơi đổ** = kho Thà Bốc (gợi ý của tuyến ກາສີ → ທ່າບົກ) — đúng số bài này, không phải thêm. Tuyến chưa có gợi ý thì **+ Thêm dòng** như cũ. *(T02, T01c)*
5. Thẻ **IV**: máy **đã điền sẵn** 3 dòng gợi ý của tuyến — tiền nước, tiền chuyến chở quặng, tiền điện thoại (SL 1). Bài này đi đúng tờ Excel mẫu nên bấm **+ Thêm dòng** thêm **2 dòng**: *Tiền chi phí sang Việt Nam cho tài xế* và *Phí chipping Lào (kho hải quan)* (SL 1) — đủ 5 dòng. Ô **cách trả** dưới khoản mục **tự chọn** — nhìn cho đúng:

   | Khoản mục | Cách trả máy chọn |
   |---|---|
   | Tiền nước | Trả theo chuyến cùng lương |
   | Tiền chi phí sang Việt Nam cho tài xế | Chi ngay khi xe đi |
   | Phí chipping Lào (kho hải quan) | Nợ NCC / trả theo đợt |
   | Tiền chuyến chở quặng | Trả theo chuyến cùng lương |
   | Tiền điện thoại | Chi ngay khi xe đi |

   Bãi không thấy cột đơn giá, dòng **Tổng** trống — đúng. *(T03, T03b)*
6. Bấm **Lưu** (nút xanh góc trên phải) → *Đã lưu*, phiếu có số **G4-…-09/EPL** (ghi số này lại). Ô **Hợp đồng vận chuyển** tự điền hợp đồng còn hạn của ຄຳຕຸ້ຍ. *(T01)*
7. Đầu các mục **I**, **III**, **IV** bấm **Gửi kiểm tra** (mục **II** chưa gửi — chờ cân ở mỏ). *(T04)*
8. Bấm **Phiếu đề nghị xuất nhiên liệu** (cột phải) → màn **Phiếu đề nghị chi** mở tờ `PLNL-…` có mã QR, 200 lít, không có tiền (tờ tô xanh ở danh sách trái) → **In**. *(T02)*
9. Quay lại phiếu → bấm **Phiếu đề nghị tạm ứng** → tờ `PTU-G4-…` có mã QR; Bãi chỉ thấy khoản mục **sang Việt Nam** và **điện thoại** (hai dòng *Chi ngay khi xe đi*), không thấy tiền → **In**. *(T03)*

#### B. Kế toán kiểm và nhập giá (trang điều xe)

10. `ketoan`: mở phiếu G4-… (ô **Số phiếu** trên cùng, hoặc **Tổng quan → Việc của tôi**) → đầu mục **I** bấm **Xác nhận kiểm tra**. *(T05)*
11. `ketoancp`: thẻ **IV** → cột **Đơn giá**: tiền nước **60.000** và điện thoại **150.000** đã có sẵn (giá gợi ý của tuyến); gõ tiền chuyến **1.800.000**, sang Việt Nam **430.000**, chipping Lào **620.000** → **Lưu** → dòng **Tổng** = **3.060.000** → **Xác nhận kiểm tra** → **Ghi sổ kế toán**. Mở lại **Phiếu đề nghị tạm ứng**: tổng **580.000 LAK** (430.000 + 150.000). *(T03c, T08)*

#### C. Cấp dầu, chi tạm ứng (trang kế toán)

12. `khotb`: **Kho → Cấp phát** → bảng **Chờ cấp** có `PLNL-G4-…` → bấm dòng (hoặc gõ mã trên tờ vào ô **Nhập mã QR**) → khung **Đối chiếu trước khi cấp** đúng xe 343, đúng tài xế → **Cấp dầu** → hộp **Số lít cấp thật** 200 → **Cấp dầu**. Tồn kho Thà Bốc giảm 200 L. *(T06)*
13. `khonl` (trang điều xe): mở phiếu G4-… → mục **III** → **Xác nhận kiểm tra** → **Ghi sổ kế toán**. *(T07)*
14. `quytb` (trang kế toán): **Kho → Cấp phát** → tab **Phiếu đề nghị tạm ứng** → dòng `PTU-G4-…` **Số tiền 580.000** → **Chi tiền** → xác nhận. Bên trang điều xe mục **IV** thành *Đã chi*. *(T09)* — Hoặc chi ở trang điều xe: mở phiếu → mục IV → **Xác nhận đã chi** (tờ QR tự thành *Đã cấp*, quét lại thì bị chặn).

#### D. Tài xế trên đường (điện thoại / ẩn danh, `tx01`)

15. **Phiếu của tôi** → vé chuyến G4-… (chuyến đang chạy tự lên vé; phiếu khác ở cột **Phiếu gần đây** — bấm để đổi): khung **Phiếu đề nghị tạm ứng** ghi **580.000 LAK · Đã nhận tiền** → nút lớn **Xuất phát** → xác nhận → ô **Chia sẻ vị trí** → cho phép vị trí. Phiếu *Đang vận chuyển*, bước **Xuất phát** thành ✓. *(T10)*
16. (tới mỏ, bốc xong) nút lớn **Báo cân ở mỏ** → **Cân tại mỏ (t)** **40** → **Thêm ảnh phiếu cân · phiếu quặng** (chụp một tờ, không bắt buộc) → **Gửi** → *Đã báo cân tại mỏ. Bãi sẽ xác nhận.* Muốn thử mất mạng: bật chế độ máy bay trước khi bấm **Gửi** (ca T10c). *(T10b)*

#### E. Bãi và kế toán chốt mục II (trang điều xe)

17. `thabok`: mở phiếu G4-… → thẻ **II**: ô **Cân tại mỏ (t)** đã có **40**, ảnh ở **Phiếu quặng đính kèm** → đầu mục **II** bấm **Gửi kiểm tra**. *(T10d)*
18. `ketoan`: thẻ **II** → gõ **Số phiếu quặng** (ví dụ `BQ-2909-01`) và **Ngày phiếu quặng** → **Lưu** → mục **II** **Xác nhận kiểm tra**. Ketoan thấy **Giá cước** **12,5 USD/t** (bảng giá ຄຳຕຸ້ຍ × tuyến). Điện thoại tài xế tải lại: không còn nút **Báo cân ở mỏ**. *(T10d)*

#### F. Xe về bãi — hàng vào kho

19. `tx01`: **Báo đã về** → **Ngày xe về** hôm nay, **Km về** **61490** → **Lưu**. *(T12)*
20. `thabok`: phiếu G4-… → **Xe đã tới · nhập cân cuối** → ô **Cân tại mỏ (t)** đã điền sẵn **40** (không sửa) → **Cân tại bãi khi về (t)** **39,6** → ngày về, km về đã điền sẵn → **Đồng ý**. Trên phiếu có dòng hao hụt **0,4 t**; ô **Km chạy** = **290**. *(T12)*
21. Trang kế toán, `ketoan`: **Kho → Kho hàng** → bảng **Lô hàng trong kho** có lô **G4-…** còn **39,6 t**, tờ **PNK_HH**. *(T12)*

#### G. Phiếu GIAO lấy hàng từ lô (trang điều xe, `thabok`)

22. **Phiếu mới** → **Loại phiếu** = **Giao (bãi → khách)** (số `T4-…`) → **Số xe** **344** (ô **Lúc đi** tự điền **58800**) → **Tài xế** **ທ້າວ ບຸນມີ** (`tx02`) → thẻ **II**: tuyến *ທ່າບົກ → ທ່າເຮືອກະລໍ · 360.0 km · ↩ 360.0 km*, khách **ຄຳຕຸ້ຍ** → khung **Hàng trên phiếu** → **Thêm dòng** → **Lấy từ lô (phiếu gom)** chọn lô **G4-… · 39,60 t** → **Số tấn** **25**. *(T14)*
23. Chọn tuyến ra cảng là máy **điền sẵn** gợi ý đúng tờ Excel: thẻ **III** hai dòng *100 L kho Thà Bốc* và *750 L kho xe · Việt Nam*; thẻ **IV** sáu dòng — tiền nước, sang Việt Nam, chipping Lào, chipping Việt, tiền chuyến, điện thoại. Bài này chỉ lĩnh dầu ở Thà Bốc: thẻ **III** sửa **100** thành **300**, bấm **×** ở dòng 750 L. Thẻ **IV** để nguyên sáu dòng; dòng **Phí cao tốc** máy **tự thêm** lúc lưu (tuyến có BOT) → ô thẻ: chọn một thẻ cao tốc (trừ thẻ, không vào tạm ứng) hoặc để **Trả tiền mặt (không dùng thẻ)**. → **Lưu** → **Cân đầu** = **25**; lô G4-… còn **14,6 t**. Thử gõ 50 t → máy chặn (quá tồn). *(T14)*
24. Làm lại như bước 7–15 cho phiếu T4-…: **Gửi kiểm tra** mục I, **II** (phiếu giao gửi luôn), IV → `ketoan` kiểm I, II (thấy giá **30,5 USD/t**) → `ketoancp` mở thẻ IV: **mọi đơn giá đã điền sẵn** theo gợi ý (tiền nước 60.000, sang VN 430.000, chipping Lào 620.000, chipping Việt 1.500.000, tiền chuyến 1.800.000, điện thoại 150.000; phí cao tốc 1.833.500 theo BOT) — chỉ đối chiếu, kiểm, ghi sổ; tổng mục IV **6.393.500** → **Phiếu đề nghị tạm ứng**: **580.000** nếu phí cao tốc trừ thẻ, **2.413.500** nếu để trả tiền mặt → `quytb` chi → `tx02` **Xuất phát**. *(T15)*
25. `tx02`: **Giao hàng hoàn tất · ký nhận** → người nhận ký lên màn → **Thêm ảnh biên bản · phiếu cân** → **Gửi** → khi về **Báo đã về** (km về **59520** = 58.800 + 720). *(T16)*
26. `thabok`: **Xe đã tới · nhập cân cuối** → **Cân cuối (tấn)** **24,7**, **Số POD** (ví dụ `POD-2909-01`), **Người ký nhận** → **Đồng ý** → dòng hao hụt **0,3 t**; **In biên bản giao nhận** in được. *(T17)*

#### H. Khoá, hoá đơn, thu tiền

27. `ketoan` (trang điều xe): phiếu T4-… → **🔒 Khoá phiếu** (cột phải) → đọc cảnh báo (không có *Km về lệch* nếu km về đúng 59.520) → **Đồng ý** → *Đã khoá 🔒*. *(T19)*
27b. `ketoan`: **Vận tải → Phiếu đề nghị thu** → nút **Chờ gửi** → DO T4-… → tờ `PDT/…` **753,35 USD** (24,7 t × 30,5), dòng *≈ … LAK · Tỷ giá khoá trên phiếu* → **In** → **Gửi bên công nợ** → trạng thái *Đã gửi*. *(T19b)*
28. `doanhthu` (trang điều xe): phiếu T4-… → **Lập hóa đơn thu ↗** → trang kế toán mở đúng phiếu → **Lập hóa đơn thu** → xác nhận. Tiền hoá đơn = **24,7 t × 30,5 USD = 753,35 USD** (cân nơi giao × đơn giá, tiền của hợp đồng: USD). *(T20)*
29. `doanhthu` (trang kế toán): khung **Sổ thu tiền** → **Ghi một lần thu** → **Số tiền khách trả** **400** USD → **Lưu** → *Thu một phần*; ghi tiếp **353,35** → *Đã thu đủ* — ở cả hai trang. *(T21)*

#### I. Cuối tháng và sổ (trang kế toán)

30. `ketoan`: **Tiền vận chuyển → Tiền chuyến & tiền nước tài xế** → tháng này → dòng ທ້າວ ທັດສະດາພອນ và ທ້າວ ບຸນມີ có **Tiền chuyến** 1.800.000, **Tiền nước** 60.000 của phiếu mới (cộng thêm phiếu mẫu cũ của họ); cột **Điện thoại**, **Chi phí VN** không cộng khoản đã đưa tiền mặt. *(T33)*
31. `ketoancp`: **Tiền vận chuyển → Tất toán tài xế** → bấm dòng ທ້າວ ທັດສະດາພອນ → khung dưới có phiếu **G4-…** **Đã chi thật 580.000** (bằng tạm ứng). Dòng tổng của tài xế vẫn gộp phiếu mẫu cũ (chi tạm ứng theo luật cũ) nên còn *Tài xế nộp lại* — xem lưu ý ở T34. *(T34)*
32. `ketoan` (trang điều xe): **Vận tải → Đề nghị theo DO** → tab **Hồ sơ gửi kế toán** → **Đẩy hết tờ chưa đẩy** → máy báo số tờ đẩy được. *(T41)*
33. `ketoan` (trang kế toán): **Sổ sách → Kế toán → Nhật ký chung** → thấy HD, PT vừa làm; **Cân đối phát sinh** *Nợ = Có*. **Chuyến & kho → Chuyến xe** → phiếu T4-…: doanh thu 753,35 USD, còn phải thu 0. *(T42, T43)*

34. `ketoan` (trang điều xe): **Vận tải → Đề nghị theo DO** → tab **Theo DO** → dòng G4-… và T4-…: chip **TU · Đã cấp**, **NL ×1 · Đã cấp**, ô **III**, **IV** xanh *Đã chi*, cột **Đề nghị thu** (T4-…) *Đã thu đủ*, cột **Đã gửi kế toán** đủ. *(T41b)*
35. `thabok`: **Mô-đun kho → Xem kho** → tab **Nhiên liệu** → dòng kho Thà Bốc: **Tồn** giảm đúng 500 L (200 + 300) so với trước khi bắt đầu, không còn đề nghị chờ cấp của hai phiếu; không có cột giá. *(T47d)*

Xong bước 35 là đi trọn một chuyến. Các ca còn lại (xe liên kết T27–T32, nhà cung cấp T37–T40, vai và chặn T44–T49, việc ngoài chuyến T50–T53) làm thêm theo bảng dưới.

### 10.0c. Phiếu mẫu đã đi trọn — mở cho sếp xem bằng nhiều vai và xem ghi sổ

Trên máy thật (8020 · 8030) đã có **một cặp phiếu đi trọn A → Z**, lập ngày 29/09/2026 bằng công cụ `tools/phieu_mau_a_z.py`. Công cụ bấm qua đúng các nút như người dùng, **mỗi bước bằng đúng tài khoản của vai đó**, máy chủ kiểm và chặn như khi bấm tay. Phiếu mẫu dùng **xe 345, 346** và tài xế **`tx03`** — không đụng xe 343/344, `tx01`/`tx02` của bài bấm tay 10.0b, nên số km trong 10.0b vẫn đúng. Hai phiếu có ghi chú *Phiếu mẫu A→Z*, số phiếu quặng `MAU-2909-01`, `MAU-2909-02`. Giá cước là giá mẫu tự đặt trong bảng giá (ຄຳຕຸ້ຍ: tuyến gom 12,5 USD/t, tuyến ra cảng 30,5 USD/t), tỷ giá trên phiếu 22.000 LAK/USD.

| | **G4-0104-09/EPL** — phiếu GOM | **T4-0447-09/EPL** — phiếu GIAO |
|---|---|---|
| Xe · tài xế | 345 · ທ້າວ ສົມພອນ (`tx03`) | 346 · ທ້າວ ສົມພອນ (`tx03`) |
| Tuyến | ກາສີ → ທ່າບົກ (145 km + 145 km về) | ທ່າບົກ → ທ່າເຮືອກະລໍ (360 km + 360 km về, BOT 1.833.500) |
| Km lúc đi → km về | 132.500 → 132.790 (đúng ước tính, không cảnh báo) | 128.900 → 129.620 (đúng ước tính) |
| Hàng | cân mỏ **42 t** (tài xế báo từ mỏ, 1 ảnh phiếu cân) → cân bãi **41,5 t**, hao hụt 0,5 t; lô vào kho bãi | lấy **30 t** từ lô G4-0104-09 (lô còn **11,5 t**) → cân cảng **29,7 t**, hao hụt 0,3 t; người nhận ນາງ ມະນີ ký trên màn |
| Dầu (mục III) | lĩnh 200 L kho Thà Bốc × 28.500 = 5.700.000 LAK | lĩnh 300 L kho Thà Bốc = 8.550.000 LAK |
| Mục IV (tổng) | 3.060.000 LAK: nước 60.000 · sang VN 430.000 · chipping Lào 620.000 · tiền chuyến 1.800.000 · điện thoại 150.000 | 4.273.500 LAK: nước 60.000 · sang VN 430.000 · tiền chuyến 1.800.000 · điện thoại 150.000 · phí cao tốc 1.833.500 (trả tiền mặt) |
| Tạm ứng (quỹ chi) | **580.000** (sang VN + điện thoại) | **2.413.500** (sang VN + điện thoại + phí cao tốc) |
| Hoá đơn | 41,5 t × 12,5 USD = **518,75 USD** (11.412.500 LAK) | 29,7 t × 30,5 USD = **905,85 USD** (19.928.700 LAK) |
| Thu tiền | một lần 518,75 USD → *Đã thu đủ* | hai lần 400 + 505,85 USD → *Đã thu đủ* |
| Trạng thái | 🔒 đã khoá · mọi mục đã xong · đã thu đủ | 🔒 đã khoá · mọi mục đã xong · đã thu đủ |

**Kho sau cặp phiếu:** kho dầu Thà Bốc 3.220 → **2.720 L**; kho hàng bãi có lô **G4-0104-09/EPL còn 11,5 t**.

#### Bốn điều cần biết trước khi demo

**1. Màn Cấp phát chỉ hiện tờ đang chờ.** Hai phiếu mẫu đã cấp dầu, đã chi tạm ứng xong, nên bảng **Chờ cấp** trống — không phải lỗi. Muốn xem lại một tờ: gõ mã vào ô **Nhập mã QR** rồi Enter, máy hiện *Đã cấp* và tên người cấp. Mã của bốn tờ:

| Tờ | Mã gõ vào ô Nhập mã QR | Ai mở |
|---|---|---|
| Đề nghị xuất nhiên liệu — phiếu gom (200 L) | `W13LRwYrS0ft` | `khotb` |
| Đề nghị xuất nhiên liệu — phiếu giao (300 L) | `F5b6KJrQkqsg` | `khotb` |
| Đề nghị tạm ứng — phiếu gom (580.000) | `mX0zV9urgYXJ` | `quytb` (tab **Phiếu đề nghị tạm ứng**) |
| Đề nghị tạm ứng — phiếu giao (2.413.500) | `y_gjm-_Yy2TM` | `quytb` (tab **Phiếu đề nghị tạm ứng**) |

**2. Lãi một chuyến có hai con số — sếp dễ hỏi.** Lấy phiếu giao T4-0447-09:

| Xem ở đâu | Lãi | Vì sao |
|---|---|---|
| Trên **phiếu** (trang điều xe, cuối trang) | **7.105.200** | trừ **mọi** khoản chi của chuyến: dầu, tạm ứng, **và cả** tiền nước + tiền chuyến |
| Màn **Chuyến xe** (trang kế toán) | **8.965.200** | chỉ trừ khoản **đã vào sổ**: dầu và tạm ứng |

Chênh **1.860.000** = tiền nước + tiền chuyến *trả cùng lương* — khoản này chưa có tờ vào sổ (xem **Khoản chưa vào sổ** ở cuối 10.0c). **Nói với sếp: lãi thật của một chuyến xem ở phiếu.**

**3. Ảnh trong phiếu mẫu là ảnh trống.** Ảnh phiếu cân (phiếu gom), chữ ký người nhận và ảnh biên bản (phiếu giao) có trong phiếu, nhưng mở ra không có hình — công cụ lập phiếu không chụp ảnh, không ký tay được. Muốn cho sếp xem **chữ ký thật, ảnh thật** thì dùng phiếu anh tự bấm theo 10.0b (ký bằng tay trên điện thoại).

**4. Ai thấy giá cước, ai không.** **Không thấy** giá cước, doanh thu, lãi: **Bãi** (`thabok`), **tài xế** (`tx01`…`tx03`), **thủ kho dầu** (`khotb`, `khovc`), **thủ kho phụ tùng** (`khopt`), **tổ sửa chữa** (`totsua`) — đó là phần lời của công ty (khách trả giá 2, thuê xe ngoài giá 1). **Mọi vai kế toán và quỹ đều thấy**: `ketoan`, `ketoancp`, `khonl`, `quytb`, `quyvc`, `doanhthu`, và `admin`. Muốn cho sếp thấy chỗ khác nhau thì mở cùng một phiếu ở tab `thabok` và tab `ketoan` đặt cạnh nhau.

#### Mở bao nhiêu tab, mỗi tab một tài khoản

Cách mở tab ở **2.1** — quan trọng nhất: mỗi lần đăng nhập **bỏ tick *Ghi nhớ đăng nhập***, không thì các tab dùng chung một tài khoản. Tab này bấm thì tab kia bấm **F5** mới thấy.

**Đủ bộ là 10 tab**, mở theo thứ tự này (tab 1–6 ở `http://<máy chủ>:8020`, tab 7–10 ở `http://<máy chủ>:8030`):

| Tab | Trang | Tài khoản | Xem để thấy |
|---|---|---|---|
| 1 | điều xe | `thabok` — Admin Thà Bốc | Bãi làm phiếu nhưng **không thấy tiền bán** |
| 2 | điều xe | `ketoan` — KT Thu/Chi VC | giá cước, doanh thu, lãi chuyến, ai duyệt bước nào |
| 3 | điều xe | `ketoancp` — KT Chi phí | đơn giá mục IV, cách trả từng dòng, tờ đề nghị tạm ứng |
| 4 | điều xe | `khonl` — KT kho xăng dầu | dầu mục III theo giá bình quân kho |
| 5 | điều xe (hoặc điện thoại) | `tx03` — tài xế ທ້າວ ສົມພອນ | tài xế chỉ thấy phiếu của mình, tiền tạm ứng đã nhận |
| 6 | điều xe | `admin` — Sếp | thấy hết; Tổng quan |
| 7 | kế toán | `khotb` — thủ kho Thà Bốc | dầu đã cấp, tồn kho dầu |
| 8 | kế toán | `quytb` — quỹ Thà Bốc | tiền tạm ứng đã chi |
| 9 | kế toán | `doanhthu` — KT Doanh thu | hoá đơn, hai lần thu tiền |
| 10 | kế toán | `ketoan` — sổ | bút toán Nợ / Có, cân đối, chuyến xe, kho hàng |

**Bản ngắn cho sếp — 5 tab:** 1 (`thabok`), 2 (`ketoan` điều xe), 5 (`tx03`), 9 (`doanhthu`), 10 (`ketoan` kế toán). Đi theo thứ tự đó là kể được trọn chuyện: Bãi lập mà không thấy tiền → kế toán thấy tiền, thấy ai duyệt → tài xế nhận tiền, giao hàng → hoá đơn, thu tiền → sổ.

**Mở một phiếu ở trang điều xe** (tab 1–4, 6): **Vận tải → Phiếu xuất xe** → ô **Số phiếu** trên cùng gõ `T4-0447` (hoặc `G4-0104`) → chọn phiếu ở ô bên cạnh. Danh sách mục **I … VI** ở cột bên phải; **Toàn phiếu** ở cuối danh sách hiện cả sáu mục một trang. Cuối trang phiếu có khung tổng (doanh thu, chi phí, lãi — vai không thấy tiền thì không có) và khung **Lịch sử duyệt**.

#### Từng tài khoản: mở phiếu nào, bấm gì, thấy gì

**Tab 1 · `thabok` — Admin Thà Bốc (trang điều xe)**

1. Mở phiếu **T4-0447-09/EPL** (như trên) → thẻ **I**: xe **346**, biển đầu kéo, rơ-moóc, tài xế ທ້າວ ສົມພອນ, **Lúc đi** 128.900, **Lúc về** 129.620, *Đã kiểm*.
2. Thẻ **II**: tuyến ທ່າບົກ → ທ່າເຮືອກະລໍ, khách ຄຳຕຸ້ຍ, khung **Hàng trên phiếu** một dòng 30 t lấy từ lô **G4-0104-09/EPL**, **Cân đầu (tấn)** 30, **Cân cuối (tấn)** 29,7, dòng **Hao hụt** 0,3 t, **Số POD** `POD-T4-0447-09` (máy tự đặt lúc ký nhận), **Người ký nhận** ນາງ ມະນີ. **Không có** ô giá cước, **Thành tiền**, doanh thu.
3. Thẻ **III**: 300 lít, nơi đổ kho Thà Bốc — **không có** cột đơn giá, thành tiền. Thẻ **IV**: năm khoản mục, SL 1, ô cách trả — **không có** cột **Đơn giá**, dòng **Tổng** trống.
4. Cuối trang: **không có** khung doanh thu, chi phí, lãi. Phiếu *Đã khoá 🔒* — Bãi không sửa được gì nữa.
5. Mở phiếu **G4-0104-09/EPL** → thẻ **II**: **Cân tại mỏ (t)** 42 (tài xế báo từ mỏ), **Cân tại bãi khi về** 41,5, dòng **Hao hụt** 0,5 t; khung **Phiếu quặng đính kèm** có 1 ảnh phiếu cân tài xế gửi.

*Nói với sếp:* Bãi lập phiếu, ghi dầu, khoản đi đường, nhận xe về — nhưng giá khách trả và lãi của công ty Bãi không bao giờ thấy (anh Khampla A2).

**Tab 2 · `ketoan` — KT Thu/Chi VC (trang điều xe)**

1. Mở phiếu **T4-0447-09/EPL** → thẻ **II**: **Số phiếu quặng** `MAU-2909-02`, **Đơn giá mỗi tấn** **30,5** USD, **Thành tiền** **905,85** USD (29,7 t × 30,5 — tính theo cân cuối), **Quy đổi (LAK)** 19.928.700, **Hợp đồng vận chuyển** của ຄຳຕຸ້ຍ. Mục I, II *Đã kiểm*.
2. Cuối trang, khung tổng: **Doanh thu chuyến** 19.928.700 LAK · **Tổng chi phí chuyến** 12.823.500 (dầu 8.550.000 + mục IV 4.273.500) · **Lãi trong chuyến này** ≈ **7.105.200 LAK**. Khung **Sổ thu tiền**: *Đã lập hóa đơn*, *Đã thu đủ*, hai lần thu 400 + 505,85 USD (ghi ở trang kế toán, bên này chỉ đọc).
3. Khung **Lịch sử duyệt** (cuối trang): từng bước ai bấm, vai gì, lúc nào — Bãi lập và gửi kiểm, KT Thu/Chi kiểm I–II, KT Chi phí nhập giá và ghi sổ IV, KT kho xăng dầu kiểm và ghi sổ III, tài xế xuất phát, ký nhận, báo về, Bãi báo tới, KT Thu/Chi khoá, KT Doanh thu lập hoá đơn, thu một phần, thu đủ. *Đây là chỗ cho sếp thấy chuỗi phê duyệt theo vai.*
4. Mở phiếu **G4-0104-09/EPL** → cuối trang: doanh thu 11.412.500 · chi phí 8.760.000 (dầu 5.700.000 + mục IV 3.060.000) · lãi ≈ **2.652.500 LAK**.
5. **Vận tải → Đề nghị theo DO** → tab **Hồ sơ gửi kế toán** → lọc theo phiếu (hoặc tab **Theo DO** → bấm dòng DO → khối **Hồ sơ gửi kế toán**): các tờ DO, PLNL, PTU, PC_TU của hai phiếu đều *đã đẩy*.

**Tab 3 · `ketoancp` — KT Chi phí (trang điều xe)**

1. Mở phiếu **G4-0104-09/EPL** → thẻ **IV**: cột **Đơn giá** 60.000 · 430.000 · 620.000 · 1.800.000 · 150.000, **Thành tiền (LAK)**, dòng **Tổng** **3.060.000**. Ô cách trả từng dòng: tiền nước, tiền chuyến *Trả theo chuyến cùng lương*; sang Việt Nam, điện thoại *Chi ngay khi xe đi*; chipping Lào *Nợ NCC / trả theo đợt*. Mục IV *Đã chi*.
2. Bấm **Phiếu đề nghị tạm ứng** (cột bên phải, khối **Phiếu đề nghị**) → màn **Phiếu đề nghị chi** mở tờ `PTU-G4-0104-09/EPL` có mã QR: chỉ hai dòng sang Việt Nam + điện thoại = **580.000 LAK**, *Đã cấp*.
3. Mở phiếu **T4-0447-09/EPL** → thẻ **IV**: thêm dòng **Phí cao tốc** 1.833.500 (máy tự thêm theo tuyến, *Trả tiền mặt*), tổng **4.273.500**; tờ đề nghị tạm ứng **2.413.500** (sang VN + điện thoại + phí cao tốc).

*Nói với sếp:* tổng mục IV không phải số tài xế cầm đi — chỉ dòng *Chi ngay khi xe đi* thành tiền mặt; tiền chuyến, tiền nước trả cùng lương; chipping nợ nhà cung cấp — đúng cột ghi chú trong Excel của anh Khampla.

**Tab 4 · `khonl` — KT kho xăng dầu (trang điều xe)**

1. Mở phiếu **T4-0447-09/EPL** → thẻ **III**: 300 lít × **28.500** (giá bình quân kho Thà Bốc, máy điền, không gõ tay) = **8.550.000 LAK**; mục III *Đã ghi sổ*.
2. Bấm **Phiếu đề nghị xuất nhiên liệu** → tờ `PLNL-T4-0447-09/EPL-1` có mã QR, 300 lít, *Đã cấp* — người cấp ທ້າວ ບຸນມາ.
3. Phiếu **G4-0104-09/EPL**: 200 lít × 28.500 = 5.700.000.

**Tab 5 · `tx03` — tài xế ທ້າວ ສົມພອນ (trang điều xe, nên mở trên điện thoại)**

1. Đăng nhập là vào thẳng **Phiếu của tôi** — chỉ thấy phiếu **của mình** (có thêm vài phiếu mẫu cũ của tài xế này; hai phiếu mẫu ở trên cùng vì là hôm nay).
2. Thẻ **G4-0104-09/EPL**: tuyến, xe 345, khách, **Cân tại mỏ (t)** 42,00 t, ô **Tiền tạm ứng** **580.000 LAK · Đã nhận tiền**. Không còn nút **Báo cân ở mỏ** (xe đã về, phiếu đã khoá).
3. Thẻ **T4-0447-09/EPL**: **Cân đầu (tấn)** 30,00 t, **Tiền tạm ứng** **2.413.500 LAK · Đã nhận tiền**, dòng **✓ Đã ký nhận: ນາງ ມະນີ** kèm giờ ký.
4. Tài xế **không thấy** giá cước, doanh thu, không mở được phiếu của tài xế khác.

**Tab 6 · `admin` — Sếp (trang điều xe)**

Mở được mọi phiếu, thấy như tab 2 cộng các nút của mọi vai. **Tổng quan**: tick **Tự cập nhật 60 s** để màn tự tải lại trong lúc demo.

**Tab 7 · `khotb` — thủ kho Thà Bốc (trang kế toán)**

1. Đăng nhập là vào **Kho → Cấp phát**: bảng **Chờ cấp** không còn tờ nào của hai phiếu mẫu (đã cấp hết). Muốn xem lại một tờ đã cấp: ô **Nhập mã QR** gõ mã phiếu đề nghị xuất nhiên liệu ở bảng **điều 1** rồi Enter → khung **Đối chiếu trước khi cấp** hiện đúng xe, biển đầu kéo, rơ-moóc, tài xế, trạng thái *Đã cấp*, **Người cấp** ທ້າວ ບຸນມາ; không có nút cấp lần hai.
2. **Kho → Kho nhiên liệu** → ô **Kho** chọn kho Thà Bốc: **Tồn kho hiện tại** **2.720 L**; sổ dầu hai dòng mới nhất *Xuất theo phiếu* `PLNL-T4-0447-09/EPL-1` xe 346 (tồn còn 2.720) và `PLNL-G4-0104-09/EPL-1` xe 345 (tồn còn 3.020), trước đó 3.220.

**Tab 8 · `quytb` — quỹ Thà Bốc (trang kế toán)**

1. **Kho → Cấp phát** → tab **Phiếu đề nghị tạm ứng**: không còn tờ chờ của hai phiếu mẫu.
2. Ô **Nhập mã QR** gõ mã tạm ứng ở bảng **điều 1** → **Số tiền** **580.000** / **2.413.500**, *Đã cấp*, **Người cấp** ນາງ ດາວ; không chi lần hai được.

**Tab 9 · `doanhthu` — KT Doanh thu (trang kế toán)**

1. **Tiền vận chuyển → Hóa đơn vận chuyển** — màn mở ra chưa có phiếu (dòng *Chọn một phiếu ở ô trên…*) → ô **Chọn phiếu** gõ `T4-0447` → chọn phiếu.
2. Bản in hoá đơn: 29,7 t × 30,5 USD = **905,85 USD**, *Đã lập hóa đơn*. Khung **Sổ thu tiền**: hai dòng thu **400 USD** (8.800.000 LAK) và **505,85 USD** (11.128.700 LAK), cách thu chuyển khoản, số UNC; trạng thái **Đã thu đủ**, còn lại 0.
3. Bấm **Phiếu thu** → tờ phiếu thu tiền khách (định khoản 1211 / 70) mở trong hộp → **In** được.
4. Chọn phiếu `G4-0104` → hoá đơn **518,75 USD** (41,5 t × 12,5), thu một lần, *Đã thu đủ* — phiếu gom cũng có cước riêng theo bảng giá khách × tuyến.

**Tab 10 · `ketoan` — sổ (trang kế toán)**

1. **Sổ sách → Kế toán** → **Nhật ký chung** → ô **Tìm kiếm…** gõ `T4-0447` → 5 bút toán: xuất dầu kho (Nợ 625 / Có 1371), hoá đơn (Nợ 1211 / Có 70), hai lần thu (Nợ 1022 / Có 1211), chi tạm ứng (Nợ 625 / Có 1011). Gõ `G4-0104` → 4 bút toán. Bảng đủ số ở mục *Ghi sổ như thế nào* ngay dưới.
2. Cùng màn → **Cân đối phát sinh** → dòng cuối **Nợ = Có, cân đối**.
3. **Chuyến & kho → Chuyến xe** → ô **Tìm kiếm…** gõ `T4-0447` → phiếu: doanh thu 19.928.700, đã thu hết, còn phải thu 0, chi phí **đã vào sổ** 10.963.500 (**Dầu cấp theo đề nghị xuất nhiên liệu** 8.550.000 + **Chi theo đề nghị tạm ứng** 2.413.500), 30 t hàng xuất kho bãi, 9 tờ chứng từ. Lãi ở đây khác lãi trên phiếu — xem **điều 2**. Phiếu `G4-0104`: doanh thu 11.412.500, chi phí đã vào sổ 6.280.000, 41,5 t hàng nhập kho bãi, 8 tờ.
4. **Kho → Kho hàng** → bảng **Lô hàng trong kho**: lô **G4-0104-09/EPL** nhập 41,5 t, còn **11,5 t** (30 t đã đi theo T4-0447-09).

#### Ghi sổ như thế nào — chứng từ và bút toán của cặp phiếu mẫu

Mỗi việc trên phiếu sinh một **tờ chứng từ**; tờ nào có tiền thì thành **một bút toán Nợ / Có** trong Nhật ký chung. Tài khoản theo hệ thống tài khoản đang có ở trang kế toán: **625** Chi phí vận chuyển · **1371** Kho hàng, vật tư · **1011** Tiền mặt bằng Kíp · **1211** Phải thu khách hàng · **70** Doanh thu bán hàng và dịch vụ · **1022** Ngân hàng ngoại tệ.

| Việc (ai bấm) | Tờ chứng từ — G4-0104-09 (gom) | Tờ chứng từ — T4-0447-09 (giao) | Bút toán |
|---|---|---|---|
| Bãi lập phiếu (`thabok`) | DO/2609/0012 phiếu xuất xe | DO/2609/0013 | — (tờ gốc, không có tiền) |
| Bãi in phiếu đề nghị xuất nhiên liệu (`thabok`) | PLNL/2609/0001 — 200 L | PLNL/2609/0002 — 300 L | — (chỉ số lít) |
| Thủ kho cấp dầu (`khotb`) | PXK_NL/2609/0006 — 5.700.000 | PXK_NL/2609/0007 — 8.550.000 | **Nợ 625 / Có 1371** (dầu kho thành chi phí chuyến, theo giá vốn bình quân kho) |
| Bãi in tờ đề nghị tạm ứng (`thabok`) | PTU/2609/0006 — 580.000 | PTU/2609/0007 — 2.413.500 | — (tờ đưa tiền, có mã QR) |
| Quỹ chi tạm ứng (`quytb`) | PC_TU/2609/0010 — 580.000 | PC_TU/2609/0011 — 2.413.500 | **Nợ 625 / Có 1011** (tiền mặt ra khỏi quỹ) |
| Xe gom về bãi · xe giao lấy hàng (`thabok`) | PNK_HH/2609/0003 — nhập 41,5 t | PXK_HH/2609/0003 — xuất 30 t | — (hàng của khách gửi bãi: sổ kho hàng theo tấn, không có tiền) |
| Lập hoá đơn (`doanhthu`) | HD/2609/0005 — 518,75 USD = 11.412.500 LAK | HD/2609/0006 — 905,85 USD = 19.928.700 LAK | **Nợ 1211 / Có 70** (khách nợ tiền cước) |
| Ghi thu tiền (`doanhthu`) | PT/2609/0004 — 518,75 USD | PT/2609/0005 — 400 USD · PT/2609/0006 — 505,85 USD | **Nợ 1022 / Có 1211** (tiền về ngân hàng, xoá nợ khách) |

Trong **Sổ sách → Kế toán → Nhật ký chung** là 9 bút toán **BT-000053 … BT-000061** (4 của phiếu gom, 5 của phiếu giao); **Cân đối phát sinh** vẫn *Nợ = Có*. Tờ sinh ở trang kế toán vào sổ ngay; tờ sinh ở trang điều xe phải **đẩy** (1.3) — tờ của cặp phiếu mẫu đã đẩy rồi.

**Khoản chưa vào sổ.** Mục IV chia theo cách trả (bước 3); chỉ dòng *Chi ngay khi xe đi* qua quỹ lúc xe đi nên có tờ PC_TU. Hai loại còn lại:

| Khoản | Phiếu gom | Phiếu giao | Đi đâu | Vào sổ lúc nào |
|---|---|---|---|---|
| Tiền nước + tiền chuyến (*Trả theo chuyến cùng lương*) | 1.860.000 | 1.860.000 | cộng lên **Tiền vận chuyển → Tiền chuyến & tiền nước tài xế**, tháng 09, dòng ທ້າວ ສົມພອນ | **chưa có tờ nào** — màn đó chỉ cộng số để trả lương, không sinh bút toán |
| Chipping Lào (*Nợ NCC / trả theo đợt*) | 620.000 | — | cộng vào phát sinh ở **Tiền vận chuyển → Theo dõi nhà cung cấp** (6.6) | chỉ khi kế toán bấm **Trả nhà cung cấp**: tờ PC_NCC (Nợ 4021 / Có 1011) |

Cộng lại đúng tổng mục IV: phiếu gom 580.000 + 1.860.000 + 620.000 = **3.060.000**; phiếu giao 2.413.500 + 1.860.000 = **4.273.500**. Đây cũng là lý do lãi ở màn **Chuyến xe** cao hơn lãi trên phiếu (**điều 2**).

**Tất toán tài xế** của ທ້າວ ສົມພອນ: hai phiếu mẫu (xe nhà 345, 346) *đã chi thật = tạm ứng*, **chênh 0**; dòng tổng của tài xế có thể còn *Tài xế nộp lại* vì phiếu mẫu cũ — lý do ở ca **T34**. Phiếu xe thuê cũ của tài xế này (T4-0430-08) không còn trong Tất toán.

**Lập lại cặp phiếu mẫu khác** (ví dụ hôm sau): `python tools/phieu_mau_a_z.py` chạy thử (không ghi, chỉ kể sẽ làm gì), thêm `http://127.0.0.1:8020 http://127.0.0.1:8030 that` là làm thật. Cùng ngày đã có phiếu mẫu thì công cụ dừng, không lập trùng. Công cụ chỉ đẩy tờ của hai phiếu mẫu, không bấm *Đẩy hết* (không cuốn tờ của phiếu anh đang test tay).

### 10.1. Chặng GOM: lập phiếu, dầu, tạm ứng, kiểm, cấp, chi

| Mã | Ai · trang | Làm | Đúng khi | Bước | Đạt |
|---|---|---|---|---|---|
| T00 | `thabok` · điều xe | **Danh mục → Tuyến đường** → bấm tuyến **ກາສີ → ທ່າບົກ** → **Sửa** → xem ô **Km chiều về** và nút **= 145 km** → **Huỷ** | Bảng có cột **Km chiều về** 145; khung chi tiết có dòng **↩ ກາສີ (ບ່ອນຂຸດແຮ່)** *Km chiều về +145 km* và *Cả đi và về: 290 km* | 6.7 | |
| T01 | `thabok` · điều xe | **Phiếu xuất xe** → **Phiếu mới** → thẻ **I**: Loại **Gom (mỏ → bãi)**, xe 343 (ô **Lúc đi** tự điền, xem T01b), tài xế `tx01` → thẻ **II**: tuyến **ກາສີ → ທ່າບົກ**, khách ຄຳຕຸ້ຍ, loại hàng quặng sắt — ô **Cân tại mỏ (t)** để trống → **Lưu** (nút xanh góc trên phải) | Máy cấp số `G4-…/EPL`, báo *Đã lưu*; Bãi **không thấy** ô giá cước, giá thuê, tỷ giá; phiếu gom **không có** khung **Hàng trên phiếu**; dưới ô **Cân tại mỏ (t)** ghi *Bốc xong ở mỏ mới ghi…*; ô **Ngày xe về**, **Lúc về**, **Cân tại bãi khi về** xám, ghi *Điền khi xe về / tới* | 1 | |
| T01b | `thabok` · điều xe | Trên phiếu T01 (chưa lưu cũng được): nhìn ô **Lúc đi**, rồi gõ đè một số khác, rồi đổi **Số xe** sang xe khác và chọn lại 343 | Chọn xe là ô **Lúc đi** có ngay số **Công-tơ-mét (km)** của xe 343 (61.200) (như ở màn **Xe**), dưới ô ghi *Điền sẵn theo công-tơ-mét của xe — sửa được*; đã gõ tay thì đổi xe **không** đè số anh gõ. **Km về ước tính** = lúc đi + 290 (145 đi + 145 về) | 1 | |
| T00 | `thabok` · điều xe | **Phiếu mới** → bấm thẻ lớn **Gom**, rồi thẻ **Giao** | Thẻ bấm tô xanh; ô **Loại phiếu** mục I đổi theo; số phiếu gợi ý đổi `G4-…` ↔ `T4-…`; nhãn ở cột phải và dưới số phiếu đổi **Gom · Gom (mỏ → bãi)** ↔ **Giao · Giao (bãi → khách)**; phiếu đã lưu không còn hai thẻ | 1 | |
| T01c | `thabok` rồi `ketoancp` · điều xe | Phiếu mới → thẻ **II** chọn tuyến **ທ່າບົກ → ທ່າເຮືອກະລໍ**, rồi đổi sang **ກາສີ → ທ່າບົກ**; sửa một dòng gợi ý rồi đổi tuyến lần nữa. Kế toán mở **Danh mục → Tuyến đường** → tuyến ra cảng | Mỗi lần chọn tuyến, mục III, IV có đúng các dòng gợi ý của tuyến đó (dòng gợi ý chưa sửa được thay; dòng đã sửa ở lại); dưới ô **Chọn tuyến** ghi *Đã điền chi phí gợi ý theo tuyến …*. Bãi không thấy giá; lưu xong `ketoancp` thấy giá gợi ý đã điền. Màn Tuyến đường: bảng **Chi phí gợi ý theo tuyến**, có cột **Đơn giá gợi ý** (Bãi không có cột này); tuyến chưa có bộ riêng ghi *đang dùng bộ chung theo Excel* | 1, 6.7 | |
| T02 | `thabok` · điều xe | Mục III → **Thêm dòng**: 200 lít, nơi đổ **kho Thà Bốc** → **Lưu** → **Phiếu đề nghị xuất nhiên liệu** → **In** | Mở màn **Phiếu đề nghị chi** ở tờ phiếu đề nghị xuất nhiên liệu có mã QR (tô xanh ở danh sách trái); không có cột tiền | 2 | |
| T03 | `thabok` · điều xe | Mục IV → **Thêm dòng** như tờ Excel: tiền nước, chi phí sang Việt Nam, chipping Lào, tiền chuyến, điện thoại (mỗi dòng SL 1) → **Lưu** → **Phiếu đề nghị tạm ứng** → **In** | Ô cách trả tự chọn: tiền nước, tiền chuyến *Trả theo chuyến cùng lương*; sang VN, điện thoại *Chi ngay khi xe đi*; chipping *Nợ NCC / trả theo đợt*. Tờ đề nghị tạm ứng có mã QR; Bãi không nhập được đơn giá | 3 | |
| T03c | `ketoancp` · điều xe | Nhập đơn giá như Excel (60.000 · 430.000 · 620.000 · 1.800.000 · 150.000) → **Lưu** → bấm lại **Phiếu đề nghị tạm ứng** | Tờ đề nghị tạm ứng **580.000 LAK** (chỉ sang VN + điện thoại). Đổi ô cách trả tiền chuyến thành *Chi ngay khi xe đi* → **Lưu** → tạm ứng 2.380.000; đổi lại thì về 580.000 | 3 | |
| T03b | `thabok` rồi `ketoancp` · điều xe | Bãi nhìn bảng mục IV: tiêu đề cột và dòng nhắc dưới bảng. Rồi `ketoancp` mở cùng phiếu | Bãi: cột **SL (lần / chuyến)**, dưới bảng ghi *SL 1 = một lần trong chuyến này, theo Excel…*; không có cột đơn giá, dòng **Tổng** trống. `ketoancp`: thấy thêm **Đơn giá**, **Thành tiền (LAK)**, dòng **Tổng** có số. Mục V dưới bảng ghi *SL: số phụ tùng, hoặc số lần sửa…* | 3 | |
| T04 | `thabok` · điều xe | **Gửi kiểm tra** ở mục I, III, IV (mục II chưa — chờ cân mỏ, ca T10b) | Ba mục *Đã nhập · chờ kiểm*; nút **Xoá** phiếu còn (chưa ai kiểm) | 4 | |
| T05 | `ketoan` · điều xe | Mở phiếu (từ **Tổng quan → Việc của tôi** hoặc ô **Số phiếu**) → **Xác nhận kiểm tra** mục I | Mục I *Đã kiểm* (mục II kiểm ở ca T10b) | 5 | |
| T06 | `khotb` · kế toán | **Kho → Cấp phát** → quét / gõ mã QR phiếu đề nghị xuất nhiên liệu T02 (hoặc bấm dòng ở bảng **Chờ cấp**) → đối chiếu → **Cấp dầu** → **Cấp dầu** | Tồn kho Thà Bốc giảm 200 L; bên điều xe phiếu đề nghị xuất nhiên liệu *Đã cấp*, dòng dầu mang **giá bình quân kho lúc cấp**; sổ có **PXK_NL**. Cấp lần hai bị chặn | 8 | |
| T07 | `khonl` · điều xe | Mục III → **Xác nhận kiểm tra** → **Ghi sổ kế toán** (sau T06). Thử thêm: một phiếu có dầu kho **chưa** cấp → **Ghi sổ kế toán** | Sau khi cấp: ghi sổ được, sổ chỉ **một** tờ PXK_NL (lúc cấp); giá dầu kho không gõ tay được. Chưa cấp: máy chặn *… chưa được cấp theo phiếu đề nghị xuất nhiên liệu …* | 6 | |
| T08 | `ketoancp` · điều xe | Mục IV → nhập **Đơn giá** từng dòng → **Xác nhận kiểm tra** → **Ghi sổ kế toán** | Mục IV *Đã ghi sổ · chờ chi* | 7 | |
| T09 | `quytb` · kế toán | **Kho → Cấp phát** → tab **Phiếu đề nghị tạm ứng** → quét QR tờ đề nghị tạm ứng T03 → **Chi tiền** | Mục IV bên điều xe *Đã chi*; bên điều xe không bấm chi lần hai được | 9 | |
| T10 | `tx01` · điều xe (điện thoại) | **Phiếu của tôi** → phiếu T01 → **Xuất phát** (cho phép vị trí) | Phiếu *Đang vận chuyển*; xe hiện trên **Theo dõi tuyến** | 10 | |
| T10b | `tx01` · điều xe (điện thoại) | (xe bốc xong ở mỏ) **Phiếu của tôi** → phiếu T01 → **Báo cân ở mỏ** → **Cân tại mỏ (t)** 39,8 → **Thêm ảnh phiếu cân · phiếu quặng** chụp một tờ → **Gửi** | Máy báo *Đã báo cân tại mỏ. Bãi sẽ xác nhận.*; thẻ phiếu dòng **Cân tại mỏ (t)** 39,80 t. Phiếu giao T14 (sau này) không có nút này | 10b | |
| T10c | `tx01` · điều xe (điện thoại) | Bật **chế độ máy bay** (máy tính: F12 → **Network** → **Offline**) → **Báo cân ở mỏ** → sửa thành 40 → **Gửi** → tắt chế độ máy bay | Lúc mất mạng: *Chờ gửi — tự gửi khi có mạng lại*, thẻ có dòng vàng *Báo cân ở mỏ · Chờ gửi…*, nút tạm ẩn. Có mạng lại: *Đã gửi xong 1 lần báo cân chờ gửi*, **Cân tại mỏ** = 40 | 10b | |
| T10d | `thabok` → `ketoan` · điều xe | Bãi: phiếu T01 thẻ **II** — xem ô **Cân tại mỏ (t)** 40 và ảnh ở **Phiếu quặng đính kèm** → **Gửi kiểm tra** mục II. Kế toán: gõ **Số phiếu quặng**, **Ngày phiếu quặng** → **Lưu** → **Xác nhận kiểm tra** mục II. Rồi `tx01` tải lại **Phiếu của tôi** | **Theo dõi tuyến** có dòng diễn biến *Báo cân tại mỏ 40 t (trước 39.8 t)…*; mục II *Đã kiểm*; ô **Cân tại bãi khi về** vẫn xám; điện thoại tài xế **không còn** nút **Báo cân ở mỏ** | 10b, 5 | |
| T11 | `tx01` → `khonl` | Tài xế **Khai đổ nhiên liệu** (số lít, trạm VN) → `khonl` **Theo dõi tuyến** → sự cố → **Duyệt** | Thành dòng mục III nguồn mua, mục III mở lại *Đã nhập*; `khonl` nhập giá khi kiểm lại | 11 | |
| T12 | `thabok` · điều xe | **Xe đã tới · nhập cân cuối** → ô **Cân tại mỏ (t)** đã điền sẵn 40 (không sửa) → **Cân tại bãi khi về (t)** 39,6, ngày về, km về → **Đồng ý** | Tự có dòng hao hụt 0,4 t; ô **Ngày xe về**, **Lúc về**, **Km chạy** trên phiếu có số và từ giờ sửa được; trang kế toán **Kho → Kho hàng** có lô mới 39,6 t và tờ **PNK_HH** | 12 | |
| T13 | `ketoan` · kế toán | **Kho → Kho hàng** → dòng lô T12 → **Điều chỉnh tồn** −0,6, **Lý do** → **Lưu** | Còn lại 39,0 t; tờ **DC_HH**; `thabok` không có nút điều chỉnh | 13 | |

### 10.2. Chặng GIAO: lấy hàng từ lô, giao, ký nhận

| Mã | Ai · trang | Làm | Đúng khi | Bước | Đạt |
|---|---|---|---|---|---|
| T14 | `thabok` · điều xe | **Phiếu mới** → Loại **Giao (bãi → khách)**, xe 344, tài xế `tx02`, tuyến **ທ່າບົກ → ທ່າເຮືອກະລໍ** (ra cảng, có chiều về), khách ຄຳຕຸ້ຍ → **Hàng trên phiếu** → **Thêm dòng** → **Lấy từ lô (phiếu gom)** chọn lô T12, **Số tấn** 25 → **Lưu** | **Cân đầu** tự = 25; lô còn 14 t ở **Kho hàng**; tờ **PXK_HH**. Thử gõ 50 t → máy chặn (quá tồn lô) | 14 | |
| T15 | như T02–T11 | Dầu, tạm ứng, gửi kiểm, kiểm, cấp, chi, xuất phát cho phiếu giao | Như chặng gom | 2–11 | |
| T16 | `tx02` · điều xe (điện thoại) | **Giao hàng hoàn tất · ký nhận** → ký lên màn, **Thêm ảnh biên bản · phiếu cân** → **Gửi** → **Báo đã về** | Khung **Biên bản giao nhận hàng (POD)** trên phiếu có chữ ký; tắt mạng thì bản ký vào hàng đợi, có mạng tự gửi | 15 | |
| T17 | `thabok` · điều xe | **Xe đã tới · nhập cân cuối** → cân 24,7, **Số POD**, **Người ký nhận** → **Đồng ý** | Dòng hao hụt 0,3 t; **In biên bản giao nhận** in được | 15 | |
| T18 | `ketoancp` → `quytb` · điều xe | Mục VI (nếu có) → kiểm → ghi sổ; quỹ **Xác nhận đã chi** | Tờ **PC_SC** ở **Đề nghị theo DO** → **Hồ sơ gửi kế toán**, *chưa đẩy* | 16 | |

### 10.3. Khoá phiếu, hoá đơn, thu tiền khách — trang kế toán

| Mã | Ai · trang | Làm | Đúng khi | Bước | Đạt |
|---|---|---|---|---|---|
| T19 | `ketoan` · điều xe | Phiếu giao T14 → **Khoá phiếu** → đọc cảnh báo → **Đồng ý** | Phiếu *Đã khoá 🔒*; Bãi không sửa được gì nữa | 17 | |
| T19b | `ketoan` · điều xe | **Vận tải → Phiếu đề nghị thu** → nút **Chờ gửi** → DO T14 → **In** → **Gửi bên công nợ** | Có tờ `PDT/…` đúng cước × tấn nơi giao, **đúng tiền tệ của phiếu** (USD), dòng quy Kíp theo tỷ giá khoá; gửi xong *Đã gửi* kèm **Mã phiếu bên kế toán**; `thabok` không có màn này | 17, 18 | |
| T19c | `ketoan` · điều xe | Phiếu T14 (tờ đề nghị thu **chưa** gửi) → **Mở khoá phiếu** → khoá lại; rồi gửi tờ → **Mở khoá phiếu** lần nữa | Mở khoá lần đầu: tờ PDT biến khỏi màn Phiếu đề nghị thu (*Chờ khoá phiếu*), khoá lại có tờ mới; tờ đã gửi: máy chặn *Phiếu đề nghị thu … đã gửi bên công nợ…*; `admin` mở được | 17 | |
| T20 | `doanhthu` · điều xe → kế toán | Phiếu T14 → **Lập hóa đơn thu ↗** (mở trang kế toán đúng phiếu) → **Lập hóa đơn thu** → xác nhận | Tờ **HD** (Nợ 1211 / Có 70) ở sổ ngay; bên điều xe phiếu hiện *Đã lập hóa đơn* | 18 | |
| T21 | `doanhthu` · kế toán | **Tiền vận chuyển → Hóa đơn vận chuyển** (vào từ menu: màn **chưa mở phiếu nào**) → **Chọn phiếu** → khung **Sổ thu tiền** → **Ghi một lần thu** một nửa số tiền → **Lưu** | Tờ **PT**; trạng thái *Thu một phần* ở cả hai trang; thu tiếp phần còn lại → *Đã thu đủ* | 18 | |
| T22 | `doanhthu` · kế toán | Ghi thu nhiều hơn số còn lại | Máy hỏi **Thu nhiều hơn số còn lại của hoá đơn** → **Vẫn ghi (thu dư)** mới ghi | 18 | |
| T23 | `doanhthu` · kế toán | Bấm **×** ở một dòng thu → xác nhận | Tờ PT rút khỏi sổ; trạng thái thu lùi lại ở cả hai trang | 18 | |
| T24 | `doanhthu` · kế toán | **In** và **Phiếu thu** | Mở bản in trong hộp, bấm **In** in được | 18 | |
| T25 | `doanhthu` · kế toán | **Tiền vận chuyển → Hoá đơn gộp tháng** → **Tháng** 09 → bảng **Chờ gộp** → **Gộp hoá đơn tháng** ở dòng ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ. Cần ít nhất một phiếu **đã khoá, chưa có hoá đơn** của khách này — bảng trống thì làm phiếu mẫu `T4-0444-09/EPL` tới bước khoá trước | Một tờ HD `HDT-…` cho mọi phiếu của dòng; **Xem** tờ → **Ghi một lần thu** → tiền chia về từng phiếu, phiếu cũ trước; bên điều xe phiếu hiện *Thuộc hoá đơn HDT-… ↗* | 18 | |
| T26 | `admin` · kế toán | **Hóa đơn vận chuyển** → một phiếu đã lập hoá đơn mà chưa thu → **Huỷ tờ hoá đơn** | Phiếu quay lại *Chưa xuất hoá đơn* ở cả hai trang; phiếu đã có lần thu thì không có nút này | 18 | |

### 10.4. Xe liên kết — trả chủ xe ở trang kế toán

| Mã | Ai · trang | Làm | Đúng khi | Bước | Đạt |
|---|---|---|---|---|---|
| T27 | `thabok` · điều xe | Lập một phiếu với xe **ຮ່ວມ-07**, tài xế `tx03`; mục III dòng dầu kho **Ai chi** = **EPL ứng** | Phiếu tự thành phiếu xe liên kết, phí và ngưỡng tấn điền theo chủ xe ທ້າວ ຄຳຫລ້າ; đầu mục III ghi *Xuất bán cho chủ xe · ທ້າວ ຄຳຫລ້າ*, đầu mục IV *Tạm ứng ghi công nợ chủ xe · ທ້າວ ຄຳຫລ້າ*; Bãi **không** thấy ô giá bán; ô cách trả của tiền nước, tiền chuyến chỉ có *Chi ngay khi xe đi* và *Nợ NCC / trả theo đợt* (không có *Trả theo chuyến cùng lương*) | 1–2 | |
| T27b | `khonl` · điều xe | Phiếu T27 (Bãi đã gửi kiểm mục III) → **Xác nhận kiểm tra** mục III khi chưa gõ giá bán → rồi gõ ô **Giá bán cho chủ xe** (ví dụ 33.000) → **Lưu** → **Xác nhận kiểm tra** | Lần đầu bị chặn *… chưa có giá bán*; gõ xong thì kiểm được, **Thành tiền** dòng dầu = lít × giá bán, ô đơn giá vẫn là giá vốn bình quân. **Phiếu đề nghị xuất nhiên liệu** in ra có dòng *Xuất bán cho chủ xe · ທ້າວ ຄຳຫລ້າ*; **Phiếu đề nghị tạm ứng** có *Tạm ứng ghi công nợ chủ xe* | 6 | |
| T28 | các vai như T04–T19 | Đi hết các bước của phiếu (có thể ít dòng): `ketoan` kiểm mục II nhập **Giá thuê họ mỗi tấn**; … xe tới; `ketoan` **Khoá phiếu** | Phiếu *Đã khoá 🔒* | 4–17 | |
| T29 | `quytb` · điều xe → kế toán | Phiếu T27 → **Trả chủ xe · <số tiền> ↗** | Mở **Tiền vận chuyển → Xe liên kết** đúng tháng, dòng phiếu tô sáng; chủ xe trả gộp nên dòng ghi *Trả gộp ở bảng Chủ xe* | 19 | |
| T30 | `quytb` · kế toán | Bảng **Chủ xe liên kết** → **Trả gộp** ở dòng ທ້າວ ຄຳຫລ້າ → tích phiếu (dòng **Tổng** tự tính; khung **Hàng mua ở quầy chờ trừ** nếu đã làm T53) → **Trả chủ xe** | Tờ **PC_CX** (Nợ 4022 / Có tiền) ở sổ ngay, số thực chi đã trừ hàng mua ở quầy; bên điều xe phiếu hiện đã trả, nút trả biến mất | 19 | |
| T31 | `admin` · kế toán | Dòng phiếu đã trả → **Huỷ đợt trả** | Tờ PC_CX rút khỏi sổ, phiếu về *chưa trả* ở cả hai trang | 19 | |
| T32 | `ketoan` · kế toán | Mở **Xe liên kết** | Xem được hai bảng, **không có** nút trả | 19 | |

### 10.5. Cuối tháng: tất toán tài xế, tiền chuyến, nhà cung cấp, cấn trừ — trang kế toán

| Mã | Ai · trang | Làm | Đúng khi | Bước | Đạt |
|---|---|---|---|---|---|
| T33 | `ketoan` · kế toán | **Tiền vận chuyển → Tiền chuyến & tiền nước tài xế** | Mở sẵn tháng có phiếu mới nhất; bảng theo tài xế, **chỉ phiếu xe nhà** (phiếu xe thuê T27 không có), chỉ cộng dòng *Trả theo chuyến cùng lương* (phiếu T03: tiền chuyến 1.800.000, tiền nước 60.000; cột **Điện thoại**, **Chi phí VN** không cộng vì đã đưa tiền mặt); **In** → bản in trong hộp | 20 | |
| T34 | `ketoancp` · kế toán | **Tiền vận chuyển → Tất toán tài xế** → bấm một dòng | Bốn ô tổng; khung dưới liệt kê phiếu của tài xế đó trong kỳ. Phiếu lập từ 29/09 (như T03): tạm ứng đúng bằng đã chi, **chênh 0**. Lưu ý khi demo: 8 phiếu mẫu cũ tháng 8–9 (T4-0428 … T4-0441) đã **chi tạm ứng theo luật cũ** — số tiền mặt gồm cả tiền chuyến, chipping… — nên dòng của ທ້າວ ທັດສະດາພອນ, ທ້າວ ບຸນມີ, ທ້າວ ສົມພອນ hiện *Tài xế nộp lại* đúng phần đã đưa thừa; sổ cũ không sửa ngược. Muốn thấy dòng sạch thì chạy T01–T09 với một tài xế chưa có phiếu (ví dụ DRV-05). **Chỉ phiếu xe nhà**: phiếu xe thuê (ví dụ T27, và hai phiếu mẫu cũ T4-0430-08, T4-0443-09) không có trong khung phiếu của tài xế | 20 | |
| T35 | `ketoancp` · kế toán | **Tất toán** ở một dòng → **Tất toán** | Dòng *Đã tất toán*; sổ có **TT_CHI** (chi bù, Nợ 625 / Có 1011) hoặc **TT_THU** (nộp lại, Nợ 1011 / Có 625); bấm lại lần hai bị chặn | 20 | |
| T36 | `quytb` → `ketoancp` · kế toán | Quỹ bấm **Bỏ chốt** (bị từ chối) → KT Chi phí **Bỏ chốt** | Chỉ KT Chi phí bỏ được; tờ TT rút khỏi sổ | 20 | |
| T37 | `ketoancp` · kế toán | **Tiền vận chuyển → Theo dõi nhà cung cấp** | Bảng công nợ: phát sinh, ghi nợ tại trạm, đã trả, còn nợ = phát sinh − đã trả; dòng **Tổng** | 6.6 | |
| T38 | `ketoancp` · kế toán | **Trả nhà cung cấp** ở một dòng → **Thành tiền (LAK)** sửa thành 1000 → **Lưu** → **Các lần trả** | Đã trả +1.000, còn nợ −1.000; tờ **PC_NCC** (Nợ 4021 / Có 1011) ở sổ; khung các lần trả có dòng mới | 6.6 | |
| T39 | `ketoancp` · kế toán → điều xe | **Thêm · sửa nhà cung cấp ↗** | Mở **Vận tải → Nhà cung cấp** bên điều xe (danh mục, không có cột tiền) | 6.6 | |
| T40 | `doanhthu` · kế toán | **Theo dõi nhà cung cấp** → khung **Cấn trừ cuối tháng** → **Tháng** 08 → **Ghi cấn trừ tháng · … LAK** ở dòng ຄຳຕຸ້ຍ → **Ghi cấn trừ tháng** | Báo *Đã ghi … phiếu thu cấn trừ*; dưới tổng cấn trừ hiện *đã ghi phiếu thu*; sổ thu của phiếu có dòng cách thu cấn trừ `CT-202608`; ghi lại lần hai bị chặn | 18 | |

### 10.6. Đẩy chứng từ và xem sổ

| Mã | Ai · trang | Làm | Đúng khi | Bước | Đạt |
|---|---|---|---|---|---|
| T41b | `ketoan` rồi `thabok` · điều xe | **Vận tải → Đề nghị theo DO** → tháng này → nút **Chi còn chờ**, **Thu còn chờ** → bấm một DO | Mỗi DO một dòng; chip **TU**, **NL**, bốn ô III–VI đúng trạng thái trên phiếu; khung phải kể từng tờ, bấm số tờ mở **Phiếu đề nghị chi**; Bãi thấy dòng nhưng **không có số tiền** và không có tab **Hồ sơ gửi kế toán** | 23 | |
| T41 | `ketoan` · điều xe | **Vận tải → Đề nghị theo DO** → tab **Hồ sơ gửi kế toán** → **Đẩy hết tờ chưa đẩy** | Máy báo đẩy được bao nhiêu tờ; chỉ còn DO, PLNL, PTU, PC_TU, PC_SC (các tờ tiền vận chuyển không nằm ở đây); đẩy lại không gửi trùng | 21 | |
| T42 | `ketoan` · kế toán | **Sổ sách → Kế toán** → **Nhật ký chung** lọc nguồn *Sinh ở tiền vận chuyển (trang kế toán)* | Thấy các tờ HD, PT, PC_CX, TT, PC_NCC vừa làm; **Cân đối phát sinh** vẫn *Nợ = Có* | 22 | |
| T43 | `ketoan` · kế toán | **Chuyến & kho → Chuyến xe** → phiếu T14 | Doanh thu, chi phí, lãi, còn phải thu khớp những gì đã thu | 22–23 | |

### 10.7. Vai và chặn

| Mã | Ai · trang | Làm | Đúng khi | Đạt |
|---|---|---|---|---|
| T44 | `thabok` · kế toán | Đăng nhập trang kế toán | Không có nhóm **Tiền vận chuyển**, không mở sổ; Kho nhiên liệu chỉ thấy lít | |
| T45 | `thabok` · điều xe | **Vận tải → Nhà cung cấp**, **Xe liên kết** | Nhà cung cấp: danh sách, số dòng, kỳ trả, **không có tiền**; không có menu Xe liên kết | |
| T46 | `khovc` · kế toán | **Cấp phát** | Chỉ phiếu đề nghị xuất nhiên liệu của kho Viêng Chăn; quét phiếu đề nghị xuất nhiên liệu kho Thà Bốc → bị chặn | |
| T47 | `tx01` · điều xe | Chưa nhận tạm ứng mà bấm **Xuất phát** | Nút lớn **Xuất phát** tắt, dưới ghi *Chưa nhận tiền tạm ứng thì chưa xuất phát*; khung **Phiếu đề nghị tạm ứng** có nút **Mã QR** → hộp mã QR lớn + **Mã tra cứu** cho quỹ quét | 10 | |
| T47d | `thabok`, `ketoan`, `khotb` · điều xe | **Mô-đun kho → Xem kho** → ba tab; bấm dòng kho Thà Bốc; lập một phiếu thử có dầu kho rồi in đề nghị | Mỗi mặt hàng một dòng; phiếu thử hiện ở *Đã khai, chưa có đề nghị* rồi chuyển sang *Chờ cấp theo đề nghị* đúng số lít, **Còn lại** giảm theo; Bãi không có cột giá; thủ kho chỉ thấy màn này ở trang điều xe; không có nút thao tác kho | 6.7 | |
| T47c | `thabok` rồi `ketoan` · điều xe | **Hệ thống → Quy trình & trách nhiệm** → xem nút *màn … ↗* ở từng bước và các thẻ chứng từ | Vai không vào được màn nào thì chỗ đó là chữ xám *màn … · không thuộc vai của bạn*, không bấm được (sếp 30/09). Thẻ chứng từ ghi rõ *phiếu đề nghị · trang điều xe lập* (DO, PLNL, PTU) hay *bên kho / bên kế toán lập theo đề nghị*; DO tên **Phiếu xuất xe · đề nghị xuất xe** | |
| T47b | `thabok` · điều xe | Lập một phiếu **Gom** thử, để trống **Cân tại mỏ** → **Lưu** → **Xe đã tới · nhập cân cuối** → để trống ô **Cân tại mỏ (t)** → **Đồng ý** (cần tạm ứng đã chi, hoặc làm bằng `admin`) | Máy nhắc *Cân tại mỏ (t)?*, phiếu **chưa** thành *Đã tới*; gõ cân tại mỏ rồi **Đồng ý** thì được và **Kho hàng** có lô mới. Xoá phiếu thử bằng `admin` | |
| T48 | (tuỳ chọn) anh tắt máy 8030 | Trang điều xe: lưu phiếu giao có lấy lô, **Xe đã tới · nhập cân cuối** | Báo *Chưa nối được trang kế toán — thử lại sau*, không lưu nửa vời; bật lại thì làm tiếp được | |
| T49 | (tuỳ chọn) anh tắt máy 8020 | Trang kế toán: mở **Tất toán tài xế**, **Theo dõi nhà cung cấp**, **Hóa đơn vận chuyển** | Báo *Chưa nối được trang điều xe — thử lại sau*, không hiện nửa số; **Cấp phát** vẫn làm được bằng bản lưu trong máy | |

### 10.8. Việc ngoài chuyến — trang kế toán

| Mã | Ai · trang | Làm | Đúng khi | Mục | Đạt |
|---|---|---|---|---|---|
| T50 | `khonl` · kế toán | **Kho → Kho nhiên liệu** → **Nhập kho** 1.000 L bằng VND có tỷ giá → **Chuyển kho** 400 L về Thà Bốc | Giá bình quân tính lại; **PNK_NL**, **CK_NL**; chuyển quá tồn bị chặn | 6.1 | |
| T51 | `khopt` · kế toán | **Kho → Kho phụ tùng** → **Nhập kho** một phụ tùng → **Xuất cho xe** | **PNK_PT**, **PXK_PT**; tồn dưới tối thiểu tô đỏ | 6.3 | |
| T52 | `totsua` → `ketoancp` → `quytb` | **Kho → Lệnh sửa chữa** → **+ Lệnh sửa chữa** xe 345 → **Thêm dòng chi** (một dòng lấy kho, một dòng mua ngoài) → kiểm → ghi sổ → **Xác nhận đã chi** | Xe *đang sửa* bên điều xe rồi về rảnh; **PXK_PT** + **PC_SC** chỉ gồm phần mua ngoài | 6.4 | |
| T53 | `ketoan` · kế toán (làm **trước T30** để thấy đợt trả tự trừ) | **Kho → Bán hàng** → **Lập phiếu bán** → **Người mua**: **Chủ xe liên kết — trừ vào tiền trả** ທ້າວ ຄຳຫລ້າ → **+ Phụ tùng** (số nhỏ) → **Lập phiếu · xuất kho** | **PXK_BAN** + **HD_BAN** (Nợ 4022); bảng **Chủ xe liên kết** ở màn **Xe liên kết** hiện dòng *Hàng mua ở quầy chờ trừ*; sau T30 phiếu bán thành *Đã trừ* | 6.5 | |
