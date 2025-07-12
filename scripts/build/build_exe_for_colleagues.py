#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSKU表现分析器 - EXE打包脚本
专为非技术同事设计的一键打包工具
"""

import os
import sys
import shutil
import subprocess
import zipfile
from datetime import datetime
import tempfile

class MSKUAnalyzerBuilder:
    def __init__(self):
        self.app_name = "MSKU表现分析器"
        self.version = "1.0.0"
        self.description = "亚马逊MSKU配送费表现分析和利润报表校正工具"
        self.author = "AI Assistant"
        
        # 路径配置
        self.project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.dist_dir = os.path.join(self.project_dir, 'output', 'dist')
        self.build_dir = os.path.join(self.project_dir, '.dev', 'build')
        
        # 时间戳
        self.timestamp = datetime.now().strftime('%Y%m%d')
        self.release_name = f"MSKU分析器_v{self.version}_{self.timestamp}"
        
    def print_step(self, step, message):
        """打印步骤信息"""
        print(f"\n{'='*60}")
        print(f"📋 步骤 {step}: {message}")
        print(f"{'='*60}")
        
    def print_info(self, message):
        """打印信息"""
        print(f"ℹ️  {message}")
        
    def print_success(self, message):
        """打印成功信息"""
        print(f"✅ {message}")
        
    def print_error(self, message):
        """打印错误信息"""
        print(f"❌ {message}")
        
    def print_warning(self, message):
        """打印警告信息"""
        print(f"⚠️  {message}")
        
    def check_environment(self):
        """检查环境"""
        self.print_step(1, "环境检查")
        
        # 检查Python版本
        python_version = sys.version_info
        self.print_info(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        if python_version < (3, 7):
            self.print_error("需要Python 3.7或更高版本")
            return False
            
        # 检查必要文件
        required_files = [
            'src/web/app.py',
            'scripts/startup/run.py', 
            'src/core/amazon_profit_analyzer_and_corrector.py',
            'requirements.txt',
            'src/web/templates'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(os.path.join(self.project_dir, file)):
                missing_files.append(file)
                
        if missing_files:
            self.print_error(f"缺少必要文件: {', '.join(missing_files)}")
            return False
            
        self.print_success("环境检查通过")
        return True
        
    def check_environment_silent(self):
        """静默环境检查"""
        # 检查Python版本
        python_version = sys.version_info
        if python_version < (3, 7):
            print("错误：需要Python 3.7或更高版本")
            return False
            
        # 检查必要文件
        required_files = [
            'src/web/app.py', 'scripts/startup/run.py', 'src/core/amazon_profit_analyzer_and_corrector.py',
            'requirements.txt', 'src/web/templates'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(os.path.join(self.project_dir, file)):
                missing_files.append(file)
                
        if missing_files:
            print(f"错误：缺少必要文件: {', '.join(missing_files)}")
            return False
            
        return True
        
    def install_pyinstaller(self):
        """安装PyInstaller"""
        self.print_step(2, "安装PyInstaller")
        
        try:
            import PyInstaller
            self.print_success("PyInstaller已安装")
            return True
        except ImportError:
            self.print_info("PyInstaller未安装，正在安装...")
            
        try:
            # 使用国内镜像源安装
            cmd = [
                sys.executable, '-m', 'pip', 'install', 
                'pyinstaller==6.3.0',
                '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple/'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.print_success("PyInstaller安装成功")
                return True
            else:
                self.print_error(f"PyInstaller安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.print_error(f"安装过程出错: {str(e)}")
            return False
            
    def install_pyinstaller_silent(self):
        """静默安装PyInstaller"""
        try:
            import PyInstaller
            return True
        except ImportError:
            pass
            
        try:
            cmd = [
                sys.executable, '-m', 'pip', 'install', 
                'pyinstaller==6.3.0',
                '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple/'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
                
        except Exception:
            return False
            
    def clean_build(self):
        """清理构建目录"""
        self.print_step(3, "清理构建环境")
        
        # 清理旧的构建文件
        for dir_name in [self.dist_dir, self.build_dir]:
            if os.path.exists(dir_name):
                self.print_info(f"清理目录: {dir_name}")
                shutil.rmtree(dir_name)
                
        # 清理spec文件
        spec_files = [f for f in os.listdir(self.project_dir) if f.endswith('.spec')]
        for spec_file in spec_files:
            os.remove(os.path.join(self.project_dir, spec_file))
            self.print_info(f"删除spec文件: {spec_file}")
            
        self.print_success("构建环境清理完成")
        
    def clean_build_silent(self):
        """静默清理构建目录"""
        for dir_name in [self.dist_dir, self.build_dir]:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
                
        spec_files = [f for f in os.listdir(self.project_dir) if f.endswith('.spec')]
        for spec_file in spec_files:
            os.remove(os.path.join(self.project_dir, spec_file))
        
    def create_spec_file(self):
        """创建PyInstaller配置文件"""
        self.print_step(4, "创建打包配置")
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['scripts/startup/run.py'],
    pathex=['{self.project_dir.replace(os.sep, "/")}'],
    binaries=[],
    datas=[
        ('src/web/templates', 'templates'),
        ('src/web/static', 'static'),
        ('src/core/amazon_profit_analyzer_and_corrector.py', '.'),
        ('src/web/app.py', '.'),
        ('requirements.txt', '.'),
        ('data/uploads', 'uploads'),
    ],
    hiddenimports=[
        'flask',
        'pandas',
        'openpyxl',
        'xlsxwriter',
        'werkzeug',
        'jinja2',
        'markupsafe',
        'itsdangerous',
        'click',
        'blinker',
        'numpy',
        'pytz',
        'dateutil',
        'six',
        'et_xmlfile',
        'defusedxml'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'setuptools',
        'distutils'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.app_name}_v{self.version}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon=None
)
'''
        
        spec_file = os.path.join(self.project_dir, f'{self.app_name}.spec')
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
            
        self.print_success(f"配置文件创建完成: {spec_file}")
        return spec_file
        
    def create_version_info(self):
        """创建版本信息文件"""
        version_info = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1,0,0,0),
    prodvers=(1,0,0,0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{self.author}'),
        StringStruct(u'FileDescription', u'{self.description}'),
        StringStruct(u'FileVersion', u'{self.version}'),
        StringStruct(u'InternalName', u'{self.app_name}'),
        StringStruct(u'LegalCopyright', u'Copyright © 2024'),
        StringStruct(u'OriginalFilename', u'{self.app_name}_v{self.version}.exe'),
        StringStruct(u'ProductName', u'{self.app_name}'),
        StringStruct(u'ProductVersion', u'{self.version}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
        
        version_file = os.path.join(self.project_dir, 'version_info.txt')
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(version_info)
            
        return version_file
        
    def build_exe(self):
        """构建EXE文件"""
        self.print_step(5, "构建EXE文件")
        
        # 创建配置文件
        spec_file = self.create_spec_file()
        version_file = self.create_version_info()
        
        try:
            self.print_info("开始构建，这可能需要几分钟...")
            
            # 执行PyInstaller
            cmd = [
                sys.executable, '-m', 'PyInstaller',
                '--clean',
                '--noconfirm',
                spec_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_dir)
            
            if result.returncode == 0:
                self.print_success("EXE构建成功")
                return True
            else:
                self.print_error(f"构建失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.print_error(f"构建过程出错: {str(e)}")
            return False
        finally:
            # 清理临时文件
            for temp_file in [spec_file, version_file]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
    def build_exe_with_progress(self):
        """带进度显示的EXE构建"""
        # 先创建发布目录
        release_dir = os.path.join(self.dist_dir, self.release_name)
        os.makedirs(release_dir, exist_ok=True)
        
        # 创建配置文件
        spec_file = self.create_spec_file_silent()
        version_file = self.create_version_info_silent()
        
        try:
            print("正在收集所有必要文件...")
            
            # 执行PyInstaller
            cmd = [
                sys.executable, '-m', 'PyInstaller',
                '--clean', '--noconfirm', spec_file
            ]
            
            print("正在编译生成EXE文件...")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_dir)
            
            if result.returncode == 0:
                print("正在优化文件大小...")
                
                # PyInstaller生成的EXE在根目录的dist文件夹
                exe_name = f"MSKU分析器_v{self.version}.exe"
                source_exe = os.path.join(self.project_dir, "dist", exe_name)
                target_exe = os.path.join(release_dir, exe_name)
                
                if os.path.exists(source_exe):
                    shutil.move(source_exe, target_exe)
                    print("       EXE构建成功")
                    return release_dir
                else:
                    print(f"错误：未找到生成的EXE文件，查找路径: {source_exe}")
                    # 列出dist目录内容进行调试
                    dist_path = os.path.join(self.project_dir, "dist")
                    if os.path.exists(dist_path):
                        print(f"dist目录内容: {os.listdir(dist_path)}")
                    return False
            else:
                print(f"构建失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"构建过程出错: {str(e)}")
            return False
        finally:
            # 清理临时文件
            for temp_file in [spec_file, version_file]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
    def create_spec_file_silent(self):
        """静默创建spec文件"""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['scripts/startup/run.py'],
    pathex=['{self.project_dir.replace(os.sep, "/")}'],
    binaries=[],
    datas=[
        ('src/web/templates', 'templates'),
        ('src/web/static', 'static'),
        ('src/core/amazon_profit_analyzer_and_corrector.py', '.'),
        ('src/web/app.py', '.'),
        ('requirements.txt', '.'),
        ('data/uploads', 'uploads'),
    ],
    hiddenimports=[
        'flask', 'pandas', 'openpyxl', 'xlsxwriter', 'werkzeug',
        'jinja2', 'markupsafe', 'itsdangerous', 'click', 'blinker',
        'numpy', 'pytz', 'dateutil', 'six', 'et_xmlfile', 'defusedxml'
    ],
    hookspath=[], hooksconfig={{}}, runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'IPython', 'jupyter', 'notebook', 'pytest', 'setuptools', 'distutils'],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=block_cipher, noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='MSKU分析器_v{self.version}',
    debug=False, bootloader_ignore_signals=False, strip=False,
    upx=True, upx_exclude=[], runtime_tmpdir=None, console=True,
    disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
    version='version_info.txt', icon=None
)

'''
        
        spec_file = os.path.join(self.project_dir, f'{self.app_name}.spec')
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        return spec_file
        
    def create_version_info_silent(self):
        """静默创建版本信息文件"""
        version_info = f'''VSVersionInfo(
  ffi=FixedFileInfo(filevers=(1,0,0,0), prodvers=(1,0,0,0), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable(u'040904B0', [StringStruct(u'CompanyName', u'{self.author}'), StringStruct(u'FileDescription', u'{self.description}'), StringStruct(u'FileVersion', u'{self.version}'), StringStruct(u'InternalName', u'{self.app_name}'), StringStruct(u'LegalCopyright', u'Copyright © 2024'), StringStruct(u'OriginalFilename', u'{self.app_name}_v{self.version}.exe'), StringStruct(u'ProductName', u'{self.app_name}'), StringStruct(u'ProductVersion', u'{self.version}')])]), VarFileInfo([VarStruct(u'Translation', [1033, 1200])])]
)'''
        
        version_file = os.path.join(self.project_dir, 'version_info.txt')
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(version_info)
        return version_file
                    
    def create_release_package(self):
        """创建发布包"""
        self.print_step(6, "创建发布包")
        
        # 查找生成的EXE文件
        exe_file = None
        if os.path.exists(self.dist_dir):
            for file in os.listdir(self.dist_dir):
                if file.endswith('.exe'):
                    exe_file = os.path.join(self.dist_dir, file)
                    break
                    
        if not exe_file or not os.path.exists(exe_file):
            self.print_error("未找到生成的EXE文件")
            return False
            
        # 创建发布目录
        release_dir = os.path.join(self.dist_dir, self.release_name)
        os.makedirs(release_dir, exist_ok=True)
        
        # 复制EXE文件
        exe_name = f"MSKU分析器_v{self.version}.exe"
        shutil.copy2(exe_file, os.path.join(release_dir, exe_name))
        self.print_info(f"复制EXE文件: {exe_name}")
        
        # 创建uploads目录
        uploads_dir = os.path.join(release_dir, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        self.print_info("创建uploads目录")
        
        # 创建使用指南
        self.create_user_guide(release_dir)
        
        # 创建启动脚本
        self.create_startup_script(release_dir, exe_name)
        
        # 复制用户手册（如果存在）
        user_manual = os.path.join(self.project_dir, 'docs', '用户手册.md')
        if os.path.exists(user_manual):
            shutil.copy2(user_manual, os.path.join(release_dir, '用户手册.md'))
            self.print_info("复制用户手册.md")
            
        self.print_success(f"发布包创建完成: {release_dir}")
        return release_dir
        
    def create_release_package_silent(self):
        """静默创建发布包"""
        # 查找生成的EXE文件
        exe_file = None
        if os.path.exists(self.dist_dir):
            for file in os.listdir(self.dist_dir):
                if file.endswith('.exe'):
                    exe_file = os.path.join(self.dist_dir, file)
                    break
                    
        if not exe_file or not os.path.exists(exe_file):
            return False
            
        # 创建发布目录
        release_dir = os.path.join(self.dist_dir, self.release_name)
        os.makedirs(release_dir, exist_ok=True)
        
        # 复制EXE文件
        exe_name = f"MSKU分析器_v{self.version}.exe"
        shutil.copy2(exe_file, os.path.join(release_dir, exe_name))
        
        # 创建uploads目录
        uploads_dir = os.path.join(release_dir, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # 创建使用指南
        self.create_user_guide(release_dir)
        
        # 创建启动脚本
        self.create_startup_script(release_dir, exe_name)
        
        # 复制用户手册（如果存在）
        user_manual = os.path.join(self.project_dir, 'docs', '用户手册.md')
        if os.path.exists(user_manual):
            shutil.copy2(user_manual, os.path.join(release_dir, '用户手册.md'))
            
        return release_dir
        
    def complete_release_package(self, release_dir):
        """完善发布包（添加其他必要文件）"""
        # 创建uploads目录
        uploads_dir = os.path.join(release_dir, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # 创建使用指南
        self.create_user_guide(release_dir)
        
        # 创建启动脚本
        exe_name = f"MSKU分析器_v{self.version}.exe"
        self.create_startup_script(release_dir, exe_name)
        
        # 复制用户手册（如果存在）
        user_manual = os.path.join(self.project_dir, 'docs', '用户手册.md')
        if os.path.exists(user_manual):
            shutil.copy2(user_manual, os.path.join(release_dir, '用户手册.md'))
        
    def create_user_guide(self, release_dir):
        """创建用户指南"""
        guide_content = f'''# {self.app_name} v{self.version} - 使用指南

## 快速开始

1. **双击运行** `MSKU分析器_v{self.version}.exe`
2. **等待启动** - 程序会自动打开浏览器
3. **上传文件** - 按照界面提示上传所需文件
4. **查看结果** - 分析完成后下载结果文件

## 文件要求

### 必需文件
- 订单利润报表 (CSV/Excel格式)
- Hual MSKU列表 (Excel格式)  
- 产品资料表 (Excel格式)

### 可选文件
- MSKU维度利润报表 (用于校正)

## 使用步骤

1. **启动程序**
   - 双击 `MSKU分析器_v{self.version}.exe`
   - 或双击 `启动脚本.bat`

2. **访问界面**
   - 程序启动后会显示访问地址
   - 通常是 http://localhost:5000
   - 浏览器会自动打开

3. **上传文件**
   - 点击"选择文件"按钮
   - 选择对应的数据文件
   - 等待文件验证通过

4. **开始分析**
   - 确保所有必需文件已上传
   - 点击"开始分析"按钮
   - 等待处理完成

5. **下载结果**
   - 分析完成后会显示下载链接
   - 点击下载所需的结果文件
   - 结果文件保存在 `uploads` 目录

## 输出文件说明

- **异常订单数据.xlsx** - 特殊订单分析结果
- **配送费分析.xlsx** - 配送费详细分析
- **MSKU利润报表校正结果.xlsx** - 校正后的利润报表（如有）

## 常见问题

### Q: 程序无法启动？
A: 确保Windows系统为Win10/11，如有杀毒软件拦截请添加信任

### Q: 浏览器没有自动打开？
A: 手动在浏览器中输入程序显示的地址（通常是localhost:5000）

### Q: 文件上传失败？
A: 检查文件格式是否正确，确保表头在指定行

### Q: 分析时间很长？
A: 大文件需要较长处理时间，请耐心等待

## 技术支持

如遇到问题，请联系技术人员并提供：
- 错误截图
- 操作步骤
- 文件信息

---
版本：{self.version}
创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
'''
        
        guide_file = os.path.join(release_dir, '使用指南.txt')
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(guide_content)
            
        self.print_info("创建使用指南.txt")
        
    def create_startup_script(self, release_dir, exe_name):
        """创建启动脚本"""
        script_content = f'''@echo off
chcp 65001 >nul
echo ========================================
echo    {self.app_name} v{self.version}
echo ========================================
echo.
echo 正在启动程序...
echo 启动后请在浏览器中访问显示的地址
echo 按 Ctrl+C 可停止程序
echo.

"{exe_name}"

if errorlevel 1 (
    echo.
    echo 程序启动失败，请检查：
    echo    1. 是否有杀毒软件拦截
    echo    2. 端口是否被占用
    echo    3. 系统是否为Windows 10/11
    echo.
    pause
)
'''
        
        script_file = os.path.join(release_dir, '启动脚本.bat')
        with open(script_file, 'w', encoding='gbk') as f:
            f.write(script_content)
            
        self.print_info("创建启动脚本.bat")
        
    def create_zip_package(self, release_dir):
        """创建ZIP压缩包"""
        self.print_step(7, "创建ZIP压缩包")
        
        zip_file = f"{release_dir}.zip"
        
        try:
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(release_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, self.dist_dir)
                        zf.write(file_path, arc_name)
                        
            file_size = os.path.getsize(zip_file) / (1024 * 1024)
            self.print_success(f"ZIP包创建成功: {zip_file} ({file_size:.1f}MB)")
            return zip_file
            
        except Exception as e:
            self.print_error(f"ZIP包创建失败: {str(e)}")
            return None
            
    def create_zip_package_silent(self, release_dir):
        """静默创建ZIP压缩包"""
        zip_file = f"{release_dir}.zip"
        
        try:
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(release_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, self.dist_dir)
                        zf.write(file_path, arc_name)
            return zip_file
            
        except Exception:
            return None
            
    def cleanup_redundant_files(self):
        """清理多余的文件"""
        try:
            # 删除dist目录下的原始EXE文件（已复制到发布包中）
            if os.path.exists(self.dist_dir):
                for file in os.listdir(self.dist_dir):
                    if file.endswith('.exe'):
                        exe_path = os.path.join(self.dist_dir, file)
                        os.remove(exe_path)
                        print(f"       清理多余文件: {file}")
                        
        except Exception as e:
            # 清理失败不影响整体流程
            pass
            
    def build(self):
        """执行完整构建流程"""
        # 简化输出，与批处理文件保持一致
        
        try:
            # 1. 环境检查 - 静默执行
            if not self.check_environment_silent():
                return False
                
            # 2. 安装PyInstaller - 静默执行
            if not self.install_pyinstaller_silent():
                return False
                
            # 3. 清理构建环境 - 静默执行
            self.clean_build_silent()
            
            # 4. 构建EXE并创建发布包 - 显示详细进度
            print("正在分析Python依赖关系...")
            release_dir = self.build_exe_with_progress()
            if not release_dir:
                return False
                
            # 5. 完善发布包
            print("\n[6/7] 正在完善发布包...")
            self.complete_release_package(release_dir)
            print("       发布包创建完成")
                
            # 6. 创建ZIP包
            print("[7/7] 正在生成ZIP压缩包...")
            zip_file = self.create_zip_package_silent(release_dir)
            if zip_file:
                file_size = os.path.getsize(zip_file) / (1024 * 1024)
                print(f"       ZIP包创建完成 ({file_size:.1f}MB)")
            
            # 注意：现在不需要清理多余文件了，因为EXE直接生成到发布包中
            
            return True
            
        except KeyboardInterrupt:
            print("\n用户中断了构建过程")
            return False
        except Exception as e:
            print(f"\n构建过程出现异常: {str(e)}")
            return False

if __name__ == '__main__':
    builder = MSKUAnalyzerBuilder()
    success = builder.build()
    
    if not success:
        print(f"\n打包失败！")
        sys.exit(1)
    else:
        print("\n打包成功！")
        sys.exit(0) 