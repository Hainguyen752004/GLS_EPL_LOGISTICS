# Chạy WEB GLS-QLSX bản của em ở https://localhost:5014, Env=laoslocal (= laos nhưng API trỏ 127.0.0.1:5090 ở máy em).
# Bản build nằm trong .may_thu (gls_web_out) để không đè bin của Visual Studio; nội dung (Views, wwwroot) đọc từ thư mục dự án.
# Chỉ dừng tiến trình có đúng "--urls https://localhost:5014" - không đụng Web của anh ở 5004.
# Tệp phụ (địa chỉ DB bản sao, khoá bàn giao, bản build Web, nhật ký) ở EPL_LAO_REAL\.may_thu - KHÔNG đưa lên git (có địa chỉ DB)
$sp = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.may_thu"))
if (-not (Test-Path $sp)) { "Thiếu thư mục $sp (tệp phụ của máy thử) - hỏi em chép lại"; exit 1 }
$web = "D:\Demo_Lao\GLS-QLSX-Web\Backend"
$url = "https://localhost:5014"
Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match [regex]::Escape("--urls $url") } | ForEach-Object {
  "dừng Web thử cũ (PID $($_.ProcessId))"; Stop-Process -Id $_.ProcessId -Confirm:$false
}
Start-Sleep -Milliseconds 800
$env:Env = "laoslocal"
$env:ASPNETCORE_ENVIRONMENT = "Development"
Start-Process -FilePath "dotnet" -ArgumentList (Join-Path $sp "gls_web_out\Backend.dll"), "--urls", $url, "--contentRoot", $web -WorkingDirectory $web `
  -RedirectStandardOutput (Join-Path $sp "gls_web.log") -RedirectStandardError (Join-Path $sp "gls_web.err") -WindowStyle Hidden
$ok = $false
for ($i = 0; $i -lt 120; $i++) {
  Start-Sleep -Seconds 1
  try { Invoke-WebRequest -UseBasicParsing -Uri "$url/Auth/Login" -TimeoutSec 5 | Out-Null; $ok = $true; break } catch { if ($_.Exception.Response) { $ok = $true; break } }
}
"Web thử $url lên: $ok (sau $i giây)"
Get-Content (Join-Path $sp "gls_web.err") -Tail 5
