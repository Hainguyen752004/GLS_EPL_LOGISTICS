# DỌN SẠCH DỮ LIỆU MODULE LOGISTICS EPL Ở CẢ HAI BÊN trước khi gieo lại bộ chuẩn (06/10) — CHỦ DỰ ÁN TỰ CHẠY.
#   1) DB demo anh Tune: GLS-QLSX-APIs\...\20261006_don_sach_logistics_epl.sql
#        lần 1 chỉ liệt kê · lần 2 chạy thử (xoá trong transaction rồi ROLLBACK) · lần 3 xoá thật (COMMIT)
#      GIỮ: danh mục, 4 phiếu tồn đầu kho EPL (NKTH), SO của EPL_System (DO-2026-…) — xem docstring của script.
#   2) DB bản sao máy thử 8011 (epl_lao_d7): tools\may_thu\don_may_thu.py that (tự sao lưu pg_dump trước khi xoá)
# Dừng ngay ở bước hỏng. Mật khẩu DB chỉ nằm trong biến môi trường của phiên này, không in, không ghi tệp.
#
#   powershell -ExecutionPolicy Bypass -File D:\Demo_Lao\EPL_LAO_REAL\tools\may_thu\don_sach_hai_ben.ps1             dọn thật
#   powershell -ExecutionPolicy Bypass -File D:\Demo_Lao\EPL_LAO_REAL\tools\may_thu\don_sach_hai_ben.ps1 -ChiLietKe  chỉ liệt kê hai bên
param([switch]$ChiLietKe)
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$api = 'D:\Demo_Lao\GLS-QLSX-APIs\Backend.API'
$sql = Join-Path $api 'Database\Scripts\20261006_don_sach_logistics_epl.sql'
$epl = 'D:\Demo_Lao\EPL_LAO_REAL'
$py = 'C:\Users\zinnn\miniconda3\envs\Auto\python.exe'
$nk = Join-Path $epl '.may_thu\nhat_ky_don_sach'
New-Item -ItemType Directory -Force $nk | Out-Null
$gio = Get-Date -Format 'yyyyMMdd_HHmm'

$cfg = Get-Content (Join-Path $api 'appsettings.laos.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$cs = @{}
foreach ($p in $cfg.ConnectionStrings.Master.Split(';')) { $kv = $p.Split('=', 2); if ($kv.Count -eq 2) { $cs[$kv[0].Trim().ToLower()] = $kv[1].Trim() } }
function Lay($a, $b) { if ($cs[$a]) { $cs[$a] } else { $cs[$b] } }
$server = Lay 'server' 'data source'; $db = Lay 'database' 'initial catalog'; $user = Lay 'user id' 'uid'
$env:SQLCMDPASSWORD = Lay 'password' 'pwd'

function ChaySql([string]$ten, [string]$thuc, [string]$thu, [int]$duoi) {
  $text = Get-Content $sql -Raw -Encoding UTF8
  foreach ($d in @('DECLARE @ThucHien bit = 0;', 'DECLARE @ChiChayThu bit = 0;')) { if (-not $text.Contains($d)) { throw "Không thấy dòng $d trong script" } }
  $text = $text.Replace('DECLARE @ThucHien bit = 0;', "DECLARE @ThucHien bit = $thuc;").Replace('DECLARE @ChiChayThu bit = 0;', "DECLARE @ChiChayThu bit = $thu;")
  $tmp = Join-Path $env:TEMP "don_sach_logistics_$ten.sql"
  [IO.File]::WriteAllText($tmp, $text, (New-Object Text.UTF8Encoding $false))
  $out = Join-Path $nk ("{0}_{1}.txt" -f $gio, $ten)
  Write-Host ""
  Write-Host "== DB demo anh Tune · $ten ($server · $db) ..." -ForegroundColor Cyan
  sqlcmd -S $server -d $db -U $user -i $tmp -f 65001 -b -W -s '|' -o $out | Out-Null
  $ma = $LASTEXITCODE
  Remove-Item $tmp -ErrorAction SilentlyContinue
  if ($duoi -gt 0) { Get-Content $out -Encoding UTF8 | Select-Object -Last $duoi | ForEach-Object { Write-Host "   $_" } }
  else { Get-Content $out -Encoding UTF8 | ForEach-Object { Write-Host "   $_" } }
  Write-Host ("   mã thoát {0} · nhật ký đầy đủ: {1}" -f $ma, $out)
  return $ma
}

try {
  if ((ChaySql 'lan1_liet_ke' 0 0 0) -ne 0) { Write-Host "DỪNG: lần 1 (liệt kê) hỏng — gửi em tệp nhật ký ở trên." -ForegroundColor Red; exit 1 }
  if (-not $ChiLietKe) {
    if ((ChaySql 'lan2_chay_thu_rollback' 1 1 25) -ne 0) { Write-Host "DỪNG: lần 2 (chạy thử, đã ROLLBACK — dữ liệu không đổi) hỏng. Chưa xoá gì; gửi em tệp nhật ký." -ForegroundColor Red; exit 1 }
    if ((ChaySql 'lan3_xoa_that' 1 0 25) -ne 0) { Write-Host "DỪNG: lần 3 (xoá thật) hỏng — transaction đã ROLLBACK; gửi em tệp nhật ký." -ForegroundColor Red; exit 1 }
  }
} finally { Remove-Item Env:\SQLCMDPASSWORD -ErrorAction SilentlyContinue }

Write-Host ""
Write-Host "== DB bản sao máy thử 8011 (epl_lao_d7) ..." -ForegroundColor Cyan
Push-Location $epl
try {
  if ($ChiLietKe) { & $py -X utf8 tools\may_thu\don_may_thu.py } else { & $py -X utf8 tools\may_thu\don_may_thu.py that }
  $ma = $LASTEXITCODE
} finally { Pop-Location }
if ($ma -ne 0) { Write-Host "DỪNG: dọn 8011 hỏng (mã $ma) — bên anh Tune đã dọn xong; sửa rồi chạy lại riêng: $py tools\may_thu\don_may_thu.py that" -ForegroundColor Red; exit 1 }
Write-Host ""
if ($ChiLietKe) { Write-Host "Mới chỉ liệt kê, chưa xoá gì. Chạy lại không có -ChiLietKe để dọn thật." -ForegroundColor Yellow }
else { Write-Host "XONG: đã dọn sạch hai bên. Báo em «đã dọn» để em gieo bộ dữ liệu chuẩn (tools\may_thu\gieo_bo_sach.py)." -ForegroundColor Green }
