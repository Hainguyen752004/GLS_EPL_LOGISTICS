# Convert EPL_PYTHON to C#

Nhật ký chuyển trang điều xe EPL (FastAPI Python + HTML/CSS/JS) vào Web GLS (C#) thành module **Vận tải**.
API và DB vẫn của EPL (FastAPI + PostgreSQL); Web GLS gọi sang qua BFF.

Mỗi việc ghi: số việc trong sheet «EPL Laos», ngày, trạng thái, tệp mới, tệp sửa (dòng nào, đổi gì), cấu hình, cách kiểm.
Đường dẫn tính từ thư mục chứa các repo: `GLS-QLSX-Web/…`, `GLS-QLSX-APIs/…`, `EPL_LAO_REAL/…`.

## Tiến độ (đối chiếu sheet «EPL Laos» của anh Khang)

Trạng thái: Chưa làm · Đang làm · Xong – chờ duyệt · Đã duyệt. Cập nhật sau khi anh Hải duyệt từng việc.

| STT | Công việc | Trạng thái | Kiểm ở đâu | Chi tiết |
|---|---|---|---|---|
| 1 | Xây dựng module logistic | Đã duyệt (trước 08/10) | | |
| 2 | Nối API Kế toán và Kho | Đã duyệt (trước 08/10) | | |
| 3 | Chốt kiến trúc: giao diện vào Web GLS, API Python + DB PostgreSQL | Chưa làm | | |
| 4 | Đăng nhập: giữ giao diện màn đăng nhập EPL, gọi API đăng nhập của GLS | Đã duyệt (08/10) | Web: đăng nhập tune → /Logistics/Me ra "username":"admin"; trang điều xe: đăng nhập bằng tài khoản GLS | [Việc 4](#việc-4--đăng-nhập-dùng-api-đăng-nhập-của-gls) |
| 5 | Khung module Vận tải + client gọi API Python | Đã duyệt (08/10) | Đăng nhập Web → mở `/Logistics/Health` → `"success": true` | [Việc 5](#việc-5--khung-module-vận-tải--client-gọi-api-python) |
| 6 | Phân quyền theo mã quyền GLS | Đã duyệt (08/10) | Gán mã Logistics.Role.* cho người dùng GLS → /Logistics/Me ra "nguon_vai":"gls" | [Việc 6](#việc-6--phân-quyền-theo-mã-quyền-gls) |
| 7 | Menu Vận tải trên màn GLS | Đã duyệt (08/10) | Web: đăng nhập → menu Vận tải (bảng 2 cột như Quản lý kho) → bấm màn → ở lại Web /Logistics/<màn> | [Việc 7](#việc-7--menu-vận-tải-trên-web-gls) |
| 8 | Chuyển đa ngôn ngữ vi / lo / en | Đã duyệt (08/10) | Web: trang /Logistics/… có 3038 khoá LOG_ (Console); trang khác 0 | [Việc 8](#việc-8--chuyển-đa-ngôn-ngữ-vi--lo--en) |
| 9 | Khách hàng dùng bảng Đối tượng của anh Khang | Đã duyệt (08/10) — phần 1 (API), 2a (danh sách, bảng giá), 2b (hợp đồng, công nợ, chuyến) | tools/chuyen_csharp/doi_chieu_khach_gls.py (chỉ xem → --ghi); trang điều xe Khách hàng: sửa tên khách đã gắn → báo sửa ở màn Đối tượng GLS; Web /Logistics/khach-hang: chọn khách → chi tiết + bảng giá; tab Hợp đồng / Công nợ / Chuyến & phiếu | [Việc 9](#việc-9--khách-hàng-dùng-bảng-đối-tượng-của-anh-khang) |
| 10 | Nhà cung cấp, chủ xe liên kết dùng bảng Đối tượng của anh Khang | Đã duyệt (08/10) — phần 1 (API), phần 2 (màn Nhà cung cấp trên Web) | tools/chuyen_csharp/doi_chieu_khach_gls.py --loai tat_ca (chỉ xem → --ghi); trang điều xe: sửa tên NCC / điện thoại chủ xe đã gắn → báo sửa ở danh mục chung; Web /Logistics/nha-cung-cap | [Việc 10](#việc-10--nhà-cung-cấp-chủ-xe-liên-kết-dùng-bảng-đối-tượng-của-anh-khang) |
| 11 | Màn Phiếu xuất xe (DO) | Đang làm (từ 08/10) | | |
| 12 | Theo dõi phiếu · Theo dõi tuyến (bản đồ) · Tổng quan | Chưa làm | | |
| 13 | Đề nghị chi · Đề nghị xuất kho · Đề nghị thu · Đề nghị theo DO · Bút toán chờ gửi | Chưa làm | | |
| 14 | Tất toán tài xế · Tiền chuyến & nước · Tất toán đối tác · Xe liên kết | Chưa làm | | |
| 15 | Danh mục: Xe · Tài xế · Thẻ cao tốc · Tỷ giá · Tuyến đường | Chưa làm | | |
| 16 | Xem kho (hàng gửi bãi) | Chưa làm | | |
| 17 | App tài xế (Phiếu của tôi) trên điện thoại | Chưa làm | | |
| 18 | Quy trình · Tài khoản | Chưa làm | | |
| 19 | Xuất Excel / PDF và in phiếu theo chuẩn Web | Chưa làm | | |
| 20 | FastAPI chỉ còn là API — dọn phần thừa | Chưa làm | | |
| 21 | Kiểm thử | Chưa làm | | |
| 22 | Triển khai và cắt chuyển | Chưa làm | | |
| 23 | Tài liệu | Chưa làm | | |

---

## Việc 10 — Nhà cung cấp, chủ xe liên kết dùng bảng Đối tượng của anh Khang

- **Thông tin chung:** ngày 08/10/2026; repo EPL_LAO_REAL (nhánh doi-kho-sang-ke-toan) + GLS-QLSX-Web (nhánh feat/hontunedhai_Laos); trạng thái đã duyệt đủ 2 phần 08/10.
- **Chốt:** như Việc 9 — nhà cung cấp và chủ xe liên kết là đối tượng trong danh mục nhà cung cấp chung (cùng nhóm suppliers bên đó); bảng `suppliers` / `owners` giữ làm hồ sơ vận tải với cột `obj_id`; tên · điện thoại · địa chỉ · mã là bản chép; phần riêng vận tải giữ bên EPL (nhà cung cấp: khoản mục chi, mã kế toán, kỳ trả, khách cấn trừ · chủ xe: phí %, ngưỡng quá tải, mức trừ, tiền thuê, cách trả). Chứng từ kế toán (phiếu chi, đề nghị trả, công nợ đối tác) dùng thẳng obj_id. Tài xế (EPLTX-) giữ như cũ. Gom khách · nhà cung cấp · chủ xe vào một module chung `services/doi_tuong_gls.py`; `services/khach_gls.py` thành lớp vỏ giữ tên hàm cũ (Việc 9 không phải sửa). Cờ mới `EPL_NCC_GLS` (mặc định 0). Luật chép (sửa 08/10 sau khi anh Hải kiểm): ô điện thoại / địa chỉ bên danh mục chung để trống thì GIỮ giá trị đang có (trước đó gắn chủ xe làm mất số "020 5555 7777" — đã trả lại trên d7). Chủ xe đổi tên trong danh mục chung thì tên trên danh mục xe đổi theo. Mô tả của đối tượng bên em tạo trong danh mục chung đổi thành «… — module Vận tải EPL» (không còn «trang điều xe»).

### Bảng Tệp mới

| Tệp | | Nội dung |
|---|---|---|
| `backend/app/services/doi_tuong_gls.py` | — | Module chung 3 loại (khach · ncc · chu_xe): `LOAI` (34) bảng / đường / tiền tố mã / cờ / câu báo từng loại; `duong` (50), `bat` (55), `tim` (82, nhớ kết quả), `mot` (101), `_chep` (108, giữ điện thoại / địa chỉ khi bên kia trống), `_nho_doi_tuong` (121), `_theo_ten_chu_xe` (130), `lien_ket` (136), `tao` (173), `dong_bo` (198), `chan_sua_chung` (226, 409 SUA_O_GLS khi đổi thông tin chung của hồ sơ đã gắn), `tim_kem_ho_so` (239, kèm customer_id / supplier_id / owner_id). |
| `kiem/thu_ncc_gls.py` | — | Bài kiểm 32 bước trên bản sao _d7 trong giao dịch ROLLBACK, danh mục chung giả lập: tìm (116), gắn (125), luật mới (147), chứng từ dùng obj_id + tài xế đường cũ (168), chép lại + tên chủ xe trên danh mục xe (181), luật cũ (204). Kết quả 32/32. |

### Bảng Tệp sửa

| Tệp | Dòng | Thay đổi |
|---|---|---|
| `backend/app/models.py` | 109–111 | `Owner`: code, obj_id, gls_synced_at. |
| | 251–255 | `Supplier`: code, phone, address, obj_id, gls_synced_at. |
| `backend/app/services/khach_gls.py` | toàn tệp | Lớp vỏ của doi_tuong_gls cho loại khach (giữ DUONG_DS, DUONG_CT, DUONG_GHI, TIEN_TO_MA, O_CHUNG, bat, tim, mot, lien_ket, tao, dong_bo…). |
| `backend/app/services/chi_tune.py` | 39 | import thêm `Supplier`. |
| | 152–157 | `doi_tuong`: khách · nhà cung cấp · chủ xe đã có obj_id → trả thẳng; tài xế đường cũ. Mô tả đối tượng tạo mới: «… — module Vận tải EPL». |
| `backend/app/routes/nha_cung_cap.py` | 28 | `SUA_NCC = can_vai("expacct")`. |
| | 191–193 | Dòng nhà cung cấp thêm code, phone, address, obj_id, gls_synced_at. |
| | 228–290 | `_ap_rieng`; mới `GET /api/suppliers/gls`, `POST /api/suppliers/gls/{obj_id}`, `POST /api/suppliers/dong-bo-gls`; `POST /api/suppliers` gắn / tạo trong danh mục chung khi có obj_id hoặc cờ bật; `PUT` chặn đổi thông tin chung của hồ sơ đã gắn. |
| `backend/app/routes/chu_xe.py` | 72–73 | Dòng chủ xe thêm code, obj_id, gls_synced_at. |
| | 162–213 | Mới `GET /api/owners/gls`, `_gan_chu_xe`, `POST /api/owners/gls/{obj_id}`, `POST /api/owners/dong-bo-gls`; `POST /api/owners` gắn / tạo khi có obj_id hoặc cờ bật; `PUT` chặn đổi thông tin chung. |
| `backend/app/services/dong_bo_nen.py` | 19, 182–200, 225–226 | Bước nền `ncc_gls` (nhà cung cấp + chủ xe chép quá 60 phút) khi `EPL_NCC_GLS=1`. |
| `tools/chuyen_csharp/doi_chieu_khach_gls.py` | 30, 58, 101–116 | Đối chiếu cả 3 loại: `--loai khach|ncc|chu_xe|tat_ca`; tham số lạ / thiếu (ví dụ `--lo`) thì dừng và in cách dùng. |
| `.env.example` | 22–24 | `EPL_NCC_GLS=0` kèm chú thích. |

### Cách kiểm (đã làm 08/10):

1. `python kiem/thu_ncc_gls.py` → 32/32; `kiem/thu_khach_gls.py` → 45/45 (sau khi gom module); các bộ cũ qua: thu_ban_giao_dau 52/52, thu_dong_bo_nen 33/33, thu_no_tram_dau 22/22, thu_tat_toan_doi_tac 64/64, thu_tat_toan_tune 79/79, thu_chu_xe 51/51, thu_but_toan_cho, thu_chi_tam_ung_ke_toan, thu_gui_but_toan, thu_xe_thue_ke_toan (exit 0).
2. Đối chiếu trên d7: `--loai tat_ca` → khách khớp 2 / chưa có 1; nhà cung cấp khớp 2 (chip Lào → 1615, trạm dầu VN → 1625) / chưa có 3 (chip Việt, thẻ cao tốc, tiệm lốp); chủ xe khớp 1 (ທ້າວ ຄຳຫລ້າ → 1606). `--ghi` ghi obj_id + mã vào d7.
3. Trang điều xe 8011 (cờ EPL_NCC_GLS=1): ketoancp sửa tên NCC đã gắn → báo sửa ở danh mục chung, đổi kỳ trả → lưu; ketoan: chủ xe còn số điện thoại, sửa điện thoại → báo, đổi phí % → lưu.

### Phần 2 — Màn Nhà cung cấp trên Web

- **Thông tin chung:** ngày 08/10/2026; repo GLS-QLSX-Web (nhánh feat/hontunedhai_Laos) + EPL_LAO_REAL; đã duyệt 08/10.
- **Màn:** địa chỉ Web `/Logistics/nha-cung-cap`. Bố cục hai cột vừa một màn hình: trái danh sách (tên, mã, dịch vụ, còn nợ LAK, đang dùng); phải chi tiết (điện thoại, địa chỉ, dịch vụ, mã kế toán — chỉ vai thấy tiền chi, kỳ trả, khách cấn trừ, số dòng chi trên phiếu, lần cập nhật, ghi chú), nút «Sửa thông tin nhà cung cấp» (mở /ObjManagement/Detail?id=…), «Sửa phần vận tải». Khối «Công nợ & trả tiền»: phát sinh / đã trả / chờ chi / còn nợ (API tính); ô lập đề nghị trả (số tiền gợi ý số còn nợ, tiền tệ, tỷ giá khi khác Kíp, cách trả, ghi chú) — trả vượt số nợ API báo TRA_QUA_NO, màn hỏi xác nhận rồi gửi lại kèm xac_nhan; lịch sử đề nghị trả với trạng thái Chờ thủ quỹ chi / Đã chi / Chưa gửi được sang Kế toán / Phiếu chi đã bị xoá ở Kế toán / Đã bỏ và nút Cập nhật · Gửi lại · Bỏ. Nút trên: Chọn từ danh mục nhà cung cấp (dòng đã là chủ xe liên kết có ghi chú) · Thêm nhà cung cấp · Cập nhật thông tin. Danh sách chọn (dịch vụ, mã kế toán, kỳ trả, tiền tệ, cách trả) do API trả qua `GET /api/suppliers/quyen` — màn cũ ghi cứng trong JS; giá trị cũ ngoài danh sách (ví dụ «diesel») vẫn hiện.

#### Bảng Tệp mới (GLS-QLSX-Web)

| Tệp | | Nội dung |
|---|---|---|
| `Backend/Views/Modules/Logistics/NhaCungCap.cshtml` | — | Trang: đầu trang + hai cột + khối công nợ & trả tiền + hộp chọn từ danh mục + hộp form thêm / sửa phần vận tải. |
| `Backend/wwwroot/ViewAssets/scripts/modules/logistics/nha-cung-cap.js` | — | JS hàm phẳng: `initSupplierPage` (83), `loadSuppliers` (137), `selectSupplier` (154), `initPayForm` (184), `initPayGrid` (206), `loadPayInfo` (263), `createPayRequest` (292, xử lý TRA_QUA_NO), `payAction` (328), chọn từ danh mục (350–424), form (426–503), `refreshSupplierDetails` (505). |
| `Backend/wwwroot/ViewAssets/styles/modules/logistics/nha-cung-cap.css` | — | CSS gói trong `.lg-ncc`, hai cột vừa màn hình, màn hẹp một cột. |
| `Backend/Controllers/Modules/Logistics/LogisticsSupplierController.cs` | — | BFF `GET Logistics/nha-cung-cap` + `Logistics/Suppliers/` Rights, List, Debts, Customers, Search, AddFromList, Create, Update, RefreshDetails, PayInfo, PayRequest, PayAction (chỉ nhận cap-nhat · gui-lai · huy); `[CheckPermission(PermissionCodes.Logistics_NhaCungCap)]`. |
| `Backend/Business/ApiClients/Logistics/LogisticsSupplierClient.cs` | — | Client có kiểu; thân gửi dựng rõ khoá snake_case; ty_gia / xac_nhan chỉ gửi khi có. |
| `Backend/Business/ApiClients/Logistics/Contracts/Suppliers/LogisticsSupplierContracts.cs` | — | Contract quyền + lookups, nhà cung cấp (kèm cột công nợ), trang tìm danh mục chung (SupplierId / OwnerId), kết quả cập nhật, công nợ + đề nghị trả (VoucherType là chữ «CMP»), các yêu cầu. |

#### Bảng Tệp sửa

| Tệp | Dòng | Thay đổi |
|---|---|---|
| `Backend/Business/ApiClients/Logistics/Endpoints/LogisticsEndpoint.cs` | 67–97 | Đường API nhà cung cấp: suppliers/quyen, suppliers, suppliers/{0}, suppliers/cong-no, suppliers/gls, suppliers/gls/{0}, suppliers/dong-bo-gls, suppliers/{0}/tra-ke-toan, suppliers/{0}/de-nghi-tra, chi-ncc/{0}/{1}. |
| `Backend/Business/Register.cs` | 68 | Đăng ký `ILogisticsSupplierClient`. |
| `Backend.Common/PermissionCodes.cs` | 398 | `Logistics_NhaCungCap = "Logistics.NhaCungCap"`. |
| `Backend/Base/Localization/logistics.*.json` | — | Sinh lại: 3101 khoá. |
| (EPL_LAO_REAL) `backend/app/routes/nha_cung_cap.py` | 239–256 | Hằng KHOAN_NCC, TK_NCC, KY_TRA_NCC, CACH_TRA_NCC; mới `GET /api/suppliers/quyen` (edit · view_acct · view_debt · request_pay · gls + lookups). |
| (EPL_LAO_REAL) `kiem/thu_ncc_gls.py` | 116 | Mục «0. quyền màn Nhà cung cấp trên Web»; tổng 36 bước. |
| (EPL_LAO_REAL) `tools/chuyen_csharp/khoa_dich_web_rieng.json` | — | Thêm 28 câu màn Nhà cung cấp (vi / lo / en), tổng 63 khoá riêng. |

#### Cách kiểm (đã làm 08/10)

1. `python kiem/thu_ncc_gls.py` → 36/36. Build Web 0 cảnh báo, 0 lỗi.
2. Chương trình kiểm C# (đọc dữ liệu thật máy thử 8011 vào contract Web, đăng nhập ketoancp cho phần nhà cung cấp) → 31/31: mọi khoá API trả có thuộc tính C# tương ứng (quyền, lookups, danh sách, công nợ, tìm danh mục chung, công nợ + đề nghị trả — dòng đề nghị so với mẫu do hàm xuất của API tạo vì d7 chưa có đề nghị nào).
3. Web `https://localhost:5014/Logistics/nha-cung-cap` (tune / admin): 5 nhà cung cấp; chip Lào và trạm dầu VN có mã EPLNCC-…; chọn → khối công nợ & trả tiền; sửa phần vận tải lưu được; NCC chưa gắn có nhãn «Chưa có trong danh mục nhà cung cấp»; «Chọn từ danh mục nhà cung cấp» gõ «Trạm» → dòng trạm dầu «Đã thêm».

**Ghi chú:** Giao diện chủ xe ở màn Xe liên kết (Việc 14), dùng lại khối Hợp đồng (kind thue_xe).

---

## Việc 9 — Khách hàng dùng bảng Đối tượng của anh Khang

- **Ngày:** 08/10/2026. **Repo:** GLS-QLSX-Web (nhánh feat/hontunedhai_Laos) + EPL_LAO_REAL. **Trạng thái:** Đã duyệt (08/10) — phần 1 (API), 2a (danh sách, bảng giá), 2b (hợp đồng, công nợ, chuyến).
- **Chốt:** khách của vận tải là đối tượng nhóm khách hàng trong Đối tượng GLS (PUBOBJECT, màn `/ObjManagement/Customer` của Web). Bảng `customers` KHÔNG bỏ mà thành «hồ sơ vận tải» của một đối tượng GLS: cột mới `customers.obj_id` = OBJ_AUTOID (một đối tượng ↔ một hồ sơ). Lý do giữ bảng: 7 bảng (phiếu DO, hợp đồng, bảng giá, hoá đơn, thẻ cao tốc, bán hàng, nhà cung cấp cấn trừ) trỏ customers.id. Tên · điện thoại · địa chỉ · mã khách (OBJ_OBJECTNO) là BẢN CHÉP từ GLS — sửa ở màn Đối tượng GLS; phần riêng vận tải giữ bên EPL: cách xuất hoá đơn, loại khách, ghi chú, bảng giá, hợp đồng. SO / đề nghị thu dùng thẳng obj_id.
- **Đường GLS dùng** (API anh Khang, cùng gốc/token với chi_tune): `POST /api/v1/master-data/customers/list` {PageIndex, ObjKey} — ObjKey khớp một phần tên hoặc đúng cả mã, 100 dòng/trang; `POST /api/v1/master-data/customers/detail` {ObjId, OrgId, LangId}; `POST /api/v1/master-data/customers/upsert`.
- **Cờ:** `EPL_KHACH_GLS` (mặc định 0 = như cũ; 1 = thêm khách là chọn/tạo đối tượng GLS, thông tin chung của khách đã gắn chỉ sửa ở GLS, luồng nền chép lại). `EPL_GLS_KHACH_GIAY` (mặc định 300) = nhớ kết quả tìm. Bật trên host SAU khi chạy công cụ đối chiếu với --ghi.

### Tệp mới

| Tệp | | Nội dung |
|---|---|---|
| `backend/app/services/khach_gls.py` | — | Dịch vụ khách = Đối tượng GLS: `bat()` (dòng 41), `tim(q, trang)` tìm có nhớ (68), `mot(obj_id)` đọc chi tiết (87), `_chep` chép tên/sđt/địa chỉ/mã (94), `_nho_doi_tuong` giữ bảng doi_tuong_tune khớp (104), `lien_ket(db, obj_id)` lập/nhận hồ sơ vận tải — tìm theo obj_id, rồi bảng nhớ đối tượng kế toán, rồi khách cũ cùng mã (113), `tao(data, ma)` tạo đối tượng khách bên GLS, mã trùng → 409 MA_DA_CO_BEN_GLS (143), `dong_bo(db, n, cu_hon_phut)` chép lại, đối tượng mất ghi vào `mat` (165). |
| `tools/chuyen_csharp/doi_chieu_khach_gls.py` | — | Đối chiếu khách cũ ↔ GLS: không cờ = chỉ xem; `--ghi` ghi obj_id + chép thông tin (DB EPL); `--ghi --tao` tạo khách chưa có bên GLS (ghi DB GLS). Thứ tự tìm: obj_id → bảng nhớ đối tượng kế toán → mã khách đúng cả mã. Chưa có cột obj_id thì dừng, bảo khởi động máy chủ bản mới một lần. |
| `kiem/thu_khach_gls.py` | — | Bài kiểm 31 bước trên bản sao _d7 trong giao dịch ROLLBACK, GLS giả lập: tìm (dòng 115), lập hồ sơ (125), luật cũ (149), luật mới (158), SO dùng obj_id (180), chép lại + luồng nền (190). Kết quả 31/31. |

### Tệp sửa

| Tệp | Dòng | Đổi gì |
|---|---|---|
| `backend/app/models.py` | 77–81 | `Customer.obj_id` (Integer, index) và `Customer.gls_synced_at` (lần chép gần nhất); máy chủ tự thêm cột khi khởi động. |
| `backend/app/services/chi_tune.py` | 39 | import thêm `Customer`. |
| | 152–155 | `doi_tuong(loai="khach")`: khách đã có obj_id → trả thẳng, không gọi GLS. |
| | 159, 182 | khách chưa có obj_id: tìm thấy / tạo xong đối tượng thì ghi luôn `obj_id` lên khách. |
| `backend/app/routes/danh_muc.py` | 30–35 | Tách bộ vai thành hằng `VAI_SUA_DANH_MUC`, `VAI_SUA_BANG_GIA`, `VAI_XEM_BANG_GIA` rồi `can_vai(*…)`. |
| | 124–141 | `_them_khach_gls`: không có obj_id thì tạo bên GLS (mã gõ tay chỉ vai acct/admin, 403 MA_KHACH_KE_TOAN), rồi `lien_ket` + phần riêng vận tải. |
| | 157–164 | `GET /api/customers/gls` trả `{items, page, pages, total}` (khoá tiếng Anh: obj_id, code, name, phone, address, tax_id, active, is_org, customer_id). |
| | 166–173 | `POST /api/customers/gls/{obj_id}`. |
| | 175–180 | `POST /api/customers/dong-bo-gls`. |
| | 228–233 | Khoá 409 `SUA_O_GLS`. |
| `backend/app/services/dong_bo_nen.py` | 17–18 | ghi chú loại `khach_gls`. |
| | 160–178 | Mới `_khach_gls`: chép lại khách chép quá 60 phút; lỗi mạng/5xx → dừng lượt; đối tượng mất → loi_ban_ghi. |
| | 199–201 | thêm bước `khach_gls` cuối lượt khi `EPL_KHACH_GLS=1`. |
| `.env.example` | 17–21 | `EPL_KHACH_GLS=0`, `EPL_GLS_KHACH_GIAY=300` kèm chú thích. |
| `backend/app/services/khach_gls.py` | 60, 69 | `_dong` và `tim` trả khoá tiếng Anh như trên. |
| `kiem/thu_khach_gls.py` | — | Bài kiểm 36 bước (thêm mục «0. quyền màn Khách hàng trên Web» dòng 115 và kiểm cờ current của bảng giá dòng 169), kết quả 36/36. |
| (EPL_LAO_REAL) câu lỗi người dùng thấy, bỏ chữ GLS / trang điều xe | — | `backend/app/services/khach_gls.py` 119, 130, 153, 162; `backend/app/routes/danh_muc.py` 137, 231; `backend/app/services/bao_mat.py` 96, 106, 108; `backend/app/routes/dang_nhap.py` 25, 58; `backend/app/services/dang_nhap_gls.py` 79, 97 (mã lỗi giữ nguyên). |
| (EPL_LAO_REAL) `tools/chuyen_csharp/sinh_khoa_dich_web.py` | — | Gộp thêm `khoa_dich_web_rieng.json` (khoá phải bắt đầu LOG_W_, không trùng từ điển trang điều xe). |
| (EPL_LAO_REAL) `tools/chuyen_csharp/sinh_menu_van_tai.py` | 66 | Mô tả màn Tài khoản: «Người dùng, vai, gắn tài khoản đăng nhập Web»; chạy lại → `GLS-QLSX-APIs/Backend.API/Database/Scripts/20261008_logistics_menu.sql` + khoá MENU cập nhật. |
| (EPL_LAO_REAL) `frontend/js/ngon_ngu.js` | 15185–15189 | Nhãn ô gắn tài khoản: «Tài khoản đăng nhập Web». |

### Cách kiểm (đã làm 08/10):

1. Đối chiếu (chỉ xem) trên DB thử d7: đặt `DATABASE_URL` = bản sao d7, `QLSX_BASE_URL=http://127.0.0.1:5090`, chạy `python -X utf8 tools/chuyen_csharp/doi_chieu_khach_gls.py` → «Khớp 2 · chưa có bên GLS 1» (ຄຳຕຸ້ຍ → 1608, ນາງ ວັນນາ → 1609; ລາວ-ຈີນ chưa có). Chạy lại với `--ghi` → hai khách có obj_id.
2. Trang điều xe thử 8011 (cờ EPL_KHACH_GLS=1), đăng nhập ketoan → Khách hàng: đổi cách xuất hoá đơn → lưu được; sửa tên khách đã gắn → báo «Tên, điện thoại, địa chỉ, mã khách sửa ở màn Đối tượng GLS — trang này tự chép về».
3. Thêm khách mới ở 8011 → khách hiện ở Web /ObjManagement/Customer với mã EPLKH-… (ghi vào DB demo).
4. `python kiem/thu_khach_gls.py` → 36/36; các bộ kiểm cũ thu_dong_bo_nen, thu_de_nghi, thu_but_toan_cho, thu_gui_but_toan, thu_tat_toan_tune, thu_chu_xe, thu_the_cao_toc, thu_ban_giao_dau, thu_no_ky_thuat chạy qua.

### Phần 2a — Màn Khách hàng trên Web (danh sách, bảng giá)

- **Ngày:** 08/10/2026. **Repo:** GLS-QLSX-Web (nhánh feat/hontunedhai_Laos) + EPL_LAO_REAL. **Trạng thái:** Đã duyệt 08/10.
- **Màn:** địa chỉ Web `/Logistics/khach-hang` (đường chữ cố định, thắng trang chờ `Logistics/{screen}`). Bố cục hai cột vừa một màn hình: trái danh sách khách (tên, mã, cách xuất hoá đơn, còn nợ LAK, đang dùng); phải chi tiết (điện thoại, địa chỉ, loại khách, cách xuất hoá đơn, còn nợ, lần cập nhật thông tin, ghi chú) + bảng giá. Thông tin chung chỉ xem, nút «Sửa thông tin khách» mở `/ObjManagement/Detail?id=…` ở tab mới; nút «Sửa phần vận tải» (cách xuất hoá đơn, loại khách, ghi chú, đang dùng); «Chọn từ danh mục khách hàng chung» (tìm theo tên / đúng mã, bấm Chọn); «Thêm khách hàng» (thêm vào danh mục chung); «Cập nhật thông tin khách». Bảng giá thêm / sửa / xoá; dòng đang áp dụng do API đánh dấu (`current`), Web chỉ tô và ghi nhãn «Đang áp dụng». Nút hiện / ẩn theo quyền API trả (`GET /api/customers/quyen`), danh sách chọn (tiền tệ, cách tính, loại hàng, cách xuất hoá đơn, loại khách) cũng lấy từ API — Web không ghi cứng vai. Chốt 08/10 (anh Hải): chữ người dùng thấy không nhắc «danh mục khách hàng chung» hay «trang điều xe» — với khách cả hệ thống là EPL.

### Tệp mới

| Tệp | | Nội dung |
|---|---|---|
| `Backend/Controllers/Modules/Logistics/LogisticsCustomerController.cs` | — | BFF: `GET Logistics/khach-hang` (trang) + `Logistics/Customers/` Rights, List, Debts, Search, AddFromList, Create, Update, RefreshDetails, Rates, RateSave, RateDelete, Routes; trả nguyên LogisticsApiResult; gắn `[CheckPermission(PermissionCodes.Logistics_KhachHang)]`. |
| `Backend/Business/ApiClients/Logistics/LogisticsCustomerClient.cs` | — | Client có kiểu `ILogisticsCustomerClient` gọi API Vận tải qua ILogisticsApiClient; thân gửi đi dựng rõ từng khoá snake_case; dòng giá gửi null rõ ràng để xoá giá thuê / ngày áp dụng. |
| `Backend/Business/ApiClients/Logistics/Contracts/Customers/LogisticsCustomerContracts.cs` | — | Contract: quyền + danh sách chọn, hồ sơ khách, công nợ gọn, trang tìm khách, kết quả cập nhật, dòng giá (có Current), tuyến, các yêu cầu từ trình duyệt. |
| `Backend/Business/ApiClients/Logistics/LogisticsSnakeCaseNamingPolicy.cs` | — | Đổi tên thuộc tính PascalCase ↔ snake_case (ObjId ↔ obj_id, TaxId ↔ tax_id) — .NET 6 chưa có sẵn. |
| `Backend/Views/Modules/Logistics/KhachHang.cshtml` | — | Trang Razor: đầu trang + hai cột + hộp chọn khách + một hộp form dùng chung (thêm khách / sửa phần vận tải / dòng giá). Nhãn dùng lớp Bootstrap 5.1 (`bg-light text-dark`…). |
| `Backend/wwwroot/ViewAssets/scripts/modules/logistics/khach-hang.js` | — | JS hàm phẳng theo chuẩn tài liệu 02: dùng AppApi, showErr/showSuccess, showActionConfirm, dxDataGrid/dxForm. |
| `Backend/wwwroot/ViewAssets/styles/modules/logistics/khach-hang.css` | — | CSS gói trong `.lg-kh`, hai cột vừa màn hình, màn hẹp xếp một cột. |
| (EPL_LAO_REAL) `tools/chuyen_csharp/khoa_dich_web_rieng.json` | — | 21 câu chỉ màn Web có (khoá `LOG_W_…`, vi / lo / en). |

### Tệp sửa

| Tệp | Dòng | Đổi gì |
|---|---|---|
| `Backend/Business/ApiClients/Logistics/LogisticsApiClient.cs` | 31–38 | Đọc / gửi JSON bằng LogisticsSnakeCaseNamingPolicy. |
| | 83, 105, 115, 125 | Câu lỗi người dùng thấy đổi sang «máy chủ Vận tải». |
| `Backend/Business/ApiClients/Logistics/Endpoints/LogisticsEndpoint.cs` | 15–45 | Đường API khách hàng: customers/quyen, customers, customers/{0}, customers-cong-no, customers/gls, customers/gls/{0}, customers/dong-bo-gls, customers/{0}/bang-gia, bang-gia/{0}, routes. |
| `Backend/Business/Register.cs` | 66 | Đăng ký `ILogisticsCustomerClient`. |
| `Backend.Common/PermissionCodes.cs` | 389–394 | Mã quyền `Logistics_KhachHang = "Logistics.KhachHang"`. |
| `Backend/Base/Localization/vi.json, lo.json, en.json` | vi 3704, 3736, 3737 | Bỏ chữ «trang điều xe» / «danh mục khách hàng chung»: mô tả menu Bút toán từ Logistics, mô tả menu Tài khoản, câu trang chờ. |
| `Backend/Base/Localization/logistics.vi.json, .lo.json, .en.json` | — | Sinh lại: 3059 khoá (thêm 21 khoá LOG_W_…). |

### Cách kiểm (đã làm 08/10):

1. Build Web: 0 cảnh báo, 0 lỗi. Đọc dữ liệu thật của máy thử 8011 vào contract C# (chương trình kiểm tạm): mọi trường khớp (quyền, 3 khách, công nợ, tìm khách, bảng giá có Current, 8 tuyến).
2. Web `https://localhost:5014` → menu Vận tải → Khách hàng: danh sách 3 khách, ຄຳຕຸ້ຍ còn nợ 112.720.300 LAK; chọn khách → chi tiết + bảng giá, nhãn «Đang áp dụng»; «Sửa thông tin khách» mở đúng khách; «Sửa phần vận tải» lưu được; «Chọn từ danh mục khách hàng chung» tìm và thêm được; bảng giá thêm / sửa / xoá.
3. Đổi ngôn ngữ ລາວ / English → chữ đổi theo; trên màn không còn chữ «danh mục khách hàng chung».
4. `python kiem/thu_khach_gls.py` → 36/36.

**Ghi chú:** Còn 27 câu cũ trong từ điển trang điều xe ghi "trang điều xe" / "anh Tune" (phần lớn màn Quy trình) — sửa khi chuyển từng màn (Việc 13, 18).

### Phần 2b — Tab Hợp đồng, Công nợ, Chuyến & phiếu

- **Thông tin chung:** ngày 08/10/2026; repo GLS-QLSX-Web (nhánh feat/hontunedhai_Laos) + EPL_LAO_REAL; đã duyệt 08/10.
- **Chi tiết khách** có thanh tab Bảng giá · Hợp đồng · Công nợ · Chuyến & phiếu, tab hiện theo quyền API trả; nội dung tab nạp khi mở tab, đổi khách thì tab đang mở nạp lại. 
- **Tab Hợp đồng** là khối dùng chung (partial + JS riêng) — Việc 10 (chủ xe liên kết, kind thue_xe) gắn lại. 
  - **Hợp đồng:** số, ngày ký, hiệu lực, trạng thái (Còn hạn / Sắp hết hạn – còn n ngày / Hết hạn / Chưa áp dụng / Ngưng dùng — API tính), số chuyến, bản scan (ảnh / PDF ≤ 10 MB, chỉ vai thấy tiền bán mở được); xoá bản scan trong hộp sửa bằng bấm hai lần (không mở hộp xác nhận chồng hộp).
- **Công nợ** (chỉ xem): tổng nợ, đã thu, quá hạn, tuổi nợ + bảng SO với tình trạng Đã thu đủ / Chưa đến hạn / Quá hạn n ngày / Không có hạn trả — API tính (màn cũ tính trên trình duyệt); lỗi đọc công nợ hiện ngay trong tab.
- **Chuyến & phiếu:** chọn tháng; tháng trống thì API tự lấy tháng gần nhất có phiếu và ghi rõ; cột đơn giá / thành tiền / SO · thu tiền chỉ hiện với vai thấy tiền bán; «Cộng tháng» (số phiếu, tấn, doanh thu theo từng tiền) do API cộng.

#### Bảng Tệp mới

| Tệp | | Nội dung |
|---|---|---|
| `Backend/Views/Modules/Logistics/Partials/_ContractPanel.cshtml` | — | Khối Hợp đồng: thanh nút + lưới + hộp sửa (form + danh sách bản scan + ô chọn tệp). |
| `Backend/wwwroot/ViewAssets/scripts/modules/logistics/contract-panel.js` | — | `initContractPanel({kind, canEdit, canViewFiles})`, `loadContractPanel(partnerId, partnerName)`; lưu hợp đồng rồi tải từng tệp đã chọn; hộp sửa chuyển ra body. |
| `Backend/Controllers/Modules/Logistics/LogisticsHaulageContractController.cs` | — | BFF `Logistics/Contracts/` List, Save, Delete, UploadFile (multipart, ≤ 10 MB), DeleteFile, File (mở bản scan inline, tên tệp Lào / Việt qua filename*). |
| `Backend/Business/ApiClients/Logistics/LogisticsHaulageContractClient.cs` | — | Client có kiểu, kind khach → customer_id, thue_xe → owner_id; ngày trống gửi null rõ ràng. |
| `Backend/Business/ApiClients/Logistics/Contracts/HaulageContracts/LogisticsHaulageContractContracts.cs` | — | Contract hợp đồng, bản scan, yêu cầu lưu, yêu cầu tải tệp. |
| `Backend/Business/ApiClients/Logistics/Contracts/LogisticsFileResult.cs` | — | Kết quả đọc tệp (nội dung, kiểu, tên). |

#### Bảng Tệp sửa

| Tệp | Dòng | Đổi gì |
|---|---|---|
| `Backend/Business/ApiClients/Logistics/LogisticsApiClient.cs` | 26–30, 69–133 | Thêm `SendFileAsync` (multipart) và `GetFileAsync` (đọc tệp); gom phần gửi chung vào `SendRawAsync`; thân là HttpContent thì gửi nguyên. |
| `Backend/Business/ApiClients/Logistics/Endpoints/LogisticsEndpoint.cs` | 48–65 | `customers/{0}/chuyen`, `customers/{0}/cong-no-ke-toan`, `hop-dong`, `hop-dong/{0}`, `hop-dong/{0}/tep`, `hop-dong-tep/{0}`. |
| `Backend/Business/ApiClients/Logistics/Contracts/Customers/LogisticsCustomerContracts.cs` | 20–27, 154–240 | Quyền hợp đồng (ViewContracts, EditContracts, ViewContractFiles); contract tab Chuyến (tháng, dòng phiếu, cộng tháng) và tab Công nợ (tổng, tuổi nợ, dòng SO có TinhTrang). |
| `Backend/Business/ApiClients/Logistics/LogisticsCustomerClient.cs` | 27–28, 114–125 | `GetTripsAsync`, `GetDebtDetailAsync`. |
| `Backend/Controllers/Modules/Logistics/LogisticsCustomerController.cs` | 79–85 | `GET Logistics/Customers/Trips`, `GET Logistics/Customers/DebtDetail`. |
| `Backend/Business/Register.cs` | 67 | Đăng ký `ILogisticsHaulageContractClient`. |
| `Backend/Views/Modules/Logistics/KhachHang.cshtml` | 71–125, 167 | Thanh tab + 4 ô tab (Bảng giá, Hợp đồng gắn partial, Công nợ, Chuyến & phiếu); nạp contract-panel.js trước khach-hang.js. |
| `Backend/wwwroot/ViewAssets/scripts/modules/logistics/khach-hang.js` | 25, 242–410 | Bảng nhãn trạng thái SO; `showCustomerTab`, `initDebtGrid` / `loadDebt`, `initTripTab` / `loadTrips`. |
| `Backend/wwwroot/ViewAssets/styles/modules/logistics/khach-hang.css` | 134–250 | Kiểu tab, ô số công nợ, dòng cộng tháng, khối Hợp đồng. |
| `Backend/Base/Localization/logistics.*.json` | — | Sinh lại: 3073 khoá. |
| (EPL_LAO_REAL) `backend/app/routes/danh_muc.py` | 145–160 | `GET /api/customers/quyen` thêm view_contracts, edit_contracts, view_contract_files (theo luật routes/hop_dong.py). |
| | 336–348 | `GET /api/customers/{id}/cong-no-ke-toan`: thêm `tinh_trang` (da_thu_du · chua_den_han · qua_han · khong_han) và `qua_han_ngay` cho từng SO. |
| | 393–455 | Mới `_thang_gan` + `GET /api/customers/{id}/chuyen?thang=&tu_tim=`: phiếu của khách trong tháng (≤ 500), tự tìm tháng gần nhất có phiếu, cộng tháng; tiền bán chỉ có với vai thấy tiền. |
| (EPL_LAO_REAL) `backend/app/services/tep.py` | 23–26 | Mới `ten_tep()`: giữ chữ Lào (U+0E80–U+0EFF) và dấu tiếng Việt trong tên tệp tải lên (trước đây "ສັນຍາ" thành "ສ_ນຍາ"). |
| (EPL_LAO_REAL) `backend/app/routes/hop_dong.py` | 232 | Tải bản scan dùng `ten_tep()`; bỏ `import re` không còn dùng. |
| (EPL_LAO_REAL) `tools/chuyen_csharp/khoa_dich_web_rieng.json` | — | Thêm 14 câu tab Công nợ / Hợp đồng (vi / lo / en). |
| (EPL_LAO_REAL) `kiem/thu_khach_gls.py` | 242 | Mục «7. tab Chuyến & phiếu, tab Công nợ, quyền hợp đồng»; tổng 45 bước. |

#### Cách kiểm

1. `python kiem/thu_khach_gls.py` → 45/45; `kiem/thu_hop_dong_pod.py` (máy thử 8011) → 37 bước qua.
2. Chương trình kiểm C# (đọc dữ liệu thật máy thử 8011 vào contract Web) → 17/17: mọi khoá API trả đều có thuộc tính C# tương ứng (7 contract); tab Chuyến tự sang tháng 10/2026 (12 phiếu, 485,6 t, 7.872,3 USD); công nợ 8 SO có tình trạng; vòng hợp đồng thử tạo → tải ảnh tên tiếng Lào → mở lại đúng → xoá tệp → sửa ngày hết hạn ra «sắp hết hạn» → xoá hợp đồng.
3. Web `https://localhost:5014/Logistics/khach-hang` → chọn ຄຳຕຸ້ຍ → 4 tab; Hợp đồng thêm / đính kèm / mở / sửa / xoá; Công nợ thấy «Quá hạn n ngày»; Chuyến đổi tháng, «Cộng tháng» khớp bảng.

**Ghi chú cuối tiểu mục:** «Lỗi giữa chừng (anh Hải thấy lúc kiểm): thiếu 3 thuộc tính quyền hợp đồng ở contract C# nên tab Hợp đồng bị ẩn — đã thêm, và chương trình kiểm nay so từng khoá API với thuộc tính C#. Ba chỗ tải tệp khác (ảnh xe / tài xế `routes/anh.py`, giấy giao nhận `routes/giao_nhan.py`, tệp đính kèm DO `routes/phieu.py`) còn lỗi tên tiếng Lào — đổi sang `ten_tep()` khi chuyển các màn đó.»

---

## Việc 8 — Chuyển đa ngôn ngữ vi / lo / en

- **Ngày:** 08/10/2026
- **Repo / nhánh:** `GLS-QLSX-Web` nhánh `feat/hontunedhai_Laos`, `EPL_LAO_REAL` (bộ sinh)
- **Trạng thái:** Đã duyệt 08/10/2026. **Chưa commit.**
- **Chốt của anh Hải:** khoá dịch Vận tải để ở **tệp riêng**, không gộp vào `vi/lo/en.json` chung — các trang Web khác không nặng thêm (gộp chung thì mọi trang nặng thêm ~50%, ≈ +100 KB nén mỗi lần mở).
- **Cách làm:** 3.038 khoá của trang điều xe (`frontend/js/ngon_ngu.js`) → `Base/Localization/logistics.{vi,lo,en}.json`. Khoá Web = `LOG_` + khoá cũ viết HOA (`nav_dash` → `LOG_NAV_DASH`, `tk_gls` → `LOG_TK_GLS`); thiếu lo / en thì lấy vi; chỗ thay số giữ dạng `{tên}` (Web dùng cùng dạng). `AppLocalizer` đọc thêm tệp module (khoá phải bắt đầu `LOG_`, không đè khoá chung) → Razor dùng `Helper.Trans("LOG_…")` như mọi khoá; `_Layout` chỉ đẩy khoá `LOG_` xuống trình duyệt ở trang `/Logistics/…`. Chế độ song ngữ «VI + ລາວ» của trang điều xe không mang sang (Web chỉ có vi / lo / en).

### Tệp mới

| Tệp | Nội dung |
|---|---|
| `GLS-QLSX-Web/Backend/Base/Localization/logistics.vi.json` | 3.038 khoá `LOG_*` tiếng Việt (xếp theo khoá). |
| `GLS-QLSX-Web/Backend/Base/Localization/logistics.lo.json` | 3.038 khoá tiếng Lào. |
| `GLS-QLSX-Web/Backend/Base/Localization/logistics.en.json` | 3.038 khoá tiếng Anh. |
| `EPL_LAO_REAL/tools/chuyen_csharp/sinh_khoa_dich_web.py` | Bộ sinh 3 tệp trên từ `ngon_ngu.js` (ghi đè toàn bộ, báo nếu trùng khoá sau khi đổi tên). Chạy lại mỗi khi từ điển trang điều xe đổi. |

### Tệp sửa

| Tệp | Dòng | Đổi gì |
|---|---|---|
| `GLS-QLSX-Web/Backend.Common/Localization/AppLocalizer.cs` | 15–16 | `LogisticsPrefix = "LOG_"`; danh sách từ điển module `ModuleDictionaries` (`logistics` → `LOG_`). |
| | 50–74 | `GetResources(culture, modulePrefix)`: thêm tham số; mặc định bỏ khoá của mọi module, chỉ giữ khoá module đúng `modulePrefix`. |
| | 99, 109–129 | `LoadLanguageDictionary` gọi `MergeModuleDictionaries`: đọc `Base/Localization/<module>.<ngôn ngữ>.json`, chỉ nhận khoá đúng tiền tố, `TryAdd` (không đè khoá chung); tệp hỏng thì bỏ qua. |
| `GLS-QLSX-Web/Backend/Views/Shared/_Layout.cshtml` | 25–27 | `i18nModulePrefix` = `LOG_` khi đường bắt đầu `/Logistics`, truyền vào cả hai lần `GetResources` (ngôn ngữ đang chọn + tiếng Việt). |

Tệp `Base\Localization\*.json` đã có sẵn luật chép ra thư mục chạy (`Backend.csproj`, `PreserveNewest`) — không phải sửa csproj.

### Cách kiểm

1. Đăng nhập Web → mở `/Logistics/tong-quan` → F12 Console: `Object.keys(window.__qlsxI18nResources).filter(k => k.startsWith('LOG_')).length` → **3038**; `AppI18n.t('LOG_NAV_DASH')` → «Tổng quan» (tiếng Lào: «ພາບລວມ»).
2. Mở trang khác (vd `/Warehouse/DocumentList`) → cùng lệnh → **0**.
3. Web build 0 lỗi · 0 cảnh báo; 3 tệp `logistics.*.json` có trong thư mục chạy.

---

## Việc 7 — Menu Vận tải trên Web GLS

- **Ngày:** 08/10/2026
- **Repo / nhánh:** `GLS-QLSX-Web` nhánh `feat/hontunedhai_Laos`, `GLS-QLSX-APIs` nhánh `feat/HonTunedaHai` (script DB), `EPL_LAO_REAL` (bộ sinh)
- **Trạng thái:** Đã duyệt 08/10/2026. Script menu **đã chạy trên DB demo** 08/10. **Chưa commit.**
- **Chốt của anh Hải:** trang điều xe chỉ còn là API; mọi màn mở trong Web GLS (địa chỉ của Web, không nhảy sang trang khác); menu trông như menu Quản lý kho.
- **Cách làm:** menu «Vận tải» (cấp 1, sau Quản lý kho) → cấp 2 là bảng 2 cột: 4 màn để thẳng (Tổng quan, Phiếu xuất xe, Phiếu của tôi, Xem kho) + 5 nhóm như «Báo cáo kho» (Theo dõi · Đề nghị gửi kế toán · Tất toán · Danh mục · Hệ thống) → 24 màn; mỗi mục một biểu tượng (Font Awesome 6.5) + một dòng mô tả ngắn (vi · lo · en). Mục màn là trang Web `PAGE / SELF`, đường cố định `/Logistics/<màn>` (cùng tên màn với trang điều xe cũ). Màn chưa chuyển sang C# → trang chờ «đang chuyển sang Web GLS» ngay trong Web; màn chuyển xong thì controller riêng khai đúng đường đó và thay trang chờ, menu không phải sửa. Mỗi màn một mã quyền trang `Logistics.<Màn>`; 12 vai `LOGISTICS_*` được quyền đúng các màn vai đó thấy ở trang điều xe (Sếp 24, KT Chi phí 22, KT Thu/Chi 21, Thủ quỹ 21, Quỹ Thà Bốc 21, KT Doanh thu 20, KT xăng dầu 19, Bãi 15, Tổ sửa 4, Thủ kho dầu 2, Kho phụ tùng 2, Tài xế 1).

### Tệp mới

| Tệp | Nội dung |
|---|---|
| `GLS-QLSX-APIs/Backend.API/Database/Scripts/20261008_logistics_menu.sql` | Sinh tự động. `LOGISTICS_ROOT` + 5 nhóm `LOGISTICS_GRP_TRACKING · REQUEST · SETTLE · MASTER · SYSTEM` + 24 mục `LOGISTICS_<MÀN>` (`/Logistics/<màn>`); 24 mã quyền trang `Logistics.<Màn>` (PAGE, gắn MenuId); gán quyền trang cho 12 vai; tắt 2 nhóm của bố cục thử trước (`LOGISTICS_GRP_TRANSPORT`, `LOGISTICS_GRP_WAREHOUSE`); gọi `proc_SysAppVersion_Touch` MENU_VERSION + PERMISSION_VERSION. Chạy lại an toàn, cần chạy `20261008_logistics_role_permissions.sql` trước. |
| `EPL_LAO_REAL/tools/chuyen_csharp/sinh_menu_van_tai.py` | Bộ sinh: đọc `frontend/js/chung.js` (MODULES, quy tắc `thayDuoc` vai nào thấy màn nào) + `frontend/js/ngon_ngu.js` (tên màn vi · lo · en), sinh script SQL trên và khoá dịch Web. Bố cục, biểu tượng, mô tả nằm trong bảng `MAN`, `NHOM`, `CAP2` của tệp. |
| `GLS-QLSX-Web/Backend/Controllers/Modules/Logistics/LogisticsPageController.cs` | `GET /Logistics/{screen}` (dòng 24): 24 tên màn hợp lệ, tên khác → 404; trả trang chờ. Đường chữ cố định của màn đã chuyển sẽ thắng đường có tham số này. |
| `GLS-QLSX-Web/Backend/Views/Modules/Logistics/Pending.cshtml` | Trang chờ: tiêu đề theo khoá `MENU_LOGISTICS_<MÀN>`, câu `LOGISTICS_PAGE_PENDING`. |

### Tệp sửa

| Tệp | Dòng | Đổi gì |
|---|---|---|
| `GLS-QLSX-Web/Backend/Controllers/Modules/Logistics/LogisticsController.cs` | 20, 29 | `[HttpGet("Logistics/Health")]`, `[HttpGet("Logistics/Me")]` — đường chữ cố định để trang chờ `Logistics/{screen}` không bắt nhầm. |
| `GLS-QLSX-Web/Backend/Base/Localization/vi.json` | 3705–3766 | Khoá `MENU_LOGISTICS_ROOT`, `MENU_LOGISTICS_GRP_*` (+ `_DESC`), `MENU_LOGISTICS_<MÀN>` (+ `_DESC`), `LOGISTICS_PAGE_PENDING`. |
| `GLS-QLSX-Web/Backend/Base/Localization/lo.json` | 3212–3273 | Như trên, tiếng Lào. |
| `GLS-QLSX-Web/Backend/Base/Localization/en.json` | 3705–3766 | Như trên, tiếng Anh. |

Ghi chú: bản thử đầu (mục menu mở tab mới sang trang điều xe, có sửa `wwwroot/layout/js/layout-shell.js` để nhận OpenMode NEW_TAB) đã BỎ theo chốt của anh Hải — `layout-shell.js` trả về nguyên như cũ, không đổi.

### Cấu hình / chạy

- `sqlcmd … -f 65001 -i 20261008_logistics_menu.sql` (DB demo đã chạy 08/10).
- Người dùng thấy menu theo vai `LOGISTICS_*` được gán (qua phòng ban) — vai kéo theo cả mã vai (`Logistics.Role.*`, việc 6) và quyền trang.
- Web giữ menu trong phiên: sau khi chạy script, đăng xuất / đăng nhập lại để thấy.

### Cách kiểm

1. Chạy script menu; kết quả in số màn mỗi vai (LOGISTICS_ADMIN 24 … LOGISTICS_DRIVER 1).
2. Gán thử quyền trang cho `tune` (ghi đè quyền người dùng) → đăng xuất / đăng nhập → menu **Vận tải** là bảng 2 cột, đủ biểu tượng và mô tả; mục có dấu › xổ danh sách màn.
3. Bấm một màn → ở lại Web, địa chỉ `localhost:5014/Logistics/<màn>`, trang «Màn này đang được chuyển sang Web GLS…».
4. Đổi ngôn ngữ Lào → nhãn ຂົນສົ່ງ, ຕິດຕາມ, ໃບສະເໜີສົ່ງບັນຊີ…

---

## Việc 6 — Phân quyền theo mã quyền GLS

- **Ngày:** 08/10/2026
- **Repo / nhánh:** `GLS-QLSX-APIs` nhánh `feat/HonTunedaHai` (script DB), `EPL_LAO_REAL` (API Python)
- **Trạng thái:** Đã duyệt 08/10/2026 (gán thử `Logistics.Role.Rev` cho `tune` → `/Logistics/Me` ra `"role":"rev"`, `"nguon_vai":"gls"`; bỏ gán → về vai Sếp). Script quyền **đã chạy trên DB demo** 08/10. **Chưa commit.**
- **Cách làm:** vai điều xe quản lý bằng phân quyền GLS (Sys_Permission / Sys_Role / Sys_RolePermission / Sys_DepartmentRole / Sys_UserPermissionOverride). Trang điều xe đọc mã quyền hiệu lực của người đăng nhập qua `GET api/v1/ui-shell/get` (`Permissions`), lấy vai theo mã `Logistics.Role.*` (`TargetCode` = mã vai EPL). Người chưa có mã nào giữ vai đặt ở màn Tài khoản (chạy song song). Ma trận quyền chi tiết (mục I–VI, thấy tiền) vẫn ở trang điều xe (`services/phan_quyen.py`).

### Tệp mới

| Tệp | Nội dung |
|---|---|
| `GLS-QLSX-APIs/Backend.API/Database/Scripts/20261008_logistics_role_permissions.sql` | (1) `Sys_Module` LOGISTICS «Vận tải»; (2) 12 mã quyền `Logistics.Role.Admin · Acct · ExpAcct · Rev · Treasury · Cash · Fuel · Yard · Repair · Parts · Depot · Driver` (PermissionScope `API`, TargetCode = mã vai EPL); (3) 12 vai `Sys_Role` `LOGISTICS_*`, mỗi vai ALLOW đúng một mã; dòng 76 gọi `proc_SysAppVersion_Touch PERMISSION_VERSION` để bộ nhớ đệm ui-shell làm mới ngay. Không thêm mã mới vào vai `QLSX_LEGACY_MENU_FULL`. Chạy lại an toàn (MERGE). |

### Tệp sửa

| Tệp | Dòng | Đổi gì |
|---|---|---|
| `EPL_LAO_REAL/backend/app/services/dang_nhap_gls.py` | 139–140 | `THU_TU_VAI` (thứ tự ưu tiên: admin, acct, expacct, rev, treasury, cash, fuel, yard, repair, parts, depot, driver), `TIEN_TO_QUYEN = "logistics.role."`. |
| | 144–170 | Mới `vai(token)`: gọi `ui-shell/get`, lấy tập vai từ mã `Logistics.Role.*`, nhớ theo sha256(token) như `xac_thuc`; lỗi → tập rỗng. |
| | 173–179 | Mới `chon_vai(vai_dang_dat, cac_vai_gls)`: không mã → giữ vai; vai đang đặt có trong mã → giữ; không thì vai đầu tiên theo thứ tự. |
| `EPL_LAO_REAL/backend/app/services/bao_mat.py` | 99–111 | Trong `nguoi_tu_token` (đường token GLS): áp vai theo mã GLS cho lượt gọi; `nguon_vai` = gls / epl; vai Tài xế / Thủ kho nhiên liệu mà chưa gắn tài xế / kho → 403 `THIEU_TAI_XE` / `THIEU_KHO`; đổi vai thì `db.expunge(user)` trước — không bao giờ ghi ngược vào bảng users. |
| `EPL_LAO_REAL/backend/app/routes/dang_nhap.py` | 70–73 | `GET /api/toi` trả thêm `nguon_vai`. |
| `GLS-QLSX-APIs/Backend.API/Database/Scripts/20261007_menu_khai_bao_kho.sql` | 38–40 | Thêm `proc_SysAppVersion_Touch MENU_VERSION` sau khi thêm menu — không có thì menu chờ tối đa 20 phút mới hiện (bộ nhớ đệm ui-shell). Script này đã vào `feat/DemoLao` (PR #165) — đây là thay đổi mới. |

### Cấu hình / gán quyền

- Chạy script: `sqlcmd … -f 65001 -i 20261008_logistics_role_permissions.sql` (DB demo đã chạy 08/10).
- Gán vai: Admin GLS gán vai `LOGISTICS_*` cho phòng ban, hoặc gán riêng mã `Logistics.Role.*` cho từng người (ghi đè quyền người dùng).
- Người có vai Tài xế / Thủ kho nhiên liệu vẫn phải gắn tài xế / kho ở màn Tài khoản của trang điều xe.

### Cách kiểm

1. Gán thử mã `Logistics.Role.Rev` cho `tune` (ghi đè quyền người dùng, UserId 846).
2. Web: `/Logistics/Me` → `"role": "rev"`, `"nguon_vai": "gls"`; KT Doanh thu xem được Tổng quan (200), vào danh sách tài khoản bị chặn (403).
3. Bỏ gán → `tune` về `"role": "admin"`, `"nguon_vai": "epl"`.
4. Bài kiểm máy: chọn vai trong tiến trình 10/10 (không mã → giữ; có mã → đúng thứ tự; bảng users không bị ghi; tài xế chưa gắn → 403); đăng nhập GLS thật 12/12.

---

## Việc 4 — Đăng nhập dùng API đăng nhập của GLS

- **Ngày:** 08/10/2026
- **Repo / nhánh:** `EPL_LAO_REAL` (API Python — phần kiểm token phải ở đây vì API vẫn của EPL), `GLS-QLSX-Web` nhánh `feat/hontunedhai_Laos`
- **Trạng thái:** Đã duyệt 08/10/2026. **Chưa commit.**
- **Cách làm:** token GLS kiểm bằng `GET api/v1/auth/info` của API GLS (đúng cách Web GLS tự kiểm phiên), nhớ kết quả 300 giây; tài khoản GLS gắn với tài khoản EPL qua cột `users.gls_username` — vai, tài xế, kho vẫn lấy từ tài khoản EPL. Token EPL cũ vẫn dùng song song.

### Tệp mới

| Tệp | Nội dung |
|---|---|
| `EPL_LAO_REAL/backend/app/services/dang_nhap_gls.py` | `bat()` đọc cờ `EPL_DANG_NHAP_GLS`; `dang_nhap(ten, mat_khau)` gọi `POST api/v2/auth/login` của GLS → token; `xac_thuc(token)` nhận diện JWT, bỏ token hết hạn theo `exp`, gọi `auth/info`, chỉ giữ `user_id, username, full_name, branch_id, object_id` (bỏ mọi trường khoá), nhớ theo sha256(token); địa chỉ GLS lấy `QLSX_BASE_URL`, không có thì lấy từ `EPL_ACC_CODE_API`. Không ghi token vào log. |

### Tệp sửa

| Tệp | Dòng | Đổi gì |
|---|---|---|
| `EPL_LAO_REAL/backend/app/services/bao_mat.py` | 64–69 | Mới `nguoi_dung_gls(db, tt)`: tài khoản EPL có `gls_username` khớp (không phân biệt hoa thường). |
| | 72–74 | `nguoi_hien_tai` đọc header rồi gọi `nguoi_tu_token`. |
| | 77–100 | Mới `nguoi_tu_token(db, token)`: token EPL cũ → như trước; không thì kiểm token GLS → 401 `CHUA_DANG_NHAP` khi sai / hết hạn, 403 `CHUA_GAN_TAI_KHOAN_GLS` khi chưa gắn, 401 `TAI_KHOAN_KHOA` khi tài khoản EPL đã khoá. |
| `EPL_LAO_REAL/backend/app/models.py` | 58 | Cột mới `User.gls_username` (có chỉ mục); tự thêm vào DB lúc khởi động. |
| `EPL_LAO_REAL/backend/app/routes/dang_nhap.py` | 20–28 | Mới `_gan_gls`: gắn / bỏ gắn tài khoản GLS; một tài khoản GLS chỉ gắn một tài khoản EPL → 409 `TRUNG_GLS`. |
| | 41–70 | `POST /api/dang-nhap`: cờ `EPL_DANG_NHAP_GLS=1` → thử tài khoản GLS trước, trả token GLS (`"nguon": "gls"`); GLS từ chối → thử tài khoản EPL cũ (`"nguon": "epl"`); GLS mất mạng mà tài khoản EPL cũng sai → báo không kết nối được GLS. |
| | 106, 125 | Thêm / sửa tài khoản nhận `gls_username`; `xuat_user` trả thêm `gls_username`. |
| `EPL_LAO_REAL/backend/app/routes/anh.py` | 104 | Mở ảnh xe / tài xế bằng `?tk=` nhận cả token GLS (`nguoi_tu_token`). |
| `EPL_LAO_REAL/backend/app/routes/hop_dong.py` | 250 | Mở tệp hợp đồng nhận cả token GLS; bỏ import `User` thừa. |
| `EPL_LAO_REAL/backend/app/routes/phieu.py` | 1936 | Mở tệp đính kèm phiếu nhận cả token GLS. |
| `EPL_LAO_REAL/frontend/modules/tai-khoan/tai-khoan.js` | 22, 124, 142 | Bảng ghi «Tài khoản GLS: …»; hộp Thêm / Sửa có ô «Tài khoản GLS»; gửi `gls_username`. |
| `EPL_LAO_REAL/frontend/js/ngon_ngu.js` | 15185–15194 | Khoá dịch `tk_gls`, `tk_gls_goi_y` (vi · lo · en). |
| `EPL_LAO_REAL/.env.example` | 12–16 | Cờ `EPL_DANG_NHAP_GLS=0` (mặc định tắt), `EPL_GLS_XAC_THUC_GIAY=300`. |
| `GLS-QLSX-Web/Backend/Business/ApiClients/Logistics/Endpoints/LogisticsEndpoint.cs` | 11–13 | `Me = "toi"`. |
| `GLS-QLSX-Web/Backend/Controllers/Modules/Logistics/LogisticsController.cs` | 26–33 | `GET /Logistics/Me`: token GLS của phiên được trang điều xe nhận là tài khoản nào. |

### Cấu hình

```
EPL_DANG_NHAP_GLS=1        # màn đăng nhập trang điều xe dùng tài khoản GLS (mặc định 0)
EPL_GLS_XAC_THUC_GIAY=300  # nhớ kết quả kiểm token GLS (giây)
```

Token GLS gửi từ Web luôn được nhận, không phụ thuộc cờ. Lên host: bật cờ + Admin gắn «Tài khoản GLS» cho từng người dùng (việc 22).

### Cách kiểm

1. Web: đăng nhập `tune` → mở `/Logistics/Me` → `"success": true`, `"username": "admin"`, `"role": "admin"`, `"gls_username": "tune"` (DB thử đã gắn tune → admin).
2. Trang điều xe (cửa sổ ẩn danh): đăng nhập bằng tên + mật khẩu GLS của `tune` → vào vai Sếp; tài khoản EPL cũ (`ketoan` / `1234`) vẫn vào được; sai mật khẩu → báo sai.
3. Màn Tài khoản: dòng `admin` ghi «Tài khoản GLS: tune»; gắn `tune` cho người thứ hai → báo «đã gắn với một tài khoản khác».
4. Bài kiểm máy: 12/12 ca đăng nhập GLS; 23 bài trong tiến trình và 24 màn giao diện đạt.

---

## Việc 5 — Khung module Vận tải + client gọi API Python

- **Ngày:** 08/10/2026
- **Repo / nhánh:** `GLS-QLSX-Web`, nhánh `feat/hontunedhai_Laos`
- **Trạng thái:** Đã duyệt 08/10/2026 (anh Hải mở /Logistics/Health ra "success": true, Web gọi thông API Python máy thử). Build 0 lỗi · 0 cảnh báo. **Chưa commit.**
- **Không đổi:** `GLS-QLSX-APIs`, `EPL_LAO_REAL`.

### Tệp mới

| Tệp | Nội dung |
|---|---|
| `GLS-QLSX-Web/Backend/Business/ApiClients/Logistics/LogisticsOptions.cs` | Lớp `LogisticsOptions` đọc mục `"Logistics"` trong appsettings: `BaseUrl` (gốc API trang điều xe, kết thúc bằng `/api/`), `TimeoutSeconds` (mặc định 30). Hằng `SectionName = "Logistics"`. |
| `GLS-QLSX-Web/Backend/Business/ApiClients/Logistics/LogisticsApiClient.cs` | Interface `ILogisticsApiClient` (`GetAsync<T>`, `SendAsync<T>`) và lớp `LogisticsApiClient : ApiServiceBase`. Chi tiết ở bảng dưới. |
| `GLS-QLSX-Web/Backend/Business/ApiClients/Logistics/Endpoints/LogisticsEndpoint.cs` | Danh sách đường API trang điều xe, tương đối với `BaseUrl`. Hiện có `Health = "suc-khoe"`. Thêm dần theo từng màn. |
| `GLS-QLSX-Web/Backend/Business/ApiClients/Logistics/Contracts/LogisticsApiResult.cs` | Kết quả một lời gọi: `Success`, `StatusCode`, `Code` (mã lỗi `ma` của trang điều xe), `Message` (câu lỗi `loi`), `Data`. |
| `GLS-QLSX-Web/Backend/Controllers/Modules/Logistics/LogisticsController.cs` | BFF chung của module Vận tải. `GET /Logistics/Health` gọi `suc-khoe` của trang điều xe, trả nguyên `LogisticsApiResult` dạng JSON. Cần đăng nhập như mọi trang Web (middleware `AuthenticationMiddleware`). |

**`LogisticsApiClient` làm gì:**

| Phần | Cách làm |
|---|---|
| Địa chỉ | Ghép `Logistics:BaseUrl` + đường tương đối + tham số truy vấn (`QueryHelpers.AddQueryString`). Thiếu `BaseUrl` hoặc không phải `http/https` → trả `CHUA_CAU_HINH`, không gọi. |
| Đăng nhập | Gửi kèm token GLS của người đang đăng nhập (lấy từ session qua `ApiServiceBase.Headers`). Không ghi token vào log. |
| Gửi dữ liệu | Thân JSON giữ nguyên tên trường (trang điều xe dùng snake_case), `Accept: application/json`. |
| HttpClient | Tên `"Logistics"`, không theo chuyển hướng, thời gian chờ theo `TimeoutSeconds`. |
| Thành công (2xx) | Đọc JSON thành `T`, không phân biệt hoa thường tên trường. |
| Lỗi trang điều xe trả | Đọc `{"detail": {"ma", "loi"}}` → `Code`, `Message`; `{"detail": "chuỗi"}` → `Message`; `{"detail": [{"msg"}]}` (kiểm dữ liệu) → `Code = DU_LIEU_SAI`. |
| Lỗi khác | 3xx → `CHUYEN_HUONG` (BaseUrl đang bị chuyển hướng); quá giờ → `QUA_GIO`; mất kết nối → `KHONG_GOI_DUOC`; JSON hỏng → `SAI_DANG`. Không ném lỗi lên BFF. |

### Tệp sửa

| Tệp | Dòng | Đổi gì |
|---|---|---|
| `GLS-QLSX-Web/Backend/Business/Register.cs` | 8 | Thêm `using Backend.Business.ApiClients.Logistics;` |
| | 24 | Thêm `using Microsoft.Extensions.Options;` |
| | 56–65 | Khối đăng ký mới: `Configure<LogisticsOptions>(GetSection("Logistics"))`; `AddHttpClient("Logistics")` đặt thời gian chờ theo `TimeoutSeconds`, `AllowAutoRedirect = false`; `AddScoped<ILogisticsApiClient, LogisticsApiClient>()`. |
| `GLS-QLSX-Web/Backend/appsettings.json` | 2–5 | Thêm khối `"Logistics"`: `BaseUrl` để trống (mặc định), `TimeoutSeconds` 30. |
| `GLS-QLSX-Web/Backend/appsettings.laos.json` | 2–5 | Thêm khối `"Logistics"`: `BaseUrl` = `http://senvangsolutions.com:1501/api/` (trang điều xe trên host), `TimeoutSeconds` 30. |
| `GLS-QLSX-Web/Backend/appsettings.laoslocal.json` | 2–5 | Thêm khối `"Logistics"`: `BaseUrl` = `http://127.0.0.1:8011/api/` (máy thử). Tệp này chỉ ở máy dev, không lên git (`.git/info/exclude`). |

### Cấu hình

```json
"Logistics": {
  "BaseUrl": "http://senvangsolutions.com:1501/api/",
  "TimeoutSeconds": 30
}
```

Đổi địa chỉ trang điều xe (vd. lên https) thì chỉ sửa `BaseUrl` trong `appsettings.{Env}.json` của Web; tệp được nạp lại khi đổi.

### Cách kiểm

1. Đăng nhập Web.
2. Mở `/Logistics/Health` → phải ra `"Success": true`, `"Data": { "ok": true, "db": "…" }`. Gõ đúng địa chỉ, không có dấu chấm ở cuối (`/Logistics/Health.` ra 404).
3. Chưa đăng nhập mà mở `/Logistics/Health` → chuyển về `/Auth/Login` (đúng).
