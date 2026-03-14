@echo off
cd /d "%~dp0"
echo Uygulama baslatiliyor...
python main.py
if errorlevel 1 (
    echo.
    echo HATA: Uygulama beklenmedik sekilde kapandi.
    pause
)
