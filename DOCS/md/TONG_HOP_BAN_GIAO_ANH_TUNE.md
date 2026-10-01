# Tổng hợp bàn giao cho anh Tune — trang điều xe EPL Lào ↔ hệ kế toán

Ngày **01/10/2026**. Bên soạn: trang điều xe **EPL_LAO_REAL** (logistics). Người đọc: **anh Tune**.

Anh đọc trang này trước. Chi tiết nằm ở:
- hợp đồng **HOP_DONG_API_KE_TOAN_ANH_TUNE** (mục 0.1, 5, 8, 10, 12.9 – 12.12);
- bản đồ nối **NOI_API_ANH_TUNE**;
- hướng dẫn triển khai **HUONG_DAN_TRIEN_KHAI_ANH_TUNE** (các bước đổi link, kiểm sau triển khai; áp script và bật bút toán ở mục 4.6);
- mục **16** trong tài liệu hiện trạng của anh: `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md` (API bút toán: mục 16.9).

Source đang đối chiếu: API `feat/HonTunedaHai@b9227aa`, WEB `feat/hontunedhai_Laos@7d168744`; trang điều xe `f85078b`, `ca7b630`, `938b007`, `a938301`, `875a0cf`; kho tạm `EPL_KETOAN@1d8d91c`. Mọi thứ dưới đây bên em thử trên **API và WEB chạy ở máy**. Bản host `demo-lao-api.goldensme.com` chưa merge code hai nhánh; triển khai lên host xong (**cần quyền host**) thì đổi link theo mục 4. Mã còn đổi nhỏ: chỗ chưa chắc ghi **đang chốt**.

**Người làm** (chủ dự án chốt 01/10: "bên mình với anh Tune giờ là một"): việc trên source ghi **bên EPL làm (đang làm)**; việc cần máy chủ host (triển khai, dữ liệu DB host, token / mật khẩu tài khoản của anh) ghi **cần quyền host**.

**Token** (chủ dự án chốt 01/10): tạm gác tài khoản tích hợp; trang điều xe tiếp tục dùng token của anh (`EPL_ACC_CODE_TOKEN`). Hết hạn khoảng 10/10 thì thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh để tự đăng nhập lại (đường này đã có sẵn). Mật khẩu tối đa 20 ký tự (`proc_LoginWithUsAndPw`, `VARCHAR(20)`); tài khoản phải được gán chi nhánh (`USERS_ORG`).

## 0. Ranh giới tiền (chủ dự án chốt 01/10/2026)

- **Bỏ phần tiền của trang kế toán tạm** `EPL_KETOAN` (cổng 8030). Trang đó chỉ còn là **kho tạm**, tới khi nối hệ kho của anh Toàn.
- **Số tiền trên trang kế toán tạm là số thử, bỏ hết**: hoá đơn, lần thu, đợt trả chủ xe, tất toán, trả nhà cung cấp, cấn trừ ở đó không mang sang.
- **Cắt sổ 01/10:** mọi DO đã khoá đều gửi SO sang hệ anh **từ đầu**. Trang điều xe không còn chặn DO đã có hoá đơn / đã thu ở trang tạm; luật `DA_HOA_DON_TRANG_TAM` đã bỏ.
- **Khoản đi qua tiền** thành **phiếu chi / phiếu thu bên anh** (`PostMode = None`). Thủ quỹ bên anh chi / thu rồi **ghi sổ**, trang điều xe đọc lại `STATUS` 12/13.
- **Khoản không qua tiền** thành **bút toán chờ gửi** ở trang điều xe, đủ hai vế từng dòng bằng mã thật. Hệ anh **đã có API bút toán tổng hợp** (`b9227aa`); bên em gửi sang khi script đã áp lên DB kế toán và cờ `QLSX_GUI_BUT_TOAN` bật (mục 5). Trong lúc chờ, bút toán vẫn nằm ở trang điều xe, không mất khoản nào.
- Trang điều xe **thôi đẩy phong bì chứng từ** `POST /api/v1/epl-lao/vouchers`; các đường liên thông phần tiền đã gỡ (còn đường kho).

## 1. Các luồng

| Việc bên trang điều xe | Đường API bên anh | Định khoản | Trạng thái 01/10 |
|---|---|---|---|
| Màn **Vụ việc** bên anh đọc DO đã khoá | `accounting/cash-voucher-references` → trang điều xe `/api/handover/delivery-orders` | — | chạy ở máy |
| **Đề nghị thu** → SO, công nợ khách | `integrations/logistics/sales-orders` | Nợ 1211 / Có 708 | chạy ở máy; mọi DO đã khoá gửi được; phiếu xuất xe hiện "Đã tạo SO" |
| Tạo đối tượng khi chưa có | `master-data/customers · suppliers · staff/upsert` | — | chạy: khách `EPLKH-…`, chủ xe `EPLCX-…`, nhà cung cấp `EPLNCC-…`, tài xế `EPLTX-…` |
| **Tạm ứng xe nhà**: thủ quỹ chi ở hệ anh | `cmpayment-receipt/save-and-commit`, "Chi trước" (DOTY 59) | Nợ 1601 / Có 1011 | chạy; ghi sổ xong thì xe mới xuất phát |
| **Tạm ứng xe thuê**: đứng tên chủ xe | như trên | Nợ 4022 / Có 1011 | chạy |
| **Trả chủ xe liên kết** — đã trừ hàng chủ xe mua ở quầy | `save-and-commit`, "Chi khác" (DOTY 60) | Nợ 4022 / Có 1011 · 1012 · 1021 · 1022; tỷ giá riêng từng dòng | chạy; ghi sổ xong thì phiếu xe "đã trả chủ xe" |
| **Chi mục V – VI** (dòng quỹ trả ngay) | `save-and-commit`, "Chi khác" (DOTY 60) | theo tờ `PC_SC`: xe nhà Nợ 614 (V) · 625 (VI) / Có 1011; xe thuê Nợ 4022 / Có 1011 | chạy ở máy; Quỹ trên trang điều xe không chi nữa |
| **Tất toán tài xế** | chênh dương TT_CHI "Chi khác" (60) · chênh âm TT_THU CMR "Thu khác" (17), đứng tên `EPLTX-` | Nợ 1601 / Có tiền · Nợ tiền / Có 1601 | chạy ở máy; màn Tất toán tài xế |
| **Trả nhà cung cấp** | `save-and-commit`, "Chi khác" (DOTY 60), đứng tên `EPLNCC-` | Nợ 4021 / Có tiền | chạy ở máy; màn Nhà cung cấp → "Trả qua kế toán" |
| **Bút toán chờ gửi** (không qua tiền) | `integrations/logistics/journal-entries` (+ `/reverse`, `GET /{SourceRef}`); `Idempotency-Key` = `EPLLAO-<nguồn>-<mã nguồn>` | thuê xe 621/4022 · ghi nợ NCC 625 · 614 / 4021 · quyết toán tạm ứng 625/1601 · bán chủ xe 4022/707 | API có (`b9227aa`), đầu gửi có (`875a0cf`, cờ tắt). **Chưa chạy trên DB**: chờ áp script; cấu hình đã có ở API máy. Trong lúc chờ: màn "Bút toán chờ gửi" |
| Đọc lại trạng thái phiếu chi / thu | `cmpayment-receipt/list`, `/{id}` | — | tự đọc lúc mở phiếu, trước khi cho xe chạy, khi bấm Cập nhật. Phiếu bị xoá tay bên anh → `PHIEU_CHI_MAT`, gửi lại thì lập phiếu mới |
| **Công nợ khách**, "đã thu" của từng SO (chỉ xem) | `sales/debt/customer-detail` | — | màn Khách hàng → tab Công nợ; đề nghị thu đọc "thu một phần / đã thu" theo `OrderCode` |
| **Thu tiền khách** của SO (kế toán bên anh làm, bên em không gọi) | WEB anh: **Chi tiết công nợ khách hàng → Tạo phiếu thu → Xác nhận thu nợ** → `sales/debt/collection-upsert` (TKN) | phiếu thu **CMR 17 "Thu khác"**, Nợ 1021 (tiền mặt 1011) / Có 1211; số dạng `4-TKN-1368-2-261001-0001` (thu nợ) và `4-1368-TK-261001-00009` (phiếu thu) | KB-AZ đi thật 01/10. **Không** thu bằng phiếu "Thu công nợ" (CMR 15): tìm ở đó ra 0 dòng |
| Rút phiếu chưa ghi sổ (xoá phiếu / huỷ đề nghị) | `cmpayment-receipt/delete` | — | đã ghi sổ thì không rút, báo đối soát |

Phiếu bên em gửi vẫn mang `Header.Amount` / `Header.BaseAmount` = tổng các dòng. Hệ anh tự tính lại **quy đổi từng dòng** (`ae0e7f6`) và **tổng header** (`ce95b3c`), 5 số lẻ, làm tròn nửa xa số 0. Phiếu trả chủ xe ngoại tệ bên em gửi tỷ giá riêng từng dòng để Kíp khoá từng phiếu xe không bị dịch.

**Trừ hàng quầy khi trả chủ xe:** phiếu bán nằm ở kho tạm. Lập đề nghị trả thì giữ chỗ các phiếu bán (`TUNE-CHO:<số đề nghị>`), thủ quỹ bên anh đã chi thì chốt (`TUNE:<số phiếu chi>`) và ghi bút toán chờ Nợ 4022 / Có 707, bỏ đề nghị thì thả phiếu bán về chờ trừ — qua ba đường kho tạm `/api/lien-thong/ban-hang/cho-tru`, `/tru`, `/bo-tru` (`EPL_KETOAN@1d8d91c`).

## 2. Thay đổi trên source của anh

| Repo | Nhánh | Commit | Nội dung |
|---|---|---|---|
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `465748b` | Nguồn DO: địa chỉ và khoá Logistics đọc từ cấu hình `LogisticsSource`, gửi `Authorization`. DO hiện số phiếu, tên khách; tìm theo số xe, biển số. |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `be123e9` | `ObjectService`: tạo đối tượng không gửi `IsOrganization` thì mặc định cá nhân (trước đó văng 500, `OBJ_ISORG` NULL). |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `64ce7a4` | Vụ việc: có từ khoá thì gửi `q` sang trang điều xe, tìm trên toàn bộ DO, Total đúng sau lọc; nguồn không hiểu `q` thì lọc trong trang. |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `ce95b3c` | Theo chuẩn QLSX: `CashVoucherReferenceService` + `LogisticsDeliveryOrderClient`, controller chỉ còn HTTP / claims / envelope; contract typed; **thiếu `LogisticsSource:BaseUrl` → 503**, không còn mặc định 1506. `CashVoucherHeaderTotals`: create / save / save-and-commit **tự tính tổng header** từ dòng. Dòng IV/IC hay công nợ thiếu số tiền thì giữ số header client gửi. |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `ed5aa0e` | Nhật ký kiểm toán: bỏ `CancellationToken` khỏi payload (hết "Đặt log sai"); che mật khẩu / token / khoá trong payload và query string. |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `ae0e7f6` | Máy chủ tự tính quy đổi từng dòng (`Amount × tỷ giá dòng`, thiếu thì tỷ giá header) trước khi cộng tổng header. |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `e2ef52f` | Script `20261001_audit_redact_secrets.sql`: che mật khẩu / token / khoá trong dòng audit cũ (trước `ed5aa0e`). Chạy lúc triển khai; trong tệp `@Apply` mặc định 1 (che luôn), đặt 0 để chỉ xem. |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `0d4eed9` | Nhật ký kiểm toán che thêm trường `jwt`, `cookie`. |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `b9227aa` | **API bút toán tổng hợp** `integrations/logistics/journal-entries`: tạo + ghi sổ tạm (ST 13), gỡ (`/reverse`), đọc lại (`GET`); chống trùng theo `SourceRef`. Script `20261001_logistics_journal_entry.sql` (ba thủ tục mới, chạy lại được) — **chưa áp DB**. Mẫu cấu hình `logistics-journal-entry-config.example.json`. Giao ước: hợp đồng 12.12.4. |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `f382a9e8` | Modal Vụ việc: thoát ký tự chuỗi DO; DO hiện số phiếu, xe, tài xế; tỷ giá nhỏ hơn 1 đọc xuôi. |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `06a14189` | Phiếu thu / chi: `isCash` theo hình thức thanh toán; tài khoản tiền mặc định đọc đúng `AccountCode`, gửi kèm loại tiền; tổng xem trước tách nguyên tệ / quy đổi; phân loại theo mã loại chứng từ, không theo tên. |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `7e14421c` | Đổi hình thức / nội tệ / loại tiền khi đã có dòng thì vế tiền các dòng đổi theo; đổi quốc gia khi đã có dòng thì chặn trước khi nạp danh mục; mã DOTY gom một chỗ. |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `77bcb0a1` | Loại phiếu không đổi ngầm: chỉ 58/60, 15/17 sửa được, loại khác (57, 59 "Chi trước", 68, 14, 16) chỉ xem. Đổi tài khoản tiền theo cờ `moneyAccountIsDefault`; hình thức không rõ thì chặn lưu; modal Vụ việc thoát ký tự cả DEAL / QUOTE. |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `fce78c52` | Phiếu thu / chi: tiền tệ ngoài danh mục (ví dụ USD đang tắt) giữ đúng mã, phiếu chỉ xem; phiếu mới thiếu tiền tệ chặn lưu; công nợ xem trước theo tỷ giá header. Hồ sơ nhân viên có tab **Tài khoản** (tạo / sửa, đặt lại mật khẩu) — chưa bấm tạo tài khoản thật. |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `7d168744` | Log WEB che mật khẩu / token / khoá / jwt / cookie; không còn in header `Authorization` vào log và câu báo. |

Trang điều xe (bên em): `a938301` gửi bút toán chờ sang API trên (cờ `QLSX_GUI_BUT_TOAN`, mặc định tắt); `875a0cf` khớp giao ước `b9227aa` (gỡ trả `Reversed=false` thì coi như đã gỡ, 409 `52512` thì tự gỡ rồi gửi lại, bỏ bản chưa rõ thì hỏi lại trước, đọc lỗi ở `ErrorDetail`).

Chưa push nhánh nào lên GitHub.

## 3. Thay đổi dữ liệu (DB mà `appsettings.laos.json` trỏ tới — anh đã sao lưu sáng 01/10)

- **Danh mục tài khoản Lào** (qua `lao-accounts`):
  - 137 và 402 chuyển thành tài khoản **tổng hợp**;
  - thêm **1371** kho hàng, vật tư; **4021** phải trả nhà cung cấp; **4022** phải trả chủ xe liên kết.

  Quốc gia 11 nay có 497 mã. Trong hai repo không chỗ nào ghi cứng 137 / 402, ngoài tệp nạp `20260909_country_account_import_lao.sql`. Muốn trả lại: xoá 1371 / 4021 / 4022 khi chưa có bút toán, rồi `lao-accounts/update` 137 / 402 với `Posting=true`.
- **Chi phí thuê xe liên kết** chốt *Nợ 621 / Có 4022* lúc khoá phiếu (621 = ຄ່າຂົນສົ່ງ, khớp "ຄ່າຂົນສົ່ງນອກ" trong Excel của khách). Bàn giao DO có `hire.acc_code = "621/4022"`.
- **Đối tượng** `EPLKH-` / `EPLCX-` / `EPLNCC-` / `EPLTX-`; một tài xế thử `EPLTX-THU01`.
- **Hai SO** `TK-20261001-000162` (T4-0449-09/EPL, ຄຳຕຸ້ຍ, 905,85 USD) và `TK-20261001-000163` (T4-0442-09/EPL, ນາງ ວັນນາ, 1.676,90 USD): tạo ngày 01/10 trước giờ cắt sổ, **giữ nguyên**, là công nợ thật của hai DO đó.
- **Phiếu chi thử** `1368-CTR-261001-…`, `1368-CKH-261001-00001`, `…00002`: phiếu chưa ghi sổ đã được rút.

## 4. Khi triển khai lên host: đổi link, kiểm một lệnh

| Bên | Khoá | Lúc thử | Sau triển khai |
|---|---|---|---|
| Trang điều xe máy thử 8011 | `QLSX_BASE_URL`, `EPL_ACC_CODE_API` | `http://127.0.0.1:5090` | bỏ đi → về host |
| Trang điều xe máy thật 8020 | `QLSX_BASE_URL` | không đặt → gọi `https://demo-lao-api.goldensme.com` | giữ nguyên |
| API anh | `LogisticsSource:BaseUrl` | `http://127.0.0.1:8011/api/` | địa chỉ `/api/` trang điều xe thật — **bắt buộc**, thiếu thì màn Vụ việc báo 503 |
| API anh | `LogisticsSource:ApiKey` | khoá máy thử | khoá Sếp tạo ở trang điều xe thật (`POST /api/handover/tao-khoa`) |
| API anh | `LogisticsSource:Branches:<BranchId>` | không đặt | chỉ khi chi nhánh có trang điều xe riêng |
| API anh | `LogisticsSalesPush:Enabled`, `AllowedUserIds` | `[846]` | giữ `846` (tài khoản `tune`, trang điều xe đang dùng) |
| API anh | `LogisticsSalesPush:BusinessTypeId`, `AreaId`, `PosId`, `CounterId`, `TableId` | đủ năm mã | thiếu một mã → 503 `LOGISTICS_CONFIG_REQUIRED` |
| API anh | `LogisticsJournalEntry:Enabled`, `AllowedUserIds`, `OrgId`, `CountryId` | API máy: `true`, `[846]`, 1368, 11 | thêm trên host **sau khi** áp script lên DB kế toán host |
| Trang điều xe | `QLSX_GUI_BUT_TOAN` | tắt | `1` khi API nó gọi đã có script + cấu hình |
| WEB anh | `BACKOFFICE_API_URL` | `Env=laoslocal` trỏ 5090 | `Env=laos` trỏ API host |
| Kho tạm `EPL_KETOAN` | bản có `1d8d91c` | máy thử 8031 | trừ hàng quầy khi trả chủ xe cần bản này |

**Kiểm:** `GET <host>/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true`:
- trả **497 mã**: host cùng DB, không làm gì thêm;
- trả **494 mã**: host trỏ DB khác. Bên em chạy `python tools/mo_ma_con_tune.py https://<API host>` để mở ba mã. Đối tượng thì lần gửi đầu bên em tự tạo.

**Bút toán tổng hợp — thứ tự trên mỗi môi trường** (máy bên em trước, host sau): áp script `20261001_logistics_journal_entry.sql` lên DB kế toán → cấu hình `LogisticsJournalEntry` → bật `QLSX_GUI_BUT_TOAN=1` ở trang điều xe → gọi thử. Lệnh và cách đọc kết quả: HUONG_DAN_TRIEN_KHAI mục 4.6.

## 5. Việc đã xong và việc còn lại

### 5.1. Đã xong (01/10)

| Việc | Ở đâu |
|---|---|
| SO, tạm ứng, trả chủ xe (trừ hàng quầy), chi mục V – VI, tất toán tài xế, trả nhà cung cấp qua phiếu bên anh | chạy ở máy (mục 1) |
| Máy chủ tự tính quy đổi từng dòng và tổng header phiếu thu chi | `ce95b3c`, `ae0e7f6` |
| Nhật ký kiểm toán API che mật khẩu / token / khoá / jwt / cookie; log WEB cũng vậy | `ed5aa0e`, `0d4eed9`, WEB `7d168744` |
| Script che mật khẩu trong dòng audit cũ | `e2ef52f` — đã có script, **chưa chạy** (xem 5.2) |
| **API bút toán tổng hợp** (tạo + ghi sổ tạm, gỡ, đọc lại; chống trùng theo `SourceRef`) và đầu gửi bên em | API `b9227aa`; trang điều xe `a938301`, `875a0cf` (cờ tắt) |
| Mục `LogisticsJournalEntry` trong `appsettings.laos.json` của API ở máy (`Enabled`, `AllowedUserIds` 846, `OrgId` 1368, `CountryId` 11) | API ở máy; GET đang trả 503 `LOGISTICS_JOURNAL_SCRIPT_REQUIRED` vì chưa áp script |
| WEB: tiền tệ ngoài danh mục không gán ngầm; công nợ xem trước theo tỷ giá header; tab Tài khoản ở hồ sơ nhân viên | `fce78c52` |

### 5.2. Còn lại

| Việc | Trạng thái | Người làm |
|---|---|---|
| **Áp script bút toán** `20261001_logistics_journal_entry.sql` lên DB demo (DB kế toán của `appsettings.laos.json`), đọc diagnostics D3 / D4 | **chưa áp**: lệnh áp từ máy bên em bị bộ an toàn chặn | **chủ dự án tự chạy** (SSMS hoặc `sqlcmd`, HUONG_DAN 4.6) |
| Sau khi áp: bật `QLSX_GUI_BUT_TOAN=1` ở trang điều xe máy thử, gọi thử tạo → GET → tạo lại → gỡ → gỡ lần hai; `ST_AUTOID` = 13 | chờ bước trên | bên EPL làm |
| **Cờ phân loại loại chứng từ** ở `document-types` (công nợ / khác / "Chi trước") | WEB và API đang ghi cứng 58/60, 15/17; phiếu 59 "Chi trước" mở trên WEB chỉ xem | bên EPL làm (đang làm) |
| **Thu tiền SO USD bị ghi thành Kíp**: hộp Tạo phiếu thu (Chi tiết công nợ khách) chỉ có tài khoản nội tệ và tỷ giá cứng 1 | đang sửa | bên EPL làm (UI-4) |
| **Mọi SO cùng một mã phiếu bán** "Demo EPL-2-261001000" | đang tìm nguồn | bên EPL làm (UI-4) |
| **Quy đổi công nợ** | WEB xem trước và máy chủ cùng theo tỷ giá header; còn đối chiếu với thủ tục nhập công nợ — **đang chốt** | bên EPL làm (đang làm) |
| Chạy lại vòng nối kế toán với bản cuối hai bên, gồm bút toán | mã còn đổi nhỏ — **đang chốt** | bên EPL làm (đang làm) |
| **Merge + triển khai** hai nhánh lên `demo-lao-api` (đến `b9227aa` / `7d168744`); cấu hình `LogisticsSource`, `LogisticsSalesPush`, `LogisticsJournalEntry` | các bước ở HUONG_DAN_TRIEN_KHAI | **cần quyền host** |
| **Hai script trên DB host**: `20261001_logistics_journal_entry.sql` (DB kế toán), `20261001_audit_redact_secrets.sql` (che audit cũ; cân nhắc đổi mật khẩu tài khoản đã đăng nhập qua API) | chưa chạy | **cần quyền host** |
| **Mở 1371 / 4021 / 4022** trên DB host (host trả 494 mã) | bên em có `tools/mo_ma_con_tune.py`, chạy khi được phép | **cần quyền host** |
| **Bật LAK** (đang tắt trên host) và **USD** (`CurrencyId` 2) | bên em tạm đặt `QLSX_TIEN_USD=2` | **cần quyền host** |
| **Lỗi `default-money-account`** trên host (HTTP 200, `Success:false`) | tra log theo mã tra cứu; đối chiếu script tài khoản tiền theo quốc gia | **cần quyền host** |
| **Token hết hạn khoảng 10/10/2026** | thay token mới trong `.env`, hoặc đặt `QLSX_USERNAME` / `QLSX_PASSWORD` của anh để tự đăng nhập lại | **cần quyền host** (token / mật khẩu của anh) |
| Tài khoản tích hợp riêng (tuỳ chọn) | **tạm gác** (chủ dự án 01/10). Nhân viên ảo `EPL-TICHHOP` (ObjId 1622) đã tạo trên DB demo, chưa có tài khoản dùng được. Có thì thêm `UserId` vào cả `LogisticsSalesPush` lẫn `LogisticsJournalEntry` | khi cần |
| Đừng **xoá tay** phiếu chi / thu do trang điều xe tạo | xoá tay thì bên em đánh `PHIEU_CHI_MAT` và lập phiếu mới khi gửi lại | cần huỷ thì báo bên EPL rút |
| Bút toán riêng cho **phí 2 %** và **trừ quá tải** xe thuê | chưa có tài khoản | anh Khampla chốt |

## 6. Tệp và lệnh

- Hợp đồng chi tiết: `EPL_LAO_REAL/DOCS/md/HOP_DONG_API_KE_TOAN_ANH_TUNE.md` (bản Word cùng tên trong `DOCS/word/`); giao ước bút toán ở mục 12.12.4.
- Bản đồ nối API: `EPL_LAO_REAL/DOCS/md/NOI_API_ANH_TUNE.md`.
- API bút toán bên anh: `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md` mục 16.9; script `Backend.API/Database/Scripts/20261001_logistics_journal_entry.sql`; mẫu cấu hình `logistics-journal-entry-config.example.json`.
- Mở ba mã: `EPL_LAO_REAL/tools/mo_ma_con_tune.py [địa chỉ API]`.
- Bài thử bên em (chạy lại được, máy thử 8011 với API anh chạy ở máy):
  - `kiem/thu_chi_tam_ung_ke_toan.py`, `kiem/thu_xe_thue_ke_toan.py`, `kiem/thu_chu_xe.py`, `kiem/thu_tru_hang_quay.py`
  - `kiem/thu_chi_muc_tune.py`, `kiem/thu_tat_toan_tune.py`, `kiem/thu_but_toan_cho.py`
  - `kiem/thu_gui_but_toan.py` — gửi bút toán với máy giả theo giao ước `b9227aa` (không gọi API thật; không chạy trên máy thật 8010 / 8020)
  - `kiem/thu_tao_so_that.py`, `kiem/thu_ban_giao.py`, `kiem/thu_dinh_khoan.py`
  - `kiem/thu_giao_dien.js` (22 màn)
  - kho tạm: `EPL_KETOAN/kiem/thu_tru_hang_chu_xe.py` (máy thử 8031)
