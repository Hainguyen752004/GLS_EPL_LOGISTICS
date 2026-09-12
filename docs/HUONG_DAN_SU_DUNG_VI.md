# EPL Logistics — Hướng dẫn sử dụng

Tài liệu thao tác cho người vận hành: từng màn hình, từng nút bấm, và điều gì xảy ra
sau khi bấm.

Bản cập nhật: 12/09/2026 · Áp dụng cho nhánh `EPL_11_9_26`

---

## Mục lục

1. [Trước khi bắt đầu](#1-trước-khi-bắt-đầu)
2. [Khung màn hình dùng chung](#2-khung-màn-hình-dùng-chung)
3. [Luồng làm việc từ đầu tới cuối](#3-luồng-làm-việc-từ-đầu-tới-cuối)
4. [Dữ liệu gốc](#4-dữ-liệu-gốc)
5. [Khách hàng và cơ hội](#5-khách-hàng-và-cơ-hội)
6. [Báo giá cước](#6-báo-giá-cước)
7. [Lệnh giao hàng](#7-lệnh-giao-hàng)
8. [Điều phối và thực thi](#8-điều-phối-và-thực-thi)
9. [Theo dõi và kiểm soát](#9-theo-dõi-và-kiểm-soát)
10. [Hoàn tất giao hàng](#10-hoàn-tất-giao-hàng)
11. [Ghi sổ kinh doanh](#11-ghi-sổ-kinh-doanh)
12. [Trang tài xế](#12-trang-tài-xế)
13. [Trang chủ và bảng điều khiển](#13-trang-chủ-và-bảng-điều-khiển)
14. [Các lời từ chối thường gặp](#14-các-lời-từ-chối-thường-gặp)
15. [Từ điển thuật ngữ](#15-từ-điển-thuật-ngữ)

---

## 1. Trước khi bắt đầu

**Mở hệ thống.** Gõ địa chỉ máy chủ vào trình duyệt. Hệ thống này là một module nằm
trong hệ thống lớn hơn, nên nó không có màn đăng nhập riêng — việc xác thực do hệ
thống cha lo.

**Ba điều nên biết ngay:**

- Hệ thống làm việc với **bốn đơn vị tiền**: VNĐ, USD, THB, LAK. Mỗi phiếu mang đơn vị
  tiền của riêng nó, và màn hình luôn hiện đúng đơn vị đó — không tự quy đổi.
- **Mọi con số tiền đều có gốc.** Giá thành lấy từ công thức của loại xe; cước lấy từ
  báo giá đã thoả thuận với khách. Không chỗ nào cho gõ một con số không có nguồn.
- **Hệ thống hay từ chối, và luôn nói vì sao.** Khi bấm một nút mà bị chặn, hãy đọc
  câu thông báo — nó chỉ đích danh thứ còn thiếu và màn cần sang để sửa. Mục 14 liệt
  kê các lời từ chối hay gặp.

---

## 2. Khung màn hình dùng chung

Phần này giống nhau ở mọi màn.

### 2.1. Thanh điều hướng trên cùng

| Mục | Mở ra |
|---|---|
| **⌂ Hôm nay** | Trang chủ — việc cần làm hôm nay |
| **Vận hành** | Lệnh giao hàng · Giao hàng và vận chuyển · Điều phối · Theo dõi · Hoàn tất giao hàng · Packing List |
| **Kinh doanh** | Khách hàng và cơ hội · Báo giá cước |
| **Dữ liệu gốc** | 10 thẻ khai dữ liệu nền |
| **Báo cáo và khác** | Phân tích doanh thu và chi phí · Trạm kiểm soát AI |

Bấm vào tên nhóm để mở bảng chọn, rồi bấm mục con.

### 2.2. Nút Quay lại

Nằm ở **đầu trang, bên trái tên màn**. Bấm để lùi về màn trước.

Ba cách lùi đều chạy như nhau:

- Nút **← Quay lại** trên màn
- Nút **Back** của trình duyệt
- Vuốt lùi trên điện thoại, hoặc phím `Alt + ←`

Nút tự ẩn khi đang ở màn đầu tiên — không có chỗ nào để lùi thì không hiện nút.

> **Mẹo:** địa chỉ trên trình duyệt mang mã màn (ví dụ `#dispatch`). Tải lại trang (F5)
> vẫn ở đúng màn đang xem, và gửi đường dẫn cho đồng nghiệp thì họ mở đúng chỗ đó.

### 2.3. Đổi ngôn ngữ

Nút cờ ở góc trên bên phải: **Tiếng Việt · English · ລາວ**. Ngôn ngữ được nhớ cho
những lần mở sau.

### 2.4. Hộp xác nhận

Những việc không hoàn lại được (xoá, ghi sổ, huỷ ca) luôn hỏi lại bằng một hộp của
ứng dụng. Hộp ghi rõ việc sẽ xảy ra, và **hai nút ghi đúng việc** — ví dụ
`[ Để lại ]` và `[ Xoá xe ]`, không phải OK/Cancel. Bấm `Esc` hoặc bấm ra ngoài hộp
là huỷ.

---

## 3. Luồng làm việc từ đầu tới cuối

```
 Cơ hội  ──►  Báo giá  ──►  Khách chấp nhận
                                   │
                                   ▼  (tự động, không bấm tay)
                            Lệnh giao hàng (DO)
                                   │
                                   ▼
                              Lập chuyến (Trip)
                                   │
                                   ▼
                          Điều phối: gán xe + tài xế
                                   │
                                   ▼
                        Tài xế ghi mốc trên điện thoại
                                   │
                                   ▼
                    Hoàn tất giao hàng: POD + chốt giá
                                   │
                                   ▼
                     Ghi sổ kinh doanh → hệ công nợ
```

**Ba tầng cần phân biệt:**

| Tầng | Là gì | Thuộc về |
|---|---|---|
| **Báo giá (QT)** | Thoả thuận với khách: tuyến nào, loại xe gì, giá bao nhiêu | Khách và giá |
| **Lệnh giao hàng (DO)** | Một lần giao cụ thể: lô hàng này, lấy ngày này, giao trước giờ này | Nhu cầu của khách |
| **Chuyến (Trip)** | Một chuyến xe thật: xe nào, tài xế nào, chạy lúc nào | Cách công ty thực hiện |

Một báo giá sinh ra nhiều lệnh giao hàng. Một chuyến có thể chở nhiều lệnh, và một
lệnh cũng có thể cần nhiều chuyến.

> **Không có đường tạo lệnh giao hàng bằng tay.** Lệnh giao hàng chỉ sinh ra khi khách
> chấp nhận báo giá — vì chỉ khi đó nó mới mang theo giá đã khoá. Một lệnh gõ tay
> không có giá nào chống lưng, và bước quyết toán sẽ không biết lấy con số ở đâu.

---

## 4. Dữ liệu gốc

**Vào:** Dữ liệu gốc trên thanh điều hướng.

Màn này có 10 thẻ. **Thứ tự khai rất quan trọng** — thẻ sau dùng dữ liệu của thẻ
trước.

| Thẻ | Khai gì | Cần có trước |
|---|---|---|
| **0. Setup A–Z** | Hướng dẫn thứ tự khai, bấm thẳng sang từng thẻ | — |
| **1. Tuyến đường vận chuyển** | Chặng A → B → C, km kế hoạch, phí BOT | — |
| **2. Công thức giá thành & xăng dầu** | Đơn giá từng khoản mục theo loại xe | Loại xe |
| **3. Loại phương tiện** | Tải trọng, thể tích, số pallet tối đa | — |
| **4. Sắp lịch xe và tài xế** | Ca trực theo tuần | Xe, tài xế |
| **5. Tài xế & bằng lái** | Hồ sơ tài xế, hạng bằng, hạn bằng | — |
| **6. Tỷ giá tiền tệ** | VNĐ · USD · THB · LAK | — |
| **7. Danh mục khách hàng** | Tên, liên hệ, điều khoản thanh toán | — |
| **8. Carrier / Vendor** | Nhà xe thuê ngoài | — |
| **9. Mapping tài khoản** | Acc code cho từng khoản mục chi phí | — |

### 4.1. Tuyến đường

**Thêm tuyến:** khai mã tuyến, tên, rồi từng chặng (điểm đi → điểm đến, km).

Khi lưu, hệ thống **tự tra toạ độ** các điểm và vẽ đường bộ thật. Nếu có điểm không
tra được, thông báo sẽ ghi rõ tên điểm đó — hãy khai toạ độ tay cho nó, nếu không bản
đồ theo dõi sẽ thiếu một điểm và vị trí xe mô phỏng đặt sai chỗ.

> Tuyến qua biên giới nên khai **đúng các chặng**, ví dụ
> `Viêng Chăn → Cửa khẩu Cầu Treo → Cảng Cửa Lò`. Khai một đường thẳng thì bản đồ vẽ
> xuyên qua núi, và điểm dừng biên giới không hiện ra.

### 4.2. Công thức giá thành

Công thức có **hai tầng**: công thức chuẩn theo **loại xe**, và từng chiếc xe chỉ ghi
đè vài con số khác biệt.

Mỗi khoản mục có **Acc code** — mã phân loại chi phí do bên công nợ cấp. Thiếu Acc code
thì hồ sơ bàn giao sẽ báo dòng đó chưa phân loại được.

> **Lưu ý quan trọng:** trong bảng cấu phần, "Cước phí vận chuyển /kg" là **giá bán**,
> không phải chi phí. Bốn cấu phần còn lại (xăng dầu, phụ cấp tài xế, cầu đường, bãi)
> mới là giá thành. Đừng cộng cả năm vào một con số.

### 4.3. Tài xế & bằng lái

Mỗi tài xế cần **hồ sơ** (tên, hạng bằng, vai trò) và **một dòng bằng lái** còn hạn,
đúng hạng ghi trên hồ sơ.

**Vai trò** quyết định tài xế có lái chính được không. Người khai "Phụ xe" không nhận
được vai trò lái chính khi điều phối.

**Ca trực** (thẻ 4) phải phủ khung giờ của chuyến. Thiếu ca là điều phối bị chặn.

---

## 5. Khách hàng và cơ hội

**Vào:** Kinh doanh → Khách hàng và cơ hội.

Đây là **bước đầu tiên của luồng**: ghi nhận yêu cầu của khách trước khi có báo giá.

### 5.1. Ba cách xem

| Nút | Hiện gì |
|---|---|
| **Bảng cơ hội** | Kanban — kéo thả cơ hội giữa các giai đoạn |
| **Danh sách** | Bảng phẳng, lọc và tìm nhanh |
| **Khách hàng** | Hồ sơ 360° từng khách: cơ hội, báo giá, lệnh, doanh thu |

### 5.2. Các nút

| Nút | Việc |
|---|---|
| **+ Cơ hội** | Tạo cơ hội mới. Khai khách (hoặc tên khách tiềm năng chưa có mã), liên hệ, nguồn, tuyến, loại hàng, khối lượng, sản lượng/tháng, giá khách mong đợi |
| **+ Cơ hội cho khách này** | Như trên, điền sẵn khách đang xem |
| **Lập báo giá** | **Đây là nút chuyển bước.** Sinh báo giá nháp kế thừa khách, tuyến, hàng và sản lượng; cơ hội tự chuyển sang giai đoạn *Đã báo giá* |
| **Xem báo giá** | Mở báo giá đã gắn với cơ hội |
| **Thắng / Mất** | Đánh dấu kết quả. Chọn *Mất* thì **bắt buộc ghi lý do** |
| **Mở lại** | Đưa cơ hội đã đóng về lại trạng thái đang theo |

**Sáu giai đoạn:** Mới · Đã liên hệ · Đang thương lượng · Đã báo giá · Thắng · Mất.

> Hai giai đoạn *Đã báo giá* và *Thắng* **hệ thống tự đặt** — khi lập báo giá và khi
> khách chấp nhận. Không kéo tay vào hai giai đoạn này.

---

## 6. Báo giá cước

**Vào:** Kinh doanh → Báo giá cước.

### 6.1. Thanh trên cùng

| Nút | Việc |
|---|---|
| **+ Báo giá** | Lập báo giá mới |
| **↻ Làm mới** | Tải lại danh sách |
| **↓ Xuất Excel** | Xuất danh sách đang lọc |

### 6.2. Trong một phiếu báo giá

Phiếu chia ba nhóm tab:

- **Khách hàng và hành trình** — khách, tuyến, loại xe, khung giờ lấy/giao
- **Báo giá & lệnh giao hàng** — hàng hoá, giá thành, cước, chiết khấu
- **Chứng từ & ghi chú** — tệp đính kèm, ghi chú nội bộ và ghi chú gửi khách

| Nút | Việc |
|---|---|
| **+ Thêm dòng hàng hoá** | Khai mặt hàng, số lượng, đơn vị tính |
| **Lưu nháp** | Lưu lại, chưa gửi ai |
| **Gửi duyệt nội bộ** | Dùng khi biên lợi nhuận **dưới ngưỡng công ty** — phiếu chờ trưởng phòng duyệt |
| **Duyệt nội bộ và gửi khách** | Trưởng phòng duyệt rồi gửi thẳng cho khách |
| **Gửi khách** | Gửi báo giá cho khách (biên đủ ngưỡng thì đi thẳng đường này) |
| **Khách từ chối** | Ghi nhận khách không đồng ý; **bắt buộc ghi lý do** |
| **Nhân bản** | Chép phiếu này thành phiếu mới |
| **Lịch sử giá** | Các lần sửa giá của phiếu |
| **In nội bộ** | Bản in đầy đủ: giá thành từng khoản, biên, ghi chú nội bộ |
| **☁ Chọn tệp và đính kèm** | Gắn tệp vào phiếu |

### 6.3. Giá được tính thế nào

1. Hệ thống đọc **công thức giá thành** của loại xe đang chọn và tính giá thành chuyến.
2. Bạn chọn **biên lợi nhuận** → ra cước.
3. **Chiết khấu** (nếu có) là tỉ lệ giảm trên cước đó.

Đơn vị tiền chọn riêng cho từng phiếu. Chọn Kíp Lào thì giá thành cũng quy theo tỷ giá
đã khai ở Dữ liệu gốc.

> Báo giá **lỗ** (cước thấp hơn giá thành) sẽ bị từ chối khi gửi.

### 6.4. Khách chấp nhận

Khi khách đồng ý, bấm nút chấp nhận trên phiếu. Hệ thống làm **trong cùng một giao
dịch**:

- Chuyển báo giá sang *Đã tách*
- **Sinh lệnh giao hàng**, mang theo tuyến, giá đã khoá và khung giờ
- Chuyển cơ hội sang *Thắng*

Một báo giá có thể sinh nhiều lệnh (mỗi lô một lệnh) — khai số lô lúc chấp nhận.

---

## 7. Lệnh giao hàng

**Vào:** Vận hành → Lệnh giao hàng (DO).

### 7.1. Dải số liệu

Sáu ô đếm, bấm vào để lọc: **Lệnh giao hàng · Tuyến tham chiếu · Cần xử lý · Đang chạy
· Hoàn thành · Đã hủy · Tất cả**.

### 7.2. Các nút

| Nút | Việc |
|---|---|
| **Lệnh giao hàng sinh từ báo giá →** | Dẫn sang màn Báo giá. Ở đây **không có** form tạo lệnh trắng |
| **Tạo chuyến** | Chọn một hoặc nhiều lệnh cùng tuyến rồi lập chuyến |
| **Xem báo giá** | Mở báo giá gốc của lệnh |
| **Thêm khoản phí / Lưu chi phí** | Ghi chi phí phát sinh gắn vào lệnh |

### 7.3. Lập chuyến

Khai: mã chuyến, ngày giờ khởi hành, vận tốc kế hoạch, thời gian dừng mỗi chặng.

**Loại chuyến:**

| Loại | Khi nào dùng |
|---|---|
| **Một chiều** | Giao xong là hết chuyến |
| **Nhiều điểm dừng** | Một chuyến chở nhiều lệnh, mỗi lệnh một điểm giao riêng. Chỉ xếp được trên tuyến từ **2 chặng trở lên** |
| **Khứ hồi (có lượt về)** | Có chặng xe về bãi. Phải chọn **tuyến chiều về**, và tuyến đó phải bắt đầu đúng nơi tuyến đi kết thúc |

> **Chở hàng chiều về tạm thời chưa dùng được.** Lệnh giao hàng chiều về hiện chưa ký
> nhận được nên chuyến sẽ không đóng được và xe bị giữ lại. Chọn *Xe về rỗng*, hoặc
> lập một chuyến riêng cho lô hàng chiều về.

---

## 8. Điều phối và thực thi

**Vào:** Vận hành → Điều phối và thực thi.

Đây là màn gán **xe** và **tổ lái** cho chuyến.

### 8.1. Thanh lọc trên cùng

| Điều khiển | Việc |
|---|---|
| **Phạm vi** | Lọc theo bãi và theo loại xe |
| **Ô tìm** | Tìm nhanh mã lệnh, khách hàng, tuyến |
| **‹ · ngày · ›** | Lùi / tiến một ngày |
| **Hôm nay** | Về ngày hiện tại |
| **⚡ Xếp DO còn lại** | Tự xếp xe cho những lệnh chưa có |

> **Màn này lọc theo NGÀY.** Nếu cột lệnh trống, đọc dòng chữ bên dưới — nó cho biết
> còn bao nhiêu lệnh đang chờ ở ngày khác và có nút bấm thẳng sang ngày đó. Nút cam
> **Tồn đọng** là lệnh đã tới ngày lấy hàng mà chưa ai xếp xe — gấp hơn việc ngày mai.

### 8.2. Dải số liệu

**DO trong ngày · Đã xuất bến · Chờ xếp · Thiếu Trip · Xe rảnh/tổng · Tài xế trong ca**

### 8.3. Cột trái — DO chờ điều phối

Nhóm theo **Theo tuyến · Theo khách · Theo hạn**. Tick nhiều lệnh để gán một lượt.

### 8.4. Cột giữa — Đội xe theo bãi

Mỗi bãi hiện số xe **rảnh / đang chạy / bảo dưỡng**. Chọn một lệnh thì cột này lọc ra
xe phù hợp.

Sắp xếp: **Phù hợp nhất · Cùng bãi · Rảnh sớm nhất**.

### 8.5. Các nút gán

| Nút | Việc |
|---|---|
| **Chọn xe trước** | Chọn xe rồi mới chọn lệnh |
| **Đổi** | Đổi xe hoặc tài xế đã gán |
| **Thêm** | Thêm phụ xe |
| **Lưu điều phối** | Lưu phân công, chưa cho chạy |
| **Chốt điều phối & xuất bến** | Xác nhận và cho xe chạy |

### 8.6. Cột phải — Ngoại lệ cần duyệt

Những việc hệ thống chặn hoặc cảnh báo: giấy tờ xe sắp hết hạn, bằng lái sắp hết hạn,
xe khác loại báo giá… Bấm vào để xem chi tiết, nút **← Quay lại danh sách ngoại lệ**
để trở ra.

---

## 9. Theo dõi và kiểm soát

**Vào:** Vận hành → Theo dõi và kiểm soát.

Bản đồ và tiến độ của các chuyến **đang chạy**.

| Nút | Việc |
|---|---|
| **Cập nhật GPS** | Lấy vị trí mới nhất |
| **Tải lại** | Nạp lại toàn bộ danh sách |
| **Cập nhật timeline** | Làm mới dòng mốc hành trình |
| **+ Báo Sự Cố Mới** | Khai sự cố: loại, mức độ, vị trí, mô tả |
| **Gửi báo cáo sự cố** | Lưu sự cố vào hệ thống |

**Trên bản đồ:**

- Đường **đỏ đậm** là phần đã đi, **nét đứt xám** là phần còn lại
- Ghim xe ở vị trí hiện tại; xe cùng chỗ được toả nhẹ ra để không chồng lên nhau
- Ghim các điểm dừng, đánh số theo thứ tự

**Vị trí mô phỏng.** Khi thiết bị không gửi GPS mới trong 15 phút, hệ thống tính vị trí
theo tiến độ tuyến và đánh dấu rõ là **mô phỏng**. Đó không phải GPS thật — mốc do tài
xế ghi mới là mốc thật.

---

## 10. Hoàn tất giao hàng

**Vào:** Vận hành → Hoàn tất giao hàng.

Hai thẻ: **Chờ hoàn tất** và **Đã hoàn tất**.

### 10.1. Thẻ "Chờ hoàn tất"

Mỗi dòng là một lệnh đang chờ ký nhận.

| Nút | Việc |
|---|---|
| **Xem DO** | Xem chi tiết lệnh và giá |
| **Hoàn tất giao** | Mở phiếu ký nhận |
| **↻** (cạnh ô giá) | Tải lại giá nếu ô ghi *Chưa tải được giá* |

### 10.2. Phiếu hoàn tất

**Phần 1 — Bằng chứng giao hàng (POD).** Mỗi điểm giao khai một khối:

- Giờ giao · Người nhận · Số điện thoại
- Kết quả giao: *Giao đủ hàng · Giao thiếu · Khách từ chối nhận*
- **Ảnh biên bản** (bắt buộc)
- **Chữ ký người nhận** — ký trực tiếp trên màn
- Tình trạng hàng / ghi chú

**Phần 2 — Chốt giá cuối.** Bảng khoản mục từ công thức giá thành, mỗi dòng có ô
**Khách trả thêm**. Tổng tự cộng vào *Giá cuối*.

| Nút | Việc |
|---|---|
| **Thêm khoản phí** | Thêm một dòng phụ thu ngoài bảng |
| **Quay lại** | Đóng phiếu, không lưu |
| **Hoàn tất giao hàng & chốt giá** | Nộp POD, chốt giá, đóng lệnh |

> Chuyến nhiều điểm giao **phải ký đủ mọi điểm** mới đóng được lệnh.

> Với báo giá ngoại tệ mà chưa có công thức giá thành bằng đúng đơn vị đó, bảng sẽ lấy
> khoản mục từ công thức VNĐ và **ghi rõ điều đó**. Các ô ở đó chỉ để tham khảo, không
> cộng vào giá bán. Khoản khách trả thêm vẫn khai được, bằng đúng tiền của báo giá.

### 10.3. Thẻ "Đã hoàn tất"

Hồ sơ của các lệnh đã đóng. Nút **Xem hồ sơ** mở ra:

- Năm ô số: Cước theo báo giá · Khách trả thêm · Giá cuối · Chi phí nội bộ · Lợi nhuận
- Thông tin lệnh đầy đủ
- **Sổ thu – chi**: từng dòng thu và chi, mỗi dòng có **Acc code**, cột *Chốt ban đầu* /
  *Thực tế* / *Khách trả thêm hoặc chênh*
- Ảnh POD và chữ ký

| Nút | Việc |
|---|---|
| **Cập nhật giá thực tế / Chốt cước** | Sửa chi phí thực tế sau khi có hoá đơn |
| **Ghi sổ kinh doanh** | Đẩy sang hệ công nợ — xem mục 11 |

---

## 11. Ghi sổ kinh doanh

Nút này nằm trên **hồ sơ đã hoàn tất**, cạnh *Cập nhật giá thực tế / Chốt cước*.

**Việc nó làm:** đẩy lệnh đã giao sang hệ QLSX của bên công nợ để tạo **đơn hàng bán**
và **ghi công nợ** cho khách theo giá cuối đã chốt.

**Cách dùng:**

1. Bấm **Ghi sổ kinh doanh**
2. Đọc hộp xác nhận, bấm **Ghi sổ**
3. Thành công thì nút đổi thành chip xanh **Đã ghi sổ kinh doanh · SO-…**

Mốc *Bàn giao công nợ* trên hồ sơ cũng ghi mã đơn hàng bán và số công nợ ban đầu.

> **Làm một lần.** Bên công nợ không có đường sửa hay xoá từ đây. Đã ghi sổ rồi thì nút
> biến mất.

> Công nợ ghi bằng **đúng tiền của báo giá** — đơn Kíp Lào ghi Kíp, không quy về đồng.

Nếu bị từ chối, nút vẫn còn và có dòng ghi lỗi lần trước. Ba lỗi hay gặp:

| Lỗi | Nghĩa là | Ai xử lý |
|---|---|---|
| Mã khách chưa có bên QLSX | Khách này chưa được khai bên công nợ | Bên công nợ |
| Chưa bật tích hợp | Hệ QLSX chưa mở đường nhận | Bên công nợ |
| Tiền tệ chưa hỗ trợ | QLSX chỉ nhận VNĐ, USD, LAK | Thống nhất lại với bên công nợ |

---

## 12. Trang tài xế

Trang riêng cho tài xế, mở trên **điện thoại**. Đây là một ứng dụng độc lập, không nằm
trong hệ thống chính.

**Mở:** chạy `python chay.py` trong thư mục `EPL_TaiXe`, rồi mở địa chỉ hiện ra trên
điện thoại cùng mạng.

### 12.1. Màn danh sách

Chạm vào **tên mình** ở đầu trang để chọn tài xế (hệ thống nhớ cho lần sau). Danh sách
chỉ hiện **chuyến của người đó**.

Mỗi thẻ ghi: mã lệnh · khách · tuyến · trạng thái · số chặng đã xong · xe · hạn giao.

### 12.2. Màn chi tiết

Chạm một thẻ để mở. Màn có:

- **Bản đồ** — đường đã đi tô đỏ, phần còn lại nét đứt, ghim xe và các điểm dừng
- **Bốn số**: Đã đi % · Còn lại km · Tốc độ · Đến dự kiến
- **Thanh mốc** sáu bước: Vào bãi → Lấy hàng → Xuất bến → Đến điểm giao → Dỡ hàng → Giao xong
- **Thông tin lệnh** và **danh sách chặng**
- **← Quay lại** ở góc trên

### 12.3. Ba nút việc (dán ở đáy màn)

| Nút | Việc |
|---|---|
| **📍 Ghi mốc: …** | Ghi mốc kế tiếp theo đúng thứ tự. Ghi **thật** vào hệ thống, vị trí xe trên bản đồ điều độ nhích theo. Không hoàn lại được |
| **✍ Hoàn tất giao hàng** | Mở phiếu ký nhận. **Chỉ bật sau khi đã ghi mốc *Đến điểm giao*** |
| **⚠ Báo sự cố** | Khai loại sự cố, mức độ, vị trí, mô tả — điều phối thấy ngay |

### 12.4. Phiếu ký nhận trên điện thoại

Mỗi điểm giao một khối: giờ giao · người nhận · số điện thoại · kết quả · **ảnh biên
bản** (chụp thẳng bằng máy) · **chữ ký vẽ tay** · ghi chú. Kèm bảng giá để khai khoản
khách trả thêm.

> **Giới hạn của bản demo:** trang này **chưa có đăng nhập**. Việc "tài xế nào chỉ thấy
> chuyến của mình" là lọc ở phần trình bày, không phải lớp bảo mật — ai mở trang cũng
> chọn được tên người khác.

---

## 13. Trang chủ và bảng điều khiển

### 13.1. Hôm nay

- **Dải số hôm nay**: lệnh giao hàng · chuyến đang đi · cơ hội cần liên hệ · sự cố ·
  **hồ sơ sẵn sàng bàn giao**
- **Việc cần làm ngay**: lệnh quá hạn, báo giá sắp hết hạn, sự cố chưa đóng…
- **Dòng chảy hôm nay**: sáu trạm nối ống — Cơ hội → Báo giá → Lệnh giao hàng → Điều
  phối → Đang chạy → Hoàn tất. Trạm tô cam là chỗ đang dồn nhiều nhất
- **Nguồn lực hôm nay**: xe rảnh / đang chạy / nằm xưởng, tài xế rảnh, và **hai dòng
  cảnh báo giấy tờ** — xe sắp hết đăng kiểm và tài xế sắp hết bằng

> Hai dòng cảnh báo giấy tờ đếm đúng những thứ sẽ **chặn điều phối**, kể cả trường hợp
> chưa khai ngày. Biết lúc xếp xe là quá muộn.

### 13.2. Bảng điều khiển

Số liệu tổng và sơ đồ luồng A–Z của tám nhóm chức năng.

### 13.3. Phân tích doanh thu và chi phí

**Vào:** Báo cáo và khác → Phân tích doanh thu và chi phí. Giá thành, cước báo giá và
lợi nhuận theo tuyến, theo xe và theo khách.

---

## 14. Các lời từ chối thường gặp

Hệ thống chặn ở đúng chỗ có rủi ro. Bảng này giải nghĩa các lời từ chối hay gặp nhất.

| Hệ thống nói | Nghĩa là | Sửa ở đâu |
|---|---|---|
| Xe không đúng loại của báo giá | Xe chọn khác loại xe đã chốt giá với khách | Chọn xe đúng loại, hoặc sửa báo giá |
| Xe thiếu hoặc hết hạn giấy tờ | Đăng kiểm / bảo hiểm / bảo dưỡng hết hạn **hoặc chưa khai** | Dữ liệu gốc → Phương tiện |
| Bằng lái không phù hợp hoặc đã hết hạn | Thiếu bằng, hết hạn, hoặc hạng bằng lệch hồ sơ | Dữ liệu gốc → Tài xế & bằng lái |
| Chưa có lịch làm việc bao phủ | Tài xế không có ca trong khung giờ chuyến | Dữ liệu gốc → Sắp lịch xe và tài xế |
| Nhân sự được chọn không có vai trò tài xế chính | Người đó khai là phụ xe | Đổi người, hoặc sửa vai trò |
| Xe/tài xế đang bận | Đang giữ một chuyến chưa đóng | Hoàn tất, xác nhận xe về bãi, hoặc huỷ chuyến đó |
| Vượt quá tải trọng / thể tích | Hàng khai vượt sức chở | Chọn xe lớn hơn, hoặc tách lô |
| Thời gian điều phối ngoài khung | Giờ phân công nằm ngoài khung lấy/giao của lệnh | Sửa khung giờ trên lệnh trước |
| Phải nộp POD cho tất cả chặng giao | Chuyến nhiều điểm còn điểm chưa ký | Ký nốt các điểm còn lại |
| Chỉ quyết toán sau khi chuyến hoàn thành | Chuyến khứ hồi chưa xác nhận xe về bãi | Xác nhận xe về bãi trước |
| Báo giá dưới giá thành | Cước thấp hơn giá thành | Sửa giá hoặc biên |
| Chưa cấu hình giá thành cho loại xe | Loại xe này chưa có công thức | Dữ liệu gốc → Công thức giá thành |

**Quy tắc chung khi bị chặn:** đọc câu thông báo, làm đúng việc nó chỉ, rồi bấm lại.
Hệ thống luôn nói tên bản ghi cụ thể và màn cần sang.

---

## 15. Từ điển thuật ngữ

| Từ | Nghĩa |
|---|---|
| **Cơ hội** | Yêu cầu của khách, ghi nhận trước khi có báo giá |
| **Báo giá (QT)** | Thoả thuận giá với khách theo tuyến và loại xe |
| **Lệnh giao hàng (DO)** | Một lần giao cụ thể, sinh từ báo giá được chấp nhận |
| **Chuyến (Trip)** | Một chuyến xe thật: xe, tài xế, giờ chạy |
| **Chặng (Leg)** | Một đoạn của chuyến, từ điểm này tới điểm kia |
| **POD** | Bằng chứng giao hàng: ảnh biên bản và chữ ký người nhận |
| **Mốc hành trình** | Sáu bước: vào bãi, lấy hàng, xuất bến, đến điểm giao, dỡ hàng, giao xong |
| **Giá thành** | Chi phí của công ty cho chuyến đó |
| **Cước** | Tiền thu của khách |
| **Biên lợi nhuận** | Phần chênh giữa cước và giá thành, tính theo phần trăm |
| **Acc code** | Mã phân loại chi phí, do bên công nợ cấp |
| **Hồ sơ bàn giao** | Gói dữ liệu đầy đủ của lệnh đã đóng, để bên công nợ lập phiếu |
| **Ghi sổ kinh doanh** | Đẩy lệnh đã giao sang hệ công nợ tạo đơn hàng bán |
| **Xe về rỗng** | Chặng xe quay về bãi, không chở hàng |
| **Tồn đọng** | Lệnh đã tới ngày lấy hàng mà chưa ai xếp xe |
