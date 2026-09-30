# Báo cáo 29–30/09/2026 — anh yêu cầu gì, em đã làm gì

Viết cho anh (chủ dự án) để đối chiếu: mỗi việc ghi **anh / sếp yêu cầu gì** (trích lời), **em đã làm gì**, **bấm ở đâu để xem**, và **chỗ còn cần anh quyết**. Cuối báo cáo là việc còn lại trên máy thật và phần chuẩn bị sang **API của anh Toàn (kho) và anh Tune (công nợ · thu chi)**.

Ký hiệu trạng thái: **Xong** · **Xong, cần anh xem** · **Chờ anh** · **Chưa làm**.

## 0. Trước khi xem

1. **Máy 8020 và 8030 đang chạy bản mới nhất** — anh khởi động lại lúc 13:34 ngày 30/09, sau lần sửa cuối (12:23). Chỉ cần **Ctrl+F5** trên trình duyệt.
2. Kiểm nhanh: menu trang điều xe có **Phiếu đề nghị chi**, **Phiếu đề nghị thu**, **Đề nghị theo DO** và nhóm **Mô-đun kho → Xem kho**.
3. Mật khẩu mọi tài khoản demo `1234`. Mỗi tab một tài khoản như mục 2.1 tài liệu A → Z (bỏ tick *Ghi nhớ đăng nhập*).

## 1. Bảng tổng

| # | Yêu cầu | Em đã làm | Trạng thái |
|---|---|---|---|
| 1 | Phiếu của mình chỉ là phiếu **đề nghị** (29/09) | Đổi tên hai phiếu cả 4 ngôn ngữ; tờ chi thật PC_TU gọi theo phiếu đề nghị | Xong |
| 2 | Tên phiếu là *"xuất **nguyên** liệu"* (30/09 chiều) | **Phiếu đề nghị xuất nguyên liệu** ở cả hai trang (51 chỗ) | Xong — **2 tờ cũ trên DB thật chờ anh cho đổi tên** |
| 3 | Tạm ứng · xuất dầu theo **loại xe**; giá bán riêng KT kho gõ trên phiếu (29/09) | Xe nhà: nội bộ. Xe thuê EPL ứng: ghi công nợ chủ xe; dầu kho là xuất bán theo ô **Giá bán cho chủ xe** | Xong |
| 4 | Xe nhà ứng thì tính vào tài xế; xe thuê muốn ứng thì ứng, ghi công nợ; chủ xe tự chi thì không ghi; *"bán xăng 50 ứng 100 thì là 150, còn trả họ là 50"* | Tất toán, Tiền chuyến chỉ xe nhà; xe thuê không có "trả cùng lương"; trả chủ xe = thuê − phí − quá tải − (dầu giá bán + mọi khoản EPL ứng); dầu kho chỉ rời kho theo phiếu đề nghị đã cấp | Xong |
| 5 | Sếp: **gợi ý chi phí theo Excel**, họ thêm bớt sửa | Mỗi tuyến một bộ gợi ý; chọn tuyến là mục III, IV, VI tự có dòng | Xong — **bộ gợi ý 5 tuyến trên máy thật chờ anh gật** |
| 6 | Sếp: tách **Phiếu đề nghị chi** / **Phiếu đề nghị thu** | Hai màn mới: danh sách trái · tờ in phải | Xong |
| 7 | Sếp: **trang quản lý DO** — *"DO nào phiếu chi gì trạng thái gì, DO nào phiếu thu gì trạng thái gì"*; DO xong thì sang anh Tune | Màn **Đề nghị theo DO**; tờ mới **PDT · Phiếu đề nghị thu** sinh lúc khoá phiếu (cả phiếu gom — anh xác nhận *"đúng"*) | Xong |
| 8 | Mục V, VI: *"tài xế báo về rồi theo role excel ai duyệt, xong tạo phiếu như bình thường"* | Không làm tờ đề nghị riêng; giữ luồng báo hỏng → duyệt theo vai → phiếu chi | Xong (giữ nguyên) |
| 9 | Sếp: **Quy trình** ràng buộc vai; chứng từ sinh ra là phiếu đề nghị | Nút sang màn chỉ bấm được với vai vào được; thẻ chứng từ ghi bên lập; bước 15 có PDT; bảng quyền có dòng **giá vốn kho** | Xong |
| 10 | Sếp: làm rõ **hai loại phiếu Giao / Gom** | Hai thẻ lớn chọn loại ở phiếu mới; nhãn loại to ở cột phải và dưới số phiếu | Xong, cần anh xem |
| 11 | Sếp: làm lại **Phiếu của tôi** (tài xế), phá cách, tôn trọng người Lào | **Vé chuyến**: một nút lớn cho bước tiếp theo, ô bấm to, mã QR ngay trên vé | Xong, cần anh xem |
| 12 | Sếp: **kho** dời về trang logistics, **theo item, chỉ xem**, *"chi tiết luôn"* | Màn **Xem kho** theo mặt hàng; số tồn hỏi bên kho | Xong |
| 13 | Sếp: giao diện **không xổ dọc dài**, dùng bề ngang | 11 màn: phiếu xuất xe, 3 màn đề nghị, xem kho, tài xế, **Xe, Khách hàng, Theo dõi phiếu, Tuyến đường** | Xong 11 màn · **9 màn còn lại chưa rà** (mục 6) |
| 14 | Anh hỏi *"mấy cái em vừa làm mới có phân quyền hết chưa"* | Dò 12 vai, vá 4 lỗ; bài kiểm quyền cố định | Xong |
| 15 | Thủ kho, thủ kho phụ tùng, tổ sửa chữa **không thấy giá vốn kho** (anh: *"chốt theo em"*) | Ẩn ở Xem kho, danh mục phụ tùng, phiếu xuất xe, màn Xe, Theo dõi tuyến; dòng kho luôn theo giá bình quân | Xong |
| 16 | Viết lại tài liệu theo luồng đề nghị | Tài liệu A → Z + Word (bản 30/09 trưa) | Xong phần sáng · **phần chiều chưa cập nhật** |

## 2. Chi tiết từng việc

### 2.1. Phiếu đề nghị, tên phiếu (việc 1, 2)

**Anh nói:** *"tạm thời các phiếu của mình chỉ là phiếu đề nghị thôi, đề nghị xuất nguyên liệu, đề nghị tạm ứng"* (29/09); *"nguyên liệu nhé"* (30/09 chiều).

**Em làm:** tên hai tờ là **Phiếu đề nghị xuất nguyên liệu** (mã `PLNL-…`) và **Phiếu đề nghị tạm ứng** (mã `PTU-…`); tờ quỹ chi thật PC_TU là **Phiếu chi theo đề nghị tạm ứng**; DO mang cả hai tên *Phiếu xuất xe · đề nghị xuất xe*. Trang kế toán (Cấp phát, Điểm đổ, nhóm chi phí màn Chuyến xe) đổi chữ theo. **Giữ chữ "nhiên liệu"** ở mục III *Chi phí nhiên liệu* và *kho nhiên liệu* vì đó là dầu; tiếng Lào (ໃບສະເໜີເບີກນໍ້າມັນ) và tiếng Anh (*Fuel issue request*) giữ nghĩa dầu.

**Còn lại:** trang kế toán lưu tên phiếu lúc nhận tờ, nên trên DB thật còn **2 tờ** mang tên cũ. Máy thử đã đổi (10 tờ). Anh gật thì em chạy `python tools/doi_ten_to_de_nghi.py that` ở EPL_KETOAN — chỉ đổi cột tên của 2 tờ đó.

### 2.2. Tạm ứng, xuất dầu theo loại xe (việc 3, 4)

**Em làm:** đầu mục III, IV của phiếu có dòng chữ đậm nói bản chất (*Xuất nội bộ — xe công ty (EPL)* · *Xuất bán cho chủ xe · <tên>* · *Tạm ứng nội bộ* · *Tạm ứng ghi công nợ chủ xe · <tên>*), hai tờ đề nghị in dòng đó dưới tiêu đề. Xe thuê: KT kho xăng dầu gõ **Giá bán cho chủ xe** khi kiểm mục III; thiếu thì không kiểm được. **Ghi sổ mục III bị chặn** nếu còn dầu kho chưa cấp theo phiếu đề nghị.

**Bấm thử:** tài liệu A → Z mục 4.0 (bảng luật và ví dụ thuê 200 · dầu 50 · ứng 100 → còn trả 50), ca T27, T27b.

### 2.3. Gợi ý chi phí theo tuyến (việc 5)

**Sếp nói:** *"dựa vào Excel kê sẵn chi phí cho họ kiểu gợi ý, họ thêm bớt chỉnh sửa bình thường"*.

**Em làm:** **Danh mục → Tuyến đường**: khung chi tiết có bảng **Chi phí gợi ý theo tuyến** (nhóm theo mục); hộp **Sửa** có **+ Thêm dòng**, **×**, **Chép bộ chung (Excel)**. Phiếu xuất xe: chọn tuyến là mục III, IV, VI tự có dòng, dưới ô **Chọn tuyến** ghi *Đã điền chi phí gợi ý theo tuyến …*. Bãi không thấy đơn giá gợi ý; máy điền giá lúc lưu cho kế toán. Tuyến chưa có bộ riêng dùng **bộ chung theo Excel**.

**Bấm thử:** `thabok` → **Phiếu xuất xe** → **Phiếu mới** → mục **II** chọn tuyến **ກາສີ → ທ່າບົກ** → mục III có sẵn 200 L kho Thà Bốc, mục IV có tiền nước, tiền chuyến, điện thoại (ca T01c).

**Chờ anh:** gieo bộ gợi ý cho 5 tuyến mẫu trên máy thật. Em đã chạy thử (không ghi) trên 8020, máy sẽ điền:

| Tuyến | Dầu | Mục IV |
|---|---|---|
| ກາສີ → ທ່າບົກ | 200 L kho Thà Bốc | tiền nước 60.000 · tiền chuyến (kế toán gõ) · điện thoại 150.000 |
| ຊຽງຂວາງ → ທ່າບົກ | 360 L kho Thà Bốc | như trên |
| ທ່າບົກ → ທ່າເຮືອກະລໍ | 100 L kho Thà Bốc + 750 L kho xe Việt Nam | nước 60.000 · sang VN 430.000 · chipping Lào 620.000 · chipping Việt 1.500.000 · tiền chuyến 1.800.000 · điện thoại 150.000 |
| ທ່າບົກ → ດ່ານ ນໍ້າພາວ | 300 L kho Thà Bốc | nước 60.000 · chipping Lào 620.000 · tiền chuyến (kế toán gõ) · điện thoại 150.000 |
| ທ່າບົກ → ວຽງຈັນ | 140 L kho Thà Bốc | nước 60.000 · tiền chuyến (kế toán gõ) · điện thoại 150.000 |

Số lít là số mẫu theo km — anh sửa ở màn Tuyến đường. Lệnh ghi thật: `python tools/mau_chi_phi_tuyen.py http://127.0.0.1:8020 that` (đi qua API bằng tài khoản `ketoan`, chỉ điền tuyến còn trống).

### 2.4. Phiếu đề nghị chi (việc 6)

**Em làm:** **Vận tải → Phiếu đề nghị chi**. Trái: danh sách tờ, lọc **Tất cả · Tạm ứng · Nguyên liệu** và **Chờ cấp · Đã cấp · Đã huỷ · Tất cả**, ô tìm số đề nghị / DO / xe / tài xế; mỗi tờ có dải màu (xanh dương tạm ứng, nâu nguyên liệu), số tiền hoặc số lít, trạng thái. Phải: tờ in đúng khổ (mã QR, dòng bản chất theo loại xe), nút **Mở phiếu**, **In**. Hai nút ở cột phải phiếu xuất xe mở thẳng màn này ở đúng tờ.

**Bấm thử:** `ketoan` → **Vận tải → Phiếu đề nghị chi** → bấm một tờ ở danh sách.

### 2.5. Phiếu đề nghị thu (việc 7)

**Sếp nói:** DO xong thì sinh qua anh Tune để anh ấy tạo SO rồi thu công nợ.

**Em làm:** tờ **PDT · Phiếu đề nghị thu** (ໃບສະເໜີຮັບເງິນ). **Kế toán khoá phiếu là máy tự lập tờ** — phiếu gom cũng vậy (gom có cước riêng): cước theo **đúng tiền tệ của phiếu** (ví dụ 24,7 t × 30,5 USD = 753,35 USD) kèm số quy Kíp theo tỷ giá khoá; khách, hợp đồng, tuyến, xe, số POD, người ký nhận. Không định khoản — bên công nợ làm. **Mở khoá** rút tờ chưa gửi; tờ **đã gửi** thì kế toán không mở khoá được, Sếp mở được. Màn **Vận tải → Phiếu đề nghị thu**: thanh **Chờ gửi · Đã gửi · Đã xuất hoá đơn · Đã thu đủ · Chờ khoá phiếu · Tất cả**, dải tổng **theo từng tiền tệ**, tờ in, nút **Gửi bên công nợ**, nút **Lập phiếu đề nghị thu** cho phiếu khoá trước 30/09. Chỉ vai thấy tiền bán.

**Bấm thử:** `ketoan` khoá một phiếu giao đã về → **Vận tải → Phiếu đề nghị thu** → nút **Chờ gửi** (ca T19b, T19c).

**Phiếu khoá trước 30/09 trên máy thật** (9 phiếu) đều đã có hoá đơn, nên màn hiện *Đã xuất hoá đơn* / *Đã thu đủ* — không cần lập bù.

### 2.6. Đề nghị theo DO (việc 7, 8)

**Em làm:** màn *Phiếu chi · Phiếu thu* cũ thành **Vận tải → Đề nghị theo DO**. Tab **Theo DO**: mỗi DO một dòng — nhãn Giao / Gom (+ Xe thuê), xe · tài xế, khách · tuyến; cột **Đề nghị chi**: chip **TU** (tạm ứng), **NL ×n** (đề nghị xuất nguyên liệu), bốn ô **III · IV · V · VI** màu theo chuỗi duyệt; cột **Đề nghị thu**; cột **Đã gửi kế toán** (x/y). Lọc **Tất cả · Chi còn chờ · Thu còn chờ**, ô **Tháng**, ô tìm. Bấm một DO → khung phải kể từng tờ; bấm số tờ mở màn in. Tab **Hồ sơ gửi kế toán** là sổ chứng từ cũ. Mục V, VI giữ luồng cũ (việc 8) — màn này chỉ hiện trạng thái của hai mục đó.

**Bấm thử:** `ketoan` → **Vận tải → Đề nghị theo DO** → nút **Chi còn chờ** → bấm một DO (ca T41b).

### 2.7. Phiếu xuất xe dàn ngang, Giao / Gom rõ (việc 10, 13)

**Sếp nói:** *"xổ xuống dưới phải kéo dài nhiều khoảng trống, lỗi thời, khó dùng, đau mắt"*; hai loại phiếu phải rõ.

**Em làm:** màn chia hai cột. Trái: tờ phiếu. **Phải (dính theo khi cuộn):** nhãn loại to (**Gom · mỏ → bãi** nâu / **Giao · bãi → khách** xanh; xe thuê thêm nhãn vàng tên chủ xe), số DO · xe · tài xế, trạng thái; **sáu mục I–VI thành danh sách dọc có chữ trạng thái**; tiền tóm tắt; ba nút **Phiếu đề nghị tạm ứng · Phiếu đề nghị xuất nguyên liệu · Phiếu đề nghị thu**; việc mức phiếu (khoá, xe đã tới, đổi xe…); các bước duyệt thu gọn; câu nhắc theo vai. Phiếu mới có **hai thẻ lớn** chọn Gom / Giao.

**Bấm thử:** `thabok` → **Phiếu xuất xe** → **Phiếu mới** → bấm thẻ **Gom** rồi **Giao** (ca T00).

**Cần anh xem:** cột phải rộng 300px có vừa không; danh sách mục dọc thay tab ngang có dễ dùng hơn không.

### 2.8. Phiếu của tôi — vé chuyến (việc 11)

**Em làm:** chuyến đang chạy là một **vé**: đầu vé xanh đậm, dải hoa văn hình thoi ngăn đầu và thân; **Điểm đi → Điểm đến** chữ to; thanh bước **Nhận tạm ứng · Xuất phát · Báo cân / Giao · ký nhận · Về tới**; khung **Phiếu đề nghị tạm ứng** và đề nghị nguyên liệu (số tiền / số lít, trạng thái, nút **Mã QR** mở mã lớn cho quỹ / thủ kho quét — mất mạng vẫn mở được); **một nút lớn** dưới **Bước tiếp theo**; việc phụ là ô bấm cao có hình. Chuyến khác ở cột **Phiếu gần đây**.

**Bấm thử:** `tx03` (hoặc `tx01`) → **Phiếu của tôi**, thử cả khổ điện thoại.

**Cần anh xem:** dải hoa văn giữ hay bỏ. Em không đặt lời chào *ສະບາຍດີ* / *ຂອບໃຈ* vì hai chữ này chưa có trong từ điển của họ — anh muốn thêm thì em thêm.

### 2.9. Xem kho (việc 12)

**Em làm:** **Mô-đun kho → Xem kho**, mọi vai trừ tài xế. Ba tab **Nhiên liệu · Phụ tùng · Kho hàng**. Dải số: tổng tồn dầu, phiếu đề nghị chờ cấp, phụ tùng dưới mức tối thiểu, hàng khách gửi ở bãi. Mỗi mặt hàng một dòng: **Tồn**, **Chờ cấp theo đề nghị**, **Đã khai, chưa có đề nghị**, **Còn lại** (âm thì đỏ) kèm thanh màu, nhập / xuất trong tháng, giá bình quân (chỉ kế toán, quỹ, Sếp). Bấm dòng → khung phải: đề nghị chờ cấp, dầu đã khai chưa có đề nghị, lô còn hàng, 10 lần nhập / xuất gần nhất. **Không có nút thao tác kho nào.**

**Bấm thử:** `thabok` → **Xem kho** → tab **Nhiên liệu** → bấm kho Thà Bốc (ca T47d).

**Chờ anh quyết:** **thủ kho nhiên liệu chỉ thấy kho của mình** ở tab Nhiên liệu (em làm theo luật "một thủ kho một kho" của màn Cấp phát). Anh muốn thủ kho thấy mọi kho thì em mở ra.

### 2.10. Bốn màn cũ dàn ngang (việc 13)

**Anh nói:** *"hoàn thiện giúp anh nhé"* — Xe, Khách hàng, Theo dõi phiếu, Tuyến đường. Cả bốn giờ **vừa một màn hình**.

| Màn | Trước | Sau |
|---|---|---|
| **Xe** | Bảng 34 dòng cao, trang dài ~2.000px; hồ sơ xe là ngăn trượt | **Hồ sơ xe đứng cố định ở cột phải**, bấm dòng nào thấy xe đó ngay; danh sách cuộn trong khung; hãng · đời một dòng (~870px). Màn hẹp dưới 1100px vẫn là ngăn trượt |
| **Khách hàng** | Bảng ngắn, dưới trống; mỗi dòng 4 nút gãy hai hàng; bảng giá, công nợ hiện chồng xuống dưới | **Danh sách khách trái**; phải là thẻ khách (điện thoại, địa chỉ, cách xuất hoá đơn, hợp đồng, ghi chú, **Sửa**) và ba tab **Hợp đồng · Bảng giá · Công nợ** mở tại chỗ. Hai tab tiền chỉ vai thấy tiền |
| **Theo dõi phiếu** | Thanh lọc gãy hai hàng; bảng tràn ngang mất cột | Thanh lọc một hàng; **Xuất báo cáo**, **Tạo phiếu xuất xe** lên đầu bảng; **ba cột #, Ngày, Số phiếu đứng yên** khi cuộn ngang. Cấu trúc bảng theo mẫu khách đã duyệt giữ nguyên |
| **Tuyến đường** | Khung chi tiết tràn ra ngoài màn; bảng gợi ý gãy từng chữ (~1.400px) | Hết tràn; bỏ hai cột Điểm đi / Điểm đến (đã có trong tên tuyến); khung chi tiết dính bên phải; chi phí gợi ý nhóm theo mục, mỗi khoản một dòng |

**Bấm thử:** `ketoan` → lần lượt **Danh mục → Xe**, **Khách hàng**, **Vận tải → Theo dõi phiếu vận chuyển**, **Danh mục → Tuyến đường**.

### 2.11. Phân quyền (việc 14, 15)

**Anh hỏi:** *"mấy cái em vừa làm mới có phân quyền hết chưa"*. Em dò thật 12 tài khoản trên máy thử: menu, nút đã ẩn đúng nhưng **máy chủ chưa chặn theo menu** — 4 lỗ, đã vá:

1. **Tài xế xem được mã QR tờ đề nghị của phiếu người khác** nếu biết mã phiếu → nay chỉ phiếu của mình.
2. Thủ kho, thủ kho phụ tùng, tổ sửa chữa không có màn **Đề nghị theo DO** mà vẫn lấy được dữ liệu kèm tiền chi → chặn.
3. Tổ sửa chữa, thủ kho phụ tùng đọc được danh sách phiếu đề nghị → chặn.
4. Phiếu xuất xe: KT Doanh thu, tổ sửa chữa thấy nút lập tờ đề nghị (bấm là lỗi) → nút chỉ hiện với vai được lập; tổ sửa chữa thấy doanh thu 0 và lãi sai → nay không.

**Giá vốn kho (anh chốt *"theo em"*):** thủ kho nhiên liệu, thủ kho phụ tùng, tổ sửa chữa **không thấy giá bình quân** dầu, phụ tùng (thủ kho giữ số lượng, kế toán giữ giá trị; giá vốn lộ ra là lộ lãi bán dầu cho chủ xe, bán phụ tùng ở quầy). Ẩn ở Xem kho, danh sách phụ tùng, phiếu xuất xe (tổ sửa không thấy đơn giá dòng **lấy kho** và tổng chi; dòng **mua ngoài / garage** vẫn thấy, vẫn ghi giá), màn Xe tab Sửa chữa, Theo dõi tuyến. **Dòng phụ tùng lấy kho luôn theo giá bình quân**, như dầu kho — tổ sửa lưu phiếu không làm giá thành 0. Lúc rà em thấy thêm **màn Xe vẫn cho Bãi xem tiền sửa chữa** (sót từ trước khi khách chốt "Bãi không thấy tiền" 23/09) — đã chặn.

**Quyền hiện tại:**

| Màn | Ai vào được | Tiền |
|---|---|---|
| Xem kho | Mọi vai trừ tài xế; thủ kho nhiên liệu chỉ kho mình | Giá vốn: chỉ kế toán, quỹ, Sếp |
| Phiếu đề nghị chi | Bãi, các kế toán, 2 quỹ, Sếp; thủ kho chỉ tờ kho mình; tài xế chỉ tờ của mình (trên vé) | Bãi không thấy số tiền tạm ứng |
| Phiếu đề nghị thu | Chỉ vai thấy tiền bán | Lập bù, gửi tờ: KT Thu/Chi, Sếp |
| Đề nghị theo DO | Bãi, các kế toán, 2 quỹ, Sếp | Bãi không thấy số tiền; tab **Hồ sơ gửi kế toán** Bãi không vào |
| Khoá / mở khoá phiếu | KT Thu/Chi, Sếp; tờ đề nghị thu đã gửi thì chỉ Sếp mở khoá | — |

### 2.12. Sửa nhỏ kèm theo

- Màn Phiếu đề nghị chi: dòng nguồn danh mục đổi thành *Danh mục Acc code từ API kế toán* (bỏ tên anh Khang).
- Màn **Quy trình & trách nhiệm**: bảng quyền có thêm dòng **Thấy giá vốn kho**.
- Hai bài kiểm có gọi trang kế toán nay **bắt buộc truyền đủ hai địa chỉ** — trước đây thiếu địa chỉ thứ hai thì bài tự gọi sang 8030 của anh (sự cố em đã báo chiều 30/09: chỉ đăng nhập 3 tài khoản và gọi một mã phiếu không có, bên đó trả 404, không ghi gì).

## 3. Việc còn trên máy thật — chờ anh gật

| # | Việc | Số liệu (em đã xem, chưa ghi) | Lệnh |
|---|---|---|---|
| 1 | Gieo chi phí gợi ý 5 tuyến mẫu | Bảng ở mục 2.3 | `python tools/mau_chi_phi_tuyen.py http://127.0.0.1:8020 that` (EPL_LAO_REAL) |
| 2 | Đổi tên 2 tờ đã nhận sang "nguyên liệu" | 29 tờ thuộc ba loại, 2 tờ cần đổi | `python tools/doi_ten_to_de_nghi.py that` (EPL_KETOAN) |
| 3 | Push GitHub hai nhánh | EPL_laoreal và repo EPL_KETOAN | — |

**Phiếu thật còn dầu kho chưa cấp theo phiếu đề nghị** — từ 30/09 ghi sổ mục III của các phiếu này sẽ bị chặn cho tới khi in phiếu đề nghị xuất nguyên liệu và thủ kho cấp ở **Cấp phát** (trang kế toán):

| Phiếu | Xe đang | Mục III | Dầu kho chưa cấp |
|---|---|---|---|
| G4-0103-09 | chưa xuất bến | đã nhập | 2 × 300 L |
| T4-0445-09 | chưa xuất bến | đã nhập | 160 L |
| T4-0432-08 | chưa xuất bến | đã nhập | 150 L |
| G4-0101-09 | đã về | đã nhập | 60 L |
| T4-0433-09 | đang chạy | đã kiểm | 90 L |
| T4-0428-08 | đang chạy | đã kiểm | 100 L |
| T4-0429-08 | đã về | đã kiểm | 120 L |
| T4-0430-08 | đã về, **đã khoá** | đã kiểm | 150 L — Bãi không lập đề nghị trên phiếu khoá được, KT Thu/Chi lập |

(Ba phiếu T4-0431-08, T4-0440-09, T4-0441-09 cũng có dòng dầu kho không gắn lần xuất nhưng mục III **đã chi** từ trước — không bị ảnh hưởng.)

## 4. Kiểm tự động (máy thử 8011 · 8031, bản sao DB)

Đạt sau lần sửa cuối: `thu_giao_dien.js` (19 màn · 4 ngôn ngữ · không lộ khoá chữ · phân vai tài xế, thủ kho), `thu_quyen_de_nghi_kho` (12 vai × các đường mới + giá vốn kho), `thu_de_nghi`, `thu_kho_xem`, `thu_loai_xe`, `thu_luong_api`, `thu_chu_xe`, `thu_kho_xe_23_09`, `thu_the_cao_toc`, `thu_tien_te`; trước đó trong ngày cũng đạt `thu_goi_y_chi_phi`, `thu_phieu_linh`, `thu_hop_dong_pod`, `thu_giao_nhan`, `thu_vai_va_doi_xe`.

## 5. Chuẩn bị sang API anh Toàn và anh Tune

Hiện trang điều xe nói chuyện với **trang kế toán tạm (8030)** qua đường liên thông có khoá. Khi có API thật, mỗi đường dưới đây đổi đích sang hệ của anh Toàn hoặc anh Tune.

### 5.1. Anh Toàn — kho

| Việc | Hướng | Đường đang dùng (bên tạm) | Dùng ở đâu bên mình |
|---|---|---|---|
| Tồn + giá bình quân từng kho dầu | mình đọc | `GET /api/lien-thong/nhien-lieu/kho` | giá dầu kho trên phiếu, Xem kho |
| Tồn theo mặt hàng (dầu, phụ tùng, hàng khách gửi), nhập / xuất tháng, lần gần nhất | mình đọc | `GET /api/lien-thong/kho/mat-hang` | Xem kho |
| Danh mục phụ tùng + tồn + giá | mình đọc | `GET /api/lien-thong/phu-tung` | ô chọn phụ tùng mục V |
| Lô hàng khách gửi còn hàng; hàng của một phiếu | mình đọc | `GET /api/lien-thong/kho-hang/lo`, `…/kho-hang/phieu/{id}` | phiếu giao lấy lô |
| Xuất phụ tùng cho dòng mục V (chống trùng bằng khoá), huỷ xuất | mình gửi | `POST …/phu-tung/xuat`, `…/huy-xuat` | duyệt báo hỏng lấy kho |
| Xuất dầu theo đề nghị, huỷ xuất | mình gửi | `POST …/nhien-lieu/xuat`, `…/huy-xuat` | đường xuất dầu còn trong mã |
| Nhập hàng vào bãi (xe gom tới), xuất hàng (phiếu giao), huỷ | mình gửi | `POST …/kho-hang/nhap`, `…/xuat`, `…/huy-nhap`, `…/huy` | xe gom tới bãi, lưu phiếu giao |
| Lệnh sửa chữa của một xe | mình đọc | `GET …/sua-chua/xe/{id}` | màn Xe, tab Sửa chữa |
| Cấp nguyên liệu theo phiếu đề nghị (quét QR) | **bên kho gọi mình** | `GET /api/lien-thong/cap-phat`, `…/tra-cuu/{mã}`, `POST …/cap-phat/{id}/cap` | phiếu đề nghị thành *Đã cấp* |

Cần báo anh Toàn luật **thủ kho không thấy giá vốn** — màn Cấp phát ở trang kế toán tạm hiện vẫn cho thủ kho thấy giá; chỗ đó thuộc phần kho của anh ấy nên em không sửa.

### 5.2. Anh Tune — công nợ · thu chi

| Việc | Hướng | Đường đang dùng (bên tạm) | Dùng ở đâu bên mình |
|---|---|---|---|
| Gửi tờ đề nghị / chứng từ: DO, PLNL, PTU, **PDT**, PC_TU, PC_SC | mình gửi | `POST {api}/api/v1/epl-lao/vouchers` (hợp đồng JSON cũ `DOCS/md/HOP_DONG_API_ANH_KHANG.md` — cần làm lại cho anh Tune) | Hồ sơ gửi kế toán, nút **Gửi bên công nợ** |
| Trạng thái hoá đơn · đã thu của DO | **bên công nợ gọi mình** | `POST /api/lien-thong/doanh-thu/xuat`, `…/bo-xuat`, `…/da-thu` | Phiếu đề nghị thu, Đề nghị theo DO, khoá / mở khoá |
| Công nợ một khách; cấn trừ cuối tháng | mình đọc | `GET …/doanh-thu/khach/{id}`, `…/doanh-thu/can-tru` | Khách hàng → tab Công nợ |
| Trả chủ xe (đã trả, bỏ trả) | bên công nợ gọi mình | `POST /api/lien-thong/chu-xe/tra`, `…/bo-tra` | phiếu xe thuê, Xe liên kết |
| Số liệu để bên đó tính (tiền chuyến, tất toán, nhà cung cấp, cước) | bên công nợ đọc mình | `GET /api/lien-thong/tien-tai-xe`, `…/tat-toan`, `…/ncc`, `…/doanh-thu/phieu` | — |
| Danh mục Acc code | mình đọc | `/api/acc-codes` (không nối được thì dùng bản dự phòng) | ô mã tài khoản trên dòng chi |

### 5.3. Câu hỏi cần chốt khi họp hai anh

1. **Xác thực:** khoá máy (token) cấp thế nào, mỗi bên một khoá hay dùng chung; người bấm gửi kèm theo không (hiện gửi `X-Nguoi-Dung`).
2. **Chống trùng:** mỗi lần gửi mang khoá riêng (hiện: số chứng từ `ref`, khoá dòng `trip_expense:<id>`) — hai anh có nhận khoá này không.
3. **Mã chung:** kho dầu, phụ tùng, mặt hàng, khách, chủ xe, nhà cung cấp — bên nào giữ bản gốc, bên kia chép theo mã nào.
4. **Trạng thái ngược về:** bên kho báo *đã cấp*, bên công nợ báo *đã hoá đơn / đã thu / đã trả chủ xe* bằng cách **gọi sang mình** (như bây giờ) hay **mình hỏi định kỳ**.
5. **Tiền tệ:** mọi số gửi đi mang mã tiền của chứng từ (USD, LAK, THB, VND) kèm tỷ giá khoá trên phiếu.
6. **Khi hệ kia tắt:** bên mình đang **chặn và báo rõ** những việc cần hệ kia (lưu phiếu giao lấy lô, xe gom tới bãi…) — giữ luật này không.

## 6. Còn lại

| Việc | Trạng thái |
|---|---|
| Thủ kho nhiên liệu chỉ thấy kho mình hay mọi kho (mục 2.9) | Chờ anh quyết |
| Ba việc trên máy thật ở mục 3 | Chờ anh gật |
| 9 màn chưa rà bố cục theo ý sếp: Tổng quan, Theo dõi tuyến, Tài xế, Thẻ cao tốc, Tỷ giá, Xe liên kết, Nhà cung cấp, Quy trình, Tài khoản (Theo dõi tuyến là màn khách thích nhất — em sẽ giữ khung, chỉ gọn lại) | Chưa làm |
| Tài liệu A → Z: bổ sung phần chiều 30/09 (phân quyền, giá vốn kho, bốn màn dàn lại, tên nguyên liệu, trạng thái máy thật) | Chưa làm |
| Hai bản **hợp đồng API** — anh Toàn (kho), anh Tune (công nợ · thu chi) — theo mục 5 | Chưa làm, là bước tiếp theo |
