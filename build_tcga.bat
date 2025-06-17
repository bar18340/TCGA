@echo off
echo Killing any running TCGA app...
taskkill /f /im tcga.exe >nul 2>&1

echo Cleaning previous build folders...
rmdir /s /q build
rmdir /s /q dist
del tcga.spec

echo Removing all __pycache__ folders...
for /d /r %%i in (__pycache__) do (
    if exist "%%i" (
        echo Deleting %%i
        rmdir /s /q "%%i"
    )
)

echo Starting PyInstaller build...
pyinstaller --clean --noconfirm --noconsole --icon=tcga_icon.ico ^
  --name tcga ^
  --add-data "tcga_web_app/templates;tcga_web_app/templates" ^
  --add-data "tcga_web_app/static;tcga_web_app/static" ^
  gui_launcher.py
