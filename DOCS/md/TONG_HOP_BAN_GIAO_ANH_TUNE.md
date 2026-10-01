# Tổng hợp bàn giao cho anh Tune — trang điều xe EPL Lào ↔ hệ kế toán

Ngày **01/10/2026**. Bên soạn: trang điều xe **EPL_LAO_REAL** (logistics). Người đọc: **anh Tune**.

Anh đọc trang này trước. Chi tiết nằm ở:
- hợp đồng **HOP_DONG_API_KE_TOAN_ANH_TUNE** (mục 8, 10, 12.9 – 12.12);
- mục **16** trong tài liệu tổng hợp của anh: `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md`.

Mọi thứ dưới đây bên em thử trên **API và WEB chạy ở máy**. Bản host `demo-lao-api.goldensme.com` chưa merge code mới. Anh triển khai xong thì đổi link theo mục 4.

## 1. Các luồng đã nối

| Việc bên trang điều xe | Đường API bên anh | Định khoản | Trạng thái 01/10 |
|---|---|---|---|
| Màn **Vụ việc** bên anh đọc DO đã khoá | `accounting/cash-voucher-references` → trang điều xe `/api/handover/…` | — | đã sửa source (mục 2), chạy ở máy |
| **Đề nghị thu** → SO, công nợ khách | `integrations/logistics/sales-orders` | Nợ 1211 / Có 708 | đã tạo thật `TK-20261001-000162`, `…163` |
| Tạo đối tượng khi chưa có | `master-data/customers · suppliers · staff/upsert` | — | khách `EPLKH-…`, chủ xe `EPLCX-…`, tài xế `EPLTX-…` |
| **Tạm ứng xe nhà**: thủ quỹ chi ở hệ anh | `cmpayment-receipt/save-and-commit`, "Chi trước" (DOTY 59) | Nợ 1601 / Có 1011 | chạy thật; ghi sổ xong (STATUS 12/13) thì xe mới xuất phát |
| **Tạm ứng xe thuê**: đứng tên chủ xe | như trên | Nợ 4022 / Có 1011 | chạy thật sau khi mở 4022 |
| **Trả chủ xe liên kết** | `cmpayment-receipt/save-and-commit`, "Chi khác" (DOTY 60) | Nợ 4022 / Có 1011 · 1012 · 1021 · 1022 | chạy thật; ghi sổ xong thì phiếu xe thành "đã trả chủ xe" |
| Đọc lại trạng thái phiếu chi | `cmpayment-receipt/list`, `/{id}` | — | tự đọc lúc mở phiếu và trước khi cho xe chạy |
| **Công nợ khách** (chỉ xem) | `sales/debt/customer-detail` | — | màn Khách hàng → tab Công nợ |
| Rút phiếu chi chưa ghi sổ (xoá phiếu / huỷ đề nghị) | `cmpayment-receipt/delete` | — | ghi sổ rồi thì không rút, báo đối soát |

## 2. Thay đổi trên source của anh

| Repo | Nhánh | Commit | Nội dung |
|---|---|---|---|
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `465748b` | Nguồn DO: địa chỉ và khoá Logistics đọc từ cấu hình `LogisticsSource` (bỏ ghi cứng). DO hiện số phiếu, tên khách; tìm theo số xe, biển số. |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `be123e9` | `ObjectService`: tạo đối tượng không gửi `IsOrganization` thì mặc định cá nhân (trước đó văng 500, `OBJ_ISORG` NULL). |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `f382a9e8` | Modal Vụ việc: thoát ký tự chuỗi nguồn; DO hiện số phiếu, xe, tài xế; tỷ giá đọc xuôi. |

Chưa push nhánh nào lên GitHub.

## 3. Thay đổi dữ liệu (DB mà `appsettings.laos.json` trỏ tới — anh đã sao lưu sáng 01/10)

- **Danh mục tài khoản Lào** (qua `lao-accounts`):
  - 137 và 402 chuyển thành tài khoản **tổng hợp**;
  - thêm **1371** kho hàng, vật tư; **4021** phải trả nhà cung cấp; **4022** phải trả chủ xe liên kết.

  Quốc gia 11 nay có 497 mã. Trong hai repo không chỗ nào ghi cứng 137 / 402.
- **Chi phí thuê xe liên kết** chốt *Nợ 621 / Có 4022* lúc khoá phiếu (621 = ຄ່າຂົນສົ່ງ, khớp "ຄ່າຂົນສົ່ງນອກ" trong Excel của khách). Bàn giao DO có `hire.acc_code = "621/4022"`.
- Đối tượng `EPLKH-` / `EPLCX-` / `EPLTX-`, hai SO ở mục 1, các phiếu chi thử. Phiếu chi thử chưa ghi sổ đã được rút.

## 4. Khi anh triển khai: đổi link, kiểm một lệnh

| Bên | Khoá | Lúc thử | Sau triển khai |
|---|---|---|---|
| Trang điều xe máy thử 8011 | `QLSX_BASE_URL` | `http://127.0.0.1:5090` | bỏ đi → về host |
| Trang điều xe máy thật 8020 | `QLSX_BASE_URL` | không đặt → gọi `https://demo-lao-api.goldensme.com` | giữ nguyên |
| API anh | `LogisticsSource:BaseUrl` | `http://127.0.0.1:8011/api/` | địa chỉ `/api/` trang điều xe thật |
| API anh | `LogisticsSource:ApiKey` | khoá máy thử | khoá Sếp tạo ở trang điều xe thật |
| API anh | `LogisticsSalesPush:AllowedUserIds` | `[846]` | thêm `UserId` tài khoản tích hợp |

**Kiểm:** `GET <host>/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true`:
- trả **497 mã**: host cùng DB, không làm gì thêm;
- trả **494 mã**: host trỏ DB khác. Bên em chạy `python tools/mo_ma_con_tune.py https://<API host>` để mở ba mã. Đối tượng thì lần gửi đầu bên em tự tạo.

## 5. Việc còn mở

| Việc | Trạng thái | Ai |
|---|---|---|
| **Bút toán chi phí thuê xe** *Nợ 621 / Có 4022* (không qua tiền) | Source chưa có chứng từ bút toán tổng hợp; định nghĩa thủ tục sổ cái chỉ nằm trong DB. Bên em đề nghị đường `POST integrations/logistics/journal-entries` (+ `/reverse`), xem hợp đồng 12.12.4. | bên em làm khi đọc được cấu trúc sổ cái (chủ dự án cấp quyền đọc DB, hoặc anh gửi định nghĩa `sp_PostTing_GeneralLedger`) |
| **Tài khoản tích hợp** `epl_logistics` thay token cá nhân | Tệp tạo đã sẵn: nhân viên `EPL-TICHHOP` chi nhánh 1368, cùng nhóm quyền người gửi hiện nay, mật khẩu chỉ nằm trong `.env`. Chủ dự án chạy tệp. | chủ dự án chạy; anh thêm `UserId` vào cấu hình host |
| **Tiền USD** (`CurrencyId` 2) đang tắt | Bên em tạm đặt `QLSX_TIEN_USD=2` | anh bật trong danh mục tiền tệ |
| Bút toán riêng cho **phí 2 %** và **trừ quá tải** xe thuê | chưa có tài khoản | anh Khampla chốt |
| Màn "Tài khoản" ở hồ sơ nhân viên bên WEB | chưa nối API `account/upsert` | anh |

## 6. Tệp và lệnh

- Hợp đồng chi tiết: `EPL_LAO_REAL/DOCS/md/HOP_DONG_API_KE_TOAN_ANH_TUNE.md` (bản Word cùng tên trong `DOCS/word/`).
- Bảng nối API: `EPL_LAO_REAL/DOCS/md/NOI_API_ANH_TUNE.md`.
- Mở ba mã: `EPL_LAO_REAL/tools/mo_ma_con_tune.py [địa chỉ API]`.
- Bài thử bên em (chạy lại được):
  - `kiem/thu_chi_tam_ung_ke_toan.py`
  - `kiem/thu_xe_thue_ke_toan.py`
  - `kiem/thu_tao_so_that.py`
  - `kiem/thu_ban_giao.py`
  - `kiem/thu_dinh_khoan.py`
