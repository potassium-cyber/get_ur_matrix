import pandas as pd
import os

# 配置路径
DATA_DIR = "SciEdu_Matrix_App/data"
TARGET_FILES = ["matrix_2023.csv", "matrix_2019.csv"]

def reorder_csv(file_path):
    if not os.path.exists(file_path):
        print(f"⚠️ 文件未找到: {file_path}")
        return

    try:
        print(f"🔄 正在处理: {file_path} ...")
        
        # 读取 CSV (保持 utf-8-sig 编码以兼容 Excel)
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        
        # 假设第一列是课程名称
        course_col = df.columns[0]
        
        # 1. 清洗数据：去除首尾空格，确保长度计算准确
        # (先转换为字符串，避免非字符串类型报错)
        df[course_col] = df[course_col].astype(str).str.strip()
        
        # 2. 计算长度：创建一个临时列存储长度
        df['_length'] = df[course_col].apply(len)
        
        # 3. 排序：
        # 第一优先级：长度 (从小到大)
        # 第二优先级：课程名称本身 (拼音/字符顺序，长度相同时保持整齐)
        df = df.sort_values(by=['_length', course_col], ascending=[True, True])
        
        # 4. 删除临时列
        df = df.drop(columns=['_length'])
        
        # 5. 保存回文件
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        print(f"✅ 排序完成: {file_path} (按课程名长度 上短->下长)")
        
    except Exception as e:
        print(f"❌ 处理出错 {file_path}: {e}")

if __name__ == "__main__":
    print("🚀 开始按课程名称长度重排数据...")
    for filename in TARGET_FILES:
        full_path = os.path.join(DATA_DIR, filename)
        reorder_csv(full_path)
    print("🏁 所有任务结束。请刷新网页查看效果。")
