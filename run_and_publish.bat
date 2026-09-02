@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo  Sapporo Chuo-ku Collector + Publish
echo ============================================
echo.

py -3.14 sapporo_chuo_collector.py

echo.
echo ============================================
echo  Publishing to GitHub Pages...
echo ============================================

git add .
git commit -m "auto update"
git push

echo.
echo ============================================
echo  Done. Check the GitHub Pages URL.
echo ============================================
pause
