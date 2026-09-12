@echo off
chcp 65001 >nul
title EPL Tro ly
cd /d "%~dp0"

rem Bat may chu tro ly. Doc GEMINI_API_KEY_GT va EPL_TMS_API_TOKEN tu ..\EPL_System\.env
rem He EPL (cong 8001) phai chay truoc: tro ly khong co co so du lieu rieng.

set PY=C:\Users\zinnn\miniconda3\python.exe
if not exist "%PY%" set PY=python

echo.
echo   Dang kiem he EPL o cong 8001...
curl -s -o nul -m 5 http://127.0.0.1:8001/api/currencies
if errorlevel 1 (
  echo   [!] CHUA BAT HE EPL. Mo mot cua so khac, vao thu muc EPL_System va chay:
  echo       python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --no-access-log
  echo.
  echo   Tro ly van bat duoc, nhung moi cau hoi se bao "khong noi duoc he thong EPL".
  echo.
  pause
) else (
  echo   [OK] He EPL dang chay.
)

echo.
"%PY%" -X utf8 chay.py --cong 8090
pause
