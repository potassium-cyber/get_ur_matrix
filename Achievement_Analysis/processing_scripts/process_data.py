import pandas as pd
import difflib
import os
import sys
import argparse

# ================= 路径配置 =================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
OUTPUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "output")

# SSoT 路径 (支持环境变量覆盖)
SSOT_DIR = os.environ.get("SCIEDU_SSOT_DIR", 
    os.path.join(os.path.dirname(PROJECT_ROOT), "SciEdu_Central_Data"))

def get_matrix_path(major: str, year: str) -> str:
    """
    获取指定专业和版本的矩阵文件路径。
    优先使用新目录结构 (majors/), 回退到旧结构 (matrices/)。
    """
    # 新结构: majors/{major}/matrix_{year}.csv
    new_path = os.path.join(SSOT_DIR, "majors", major, f"matrix_{year}.csv")
    if os.path.exists(new_path):
        return new_path
    
    # 旧结构回退: matrices/matrix_{year}.csv (仅限 sci_edu)
    if major == "sci_edu":
        old_path = os.path.join(SSOT_DIR, "matrices", f"matrix_{year}.csv")
        if os.path.exists(old_path):
            return old_path
    
    # 最后尝试 App 内的数据 (兼容性)
    app_path = os.path.join(PROJECT_ROOT, "SciEdu_Matrix_App", "data", f"matrix_{year}.csv")
    if os.path.exists(app_path):
        return app_path
    
    raise FileNotFoundError(f"Matrix file not found for major={major}, year={year}")

def parse_args():
    parser = argparse.ArgumentParser(description="毕业要求达成度计算 - 数据处理脚本")
    parser.add_argument("--major", default="sci_edu", 
                        help="专业代码，如 sci_edu (科学教育) 或 physics (物理学)")
    parser.add_argument("--year", default="2019", 
                        help="培养方案版本年份，如 2019 或 2023")
    parser.add_argument("--input", default=None,
                        help="成绩数据文件路径 (默认: output/{year}_course_achievement_final.csv)")
    parser.add_argument("--output-suffix", default="",
                        help="输出文件后缀 (用于区分不同批次)")
    return parser.parse_args()

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

def load_data(input_file: str, matrix_file: str):
    """读取并预处理数据"""
    print(f"Reading Input: {input_file}")
    print(f"Reading Matrix: {matrix_file}")
    
    if not os.path.exists(input_file):
        print(f"❌ Error: 输入文件不存在: {input_file}")
        sys.exit(1)
    if not os.path.exists(matrix_file):
        print(f"❌ Error: 矩阵文件不存在: {matrix_file}")
        sys.exit(1)

    df_input = pd.read_csv(input_file, encoding='utf-8-sig', dtype=str)
    df_matrix = pd.read_csv(matrix_file, encoding='utf-8-sig', dtype=str)

    # 预处理标准化列
    df_input['norm_code'] = df_input['课程代码'].apply(normalize_code)
    df_input['norm_name'] = df_input['课程名称'].apply(normalize_name)
    
    df_matrix['norm_code'] = df_matrix['课程编码'].apply(normalize_code)
    df_matrix['norm_name'] = df_matrix['课程名称'].apply(normalize_name)

    return df_input, df_matrix

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

def generate_output_files(df_matrix, valid_matches, match_results, final_output_file: str, log_file: str):
    """生成最终需要的两个 Excel 文件"""
    
    # --- 1. 生成详细日志 ---
    print(f"Generating Log: {log_file}")
    pd.DataFrame(match_results).to_excel(log_file, index=False)
    
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
    
    print(f"Saving Final Output: {final_output_file}")
    final_df.to_excel(final_output_file, index=False)
    
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
        
    print(f"📂 最终文件: {final_output_file}")
    print("=" * 50)

def main():
    args = parse_args()
    
    # 解析路径
    matrix_file = get_matrix_path(args.major, args.year)
    
    # 输入文件: CLI 指定 或 默认
    if args.input:
        input_file = args.input
    else:
        input_file = os.path.join(OUTPUT_DIR, f"{args.year}_course_achievement_final.csv")
    
    # 输出文件
    suffix = f"_{args.output_suffix}" if args.output_suffix else ""
    final_output_file = os.path.join(OUTPUT_DIR, f"{args.major}_{args.year}_achievement_ready{suffix}.xlsx")
    log_file = os.path.join(OUTPUT_DIR, f"{args.major}_{args.year}_match_log{suffix}.xlsx")
    
    print(f"\n🎓 毕业要求达成度计算")
    print(f"   专业: {args.major}")
    print(f"   版本: {args.year}")
    print(f"   矩阵: {matrix_file}")
    print()
    
    # 1. 加载
    df_input, df_matrix = load_data(input_file, matrix_file)
    # 2. 匹配
    match_results, valid_matches = perform_matching(df_input, df_matrix)
    # 3. 输出
    generate_output_files(df_matrix, valid_matches, match_results, final_output_file, log_file)

if __name__ == "__main__":
    main()
