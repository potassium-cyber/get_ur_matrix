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

# --- DEBUG INFO START (临时调试) ---
try:
    parent_dir = os.path.dirname(BASE_DIR) # get_ur_matrix root
    central_dir = os.path.join(parent_dir, "central_data")
    
    debug_msg = f"""
    **🔍 Debugging Path Info:**
    - Base Dir: `{BASE_DIR}`
    - Parent Dir: `{parent_dir}`
    - Central Dir Expected: `{central_dir}`
    
    **📂 Directory Listing (Parent):**
    `{os.listdir(parent_dir)}`
    """
    
    if os.path.exists(central_dir):
        debug_msg += f"\n**📂 Directory Listing (Central Data):**\n`{os.listdir(central_dir)}`"
        matrices_dir = os.path.join(central_dir, "matrices")
        if os.path.exists(matrices_dir):
             debug_msg += f"\n**📂 Directory Listing (Matrices):**\n`{os.listdir(matrices_dir)}`"
    else:
        debug_msg += "\n❌ **Central Data directory NOT FOUND!**"
        
    st.info(debug_msg)
except Exception as e:
    st.error(f"Debug Error: {e}")
# --- DEBUG INFO END ---

VERSIONS = {
    "2023版": {"csv": "matrix_2023.csv", "yaml": "2023_program.yaml"},
    "2019版": {"csv": "matrix_2019.csv", "yaml": "2019_program.yaml"}
}

# --- 2. 数据加载函数 (带缓存) ---
@st.cache_data
def load_data(file_name, timestamp):
    # 优先尝试默认路径 (可能是软链接)
    file_path = os.path.join(DATA_DIR, file_name)
    
    # 备用路径逻辑：如果默认路径不存在或不可读，尝试直接去 submodule 找
    if not os.path.exists(file_path):
        # 假设 csv 文件都在 matrices 目录下
        alt_path = os.path.join(BASE_DIR, "..", "central_data", "matrices", file_name)
        if os.path.exists(alt_path):
            file_path = alt_path
        else:
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

def get_indicator_cols(dataframe):
    """获取所有指标点列（排除元数据列）"""
    return [c for c in dataframe.columns if c not in ['课程名称', '课程编码']]

@st.cache_data
def load_program_data(yaml_file):
    """解析YAML文件，返回完整配置数据"""
    file_path = os.path.join(DATA_DIR, yaml_file)
    
    # 备用路径逻辑
    if not os.path.exists(file_path):
        # 假设 yaml 文件都在 programs 目录下
        alt_path = os.path.join(BASE_DIR, "..", "central_data", "programs", yaml_file)
        if os.path.exists(alt_path):
            file_path = alt_path
        else:
            return {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data
    except Exception as e:
        st.error(f"配置文件加载失败: {e}")
        return {}

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

# 加载指标定义和培养目标
program_data = load_program_data(current_config["yaml"])
indicators_map = {}
if 'graduation_requirements' in program_data:
    for req in program_data['graduation_requirements']:
        if 'indicators' in req:
            for ind in req['indicators']:
                ind_id = str(ind.get('id', '')).strip()
                indicators_map[ind_id] = ind.get('content', '')

st.sidebar.title("🍵 选择需要的功能")
if "mode" not in st.session_state:
    st.session_state.mode = "🎯 查看培养目标"

mode = st.sidebar.radio(
    "请选择功能:",
    ["🎯 查看培养目标", "📚 课程反查 (查指标)", "📌 指标反查 (查课程)", "📊 统计与对比", "👀 单课跨版对比", "🔍 全表浏览", "🧮 达成度计算 (测试版)"],
    key="mode",
    label_visibility="collapsed"
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

# === 模式 0: 查看培养目标 ===
if mode == "🎯 查看培养目标":
    st.header(f"🎯 专业培养目标 ({selected_version})")
    
    objectives = program_data.get('educational_objectives', "暂无培养目标描述。")
    formatted_obj = objectives.replace('\n', '<br>')
    
    with st.expander(f"✨ 点击展开查看【{selected_version}】完整描述", expanded=False):
        # 🎨 漂亮排版展示
        st.markdown(
            f"""
            <div style="
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                font-size: 16px;
                line-height: 1.8;
                color: #2c3e50;
                background-color: rgba(248, 249, 250, 0.7);
                padding: 20px;
                border-radius: 8px;
                border-left: 5px solid #4e8cff;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                margin-bottom: 20px;
            ">
                {formatted_obj}
            </div>
            """,
            unsafe_allow_html=True
        )
        
        with st.expander("🔗 复制原始内容", expanded=False):
                st.code(objectives, language=None)
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

    # --- 5. 数据导出 (按强度拆分) ---
    st.divider()
    st.subheader("📥 原始数据导出 (长表格式)")
    st.caption("导出格式：课程名称 | 指标点 | 支撑强度 (仅包含选中强度的行)")

    def convert_to_long_format(dataframe):
        # 1. 识别指标点列
        ind_cols = get_indicator_cols(dataframe)
        # 2. 逆透视 (Wide to Long)
        long_df = dataframe.melt(
            id_vars=['课程名称'], 
            value_vars=ind_cols, 
            var_name='指标点', 
            value_name='支撑强度'
        )
        # 3. 过滤无效数据
        long_df = long_df[long_df['支撑强度'].notna() & (long_df['支撑强度'].str.strip() != "")]
        return long_df

    ex_col1, ex_col2 = st.columns(2)

    with ex_col1:
        st.markdown("#### 2019版 导出")
        long19 = convert_to_long_format(df19)
        for strength in ['H', 'M', 'L']:
            subset = long19[long19['支撑强度'] == strength]
            if not subset.empty:
                csv_data = subset.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"⬇️ 下载 {strength} 强度表 (2019)",
                    data=csv_data,
                    file_name=f"matrix_2019_{strength}.csv",
                    mime='text/csv',
                    key=f"btn_2019_{strength}",
                    use_container_width=True
                )
            else:
                st.button(f"🚫 无 {strength} 强度数据", disabled=True, key=f"dis_2019_{strength}", use_container_width=True)

    with ex_col2:
        st.markdown("#### 2023版 导出")
        long23 = convert_to_long_format(df23)
        for strength in ['H', 'M', 'L']:
            subset = long23[long23['支撑强度'] == strength]
            if not subset.empty:
                csv_data = subset.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"⬇️ 下载 {strength} 强度表 (2023)",
                    data=csv_data,
                    file_name=f"matrix_2023_{strength}.csv",
                    mime='text/csv',
                    key=f"btn_2023_{strength}",
                    use_container_width=True
                )
            else:
                st.button(f"🚫 无 {strength} 强度数据", disabled=True, key=f"dis_2023_{strength}", use_container_width=True)

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

# === 模式 F: 达成度计算 (测试版) ===
elif mode == "🧮 达成度计算 (测试版)":
    st.header("🧮 毕业要求达成度计算")
    
    st.markdown("""
    本模块提供基于课程达成度的毕业要求达成情况分析。系统采用 **两级聚合算法**，并支持自定义权重。
    
    **💡 操作流程：**
    1. **下载模版**：获取当前版本（{0}）的预填充 Excel 关联表。
    2. **填报得分**：在 Excel 的 **`达成度`** 列中，为每门课程填入 0-1 之间的实测得分。
    3. **参数设置**：在下方设置权重及**达标红线**。
    4. **上传分析**：上传文件，系统将实时计算综合及分项达成度。
    """.format(selected_version))
    
    st.divider()

    # --- Step 1: 下载模版 ---
    st.subheader("1️⃣ 获取预填充模版")
    
    def get_template_data(version_df):
        ind_cols = get_indicator_cols(version_df)
        long_df = version_df.melt(
            id_vars=['课程名称'], 
            value_vars=ind_cols, 
            var_name='指标点', 
            value_name='支撑强度'
        )
        long_df = long_df[long_df['支撑强度'].notna() & (long_df['支撑强度'].str.strip() != "")]
        long_df = long_df.sort_values(by=['指标点', '课程名称'])
        long_df['达成度'] = None
        return long_df

    # 直接生成，不使用 status 框
    tpl_df = get_template_data(df)
    import io
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        tpl_df.to_excel(writer, index=False, sheet_name='达成度填报')
    excel_data = output.getvalue()
    
    st.download_button(
        label=f"📥 点击下载【{selected_version}】预填充填报模版",
        data=excel_data,
        file_name=f"achievement_template_{selected_version}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        help="模版已包含所有课程与指标点的对应关系，您只需填写达成度数值。"
    )

    st.divider()

    # --- Step 2: 上传并分析 ---
    st.subheader("2️⃣ 上传计算与可视化")
    
    # === 权重与预警设置区域 ===
    with st.expander("⚙️ 计算参数与预警设置", expanded=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("**权重分配 (影响综合达成度)**")
            w_col1, w_col2, w_col3 = st.columns(3)
            w_h = w_col1.number_input("H (强) 权重", min_value=0.1, value=1.0, step=0.1, format="%.1f")
            w_m = w_col2.number_input("M (中) 权重", min_value=0.1, value=0.8, step=0.1, format="%.1f")
            w_l = w_col3.number_input("L (弱) 权重", min_value=0.1, value=0.6, step=0.1, format="%.1f")
        with c2:
            st.markdown("**质量预警红线**")
            threshold = st.slider("达成度达标阈值", 0.0, 1.0, 0.70, 0.05, help="低于此数值的达成度将被红色标记。")
        
        weight_map = {'H': w_h, 'M': w_m, 'L': w_l}

    uploaded_file = st.file_uploader("请上传填写好“达成度”列的 Excel 文件", type=["xlsx", "xls"])
    
    if uploaded_file:
        try:
            # 读取上传的文件
            input_df = pd.read_excel(uploaded_file)
            
            # 基础列校验
            if '达成度' not in input_df.columns or '指标点' not in input_df.columns:
                st.error("⚠️ 识别失败：上传的文件缺少“达成度”或“指标点”列。请务必使用上方生成的模版。")
                st.stop()
            
            # 数据清洗：移除达成度为空的行，并确保其为数值
            calc_df = input_df.dropna(subset=['达成度']).copy()
            calc_df['达成度'] = pd.to_numeric(calc_df['达成度'], errors='coerce')
            
            # 【修复】强力清洗支撑强度列，防止因空格导致筛选失败
            if '支撑强度' in calc_df.columns:
                calc_df['支撑强度'] = calc_df['支撑强度'].astype(str).str.strip().str.upper()
            
            calc_df = calc_df.dropna(subset=['达成度'])
            
            if calc_df.empty:
                st.warning("⚠️ 未检测到任何有效的达成度数据。请确保在“达成度”列中填入了数字。")
            else:
                # 提取大指标点逻辑
                import re
                def get_major(val):
                    m = re.match(r'^(\d+)', str(val).strip())
                    return m.group(1) if m else "其他"
                
                calc_df['大指标'] = calc_df['指标点'].apply(get_major)
                
                # 为每一行分配权重
                calc_df['权重'] = calc_df['支撑强度'].map(weight_map).fillna(1.0)
                
                # --- 核心计算函数 (升级为加权平均) ---
                def run_aggregation(data_subset, use_weight=False):
                    if data_subset.empty: return pd.DataFrame(columns=['大指标', 'score'])
                    
                    if use_weight:
                        # 定义加权平均函数
                        def weighted_avg(x):
                            # x 是一个组 (Group)，包含 '达成度' 和 '权重'
                            v = x['达成度']
                            w = x['权重']
                            if w.sum() == 0: return 0
                            return (v * w).sum() / w.sum()

                        # 1. 细分指标加权平均 (同一 1-1 下不同课程)
                        # 注意：这里需要先把权重带上
                        # GroupBy apply 比较慢，但逻辑清晰
                        sub_avg = data_subset.groupby(['大指标', '指标点']).apply(weighted_avg).reset_index(name='val')
                        
                        # 2. 大指标简单平均 (1-1, 1-2 之间通常视为等权重，或者也可以加权，这里暂按等权)
                        # 如果需要大指标也加权，需要知道每个细分指标的权重，通常细分指标间是平等的
                        major_avg = sub_avg.groupby('大指标')['val'].mean().reset_index()
                        major_avg.columns = ['大指标', 'score']
                        return major_avg
                    else:
                        # 算术平均 (旧逻辑，用于分项统计)
                        sub_avg = data_subset.groupby(['大指标', '指标点'])['达成度'].mean().reset_index()
                        major_avg = sub_avg.groupby('大指标')['达成度'].mean().reset_index()
                        major_avg.columns = ['大指标', 'score']
                        return major_avg

                # 执行多维度计算
                # 综合达成度：开启加权
                total_res = run_aggregation(calc_df, use_weight=True).rename(columns={'score': '综合达成度'})
                
                # 分项达成度：内部权重一致，用算术平均即可
                h_res = run_aggregation(calc_df[calc_df['支撑强度']=='H'], use_weight=False).rename(columns={'score': 'H(强支撑)'})
                m_res = run_aggregation(calc_df[calc_df['支撑强度']=='M'], use_weight=False).rename(columns={'score': 'M(中支撑)'})
                l_res = run_aggregation(calc_df[calc_df['支撑强度']=='L'], use_weight=False).rename(columns={'score': 'L(弱支撑)'})

                # 合并表格
                final_df = total_res
                for other in [h_res, m_res, l_res]:
                    final_df = pd.merge(final_df, other, on='大指标', how='outer')
                
                # 排序
                try:
                    final_df['sort'] = final_df['大指标'].astype(int)
                    final_df = final_df.sort_values('sort').drop(columns=['sort'])
                except:
                    final_df = final_df.sort_values('大指标')

                num_courses = calc_df['课程名称'].nunique()
                num_records = len(calc_df)
                st.success(f"✅ 计算完成！共处理 **{num_courses}** 门课程和 **{num_records}** 条分解指标点。权重：H={w_h:.1f}, M={w_m:.1f}, L={w_l:.1f}")

                # 表格样式优化：红线预警
                numeric_cols = ['综合达成度', 'H(强支撑)', 'M(中支撑)', 'L(弱支撑)']
                cols_to_fmt = [c for c in numeric_cols if c in final_df.columns]
                
                def color_warning(val):
                    if pd.isna(val) or not isinstance(val, (int, float)): return ''
                    color = '#f8d7da' if val < threshold else '' # 浅红色背景
                    text_color = '#721c24' if val < threshold else '' # 深红色文字
                    return f'background-color: {color}; color: {text_color}'

                st.dataframe(
                    final_df.style.format("{:.3f}", subset=cols_to_fmt, na_rep="-")
                            .applymap(color_warning, subset=cols_to_fmt),
                    use_container_width=True, hide_index=True
                )
                
                # 达标总结
                low_reqs = final_df[final_df['综合达成度'] < threshold]['大指标'].tolist()
                if low_reqs:
                    st.warning(f"🚨 **预警**: 毕业要求 **{', '.join(low_reqs)}** 的综合达成度未达到红线 ({threshold:.2f})，建议重点关注。")
                else:
                    st.success(f"🎊 **优异**: 所有毕业要求均已达标 (>{threshold:.2f})！")

                # === 可视化升级 ===
                st.subheader("📊 达成度可视化分析")
                
                tab1, tab2 = st.tabs(["📊 分组柱状图 (对比)", "🌡️ 热力图 (分布)"])
                
                # 准备绘图数据 (Long Format)
                plot_df = final_df.melt(id_vars=['大指标'], value_vars=cols_to_fmt, var_name='维度', value_name='达成度')
                plot_df = plot_df.dropna() # 去掉空值以免绘图报错
                
                with tab1:
                    fig_bar = px.bar(
                        plot_df, x='大指标', y='达成度', color='维度',
                        barmode='group',
                        text_auto='.3f',
                        title="各毕业要求达成度多维对比",
                        color_discrete_map={
                            '综合达成度': '#1f77b4', 
                            'H(强支撑)': '#d62728',
                            'M(中支撑)': '#ff7f0e', 
                            'L(弱支撑)': '#2ca02c'
                        }
                    )
                    fig_bar.add_hline(y=threshold, line_dash="dash", line_color="red", annotation_text=f"达标红线 {threshold}")
                    fig_bar.update_layout(yaxis_range=[0, 1.1])
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
                with tab2:
                    hm_data = final_df.set_index('大指标')[cols_to_fmt]
                    fig_hm = px.imshow(
                        hm_data.T,
                        text_auto='.3f',
                        aspect="auto",
                        color_continuous_scale="RdBu",
                        color_continuous_midpoint=threshold,
                        title="达成度热力分布图"
                    )
                    st.plotly_chart(fig_hm, use_container_width=True)

                # --- 专业导出 ---
                st.divider()
                st.subheader("📥 导出分析报告")
                
                output_report = io.BytesIO()
                with pd.ExcelWriter(output_report, engine='openpyxl') as writer:
                    # 分页1: 达成度结果
                    final_df.to_excel(writer, index=False, sheet_name='达成度汇总')
                    # 分页2: 计算参数存证 (Metadata)
                    metadata = pd.DataFrame({
                        "参数项": ["评估版本", "计算时间", "处理课程数", "支撑记录数", "达标阈值", "H权重", "M权重", "L权重"],
                        "取值": [selected_version, pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), num_courses, num_records, threshold, w_h, w_m, w_l]
                    })
                    metadata.to_excel(writer, index=False, sheet_name='计算参数存证')
                
                st.download_button(
                    label="📥 下载专业分析报告 (Excel)",
                    data=output_report.getvalue(),
                    file_name=f"Analysis_Report_{selected_version}_{pd.Timestamp.now().strftime('%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )



        except Exception as e:
            st.error(f"处理文件时发生致命错误: {e}")
            st.info("请尝试重新下载模版并填报。")