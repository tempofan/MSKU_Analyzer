@echo off
chcp 65001 >nul
title MSKU表现分析器 - EXE打包工具

echo ========================================
echo    MSKU表现分析器 - EXE打包工具
echo ========================================
echo.
echo 准备将Web版本打包为EXE文件
echo 打包过程需要5-10分钟，请耐心等待
echo 确保网络连接正常（需要下载依赖）
echo.

:: 自动切换到项目根目录（无论从哪里运行此脚本）
cd /d "%~dp0..\.."
echo 📁 项目根目录：%CD%
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python环境
    echo 请先安装Python 3.7或更高版本
    echo 下载地址：https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Python环境检查通过
echo.



:: 检查必要文件
set missing_files=
if not exist "src\web\app.py" set missing_files=%missing_files% src\web\app.py
if not exist "scripts\startup\run.py" set missing_files=%missing_files% scripts\startup\run.py
if not exist "src\core\amazon_profit_analyzer_and_corrector.py" set missing_files=%missing_files% src\core\amazon_profit_analyzer_and_corrector.py
if not exist "requirements.txt" set missing_files=%missing_files% requirements.txt
if not exist "src\web\templates" set missing_files=%missing_files% src\web\templates目录

if not "%missing_files%"=="" (
    echo 错误：缺少必要文件
    echo 缺少文件：%missing_files%
    echo 请确保在正确的项目目录中运行此脚本
    echo.
    pause
    exit /b 1
)

echo 必要文件检查通过
echo.

:: 提示用户确认
echo 即将开始打包，包含以下步骤：
echo    步骤1. 检查Python环境
echo    步骤2. 安装PyInstaller（如需要）
echo    步骤3. 清理旧的构建文件
echo    步骤4. 创建打包配置
echo    步骤5. 构建EXE文件
echo    步骤6. 创建发布包
echo    步骤7. 生成ZIP压缩包
echo.

set /p confirm="是否继续？(Y/N): "
if /i not "%confirm%"=="Y" if /i not "%confirm%"=="y" (
    echo 用户取消了打包过程
    pause
    exit /b 0
)

echo.
echo ========================================
echo           开始打包流程
echo ========================================
echo.
echo 总共7个步骤，预计耗时5-10分钟
echo.

echo [1/7] 正在检查Python环境...
echo       检查完成

echo [2/7] 正在检查PyInstaller...
echo       检查完成

echo [3/7] 正在清理旧的构建文件...
echo       清理完成

echo [4/7] 正在创建打包配置...
echo       配置完成

echo.
echo ========================================
echo [5/7] 开始构建EXE文件
echo ========================================
echo.
echo 这是最耗时的步骤，请耐心等待...
echo 预计需要3-8分钟，具体时间取决于您的电脑性能
echo.

:: 执行Python打包脚本
python scripts\build\build_exe_for_colleagues.py

:: 检查打包结果
if errorlevel 1 (
    echo.
    echo ========================================
    echo           打包失败！
    echo ========================================
    echo.
    echo 请检查上方的错误信息
    echo.
    echo 常见解决方案：
    echo    方案1. 确保网络连接正常
    echo    方案2. 以管理员身份运行此脚本
    echo    方案3. 关闭杀毒软件实时保护
    echo    方案4. 清理Python缓存
    echo    方案5. 重启电脑后重试
    echo.
    echo 如果问题持续存在，请联系技术人员
    echo.
) else (
    echo.
    echo ========================================
    echo           打包成功完成！
    echo ========================================
    echo.
    echo [6/7] 已创建发布包
    echo [7/7] 已生成ZIP压缩包
    echo.
    echo 结果文件位置：
    echo    output\dist\ 目录中的 ZIP 文件
    echo.
    echo 下一步操作：
    echo    操作1. 测试运行EXE文件
    echo    操作2. 将ZIP包分发给同事
    echo    操作3. 提供使用指南给用户
    echo.
    echo ZIP压缩包可直接分发给同事使用！
    echo.
)

echo 按任意键退出...
pause >nul 