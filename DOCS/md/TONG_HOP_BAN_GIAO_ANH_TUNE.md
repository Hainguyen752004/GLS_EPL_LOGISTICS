# Tổng hợp bàn giao cho anh Tune — trang điều xe EPL Lào ↔ hệ kế toán

Ngày **01/10/2026**. Bên soạn: trang điều xe **EPL_LAO_REAL** (logistics). Người đọc: **anh Tune**.

Anh đọc trang này trước. Chi tiết nằm ở:
- hợp đồng **HOP_DONG_API_KE_TOAN_ANH_TUNE** (mục 0.1, 5, 8, 10, 12.9 – 12.12);
- bản đồ nối **NOI_API_ANH_TUNE**;
- hướng dẫn triển khai **HUONG_DAN_TRIEN_KHAI_ANH_TUNE** (các bước đổi link, kiểm sau triển khai);
- mục **16** trong tài liệu hiện trạng của anh: `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md`.

Source của anh đang đối chiếu: API `feat/HonTunedaHai@ce95b3c`, WEB `feat/hontunedhai_Laos@7e14421c`. Mọi thứ dưới đây bên em thử trên **API và WEB chạy ở máy**. Bản host `demo-lao-api.goldensme.com` chưa merge code hai nhánh; anh triển khai xong thì đổi link theo mục 4.

## 0. Ranh giới tiền (chủ dự án chốt 01/10/2026)

- **Bỏ phần tiền của trang kế toán tạm** `EPL_KETOAN` (cổng 8030). Trang đó chỉ còn là **kho tạm**, tới khi nối hệ kho của anh Toàn.
- **Số tiền trên trang kế toán tạm là số thử, bỏ hết**: hoá đơn, lần thu, đợt trả chủ xe, tất toán, trả nhà cung cấp, cấn trừ ở đó không mang sang.
- **Cắt sổ 01/10:** mọi DO đã khoá đều gửi SO sang hệ anh **từ đầu**. Trang điều xe không còn chặn DO đã có hoá đơn / đã thu ở trang tạm; luật `DA_HOA_DON_TRANG_TAM` đã bỏ.
- **Khoản đi qua tiền** thành **phiếu chi / phiếu thu bên anh**. Thủ quỹ bên anh chi / thu rồi **ghi sổ**, trang điều xe đọc lại trạng thái.
- **Khoản không qua tiền** thành **bút toán chờ gửi** ở trang điều xe, đủ hai vế từng dòng bằng mã thật. Bên em giữ cho tới khi hệ anh có API bút toán (mục 5).
- Trang điều xe **thôi đẩy phong bì chứng từ** `POST /api/v1/epl-lao/vouchers`. Hệ anh không cần dựng cửa đó.

## 1. Các luồng

| Việc bên trang điều xe | Đường API bên anh | Định khoản | Trạng thái 01/10 |
|---|---|---|---|
| Màn **Vụ việc** bên anh đọc DO đã khoá | `accounting/cash-voucher-references` → trang điều xe `/api/handover/delivery-orders` | — | chạy ở máy (`ce95b3c`) |
| **Đề nghị thu** → SO, công nợ khách | `integrations/logistics/sales-orders` | Nợ 1211 / Có 708 | chạy ở máy; mọi DO đã khoá gửi được |
| Tạo đối tượng khi chưa có | `master-data/customers · suppliers · staff/upsert` | — | chạy: khách `EPLKH-…`, chủ xe `EPLCX-…`, tài xế `EPLTX-…`, nhà cung cấp `EPLNCC-…` |
| **Tạm ứng xe nhà**: thủ quỹ chi ở hệ anh | `cmpayment-receipt/save-and-commit`, "Chi trước" (DOTY 59) | Nợ 1601 / Có 1011 | chạy; ghi sổ xong (STATUS 12/13) thì xe mới xuất phát |
| **Tạm ứng xe thuê**: đứng tên chủ xe | như trên | Nợ 4022 / Có 1011 | chạy |
| **Trả chủ xe liên kết** | `save-and-commit`, "Chi khác" (DOTY 60) | Nợ 4022 / Có 1011 · 1012 · 1021 · 1022 | chạy; ghi sổ xong thì phiếu xe "đã trả chủ xe" |
| **Chi mục V – VI** (dòng quỹ trả ngay; thực tế chỉ mục V có) | `save-and-commit`, "Chi khác" (DOTY 60) | xe nhà Nợ 614 (V) · 625 (VI) / Có 1011 · xe thuê Nợ 4022 / Có 1011 | **đang làm** |
| **Tất toán tài xế**: chi bù / thu hoàn | `save-and-commit` CMP "Chi khác" (60) · CMR "Thu khác" (17) | Nợ 1601 / Có tiền · Nợ tiền / Có 1601 | **đang làm** |
| **Trả nhà cung cấp** | `save-and-commit`, "Chi khác" (DOTY 60) | Nợ 4021 / Có tiền | **đang làm** |
| **Bút toán chờ gửi** (không qua tiền) | chưa có đường bên anh | thuê xe 621/4022 · ghi nợ NCC 625 · 614 / 4021 · quyết toán tạm ứng 625/1601 | **đang làm** ở trang điều xe; chờ API bút toán |
| Đọc lại trạng thái phiếu chi / thu | `cmpayment-receipt/list`, `/{id}` | — | tự đọc lúc mở phiếu, trước khi cho xe chạy, khi bấm Cập nhật |
| **Công nợ khách**, "đã thu" của từng SO (chỉ xem) | `sales/debt/customer-detail` | — | màn Khách hàng → tab Công nợ; đề nghị thu đọc "thu một phần / đã thu" theo `OrderCode` |
| Rút phiếu chưa ghi sổ (xoá phiếu / huỷ đề nghị) | `cmpayment-receipt/delete` | — | đã ghi sổ thì không rút, báo đối soát |

Phiếu bên em gửi vẫn mang `Header.Amount` / `Header.BaseAmount` = tổng các dòng. Từ `ce95b3c`, hệ anh tự tính lại tổng header từ `Entries` (5 số lẻ, làm tròn nửa xa số 0), nên số header bên em không có thẩm quyền.

## 2. Thay đổi trên source của anh

| Repo | Nhánh | Commit | Nội dung |
|---|---|---|---|
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `465748b` | Nguồn DO: địa chỉ và khoá Logistics đọc từ cấu hình `LogisticsSource`, gửi `Authorization`. DO hiện số phiếu, tên khách; tìm theo số xe, biển số. |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `be123e9` | `ObjectService`: tạo đối tượng không gửi `IsOrganization` thì mặc định cá nhân (trước đó văng 500, `OBJ_ISORG` NULL). |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `64ce7a4` | Vụ việc: có từ khoá thì gửi `q` sang trang điều xe, tìm trên toàn bộ DO, Total đúng sau lọc; nguồn không hiểu `q` thì lọc trong trang. |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `ce95b3c` | Theo chuẩn QLSX: `CashVoucherReferenceService` + `LogisticsDeliveryOrderClient`, controller chỉ còn HTTP / claims / envelope; contract typed; **thiếu `LogisticsSource:BaseUrl` → 503**, không còn mặc định 1506. `CashVoucherHeaderTotals`: create / save / save-and-commit **tự tính tổng header** từ dòng. Dòng IV/IC hay công nợ thiếu số tiền thì giữ số header client gửi. |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `f382a9e8` | Modal Vụ việc: thoát ký tự chuỗi DO; DO hiện số phiếu, xe, tài xế; tỷ giá nhỏ hơn 1 đọc xuôi. |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `06a14189` | Phiếu thu / chi: `isCash` theo hình thức thanh toán; tài khoản tiền mặc định đọc đúng `AccountCode`, gửi kèm loại tiền; tổng xem trước tách nguyên tệ / quy đổi; phân loại theo mã loại chứng từ, không theo tên. |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `7e14421c` | Đổi hình thức thanh toán / nội tệ / loại tiền khi đã có dòng: vế tiền các dòng đổi theo tài khoản mặc định mới, dòng tự chọn giữ nguyên. Đổi quốc gia khi đã có dòng: chặn trước khi nạp danh mục. Mã DOTY gom một chỗ. Sửa câu `lo.json`. |

Chưa push nhánh nào lên GitHub.

## 3. Thay đổi dữ liệu (DB mà `appsettings.laos.json` trỏ tới — anh đã sao lưu sáng 01/10)

- **Danh mục tài khoản Lào** (qua `lao-accounts`):
  - 137 và 402 chuyển thành tài khoản **tổng hợp**;
  - thêm **1371** kho hàng, vật tư; **4021** phải trả nhà cung cấp; **4022** phải trả chủ xe liên kết.

  Quốc gia 11 nay có 497 mã. Trong hai repo không chỗ nào ghi cứng 137 / 402, ngoài tệp nạp `20260909_country_account_import_lao.sql`. Muốn trả lại: xoá 1371 / 4021 / 4022 khi chưa có bút toán, rồi `lao-accounts/update` 137 / 402 với `Posting=true`.
- **Chi phí thuê xe liên kết** chốt *Nợ 621 / Có 4022* lúc khoá phiếu (621 = ຄ່າຂົນສົ່ງ, khớp "ຄ່າຂົນສົ່ງນອກ" trong Excel của khách). Bàn giao DO có `hire.acc_code = "621/4022"`.
- **Đối tượng** `EPLKH-` / `EPLCX-` / `EPLTX-` / `EPLNCC-`; một tài xế thử `EPLTX-THU01`.
- **Hai SO thử** `TK-20261001-000162` (ຄຳຕຸ້ຍ, 905,85 USD) và `TK-20261001-000163` (ນາງ ວັນນາ, 1.676,90 USD) là **dữ liệu thử, nhờ anh huỷ**.
- **Phiếu chi thử** `1368-CTR-261001-…`, `1368-CKH-261001-00001`, `…00002`: phiếu chưa ghi sổ đã được rút.

## 4. Khi anh triển khai: đổi link, kiểm một lệnh

| Bên | Khoá | Lúc thử | Sau triển khai |
|---|---|---|---|
| Trang điều xe máy thử 8011 | `QLSX_BASE_URL`, `EPL_ACC_CODE_API` | `http://127.0.0.1:5090` | bỏ đi → về host |
| Trang điều xe máy thật 8020 | `QLSX_BASE_URL` | không đặt → gọi `https://demo-lao-api.goldensme.com` | giữ nguyên |
| API anh | `LogisticsSource:BaseUrl` | `http://127.0.0.1:8011/api/` | địa chỉ `/api/` trang điều xe thật — **bắt buộc**, thiếu thì màn Vụ việc báo 503 |
| API anh | `LogisticsSource:ApiKey` | khoá máy thử | khoá Sếp tạo ở trang điều xe thật (`POST /api/handover/tao-khoa`) |
| API anh | `LogisticsSource:Branches:<BranchId>` | không đặt | chỉ khi chi nhánh có trang điều xe riêng |
| API anh | `LogisticsSalesPush:Enabled`, `AllowedUserIds` | `[846]` | thêm `UserId` tài khoản tích hợp |
| API anh | `LogisticsSalesPush:BusinessTypeId`, `AreaId`, `PosId`, `CounterId`, `TableId` | đủ năm mã | thiếu một mã → 503 `LOGISTICS_CONFIG_REQUIRED` |
| WEB anh | `BACKOFFICE_API_URL` | `Env=laoslocal` trỏ 5090 | `Env=laos` trỏ API host |

**Kiểm:** `GET <host>/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true`:
- trả **497 mã**: host cùng DB, không làm gì thêm;
- trả **494 mã**: host trỏ DB khác. Bên em chạy `python tools/mo_ma_con_tune.py https://<API host>` để mở ba mã. Đối tượng thì lần gửi đầu bên em tự tạo.

## 5. Việc còn mở

| Việc | Trạng thái | Ai |
|---|---|---|
| **API bút toán** (không qua tiền) cho mọi bút toán chờ gửi: thuê xe 621/4022, ghi nợ nhà cung cấp 625 · 614 / 4021, quyết toán tạm ứng 625/1601 | Source chưa có chứng từ bút toán tổng hợp; định nghĩa thủ tục sổ cái chỉ nằm trong DB. Đề nghị `POST integrations/logistics/journal-entries` (+ `/reverse`), khoá chống trùng theo nguồn; hợp đồng 12.12.4 | anh duyệt, hoặc gửi định nghĩa `sp_PostTing_GeneralLedger` (hay chủ dự án cấp quyền đọc DB) để bên em viết |
| **Huỷ hai SO thử** `…162`, `…163` | dữ liệu thử | anh. Huỷ xong, anh cho bên em biết gửi lại hai DO đó thế nào: khoá chống trùng cũ `logistics:EPLLAO-<Trip.id>` vẫn còn bên anh |
| **Tài khoản tích hợp** `epl_logistics` thay token cá nhân (hết hạn 10/10/2026) | Tệp tạo đã sẵn: nhân viên `EPL-TICHHOP` chi nhánh 1368, cùng nhóm quyền người gửi hiện nay, mật khẩu chỉ nằm trong `.env`. Chủ dự án chạy tệp | chủ dự án chạy; anh thêm `UserId` vào cấu hình host |
| **Cờ phân loại loại chứng từ** ở `document-types` (công nợ / khác / "Chi trước") | WEB và API đang ghi cứng 58/60, 15/17; phiếu "Chi trước" (59) tạm ứng bên em tạo không có trong ô chọn của WEB | anh |
| **Tiền USD** (`CurrencyId` 2) đang tắt | Bên em tạm đặt `QLSX_TIEN_USD=2` | anh bật trong danh mục tiền tệ |
| **Log kiểm toán** "Đặt log sai" (`ApiAuditAutoLogFilter.cs:27`) | lệnh vẫn chạy, nhật ký không ghi | anh xem |
| Bút toán riêng cho **phí 2 %** và **trừ quá tải** xe thuê | chưa có tài khoản | anh Khampla chốt |
| Màn "Tài khoản" ở hồ sơ nhân viên bên WEB | chưa nối API `account/upsert` | anh |
| Chạy lại vòng nối kế toán với `ce95b3c` | 8 bài đạt trên `64ce7a4`; tổng header nay máy chủ tính | bên em |

## 6. Tệp và lệnh

- Hợp đồng chi tiết: `EPL_LAO_REAL/DOCS/md/HOP_DONG_API_KE_TOAN_ANH_TUNE.md` (bản Word cùng tên trong `DOCS/word/`).
- Bản đồ nối API: `EPL_LAO_REAL/DOCS/md/NOI_API_ANH_TUNE.md`.
- Mở ba mã: `EPL_LAO_REAL/tools/mo_ma_con_tune.py [địa chỉ API]`.
- Bài thử bên em (chạy lại được):
  - `kiem/thu_chi_tam_ung_ke_toan.py`
  - `kiem/thu_xe_thue_ke_toan.py`
  - `kiem/thu_tao_so_that.py`
  - `kiem/thu_ban_giao.py`
  - `kiem/thu_dinh_khoan.py`
  - `kiem/thu_tat_toan_tune.py` (đang làm, cùng phần tất toán / trả nhà cung cấp)
