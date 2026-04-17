"""
smart_data_cleaner.py — 成绩数据自动清洗管线

将教务系统导出的"脏"成绩 Excel 一键转换为 process_data.py 可用的标准 CSV。

用法:
    python smart_data_cleaner.py --major physics --input 2021级物理学.xlsx
    python smart_data_cleaner.py --major physics --input data.xlsx --code-csv 课程编码与名称.csv

自动处理:
    1. 全角字符 → 半角字符 (括号、罗马数字、数字)
    2. 课程编码自动匹配 (从 SSoT 的 课程编码与名称.csv 或 培养方案 DOCX)
    3. 平均分 → 达成度 (score / 100)
    4. 输出标准格式 CSV (课程代码, 课程名称, 达成度)
"""

import pandas as pd
import re
import os
import sys
import argparse

# ============================================================
# 路径解析
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # get_ur_matrix/
SSOT_DIR = os.environ.get(
    "SCIEDU_SSOT_DIR",
    os.path.join(os.path.dirname(PROJECT_ROOT), "SciEdu_Central_Data")
)

# ============================================================
# 1. 全角 → 半角 & 标准化
# ============================================================
FULLWIDTH_MAP = {
    '（': '(', '）': ')',
    '１': '1', '２': '2', '３': '3', '４': '4', '５': '5',
    '６': '6', '７': '7', '８': '8', '９': '9', '０': '0',
    '－': '-', '—': '-', '–': '-',
    '：': ':', '；': ';', '，': ',',
    'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV',
    'Ⅴ': 'V', 'Ⅵ': 'VI', 'Ⅶ': 'VII', 'Ⅷ': 'VIII',
}

def normalize_text(text: str) -> str:
    """全角转半角 + 去空格"""
    if not isinstance(text, str):
        return text
    for full, half in FULLWIDTH_MAP.items():
        text = text.replace(full, half)
    return text.strip()


def get_base_name(name: str) -> str:
    """
    提取课程基础名 (用于模糊匹配)
    '形势与政策III' → '形势与政策'
    '普通物理实验I(力热)' → '普通物理实验'
    """
    name = normalize_text(str(name))
    # 罗马数字 → 数字 (先长后短防止误匹配)
    for r, d in [('VIII','8'),('VII','7'),('VI','6'),
                  ('III','3'),('II','2'),('IV','4'),('V','5'),('I','1')]:
        name = name.replace(r, d)
    # 特殊前缀保护 (C语言)
    if name.startswith('C语言'):
        return 'C语言程序设计'
    # "之—" 类别
    if '之—' in name or '之--' in name:
        name = name.split('之')[0]
    # 移除括号内容和末尾数字
    name = re.sub(r'\([^)]*\)$', '', name).strip()
    name = re.sub(r'\d+$', '', name).strip()
    return name


# ============================================================
# 2. 课程编码匹配
# ============================================================
def load_code_mapping(major: str, code_csv_path: str = None) -> dict:
    """
    加载课程编码映射表.
    优先使用用户指定的 CSV，回退到 SSoT 中的标准文件。
    返回 {标准化课程名: 编码} 字典。
    """
    # 查找编码文件
    if code_csv_path and os.path.exists(code_csv_path):
        csv_path = code_csv_path
    else:
        csv_path = os.path.join(SSOT_DIR, "majors", major, "课程编码与名称.csv")

    if not os.path.exists(csv_path):
        print(f"⚠️ 未找到课程编码文件: {csv_path}")
        return {}

    print(f"📖 加载课程编码表: {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    
    mapping = {}
    for _, row in df.iterrows():
        code = str(row['课程编码']).strip()
        if code in ('新编号', 'nan', ''):
            continue
        raw_name = str(row['课程名称']).split('\n')[0].strip()
        # 清理英文和星号
        clean = re.sub(r'\s+[A-Za-z].*$', '', raw_name).strip()
        clean = clean.replace('*', '').strip()
        # 保留 C语言 开头的
        if not clean.startswith('C语言') and not clean.startswith('C 语言'):
            # 移除非空格开头的英文
            match = re.match(r'^([\u4e00-\u9fa5A-Za-z0-9\(\)（）\-—]+)', clean)
            if match:
                clean = match.group(1)
        clean = normalize_text(clean)
        mapping[clean] = code

    print(f"   ✅ 加载 {len(mapping)} 条编码映射")
    return mapping


def match_course_code(name: str, mapping: dict) -> str:
    """根据课程名称匹配编码 (精确 → 基础名称)"""
    norm = normalize_text(name)
    
    # 精确匹配
    if norm in mapping:
        return mapping[norm]
    
    # 基础名称匹配 (如 "形势与政策" 匹配 "形势与政策III")
    base = get_base_name(name)
    for map_name, code in mapping.items():
        if get_base_name(map_name) == base:
            return code
    
    return ''


# ============================================================
# 3. 主流程
# ============================================================
def clean_data(input_path: str, major: str, code_csv: str = None,
               output_path: str = None) -> str:
    """
    主流程: 读取脏 Excel → 输出干净 CSV
    
    Returns:
        输出文件路径
    """
    print(f"\n{'='*60}")
    print(f"🧹 Smart Data Cleaner")
    print(f"   输入: {input_path}")
    print(f"   专业: {major}")
    print(f"{'='*60}\n")

    # --- Step 0: 读取 Excel ---
    print("[Step 1/4] 📂 读取原始数据...")
    df = pd.read_excel(input_path)
    print(f"   原始数据: {len(df)} 行, 列: {df.columns.tolist()}")

    # --- Step 1: 全角转半角 ---
    print("\n[Step 2/4] 🔧 标准化文本 (全角→半角)...")
    text_cols = df.select_dtypes(include=['object']).columns
    changes_count = 0
    for col in text_cols:
        original = df[col].copy()
        df[col] = df[col].apply(lambda x: normalize_text(x) if isinstance(x, str) else x)
        changes_count += (original != df[col]).sum()
    print(f"   修正了 {changes_count} 处全角字符")

    # --- Step 2: 列名智能检测 ---
    print("\n[Step 3/4] 🔍 检测列名并计算达成度...")
    
    # 检测课程代码列
    code_col = None
    for candidate in ['课程代码', '课程编码', '课程号', 'course_code']:
        if candidate in df.columns:
            code_col = candidate
            break
    
    # 检测课程名称列
    name_col = None
    for candidate in ['课程名称', '课程名', 'course_name']:
        if candidate in df.columns:
            name_col = candidate
            break
    
    if name_col is None:
        print("   ❌ 未找到课程名称列！")
        sys.exit(1)
    
    # 检测分数/达成度列
    score_col = None
    achievement_col = None
    for candidate in ['达成度', 'achievement']:
        if candidate in df.columns:
            achievement_col = candidate
            break
    if achievement_col is None:
        for candidate in ['平均分', '平均成绩', 'average_score', '均分']:
            if candidate in df.columns:
                score_col = candidate
                break

    # 计算达成度
    if achievement_col:
        print(f"   ✅ 找到达成度列: {achievement_col}")
        df['达成度'] = pd.to_numeric(df[achievement_col], errors='coerce')
    elif score_col:
        print(f"   📊 找到分数列: {score_col}，自动计算达成度 = 分数/100")
        df['达成度'] = pd.to_numeric(df[score_col], errors='coerce') / 100
    else:
        print("   ❌ 未找到分数或达成度列！")
        print(f"   可用列: {df.columns.tolist()}")
        sys.exit(1)

    # --- Step 3: 课程编码匹配 ---
    print("\n[Step 4/4] 🔗 匹配课程编码...")
    
    # 如果原始数据有课程代码，直接使用
    if code_col:
        df['课程代码'] = df[code_col].astype(str).str.strip()
        # 补零 (如 '7190140' → '07190140')
        df['课程代码'] = df['课程代码'].apply(
            lambda x: x.zfill(8) if x.isdigit() and len(x) < 8 else x
        )
        print(f"   ✅ 使用原始课程代码列: {code_col}")
    else:
        # 从编码表匹配
        mapping = load_code_mapping(major, code_csv)
        if mapping:
            df['课程代码'] = df[name_col].apply(lambda n: match_course_code(n, mapping))
            matched = (df['课程代码'] != '').sum()
            print(f"   ✅ 编码匹配: {matched}/{len(df)} ({matched/len(df)*100:.0f}%)")
        else:
            df['课程代码'] = ''
            print("   ⚠️ 无编码表可用，课程代码为空")

    # --- 生成输出 ---
    result = df[['课程代码', name_col, '达成度']].copy()
    result = result.rename(columns={name_col: '课程名称'})
    
    # 清理无效行
    result = result.dropna(subset=['达成度'])
    result = result[result['达成度'] > 0]

    # 确定输出路径
    if output_path is None:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_dir = os.path.join(SCRIPT_DIR, '..', 'output')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{major}_{basename}_cleaned.csv")

    result.to_csv(output_path, index=False, encoding='utf-8-sig')

    # --- 报告 ---
    print(f"\n{'='*60}")
    print(f"✅ 清洗完成!")
    print(f"   输出文件: {output_path}")
    print(f"   有效课程: {len(result)} 门")
    
    # 数据质量检查
    missing_codes = (result['课程代码'] == '').sum()
    if missing_codes > 0:
        print(f"   ⚠️ {missing_codes} 门课程缺少编码")
    
    abnormal = result[result['达成度'] > 1.0]
    if len(abnormal) > 0:
        print(f"   ⚠️ {len(abnormal)} 门课程达成度 > 1.0 (异常)")
    
    low = result[result['达成度'] < 0.6]
    if len(low) > 0:
        print(f"   ℹ️ {len(low)} 门课程达成度 < 0.6 (偏低)")
    
    print(f"{'='*60}")
    
    return output_path


# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="🧹 成绩数据自动清洗管线",
        epilog="示例: python smart_data_cleaner.py --major physics --input 2021级物理学.xlsx"
    )
    parser.add_argument("--input", "-i", required=True,
                        help="原始成绩 Excel 文件路径")
    parser.add_argument("--major", "-m", required=True,
                        help="专业代码 (如 physics, sci_edu)")
    parser.add_argument("--code-csv", default=None,
                        help="课程编码映射 CSV (默认: SSoT/majors/{major}/课程编码与名称.csv)")
    parser.add_argument("--output", "-o", default=None,
                        help="输出文件路径 (默认: output/{major}_{input}_cleaned.csv)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ 文件不存在: {args.input}")
        sys.exit(1)
    
    output = clean_data(args.input, args.major, args.code_csv, args.output)
    
    # 提示下一步
    print(f"\n💡 下一步:")
    print(f"   python process_data.py --major {args.major} --year 2019 --input {output}")


if __name__ == "__main__":
    main()
