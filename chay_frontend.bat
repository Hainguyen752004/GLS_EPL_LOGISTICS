@echo off
chcp 65001 >nul
title EPL - Giao dien chay rieng
cd /d "%~dp0"

rem Chay RIENG giao dien, tach khoi backend.
rem Sua dong API_GOC ben duoi neu backend nam o may khac.

set PY=C:\Users\zinnn\miniconda3\python.exe
if not exist "%PY%" set PY=python

set CONG=8080
set API_GOC=http://127.0.0.1:8001

echo.
echo   Giao dien : http://localhost:%CONG%
echo   API ve    : %API_GOC%
echo.
"%PY%" -X utf8 chay_frontend.py --cong %CONG% --api %API_GOC%
pause
