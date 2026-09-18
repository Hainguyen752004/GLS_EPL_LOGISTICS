# Phân tích luồng phiếu xuất xe (DO) và vai — tài liệu nội bộ

Tài liệu này là **ghi chép làm việc giữa anh và em**: phần anh nêu, phần em đối chiếu với bộ Excel và
quy trình chữ của bên Lào, chỗ nào chốt được thì chốt, chỗ nào phải hỏi thì đánh dấu để đưa sang tài
liệu gửi bên EPL (`CAU_HOI_NGHIEP_VU_EPL.md`, bản Lào `ຄຳຖາມວິຊາການ_EPL.md`, bản Anh `EPL_BUSINESS_QUESTIONS.md`).

Nguồn đối chiếu:

- `D:\Demo_Lao\LaoReports\Bao_cao_Van_tai_EPL_Tieng_Viet1.xlsx` — 5 sheet: Báo Cáo, BC Vận Tải, Hóa Đơn
  Vận Tải, Phiếu Xuất Xe, **Nhiệm Vụ** (bảng ai làm gì).
- `D:\Demo_Lao\EPL_System\luonghoatdongEPL\EPL_Quy_trinh_Logistics_VN.docx` — 9 bước quy trình chữ.
- Web đang chạy: `backend/app/services/phan_quyen.py` (chuỗi duyệt), `DOCS/CHUNG_TU_VA_DIEM_NOI.md`
  (chứng từ từng bước), màn Quy trình trong ứng dụng.

---

## 0. Kết luận trước, chi tiết sau

1. **Câu hỏi lớn nhất chưa có lời đáp: một phiếu xuất xe là MỘT chặng xe chạy hay CẢ vòng?**
   Excel của họ cho hai bằng chứng trái nhau trong cùng một số phiếu `T4-0428-08/EPL`:
   - sheet *Phiếu Xuất Xe*: Điểm đi **Kasi** (mỏ) → Điểm đến **Kalo**;
   - sheet *BC Vận Tải*: Điểm đi **Bãi EPL** → Điểm đến **Cảng Kalo**, và **chỉ có Trọng lượng đến
     = 42,06 t**, Trọng lượng đi để trống.

   Nghĩa là trên giấy họ đang dùng một số phiếu cho một vòng có (ít nhất) hai đoạn: mỏ → bãi (gom
   hàng), bãi → cảng (giao hàng). Anh nghi đúng. Phải hỏi, không đoán. Em đề nghị **hai phương án**
   để họ chọn (mục 2.1), mỗi phương án web đều làm được.

2. **Cân cuối là cân ở nơi giao (cảng), và hoá đơn tính trên cân cuối.** Sheet *Hóa Đơn Vận Tải*:
   Trọng lượng đến 41,3 t × 41 USD = 1.693,3 USD. Web đang làm đúng chỗ này (`tan_tinh = weight_dest`).
   Cân đầu họ để trống trong Excel — nên phải hỏi cân đầu lấy ở đâu (cân mỏ trên phiếu quặng, hay
   cân ở bãi).

3. **Đơn giá phải có TRƯỚC khi chạy** (vì thuê xe ngoài phải biết giá để trừ). Excel ghi đơn giá theo
   "hợp đồng" (bước 7 quy trình chữ: *theo đơn giá quy định trong hợp đồng*). Em đề nghị **bảng giá
   theo khách + tuyến** trong Danh mục, phiếu tự điền, kế toán Viêng Chăn xác nhận. Không làm module
   báo giá riêng — họ đang ở "năm 2016", báo giá là thứ họ không có trong Excel.

4. **Bảng "Nhiệm Vụ" trong Excel là bản phân vai chính thức của họ.** Web đang khớp 80 %, lệch ở
   một chỗ còn hở: quy trình chữ có *Kho phụ tùng Thabok* và *Tổ sửa chữa Thabok*, web chưa có vai.
   **Anh chốt (18/09): vai của họ là chuẩn, web phải theo đúng bảng đó.** Em đã tách *KT Thu/Chi VC*
   (`acct`, kiểm I–II) khỏi *KT Chi phí VC* (`expacct`, kiểm + ghi sổ IV–VI, nhà cung cấp, tất toán)
   và đổi nhãn mọi vai về đúng chữ của họ.

5. **Hướng giao diện anh nêu là đúng và nên làm ngay sau khi hỏi xong:** thanh tiến trình trên đầu,
   **mỗi vai vào chỉ thấy tab của mình**, ô không thuộc thẩm quyền thì ẩn hoặc chỉ đọc, **tab cuối là
   "Toàn phiếu" chỉ để xem**. Phiếu dạng cuộn dài hiện tại giữ làm bản in và bản xem tổng.

---

## 1. Vai — tên họ dùng, tên web dùng

| Tên trong Excel "Nhiệm Vụ" của họ | Tên trong quy trình chữ | Vai trên web | Việc |
|---|---|---|---|
| Bãi cảng cạn | Văn phòng hiện trường (Thabok) | `yard` — **Admin Thà Bốc** | Nhập cả sáu mục I–VI, lập phiếu, bấm xe đi / xe tới |
| KT Thu/Chi Viêng Chăn | — | `acct` — KT Thu/Chi Viêng Chăn | Xác nhận mục I, II; khoá phiếu khi xe về |
| KT Chi phí VC | Kế toán chi phí – công nợ phải trả | `expacct` — KT Chi phí VC | Xác nhận + ghi sổ IV, V, VI; nhà cung cấp; tất toán tài xế |
| KT kho xăng dầu VC | Kho nhiên liệu | `fuel` — Kế toán kho nhiên liệu | Xác nhận + ghi sổ III |
| Thủ quỹ VC | — | `treasury` — Quỹ Viêng Chăn | Chi tiền mục III |
| Quỹ tiền mặt cảng cạn | — | `cash` — Tiền mặt lẻ Thà Bốc | Chi tiền mục IV, V, VI |
| KT Doanh thu VC | Kế toán doanh thu và công nợ phải thu | `rev` — Kế toán doanh thu | Lập hoá đơn, ghi thu |
| — | Kho phụ tùng Thabok | *chưa có* | Cấp phụ tùng cho thợ, ghi 614/37 |
| — | Tổ sửa chữa Thabok | *chưa có* | Kiểm sửa được không, không thì chuyển gara ngoài |
| — | — | `depot` — Thủ kho tại điểm đổ | Cấp dầu theo phiếu lĩnh QR (web thêm) |
| — | — | `driver` — Tài xế | Xem phiếu của mình, xuất phát, báo hỏng, khai đổ dầu, chia sẻ GPS (web thêm) |
| — | — | `admin` — Sếp | Xem và sửa tất cả |

**Đã chốt, không hỏi nữa:** *KT Thu/Chi VC* và *KT Chi phí VC* là hai vai riêng đúng như bảng của họ
(anh chốt "phải theo role của họ"). **Việc phải hỏi (V1):** *Kho phụ tùng Thabok* và *Tổ sửa chữa
Thabok* có phải người riêng không, hay cũng là Bãi cảng cạn?

---

## 2. Đi từng bước theo đúng cách anh đặt câu hỏi

Mỗi bước em trả lời năm câu cố định: **Cần thông tin gì · Ai nhập · Ai kiểm · Trạng thái và khoá ·
Sinh chứng từ gì · Sang bước sau còn sửa được gì**. Chỗ ghi **HỎI** là chưa chốt được.

### 2.1 Bước 0 — Phiếu này là chuyến nào? (câu hỏi gốc, quyết định mọi bước sau)

Anh mô tả luồng thật: **bãi xe → mỏ lấy hàng → mang về kho/bãi → rồi mới mang đi giao**. Excel của họ
xác nhận có hai điểm đi khác nhau cho cùng một số phiếu (Kasi và Bãi EPL).

Ba cách hiểu, web đều làm được, nhưng phải chọn một:

| Phương án | Nghĩa | Được | Mất |
|---|---|---|---|
| **A. Một phiếu = một vòng xe** (mỏ → bãi → cảng) | Một số phiếu cho cả vòng, tuyến có 3–4 chặng, cân đầu ở mỏ, cân cuối ở cảng | Ít giấy nhất, giống Excel họ đang làm | Xe về bãi mà chưa đi cảng (hàng nằm kho vài ngày, đổi xe khác chở đi) thì phiếu treo; không tách được chi phí đoạn gom và đoạn giao |
| **B. Hai phiếu: DO gom hàng (mỏ → bãi) và DO giao hàng (bãi → cảng)**, nối nhau bằng số phiếu quặng | Mỗi lần xe lăn bánh là một phiếu; phiếu giao hàng mới có đơn giá và hoá đơn; phiếu gom hàng chỉ có chi phí | Đúng với việc hàng nằm kho và đổi xe; chi phí rõ từng đoạn; xe ngoài thuê đoạn nào tính đoạn đó | Gấp đôi số phiếu; phải nối hai phiếu để tính lãi cả vòng |
| **C. Một phiếu, hai chặng có cân riêng** | Như A nhưng mỗi chặng có ô cân riêng, trạng thái riêng ("đã về bãi", "đã giao") | Giữ một số phiếu như Excel mà vẫn biết xe đang ở đoạn nào | Phiếu dài hơn; vẫn không xử lý được đổi xe giữa vòng |

**Đề nghị của em: hỏi họ bằng hai câu cụ thể (mục 2.1 tài liệu gửi anh Khampla): (1) hàng về bãi có
nằm kho rồi đổi xe không; (2) hoá đơn tính theo chuyến giao hàng hay theo vòng.** Nếu có đổi xe → B.
Nếu xe nào lấy thì xe đó giao luôn → A (web hiện tại đã là A).

Web hiện tại: **A**. Tuyến có nhiều chặng (`route_stops`), một phiếu một tuyến, chấm mốc từng chặng.

### 2.2 Bước 1 — Mục I: Thông tin xe

- **Cần gì:** loại xe (nhà / liên kết), số xe, hãng xe, biển đầu kéo, biển rơ-moóc, tài xế, ngày lập
  phiếu, ngày xe đi, ngày xe về, km lúc đi, km lúc về, km chạy.
- **Ai nhập:** Admin Thà Bốc (Excel: *Bãi cảng cạn* — Người phụ trách). Web đúng.
- **Km về:** anh nói đúng, phải có **hai ô**: *km về ước tính* (tự tính = km đi + km tuyến, đã có) và
  *km về thật* (Bãi nhập khi xe về, đã có ở nút "Xe đã tới"). Km chạy = km về thật − km đi. Kế toán
  đối hai số này ở bước khoá phiếu (đã có cảnh báo lệch >10 %).
- **Ai kiểm:** Excel: *KT Thu/Chi VC* — Người xác nhận. Web: `acct` kiểm mục I.
- **Trạng thái mục I:** chờ → đã nhập → đã kiểm. Web đúng.
- **Khoá:** anh hỏi "xong cái này còn sửa được không, ai ngoài admin". Web hiện tại: Bãi sửa được khi
  mục còn *chờ / đã nhập*; kế toán **kiểm** là khoá; muốn sửa kế toán phải **trả lại**; Sếp mở khoá
  được. Em cho là đúng ý anh — **không cần hỏi**, chỉ cần nói cho họ biết.
- **Chứng từ:** `DO` — phiếu xuất xe (một tờ trong Sổ chứng từ khi lập).
- **Sang bước 2 còn sửa gì:** ngày xe về, km về thật — hai ô này phát sinh sau khi xe về nên phải
  còn nhập được dù mục I đã kiểm. Web hiện tại cho nhập qua nút "Xe đã tới" ở màn Theo dõi, không
  qua ô của mục I. **Chốt:** đúng như vậy, không mở lại mục I.

**HỎI (V2):** ngày xe về và km về do Bãi nhập lúc xe về, hay tài xế tự báo qua điện thoại? (ảnh
hưởng việc mở ô đó cho tài xế trên app.)

### 2.3 Bước 2 — Mục II: Thông tin vận chuyển

- **Cần gì:** tuyến (chọn từ Danh mục), khách hàng, loại hàng, số phiếu quặng, ngày phiếu quặng, điểm
  đi / điểm đến (kéo từ tuyến), cân đầu, cân cuối, hao hụt, đơn giá, thành tiền, quy đổi; xe liên kết
  thêm: giá thuê, phí 2 %, ngưỡng tấn, phạt quá tải.
- **Số phiếu quặng** là của khách giao, anh hỏi ai nhập: người cầm tờ giấy là **Bãi** (lúc bốc), nên
  Bãi nhập số và đính kèm ảnh (web đã có ô đính kèm). Kế toán chỉ kiểm. **Chốt được, không cần hỏi.**
- **Cân đầu — ai nhập, ở đâu:** Excel để trống cân đầu trong cả hai sheet. Hai khả năng: cân ở mỏ (ghi
  trên phiếu quặng của khách) hay cân ở bãi EPL. Nếu là cân mỏ → Bãi chép từ phiếu quặng. Nếu bãi có
  cân riêng → Bãi cân lúc xe về bãi. **HỎI (V3).** Web hiện tại: Bãi nhập.
- **Cân cuối — ở đâu:** *Hóa Đơn Vận Tải* của họ ghi "Trọng lượng đến 41,3 t" và **thành tiền tính
  trên số đó**. Vậy cân cuối là **cân ở nơi giao (cảng)**, không phải kéo về kho cân lại. Ai cập nhật:
  Bãi khi xe báo tới (web hiện tại). **HỎI (V4)** để xác nhận: phiếu cân ở cảng do ai cầm về, tài xế
  hay gửi ảnh?
- **Hao hụt và giá thành:** hao hụt = (cân đầu − cân cuối) ÷ cân đầu; web gắn cờ >1,5 %. Giá thành
  chuyến = tổng chi I–VI quy LAK; lãi = thành tiền × tỷ giá − chi. Web đã tính (ảnh 4 của anh).
  **HỎI (V5):** hao hụt có bị khách phạt hay trừ tiền không, hay chỉ để theo dõi?
- **Báo giá trước:** anh nói đúng — phải có giá trước mới thuê xe ngoài được. Quy trình chữ bước 7:
  *theo đơn giá quy định trong hợp đồng*. Vậy giá không phải báo từng chuyến mà **có sẵn theo hợp
  đồng**. **Đề nghị:** bảng giá theo *khách × tuyến × loại hàng* trong Danh mục; mở phiếu là tự điền;
  kế toán Viêng Chăn kiểm. **HỎI (V6):** hợp đồng ghi giá theo tấn ở điểm đến đúng không, có đổi theo
  mùa hay theo lô không?
- **Xe liên kết (ảnh 2, 3):** anh mô tả đúng cách họ nói: khách thuê EPL giá 2, EPL thuê lại xe ngoài
  giá 1, EPL giữ phí 2 %/phiếu và 1 USD/tấn vượt 40 t, trừ luôn các khoản EPL ứng cho chuyến. Web đã
  tính đúng công thức này và ghi `1211/402 Phí vận tải ngoài` là có trong Excel của họ (dòng "Thành
  tiền THB"). **HỎI (V7):** ai nhập giá thuê xe ngoài — Bãi (người gọi xe) hay kế toán Viêng Chăn
  (người ký với chủ xe)? Phí 2 % và 1 USD/tấn là cố định cho mọi chủ xe hay từng người khác nhau?
- **Ai kiểm:** KT Thu/Chi VC. **Khoá:** như mục I. **Trạng thái:** chờ → đã nhập → đã kiểm.
- **Chứng từ:** chưa sinh ở bước này; hoá đơn `HD` và thu `PT` sinh ở bước 7 sau khi khoá phiếu.
- **Sang bước 3 còn sửa gì:** cân cuối (xe chưa về), khấu trừ xe liên kết (phát sinh sau). Web cho
  nhập cân cuối qua "Xe đã tới"; khấu trừ thì kế toán sửa (mục II thuộc quyền kiểm của kế toán).

### 2.4 Bước 3 — Mục III: Chi phí nhiên liệu

- **Cần gì:** khoản mục (dầu), số lít, nơi đổ, đơn giá, tiền tệ, thành tiền, mã tài khoản.
- **Ai nhập gì:** anh chốt đúng — Bãi chỉ nhập **số lít + nơi đổ**; đơn giá, tiền tệ, mã TK Bãi
  **không thấy** (web đã ẩn bằng lớp `px-an-tien`). Excel *Nhiệm Vụ*: người xác nhận **và** ghi sổ là
  *KT kho xăng dầu VC*, người thanh toán là *Thủ quỹ VC*.
- **Vòng quay về mà anh nói:** đúng, có một vòng. Đổ ở **kho EPL** → Bãi in phiếu lĩnh QR → thủ kho
  cấp thật (số lít thật, giá kho) → dòng III tự cập nhật. Đổ **dọc đường bên Việt Nam** → tài xế khai
  (lít, trạm, đơn giá VND) → kế toán kho duyệt → thành dòng III nguồn *mua*. Hai đường đó web đã có.
- **Ai thấy đơn giá và tiền tệ:** kế toán kho nhiên liệu, thủ kho, kế toán Viêng Chăn, quỹ, Sếp. Bãi
  và tài xế không. **HỎI (V8):** tài xế đổ dầu bên Việt Nam có được thấy đơn giá không (anh ấy trả tiền
  mặt tại trạm nên đương nhiên biết) — nếu có thì tài xế nhập đơn giá luôn, kế toán chỉ kiểm.
- **Khoá:** kế toán kho *ghi sổ* là khoá; quỹ *chi* là xong. **Trạng thái:** chờ → đã nhập → đã kiểm →
  đã ghi sổ → đã chi.
- **Chứng từ:** `PLNL` phiếu lĩnh (lập), `PXK_NL` xuất kho nhiên liệu (thủ kho cấp hoặc kế toán ghi
  sổ), định khoản 625/371 xe nhà, 4022/371 xe liên kết. **HỎI (V9):** mã kho là **37** (quy trình chữ),
  **371** (Excel Phiếu Xuất Xe) hay **137** (danh mục anh Khang)?
- **Sang bước 4 còn sửa gì:** không. Dầu bổ sung sau khi ghi sổ thì thêm dòng mới, không sửa dòng cũ.

### 2.5 Bước 4 — Mục IV: Chi phí đi đường

Anh chưa hỏi chi tiết bước này nhưng Excel của họ có ghi chú rất đáng giá về **lúc nào trả tiền**
(cột ໝາຍເຫດ trong sheet Phiếu Xuất Xe):

| Khoản | Ghi chú của họ | Nghĩa | Web hiện tại |
|---|---|---|---|
| Tiền đổ nước, tiền chuyến chở quặng | ຈ່າຍຕາມຖ່ຽວພ້ອມເງິນເດືອນ | Trả theo chuyến **cùng kỳ lương** | Tất toán tài xế theo tháng — khớp |
| Chi tiêu đi VN, tiền điện thoại | ຈ່າຍເລີຍຕາມໂຊເຟີອອກລົດ | Trả **ngay khi tài xế xuất xe** | Phiếu tạm ứng QR — khớp |
| Shipping Lào, shipping Việt | ຕິດໜີ້ຜູ້ສະໜອງ / ຊໍາລະເປັນງວດ | **Nợ nhà cung cấp, trả theo đợt** | Nhà cung cấp trả theo đợt, loại khỏi tất toán tài xế — khớp |
| Cao tốc | ຈ່າຍຜ່ານບັດ, ອັບບັດເທື່ອລະ 15 ລ້ານ | Trả **qua thẻ**, nạp thẻ mỗi lần 15 triệu kíp | **Chưa có** khái niệm thẻ cao tốc |

- **Ai nhập:** Bãi. **Ai kiểm + ghi sổ:** *KT Chi phí VC*. **Ai chi:** *Quỹ tiền mặt cảng cạn*.
- **Chứng từ:** `PTU` phiếu tạm ứng QR (lập), `PC_TU` phiếu chi tạm ứng (quỹ chi), `TT_CHI/TT_THU`
  tất toán cuối tháng.
- **HỎI (V10):** thẻ cao tốc — ai giữ thẻ, nạp bằng tiền quỹ nào, có cần theo dõi số dư thẻ không?
  Nếu có thì đó là một "kho" nữa (kho tiền trong thẻ) cần phiếu nạp / phiếu trừ.

### 2.6 Bước 5 — Mục V: Sửa chữa

- **Tài xế báo về → ai nhập:** web hiện tại tài xế **tự khai** trên app (hỏng gì, bao nhiêu tiền), Bãi
  **duyệt** (chọn nguồn kho / mua, phụ tùng, số tiền), kế toán kiểm và ghi sổ, tiền mặt lẻ Thà Bốc
  chi. Excel: người phụ trách *Bãi cảng cạn*, xác nhận + ghi sổ *KT Chi phí VC*, thanh toán *Quỹ tiền
  mặt cảng cạn* — khớp.
- Quy trình chữ tách ba trường hợp: **sửa tại bãi lấy kho** (Kho phụ tùng Thabok, 614/37), **sửa
  gara ngoài** (Tổ sửa chữa Thabok kiểm rồi chuyển gara, 614/4021), **sửa dọc đường**. Web gộp thành
  nguồn *kho* / *mua*. **HỎI (V11):** Tổ sửa chữa Thabok có cần một vai riêng để "nhận báo hỏng → quyết
  sửa trong hay ngoài" không, hay Bãi làm luôn?
- **Chứng từ:** `PXK_PT` xuất kho phụ tùng (lấy kho), `PC_SC` phiếu chi sửa chữa (quỹ chi).

### 2.7 Ảnh 3 — Tổng kết thanh toán xe thuê ngoài · Ảnh 4 — Thu − Chi trong chuyến

- **Khi nào cập nhật:** hai khối này là **phép tính**, đổi ngay khi bất kỳ ô nào đổi. Không có bước
  nhập riêng.
- **Ai xem:** kế toán Viêng Chăn, kế toán doanh thu, quỹ, Sếp. **Bãi không thấy** (đã ẩn). Tài xế
  không thấy. **Chốt, không cần hỏi.**
- **Chứng từ:** khối xe thuê ngoài sinh `PC_CX` khi quỹ bấm *Trả chủ xe* (phiếu phải đã khoá, mỗi
  phiếu một lần). Khối Thu − Chi không sinh chứng từ (là báo cáo).
- **HỎI (V12):** chủ xe liên kết được trả **theo từng phiếu** hay **gom cuối tháng**? Nếu gom tháng thì
  `PC_CX` phải là một tờ cho nhiều phiếu (giống tất toán tài xế), web hiện tại là từng phiếu.

### 2.8 Khoá toàn phiếu (bước 14) và hoá đơn (bước 7)

Đã làm: xe về → kế toán bấm **Khoá phiếu** (máy rà km, hao hụt, phiếu quặng, mục chưa kiểm) → khoá
rồi mới xuất hoá đơn `HD` và thu `PT` → khoá rồi mới trả chủ xe. **Chốt, chỉ cần nói cho họ biết.**

---

## 3. Điều web đang làm KHÁC ý anh hoặc khác Excel của họ — cần quyết

| # | Điều | Web hiện tại | Đề nghị |
|---|---|---|---|
| K1 | Phiếu = một vòng hay một chặng | Một phiếu một tuyến nhiều chặng (phương án A) | Hỏi V1 trước; nếu B thì thêm loại phiếu *gom hàng* không có mục II tiền |
| K2 | Vai kế toán | ~~Một vai `acct` gộp~~ → **đã tách** `acct` (KT Thu/Chi, I–II) và `expacct` (KT Chi phí, IV–VI) | Xong 18/09 theo lời anh |
| K3 | Giá cước | **ĐÃ LÀM (18/09)**: bảng giá khách × tuyến (× loại hàng, có ngày hiệu lực) trong Danh mục khách hàng; Bãi lập phiếu không gửi giá, máy tự điền đơn giá và giá thuê xe ngoài; KT Thu/Chi VC (người kiểm mục II) sửa được ô tiền trên phiếu khi chuyến khác hợp đồng | Bãi không thấy bảng giá; C3.5 chỉ còn hỏi giá lấy từ đâu để nhập vào bảng |
| K4 | Thẻ cao tốc | Chi như tiền mặt | Nếu V10 xác nhận: thêm "ví thẻ cao tốc", phiếu nạp thẻ, mỗi phiếu trừ thẻ |
| K5 | Vai sửa chữa | Bãi duyệt báo hỏng | Nếu V11 xác nhận: thêm vai *Tổ sửa chữa* nhận báo hỏng và chọn trong / ngoài |
| K6 | Trả chủ xe liên kết | Từng phiếu | Nếu V12 là theo tháng: bảng tất toán chủ xe giống tất toán tài xế |
| K7 | Giao diện phiếu | **ĐÃ LÀM (18/09)**: thanh tiến trình + tab theo mục I–VI, vai nào vào tự mở tab có việc của vai đó (Bãi → mục đầu chờ nhập, KT Thu/Chi → I/II, KT kho xăng dầu và Thủ quỹ → III, KT Chi phí và Quỹ tiền mặt → IV–VI, Doanh thu/Sếp → Toàn phiếu); tab khác vẫn bấm xem được nhưng chỉ có nút ở mục mình phụ trách; tab cuối *Toàn phiếu* chỉ xem và in; chấm đỏ trên tab = còn việc | Đường dẫn `#/phieu-xuat-xe?id=…&tab=fuel` mở thẳng tab |

---

## 4. Màn phiếu xuất xe dạng tab (K7) — đã dựng 18/09, đây là bố cục đã theo

Anh nói: *"nếu chuẩn là phải làm dạng thanh process và dạng tab, mỗi role vào chỉ thấy tab của mình,
thông tin không thuộc thẩm quyền phải ẩn hoặc chỉ đọc; phiếu dài chỉ để xem tổng thể ở tab cuối."*
Em đồng ý hoàn toàn, và nó khớp với ghi nhớ đã có của dự án: *phiếu dài thì chia tab theo cụm việc*.

Bố cục đề nghị:

```
┌ Thanh tiến trình (đã có): Nhập liệu → Kiểm tra → Ghi sổ → Chi tiền → Hoá đơn ┐
├ Tab: [I Xe] [II Vận chuyển] [III Nhiên liệu] [IV Đi đường] [V Sửa chữa] [VI Khác] [Toàn phiếu] ┤
│                                                                                              │
│  Vai vào màn → tự mở tab của vai đó, tab khác vẫn bấm được nhưng CHỈ ĐỌC.                     │
│  Trong tab: ô nào vai không có quyền → ẩn hẳn (tiền với Bãi) hoặc mờ chỉ đọc (cân với kế toán). │
│  Nút hành động của tab (Gửi kiểm / Kiểm / Trả lại / Ghi sổ / Chi) nằm ở chân tab.              │
│  Tab "Toàn phiếu" = bản in hiện tại, không có ô nhập, có nút In và Khoá phiếu.                  │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

Vai → tab mở mặc định: Bãi → I (phiếu mới) hoặc tab đang *chờ* đầu tiên; KT Thu/Chi → II; KT kho
nhiên liệu → III; KT Chi phí → IV (rồi V, VI); Quỹ → tab đang *đã ghi sổ* đầu tiên; KT Doanh thu và
Sếp → Toàn phiếu.

Không đổi gì ở máy chủ: chuỗi trạng thái, quyền, chứng từ đã có. Đây là việc **thuần giao diện**.

---

## 5. Danh sách câu hỏi đã gom (chuyển sang tài liệu gửi anh Khampla)

V1 vai kế toán và vai Thabok · V2 ai nhập ngày về/km về · V3 cân đầu ở đâu · V4 phiếu cân cảng ai
cầm · V5 hao hụt có phạt không · V6 giá hợp đồng theo gì · V7 ai nhập giá thuê xe ngoài, phí cố định
hay không · V8 tài xế có thấy đơn giá dầu · V9 mã kho 37/371/137 · V10 thẻ cao tốc · V11 Tổ sửa chữa
· V12 trả chủ xe theo phiếu hay tháng — cộng câu hỏi gốc **một phiếu là một chặng hay cả vòng**.
