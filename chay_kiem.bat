@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === 1/5 Kiem nghiep vu (DB that) ===
python backend	ests	est_luong_a_z.py
if errorlevel 1 goto hong
echo.
echo === 2/5 Kiem API va tep tinh ===
python backend	ests	est_api_http.py
if errorlevel 1 goto hong
echo.
echo === 3/5 Kiem cu phap va ban dich ===
node frontend	ests\kiem-giao-dien.js
if errorlevel 1 goto hong
echo.
echo === 4/5 Kiem ve man that ===
node frontend	ests\kiem-ve-man.js
if errorlevel 1 goto hong
echo.
echo TAT CA XANH
goto het
:hong
echo.
echo CO BAI KIEM HONG
:het
pause
