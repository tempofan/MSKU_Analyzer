#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSKU表现分析器 - 根目录启动脚本
快速启动Web版本的MSKU表现分析器
"""

import os
import sys
import subprocess

def main():
    """主函数"""
    print("🚀 MSKU表现分析器 - Web版本")
    print("=" * 50)
    
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # 启动脚本路径
    startup_script = os.path.join(project_root, 'scripts', 'startup', 'run.py')
    
    # 检查启动脚本是否存在
    if not os.path.exists(startup_script):
        print(f"❌ 错误：找不到启动脚本 {startup_script}")
        print("请确保项目结构完整")
        input("按回车键退出...")
        return
    
    try:
        # 启动Web应用
        print("📱 正在启动Web应用...")
        subprocess.run([sys.executable, startup_script], cwd=project_root)
    except KeyboardInterrupt:
        print("\n👋 程序已停止运行")
    except Exception as e:
        print(f"❌ 启动失败：{e}")
        input("按回车键退出...")

if __name__ == '__main__':
    main() 