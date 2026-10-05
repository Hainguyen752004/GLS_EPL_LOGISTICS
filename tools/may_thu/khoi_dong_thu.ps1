# Khởi động lại HAI MÁY THỬ của em trên bản sao DB: 8011 (điều xe, epl_lao_d7) · 8031 (kế toán, epl_ketoan_d7).
# Chỉ dừng tiến trình mà dòng lệnh có đúng "--port 8011" / "--port 8031" - không bao giờ đụng 8020 / 8030 của anh.
param([string[]]$Cong = @("8011", "8031"))
# Tệp phụ (địa chỉ DB bản sao, khoá bàn giao, bản build Web, nhật ký) ở EPL_LAO_REAL\.may_thu - KHÔNG đưa lên git (có địa chỉ DB)
$sp = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.may_thu"))
if (-not (Test-Path $sp)) { "Thiếu thư mục $sp (tệp phụ của máy thử) - hỏi em chép lại"; exit 1 }
$py = "C:\Users\zinnn\miniconda3\envs\Auto\python.exe"
$may = @{
  "8011" = @{ Thu = "D:\Demo_Lao\EPL_LAO_REAL"; Url = "url_epl_lao_d7.txt"; Kiem = "/api/lien-thong/dia-chi" };
  "8031" = @{ Thu = "D:\Demo_Lao\EPL_KETOAN";   Url = "url_epl_ketoan_d7.txt"; Kiem = "/api/suc-khoe" }
}
foreach ($c in $Cong) {
  if ($c -notin @("8011", "8031")) { "BỎ QUA cổng $c - chỉ khởi động lại máy thử 8011 / 8031"; continue }
  $m = $may[$c]
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "--port $c(\s|$)" } | ForEach-Object {
    "dừng máy thử $c (PID $($_.ProcessId))"; Stop-Process -Id $_.ProcessId -Confirm:$false
  }
  Start-Sleep -Milliseconds 800
  $env:DATABASE_URL = (Get-Content (Join-Path $sp $m.Url) -Raw).Trim()
  # 01/10: máy thử điều xe gọi API anh Tune CHẠY Ở MÁY EM (5090) - chủ dự án: nối thử thì gọi localhost
  # chủ dự án 01/10 chiều: tạm quên demo-lao-api - danh mục tài khoản (EPL_ACC_CODE_API) cũng đọc từ API ở máy
  # 02/10: API bút toán bên anh Tune đã áp script và chạy thật (GL021020263/264) - máy thử 8011 bật gửi bút toán
  # 05/10: bỏ kho tạm — kho EPL là kho anh Tune (API 5090, màn Quản lý kho Web 5014); KHO_NGUON=kho_tam để quay lui
  if ($c -eq "8011") { $env:QLSX_BASE_URL = "http://127.0.0.1:5090"; $env:EPL_ACC_CODE_API = "http://127.0.0.1:5090"; $env:QLSX_GUI_BUT_TOAN = "1"; $env:KHO_NGUON = "qlsx"; $env:QLSX_WEB_URL = "https://localhost:5014" }
  else { Remove-Item Env:KHO_NGUON -ErrorAction SilentlyContinue; Remove-Item Env:QLSX_WEB_URL -ErrorAction SilentlyContinue; Remove-Item Env:QLSX_BASE_URL -ErrorAction SilentlyContinue; Remove-Item Env:EPL_ACC_CODE_API -ErrorAction SilentlyContinue; Remove-Item Env:QLSX_GUI_BUT_TOAN -ErrorAction SilentlyContinue }
  Start-Process -FilePath $py -ArgumentList '-X','utf8','-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',$c,'--no-access-log' `
    -WorkingDirectory $m.Thu -RedirectStandardOutput (Join-Path $sp "may_$c.log") -RedirectStandardError (Join-Path $sp "may_$c.err") -WindowStyle Hidden
  $ok = $false
  for ($i = 0; $i -lt 90; $i++) { Start-Sleep -Seconds 1; try { Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:$c" + $m.Kiem) -TimeoutSec 2 | Out-Null; $ok = $true; break } catch { if ($_.Exception.Response) { $ok = $true; break } } }
  "máy thử $c lên: $ok (sau $i giây)"
  Get-Content (Join-Path $sp "may_$c.err") -Tail 3
}
