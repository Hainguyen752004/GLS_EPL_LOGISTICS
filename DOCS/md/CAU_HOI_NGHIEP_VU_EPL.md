# Phiếu xuất xe EPL — mô tả cách phần mềm đang chạy và các câu hỏi nghiệp vụ xin bên EPL xác nhận

Kính gửi anh Khampla, anh Ped và các anh chị phụ trách nghiệp vụ vận tải bên EPL,

Bên em đã dựng xong phần lớn phần mềm quản lý vận tải theo đúng bộ Excel *Báo cáo vận tải EPL* và
quy trình *Luân chuyển lệnh điều xe* mà bên EPL gửi. Trước khi đi tiếp, bên em xin trình bày **phần mềm
hiện đang chạy như thế nào** và **xin các anh chị xác nhận một số điểm nghiệp vụ** mà bên em chưa dám tự
quyết. Mỗi câu hỏi có sẵn các lựa chọn để đánh dấu; chỗ nào không đúng lựa chọn nào các anh chị cứ ghi
thêm.

---

## Phần A. Phần mềm hiện đang làm gì

### A1. Một phiếu xuất xe đi qua những bước nào

Phiếu xuất xe (bên EPL gọi là *Lệnh điều xe*, số dạng `T4-0428-08/EPL`) có sáu mục như trên giấy:
I Thông tin xe · II Thông tin vận chuyển · III Chi phí xăng dầu · IV Chi phí đi lại · V Chi phí sửa
chữa · VI Chi phí khác. Mỗi mục đi qua chuỗi:

**Kho Thabok NHẬP → Kế toán KIỂM TRA → Kế toán GHI SỔ → Quỹ CHI TIỀN**

Ai làm bước nào lấy đúng theo sheet *Nhiệm Vụ* trong Excel của bên EPL:

| Mục | Người nhập | Người xác nhận | Ghi sổ kế toán | Người thanh toán |
|---|---|---|---|---|
| I. Thông tin xe | Kho Thabok | KT Thu/Chi Viêng Chăn | — | — |
| II. Thông tin khách hàng, vận chuyển | Kho Thabok | KT Thu/Chi Viêng Chăn | — | — |
| III. Chi phí xăng dầu | Kho Thabok | KT kho xăng dầu VC | KT kho xăng dầu VC | Thủ quỹ VC |
| IV. Chi phí đi lại | Kho Thabok | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt cảng cạn |
| V. Chi phí sửa chữa | Kho Thabok | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt cảng cạn |
| VI. Chi phí khác | Kho Thabok | KT Chi phí VC | KT Chi phí VC | Quỹ tiền mặt cảng cạn |
| Hoá đơn thu phí vận tải | KT Doanh thu VC | — | KT Doanh thu VC | — |

Quy tắc khoá: người nhập chỉ sửa được khi mục còn *chờ* hoặc *đã nhập*. Kế toán đã **kiểm** là mục
đó khoá; muốn sửa kế toán phải **trả lại** cho Bãi. Chỉ tài khoản quản trị (Sếp) mở khoá được.

### A2. Những gì Kho Thabok không nhìn thấy

Kho Thabok **thấy mọi khoản CHI** vì chính họ chi và chính họ nhập: số lít và giá dầu mua dọc đường,
tiền cầu đường, tiền đi lại, tiền sửa xe, giá nhập kho dầu và phụ tùng, cân, ngày giờ.

Kho Thabok **không thấy tiền BÁN**: đơn giá cước khách trả, thành tiền của chuyến, hoá đơn và tiền thu
của khách, giá thuê xe liên kết cùng các khoản khấu trừ chủ xe, lãi từng chuyến, và mã tài khoản. Những
ô đó chỉ kế toán, quỹ và Sếp thấy.

Lý do bên em chia như vậy: phần chi là việc hằng ngày của kho, giấu đi thì họ không làm việc được; còn
**chênh lệch giữa giá khách trả và giá thuê xe ngoài là phần lãi của công ty**, không cần cho người ở
kho. Nếu bên anh muốn khác (kho được thấy cả giá cước, hoặc ngược lại không thấy cả tiền chi), xin anh
ghi rõ ở đây: ......................

### A3. Nhiên liệu — hai đường

1. **Đổ ở kho dầu của EPL:** Bãi khai số lít và nơi đổ → phần mềm in **phiếu lĩnh nhiên liệu có mã
   QR** cho tài xế cầm tới kho → thủ kho quét mã, cấp dầu, nhập số lít thật → tồn kho trừ ngay, sinh
   phiếu xuất kho, định khoản 625/371 (xe EPL) hoặc 4022/371 (xe thuê ngoài).
2. **Đổ dọc đường bên Việt Nam:** tài xế khai trên điện thoại (số lít, trạm, đơn giá VND) → kế toán
   kho xăng dầu duyệt → thành một dòng mua ngoài trong mục III, tự quy đổi về LAK theo tỷ giá ghi trên
   phiếu.

### A4. Tiền đi đường — trả đúng lúc như ghi chú trong Excel của bên EPL

| Khoản | Ghi chú trong Excel | Phần mềm làm |
|---|---|---|
| Chi tiêu đi VN, điện thoại | Trả ngay khi tài xế xuất xe | **Phiếu tạm ứng có mã QR**, quỹ quét mã chi tiền; chưa nhận tiền thì tài xế chưa bấm được *Xuất phát* |
| Tiền đổ nước, tiền chuyến chở quặng | Trả theo chuyến cùng lương | **Tất toán tài xế theo tháng**: đã ứng bao nhiêu, chi thật bao nhiêu, dương công ty trả thêm, âm tài xế nộp lại |
| Shipping Lào, shipping Việt | Nợ nhà cung cấp, trả theo đợt | Màn **Theo dõi nhà cung cấp**, trả theo đợt, không tính vào tất toán tài xế |
| Cao tốc | Trả qua thẻ, nạp 15 triệu kíp mỗi lần | Hiện ghi như khoản chi thường — **xem câu hỏi C6.1** |

### A5. Xe về, khoá phiếu, hoá đơn, xe thuê ngoài

- Xe tới nơi → Bãi bấm *Xe đã tới*, nhập **cân cuối**, km về thật, ngày về.
- Kế toán bấm **Khoá phiếu**: phần mềm rà km về so với ước tính, hao hụt cân (cờ đỏ nếu quá 1,5 %),
  phiếu quặng đã đính kèm chưa, mục nào có chi mà chưa kiểm. Khoá rồi Bãi không sửa được nữa.
- **Chỉ phiếu đã khoá mới xuất hoá đơn** (định khoản 1211/70) và mới ghi thu tiền.
- **Xe thuê ngoài:** khách trả EPL theo đơn giá hợp đồng; EPL trả chủ xe = giá thuê × tấn − phí quản lý
  2 %/phiếu − 1 USD mỗi tấn vượt 40 tấn − các khoản EPL đã ứng cho chuyến; lãi = tiền khách trả − tiền
  thuê. Quỹ bấm *Trả chủ xe* sau khi phiếu khoá.

### A6. Sổ chứng từ cho kế toán

Mỗi bước sinh ra tiền hoặc hàng để lại **một tờ chứng từ có số** để kế toán kéo về: phiếu xuất kho
nhiên liệu, xuất kho phụ tùng, phiếu chi tạm ứng, phiếu chi sửa chữa, hoá đơn, phiếu thu, tất toán tài
xế, chi trả chủ xe, nhập kho, trả nhà cung cấp, và ba tờ cho **bán phụ tùng / xăng dầu ra ngoài**
(xuất kho bán, hoá đơn bán, phiếu thu bán).

---

## Phần B. Câu hỏi quan trọng nhất — một phiếu xuất xe là chuyến nào?

Trong Excel của bên EPL, **cùng số phiếu `T4-0428-08/EPL`** nhưng:

- sheet *Phiếu Xuất Xe* ghi: Điểm đi **Kasi** → Điểm đến **Kalo**;
- sheet *BC Vận Tải* ghi: Điểm đi **Bãi EPL** → Điểm đến **Cảng Kalo**, và chỉ có **Trọng lượng đến
  42,06 t**, Trọng lượng đi để trống.

Bên em hiểu luồng thực tế là: **xe từ bãi đi mỏ lấy quặng → chở về bãi/kho → rồi từ bãi chở đi giao
ở cảng**. Xin các anh chị xác nhận:

**B1.** Một phiếu xuất xe bao gồm:
- [ ] cả vòng: bãi → mỏ → bãi → cảng (một số phiếu cho cả vòng)
- [ ] chỉ đoạn **mỏ → bãi** (gom hàng về kho)
- [ ] chỉ đoạn **bãi → cảng** (giao hàng cho khách)
- [ ] mỗi lần xe lăn bánh là một phiếu, tức là **hai phiếu**: một phiếu gom hàng, một phiếu giao hàng

**B2.** Quặng về bãi có **nằm kho** rồi mới đi giao không? Có khi nào **xe khác** chở đi giao không?
- [ ] Không, xe nào lấy thì xe đó chở đi giao luôn
- [ ] Có, hàng nằm kho vài ngày, xe khác chở đi giao
- [ ] Cả hai tuỳ lô

**B3.** Hoá đơn thu khách tính theo:
- [ ] từng **chuyến giao ở cảng** (cân tại cảng × đơn giá)
- [ ] từng **vòng** mỏ → cảng
- [ ] gom **theo tháng** cho từng khách

**B4.** Nếu là hai phiếu, phiếu **gom hàng** (mỏ → bãi) có đơn giá cước không, hay chỉ có chi phí?
- [ ] Không có cước, chỉ ghi chi phí
- [ ] Có cước riêng (khách trả cho đoạn gom)

---

## Phần C. Câu hỏi theo từng mục

### C1. Vai người dùng

- **C1.1** Phần mềm đã làm đúng bảng *Nhiệm Vụ*: *KT Thu/Chi Viêng Chăn* là một tài khoản (xác nhận mục
  I, II), *KT Chi phí VC* là một tài khoản khác (xác nhận và ghi sổ mục IV–VI). Xin xác nhận giúp tên
  người giữ từng tài khoản: KT Thu/Chi VC: .................. · KT Chi phí VC: ..................
- **C1.2** Quy trình chữ có *Kho phụ tùng Thabok* và *Tổ sửa chữa Thabok*. Đó là:
  - [ ] Người riêng, cần tài khoản riêng — [ ] Cũng là người của Kho Thabok
- **C1.3** Tài xế có dùng điện thoại được không (để nhận phiếu, khai đổ dầu, báo hỏng, chia sẻ vị trí)?
  - [ ] Có, tất cả tài xế — [ ] Chỉ một số — [ ] Không, Bãi nhập thay

### C2. Mục I — Thông tin xe

- **C2.1** Ngày xe về và km về thật do ai ghi?
  - [ ] Bãi ghi khi xe về tới — [ ] Tài xế tự báo qua điện thoại — [ ] Kế toán ghi theo giấy
- **C2.2** Sau khi kế toán đã kiểm mục I, Bãi có cần sửa gì nữa không (ngoài ngày về, km về)?
  - [ ] Không — [ ] Có, ví dụ: ..............................

### C3. Mục II — Thông tin vận chuyển, cân, giá

- **C3.1** **Cân đầu** lấy ở đâu?
  - [ ] Cân của mỏ, ghi trên phiếu quặng khách giao — [ ] Cân của bãi EPL khi xe về bãi — [ ] Không có cân đầu
- **C3.2** **Cân cuối** lấy ở đâu? (Hoá đơn trong Excel tính trên *Trọng lượng đến 41,3 t*.)
  - [ ] Cân của cảng / nơi giao — [ ] Cân của bãi EPL — [ ] Khác: ...........
- **C3.3** Phiếu cân ở cảng do ai mang về, dưới dạng gì?
  - [ ] Tài xế cầm giấy về bãi — [ ] Tài xế chụp ảnh gửi — [ ] Cảng gửi thẳng cho kế toán
- **C3.4** **Hao hụt** (cân đầu − cân cuối) có bị khách trừ tiền hay phạt không?
  - [ ] Không, chỉ theo dõi — [ ] Có, quá ....... % thì trừ theo .......
- **C3.5** **Đơn giá cước** lấy từ đâu?
  - [ ] Hợp đồng với khách, cố định theo tuyến (USD/tấn) — [ ] Thoả thuận từng chuyến — [ ] Theo bảng giá đổi theo mùa
- **C3.6** Đơn giá tính trên:
  - [ ] Tấn ở điểm đến — [ ] Tấn ở điểm đi — [ ] Theo chuyến (không theo tấn)
- **C3.7** Số phiếu quặng và ngày phiếu quặng do ai nhập?
  - [ ] Bãi, lúc bốc hàng (đính kèm ảnh) — [ ] Kế toán, khi nhận giấy — [ ] Khác

### C4. Xe thuê ngoài (xe liên kết)

- **C4.1** Giá thuê xe ngoài (USD/tấn) do ai nhập?
  - [ ] Bãi (người gọi xe) — [ ] Kế toán Viêng Chăn (người ký với chủ xe) — [ ] Sếp
- **C4.2** Phí quản lý **2 %/phiếu** và phạt quá tải **1 USD/tấn vượt 40 tấn** là:
  - [ ] Cố định cho mọi chủ xe — [ ] Khác nhau theo từng chủ xe / hợp đồng
- **C4.3** Chủ xe được trả tiền:
  - [ ] Theo từng phiếu, ngay sau khi phiếu khoá — [ ] Gom cuối tháng một lần — [ ] Theo đợt thoả thuận
- **C4.4** Các khoản EPL ứng cho chuyến xe thuê ngoài (dầu kho EPL, cao tốc, tiền đi đường) **trừ hết**
  vào tiền trả chủ xe, hay có khoản nào EPL chịu?
  - [ ] Trừ hết — [ ] EPL chịu khoản: ..............................

### C5. Mục III — Nhiên liệu

- **C5.1** Tài xế đổ dầu bên Việt Nam trả tiền mặt tại trạm, vậy tài xế **có được nhập đơn giá** không?
  - [ ] Có, tài xế nhập lít + đơn giá + trạm, kế toán kiểm — [ ] Không, tài xế chỉ nhập lít, kế toán nhập giá
- **C5.2** Kho dầu EPL có mấy điểm? (Phần mềm đang có *Kho Thà Bốc* và *Kho Viêng Chăn*.)
  - [ ] Đúng hai — [ ] Thêm: ..............................
- **C5.3** Giá dầu xuất kho tính theo:
  - [ ] Giá nhập lần gần nhất — [ ] Giá bình quân — [ ] Giá cố định do kế toán đặt
- **C5.4** Mã tài khoản **kho** là gì? Quy trình chữ ghi **37**, sheet Phiếu Xuất Xe ghi **371**, danh
  mục kế toán hiện có **137**.
  - [ ] 371 — [ ] 37 — [ ] 137 — [ ] Khác: ......
- **C5.5** Mã **nhà cung cấp**: quy trình ghi **4021**, sheet ghi **402**. Dùng mã nào?
  - [ ] 402 — [ ] 4021 — [ ] Cả hai, tách theo: ..............................
- **C5.6** Mã **tiền mặt / ngân hàng** để ghi vế Có của phiếu chi, phiếu thu là gì? ..............

### C6. Mục IV — Đi đường

- **C6.1** Thẻ cao tốc: ai giữ thẻ, nạp bằng tiền của quỹ nào, có cần phần mềm theo dõi **số dư thẻ**
  không?
  - [ ] Có, cần theo dõi số dư và mỗi phiếu trừ thẻ — [ ] Không, chỉ ghi khoản chi như hiện nay
- **C6.2** Tiền chuyến chở quặng (ເງີນຖ້ຽວແກ່ແຮ່) và tiền đổ nước tính **theo chuyến hay theo tấn**?
  - [ ] Cố định theo chuyến — [ ] Theo tấn — [ ] Theo tuyến

### C7. Mục V — Sửa chữa

- **C7.1** Xe hỏng dọc đường, tài xế báo về ai?
  - [ ] Kho Thabok — [ ] Tổ sửa chữa Thabok — [ ] Cả hai
- **C7.2** Ai quyết định sửa bằng phụ tùng kho hay đưa gara ngoài?
  - [ ] Bãi — [ ] Tổ sửa chữa Thabok — [ ] Kế toán duyệt trước
- **C7.3** Sửa xe **tại bãi** lúc xe không chạy (bảo dưỡng) ghi vào phiếu xuất xe nào?
  - [ ] Phiếu gần nhất — [ ] Không gắn phiếu, ghi riêng theo xe — [ ] Lệnh sửa chữa riêng

### C8. Mục VI — Chi khác, và hoá đơn

- **C8.1** Ví dụ những khoản hay rơi vào mục VI: ..............................
- **C8.2** Một khách một tháng nhận **một hoá đơn gom** hay **mỗi phiếu một hoá đơn**?
  - [ ] Mỗi phiếu một hoá đơn — [ ] Gom theo tháng — [ ] Gom theo lô hàng
- **C8.3** Khách trả tiền bằng:
  - [ ] Chuyển khoản — [ ] Tiền mặt — [ ] Cả hai; có trả một phần rồi trả tiếp không? [ ] Có [ ] Không

### C9. Màn hình

- **C9.1** Phần mềm dự định đổi màn phiếu xuất xe thành **tab theo mục**, mỗi vai vào chỉ thấy tab của
  mình, ô ngoài thẩm quyền ẩn hoặc chỉ đọc, tab cuối là *Toàn phiếu* để xem và in. Các anh chị thấy phù hợp
  không?
  - [ ] Phù hợp — [ ] Giữ phiếu dài như giấy — [ ] Ý khác: ..............................
- **C9.2** Ngôn ngữ mặc định khi mở máy ở bãi: [ ] Lào — [ ] Việt — [ ] Việt + Lào

---

Các anh chị trả lời tới đâu bên em làm tới đó; những phần chưa có trả lời bên em giữ như đang chạy. Cảm ơn
anh Khampla, anh Ped và các anh chị bên EPL.
