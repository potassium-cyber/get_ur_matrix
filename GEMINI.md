# SciEdu Matrix Explorer: Streamlit Web App Guide

这是一个基于 **Streamlit** 的 Web 应用项目方案，旨在将《课程与毕业要求关联矩阵》的可视化与查询功能从命令行迁移到浏览器，打造一个全院教师皆可零门槛使用的查询平台。

## 1. 项目愿景
打造一个**零门槛**的数据查询平台，教师只需通过下拉菜单或搜索框，即可实时查看课程对毕业要求的支撑情况，或反向查询指标点的课程覆盖度。

## 2. 技术栈
- **核心框架**: [Streamlit](https://streamlit.io/) (极速构建数据应用)
- **数据处理**: [Pandas](https://pandas.pydata.org/) (高效处理 CSV 表格)
- **数据源**: `课程与毕业要求关联矩阵.csv`

## 3. 项目结构建议
建议在新的工作目录下（例如 `SciEdu_Matrix_Web`）创建如下结构：

```text
sciedu_matrix_app/
├── .streamlit/
│   └── config.toml      # (可选) 界面主题配置
├── data/
│   └── matrix.csv       # 【重要】将原来的 csv 文件复制到这里并重命名为 matrix.csv
├── app.py               # 主应用程序 (代码见下文)
├── requirements.txt     # 依赖列表
└── README.md            # 项目说明
```

## 4. 核心代码 (`app.py`)

你可以直接使用以下代码作为 `app.py` 的初始版本。它完美复刻并增强了 CLI 工具的功能，提供了更现代的交互体验。

```python
import streamlit as st
import pandas as pd
import os

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="课程关联矩阵速查",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 定义数据路径 (请确保文件在 data 目录下)
DATA_PATH = "data/matrix.csv"

# --- 2. 数据加载函数 (带缓存) ---
@st.cache_data
def load_data():
    if not os.path.exists(DATA_PATH):
        return None
    
    try:
        # 读取CSV，自动处理 utf-8-sig (BOM) 和空行
        df = pd.read_csv(DATA_PATH, encoding='utf-8-sig', skip_blank_lines=True)
        
        # 数据清洗：去除表头和内容的空格
        df.columns = df.columns.str.strip()
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        
        # 确保第一列是 '课程名称'，如果是空的（比如之前的空行问题），drop掉
        if '课程名称' in df.columns:
            df = df.dropna(subset=['课程名称'])
            
        return df
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None

df = load_data()

# --- 3. 侧边栏导航 ---
st.sidebar.title("🔍 查询模式")
mode = st.sidebar.radio(
    "请选择功能:",
    ["课程反查 (查指标)", "指标反查 (查课程)", "全表浏览"]
)

st.sidebar.markdown("---")
if df is not None:
    st.sidebar.success(f"📊 数据已加载\n\n共 **{len(df)}** 门课程\n**{len(df.columns)-1}** 个指标点")
else:
    st.sidebar.error("⚠️ 数据未加载")

# --- 4. 主界面逻辑 ---
st.title("🎓 科学教育专业 - 毕业要求关联矩阵")

if df is None:
    st.warning(f"请将数据文件放置于 `{DATA_PATH}`")
    st.stop()

# === 模式 A: 课程查指标 ===
if mode == "课程反查 (查指标)":
    st.header("📘 课程 -> 毕业要求")
    st.caption("查看特定课程支撑了哪些毕业要求指标点。")
    
    # 搜索框 (支持多选)
    selected_courses = st.multiselect(
        "请选择课程 (支持关键词搜索):",
        options=df['课程名称'].unique(),
        placeholder="例如：输入'创新'..."
    )
    
    if selected_courses:
        for course in selected_courses:
            with st.expander(f"📖 {course}", expanded=True):
                # 提取该课程的一行
                row = df[df['课程名称'] == course].iloc[0]
                
                # 筛选出有支撑强度的列
                supported = {}
                for col in df.columns[1:]: # 跳过第一列'课程名称'
                    val = row[col]
                    if pd.notna(val) and str(val).strip() != "":
                        supported[col] = val
                
                if supported:
                    # 转为 DataFrame 展示以便美化
                    res_df = pd.DataFrame(list(supported.items()), columns=['指标点', '支撑强度'])
                    
                    # 简单的样式高亮
                    def color_coding(val):
                        color = 'black'
                        if val == 'H': color = '#d9534f' # Red
                        elif val == 'M': color = '#f0ad4e' # Orange
                        elif val == 'L': color = '#5bc0de' # Blue
                        return f'color: {color}; font-weight: bold'

                    st.dataframe(
                        res_df.style.applymap(color_coding, subset=['支撑强度']),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("该课程暂无关联指标点。")

# === 模式 B: 指标查课程 ===
elif mode == "指标反查 (查课程)":
    st.header("🎯 毕业要求 -> 支撑课程")
    st.caption("查看某个指标点由哪些课程来支撑。")
    
    # 获取所有指标点列
    indicators = df.columns[1:].tolist()
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_ind = st.selectbox("选择指标点:", indicators)
    
    if selected_ind:
        # 筛选出该列不为空的行
        filtered = df[df[selected_ind].notna() & (df[selected_ind] != "") ]
        
        if not filtered.empty:
            st.success(f"✅ 指标点 **{selected_ind}** 由以下 **{len(filtered)}** 门课程支撑:")
            
            # 整理显示数据
            display_df = filtered[['课程名称', selected_ind]].copy()
            display_df.columns = ['课程名称', '支撑强度']
            
            # 自定义排序：H > M > L
            display_df['Rank'] = display_df['支撑强度'].map({'H': 0, 'M': 1, 'L': 2})
            display_df = display_df.sort_values('Rank').drop(columns=['Rank'])
            
            st.dataframe(
                display_df, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "课程名称": st.column_config.TextColumn(width="medium"),
                    "支撑强度": st.column_config.Column(width="small")
                }
            )
        else:
            st.warning(f"⚠️ 目前没有课程支撑指标点 {selected_ind}")

# === 模式 C: 全表浏览 ===
elif mode == "全表浏览":
    st.header("📋 完整关联矩阵")
    st.markdown("点击表头可排序，右上角可放大查看。" )
    st.dataframe(df, use_container_width=True, height=700)
```

## 5. 依赖配置 (`requirements.txt`)

```text
streamlit
pandas
openpyxl
```

## 6. 部署与运行

> **注意**: 在此项目中，请始终使用 `python` 命令而非 `python3`。

1.  **准备环境**:
    在终端中运行：
    ```bash
    mkdir SciEdu_Matrix_App
    cd SciEdu_Matrix_App
    mkdir data
    # (此时将 matrix.csv 放入 data 目录)
    ```

2.  **创建文件**:
    将上述 `app.py` 和 `requirements.txt` 内容写入对应文件。

3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **启动应用**:
    ```bash
    streamlit run app.py
    ```

5.  **开始使用**:
    系统会自动打开浏览器（通常是 `http://localhost:8501`），您将看到一个美观的现代化交互界面。

## 7. 进阶功能展望
- **统计图表**: 添加饼图展示“强支撑(H)”课程的比例。
- **导出报告**: 一键生成某门课程的达成度分析报告 (PDF)。
- **多版本对比**: 比较 2019 版和 2023 版矩阵的差异。
