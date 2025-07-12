@echo off
chcp 65001 >nul
echo ========================================
echo    MSKU表现分析器 v1.0.0
echo ========================================
echo.
echo 正在启动程序...
echo 启动后请在浏览器中访问显示的地址
echo 按 Ctrl+C 可停止程序
echo.

"MSKU分析器_v1.0.0.exe"

if errorlevel 1 (
    echo.
    echo 程序启动失败，请检查：
    echo    1. 是否有杀毒软件拦截
    echo    2. 端口是否被占用
    echo    3. 系统是否为Windows 10/11
    echo.
    pause
)
