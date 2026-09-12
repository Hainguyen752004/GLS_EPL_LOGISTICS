@echo off
chcp 65001 >nul
title EPL - Lam tuoi du lieu demo
cd /d "%~dp0"

rem Chay truoc buoi demo, va sau khi tu dieu phoi chuyen moi neu hom sau con muon bam moc.
rem An toan de chay lai nhieu lan: no dat lai moc chu khong cong don.

set PY=C:\Users\zinnn\miniconda3\python.exe
if not exist "%PY%" set PY=python

echo.
echo   Dang lam tuoi moc thoi gian cua bo du lieu demo...
echo.
"%PY%" -X utf8 backend\scripts\keo_dai_khung_demo.py --den 2026-09-30 --ghi
if errorlevel 1 (
  echo.
  echo   [!] KHONG CHAY DUOC. Thuong la do khong noi duoc may chu du lieu.
  echo       Kiem DATABASE_URL trong .env va duong mang toi 103.9.159.8
)
echo.
pause
