import streamlit as st
import pandas as pd
import os
import yaml
import plotly.express as px
import plotly.graph_objects as go

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="课程关联矩阵速查",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 隐藏底部页脚、顶部装饰条
hide_st_style = """
            <style>
            footer {visibility: hidden;}
            .stDecoration {display:none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# 定义数据目录 (使用绝对路径，适应云端部署)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

VERSIONS = {
    "2023版": {"csv": "matrix_2023.csv", "yaml": "2023_program.yaml"},
    "2019版": {"csv": "matrix_2019.csv", "yaml": "2019_program.yaml"}
}

# --- 2. 数据加载函数 (带缓存) ---
@st.cache_data
def load_data(file_name, timestamp):
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        return None
    
    try:
        # 读取CSV，自动处理 utf-8-sig (BOM) 和空行
        df = pd.read_csv(file_path, encoding='utf-8-sig', skip_blank_lines=True, dtype={'课程编码': str})
        
        # 数据清洗：去除表头和内容的空格
        df.columns = df.columns.str.strip()
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        
        # 填充缺失的课程编码
        if '课程编码' in df.columns:
            df['课程编码'] = df['课程编码'].fillna('')

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

def get_indicator_cols(dataframe):
    """获取所有指标点列（排除元数据列）"""
    return [c for c in dataframe.columns if c not in ['课程名称', '课程编码']]

# --- 3. 侧边栏导航 ---
st.sidebar.title("🛠️ 版本选择")
selected_version = st.sidebar.selectbox(
    "请选择矩阵版本:",
    options=list(VERSIONS.keys()),
    index=0
)

# 加载当前选中的数据
current_config = VERSIONS[selected_version]
_f_path = os.path.join(DATA_DIR, current_config["csv"])
_ts = os.path.getmtime(_f_path) if os.path.exists(_f_path) else 0
df = load_data(current_config["csv"], _ts)
indicators_map = load_indicators_map(current_config["yaml"])

st.sidebar.title("🔍 查询模式")
if "mode" not in st.session_state:
    st.session_state.mode = "📚 课程反查 (查指标)"

mode = st.sidebar.radio(
    "请选择功能:",
    ["📚 课程反查 (查指标)", "📌 指标反查 (查课程)", "📊 统计与对比", "👀 单课跨版对比", "🔍 全表浏览"],
    key="mode"
)

st.sidebar.markdown("---")
if df is not None:
    st.sidebar.success(f"📊 {selected_version} 数据已加载\n\n共 **{len(df)}** 门课程\n**{len(get_indicator_cols(df))}** 个指标点")
else:
    st.sidebar.warning(f"⚠️ {selected_version} 数据未找到")

# --- 4. 主界面逻辑 ---
st.title(f"🎓 科学教育专业 - 毕业要求关联矩阵")

if df is None:
    st.warning(f"未找到数据文件")
    st.stop()

# === 模式 A: 课程查指标 ===
if mode == "📚 课程反查 (查指标)":
    st.header(f"📘 课程 -> 毕业要求 ({selected_version})")
    st.caption("查看特定课程支撑了哪些毕业要求指标点，并获取详细描述。")
    
    # 搜索框 (支持多选)
    selected_courses = st.multiselect(
        "请选择课程 (支持关键词搜索):",
        options=df['课程名称'].unique(),
        placeholder="例如：输入'创新'..."
    )
    
    if selected_courses:
        for course in selected_courses:
            # 提取该课程的一行
            row = df[df['课程名称'] == course].iloc[0]
            code = row.get('课程编码', '')
            title = f"📖 {course} ({code})" if code else f"📖 {course}"

            with st.expander(title, expanded=True):
                # 筛选出有支撑强度的列
                supported = []
                for col in get_indicator_cols(df):
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
                    res_df = pd.DataFrame(supported)
                    def color_coding(val):
                        if val == 'H': return 'color: #d9534f; font-weight: bold'
                        elif val == 'M': return 'color: #f0ad4e; font-weight: bold'
                        elif val == 'L': return 'color: #5bc0de; font-weight: bold'
                        return '' 

                    st.dataframe(
                        res_df.style.applymap(color_coding, subset=['支撑强度']),
                        use_container_width=True,
                        hide_index=True,
                        column_config={"指标点描述": st.column_config.TextColumn(width="large")}
                    )

                    csv = res_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label=f"📥 下载【{course}】指标点详情",
                        data=csv,
                        file_name=f"{course}_{selected_version}.csv",
                        mime='text/csv',
                    )
                else:
                    st.info("该课程暂无关联指标点。")

# === 模式 B: 指标查课程 ===
elif mode == "📌 指标反查 (查课程)":
    st.header(f"🎯 毕业要求 -> 支撑课程 ({selected_version})")
    st.caption("查看某个指标点由哪些课程来支撑。")
    
    indicators = get_indicator_cols(df)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_ind = st.selectbox("选择指标点:", indicators)
        ind_desc = indicators_map.get(selected_ind, "暂无描述")
        st.info(f"**指标点 {selected_ind} 含义**:\n\n{ind_desc}")
    
    if selected_ind:
        filtered = df[df[selected_ind].notna() & (df[selected_ind] != "" ) ]
        with col2:
            if not filtered.empty:
                counts = filtered[selected_ind].value_counts()
                fig = px.pie(
                    values=counts.values, names=counts.index, 
                    title=f"指标点 {selected_ind} 支撑强度分布",
                    color=counts.index,
                    color_discrete_map={'H':'#d9534f', 'M':'#f0ad4e', 'L':'#5bc0de'},
                    hole=0.4
                )
                fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)

        st.divider()
        if not filtered.empty:
            st.success(f"✅ 指标点 **{selected_ind}** 由以下 **{len(filtered)}** 门课程支撑:")
            
            cols = ['课程名称', selected_ind]
            if '课程编码' in filtered.columns:
                cols.insert(0, '课程编码')
            
            display_df = filtered[cols].copy()
            # Rename columns
            rename_map = {selected_ind: '支撑强度'}
            display_df.rename(columns=rename_map, inplace=True)
            
            display_df['Rank'] = display_df['支撑强度'].map({'H': 0, 'M': 1, 'L': 2})
            display_df = display_df.sort_values('Rank').drop(columns=['Rank'])
            
            st.dataframe(display_df, hide_index=True, use_container_width=True)
        else:
            st.warning(f"⚠️ 目前没有课程支撑指标点 {selected_ind}")

# === 模式 C: 数据统计与对比 (增强版) ===
elif mode == "📊 统计与对比":
    st.header("📈 2023版对比2019版人才培养方案")
    
    # 加载两个版本数据
    def load_with_ts(fname):
        fp = os.path.join(DATA_DIR, fname)
        ts = os.path.getmtime(fp) if os.path.exists(fp) else 0
        return load_data(fname, ts)

    df19 = load_with_ts("matrix_2019.csv")
    df23 = load_with_ts("matrix_2023.csv")
    
    if df19 is None or df23 is None:
        st.error("无法进行对比：缺少 2019 或 2023 版数据文件。")
        st.stop()

    # --- 1. 核心指标对比 (KPIs) ---
    def get_stats(dataframe):
        meta_cols = [c for c in dataframe.columns if c in ['课程名称', '课程编码']]
        m = dataframe.melt(id_vars=meta_cols, var_name='ind', value_name='val')
        m = m[m['val'].notna() & (m['val'] != "")]
        return len(dataframe), len(get_indicator_cols(dataframe)), len(m)

    c19_n, i19_n, r19_n = get_stats(df19)
    c23_n, i23_n, r23_n = get_stats(df23)

    k1, k2, k3 = st.columns(3)
    k1.metric("课程总数", f"{c23_n}", f"{c23_n - c19_n} vs 2019")
    k2.metric("指标点总数", f"{i23_n}", f"{i23_n - i19_n} vs 2019")
    k3.metric("支撑关系总数", f"{r23_n}", f"{r23_n - r19_n} vs 2019")

    st.divider()

    # --- 2. 课程变动分析 ---
    st.subheader("🔄 课程变动明细")
    set19 = set(df19['课程名称'].unique())
    set23 = set(df23['课程名称'].unique())
    
    added_courses = sorted(list(set23 - set19))
    removed_courses = sorted(list(set19 - set23))
    common_courses = set19 & set23
    
    # 计算有多少公共课程的指标发生了变化
    changed_courses = []
    for course in common_courses:
        row19 = df19[df19['课程名称'] == course].iloc[0]
        row23 = df23[df23['课程名称'] == course].iloc[0]
        
        inds19 = get_indicator_cols(df19)
        inds23 = get_indicator_cols(df23)

        # 简化比较：转为 dict 后比较
        d19 = {k: row19[k] for k in inds19 if pd.notna(row19[k]) and str(row19[k]).strip() != ""}
        d23 = {k: row23[k] for k in inds23 if pd.notna(row23[k]) and str(row23[k]).strip() != ""}
        
        if d19 != d23:
            tags = []
            keys19, keys23 = set(d19.keys()), set(d23.keys())
            
            # 判断类型1: 指标点集合是否有变 (增减)
            if keys19 != keys23:
                tags.append("指标增减")
            
            # 判断类型2: 公共指标点的强度是否有变
            common_keys = keys19 & keys23
            if any(d19[k] != d23[k] for k in common_keys):
                tags.append("强度调整")
            
            tag_label = " + ".join(tags)
            changed_courses.append(f"{course} (`{tag_label}`)")
    
    changed_courses.sort()

    m1, m2, m3 = st.columns(3)
    with m1:
        st.info(f"🆕 **新开课程 ({len(added_courses)})**")
        with st.expander("点击查看详情"):
            for c in added_courses: st.write(f"- {c}")
        st.caption("指2019版中不存在，2023版中新增加的课程。")
    with m2:
        st.warning(f"❌ **已停开/移除 ({len(removed_courses)})**")
        with st.expander("点击查看详情"):
            for c in removed_courses: st.write(f"- {c}")
        st.caption("指2019版中存在，2023版中已停开或移除的课程。")
    # 定义回调函数，用于跳转
    def jump_to_comparison(c_name):
        st.session_state.mode = "👀 单课跨版对比"
        st.session_state.target_course_list = [c_name]

    with m3:
        st.success(f"🔄 **指标点变动 ({len(changed_courses)})**")
        with st.expander("点击查看详情"):
            for item in changed_courses:
                # item format: "CourseName (`Tags`)"
                c_name = item.split(" (`")[0]
                c_col1, c_col2 = st.columns([0.75, 0.25])
                c_col1.markdown(f"- {item}")
                c_col2.button(
                    "对比", 
                    key=f"jump_{c_name}", 
                    help=f"跳转至 {c_name} 对比页面",
                    on_click=jump_to_comparison,
                    args=(c_name,)
                )
        st.caption("指课程名称相同，但支撑的指标点或强度发生了变化。")

    st.divider()

    # --- 3. 指标点覆盖度热度对比 (条状图) ---
    st.subheader("📊 指标点覆盖度对比 (2019 vs 2023)")
    
    def get_coverage(dataframe, label):
        meta_cols = [c for c in dataframe.columns if c in ['课程名称', '课程编码']]
        m = dataframe.melt(id_vars=meta_cols, var_name='指标点', value_name='val')
        m = m[m['val'].notna() & (m['val'] != "")]
        counts = m['指标点'].value_counts().reset_index()
        counts.columns = ['指标点', '支撑课程数']
        counts['版本'] = label
        return counts

    cov19 = get_coverage(df19, "2019版")
    cov23 = get_coverage(df23, "2023版")
    all_cov = pd.concat([cov19, cov23])
    
    fig_cov = px.bar(
        all_cov, x='指标点', y='支撑课程数', color='版本',
        barmode='group',
        title="各指标点支撑课程数量对比",
        color_discrete_map={'2019版': '#95a5a6', '2023版': '#3498db'}
    )
    fig_cov.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_cov, use_container_width=True)

    # --- 4. 支撑强度全局分布对比 ---
    st.subheader("🎨 支撑强度分布对比")
    def get_dist(dataframe, label):
        meta_cols = [c for c in dataframe.columns if c in ['课程名称', '课程编码']]
        m = dataframe.melt(id_vars=meta_cols, var_name='ind', value_name='强度')
        counts = m['强度'].value_counts().reset_index()
        counts.columns = ['强度', '数量']
        counts = counts[counts['强度'].isin(['H', 'M', 'L'])]
        counts['版本'] = label
        return counts

    dist19 = get_dist(df19, "2019版")
    dist23 = get_dist(df23, "2023版")
    all_dist = pd.concat([dist19, dist23])
    
    fig_dist = px.bar(
        all_dist, x='强度', y='数量', color='版本',
        barmode='group',
        text_auto=True,
        color_discrete_map={'2019版': '#bdc3c7', '2023版': '#e67e22'}
    )
    st.plotly_chart(fig_dist, use_container_width=True)

# === 模式 D: 单课跨版对比 ===
elif mode == "👀 单课跨版对比":
    st.header("⚔️ 课程支撑度跨版本对比")
    
    def load_with_ts(fname):
        fp = os.path.join(DATA_DIR, fname)
        ts = os.path.getmtime(fp) if os.path.exists(fp) else 0
        return load_data(fname, ts)

    df19 = load_with_ts("matrix_2019.csv")
    df23 = load_with_ts("matrix_2023.csv")

    if df19 is None or df23 is None:
        st.error("数据文件不全。")
    else:
        all_courses = sorted(list(set(df19['课程名称'].dropna()) | set(df23['课程名称'].dropna())))
        
        # 确保 session_state 初始化，防止报错
        if "target_course_list" not in st.session_state:
            st.session_state.target_course_list = []

        search_res = st.multiselect(
            "🔍 选择课程:", 
            options=all_courses, 
            max_selections=1, 
            key="target_course_list"
        )
        target_course = search_res[0] if search_res else None

        if target_course:
            # 获取课程代码
            c19 = '-'
            if target_course in df19['课程名称'].values:
                c19 = df19[df19['课程名称'] == target_course].iloc[0].get('课程编码', '-')
            
            c23 = '-'
            if target_course in df23['课程名称'].values:
                c23 = df23[df23['课程名称'] == target_course].iloc[0].get('课程编码', '-')
            
            st.info(f"🔢 课程代码: **2019版 [{c19}]**  →  **2023版 [{c23}]**")

            def get_course_support(dataframe, course_name):
                if course_name not in dataframe['课程名称'].values: return {}
                row = dataframe[dataframe['课程名称'] == course_name].iloc[0]
                # Filter only indicator columns
                indicator_cols = get_indicator_cols(dataframe)
                return {k: v for k, v in row[indicator_cols].items() if pd.notna(v) and str(v).strip() != ""}

            s19 = get_course_support(df19, target_course)
            s23 = get_course_support(df23, target_course)

            all_inds = sorted(list(set(s19.keys()) | set(s23.keys())))
            comparison_data = []
            for ind in all_inds:
                v19, v23 = s19.get(ind, ""), s23.get(ind, "")
                status = "⏹️ 保持" if v19 == v23 else ("❌ 移除" if v19 and not v23 else ("🆕 新增" if not v19 and v23 else "🔄 变更"))
                comparison_data.append({"指标点": ind, "2019版": v19, "2023版": v23, "状态": status})
            
            if comparison_data:
                comp_df = pd.DataFrame(comparison_data)
                def style_change(row):
                    css = ''
                    if "新增" in row['状态']: css = 'color: #198754; font-weight: bold'
                    elif "移除" in row['状态']: css = 'color: #dc3545; font-weight: bold'
                    elif "变更" in row['状态']: css = 'color: #fd7e14; font-weight: bold'
                    return [css] * len(row)
                st.dataframe(comp_df.style.apply(style_change, axis=1), use_container_width=True, hide_index=True)
            else:
                st.info("无对比数据。")

# === 模式 E: 全表浏览 ===
elif mode == "🔍 全表浏览":
    st.header(f"📋 完整关联矩阵 ({selected_version})")
    st.dataframe(df, use_container_width=True, height=700)