# Chạy API GLS-QLSX ở 5090 từ BẢN ĐÃ COMMIT (git worktree tại HEAD của feat/HonTunedaHai) - không dính mã agent đang sửa dở.
# Build ra .may_thu\api_head_out; chạy với thư mục làm việc = Backend.API thật (đọc appsettings.laos.json có cấu hình máy, không in).
# Chỉ dừng tiến trình có đúng "--urls http://127.0.0.1:5090".
# Tệp phụ (địa chỉ DB bản sao, khoá bàn giao, bản build Web, nhật ký) ở EPL_LAO_REAL\.may_thu - KHÔNG đưa lên git (có địa chỉ DB)
$sp = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.may_thu"))
if (-not (Test-Path $sp)) { "Thiếu thư mục $sp (tệp phụ của máy thử) - hỏi em chép lại"; exit 1 }
$repo = "D:\Demo_Lao\GLS-QLSX-APIs"
$api = "$repo\Backend.API"
$wt = Join-Path $sp "wt_api_head"
$out = Join-Path $sp "api_head_out"
$url = "http://127.0.0.1:5090"
$tepKhoa = Join-Path $sp "khoa_ban_giao_8011.txt"
if (Test-Path $wt) { git -C $repo worktree remove --force $wt | Out-Null }
git -C $repo worktree add --detach $wt HEAD | Out-Null
"bản mã: $(git -C $wt log --oneline -1)"
# dừng 5090 TRƯỚC khi build: 5090 chạy từ chính thư mục $out - để chạy thì build bị khoá tệp
Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match [regex]::Escape("--urls $url") } | ForEach-Object {
  "dừng API thử cũ (PID $($_.ProcessId))"; Stop-Process -Id $_.ProcessId -Confirm:$false
}
Start-Sleep -Milliseconds 1500
$kq = dotnet build "$wt\Backend.API\Backend.API.csproj" -v q -nologo -o $out 2>&1
$kq | Select-Object -Last 3
if ($kq -match "[1-9]\d* Error\(s\)") { "BUILD LỖI - không chạy 5090"; $kq | Select-String "error" | Select-Object -First 5; exit 1 }
$env:LogisticsSource__BaseUrl = "http://127.0.0.1:8011/api/"
$env:LogisticsSource__ApiKey = (Get-Content $tepKhoa -Raw).Trim()
$env:ASPNETCORE_ENVIRONMENT = "Development"
# Trang "Tổng hợp thu chi" (02/10): bật trên máy thử; phiếu chi nhánh chi = loại 60 "Chi khác"
$env:CashVoucherCombined__Enabled = "true"
$env:CashVoucherCombined__PaymentDocumentTypeId = "60"
# SO "Nhiên liệu" cho đối tác + cấn trừ khi trả đối tác (02/10 tối): bật trên máy thử SAU khi anh áp 2 script 20261002_logistics_fuel_sales_order / 20261002_sales_debt_collection_offset
$env:LogisticsFuelSalesOrder__Enabled = "true"
$env:LogisticsFuelSalesOrder__BranchId = "1368"
$env:LogisticsFuelSalesOrder__CreatedByObjectId = "4"
$env:SalesDebtCollectionOffset__Enabled = "true"
$env:SalesDebtCollectionOffset__AllowedUserIds__0 = "846"
$env:SalesDebtCollectionOffset__CountryId = "11"
$env:SalesDebtCollectionOffset__PayableAccountRole = "PARTNER_PAYABLE"
$env:SalesDebtCollectionOffset__ReceivableAccountRole = "CUSTOMER_GOODS"
# Kho EPL trên source anh Tune (05/10): tích hợp stock-balance / stock-issues + chặn vượt tồn màn xuất Web cho chi nhánh EPL — bật SAU khi anh áp 20261005_logistics_stock_issue.sql
$env:LogisticsStock__Enabled = "true"
$env:LogisticsStock__AllowedUserIds__0 = "846"
$env:LogisticsStock__BranchId = "1368"
$env:LogisticsStock__CurrencyId = "26"
$env:LogisticsStock__AmountDecimals = "0"
# người được bấm "Cấp dầu theo phiếu đề nghị" trên Web anh Tune (tune = 846; thêm tài khoản thủ kho khi có)
$env:LogisticsStock__FuelIssueUserIds__0 = "846"
Start-Process -FilePath "dotnet" -ArgumentList (Join-Path $out "Backend.API.dll"), "--urls", $url -WorkingDirectory $api `
  -RedirectStandardOutput (Join-Path $sp "gls_api.log") -RedirectStandardError (Join-Path $sp "gls_api.err") -WindowStyle Hidden
$ok = $false
for ($i = 0; $i -lt 120; $i++) {
  Start-Sleep -Seconds 1
  try { Invoke-WebRequest -UseBasicParsing -Uri "$url/swagger/index.html" -TimeoutSec 3 | Out-Null; $ok = $true; break } catch { if ($_.Exception.Response) { $ok = $true; break } }
}
"API thử $url lên: $ok (sau $i giây)"
Get-Content (Join-Path $sp "gls_api.err") -Tail 5
