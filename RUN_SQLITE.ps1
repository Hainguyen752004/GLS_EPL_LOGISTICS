# Chạy EPL_System bằng SQLite — KHÔNG cần máy chủ PostgreSQL.
#
# Dùng khi máy chứa PostgreSQL (192.168.1.89:1437) không tới được: mất mạng,
# máy tắt, hoặc đang ngồi ở nơi khác. Tệp `.env` chính vẫn giữ nguyên cấu hình
# PostgreSQL và KHÔNG bị sửa — chọn cấu hình nào là bằng biến `EPL_ENV_FILE`,
# mà biến đó chỉ sống trong đúng cửa sổ PowerShell này.
#
# CÁCH DÙNG:  .\RUN_SQLITE.ps1
# Rồi mở:     http://127.0.0.1:8001/static/index.html
#
# QUAY VỀ PostgreSQL: đóng cửa sổ này, mở cửa sổ mới và chạy lệnh uvicorn như
# bình thường. Không phải hoàn tác gì.
#
# LƯU Ý: tệp dữ liệu là `backend/app/epl_sqlite_lam_viec.db`, KHÔNG phải tệp
# mặc định `epl_logistics.db` — tệp mặc định là bản SQLite cũ mà bài kiểm
# `test_migration_v001` dùng để kiểm phép nâng cấp schema, ghi vào đó là làm
# bài kiểm mất dữ liệu cũ để kiểm. Dữ liệu
# nhập ở chế độ này KHÔNG chạy sang PostgreSQL và ngược lại.

param(
    [int]$Port = 8001,
    # Nạp lại dữ liệu demo trước khi chạy. Việc này XÓA và dựng lại dữ liệu
    # demo trong tệp SQLite, nên mặc định là tắt.
    [switch]$SeedLaiDuLieu
)

$ErrorActionPreference = 'Stop'
$GocDuAn = $PSScriptRoot
$Python = 'C:\Users\zinnn\miniconda3\python.exe'
$TepCauHinh = Join-Path $GocDuAn '.env.sqlite'
$TepDuLieu = Join-Path $GocDuAn 'backend\app\epl_sqlite_lam_viec.db'

if (-not (Test-Path $Python)) {
    Write-Host "Khong thay Python o: $Python" -ForegroundColor Red
    Write-Host "Sua duong dan `$Python trong tep nay cho dung may cua anh." -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path $TepCauHinh)) {
    Write-Host "Khong thay tep cau hinh: $TepCauHinh" -ForegroundColor Red
    exit 1
}

Set-Location $GocDuAn
$env:EPL_ENV_FILE = $TepCauHinh
$env:PYTHONUNBUFFERED = '1'

# Cong dang bi ai giu thi noi ro, thay vi de uvicorn bao mot dong loi kho hieu.
$dangGiu = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($null -ne $dangGiu) {
    $pidGiu = $dangGiu[0].OwningProcess
    Write-Host "Cong $Port dang bi tien trinh $pidGiu giu." -ForegroundColor Yellow
    Write-Host "  Dung no:  Stop-Process -Id $pidGiu -Force" -ForegroundColor Yellow
    Write-Host "  Hoac chay cong khac:  .\RUN_SQLITE.ps1 -Port 8003" -ForegroundColor Yellow
    exit 1
}

# Chua co tep du lieu thi dung schema roi nap demo — khong thi man hinh trong
# tron va nhin nhu ung dung hong.
$canSeed = $SeedLaiDuLieu -or (-not (Test-Path $TepDuLieu))
if ($canSeed) {
    Write-Host 'Dung co so du lieu SQLite va nap du lieu demo...' -ForegroundColor Cyan
    $ma = @'
import os, sys
os.chdir("backend/app"); sys.path.insert(0, ".")
import database, models
database.auto_migrate_db()
from services import demo_seed_service
with database.SessionLocal() as db:
    ids = demo_seed_service.seed_demo(db, reset=True, verify=True)
print("Da nap du lieu demo:")
for k, v in ids.items():
    print("   %-10s %s" % (k, v.get("delivery_order_id", "")))
'@
    & $Python -c $ma
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Nap du lieu demo that bai. Xem loi o tren.' -ForegroundColor Red
        exit 1
    }
}

Write-Host ''
Write-Host '========================================================' -ForegroundColor Green
Write-Host ' EPL_System dang chay bang SQLite (khong can PostgreSQL)' -ForegroundColor Green
Write-Host "   Mo:  http://127.0.0.1:$Port/static/index.html" -ForegroundColor Green
Write-Host '   Dung lai: bam Ctrl+C' -ForegroundColor Green
Write-Host '========================================================' -ForegroundColor Green
Write-Host ''

# `--no-access-log` khong phai de cho gon: Console cua Windows bat san QuickEdit,
# bam chuot vao cua so la no tam dung dau ra, va lenh ghi tiep se bi chan vo
# thoi han — may chu dung han du tien trinh van song. Cat gan het luong ghi thi
# gan nhu khong con cua so de ket. Xem them phan cuoi README.
& $Python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port $Port --no-access-log
