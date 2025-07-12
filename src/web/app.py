from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import os
import pandas as pd
from werkzeug.utils import secure_filename
from datetime import datetime
import traceback
import io
import zipfile
from pathlib import Path
import sys
import logging

# 配置日志记录（兼容EXE环境）
def setup_logging():
    """设置日志配置，兼容EXE环境"""
    try:
        # 尝试创建日志目录
        if hasattr(sys, '_MEIPASS'):
            # EXE环境：在EXE同目录创建logs文件夹
            exe_dir = os.path.dirname(sys.executable)
            log_dir = os.path.join(exe_dir, 'logs')
        else:
            # 开发环境：使用项目的output/logs目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            log_dir = os.path.join(project_root, 'output', 'logs')
        
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'app.log')
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file, encoding='utf-8')
            ]
        )
        logging.info(f"日志文件路径: {log_file}")
    except Exception as e:
        # 如果日志文件创建失败，只使用控制台输出
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        logging.warning(f"无法创建日志文件，仅使用控制台输出: {str(e)}")

# 初始化日志
setup_logging()

# 设置控制台输出编码
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 暂时不导入有问题的原模块，使用简化版本
# from amazon_profit_analyzer_and_corrector import ...

# 获取模板和静态文件的正确路径（兼容PyInstaller）
def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容PyInstaller打包"""
    try:
        # PyInstaller打包后的临时目录
        base_path = sys._MEIPASS
    except AttributeError:
        # 开发环境
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

# 设置模板和静态文件路径
template_dir = get_resource_path('templates')
static_dir = get_resource_path('static') if os.path.exists(get_resource_path('static')) else None

# 创建Flask应用，指定模板目录
if static_dir and os.path.exists(static_dir):
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
else:
    app = Flask(__name__, template_folder=template_dir)

app.secret_key = 'msku-analyzer-secret-key-2024'

# 配置文件上传（兼容EXE环境）
def setup_upload_folder():
    """设置上传目录，兼容EXE环境"""
    if hasattr(sys, '_MEIPASS'):
        # EXE环境：在EXE同目录创建uploads文件夹
        exe_dir = os.path.dirname(sys.executable)
        upload_folder = os.path.join(exe_dir, 'uploads')
    else:
        # 开发环境：使用项目的data/uploads目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        upload_folder = os.path.join(project_root, 'data', 'uploads')
    
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder

UPLOAD_FOLDER = setup_upload_folder()
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_remove_file(file_path, max_retries=3):
    """安全删除文件，处理Windows文件占用问题"""
    import time
    for attempt in range(max_retries):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))  # 递增等待时间
                continue
            else:
                logging.warning(f"无法删除临时文件 {file_path}，文件可能被占用")
                return False
        except Exception as e:
            logging.error(f"删除文件时出现错误: {str(e)}")
            return False
    return False

def get_file_requirements():
    """获取各类文件的要求说明"""
    return {
        'order_profit': {
            'name': '订单利润报表',
            'source': '<i class="fas fa-chart-bar me-1"></i>来源：ERP-财务-利润报表-订单-筛选"费用类型"=order，对应目标MSKU的订单数据',
            'required_fields': [
                '结算时间', '销售额', '买家运费', 'FBA费', '促销折扣', 
                'MSKU', '采购成本', '头程费用', '平台费', '数量'
            ],
            'format': '<i class="fas fa-file-alt me-1"></i>格式：CSV或Excel格式，第二行为表头',
            'description': '包含所有订单详细利润数据的报表，表头必须在第二行。美国市场订单不允许混合旺季(10月15日00:00-次年1月14日23:59)和淡季配送费结算周期，需要全部为旺季或全部为淡季'
        },
        'hual_msku': {
            'name': 'Hual MSKU列表',
            'source': '<i class="fas fa-chart-bar me-1"></i>来源：内部数据 → Hual产品管理系统',
            'required_fields': ['MSKU'],
            'format': '<i class="fas fa-file-alt me-1"></i>格式：Excel格式',
            'description': '包含所有Hual产品MSKU的清单文件'
        },
        'product_info': {
            'name': '产品资料表',
            'source': '<i class="fas fa-chart-bar me-1"></i>来源：内部数据 → 产品管理系统',
            'required_fields': ['SKC', 'MSKU', 'SKU', '品质'],
            'format': '<i class="fas fa-file-alt me-1"></i>格式：Excel格式，第一个工作表',
            'description': '包含产品SKC和MSKU对应关系的资料表'
        },
        'msku_profit': {
            'name': 'MSKU维度利润报表',
            'source': '<i class="fas fa-chart-bar me-1"></i>来源：ERP-财务-利润报表-MSKU-筛选"费用类型"=order，对应目标MSKU的订单数据',
            'required_fields': [
                'MSKU', 'FBA发货费(FBA)', '采购成本', '头程成本', 
                '平台费', 'FBA销售额', '毛利润', '日期', '国家', '费用类型'
            ],
            'format': '<i class="fas fa-file-alt me-1"></i>格式：Excel (.xlsx, .xls) 或 CSV (.csv)，第二行为表头',
            'description': '可选，用于校正MSKU维度利润报表。要求：所有数据来自同一国家，美国市场不允许混合旺季/淡季配送费结算周期，费用类型必须为"Order"'
        }
    }

@app.route('/')
def index():
    """主页面"""
    file_requirements = get_file_requirements()
    return render_template('index.html', file_requirements=file_requirements)

@app.route('/upload', methods=['POST'])
def upload_files():
    """处理文件上传"""
    try:
        logging.info("\n===== 开始处理文件上传 =====")
        logging.info(f"请求方法: {request.method}")
        logging.info(f"表单数据: {list(request.form.keys())}")
        logging.info(f"文件数据: {list(request.files.keys())}")
        
        # 检查必要文件是否都已上传
        required_files = ['order_profit', 'hual_msku', 'product_info']
        uploaded_files = {}
        
        # 先处理订单利润报表，确保日期范围正确
        if 'order_profit' not in request.files:
            logging.error("❌ 缺少订单利润报表文件")
            flash(f'❌ 请选择{get_file_requirements()["order_profit"]["name"]}文件', 'error')
            return redirect(url_for('index'))
        
        # 获取订单利润报表文件
        order_file = request.files['order_profit']
        logging.info(f"订单利润报表文件名: {order_file.filename}")
        
        if order_file.filename == '':
            logging.error("❌ 订单利润报表文件名为空")
            flash(f'❌ 请选择{get_file_requirements()["order_profit"]["name"]}文件', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(order_file.filename):
            logging.error("❌ 订单利润报表文件格式不支持")
            flash(f'❌ {get_file_requirements()["order_profit"]["name"]}文件格式不支持，请上传CSV或Excel文件', 'error')
            return redirect(url_for('index'))
        
        # 保存订单利润报表文件
        order_filename = secure_filename(order_file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        order_filename = f"{timestamp}_order_profit_{order_filename}"
        order_filepath = os.path.join(app.config['UPLOAD_FOLDER'], order_filename)
        logging.info(f"保存订单利润报表: {order_filepath}")
        order_file.save(order_filepath)
        
        # 强制检查订单利润报表日期范围
        logging.info("\n***** 强制检查订单利润报表日期范围 *****")
        try:
            # 读取订单利润报表，表头在第二行
            if order_filepath.endswith('.csv'):
                logging.info("📄 读取CSV文件，表头在第二行")
                df = pd.read_csv(order_filepath, header=1)
            else:
                logging.info("📄 读取Excel文件，表头在第二行")
                df = pd.read_excel(order_filepath, header=1)
            
            logging.info(f"✅ 成功读取订单数据，共{len(df)}行")
            logging.info(f"📊 数据列: {list(df.columns)}")
            
            # 检查结算时间列是否存在
            if '结算时间' not in df.columns:
                logging.error("❌ 缺少'结算时间'列")
                flash(f'❌ 订单利润报表缺少必要的"结算时间"列', 'error')
                os.remove(order_filepath)
                return redirect(url_for('index'))
            
            # 检查国家列是否存在
            if '国家' not in df.columns:
                logging.error("❌ 缺少'国家'列")
                flash(f'❌ 订单利润报表缺少必要的"国家"列', 'error')
                os.remove(order_filepath)
                return redirect(url_for('index'))
            
            # 检查国家数据一致性
            unique_countries = df['国家'].dropna().unique()
            if len(unique_countries) > 1:
                logging.error(f"❌ 检测到多个不同国家: {unique_countries}")
                flash(f'❌ 检测到多个不同国家！订单数据必须来自同一个国家。发现的国家：{", ".join(unique_countries)}', 'error')
                os.remove(order_filepath)
                return redirect(url_for('index'))
            elif len(unique_countries) == 0:
                logging.error("❌ 国家列没有有效数据")
                flash(f'❌ 国家列没有有效数据', 'error')
                os.remove(order_filepath)
                return redirect(url_for('index'))
            else:
                country_name = unique_countries[0]
                logging.info(f"✅ 国家检查通过：所有订单都来自 {country_name}")
            
            # 将结算时间转换为日期类型
            try:
                logging.info(f"📅 结算时间样例: {df['结算时间'].head(3).tolist()}")
                df['结算时间'] = pd.to_datetime(df['结算时间'])
                logging.info(f"✅ 结算时间转换成功，数据类型: {df['结算时间'].dtype}")
            except Exception as date_error:
                logging.error(f"❌ 结算时间转换失败: {str(date_error)}")
                flash(f'❌ 结算时间格式无法解析: {str(date_error)}', 'error')
                os.remove(order_filepath)
                return redirect(url_for('index'))
            
            # 获取最早和最晚的结算时间
            earliest_date = df['结算时间'].min()
            latest_date = df['结算时间'].max()
            logging.info(f"📅 订单日期范围: {earliest_date.strftime('%Y-%m-%d')} 至 {latest_date.strftime('%Y-%m-%d')}")
            
            # 检查每一行的结算时间是否在旺季区间内
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
            
            # 对每一行应用检查函数
            logging.info("检查所有订单日期...")
            in_peak_season = df['结算时间'].apply(is_in_peak_season)
            peak_count = in_peak_season.sum()
            non_peak_count = len(df) - peak_count
            
            logging.info(f"✓ 旺季区间内订单数: {peak_count}")
            logging.info(f"✗ 非旺季区间内订单数: {non_peak_count}")
            logging.info(f"总订单数: {len(df)}")
            
            # 检查是否混合周期（不允许同时存在旺季和淡季）
            all_in_peak_season = in_peak_season.all()
            all_in_off_season = (~in_peak_season).all()
            
            if not (all_in_peak_season or all_in_off_season):
                # 混合周期 - 既有旺季又有非旺季
                non_peak_orders = len(df[~in_peak_season])
                non_peak_examples = df.loc[~in_peak_season, '结算时间'].head(5).dt.strftime('%Y-%m-%d').tolist()
                peak_examples = df.loc[in_peak_season, '结算时间'].head(5).dt.strftime('%Y-%m-%d').tolist()
                
                logging.error(f"❌ 检测到混合结算周期！旺季订单: {peak_count}, 淡季订单: {non_peak_count}")
                logging.error(f"旺季示例: {peak_examples}")
                logging.error(f"淡季示例: {non_peak_examples}")
                
                error_msg = f'❌ 日期范围检查失败：检测到混合结算周期！美国市场数据不允许同时包含旺季(10月15日00:00-次年1月14日23:59)和淡季配送费结算周期。您上传的订单日期范围为{earliest_date.strftime("%Y-%m-%d")}至{latest_date.strftime("%Y-%m-%d")}，包含旺季订单{peak_count}条，淡季订单{non_peak_count}条。请确保数据全部在旺季或全部在淡季。'
                logging.error(error_msg)
                flash(error_msg, 'error')
                os.remove(order_filepath)
                return redirect(url_for('index'))
            
            # 确定是旺季还是淡季
            season_type = "旺季" if all_in_peak_season else "淡季"
            logging.info(f"✅ 配送周期检查通过！所有订单都在{season_type}配送费结算周期内")
            logging.info(f"订单统计：{season_type}订单 {peak_count if all_in_peak_season else non_peak_count} 条")
            
            # 保存到上传文件列表
            uploaded_files['order_profit'] = order_filepath
            
        except Exception as e:
            logging.error(f"❌ 订单利润报表日期检查过程中出错: {str(e)}")
            logging.error(f"错误详情: {traceback.format_exc()}")
            flash(f'❌ 订单利润报表日期检查失败：{str(e)}', 'error')
            if os.path.exists(order_filepath):
                os.remove(order_filepath)
            return redirect(url_for('index'))
        
        # 处理其他必要文件
        for file_type in ['hual_msku', 'product_info']:
            logging.info(f"\n----- 处理{file_type}文件 -----")
            if file_type not in request.files:
                logging.error(f"❌ 缺少{file_type}文件")
                flash(f'❌ 请选择{get_file_requirements()[file_type]["name"]}文件', 'error')
                return redirect(url_for('index'))
            
            file = request.files[file_type]
            logging.info(f"文件名: {file.filename}")
            
            if file.filename == '':
                logging.error(f"❌ {file_type}文件名为空")
                flash(f'❌ 请选择{get_file_requirements()[file_type]["name"]}文件', 'error')
                return redirect(url_for('index'))
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{file_type}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logging.info(f"保存路径: {filepath}")
                file.save(filepath)
                uploaded_files[file_type] = filepath
                logging.info(f"✅ {file_type}文件保存成功")
            else:
                logging.error(f"❌ {file_type}文件格式不支持")
                flash(f'❌ {get_file_requirements()[file_type]["name"]}文件格式不支持，请上传CSV或Excel文件', 'error')
                return redirect(url_for('index'))
        
        logging.info("\n===== 所有必要文件上传完成 =====")
        
        # 检查可选文件
        msku_profit_file = None
        if 'msku_profit' in request.files:
            file = request.files['msku_profit']
            if file.filename != '' and file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_msku_profit_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                msku_profit_file = filepath
                logging.info(f"✅ 可选文件 msku_profit 上传成功: {filepath}")
        
        # 处理分析
        logging.info("\n===== 开始处理分析 =====")
        result = process_analysis(
            uploaded_files['order_profit'],
            uploaded_files['hual_msku'], 
            uploaded_files['product_info'],
            msku_profit_file
        )
        
        if result['success']:
            logging.info("✅ 分析成功完成")
            return render_template('results.html', 
                                 result=result, 
                                 download_files=result.get('download_files', []))
        else:
            logging.info(f"❌ 分析失败: {result['error']}")
            flash(f'❌ 处理过程中出现错误：{result["error"]}', 'error')
            return redirect(url_for('index'))
            
    except Exception as e:
        logging.info(f"❌ 上传处理过程中出现未捕获异常: {str(e)}")
        logging.info(f"错误详情: {traceback.format_exc()}")
        flash(f'❌ 上传处理失败：{str(e)}', 'error')
        return redirect(url_for('index'))

def process_analysis(order_profit_path, hual_msku_path, product_info_path, msku_profit_path=None):
    """处理分析逻辑 - 简化版本，不依赖原模块"""
    result = {
        'success': False,
        'steps': [],
        'download_files': [],
        'error': None
    }
    
    try:
        # 步骤1：读取订单利润报表
        result['steps'].append({
            'step': 1,
            'title': '📊 读取订单利润报表',
            'status': '处理中...'
        })
        
        try:
            # 读取订单利润报表，表头在第二行
            if order_profit_path.endswith('.csv'):
                # CSV文件，指定表头行为第二行（索引为1）
                df = pd.read_csv(order_profit_path, header=1)
            else:
                # Excel文件，指定表头行为第二行（索引为1）
                df = pd.read_excel(order_profit_path, header=1)
            
            result['steps'][-1]['status'] = f'✅ 成功读取 {len(df)} 条订单记录'
            result['steps'][-1]['details'] = f'数据列包括：{", ".join(list(df.columns)[:10])}...'
        except Exception as e:
            result['steps'][-1]['status'] = f'❌ 读取失败：{str(e)}'
            result['error'] = f'订单利润报表读取失败：{str(e)}'
            return result
        
        # 步骤2：读取Hual MSKU列表
        result['steps'].append({
            'step': 2,
            'title': '📋 读取Hual MSKU列表',
            'status': '处理中...'
        })
        
        try:
            hual_df = pd.read_excel(hual_msku_path)
            if 'MSKU' not in hual_df.columns:
                raise Exception("Hual MSKU列表文件缺少必要的'MSKU'列")
            hual_msku_list = hual_df['MSKU'].astype(str).tolist()
            result['steps'][-1]['status'] = f'✅ 成功读取 {len(hual_msku_list)} 个Hual MSKU'
        except Exception as e:
            result['steps'][-1]['status'] = f'❌ 读取失败：{str(e)}'
            result['error'] = f'Hual MSKU列表读取失败：{str(e)}'
            return result
        
        # 步骤3：读取产品资料表
        result['steps'].append({
            'step': 3,
            'title': '📦 读取产品资料表',
            'status': '处理中...'
        })
        
        try:
            # 直接读取第一个工作表
            product_info_df = pd.read_excel(product_info_path, sheet_name=0)
            
            required_cols = ['SKC', 'MSKU', 'SKU', '品质']
            missing_cols = [col for col in required_cols if col not in product_info_df.columns]
            if missing_cols:
                raise Exception(f"产品资料表缺少必要列：{missing_cols}")
            
            result['steps'][-1]['status'] = f'✅ 成功读取 {len(product_info_df)} 个产品信息'
            result['steps'][-1]['details'] = f'包含 {product_info_df["SKC"].nunique()} 个不同SKC'
        except Exception as e:
            result['steps'][-1]['status'] = f'❌ 读取失败：{str(e)}'
            result['error'] = f'产品资料表读取失败：{str(e)}'
            return result
        
        # 步骤4：计算实际配送费
        result['steps'].append({
            'step': 4,
            'title': '💰 计算实际配送费用',
            'status': '处理中...'
        })
        
        try:
            # 简化的实际配送费计算
            def calc_shipping_fee(row):
                buyer_shipping = row.get('买家运费', 0) if '买家运费' in row.index else 0
                fba_fee = row.get('FBA费', 0) if 'FBA费' in row.index else 0
                promotion_discount = row.get('促销折扣', 0) if '促销折扣' in row.index else 0
                
                if buyer_shipping == 0:
                    return fba_fee
                elif buyer_shipping + promotion_discount == 0:
                    return fba_fee
                else:
                    return buyer_shipping + promotion_discount + fba_fee
            
            df['实际配送费'] = df.apply(calc_shipping_fee, axis=1)
            result['steps'][-1]['status'] = '✅ 实际配送费计算完成'
        except Exception as e:
            result['steps'][-1]['status'] = f'❌ 计算失败：{str(e)}'
            result['error'] = f'实际配送费计算失败：{str(e)}'
            return result
        
        # 步骤5：识别特殊订单
        result['steps'].append({
            'step': 5,
            'title': '🔍 识别特殊订单类型',
            'status': '处理中...'
        })
        
        try:
            # 识别各类特殊订单
            # 安全获取列数据，如果列不存在则用0填充
            sales_col = df['销售额'] if '销售额' in df.columns else pd.Series([0] * len(df))
            fba_col = df['FBA费'] if 'FBA费' in df.columns else pd.Series([0] * len(df))
            
            # 确保MSKU列存在
            if 'MSKU' not in df.columns:
                df['MSKU'] = '未知MSKU'
                logging.warning("⚠️ 警告: 订单数据中缺少MSKU列，将使用默认值")
            msku_col = df['MSKU']
            
            vine_orders = df[(sales_col == 0) & (fba_col != 0)].copy()
            if not vine_orders.empty:
                vine_orders['订单类型'] = 'VINE订单'
            
            exchange_orders = df[(sales_col == 0) & (fba_col == 0)].copy()
            if not exchange_orders.empty:
                exchange_orders['订单类型'] = '换货订单'
            
            new_product_orders = df[(fba_col == 0) & (sales_col > 0)].copy()
            if not new_product_orders.empty:
                new_product_orders['订单类型'] = '新品入仓优惠订单'
            
            hual_orders = df[msku_col.astype(str).isin(hual_msku_list)].copy()
            if not hual_orders.empty:
                hual_orders['订单类型'] = 'Hual订单'
            
            # 识别二手商品订单 - MSKU前4个字母为"amzn"
            secondhand_orders = df[msku_col.astype(str).str[:4].str.lower() == 'amzn'].copy()
            if not secondhand_orders.empty:
                secondhand_orders['订单类型'] = '二手商品订单'
            
            result['steps'][-1]['status'] = f'✅ 识别完成 - VINE: {len(vine_orders)}, 换货: {len(exchange_orders)}, 新品优惠: {len(new_product_orders)}, Hual: {len(hual_orders)}, 二手商品: {len(secondhand_orders)}'
            
        except Exception as e:
            result['steps'][-1]['status'] = f'❌ 识别失败：{str(e)}'
            result['error'] = f'特殊订单识别失败：{str(e)}'
            return result
        
        # 步骤6：生成分析报告
        result['steps'].append({
            'step': 6,
            'title': '📈 生成分析报告',
            'status': '处理中...'
        })
        
        try:
            # 创建输出文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 1. 异常订单数据文件
            abnormal_output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'异常订单数据_{timestamp}.xlsx')
            
            # 准备要合并的特殊订单列表
            special_orders_list = []
            
            with pd.ExcelWriter(abnormal_output_path, engine='openpyxl') as writer:
                # 只写入非空的DataFrame
                if not vine_orders.empty:
                    vine_orders.to_excel(writer, sheet_name='VINE订单', index=False)
                    special_orders_list.append(vine_orders)
                else:
                    # 创建空的工作表
                    pd.DataFrame(columns=['MSKU', '订单类型']).to_excel(writer, sheet_name='VINE订单', index=False)
                
                if not exchange_orders.empty:
                    exchange_orders.to_excel(writer, sheet_name='换货订单', index=False)
                    special_orders_list.append(exchange_orders)
                else:
                    pd.DataFrame(columns=['MSKU', '订单类型']).to_excel(writer, sheet_name='换货订单', index=False)
                
                if not new_product_orders.empty:
                    new_product_orders.to_excel(writer, sheet_name='新品入仓优惠订单', index=False)
                    special_orders_list.append(new_product_orders)
                else:
                    pd.DataFrame(columns=['MSKU', '订单类型']).to_excel(writer, sheet_name='新品入仓优惠订单', index=False)
                
                if not hual_orders.empty:
                    hual_orders.to_excel(writer, sheet_name='Hual订单', index=False)
                    special_orders_list.append(hual_orders)
                else:
                    pd.DataFrame(columns=['MSKU', '订单类型']).to_excel(writer, sheet_name='Hual订单', index=False)
                
                if not secondhand_orders.empty:
                    secondhand_orders.to_excel(writer, sheet_name='二手商品订单', index=False)
                    special_orders_list.append(secondhand_orders)
                else:
                    pd.DataFrame(columns=['MSKU', '订单类型']).to_excel(writer, sheet_name='二手商品订单', index=False)
                
                # 合并所有特殊订单
                if special_orders_list:
                    all_abnormal_orders = pd.concat(special_orders_list, ignore_index=True)
                    all_abnormal_orders.to_excel(writer, sheet_name='所有特殊订单', index=False)
                else:
                    pd.DataFrame(columns=['MSKU', '订单类型']).to_excel(writer, sheet_name='所有特殊订单', index=False)
            
            result['download_files'].append({
                'name': '异常订单数据分析',
                'filename': os.path.basename(abnormal_output_path),
                'path': abnormal_output_path,
                'description': '包含VINE订单、换货订单、新品入仓优惠订单、Hual订单和二手商品订单的详细数据'
            })
            
            # 2. 配送费分析文件
            shipping_output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'配送费分析_{timestamp}.xlsx')
            
            # 排除所有异常订单，只分析正常订单的配送费
            logging.info("🔍 正在筛选正常订单用于配送费分析...")
            
            # 创建所有异常订单的索引集合
            abnormal_indices = set()
            
            # 添加各类异常订单的索引
            if not vine_orders.empty:
                abnormal_indices.update(vine_orders.index)
            if not exchange_orders.empty:
                abnormal_indices.update(exchange_orders.index)
            if not new_product_orders.empty:
                abnormal_indices.update(new_product_orders.index)
            if not hual_orders.empty:
                abnormal_indices.update(hual_orders.index)
            if not secondhand_orders.empty:
                abnormal_indices.update(secondhand_orders.index)
            
            # 筛选正常订单（排除所有异常订单）
            normal_orders = df[~df.index.isin(abnormal_indices)].copy()
            
            logging.info(f"📊 数据筛选结果：")
            logging.info(f"   总订单数：{len(df)}")
            logging.info(f"   正常订单数：{len(normal_orders)}")
            logging.info(f"   异常订单数：{len(abnormal_indices)}")
            logging.info(f"   异常订单占比：{(len(abnormal_indices)/len(df)*100):.2f}%")
            
            # 基于正常订单进行配送费分析
            numeric_cols = ['实际配送费', '数量', '销售额', 'FBA费', '买家运费', '促销折扣']
            agg_dict = {}
            for col in numeric_cols:
                if col in normal_orders.columns:
                    agg_dict[col] = 'sum'
            
            # 检查MSKU列是否存在
            if 'MSKU' not in normal_orders.columns:
                # 如果MSKU列不存在，添加一个默认的MSKU列
                normal_orders['MSKU'] = '未知MSKU'
                logging.warning("⚠️ 警告: 订单数据中缺少MSKU列，将使用默认值")
            
            # 通过产品资料表关联SKU和SKC信息
            logging.info("正在关联产品资料表获取SKU和SKC信息...")
            try:
                # 检查产品资料表的列
                logging.info(f"产品资料表列: {list(product_info_df.columns)}")
                logging.info(f"产品资料表行数: {len(product_info_df)}")
                
                # 检查产品资料表中是否有必要的列
                required_cols = ['MSKU', 'SKU', 'SKC']
                missing_cols = [col for col in required_cols if col not in product_info_df.columns]
                if missing_cols:
                    raise Exception(f"产品资料表缺少必要列: {missing_cols}")
                
                # 合并产品资料表，获取SKU和SKC信息
                # 注意：订单数据中的SKU字段实际对应产品资料表中的MSKU字段
                normal_orders_with_sku = normal_orders.merge(
                    product_info_df[['MSKU', 'SKU', 'SKC']].rename(columns={'MSKU': '订单SKU_映射MSKU'}),
                    left_on='SKU',  # 订单数据的SKU列
                    right_on='订单SKU_映射MSKU',  # 产品资料表的MSKU列
                    how='left'
                ).drop(columns=['订单SKU_映射MSKU'])  # 删除临时列
                
                # 重命名列以避免混淆：订单中的SKU实际是MSKU，产品资料中的SKU才是真正的SKU
                normal_orders_with_sku = normal_orders_with_sku.rename(columns={
                    'SKU_x': '订单MSKU',  # 订单数据原来的SKU列，实际是MSKU
                    'SKU_y': 'SKU'        # 产品资料表的SKU列，这才是真正的SKU
                })
                
                # 检查关联后的结果
                logging.info(f"关联后数据行数: {len(normal_orders_with_sku)}")
                logging.info(f"关联后数据列: {list(normal_orders_with_sku.columns)}")
                
                # 检查SKU和SKC列的数据情况
                if 'SKU' in normal_orders_with_sku.columns:
                    sku_null_count = normal_orders_with_sku['SKU'].isna().sum()
                    sku_valid_count = normal_orders_with_sku['SKU'].notna().sum()
                    logging.info(f"SKU列: 有效数据{sku_valid_count}行, 空值{sku_null_count}行")
                
                if 'SKC' in normal_orders_with_sku.columns:
                    skc_null_count = normal_orders_with_sku['SKC'].isna().sum()
                    skc_valid_count = normal_orders_with_sku['SKC'].notna().sum()
                    logging.info(f"SKC列: 有效数据{skc_valid_count}行, 空值{skc_null_count}行")
                
                # 检查店铺信息列是否存在
                if '店铺' in normal_orders.columns:
                    shop_col = '店铺'
                    logging.info(f"找到店铺列: {shop_col}")
                    # 确保关联后的数据也有店铺列
                    if '店铺' not in normal_orders_with_sku.columns:
                        normal_orders_with_sku['店铺'] = normal_orders['店铺']
                        logging.info("已将店铺信息复制到关联后的数据中")
                else:
                    # 如果没有店铺列，使用默认值
                    normal_orders_with_sku['店铺'] = '未知店铺'
                    shop_col = '店铺'
                    logging.warning("警告: 订单数据中缺少'店铺'列，将使用默认值")
                
                logging.info(f"成功关联产品信息，关联后数据行数: {len(normal_orders_with_sku)}")
                
            except Exception as e:
                logging.error(f"产品资料表关联失败: {str(e)}")
                # 如果关联失败，使用原始数据
                normal_orders_with_sku = normal_orders.copy()
                normal_orders_with_sku['SKU'] = '未知SKU'
                normal_orders_with_sku['SKC'] = '未知SKC'
                if '店铺' not in normal_orders_with_sku.columns:
                    normal_orders_with_sku['店铺'] = '未知店铺'
                shop_col = '店铺'
            
            # 1. 基于正常订单按MSKU和店铺汇总
            logging.info("正在生成MSKU维度汇总（包含店铺信息）...")
            msku_summary = normal_orders_with_sku.groupby(['MSKU', shop_col]).agg(agg_dict).reset_index()
            if '实际配送费' in msku_summary.columns and '数量' in msku_summary.columns:
                msku_summary['单个实际配送费'] = (msku_summary['实际配送费'] / msku_summary['数量']).round(2)
            
            logging.info(f"MSKU维度汇总完成，共{len(msku_summary)}条记录")
            
            # 3. 新增：SKC配送费异常检查
            logging.info("正在进行SKC配送费异常检查...")
            skc_consistency_issues = []
            
            try:
                # 检查是否有必要的列
                if 'SKU' in normal_orders_with_sku.columns and 'SKC' in normal_orders_with_sku.columns:
                    # 只检查有SKC信息的数据
                    valid_skc_data = normal_orders_with_sku[
                        (normal_orders_with_sku['SKC'].notna()) & 
                        (normal_orders_with_sku['SKC'] != '未知SKC') &
                        (normal_orders_with_sku['SKC'] != '')
                    ].copy()
                    
                    if not valid_skc_data.empty:
                        # 计算每个SKU的单个实际配送费
                        sku_shipping_summary = valid_skc_data.groupby(['SKU', 'SKC']).agg({
                            '实际配送费': 'sum',
                            '数量': 'sum',
                            'MSKU': lambda x: ', '.join(x.unique())  # 记录涉及的MSKU
                        }).reset_index()
                        
                        sku_shipping_summary['单个实际配送费'] = (
                            sku_shipping_summary['实际配送费'] / sku_shipping_summary['数量']
                        ).round(2)
                        
                        # 按SKC分组，检查同一SKC下配送费绝对值是否存在异常
                        skc_detail_records = []
                        for skc, skc_group in sku_shipping_summary.groupby('SKC'):
                            if len(skc_group) >= 1:  # 检查所有SKC
                                # 计算配送费绝对值
                                skc_group = skc_group.copy()
                                skc_group['配送费绝对值'] = skc_group['单个实际配送费'].abs()
                                
                                # 找到绝对值的最小值作为基准
                                min_abs_fee = skc_group['配送费绝对值'].min()
                                
                                # 找出绝对值大于最小值的异常记录
                                abnormal_records = skc_group[skc_group['配送费绝对值'] > min_abs_fee]
                                
                                if not abnormal_records.empty:
                                    # 计算配送费范围和最大差异
                                    all_fees = skc_group['单个实际配送费']
                                    min_fee = all_fees.min()
                                    max_fee = all_fees.max()
                                    fee_diff = max_fee - min_fee
                                    
                                    # 为每个异常SKU创建记录
                                    for idx, (_, row) in enumerate(abnormal_records.iterrows()):
                                        # 获取该SKU对应的MSKU和店铺信息
                                        sku_msku_info = normal_orders_with_sku[
                                            normal_orders_with_sku['SKU'] == row['SKU']
                                        ][['订单MSKU', shop_col]].drop_duplicates()
                                        
                                        if not sku_msku_info.empty:
                                            for msku_idx, (_, msku_row) in enumerate(sku_msku_info.iterrows()):
                                                detail_record = {
                                                    'SKC': skc if idx == 0 and msku_idx == 0 else '',  # 只在第一行显示SKC
                                                    '涉及SKU数量': len(skc_group) if idx == 0 and msku_idx == 0 else '',  # 只在第一行显示数量
                                                    '配送费范围': f'{min_fee:.2f} - {max_fee:.2f}' if idx == 0 and msku_idx == 0 else '',  # 只在第一行显示范围
                                                    '最小值': f'{min_abs_fee:.2f}' if idx == 0 and msku_idx == 0 else '',  # 只在第一行显示最小值
                                                    '最大差异': f'{fee_diff:.2f}' if idx == 0 and msku_idx == 0 else '',  # 只在第一行显示差异
                                                    '异常MSKU': msku_row['订单MSKU'],
                                                    '店铺': msku_row[shop_col],
                                                    '异常配送费': f'{row["单个实际配送费"]:.2f}'
                                                }
                                                skc_detail_records.append(detail_record)
                                        
                        skc_consistency_issues = skc_detail_records
                        
                        logging.info(f"SKC配送费异常检查完成，发现{len(skc_consistency_issues)}个异常记录")
                    else:
                        logging.warning("没有有效的SKC数据进行一致性检查")
                else:
                    logging.warning("缺少SKU或SKC列，跳过一致性检查")
                    
            except Exception as e:
                logging.error(f"SKC配送费一致性检查失败: {str(e)}")
                skc_consistency_issues = []
            
            # 创建SKC异常检查DataFrame
            if skc_consistency_issues:
                skc_issues_df = pd.DataFrame(skc_consistency_issues)
            else:
                # 创建空的DataFrame，包含所有必要列
                skc_issues_df = pd.DataFrame(columns=[
                    'SKC', '涉及SKU数量', '配送费范围', '最小值', '最大差异', 
                    '异常MSKU', '店铺', '异常配送费'
                ])
            
            with pd.ExcelWriter(shipping_output_path, engine='openpyxl') as writer:
                # 输出正常订单明细（包含SKU和SKC信息）
                normal_orders_with_sku.to_excel(writer, sheet_name='正常订单明细', index=False)
                
                # 输出MSKU维度汇总（包含店铺信息）
                msku_summary.to_excel(writer, sheet_name='MSKU维度汇总', index=False)
                
                # 输出SKC配送费异常检查
                skc_issues_df.to_excel(writer, sheet_name='SKC配送费异常检查', index=False)
                
                # 同时提供完整数据作为参考
                df.to_excel(writer, sheet_name='全部订单参考数据', index=False)
            
            result['download_files'].append({
                'name': '配送费分析报告',
                'filename': os.path.basename(shipping_output_path),
                'path': shipping_output_path,
                'description': f'正常订单配送费分析（已排除{len(abnormal_indices)}个异常订单）- 包含正常订单明细（含SKU/SKC信息）、MSKU维度汇总（含店铺信息）、SKC配送费异常检查和全部订单参考数据'
            })
            
            result['steps'][-1]['status'] = '✅ 分析报告生成完成'
            
        except Exception as e:
            result['steps'][-1]['status'] = f'❌ 生成失败：{str(e)}'
            result['error'] = f'分析报告生成失败：{str(e)}'
            return result
        
        # 步骤7: MSKU维度利润报表校正
        if msku_profit_path:
            result['steps'].append({
                'step': 7,
                'title': '🔧 MSKU维度利润报表校正',
                'status': '处理中...'
            })
            
            try:
                logging.info("🔧 开始MSKU维度利润报表校正...")
                
                # 读取MSKU维度利润报表
                logging.info(f"📄 读取MSKU维度利润报表: {msku_profit_path}")
                if msku_profit_path.endswith('.csv'):
                    msku_report = pd.read_csv(msku_profit_path, header=1)
                else:
                    msku_report = pd.read_excel(msku_profit_path, header=1)
                
                logging.info(f"✅ 成功读取MSKU维度利润报表，共{len(msku_report)}行")
                logging.info(f"📊 数据列: {list(msku_report.columns)}")
                
                # 检查必要列是否存在
                required_msku_cols = ['MSKU', 'FBA发货费(FBA)', '采购成本', '头程成本', '平台费', 'FBA销售额']
                missing_msku_cols = [col for col in required_msku_cols if col not in msku_report.columns]
                if missing_msku_cols:
                    raise Exception(f"MSKU维度利润报表缺少必要列：{missing_msku_cols}")
                
                # 1. 计算异常订单费用汇总
                logging.info("📊 计算异常订单费用汇总...")
                
                # 合并所有异常订单
                all_abnormal_orders = []
                if not vine_orders.empty:
                    all_abnormal_orders.append(vine_orders)
                if not exchange_orders.empty:
                    all_abnormal_orders.append(exchange_orders)
                if not new_product_orders.empty:
                    all_abnormal_orders.append(new_product_orders)
                if not hual_orders.empty:
                    all_abnormal_orders.append(hual_orders)
                if not secondhand_orders.empty:
                    all_abnormal_orders.append(secondhand_orders)
                
                if all_abnormal_orders:
                    abnormal_orders_df = pd.concat(all_abnormal_orders, ignore_index=True)
                    
                    # 按MSKU汇总异常订单费用
                    abnormal_fee_cols = ['FBA费', '采购成本', '头程费用', '平台费', '销售额', '买家运费', '促销折扣', '其他成本', '站外推广费']
                    agg_dict = {}
                    for col in abnormal_fee_cols:
                        if col in abnormal_orders_df.columns:
                            agg_dict[col] = 'sum'
                    
                    if agg_dict:
                        abnormal_fees = abnormal_orders_df.groupby('MSKU').agg(agg_dict).reset_index()
                        logging.info(f"✅ 异常订单费用汇总完成，涉及{len(abnormal_fees)}个MSKU")
                    else:
                        abnormal_fees = pd.DataFrame(columns=['MSKU'])
                        logging.warning("⚠️ 没有找到可汇总的费用列")
                else:
                    abnormal_fees = pd.DataFrame(columns=['MSKU'])
                    logging.info("ℹ️ 没有异常订单，跳过费用汇总")
                
                # 2. 创建SKC最低配送费字典
                logging.info("📊 创建SKC最低配送费字典...")
                skc_min_shipping_fees = {}
                
                try:
                    # 基于正常订单创建SKC最低配送费字典
                    if not normal_orders_with_sku.empty and 'SKC' in normal_orders_with_sku.columns:
                        # 计算每个SKU的单个实际配送费
                        sku_shipping_data = normal_orders_with_sku.groupby(['SKU', 'SKC']).agg({
                            '实际配送费': 'sum',
                            '数量': 'sum'
                        }).reset_index()
                        
                        sku_shipping_data['单个实际配送费'] = (
                            sku_shipping_data['实际配送费'] / sku_shipping_data['数量']
                        ).round(2)
                        
                        # 按SKC分组，找到每个SKC的最低配送费绝对值
                        for skc, skc_group in sku_shipping_data.groupby('SKC'):
                            if not skc_group.empty:
                                # 计算配送费绝对值
                                abs_fees = skc_group['单个实际配送费'].abs()
                                min_abs_fee = abs_fees.min()
                                
                                skc_min_shipping_fees[skc] = {
                                    'min_fee': min_abs_fee,
                                    'sku_count': len(skc_group)
                                }
                        
                        logging.info(f"✅ SKC最低配送费字典创建完成，包含{len(skc_min_shipping_fees)}个SKC")
                    else:
                        logging.warning("⚠️ 无法创建SKC最低配送费字典，缺少必要数据")
                except Exception as e:
                    logging.error(f"❌ 创建SKC最低配送费字典失败: {str(e)}")
                
                # 3. 创建SKC最低头程均价字典
                logging.info("📊 创建SKC最低头程均价字典...")
                skc_min_shipping_costs = {}
                
                try:
                    # 基于正常订单创建SKC最低头程均价字典
                    if not normal_orders_with_sku.empty and 'SKC' in normal_orders_with_sku.columns:
                        # 计算每个SKU的头程均价（排除头程费用为0的记录）
                        sku_cost_data = normal_orders_with_sku[normal_orders_with_sku['头程费用'] != 0].groupby(['SKU', 'SKC']).agg({
                            '头程费用': 'sum',
                            '数量': 'sum'
                        }).reset_index()
                        
                        if not sku_cost_data.empty:
                            sku_cost_data['头程均价'] = (
                                sku_cost_data['头程费用'] / sku_cost_data['数量']
                            ).round(2)
                            
                            # 按SKC分组，找到每个SKC的最低头程均价绝对值
                            for skc, skc_group in sku_cost_data.groupby('SKC'):
                                if not skc_group.empty:
                                    # 计算头程均价绝对值
                                    abs_costs = skc_group['头程均价'].abs()
                                    min_abs_cost = abs_costs.min()
                                    
                                    skc_min_shipping_costs[skc] = {
                                        'min_cost': min_abs_cost,
                                        'sku_count': len(skc_group)
                                    }
                            
                            logging.info(f"✅ SKC最低头程均价字典创建完成，包含{len(skc_min_shipping_costs)}个SKC")
                        else:
                            logging.warning("⚠️ 没有有效的头程费用数据")
                    else:
                        logging.warning("⚠️ 无法创建SKC最低头程均价字典，缺少必要数据")
                except Exception as e:
                    logging.error(f"❌ 创建SKC最低头程均价字典失败: {str(e)}")
                
                # 4. 执行三重校正
                corrected_report = msku_report.copy()
                original_report = msku_report.copy()
                abnormal_correction_records = []
                fee_correction_records = []
                cost_correction_records = []
                
                # 4.1 异常订单费用校正
                if not abnormal_fees.empty:
                    logging.info("🔧 执行异常订单费用校正...")
                    
                    # 创建列映射关系
                    column_mapping = {
                        'FBA费': 'FBA发货费(FBA)',
                        '采购成本': '采购成本',
                        '头程费用': '头程成本',
                        '平台费': '平台费',
                        '销售额': 'FBA销售额',
                        '买家运费': '买家运费',
                        '促销折扣': '促销折扣',
                        '其他成本': '其他成本',
                        '站外推广费': '站外推广费'
                    }
                    
                    # 将MSKU维度报表与产品资料表合并，获取SKC信息
                    corrected_report['MSKU'] = corrected_report['MSKU'].astype(str)
                    abnormal_fees['MSKU'] = abnormal_fees['MSKU'].astype(str)
                    
                    corrected_count = 0
                    for _, abnormal_row in abnormal_fees.iterrows():
                        msku = abnormal_row['MSKU']
                        
                        # 查找MSKU维度报表中的对应行
                        msku_idx = corrected_report[corrected_report['MSKU'] == msku].index
                        
                        if len(msku_idx) > 0:
                            idx = msku_idx[0]
                            
                            # 对应列进行校正
                            for abnormal_col, report_col in column_mapping.items():
                                if abnormal_col in abnormal_row and report_col in corrected_report.columns:
                                    if pd.notna(abnormal_row[abnormal_col]) and abnormal_row[abnormal_col] != 0:
                                        # 记录校正前的值
                                        original_value = corrected_report.at[idx, report_col]
                                        
                                        # 进行校正（相减）
                                        corrected_report.at[idx, report_col] = corrected_report.at[idx, report_col] - abnormal_row[abnormal_col]
                                        
                                        # 记录校正信息
                                        abnormal_correction_records.append({
                                            'MSKU': msku,
                                            f'{report_col}_原始值': round(original_value, 2),
                                            f'{report_col}_校正值': round(corrected_report.at[idx, report_col], 2),
                                            f'{report_col}_异常费用': round(abnormal_row[abnormal_col], 2)
                                        })
                            
                            corrected_count += 1
                    
                    logging.info(f"✅ 异常订单费用校正完成，校正了{corrected_count}个MSKU")
                
                # 4.2 FBA配送费理想校正
                if skc_min_shipping_fees and 'FBA销量' in corrected_report.columns:
                    logging.info("🔧 执行FBA配送费理想校正...")
                    
                    try:
                        # 将MSKU维度报表与产品资料表合并，获取SKC信息
                        corrected_report['MSKU'] = corrected_report['MSKU'].astype(str)
                        product_info_df['MSKU'] = product_info_df['MSKU'].astype(str)
                        
                        merged_df = pd.merge(corrected_report, product_info_df[['MSKU', 'SKC']], on='MSKU', how='left')
                        
                        # 检查FBA补换货量列
                        fba_replacement_column = None
                        possible_replacement_names = [
                            'FBA补(换)货量', 'FBA补（换）货量', 'FBA补换货量', 'FBA补货量', 
                            'FBA换货量', '补货数量', '换货数量', '补换货量'
                        ]
                        
                        for possible_name in possible_replacement_names:
                            if possible_name in corrected_report.columns:
                                fba_replacement_column = possible_name
                                break
                        
                        if not fba_replacement_column:
                            # 创建零值列
                            corrected_report['FBA补换货量'] = 0
                            fba_replacement_column = 'FBA补换货量'
                            logging.info("⚠️ 未找到FBA补换货量列，使用零值")
                        
                        ideal_corrected_count = 0
                        for idx, row in merged_df.iterrows():
                            msku = row['MSKU']
                            skc = row['SKC']
                            
                            # 跳过没有SKC信息的MSKU
                            if pd.isna(skc) or skc not in skc_min_shipping_fees:
                                continue
                            
                            # 获取FBA销量和FBA补（换）货量
                            fba_sales = row['FBA销量'] if not pd.isna(row['FBA销量']) else 0
                            fba_replacement = row[fba_replacement_column] if not pd.isna(row[fba_replacement_column]) else 0
                            
                            # 确保销量和补换货量是数值类型
                            try:
                                fba_sales = float(fba_sales)
                                fba_replacement = float(fba_replacement)
                            except (ValueError, TypeError):
                                continue
                            
                            # 计算总数量
                            total_quantity = fba_sales + fba_replacement
                            
                            # 如果总数量为0，跳过
                            if total_quantity == 0:
                                continue
                            
                            # 获取原始FBA发货费
                            original_shipping_fee = row['FBA发货费(FBA)']
                            
                            # 确保原始FBA发货费是数值类型
                            try:
                                original_shipping_fee = float(original_shipping_fee)
                            except (ValueError, TypeError):
                                continue
                            
                            # 获取该SKC的最低单个实际配送费
                            min_fee_abs = skc_min_shipping_fees[skc]['min_fee']
                            
                            # 计算理想的FBA发货费（使用负值，因为费用是负数）
                            ideal_shipping_fee = -min_fee_abs * total_quantity
                            ideal_shipping_fee = round(ideal_shipping_fee, 2)
                            
                            # 计算校正量（理想 - 原始）
                            correction_amount = ideal_shipping_fee - original_shipping_fee
                            correction_amount = round(correction_amount, 2)
                            
                            # 如果校正量绝对值小于0.01，则视为不需要校正
                            if abs(correction_amount) < 0.01:
                                continue
                            
                            # 更新FBA发货费
                            corrected_report.at[idx, 'FBA发货费(FBA)'] = ideal_shipping_fee
                            
                            # 记录校正信息
                            fee_correction_records.append({
                                'MSKU': msku,
                                'SKC': skc,
                                'FBA销量': fba_sales,
                                'FBA补换货量': fba_replacement,
                                '总数量': total_quantity,
                                '原始FBA发货费': round(original_shipping_fee, 2),
                                '理想FBA发货费': ideal_shipping_fee,
                                '校正量': correction_amount,
                                '单个最低配送费': round(-min_fee_abs, 2)
                            })
                            
                            ideal_corrected_count += 1
                        
                        logging.info(f"✅ FBA配送费理想校正完成，校正了{ideal_corrected_count}个MSKU")
                        
                    except Exception as e:
                        logging.error(f"❌ FBA配送费理想校正失败: {str(e)}")
                
                # 4.3 头程成本理想校正
                if skc_min_shipping_costs and 'FBA销量' in corrected_report.columns:
                    logging.info("🔧 执行头程成本理想校正...")
                    
                    try:
                        # 将MSKU维度报表与产品资料表合并，获取SKC信息
                        merged_df = pd.merge(corrected_report, product_info_df[['MSKU', 'SKC']], on='MSKU', how='left')
                        
                        # 检查FBA补换货量列
                        fba_replacement_column = None
                        possible_replacement_names = [
                            'FBA补(换)货量', 'FBA补（换）货量', 'FBA补换货量', 'FBA补货量', 
                            'FBA换货量', '补货数量', '换货数量', '补换货量'
                        ]
                        
                        for possible_name in possible_replacement_names:
                            if possible_name in corrected_report.columns:
                                fba_replacement_column = possible_name
                                break
                        
                        if not fba_replacement_column:
                            # 创建零值列
                            corrected_report['FBA补换货量'] = 0
                            fba_replacement_column = 'FBA补换货量'
                            logging.info("⚠️ 未找到FBA补换货量列，使用零值")
                        
                        cost_corrected_count = 0
                        for idx, row in merged_df.iterrows():
                            msku = row['MSKU']
                            skc = row['SKC']
                            
                            # 跳过没有SKC信息的MSKU
                            if pd.isna(skc) or skc not in skc_min_shipping_costs:
                                continue
                            
                            # 获取FBA销量和FBA补（换）货量
                            fba_sales = row['FBA销量'] if not pd.isna(row['FBA销量']) else 0
                            fba_replacement = row[fba_replacement_column] if not pd.isna(row[fba_replacement_column]) else 0
                            
                            # 确保销量和补换货量是数值类型
                            try:
                                fba_sales = float(fba_sales)
                                fba_replacement = float(fba_replacement)
                            except (ValueError, TypeError):
                                continue
                            
                            # 计算总数量
                            total_quantity = fba_sales + fba_replacement
                            
                            # 如果总数量为0，跳过
                            if total_quantity == 0:
                                continue
                            
                            # 获取原始头程成本
                            original_shipping_cost = row['头程成本']
                            
                            # 确保原始头程成本是数值类型
                            try:
                                original_shipping_cost = float(original_shipping_cost)
                            except (ValueError, TypeError):
                                continue
                            
                            # 获取该SKC的最低头程均价
                            min_cost_abs = skc_min_shipping_costs[skc]['min_cost']
                            
                            # 计算理想的头程成本（使用负值，因为费用是负数）
                            ideal_shipping_cost = -min_cost_abs * total_quantity
                            ideal_shipping_cost = round(ideal_shipping_cost, 2)
                            
                            # 计算校正量（理想 - 原始）
                            correction_amount = ideal_shipping_cost - original_shipping_cost
                            correction_amount = round(correction_amount, 2)
                            
                            # 如果校正量绝对值小于0.01，则视为不需要校正
                            if abs(correction_amount) < 0.01:
                                continue
                            
                            # 更新头程成本
                            corrected_report.at[idx, '头程成本'] = ideal_shipping_cost
                            
                            # 记录校正信息
                            cost_correction_records.append({
                                'MSKU': msku,
                                'SKC': skc,
                                'FBA销量': fba_sales,
                                'FBA补换货量': fba_replacement,
                                '总数量': total_quantity,
                                '原始头程成本': round(original_shipping_cost, 2),
                                '理想头程成本': ideal_shipping_cost,
                                '校正量': correction_amount,
                                '单个最低头程均价': round(-min_cost_abs, 2)
                            })
                            
                            cost_corrected_count += 1
                        
                        logging.info(f"✅ 头程成本理想校正完成，校正了{cost_corrected_count}个MSKU")
                        
                    except Exception as e:
                        logging.error(f"❌ 头程成本理想校正失败: {str(e)}")
                
                # 5. 生成校正后的文件（按桌面版6个工作表结构）
                correction_output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'MSKU利润报表校正结果_{timestamp}.xlsx')
                
                with pd.ExcelWriter(correction_output_path, engine='openpyxl') as writer:
                    # 1. 校正后MSKU报表
                    corrected_report.to_excel(writer, sheet_name='校正后MSKU报表', index=False)
                    
                    # 2. 原始MSKU报表
                    original_report.to_excel(writer, sheet_name='原始MSKU报表', index=False)
                    
                    # 3. FBA配送费理想校正记录
                    if fee_correction_records:
                        fee_correction_df = pd.DataFrame(fee_correction_records)
                        fee_correction_df.to_excel(writer, sheet_name='FBA配送费理想校正记录', index=False)
                    else:
                        pd.DataFrame(columns=['MSKU', 'SKC', 'FBA销量', 'FBA补换货量', '总数量', '原始FBA发货费', '理想FBA发货费', '校正量', '单个最低配送费']).to_excel(writer, sheet_name='FBA配送费理想校正记录', index=False)
                    
                    # 4. 头程成本理想校正记录
                    if cost_correction_records:
                        cost_correction_df = pd.DataFrame(cost_correction_records)
                        cost_correction_df.to_excel(writer, sheet_name='头程成本理想校正记录', index=False)
                    else:
                        pd.DataFrame(columns=['MSKU', 'SKC', 'FBA销量', 'FBA补换货量', '总数量', '原始头程成本', '理想头程成本', '校正量', '单个最低头程均价']).to_excel(writer, sheet_name='头程成本理想校正记录', index=False)
                    
                    # 5. 异常订单校正记录
                    if abnormal_correction_records:
                        abnormal_correction_df = pd.DataFrame(abnormal_correction_records)
                        abnormal_correction_df.to_excel(writer, sheet_name='异常订单校正记录', index=False)
                    else:
                        pd.DataFrame(columns=['MSKU']).to_excel(writer, sheet_name='异常订单校正记录', index=False)
                    
                    # 6. 异常订单费用
                    if not abnormal_fees.empty:
                        abnormal_fees.to_excel(writer, sheet_name='异常订单费用', index=False)
                    else:
                        pd.DataFrame(columns=['MSKU']).to_excel(writer, sheet_name='异常订单费用', index=False)
                
                # 计算总校正记录数
                total_corrections = len(abnormal_correction_records) + len(fee_correction_records) + len(cost_correction_records)
                
                result['download_files'].append({
                    'name': 'MSKU利润报表校正结果',
                    'filename': os.path.basename(correction_output_path),
                    'path': correction_output_path,
                    'description': f'包含6个工作表：校正后MSKU报表、原始MSKU报表、FBA配送费理想校正记录、头程成本理想校正记录、异常订单校正记录、异常订单费用，共校正了{total_corrections}项'
                })
                
                result['steps'][-1]['status'] = f'✅ MSKU维度利润报表校正完成，共校正了{total_corrections}项（异常订单: {len(abnormal_correction_records)}, FBA配送费: {len(fee_correction_records)}, 头程成本: {len(cost_correction_records)}）'
                
            except Exception as e:
                result['steps'][-1]['status'] = f'❌ 校正失败：{str(e)}'
                logging.error(f"MSKU维度利润报表校正失败: {str(e)}")
                # 校正失败不影响整体流程，继续执行
        
        result['success'] = True
        return result
        
    except Exception as e:
        result['error'] = f'处理过程中发生错误：{str(e)}'
        return result

@app.route('/check_order_profit', methods=['POST'])
def check_order_profit():
    """检查订单利润报表的日期范围"""
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有选择文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '文件格式不支持，请上传CSV或Excel文件'})
        
        # 临时保存文件
        temp_filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{temp_filename}")
        file.save(temp_path)
        
        try:
            # 读取文件，表头在第二行
            if temp_path.endswith('.csv'):
                df = pd.read_csv(temp_path, header=1)
            else:
                df = pd.read_excel(temp_path, header=1)
            
            # 检查结算时间列是否存在
            if '结算时间' not in df.columns:
                return jsonify({
                    'success': False, 
                    'error': '文件缺少必要的"结算时间"列',
                    'available_columns': list(df.columns)
                })
            
            # 检查国家列是否存在
            if '国家' not in df.columns:
                return jsonify({
                    'success': False,
                    'error': '文件缺少必要的"国家"列',
                    'available_columns': list(df.columns)
                })
            
            # 检查国家数据一致性
            unique_countries = df['国家'].dropna().unique()
            if len(unique_countries) > 1:
                return jsonify({
                    'success': False,
                    'error': f'检测到多个不同国家！订单数据必须来自同一个国家。发现的国家：{", ".join(unique_countries)}',
                    'details': {
                        'countries_found': unique_countries.tolist(),
                        'total_countries': len(unique_countries),
                        'sample_countries': unique_countries[:5].tolist()
                    }
                })
            elif len(unique_countries) == 0:
                return jsonify({
                    'success': False,
                    'error': '国家列没有有效数据'
                })
            else:
                country_name = unique_countries[0]
                logging.info(f"✅ 国家检查通过：所有订单都来自 {country_name}")
            
            # 将结算时间转换为日期类型
            try:
                df['结算时间'] = pd.to_datetime(df['结算时间'])
            except Exception as date_error:
                return jsonify({
                    'success': False, 
                    'error': f'结算时间格式无法解析: {str(date_error)}'
                })
            
            # 获取日期范围
            earliest_date = df['结算时间'].min()
            latest_date = df['结算时间'].max()
            
            # 检查每一行的结算时间是否在旺季区间内
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
            
            # 对每一行应用检查函数
            in_peak_season = df['结算时间'].apply(is_in_peak_season)
            peak_count = int(in_peak_season.sum())  # 转换为Python int
            non_peak_count = int(len(df) - peak_count)  # 转换为Python int
            
            # 检查必要字段是否存在
            required_fields = [
                '结算时间', '销售额', '买家运费', 'FBA费', '促销折扣', 
                'MSKU', '采购成本', '头程费用', '平台费', '数量', '国家'
            ]
            missing_fields = [field for field in required_fields if field not in df.columns]
            if missing_fields:
                return jsonify({
                    'success': False,
                    'error': f'文件缺少必要字段：{", ".join(missing_fields)}',
                    'details': {
                        'missing_fields': missing_fields,
                        'available_columns': list(df.columns),
                        'required_fields': required_fields
                    }
                })
            
            # 检查"国家"列数据一致性
            if '国家' in df.columns:
                unique_countries = df['国家'].dropna().unique()
                if len(unique_countries) > 1:
                    return jsonify({
                        'success': False,
                        'error': f'检测到多个不同国家！订单数据必须来自同一个国家',
                        'details': {
                            'countries_found': unique_countries.tolist(),
                            'total_countries': len(unique_countries),
                            'sample_countries': unique_countries[:5].tolist()
                        }
                    })
                elif len(unique_countries) == 0:
                    return jsonify({
                        'success': False,
                        'error': '国家列没有有效数据'
                    })
                else:
                    country_name = unique_countries[0]
                    logging.info(f"✅ 国家检查通过：所有订单都来自 {country_name}")
            else:
                return jsonify({
                    'success': False,
                    'error': '文件缺少必要的"国家"列'
                })
            
            # 检查费用类型是否为Refund
            if '费用类型' in df.columns:
                refund_orders = df[df['费用类型'] == 'Refund']
                if not refund_orders.empty:
                    return jsonify({
                        'success': False,
                        'error': f'检测到{len(refund_orders)}条费用类型为"Refund"的记录，程序拒绝处理',
                        'details': {
                            'refund_count': int(len(refund_orders)),
                            'total_orders': int(len(df))
                        }
                    })
            
            # 检查日期范围是否混合（不允许同时存在旺季和非旺季）
            all_in_peak_season = in_peak_season.all()
            all_in_off_season = (~in_peak_season).all()
            
            if not (all_in_peak_season or all_in_off_season):
                # 混合周期 - 既有旺季又有非旺季
                non_peak_examples = df.loc[~in_peak_season, '结算时间'].head(5).dt.strftime('%Y-%m-%d').tolist()
                peak_examples = df.loc[in_peak_season, '结算时间'].head(5).dt.strftime('%Y-%m-%d').tolist()
                return jsonify({
                    'success': False,
                    'error': '检测到混合结算周期！订单数据不允许同时存在旺季和淡季范围日期',
                    'details': {
                        'date_range': f'{earliest_date.strftime("%Y-%m-%d")} 至 {latest_date.strftime("%Y-%m-%d")}',
                        'total_orders': int(len(df)),
                        'peak_orders': peak_count,
                        'non_peak_orders': non_peak_count,
                        'peak_examples': peak_examples,
                        'non_peak_examples': non_peak_examples,
                        'peak_season_range': '10月15日00:00-次年1月14日24:59'
                    }
                })
            
            # 确定是旺季还是淡季
            season_type = "旺季" if all_in_peak_season else "淡季"
            
            # 所有检查通过
            return jsonify({
                'success': True,
                'message': f'✅ 检查通过！所有订单都在{season_type}配送费结算日期范围内',
                'details': {
                    'date_range': f'{earliest_date.strftime("%Y-%m-%d")} 至 {latest_date.strftime("%Y-%m-%d")}',
                    'total_orders': int(len(df)),
                    'season_type': season_type,
                    'peak_orders': peak_count if all_in_peak_season else 0,
                    'off_season_orders': non_peak_count if all_in_off_season else 0
                }
            })
            
        finally:
            # 安全删除临时文件
            safe_remove_file(temp_path)
                
    except Exception as e:
        # 确保删除临时文件
        if 'temp_path' in locals():
            safe_remove_file(temp_path)
        
        return jsonify({
            'success': False,
            'error': f'检查过程中出现错误: {str(e)}'
        })

@app.route('/check_hual_msku', methods=['POST'])
def check_hual_msku():
    """检查Hual MSKU列表文件"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有选择文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '文件格式不支持，请上传Excel文件'})
        
        temp_filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{temp_filename}")
        file.save(temp_path)
        
        try:
            # 读取Excel文件的第一个工作表
            df = pd.read_excel(temp_path, sheet_name=0)
            
            # 检查必要字段
            required_fields = ['MSKU']
            missing_fields = [field for field in required_fields if field not in df.columns]
            if missing_fields:
                return jsonify({
                    'success': False,
                    'error': f'文件缺少必要字段：{", ".join(missing_fields)}',
                    'details': {
                        'missing_fields': missing_fields,
                        'available_columns': list(df.columns),
                        'required_fields': required_fields
                    }
                })
            
            # 检查MSKU列是否有数据
            if df['MSKU'].isna().all():
                return jsonify({
                    'success': False,
                    'error': 'MSKU列没有任何数据'
                })
            
            valid_msku_count = df['MSKU'].notna().sum()
            
            return jsonify({
                'success': True,
                'message': '✅ Hual MSKU列表检查通过！',
                'details': {
                    'total_rows': int(len(df)),
                    'valid_msku_count': int(valid_msku_count),
                    'columns': list(df.columns)
                }
            })
            
        finally:
            safe_remove_file(temp_path)
                
    except Exception as e:
        if 'temp_path' in locals():
            safe_remove_file(temp_path)
        return jsonify({
            'success': False,
            'error': f'检查过程中出现错误: {str(e)}'
        })

@app.route('/check_product_info', methods=['POST'])
def check_product_info():
    """检查产品资料表文件"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有选择文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '文件格式不支持，请上传Excel文件'})
        
        temp_filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{temp_filename}")
        file.save(temp_path)
        
        try:
            # 尝试读取"单个产品"工作表，如果不存在则读取第一个工作表
            try:
                df = pd.read_excel(temp_path, sheet_name='单个产品')
                sheet_name = '单个产品'
            except:
                df = pd.read_excel(temp_path, sheet_name=0)
                sheet_name = '第一个工作表'
            
            # 检查必要字段（智能匹配）
            required_base_fields = ['SKC', 'MSKU', '品质']
            sku_field = None
            
            # 智能匹配SKU字段
            for col in df.columns:
                if 'SKU' in str(col) and col != 'MSKU' and col != 'SKC':
                    if '必填' in str(col) or '*' in str(col):
                        sku_field = col
                        break
            
            if not sku_field:
                # 如果没有找到带标记的SKU字段，寻找普通SKU字段
                for col in df.columns:
                    if str(col).strip() == 'SKU':
                        sku_field = col
                        break
            
            missing_fields = []
            for field in required_base_fields:
                if field not in df.columns:
                    missing_fields.append(field)
            
            if not sku_field:
                missing_fields.append('SKU（必填）')
            
            if missing_fields:
                return jsonify({
                    'success': False,
                    'error': f'文件缺少必要字段：{", ".join(missing_fields)}',
                    'details': {
                        'missing_fields': missing_fields,
                        'available_columns': list(df.columns),
                        'required_fields': required_base_fields + ['SKU（必填）'],
                        'sheet_name': sheet_name
                    }
                })
            
            # 检查关键列是否有数据
            data_issues = []
            if df['MSKU'].isna().all():
                data_issues.append('MSKU列没有任何数据')
            if df['SKC'].isna().all():
                data_issues.append('SKC列没有任何数据')
            if df[sku_field].isna().all():
                data_issues.append(f'{sku_field}列没有任何数据')
            
            if data_issues:
                return jsonify({
                    'success': False,
                    'error': '数据质量问题：' + '，'.join(data_issues)
                })
            
            valid_rows = df.dropna(subset=['MSKU', 'SKC', sku_field]).shape[0]
            
            return jsonify({
                'success': True,
                'message': '✅ 产品资料表检查通过！',
                'details': {
                    'sheet_name': sheet_name,
                    'total_rows': int(len(df)),
                    'valid_rows': int(valid_rows),
                    'sku_field': sku_field,
                    'columns': list(df.columns)
                }
            })
            
        finally:
            safe_remove_file(temp_path)
                
    except Exception as e:
        if 'temp_path' in locals():
            safe_remove_file(temp_path)
        return jsonify({
            'success': False,
            'error': f'检查过程中出现错误: {str(e)}'
        })

@app.route('/check_msku_profit', methods=['POST'])
def check_msku_profit():
    """检查MSKU维度利润报表文件"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有选择文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '文件格式不支持，请上传CSV或Excel文件'})
        
        temp_filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{temp_filename}")
        file.save(temp_path)
        
        try:
            # 读取文件，表头在第二行
            if temp_path.endswith('.csv'):
                df = pd.read_csv(temp_path, header=1)
            else:
                df = pd.read_excel(temp_path, header=1)
            
            # 检查必要字段
            required_fields = [
                'MSKU', 'FBA发货费(FBA)', '采购成本', '头程成本', 
                '平台费', 'FBA销售额', '毛利润'
            ]
            missing_fields = [field for field in required_fields if field not in df.columns]
            if missing_fields:
                return jsonify({
                    'success': False,
                    'error': f'文件缺少必要字段：{", ".join(missing_fields)}',
                    'details': {
                        'missing_fields': missing_fields,
                        'available_columns': list(df.columns),
                        'required_fields': required_fields
                    }
                })
            
            # 检查MSKU列是否有数据
            if df['MSKU'].isna().all():
                return jsonify({
                    'success': False,
                    'error': 'MSKU列没有任何数据'
                })
            
            # 检查日期列是否存在（MSKU维度利润报表使用"日期"列而不是"结算时间"列）
            if '日期' not in df.columns:
                return jsonify({
                    'success': False, 
                    'error': '文件缺少必要的"日期"列，MSKU维度利润报表需要包含日期信息用于配送周期检查',
                    'available_columns': list(df.columns)
                })
            
            # 检查国家列是否存在
            if '国家' not in df.columns:
                return jsonify({
                    'success': False,
                    'error': '文件缺少必要的"国家"列，MSKU维度利润报表需要包含国家信息',
                    'available_columns': list(df.columns)
                })
            
            # 检查国家数据一致性
            unique_countries = df['国家'].dropna().unique()
            if len(unique_countries) > 1:
                return jsonify({
                    'success': False,
                    'error': f'检测到多个不同国家！MSKU维度利润报表数据必须来自同一个国家。发现的国家：{", ".join(unique_countries)}',
                    'details': {
                        'countries_found': unique_countries.tolist(),
                        'total_countries': len(unique_countries),
                        'sample_countries': unique_countries[:5].tolist()
                    }
                })
            elif len(unique_countries) == 0:
                return jsonify({
                    'success': False,
                    'error': '国家列没有有效数据'
                })
            else:
                country_name = unique_countries[0]
                logging.info(f"✅ MSKU报表国家检查通过：所有数据都来自 {country_name}")
            
            # 解析日期范围格式（如：2024-10-15~2025-01-14）
            def parse_date_range(date_range_str):
                """
                解析日期范围字符串，返回开始和结束日期
                Args:
                    date_range_str: 日期范围字符串，格式如"2024-10-15~2025-01-14"
                Returns:
                    tuple: (start_date, end_date) 或 (None, None) 如果解析失败
                """
                try:
                    if pd.isna(date_range_str) or not isinstance(date_range_str, str):
                        return None, None
                    
                    # 检查是否包含范围分隔符
                    if '~' in date_range_str:
                        parts = date_range_str.split('~')
                        if len(parts) == 2:
                            start_date = pd.to_datetime(parts[0].strip())
                            end_date = pd.to_datetime(parts[1].strip())
                            return start_date, end_date
                    else:
                        # 如果没有范围分隔符，尝试解析单个日期
                        single_date = pd.to_datetime(date_range_str.strip())
                        return single_date, single_date
                except Exception as e:
                    logging.warning(f"日期范围解析失败：{date_range_str}, 错误：{str(e)}")
                    return None, None
                
                return None, None
            
            # 解析所有日期范围
            date_ranges = []
            invalid_dates = []
            
            for idx, date_str in enumerate(df['日期']):
                start_date, end_date = parse_date_range(date_str)
                if start_date is not None and end_date is not None:
                    date_ranges.append((start_date, end_date))
                else:
                    invalid_dates.append((idx, date_str))
            
            if invalid_dates:
                return jsonify({
                    'success': False, 
                    'error': f'日期格式无法解析，发现{len(invalid_dates)}个无效的日期格式。MSKU维度利润报表的日期应为范围格式如"2024-10-15~2025-01-14"',
                    'details': {
                        'invalid_dates': invalid_dates[:5],  # 只显示前5个
                        'total_invalid': len(invalid_dates)
                    }
                })
            
            # 获取所有日期的最小和最大值
            all_dates = []
            for start_date, end_date in date_ranges:
                all_dates.extend([start_date, end_date])
            
            earliest_date = min(all_dates)
            latest_date = max(all_dates)
            
            # 如果是美国市场，检查配送周期一致性
            if country_name == "美国":
                def is_date_range_in_peak_season(start_date, end_date):
                    """
                    检查日期范围是否完全在旺季范围内
                    旺季定义：10月15日00:00 至 次年1月14日23:59:59
                    """
                    def is_in_peak_season(date):
                        month = date.month
                        day = date.day
                        
                        # 检查是否在10月15日至次年1月14日之间
                        if month == 10 and day >= 15:
                            return True
                        elif month == 11 or month == 12:
                            return True
                        elif month == 1 and day <= 14:  # 1月14日或之前
                            return True
                        else:
                            return False
                    
                    # 日期范围完全在旺季内，需要开始和结束日期都在旺季内
                    return is_in_peak_season(start_date) and is_in_peak_season(end_date)
                
                def is_date_range_in_off_season(start_date, end_date):
                    """
                    检查日期范围是否完全在淡季范围内
                    """
                    def is_in_peak_season(date):
                        month = date.month
                        day = date.day
                        
                        # 检查是否在10月15日至次年1月14日之间
                        if month == 10 and day >= 15:
                            return True
                        elif month == 11 or month == 12:
                            return True
                        elif month == 1 and day <= 14:  # 1月14日或之前
                            return True
                        else:
                            return False
                    
                    # 日期范围完全在淡季内，需要开始和结束日期都不在旺季内
                    return not is_in_peak_season(start_date) and not is_in_peak_season(end_date)
                
                # 检查所有日期范围
                peak_season_ranges = 0
                off_season_ranges = 0
                mixed_ranges = 0
                
                for start_date, end_date in date_ranges:
                    if is_date_range_in_peak_season(start_date, end_date):
                        peak_season_ranges += 1
                    elif is_date_range_in_off_season(start_date, end_date):
                        off_season_ranges += 1
                    else:
                        mixed_ranges += 1
                
                # 检查是否存在混合配送周期
                if mixed_ranges > 0 or (peak_season_ranges > 0 and off_season_ranges > 0):
                    # 找出最早年份，用于显示旺季时间范围
                    earliest_year = earliest_date.year
                    peak_season_start = f"{earliest_year}-10-15 00:00"
                    peak_season_end = f"{earliest_year + 1}-01-14 23:59"
                    
                    return jsonify({
                        'success': False,
                        'error': f'检测到混合配送周期！MSKU维度利润报表数据不允许同时包含旺季和淡季配送费结算周期',
                        'details': {
                            'peak_season_ranges': peak_season_ranges,
                            'off_season_ranges': off_season_ranges,
                            'mixed_ranges': mixed_ranges,
                            'total_ranges': len(date_ranges),
                            'peak_season_range': f'{peak_season_start} 至 {peak_season_end}',
                            'date_range': f'{earliest_date.strftime("%Y-%m-%d")} 至 {latest_date.strftime("%Y-%m-%d")}',
                            'country': country_name
                        }
                    })
                
                # 确定是旺季还是淡季
                if peak_season_ranges > 0:
                    season_type = "旺季"
                else:
                    season_type = "淡季"
                
                logging.info(f"✅ MSKU报表配送周期检查通过：所有日期范围都在{season_type}配送费结算周期内")
            else:
                season_type = "非美国市场，跳过配送周期检查"
                logging.info(f"✅ MSKU报表配送周期：{season_type}")
            
            # 检查费用类型是否为Order
            if '费用类型' in df.columns:
                non_order_records = df[df['费用类型'] != 'Order']
                if not non_order_records.empty:
                    return jsonify({
                        'success': False,
                        'error': f'检测到{len(non_order_records)}条费用类型不为"Order"的记录，MSKU维度利润报表应该只包含费用类型为"Order"的数据',
                        'details': {
                            'non_order_count': int(len(non_order_records)),
                            'total_count': int(len(df)),
                            'fee_types_found': non_order_records['费用类型'].unique().tolist()
                        }
                    })
                else:
                    logging.info("✅ MSKU报表费用类型检查通过：所有记录的费用类型都为'Order'")
            else:
                logging.warning("⚠️ MSKU报表未找到'费用类型'列，跳过费用类型检查")
            
            valid_msku_count = df['MSKU'].notna().sum()
            
            return jsonify({
                'success': True,
                'message': '✅ MSKU维度利润报表检查通过！',
                'details': {
                    'total_rows': int(len(df)),
                    'valid_msku_count': int(valid_msku_count),
                    'country': country_name,
                    'season_type': season_type,
                    'date_range': f'{earliest_date.strftime("%Y-%m-%d")} 至 {latest_date.strftime("%Y-%m-%d")}',
                    'columns': list(df.columns)
                }
            })
            
        finally:
            safe_remove_file(temp_path)
                
    except Exception as e:
        if 'temp_path' in locals():
            safe_remove_file(temp_path)
        return jsonify({
            'success': False,
            'error': f'检查过程中出现错误: {str(e)}'
        })

@app.route('/download/<filename>')
def download_file(filename):
    """下载生成的文件"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            flash('❌ 文件不存在', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'❌ 下载失败：{str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/help')
def help_page():
    """帮助页面"""
    file_requirements = get_file_requirements()
    return render_template('help.html', file_requirements=file_requirements)

@app.errorhandler(413)
def too_large(e):
    """文件过大错误处理"""
    flash('❌ 文件过大，请上传小于50MB的文件', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000) 