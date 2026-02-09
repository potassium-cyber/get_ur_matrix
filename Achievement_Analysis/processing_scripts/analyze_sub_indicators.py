import pandas as pd
import os

# 配置路径
OUTPUT_DIR = "get_ur_matrix/Achievement_Analysis/output"
INPUT_FILE = os.path.join(OUTPUT_DIR, "2021_achievement_calculation_ready.xlsx")
RESULT_FILE = os.path.join(OUTPUT_DIR, "sub_indicator_hml_stats.xlsx")

def analyze():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 错误：找不到文件 {INPUT_FILE}")
        return

    print(f"📂 正在读取数据: {INPUT_FILE}")
    df = pd.read_excel(INPUT_FILE)

    # 数据清洗
    df['支撑强度'] = df['支撑强度'].astype(str).str.strip().str.upper()
    df['达成度'] = pd.to_numeric(df['达成度'], errors='coerce')
    
    # 按照 指标点 和 支撑强度 分组统计
    stats = df.groupby(['指标点', '支撑强度'])['达成度'].agg(['mean', 'std', 'count']).reset_index()
    
    # 重命名
    stats.columns = ['指标点', '支撑强度', '平均达成度', '标准差', '课程门数']
    
    # 为了方便对比，我们可以做一个透视表
    pivot_stats = stats.pivot(index='指标点', columns='支撑强度', values='平均达成度')
    
    # --- 新增计算逻辑 ---
    def calculate_weighted_score(row):
        # 定义标准权重
        weights = {'H': 0.7, 'M': 0.25, 'L': 0.05}
        
        valid_score_sum = 0
        valid_weight_sum = 0
        
        for col in ['H', 'M', 'L']:
            if col in row.index and pd.notna(row[col]):
                valid_score_sum += row[col] * weights[col]
                valid_weight_sum += weights[col]
        
        if valid_weight_sum == 0:
            return 0
        
        # 归一化计算：确保权重之和为1
        return valid_score_sum / valid_weight_sum

    # 1. 计算【分解指标点达成度】
    pivot_stats['分解指标点达成度'] = pivot_stats.apply(calculate_weighted_score, axis=1)
    
    # 2. 计算【毕业要求达成度】(大指标点的算术平均)
    # 提取大指标点 (例如 "1-1" -> "1")
    pivot_stats['大指标'] = pivot_stats.index.to_series().apply(lambda x: str(x).split('-')[0])
    
    # 计算分组平均值
    major_scores = pivot_stats.groupby('大指标')['分解指标点达成度'].mean()
    
    # 映射回原表
    pivot_stats['毕业要求达成度'] = pivot_stats['大指标'].map(major_scores)
    
    # 清理临时列，并调整列顺序
    pivot_stats = pivot_stats.drop(columns=['大指标'])
    
    # 确保 H, M, L 列都存在（防止某一列全空导致列名缺失）
    for col in ['H', 'M', 'L']:
        if col not in pivot_stats.columns:
            pivot_stats[col] = pd.NA
            
    # 指定列顺序：H -> M -> L -> 分解 -> 毕业要求
    cols = ['H', 'M', 'L', '分解指标点达成度', '毕业要求达成度']
    pivot_stats = pivot_stats[cols]

    # 保存结果到 Excel 的两个 Sheet
    with pd.ExcelWriter(RESULT_FILE) as writer:
        stats.to_excel(writer, sheet_name='详细统计', index=False)
        pivot_stats.to_excel(writer, sheet_name='HML对比透视表')

    print(f"✅ 统计完成！结果已保存至: {RESULT_FILE}")
    
    # 打印部分结果预览
    print("\n--- 分解指标点 H/M/L 达成度统计预览 ---")
    print(stats.head(15))
    
    # 简单分析：找出平均达成度低于 0.8 的薄弱点
    weak_points = stats[stats['平均达成度'] < 0.8]
    if not weak_points.empty:
        print("\n⚠️ 预警：以下指标点的平均达成度低于 0.8：")
        print(weak_points[['指标点', '支撑强度', '平均达成度', '课程门数']])

if __name__ == "__main__":
    analyze()