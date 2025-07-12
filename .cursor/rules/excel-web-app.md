description: 🚀 专门针对Excel数据处理Web应用程序的通用开发规范，基于Flask框架，提供统一的项目结构、样式和开发模式，包含动态端口分配等完整配置
globs: 
  - "*.py"
  - "*.html" 
  - "*.css"
  - "*.js"
  - "*.md"
  - "requirements.txt"
  - "*.bat"
  - "*.sh"
  - "*.env"
  - "config.py"
---

# 📊 Excel数据处理Web应用程序开发规范

## 🏗️ 项目结构标准

### 📁 目录结构规范
```
project_root/
├── 📁 src/                          # 源代码目录
│   ├── 📁 web/                      # Web应用层
│   │   ├── 📄 app.py               # Flask主应用文件
│   │   ├── 📄 config.py            # 配置文件
│   │   ├── 📁 templates/           # Jinja2模板目录
│   │   │   ├── 📄 base.html        # 基础模板（必须）
│   │   │   ├── 📄 index.html       # 主页面（上传页面）
│   │   │   ├── 📄 results.html     # 结果展示页面
│   │   │   └── 📄 help.html        # 帮助说明页面
│   │   └── 📁 static/              # 静态资源目录
│   │       ├── 📁 css/             # 样式文件
│   │       │   ├── 📄 bootstrap.min.css  # Bootstrap框架
│   │       │   └── 📄 fontawesome.min.css # 图标字体
│   │       └── 📁 js/              # JavaScript文件
│   └── 📁 core/                     # 核心业务逻辑层
│       └── 📄 *.py                 # 数据处理核心模块
├── 📁 data/                         # 数据目录
│   ├── 📁 uploads/                 # 用户上传文件
│   └── 📁 samples/                 # 示例文件
├── 📁 output/                       # 输出目录
│   ├── 📁 results/                 # 处理结果文件
│   └── 📁 logs/                    # 日志文件
├── 📁 scripts/                      # 脚本工具
├── 📁 docs/                         # 文档目录
├── 📄 requirements.txt             # 依赖包清单
├── 📄 .env.example                 # 环境变量示例
├── 📄 启动应用.bat                 # Windows启动脚本
└── 📄 start.sh                     # Linux/Mac启动脚本
```

### 🎯 文件命名约定
- **Python文件**: 使用下划线命名法 (`snake_case`)
- **模板文件**: 使用小写+下划线 (`template_name.html`)
- **静态文件**: 使用小写+连字符 (`style-name.css`)
- **目录名**: 使用小写+下划线
- **配置文件**: 使用标准名称 (`config.py`, `.env`)

## 🐍 Python后端开发规范

### 📋 核心依赖包标准
```python
# requirements.txt 标准结构
# Flask核心框架
Flask==2.3.3
Werkzeug==3.1.3
Jinja2==3.1.6
MarkupSafe==3.0.2
click==8.2.1
blinker==1.9.0
itsdangerous==2.2.0

# Excel数据处理必备
pandas==2.2.3          # 数据处理核心
numpy==2.2.6           # 数值计算
openpyxl==3.1.5        # Excel读写(.xlsx)
xlrd==2.0.1            # Excel读取(.xls)

# 日期时间处理
python-dateutil==2.9.0.post0
pytz==2025.2
tzdata==2025.2

# 环境变量和配置管理
python-dotenv==1.0.0   # .env文件支持

# 可选：数据可视化
matplotlib==3.10.3     # 图表生成
seaborn==0.13.2        # 统计图表

# 工具库
chardet==5.2.0         # 编码检测
tabulate==0.9.0        # 表格格式化
```

### ⚙️ 动态端口配置标准
```python
# config.py - 配置管理标准模板
import os
import socket
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """📁 基础配置类"""
    
    # 🔐 安全配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'excel-web-app-secret-key-2024'
    
    # 📁 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'data/uploads'
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    # 🌐 服务器配置
    HOST = os.environ.get('FLASK_HOST') or '127.0.0.1'
    PORT = int(os.environ.get('FLASK_PORT') or 0)  # 0表示自动分配
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # 📝 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'output/logs/app.log'
    
    @staticmethod
    def find_free_port(start_port=5000, max_attempts=100):
        """🔍 查找可用端口"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        raise RuntimeError(f"❌ 无法在{start_port}-{start_port + max_attempts}范围内找到可用端口")
    
    @classmethod
    def get_port(cls):
        """🌐 获取应用端口"""
        if cls.PORT == 0:
            # 动态分配端口
            return cls.find_free_port()
        else:
            # 使用指定端口
            return cls.PORT

class DevelopmentConfig(Config):
    """🔧 开发环境配置"""
    DEBUG = True
    
class ProductionConfig(Config):
    """🚀 生产环境配置"""
    DEBUG = False
    
class TestingConfig(Config):
    """🧪 测试环境配置"""
    TESTING = True
    DEBUG = True

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
```

### 🔧 Flask应用结构模式
```python
# app.py 标准结构模板
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import os
import sys
import pandas as pd
from werkzeug.utils import secure_filename
from datetime import datetime
import traceback
import logging
import webbrowser
import threading
import time
from config import config

class ExcelWebApp:
    """📊 Excel数据处理Web应用基类"""
    
    def __init__(self, app_name="ExcelProcessor", config_name=None):
        # 获取配置
        config_name = config_name or os.environ.get('FLASK_ENV', 'default')
        self.config = config[config_name]
        
        # 创建Flask应用
        self.app = Flask(__name__, 
                        template_folder='templates',
                        static_folder='static')
        self.app.config.from_object(self.config)
        
        # 初始化
        self.setup_logging()
        self.setup_directories()
        self.register_routes()
        self.register_error_handlers()
    
    def setup_logging(self):
        """📝 日志配置（兼容EXE环境）"""
        try:
            # 获取日志目录
            if hasattr(sys, '_MEIPASS'):
                # EXE环境
                exe_dir = os.path.dirname(sys.executable)
                log_dir = os.path.join(exe_dir, 'logs')
            else:
                # 开发环境
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                log_dir = os.path.join(project_root, 'output', 'logs')
            
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'app.log')
            
            # 配置日志
            logging.basicConfig(
                level=getattr(logging, self.config.LOG_LEVEL),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout),
                    logging.FileHandler(log_file, encoding='utf-8')
                ]
            )
            logging.info(f"📝 日志文件路径: {log_file}")
        except Exception as e:
            logging.basicConfig(level=logging.INFO,
                              format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                              handlers=[logging.StreamHandler(sys.stdout)])
            logging.warning(f"⚠️ 无法创建日志文件: {str(e)}")
    
    def setup_directories(self):
        """📁 设置应用目录"""
        # 上传目录
        if hasattr(sys, '_MEIPASS'):
            exe_dir = os.path.dirname(sys.executable)
            upload_folder = os.path.join(exe_dir, 'uploads')
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            upload_folder = os.path.join(project_root, 'data', 'uploads')
        
        os.makedirs(upload_folder, exist_ok=True)
        self.app.config['UPLOAD_FOLDER'] = upload_folder
    
    def register_routes(self):
        """🛣️ 注册路由"""
        @self.app.route('/')
        def index():
            """🏠 主页面 - 文件上传界面"""
            file_requirements = self.get_file_requirements()
            return render_template('index.html', 
                                 file_requirements=file_requirements)
        
        @self.app.route('/upload', methods=['POST'])
        def upload_files():
            """📤 文件上传处理"""
            return self.handle_file_upload()
        
        @self.app.route('/download/<filename>')
        def download_file(filename):
            """⬇️ 文件下载"""
            return self.handle_file_download(filename)
        
        @self.app.route('/help')
        def help_page():
            """❓ 帮助页面"""
            return render_template('help.html')
        
        @self.app.route('/health')
        def health_check():
            """💓 健康检查接口"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })
    
    def register_error_handlers(self):
        """🛡️ 注册错误处理器"""
        @self.app.errorhandler(413)
        def too_large(e):
            flash('❌ 文件过大，请选择小于50MB的文件', 'error')
            return redirect(url_for('index')), 413
        
        @self.app.errorhandler(404)
        def not_found(e):
            return render_template('error.html', 
                                 error_code=404, 
                                 error_message='页面未找到'), 404
        
        @self.app.errorhandler(500)
        def internal_error(e):
            logging.error(f"❌ 内部服务器错误: {str(e)}")
            return render_template('error.html', 
                                 error_code=500, 
                                 error_message='内部服务器错误'), 500
    
    def get_file_requirements(self):
        """📋 定义文件上传要求 - 子类需重写"""
        return {}
    
    def handle_file_upload(self):
        """📤 处理文件上传逻辑 - 子类需重写"""
        flash('⚠️ 请实现handle_file_upload方法', 'warning')
        return redirect(url_for('index'))
    
    def handle_file_download(self, filename):
        """⬇️ 处理文件下载逻辑 - 子类需重写"""
        flash('⚠️ 请实现handle_file_download方法', 'warning')
        return redirect(url_for('index'))
    
    def allowed_file(self, filename):
        """✅ 检查文件类型是否允许"""
        return ('.' in filename and 
                filename.rsplit('.', 1)[1].lower() in self.config.ALLOWED_EXTENSIONS)
    
    def open_browser(self, url):
        """🌐 自动打开浏览器"""
        def open_browser_delayed():
            time.sleep(1.5)  # 等待服务器启动
            try:
                webbrowser.open(url)
                logging.info(f"🌐 已自动打开浏览器: {url}")
            except Exception as e:
                logging.warning(f"⚠️ 无法自动打开浏览器: {str(e)}")
        
        if not self.config.DEBUG:  # 只在非调试模式下自动打开
            threading.Thread(target=open_browser_delayed, daemon=True).start()
    
    def run(self, auto_open_browser=True):
        """🚀 启动应用"""
        try:
            # 获取端口
            port = self.config.get_port()
            host = self.config.HOST
            
            # 构建URL
            url = f"http://{host}:{port}"
            
            # 启动信息
            print("=" * 60)
            print(f"🚀 Excel数据处理器正在启动...")
            print(f"🌐 访问地址: {url}")
            print(f"📝 日志级别: {self.config.LOG_LEVEL}")
            print(f"🔧 调试模式: {'开启' if self.config.DEBUG else '关闭'}")
            print("=" * 60)
            
            # 自动打开浏览器
            if auto_open_browser:
                self.open_browser(url)
            
            # 启动Flask应用
            self.app.run(
                host=host,
                port=port,
                debug=self.config.DEBUG,
                use_reloader=False  # 避免重复启动
            )
            
        except Exception as e:
            logging.error(f"❌ 启动失败: {str(e)}")
            print(f"❌ 启动失败: {str(e)}")
            input("按任意键退出...")
```

### 📊 Excel数据处理标准模式
```python
class ExcelDataProcessor:
    """📊 Excel数据处理器基类"""
    
    @staticmethod
    def read_excel_safe(file_path, sheet_name=0, header_row=0):
        """🔍 安全读取Excel文件"""
        try:
            if file_path.endswith('.csv'):
                # CSV文件处理
                df = pd.read_csv(file_path, header=header_row, encoding='utf-8-sig')
            else:
                # Excel文件处理
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
            
            logging.info(f"✅ 成功读取文件: {file_path}")
            logging.info(f"📊 数据形状: {df.shape}")
            return df
        except Exception as e:
            logging.error(f"❌ 读取文件失败: {file_path}, 错误: {str(e)}")
            raise
    
    @staticmethod
    def validate_required_columns(df, required_columns, file_name="文件"):
        """🔍 验证必需列是否存在"""
        missing_columns = []
        for col in required_columns:
            if col not in df.columns:
                missing_columns.append(col)
        
        if missing_columns:
            error_msg = f"❌ {file_name}缺少必需列: {', '.join(missing_columns)}"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        logging.info(f"✅ {file_name}列验证通过")
        return True
    
    @staticmethod
    def safe_write_excel(data_dict, output_path):
        """💾 安全写入Excel文件（多工作表）"""
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for sheet_name, df in data_dict.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            logging.info(f"✅ 成功输出文件: {output_path}")
            return True
        except Exception as e:
            logging.error(f"❌ 输出文件失败: {output_path}, 错误: {str(e)}")
            raise
```

## 🎨 前端样式标准

### 🎯 统一UI设计规范
```html
<!-- base.html 标准模板结构 -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Excel数据处理器{% endblock %}</title>
    
    <!-- 🎨 标准CSS资源 -->
    <link href="{{ url_for('static', filename='css/bootstrap.min.css') }}" rel="stylesheet">
    <link href="{{ url_for('static', filename='css/fontawesome.min.css') }}" rel="stylesheet">
    
    <!-- 🎨 统一样式变量 -->
    <style>
        :root {
            --primary-color: #2c3e50;      /* 主色调 */
            --secondary-color: #3498db;    /* 次要色调 */
            --success-color: #27ae60;      /* 成功色 */
            --warning-color: #f39c12;      /* 警告色 */
            --danger-color: #e74c3c;       /* 危险色 */
            --light-gray: #ecf0f1;         /* 浅灰色 */
            --dark-gray: #95a5a6;          /* 深灰色 */
        }
        
        /* 服务器状态指示器 */
        .server-status {
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 1000;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            background: var(--success-color);
            color: white;
        }
        
        .server-status.offline {
            background: var(--danger-color);
        }
    </style>
</head>
<body>
    <!-- 🔴 服务器状态指示器 -->
    <div id="serverStatus" class="server-status">
        <i class="fas fa-circle"></i> 服务器在线
    </div>
    
    <!-- 导航栏 -->
    <nav class="navbar navbar-expand-lg">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="fas fa-chart-bar me-2"></i>{% block app_name %}Excel数据处理器{% endblock %}
            </a>
        </div>
    </nav>
    
    <!-- 主要内容 -->
    <div class="container main-container">
        {% block content %}{% endblock %}
    </div>
    
    <!-- JavaScript -->
    <script>
        // 🔍 服务器状态检查
        function checkServerStatus() {
            fetch('/health')
                .then(response => {
                    if (response.ok) {
                        document.getElementById('serverStatus').className = 'server-status';
                        document.getElementById('serverStatus').innerHTML = '<i class="fas fa-circle"></i> 服务器在线';
                    } else {
                        throw new Error('Server error');
                    }
                })
                .catch(error => {
                    document.getElementById('serverStatus').className = 'server-status offline';
                    document.getElementById('serverStatus').innerHTML = '<i class="fas fa-circle"></i> 服务器离线';
                });
        }
        
        // 每30秒检查一次服务器状态
        setInterval(checkServerStatus, 30000);
    </script>
</body>
</html>
```

### 📱 响应式组件标准
```html
<!-- 🔄 文件上传区域标准组件 -->
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0">
            <i class="fas fa-upload me-2"></i>{{ file_info.name }}
            {% if required %}<span class="text-danger">*</span>{% endif %}
        </h5>
    </div>
    <div class="card-body">
        <div class="mb-3">
            <label class="form-label">{{ file_info.description }}</label>
            <input type="file" class="form-control" name="{{ file_key }}" 
                   accept=".xlsx,.xls,.csv" {% if required %}required{% endif %}>
        </div>
        
        <!-- 📋 文件要求说明 -->
        <div class="alert alert-info">
            <small>
                <strong>📋 要求:</strong><br>
                {{ file_info.source|safe }}<br>
                {{ file_info.format|safe }}<br>
                <strong>🔑 必需字段:</strong> {{ file_info.required_fields|join(', ') }}
            </small>
        </div>
    </div>
</div>

<!-- 🌐 端口信息显示组件 -->
<div class="alert alert-info">
    <i class="fas fa-info-circle me-2"></i>
    <strong>🌐 服务器信息:</strong> 当前运行在端口 <code id="currentPort">{{ request.environ.SERVER_PORT }}</code>
    <br>
    <small>💡 如果端口被占用，系统会自动分配可用端口</small>
</div>
```

## 🔧 环境配置标准

### 📄 环境变量配置(.env.example)
```bash
# 🔐 应用安全配置
SECRET_KEY=your-secret-key-here

# 🌐 服务器配置
FLASK_ENV=development
FLASK_HOST=127.0.0.1
FLASK_PORT=0                    # 0表示自动分配端口，或指定具体端口如5000
FLASK_DEBUG=true

# 📁 文件上传配置
UPLOAD_FOLDER=data/uploads
MAX_CONTENT_LENGTH=52428800     # 50MB in bytes

# 📝 日志配置
LOG_LEVEL=INFO
LOG_FILE=output/logs/app.log

# 🎯 应用特定配置
APP_NAME=Excel数据处理器
AUTO_OPEN_BROWSER=true
```

## 🚀 启动脚本标准

### 🪟 Windows启动脚本(启动应用.bat)
```batch
@echo off
:: 设置控制台编码为UTF-8
chcp 65001 >nul

echo.
echo ==========================================
echo    🚀 Excel数据处理器启动中...
echo ==========================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未检测到Python，请先安装Python
    echo 💡 建议：访问 https://www.python.org/downloads/ 下载安装Python
    pause
    exit /b 1
)

:: 检查虚拟环境
if not exist "venv" (
    echo 📦 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )
)

:: 激活虚拟环境
echo 🔧 激活虚拟环境...
call venv\Scripts\activate

:: 安装/更新依赖
echo 📦 检查并安装依赖包...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --quiet

:: 设置环境变量
set FLASK_ENV=development
set PYTHONPATH=%CD%\src

:: 启动应用
echo 🚀 启动应用...
echo.
python src\web\app.py

:: 如果出错，保持窗口打开
if errorlevel 1 (
    echo.
    echo ❌ 应用启动失败，请检查错误信息
    pause
)
```

### 🐧 Linux/Mac启动脚本(start.sh)
```bash
#!/bin/bash

echo "=========================================="
echo "    🚀 Excel数据处理器启动中..."
echo "=========================================="
echo

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未检测到Python3，请先安装Python3"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ 创建虚拟环境失败"
        exit 1
    fi
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装/更新依赖
echo "📦 检查并安装依赖包..."
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --quiet

# 设置环境变量
export FLASK_ENV=development
export PYTHONPATH="$PWD/src"

# 启动应用
echo "🚀 启动应用..."
echo
python src/web/app.py

# 如果出错，等待用户输入
if [ $? -ne 0 ]; then
    echo
    echo "❌ 应用启动失败，请检查错误信息"
    read -p "按任意键退出..."
fi
```

## 🛡️ 最佳实践

### 🎯 端口管理策略
```python
# 端口管理最佳实践
class PortManager:
    """🌐 端口管理器"""
    
    @staticmethod
    def get_local_ip():
        """🔍 获取本机IP地址"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    @staticmethod
    def check_port_available(host, port):
        """✅ 检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                return result != 0
        except:
            return False
    
    @staticmethod
    def find_free_ports(start_port=5000, count=1):
        """🔍 查找多个可用端口"""
        free_ports = []
        port = start_port
        while len(free_ports) < count and port < 65535:
            if PortManager.check_port_available('127.0.0.1', port):
                free_ports.append(port)
            port += 1
        return free_ports
```

### 🔧 性能优化指南
1. **📊 大文件处理**: 使用`pandas.read_excel(chunksize=1000)`分块读取
2. **💾 内存管理**: 及时清理临时变量和文件
3. **⚡ 缓存策略**: 对重复计算结果进行缓存
4. **🔄 异步处理**: 对耗时操作考虑使用Celery等异步任务队列
5. **🌐 端口优化**: 使用端口池管理，避免端口冲突

### 🛡️ 安全最佳实践
1. **📁 文件验证**: 严格验证上传文件类型和大小
2. **🔒 路径安全**: 使用`secure_filename()`处理文件名
3. **🧹 临时文件**: 及时清理临时上传文件
4. **📝 日志安全**: 不在日志中记录敏感信息
5. **🌐 端口安全**: 仅绑定本地地址，避免外部访问

## 📦 部署标准

### 🐳 Docker支持
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 5000

# 设置环境变量
ENV FLASK_ENV=production
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000

# 启动应用
CMD ["python", "src/web/app.py"]
```

### 🎯 主应用入口模板
```python
# main.py - 标准主入口文件
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from web.app import ExcelWebApp

class MyExcelApp(ExcelWebApp):
    """🎯 具体的Excel处理应用"""
    
    def __init__(self):
        super().__init__(app_name="我的Excel处理器")
    
    def get_file_requirements(self):
        """📋 定义文件上传要求"""
        return {
            'data_file': {
                'name': '数据文件',
                'description': '包含需要处理的Excel数据',
                'required_fields': ['字段1', '字段2', '字段3'],
                'source': '数据来源说明',
                'format': 'Excel格式，第一行为表头'
            }
        }
    
    def handle_file_upload(self):
        """📤 处理文件上传"""
        # 实现具体的文件处理逻辑
        pass

if __name__ == '__main__':
    app = MyExcelApp()
    app.run()
```

---

## 🎯 总结

这个增强版的cursor rules提供了：

- 🌐 **动态端口分配**：自动查找可用端口，避免端口冲突
- ⚙️ **完整的配置管理**：环境变量、配置类、多环境支持
- 🚀 **智能启动脚本**：跨平台启动脚本，自动环境检查
- 🔍 **健康检查机制**：服务器状态监控和前端状态显示
- 🐳 **容器化支持**：Docker配置和部署标准
- 🛡️ **增强的错误处理**：完整的异常处理和用户友好提示
- 📝 **标准化日志**：兼容开发和生产环境的日志配置
- 🎨 **响应式UI**：现代化的用户界面和实时状态显示

遵循这些规范，可以构建功能完善、配置灵活、部署简单的Excel数据处理Web应用程序！🎉