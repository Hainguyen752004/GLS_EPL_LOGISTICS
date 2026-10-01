# Hướng dẫn triển khai cho anh Tune — đưa code nối trang điều xe EPL Lào lên máy host

Ngày **01/10/2026**. Bên soạn: trang điều xe **EPL_LAO_REAL**. Người đọc: **anh Tune**.

Tài liệu này đi từng bước: sao lưu, merge, build, publish, cấu hình, đổi link, kiểm, sửa lỗi, quay lại bản cũ. Lý do và chi tiết từng thay đổi nằm ở:
- `DOCS/md/TONG_HOP_BAN_GIAO_ANH_TUNE.md` (một trang, đọc trước);
- `DOCS/md/HOP_DONG_API_KE_TOAN_ANH_TUNE.md` mục 12.9 – 12.12;
- `GLS-QLSX-APIs/docs/PHIEU-THU-CHI-DEMOLAO-TONG-HOP.md` mục 16 (tài liệu của anh).

Quy ước:
- `<…>` là chỗ anh điền. Tài liệu **không ghi** mật khẩu, token, khoá hay chuỗi kết nối nào. Giá trị bí mật chỉ đặt thẳng vào tệp cấu hình trên máy chủ.
- "Bên em" = trang điều xe EPL Lào. "Host" = `https://demo-lao-api.goldensme.com` (API, IIS `DemoLao_API`) và WEB (IIS `DemoLao_WEB`).

## 0. Tóm tắt

| Bước | Việc | Ai | Xong khi |
|---|---|---|---|
| 1 | Sao lưu DB host, thư mục hai site IIS | anh Tune | có tệp `.bak` và hai tệp `.zip` |
| 2 | Lấy hai nhánh, merge vào nhánh anh triển khai | anh Tune (chủ dự án push nhánh trước) | `git log` thấy đủ 5 commit ở mục 1.3 |
| 3 | Build, publish API rồi WEB | anh Tune | `dotnet build` 0 lỗi; hai site chạy lại |
| 4 | Cấu hình `LogisticsSalesPush`, `LogisticsSource`, tiền tệ | anh Tune | mục 4 xong |
| 5 | Mở ba mã tài khoản nếu DB host còn thiếu | bên em, chủ dự án cho phép | danh mục quốc gia 11 có 1371 / 4021 / 4022 |
| 6 | Tài khoản tích hợp | anh Tune hoặc chủ dự án | đăng nhập được; `UserId` nằm trong `AllowedUserIds` |
| 7 | Đổi link phía trang điều xe | bên em | trang điều xe gửi sang host |
| 8 | Chạy bài kiểm sau triển khai | bên em hoặc anh | không còn dòng SAI |

**Hôm nay host chưa sẵn sàng.** Bên em chạy bài kiểm (chỉ đọc) vào host lúc 14:54 ngày 01/10: **5 dòng SAI**. Đó là việc của các bước 4–6, xem mục 8.3. Trong đó có hai việc mới, chưa ghi ở tài liệu trước:
- trên host **LAK đang tắt**;
- `default-money-account` của host đang **báo lỗi**.

## 1. Trước khi triển khai

### 1.1. Cần có trong tay

| Thứ | Ai giữ | Dùng ở bước |
|---|---|---|
| Quyền publish Web Deploy tới IIS (hồ sơ `DEMO_LAO` của hai repo) | anh Tune | 3 |
| Quyền vào máy host: IIS Manager, thư mục site, SQL Server | anh Tune | 1, 4 |
| Hai nhánh `feat/HonTunedaHai` (API) và `feat/hontunedhai_Laos` (WEB) | máy bên em; **chưa push lên GitHub** | 2 |
| Địa chỉ Internet của trang điều xe Lào | chủ dự án. **Chưa có**: trang điều xe chưa ra Internet | 4.2 |
| Khoá bàn giao (`LogisticsSource:ApiKey`) | Sếp trang điều xe tạo; bên em chuyển cho anh qua kênh riêng | 4.2 |
| Mật khẩu tài khoản tích hợp | người tạo tài khoản (anh hoặc chủ dự án); chỉ đặt vào `.env` máy chủ trang điều xe | 6 |

### 1.2. Sao lưu

Làm cả ba thứ, trước khi publish.

**a. DB mà host trỏ tới.**
- Bên em đọc thấy host **khác DB** với bản API chạy ở máy bên em: host có 494 mã tài khoản, LAK đang tắt; bản ở máy có 497 mã, LAK đang bật.
- Bản sao lưu sáng 01/10 của anh là DB của `appsettings.laos.json` máy bên em. Nó **không** thay được bản sao lưu DB host.
- Trong SSMS, mở một cửa sổ truy vấn tới DB host:

```sql
BACKUP DATABASE [<tên DB host>]
TO DISK = N'<thư mục sao lưu>\<tên DB host>_20261001_truoc_trien_khai.bak'
WITH COPY_ONLY, INIT, STATS = 10;
```

`COPY_ONLY` để không làm đứt chuỗi sao lưu định kỳ của máy chủ.

**b. Thư mục hai site IIS** (gồm `appsettings*.json` và `web.config` đang chạy).
- Tìm đường dẫn: IIS Manager → Sites → `DemoLao_API` → **Basic Settings…** → Physical path. Làm lại với `DemoLao_WEB`.
- Nén bằng PowerShell trên máy host:

```powershell
Compress-Archive -Path "<physical path DemoLao_API>\*" -DestinationPath "<thư mục sao lưu>\DemoLao_API_20261001.zip"
Compress-Archive -Path "<physical path DemoLao_WEB>\*" -DestinationPath "<thư mục sao lưu>\DemoLao_WEB_20261001.zip"
```

Hai tệp `.zip` này là đường quay lại nhanh nhất (mục 10.1).

**c. Ghi lại commit đang chạy trên host**, nếu anh biết. Hai hồ sơ publish không ghi commit vào gói, nên không biết thì dùng tệp `.zip`.

### 1.3. Lấy code và merge

**Commit bên em thêm** so với `feat/DemoLao`. Ngày 01/10, `git ls-remote` cho thấy `origin/feat/DemoLao` vẫn đúng gốc: API `31c98db`, WEB `de04913f`. Nên merge là **fast-forward**, không có xung đột.

| Repo | Nhánh | Commit | Tệp | Nội dung |
|---|---|---|---|---|
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `465748b` | `CashVoucherReferenceController.cs`, `Database/Scripts/logistics-source-config.example.json` (mới) | địa chỉ + khoá Logistics từ cấu hình `LogisticsSource`, gửi `Authorization`; DO hiện số phiếu, tên khách; báo rõ 401 / 403 / 404 / 409 |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `be123e9` | `ObjectService.cs` | tạo đối tượng qua API không gửi `IsOrganization` thì mặc định cá nhân (trước văng 500, `OBJ_ISORG` NULL) |
| GLS-QLSX-APIs | `feat/HonTunedaHai` | `64ce7a4` | `CashVoucherReferenceController.cs` | có `keyword` thì gửi `q` sang trang điều xe; tìm trên toàn bộ DO; `Total` đúng sau lọc; `SearchScope=ALL` |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `f382a9e8` | `cm-source-reference-modal.js` | thoát ký tự chuỗi nguồn; DO hiện số phiếu, xe · biển số — tài xế; tỷ giá đọc xuôi |
| GLS-QLSX-Web | `feat/hontunedhai_Laos` | `06a14189` | `cm-payment-upsert.js`, `cm-receipt-upsert.js`, `CMPaymentReceiptController.cs` (BFF) | `isCash` theo hình thức thanh toán; tài khoản tiền mặc định tự điền (gửi kèm `currencyId`); `Amount` / `BaseAmount` tách đúng; phân loại theo `DOTY_AUTOID` |

**Không có script DB nào** trong 5 commit. Không phải chạy migration cho phần code này.

Những thứ **không** đi theo commit, anh đừng lấy:
- WEB `Backend/Properties/launchSettings.json`, `Backend/package-lock.json`: sửa ở máy bên em, chưa commit;
- API `Backend.API/Backend.API.csproj`: thay đổi có từ trước, bên em không đụng;
- API thư mục `docs/` (tài liệu tổng hợp của anh): đang chưa commit.

**Cách nhận nhánh — chủ dự án chọn một:**

| Cách | Bên em làm | Anh làm |
|---|---|---|
| A. Push lên GitHub (đề nghị) | chủ dự án push hai nhánh lên `origin` | `git fetch origin` |
| B. Gói `git bundle` (không đụng GitHub) | `git bundle create <tệp>.bundle 31c98db..feat/HonTunedaHai` (API), `git bundle create <tệp>.bundle de04913f..feat/hontunedhai_Laos` (WEB), gửi hai tệp | `git fetch <tệp>.bundle <nhánh>:<nhánh>` |

**Merge, API** (thay `origin/feat/HonTunedaHai` bằng `feat/HonTunedaHai` nếu dùng cách B):

```powershell
cd <thư mục GLS-QLSX-APIs>
git status
git checkout feat/DemoLao
git pull --ff-only origin feat/DemoLao
git merge --ff-only origin/feat/HonTunedaHai
git log --oneline -4
```

`git status` phải sạch trước khi checkout. Kết quả `git log` đúng:

```text
64ce7a4 Vụ việc: tìm DO theo từ khoá ở phía Logistics (q), Total đúng sau lọc
be123e9 Đối tượng tạo qua API không gửi IsOrganization → mặc định cá nhân (hết lỗi 500 OBJ_ISORG NULL)
465748b Nguồn DO cho phiếu thu chi: địa chỉ + khoá Logistics từ cấu hình, DO hiện số phiếu / tên khách
31c98db Merge pull request #151 from nguyenduykhanghuflit/feat/APIs_hoadondientudemoLao
```

**Merge, WEB:**

```powershell
cd <thư mục GLS-QLSX-Web>
git status
git checkout feat/DemoLao
git pull --ff-only origin feat/DemoLao
git merge --ff-only origin/feat/hontunedhai_Laos
git log --oneline -3
```

Kết quả đúng: `06a14189`, `f382a9e8`, rồi `de04913f`.

**`--ff-only` báo lỗi** nghĩa là `feat/DemoLao` đã có commit mới sau 01/10. Khi đó:
- chạy `git merge --no-ff origin/feat/HonTunedaHai` (WEB: `origin/feat/hontunedhai_Laos`);
- nếu có xung đột, nó chỉ nằm trong các tệp ở bảng trên; giữ cả hai phần sửa;
- build lại rồi mới publish.

Anh triển khai từ nhánh khác `feat/DemoLao` thì thay tên nhánh ở `git checkout`.

## 2. Build

Cả hai repo là .NET 6. WEB ghim SDK `6.0.428` (`global.json`, `rollForward: major`).

```powershell
cd <thư mục GLS-QLSX-APIs>
dotnet build Backend.API.sln -c Release
cd <thư mục GLS-QLSX-Web>
dotnet build Backend.sln -c Release
```

Cả hai phải kết thúc `0 Error(s)`. Cảnh báo cũ không sao.

WEB **không cần** `npm run` hay bundle. Ba tệp JS sửa được phục vụ thẳng từ `wwwroot/ViewAssets/scripts/ACC/`, kèm `asp-append-version="true"`. Nên người dùng không phải Ctrl+F5 sau khi publish.

## 3. Publish

### 3.1. Tệp appsettings đi theo gói — đọc trước khi bấm Publish

- `appsettings*.json` bị `.gitignore` nhưng **vẫn nằm trong gói publish**: Web SDK coi chúng là nội dung của dự án.
- Publish từ máy nào thì **tệp `appsettings` của máy đó ghi đè** tệp trên host. `SkipExtraFilesOnServer` chỉ giữ tệp **không có** trong gói.
- **Đừng publish từ máy bên em.** `appsettings.laos.json` ở máy bên em trỏ `LogisticsSource:BaseUrl` vào `http://127.0.0.1:8011/api/` (máy thử).

Chọn một trong hai cách. Anh quyết:
- **(a)** trước khi publish, sửa `appsettings.<Env>.json` trên máy anh cho giống host, cộng các khoá mới ở mục 4 (cách anh vẫn làm);
- **(b)** publish, rồi chép lại `appsettings*.json` từ tệp `.zip` (1.2b) và thêm khoá mới ở mục 4 thẳng trên host.

Sau publish, mở `appsettings.<Env>.json` **trên host** và soát lại theo bảng mục 4. `<Env>` là giá trị khoá `Env` mà host đang dùng; bản Lào là `laos`.

### 3.2. API trước, WEB sau

Hai bản tương thích hai chiều: WEB mới chạy được với API cũ, và ngược lại. Thứ tự chỉ để dễ khoanh lỗi.

**API:**
1. Visual Studio → chuột phải `Backend.API` → **Publish…** → chọn hồ sơ **DEMO_LAO** → **Publish**. Hồ sơ trỏ IIS `DemoLao_API`, Release, `EnableMsDeployAppOffline=true`.
2. Hoặc dòng lệnh:

```powershell
cd <thư mục GLS-QLSX-APIs>
dotnet publish Backend.API\Backend.API.csproj -c Release /p:PublishProfile=DEMO_LAO /p:Password=<mật khẩu Web Deploy>
```

Mật khẩu gõ trên dòng lệnh sẽ nằm lại trong lịch sử PowerShell, nên ưu tiên cách 1. Báo lỗi chứng chỉ máy chủ thì thêm `/p:AllowUntrustedCertificate=true`.

**WEB:** như trên, dự án `Backend` của `GLS-QLSX-Web`, hồ sơ **DEMO_LAO** (IIS `DemoLao_WEB`).

**Lúc publish site tạm ngừng** (`app_offline`), thường dưới một phút. Nếu trang điều xe gọi sang đúng lúc đó:
- **gửi SO**: bên em coi là "chưa rõ kết quả"; lần bấm sau gửi lại **đúng gói, cùng `Idempotency-Key`**, nên không ghi trùng;
- **tạo phiếu chi tạm ứng**: KT Chi phí thấy lỗi, bấm **Gửi lại**. Trước khi tạo, bên em tìm phiếu cũ theo số PTU, nên không tạo trùng.

Vẫn nên chọn lúc ít người thao tác, và báo bên em trước.

**Thấy ngay sau publish:**
- mở `https://demo-lao-api.goldensme.com/api/v1/common/GetAllCurrency` trên trình duyệt. Đường này không đòi token, phải trả `"Success":true`;
- WEB đăng nhập được, mở được màn Phiếu chi.

## 4. Cấu hình trên host

Mọi khoá dưới đây nằm trong `appsettings.<Env>.json` của **API** trên host. WEB không có khoá mới: `Env=laos` và `BACKOFFICE_API_URL` đã đúng.

Hai controller đọc cấu hình **mỗi lần gọi**. Tệp nạp với `reloadOnChange: true`, nên lưu tệp là có hiệu lực. Muốn chắc ăn thì **Recycle** app pool: IIS Manager → Application Pools → pool của `DemoLao_API` → Recycle.

### 4.1. LogisticsSalesPush — nhận SO từ trang điều xe

Mẫu: `Backend.API/Database/Scripts/logistics-sales-push-config.example.json`.

| Khoá | Ý nghĩa | Lấy ở đâu | Bí mật |
|---|---|---|---|
| `LogisticsSalesPush:Enabled` | `true` mới nhận SO; `false` hoặc thiếu → 503 `LOGISTICS_DISABLED` | đặt `true` | không |
| `LogisticsSalesPush:AllowedUserIds` | danh sách `dbo.Users.UserID` được gửi SO (không phải `OBJ_AUTOID`). Rỗng → ai cũng 403 | giữ `846` nếu còn dùng; thêm `UserId` tài khoản tích hợp **trên DB host** (mục 6) | không |
| `LogisticsSalesPush:BusinessTypeId`, `AreaId`, `PosId`, `CounterId`, `TableId` | năm mã thủ tục `sp_Logistics_CreateSalesOrder` dùng để dựng SO. Thiếu một → 503 `LOGISTICS_CONFIG_REQUIRED` | danh mục bán hàng của chi nhánh **1368** trên **DB host**. Mẫu ghi `2 / 2 / 2 / 2 / 4`: đó là số của DB demo, DB host khác thì số có thể khác | không |
| `LogisticsSalesPush:VndCurrencyId` | chỉ giữ cho tương thích; thủ tục mới tự tra tiền theo `currency_thu` | để nguyên giá trị đang có | không |

**Host đã có mục `LogisticsSalesPush`**: chỉ thêm `UserId` vào `AllowedUserIds`.

**Chưa có**: chép cả khối từ tệp mẫu, rồi thay năm mã bằng số thật của DB host. DB host cũng phải có thủ tục của `Database/Scripts/20260911_logistics_sales_push.sql`. Thiếu thủ tục thì API trả 503 `LOGISTICS_DATABASE_ERROR`.

### 4.2. LogisticsSource — màn "Vụ việc" đọc DO từ trang điều xe

Mẫu: `Backend.API/Database/Scripts/logistics-source-config.example.json`.

| Khoá | Ý nghĩa | Lấy ở đâu | Bí mật |
|---|---|---|---|
| `LogisticsSource:BaseUrl` | địa chỉ `/api/` của trang điều xe Lào, ví dụ `https://<địa chỉ trang điều xe>/api/` | chủ dự án cấp khi trang điều xe ra Internet | không |
| `LogisticsSource:ApiKey` | khoá bàn giao, gửi trong `Authorization: Bearer …` | Sếp trang điều xe tạo bằng `POST /api/handover/tao-khoa`. Khoá **chỉ hiện một lần**; bên em chuyển cho anh qua kênh riêng | **có** — không đưa lên git, không dán vào nhóm chat |
| `LogisticsSource:Branches:<BranchId>:BaseUrl`, `…:ApiKey` | chỉ dùng khi một chi nhánh có trang điều xe riêng | để trống | khoá: **có** |

Điều code làm, anh cần biết khi đặt:
- **Không theo chuyển hướng** (`AllowAutoRedirect = false`). `BaseUrl` phải là địa chỉ **cuối**: nếu `http://` chuyển sang `https://` thì phải ghi thẳng `https://`.
- Thiếu dấu `/` cuối thì code tự thêm.
- Hết giờ 15 giây; gói tối đa 2 MB. Một trang 13 DO chỉ khoảng 11 KB.
- `Branches:<BranchId>` lấy theo chi nhánh trong token của người đang mở màn Vụ việc. Chi nhánh có `BaseUrl` riêng thì dùng **cả** `ApiKey` của chi nhánh đó, không gửi khoá chung sang máy khác.
- **Chưa đặt `BaseUrl`**: code dùng `http://senvangsolutions.com:1506/api/` (EPL_System bên Việt Nam, không khoá), y như bản cũ. Màn Vụ việc khi đó hiện DO của EPL_System, **không** phải DO Lào.
- Sếp **tạo lại** khoá thì khoá cũ hết hiệu lực ngay. Màn Vụ việc báo "Logistics từ chối khoá truy cập" cho tới khi anh dán khoá mới.

**Đề nghị làm hai đợt.** Trang điều xe chưa có địa chỉ Internet nên chưa đặt được `BaseUrl`.
- **Đợt 1 (lần triển khai này):** chưa đặt `LogisticsSource`. Màn Vụ việc trên host đọc EPL_System như hôm nay. Luồng SO, phiếu chi, đối tượng và công nợ chạy được ngay.
- **Đợt 2 (khi trang điều xe ra Internet):** đặt `BaseUrl` + `ApiKey`, rồi chạy lại bài kiểm (dòng "Vụ việc", "Tìm DO", "Trạng thái bàn giao").

Mẫu khối cấu hình (đợt 2):

```json
"LogisticsSource": {
  "BaseUrl": "https://<địa chỉ trang điều xe Lào>/api/",
  "ApiKey": "<khoá bàn giao — dán trên máy chủ>"
}
```

### 4.3. Tiền tệ: LAK và USD

- Trang điều xe tra mã tiền **theo tên** (`CUR_NAME`) ở `GET /api/v1/common/GetAllCurrency`.
- Đường này **chỉ trả tiền đang bật**.

| Tiền | Bản ở máy (DB demo) | Host (đọc 01/10) | Thiếu thì hỏng gì |
|---|---|---|---|
| LAK | mã 26, đang bật | **không có trong danh sách đang bật** (chỉ có VND) | mọi phiếu chi tạm ứng và trả chủ xe bằng Kíp: lỗi `THIEU_TIEN_TE` |
| USD | mã 2, **đang tắt** | **đang tắt** | phiếu chi bằng USD (trả chủ xe thuê bằng USD) |

Hai cách, anh chọn:
1. **Bật LAK và USD** trong danh mục tiền tệ trên DB host (đề nghị);
2. hoặc anh gửi bên em `CUR_AUTOID` của từng tiền. Bên em đặt tạm `QLSX_TIEN_LAK=<mã>`, `QLSX_TIEN_USD=<mã>` trong `.env` trang điều xe. Bên em đang dùng tạm `QLSX_TIEN_USD=2` cho DB demo.

**DB host khác DB demo** nên mã tiền có thể khác. Đừng chép số 26 / 2 sang host khi chưa kiểm.

### 4.4. Tài khoản tiền mặc định (WEB tự điền)

Bản ở máy trả **1011** cho tiền mặt và **1021** cho chuyển khoản. **Host hôm nay trả lỗi** cho cả hai: HTTP 200, `Success:false`, "Hệ thống chưa xử lý được yêu cầu…", kèm mã tra cứu.
- Anh tra log API theo mã tra cứu đó.
- Bên em đoán DB host thiếu bảng cấu hình hoặc thủ tục tài khoản tiền theo quốc gia: `CMACCOUNTCONFIGCOUNTRY`, script `20260910_cash_voucher_country_account_phase1`.
- Mục 13 tài liệu của anh liệt kê các script phải có. Nếu DB host chưa chạy chúng, xin anh đối chiếu cả danh sách đó:
  - `20260908_cash_voucher_cost_assignment`;
  - `20260909_country_account` + `import_lao`;
  - `20260910_cash_voucher_country_account_phase1`;
  - `20260910_sales_debt_collection_country`;
  - `20260912_cash_voucher_source_reference`;
  - `20260911_logistics_sales_push`.

### 4.5. Kỳ tài chính

Phiếu chi cần kỳ (`FiciAutoId`) chứa ngày lập, **đang mở**. Host hôm nay có kỳ 10/2026 (mã 19) đang mở. Sang tháng 11 thì nhớ mở kỳ mới. Thiếu kỳ, trang điều xe báo `THIEU_KY` hoặc `KY_DA_DONG`.

## 5. Ba mã tài khoản 1371 / 4021 / 4022

### 5.1. Kiểm

```powershell
$api = "https://demo-lao-api.goldensme.com"
$h = @{ Authorization = "Bearer $env:QLSX_ACCESS_TOKEN" }
$r = Invoke-RestMethod "$api/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true" -Headers $h
$r.Result.Count
$r.Result | Where-Object { $_.AccCode -in '137','1371','402','4021','4022' } | Select-Object AccCode, AccParentId, AccAccountWrite
```

`$env:QLSX_ACCESS_TOKEN` là token của anh, đặt trong phiên PowerShell, không ghi ra tệp.

| Kết quả | Nghĩa | Làm gì |
|---|---|---|
| **497 mã**, có 1371 / 4021 / 4022 (`AccAccountWrite` 1), 137 / 402 có `AccAccountWrite` 0 | host cùng DB với bản ở máy | không làm gì |
| **494 mã**, không có ba mã con | host trỏ DB khác. **Đây là kết quả của host ngày 01/10** | mở ba mã (5.2) |

### 5.2. Mở ba mã

Đi qua API `accounting/lao-accounts` của anh, không sửa thẳng DB. Làm một trong hai cách:
- **bên em chạy** `python -X utf8 tools/mo_ma_con_tune.py https://demo-lao-api.goldensme.com`. Đây là lệnh **ghi**, bên em chỉ chạy khi chủ dự án cho phép. Chạy lại không sao: mã đã có thì bỏ qua;
- hoặc **anh tự làm** trên màn Tài khoản Lào của WEB (`LaoAccounts`), đúng thứ tự:

| Bước | Mã | Cha | Hạch toán (`Posting`) | Số dư | Tên ລາວ |
|---|---|---|---|---|---|
| 1 | 137 | 13 | **bỏ** (thành tài khoản tổng hợp) | giữ | giữ |
| 2 | 1371 | 137 | có | Nợ | ສາງສິນຄ້າ, ວັດຖຸ |
| 3 | 402 | 40 | **bỏ** (thành tài khoản tổng hợp) | giữ | giữ |
| 4 | 4021 | 402 | có | Có | ໜີ້ຕ້ອງສົ່ງ ຜູ້ສະໜອງ |
| 5 | 4022 | 402 | có | Có | ເຈົ້າໜີ້ເຈົ້າຂອງລົດຮ່ວມ |

**Ảnh hưởng:** 137 và 402 **không ghi sổ trực tiếp được nữa**. Trong hai repo không chỗ nào ghi cứng 137 / 402, ngoài tệp nạp `20260909_country_account_import_lao.sql`. Thủ tục SQL hay màn cũ nào ghi thẳng 137 / 402 sẽ bị từ chối "tài khoản không hợp lệ theo quốc gia".

**Đối tượng** (khách `EPLKH-…`, chủ xe `EPLCX-…`, tài xế `EPLTX-…`) không phải chép sang DB host. Lần gửi đầu, bên em tự tạo qua `master-data/*/upsert`.

## 6. Tài khoản tích hợp

**Để làm gì:** trang điều xe gọi API anh bằng một tài khoản riêng của hệ thống. Hiện bên em mượn token cá nhân. Token đó **hết hạn 10/10/2026**: hết hạn là không tạo được phiếu chi tạm ứng, nên tài xế không xuất phát được. Sếp vẫn chi tay được.

**Trạng thái 01/10:** `.env` trang điều xe chưa có `QLSX_USERNAME`, nên bên em hiểu là tệp tạo tài khoản (viết sẵn cho API ở máy, chủ dự án chạy) chưa chạy. Host khác DB nên dù tệp đó chạy ở máy, **host vẫn phải tạo riêng**.

Các bước trên host:

1. Tạo một **nhân viên** thuộc chi nhánh **1368**, ví dụ mã `EPL-TICHHOP`, tên "EPL Logistics (tích hợp)". Màn nhân viên của WEB, hoặc `POST /api/v1/master-data/staff/upsert`.
2. Tạo **tài khoản** cho nhân viên đó: `POST /api/v1/master-data/object-auth/account/upsert`. Màn "Tài khoản" ở hồ sơ nhân viên bên WEB chưa nối API này nên phải gọi thẳng.
   - `UserId = null`;
   - `ObjectAutoId` = mã nhân viên bước 1;
   - `UserName = epl_logistics` (3–20 ký tự);
   - `Password` = mật khẩu dài, ngẫu nhiên;
   - `IsActive = true`, `OrgAutoId = 1368`;
   - `GroupId` = cùng nhóm quyền với tài khoản đang gửi SO hiện nay.
3. Lấy **`UserId`**: `POST /api/v1/hr/employees/account-lookups {"UserName": "epl_logistics"}`, hoặc anh xem `dbo.Users.UserID`.
4. Thêm `UserId` đó vào `LogisticsSalesPush:AllowedUserIds` (mục 4.1).
5. **Mật khẩu:** người tạo đặt thẳng vào `.env` máy chủ trang điều xe, không gửi qua chat. Nếu phải chuyển, dùng kênh riêng rồi đổi mật khẩu sau khi đặt xong. Ba khoá:
   - `QLSX_USERNAME=epl_logistics`
   - `QLSX_PASSWORD=<mật khẩu>`
   - `QLSX_ORG_ID=1368`

   Xoá `QLSX_ACCESS_TOKEN` nếu có: biến đó được ưu tiên trước. Bên em khởi động lại trang điều xe.
6. Từ đó trang điều xe tự đăng nhập:
   - token sống 30 ngày, không có refresh token;
   - bên em đăng nhập lại khi token còn dưới 5 phút, hoặc ngay khi bị 401.

**Quyền:**
- Gửi SO xét `AllowedUserIds`. Tài khoản cũng phải gắn nhân viên (`ObjectId` trong token), nếu không thì 403 thân rỗng.
- Phiếu thu chi, tạo đối tượng, công nợ khách chỉ cần token hợp lệ. Người lập phiếu bên anh sẽ là nhân viên tích hợp.

## 7. Đổi link phía trang điều xe

Bên em làm, sau khi anh báo publish và cấu hình xong.

| Máy | Khoá | Lúc thử (bây giờ) | Sau triển khai |
|---|---|---|---|
| Trang điều xe máy thử (cổng 8011) | `QLSX_BASE_URL`, `EPL_ACC_CODE_API` | `http://127.0.0.1:5090` (API chạy ở máy bên em) | bỏ `QLSX_BASE_URL`; `EPL_ACC_CODE_API` về host |
| Trang điều xe máy thật (cổng 8020) | `QLSX_BASE_URL` | không đặt → tự gọi máy của `EPL_ACC_CODE_API` = `https://demo-lao-api.goldensme.com` | giữ nguyên, tự gọi bản mới |
| Trang điều xe (mọi máy) | `QLSX_USERNAME`, `QLSX_PASSWORD`, `QLSX_ORG_ID` | chưa đặt (mượn `EPL_ACC_CODE_TOKEN`) | đặt theo mục 6 |
| Trang điều xe (mọi máy) | `QLSX_TIEN_LAK`, `QLSX_TIEN_USD` | `QLSX_TIEN_USD=2` (DB demo) | bỏ nếu anh bật tiền; giữ, đúng mã của DB host, nếu chưa bật |
| API anh (host) | `LogisticsSource:BaseUrl`, `ApiKey` | máy thử `http://127.0.0.1:8011/api/` | đợt 2 (mục 4.2) |
| WEB anh (host) | `BACKOFFICE_API_URL` | bản ở máy dùng `Env=laoslocal` trỏ 5090 | `Env=laos` trỏ API host (đã đúng sẵn) |

Thứ tự:
1. Anh publish, cấu hình mục 4 – 6, báo bên em.
2. Bên em sửa `.env` trang điều xe theo bảng, rồi khởi động lại trang điều xe.
3. Chạy bài kiểm (mục 8). Không còn dòng SAI thì xong.

Dự phòng: hệ anh chưa dùng được thì bên em đặt `EPL_CHI_TAM_UNG=tai_cho`. Tạm ứng khi đó quay về Quỹ chi trên trang điều xe như trước 01/10.

## 8. Kiểm sau triển khai

### 8.1. Bài kiểm tự động — tools/kiem_sau_trien_khai.py

**Chỉ đọc:**
- chỉ gửi `GET`;
- hai lệnh `POST` duy nhất là **đăng nhập**, và chỉ chạy khi có biến tương ứng;
- không tạo phiếu, không gửi SO, không sửa danh mục, không tạo khoá;
- không in token, mật khẩu hay khoá;
- **không theo chuyển hướng**, giống API anh: địa chỉ chuyển hướng là báo SAI.

Cần Python 3.8 trở lên, chỉ dùng thư viện chuẩn. Chạy từ máy gọi được cả hai địa chỉ:

```powershell
cd <thư mục EPL_LAO_REAL>
python -X utf8 tools/kiem_sau_trien_khai.py https://demo-lao-api.goldensme.com https://<địa chỉ trang điều xe>
```

Anh chạy ở máy anh thì chép riêng tệp `kiem_sau_trien_khai.py`, đặt token trong phiên, rồi bỏ đọc `.env` bằng `--env NUL`:

```powershell
$env:QLSX_ACCESS_TOKEN = "<token của anh>"
python -X utf8 kiem_sau_trien_khai.py https://demo-lao-api.goldensme.com https://<địa chỉ trang điều xe> --env NUL
```

Bài đọc biến môi trường trước, rồi tới `.env` của EPL_LAO_REAL:

| Biến | Bắt buộc | Dùng cho |
|---|---|---|
| `QLSX_ACCESS_TOKEN`, hoặc `QLSX_USERNAME` + `QLSX_PASSWORD` (+ `QLSX_ORG_ID`), hoặc `EPL_ACC_CODE_TOKEN` | một trong ba | gọi API anh; cùng thứ tự ưu tiên với trang điều xe. Có `QLSX_USERNAME` thì bài kiểm luôn việc đăng nhập tài khoản tích hợp |
| `QLSX_TIEN_LAK`, `QLSX_TIEN_USD` | không | coi tiền đang tắt là "đã đặt tạm" |
| `QLSX_DOTY_CHI_TAM_UNG`, `QLSX_DOTY_TRA_CHU_XE` | không | DB host đánh số loại chứng từ khác 59 / 60 |
| `KIEM_SEP_TEN` + `KIEM_SEP_MAT_KHAU`, hoặc `KIEM_PHIEN_SEP` | không — bên em đặt | ba dòng cần phiên Sếp trang điều xe: trạng thái bàn giao, máy đang gửi sang, danh mục tài khoản |
| `KIEM_KHOA_BAN_GIAO` | không | đọc thẳng danh sách DO bằng khoá bàn giao, so với số API anh thấy |

Các dòng kiểm:

| # | Kiểm | Đúng khi | Chứng minh |
|---|---|---|---|
| 1 | API anh trả lời | `GetAllCurrency` HTTP 200, `Success:true` | site chạy |
| 2 | Đăng nhập tài khoản tích hợp | `auth/login` trả token | mục 6 xong |
| 3 | Danh mục tài khoản quốc gia 11 | có 1371 / 4021 / 4022 hạch toán được; 137 / 402 tổng hợp | mục 5 xong |
| 4 | Mã hạch toán được trên phiếu chi | có 1011, 1012, 1021, 1601, 4022, 621 | phiếu chi bên em gửi không bị từ chối vì tài khoản |
| 5 | Loại chứng từ 58 / 59 / 60 | có, là loại chi | phiếu "Chi trước", "Chi khác" lập được; WEB phân loại đúng |
| 6 | Tiền tệ LAK / USD | đang bật, hoặc đã đặt tạm `QLSX_TIEN_<MÃ>` | mục 4.3 xong |
| 7 | Tài khoản tiền mặc định (LAK) | tiền mặt và chuyển khoản đều có mã | WEB tự điền tài khoản tiền (commit `06a14189`) |
| 8 | Kỳ tài chính hôm nay | có kỳ, đang mở | phiếu chi lập được |
| 9 | Vụ việc: đọc DO từ trang điều xe | DO mã `EPLLAO-…`, hiện số phiếu | `LogisticsSource` đúng; host có `465748b` |
| 10 | Tìm DO theo từ khoá | `SearchScope=ALL`; từ khoá không có → `Total 0` | host có `64ce7a4` và trang điều xe có `q` |
| 11 | Trang điều xe trả lời | `/api/suc-khoe` 200, DB trả lời | trang điều xe chạy |
| 12 | Trang điều xe có đường bàn giao + `q` | `/openapi.json` có `/api/handover/…` và tham số `q` | trang điều xe đúng bản |
| 13 | Khoá bàn giao | danh sách DO 200; số DO bằng số API anh thấy | khoá anh dán đúng là khoá trang điều xe đang giữ |
| 14 | Trạng thái bàn giao (Sếp) | đã tạo khoá; số DO bằng số API anh thấy | API anh đọc **đúng** trang điều xe này |
| 15 | Trang điều xe gửi sang đúng API | máy đích = địa chỉ API đã nhập; có token | mục 7 xong |
| 16 | Trang điều xe đọc danh mục tài khoản | `remote` hoặc `cached` | `EPL_ACC_CODE_API`, token đúng |

Thoát mã **0** khi không có dòng SAI, **1** khi có. Dòng `--` là bỏ qua vì chưa đủ biến; mỗi dòng có một câu nói thiếu gì.

**Hai điều bài này không kiểm được bằng lệnh đọc:**
- **`be123e9`** (`IsOrganization` mặc định). Trang điều xe luôn gửi ô này nên luồng bên em không phụ thuộc. Muốn chắc, anh tạo thử một khách qua API mà không gửi `IsOrganization`: phải ra khách cá nhân, không văng 500.
- **Quyền gửi SO** (`AllowedUserIds`). Chỉ biết khi gửi thật (mục 8.4).

### 8.2. Mẫu "chạy đúng thì trông thế này" — máy bên em, 01/10/2026 15:00

API chạy ở máy `http://127.0.0.1:5090`, trang điều xe máy thử `http://127.0.0.1:8011`, có đặt phiên Sếp:

```text
KIỂM SAU TRIỂN KHAI — 01/10/2026 15:00
  API anh Tune : http://127.0.0.1:5090
  Trang điều xe: http://127.0.0.1:8011
  Token API    : EPL_ACC_CODE_TOKEN (không in)

 #   KQ   Kiểm                                    Chi tiết
 ---------------------------------------------------------------------------------------------------
 1   ✓    API anh Tune trả lời                    HTTP 200, 0,04 giây
 2   --   Đăng nhập tài khoản tích hợp            chưa đặt QLSX_USERNAME / QLSX_PASSWORD — đang dùng EPL_ACC_CODE_TOKEN
 3   ✓    Danh mục tài khoản quốc gia 11          497 mã; 1371 · 4021 · 4022 có; 137 · 402 là tổng hợp
 4   ✓    Mã hạch toán được trên phiếu chi        406 mã hạch toán; đủ 1011 · 1012 · 1021 · 1601 · 4022 · 621
 5   ✓    Loại chứng từ chi 58 / 59 / 60          58 Chi công nợ · 59 Chi trước · 60 Chi khác
 6   ✓    Tiền tệ LAK / USD                       LAK mã 26 đang bật; USD đang TẮT, trang điều xe dùng tạm QLSX_TIEN_USD=2
 7   ✓    Tài khoản tiền mặc định (LAK)           tiền mặt 1011 · chuyển khoản 1021
 8   ✓    Kỳ tài chính hôm nay                    kỳ 10/2026 (mã 19) đang mở
 9   ✓    Vụ việc: đọc DO từ trang điều xe        13 DO; dòng đầu EPLLAO-779739f4b582, số phiếu T4-0449-09/EPL
 10  SAI  Tìm DO theo từ khoá → SearchScope ALL   từ khoá 'T4-0449-09/EPL' → CURRENT_PAGE, Total 13 (có DO đầu); chữ không có → Total 13
 11  ✓    Trang điều xe trả lời                   HTTP 200, 0,03 giây, DB epl_lao_d7 trả lời
 12  ✓    Trang điều xe có đường bàn giao + q     có hai đường bàn giao; tham số q có
 13  --   Khoá bàn giao đọc được danh sách DO     chưa đặt KIEM_KHOA_BAN_GIAO
 14  ✓    Trạng thái bàn giao (Sếp)               khoá đã tạo; 13 DO bàn giao được; API anh thấy 13
 15  ✓    Trang điều xe gửi sang đúng API         gửi SO / phiếu chi sang 127.0.0.1:5090; token có
 16  ✓    Trang điều xe đọc danh mục tài khoản    cached — Danh mục 497 mã (bộ nhớ, tối đa 10 phút).

Hướng sửa:
 10  Tìm DO theo từ khoá → SearchScope ALL: API chưa chạy bản có commit 64ce7a4 (gửi q sang trang điều xe), hoặc LogisticsSource:BaseUrl trỏ vào một trang điều xe khác bản cũ. Merge + publish lại đúng nhánh (mục 1.3, 3).

Bỏ qua (chưa đủ dữ liệu để kiểm):
 2   Đăng nhập tài khoản tích hợp: Tạo tài khoản tích hợp theo mục 6, đặt hai biến vào .env trang điều xe trước 10/10 (token cá nhân hết hạn).

Tổng: 13 ✓ · 1 SAI · 2 bỏ qua
```

Đọc kết quả:
- **Dòng 10 SAI là đúng sự thật.** API ở máy bên em đang chạy bản build lúc 12:12, **trước** commit `64ce7a4` (14:17). Bài kiểm bắt được đúng chỗ đó: trang điều xe đã có `q` (dòng 12 ✓) mà API vẫn trả `CURRENT_PAGE`. Bên em không khởi động lại API ở máy.
- Trên host, sau khi publish đủ ba commit API, dòng 10 phải ra dạng: `từ khoá 'T4-0449-09/EPL' → ALL, Total 1 (có DO đầu); chữ không có → Total 0`.
- Dòng 2 và 13 là `--` vì chưa có tài khoản tích hợp, và bên em không đặt khoá bàn giao vào biến. Trên host phải đặt cả hai, và cả hai phải ✓.
- **Chạy đúng hết** là 16 dòng ✓, `Tổng: 16 ✓ · 0 SAI · 0 bỏ qua`, thoát mã 0.

### 8.3. Host hôm nay, trước triển khai — cùng bài, 01/10/2026 14:54

`https://demo-lao-api.goldensme.com` với trang điều xe máy thử, không đặt phiên Sếp. Mã tra cứu trong câu lỗi được thay bằng `<mã tra cứu>`:

```text
 #   KQ   Kiểm                                   Chi tiết
 1   ✓    API anh Tune trả lời                   HTTP 200, 0,08 giây
 2   --   Đăng nhập tài khoản tích hợp           chưa đặt QLSX_USERNAME / QLSX_PASSWORD — đang dùng EPL_ACC_CODE_TOKEN
 3   SAI  Danh mục tài khoản quốc gia 11         494 mã; 1371 · 4021 · 4022 THIẾU 1371, 4021, 4022; 137 · 402 VẪN hạch toán: 137, 402
 4   SAI  Mã hạch toán được trên phiếu chi       405 mã hạch toán; thiếu 4022
 5   ✓    Loại chứng từ chi 58 / 59 / 60         58 Chi công nợ · 59 Chi trước · 60 Chi khác
 6   SAI  Tiền tệ LAK / USD                      LAK KHÔNG có trong tiền đang bật; USD đang TẮT, trang điều xe dùng tạm QLSX_TIEN_USD=2 (đang bật: VND)
 7   SAI  Tài khoản tiền mặc định (LAK)          tiền mặt lỗi: HTTP 200 — Hệ thống chưa xử lý được yêu cầu… (<mã tra cứu>) · chuyển khoản lỗi: như trên
 8   ✓    Kỳ tài chính hôm nay                   kỳ 10/2026 (mã 19) đang mở
 9   SAI  Vụ việc: đọc DO từ trang điều xe       DO không phải của trang điều xe Lào (mã DO-2026-0047-DO01)
 10  ✓    Trang điều xe trả lời                  HTTP 200, 0,04 giây, DB epl_lao_d7 trả lời
 ...
 Tổng: 5 ✓ · 5 SAI · 5 bỏ qua
```

Mỗi dòng SAI ứng với một việc:

| Dòng | Việc | Mục |
|---|---|---|
| 3, 4 | mở 1371 / 4021 / 4022 trên DB host | 5 |
| 6 | bật LAK (và USD) trên DB host, hoặc gửi bên em mã để đặt tạm | 4.3 |
| 7 | tra log theo mã tra cứu; đối chiếu script tài khoản tiền theo quốc gia | 4.4 |
| 9 | host chưa có `465748b` và chưa đặt `LogisticsSource`: đang đọc EPL_System 1506. Hết SAI ở đợt 2 | 4.2 |

Dòng 6 (LAK tắt) và dòng 3 (494 mã) là **dữ liệu**, không phải code. Nên gần như chắc host trỏ **DB khác** DB demo bên em đã thử.

### 8.4. Kiểm bằng tay trên WEB (sau publish WEB)

Chỉ mở form và đọc. **Không bấm Lưu phiếu, Ghi sổ.**

1. **Phiếu chi → Thêm mới.**
   - Hình thức "Tiền mặt": ô tài khoản tiền tự điền **1011**.
   - Đổi sang "Chuyển khoản": tự điền **1021**.
   - Không tự điền: xem dòng 7 bài kiểm.
2. **Danh sách phiếu chi**, lọc theo loại: "Chi công nợ" (58) và "Chi khác" (60) tách đúng, kể cả khi WEB đang ở tiếng Anh hoặc tiếng Lào.
3. **Nút Vụ việc → nguồn DO** (sau đợt 2, mục 4.2):
   - mỗi dòng hiện **số phiếu** (`T4-…/EPL`), **xe · biển số — tài xế**, không hiện mã 12 ký tự;
   - gõ "T4": số dòng và Total khớp nhau, chuyển trang được;
   - mở một DO cước USD: tỷ giá đọc xuôi, dạng "1 USD = 22.000 LAK".
4. Một tên khách có dấu `<` không làm vỡ bố cục modal (commit `f382a9e8` thoát ký tự).

**Lần gửi thật đầu tiên** (ghi dữ liệu): bên em làm sau khi chủ dự án cho phép, mỗi luồng một lần.
- **Một SO:** bên anh có `TK-…`, công nợ khách hiện ở `sales/debt/customer-detail`.
- **Một phiếu chi tạm ứng** "Chi trước": thủ quỹ ghi sổ bên anh; bên em đọc thấy `STATUS` 12 hoặc 13 thì tài xế xuất phát được.

Bị 403 khi gửi SO thì xem mục 9.

## 9. Khi có lỗi — dấu hiệu → nguyên nhân → cách sửa

Thử từ **chính máy host** tới trang điều xe, mô phỏng đúng cách API anh gọi (không chuyển hướng):

```powershell
$k = $env:KHOA_BAN_GIAO
Invoke-WebRequest "https://<địa chỉ trang điều xe>/api/handover/delivery-orders?page=1&page_size=1" -Headers @{ Authorization = "Bearer $k" } -MaximumRedirection 0 -UseBasicParsing
```

`$env:KHOA_BAN_GIAO` đặt trong phiên, không ghi ra tệp. Đúng thì HTTP 200, thân JSON có `data.items`, `data.total`, `data.q`.

**Màn Vụ việc (API anh → trang điều xe):**

| Dấu hiệu | Nguyên nhân | Cách sửa |
|---|---|---|
| "Logistics từ chối khoá truy cập. Kiểm tra cấu hình LogisticsSource:ApiKey." (502) | khoá sai, thiếu, hoặc Sếp đã tạo lại khoá | bên em gửi khoá đang dùng (hoặc tạo mới), anh dán vào `ApiKey` |
| "Không tải được nguồn Logistics. Vui lòng thử lại." (502) | `BaseUrl` sai; trang điều xe tắt; host không ra được địa chỉ đó; địa chỉ chuyển hướng `http`→`https`; trang điều xe chưa tạo khoá (503 `CHUA_DAT_TOKEN`) | chạy lệnh thử ở trên từ máy host; sửa `BaseUrl` thành địa chỉ cuối `https://…/api/` |
| "Nguồn Logistics phản hồi quá thời gian." (504) | trang điều xe trả lời quá 15 giây | kiểm mạng từ host; báo bên em |
| "Nguồn Logistics trả dữ liệu không hợp lệ." / "Cấu trúc danh sách Logistics không hợp lệ." (502) | `BaseUrl` không trỏ vào `/api/` (trả HTML, trang đăng nhập…) | sửa `BaseUrl`, nhớ đuôi `/api/` |
| DO hiện mã `DO-2026-…` thay vì `EPLLAO-…` | chưa đặt `LogisticsSource:BaseUrl`, hoặc đặt sai tệp `Env`: đang đọc EPL_System 1506 | đặt `LogisticsSource` đúng tệp `appsettings.<Env>.json` của host |
| DO hiện mã 12 ký tự thay số phiếu | API chưa có `465748b` (hoặc WEB chưa có `f382a9e8`) | publish lại đúng nhánh |
| Tìm từ khoá chỉ ra dòng trong trang đang xem, Total không đổi | API chưa có `64ce7a4`, hoặc trang điều xe chạy bản cũ chưa trả `data.q` | publish lại API; bên em khởi động lại trang điều xe |
| "DO chưa hoàn tất hoặc chưa khoá ở Logistics." (409) khi mở chi tiết | kế toán Viêng Chăn vừa mở khoá phiếu đó | chọn DO khác; hỏi bên em |
| "DO không tồn tại ở Logistics." (404) | DO đã bị xoá bên trang điều xe | chọn lại |

**Trang điều xe gửi SO** (câu lỗi hiện trên màn Đề nghị thu bên em):

| Dấu hiệu | Nguyên nhân | Cách sửa |
|---|---|---|
| `QLSX_CHUA_CHO_PHEP` (403, thân rỗng) | `UserId` của token không có trong `AllowedUserIds`, hoặc tài khoản chưa gắn nhân viên | thêm `UserId` (mục 4.1); gắn nhân viên (mục 6) |
| `LOGISTICS_DISABLED` (503) | `LogisticsSalesPush:Enabled` không phải `true`, hoặc thiếu cả mục | sửa cấu hình |
| `LOGISTICS_CONFIG_REQUIRED` (503) | thiếu một trong năm mã `BusinessTypeId`…`TableId` | điền đủ theo DB host |
| `LOGISTICS_DATABASE_ERROR` (503) | DB host thiếu `sp_Logistics_CreateSalesOrder`, hoặc năm mã trỏ bản ghi không có | đối chiếu `20260911_logistics_sales_push.sql`; tra log theo `traceId`. Bên em gửi lại cùng khoá, không ghi trùng |
| `LOGISTICS_52905` (422) | khách chưa có mã bên anh, hoặc trùng / ngừng hoạt động | bên em tự tạo `EPLKH-…` trước khi gửi; còn lỗi thì xem `PUBOBJECT` của mã đó |
| `QLSX_TOKEN_HET_HAN` (401) | token mượn hết hạn (10/10), hoặc mật khẩu tích hợp đã đổi | làm mục 6; đổi mật khẩu thì bên em cập nhật `.env` |
| `QLSX_SAI_TAI_KHOAN`, `QLSX_KHONG_DANG_NHAP_DUOC` | sai tên / mật khẩu / `OrgID`, hoặc tài khoản không có trên DB host | kiểm tài khoản trên DB host |

**Phiếu chi tạm ứng, trả chủ xe:**

| Dấu hiệu | Nguyên nhân | Cách sửa |
|---|---|---|
| "Tài khoản không hợp lệ theo quốc gia của phiếu", kèm danh sách mã | DB host thiếu 1371 / 4021 / 4022 | mục 5 |
| `THIEU_TIEN_TE` | LAK / USD đang tắt bên anh, bên em chưa đặt tạm | mục 4.3 |
| `THIEU_KY`, `KY_DA_DONG` | chưa có kỳ tháng này, hoặc kỳ đã đóng | mở kỳ (mục 4.5) |
| Tạo khách / nhà cung cấp / nhân viên văng 500 "Cannot insert the value NULL into column 'OBJ_ISORG'" | API chưa có `be123e9` | publish lại API |

**WEB:**

| Dấu hiệu | Nguyên nhân | Cách sửa |
|---|---|---|
| Tài khoản tiền không tự điền | WEB chưa có `06a14189`; hoặc `default-money-account` lỗi (dòng 7 bài kiểm) | publish lại WEB; mục 4.4 |
| Lọc "Chi công nợ" / "Chi khác" ra rỗng khi đổi ngôn ngữ | WEB chưa có `06a14189` (còn phân loại theo tên) | publish lại WEB |

**Site không chạy sau publish:**

| Dấu hiệu | Nguyên nhân | Cách sửa |
|---|---|---|
| HTTP 500.30 / 502.5, hoặc mọi đường trả 500 | `appsettings` trên host bị ghi đè bằng tệp máy khác: chuỗi kết nối sai, `Env` sai | chép lại `appsettings*.json` từ `.zip` (1.2b), thêm khoá mục 4, Recycle |
| Dòng 1 bài kiểm SAI "chuyển hướng" | gọi `http://` mà host ép `https://` | dùng `https://` |

## 10. Quay lại bản cũ

### 10.1. Code

**Nhanh nhất — từ tệp `.zip`:**
1. IIS Manager → Sites → `DemoLao_API` → **Stop**.
2. Giải nén `DemoLao_API_20261001.zip` đè lên physical path.
3. **Start**. Làm lại với `DemoLao_WEB` nếu cần.

**Từ git** (khi không có `.zip`):

```powershell
cd <thư mục GLS-QLSX-APIs>
git checkout -b quay-lai-31c98db 31c98db
dotnet build Backend.API.sln -c Release
```

Rồi publish hồ sơ `DEMO_LAO` như mục 3.2. WEB: `git checkout -b quay-lai-de04913f de04913f`, publish.

Đã push merge lên `feat/DemoLao` mà muốn gỡ hẳn: `git revert --no-edit 64ce7a4 be123e9 465748b` (API), `git revert --no-edit 06a14189 f382a9e8` (WEB). Lệnh này tạo commit đảo, anh hoặc chủ dự án quyết có làm không.

**Cấu hình:** `LogisticsSource` để nguyên cũng được, code cũ không đọc khoá này. `UserId` thêm vào `AllowedUserIds` cũng không hại gì.

**Quay lại API cũ thì luồng bên em ra sao:**

| Luồng | Với API cũ |
|---|---|
| Gửi SO, phiếu chi tạm ứng, trả chủ xe, công nợ khách | vẫn chạy: các đường này không đổi trong 5 commit |
| Tạo đối tượng | vẫn chạy: bên em luôn gửi `IsOrganization` |
| Màn Vụ việc | quay về đọc EPL_System 1506, không có DO Lào |
| Tìm DO | lọc trong trang như cũ |

### 10.2. Dữ liệu

- **Ba mã tài khoản:**
  - trả lại được khi **chưa có bút toán** dùng 1371 / 4021 / 4022;
  - xoá ba mã, rồi `lao-accounts/update` cho 137 và 402 với `Posting=true`;
  - đã có bút toán thì không xoá: đối soát trước.
- **Đối tượng** `EPLKH-` / `EPLCX-` / `EPLTX-`: để nguyên, không ảnh hưởng gì.
- **SO** `TK-20261001-000162` và `…163` chỉ có trên DB demo, là SO thử. Anh huỷ hoặc bỏ qua khi đối soát.
- Cách chắc nhất vẫn là khôi phục tệp `.bak` (1.2a). Nhưng làm vậy là mất mọi chứng từ ghi sau lúc sao lưu.

### 10.3. Phía trang điều xe

Bên em đặt lại `QLSX_BASE_URL` / `EPL_ACC_CODE_API` như trước, rồi khởi động lại.

Hệ anh tạm không dùng được thì bên em đặt `EPL_CHI_TAM_UNG=tai_cho`: Quỹ chi tạm ứng ngay trên trang điều xe. Gửi SO thì chờ, không mất gì: lần gửi sau đi đúng gói, cùng khoá.

## 11. Điểm cần chủ dự án hoặc anh Tune quyết

| # | Việc | Ai quyết | Đề nghị của bên em |
|---|---|---|---|
| 1 | Đưa hai nhánh cho anh: push GitHub hay gói `git bundle` | chủ dự án | push (cách A, mục 1.3) |
| 2 | Merge vào `feat/DemoLao` hay nhánh khác; lúc nào publish (site tạm ngừng khi publish) | anh Tune | `feat/DemoLao`, lúc ít thao tác |
| 3 | Cách giữ `appsettings` khi publish (mục 3.1) | anh Tune | sửa tệp máy anh trước khi publish |
| 4 | Host trỏ DB khác DB demo: đó là DB thật của EPL Lào, hay nên trỏ về DB demo đã thử | anh Tune + chủ dự án | anh xác nhận DB; mọi việc mục 4 – 6 làm trên đúng DB đó |
| 5 | Mở ba mã trên DB host: bên em chạy `mo_ma_con_tune.py` hay anh tự làm trên màn Tài khoản Lào | chủ dự án cho phép | bên em chạy, anh xem lại |
| 6 | Bật LAK, USD trên DB host, hay bên em đặt tạm `QLSX_TIEN_*` | anh Tune | bật |
| 7 | Lỗi `default-money-account` trên host | anh Tune | tra log theo mã tra cứu; đối chiếu script mục 4.4 |
| 8 | Tài khoản tích hợp trên host: ai tạo, ai giữ mật khẩu; **hạn 10/10** | anh Tune hoặc chủ dự án | anh tạo, đặt thẳng mật khẩu vào `.env` máy chủ trang điều xe |
| 9 | Năm mã `LogisticsSalesPush` của chi nhánh 1368 trên DB host | anh Tune | lấy từ danh mục bán hàng DB host |
| 10 | Làm hai đợt (`LogisticsSource` sau, khi trang điều xe ra Internet) | chủ dự án | hai đợt (mục 4.2) |
| 11 | Ai giữ và chuyển khoá bàn giao | chủ dự án | Sếp tạo, bên em chuyển anh qua kênh riêng, không qua nhóm chat |
