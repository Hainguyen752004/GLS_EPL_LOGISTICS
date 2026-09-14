@echo off
chcp 65001 >nul
title EPL - Trang tai xe
cd /d "%~dp0"

rem Bat trang TAI XE. Mac dinh hoi may chu da host (1506), chay vinh vien,
rem nen khong can bat gi them tren may nay.
rem Muon chay voi may chu trong nha thi doi API_GOC thanh http://127.0.0.1:8001.

set PY=C:\Users\zinnn\miniconda3\python.exe
if not exist "%PY%" set PY=python

set CONG=8080
set API_GOC=http://senvangsolutions.com:1506

echo.
echo   Dang kiem he EPL tai %API_GOC% ...
curl -s -o nul -m 10 %API_GOC%/api/drivers
if errorlevel 1 (
  echo   [!] KHONG NOI DUOC %API_GOC%
  echo       Kiem duong mang, hoac doi API_GOC trong tep nay thanh http://127.0.0.1:8001
  echo.
  pause
) else (
  echo   [OK] He EPL dang chay.
)

echo.
echo   Trang     : http://localhost:%CONG%
echo   API EPL   : %API_GOC%
echo.
"%PY%" -X utf8 chay.py --cong %CONG% --api %API_GOC%
pause
