# Theo dõi xe cho đội 500 chiếc: điện thoại tài xế hay thiết bị GPS gắn xe

Tài liệu so sánh hai cách theo dõi vị trí xe cho EPL Lào, kèm chi phí gọi API Google và chi phí
vận hành thật ở quy mô 500 xe.

Ngày lập: 17/09/2026 · Hệ thống: EPL_LAO_REAL

---

## 1. Trả lời ngắn

**Điện thoại tài xế rẻ hơn thiết bị GPS gắn xe khoảng mười tới hai mươi lần, và triển khai được
ngay hôm nay.** Ba năm cho 500 xe, cách điện thoại tốn chừng **5.000 USD**, cách thiết bị tốn
**68.000 USD** nếu tự dựng máy chủ, hoặc **158.000 USD** nếu thuê nền tảng của hãng thiết bị.

Nhưng hai cách **không làm cùng một việc**. Điện thoại cho biết xe đang ở đâu. Thiết bị còn cho
biết xe có nổ máy không, dầu trong bình còn bao nhiêu, có ai rút dây ra không. Với một công ty chở
quặng mà tiền dầu chiếm phần lớn chi phí chuyến, cái thứ hai mới là thứ đáng tiền.

**Đề nghị: làm hai tầng.** Điện thoại cho toàn bộ đội xe ngay từ đầu, kể cả xe liên kết. Thiết bị
chỉ gắn cho xe nhà, và gắn vì cảm biến dầu chứ không phải vì vị trí.

---

## 2. Giả định dùng để tính

Mọi con số dưới đây dựa trên các giả định sau. Sai giả định thì sai kết quả, nên xin anh xác nhận
trước khi đưa cho khách.

| Khoản | Giá trị dùng để tính |
|---|---|
| Số xe | 500 |
| Ngày chạy mỗi tháng | 20 |
| Giờ chạy mỗi ngày | 10 |
| Số chuyến mỗi xe mỗi tháng | 10 (tổng 5.000 chuyến) |
| Người điều phối mở màn theo dõi | 10 đến 15 người |
| Nhịp gửi vị trí hiện tại | 1 điểm mỗi 25 giây |
| Tỉ giá quy đổi | 1 USD = 22.000 LAK |

Riêng số liệu dầu lấy từ chính tệp Excel của họ: một chuyến Kasi đi cảng đổ khoảng **150 lít ở kho
Thà Bốc** và mua thêm khoảng **750 lít bên Việt Nam** cho chiều về.

---

## 3. Cách A — điện thoại tài xế (cái đang chạy trong hệ thống)

Tài xế mở màn *Phiếu của tôi* trên điện thoại, bấm **Chia sẻ vị trí**, trình duyệt gửi toạ độ về
máy chủ EPL. Không cài app từ chợ ứng dụng, không mua gì cả.

### Chi phí

| Khoản | Cách tính | Tiền |
|---|---|---|
| Thiết bị | Tài xế dùng máy sẵn có | 0 |
| Dữ liệu di động | Khoảng 6 MB mỗi xe mỗi tháng | Không đáng kể |
| API Google | Xem mục 6 | 35 đến 85 USD mỗi tháng |
| Máy chủ và ổ đĩa | Phần tăng thêm do lưu vị trí | 30 đến 60 USD mỗi tháng |
| **Cộng mỗi tháng** | | **65 đến 145 USD** |
| **Cộng ba năm** | | **khoảng 2.300 đến 5.200 USD** |

Nếu công ty mua điện thoại cấp cho tài xế thì cộng thêm khoảng 120 USD mỗi máy, tức 60.000 USD cho
500 người. Con số đó xoá sạch lợi thế giá, nên chỉ nên làm nếu công ty muốn cấp máy vì lý do khác.

### Được gì

Triển khai ngay, không chờ mua hàng, không cần đưa xe vào xưởng. Gắn với **con người** chứ không
gắn với cái xe, nên biết ai đang chạy chuyến nào. Dùng được cho **xe liên kết** mà công ty không sở
hữu. Cùng một cái điện thoại đó còn làm được việc khác trong hệ thống: nhận phiếu lĩnh có mã QR,
báo hỏng dọc đường, khai đổ dầu bên Việt Nam.

### Mất gì

Tài xế quên bật, tắt đi, hết pin, hoặc đóng tab là mất tín hiệu. Trình duyệt ngừng gửi khi tài xế
đóng trang, nên trang phải để mở suốt chuyến. Không biết gì về cái xe: không biết nổ máy hay không,
không biết dầu còn bao nhiêu. Và tài xế hoàn toàn có thể tắt đúng lúc không muốn ai nhìn.

---

## 4. Cách B — thiết bị GPS gắn xe

Hộp định vị đấu vào điện xe, có SIM riêng, gửi dữ liệu thẳng về máy chủ.

### Chi phí

Giá thị trường, cần anh hỏi lại nhà cung cấp bên Lào và Việt Nam để chốt.

| Khoản | Đơn giá | 500 xe |
|---|---|---|
| Thiết bị | 40 đến 60 USD mỗi cái | 20.000 đến 30.000 USD |
| Công lắp | 10 đến 20 USD mỗi xe | 5.000 đến 10.000 USD |
| SIM và cước | 1,5 đến 3 USD mỗi xe mỗi tháng | 750 đến 1.500 USD mỗi tháng |
| Nền tảng của hãng (nếu thuê) | 4 đến 6 USD mỗi xe mỗi tháng | 2.000 đến 3.000 USD mỗi tháng |
| Hỏng và thay thế | Khoảng 5% mỗi năm | 1.000 đến 1.500 USD mỗi năm |

**Ba năm, tự dựng máy chủ nhận dữ liệu:** khoảng 32.500 USD ban đầu cộng 36.000 USD cước SIM, tổng
chừng **68.500 USD**.

**Ba năm, thuê nền tảng của hãng:** cộng thêm khoảng 90.000 USD, tổng chừng **158.500 USD**.

Cộng thêm phần không ra tiền mặt: 500 lượt đưa xe vào xưởng để lắp, mỗi lượt xe nằm vài tiếng.

### Được gì

Chạy liên tục, không phụ thuộc tài xế có nhớ bật hay không. Đấu vào điện xe nên không lo hết pin.
Báo được **trạng thái nổ máy**, thời gian xe đứng máy nổ, và quan trọng nhất là gắn thêm được
**cảm biến mức dầu trong bình**. Có cảnh báo khi ai đó tháo dây. Dữ liệu này dùng làm bằng chứng
với bảo hiểm và với khách hàng được.

### Mất gì

Tốn tiền ngay từ đầu. Không gắn được lên **xe liên kết** vì đó là xe của người khác, họ không cho
khoan lắp vào xe họ. Gắn với cái xe chứ không gắn với người, nên vẫn phải có cách biết ai đang lái.
Và nếu thuê nền tảng của hãng thì dữ liệu nằm bên hãng, muốn ghép vào phiếu xuất xe của mình lại
phải làm thêm một lớp nối.

---

## 5. So sánh ba năm

| | Điện thoại tài xế | Thiết bị, tự dựng máy chủ | Thiết bị, thuê nền tảng |
|---|---|---|---|
| Tiền bỏ ra ban đầu | 0 | 32.500 USD | 32.500 USD |
| Mỗi tháng | 65 đến 145 USD | 1.000 USD | 3.500 USD |
| **Ba năm** | **2.300 đến 5.200 USD** | **68.500 USD** | **158.500 USD** |
| Triển khai xong sau | 1 ngày | 2 đến 3 tháng | 2 đến 3 tháng |
| Dùng cho xe liên kết | Được | Không | Không |
| Phụ thuộc tài xế | Có | Không | Không |
| Biết nổ máy, mức dầu | Không | Có | Có |

---

## 6. Chi phí gọi API Google

### Tiền trả Google mỗi tháng

| Dịch vụ | Gọi khi nào | Lượt mỗi tháng | Tiền |
|---|---|---|---|
| Dynamic Maps | Mỗi lần mở màn theo dõi | 5.000 đến 12.000 | 35 đến 85 USD |
| Routes | Một lần cho mỗi tuyến, lưu lại dùng mãi | dưới 100 | Gần như 0 |
| Geocoding | Khi khai điểm dừng mới | vài chục | 0, nằm trong 10.000 miễn phí |
| Places và Autocomplete | Không dùng | 0 | 0 |

Tổng khoảng 35 đến 85 đô một tháng, tức chừng 1 đến 2 triệu kip. Với đội 500 xe thì đó là tiền lẻ.

Và con số này còn có thể bằng **không**, vì nền bản đồ hiện tại dùng ảnh vệ tinh Esri chứ không
phải Google. Nếu giữ nguyên nền đó thì chỉ trả tiền cho Routes và Geocoding, mà hai cái đó gọi rất
thưa.

### Cách làm sai khiến hoá đơn vọt lên

Màn theo dõi có ô tự cập nhật 30 giây. Nếu người lập trình khởi tạo lại bản đồ mỗi lần cập nhật thì
một người ngồi canh 8 tiếng sinh ra 960 lượt tải bản đồ một ngày.

| Cách làm | Lượt mỗi tháng | Tiền |
|---|---|---|
| Khởi tạo bản đồ một lần, cập nhật chỉ vẽ lại lớp | 12.000 | 85 USD |
| Khởi tạo lại mỗi 30 giây | 250.000 | 1.750 USD |

Code hiện tại theo cách thứ nhất: bản đồ dựng một lần khi mở màn, mỗi lần cập nhật chỉ xoá lớp vẽ
rồi vẽ lại chấm và đường. **Phải giữ nguyên nguyên tắc đó khi ai sửa về sau.**

Tương tự với Routes. Gọi một lần cho mỗi **tuyến** rồi lưu hình đường vào cơ sở dữ liệu thì gần như
miễn phí. Gọi theo từng **chuyến** thì 5.000 chuyến một tháng thành 25 đến 50 đô, không chết nhưng
vô ích vì cùng một tuyến đường lặp đi lặp lại.

### Lưu ý

Ảnh vệ tinh Esri đang dùng là dịch vụ miễn phí nhưng có điều khoản riêng. Triển khai thương mại cho
doanh nghiệp lớn thì phải đọc lại điều khoản đó, hoặc chuyển sang nền Google mà chịu tiền, hoặc tự
dựng máy chủ ảnh nền.

Bảng giá Google thay đổi khá thường xuyên, cần kiểm lại trước khi ký. Việc đầu tiên khi có tài
khoản là vào Google Cloud Console **đặt hạn mức và cảnh báo chi phí**, để nếu có ai viết sai vòng
lặp thì hoá đơn dừng lại chứ không chạy tới cuối tháng.

---

## 7. Khoản tốn thật ở quy mô 500 xe

Không phải Google mà là cơ sở dữ liệu của mình.

Mỗi xe gửi một điểm mỗi 25 giây, tức 1.440 điểm một ngày. Năm trăm xe chạy 20 ngày là **14,4 triệu
dòng một tháng**, cỡ 1,7 GB mỗi tháng kể cả chỉ mục. Một năm là hơn 170 triệu dòng. Bảng đó sẽ chậm
dần và ổ đĩa sẽ đầy.

Ba việc phải làm trước khi lên 500 xe, hiện chưa làm vì mới có 3 xe demo:

**Giãn nhịp gửi và chỉ ghi khi xe thật sự di chuyển.** Đổi từ 25 giây lên 60 giây, và bỏ điểm nào
cách điểm trước dưới 200 mét. Xe đứng chờ bốc hàng nửa ngày mà vẫn ghi 700 điểm giống hệt nhau là
phí. Riêng hai việc này cắt được khoảng 70 phần trăm.

**Dọn theo thời gian.** Giữ chi tiết từng điểm trong 30 ngày, quá hạn thì rút gọn còn một điểm mỗi
10 phút, quá một năm thì chỉ giữ quãng đường tổng.

**Đánh chỉ mục và chia bảng theo tháng.** Bảng vị trí là bảng ghi nhiều đọc ít, để chung một khối
vài trăm triệu dòng là truy vấn nào cũng chậm.

Sau khi làm ba việc trên, lượng dòng còn khoảng 4 triệu mỗi tháng và chi phí máy chủ giữ được ở mức
vài chục đô.

---

## 8. Chỗ quyết định: mô hình môi giới và xe liên kết

Đây là điểm quan trọng nhất của cả tài liệu, và nó thuộc về nghiệp vụ chứ không phải kỹ thuật.

EPL không chỉ chạy xe của mình. Mô hình của họ là **nhận cước rồi thuê lại xe ngoài**: bên A thuê
với giá 2, EPL thuê lại xe liên kết giá 1, lời 1. Hệ thống có sẵn khái niệm xe liên kết với cách
tính riêng, trừ 2% mỗi phiếu và 1 USD mỗi tấn vượt ngưỡng.

**Không thể gắn thiết bị lên xe của nhà thầu phụ.** Đó là tài sản của người ta. Nghĩa là nếu chỉ
chọn cách thiết bị, toàn bộ xe liên kết sẽ không có vị trí, mà đó lại chính là nhóm xe công ty ít
kiểm soát nhất và cần nhìn nhất.

Tỉ lệ xe nhà trên xe liên kết quyết định câu trả lời:

| Nếu đội xe là | Thì nên |
|---|---|
| Phần lớn xe nhà | Cân nhắc gắn thiết bị cho xe nhà, điện thoại cho phần còn lại |
| Phần lớn xe liên kết | Điện thoại là cách duy nhất phủ được toàn đội |
| Chia đôi | Hai tầng như mục 10 |

Xin anh cho con số tỉ lệ thật, hiện dữ liệu mẫu chỉ có 3 xe nên không suy ra được gì.

---

## 9. Dầu — chỗ thiết bị tự trả tiền cho chính nó

So sánh giá ở trên chỉ đúng khi coi hai cách làm cùng một việc. Nhưng thiết bị còn gắn được cảm
biến mức dầu, và với công ty này thì đó mới là lý do đáng mua.

Lấy từ Excel của họ: một chuyến đổ khoảng 150 lít ở kho cộng 750 lít mua bên Việt Nam, tiền dầu
chừng **1.000 USD một chuyến**. Nhân 5.000 chuyến một tháng là khoảng **5 triệu USD tiền dầu mỗi
tháng** cho cả đội.

| Nếu cắt được thất thoát dầu | Tiết kiệm mỗi tháng | Tiết kiệm ba năm |
|---|---|---|
| 0,5% | 25.000 USD | 900.000 USD |
| 1% | 50.000 USD | 1.800.000 USD |
| 2% | 100.000 USD | 3.600.000 USD |

Toàn bộ chi phí thiết bị ba năm là 68.500 USD. Chỉ cần cảm biến dầu cắt được **0,05%** thất thoát
là đã hoà vốn.

Nói cách khác: **mua thiết bị để biết xe ở đâu thì đắt, mua thiết bị để biết dầu đi đâu thì rẻ.**

Con số 5 triệu USD tiền dầu mỗi tháng là suy từ giả định 5.000 chuyến. Xin anh xác nhận lại sản
lượng thật, vì cả lập luận ở mục này dựa vào nó.

## 11. Những con số cần anh xác nhận

Tài liệu này sẽ sai nếu các con số dưới đây sai. Xin anh cho số thật trước khi đưa cho khách.

1. Đội xe thật có bao nhiêu chiếc, trong đó bao nhiêu là xe nhà và bao nhiêu là xe liên kết.
2. Mỗi tháng chạy bao nhiêu chuyến.
3. Giá thiết bị GPS và cước SIM tại Lào, vì đơn giá trong tài liệu là giá tham khảo thị trường.
4. Bảng giá Google mới nhất, vì họ đổi cách tính khá thường xuyên.
5. Công ty có định cấp điện thoại cho tài xế không, hay để tài xế dùng máy của mình.
