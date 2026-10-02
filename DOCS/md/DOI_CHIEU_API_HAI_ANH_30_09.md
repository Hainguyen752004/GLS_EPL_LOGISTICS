# Đọc tài liệu và API của anh Tune, anh Toàn — mình có gì, các anh cần làm gì

Ngày 30/09/2026, chiều.

## 0. Em đã đọc và thử những gì

- **Tài liệu:**
  - `anh_Tune_taichinh_quaithuaram/md/CM-CASH-VOUCHER-DEMOLAO-API-GUIDE.md`: API thu chi DemoLao, nhánh `feat/DemoLao`.
  - `anh_toan_kho/`:
    - bản API kho đã biên dịch `Backend.API.dll`, kèm tệp mô tả `Backend.API.xml`;
    - các tệp `appsettings` (em chỉ xem tên khoá, không đọc mật khẩu);
    - ghi chú `anhtoan.txt`.
- **Hai máy chủ, chỉ đọc bản mô tả (swagger):**
  - `cantinbv-backend-api-dev.goldensme.com` — bản dev anh Toàn cho, tên *"Căn tin - Bệnh viện"*;
  - `demo-lao-api.goldensme.com` — máy anh Tune, đang cấu hình trong `.env`, tên *"QLSX - HOÀNG ANH GROUP - PRODUCTION"*.
- **Gọi thử máy `demo-lao-api`** bằng token trong `.env`:
  - **chỉ các đường xem, danh sách, tìm** (hơn 30 lần gọi, lưu bản chụp để đối chiếu);
  - **không gọi đường tạo, lưu, ghi sổ, xoá nào**;
  - không in token.

**Phát hiện quan trọng nhất:** máy `demo-lao-api` của anh Tune là **một hệ QLSX trọn bộ, 702 đường**, trên đó có **cả phần kế toán lẫn phần kho**:

- phần kho nằm ở `supply-chain/warehouse`, `supply-chain/inventory`, `supply-chain/stocktaking`, `supply-chain/plot`, `items`;
- phần kho này **cùng lõi Golden SME** với bản anh Toàn gửi: xuất nhập, tồn, mặt hàng, kiểm kho (kể cả khi mất mạng) đều có.
- Hai bản chỉ **khác nhánh**:
  - bản anh Toàn có thêm luồng bảng tạm và bước điều chỉnh sau kiểm kho, đặt tên đường hơi khác;
  - bản `demo-lao-api` có thêm quản lý kho, vị trí trong kho, lệnh sản xuất.

**Anh chốt 30/09: kho dùng API RIÊNG của anh Toàn**, không nối vào phần kho trên máy anh Tune. Phần kho trên `demo-lao-api` bên mình chỉ dùng để tham khảo khuôn trả về. Máy `demo-lao-api` chỉ dùng cho **kế toán / công nợ / thu chi của anh Tune** — làm phần này trước.

## 1. Token hiện có trong `.env`

| | |
|---|---|
| Địa chỉ | `https://demo-lao-api.goldensme.com` (biến `EPL_ACC_CODE_API`) |
| Token | của **tài khoản cá nhân `tune`** (UserId 846, ObjectId 1503) · **hết hạn 10/10/2026 09:05 (giờ Lào)** |
| Chi nhánh token được vào | 1368 "Demo EPL" · 5 "EPL 2" · 1369 "EPL 3" |

- **Cần làm:** xin anh Tune một **tài khoản dịch vụ riêng cho trang điều xe Lào**, kèm cách lấy token mới (`POST /api/v1/auth/login`).
- Token cá nhân của anh Tune thì mọi phiếu sẽ ghi tên anh ấy, và **tới 10/10 là tắt**.

## 2. Đã có sẵn, dùng được ngay

| Việc | Đường trên máy Lào | Kết quả thật (30/09) |
|---|---|---|
| Danh mục tài khoản Lào | `GET /api/v1/accounting/lao-accounts` | **494 mã**, khớp bản em chụp. Có sẵn 137, 401, 402, 1601, 4201, 707, 708 |
| Tài khoản cho hạch toán (ô Nợ/Có) | `GET …/cmpayment-receipt/country-accounts?countryId=11` | 405 mã |
| Tài khoản tiền mặc định | `GET …/default-money-account` | tiền mặt Kíp **1011** · tiền mặt ngoại tệ **1012** · ngân hàng Kíp **1021** · ngân hàng ngoại tệ **1022** — **đúng y bảng định khoản bên mình** |
| Loại phiếu thu chi | `GET …/document-types` | 14 Thu hoá đơn · 15 Thu công nợ · 16 Thu trước · 17 Thu khác · 57 Chi hoá đơn · 58 Chi công nợ · 59 Chi trước · 60 Chi khác · 68 Chuyển tiền nội bộ |
| Phương thức thanh toán | `POST /api/v1/sales/debt/payment-methods` | 1 Tiền mặt · 3 Chuyển khoản · 6 Tiền mặt/Chuyển khoản |
| Kỳ tài chính | `GET /api/v1/common/GetFinancyCicle` | 22 kỳ, từ 10/2025 tới 7/2027, đều đang mở |
| Loại chứng từ kho | `POST /api/v1/supply-chain/warehouse/GetDocType` `{OrgId, LangId}` | **65 Xuất nội bộ** (xe nhà) · **44 Xuất kho hàng bán** (xe thuê) · 42 Nhập kho hàng hoá · 53 Nhập kho tổng hợp · 33 Xuất chuyển kho · 66 Nhập kho nội bộ · 39/40 Xuất/Nhập điều chỉnh · 64 Xuất huỷ… (26 loại) |
| Báo cáo tồn | `GET /api/v1/report/inventory/now/{orgId}` | chạy được: tồn đầu, nhập, xuất, còn theo kho × mặt hàng |
| Tạo đơn bán từ DO đã giao (đề nghị thu) | `POST /api/v1/integrations/logistics/sales-orders` | có (tài liệu anh Tune 11/09) |
| Chọn DO làm nguồn cho phiếu thu chi | `GET /api/v1/accounting/cash-voucher-references?type=DO` | chạy được — nhưng **đang đọc DO của EPL_System bên Việt Nam** (23 DO mẫu `DEMO-CUS-…`), chưa đọc trang điều xe Lào |

## 3. Anh Tune cần làm

| # | Việc | Vì sao |
|---|---|---|
| 1 | **Mở 3 mã con** 1371 (dưới 137), 4021 và 4022 (dưới 402) — cách A anh đã chốt | danh mục chưa có. Tài khoản anh Tune có quyền tạo (`CanCreate`) ở `POST /api/v1/accounting/lao-accounts` |
| 2 | **Tạo đơn vị / chi nhánh EPL Lào** (quốc gia Lào, tiền mặc định LAK) | cả 4 đơn vị hiện có (EPL 1, Demo EPL, EPL 2, EPL 3) đều là **Việt Nam, tiền VND** |
| 3 | **Thêm tiền tệ USD, THB** (và CNY nếu dùng) | hệ chỉ có **VND (mã 3) và LAK (mã 26)**, trong khi cước bên Lào thường tính **USD** |
| 4 | **Tài khoản dịch vụ** cho trang điều xe | mục 1 |
| 5 | Chốt **loại phiếu chi tạm ứng**: 59 "Chi trước" hay 60 "Chi khác" kèm Nợ 1601 | |
| 6 | **Trỏ nguồn DO của phiếu thu chi sang trang điều xe Lào** (sau khi bên mình dựng xong, mục 5.1) | hiện đọc EPL_System |
| 7 | Tạo **đối tượng** (khách, tài xế, chủ xe liên kết, nhà cung cấp) cho EPL Lào, hoặc cho bên mình đồng bộ qua `master-data/customers/upsert`, `suppliers/upsert` | danh mục hiện có 189 khách, 517 nhà cung cấp, đều là dữ liệu bên khác |
| 8 | Ghi nhận **nợ tiền thuê xe liên kết** và **tách bút toán xuất bán cho chủ xe** (hai lỗ hổng đã ghi trong hợp đồng) | |

## 4. Anh Toàn cần làm (trên API kho riêng của anh ấy)

| # | Việc | Vì sao |
|---|---|---|
| 1 | **Tạo kho của EPL Lào**: kho dầu Thà Bốc, kho dầu Viêng Chăn (và các kho dầu khác), kho phụ tùng Thà Bốc | (tham khảo) máy `demo-lao-api` chỉ có kho của nhà máy giấy (Kho giấy cuộn, giấy tấm, vật tư, thành phẩm, hàng hoá, tem in) và các kho `[Test]` |
| 2 | **Tạo mặt hàng**: dầu diesel (đơn vị **lít**), danh mục phụ tùng | 2.861 mặt hàng hiện có đều là thùng carton, giấy |
| 3 | **Bổ sung thủ tục lưu còn thiếu** vào DB Lào (đúng ghi chú của anh ấy) | `POST /api/v1/supply-chain/inventory/now` trả rỗng; `GET /api/v1/report/inventory/now/1368` báo **lỗi 500**; `…/now/5` lại trả hàng của đơn vị 1368 |
| 4 | **Trả giá vốn bình quân** theo kho × mặt hàng (ở tồn tức thời hoặc lúc xuất) | báo cáo tồn chỉ có số lượng (`BeginStock`, `InQty`, `OutQty`, `Balance`), không có cột giá; bên mình cần giá bình quân cho dòng dầu kho và màn Xem kho |
| 5 | Sửa **tên loại chứng từ bị lỗi mã hoá** (mã 151–154 hiện kiểu "Nháº…p kho nguyÃªn…"; đúng ra là "Nhập kho nguyên vật liệu", "Nhập kho sản xuất", "Xuất kho sản xuất", "Xuất kho nguyên vật liệu") | |
| 6 | **Chặn trùng** khi bên mình gửi lại một phiếu xuất (theo số chứng từ tham chiếu `RefDocumentNo`) | API xuất kho không có khoá chống trùng |
| 7 | Chốt màn **cấp dầu theo mã QR** ở đâu (màn của anh ấy, hay giữ màn Cấp phát bên mình rồi gọi API xuất kho) | |

**Về bản `Backend.API` anh Toàn gửi kèm `appsettings`:**
- Bản này **cùng lõi** với phần kho đã chạy trên `demo-lao-api`, chỉ khác nhánh (hợp đồng kho, mục 13.6.1).
- **Anh chốt: bên mình nối kho vào bản riêng này.** Máy chạy và DB bên Lào anh chốt với anh Toàn. Em không tự dựng, không trỏ DB.
- Các ID kho ở mục này là của máy `demo-lao-api`, chỉ để tham khảo. Trên hệ anh Toàn, ID có thể khác.
- Các tệp `appsettings` có chuỗi kết nối DB, `JWT.Secret`, `ApiKey`. Em **không đọc giá trị**, đã chặn git, không đưa lên GitHub. Anh nên giữ hai thư mục này ngoài dự án, hoặc xoá bản sao khi xong.

## 5. Bên mình (trang điều xe) cần làm

| # | Việc | Khi nào làm được |
|---|---|---|
| 1 | **Dựng API bàn giao DO** đúng khuôn EPL_System: `GET /api/handover/delivery-orders` (danh sách) và `/{do_id}` (`{header, details}`), chỉ phiếu đã về và đã khoá | **làm ngay được**, không chờ ai |
| 2 | **Lớp chuyển tiền:** đề nghị thu → `sales-orders`; đề nghị tạm ứng → phiếu chi chờ (`save-and-commit`, `PostMode = None`); đọc công nợ khách từ `sales/debt/customer-detail` | khi có tài khoản dịch vụ và đơn vị EPL Lào |
| 3 | **Lớp chuyển kho:** cấp dầu → `CreateStockOut` loại 65 / 44; tồn, giá → `inventory/now`, báo cáo tồn; danh mục kho, mặt hàng | khi anh Toàn có kho, mặt hàng, thủ tục lưu |
| 4 | **Bảng đối chiếu mã** (đơn vị, kho, mặt hàng, tiền tệ, đối tượng, loại chứng từ) — Sếp nhập ở màn cấu hình | làm khung ngay, điền khi hai anh cấp mã |
| 5 | Ô **"Mã khách bên kế toán"** trên danh mục khách | làm ngay được |
| 6 | Đổi danh mục tài khoản sang đường `cmpayment-receipt/country-accounts` (chỉ mã cho hạch toán) | làm ngay được |

## 6. Anh cần quyết

1. Gửi cho anh Tune và anh Toàn **danh sách việc ở mục 3 và 4**, kèm hai hợp đồng (đã cập nhật số thật).
2. Cho em **làm trước mục 5.1, 5.5, 5.6** (không đụng hệ của hai anh, không ghi gì sang máy Lào)?
3. ~~Kho nối vào máy nào~~ — **anh đã chốt 30/09: API riêng của anh Toàn.** Làm module anh Tune trước.
