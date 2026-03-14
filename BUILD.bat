@echo off
cd /d "%~dp0"
chcp 65001 >nul
title YouTube Indirici - EXE Olusturucu
echo.
echo ================================================
echo  YouTube Indirici v1.0.0 - EXE Build
echo ================================================
echo.
python --version >nul 2>&1
if errorlevel 1 goto nopython
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 goto installpi
goto build
:nopython
echo [HATA] Python bulunamadi.
pause
exit /b 1
:installpi
echo [BILGI] PyInstaller kuruluyor...
pip install pyinstaller --quiet
if errorlevel 1 goto pifail
goto build
:pifail
echo [HATA] PyInstaller kurulamadi.
pause
exit /b 1
:build
echo [BILGI] Eski build temizleniyor...
if exist "dist" rmdir /s /q "dist"
if exist "build_out" rmdir /s /q "build_out"
echo [BILGI] EXE olusturuluyor... (2-5 dakika)
echo.
REM PyInstaller ile build -- UPX kapali (DLL bozabilir)
python -m PyInstaller build_exe.spec --noconfirm --workpath build_out

if errorlevel 1 goto buildfail

REM Python DLL garantisi -- _internal klasorune kopyala
set DISTDIR=dist\YouTube Indirici\_internal
for /f "delims=" %%i in ('python -c "import sys; print(sys.exec_prefix)"') do set PYDIR=%%i

for %%v in (313 312 311 310) do (
    if exist "%PYDIR%\python%%v.dll" (
        echo [BILGI] python%%v.dll kopyalaniyor...
        copy "%PYDIR%\python%%v.dll" "%DISTDIR%\" /Y >nul
    )
)

REM MSVC runtime DLL'leri
for %%d in (vcruntime140.dll vcruntime140_1.dll msvcp140.dll) do (
    if exist "%SystemRoot%\System32\%%d" (
        copy "%SystemRoot%\System32\%%d" "%DISTDIR%\" /Y >nul
    )
)

echo.
echo ================================================
echo  TAMAMLANDI! dist\YouTube Indirici\ dagit.
echo ================================================
pause
exit /b 0
:buildfail
echo [HATA] Build basarisiz!
pause
exit /b 1
