import pandas as pd
import difflib
import os
import sys

# ================= 配置区域 =================
# 脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR)) 
# 数据输出目录 (Achievement_Analysis/output)
OUTPUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "output")
# 矩阵定义文件目录 (SciEdu_Matrix_App/data)
MATRIX_DIR = os.path.join(PROJECT_ROOT, "SciEdu_Matrix_App", "data")

# 文件名配置
INPUT_FILENAME = "2021_course_achievement_final.csv"
MATRIX_FILENAME = "matrix_2019.csv"
FINAL_OUTPUT_FILENAME = "2021_achievement_calculation_ready.xlsx"
LOG_FILENAME = "match_log.xlsx"

# 完整路径
INPUT_FILE = os.path.join(OUTPUT_DIR, INPUT_FILENAME)
MATRIX_FILE = os.path.join(MATRIX_DIR, MATRIX_FILENAME)
FINAL_OUTPUT_FILE = os.path.join(OUTPUT_DIR, FINAL_OUTPUT_FILENAME)
LOG_FILE = os.path.join(OUTPUT_DIR, LOG_FILENAME)
# ===========================================

def normalize_name(name):
    """标准化课程名称：处理空格、括号、罗马数字转阿拉伯数字"""
    if pd.isna(name): return ""
    name = str(name).strip()
    
    # 符号统一
    replacements = {'（': '(', '）': ')', '--': '一', '—': '一'}
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    # 罗马数字替换 (按长度降序防止部分替换)
    roman_map = [
        ('VIII', '8'), ('VII', '7'), ('VI', '6'), ('III', '3'), ('II', '2'), ('IV', '4'), ('V', '5'), ('I', '1'),
        ('Ⅷ', '8'), ('Ⅶ', '7'), ('Ⅵ', '6'), ('Ⅲ', '3'), ('Ⅱ', '2'), ('Ⅳ', '4'), ('Ⅴ', '5'), ('Ⅰ', '1')
    ]
    for old, new in roman_map:
        name = name.replace(old, new)
        
    return name

def normalize_code(code):
    """标准化课程代码：去空格，去 .0"""
    if pd.isna(code): return ""
    return str(code).strip().split('.')[0]

def load_data():
    """读取并预处理数据"""
    print(f"Reading Input: {INPUT_FILE}")
    print(f"Reading Matrix: {MATRIX_FILE}")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: 输入文件不存在: {INPUT_FILE}")
        sys.exit(1)
    if not os.path.exists(MATRIX_FILE):
        print(f"❌ Error: 矩阵文件不存在: {MATRIX_FILE}")
        sys.exit(1)

    df_2021 = pd.read_csv(INPUT_FILE, encoding='utf-8-sig', dtype=str)
    df_matrix = pd.read_csv(MATRIX_FILE, encoding='utf-8-sig', dtype=str)

    # 预处理标准化列
    df_2021['norm_code'] = df_2021['课程代码'].apply(normalize_code)
    df_2021['norm_name'] = df_2021['课程名称'].apply(normalize_name)
    
    df_matrix['norm_code'] = df_matrix['课程编码'].apply(normalize_code)
    df_matrix['norm_name'] = df_matrix['课程名称'].apply(normalize_name)

    return df_2021, df_matrix

def perform_matching(df_2021, df_matrix):
    """执行核心匹配逻辑"""
    print("Executing matching logic...")
    
    # 构建查找字典 (去重)
    df_2021_by_code = df_2021.drop_duplicates(subset=['norm_code'])
    df_2021_by_name = df_2021.drop_duplicates(subset=['norm_name'])
    
    map_code = df_2021_by_code.set_index('norm_code')[['课程代码', '课程名称', '达成度']].to_dict('index')
    map_name = df_2021_by_name.set_index('norm_name')[['课程代码', '课程名称', '达成度']].to_dict('index')
    
    # 结果列表
    match_results = [] # 详细日志用
    valid_matches = {} # 最终计算用 {Matrix_Code: 达成度}
    
    for idx, row in df_matrix.iterrows():
        m_code = row['norm_code']
        m_name = row['norm_name']
        m_orig_name = row['课程名称']
        m_orig_code = row['课程编码']
        
        match_data = None
        match_type = "Not Found"

        # 1. Code Exact
        if m_code in map_code:
            match_data = map_code[m_code]
            match_type = "Code Exact"
        # 2. Code Padded (8位补零)
        elif m_code.zfill(8) in map_code:
            match_data = map_code[m_code.zfill(8)]
            match_type = "Code Padded"
        # 3. Name Exact
        elif m_name in map_name:
            match_data = map_name[m_name]
            match_type = "Name Exact"
        # 4. Fuzzy Name
        else:
            all_names = list(map_name.keys())
            close = difflib.get_close_matches(m_name, all_names, n=1, cutoff=0.7)
            if close:
                match_data = map_name[close[0]]
                match_type = f"Fuzzy ({close[0]})"
        
        # 记录
        if match_data:
            valid_matches[m_code] = match_data['达成度']
            
        match_results.append({
            'Matrix_Code': m_orig_code,
            'Matrix_Name': m_orig_name,
            'Match_Type': match_type,
            '2021_Code': match_data['课程代码'] if match_data else "",
            '2021_Name': match_data['课程名称'] if match_data else "",
            '达成度': match_data['达成度'] if match_data else ""
        })
        
    return match_results, valid_matches

def generate_output_files(df_matrix, valid_matches, match_results):
    """生成最终需要的两个 Excel 文件"""
    
    # --- 1. 生成详细日志 ---
    print(f"Generating Log: {LOG_FILE}")
    pd.DataFrame(match_results).to_excel(LOG_FILE, index=False)
    
    # --- 2. 生成计算用长表 ---
    print("Generating Final Calculation File...")
    
    # 识别指标点列
    meta_cols = ['课程编码', '课程名称', '序号', 'norm_code', 'norm_name']
    indicator_cols = [c for c in df_matrix.columns if c not in meta_cols]
    
    # 宽表转长表
    df_long = df_matrix.melt(
        id_vars=['课程名称', 'norm_code'],
        value_vars=indicator_cols,
        var_name='指标点',
        value_name='支撑强度'
    )
    
    # 清洗
    df_long = df_long.dropna(subset=['支撑强度'])
    df_long = df_long[df_long['支撑强度'].astype(str).str.strip() != '']
    
    # 填入达成度
    final_rows = []
    for _, row in df_long.iterrows():
        m_code = row['norm_code']
        # 只有当这门课在 2021 数据中匹配到了，才写入最终表
        if m_code in valid_matches:
            final_rows.append({
                '课程名称': row['课程名称'], # 统一使用 Matrix 里的标准名称
                '指标点': row['指标点'],
                '支撑强度': row['支撑强度'],
                '达成度': valid_matches[m_code]
            })
            
    final_df = pd.DataFrame(final_rows)
    
    # 类型转换与排序
    if not final_df.empty:
        final_df['达成度'] = pd.to_numeric(final_df['达成度'], errors='coerce')
        final_df = final_df.sort_values(by=['指标点', '课程名称'])
    
    print(f"Saving Final Output: {FINAL_OUTPUT_FILE}")
    final_df.to_excel(FINAL_OUTPUT_FILE, index=False)
    
    # 打印摘要
    found_count = len(valid_matches)
    total_count = len(df_matrix)
    total_indicators = len(final_df)
    
    print("=" * 50)
    print(f"🎉 处理完成！数据分析报告如下：")
    print(f"--------------------------------------------------")
    print(f"📚 Matrix 课程总数: {total_count}")
    print(f"✅ 成功匹配课程数: {found_count}")
    print(f"🔗 生成支撑关系数: {total_indicators} (分解指标点)")
    print(f"❌ 缺失成绩课程数: {total_count - found_count}")
    print(f"--------------------------------------------------")
    
    if total_count - found_count > 0:
        missing_courses = [r['Matrix_Name'] for r in match_results if r['Match_Type'] == 'Not Found']
        print(f"⚠️ 以下 {len(missing_courses)} 门 Matrix 核心课程未找到对应成绩：")
        for i, c in enumerate(missing_courses):
            print(f"  {i+1}. {c}")
        print(f"--------------------------------------------------")
        
    print(f"📂 最终文件: {FINAL_OUTPUT_FILE}")
    print("=" * 50)

def main():
    # 1. 加载
    df_2021, df_matrix = load_data()
    # 2. 匹配
    match_results, valid_matches = perform_matching(df_2021, df_matrix)
    # 3. 输出
    generate_output_files(df_matrix, valid_matches, match_results)

if __name__ == "__main__":
    main()
