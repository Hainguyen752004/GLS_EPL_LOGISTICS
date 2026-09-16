# Bản đồ chức năng: từ EPL_System sang bản Lào (EPL_LAO_REAL)

Tài liệu này trả lời một câu: **mỗi thứ trong EPL_System đi đâu** khi làm lại theo Excel `ຂົນສົ່ງ EPL.xlsx` và bản giao diện bên Lào đã duyệt. Ba nhóm: **giữ và làm gọn** · **thay bằng thứ họ đang dùng** · **bỏ hẳn**.

Nguyên tắc chọn: Excel của họ có ô nào thì bản Lào có cột đó; không có thì không thêm. Khi phân vân, hỏi *"trong Excel của họ có ô này không?"*.

## 1. Vì sao phải làm lại

Bên Lào phản hồi: module quá cao, họ không hiểu. Thực tế vận hành của họ:

- Làm việc và phân quyền **trên một tệp Excel** — không kiểm xe rảnh, không kiểm tài xế rảnh, không tạo Trip, không công thức giá thành, không sắp ca.
- **Xe container có hai biển số**: biển đầu kéo (ທະບຽນຫົວ) và biển thùng (ທະບຽນຫາງ), cộng số hiệu nội bộ (ເບີລົດ, ví dụ 341). Module xe của EPL_System thiếu chỗ này.
- **Mô hình môi giới**: bên A thuê họ giá 2, họ thuê lại xe ngoài (ລົດຮ່ວມ) giá 1, lời 1. Xe ngoài bị trừ 2%/phiếu và 1 USD/tấn vượt 40 tấn.
- **Tiền trộn trong một phiếu**: cước tính USD, chi phí LAK/VND/THB, tỷ giá ghi ngay đầu phiếu (USD 22.000 · THB 700 · VND 1,2).
- **Chuỗi duyệt theo vai**: Bãi Thà Bốc nhập → Kế toán Viêng Chăn kiểm → ghi sổ → Quỹ chi. Mỗi khoản chi có mã tài khoản kép (`625/371`, `625/402`, `614/402`).
- Họ **rất thích module Tracking** và bảng theo dõi phiếu vận chuyển đã dựng lại theo ý họ.

## 2. Bảng ánh xạ

| EPL_System | Bản Lào | Quyết định | Vì sao |
|---|---|---|---|
| Báo giá (QT) | — | **Bỏ** | Họ không báo giá trên hệ; giá USD/tấn ghi thẳng vào phiếu xuất xe |
| Lệnh giao hàng (DO) | — | **Bỏ** | Không có tầng "yêu cầu của khách" riêng; một tờ phiếu là đủ |
| Chuyến (Trip) + điều phối | **Phiếu xuất xe** (ໃບເບີກລົດອອກໄປຂົນສົ່ງ) | **Thay** | Đơn vị làm việc duy nhất của họ: 6 mục I–VI, mỗi mục một trạng thái duyệt |
| Kiểm xe rảnh / tài xế rảnh / trùng lịch | — | **Bỏ** | Excel của họ không kiểm; thêm vào là thêm một thứ họ không hiểu |
| Tracking / tháp kiểm soát | **Theo dõi phiếu vận chuyển** | **Giữ, làm gọn** | Bảng họ thích nhất: một dòng một phiếu, đủ 29 cột như sheet ໜ້າລາຍງານຂົນສົ່ງ |
| Trạng thái DO (pending → in_transit → arrived → delivered) | Trạng thái vận chuyển: **xuất bến → đang chạy → đã tới** + trạng thái tài chính: **chưa thu → thu một phần → đã thu** | **Thay** | Đúng hai cột ສະຖານະ trong Excel |
| Hoàn tất giao hàng · POD · chốt giá | **Hoá đơn vận chuyển** (bản in) + nút *Lập hoá đơn* / *Đã thu tiền* của kế toán doanh thu | **Thay** | Họ không ký POD điện tử; hoá đơn giấy in ra và ký tay |
| Master data: Khách hàng | **Khách hàng** | **Giữ** | Danh mục duy nhất họ còn dùng — anh đã nói *"chỉ giữ lại được khách hàng"* |
| Master data: Xe · Loại xe · giấy tờ xe | **Xe — đầu kéo** (hồ sơ như EPL_System: số máy, số khung, hạn bảo hiểm / đăng kiểm / giấy lưu hành, công-tơ-mét, mốc bảo dưỡng, trạng thái) + **Rơ-moóc** là thực thể riêng | **Giữ, làm gọn + Mới** | Anh yêu cầu mang cả module xe sang; rơ-moóc tách riêng vì "hư cái này thì lấy cái kia lắp vào" — có lịch sử lắp/tháo |
| Tuyến đường (chặng A→B→C, km, BOT) | **Tuyến đường** | **Giữ, làm gọn** | Bỏ hình đường bộ, toạ độ, ETA; giữ chặng, km từng chặng, BOT. Chọn tuyến trên phiếu → tự điền điểm đi/đến và dòng phí cao tốc |
| Tracking / GPS / tiến độ chặng / sự cố | **Theo dõi tuyến** | **Thay** | Không GPS: Bãi bấm "xe đã tới điểm X" khi tài xế gọi về. Sự cố / sửa xe khai ở đây → dòng chi rơi vào mục V của phiếu |
| Master data: Tài xế · bằng lái · lịch ca | **Tài xế & bằng lái** (hồ sơ, hạng bằng, ngày cấp, hạn, lịch sử gia hạn, xe thường lái) | **Giữ, làm gọn** | Anh yêu cầu mang module tài xế + bằng lái sang; bỏ ca, tổ, lịch trực |
| Bảo dưỡng / phiếu sửa chữa xe | **Mục V của phiếu** + báo cáo sửa chữa theo xe (gom từ mục V) | **Thay** | Quy trình của họ: sửa xe gắn vào số phiếu xuất xe, không có phiếu bảo dưỡng riêng |
| Công thức giá thành theo loại xe | — | **Bỏ** | Họ ghi từng khoản chi thật vào phiếu, không tính giá thành theo công thức |
| Tỷ giá tiền tệ | **Tỷ giá** (USD · THB · VND → LAK), khoá vào từng phiếu lúc lập | **Giữ, làm gọn** | Đúng ba dòng Rate trên đầu phiếu của họ |
| Sổ thu – chi · Acc code từ hệ công nợ | **Mã tài khoản kép** trên từng dòng chi (625/371 · 625/402 · 614/402 · 614/371 · 1211/70 · 1211/402) | **Thay** | Chép nguyên cột ເດິນບັນຊີ trong Excel |
| Sự cố · GPS · mốc tài xế | **Diễn biến trên đường** trong Theo dõi tuyến (tới điểm · sự cố · sửa xe · ghi chú) — Bãi ghi tay | **Thay** | Không GPS, không ứng dụng tài xế: tài xế gọi điện, Bãi bấm. Đúng cách họ đang làm |
| Bãi xe · Packing list · QR | — | **Bỏ** | Hàng quặng nguyên khối, không có kiện |
| Xe liên kết (chưa có) | **Xe liên kết** — báo cáo riêng + bảng thanh toán chủ xe trên phiếu | **Mới** | Trọng tâm mô hình môi giới của họ |
| Tiền chuyến tài xế (chưa có) | **Tiền chuyến & tiền nước tài xế** — gom từ mục IV theo tháng | **Mới** | Sheet báo cáo số 5 của họ |
| Công nợ nhà cung cấp (chưa có) | **Theo dõi nhà cung cấp** — phát sinh từ phiếu, đã trả, còn nợ | **Mới** | Sheet báo cáo số 6 |
| Kho nhiên liệu (chưa có) | **Kho nhiên liệu** — sổ nhập / xuất cho xe / tồn | **Mới** | Sheet báo cáo số 3 · TK 625/371 |
| Kho phụ tùng (chưa có) | **Kho phụ tùng** — tồn, tồn tối thiểu, xuất theo xe | **Mới** | Sheet báo cáo số 4 · TK 614/371 |
| Phân quyền (hệ cha lo) | **Tài khoản & vai** — 7 vai, mỗi vai được làm một bước trên phiếu | **Mới** | Sheet ໜ້າວຽກ: ai nhập, ai kiểm, ai ghi sổ, ai chi |
| Trợ lý AI (EPL_TroLy) | — | **Không mang sang** | Ngoài phạm vi "năm 2016" |
| Trang tài xế (EPL_TaiXe) | — | **Không mang sang** | Tài xế không thao tác trên hệ |

## 3. Tám vai và việc của từng vai

| Vai | Tên trong Excel | Trên phiếu xuất xe |
|---|---|---|
| `yard` | ສະໜາມທ່າບົກ — Bãi Thà Bốc | **Nhập** mục I–VI, lập phiếu, cập nhật xe đã chạy / đã tới |
| `acct` | ບັນຊີລາຍຈ່າຍ/ຮັບ ວຽງຈັນ — Kế toán thu/chi Viêng Chăn | **Kiểm** I, II, IV, V, VI · **ghi sổ** IV, V, VI · trả lại cho Bãi sửa |
| `fuel` | ບັນຊີສາງນໍ້າມັນ — Kế toán kho nhiên liệu | **Kiểm** và **ghi sổ** mục III |
| `treasury` | ຄັງເງິນ ວຽງຈັນ — Quỹ Viêng Chăn | **Chi** mục III |
| `cash` | ຄັງເງິນສົດຍ່ອຍ ທ່າບົກ — Tiền mặt lẻ Thà Bốc | **Chi** mục IV, V, VI |
| `rev` | ບັນຊີລາຍຮັບ — Kế toán doanh thu | **Lập hoá đơn**, **ghi thu tiền** khách (mức phiếu) |
| `driver` | ໂຊເຟີ — Tài xế | Chỉ thấy **phiếu của mình**: xem tiền tạm ứng đã chi chưa, bấm **Xuất phát**, **Báo hỏng** trên đường |
| `admin` | — | Mọi việc, kể cả mở khoá mục đã duyệt và quản lý tài khoản |

Chuỗi trạng thái từng mục: `chờ → đã nhập → đã kiểm → đã ghi sổ → đã chi` (mục I–II dừng ở *đã kiểm*). Bãi chỉ sửa được khi mục còn ở *chờ* / *đã nhập*; kế toán đã kiểm là khoá.

## 4. Phép tính trên phiếu (chép từ Excel)

**Xe công ty (EPL):**
```
Tấn tính tiền = tấn cân nơi giao (chưa cân thì tạm dùng tấn đầu đi)
Doanh thu USD = tấn × giá USD/tấn
Chi LAK       = Σ (số lượng × đơn giá × tỷ giá về LAK) của mục III + IV + V + VI
Lãi USD       = doanh thu − chi ÷ tỷ giá USD
```

**Xe liên kết:**
```
Tiền thuê     = tấn × giá thuê USD/tấn
Phí           = tiền thuê × 2%
Trừ vượt      = max(0, tấn − 40) × 1 USD
Ứng trước     = Σ dòng chi EPL đã ứng ÷ tỷ giá USD   (dòng "chủ xe tự trả" không tính)
Trả chủ xe    = tiền thuê − phí − trừ vượt − ứng trước
Lãi EPL       = (giá nhận − giá thuê) × tấn
```

Ví dụ thật từ dữ liệu mẫu — phiếu `T4-0430-08/EPL`, xe ຮ່ວມ-07: 40,50 t × 40,5 = 1.640,25 · phí 32,80 · vượt 0,5 t = 0,50 · ứng 316,07 → **trả chủ xe 1.290,88 USD**; lãi EPL (41 − 40,5) × 40,5 = **20,25 USD**.

## 4b. Có trong kho thì xuất kho, không có thì chi mua ngoài

Quy tắc anh chốt sau khi đọc quy trình của họ (*EPL flow of Logistics*): **vật tư có trong kho → phiếu xuất kho; không có → phiếu chi đi mua**. Hệ áp thẳng vào từng dòng chi:

| Khoản | Nguồn | Điều gì xảy ra | Định khoản xe nhà | Định khoản xe liên kết |
|---|---|---|---|---|
| Nhiên liệu đổ ở **kho Thà Bốc** | kho | Kế toán kho **ghi sổ** mục III → tự sinh dòng **xuất kho nhiên liệu** theo số phiếu | `625/371` | `4022/371` |
| Nhiên liệu đổ **trạm ngoài / Việt Nam** | mua | Chi tiền / công nợ | `625/402` | `4022/402` |
| Sửa xe **lấy phụ tùng từ kho** | kho | Trừ tồn kho phụ tùng **ngay lúc khai** trên màn Theo dõi tuyến | `614/371` | `4022/371` |
| Sửa xe **mua ngoài / garage** | mua | Công nợ nhà cung cấp / tiền mặt | `614/402` | `4022/402` |
| Đi đường, khác | mua | Chi tiền | `625/402` | `4022/402` |

Xe liên kết đi mã `4022/…` vì đó là **chi hộ nhà thầu phụ** — sau trừ vào tiền trả chủ xe — đúng cột "for Sub contracts" trong tài liệu quy trình của họ.

Sửa xe khai trên đường (màn **Theo dõi tuyến → Báo sự cố / sửa xe**) trở thành một dòng trong **mục V của phiếu xuất xe**; mục V quay về *đã nhập* để kế toán kiểm lại. Dòng đã sinh phiếu xuất kho là chứng từ kho — không xoá, không đổi số trên phiếu.

## 4c. Acc code lấy từ API bên công nợ (anh Khang), không tự đặt

Mỗi dòng chi trên phiếu phải có **Acc code** thì mới lập được phiếu thu / phiếu chi. Danh mục mã
**không khai trong hệ này** mà gọi sang API bên công nợ (`GET /api/acc-codes` proxy sang Golden SME,
nhớ đệm 10 phút). Màn phiếu xuất xe cho bấm vào ô mã để chọn từ danh mục đó.

Hệ tự gợi ý mã mặc định theo đúng bảng định khoản của họ: xe nhà `625/…` (nhiên liệu, đi đường,
khác) và `614/…` (sửa chữa); xe liên kết `4022/…`; lấy kho thì vế sau là `…/371`, mua ngoài là
`…/402`. Mã nào **chưa có trong danh mục bên công nợ** thì màn hình ghi rõ "không có trong danh
mục" — không bịa thêm mã, cũng không im lặng bỏ qua.

## 4d. Một giai đoạn một tờ chứng từ

Phiếu xuất xe không phải một tờ giấy chết: nó **mở suốt chuyến**, mỗi giai đoạn sinh một chứng từ.

1. **Lập phiếu xuất xe** → bấm **Phiếu chi tạm ứng**, in cho tài xế cầm đi lấy tiền. Phiếu chi
   gom đúng những dòng EPL ứng trước (mục III · IV · VI, không phải hàng lấy từ kho).
2. **Duyệt hết dây chuyền** (Bãi nhập → Kế toán kiểm → ghi sổ → Quỹ chi) thì tài xế mới nhận tiền.
3. **Tài xế bấm Xuất phát.** Mục IV chưa ở trạng thái *đã chi* mà bấm thì hệ chặn
   (`CHUA_NHAN_TAM_UNG`) — chỉ admin đi tắt được.
4. **Đang chạy, xe hỏng** → tài xế bấm **Báo hỏng**, khai hỏng gì và bao nhiêu tiền.
5. **Bãi hoặc admin duyệt** báo hỏng đó → hệ **tự mở lại phiếu**, thêm dòng sửa chữa vào **mục V**
   đúng số tiền đã duyệt, định khoản theo quy tắc kho / mua ở mục 4b. Từ chối thì không sinh dòng nào.
6. **Xe tới nơi** → cân cuối, lập hoá đơn, ghi thu tiền khách.

## 5. Kiến trúc — cố ý đơn giản

- **Một DB riêng** `epl_lao` trên cùng máy chủ PostgreSQL; không đụng `epl_logistics` của EPL_System.
- **Không migration**: bảng dựng từ model bằng `create_all`. Đổi cột thì `python backend/app/seed.py --dung-lai` trên máy dev.
- **Backend** FastAPI: một tệp route cho mỗi module (`routes/phieu.py`, `routes/kho.py`, …), luật phân quyền tập trung ở `services/phan_quyen.py`, phép tính ở `services/tinh_toan.py`.
- **Frontend**: khung `index.html` + `js/chung.js` nạp từng module từ `modules/<tên>/<tên>.html · .css · .js` — **một module một bộ ba tệp**, sai đâu mở đúng thư mục đó.
- **Ngôn ngữ**: Việt · Lào · Anh · Việt+Lào, từ điển 607 khoá trong `js/ngon_ngu.js`. Chữ Lào chép nguyên từ bản mẫu bên Lào đã duyệt.
- **Đăng nhập** tên + mật khẩu, phiên ký HMAC 12 giờ. Mật khẩu băm PBKDF2, không lưu chữ thường.
- **Màn đăng nhập** là một trang riêng chiếm trọn màn hình (trái: thương hiệu, phải: biểu mẫu tự cuộn), có sẵn danh sách tài khoản demo để bấm thẳng vào — bản demo chạy trên máy chiếu, không ai muốn gõ tay mười tài khoản.

## 6. Những gì cố ý KHÔNG làm

Không kiểm xe rảnh khi lập phiếu (chỉ hiện trạng thái xe/tài xế để người lập tự nhìn). Không kiểm tài xế trùng lịch. Không công thức giá thành. Không sắp ca. Không GPS — "xe tới điểm X" là do Bãi bấm. Không POD điện tử. Không QR. Không trợ lý AI. Không ứng dụng riêng cho tài xế — tài xế dùng chính web này, đăng nhập vào chỉ thấy một màn "Phiếu của tôi" với ba việc: xem tiền tạm ứng, bấm xuất phát, báo hỏng.

Hạn giấy tờ xe, hạn đăng kiểm, hạn bằng lái thì **có** — nhưng chỉ là cờ màu trên danh mục (còn hạn · sắp hết · đã hết), không chặn lập phiếu. Chặn là thêm một cái họ không hiểu; cờ màu thì ai cũng hiểu.

Mỗi thứ trên đều là một tính năng họ không có trong Excel — tức một tính năng họ sẽ không hiểu, và không hiểu thì không dùng.
