import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os
import traceback
from datetime import datetime, timedelta

def calculate_abnormal_fees(df):
    """计算异常订单（VINE订单、换货订单、新品入仓优惠订单、Hual订单等）的MSKU维度费用
    费用类型：FBA费、采购成本、头程费用、平台费、销售额、销售税、买家运费、买家运费税、礼品包装、礼品包装税、
    促销折扣、促销折扣税、代扣代缴增值税、市场预扣税、其他交易费、其他、隐藏税、其他成本、站外推广费
    """
    # 订单维度的所有财务字段
    financial_fields = [
        'FBA费', '采购成本', '头程费用', '平台费', 
        '销售额', '销售税', '买家运费', '买家运费税', 
        '礼品包装', '礼品包装税', '促销折扣', '促销折扣税', 
        '代扣代缴增值税', '市场预扣税', '其他交易费', 
        '其他', '隐藏税', '其他成本', '站外推广费'
    ]
    
    # 确保所有字段都存在于DataFrame中
    for field in financial_fields:
        if field not in df.columns:
            print(f"警告: 财务字段 '{field}' 不存在于订单数据中，将设置为0")
            df[field] = 0
    
    # 按MSKU分组并计算各项费用
    agg_dict = {field: 'sum' for field in financial_fields}
    agg_dict['订单类型'] = lambda x: '，'.join(sorted(set(x)))  # 添加订单类型字段
    
    abnormal_fees = df.groupby('MSKU').agg(agg_dict).reset_index()
    
    # 添加费用说明
    print("\n异常订单费用汇总说明：")
    print("1. 所有费用项均为负值表示")
    print("2. 这些费用需要在MSKU维度利润报表中减去")
    print("3. 费用类型包括：")
    for field in financial_fields:
        print(f"   - {field}")
    print("4. 订单类型：记录每个MSKU存在的特殊订单类型")
    
    return abnormal_fees

def correct_msku_profit_report(msku_report_data, abnormal_fees, skc_min_shipping_fees=None):
    """根据异常订单费用数据校正MSKU维度利润报表
    
    映射关系：
    - 异常订单中的"FBA费"对应MSKU维度报表中的"FBA发货费(FBA)"
    - 异常订单中的"采购成本"对应MSKU维度报表中的"采购成本"
    - 异常订单中的"头程费用"对应MSKU维度报表中的"头程成本"
    - 异常订单中的"平台费"对应MSKU维度报表中的"平台费"
    - 异常订单中的"销售额"对应MSKU维度报表中的"FBA销售额"
    - 异常订单中的"销售税"对应MSKU维度报表中的"商品价格税"
    - 异常订单中的"买家运费"对应MSKU维度报表中的"买家运费"
    - 异常订单中的"买家运费税"对应MSKU维度报表中的"税费-销售税-买家运费税"
    - 异常订单中的"礼品包装税"对应MSKU维度报表中的"税费-销售税-礼品包装税"
    - 异常订单中的"促销折扣"对应MSKU维度报表中的"促销折扣"
    - 异常订单中的"促销折扣税"对应MSKU维度报表中的"税费-销售税-促销折扣税"
    - 异常订单中的"市场预扣税"对应MSKU维度报表中的"市场税"
    - 异常订单中的"其他成本"对应MSKU维度报表中的"其他成本"
    - 异常订单中的"站外推广费"对应MSKU维度报表中的"站外推广费"
    - 同时也会根据所有收入和费用项重新计算"毛利润"列
    
    注意：异常订单费用包含所有特殊订单类型（VINE订单、换货订单、新品入仓优惠订单和Hual订单）
    
    参数：
        msku_report_data: MSKU维度利润报表DataFrame或文件路径
        abnormal_fees: 异常订单费用数据
        skc_min_shipping_fees: SKC最低单个实际配送费字典，用于理想校正（可选）
    """
    try:
        # 确定输入是DataFrame还是文件路径
        if isinstance(msku_report_data, str):
            # 是文件路径，需要读取文件
            msku_report_path = msku_report_data
            print(f"\n正在读取MSKU维度利润报表: {msku_report_path}")
            print("使用第二行作为表头读取数据...")
            
            # 读取前几行以检查表头情况
            preview_df = pd.read_excel(msku_report_path, nrows=5)
            print("\n预览前5行数据:")
            print(preview_df.head())
            
            # 先读取前两行来获取表头
            header_df = pd.read_excel(msku_report_path, nrows=2, header=None)
            print("\n前两行内容:")
            print(header_df)
            
            # 使用第二行作为表头
            headers = header_df.iloc[1].tolist()
            print(f"\n使用第二行作为表头: {headers[:10]}...")
            
            # 读取完整数据，跳过前两行，使用第二行的值作为列名
            try:
                msku_report = pd.read_excel(
                    msku_report_path,
                    skiprows=2,  # 跳过前两行
                    names=headers  # 使用第二行的值作为列名
                )
                print(f"成功读取数据，共 {len(msku_report)} 行")
            except Exception as e:
                print(f"读取数据时出错: {str(e)}")
                print("尝试使用默认的header=1参数读取...")
                try:
                    msku_report = pd.read_excel(msku_report_path, header=1)
                    print(f"使用header=1成功读取数据，共 {len(msku_report)} 行")
                    print(f"列名: {list(msku_report.columns)[:10]}...")
                except Exception as e2:
                    print(f"使用header=1读取仍然失败: {str(e2)}")
                    raise Exception("无法正确读取MSKU维度利润报表，请检查文件格式")
        else:
            # 是DataFrame，直接使用
            msku_report = msku_report_data
        
        # 创建映射关系字典
        column_mapping = {
            'FBA费': 'FBA发货费(FBA)',
            '采购成本': '采购成本',
            '头程费用': '头程成本',
            '平台费': '平台费',
            '销售额': 'FBA销售额',
            '销售税': '商品价格税',
            '买家运费': '买家运费',
            '买家运费税': '税费-销售税-买家运费税',
            '礼品包装税': '税费-销售税-礼品包装税',
            '促销折扣': '促销折扣',
            '促销折扣税': '税费-销售税-促销折扣税',
            '市场预扣税': '市场税',
            '其他成本': '其他成本',
            '站外推广费': '站外推广费'
        }
        
        # 创建反向映射关系字典，用于获取异常费用数据
        reverse_mapping = {v: k for k, v in column_mapping.items()}
        
        # 检查必要的列是否存在
        available_mapping = {}
        missing_columns = []
        for abnormal_col, report_col in column_mapping.items():
            if report_col in msku_report.columns:
                available_mapping[abnormal_col] = report_col
            else:
                missing_columns.append(report_col)
        
        if missing_columns:
            print(f"警告: 找不到以下MSKU维度报表列: {missing_columns}")
            print(f"可用的列: {list(msku_report.columns)}")
            print("将仅校正存在的列")
        
        # 检查MSKU列是否存在
        if 'MSKU' not in msku_report.columns:
            raise Exception("MSKU维度利润报表缺少必要的列：MSKU")
        
        # 检查毛利润列是否存在
        if '毛利润' not in msku_report.columns:
            print("警告: 找不到毛利润列，将不进行毛利润校正")
        
        # 显示原始数据信息
        print(f"MSKU维度利润报表行数: {len(msku_report)}")
        print(f"异常订单费用汇总行数: {len(abnormal_fees)}")
        
        # 将MSKU列转为字符串类型以确保匹配
        msku_report['MSKU'] = msku_report['MSKU'].astype(str)
        abnormal_fees['MSKU'] = abnormal_fees['MSKU'].astype(str)
        
        # 记录修正前的数据
        original_report = msku_report.copy()
        
        # 创建校正记录列表
        correction_records = []
        
        # 遍历异常费用数据，对MSKU维度报表进行校正
        print("\n开始校正MSKU维度利润报表...")
        corrected_count = 0
        
        # 设置小数位数
        decimal_places = 2
        
        for _, abnormal_row in abnormal_fees.iterrows():
            msku = abnormal_row['MSKU']
            
            # 查找MSKU维度报表中的对应行
            msku_idx = msku_report[msku_report['MSKU'] == msku].index
            
            if len(msku_idx) > 0:
                idx = msku_idx[0]
                # 记录校正前的数据
                original_values = {}
                corrected_values = {}
                abnormal_values = {}
                
                # 记录校正前的毛利润值
                if '毛利润' in msku_report.columns:
                    original_profit = msku_report.at[idx, '毛利润']
                    original_values['毛利润'] = original_profit
                
                # 对应列进行校正
                for abnormal_col, report_col in available_mapping.items():
                    if abnormal_col in abnormal_row and report_col in msku_report.columns:
                        # 记录原始值
                        original_values[report_col] = msku_report.at[idx, report_col]
                        
                        # 记录异常费用值
                        abnormal_values[report_col] = abnormal_row[abnormal_col]
                        
                        # 进行校正（相减）
                        msku_report.at[idx, report_col] = msku_report.at[idx, report_col] - abnormal_row[abnormal_col]
                        
                        # 记录校正后的值
                        corrected_values[report_col] = msku_report.at[idx, report_col]
                
                # 校正毛利润 - 改进计算逻辑，确保结果正确
                if '毛利润' in msku_report.columns:
                    print(f"\n正在为MSKU {msku} 重新计算毛利润...")
                    
                    # 初始化收入和费用总和
                    total_income = 0
                    total_expense = 0
                    
                    # 定义收入和费用列表
                    income_columns = [
                        'FBA销售额', 'FBM销售额', '买家运费', 'FBA库存赔偿', 'COD', '包装收入', 
                        '买家交易保障索赔额', '积分抵减收入', '清算收入', '亚马逊运费赔偿', 'Safe-T索赔',
                        'Netco交易', '赔偿收入', '追索收入', '其他收入-其他', '清算调整', '混合VAT收入',
                        '平台费退款项', '发货费退款项', '其他订单费退款项', '运输标签费退款', '交易费用退款额', '广告退款额'
                    ]
                    
                    expense_columns = [
                        'FBM销售退款额', 'FBA销售退款额', '买家运费退款额', '买家包装退款额', '买家拒付', 
                        '积分抵减退回', '积分费用', '平台费', 'FBA发货费(FBA)', '亚马逊物流客户退货费',
                        'FBA发货费(多渠道)', '其他订单费用', 'FBA国际物流货运费', '调整费用', 'SP广告',
                        'SD广告', 'SB广告', 'SBV广告', '差异分摊', '订阅费', '秒杀费', '优惠券',
                        '早期评论人计划', 'VINE', '其他仓储费', '月仓储费', '月仓储费差异', '月仓储费本月计提',
                        '月仓储费上月冲销', '长期仓储费', '长期仓储费差异', '长期仓储费本月计提', '长期仓储费上月冲销',
                        '库存续订费用', 'FBA销毁费', 'FBA移除费', '入仓手续费', '标签费', '塑料包装费',
                        'FBA卖家退回费', 'FBA仓储费-入库缺陷费', '库存调整费', '合作承运费', '入库配置费（原合仓费）',
                        '超量仓储费', '泡沫包装费', '胶带费', 'AWD处理费', 'AWD运输费', 'AWD仓储费',
                        '卫星仓仓储费', '购买配送费（原运输标签费）', '承运人装运标签调整费', '其他服务费', '人工处理费用',
                        '清算费', 'MFNPostageFee', '站外推广费', '财务费用', '其他费用-发AWD仓库费用',
                        '管理费用', '销售费用（线下）', 'TCS_IGST', 'TCS_SGST', 'TCS_CGST', '混合VAT',
                        'VAT/GST', '商品税调整', '礼品包装税', '买家运费税', '促销折扣税', '商品价格税',
                        'TCS_IGST.1', 'TCS_SGST.1', 'TCS_CGST.1', 'VAT/GST.1', '礼品包装税.1',
                        '买家运费税.1', '促销折扣税.1', '商品价格税.1', '市场税', '市场税退款额', '混合网络费',
                        '采购成本', '头程成本', '其他成本'
                    ]
                    
                    # 特殊处理的列
                    special_columns = {
                        '促销折扣': 'expense',
                        '促销折扣退款额': 'income'
                    }
                    
                    # 计算收入
                    for col in income_columns:
                        if col in msku_report.columns:
                            try:
                                value = msku_report.at[idx, col]
                                if pd.notna(value) and (isinstance(value, (int, float)) or 
                                                      (isinstance(value, str) and value.replace('-', '', 1).replace('.', '', 1).isdigit())):
                                    total_income += float(value)
                            except (ValueError, TypeError) as e:
                                print(f"无法转换列 '{col}' 的值: {e}")
                    
                    # 计算费用
                    for col in expense_columns:
                        if col in msku_report.columns:
                            try:
                                value = msku_report.at[idx, col]
                                if pd.notna(value) and (isinstance(value, (int, float)) or 
                                                      (isinstance(value, str) and value.replace('-', '', 1).replace('.', '', 1).isdigit())):
                                    total_expense += float(value)
                            except (ValueError, TypeError) as e:
                                print(f"无法转换列 '{col}' 的值: {e}")
                    
                    # 处理特殊列
                    for col, category in special_columns.items():
                        if col in msku_report.columns:
                            try:
                                value = msku_report.at[idx, col]
                                if pd.notna(value) and (isinstance(value, (int, float)) or 
                                                      (isinstance(value, str) and value.replace('-', '', 1).replace('.', '', 1).isdigit())):
                                    if category == 'income':
                                        total_income += float(value)
                                    else:  # expense
                                        total_expense += float(value)
                            except (ValueError, TypeError) as e:
                                print(f"无法转换特殊列 '{col}' 的值: {e}")
                    
                    # 计算毛利润
                    calculated_profit = total_income - abs(total_expense)
                    calculated_profit = round(calculated_profit, decimal_places)
                    
                    print(f"毛利润计算结果: 总收入({total_income}) - 总费用({abs(total_expense)}) = {calculated_profit}")
                    
                    # 更新毛利润
                    msku_report.at[idx, '毛利润'] = calculated_profit
                    
                    # 记录校正后的毛利润值
                    corrected_values['毛利润'] = calculated_profit
                    
                    # 记录毛利润调整量（校正后 - 原始值）
                    if isinstance(original_profit, (int, float)) or (isinstance(original_profit, str) and original_profit.replace('-', '', 1).replace('.', '', 1).isdigit()):
                        original_profit_float = float(original_profit)
                        profit_adjustment = calculated_profit - original_profit_float
                        abnormal_values['毛利润'] = round(profit_adjustment, decimal_places)
                    else:
                        abnormal_values['毛利润'] = "N/A"
                
                # 添加到校正记录
                record = {
                    'MSKU': msku
                }
                
                # 添加原始值
                for col in list(available_mapping.values()) + (['毛利润'] if '毛利润' in msku_report.columns else []):
                    record[f"{col}_原始值"] = original_values.get(col, "N/A")
                
                # 添加校正值
                for col in list(available_mapping.values()) + (['毛利润'] if '毛利润' in msku_report.columns else []):
                    record[f"{col}_校正值"] = corrected_values.get(col, "N/A")
                
                # 添加异常费用/调整量
                for col in list(available_mapping.values()) + (['毛利润'] if '毛利润' in msku_report.columns else []):
                    record[f"{col}_异常费用"] = abnormal_values.get(col, 0)
                
                correction_records.append(record)
                corrected_count += 1
        
        print(f"\n校正完成，共校正了 {corrected_count} 个MSKU的数据")
        print(f"包括费用项和毛利润的校正（收入-费用）")
        
        # 创建校正记录DataFrame
        correction_df = pd.DataFrame(correction_records)
        
        return msku_report, original_report, correction_df
    
    except Exception as e:
        import traceback
        print(f"校正MSKU维度利润报表失败：{str(e)}")
        print("\n详细错误信息:")
        traceback.print_exc()
        raise Exception(f"校正MSKU维度利润报表失败：{str(e)}")

def calculate_actual_shipping_fee(row):
    """计算实际配送费
    规则：
    1. 当买家运费为0时，FBA费即为实际配送费
    2. 当买家运费>0时：
       2.1 如果买家运费+促销折扣=0，FBA费即为实际配送费
       2.2 如果买家运费+促销折扣≠0，实际配送费=买家运费+促销折扣+FBA费
    """
    buyer_shipping = row['买家运费']
    fba_fee = row['FBA费']
    promotion_discount = row['促销折扣']
    
    if buyer_shipping == 0:
        return fba_fee
    else:
        temp_result = buyer_shipping + promotion_discount
        if temp_result == 0:
            return fba_fee
        else:
            return temp_result + fba_fee

def read_file(file_path):
    """读取文件内容，支持CSV和Excel格式，从第二行开始读取表头"""
    file_ext = os.path.splitext(file_path)[1].lower()
    df = None
    
    print("\n开始读取文件...")
    print(f"文件路径: {file_path}")
    print(f"文件类型: {file_ext}")
    
    if file_ext == '.csv':
        # 尝试不同的编码方式读取CSV
        encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']
        for encoding in encodings:
            try:
                # 尝试不同的分隔符
                for sep in [',', '\t', ';', '|']:
                    try:
                        print(f"\n尝试使用编码 '{encoding}' 和分隔符 '{sep}' 读取CSV文件...")
                        # 先读取前两行来获取表头
                        header_df = pd.read_csv(
                            file_path,
                            encoding=encoding,
                            sep=sep,
                            engine='python',
                            nrows=1,
                            header=None
                        )
                        # 使用第二行作为表头
                        headers = header_df.iloc[0].tolist()
                        print(f"读取到的表头: {headers}")
                        
                        # 读取完整数据，跳过前两行
                        df = pd.read_csv(
                            file_path,
                            encoding=encoding,
                            sep=sep,
                            engine='python',
                            on_bad_lines='skip',
                            skiprows=2,
                            names=headers
                        )
                        print(f"成功使用编码 '{encoding}' 和分隔符 '{sep}' 读取CSV文件")
                        break
                    except Exception as e:
                        print(f"使用编码 '{encoding}' 和分隔符 '{sep}' 读取失败: {str(e)}")
                        continue
                if df is not None:
                    break
            except Exception as e:
                print(f"使用编码 '{encoding}' 读取失败: {str(e)}")
                continue
        if df is None:
            raise Exception("无法读取CSV文件，请检查文件格式和编码")
    
    elif file_ext in ['.xlsx', '.xls']:
        try:
            print("\n尝试读取Excel文件...")
            # 读取Excel文件，跳过第一行，使用第二行作为表头
            df = pd.read_excel(
                file_path,
                engine='openpyxl' if file_ext == '.xlsx' else 'xlrd',
                header=1
            )
            print("成功读取Excel文件")
        except Exception as e:
            raise Exception(f"无法读取Excel文件：{str(e)}")
    
    else:
        raise Exception("不支持的文件格式，请使用CSV或Excel文件")
    
    print("\n文件读取完成，开始检查数据...")
    print(f"数据列名: {list(df.columns)}")
    
    # 检查费用类型是否为Refund
    if '费用类型' in df.columns:
        if (df['费用类型'] == 'Refund').any():
            raise Exception("检测到订单利润报表中存在费用类型为'Refund'的记录，程序终止。请检查源数据！")
    
    # 检查必要的列是否存在
    required_columns = ['结算时间']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise Exception(f"文件缺少必要的列：{', '.join(missing_columns)}")
    
    # 检查"国家"列是否存在，如果存在并且是"美国"，则进行结算时间范围检查
    is_us_marketplace = False
    if '国家' in df.columns:
        # 检查第一行数据的国家列是否为"美国"
        if len(df) > 0 and df['国家'].iloc[0] == "美国":
            is_us_marketplace = True
            print("\n检测到美国市场数据，将进行结算时间范围检查...")
    
    # 检查结算时间范围
    print("\n正在检查结算时间范围...")
    try:
        # 确保结算时间列为datetime类型
        df['结算时间'] = pd.to_datetime(df['结算时间'])
        print(f"结算时间列数据类型: {df['结算时间'].dtype}")
        
        # 获取最早和最晚的结算时间
        earliest_date = df['结算时间'].min()
        latest_date = df['结算时间'].max()
        earliest_year = earliest_date.year
        print(f"最早的结算时间: {earliest_date}")
        print(f"最晚的结算时间: {latest_date}")
        print(f"最早年份: {earliest_year}")
        
        # 如果是美国市场，需要确认结算时间是否在旺季或淡季范围内
        if is_us_marketplace:
            # 定义旺季和淡季日期范围
            peak_season_start = datetime(earliest_year, 10, 15)  # 当年10月15日
            peak_season_end = datetime(earliest_year + 1, 1, 14, 23, 59, 59)  # 次年1月14日 23:59:59
            
            # 检查订单是否全部在旺季范围内
            all_in_peak_season = ((df['结算时间'] >= peak_season_start) & 
                                 (df['结算时间'] <= peak_season_end)).all()
            
            # 检查订单是否全部在淡季范围内
            all_in_off_season = ((df['结算时间'] < peak_season_start) | 
                                (df['结算时间'] > peak_season_end)).all()
            
            if not (all_in_peak_season or all_in_off_season):
                print("\n错误: 检测到混合结算周期！")
                print(f"旺季配送费结算日期范围：{peak_season_start.strftime('%Y-%m-%d')} 00:00 至 {peak_season_end.strftime('%Y-%m-%d')} 23:59")
                print("淡季配送费结算日期范围：非旺季配送费日期范围")
                print("订单数据的结算周期不允许同时存在旺季和淡季范围日期")
                raise Exception("检测到混合结算周期，请确保数据全部在旺季或全部在淡季")
            
            # 根据是旺季还是淡季，显示相应的信息
            if all_in_peak_season:
                print("\n检测到所有订单都在旺季配送费结算日期范围内")
                print(f"旺季时间范围：{peak_season_start.strftime('%Y-%m-%d')} 00:00 至 {peak_season_end.strftime('%Y-%m-%d')} 23:59")
            else:
                print("\n检测到所有订单都在淡季配送费结算日期范围内")
                print(f"淡季时间范围：非 {peak_season_start.strftime('%Y-%m-%d')} 00:00 至 {peak_season_end.strftime('%Y-%m-%d')} 23:59")
        else:
            print("\n非美国市场数据，跳过结算时间范围验证")
        
        print(f"\n结算时间范围检查通过")
        print(f"数据中的日期范围：{df['结算时间'].min().strftime('%Y-%m-%d')} 至 {df['结算时间'].max().strftime('%Y-%m-%d')}")
        
    except Exception as e:
        if str(e) == "检测到混合结算周期，请确保数据全部在旺季或全部在淡季":
            raise Exception(f"结算时间范围检查失败：{str(e)}")
        else:
            print(f"结算时间范围检查过程中出错：{str(e)}")
            traceback.print_exc()
            raise Exception(f"结算时间范围检查失败：{str(e)}")
    
    return df

def filter_zero_sales_orders(df):
    """筛选销售额为0的订单（用于排除VINE订单和换货订单）"""
    # 确保销售额列为数值类型
    df['销售额'] = pd.to_numeric(df['销售额'], errors='coerce').fillna(0)
    
    # 筛选销售额为0的订单
    zero_sales_df = df[df['销售额'] == 0].copy()
    
    # 打印筛选信息
    total_orders = len(df)
    zero_sales_orders = len(zero_sales_df)
    print(f"\n数据筛选信息：")
    print(f"总订单数：{total_orders}")
    print(f"销售额为0的订单数（VINE订单和换货订单）：{zero_sales_orders}")
    print(f"筛选比例：{(zero_sales_orders/total_orders*100):.2f}%")
    
    return zero_sales_df

def read_hual_msku_list(file_path):
    """读取Hual的MSKU列表文件"""
    try:
        df = pd.read_excel(file_path)
        # 假设MSKU列名为'MSKU'，如果不是，需要根据实际文件调整
        if 'MSKU' not in df.columns:
            raise Exception("Hual MSKU列表文件中未找到'MSKU'列")
        return set(df['MSKU'].astype(str))
    except Exception as e:
        raise Exception(f"读取Hual MSKU列表文件失败：{str(e)}")

def read_product_info(file_path):
    """读取产品资料表，获取SKC关系"""
    try:
        df = pd.read_excel(file_path)
        # 假设SKC列名为'SKC'，MSKU列名为'MSKU'，如果不是，需要根据实际文件调整
        required_columns = ['SKC', 'MSKU']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise Exception(f"产品资料表缺少必要的列：{', '.join(missing_columns)}")
        
        # 检查品质列是否存在
        if '品质' in df.columns:
            print(f"产品资料表中包含'品质'列，唯一值有：{df['品质'].unique()}")
            return df  # 返回完整的产品资料表
        else:
            print("警告：产品资料表中未找到'品质'列，无法进行品质维度分析")
            return df  # 返回完整的产品资料表，以便后续检查
    except Exception as e:
        raise Exception(f"读取产品资料表失败：{str(e)}")

def check_shipping_fee_consistency(msku_summary_df, product_info_df):
    """检查相同SKC的配送费是否一致，并返回每个SKC下所有MSKU及其配送费"""
    print("\n开始检查相同SKC的配送费一致性...")
    
    # 检查输入参数
    if msku_summary_df is None or product_info_df is None:
        print("错误: 输入数据为空")
        return []
    
    # 检查必要的列是否存在
    if '单个实际配送费' not in msku_summary_df.columns:
        print("错误: MSKU汇总表中没有'单个实际配送费'列")
        print(f"可用的列: {msku_summary_df.columns.tolist()}")
        return []
    
    if 'MSKU' not in msku_summary_df.columns:
        print("错误: MSKU汇总表中没有'MSKU'列")
        print(f"可用的列: {msku_summary_df.columns.tolist()}")
        return []
    
    if 'MSKU' not in product_info_df.columns:
        print("错误: 产品资料表中没有'MSKU'列")
        print(f"可用的列: {product_info_df.columns.tolist()}")
        return []
    
    if 'SKC' not in product_info_df.columns:
        print("错误: 产品资料表中没有'SKC'列")
        print(f"可用的列: {product_info_df.columns.tolist()}")
        return []
    
    # 显示数据信息
    print(f"MSKU汇总表行数: {len(msku_summary_df)}")
    print(f"产品资料表行数: {len(product_info_df)}")
    
    # 确保MSKU列为字符串类型以确保匹配
    print("转换MSKU列为字符串类型...")
    msku_summary_df['MSKU'] = msku_summary_df['MSKU'].astype(str)
    product_info_df['MSKU'] = product_info_df['MSKU'].astype(str)
    
    # 去除可能存在的空格
    print("清理列名中可能存在的空格...")
    msku_summary_df.columns = [col.strip() for col in msku_summary_df.columns]
    product_info_df.columns = [col.strip() for col in product_info_df.columns]
    
    # 仅选择需要的列进行合并，并重命名SKC列以避免可能的命名冲突
    product_info_subset = product_info_df[['MSKU', 'SKC']].copy()
    product_info_subset = product_info_subset.rename(columns={'SKC': 'Product_SKC'})
    print(f"产品资料表子集列: {product_info_subset.columns.tolist()}")
    
    try:
        # 将MSKU维度的数据与产品资料表合并
        print("执行合并操作...")
        merged_df = pd.merge(msku_summary_df, product_info_subset, on='MSKU', how='left')
        
        print(f"合并后数据行数: {len(merged_df)}")
        print(f"合并后数据列前10个: {merged_df.columns.tolist()[:10]}")
        print(f"合并后数据所有列: {merged_df.columns.tolist()}")
        
        # 检查合并后Product_SKC列是否存在并且有数据
        if 'Product_SKC' not in merged_df.columns:
            print("错误: 合并后的数据中没有'Product_SKC'列")
            return []
        
        # 修改：处理可能的重复列问题
        # 先创建一个副本，避免视图问题
        merged_df = merged_df.copy()
        
        # 如果存在SKC列，暂时将其重命名为临时列名
        if 'SKC' in merged_df.columns:
            print("检测到已存在SKC列，将其重命名为临时列名")
            merged_df = merged_df.rename(columns={'SKC': 'SKC_original'})
        
        # 将Product_SKC重命名为SKC
        merged_df = merged_df.rename(columns={'Product_SKC': 'SKC'})
        print("成功将'Product_SKC'重命名为'SKC'")
        
        # 检查SKC列是否有空值
        try:
            null_count = merged_df['SKC'].isnull().sum()
            print(f"SKC列中空值数量: {null_count}")
        except Exception as e:
            print(f"检查SKC列空值时出错: {str(e)}")
            print("尝试使用替代方法...")
            try:
                # 更安全的空值检查方法
                null_count = sum(pd.isna(merged_df['SKC']))
                print(f"使用替代方法计算的SKC列空值数量: {null_count}")
            except Exception as e2:
                print(f"替代方法仍然出错: {str(e2)}")
                null_count = 0  # 假设没有空值
        
        if null_count > 0:
            print(f"警告: 合并后'SKC'列有{null_count}个空值")
            # 过滤掉SKC为空的行
            merged_df = merged_df.dropna(subset=['SKC'])
            print(f"过滤后数据行数: {len(merged_df)}")
            
            if len(merged_df) == 0:
                print("错误: 过滤后没有有效数据")
                return []
        
        # 按SKC分组，检查每个SKC的单个实际配送费是否一致
        print("按SKC分组...")
        skc_groups = merged_df.groupby('SKC')
        print(f"SKC分组数: {len(skc_groups)}")
        inconsistent_skcs = []
        
        for skc, group in skc_groups:
            if pd.isna(skc):
                print(f"警告: 跳过SKC为空的组")
                continue
                
            if len(group) > 1:  # 只检查有多个MSKU的SKC
                # 确保配送费不含NaN值
                valid_fees = group['单个实际配送费'].dropna()
                if len(valid_fees) <= 1:
                    continue
                    
                shipping_fees = valid_fees.unique()
                if len(shipping_fees) > 1:  # 如果配送费不一致
                    # 找出非最低值的MSKU
                    min_fee = min(shipping_fees)
                    abnormal_mskus = group[group['单个实际配送费'] > min_fee]['MSKU'].tolist()
                    
                    if abnormal_mskus:  # 确保有异常MSKU
                        inconsistent_skcs.append({
                            'SKC': skc,
                            '异常MSKU': abnormal_mskus,
                            '配送费': group[group['单个实际配送费'] > min_fee]['单个实际配送费'].tolist(),
                            '全部MSKU': group['MSKU'].tolist(),
                            '全部配送费': group['单个实际配送费'].tolist()
                        })
        
        print(f"发现{len(inconsistent_skcs)}个配送费不一致的SKC")
        return inconsistent_skcs
        
    except Exception as e:
        import traceback
        print(f"检查配送费一致性时发生错误: {str(e)}")
        traceback.print_exc()
        return []

def check_shipping_cost_consistency(msku_summary_df, product_info_df):
    """检查相同SKC的头程均价是否一致
    判断标准：
    1. 只检查有多个MSKU的SKC
    2. 当头程均价差异超过最低头程均价的50%时，认为是异常
    """
    print("\n开始检查相同SKC的头程均价一致性...")
    
    # 检查输入参数
    if msku_summary_df is None or product_info_df is None:
        print("错误: 输入数据为空")
        return []
    
    # 检查必要的列是否存在
    if '头程均价' not in msku_summary_df.columns:
        print("错误: MSKU汇总表中没有'头程均价'列")
        print(f"可用的列: {msku_summary_df.columns.tolist()}")
        return []
    
    if 'MSKU' not in msku_summary_df.columns:
        print("错误: MSKU汇总表中没有'MSKU'列")
        print(f"可用的列: {msku_summary_df.columns.tolist()}")
        return []
    
    if 'MSKU' not in product_info_df.columns:
        print("错误: 产品资料表中没有'MSKU'列")
        print(f"可用的列: {product_info_df.columns.tolist()}")
        return []
    
    if 'SKC' not in product_info_df.columns:
        print("错误: 产品资料表中没有'SKC'列")
        print(f"可用的列: {product_info_df.columns.tolist()}")
        return []
    
    # 显示数据信息
    print(f"MSKU汇总表行数: {len(msku_summary_df)}")
    print(f"产品资料表行数: {len(product_info_df)}")
    
    # 确保MSKU列为字符串类型以确保匹配
    print("转换MSKU列为字符串类型...")
    msku_summary_df['MSKU'] = msku_summary_df['MSKU'].astype(str)
    product_info_df['MSKU'] = product_info_df['MSKU'].astype(str)
    
    # 去除可能存在的空格
    print("清理列名中可能存在的空格...")
    msku_summary_df.columns = [col.strip() for col in msku_summary_df.columns]
    product_info_df.columns = [col.strip() for col in product_info_df.columns]
    
    # 过滤掉头程均价为NULL或0的记录
    valid_df = msku_summary_df.dropna(subset=['头程均价']).copy()
    valid_df = valid_df[valid_df['头程均价'] != 0]
    
    print(f"原始MSKU汇总记录数: {len(msku_summary_df)}")
    print(f"有效头程均价记录数: {len(valid_df)}")
    
    # 仅选择需要的列进行合并，并重命名SKC列以避免可能的命名冲突
    product_info_subset = product_info_df[['MSKU', 'SKC']].copy()
    product_info_subset = product_info_subset.rename(columns={'SKC': 'Product_SKC'})
    print(f"产品资料表子集列: {product_info_subset.columns.tolist()}")
    
    try:
        # 将MSKU维度的数据与产品资料表合并
        print("执行合并操作...")
        merged_df = pd.merge(valid_df, product_info_subset, on='MSKU', how='left')
        
        print(f"合并后数据行数: {len(merged_df)}")
        print(f"合并后数据列前10个: {merged_df.columns.tolist()[:10]}")
        print(f"合并后数据所有列: {merged_df.columns.tolist()}")
        
        # 检查合并后Product_SKC列是否存在并且有数据
        if 'Product_SKC' not in merged_df.columns:
            print("错误: 合并后的数据中没有'Product_SKC'列")
            return []
        
        # 修改：处理可能的重复列问题
        # 先创建一个副本，避免视图问题
        merged_df = merged_df.copy()
        
        # 如果存在SKC列，暂时将其重命名为临时列名
        if 'SKC' in merged_df.columns:
            print("检测到已存在SKC列，将其重命名为临时列名")
            merged_df = merged_df.rename(columns={'SKC': 'SKC_original'})
        
        # 将Product_SKC重命名为SKC
        merged_df = merged_df.rename(columns={'Product_SKC': 'SKC'})
        print("成功将'Product_SKC'重命名为'SKC'")
        
        # 检查SKC列是否有空值
        try:
            null_count = merged_df['SKC'].isnull().sum()
            print(f"SKC列中空值数量: {null_count}")
        except Exception as e:
            print(f"检查SKC列空值时出错: {str(e)}")
            print("尝试使用替代方法...")
            try:
                # 更安全的空值检查方法
                null_count = sum(pd.isna(merged_df['SKC']))
                print(f"使用替代方法计算的SKC列空值数量: {null_count}")
            except Exception as e2:
                print(f"替代方法仍然出错: {str(e2)}")
                null_count = 0  # 假设没有空值
        
        if null_count > 0:
            print(f"警告: 合并后'SKC'列有{null_count}个空值")
            # 过滤掉SKC为空的行
            merged_df = merged_df.dropna(subset=['SKC'])
            print(f"过滤后数据行数: {len(merged_df)}")
            
            if len(merged_df) == 0:
                print("错误: 过滤后没有有效数据")
                return []
        
        # 按SKC分组，检查每个SKC的头程均价是否一致
        print("按SKC分组...")
        skc_groups = merged_df.groupby('SKC')
        print(f"SKC分组数: {len(skc_groups)}")
        inconsistent_skcs = []
        
        for skc, group in skc_groups:
            if pd.isna(skc):
                print(f"警告: 跳过SKC为空的组")
                continue
                
            if len(group) > 1:  # 只检查有多个MSKU的SKC
                # 获取头程均价（取绝对值进行比较，因为负号只代表费用）
                shipping_costs = group['头程均价'].abs().unique()
                if len(shipping_costs) > 1:  # 如果头程均价不一致
                    min_cost = min(shipping_costs)
                    
                    # 找出差异超过阈值的MSKU
                    abnormal_mskus = []
                    abnormal_costs = []
                    for _, row in group.iterrows():
                        cost = abs(row['头程均价'])
                        if cost > min_cost:
                            # 计算差异百分比
                            diff_percent = (cost - min_cost) / min_cost * 100
                            # 当差异超过最低头程均价的50%时，认为是异常
                            if diff_percent > 50:
                                abnormal_mskus.append(row['MSKU'])
                                abnormal_costs.append(row['头程均价'])
                    
                    if abnormal_mskus:  # 只有当存在异常MSKU时才添加到结果中
                        inconsistent_skcs.append({
                            'SKC': skc,
                            '异常MSKU': abnormal_mskus,
                            '头程均价': abnormal_costs,
                            '最低头程均价': -min_cost if group['头程均价'].min() < 0 else min_cost  # 保持原始符号
                        })
        
        print(f"发现{len(inconsistent_skcs)}个头程均价异常的SKC")
        return inconsistent_skcs
        
    except Exception as e:
        import traceback
        print(f"检查头程均价一致性时发生错误: {str(e)}")
        traceback.print_exc()
        return []

def create_skc_min_shipping_fee_dict(msku_summary_df, product_info_df):
    """创建SKC最低单个实际配送费字典，用于理想校正
    
    返回一个字典，键为SKC，值为字典：
    {
        'min_fee': 最低单个实际配送费（绝对值），
        'msku_fees': {MSKU: 单个实际配送费}
    }
    """
    print("\n开始创建SKC最低单个实际配送费字典...")
    
    # 检查输入参数
    if msku_summary_df is None or product_info_df is None:
        print("错误: 输入数据为空")
        return {}
    
    # 检查必要的列是否存在
    if '单个实际配送费' not in msku_summary_df.columns:
        print("错误: MSKU汇总表中没有'单个实际配送费'列")
        print(f"可用的列: {msku_summary_df.columns.tolist()}")
        return {}
    
    if 'MSKU' not in msku_summary_df.columns:
        print("错误: MSKU汇总表中没有'MSKU'列")
        print(f"可用的列: {msku_summary_df.columns.tolist()}")
        return {}
    
    if 'MSKU' not in product_info_df.columns:
        print("错误: 产品资料表中没有'MSKU'列")
        print(f"可用的列: {product_info_df.columns.tolist()}")
        return {}
    
    if 'SKC' not in product_info_df.columns:
        print("错误: 产品资料表中没有'SKC'列")
        print(f"可用的列: {product_info_df.columns.tolist()}")
        return {}
    
    # 确保MSKU列为字符串类型以确保匹配
    print("转换MSKU列为字符串类型...")
    msku_summary_df['MSKU'] = msku_summary_df['MSKU'].astype(str)
    product_info_df['MSKU'] = product_info_df['MSKU'].astype(str)
    
    # 去除可能存在的空格
    print("清理列名中可能存在的空格...")
    msku_summary_df.columns = [col.strip() for col in msku_summary_df.columns]
    product_info_df.columns = [col.strip() for col in product_info_df.columns]
    
    # 仅选择需要的列进行合并，并重命名SKC列以避免可能的命名冲突
    product_info_subset = product_info_df[['MSKU', 'SKC']].copy()
    product_info_subset = product_info_subset.rename(columns={'SKC': 'Product_SKC'})
    print(f"产品资料表子集列: {product_info_subset.columns.tolist()}")
    
    try:
        # 将MSKU维度的数据与产品资料表合并
        print("执行合并操作...")
        merged_df = pd.merge(msku_summary_df, product_info_subset, on='MSKU', how='left')
        
        print(f"合并后数据行数: {len(merged_df)}")
        print(f"合并后数据列前10个: {merged_df.columns.tolist()[:10]}")
        
        # 检查合并后Product_SKC列是否存在并且有数据
        if 'Product_SKC' not in merged_df.columns:
            print("错误: 合并后的数据中没有'Product_SKC'列")
            return {}
        
        # 修改：处理可能的重复列问题
        # 先创建一个副本，避免视图问题
        merged_df = merged_df.copy()
        
        # 如果存在SKC列，暂时将其重命名为临时列名
        if 'SKC' in merged_df.columns:
            print("检测到已存在SKC列，将其重命名为临时列名")
            merged_df = merged_df.rename(columns={'SKC': 'SKC_original'})
        
        # 将Product_SKC重命名为SKC
        merged_df = merged_df.rename(columns={'Product_SKC': 'SKC'})
        print("成功将'Product_SKC'重命名为'SKC'")
        
        # 检查SKC列是否有空值
        try:
            null_count = merged_df['SKC'].isnull().sum()
            print(f"SKC列中空值数量: {null_count}")
        except Exception as e:
            print(f"检查SKC列空值时出错: {str(e)}")
            print("尝试使用替代方法...")
            try:
                # 更安全的空值检查方法
                null_count = sum(pd.isna(merged_df['SKC']))
                print(f"使用替代方法计算的SKC列空值数量: {null_count}")
            except Exception as e2:
                print(f"替代方法仍然出错: {str(e2)}")
                null_count = 0  # 假设没有空值
        
        if null_count > 0:
            print(f"警告: 合并后'SKC'列有{null_count}个空值")
            # 过滤掉SKC为空的行
            merged_df = merged_df.dropna(subset=['SKC'])
            print(f"过滤后数据行数: {len(merged_df)}")
            
            if len(merged_df) == 0:
                print("错误: 过滤后没有有效数据")
                return {}
        
        # 按SKC分组
        print("按SKC分组...")
        skc_groups = merged_df.groupby('SKC')
        print(f"SKC分组数: {len(skc_groups)}")
        skc_min_fees = {}
        
        for skc, group in skc_groups:
            if pd.isna(skc):
                print(f"警告: 跳过SKC为空的组")
                continue
                
            # 获取该SKC下所有MSKU的单个实际配送费
            msku_fees = {}
            for _, row in group.iterrows():
                if not pd.isnull(row['单个实际配送费']):
                    msku_fees[row['MSKU']] = row['单个实际配送费']
            
            if not msku_fees:
                print(f"警告: SKC {skc} 没有有效的配送费数据")
                continue
                
            # 计算绝对值最小的单个实际配送费
            min_fee_abs = min([abs(fee) for fee in msku_fees.values()])
            
            skc_min_fees[skc] = {
                'min_fee': min_fee_abs,  # 存储绝对值，但保持为负值
                'msku_fees': msku_fees
            }
        
        print(f"成功创建SKC最低单个实际配送费字典，共 {len(skc_min_fees)} 个SKC")
        return skc_min_fees
        
    except Exception as e:
        import traceback
        print(f"创建SKC最低单个实际配送费字典时发生错误: {str(e)}")
        traceback.print_exc()
        return {}

def create_skc_min_shipping_cost_dict(msku_summary_df, product_info_df):
    """创建SKC最低头程均价字典，用于理想校正
    
    返回一个字典，键为SKC，值为字典：
    {
        'min_cost': 最低头程均价（绝对值），
        'msku_costs': {MSKU: 头程均价}
    }
    """
    print("\n开始创建SKC最低头程均价字典...")
    
    # 检查输入参数
    if msku_summary_df is None or product_info_df is None:
        print("错误: 输入数据为空")
        return {}
    
    # 检查必要的列是否存在
    if '头程均价' not in msku_summary_df.columns:
        print("错误: MSKU汇总表中没有'头程均价'列")
        print(f"可用的列: {msku_summary_df.columns.tolist()}")
        return {}
    
    if 'MSKU' not in msku_summary_df.columns:
        print("错误: MSKU汇总表中没有'MSKU'列")
        print(f"可用的列: {msku_summary_df.columns.tolist()}")
        return {}
    
    if 'MSKU' not in product_info_df.columns:
        print("错误: 产品资料表中没有'MSKU'列")
        print(f"可用的列: {product_info_df.columns.tolist()}")
        return {}
    
    if 'SKC' not in product_info_df.columns:
        print("错误: 产品资料表中没有'SKC'列")
        print(f"可用的列: {product_info_df.columns.tolist()}")
        return {}
    
    # 确保MSKU列为字符串类型以确保匹配
    print("转换MSKU列为字符串类型...")
    msku_summary_df['MSKU'] = msku_summary_df['MSKU'].astype(str)
    product_info_df['MSKU'] = product_info_df['MSKU'].astype(str)
    
    # 去除可能存在的空格
    print("清理列名中可能存在的空格...")
    msku_summary_df.columns = [col.strip() for col in msku_summary_df.columns]
    product_info_df.columns = [col.strip() for col in product_info_df.columns]
    
    # 首先过滤掉头程均价为NULL或0的行
    valid_df = msku_summary_df.dropna(subset=['头程均价']).copy()
    valid_df = valid_df[valid_df['头程均价'] != 0]
    
    print(f"原始MSKU汇总记录数: {len(msku_summary_df)}")
    print(f"有效头程均价记录数: {len(valid_df)}")
    
    # 仅选择需要的列进行合并，并重命名SKC列以避免可能的命名冲突
    product_info_subset = product_info_df[['MSKU', 'SKC']].copy()
    product_info_subset = product_info_subset.rename(columns={'SKC': 'Product_SKC'})
    print(f"产品资料表子集列: {product_info_subset.columns.tolist()}")
    
    try:
        # 将MSKU维度的数据与产品资料表合并
        print("执行合并操作...")
        merged_df = pd.merge(valid_df, product_info_subset, on='MSKU', how='left')
        
        print(f"合并后数据行数: {len(merged_df)}")
        print(f"合并后数据列前10个: {merged_df.columns.tolist()[:10]}")
        
        # 检查合并后Product_SKC列是否存在并且有数据
        if 'Product_SKC' not in merged_df.columns:
            print("错误: 合并后的数据中没有'Product_SKC'列")
            return {}
        
        # 修改：处理可能的重复列问题
        # 先创建一个副本，避免视图问题
        merged_df = merged_df.copy()
        
        # 如果存在SKC列，暂时将其重命名为临时列名
        if 'SKC' in merged_df.columns:
            print("检测到已存在SKC列，将其重命名为临时列名")
            merged_df = merged_df.rename(columns={'SKC': 'SKC_original'})
        
        # 将Product_SKC重命名为SKC
        merged_df = merged_df.rename(columns={'Product_SKC': 'SKC'})
        print("成功将'Product_SKC'重命名为'SKC'")
        
        # 检查SKC列是否有空值
        try:
            null_count = merged_df['SKC'].isnull().sum()
            print(f"SKC列中空值数量: {null_count}")
        except Exception as e:
            print(f"检查SKC列空值时出错: {str(e)}")
            print("尝试使用替代方法...")
            try:
                # 更安全的空值检查方法
                null_count = sum(pd.isna(merged_df['SKC']))
                print(f"使用替代方法计算的SKC列空值数量: {null_count}")
            except Exception as e2:
                print(f"替代方法仍然出错: {str(e2)}")
                null_count = 0  # 假设没有空值
        
        if null_count > 0:
            print(f"警告: 合并后'SKC'列有{null_count}个空值")
            # 过滤掉SKC为空的行
            merged_df = merged_df.dropna(subset=['SKC'])
            print(f"过滤后数据行数: {len(merged_df)}")
            
            if len(merged_df) == 0:
                print("错误: 过滤后没有有效数据")
                return {}
        
        # 按SKC分组
        print("按SKC分组...")
        skc_groups = merged_df.groupby('SKC')
        print(f"SKC分组数: {len(skc_groups)}")
        skc_min_costs = {}
        
        for skc, group in skc_groups:
            if pd.isna(skc):
                print(f"警告: 跳过SKC为空的组")
                continue
                
            # 获取该SKC下所有MSKU的头程均价
            msku_costs = {}
            for _, row in group.iterrows():
                if not pd.isnull(row['头程均价']):  # 已经过滤过0值，只需要检查是否为NULL
                    msku_costs[row['MSKU']] = row['头程均价']
            
            if not msku_costs:
                print(f"警告: SKC {skc} 没有有效的头程均价数据")
                continue
                
            # 计算绝对值最小的头程均价
            min_cost_abs = min([abs(cost) for cost in msku_costs.values()])
            
            skc_min_costs[skc] = {
                'min_cost': min_cost_abs,  # 存储绝对值，但保持为负值
                'msku_costs': msku_costs
            }
        
        print(f"成功创建SKC最低头程均价字典，共 {len(skc_min_costs)} 个SKC")
        return skc_min_costs
        
    except Exception as e:
        import traceback
        print(f"创建SKC最低头程均价字典时发生错误: {str(e)}")
        traceback.print_exc()
        return {}

def ideal_correct_shipping_fee(msku_report, product_info_df, skc_min_shipping_fees):
    """使用SKC最低单个实际配送费进行理想校正
    
    1. 按SKC对MSKU进行分组
    2. 对于每个SKC，获取其最低单个实际配送费
    3. 对于每个MSKU，使用理想计算公式：最低单个实际配送费 * (FBA销量 + FBA补（换）货量)
    4. 将计算结果与原FBA发货费(FBA)进行比较，记录差值
    
    参数：
        msku_report: MSKU维度利润报表DataFrame
        product_info_df: 产品资料表DataFrame
        skc_min_shipping_fees: SKC最低单个实际配送费字典
    
    返回：
        理想校正后的MSKU报表，原始报表，校正记录
    """
    try:
        print("\n开始进行FBA配送费单价理想校正...")
        
        # 打印所有列名，帮助调试
        print("\nMSKU维度报表所有列名:")
        for i, col in enumerate(msku_report.columns):
            print(f"{i+1}. {col}")
        
        # 检查FBA销量列是否存在，尝试多种可能的列名
        fba_sales_column = None
        for possible_name in ['FBA销量', 'FBA销售数量', 'FBA销售量', 'FBA销量(数量)', '销量', '销售数量']:
            if possible_name in msku_report.columns:
                fba_sales_column = possible_name
                print(f"找到FBA销量列: {fba_sales_column}")
                break
        
        if not fba_sales_column:
            raise Exception("找不到FBA销量列，请检查报表中的列名。可能的列名有：'FBA销量', 'FBA销售数量', 'FBA销售量', 'FBA销量(数量)', '销量', '销售数量'")
        
        # 检查FBA补换货量列是否存在，尝试多种可能的列名
        fba_replacement_column = None
        possible_replacement_names = [
            'FBA补(换)货量', 'FBA补（换）货量', 'FBA补换货量', 'FBA补货量', 
            'FBA换货量', '补货数量', '换货数量', '补换货量', 'FBA补发货销售数量'
        ]
        
        # 打印详细的列名匹配信息
        print("\n尝试匹配FBA补换货量列:")
        for possible_name in possible_replacement_names:
            if possible_name in msku_report.columns:
                fba_replacement_column = possible_name
                print(f"✓ 成功匹配到: {fba_replacement_column}")
                break
            else:
                print(f"✗ 未匹配: {possible_name}")
        
        # 打印所有可能与FBA补换货相关的列，帮助调试
        print("\n所有可能与FBA补换货相关的列:")
        related_columns = []
        for col in msku_report.columns:
            if '补' in col or '换' in col or '货量' in col or 'FBA' in col and '销量' not in col:
                related_columns.append(col)
                print(f"- {col}")
        
        # 如果仍然找不到，尝试手动匹配
        if not fba_replacement_column and related_columns:
            print("\n没有找到精确匹配的FBA补换货量列，请从以下相关列中选择一个作为FBA补换货量列:")
            for i, col in enumerate(related_columns):
                print(f"{i+1}. {col}")
            
            try:
                choice = input("\n请输入选项编号(1-" + str(len(related_columns)) + ")，或者输入0表示使用零值: ")
                choice = int(choice)
                if choice > 0 and choice <= len(related_columns):
                    fba_replacement_column = related_columns[choice-1]
                    print(f"已选择 '{fba_replacement_column}' 作为FBA补换货量列")
                else:
                    print("将使用零值作为FBA补换货量")
                    msku_report['FBA补换货量'] = 0
                    fba_replacement_column = 'FBA补换货量'
            except (ValueError, IndexError):
                print("输入无效，将使用零值作为FBA补换货量")
                msku_report['FBA补换货量'] = 0
                fba_replacement_column = 'FBA补换货量'
        
        # 如果还是找不到FBA补换货量列，提供创建零值列的选项
        if not fba_replacement_column:
            print("\n未找到任何可能的FBA补换货量列")
            try:
                choice = input("是否创建一个值为0的FBA补换货量列继续？(y/n): ")
                if choice.lower() == 'y':
                    print("创建零值FBA补换货量列")
                    msku_report['FBA补换货量'] = 0
                    fba_replacement_column = 'FBA补换货量'
                else:
                    raise Exception("找不到FBA补换货量列，理想校正无法继续")
            except Exception:
                raise Exception("找不到FBA补换货量列，理想校正无法继续")
        
        # 检查FBA发货费列是否存在
        if 'FBA发货费(FBA)' not in msku_report.columns:
            raise Exception("找不到'FBA发货费(FBA)'列，请检查报表中的列名")
        
        # 检查MSKU列是否存在
        if 'MSKU' not in msku_report.columns:
            raise Exception("找不到'MSKU'列，请检查报表中的列名")
        
        # 将MSKU列转为字符串类型以确保匹配
        msku_report['MSKU'] = msku_report['MSKU'].astype(str)
        product_info_df['MSKU'] = product_info_df['MSKU'].astype(str)
        
        # 将MSKU维度报表与产品资料表合并，获取SKC信息
        merged_df = pd.merge(msku_report, product_info_df[['MSKU', 'SKC']], on='MSKU', how='left')
        
        # 检查是否有MSKU没有对应的SKC
        no_skc_mskus = merged_df[merged_df['SKC'].isna()]['MSKU'].tolist()
        if no_skc_mskus:
            print(f"警告: 以下MSKU在产品资料表中没有对应的SKC: {no_skc_mskus[:5]}...")
            print(f"共 {len(no_skc_mskus)} 个MSKU没有SKC信息，这些MSKU将不会进行理想校正")
        
        # 记录原始报表
        original_report = msku_report.copy()
        
        # 创建校正记录
        correction_records = []
        
        # 设置小数位数
        decimal_places = 2
        
        # 遍历每个MSKU，进行理想校正
        corrected_count = 0
        
        for idx, row in merged_df.iterrows():
            msku = row['MSKU']
            skc = row['SKC']
            
            # 跳过没有SKC信息的MSKU
            if pd.isna(skc) or skc not in skc_min_shipping_fees:
                continue
            
            # 获取FBA销量和FBA补（换）货量
            fba_sales = row[fba_sales_column] if not pd.isna(row[fba_sales_column]) else 0
            fba_replacement = row[fba_replacement_column] if not pd.isna(row[fba_replacement_column]) else 0
            
            # 确保销量和补换货量是数值类型
            try:
                fba_sales = float(fba_sales)
                fba_replacement = float(fba_replacement)
            except (ValueError, TypeError):
                print(f"警告: MSKU {msku} 的销量或补换货量不是有效的数值，将跳过")
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
                print(f"警告: MSKU {msku} 的FBA发货费不是有效的数值，将跳过")
                continue
            
            # 获取该SKC的最低单个实际配送费
            min_fee_abs = skc_min_shipping_fees[skc]['min_fee']
            
            # 计算理想的FBA发货费（使用负值，因为费用是负数）
            ideal_shipping_fee = -min_fee_abs * total_quantity
            ideal_shipping_fee = round(ideal_shipping_fee, decimal_places)
            
            # 计算校正量（理想 - 原始）
            correction_amount = ideal_shipping_fee - original_shipping_fee
            correction_amount = round(correction_amount, decimal_places)
            
            # 如果校正量绝对值小于0.01，则视为不需要校正
            if abs(correction_amount) < 0.01:
                continue
            
            # 更新FBA发货费
            msku_report.at[idx, 'FBA发货费(FBA)'] = ideal_shipping_fee
            
            # 记录校正信息
            correction_records.append({
                'MSKU': msku,
                'SKC': skc,
                'FBA销量': fba_sales,
                'FBA补换货量': fba_replacement,
                '总数量': total_quantity,
                '原始FBA发货费': original_shipping_fee,
                '理想FBA发货费': ideal_shipping_fee,
                '校正量': correction_amount,
                '单个最低配送费': -min_fee_abs
            })
            
            corrected_count += 1
        
        # 创建校正记录DataFrame
        correction_df = pd.DataFrame(correction_records)
        
        print(f"\nFBA配送费单价理想校正完成，共校正了 {corrected_count} 个MSKU的数据")
        
        # 重新计算毛利润（如果存在）
        if '毛利润' in msku_report.columns:
            print("\n正在重新计算毛利润...")
            # 这里可以添加重新计算毛利润的代码，或者复用原有的毛利润计算逻辑
            # 略，因为在后续的异常订单校正中会重新计算毛利润
        
        return msku_report, original_report, correction_df
    
    except Exception as e:
        import traceback
        print(f"FBA配送费单价理想校正失败：{str(e)}")
        print("\n详细错误信息:")
        traceback.print_exc()
        raise Exception(f"FBA配送费单价理想校正失败：{str(e)}")

def ideal_correct_shipping_cost(msku_report, product_info_df, skc_min_shipping_costs):
    """使用SKC最低头程均价进行理想校正
    
    1. 按SKC对MSKU进行分组
    2. 对于每个SKC，获取其最低头程均价
    3. 对于每个MSKU，使用理想计算公式：最低头程均价 * (FBA销量 + FBA补（换）货量)
    4. 将计算结果与原头程成本进行比较，记录差值
    
    参数：
        msku_report: MSKU维度利润报表DataFrame
        product_info_df: 产品资料表DataFrame
        skc_min_shipping_costs: SKC最低头程均价字典
    
    返回：
        理想校正后的MSKU报表，原始报表，校正记录
    """
    try:
        print("\n开始进行头程成本单价理想校正...")
        
        # 打印所有列名，帮助调试
        print("\nMSKU维度报表所有列名:")
        for i, col in enumerate(msku_report.columns):
            print(f"{i+1}. {col}")
        
        # 检查FBA销量列是否存在，尝试多种可能的列名
        fba_sales_column = None
        for possible_name in ['FBA销量', 'FBA销售数量', 'FBA销售量', 'FBA销量(数量)', '销量', '销售数量']:
            if possible_name in msku_report.columns:
                fba_sales_column = possible_name
                print(f"找到FBA销量列: {fba_sales_column}")
                break
        
        if not fba_sales_column:
            raise Exception("找不到FBA销量列，请检查报表中的列名。可能的列名有：'FBA销量', 'FBA销售数量', 'FBA销售量', 'FBA销量(数量)', '销量', '销售数量'")
        
        # 检查FBA补换货量列是否存在，尝试多种可能的列名
        fba_replacement_column = None
        possible_replacement_names = [
            'FBA补(换)货量', 'FBA补（换）货量', 'FBA补换货量', 'FBA补货量', 
            'FBA换货量', '补货数量', '换货数量', '补换货量', 'FBA补发货销售数量'
        ]
        
        # 打印详细的列名匹配信息
        print("\n尝试匹配FBA补换货量列:")
        for possible_name in possible_replacement_names:
            if possible_name in msku_report.columns:
                fba_replacement_column = possible_name
                print(f"✓ 成功匹配到: {fba_replacement_column}")
                break
            else:
                print(f"✗ 未匹配: {possible_name}")
        
        # 打印所有可能与FBA补换货相关的列，帮助调试
        print("\n所有可能与FBA补换货相关的列:")
        related_columns = []
        for col in msku_report.columns:
            if '补' in col or '换' in col or '货量' in col or 'FBA' in col and '销量' not in col:
                related_columns.append(col)
                print(f"- {col}")
        
        # 如果仍然找不到，尝试手动匹配
        if not fba_replacement_column and related_columns:
            print("\n没有找到精确匹配的FBA补换货量列，请从以下相关列中选择一个作为FBA补换货量列:")
            for i, col in enumerate(related_columns):
                print(f"{i+1}. {col}")
            
            try:
                choice = input("\n请输入选项编号(1-" + str(len(related_columns)) + ")，或者输入0表示使用零值: ")
                choice = int(choice)
                if choice > 0 and choice <= len(related_columns):
                    fba_replacement_column = related_columns[choice-1]
                    print(f"已选择 '{fba_replacement_column}' 作为FBA补换货量列")
                else:
                    print("将使用零值作为FBA补换货量")
                    msku_report['FBA补换货量'] = 0
                    fba_replacement_column = 'FBA补换货量'
            except (ValueError, IndexError):
                print("输入无效，将使用零值作为FBA补换货量")
                msku_report['FBA补换货量'] = 0
                fba_replacement_column = 'FBA补换货量'
        
        # 如果还是找不到FBA补换货量列，提供创建零值列的选项
        if not fba_replacement_column:
            print("\n未找到任何可能的FBA补换货量列")
            try:
                choice = input("是否创建一个值为0的FBA补换货量列继续？(y/n): ")
                if choice.lower() == 'y':
                    print("创建零值FBA补换货量列")
                    msku_report['FBA补换货量'] = 0
                    fba_replacement_column = 'FBA补换货量'
                else:
                    raise Exception("找不到FBA补换货量列，理想校正无法继续")
            except Exception:
                raise Exception("找不到FBA补换货量列，理想校正无法继续")
        
        # 检查头程成本列是否存在
        if '头程成本' not in msku_report.columns:
            raise Exception("找不到'头程成本'列，请检查报表中的列名")
        
        # 检查MSKU列是否存在
        if 'MSKU' not in msku_report.columns:
            raise Exception("找不到'MSKU'列，请检查报表中的列名")
        
        # 将MSKU列转为字符串类型以确保匹配
        msku_report['MSKU'] = msku_report['MSKU'].astype(str)
        product_info_df['MSKU'] = product_info_df['MSKU'].astype(str)
        
        # 将MSKU维度报表与产品资料表合并，获取SKC信息
        merged_df = pd.merge(msku_report, product_info_df[['MSKU', 'SKC']], on='MSKU', how='left')
        
        # 检查是否有MSKU没有对应的SKC
        no_skc_mskus = merged_df[merged_df['SKC'].isna()]['MSKU'].tolist()
        if no_skc_mskus:
            print(f"警告: 以下MSKU在产品资料表中没有对应的SKC: {no_skc_mskus[:5]}...")
            print(f"共 {len(no_skc_mskus)} 个MSKU没有SKC信息，这些MSKU将不会进行理想校正")
        
        # 记录原始报表
        original_report = msku_report.copy()
        
        # 创建校正记录
        correction_records = []
        
        # 设置小数位数
        decimal_places = 2
        
        # 遍历每个MSKU，进行理想校正
        corrected_count = 0
        
        for idx, row in merged_df.iterrows():
            msku = row['MSKU']
            skc = row['SKC']
            
            # 跳过没有SKC信息的MSKU
            if pd.isna(skc) or skc not in skc_min_shipping_costs:
                continue
            
            # 获取FBA销量和FBA补（换）货量
            fba_sales = row[fba_sales_column] if not pd.isna(row[fba_sales_column]) else 0
            fba_replacement = row[fba_replacement_column] if not pd.isna(row[fba_replacement_column]) else 0
            
            # 确保销量和补换货量是数值类型
            try:
                fba_sales = float(fba_sales)
                fba_replacement = float(fba_replacement)
            except (ValueError, TypeError):
                print(f"警告: MSKU {msku} 的销量或补换货量不是有效的数值，将跳过")
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
                print(f"警告: MSKU {msku} 的头程成本不是有效的数值，将跳过")
                continue
            
            # 获取该SKC的最低头程均价
            min_cost_abs = skc_min_shipping_costs[skc]['min_cost']
            
            # 计算理想的头程成本（使用负值，因为费用是负数）
            ideal_shipping_cost = -min_cost_abs * total_quantity
            ideal_shipping_cost = round(ideal_shipping_cost, decimal_places)
            
            # 计算校正量（理想 - 原始）
            correction_amount = ideal_shipping_cost - original_shipping_cost
            correction_amount = round(correction_amount, decimal_places)
            
            # 如果校正量绝对值小于0.01，则视为不需要校正
            if abs(correction_amount) < 0.01:
                continue
            
            # 更新头程成本
            msku_report.at[idx, '头程成本'] = ideal_shipping_cost
            
            # 记录校正信息
            correction_records.append({
                'MSKU': msku,
                'SKC': skc,
                'FBA销量': fba_sales,
                'FBA补换货量': fba_replacement,
                '总数量': total_quantity,
                '原始头程成本': original_shipping_cost,
                '理想头程成本': ideal_shipping_cost,
                '校正量': correction_amount,
                '单个最低头程均价': -min_cost_abs
            })
            
            corrected_count += 1
        
        # 创建校正记录DataFrame
        correction_df = pd.DataFrame(correction_records)
        
        print(f"\n头程成本单价理想校正完成，共校正了 {corrected_count} 个MSKU的数据")
        
        # 重新计算毛利润（如果存在）
        if '毛利润' in msku_report.columns:
            print("\n正在重新计算毛利润...")
            # 这里可以添加重新计算毛利润的代码，或者复用原有的毛利润计算逻辑
            # 略，因为在后续的异常订单校正中会重新计算毛利润
        
        return msku_report, original_report, correction_df
    
    except Exception as e:
        import traceback
        print(f"头程成本单价理想校正失败：{str(e)}")
        print("\n详细错误信息:")
        traceback.print_exc()
        raise Exception(f"头程成本单价理想校正失败：{str(e)}")

def create_skc_min_fees_table(msku_summary_df, product_info_df):
    """创建SKC维度的最低配送费和最低头程均价表，包含店铺列信息
    
    参数:
        msku_summary_df: MSKU维度汇总数据
        product_info_df: 产品资料表DataFrame
    
    返回:
        SKC维度的最低配送费和最低头程均价DataFrame
    """
    print("\n正在创建SKC维度的最低配送费和最低头程均价表...")
    
    # 确保MSKU列是字符串类型
    msku_summary_df['MSKU'] = msku_summary_df['MSKU'].astype(str)
    product_info_df['MSKU'] = product_info_df['MSKU'].astype(str)
    
    # 去除可能存在的空格
    print("清理列名中可能存在的空格...")
    msku_summary_df.columns = [col.strip() for col in msku_summary_df.columns]
    product_info_df.columns = [col.strip() for col in product_info_df.columns]
    
    # 仅选择需要的列进行合并，并重命名SKC列以避免可能的命名冲突
    product_info_subset = product_info_df[['MSKU', 'SKC']].copy()
    product_info_subset = product_info_subset.rename(columns={'SKC': 'Product_SKC'})
    
    try:
        # 将MSKU维度数据与产品资料表合并，获取SKC信息
        print("执行合并操作...")
        merged_df = pd.merge(msku_summary_df, product_info_subset, on='MSKU', how='left')
        print(f"合并后数据行数: {len(merged_df)}")
        print(f"合并后数据列前10个: {merged_df.columns.tolist()[:10]}")
        
        # 检查合并后Product_SKC列是否存在并且有数据
        if 'Product_SKC' not in merged_df.columns:
            print("错误: 合并后的数据中没有'Product_SKC'列")
            return pd.DataFrame(), pd.DataFrame()
        
        # 修改：处理可能的重复列问题
        # 先创建一个副本，避免视图问题
        merged_df = merged_df.copy()
        
        # 如果存在SKC列，暂时将其重命名为临时列名
        if 'SKC' in merged_df.columns:
            print("检测到已存在SKC列，将其重命名为临时列名")
            merged_df = merged_df.rename(columns={'SKC': 'SKC_original'})
        
        # 将Product_SKC重命名为SKC
        merged_df = merged_df.rename(columns={'Product_SKC': 'SKC'})
        print("成功将'Product_SKC'重命名为'SKC'")
        
        # 检查SKC列是否有空值
        try:
            null_count = merged_df['SKC'].isnull().sum()
            print(f"SKC列中空值数量: {null_count}")
        except Exception as e:
            print(f"检查SKC列空值时出错: {str(e)}")
            print("尝试使用替代方法...")
            try:
                # 更安全的空值检查方法
                null_count = sum(pd.isna(merged_df['SKC']))
                print(f"使用替代方法计算的SKC列空值数量: {null_count}")
            except Exception as e2:
                print(f"替代方法仍然出错: {str(e2)}")
                null_count = 0  # 假设没有空值
        
        if null_count > 0:
            print(f"警告: 合并后'SKC'列有{null_count}个空值")
            # 过滤掉SKC为空的行
            merged_df = merged_df.dropna(subset=['SKC'])
            print(f"过滤后数据行数: {len(merged_df)}")
            
            if len(merged_df) == 0:
                print("错误: 过滤后没有有效数据")
                return pd.DataFrame(), pd.DataFrame()
    
        # 检查"店铺"列是否存在，如果不存在，尝试找到替代列
        shop_column = None
        for possible_name in ['店铺', '销售店铺', 'store', 'Shop', 'seller_id', '卖家ID', '卖家账号']:
            if possible_name in merged_df.columns:
                shop_column = possible_name
                print(f"找到店铺列: {shop_column}")
                break
        
        if not shop_column:
            print("警告: 未找到店铺列，将使用'未知店铺'作为默认值")
            merged_df['店铺'] = '未知店铺'
            shop_column = '店铺'
            
        # 检查"国家"列是否存在
        country_column = None
        for possible_name in ['国家', 'country', 'Country', '国家/地区', '市场']:
            if possible_name in merged_df.columns:
                country_column = possible_name
                print(f"找到国家列: {country_column}")
                break
                
        if not country_column:
            print("警告: 未找到国家列，将使用'未知国家'作为默认值")
            merged_df['国家'] = '未知国家'
            country_column = '国家'
        
        # 1. 创建"SKC维度最低费用-原始订单"表
        print(f"按SKC、{country_column}和{shop_column}分组...")
        # 准备结果列表
        original_result_rows = []
        
        for (skc, country, shop), group in merged_df.groupby(['SKC', country_column, shop_column]):
            if pd.isna(skc):
                continue  # 跳过没有SKC的记录
            
            # 如果单个实际配送费和头程均价列已存在，直接使用
            if '单个实际配送费' in group.columns and '头程均价' in group.columns:
                # 找出绝对值最小的配送费和头程均价（负数中最接近0的）
                try:
                    # 处理单个实际配送费
                    valid_fees = group['单个实际配送费'].dropna()
                    if len(valid_fees) == 0:
                        continue
                    min_shipping_fee_idx = valid_fees.abs().idxmin()
                    min_shipping_fee = group.loc[min_shipping_fee_idx, '单个实际配送费']
                    
                    # 过滤掉空值和0值后找出绝对值最小的头程均价
                    valid_costs = group['头程均价'].dropna()
                    
                    # 直接过滤掉为0的值，这些是由于头程费用为0导致的
                    valid_costs = valid_costs[valid_costs != 0]
                    
                    # 如果没有有效的头程均价值，则显示"未匹配"
                    min_shipping_cost = "未匹配" if valid_costs.empty else None
                    if len(valid_costs) > 0:
                        min_shipping_cost_idx = valid_costs.abs().idxmin()
                        min_shipping_cost = group.loc[min_shipping_cost_idx, '头程均价']
                    
                    # 添加到结果
                    original_result_rows.append({
                        'SKC': skc,
                        '国家': country,
                        '店铺': shop,
                        '最低配送费': min_shipping_fee,
                        '最低头程均价': min_shipping_cost
                    })
                except Exception as e:
                    print(f"处理SKC {skc}的配送费和头程均价时出错: {str(e)}")
                    continue
        
        # 创建原始订单的SKC维度最低费用DataFrame
        skc_min_fees_original_df = pd.DataFrame(original_result_rows)
        
        # 2. 创建"SKC维度最低费用"表 - 同一SKC在亚马逊上可获取的最低配送费
        print("创建SKC维度最低费用表（亚马逊最低配送费）...")
        # 准备结果列表
        amazon_min_fees_rows = []
        
        # 按SKC和国家分组，找出每个SKC在每个国家的最低配送费（不考虑店铺）
        for (skc, country), group in merged_df.groupby(['SKC', country_column]):
            if pd.isna(skc) or pd.isna(country):
                continue  # 跳过没有SKC或国家的记录
            
            # 如果单个实际配送费列已存在
            if '单个实际配送费' in group.columns:
                # 找出绝对值最小的配送费（负数中最接近0的）
                try:
                    valid_fees = group['单个实际配送费'].dropna()
                    if len(valid_fees) == 0:
                        continue
                        
                    # 找出绝对值最小的配送费
                    min_abs_fee_idx = valid_fees.abs().idxmin()
                    min_shipping_fee = group.loc[min_abs_fee_idx, '单个实际配送费']
                    
                    # 找出绝对值最小的头程均价（如果存在）
                    min_shipping_cost = None
                    if '头程均价' in group.columns:
                        # 过滤掉空值和0值
                        valid_costs = group['头程均价'].dropna()
                        
                        # 直接排除为0的值，这些是由于头程费用为0导致的
                        valid_costs = valid_costs[valid_costs != 0]
                        
                        # 如果没有有效值，则显示"未匹配"
                        min_shipping_cost = "未匹配" if valid_costs.empty else None
                        if len(valid_costs) > 0:
                            min_abs_cost_idx = valid_costs.abs().idxmin()
                            min_shipping_cost = group.loc[min_abs_cost_idx, '头程均价']
                    
                    # 找出该SKC在该国家下所有店铺
                    shops = group[shop_column].unique()
                    shops_str = ', '.join(shops) if len(shops) <= 3 else f"{', '.join(shops[:3])}... 等{len(shops)}个店铺"
                    
                    # 添加到结果
                    amazon_min_fees_rows.append({
                        'SKC': skc,
                        '国家': country,
                        '店铺': shops_str,  # 显示所有店铺或前几个
                        '亚马逊最低配送费': min_shipping_fee,
                        '最低头程均价': min_shipping_cost
                    })
                except Exception as e:
                    print(f"处理SKC {skc}的亚马逊最低配送费时出错: {str(e)}")
                    continue
        
        # 创建亚马逊最低配送费的DataFrame
        skc_amazon_min_fees_df = pd.DataFrame(amazon_min_fees_rows)
        
        # 按SKC和国家排序
        if not skc_min_fees_original_df.empty:
            skc_min_fees_original_df = skc_min_fees_original_df.sort_values(['SKC', '国家', '店铺'])
            
            # 格式化数值列为2位小数
            for col in ['最低配送费', '最低头程均价']:
                if col in skc_min_fees_original_df.columns:
                    # 只对数值类型的单元格进行格式化
                    mask = skc_min_fees_original_df[col].apply(lambda x: isinstance(x, (int, float)))
                    if mask.any():
                        skc_min_fees_original_df.loc[mask, col] = skc_min_fees_original_df.loc[mask, col].round(2)
            
            print(f"SKC维度最低费用-原始订单表创建完成，共{len(skc_min_fees_original_df)}条记录")
            print(f"表包含以下列: {skc_min_fees_original_df.columns.tolist()}")
        else:
            print("警告: 未能创建SKC维度最低费用-原始订单表，可能是因为没有有效的SKC数据")
            
        if not skc_amazon_min_fees_df.empty:
            skc_amazon_min_fees_df = skc_amazon_min_fees_df.sort_values(['SKC', '国家'])
            
            # 格式化数值列为2位小数
            skc_amazon_min_fees_df['亚马逊最低配送费'] = skc_amazon_min_fees_df['亚马逊最低配送费'].round(2)
            # 格式化最低头程均价（如果存在）
            if '最低头程均价' in skc_amazon_min_fees_df.columns:
                # 只对数值类型的单元格进行格式化
                mask = skc_amazon_min_fees_df['最低头程均价'].apply(lambda x: isinstance(x, (int, float)))
                if mask.any():
                    skc_amazon_min_fees_df.loc[mask, '最低头程均价'] = skc_amazon_min_fees_df.loc[mask, '最低头程均价'].round(2)
            
            print(f"SKC维度最低费用表创建完成，共{len(skc_amazon_min_fees_df)}条记录")
            print(f"表包含以下列: {skc_amazon_min_fees_df.columns.tolist()}")
        else:
            print("警告: 未能创建SKC维度最低费用表，可能是因为没有有效的SKC数据")
            
        return skc_min_fees_original_df, skc_amazon_min_fees_df
    
    except Exception as e:
        import traceback
        print(f"创建SKC维度最低费用表时发生错误: {str(e)}")
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame()

def check_zero_financial_fields(df, abnormal_df=None):
    """检测订单维度中的关键财务字段是否为0
    
    参数:
        df: 订单数据DataFrame
        abnormal_df: 异常订单数据DataFrame（可选）
    
    返回:
        zero_fields: 所有订单中值都为0的财务字段列表
        partial_zero_fields: 部分订单中值为0的财务字段及其比例
        abnormal_zero_fields: 异常订单中值为0的财务字段统计（如果提供了abnormal_df）
    """
    # 只统计关键财务字段
    financial_fields = [
        'FBA费', '采购成本', '头程费用', '平台费', '销售额'
    ]
    
    # 确保所有字段都存在于DataFrame中
    available_fields = []
    for field in financial_fields:
        if field in df.columns:
            available_fields.append(field)
        else:
            print(f"警告: 关键财务字段 '{field}' 不存在于订单数据中")
    
    # 检查每个字段是否全为0 - 所有订单
    zero_fields = []
    partial_zero_fields = []
    
    for field in available_fields:
        # 计算该字段为0的订单比例
        zero_count = (df[field] == 0).sum()
        total_count = len(df)
        zero_ratio = zero_count / total_count
        
        if zero_count == total_count:
            zero_fields.append(field)
        elif zero_count > 0:
            partial_zero_fields.append({
                '字段': field,
                '为0的订单数': zero_count,
                '总订单数': total_count,
                '为0比例': f"{zero_ratio:.2%}"
            })
    
    # 如果提供了异常订单数据，单独统计异常订单的零值情况
    abnormal_zero_fields = None
    if abnormal_df is not None and not abnormal_df.empty:
        abnormal_zero_fields = []
        for field in available_fields:
            # 计算异常订单中该字段为0的比例
            zero_count = (abnormal_df[field] == 0).sum()
            total_count = len(abnormal_df)
            zero_ratio = zero_count / total_count if total_count > 0 else 0
            
            abnormal_zero_fields.append({
                '字段': field,
                '为0的异常订单数': zero_count,
                '异常订单总数': total_count,
                '为0比例': f"{zero_ratio:.2%}"
            })
    
    return zero_fields, partial_zero_fields, abnormal_zero_fields

def detect_unclassified_abnormal_orders(df, abnormal_df):
    """识别不属于已知异常类型但关键财务字段为0的可能异常订单
    
    参数:
        df: 所有订单数据DataFrame
        abnormal_df: 已识别的异常订单数据DataFrame
    
    返回:
        unclassified_abnormal_df: 可能是未识别异常类型的订单DataFrame
    """
    print("\n正在识别未归类的异常订单...")
    
    # 获取已知异常订单的订单号
    if '订单号' in abnormal_df.columns:
        abnormal_order_ids = set(abnormal_df['订单号'].astype(str))
    else:
        print("警告: 异常订单数据中未找到'订单号'列，将使用索引作为标识")
        abnormal_order_ids = set()
    
    # 识别不属于已知异常类型但关键财务字段为0的订单
    unclassified_abnormal_orders = []
    
    # 检查每个订单
    for _, row in df.iterrows():
        # 跳过已识别的异常订单
        if '订单号' in df.columns and str(row['订单号']) in abnormal_order_ids:
            continue
        
        # 检查关键财务字段
        fba_fee_zero = row['FBA费'] == 0 if 'FBA费' in row else False
        platform_fee_zero = row['平台费'] == 0 if '平台费' in row else False
        sales_zero = row['销售额'] == 0 if '销售额' in row else False
        
        # 如果任意关键财务字段为0，加入未归类异常订单
        if fba_fee_zero or platform_fee_zero or sales_zero:
            row_data = row.to_dict()
            # 添加异常标记字段
            row_data['FBA费为0'] = '是' if fba_fee_zero else '否'
            row_data['平台费为0'] = '是' if platform_fee_zero else '否'
            row_data['销售额为0'] = '是' if sales_zero else '否'
            row_data['建议确认'] = '异常订单'
            unclassified_abnormal_orders.append(row_data)
    
    # 创建DataFrame
    if unclassified_abnormal_orders:
        unclassified_df = pd.DataFrame(unclassified_abnormal_orders)
        print(f"发现 {len(unclassified_df)} 个未归类的可能异常订单")
        return unclassified_df
    else:
        print("未发现未归类的异常订单")
        return pd.DataFrame()

def analyze_skc_min_shipping_fee_by_quality(msku_summary_df, product_info_df, output_writer=None):
    """
    分析SKC维度最低配送费，按SKC+国家+品质分组，统计最低配送费，
    - 若同品质下最低配送费不同，提示检查listing尺寸重量
    - 若不同品质下最低配送费不同，输出对应品质信息
    - 结果写入"配送费分析"表新工作表
    """
    print("\n开始SKC维度最低配送费品质分析...")
    
    # 检查参数是否为空
    if msku_summary_df is None or product_info_df is None:
        print("错误：输入数据为空")
        return pd.DataFrame(), pd.DataFrame()
    
    # 检查数据列
    if '单个实际配送费' not in msku_summary_df.columns:
        print("错误：MSKU汇总表缺少'单个实际配送费'列")
        return pd.DataFrame(), pd.DataFrame()
        
    # 检查产品资料表中必要的列
    if '品质' not in product_info_df.columns:
        print("❌ 错误：产品资料表缺少'品质'列，程序无法继续执行")
        print("请确保产品资料表包含'品质'列后重新运行程序")
        raise Exception("产品资料表缺少必要字段'品质'列，程序停止执行")
    
    if 'SKC' not in product_info_df.columns:
        print("错误：产品资料表缺少'SKC'列")
        return pd.DataFrame(), pd.DataFrame()
        
    if '国家' not in msku_summary_df.columns:
        print("错误：MSKU汇总表缺少'国家'列，无法进行国家维度分析")
        return pd.DataFrame(), pd.DataFrame()
    
    # 检查店铺列是否存在
    shop_column = None
    for possible_name in ['店铺', '销售店铺', 'store', 'Shop', 'seller_id', '卖家ID', '卖家账号']:
        if possible_name in msku_summary_df.columns:
            shop_column = possible_name
            print(f"找到店铺列: {shop_column}")
            break
    
    if not shop_column:
        print("警告: 未找到店铺列，将使用'未知店铺'作为默认值")
        msku_summary_df['店铺'] = '未知店铺'
        shop_column = '店铺'
    
    # 打印数据概览
    print(f"MSKU汇总表行数: {len(msku_summary_df)}")
    print(f"产品资料表行数: {len(product_info_df)}")
    print(f"产品资料表'品质'列唯一值: {product_info_df['品质'].unique()}")
    
    # 确保MSKU列为字符串类型以确保匹配
    print("转换MSKU列为字符串类型...")
    msku_summary_df['MSKU'] = msku_summary_df['MSKU'].astype(str)
    product_info_df['MSKU'] = product_info_df['MSKU'].astype(str)
    
    # 去除可能存在的空格
    print("清理列名中可能存在的空格...")
    msku_summary_df.columns = [col.strip() for col in msku_summary_df.columns]
    product_info_df.columns = [col.strip() for col in product_info_df.columns]
    
    # 仅选择需要的列进行合并，并重命名SKC列以避免可能的命名冲突
    product_info_subset = product_info_df[['MSKU', 'SKC', '品质']].copy()
    product_info_subset = product_info_subset.rename(columns={'SKC': 'Product_SKC'})
    
    try:
        # 合并产品资料表，获取品质、国家
        print("执行合并操作...")
        merged_df = pd.merge(msku_summary_df, product_info_subset, on='MSKU', how='left')
        print(f"合并后数据行数: {len(merged_df)}")
        print(f"合并后数据列前10个: {merged_df.columns.tolist()[:10]}")
        
        # 检查合并后Product_SKC列是否存在并且有数据
        if 'Product_SKC' not in merged_df.columns:
            print("错误: 合并后的数据中没有'Product_SKC'列")
            return pd.DataFrame(), pd.DataFrame()
            
        # 修改：处理可能的重复列问题
        # 先创建一个副本，避免视图问题
        merged_df = merged_df.copy()
        
        # 如果存在SKC列，暂时将其重命名为临时列名
        if 'SKC' in merged_df.columns:
            print("检测到已存在SKC列，将其重命名为临时列名")
            merged_df = merged_df.rename(columns={'SKC': 'SKC_original'})
        
        # 将Product_SKC重命名为SKC
        merged_df = merged_df.rename(columns={'Product_SKC': 'SKC'})
        print("成功将'Product_SKC'重命名为'SKC'")
        
        # 检查合并后是否有缺失值
        try:
            # 检查品质列缺失值
            missing_quality = merged_df['品质'].isnull().sum()
            print(f"品质列中空值数量: {missing_quality}")
            
            # 检查SKC列缺失值
            missing_skc = merged_df['SKC'].isnull().sum()
            print(f"SKC列中空值数量: {missing_skc}")
        except Exception as e:
            print(f"检查列空值时出错: {str(e)}")
            print("尝试使用替代方法...")
            try:
                # 更安全的空值检查方法
                missing_quality = sum(pd.isna(merged_df['品质']))
                missing_skc = sum(pd.isna(merged_df['SKC']))
                print(f"使用替代方法计算的品质列空值数量: {missing_quality}")
                print(f"使用替代方法计算的SKC列空值数量: {missing_skc}")
            except Exception as e2:
                print(f"替代方法仍然出错: {str(e2)}")
                missing_quality = 0
                missing_skc = 0
        
        if missing_quality > 0:
            print(f"警告：合并后有{missing_quality}行缺少品质信息")
        
        if missing_skc > 0:
            print(f"警告：合并后有{missing_skc}行缺少SKC信息")
        
        # 过滤掉没有SKC或品质信息的行
        merged_df = merged_df.dropna(subset=['SKC', '品质'])
        print(f"过滤后数据行数: {len(merged_df)}")
        
        # 如果过滤后没有数据，就结束分析
        if len(merged_df) == 0:
            print("过滤后没有有效数据，无法进行分析")
            return pd.DataFrame(), pd.DataFrame()

        # 首先创建SKC维度最低费用表
        print("创建SKC维度最低费用表...")
        skc_min_fees_original_df, skc_amazon_min_fees_df = create_skc_min_fees_table(merged_df, product_info_df)
        
        if skc_min_fees_original_df.empty:
            print("SKC维度最低费用表为空，无法进行分析")
            return pd.DataFrame(), pd.DataFrame()
            
        print(f"SKC维度最低费用-原始订单表包含 {len(skc_min_fees_original_df)} 行数据")
        
        # 检查SKC维度最低费用表中是否包含必要的列
        required_cols = ['SKC', '店铺', '国家', '最低配送费']
        missing_cols = [col for col in required_cols if col not in skc_min_fees_original_df.columns]
        if missing_cols:
            print(f"错误: SKC维度最低费用表缺少必要的列: {missing_cols}")
            print(f"可用的列: {skc_min_fees_original_df.columns.tolist()}")
            return pd.DataFrame(), pd.DataFrame()
            
        # 基于SKC维度最低费用表检测同国家不同店铺间配送费异常
        print("检查同SKC、同国家下不同店铺的配送费差异...")
        same_quality_rows = []
        diff_quality_rows = []
        
        # 按SKC和国家分组
        skc_country_groups = skc_min_fees_original_df.groupby(['SKC', '国家'])
        
        for (skc, country), group in skc_country_groups:
            # 如果该SKC+国家组合下有多个店铺
            if len(group) > 1:
                # 找出绝对值最小的配送费（因为配送费是负数，绝对值最小的实际是数值最大的）
                # 使用绝对值进行比较
                abs_fees = group['最低配送费'].abs()
                min_abs_fee_idx = abs_fees.idxmin()
                min_abs_fee = group.loc[min_abs_fee_idx, '最低配送费']
                
                # 检查是否有不同的配送费
                if len(group['最低配送费'].unique()) > 1:
                    # 为每个配送费绝对值大于最小值的店铺创建一行记录
                    for idx, row in group.iterrows():
                        current_fee = row['最低配送费']
                        # 只有当当前店铺的配送费绝对值大于最小绝对值时，才标记为异常
                        # 因为配送费是负数，所以绝对值大的实际数值更小
                        if abs(current_fee) > abs(min_abs_fee):
                            same_quality_rows.append({
                                'SKC': skc,
                                '国家': country,
                                '店铺': row['店铺'],
                                '最低配送费': current_fee,
                                '同品质其他店铺SKC最低配送费': min_abs_fee
                            })
        
        # 处理不同品质下的配送费差异
        # 按SKC+国家分组
        skc_country_groups = merged_df.groupby(['SKC', '国家'])
        print(f"共有{len(skc_country_groups)}个SKC+国家组合")
        
        for (skc, country), group1 in skc_country_groups:
            # 跳过SKC或国家为空的组
            if pd.isna(skc) or pd.isna(country):
                continue
                
            # 按品质分组
            quality_fee_map = {}
            quality_groups = group1.groupby('品质')
            
            for quality, group2 in quality_groups:
                # 跳过品质为空的组
                if pd.isna(quality):
                    continue
                    
                # 确保单个实际配送费列中不含NaN值
                valid_fees = group2['单个实际配送费'].dropna()
                if len(valid_fees) == 0:
                    continue
                    
                # 获取最低配送费（绝对值最小的）
                min_abs_fee_idx = valid_fees.abs().idxmin()
                min_fee = valid_fees.loc[min_abs_fee_idx]
                quality_fee_map[quality] = min_fee
            
            # 检查不同品质下最低配送费是否不同
            if len(quality_fee_map) > 1 and len(set(quality_fee_map.values())) > 1:
                # 为每个品质创建一行
                for quality, fee in quality_fee_map.items():
                    diff_quality_rows.append({
                        'SKC': skc,
                        '国家': country,
                        '品质': quality,
                        '配送费': fee
                    })
        
        # 创建同品质配送费异常DataFrame
        if same_quality_rows:
            same_quality_df = pd.DataFrame(same_quality_rows)
            same_quality_df = same_quality_df.sort_values(['SKC', '国家', '店铺'])
        else:
            same_quality_df = pd.DataFrame(columns=['SKC', '国家', '店铺', '最低配送费', '同品质其他店铺SKC最低配送费'])
            print("未发现同品质下不同店铺配送费不一致的情况")
        
        # 创建不同品质配送费DataFrame
        if diff_quality_rows:
            diff_quality_df = pd.DataFrame(diff_quality_rows)
            diff_quality_pivot = diff_quality_df.pivot_table(
                index=['SKC', '国家', '品质'],
                values='配送费',
                aggfunc='first'
            ).reset_index()
        else:
            diff_quality_pivot = pd.DataFrame(columns=['SKC', '国家', '品质', '配送费'])
            print("未发现不同品质下配送费不同的SKC")
        
        print(f"发现{len(set(same_quality_df['SKC']))}个同品质下不同店铺配送费异常的SKC")
        print(f"发现{len(set(diff_quality_pivot['SKC']))}个不同品质下配送费不同的SKC")
        
        # 写入Excel新工作表
        if output_writer is not None:
            try:
                if not same_quality_df.empty:
                    # 创建适合层级显示的Excel
                    same_quality_sheet_name = '同品质配送费异常'
                    same_quality_df.to_excel(output_writer, sheet_name=same_quality_sheet_name, index=False)
                    print(f"成功写入'{same_quality_sheet_name}'工作表")
                else:
                    print("未发现同品质配送费异常，不创建相应工作表")
                    
                if not diff_quality_pivot.empty:
                    # 创建适合层级显示的Excel
                    diff_quality_sheet_name = '不同品质配送费'
                    
                    # 为Excel写入准备数据
                    if 'openpyxl' in str(type(output_writer)):
                        # 使用pivot_table生成的数据很难直接写入层级结构
                        # 因此我们创建一个新的DataFrame，格式更适合层级显示
                        skc_groups = diff_quality_pivot.groupby('SKC')
                        formatted_rows = []
                        
                        for skc, skc_group in skc_groups:
                            # 添加SKC行
                            formatted_rows.append({
                                'SKC': skc,
                                '国家': '',
                                '品质': '',
                                '配送费': ''
                            })
                            
                            # 添加国家+品质行
                            for _, row in skc_group.iterrows():
                                formatted_rows.append({
                                    'SKC': '',
                                    '国家': row['国家'],
                                    '品质': row['品质'],
                                    '配送费': row['配送费']
                                })
                        
                        formatted_df = pd.DataFrame(formatted_rows)
                        formatted_df.to_excel(output_writer, sheet_name=diff_quality_sheet_name, index=False)
                    else:
                        # 使用默认方式写入
                        diff_quality_pivot.to_excel(output_writer, sheet_name=diff_quality_sheet_name, index=False)
                        
                    print(f"成功写入'{diff_quality_sheet_name}'工作表")
                else:
                    print("未发现不同品质下配送费不同的SKC，不创建相应工作表")
                
            except Exception as e:
                print(f"写入Excel过程中出错: {str(e)}")
                import traceback
                traceback.print_exc()
        
        return same_quality_df, diff_quality_pivot
        
    except Exception as e:
        import traceback
        print(f"SKC维度品质分析失败：{str(e)}")
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame()

def check_msku_profit_date_range(msku_report_df):
    """
    检查MSKU维度利润报表的日期范围是否符合要求
    MSKU维度利润报表使用"日期"列，格式为"2024-10-15~2025-01-14"的范围格式
    """
    print("\n正在检查MSKU维度利润报表的日期范围...")
    
    # 检查日期列是否存在
    if '日期' not in msku_report_df.columns:
        raise Exception("MSKU维度利润报表缺少必要的'日期'列，请检查文件格式")
    
    # 检查国家列是否存在
    if '国家' not in msku_report_df.columns:
        print("警告：MSKU维度利润报表缺少'国家'列，将跳过国家相关的日期检查")
        return
    
    # 检查国家数据一致性
    unique_countries = msku_report_df['国家'].dropna().unique()
    if len(unique_countries) > 1:
        raise Exception(f"检测到多个不同国家！MSKU维度利润报表数据必须来自同一个国家。发现的国家：{', '.join(unique_countries)}")
    elif len(unique_countries) == 0:
        print("警告：国家列没有有效数据，将跳过日期范围检查")
        return
    else:
        country_name = unique_countries[0]
        print(f"✅ MSKU报表国家检查通过：所有数据都来自 {country_name}")
    
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
            print(f"日期范围解析失败：{date_range_str}, 错误：{str(e)}")
            return None, None
        
        return None, None
    
    # 解析所有日期范围
    date_ranges = []
    invalid_dates = []
    
    for idx, date_str in enumerate(msku_report_df['日期']):
        start_date, end_date = parse_date_range(date_str)
        if start_date is not None and end_date is not None:
            date_ranges.append((start_date, end_date))
        else:
            invalid_dates.append((idx, date_str))
    
    if invalid_dates:
        error_msg = f"日期格式无法解析，发现{len(invalid_dates)}个无效的日期格式。\n"
        error_msg += "MSKU维度利润报表的日期应为范围格式如'2024-10-15~2025-01-14'\n"
        error_msg += f"无效日期示例：{invalid_dates[:3]}"
        raise Exception(error_msg)
    
    print(f"成功解析{len(date_ranges)}个日期范围")
    
    # 获取所有日期的最小和最大值
    all_dates = []
    for start_date, end_date in date_ranges:
        all_dates.extend([start_date, end_date])
    
    earliest_date = min(all_dates)
    latest_date = max(all_dates)
    
    print(f"数据日期范围：{earliest_date.strftime('%Y-%m-%d')} 至 {latest_date.strftime('%Y-%m-%d')}")
    
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
        
        print(f"日期范围分析：旺季范围={peak_season_ranges}, 淡季范围={off_season_ranges}, 混合范围={mixed_ranges}")
        
        # 检查是否存在混合配送周期
        if mixed_ranges > 0 or (peak_season_ranges > 0 and off_season_ranges > 0):
            # 找出最早年份，用于显示旺季时间范围
            earliest_year = earliest_date.year
            peak_season_start = f"{earliest_year}-10-15 00:00"
            peak_season_end = f"{earliest_year + 1}-01-14 23:59"
            
            error_msg = f"检测到混合配送周期！MSKU维度利润报表数据不允许同时包含旺季和淡季配送费结算周期。\n"
            error_msg += f"旺季时间范围：{peak_season_start} 至 {peak_season_end}\n"
            error_msg += f"数据日期范围：{earliest_date.strftime('%Y-%m-%d')} 至 {latest_date.strftime('%Y-%m-%d')}\n"
            error_msg += f"旺季范围：{peak_season_ranges}，淡季范围：{off_season_ranges}，混合范围：{mixed_ranges}"
            raise Exception(error_msg)
        
        # 确定是旺季还是淡季
        if peak_season_ranges > 0:
            season_type = "旺季"
        else:
            season_type = "淡季"
        
        print(f"✅ MSKU报表配送周期检查通过：所有日期范围都在{season_type}配送费结算周期内")
    else:
        print(f"✅ 非美国市场（{country_name}），跳过配送周期检查")
    
    print("MSKU维度利润报表日期范围检查完成")

def main():
    # 创建tkinter根窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 打开文件选择对话框
    file_path = filedialog.askopenfilename(
        title="选择订单利润报表文件",
        filetypes=[
            ("Excel文件", "*.xlsx;*.xls"),
            ("CSV文件", "*.csv"),
            ("所有文件", "*.*")
        ]
    )
    
    if not file_path:
        print("未选择文件，程序退出")
        return
        
    try:
        # 读取订单利润报表文件并检查日期范围
        print("\n正在读取订单利润报表文件...")
        df = read_file(file_path)
        
        # 选择Hual MSKU列表文件
        hual_msku_path = filedialog.askopenfilename(
            title="选择Hual MSKU列表文件",
            filetypes=[
                ("Excel文件", "*.xlsx;*.xls"),
                ("所有文件", "*.*")
            ]
        )
        
        if not hual_msku_path:
            print("未选择Hual MSKU列表文件，程序退出")
            return
        
        # 选择产品资料表
        product_info_path = filedialog.askopenfilename(
            title="选择产品资料表",
            filetypes=[
                ("Excel文件", "*.xlsx;*.xls"),
                ("所有文件", "*.*")
            ]
        )
        
        if not product_info_path:
            print("未选择产品资料表，程序退出")
            return
        
        # 读取产品资料表
        print("正在读取产品资料表...")
        try:
            product_info_df = read_product_info(product_info_path)
            print("✅ 产品资料表读取成功")
        except Exception as e:
            print(f"❌ 读取产品资料表失败: {str(e)}")
            print("程序无法继续执行，请检查产品资料表文件格式和内容")
            return
        
        # 读取Hual MSKU列表
        print("正在读取Hual MSKU列表...")
        try:
            hual_msku_set = read_hual_msku_list(hual_msku_path)
            print("✅ Hual MSKU列表读取成功")
        except Exception as e:
            print(f"❌ 读取Hual MSKU列表失败: {str(e)}")
            print("程序无法继续执行，请检查Hual MSKU列表文件格式和内容")
            return
        
        # 检查必要的列是否存在
        required_columns = ['销售额', '买家运费', 'FBA费', '促销折扣', 'MSKU', 
                          '采购成本', '头程费用', '平台费', '数量']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise Exception(f"文件缺少必要的列：{', '.join(missing_columns)}")
        
        # 处理数值列
        numeric_columns = [
            '销售额', '销售税', '买家运费', '买家运费税', 
            '礼品包装', '礼品包装税', '促销折扣', '促销折扣税', 
            '代扣代缴增值税', '市场预扣税', 'FBA费', '其他交易费', 
            '其他', '隐藏税', '采购成本', '头程费用', 
            '其他成本', '站外推广费', '平台费', '数量'
        ]
        
        # 确保所有数值列存在
        for col in numeric_columns:
            if col not in df.columns:
                print(f"警告: 数值列 '{col}' 不存在于订单数据中，将设置为0")
                df[col] = 0
                
        # 将所有数值列转换为数值类型
        for col in numeric_columns:
            df[col] = df[col].astype(str).str.replace(',', '').replace('', '0')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 1. 处理各类特殊订单
        print("\n正在识别各类特殊订单...")
        
        # 识别VINE订单（销售额=0且FBA费不为0）
        vine_df = df[(df['销售额'] == 0) & (df['FBA费'] != 0)].copy()
        vine_df['订单类型'] = 'VINE订单'
        print(f"VINE订单数量: {len(vine_df)}")
        
        # 识别换货订单（销售额=0且FBA费=0）
        exchange_df = df[(df['销售额'] == 0) & (df['FBA费'] == 0)].copy()
        exchange_df['订单类型'] = '换货订单'
        print(f"换货订单数量: {len(exchange_df)}")
        
        # 识别新品入仓优惠订单（FBA费=0且销售额>0）
        new_product_df = df[(df['FBA费'] == 0) & (df['销售额'] > 0)].copy()
        new_product_df['订单类型'] = '新品入仓优惠订单'
        print(f"新品入仓优惠订单数量: {len(new_product_df)}")
        
        # 识别Hual订单
        hual_df = df[df['MSKU'].astype(str).isin(hual_msku_set)].copy()
        hual_df['订单类型'] = 'Hual订单'
        print(f"Hual订单数量: {len(hual_df)}")
        
        # 合并所有特殊订单为异常订单
        abnormal_df = pd.concat([vine_df, exchange_df, new_product_df, hual_df], ignore_index=True)
        print(f"特殊订单总数量: {len(abnormal_df)}")
        
        # 计算所有特殊订单的费用汇总
        abnormal_fees = calculate_abnormal_fees(abnormal_df)
        
        # 检测财务字段是否存在为0的异常情况
        print("\n正在检测财务字段是否存在异常值...")
        zero_fields, partial_zero_fields, abnormal_zero_fields = check_zero_financial_fields(df, abnormal_df)
        
        if zero_fields:
            print("\n警告: 以下财务字段在所有订单中均为0，可能存在数据异常:")
            for field in zero_fields:
                print(f"  - {field}")
                
        if partial_zero_fields:
            print("\n以下财务字段在部分订单中为0:")
            for item in partial_zero_fields:
                print(f"  - {item['字段']}: {item['为0的订单数']}/{item['总订单数']} ({item['为0比例']})")
                
        if abnormal_zero_fields:
            print("\n特殊订单中各财务字段为0的统计:")
            for item in abnormal_zero_fields:
                print(f"  - {item['字段']}: {item['为0的异常订单数']}/{item['异常订单总数']} ({item['为0比例']})")
        
        # 识别未归类的异常订单
        unclassified_abnormal_df = detect_unclassified_abnormal_orders(df, abnormal_df)
        
        # 2. 处理正常订单的实际配送费计算
        print("\n正在处理正常订单的实际配送费计算...")
        # 排除所有特殊订单
        normal_df = df[
            (df['销售额'] != 0) & 
            ~((df['FBA费'] == 0) & (df['销售额'] > 0)) &  # 排除新品入仓优惠订单
            (~df['MSKU'].astype(str).isin(hual_msku_set))  # 排除Hual订单
        ].copy()
        
        print(f"\n数据筛选信息：")
        print(f"总订单数：{len(df)}")
        print(f"正常订单数：{len(normal_df)}")
        print(f"特殊订单数：{len(abnormal_df)}")
        print(f"特殊订单占比：{(len(abnormal_df)/len(df)*100):.2f}%")
        if not unclassified_abnormal_df.empty:
            print(f"未归类异常订单数：{len(unclassified_abnormal_df)}")
            print(f"未归类异常订单占比：{(len(unclassified_abnormal_df)/len(df)*100):.2f}%")
        
        # 计算每个订单的实际配送费和单个实际配送费
        print("\n正在计算订单维度的配送费...")
        normal_df['实际配送费'] = normal_df.apply(calculate_actual_shipping_fee, axis=1)
        normal_df['单个实际配送费'] = normal_df.apply(
            lambda row: row['实际配送费'] / row['数量'] if row['数量'] != 0 else 0, 
            axis=1
        )
        
        # 计算订单维度的采购均价和头程均价
        print("\n正在计算订单维度的采购均价和头程均价...")
        normal_df['采购均价'] = normal_df.apply(
            lambda row: row['采购成本'] / row['数量'] if row['数量'] != 0 else 0, 
            axis=1
        )
        # 修改头程均价计算逻辑，排除头程费用为0的情况
        normal_df['头程均价'] = normal_df.apply(
            lambda row: row['头程费用'] / row['数量'] if row['数量'] != 0 and row['头程费用'] != 0 else 0, 
            axis=1
        )
        
        # 设置配送费的小数位数为2位
        normal_df['实际配送费'] = normal_df['实际配送费'].round(2)
        normal_df['单个实际配送费'] = normal_df['单个实际配送费'].round(2)
        normal_df['采购均价'] = normal_df['采购均价'].round(2)
        normal_df['头程均价'] = normal_df['头程均价'].round(2)
        
        # 创建两个数据集：一个包含所有数据，一个排除头程费用为0的记录
        normal_df_all = normal_df.copy()
        print(f"\n订单维度总记录数: {len(normal_df_all)}")
        
        # 过滤掉头程费用为0的记录，用于计算头程均价相关指标
        normal_df_nonzero_shipping = normal_df[normal_df['头程费用'] != 0].copy()
        print(f"排除头程费用为0后的记录数: {len(normal_df_nonzero_shipping)}")
        print(f"头程费用为0的记录数: {len(normal_df_all) - len(normal_df_nonzero_shipping)}")
        
        # 创建MSKU维度的汇总数据
        # 定义需要汇总的列和需要保留第一个值的列
        sum_columns = numeric_columns + ['实际配送费']
        first_columns = [col for col in normal_df.columns if col not in sum_columns and col != 'MSKU' and col != '订单号']
        
        # 创建分组聚合字典
        agg_dict = {col: 'sum' for col in sum_columns}
        agg_dict.update({col: 'first' for col in first_columns})
        
        # 按MSKU分组并应用聚合 - 使用所有数据
        msku_summary_df = normal_df_all.groupby('MSKU').agg(agg_dict).reset_index()
        
        # 为非零头程费用的数据创建单独的汇总
        msku_nonzero_shipping_df = normal_df_nonzero_shipping.groupby('MSKU').agg({
            'MSKU': 'first',
            '头程费用': 'sum',
            '数量': 'sum'
        }).reset_index(drop=True)
        
        # 计算MSKU维度的单个实际配送费
        print("\n正在计算MSKU维度的单个实际配送费...")
        msku_summary_df['单个实际配送费'] = msku_summary_df.apply(
            lambda row: row['实际配送费'] / row['数量'] if row['数量'] != 0 else 0, 
            axis=1
        )
        
        # 计算MSKU维度的采购均价和头程均价
        print("\n正在计算MSKU维度的采购均价和头程均价...")
        msku_summary_df['采购均价'] = msku_summary_df.apply(
            lambda row: row['采购成本'] / row['数量'] if row['数量'] != 0 else 0, 
            axis=1
        )
        
        # 从非零头程费用数据中计算头程均价
        nonzero_shipping_dict = {}
        for _, row in msku_nonzero_shipping_df.iterrows():
            msku = row['MSKU']
            if row['数量'] > 0:  # 确保不除以零
                nonzero_shipping_dict[msku] = row['头程费用'] / row['数量']
        
        # 将计算结果合并到主汇总表中
        msku_summary_df['头程均价'] = msku_summary_df['MSKU'].map(nonzero_shipping_dict)
        
        # 对于没有非零头程费用数据的MSKU，保持头程均价为NULL
        print(f"头程均价为NULL的MSKU数量: {msku_summary_df['头程均价'].isnull().sum()}")
        print(f"有有效头程均价的MSKU数量: {len(msku_summary_df) - msku_summary_df['头程均价'].isnull().sum()}")
        
        # 设置MSKU维度配送费的小数位数为2位
        msku_summary_df['实际配送费'] = msku_summary_df['实际配送费'].round(2)
        msku_summary_df['单个实际配送费'] = msku_summary_df['单个实际配送费'].round(2)
        msku_summary_df['采购均价'] = msku_summary_df['采购均价'].round(2)

        # 对有效的头程均价设置小数位数
        mask = ~msku_summary_df['头程均价'].isna()
        if mask.any():
            msku_summary_df.loc[mask, '头程均价'] = msku_summary_df.loc[mask, '头程均价'].round(2)
        
        # 检查相同SKC的配送费是否一致
        print("\n正在检查相同SKC的配送费一致性...")
        try:
            inconsistent_skcs = check_shipping_fee_consistency(msku_summary_df, product_info_df)
            print("✅ 配送费一致性检查完成")
        except Exception as e:
            print(f"❌ 配送费一致性检查失败: {str(e)}")
            print("程序无法继续执行，请检查产品资料表和MSKU汇总数据")
            return
        
        if inconsistent_skcs:
            print("\n发现配送费异常：")
            for item in inconsistent_skcs:
                print(f"\nSKC: {item['SKC']}")
                print(f"异常MSKU: {', '.join(item['异常MSKU'])}")
                print(f"配送费: {item['配送费']}")
                print("请确认配送费异常问题，确认是后台尺寸信息一致性")
        
        # 检查相同SKC的头程均价是否一致
        print("\n正在检查相同SKC的头程均价一致性...")
        try:
            inconsistent_shipping_costs = check_shipping_cost_consistency(msku_summary_df, product_info_df)
            print("✅ 头程均价一致性检查完成")
        except Exception as e:
            print(f"❌ 头程均价一致性检查失败: {str(e)}")
            print("程序无法继续执行，请检查产品资料表和MSKU汇总数据")
            return
        
        if inconsistent_shipping_costs:
            print("\n发现头程均价异常：")
            for item in inconsistent_shipping_costs:
                print(f"\nSKC: {item['SKC']}")
                print(f"异常MSKU: {', '.join(item['异常MSKU'])}")
                print(f"头程均价: {item['头程均价']}")
                print(f"最低头程均价: {item['最低头程均价']}")
                print("空运运输方式导致，请确认")
        
        # 获取源文件所在目录和文件名
        source_dir = os.path.dirname(file_path)
        original_filename = os.path.basename(file_path)
        filename_without_ext = os.path.splitext(original_filename)[0]
        
        # 合并异常订单数据和异常订单费用汇总到一个Excel文件中
        abnormal_output_path = os.path.join(source_dir, f"{filename_without_ext}_异常订单数据.xlsx")
        with pd.ExcelWriter(abnormal_output_path, engine='openpyxl') as writer:
            # 按订单类型分组输出到不同的工作表
            vine_df.to_excel(writer, sheet_name='VINE订单', index=False)
            exchange_df.to_excel(writer, sheet_name='换货订单', index=False)
            new_product_df.to_excel(writer, sheet_name='新品入仓优惠订单', index=False)
            hual_df.to_excel(writer, sheet_name='Hual订单', index=False)
            abnormal_df.to_excel(writer, sheet_name='所有特殊订单', index=False)
            abnormal_fees.to_excel(writer, sheet_name='异常订单费用汇总', index=False)
            
            # 输出财务字段零值统计
            if partial_zero_fields:
                zero_field_df = pd.DataFrame(partial_zero_fields)
                zero_field_df.to_excel(writer, sheet_name='所有订单财务字段零值', index=False)
            
            # 输出特殊订单财务字段零值统计
            if abnormal_zero_fields:
                abnormal_zero_df = pd.DataFrame(abnormal_zero_fields)
                abnormal_zero_df.to_excel(writer, sheet_name='特殊订单财务字段零值', index=False)
            
            # 输出未归类的异常订单
            if not unclassified_abnormal_df.empty:
                unclassified_abnormal_df.to_excel(writer, sheet_name='未归类异常订单', index=False)
            
        print(f"\n异常订单数据处理完成，结果已保存至：{abnormal_output_path}")
        print("包含以下工作表：")
        print("1. VINE订单 - 销售额为0且FBA费不为0的订单")
        print("2. 换货订单 - 销售额为0且FBA费=0的订单")
        print("3. 新品入仓优惠订单 - FBA费为0且销售额大于0的订单")
        print("4. Hual订单 - 基于Hual MSKU列表匹配的订单")
        print("5. 所有特殊订单 - 包含上述所有类型的特殊订单")
        print("6. 异常订单费用汇总 - 按MSKU汇总的异常订单费用（包含所有类型的特殊订单）")
        if partial_zero_fields:
            print("7. 所有订单财务字段零值 - 统计所有订单中各财务字段为0的订单数量及比例")
        if abnormal_zero_fields:
            print("8. 特殊订单财务字段零值 - 统计特殊订单中各财务字段为0的订单数量及比例")
        if not unclassified_abnormal_df.empty:
            print("9. 未归类异常订单 - 不属于已知特殊类型但关键财务字段为0的订单，需确认其类型")
        
        # 保存订单维度和MSKU维度的数据到同一个Excel文件
        msku_output_path = os.path.join(source_dir, f"{filename_without_ext}_配送费分析.xlsx")
        with pd.ExcelWriter(msku_output_path, engine='openpyxl') as writer:
            normal_df.to_excel(writer, sheet_name='订单维度明细', index=False)
            msku_summary_df.to_excel(writer, sheet_name='MSKU维度汇总', index=False)
            
            # 创建并输出SKC维度的最低配送费和最低头程均价表
            print("\n正在创建SKC维度的最低配送费和最低头程均价表...")
            try:
                skc_min_fees_original_df, skc_amazon_min_fees_df = create_skc_min_fees_table(msku_summary_df, product_info_df)
                print("✅ SKC最低费用表创建成功")
            except Exception as e:
                print(f"❌ SKC最低费用表创建失败: {str(e)}")
                print("程序无法继续执行，请检查产品资料表和MSKU汇总数据")
                return
            if not skc_min_fees_original_df.empty:
                skc_min_fees_original_df.to_excel(writer, sheet_name='SKC维度最低费用-原始订单', index=False)
            if not skc_amazon_min_fees_df.empty:
                skc_amazon_min_fees_df = skc_amazon_min_fees_df.sort_values(['SKC', '国家'])
                
                # 格式化数值列为2位小数
                skc_amazon_min_fees_df['亚马逊最低配送费'] = skc_amazon_min_fees_df['亚马逊最低配送费'].round(2)
                # 格式化最低头程均价（如果存在）
                if '最低头程均价' in skc_amazon_min_fees_df.columns:
                    # 只对数值类型的单元格进行格式化
                    mask = skc_amazon_min_fees_df['最低头程均价'].apply(lambda x: isinstance(x, (int, float)))
                    if mask.any():
                        skc_amazon_min_fees_df.loc[mask, '最低头程均价'] = skc_amazon_min_fees_df.loc[mask, '最低头程均价'].round(2)
                
                print(f"SKC维度最低费用表创建完成，共{len(skc_amazon_min_fees_df)}条记录")
                print(f"表包含以下列: {skc_amazon_min_fees_df.columns.tolist()}")
                skc_amazon_min_fees_df.to_excel(writer, sheet_name='SKC维度最低费用', index=False)
            
            # 执行SKC维度最低配送费按品质分析
            print("\n正在进行SKC维度最低配送费品质分析...")
            try:
                warn_df, diff_quality_df = analyze_skc_min_shipping_fee_by_quality(msku_summary_df, product_info_df, writer)
                if not warn_df.empty:
                    print(f"发现{len(warn_df)}个同品质下配送费不一致的SKC")
                if not diff_quality_df.empty:
                    print(f"发现{len(diff_quality_df)}个不同品质下配送费不同的SKC")
                print("✅ SKC维度品质分析完成")
            except Exception as e:
                import traceback
                print(f"❌ SKC维度品质分析失败：{str(e)}")
                traceback.print_exc()
                print("程序无法继续执行，请检查产品资料表是否包含必要字段")
                return
            
            # 如果存在配送费异常，按SKC分组统计全部配送费金额分布，并标记是否异常
            if inconsistent_skcs:
                rows = []
                for item in inconsistent_skcs:
                    skc = item['SKC']
                    # 用全部配送费统计分布
                    fee_series = pd.Series(item['全部配送费'])
                    fee_counts = fee_series.value_counts().sort_index()
                    total = fee_series.size
                    min_fee_abs = fee_series.abs().min()
                    for fee, count in fee_counts.items():
                        percent = f"{(count / total * 100):.1f}%"
                        is_abnormal = "是" if abs(fee) > min_fee_abs else "否"
                        rows.append({
                            'SKC': skc,
                            '配送费金额': fee,
                            '数量': count,
                            '占比': percent,
                            '是否异常': is_abnormal
                        })
                shipping_fee_stat_df = pd.DataFrame(rows)
                shipping_fee_stat_df.to_excel(writer, sheet_name='配送费异常', index=False)
            
            # 如果存在头程均价异常，创建一个DataFrame并输出到Excel
            if inconsistent_shipping_costs:
                # 创建一个字典来存储每个SKC每个头程均价对应的MSKU数量
                skc_shipping_cost_stats = {}
                
                # 遍历每个异常SKC
                for item in inconsistent_shipping_costs:
                    skc = item['SKC']
                    min_cost = item['最低头程均价']
                    
                    # 如果这个SKC还没有在统计字典中，则初始化
                    if skc not in skc_shipping_cost_stats:
                        skc_shipping_cost_stats[skc] = {
                            'msku_counts': {},  # 存储每个头程均价对应的MSKU数量
                            'min_cost': min_cost  # 存储最低头程均价
                        }
                    
                    # 统计每个头程均价对应的MSKU数量
                    for msku, cost in zip(item['异常MSKU'], item['头程均价']):
                        if cost not in skc_shipping_cost_stats[skc]['msku_counts']:
                            skc_shipping_cost_stats[skc]['msku_counts'][cost] = []
                        skc_shipping_cost_stats[skc]['msku_counts'][cost].append(msku)
                
                # 创建统计结果列表
                shipping_cost_stats_rows = []
                
                # 对每个SKC处理
                for skc, stats in skc_shipping_cost_stats.items():
                    min_cost = stats['min_cost']
                    total_mskus = sum(len(mskus) for mskus in stats['msku_counts'].values())
                    
                    # 对每个头程均价处理
                    for cost, mskus in stats['msku_counts'].items():
                        count = len(mskus)
                        percentage = (count / total_mskus) * 100
                        diff_percent = (abs(cost) - abs(min_cost)) / abs(min_cost) * 100 if abs(min_cost) > 0 else float('inf')
                        
                        shipping_cost_stats_rows.append({
                            'SKC': skc,
                            '头程均价': cost,
                            'MSKU数量': count,
                            '占比': f"{percentage:.1f}%",
                            '最低头程均价': min_cost,
                            '差异百分比': f"{diff_percent:.1f}%",
                            '是否异常': "是" if diff_percent > 50 else "否",
                            'MSKU列表': ', '.join(mskus)
                        })
                
                # 创建头程均价统计DataFrame
                shipping_cost_stats_df = pd.DataFrame(shipping_cost_stats_rows)
                
                # 按SKC和是否异常排序
                shipping_cost_stats_df = shipping_cost_stats_df.sort_values(
                    by=['SKC', '是否异常', '头程均价'],
                    ascending=[True, False, True]
                )
                
                # 只输出统计表，不再输出明细表
                shipping_cost_stats_df.to_excel(writer, sheet_name='头程均价异常', index=False)
        
        print(f"配送费分析数据已保存至：{msku_output_path}")
        print("包含以下工作表：")
        print("1. 订单维度明细 - 包含所有原始订单数据，以及实际配送费和单个实际配送费")
        print("2. MSKU维度汇总 - 包含按MSKU汇总的数据和单个实际配送费（不含订单号）")
        print("3. SKC维度最低费用 - 按SKC和国家分组统计，显示每个SKC在亚马逊上可获取的最低配送费和最低头程均价")
        print("4. SKC维度最低费用-原始订单 - 按SKC、国家和店铺分组统计，显示当前订单数据中每个店铺的最低配送费")
        print("5. 同品质配送费异常 - 列出同一品质下最低配送费不同的SKC，提示检查listing产品尺寸重量")
        print("6. 不同品质配送费 - 列出不同品质下最低配送费不同的SKC，显示对应品质信息")
        if inconsistent_skcs:
            print("7. 配送费异常 - 包含相同SKC但配送费不一致的MSKU信息")
        if inconsistent_shipping_costs:
            num = 7 if not inconsistent_skcs else 8
            print(f"{num}. 头程均价异常 - 按SKC和头程均价汇总统计，显示每个头程均价对应的MSKU数量和占比")
        
        # 新增功能：校正MSKU维度利润报表
        print("\n是否要校正MSKU维度利润报表？(1: 是, 0: 否)")
        choice = input("请输入选择 (1/0): ")
        
        if choice == "1":
            print("\n准备校正MSKU维度利润报表...")
            # 选择MSKU维度利润报表文件
            msku_report_path = filedialog.askopenfilename(
                title="选择MSKU维度利润报表文件",
                filetypes=[
                    ("Excel文件", "*.xlsx;*.xls"),
                    ("所有文件", "*.*")
                ]
            )
            
            if not msku_report_path:
                print("未选择MSKU维度利润报表文件，跳过校正步骤")
            else:
                print(f"已选择MSKU维度利润报表文件: {msku_report_path}")
                # 校正MSKU维度利润报表
                try:
                    print("\n开始校正过程...")
                    
                    # 创建SKC最低单个实际配送费字典
                    print("\n正在创建SKC最低单个实际配送费字典...")
                    skc_min_shipping_fees = create_skc_min_shipping_fee_dict(msku_summary_df, product_info_df)
                    print(f"共获取到 {len(skc_min_shipping_fees)} 个SKC的最低单个实际配送费信息")
                    
                    # 创建SKC最低头程均价字典
                    print("\n正在创建SKC最低头程均价字典...")
                    skc_min_shipping_costs = create_skc_min_shipping_cost_dict(msku_summary_df, product_info_df)
                    print(f"共获取到 {len(skc_min_shipping_costs)} 个SKC的最低头程均价信息")
                    
                    # 先读取MSKU维度利润报表，从第二行开始读取表头
                    print(f"\n正在读取MSKU维度利润报表: {msku_report_path}")
                    print("使用第二行作为表头读取数据...")
                    
                    # 读取前几行以检查表头情况
                    preview_df = pd.read_excel(msku_report_path, nrows=5)
                    print("\n预览前5行数据:")
                    print(preview_df.head())
                    
                    # 先读取前两行来获取表头
                    header_df = pd.read_excel(msku_report_path, nrows=2, header=None)
                    print("\n前两行内容:")
                    print(header_df)
                    
                    # 使用第二行作为表头
                    headers = header_df.iloc[1].tolist()
                    print(f"\n使用第二行作为表头: {headers[:10]}...")
                    
                    # 读取完整数据，跳过前两行，使用第二行的值作为列名
                    try:
                        msku_report = pd.read_excel(
                            msku_report_path,
                            skiprows=2,  # 跳过前两行
                            names=headers  # 使用第二行的值作为列名
                        )
                        print(f"成功读取数据，共 {len(msku_report)} 行")
                    except Exception as e:
                        print(f"读取数据时出错: {str(e)}")
                        print("尝试使用默认的header=1参数读取...")
                        try:
                            msku_report = pd.read_excel(msku_report_path, header=1)
                            print(f"使用header=1成功读取数据，共 {len(msku_report)} 行")
                            print(f"列名: {list(msku_report.columns)[:10]}...")
                        except Exception as e2:
                            print(f"使用header=1读取仍然失败: {str(e2)}")
                            raise Exception("无法正确读取MSKU维度利润报表，请检查文件格式")
                    
                    # 检查MSKU维度利润报表的日期范围（支持范围格式如"2024-10-15~2025-01-14"）
                    print("\n开始检查MSKU维度利润报表的日期范围...")
                    try:
                        check_msku_profit_date_range(msku_report)
                        print("✅ MSKU维度利润报表日期范围检查通过")
                    except Exception as date_error:
                        print(f"❌ MSKU维度利润报表日期检查失败：{str(date_error)}")
                        print("请检查报表中的'日期'列格式是否正确（应为'2024-10-15~2025-01-14'格式）")
                        print("或确认美国市场数据不包含混合的旺季/淡季日期范围")
                        print("校正过程被终止，请修正日期问题后重新运行")
                        raise Exception(f"MSKU维度利润报表日期检查失败：{str(date_error)}")
                    
                    # 先进行FBA配送费的理想校正
                    print("\n开始进行FBA配送费单价理想校正...")
                    shipping_fee_corrected_report, original_report, fee_correction_df = ideal_correct_shipping_fee(
                        msku_report, product_info_df, skc_min_shipping_fees
                    )
                    
                    # 再进行头程成本的理想校正
                    print("\n开始进行头程成本单价理想校正...")
                    shipping_cost_corrected_report, _, cost_correction_df = ideal_correct_shipping_cost(
                        shipping_fee_corrected_report, product_info_df, skc_min_shipping_costs
                    )
                    
                    # 检查异常订单费用汇总数据是否存在
                    if abnormal_fees.empty:
                        print("警告：异常订单费用汇总数据为空，异常订单校正可能无效")
                    else:
                        print(f"使用异常订单费用汇总数据，共 {len(abnormal_fees)} 条记录")
                        print("包含所有特殊订单类型：VINE订单、换货订单、新品入仓优惠订单和Hual订单")
                    
                    # 执行异常订单校正
                    print("\n开始执行异常订单费用校正...")
                    final_corrected_report, _, abnormal_correction_df = correct_msku_profit_report(
                        shipping_cost_corrected_report, abnormal_fees, skc_min_shipping_fees
                    )
                    
                    # 保存校正后的报表和校正记录
                    corrected_report_path = os.path.join(
                        source_dir, 
                        f"{os.path.splitext(os.path.basename(msku_report_path))[0]}_校正后.xlsx"
                    )
                    
                    print(f"\n正在保存校正结果至: {corrected_report_path}")
                    with pd.ExcelWriter(corrected_report_path, engine='openpyxl') as writer:
                        final_corrected_report.to_excel(writer, sheet_name='校正后MSKU报表', index=False)
                        original_report.to_excel(writer, sheet_name='原始MSKU报表', index=False)
                        fee_correction_df.to_excel(writer, sheet_name='FBA配送费理想校正记录', index=False)
                        cost_correction_df.to_excel(writer, sheet_name='头程成本理想校正记录', index=False)
                        abnormal_correction_df.to_excel(writer, sheet_name='异常订单校正记录', index=False)
                        abnormal_fees.to_excel(writer, sheet_name='异常订单费用', index=False)
                    
                    print(f"\nMSKU维度利润报表校正完成，结果已保存至：{corrected_report_path}")
                    print("包含以下工作表：")
                    print("1. 校正后MSKU报表 - 校正后的MSKU维度利润报表")
                    print("2. 原始MSKU报表 - 原始的MSKU维度利润报表")
                    print("3. FBA配送费理想校正记录 - 详细记录了每个MSKU的FBA配送费理想校正")
                    print("4. 头程成本理想校正记录 - 详细记录了每个MSKU的头程成本理想校正")
                    print("5. 异常订单校正记录 - 详细记录了每个MSKU的异常订单校正前后值")
                    print("6. 异常订单费用 - 用于校正的异常订单费用汇总（包含所有特殊订单类型和所有财务字段）")
                    
                except Exception as e:
                    import traceback
                    print(f"\n校正MSKU维度利润报表时出错：{str(e)}")
                    print("\n详细错误信息:")
                    traceback.print_exc()
        
    except Exception as e:
        import traceback
        print(f"\n处理过程中出现错误：{str(e)}")
        print("\n详细错误信息:")
        traceback.print_exc()

if __name__ == "__main__":
    main() 