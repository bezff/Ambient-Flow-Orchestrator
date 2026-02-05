@echo off
title Сборка AFO
cd /d "%~dp0"

echo Проверка PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Установка PyInstaller...
    pip install pyinstaller
)

echo.
echo Сборка AFO.exe...
echo.

pyinstaller --noconfirm ^
    --name=AFO ^
    --onefile ^
    --windowed ^
    --icon=icon.ico ^
    --add-data "afo/web;afo/web" ^
    --add-data "afo/sounds;afo/sounds" ^
    --hidden-import=win32gui ^
    --hidden-import=win32process ^
    --hidden-import=psutil ^
    afo/main.py

if exist "dist\AFO.exe" (
    echo.
    echo ========================================
    echo Готово! Файл: dist\AFO.exe
    echo ========================================
) else (
    echo.
    echo Ошибка сборки
)

pause
