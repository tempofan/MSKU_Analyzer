#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSKU表现分析器 - 项目结构验证脚本
验证项目重构后的文件结构是否完整
"""

import os
import sys

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    abs_path = os.path.abspath(file_path)
    if os.path.exists(abs_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (缺失) - 绝对路径: {abs_path}")
        return False

def check_directory_exists(dir_path, description):
    """检查目录是否存在"""
    abs_path = os.path.abspath(dir_path)
    if os.path.exists(abs_path) and os.path.isdir(abs_path):
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} (缺失) - 绝对路径: {abs_path}")
        return False

def main():
    """主验证函数"""
    print("🔍 MSKU表现分析器 - 项目结构验证")
    print("=" * 60)
    
    # 获取项目根目录（验证脚本在.dev目录中，需要回到上级目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    print(f"📍 项目根目录: {project_root}")
    
    all_checks_passed = True
    
    # 检查核心目录结构
    print("\n📁 核心目录结构:")
    directories = [
        ("src", "源代码目录"),
        ("src/web", "Web应用目录"),
        ("src/core", "核心逻辑目录"),
        ("scripts", "脚本目录"),
        ("scripts/build", "构建脚本目录"),
        ("scripts/startup", "启动脚本目录"),
        ("data", "数据目录"),
        ("data/uploads", "上传文件目录"),
        ("data/temp", "临时文件目录"),
        ("output", "输出目录"),
        ("output/logs", "日志目录"),
        ("docs", "文档目录"),
        (".dev", "开发工具目录")
    ]
    
    for dir_path, description in directories:
        if not check_directory_exists(dir_path, description):
            all_checks_passed = False
    
    # 检查核心文件
    print("\n📄 核心文件:")
    core_files = [
        ("src/web/app.py", "Flask Web应用主文件"),
        ("src/core/amazon_profit_analyzer_and_corrector.py", "核心分析器"),
        ("scripts/startup/run.py", "启动脚本"),
        ("scripts/build/build_exe_for_colleagues.py", "构建脚本"),
        ("scripts/build/打包为EXE.bat", "批处理构建脚本"),
        ("requirements.txt", "Python依赖文件"),
        ("start_web.bat", "批处理启动脚本"),
        ("run_web.py", "Python启动脚本")
    ]
    
    for file_path, description in core_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # 检查Web资源文件
    print("\n🌐 Web资源文件:")
    web_files = [
        ("src/web/templates/base.html", "基础模板"),
        ("src/web/templates/index.html", "主页模板"),
        ("src/web/templates/help.html", "帮助页模板"),
        ("src/web/templates/results.html", "结果页模板"),
        ("src/web/static/css/bootstrap.min.css", "Bootstrap CSS"),
        ("src/web/static/css/fontawesome.min.css", "Font Awesome CSS"),
        ("src/web/static/js/bootstrap.bundle.min.js", "Bootstrap JavaScript")
    ]
    
    for file_path, description in web_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # 检查配置文件
    print("\n⚙️ 配置文件:")
    config_files = [
        ("使用说明.md", "使用说明文档"),
        ("README_WEB版本.md", "Web版本说明"),
        ("EXE打包说明.md", "打包说明文档")
    ]
    
    for file_path, description in config_files:
        if not check_file_exists(file_path, description):
            # 配置文件缺失不算严重错误，只是警告
            print(f"⚠️ {description}: {file_path} (可选)")
    
    # 测试导入功能
    print("\n🧪 功能测试:")
    try:
        # 测试启动脚本导入
        sys.path.insert(0, os.path.join(project_root, 'src', 'web'))
        import app
        print("✅ Web应用模块导入成功")
        
        # 测试Flask应用创建
        if hasattr(app, 'app'):
            print("✅ Flask应用实例创建成功")
        else:
            print("❌ Flask应用实例未找到")
            all_checks_passed = False
            
    except ImportError as e:
        print(f"❌ Web应用模块导入失败: {e}")
        all_checks_passed = False
    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        all_checks_passed = False
    
    # 总结
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("🎉 项目结构验证通过！所有核心文件和目录都存在。")
        print("✅ 项目已成功重构，可以正常使用。")
        return 0
    else:
        print("❌ 项目结构验证失败！存在缺失的文件或目录。")
        print("🔧 请检查上述错误并修复后重新验证。")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 