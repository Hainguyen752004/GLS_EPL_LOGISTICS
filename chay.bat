@echo off
chcp 65001 >nul
title EPL Tro ly
cd /d "%~dp0"

rem Bat may chu tro ly. Doc GEMINI_API_KEY_GT va EPL_TMS_API_TOKEN tu ..\EPL_System\.env
rem Tro ly khong co co so du lieu rieng - no hoi API cua he EPL.
rem Mac dinh hoi MAY CHU DA HOST (1506), chay vinh vien, nen khong can bat gi tren may nay.
rem Muon chay voi may chu trong nha thi doi API_GOC thanh http://127.0.0.1:8001.

set PY=C:\Users\zinnn\miniconda3\python.exe
if not exist "%PY%" set PY=python

set CONG=8090
set API_GOC=http://senvangsolutions.com:1506

echo.
echo   Dang kiem he EPL tai %API_GOC% ...
curl -s -o nul -m 10 %API_GOC%/api/currencies
if errorlevel 1 (
  echo   [!] KHONG NOI DUOC %API_GOC%
  echo       Kiem duong mang, hoac doi API_GOC trong tep nay thanh http://127.0.0.1:8001
  echo       roi bat may chu EPL tren may nay.
  echo.
  echo   Tro ly van bat duoc, nhung moi cau hoi se bao "khong noi duoc he thong EPL".
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
