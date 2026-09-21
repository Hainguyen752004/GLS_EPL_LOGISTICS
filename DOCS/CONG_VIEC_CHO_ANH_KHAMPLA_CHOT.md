# Việc đang chờ chốt — EPL Lào

Cập nhật **21/09/2026**. Ngày này sếp đã chốt câu quan trọng nhất (một chuyến đi qua **hai DO**) và
giao cho bên mình tự quyết phần còn lại theo logic vận tải chuyên nghiệp. Tệp này ghi lại **đã chốt gì,
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
| **B3, C8.2** | **Mỗi DO giao một hoá đơn**, tính trên tấn cân ở nơi giao × đơn giá | Hoá đơn khớp một lần giao, đối chiếu phiếu cân dễ; gom theo tháng làm sau cũng không phá cấu trúc |
| **B4** | DO gom **không có cước**, chỉ có chi phí | Khách trả cho việc đưa hàng tới cảng; chặng gom là việc nội bộ giữa hai chân của cùng một dịch vụ |
| **A2** | Bãi thấy mọi khoản **chi**; không thấy **tiền bán** (cước, doanh thu, hoá đơn, giá thuê xe ngoài, lãi, mã TK) | Bãi là người chi nên phải thấy chi; chênh lệch giá bán và giá thuê là biên lợi nhuận |
| **C3.1** | Cân đầu = **cân của mỏ**, nhập trên DO gom | Đó là số trên phiếu quặng khách giao |
| **C3.2** | Cân cuối = **cân ở nơi giao**, nhập trên DO giao | Hoá đơn tính trên số này |
| **C3.3** | Tài xế chụp ảnh phiếu cân, **đính kèm vào phiếu**; máy nhắc khi khoá nếu còn thiếu | Giấy dễ mất, ảnh vào phiếu thì kế toán ở Viêng Chăn xem được ngay |
| **C3.4** | Hao hụt **chỉ theo dõi**, không tự trừ tiền khách; quá 1,5 % thì cờ đỏ và cảnh báo khi khoá | Hợp đồng chưa nói trừ; nhưng hao hụt đã có **dòng riêng** nên bật trừ tiền sau rất nhanh |
| **C3.5, C3.6** | Giá lấy từ **bảng giá khách × tuyến** (có ngày hiệu lực), tính trên **tấn ở điểm đến** | Giá hợp đồng nhập một lần, phiếu tự điền, kế toán chỉ sửa khi chuyến đó khác hợp đồng |
| **C3.7** | Số và ngày phiếu quặng do **Bãi nhập lúc bốc hàng**, kèm ảnh | Người cầm giấy là người nhập |
| **C4.1** | Giá thuê xe ngoài do **kế toán Viêng Chăn** nhập | Người ký với chủ xe; và Bãi không được thấy giá thuê |
| **C4.2** | 2 %/phiếu và 1 USD/tấn vượt 40 t là **mặc định**, sửa được trên từng phiếu | Đủ cho hợp đồng khác nhau mà không phải dựng danh mục chủ xe |
| **C4.3** | Trả chủ xe **theo từng phiếu**, sau khi phiếu khoá | Khớp với chứng từ `PC_CX` từng phiếu; gom tháng làm sau nếu họ cần |
| **C4.4** | Các khoản EPL ứng **trừ hết** vào tiền trả chủ xe | Đúng bảng tính trong Excel của họ |
| **C5.1** | Tài xế nhập **lít + đơn giá + trạm**, kế toán kho xăng dầu duyệt | Tài xế trả tiền mặt tại trạm nên chỉ họ biết giá |
| **C5.2** | Hai kho dầu: **Thà Bốc** và **Viêng Chăn** | Theo dữ liệu họ gửi |
| **C5.3** | Giá dầu xuất kho **bình quân** | Tránh nhảy giá theo từng lần nhập |
| **C6.1** | Thẻ cao tốc ghi **như khoản chi thường**, chưa theo dõi số dư | Thêm "ví thẻ" là một tầng nữa mà Excel của họ không có; làm khi họ thấy cần |
| **C6.2** | Tiền chuyến, tiền nước tính **theo chuyến** | Theo ghi chú trong Excel |
| **C1.2, C7.1, C7.2** | Kho phụ tùng và tổ sửa chữa coi là **người của Bãi**; Bãi duyệt báo hỏng và quyết định sửa kho hay gara | Không đẻ thêm vai khi chưa chắc có người thật |
| **C7.3** | Sửa xe tại bãi vẫn **gắn phiếu gần nhất** | Lệnh sửa chữa riêng là một luồng mới; xem mục 3.3 |
| **C1.3** | Tài xế **có** dùng điện thoại: nhận phiếu, khai đổ dầu, báo hỏng, chia sẻ GPS | Đã làm xong màn tài xế |
| **C2.1, C2.2** | Ngày về và km về do **Bãi** ghi khi xe về; kiểm mục I xong Bãi không sửa gì thêm | |
| **C8.3** | Khách trả chuyển khoản hoặc tiền mặt, **có trả một phần** | Đã có trạng thái *thu một phần* |
| **C9.1** | Màn phiếu chia **tab theo mục**, mỗi vai mở đúng tab của mình | Đã làm xong |
| **C9.2** | Ngôn ngữ mặc định ở máy bãi: **tiếng Lào** | Người dùng ở bãi là người Lào; đổi một nút là xong và máy nào nhớ theo máy đó |

---

## Phần 2. Vẫn phải chờ bên EPL trả lời

| Mã | Câu hỏi | Vì sao không tự quyết được |
|---|---|---|
| **C5.4** | Mã tài khoản **kho**: `37`, `371` hay `137`? | Ba tài liệu của họ ghi ba số khác nhau. Đang dùng `371` |
| **C5.5** | Mã **nhà cung cấp**: `402` hay `4021`? | Đang dùng `402` |
| **C5.6** | Mã **tiền mặt** và **ngân hàng** | Chưa có trong tài liệu nào; đang để trống tên, chưa có mã. **Phải có trước khi bàn giao dữ liệu cho bên anh Khang**, không thì sổ sai mã |
| **C1.1** | Tên người giữ tài khoản *KT Thu/Chi VC* và *KT Chi phí VC* | Chỉ họ biết |
| **C8.1** | Những khoản hay rơi vào mục VI | Cần họ liệt kê để đặt sẵn danh mục |

Ba câu mã tài khoản sửa rất nhanh (một bảng trong `services/chung_tu.py`), nhưng sai thì sổ kế toán sai.

---

## Phần 3. Nợ kỹ thuật bên mình tự biết

### 3.1 Máy chủ vẫn trả giá bán cho mọi vai ở các API khác

Hai báo cáo của màn Tổng quan đã **bỏ hẳn** các khoá tiền bán với Bãi, tài xế, thủ kho. Nhưng
`/api/trips` và `/api/bao-cao/theo-doi` vẫn trả đơn giá, thành tiền, lãi cho mọi vai — giao diện có che
nhưng mở công cụ trình duyệt là thấy.

Chưa dọn ngay vì chỗ này đụng đường dữ liệu chung của màn phiếu (`xuat_phieu` dùng cho cả nhập liệu lẫn
báo cáo), sửa vội dễ hỏng phép tính. Nay A2 đã chốt nên **làm được rồi**: khoảng nửa ngày, kèm bộ kiểm
chặn ở mức API chứ không chỉ ở giao diện.

### 3.2 Ảnh xe chưa lưu được

Bản thiết kế màn Xe có khung ảnh. Máy chủ chưa có chỗ chứa tệp cho ảnh xe (phần đính kèm hiện chỉ làm
cho phiếu quặng), nên khung ảnh để trống kèm dòng ghi rõ là chưa lưu được — không để nút bấm chết.
Khoảng nửa ngày, dùng lại đúng chỗ chứa tệp của phiếu.

### 3.3 Lệnh sửa chữa không gắn chuyến

Sửa xe tại bãi lúc xe không chạy hiện phải gắn vào phiếu gần nhất, hơi gượng. Một lệnh sửa chữa riêng
theo xe sẽ sạch hơn (khoảng một ngày). Chờ xem họ có làm bảo dưỡng định kỳ thật không đã.

### 3.4 Ô "Việc của tôi" của KT Doanh thu luôn là 0

Ô này đếm mục I–VI đang chờ chính vai đó làm. KT Doanh thu không phụ trách mục nào — việc của họ là
hoá đơn và thu tiền, nằm ở mức phiếu. Họ đã có chip *Chờ hoá đơn* riêng. Làm gọn khi có dịp: cho ô này
đếm phiếu đã khoá chưa xuất hoá đơn cộng hoá đơn chưa thu tiền.

---

## Phần 4. Chờ bên khác

| Việc | Chờ ai | Hiện đang làm gì |
|---|---|---|
| Khoá Google Routes / Geocoding | Anh cấp khoá | Tuyến và km nhập tay; bản đồ vẽ từ toạ độ trong CSDL |
| **Đường nhận chứng từ** | Anh Khang | **Bên mình đã làm xong lớp đẩy** (21/09): nút Đẩy, thử lại khi lỗi, chống gửi trùng, Sếp đặt địa chỉ và token trong màn hình. Hợp đồng JSON đề nghị ở `HOP_DONG_API_ANH_KHANG.md`. Chỉ chờ anh Khang cho địa chỉ + token, và chốt tên đường nếu muốn khác `/api/v1/epl-lao/vouchers` |
| Mã tài khoản còn thiếu (tiền mặt, ngân hàng, hàng khách gửi, giá vốn) | Anh Khang | Đang để tên không mã; sửa một bảng `services/chung_tu.py` khi có |
| API công nợ phải thu / phải trả | Anh Khang | Chưa làm; chỉ đọc và hiện nếu anh có đường sẵn |
| Danh mục Acc code | Anh Khang | Ô chọn định khoản đang dùng danh mục dự phòng, mã lạ thì ghi rõ "không có trong danh mục" |
