# Bàn giao cho anh Tune — trang điều xe EPL Lào ↔ hệ kế toán QLSX

Bản chính thức, ngày **02/10/2026**. Bên soạn: trang điều xe **EPL_LAO_REAL** (logistics). Người đọc: **anh Tune**.

**Mốc source đã chốt** (luồng hai bên đã xong trên máy, không còn gì đang sửa):

| Repo | Nhánh | Tách từ | HEAD | Số commit bên em |
|---|---|---|---|---|
| `GLS-QLSX-APIs` (API của anh) | `feat/HonTunedaHai` | `31c98db` | **`a8c7014`** | 17 |
| `GLS-QLSX-Web` (WEB của anh) | `feat/hontunedhai_Laos` | `de04913f` | **`6abe0ad8`** | 8 |
| `EPL_LAO_REAL` (trang điều xe) | `main` | — | **`2ac74de`** | mục 3 |
| `EPL_KETOAN` (kho tạm) | `main` | — | **`a1a5955`** | mục 3.4 |

Mọi thứ dưới đây chạy thật trên **API và WEB của anh chạy ở máy em** (`http://127.0.0.1:5090`, `Env=laos`), trỏ **DB demo Lào anh sao lưu sáng 01/10**. Host `demo-lao-api.goldensme.com` **chưa có** code hai nhánh, chưa áp script nào (mục 4).

Tài liệu kèm (đọc khi cần chi tiết):

- `NOI_API_ANH_TUNE` — bản đồ từng đường, gói mẫu, từng commit đổi gì / DB ghi gì / nằm ở bước nào;
- `HOP_DONG_API_KE_TOAN_ANH_TUNE` — từng trường của gói;
- `HUONG_DAN_TRIEN_KHAI_ANH_TUNE` — lệnh triển khai từng bước;
- `KICH_BAN_A_Z_EPL_TUNE` — kịch bản thử 27 bước hai hệ;
- `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md` mục 12, 16 — hiện trạng phía anh (16.9 bút toán, 16.11 huỷ thu nợ).

**Ranh giới tiền (chủ dự án chốt 01/10):** mọi việc tiền chỉ ở hệ anh. Trang kế toán tạm `EPL_KETOAN` bỏ phần tiền (số ở đó là số thử), chỉ còn là **kho tạm** tới khi nối hệ kho anh Toàn. **Cắt sổ 01/10:** mọi DO đã khoá gửi SO từ đầu. Khoản **đi qua tiền** → phiếu chi / thu bên anh (thủ quỹ bên anh chi, ghi sổ). Khoản **không qua tiền** → **bút toán tổng hợp** bên anh.

**Token:** trang điều xe dùng token của anh (`EPL_ACC_CODE_TOKEN`, tài khoản `tune`, UserId 846, hết hạn khoảng 10/10/2026). Không có token, mật khẩu, chuỗi kết nối nào trong tài liệu này.

---

## 1. Hai bên trao đổi gì

Quy ước cột: **ST** = `ST_AUTOID` (1 chưa ghi sổ · 13 ghi sổ tạm · 12 ghi sổ chính thức). **LAO** = trang điều xe. Đối tượng bên anh do LAO tạo: khách `EPLKH-`, chủ xe `EPLCX-`, nhà cung cấp `EPLNCC-`, tài xế `EPLTX-`.

### 1.1. Mình gửi anh (LAO gọi API của anh, có ghi)

| Việc nghiệp vụ | Đường API | Ai bấm · lúc nào | Gói chính | Bên anh ghi vào | Chống trùng | Lỗi thường gặp |
|---|---|---|---|---|---|---|
| **Mở mã con tài khoản** 1371 / 4021 / 4022 (một lần mỗi DB) | `POST /api/v1/accounting/lao-accounts` · `POST …/lao-accounts/update` | bên em chạy `tools/mo_ma_con_tune.py [gốc API]` lúc triển khai | `Code, ParentCode, Name, Posting, …, Version` | `proc_LaoAccounts_CRUD` → `PUBACCOUNTCOUNTRY` (quốc gia 11); 137, 402 thành tài khoản tổng hợp | mã đã có thì bỏ qua | 503 `LAO_ACCOUNTS_WRITE_NOT_CONFIGURED` (thiếu `LaoAccountsWrite`) · 403 `…_FORBIDDEN` · HTTP 200 `Code` 400 (lỗi thủ tục 53200–53220) |
| **Đối tượng** (tìm, chưa có thì tạo) | `POST /api/v1/master-data/{customers · suppliers · staff}/list` · `…/upsert` | máy LAO tự gọi ngay trước khi gửi SO / phiếu | `ObjectNo` (`EPLKH-<mã>`…), `ObjectName`, `CountryAutoId` 11, `ObjectOfOrganization` 1368, `IsOrganization` | `sp_Meta_Insert_Update_PUBOBJECT` → `PUBOBJECT` | tìm theo `ObjectNo` trước; LAO nhớ ở bảng `doi_tuong_tune` | 500 `OBJ_ISORG` NULL (đã sửa `be123e9`) |
| **SO + công nợ khách** | `POST /api/v1/integrations/logistics/sales-orders` | KT Thu/Chi VC (`acct`) hoặc Sếp · **Phiếu đề nghị thu** → *Tạo SO bên kế toán*, sau khi DO đã về và đã khoá | `schemaVersion 1`, `header` (do_id `EPLLAO-<Trip.id>`, `customer_id`, tuyến, tiền, POD), `details` một dòng thu | `sp_Logistics_CreateSalesOrder`: `TicketOrder` (đơn trạng thái 5), `RESTICKET*`, `RESCUSTOMERSDEBT` (nợ), `PUBITEMS` mặt hàng `mã khách_mã tuyến`, `LogisticsPushOrder` | `Idempotency-Key: logistics:EPLLAO-<Trip.id>` + `do_id` duy nhất | 401 / 403 thân rỗng (token / `LogisticsSalesPush.AllowedUserIds`) · 409 trùng DO · 422 `52905` khách chưa có · 503 `LOGISTICS_CONFIG_REQUIRED` |
| **Tạm ứng** chuyến | `POST /api/v1/accounting/cmpayment-receipt/save-and-commit` (CMP, DOTY **59** "Chi trước", `PostMode None`) | KT Chi phí VC ghi sổ mục IV trên LAO | `Header` (đơn vị 1368, kỳ, đối tượng, `RefDocumentNo` = số PTU), một dòng `Entries` | `PUBDOCUMENT` + `CMPAYMENT` + `PUBENTRY`, ST 1 → thủ quỹ bên anh ghi sổ → 12 / 13 | `POST …/list` theo đối tượng + `DOC_REFDOCUMENTNO` = số PTU | tài khoản không hợp lệ theo quốc gia · kỳ đóng · HTTP 200 `Success:false` · phiếu bị xoá tay → LAO `PHIEU_CHI_MAT` |
| **Chi mục V – VI** (quỹ trả ngay) | `save-and-commit` (CMP, DOTY **60** "Chi khác") | KT Chi phí VC ghi sổ mục V / VI | xe nhà Nợ 614 · 625 / Có 1011; xe thuê Nợ 4022 / Có 1011 | như trên | như trên, số tham chiếu `PCSC-…` | như trên |
| **Trả chủ xe liên kết** (đã trừ hàng mua ở quầy) | `save-and-commit` (CMP 60) | KT Thu/Chi VC · màn **Xe liên kết** → *Trả qua kế toán* | mỗi phiếu xe một dòng Nợ 4022 / Có 1011 · 1012 · 1021 · 1022, tỷ giá riêng từng dòng | như trên | số tham chiếu `TCX-…` | như trên |
| **Tất toán tài xế** (chênh) | `save-and-commit`: chi bù CMP 60 · thu hoàn CMR **17** "Thu khác" | KT Chi phí VC chốt kỳ ở màn **Tất toán tài xế** | Nợ 1601 / Có tiền · Nợ tiền / Có 1601, đứng tên `EPLTX-` | `PUBDOCUMENT` + `CMPAYMENT` / `CMRECEIPT` + `PUBENTRY`, ST 1 | số tham chiếu `TTX-<kỳ>-…` | như trên |
| **Trả nhà cung cấp** | `save-and-commit` (CMP 60) | KT Chi phí · màn **Nhà cung cấp** → *Trả qua kế toán* | Nợ 4021 / Có tiền, đứng tên `EPLNCC-` | như trên | số tham chiếu `TNCC-…` | như trên |
| **Rút phiếu chưa ghi sổ** | `POST …/cmpayment-receipt/delete` | máy LAO, khi số đổi / huỷ đề nghị / xoá phiếu | `DocumentId`, `VoucherType` | `SP_CMP_DELETECMP_CMPAYMENT` / `SP_CMR_DELETEMCMR_CMRECEIPT` | — | 409 `CASH_VOUCHER_DELETE_REFUSED` khi thủ tục legacy từ chối (`a8c7014`; trước đó báo thành công giả) |
| **Bút toán tổng hợp** (không qua tiền) — 6 nguồn: thuê xe `thue_xe` 621/4022 · nợ NCC `no_ncc` 625 · 614 / 4021 · tất toán `tat_toan` 625/1601 · bán chủ xe ở quầy `ban_chu_xe` 4022/707 · xuất kho nội bộ xe nhà `xuat_noi_bo` 625 · 614 / 1371 · xuất bán xe thuê `xuat_ban` 4022/707 + 607/1371 | `POST /api/v1/integrations/logistics/journal-entries` | máy LAO tự gửi khi **khoá phiếu** (thue_xe, no_ncc, xuất kho), **chốt tất toán** (tat_toan), thấy phiếu trả chủ xe **đã ghi sổ** (ban_chu_xe); nút *Gửi / Gửi hết* ở màn **Bút toán chờ gửi** | `DocumentDate`, `Description`, `FiciAutoId?`, `Entries[]` (Nợ, Có, `Amount`, `ExchangeRate`, `CurrencyId`, `ObjectId?`, `Note`); máy chủ tự tính `BaseAmount` | `proc_Logistics_JournalEntry_Save`: `PUBDOCUMENT` (hệ 6 / phân hệ 38, `DOC_REFDOCUMENTNO` = SourceRef) → `GLBUSINESS` **DOTY 12** → `PUBENTRY` → `sp_PostTing_GeneralLedger` **ST 13** | `Idempotency-Key` = SourceRef `EPLLAO-<nguồn>-<mã nguồn>[-phiên]`; gửi lại cùng nội dung → 200 `IsExisting` | 400 `INVALID_ACCOUNTS` · 409 `52512` cùng SourceRef khác số (LAO tự gỡ rồi gửi lại) · 403 `…_FORBIDDEN` · 503 `…_DISABLED` / `_SCRIPT_REQUIRED` |
| **Gỡ bút toán** (mở khoá / xoá phiếu, bỏ chốt) | `POST …/journal-entries/reverse` · hỏi lại `GET …/journal-entries/{SourceRef}` | máy LAO tự gửi | `{SourceRef}` | `proc_Logistics_JournalEntry_Reverse`: `sp_GL_Delete_GENERALLEDGER` → `sp_GL_Delete_GLBusiness`; dòng `PUBENTRY` sót → `ET_ISACTIVE = 0` | gọi lại an toàn (`Reversed=false` + `DocumentId` null = đã gỡ) | 409 `52515` đã khoá / ghi sổ chính thức ST 12 · `52516` legacy không gỡ được (rollback) |

Mã số LAO dùng (cấu hình `.env`, có mặc định): đơn vị `QLSX_ORG_ID` 1368, quốc gia `QLSX_COUNTRY_ID` 11, DOTY 59 / 60 / 17, tiền LAK 26 (tra `GetAllCurrency`), USD 2 (đang tắt trong danh mục → `QLSX_TIEN_USD=2`), kỳ tra `GetFinancyCicle`.

### 1.2. Anh gửi mình / mình đọc của anh

| Việc nghiệp vụ | Đường | Ai · lúc nào | Gói / thứ đọc | Ghi vào đâu | Chống trùng | Lỗi thường gặp |
|---|---|---|---|---|---|---|
| **Danh mục tài khoản** cho ô chọn mã | `GET /api/v1/common/country-accounts?tryAutoId=11&onlyActive=true` | máy LAO, nhớ 10 phút; hỏng thì dùng bản chụp `danh_muc_tai_khoan_lao.json` | `AccCode`, `AccName`, `AccParentId`, `AccAccountWrite` | không ghi | — | token hết hạn → 401 |
| **Mã số** đơn vị / kỳ / tiền / loại chứng từ | `GET common/GetFinancyCicle` · `GetAllCurrency` · `cmpayment-receipt/document-types` · `default-money-account` | máy LAO, nhớ 10 phút | `FICI_AUTOID`, `CUR_AUTOID`, `DOTY_AUTOID` | không ghi | — | USD đang tắt → không có trong `GetAllCurrency` |
| **Đã chi / đã thu** của phiếu LAO tạo | `GET …/cmpayment-receipt/{id}?voucherType=CMP·CMR` | máy LAO hỏi lại lúc mở tờ, lúc tài xế bấm Xuất phát, khi bấm Cập nhật | `Master.STATUS` 12 / 13 = đã chi / đã thu | LAO: mục IV "đã chi", tờ PTU "đã cấp", phiếu xe "đã trả chủ xe"… | — | `Master` null = phiếu bị xoá tay → `PHIEU_CHI_MAT` |
| **Thu tiền khách** của SO (kế toán bên anh làm) | WEB anh **Chi tiết công nợ khách hàng → Tạo phiếu thu → Xác nhận thu nợ** → `POST /api/v1/sales/debt/collection-upsert` (`DocumentType "TKN"`) | kế toán bên anh, sau khi khách trả | mỗi SO một lần: `AmountCur` (nguyên tệ), tài khoản tiền theo vai; nợ ngoại tệ: vai `*_FOREIGN` + **tỷ giá ngày thu** (máy chủ tính `Amount`, `3d6f330`) | `sp_RES_CreateDebtCollection_COUNTRY`: `RESDOCUMENT` (TKN) + `RESDOCUMENT_TICKET`, `RESCUSTOMERSDEBT` trừ **nguyên tệ**, `PUBDOCUMENT` + `CMRECEIPT` **DOTY 17** + `PUBENTRY` Nợ tiền / Có 1211, ST 1 → thủ quỹ ghi sổ | một TKN ↔ một CMR (`DOC_REFDOCUMENTNO` = số TKN) | 400 `527xx` (vượt dư nợ, khác loại tiền, tài khoản nội tệ + tỷ giá ≠ 1). **Không** thu bằng phiếu "Thu công nợ" CMR 15 (ra 0 dòng) |
| **Đọc lại "đã thu"** | `POST /api/v1/sales/debt/customer-detail` `{CustomerObjectId, OrgId}` | máy LAO khi bấm **Cập nhật** ở Phiếu đề nghị thu; tab Công nợ của khách | dòng nợ theo `OrderCode`: `RETK_PAYMENTAMOUNT`, `RCTD_DEBTMONEY`, `LocalCurrencyCode`, `IsForeignCurrency` | LAO: `chi_tune._da_tra` = tiền − còn nợ (vì `RETK_MONEYPAID` giữ 0 khi thu sau); `de_nghi_thu.ap_thu` → đã thu / thu một phần / chưa thu | mỗi khách một lần / 60 giây | — |
| **Huỷ phiếu thu nợ** (thu sai) | `POST /api/v1/sales/debt/collection-cancel` | kế toán bên anh (chưa có nút WEB — gọi API) | `DocumentNo` (số TKN) hoặc `DocumentId`, `ReceiptDocumentId` (CMR), `Reason` | `sp_RES_CancelDebtCollection_COUNTRY`, một transaction: gỡ sổ CMR → ST 1 → xoá CMR → trả lại `RESCUSTOMERSDEBT` đúng nguyên tệ → vô hiệu `RESDOCUMENT` (`RDO_DELETEBY` / `RDO_DELETEDATE`) | gọi lại → `AlreadyCancelled` | 503 `…_NOT_CONFIGURED` (thiếu `SalesDebtCollectionCancel`) · 409 `52767` kỳ khoá · 422 `52768` tỷ giá ≠ 1 trước bản sửa · `52771` / `52773` hậu kiểm lệch (rollback) |
| **Gỡ ghi sổ phiếu thu / chi** | `POST /api/v1/accounting/cmpayment-receipt/unpost` | kế toán bên anh (màn phiếu); bài thử bên em | `DocumentId`, `VoucherType` | `proc_CM_UnpostCashVoucher` (`a8c7014`): `sp_GL_Delete_GENERALLEDGER`, kiểm chứng từ con đã hết, `CMRECEIPT` / `CMPAYMENT.ST_AUTOID` về **1** | sp_getapplock theo phiếu | 503 `CASH_VOUCHER_UNPOST_SCRIPT_REQUIRED` · 409 kỳ khoá |
| **Đọc DO** đã về + đã khoá (B1 / B2) | API anh gọi LAO: `GET {LogisticsSource:BaseUrl}handover/delivery-orders?q=&page=&page_size=` · `GET …/delivery-orders/{do_id}` | modal **Vụ việc** trên phiếu thu / chi của anh | `Authorization: Bearer <khoá bàn giao>`; danh sách 14 khoá EPL_System + `doc_no`, `customer_name`, `truck_no`…; chi tiết `header` + `details` (dòng thu, dòng chi III – VI kèm `acc_code`) | không ghi; lưu phiếu thì chụp DO (`proc_PP_CashVoucherSourceReference_Save`) | — | 401 `SAI_TOKEN` · 503 `CHUA_DAT_TOKEN` (LAO) · 503 thiếu `LogisticsSource:BaseUrl` · 502 khoá sai (API anh) |
| **Modal Vụ việc** | WEB → BFF → `GET /api/v1/accounting/cash-voucher-references?type=DO&keyword=` · `GET …/{type}/{id}` | thủ quỹ / kế toán bên anh khi gắn chi phí vào DO | `SourceCode` = số phiếu, `SourceName` = tên khách, `SelectionToken` (7200 giây) | snapshot khi lưu phiếu | — | như trên |
| **Màn "Bút toán từ Logistics"** (chỉ đọc) | WEB `/LogisticsJournalEntry/Index` → `GET /api/v1/integrations/logistics/journal-entries?fromDate&toDate&statusId&keyword&pageIndex&pageSize` · `GET …/{sourceRef}` | kế toán bên anh, menu **Phiếu thu chi → Bút toán từ Logistics** | danh sách chứng từ tổng hợp `EPLLAO-…` của đơn vị, tóm tắt theo trạng thái, chi tiết dòng Nợ / Có | không ghi (`proc_Logistics_JournalEntry_List`, `_Get`) | — | 403 `LOGISTICS_JOURNAL_READ_FORBIDDEN` (không thuộc đơn vị) · 503 chưa áp script |

**Không còn** nhóm `/api/lien-thong/*` phần tiền (đã gỡ 01/10): hệ anh không cần gọi sang LAO báo trạng thái tiền; LAO tự hỏi lại. LAO cũng thôi đẩy phong bì `POST /api/v1/epl-lao/vouchers`.

---

## 2. Đã sửa gì trong source anh Tune

Mọi tệp bên em sửa có dòng `Created by / Modified by: EPL Logistics`. Xem lại: `git log --oneline 31c98db..feat/HonTunedaHai` (API), `git log --oneline de04913f..feat/hontunedhai_Laos` (WEB). Hai nhánh **chưa push**.

### 2.1. API `feat/HonTunedaHai` — 17 commit

| Commit | Tệp chính | Đổi gì | Lý do |
|---|---|---|---|
| `465748b` | `Api/V1/CashVoucherReferenceController.cs`; mẫu `logistics-source-config.example.json` | nguồn DO đọc `LogisticsSource` (BaseUrl, ApiKey, theo chi nhánh), gửi `Authorization`; DO hiện số phiếu / tên khách | bỏ địa chỉ ghi cứng EPL_System 1506, không có khoá |
| `be123e9` | `Shared/ObjectManagement/Application/ObjectService.cs` | không gửi `IsOrganization` → `false` | `INSERT PUBOBJECT` văng 500 vì `OBJ_ISORG` không nhận NULL |
| `64ce7a4` | `CashVoucherReferenceController.cs` | tìm DO theo `q` ở phía LAO, `Total` / `HasMore` đúng sau lọc | trước chỉ lọc trong trang đã tải |
| `ce95b3c` | mới `CashVoucherReferenceService`, `LogisticsDeliveryOrderClient`, `CashVoucherHeaderTotals`, `CashVoucherSourceReferenceModels`; sửa `CMPaymentReceiptService`, `AccountingModule` | tách tầng (controller chỉ HTTP / claim / envelope), typed HttpClient; thiếu BaseUrl → 503; **máy chủ tính tổng header** phiếu thu chi | chuẩn QLSX; không tin số trình duyệt |
| `ed5aa0e` | `AuditLog/Filters/ApiAuditAutoLogFilter.cs`, `ApiAuditLogger.cs`, mới `ApiAuditPayloadSanitizer.cs` | bỏ `CancellationToken` khỏi payload; che mật khẩu / token / khoá | hết "Đặt log sai"; đăng nhập từng lưu mật khẩu chữ thường |
| `ae0e7f6` | `CashVoucherHeaderTotals.cs`, `CMPaymentReceiptService.cs` | máy chủ tính quy đổi **từng dòng** `Amount × tỷ giá dòng` trước khi cộng header | trả chủ xe ngoại tệ giữ đúng Kíp từng phiếu xe |
| `e2ef52f` | mới `Database/Scripts/20261001_audit_redact_secrets.sql` | script che bí mật trong dòng audit **cũ** | dòng trước `ed5aa0e` còn mật khẩu |
| `0d4eed9` | `ApiAuditPayloadSanitizer.cs` | che thêm `jwt`, `cookie` | `JWTKey` là token đăng nhập |
| `b9227aa` | mới `LogisticsJournalEntryController / Service / Repository / Models`; script `20261001_logistics_journal_entry.sql`; mẫu `logistics-journal-entry-config.example.json` | **API bút toán tổng hợp**: tạo + ghi sổ tạm, gỡ, đọc lại; idempotent theo SourceRef | khoản không qua tiền chưa có đường nhận |
| `2b4e274` | `LaoAccountsController` → mới `LaoAccountsService` / `LaoAccountsRepository` / `LaoAccountModels`; `LogisticsPushController` → mới `LogisticsPushService` / `ILogisticsPushRepository`; script audit; mẫu `lao-accounts-write-config.example.json` | tách tầng; **cổng quyền ghi danh mục tài khoản** `LaoAccountsWrite`; script audit đủ luật, `@Apply` mặc định 0 | chuẩn QLSX (không `SqlConnection` trong controller); ai cũng sửa được danh mục là rủi ro |
| `c1754d4` | script bút toán | Save / Reverse chỉ đếm chứng từ **có `GLBUSINESS`** | đo DB demo: `sp_PostTing_GeneralLedger` sinh thêm `PUBDOCUMENT` con cùng số, cùng SourceRef → 409 `52511` |
| `3d6f330` | `SalesService.DebtCollection.cs`, `SalesRepository.DebtCollection.cs`, `SalesModels.cs`; script `20261001_sales_debt_collection_currency.sql` | thu nợ: **máy chủ quyết tỷ giá / quy đổi** theo loại tiền khoản nợ; dư nợ trừ theo nguyên tệ; `CMR_ISLOCAL`; diễn giải kèm `OrderCode` | SO USD bị ghi thành Kíp (tỷ giá cứng 1) |
| `66ba289` | `DebtCollectionController`, mới `SalesService.DebtCollectionCancel`, `SalesRepository.DebtCollectionCancel`, `DebtCollectionCancelModels`; script `20261002_sales_debt_collection_cancel.sql`; mẫu `sales-debt-collection-cancel-config.example.json` | **huỷ phiếu thu nợ** TKN cả cụm | xoá riêng CMR thì dư nợ không về lại |
| `95d58bb` | script huỷ | bỏ hậu kiểm ST ngay sau gỡ sổ | đo DB demo: legacy gỡ sổ cái nhưng để nguyên ST → `52771` |
| `97d5a91` | script huỷ | kiểm chứng từ con đã hết, đưa `CMRECEIPT.ST_AUTOID` về 1 rồi mới xoá; đọc mã trả về của thủ tục xoá | thủ tục xoá legacy trả `'2'` (từ chối) khi ST còn 12 → `52773` |
| `6f91fd2` | `LogisticsJournalEntryController / Service / Repository / Models`; `Security/Auth/AuthService.cs`, `AuthRepository.cs` (`GetAssignedBranchIdsAsync`); script `20261002_logistics_journal_entry_list.sql` | `GET journal-entries` (danh sách); cổng đọc theo đơn vị | cho màn WEB "Bút toán từ Logistics" |
| `a8c7014` | `CMPaymentReceiptController / Service / Repository`, mới `CashVoucherUnpostModels.cs`, `ApiLogConst.cs`; script `20261002_cm_unpost_cash_voucher.sql` | **gỡ ghi sổ phiếu thu chi** đưa ST về 1; xoá đọc mã trả về của legacy | unpost cũ để ST 12 / 13, xoá sau đó bị legacy từ chối mà API báo thành công (audit DB demo 01/10: CMP 81331, 81337, 81371, 81435) |

### 2.2. WEB `feat/hontunedhai_Laos` — 8 commit

| Commit | Tệp chính | Đổi gì | Lý do |
|---|---|---|---|
| `f382a9e8` | `ACC/cm-source-reference-modal.js` | thoát ký tự chuỗi DO; hiện số phiếu, xe, tài xế; tỷ giá < 1 đọc xuôi | tên khách có `<` vỡ bố cục / chạy được thẻ |
| `06a14189` | BFF `CMPaymentReceiptController.cs` (chuyển `currencyId`), `cm-payment-upsert.js`, `cm-receipt-upsert.js` | `isCash` theo hình thức thanh toán; tài khoản tiền mặc định đọc đúng `AccountCode`; tổng xem trước; phân loại theo DOTY | tài khoản mặc định chưa bao giờ tự điền; so tên hiển thị sai khi đổi tiếng |
| `7e14421c` | `cm-payment-upsert.js`, `cm-receipt-upsert.js`, `lo.json` | đổi hình thức / nội tệ / loại tiền thì vế tiền dòng mặc định đổi theo; đổi quốc gia chặn trước khi nạp | vế tiền cũ ở lại sai |
| `77bcb0a1` | `cm-payment-upsert.js`, `cm-receipt-upsert.js`, modal, `vi / lo / en.json` | loại phiếu không đổi ngầm: chỉ 58 / 60, 15 / 17 sửa được; **59 "Chi trước" chỉ xem**; chặn XSS | sửa phiếu 59 từng lưu thành 58, mất dòng |
| `fce78c52` | `cm-*-upsert.js`; `OrganizationHrController.cs`, `Employees.cshtml`, mới `employee-account.js` | tiền tệ ngoài danh mục không gán ngầm; tab **Tài khoản** ở hồ sơ nhân viên | USD đang tắt bị thay bằng loại đầu; cần tạo tài khoản tích hợp |
| `7d168744` | mới `Backend.Common/Logging/LogPayloadSanitizer.cs`; `BackofficeApiService.cs`, `AppLoggingHelper.cs`, `ExceptionLoggingMiddleware.cs`, `commonScripts.js` | che bí mật trong log WEB | log từng in `Authorization: Bearer …` |
| `c1a5d231` | BFF `DebtCollectionController.cs`; `debtCollectionCustomerDetail.js`, `debtCollectionWorkspace.js`, `CustomerDetail.cshtml`, `Workspace.cshtml`; `cm-*-list.js`, `cm-*-upsert.js`; `Hr/Employees.cshtml`, `_EmployeeAccountTab.cshtml` | thu nợ ngoại tệ: chỉ tài khoản ngoại tệ, bắt nhập tỷ giá, BFF **bỏ tỷ giá cứng 1**; phiếu mở lại giữ đúng kỳ; hộp xác nhận chung; tab Tài khoản ở `/HR/Employees` | SO USD ghi thành Kíp; kỳ bị đặt lại về hiện tại |
| `6abe0ad8` | mới BFF `LogisticsJournalEntryController.cs`, `LogisticsJournalEntryClient` (+ Endpoint, ClientModels), `LogisticsJournalEntryPageModel`, `Views/…/LogisticsJournalEntry/Index.cshtml`, `modules/accounting/logistics-journal-entry.js / .css`; `Register.cs`; khoá `ACC_LJE_*`, `MENU_LOGISTICS_JOURNAL_ENTRY` | màn **"Bút toán từ Logistics"** (chỉ đọc): lọc, tóm tắt, chi tiết Nợ / Có. Không có nút ghi sổ / gỡ | kế toán cần xem bút toán LAO gửi sang |

### 2.3. Sổ đối tượng DB

Kiểm bằng cách đọc mọi script `Database/Scripts/2026*` bên em thêm trên nhánh (6 tệp). **Không thêm bảng, không thêm cột, không đổi kiểu cột, không đổi chỉ mục.** Bảng `#…` trong script audit và `#Docs` trong thủ tục danh sách là bảng tạm. Script tiền tệ **cần sẵn** cột `CMRECEIPT.CMR_ISLOCAL` (có trên DB demo), không tạo cột.

**Thủ tục mới**

| Thủ tục | Script | DB | Làm gì | Bảng ghi |
|---|---|---|---|---|
| `proc_Logistics_JournalEntry_Save` | `20261001_logistics_journal_entry.sql` | kế toán `CenterConnectionStrings[0]` | tạo chứng từ tổng hợp + ghi sổ tạm, idempotent (`sp_getapplock`) | `PUBDOCUMENT`, `GLBUSINESS`, `PUBENTRY`; gọi `spGetconfigID 6`, `sp_PostTing_GeneralLedger` |
| `proc_Logistics_JournalEntry_Reverse` | như trên | như trên | gỡ sổ + xoá chứng từ, hậu kiểm | gọi `sp_GL_Delete_GENERALLEDGER`, `sp_GL_Delete_GLBusiness`; `PUBENTRY.ET_ISACTIVE = 0` |
| `proc_Logistics_JournalEntry_Get` | như trên | như trên | đọc một chứng từ theo SourceRef | chỉ đọc |
| `proc_Logistics_JournalEntry_List` | `20261002_logistics_journal_entry_list.sql` | như trên | danh sách, phân trang, đếm theo trạng thái | chỉ đọc |
| `sp_RES_CancelDebtCollection_COUNTRY` | `20261002_sales_debt_collection_cancel.sql` | `ConnectionStrings:Master` | huỷ phiếu thu nợ cả cụm | `CMRECEIPT.ST_AUTOID`, `PUBENTRY.ET_ISACTIVE`, `RESCUSTOMERSDEBT`, `RESDOCUMENT` (`RDO_DELETEBY`, `RDO_DELETEDATE`); gọi `sp_GL_Delete_GENERALLEDGER`, `proc_PP_CashVoucherCostAssignment_Delete`, `SP_CMR_DELETEMCMR_CMRECEIPT` |
| `proc_CM_UnpostCashVoucher` | `20261002_cm_unpost_cash_voucher.sql` | kế toán | gỡ ghi sổ phiếu thu / chi | `CMRECEIPT` / `CMPAYMENT.ST_AUTOID` → 1; gọi `sp_GL_Delete_GENERALLEDGER` |

**Thủ tục sửa** (thay bản có sẵn, tham số giữ nguyên)

| Thủ tục | Script | Bản cũ | Đổi |
|---|---|---|---|
| `sp_RES_CreateDebtCollection_COUNTRY` | `20261001_sales_debt_collection_currency.sql` | `20260910_sales_debt_collection_country.sql` (của anh) | kiểm / trừ dư nợ theo **nguyên tệ** `@RDO_AMOUNTCUR`; chặn tài khoản nội tệ + tỷ giá ≠ 1; ghi `CMR_ISLOCAL`; diễn giải kèm `OrderCode`. Vẫn ghi `RESDOCUMENT`, `RESDOCUMENT_TICKET`, `RESCUSTOMERSDEBT`, `PUBDOCUMENT`, `CMRECEIPT` DOTY 17, `PUBENTRY` |

**Script**

| Tệp | Commit | DB | Chạy lại được | DB demo | Host |
|---|---|---|---|---|---|
| `20261001_logistics_journal_entry.sql` | `b9227aa`, `c1754d4` | kế toán | có (chỉ `CREATE OR ALTER`) | **đã áp 02/10** (áp lại bản `c1754d4`) | chưa |
| `20261002_logistics_journal_entry_list.sql` | `6f91fd2` | kế toán | có | **đã áp 02/10** | chưa |
| `20261002_cm_unpost_cash_voucher.sql` | `a8c7014` | kế toán | có | **đã áp 02/10, 01:50** | chưa |
| `20261001_sales_debt_collection_currency.sql` | `3d6f330` | Master | có | **đã áp 02/10** | chưa |
| `20261002_sales_debt_collection_cancel.sql` | `66ba289`, `95d58bb`, `97d5a91` | Master | có | **đã áp 02/10** — ba lần; bản `97d5a91` chạy được | chưa |
| `20261001_audit_redact_secrets.sql` | `e2ef52f`, `2b4e274` | Master | có; `@Apply` mặc định **0** (chỉ chẩn đoán) | **chưa chạy** | chưa |

Mọi script đầu tệp có guard (thiếu nền thì `RAISERROR` + `SET NOEXEC ON`, không tạo gì) và cuối tệp có diagnostics **chỉ đọc** (D1 …). Định nghĩa các thủ tục legacy được gọi (`sp_PostTing_GeneralLedger`, `sp_GL_Delete_*`, `spGetconfigID`, `SP_CMR_DELETEMCMR_CMRECEIPT`…) không có trong repo; script chỉ kiểm tên tham số (D3). Bên em **không sửa** thủ tục legacy nào.

### 2.4. Mục cấu hình `appsettings` (giá trị không bí mật; tệp không đưa lên git; mẫu ở `Database/Scripts/*.example.json`)

| Mục | Khoá | Ý nghĩa | Thiếu thì | API ở máy |
|---|---|---|---|---|
| `LogisticsSource` (mới) | `BaseUrl`, `ApiKey`, `Branches:<BranchId>:BaseUrl / ApiKey` | địa chỉ `/api/` trang điều xe, khoá bàn giao (Sếp LAO tạo) | modal Vụ việc DO 503 | trỏ máy thử 8011 |
| `LogisticsSalesPush` (có sẵn của anh) | `Enabled`, `AllowedUserIds`, `BusinessTypeId`, `AreaId`, `PosId`, `CounterId`, `TableId`, `VndCurrencyId` | cổng nhận SO | 503 `LOGISTICS_CONFIG_REQUIRED` / `_DISABLED` | `AllowedUserIds [846]` |
| `LogisticsJournalEntry` (mới) | `Enabled`, `AllowedUserIds`, `OrgId`, `CountryId` | cổng tạo / gỡ bút toán; đơn vị và quốc gia của chứng từ (không lấy từ gói) | 503 `LOGISTICS_JOURNAL_DISABLED` / `_CONFIG_REQUIRED` | `true`, `[846]`, 1368, 11 |
| `LaoAccountsWrite` (mới) | `AllowedUserIds` | ai được tạo / sửa / xoá danh mục tài khoản Lào (đọc thì ai cũng được) | mọi lệnh ghi 503; WEB ẩn nút | `[846]` |
| `SalesDebtCollectionCancel` (mới) | `AllowedUserIds` | ai được huỷ phiếu thu nợ | 503 `DEBT_COLLECTION_CANCEL_NOT_CONFIGURED` | `[846]` |

Mọi `AllowedUserIds` là claim **UserId** (`dbo.Users.UserID`), không phải ObjectId. Cấu hình đọc lại mỗi request, đổi không cần khởi động lại API. WEB: `BACKOFFICE_API_URL` (`Env=laoslocal` trỏ 5090; `Env=laos` trỏ host).

### 2.5. Dữ liệu bên em đã ghi vào DB demo (qua API ở máy; không sửa thẳng DB, trừ áp script)

| Loại | Cụ thể | Còn / đã gỡ |
|---|---|---|
| Danh mục tài khoản | 137, 402 → tổng hợp; thêm **1371** kho hàng vật tư, **4021** phải trả NCC, **4022** phải trả chủ xe liên kết; quốc gia 11 nay **497** mã | còn (đã có chứng từ dùng 4022, 1371) |
| Đối tượng | khách `EPLKH-0834a9e9606b` ຄຳຕຸ້ຍ (ObjId 1608), chủ xe `EPLCX-0a073ea75bb3` (và ObjId 1606 của phiếu thử bút toán), NCC `EPLNCC-804c0e8ff1d8`, tài xế `EPLTX-a6313dd63966`, tài xế thử `EPLTX-THU01`; nhân viên ảo `EPL-TICHHOP` ObjId 1622 (chưa có tài khoản) | còn, vô hại |
| SO | `TK-20261001-000162` (905,85 USD), `…163` (1.676,90 USD) — công nợ thật trước cắt sổ; `…164` (495 USD), `…165` (753,35 USD) — chuyến thử THU-KBAZ | còn |
| Phiếu chi thử | CMP 59 `1368-CTR-261001-00072`, `…00073`; CMP 60 `1368-CKH-261001-00067` … `00070` (KB-AZ, đã ghi sổ chính); phiếu "Chi trước" của bài `thu_chi_tam_ung_ke_toan.py` (tham chiếu `PTU-THU-CK-…`, đã ghi sổ) | **còn** — giữ làm mẫu, hoặc anh gỡ sổ (`unpost`) rồi xoá |
| Phiếu chi thử khác | `…CTR-261001-00013`, `…00016`, `…CKH-261001-00001`, `…00002`; phiếu chi mục V – VI, tất toán, NCC của các bài thử | đã rút / gỡ sổ + xoá; bài `thu_chi_muc_tune.py` 02/10: ghi sổ chính → **gỡ (`unpost`) → xoá** thành công, DB không còn |
| Thu nợ sai 01/10 | TKN `4-TKN-1368-2-261001-0001` / `-0002` → CMR `4-1368-TK-261001-00009` / `-00010` (DocumentId 81423 / 81424, ST 12, SO USD ghi thành Kíp) | **đã huỷ 02/10** qua `collection-cancel`: CMR xoá, TKN vô hiệu, dư nợ về 495 / 753,35 USD; gọi lần hai `AlreadyCancelled` |
| Thu lại đúng 02/10 | TKN `4-TKN-1368-2-261001-0003` / `-0004` → CMR **`4-1368-TK-261002-00001` / `-00002`**, Nợ **1012** / Có 1211, 495 × 22.000 = 10.890.000 LAK, 753,35 × 22.000 = 16.573.700 LAK | còn, **ST 1 chờ thủ quỹ ghi sổ** |
| Bút toán tổng hợp | `GL021020262` (vòng API) · `263` thuê xe 621/4022 1.200 USD × 22.000 · `264` NCC 4022/4021 · `265` xuất nội bộ 625/1371 · `267` xuất bán 4022/707 + 607/1371 | **đã gỡ sạch**, không còn chứng từ thử |
| Menu WEB | mục **Bút toán từ Logistics** (`LOGISTICS_JOURNAL_ENTRY`, MenuId 154, nhóm `CASH_VOUCHER`, thứ tự 70), thêm qua màn quản trị menu WEB (`/UiShellAdmin/SaveMenu`) | còn; **host phải thêm lại** |
| Nhật ký kiểm toán | mỗi lời gọi API có một dòng audit; dòng trước `ed5aa0e` có thể chứa mật khẩu | chưa che (script audit chưa chạy) |

Trả lại danh mục: xoá 1371 / 4021 / 4022 khi chưa có bút toán, rồi `lao-accounts/update` 137 / 402 với `Posting=true`.

---

## 3. Đã sửa gì trong backend bên mình

### 3.1. Trang điều xe `EPL_LAO_REAL` (01 – 02/10, HEAD `2ac74de`)

| Việc | Commit | Tệp chính | Ghi chú |
|---|---|---|---|
| Gửi SO + khách tự tạo | `efc33de`, `f306a24`, `84053e8`, `5d7a90b` | `services/gui_tune.py`, `routes/de_nghi.py` | Idempotency-Key, luật mã khách của anh, phiếu phải có xe + tài xế |
| Tạm ứng chi ở hệ anh | `41aeae9`, `37dd4b6` | `services/chi_tune.py`, `routes/phieu_linh.py` | CMP 59; tờ tạm ứng bỏ QR — lĩnh tiền ở quỹ hệ anh theo số DO |
| Xe thuê, trả chủ xe, trừ hàng quầy | `f306a24`, `fc51a67`, `f85078b` | `services/chi_tune.py`, `services/tra_chu_xe.py` | 621/4022; Nợ 4022 / Có tiền; tỷ giá riêng từng dòng |
| Chi mục V – VI, tất toán, trả NCC | `f85078b` | `services/chi_muc_tune.py`, `services/chi_tat_toan_tune.py` | CMP 60 / CMR 17 |
| Mở mã con tài khoản | `28101b7`, `38ea010` | `tools/mo_ma_con_tune.py`, `services/tai_khoan.py`, `routes/acc_code.py` | bảng định khoản một chỗ |
| Bàn giao DO B1 / B2 | `84053e8`, `38ea010`, `938b007` | `routes/ban_giao.py`, `services/ban_giao.py` | `customer_id` = mã bên anh; `q`; `invoiced` / `inv_no` theo SO |
| Cắt sổ, bỏ phần tiền trang tạm | `cd65128`, `c237f3e`, `79f4fe8`, `52f673c`, `52fbd73`, `677e800`, `f85078b`, `938b007` | `tools/bo_tien_trang_tam.py`, `services/goi_ke_toan.py` | thôi đẩy phong bì; cấu hình kho tạm riêng |
| Đọc lại "đã thu", các màn đề nghị theo trạng thái mới | `84a09d4`, `22dd4c8` | `services/chi_tune.py` (`_da_tra`), `services/de_nghi_thu.py` (`ap_thu`) | đã thu = tiền − còn nợ |
| Bút toán chờ + màn | `f85078b`, `ca7b630` | `services/but_toan_cho.py`, `routes/de_nghi.py` (`/api/but-toan-cho`), `frontend/modules/but-toan-cho` | 4 nguồn ban đầu |
| Gửi bút toán sang API anh | `a938301`, `875a0cf`, `3d4ba03` | `services/gui_but_toan_tune.py` | cờ `QLSX_GUI_BUT_TOAN`; gỡ, hỏi lại, xếp lỗi theo mã thật |
| Bút toán xuất kho cho chuyến | `1ac7acf`, `b9a11ef`, `2ac74de` | `services/but_toan_cho.py`, `routes/phieu.py` | `xuat_noi_bo` / `xuat_ban`; chặn khoá thiếu giá bán (`THIEU_GIA_BAN`), dầu kho chưa cấp (`DAU_KHO_CHUA_CAP`), phụ tùng chưa xuất (`PT_KHO_CHUA_XUAT`); sau khoá không sửa được số (`DA_KHOA`) |
| Gọi kho tạm | `d7cb27d`, `b966546` | `services/goi_ke_toan.py`, `kiem/*` | giữ tham số câu lỗi `VUOT_TON`; bài thử nhập trước rồi gỡ |
| Rà giao diện (không đụng kế toán) | `6405e4e` … `4bb2fd6`, `21f5954`, `ab97a9d`, `bcbfe81` | `frontend/*` | vừa khung 1366, ba thứ tiếng |
| Tài liệu + kịch bản thử | `4ea1a6d` … `226659f`, `191ab29` | `DOCS/md/*` | KB-AZ đi thật chuyến THU-KBAZ |

**Bảng mới trong DB trang điều xe** (dựng tự động bằng `create_all` khi khởi động): `gui_so_tune` (SO đã gửi, gói + khoá), `doi_tuong_tune` (ObjectId bên anh), `chi_tune` (phiếu tạm ứng), `chi_muc_tune` (chi mục V – VI), `chi_chu_xe_tune` (đề nghị trả chủ xe), `phieu_tien_tune` (tất toán, trả NCC), `but_toan_cho` (bút toán chờ / đã gửi). Cấu hình trong bảng `cau_hinh`: `token_nhan_qlsx` (khoá bàn giao), `kho_api` / `kho_token` / `kho_web` (kho tạm).

**Biến môi trường** (`.env` máy chủ trang điều xe):

| Biến | Ý nghĩa | Hiện tại |
|---|---|---|
| `EPL_ACC_CODE_API`, `EPL_ACC_CODE_TOKEN`, `EPL_ACC_CODE_COUNTRY` | đường danh mục tài khoản, token, quốc gia 11 | máy thử 8011 trỏ 5090; máy thật 8020 trỏ host |
| `QLSX_BASE_URL` | gốc API anh (không đặt thì lấy máy của `EPL_ACC_CODE_API`) | 8011: `http://127.0.0.1:5090` |
| `QLSX_ACCESS_TOKEN` / `QLSX_USERNAME`, `QLSX_PASSWORD`, `QLSX_ORG_ID` | token riêng / tự đăng nhập | không đặt (dùng `EPL_ACC_CODE_TOKEN`) |
| `QLSX_COUNTRY_ID`, `QLSX_DOTY_CHI_TAM_UNG`, `QLSX_DOTY_TRA_CHU_XE`, `QLSX_DOTY_CHI_KHAC`, `QLSX_DOTY_THU_KHAC`, `QLSX_TIEN_<MÃ>` | mã số (mặc định 11, 59, 60, 60, 17) | `QLSX_TIEN_USD=2` |
| `EPL_CHI_TAM_UNG` | `tai_cho` = quay về Quỹ chi trên LAO (dự phòng) | không đặt |
| `QLSX_GUI_BUT_TOAN` | gửi bút toán sang API anh | **bật trên máy thử 8011**; máy khác tắt |

### 3.2. Kho tạm `EPL_KETOAN` (HEAD `a1a5955`)

| Commit | Đổi gì |
|---|---|
| `1d8d91c` | ba đường máy trừ hàng chủ xe mua ở quầy: `/api/lien-thong/ban-hang/cho-tru` · `tru` · `bo-tru` |
| `09ae236` | chặn cấp / xuất vượt tồn ở máy chủ (`VUOT_TON`) |
| `8d5af08` | Bãi / thủ kho / tổ sửa chữa không thấy giá vốn; phụ tùng mới tồn 0 |
| `a1a5955` | thủ kho phụ tùng nhập số lượng, KT Chi phí / Sếp gõ giá nhập |

Kho tạm không nối gì sang hệ anh.

---

## 4. Anh Tune cần làm gì khi nhận lại source

Theo thứ tự. Bước có ghi **(host)** cần quyền máy chủ của anh.

1. **Review hai nhánh** (mục 2.1, 2.2; chi tiết từng commit ở `NOI_API_ANH_TUNE` mục 8). Bên em push hai nhánh lên repo khi chủ dự án cho.
2. **Merge** `feat/HonTunedaHai` (đến `a8c7014`) và `feat/hontunedhai_Laos` (đến `6abe0ad8`) vào nhánh anh dùng để triển khai.
3. **Áp script lên DB host (host)** — đối chiếu trước các script nền của anh đã có trên host (`20260910_sales_debt_collection_country`, `20260911_logistics_sales_push`, `20260912_cash_voucher_source_reference`, `20260913_lao_accounts_crud`):
   1. DB kế toán (`CenterConnectionStrings[0]`): `20261001_logistics_journal_entry.sql` → đọc D1 (3 thủ tục), D2 (nền đủ), **D3** (tên tham số legacy khớp), **D4** (`PUBENTRY.OBJ_AUTOID` cho NULL không), D6 (phải 0 dòng);
   2. cùng DB: `20261002_logistics_journal_entry_list.sql` → D1 – D4;
   3. cùng DB: `20261002_cm_unpost_cash_voucher.sql` → D1 – D3, **D6** (phiếu ST 12 / 13 không còn chứng từ con — phải 0 dòng);
   4. DB `ConnectionStrings:Master`: kiểm có cột `CMRECEIPT.CMR_ISLOCAL`, rồi `20261001_sales_debt_collection_currency.sql`;
   5. cùng DB: `20261002_sales_debt_collection_cancel.sql` → D1 – D4, **D6** (TKN lệch CMR — phải 0 dòng, có dòng thì đối soát);
   6. cùng DB: `20261001_audit_redact_secrets.sql` chạy nguyên tệp (`@Apply = 0`, chỉ chẩn đoán) → lưu kết quả → sửa `@Apply = 1` chạy lại → chẩn đoán sau phải 0 → cân nhắc đổi mật khẩu các tài khoản đã đăng nhập qua API; xoá / xoay vòng tệp log WEB cũ trên host.
4. **Thêm mục cấu hình (host)** vào `appsettings.<Env>.json` của API: `LogisticsSource` (`BaseUrl` = địa chỉ `/api/` trang điều xe thật — bắt buộc; `ApiKey` = khoá Sếp LAO tạo bằng `POST /api/handover/tao-khoa`), `LogisticsJournalEntry` (`Enabled true`, `AllowedUserIds`, `OrgId`, `CountryId`), `LaoAccountsWrite`, `SalesDebtCollectionCancel`; giữ `LogisticsSalesPush` (`AllowedUserIds` có 846).
5. **Dữ liệu host (host):**
   - danh mục tài khoản: `GET country-accounts?tryAutoId=11` trả 494 mã thì mở 1371 / 4021 / 4022 (`tools/mo_ma_con_tune.py https://<API host>`, cần 846 trong `LaoAccountsWrite`); bút toán cần thêm 621, 625, 614, 1601, 607, 707 hạch toán được;
   - **bật LAK** và **USD** (`CurrencyId` 2) trong danh mục tiền tệ;
   - **tài khoản tiền mặc định** theo vai (`CMACCOUNTCONFIGCOUNTRY` quốc gia 11: tiền mặt / ngân hàng × nội tệ / ngoại tệ = 1011 / 1012 / 1021 / 1022) — `default-money-account` của host đang báo lỗi;
   - **mã chi nhánh bị cắt trong `RETK_CODE`**: `sp_RES_Create_RESTICKET` cắt mã phiếu bán về 20 ký tự, mã chi nhánh "Demo EPL" dài nên mọi SO cùng `Demo EPL-2-261001000` — rút ngắn mã chi nhánh hoặc sửa thủ tục sinh mã;
   - **menu WEB**: thêm mục "Bút toán từ Logistics" (`LOGISTICS_JOURNAL_ENTRY`, nhóm `CASH_VOUCHER`) ở màn quản trị menu.
6. **Deploy API trước, WEB sau (host).** WEB mới đọc `LocalCurrencyCode` / `IsForeignCurrency` và không gửi số quy đổi; WEB mới chạy với API cũ thì quy đổi không được tính lại.
7. **Đổi link bên em, bật cờ:** trang điều xe máy thử bỏ `QLSX_BASE_URL` / đổi `EPL_ACC_CODE_API` từ localhost sang `https://demo-lao-api.goldensme.com`; máy thật 8020 đã trỏ host sẵn. Bật `QLSX_GUI_BUT_TOAN=1` ở máy nào gọi API đã có script + cấu hình. Gửi anh địa chỉ gốc + khoá bàn giao khi trang điều xe ra Internet.
8. **Test lại theo `KICH_BAN_A_Z_EPL_TUNE`** trên host: SO → tạm ứng → chi mục V – VI → khoá phiếu (bút toán ST 13) → thu nợ TKN (SO USD với tài khoản ngoại tệ, tỷ giá ngày thu) → tất toán → trả chủ xe → trả NCC → mở khoá (gỡ bút toán) → màn "Bút toán từ Logistics" → huỷ một TKN thử → gỡ ghi sổ một phiếu thử.
9. **Việc anh phải quyết:**
   - **khoảng 60 TKN cũ không có CMR** trên DB demo (D6 của script huỷ: TKN đang hiệu lực mà không có phiếu thu CMR hoạt động — dư nợ đã trừ nhưng không có chứng từ thu bên kế toán; thủ tục huỷ trả 409 `52765` với các phiếu này) — anh quyết giữ, đối soát hay xử lý tay;
   - **ghi sổ chính thức (ST 12)** cho chứng từ tổng hợp: ai ghi, ở màn nào (WEB mới có màn xem, chưa có nút ghi sổ / gỡ); sau ST 12 thì LAO không gỡ được (409 `52515`);
   - **màn GL**: có cần màn chứng từ tổng hợp DOTY 12 đầy đủ (ghi sổ, gỡ) không;
   - hai CMR thu lại `4-1368-TK-261002-00001` / `-00002` đang ST 1: thủ quỹ ghi sổ;
   - các phiếu thử còn lại trên DB demo (mục 2.5): giữ làm mẫu hay gỡ;
   - tài khoản tích hợp riêng (thay token cá nhân `tune`): tạo qua tab Tài khoản hồ sơ nhân viên, thêm UserId vào mọi `AllowedUserIds`;
   - bút toán riêng cho **phí 2 %** và **trừ quá tải** xe thuê (chờ anh Khampla chọn tài khoản).

---

## 5. Rủi ro và việc còn mở

| # | Rủi ro / việc | Mức | Người làm |
|---|---|---|---|
| 1 | **Token `tune` hết hạn khoảng 10/10/2026**: hết hạn thì không gửi SO, không lập phiếu chi, tài xế không xuất phát được | cao | thay token trong `.env` hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` (mật khẩu ≤ 20 ký tự) — **cần quyền host** |
| 2 | **Host chưa có gì**: code, 6 script, cấu hình, mã tài khoản, LAK / USD, menu (mục 4) | cao | **cần quyền host** |
| 3 | Thủ tục legacy (`sp_PostTing_GeneralLedger`, `sp_GL_Delete_*`, `SP_CMR_DELETEMCMR_CMRECEIPT`…) không có trong repo; hành vi đã đo trên DB demo (sinh chứng từ con, gỡ sổ không đổi ST, xoá trả `'2'`). DB host khác thì hậu kiểm của thủ tục mới rollback với mã riêng | trung bình | đọc D3 / D6 lúc áp |
| 4 | "Đã thu" bên LAO theo **dư nợ RES** — TKN trừ nợ ngay lúc tạo, trước khi thủ quỹ ghi sổ CMR (hai CMR thu lại đang ST 1 nhưng LAO đã thấy "đã thu đủ") | thấp | biết để đối soát |
| 5 | **Chưa có bảng tỷ giá ngày**: tỷ giá thu nợ ngoại tệ do người thu nhập; nội tệ của SO Logistics suy từ tiền chi của DO | trung bình | anh quyết có làm bảng tỷ giá |
| 6 | **`RETK_CODE` trùng** giữa các SO (mục 4 bước 5); khoá đúng của đơn là `OrderCode` | thấp | anh |
| 7 | Script audit chưa chạy: dòng audit cũ trên DB demo / host có thể còn mật khẩu | trung bình | **cần quyền host** (DB demo: chủ dự án) |
| 8 | Cờ phân loại loại chứng từ ở `document-types` chưa có: WEB / API ghi cứng DOTY 58 / 60, 15 / 17; phiếu 59 chỉ xem trên WEB | thấp | bên EPL |
| 9 | Relation IV / IC và công nợ không gửi số tiền: máy chủ vẫn dùng tổng header client (đường tương thích) | thấp | bên EPL |
| 10 | Huỷ phiếu thu nợ **chưa có nút WEB** (gọi API); WEB chưa có nút gỡ / ghi sổ chính thức cho chứng từ tổng hợp | thấp | bên EPL khi anh cần |
| 11 | Trừ hàng quầy khi trả chủ xe phụ thuộc kho tạm `EPL_KETOAN`; kho tạm tắt thì không lập được đề nghị trả (503) | thấp | — |
| 12 | **Phần kho gác lại** (thuộc kho tạm / hệ kho anh Toàn, không làm lượt này): phiếu điều chỉnh kiểm kê; thủ kho điểm đổ nhập dầu | — | khi nối hệ kho anh Toàn |
| 13 | Đừng **xoá tay** phiếu chi / thu do LAO tạo: LAO đánh `PHIEU_CHI_MAT` và lập phiếu mới khi gửi lại; cần huỷ thì báo bên EPL rút | — | kế toán bên anh |
| 14 | Bên em không có mật khẩu WEB nên các màn WEB thử bằng đúng lời gọi WEB gửi và harness, chưa bấm tay đủ trên giao diện | thấp | anh bấm thử lúc review |

---

## 6. Bài thử bên em (chạy lại được; máy thử 8011 ↔ API ở máy 5090; không chạy trên máy thật 8010 / 8020)

- SO, khách, bàn giao: `kiem/thu_tao_so.py`, `thu_tao_so_that.py`, `thu_luat_so_ben_tune.py`, `thu_ban_giao.py`, `thu_khach_hang_moi.py`;
- phiếu bên anh: `thu_chi_tam_ung_ke_toan.py`, `thu_xe_thue_ke_toan.py`, `thu_chu_xe.py`, `thu_tru_hang_quay.py`, `thu_chi_muc_tune.py` (có gỡ ghi sổ thật), `thu_tat_toan_tune.py`;
- bút toán: `thu_but_toan_cho.py`, `thu_gui_but_toan.py` (máy giả theo giao ước), `thu_but_toan_xuat_kho.py`;
- giao diện: `thu_giao_dien.js`; kho tạm: `EPL_KETOAN/kiem/thu_tru_hang_chu_xe.py` (8031).
