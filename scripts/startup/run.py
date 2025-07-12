#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSKU表现分析器 - Flask Web应用启动脚本
作者：AI Assistant
版本：1.0.0
创建时间：2024年
功能：启动Web版本的MSKU表现分析器，支持动态端口分配
"""

import sys
import os
# 添加src/web目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src', 'web'))
from app import app
import os
import pandas as pd
from datetime import datetime
import logging
import socket
import argparse
import sys

# 版本信息
VERSION = "1.0.0"
PROGRAM_NAME = "MSKU表现分析器"

def find_free_port():
    """
    查找可用的端口号
    返回一个未被占用的端口号
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def check_port_available(port):
    """
    检查指定端口是否可用
    Args:
        port (int): 要检查的端口号
    Returns:
        bool: 端口可用返回True，否则返回False
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except OSError:
        return False

def display_startup_info(port):
    """
    显示程序启动信息
    Args:
        port (int): 程序运行的端口号
    """
    print("=" * 60)
    print(f"🚀 {PROGRAM_NAME}")
    print(f"📋 版本：{VERSION}")
    print(f"📱 访问地址：http://localhost:{port}")
    print(f"🌐 局域网访问：http://你的IP地址:{port}")
    print("🔧 开发模式：已启用")
    print("📁 上传目录：./data/uploads")
    print("💡 提示：按 Ctrl+C 停止程序")
    print("=" * 60)

def test_date_range_check():
    """测试日期范围检查功能"""
    logging.info("======= 测试日期范围检查功能 =======")
    
    # 创建测试数据
    test_dates = [
        # 旺季日期
        '2023-10-15',  # 10月15日 - 应该在旺季
        '2023-11-01',  # 11月1日 - 应该在旺季
        '2023-12-31',  # 12月31日 - 应该在旺季
        '2024-01-14',  # 1月14日 - 应该在旺季
        
        # 非旺季日期
        '2023-10-14',  # 10月14日 - 不应该在旺季
        '2024-01-15',  # 1月15日 - 不应该在旺季（修改后）
        '2023-02-01',  # 2月1日 - 不应该在旺季
        '2023-09-01',  # 9月1日 - 不应该在旺季
    ]
    
    # 转换为datetime对象
    test_dates = [pd.to_datetime(date) for date in test_dates]
    
    # 定义检查函数
    def is_in_peak_season(date):
        """
        检查日期是否在旺季范围内
        旺季定义：10月15日00:00 至 次年1月14日23:59:59
        """
        month = date.month
        day = date.day
        
        # 检查是否在10月15日至次年1月14日之间
        if month == 10 and day >= 15:
            return True
        elif month == 11 or month == 12:
            return True
        elif month == 1 and day <= 14:  # 修改：1月14日或之前
            return True
        else:
            return False
    
    # 测试每个日期
    for date in test_dates:
        result = is_in_peak_season(date)
        logging.info(f"日期 {date.strftime('%Y-%m-%d')} {'在旺季内' if result else '不在旺季内'}")
    
    logging.info("======= 日期范围检查测试完成 =======")

if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description=f'{PROGRAM_NAME} v{VERSION}')
    parser.add_argument('--port', '-p', type=int, default=0, 
                       help='指定端口号 (默认: 自动分配可用端口)')
    parser.add_argument('--host', default='0.0.0.0',
                       help='指定主机地址 (默认: 0.0.0.0 - 允许局域网访问)')
    parser.add_argument('--no-debug', action='store_true',
                       help='禁用调试模式')
    parser.add_argument('--version', '-v', action='version', version=f'{PROGRAM_NAME} {VERSION}')
    
    args = parser.parse_args()
    
    try:
        # 确保必要的目录存在
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        os.makedirs(os.path.join(project_root, 'data', 'uploads'), exist_ok=True)
        os.makedirs(os.path.join(project_root, 'output', 'logs'), exist_ok=True)
        
        # 测试日期范围检查功能
        test_date_range_check()
        
        # 端口配置逻辑
        if args.port > 0:
            # 用户指定了端口，检查是否可用
            if check_port_available(args.port):
                port = args.port
                print(f"✅ 使用指定端口：{port}")
            else:
                print(f"⚠️ 端口 {args.port} 已被占用，自动寻找可用端口...")
                port = find_free_port()
                print(f"🔄 自动分配端口：{port}")
        else:
            # 自动分配端口
            port = find_free_port()
            print(f"🎯 自动分配端口：{port}")
        
        # 显示启动信息
        display_startup_info(port)
        
        # 启动Flask应用
        app.run(
            host=args.host,
            port=port,
            debug=not args.no_debug,  # 根据参数决定是否启用调试模式
            threaded=True,
            use_reloader=False  # 禁用重载器，避免端口冲突
        )
        
    except KeyboardInterrupt:
        print("\n👋 程序已停止运行")
    except Exception as e:
        print(f"❌ 程序启动失败：{e}")
        sys.exit(1)