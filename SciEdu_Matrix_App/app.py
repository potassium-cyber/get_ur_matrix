import streamlit as st
import pandas as pd
import os
import yaml

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="课程关联矩阵速查",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 定义数据目录
DATA_DIR = "data"
VERSIONS = {
    "2023版": {"csv": "matrix_2023.csv", "yaml": "2023_program.yaml"},
    "2019版": {"csv": "matrix_2019.csv", "yaml": "2019_program.yaml"}
}

# --- 2. 数据加载函数 (带缓存) ---
@st.cache_data
def load_data(file_name):
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        return None
    
    try:
        # 读取CSV，自动处理 utf-8-sig (BOM) 和空行
        df = pd.read_csv(file_path, encoding='utf-8-sig', skip_blank_lines=True)
        
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

@st.cache_data
def load_indicators_map(yaml_file):
    """解析YAML文件，返回 {id: content} 的字典"""
    file_path = os.path.join(DATA_DIR, yaml_file)
    if not os.path.exists(file_path):
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        mapping = {}
        if 'graduation_requirements' in data:
            for req in data['graduation_requirements']:
                if 'indicators' in req:
                    for ind in req['indicators']:
                        # 兼容 id 为数字或字符串的情况
                        ind_id = str(ind.get('id', '')).strip()
                        mapping[ind_id] = ind.get('content', '')
        return mapping
    except Exception as e:
        st.error(f"指标定义加载失败: {e}")
        return {}

# --- 3. 侧边栏导航 ---
st.sidebar.title("🛠️ 版本选择")
selected_version = st.sidebar.selectbox(
    "请选择矩阵版本:",
    options=list(VERSIONS.keys()),
    index=0
)

# 加载选中的数据
current_config = VERSIONS[selected_version]
df = load_data(current_config["csv"])
indicators_map = load_indicators_map(current_config["yaml"])

st.sidebar.title("🔍 查询模式")
mode = st.sidebar.radio(
    "请选择功能:",
    ["课程反查 (查指标)", "指标反查 (查课程)", "全表浏览", "⚔️ 版本对比 (2019 vs 2023)"]
)

st.sidebar.markdown("---")
if df is not None:
    st.sidebar.success(f"📊 {selected_version} 数据已加载\n\n共 **{len(df)}** 门课程\n**{len(df.columns)-1}** 个指标点")
else:
    st.sidebar.warning(f"⚠️ {selected_version} 数据未找到\n\n请检查 `data/` 目录")

# --- 4. 主界面逻辑 ---
st.title(f"🎓 科学教育专业 - 毕业要求关联矩阵 ({selected_version})")

if df is None:
    st.warning(f"未找到数据文件")
    st.stop()

# === 模式 A: 课程查指标 ===
if mode == "课程反查 (查指标)":
    st.header("📘 课程 -> 毕业要求")
    st.caption("查看特定课程支撑了哪些毕业要求指标点，并获取详细描述。")
    
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
                supported = []
                for col in df.columns[1:]: # 跳过第一列'课程名称'
                    val = row[col]
                    if pd.notna(val) and str(val).strip() != "":
                        # 获取描述文本
                        desc = indicators_map.get(col, "（暂无描述）")
                        supported.append({
                            "指标点": col,
                            "支撑强度": val,
                            "指标点描述": desc
                        })
                
                if supported:
                    # 转为 DataFrame 展示
                    res_df = pd.DataFrame(supported)
                    
                    # 样式高亮
                    def color_coding(val):
                        color = 'black'
                        if val == 'H': color = '#d9534f' 
                        elif val == 'M': color = '#f0ad4e'
                        elif val == 'L': color = '#5bc0de'
                        return f'color: {color}; font-weight: bold'

                    # 显示表格
                    st.dataframe(
                        res_df.style.applymap(color_coding, subset=['支撑强度']),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "指标点描述": st.column_config.TextColumn(width="large")
                        }
                    )

                    # --- 下载按钮 ---
                    # 准备 CSV 数据
                    csv = res_df.to_csv(index=False).encode('utf-8-sig')
                    filename = f"{course}_指标点明细_{selected_version}.csv"
                    
                    st.download_button(
                        label=f"📥 下载【{course}】对应指标点详情 (CSV)",
                        data=csv,
                        file_name=filename,
                        mime='text/csv',
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
        filtered = df[df[selected_ind].notna() & (df[selected_ind] != "" ) ]
        
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

# === 模式 D: 版本对比 ===
elif mode == "⚔️ 版本对比 (2019 vs 2023)":
    st.header("⚔️ 课程支撑度跨版本对比")
    st.caption("对比同一门课程在 2019 版和 2023 版培养方案中的支撑变化。")

    # 1. 尝试加载两个版本的数据
    df19 = load_data("matrix_2019.csv")
    df23 = load_data("matrix_2023.csv")

    if df19 is None or df23 is None:
        st.error("❌ 无法进行对比：缺少数据文件。")
        st.info("请确保 `data/` 目录下同时存在 `matrix_2019.csv` 和 `matrix_2023.csv`。")
    else:
        # 2. 获取课程并集
        courses19 = set(df19['课程名称'].dropna())
        courses23 = set(df23['课程名称'].dropna())
        all_courses = sorted(list(courses19 | courses23))

        # 使用 multiselect 模拟搜索框体验 (比下拉菜单更方便搜索)
        search_res = st.multiselect(
            "🔍 搜索并选择课程 (支持关键词):", 
            options=all_courses,
            max_selections=1,
            placeholder="点击输入课程名称..."
        )
        
        target_course = search_res[0] if search_res else None

        if target_course:
            col_a, col_b = st.columns(2)
            
            # 获取数据辅助函数
            def get_course_support(dataframe, course_name):
                if course_name not in dataframe['课程名称'].values:
                    return {}
                row = dataframe[dataframe['课程名称'] == course_name].iloc[0]
                support = {}
                for col in dataframe.columns[1:]:
                    val = row[col]
                    if pd.notna(val) and str(val).strip() != "":
                        support[col] = str(val).strip()
                return support

            support19 = get_course_support(df19, target_course)
            support23 = get_course_support(df23, target_course)

            with col_a:
                st.subheader("2019 版支撑")
                if not support19:
                    st.warning("该版本无此课程")
                else:
                    st.dataframe(pd.DataFrame(list(support19.items()), columns=['指标点', '强度']), hide_index=True, use_container_width=True)

            with col_b:
                st.subheader("2023 版支撑")
                if not support23:
                    st.warning("该版本无此课程")
                else:
                    st.dataframe(pd.DataFrame(list(support23.items()), columns=['指标点', '强度']), hide_index=True, use_container_width=True)

            # 3. 智能分析变化 (仅当两版都有数据时)
            if support19 and support23:
                st.divider()
                st.subheader("📊 变化分析")
                
                # 简单逻辑：如果指标点名称包含相同的代码（如 1.1），则认为对应
                # 这里为了通用性，直接展示并集对比
                
                all_inds = sorted(list(set(support19.keys()) | set(support23.keys())))
                comparison_data = []
                
                for ind in all_inds:
                    v19 = support19.get(ind, "")
                    v23 = support23.get(ind, "")
                    
                    status = ""
                    if v19 == v23:
                        status = "⏹️ 保持"
                    elif v19 and not v23:
                        status = "❌ 移除"
                    elif not v19 and v23:
                        status = "🆕 新增"
                    else:
                        status = "🔄 变更"
                    
                    # 只有当发生变化，或者有值的时候才显示，避免全是空行
                    if v19 or v23:
                        comparison_data.append({
                            "指标点": ind,
                            "2019": v19,
                            "2023": v23,
                            "状态": status
                        })
                
                if comparison_data:
                    comp_df = pd.DataFrame(comparison_data)
                    
                    # 样式函数 (改为修改文字颜色，避免背景刺眼)
                    def style_change(row):
                        css = ''
                        if "新增" in row['状态']: css = 'color: #198754; font-weight: bold' # Green
                        elif "移除" in row['状态']: css = 'color: #dc3545; font-weight: bold' # Red
                        elif "变更" in row['状态']: css = 'color: #fd7e14; font-weight: bold' # Orange
                        return [css] * len(row)

                    st.dataframe(comp_df.style.apply(style_change, axis=1), use_container_width=True, hide_index=True)
                else:
                    st.info("该课程在两个版本中的支撑情况完全一致。")
