@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem Duong dan viet bang dau / de khong bao gio bi nuot thanh ky tu tab.
echo === 1/6 Kiem nghiep vu (DB that) ===
python backend/tests/test_luong_a_z.py
if errorlevel 1 goto hong
echo.
echo === 2/6 Kiem API va tep tinh ===
python backend/tests/test_api_http.py
if errorlevel 1 goto hong
echo.
echo === 3/6 Kiem luong nhan don tu dong (goi that Gemini) ===
python backend/tests/test_nhan_don.py
if errorlevel 1 goto hong
echo.
echo === 4/6 Kiem cu phap va ban dich ===
node frontend/tests/kiem-giao-dien.js
if errorlevel 1 goto hong
echo.
echo === 5/6 Kiem ve man that ===
node frontend/tests/kiem-ve-man.js
if errorlevel 1 goto hong
echo.
echo === 6/6 Kiem hai ban in ===
node frontend/tests/kiem-ban-in.js
if errorlevel 1 goto hong
echo.
echo TAT CA XANH
goto het
:hong
echo.
echo CO BAI KIEM HONG
:het
pause
