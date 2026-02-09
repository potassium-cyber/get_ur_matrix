import pandas as pd
import plotly.express as px
import os

# 配置路径
OUTPUT_DIR = "get_ur_matrix/Achievement_Analysis/output"
INPUT_FILE = os.path.join(OUTPUT_DIR, "sub_indicator_hml_stats.xlsx")
HTML_OUTPUT = os.path.join(OUTPUT_DIR, "sub_indicator_visualization.html")

def visualize():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 错误：找不到文件 {INPUT_FILE}")
        return

    print(f"📂 正在加载统计数据: {INPUT_FILE}")
    # 读取详细统计 Sheet
    df = pd.read_excel(INPUT_FILE, sheet_name='详细统计')

    # 排序：确保指标点按 1-1, 1-2, 2-1 的顺序排列
    # 我们创建一个临时的排序键
    df['sort_key'] = df['指标点'].apply(lambda x: [int(i) for i in x.split('-')])
    df = df.sort_values(by='sort_key').drop(columns=['sort_key'])

    # 创建交互式柱状图
    fig = px.bar(
        df,
        x="指标点",
        y="平均达成度",
        color="支撑强度",
        barmode="group",
        title="分解指标点 HML 达成度对比图 (2021级)",
        hover_data=["课程门数", "标准差"],
        # 自定义颜色：H(深蓝), M(中蓝), L(浅蓝)
        color_discrete_map={'H': '#003366', 'M': '#336699', 'L': '#99CCFF'},
        labels={'平均达成度': '平均达成度 (Score)', '指标点': '分解指标点'}
    )

    # 添加 0.80 基准线 (不带字符标注)
    fig.add_hline(
        y=0.80, 
        line_dash="dash", 
        line_color="red", 
        line_width=2
    )

    # 优化布局
    fig.update_layout(
        yaxis_range=[0.5, 1.0], # 聚焦 0.5 以上的区间
        xaxis_title="分解指标点 (Indicator Points)",
        yaxis_title="达成度均值 (Average Achievement)",
        legend_title="支撑强度",
        plot_bgcolor='white'
    )
    
    # 增加网格线方便对齐
    fig.update_yaxes(showgrid=True, gridcolor='LightGray')

    # 保存为 HTML 文件
    print(f"📊 正在生成可视化图表...")
    fig.write_html(HTML_OUTPUT)
    print(f"✅ 可视化完成！请在浏览器中打开: {HTML_OUTPUT}")

if __name__ == "__main__":
    visualize()
