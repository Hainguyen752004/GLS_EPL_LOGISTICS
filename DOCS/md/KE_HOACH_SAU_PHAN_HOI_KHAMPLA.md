# Kế hoạch sửa theo phản hồi của anh Khampla — ba đợt

Viết cho anh chủ dự án và người làm tiếp. Lập 22/09/2026, ngay sau khi nhận tệp trả lời
`DOCS/word/traloituanhkhamplar.docx` (bản tiếng Lào có tích ✔, 32/36 câu). Mỗi mục ghi: **họ nói gì ·
mình đang làm gì · phải sửa gì · to nhỏ ra sao**. Ô ☐ để tích khi xong; làm xong mục nào thì ghi số
commit vào cột cuối.

Quy tắc chung của đợt sửa này: chỉ sửa đúng cái họ trả lời, không thêm gì họ không hỏi. Chỗ họ để
trống thì giữ như đang chạy và ghi rõ là đang chờ.

---

## Cái gì KHỚP, không phải đụng

| Câu | Họ trả lời | Mình đã làm |
|---|---|---|
| B1, B2 | Hai phiếu: chặng mỏ → bãi và chặng bãi → cảng; hàng nằm kho nhiều ngày, xe khác chở đi | Đúng mô hình hai DO + kho hàng ở bãi (commit `0d353da`) |
| C8.3 | Trả chuyển khoản lẫn tiền mặt, có trả một phần | Sổ thu tiền từng lần (`34bb5e4`) |
| C3.1, C3.2 | Cân đầu lấy ở mỏ (ghi trên phiếu quặng), cân cuối lấy ở cảng | Đúng |
| C3.3 | Tài xế mang giấy cân về **và** chụp ảnh gửi | Đã có đính kèm ảnh phiếu quặng |
| C4.1, C4.4 | Kế toán VC nhập giá thuê xe ngoài; trừ hết khoản EPL ứng | Đúng |
| C5.1 | Tài xế chỉ khai lít, kế toán nhập giá | Đúng |
| C6.2 | Tiền chuyến, tiền nước khoán theo chuyến | Đúng |
| C1.3 | Mọi tài xế dùng điện thoại | Màn Phiếu của tôi |
| C7.1, C7.2 | Xe hỏng báo cả Bãi lẫn tổ sửa; tổ sửa quyết lấy kho hay ra gara | Đúng luồng báo hỏng → duyệt |

---

## ĐỢT 1 — rõ ràng, không phải hỏi ai (khoảng nửa ngày)

| ☐ | Mục | Họ nói | Đang có | Sửa | Commit |
|---|---|---|---|---|---|
| ☑ | **1.1 Mã tài khoản** | Kho **137** mẹ / **1371** con · Nhà cung cấp **402** mẹ / **4021** con, tách theo NCC · Tiền mặt Kíp **1011** · tiền mặt ngoại tệ **1012** · ngân hàng Kíp **1021** · ngân hàng ngoại tệ **1022** (theo sá-la-ban kế toán doanh nghiệp Lào) | Kho `371`, NCC `402`, bốn mã tiền để trống | Ghi sổ theo **mã con** (1371, 4021) vì đó là cấp hạch toán; vế tiền chọn theo *cách thu/chi* (mặt/ngân hàng) × *tiền tệ* (Kíp/khác). Sửa một bảng `services/chung_tu.py`, `ma_tk_mac_dinh`, danh mục dự phòng `acc_code.py`, nhãn giao diện, tài liệu | 22/09 |
| ☑ | **1.2 Phiếu gom có cước** (B4) | Khách trả riêng cho chặng gom | Chặn hẳn: `PHIEU_GOM` khi xuất hoá đơn; giao diện ẩn mọi ô tiền trên phiếu gom | Bỏ chặn; phiếu gom có đơn giá, tiền tệ, thành tiền, hoá đơn như phiếu giao. Vẫn ẩn ô *lấy từ lô* (chỉ phiếu giao có). Dữ liệu mẫu G4-0101 thêm giá | 22/09 |
| ☑ | **1.3 Tài xế báo ngày về và km về** (C2.1) | Tài xế tự báo qua điện thoại | Bãi ghi khi bấm *Xe đã tới* | Thêm nút **Báo đã về** trên màn tài xế: ngày về + km về. Máy chủ ghi hai số đó và đánh mốc tới điểm cuối, **không** tự chuyển sang "đã tới": cân tại bãi/cảng vẫn là việc của Bãi, Bãi bấm *Xe đã tới* thì hai ô đã được điền sẵn số tài xế báo | 22/09 |
| ☑ | **1.4 Số phiếu quặng do kế toán nhập** (C3.7) | Kế toán nhập khi nhận giấy | Bãi nhập cùng lúc lập phiếu | Hai ô *số phiếu quặng · ngày* chuyển sang nhóm ô của **người kiểm mục II** (như ô tiền): Bãi thấy nhưng chỉ đọc, kế toán Thu/Chi VC gõ | 22/09 |
| ☑ | **1.5 Thêm 5 kho dầu** (C5.2) | Hlak 28 Viêng Chăn · sân Thà Bốc Huay Lek · bản Thavai · sân Thakhek · tuyến Hlak 28 Thakhek (đường 8) | Hai kho: Thà Bốc, Viêng Chăn | Thêm năm điểm đổ loại *kho EPL* vào dữ liệu mẫu; màn Điểm đổ đã cho thêm/sửa nên sau này họ tự quản | 22/09 |
| ☑ | **1.6 Máy bãi mặc định tiếng Lào** (C9.2) | Lào | Mặc định Việt | Lần đầu đăng nhập trên máy chưa chọn ngôn ngữ, vai Bãi · thủ kho · tài xế → tự đặt tiếng Lào; đã chọn rồi thì giữ | 22/09 |
| ☑ | **1.7 Tài liệu** | | | Ghi câu trả lời vào `CONG_VIEC_CHO_ANH_KHAMPLA_CHOT.md` (phần 2 rút xuống còn bốn câu trống), sửa `NGHIEP_VU_DB_API.md` (A0 phiếu gom, mã tài khoản, bảng lỗi), `HOP_DONG_API_ANH_KHANG.md` (mục 4 "còn thiếu mã" nay có mã), `HUONG_DAN_THU_TUNG_VAI.md` (bước 1, bước 2, bước 8) | 22/09 |

---

## ĐỢT 2 — đụng tiền, phải nghĩ kỹ (một đến hai ngày)

| ☐ | Mục | Họ nói | Đang có | Sửa | Commit |
|---|---|---|---|---|---|
| ☑ | **2.1 Cước khoán theo chuyến** (C3.6, C3.5) | Ngoài tấn × đơn giá còn có **giá trọn chuyến**, dùng cho xe ngoài không hợp đồng; giá hợp đồng có thể **đổi theo mùa/giá dầu** | Chỉ tấn × đơn giá; bảng giá đã có `valid_from` | Phiếu thêm ô *Cách tính cước*: theo tấn · trọn chuyến. Trọn chuyến thì thành tiền = đơn giá, không nhân tấn. Bảng giá khách × tuyến thêm cột cách tính. Lịch sử giá theo `valid_from` giữ nguyên, đủ cho "đổi theo mùa" | 22/09 |
| ☑ | **2.2 Hoá đơn gộp tháng** (C8.2, B3) | Khách **có hợp đồng**: một hoá đơn gộp cả tháng · khách vãng lai: mỗi phiếu một hoá đơn | Mỗi phiếu một hoá đơn, tờ `HD` gắn một phiếu | Hai bảng `invoices` + `invoice_payments`; khách có ô *Cách xuất hoá đơn* (`phieu`/`thang`). Màn **Hoá đơn gộp tháng**: bảng *Chờ gộp* theo khách × loại tiền → một tờ `HDT-YYYYMM-NN` nhiều dòng phiếu, một chứng từ `HD`. Thu tiền ghi ở tờ và **tự phân bổ xuống từng phiếu theo thứ tự ngày**, nên trạng thái từng phiếu vẫn đúng. Khách để *gộp tháng* thì nút hoá đơn lẻ trên phiếu bị chặn | 22/09 |
| ☑ | **2.3 Trả chủ xe gộp** (C4.3) | Ba kiểu: từng phiếu (xe ngoài không hợp đồng) · gộp cuối tháng · theo đợt thoả thuận | Chỉ trả từng phiếu ngay sau khoá | Chủ xe liên kết thành danh mục riêng (`owners`) có *cách trả* và *phí 2 % / mức quá tải riêng* (C4.2). Bảng `owner_payments` một lần trả nhiều phiếu; phiếu đánh *đã trả* khi nằm trong một lần trả | 22/09 |
| ☑ | **2.4 Phí 2 % và mức quá tải theo từng chủ xe** (C4.2) | Khác nhau theo chủ xe / hợp đồng | Ba ô trên từng phiếu, mặc định 2 % · 40 t · 1 | Lấy mặc định từ hồ sơ chủ xe (2.3), phiếu vẫn sửa được | 22/09 |

Thứ tự trong đợt: 2.1 trước (nhỏ, độc lập) → 2.3 và 2.4 cùng lúc (chung danh mục chủ xe) → 2.2 sau
cùng (to nhất, đụng sổ thu tiền vừa làm). **Đợt 2 xong ngày 22/09.**

---

## ĐỢT 3 — việc mới hoàn toàn (hai đến ba ngày)

| ☐ | Mục | Họ nói | Sửa | Commit |
|---|---|---|---|---|
| ☑ | **3.1 Hai vai mới** (C1.2) | Kho phụ tùng Thà Bốc và tổ sửa chữa Thà Bốc là **người riêng**, cần tài khoản riêng | Vai `parts` (thủ kho phụ tùng: nhập/xuất phụ tùng) và `repair` (tổ sửa: duyệt báo hỏng, quyết kho hay gara, ghi mục V). Rút hai việc đó khỏi Bãi. Sửa bảng Nhiệm Vụ trong màn Quy trình | 22/09 |
| ☐ | **3.2 Thẻ cao tốc** (C6.1) | Muốn theo dõi **số dư thẻ**, mỗi phiếu trừ từ thẻ. Hai kiểu: khách cấp thẻ và nạp tiền, cuối tháng **cấn trừ vào cước** · khách không cấp thì quỹ Thà Bốc đưa tiền mặt cho tài xế | Danh mục thẻ (số thẻ, của khách nào, tài xế nào cầm, số dư); nạp tiền vào thẻ = một dòng; dòng chi BOT trên phiếu chọn *trừ thẻ nào* thì số dư giảm; cuối tháng ra được số cấn trừ với khách | |
| ☐ | **3.3 Nợ trạm dầu Việt Nam, cấn trừ cước tháng** (C5.1 ghi chú) | Tài xế đổ dầu ở VN **ghi nợ tại trạm**, cuối tháng EPL cấn trừ với cước khách | Dòng dầu mua ở VN đánh *nợ trạm* thay vì *tài xế ứng tiền mặt*; nhà cung cấp trạm dầu có công nợ; báo cáo cuối tháng: nợ trạm × cước khách. Đây là công nợ hai chiều — chỉ ghi và hiện, hạch toán để anh Khang | |
| ☑ | **3.4 Đổi xe giữa đường** (C2.2) | Xe hỏng nặng, đổi xe khác chở tiếp, dù mục I đã kiểm | Nút *Đổi xe* trên phiếu đã kiểm mục I: ghi xe mới, giữ xe cũ trong lịch sử, mục I quay về *đã nhập* để kiểm lại. Đổi sang xe liên kết thì phiếu tự chuyển sang xe liên kết | 22/09 |
| ☑ | **3.5 Lệnh sửa chữa riêng** (C7.3) | Xe nằm lâu, bảo dưỡng định kỳ → **lệnh sửa riêng**, không gắn phiếu | Bảng `repair_orders`: xe, ngày, dòng chi, kho hay gara, chuỗi duyệt như mục V. Màn **Lệnh sửa chữa** riêng + màn Xe tab Sửa chữa gom cả hai nguồn. Lấy kho trừ tồn ngay (`PXK_PT`), chi chỉ phần mua ngoài (`PC_SC`) | 22/09 |

---

## Bốn câu họ để trống — giữ như đang chạy, hỏi lại khi gặp

| Câu | Đang làm |
|---|---|
| C1.1 tên hai người giữ tài khoản kế toán | Tài khoản mẫu `ketoan`, `ketoancp`; đổi tên trong màn Tài khoản khi có |
| C3.4 hao hụt khách có phạt không | Chỉ theo dõi và cảnh báo trên 1,5 %, không trừ tiền |
| C8.1 khoản nào hay vào mục VI | Ô gõ tự do như hiện tại |
| C9.1 màn phiếu chia tab có hợp lý không | Giữ tab; họ dùng thử rồi góp ý |

---

## Hai điểm em tự quyết, ghi ra để anh biết

1. **Ghi sổ theo mã con** (1371, 4021) chứ không phải mã mẹ (137, 402). Trong kế toán, mã mẹ để cộng
   dồn, mã con mới là chỗ ghi bút toán; anh Khampla cũng nói "1371 là tài khoản con". Anh Khang thấy khác
   thì đổi một bảng.
2. **Vế tiền chọn tự động**: phiếu thu có ghi *cách thu* và *tiền tệ* nên chọn đúng 1011/1012/1021/1022.
   Phiếu chi từ hai quỹ (Quỹ tiền mặt Thà Bốc, Thủ quỹ VC) mặc định **tiền mặt** đúng tên vai của họ; chi
   bằng chuyển khoản thì đổi ở bước sau nếu họ cần.
