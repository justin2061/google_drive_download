@echo off
chcp 65001
title Google Drive 快速備份工具

echo.
echo ==========================================
echo    🚀 Google Drive 快速備份工具
echo ==========================================
echo 🆕 新功能：自動轉換為 Office 格式！
echo    📝 Google文件→Word (.docx)
echo    📊 試算表→Excel (.xlsx)  
echo    📽️ 簡報→PowerPoint (.pptx)
echo ==========================================
echo.

echo 📋 可用選項：
echo.
echo 1. 🎯 執行簡化版備份工具 (支援Office轉換)
echo 2. 📖 開啟備份方案說明
echo 3. 🌐 開啟 Google Takeout
echo 4. 📁 開啟 rclone 官網
echo 5. 🔄 重新啟動 Streamlit 應用
echo 6. ❌ 退出
echo.

set /p choice="請選擇 (1-6): "

if "%choice%"=="1" (
    echo.
    echo 🚀 啟動簡化版備份工具...
    python simple_backup.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo 📖 開啟備份方案說明...
    start notepad.exe "README_簡化備份方案.md"
) else if "%choice%"=="3" (
    echo.
    echo 🌐 開啟 Google Takeout...
    start https://takeout.google.com/
) else if "%choice%"=="4" (
    echo.
    echo 📁 開啟 rclone 官網...
    start https://rclone.org/
) else if "%choice%"=="5" (
    echo.
    echo 🔄 重新啟動 Streamlit 應用...
    echo 正在終止現有進程...
    taskkill /f /im python.exe /fi "windowtitle eq streamlit*" 2>nul
    timeout /t 2 /nobreak >nul
    echo 啟動新的 Streamlit 應用...
    start cmd /k "streamlit run ui/streamlit_app.py"
) else if "%choice%"=="6" (
    echo.
    echo 👋 再見！
    exit /b
) else (
    echo.
    echo ❌ 無效選擇，請重新執行腳本
    pause
)

echo.
pause 