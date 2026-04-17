"""
add_course_codes.py
从培养方案 DOCX 中提取课程编码，并添加到矩阵 CSV 文件中。

用法:
    python add_course_codes.py <培养方案.docx> <矩阵.csv> [--output <输出.csv>]
"""

import pandas as pd
import os
import sys
import re
import argparse
from docx import Document

def extract_course_codes(docx_path: str) -> dict:
    """从培养方案 DOCX 中提取课程编码和名称的对应关系"""
    doc = Document(docx_path)
    course_map = {}
    
    for table in doc.tables:
        for row in table.rows[1:]:
            cells = [cell.text.strip() for cell in row.cells]
            
            for i, cell in enumerate(cells):
                # 课程编码通常是 7-8 位数字
                if cell.isdigit() and 7 <= len(cell) <= 10:
                    # 向后查找课程名称
                    for j in range(i+1, len(cells)):
                        name_cell = cells[j].strip()
                        if name_cell:
                            # 提取中文课程名称 (去掉英文)
                            name = name_cell.split('\n')[0].split()[0] if name_cell else ''
                            name = re.sub(r'[A-Za-z].*$', '', name).strip()
                            if name and len(name) >= 2:
                                course_map[name] = cell
                            break
                    break
    
    return course_map

def normalize_name(name: str) -> str:
    """标准化课程名称用于匹配"""
    if not name:
        return ""
    name = str(name).strip()
    
    # 1. 全角转半角
    fullwidth_to_halfwidth = {
        '（': '(', '）': ')', 
        '１': '1', '２': '2', '３': '3', '４': '4', '５': '5',
        '６': '6', '７': '7', '８': '8', '９': '9', '０': '0',
        '－': '-', '—': '-', '–': '-',
        '：': ':', '；': ';', '，': ',',
    }
    for full, half in fullwidth_to_halfwidth.items():
        name = name.replace(full, half)
    
    # 2. 罗马数字替换 (按长度降序防止部分替换)
    roman_map = [
        ('VIII', '8'), ('VII', '7'), ('VI', '6'), 
        ('III', '3'), ('II', '2'), ('IV', '4'), ('V', '5'), ('I', '1'),
        ('Ⅷ', '8'), ('Ⅶ', '7'), ('Ⅵ', '6'), 
        ('Ⅲ', '3'), ('Ⅱ', '2'), ('Ⅳ', '4'), ('Ⅴ', '5'), ('Ⅰ', '1')
    ]
    for old, new in roman_map:
        name = name.replace(old, new)
    
    return name

def get_base_course_name(name: str) -> str:
    """
    提取课程的基础名称（去掉编号后缀如 I, II, 1, 2 等）
    例如: "教育见习I" -> "教育见习", "形势与政策III" -> "形势与政策"
    """
    name = normalize_name(name)
    # 移除末尾的数字编号
    import re
    # 移除末尾的 (xxx) 括号内容
    name = re.sub(r'\([^)]*\)$', '', name).strip()
    # 移除末尾的数字
    name = re.sub(r'[0-9]+$', '', name).strip()
    return name

def add_codes_to_matrix(docx_path: str, csv_path: str, output_path: str = None):
    """将课程编码添加到矩阵 CSV"""
    
    print(f"📖 正在从培养方案提取课程编码: {docx_path}")
    course_map = extract_course_codes(docx_path)
    print(f"   找到 {len(course_map)} 个课程编码")
    
    print(f"📊 正在读取矩阵文件: {csv_path}")
    
    # 读取 CSV，跳过第一行（毕业要求名称行）
    df = pd.read_csv(csv_path, encoding='utf-8-sig', header=1)
    
    # 假设第一列是课程名称
    name_col = df.columns[0]
    
    # 创建标准化名称映射
    norm_course_map = {}
    for name, code in course_map.items():
        norm_name = normalize_name(name)
        norm_course_map[norm_name] = code
    
    # 匹配并添加课程编码
    codes = []
    matched = 0
    unmatched = []
    
    for idx, row in df.iterrows():
        course_name = str(row[name_col]).strip()
        norm_name = normalize_name(course_name)
        
        # 精确匹配
        if norm_name in norm_course_map:
            codes.append(norm_course_map[norm_name])
            matched += 1
        else:
            # 尝试部分匹配 (课程名称可能有编号如 I, II)
            found = False
            for map_name, code in norm_course_map.items():
                if map_name.startswith(norm_name) or norm_name.startswith(map_name):
                    codes.append(code)
                    matched += 1
                    found = True
                    break
            if not found:
                codes.append('')
                unmatched.append(course_name)
    
    # 插入课程编码列
    df.insert(0, '课程编码', codes)
    
    # 保存
    if output_path is None:
        output_path = csv_path
    
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ 处理完成!")
    print(f"   匹配成功: {matched} 门")
    print(f"   未匹配: {len(unmatched)} 门")
    print(f"   输出文件: {output_path}")
    
    if unmatched:
        print(f"\n⚠️ 以下课程未找到编码 (需手动补充):")
        for name in unmatched:
            print(f"   - {name}")
    
    return matched, len(unmatched)

def main():
    parser = argparse.ArgumentParser(description="从培养方案提取课程编码并添加到矩阵CSV")
    parser.add_argument("docx", help="培养方案 DOCX 文件路径")
    parser.add_argument("csv", help="矩阵 CSV 文件路径")
    parser.add_argument("--output", "-o", default=None, help="输出文件路径 (默认覆盖原文件)")
    
    args = parser.parse_args()
    add_codes_to_matrix(args.docx, args.csv, args.output)

if __name__ == "__main__":
    main()
