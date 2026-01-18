import os
import sys
import pandas as pd
import subprocess

# 定义路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SCRIPTS_DIR = os.path.join(BASE_DIR, "processing_scripts")
PROJECT_ROOT = os.path.dirname(BASE_DIR)
MATRIX_FILE = os.path.join(PROJECT_ROOT, "SciEdu_Matrix_App", "data", "matrix_2019.csv")

print(f"工作目录: {BASE_DIR}")

def step_1_clean_data():
    print("\n[Step 1] 清洗原始数据...")
    # 这里模拟之前的 python -c 逻辑
    # 假设原始文件是 raw_data/2021年_课程目标达成度.csv 或 2021课程达成情况.csv
    # 根据之前的情况，我们最终用的是 2021_course_achievement_final.csv (已生成好)
    # 如果要从头开始，需要明确原始文件是谁。
    # 这里我们假设 Step 1 已经完成，文件在 output/2021_course_achievement_final.csv
    
    src = os.path.join(OUTPUT_DIR, "2021_course_achievement_final.csv")
    if not os.path.exists(src):
        # 尝试找 cleaned
        src = os.path.join(OUTPUT_DIR, "2021_course_achievement_cleaned.csv")
        
    if os.path.exists(src):
        print(f"找到中间数据: {src}")
        return src
    else:
        print("❌ 未找到 '2021_course_achievement_final.csv'。请确保原始数据已清洗。" )
        return None

def step_2_generate_final(input_csv):
    print("\n[Step 2] 执行生成脚本 (generate_final_excel.py)...")
    script_path = os.path.join(SCRIPTS_DIR, "generate_final_excel.py")
    
    # 我们需要修改 generate_final_excel.py 的逻辑，或者在这里直接调用它的核心函数
    # 为了方便，我们这里直接运行它，但需要它能找到文件
    # 临时方案：把脚本里的路径改成参数传入，或者修改脚本
    
    # 让我们直接读取脚本内容并在当前环境中执行（稍微黑客一点，但省事）
    # 或者，更好的方式是重写 generate_final_excel.py 让它接受参数
    # 这里我选择：调用 python 子进程，但传入环境变量或参数？
    
    # 最简单的：在这个 run 脚本里重写一遍核心逻辑，反正也不长。
    pass

# 由于之前的脚本都是硬编码路径，我现在更新一下 generate_final_excel.py
# 让它使用相对路径
