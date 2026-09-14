@echo off
chcp 65001 >nul
title EPL Lao - may chu 8010
cd /d "%~dp0"

rem Bat may chu EPL Lao. Giao dien va API cung mot cong: http://localhost:8010
rem Ket noi PostgreSQL doc tu .env (DATABASE_URL tro vao DB epl_lao).
rem Lan dau chay tren may moi: python backend\app\seed.py  (gieo tai khoan va du lieu mau)

set PY=C:\Users\zinnn\miniconda3\python.exe
if not exist "%PY%" set PY=python

if not exist ".env" (
  echo   [!] Chua co tep .env. Chep .env.example thanh .env va dien DATABASE_URL.
  pause
  exit /b 1
)

echo.
echo   Trang     : http://localhost:8010
echo   API docs  : http://localhost:8010/api/docs
echo   Dung      : Ctrl+C
echo.
"%PY%" -X utf8 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8010 --no-access-log
pause
