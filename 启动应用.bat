@echo off
chcp 65001 >nul
echo ========================================
echo    🚀 MSKU表现分析器 - Web版本
echo ========================================
echo.
echo 正在启动应用...
echo.

python scripts\startup\run.py

if errorlevel 1 (
    echo.
    echo ❌ 启动失败，请检查：
    echo    1. Python环境是否正确安装
    echo    2. 依赖包是否已安装：pip install -r requirements.txt
    echo    3. 项目文件是否完整
    echo.
    pause
) 