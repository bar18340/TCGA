@echo off
REM Clean up previous builds
if exist build rd /s /q build
if exist dist rd /s /q dist
if exist *.spec del /f /q *.spec

REM Create single-file executable
echo Building single-file Data Merger Tool.exe...
pyinstaller ^
  --clean --noconfirm ^
  --onefile ^
  --windowed ^
  --name "Data_Merger_Tool" ^
  --icon=tcga_icon.ico ^
  --add-data "tcga_web_app\templates;templates" ^
  --add-data "tcga_web_app\static;static" ^
  --hidden-import=polars ^
  --hidden-import=openpyxl ^
  --hidden-import=xlsxwriter ^
  --collect-all polars ^
  --collect-all openpyxl ^
  --collect-all xlsxwriter ^
  gui_launcher.py

echo.
echo Build complete! 
echo Your single exe file is in: dist\Data_Merger_Tool.exe
pause