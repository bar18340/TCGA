set PYTHONDONTWRITEBYTECODE=1

@echo off
REM — Activate the virtualenv (batch version)
call .venv\Scripts\activate.bat

REM — Clean up previous builds
if exist build    rd /s /q build
if exist dist     rd /s /q dist
if exist tcga.spec del /f /q tcga.spec

REM — Bundle into one windowed EXE
echo Building TCGA.exe…
pyinstaller ^
  --clean --noconfirm --onedir --windowed ^
  --name tcga ^
  --icon=tcga_icon.ico ^
  --add-data "tcga_web_app\templates;templates" ^
  --add-data "tcga_web_app\static;static" ^
  gui_launcher.py

echo.
echo ✅ Build complete. Your EXE is here: dist\tcga.exe
pause
