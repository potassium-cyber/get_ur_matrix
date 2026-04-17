import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import load_data_with_ts, get_indicator_cols

def view_compare(major_config, selected_major):
    """
    统计与对比视图
    """
    st.markdown(f"## 📈 {selected_major}专业 版本对比")
    
    # Check versions
    available_versions = list(major_config["versions"].keys())
    if len(available_versions) < 2:
        st.warning(f"⚠️ {selected_major}专业目前仅有 {available_versions[0]}，暂无法进行版本对比。")
        return
    
    major_dir = major_config["dir"]
    
    # Get old and new versions
    version_keys = sorted(available_versions)
    old_ver, new_ver = version_keys[0], version_keys[-1]
    old_config = major_config["versions"][old_ver]
    new_config = major_config["versions"][new_ver]
    
    df_old = load_data_with_ts(major_dir, old_config["csv"])
    df_new = load_data_with_ts(major_dir, new_config["csv"])
    
    if df_old is None or df_new is None:
        st.error("无法进行对比：数据文件缺失。")
        return

    # --- 1. KPIs ---
    def get_stats(dataframe):
        meta_cols = [c for c in dataframe.columns if c in ['课程名称', '课程编码']]
        m = dataframe.melt(id_vars=meta_cols, var_name='ind', value_name='val')
        m = m[m['val'].notna() & (m['val'] != "")]
        return len(dataframe), len(get_indicator_cols(dataframe)), len(m)

    c_old, i_old, r_old = get_stats(df_old)
    c_new, i_new, r_new = get_stats(df_new)
    
    # Display Metrics with custom styling
    st.markdown("### 📊 核心指标变化")
    k1, k2, k3 = st.columns(3)
    k1.metric("课程总数", f"{c_new}", f"{c_new - c_old} vs {old_ver}")
    k2.metric("指标点总数", f"{i_new}", f"{i_new - i_old} vs {old_ver}")
    k3.metric("支撑关系总数", f"{r_new}", f"{r_new - r_old} vs {old_ver}")

    st.divider()

    # --- 2. 课程变动分析 ---
    st.markdown("### 🔄 课程与指标变动明细")
    
    set_old = set(df_old['课程名称'].unique())
    set_new = set(df_new['课程名称'].unique())
    
    added_courses = sorted(list(set_new - set_old))
    removed_courses = sorted(list(set_old - set_new))
    common_courses = set_old & set_new
    
    # Calculate changes
    changed_courses = []
    for course in common_courses:
        row_old = df_old[df_old['课程名称'] == course].iloc[0]
        row_new = df_new[df_new['课程名称'] == course].iloc[0]
        
        inds_old = get_indicator_cols(df_old)
        inds_new = get_indicator_cols(df_new)

        d_old = {k: row_old[k] for k in inds_old if pd.notna(row_old[k]) and str(row_old[k]).strip() != ""}
        d_new = {k: row_new[k] for k in inds_new if pd.notna(row_new[k]) and str(row_new[k]).strip() != ""}
        
        if d_old != d_new:
            tags = []
            keys_old, keys_new = set(d_old.keys()), set(d_new.keys())
            
            if keys_old != keys_new:
                tags.append("指标增减")
            
            common_keys = keys_old & keys_new
            if any(d_old[k] != d_new[k] for k in common_keys):
                tags.append("强度调整")
            
            tag_label = " + ".join(tags)
            changed_courses.append(f"{course} ({tag_label})")
    
    changed_courses.sort()

    # Display lists
    col_added, col_removed, col_changed = st.columns(3)
    
    with col_added:
        st.success(f"**➕ 新开课程 ({len(added_courses)})**")
        if added_courses:
            with st.expander("查看详情"):
                for c in added_courses: st.write(f"- {c}")
                
    with col_removed:
        st.error(f"**➖ 移除课程 ({len(removed_courses)})**")
        if removed_courses:
            with st.expander("查看详情"):
                for c in removed_courses: st.write(f"- {c}")
                
    with col_changed:
        st.warning(f"**⚡️ 变动课程 ({len(changed_courses)})**")
        if changed_courses:
            with st.expander("查看详情"):
                for c in changed_courses: st.write(f"- {c}")

    # --- 3. Charts & Comparison ---
    st.divider()
    
    tab_cov, tab_dist, tab_single = st.tabs(["📊 指标覆盖度", "🎨 强度分布", "🔍 单课对比"])
    
    with tab_cov:
        def get_coverage(dataframe, label):
            meta_cols = [c for c in dataframe.columns if c in ['课程名称', '课程编码']]
            m = dataframe.melt(id_vars=meta_cols, var_name='指标点', value_name='val')
            m = m[m['val'].notna() & (m['val'] != "")]
            counts = m['指标点'].value_counts().reset_index()
            counts.columns = ['指标点', '支撑课程数']
            counts['版本'] = label
            return counts

        cov_old = get_coverage(df_old, old_ver)
        cov_new = get_coverage(df_new, new_ver)
        all_cov = pd.concat([cov_old, cov_new])
        
        fig_cov = px.bar(
            all_cov, x='指标点', y='支撑课程数', color='版本',
            barmode='group',
            color_discrete_map={old_ver: '#94a3b8', new_ver: '#0ea5e9'}
        )
        st.plotly_chart(fig_cov, use_container_width=True)
        
    with tab_dist:
        def get_dist(dataframe, label):
            meta_cols = [c for c in dataframe.columns if c in ['课程名称', '课程编码']]
            m = dataframe.melt(id_vars=meta_cols, var_name='ind', value_name='强度')
            counts = m['强度'].value_counts().reset_index()
            counts.columns = ['强度', '数量']
            counts = counts[counts['强度'].isin(['H', 'M', 'L'])]
            counts['版本'] = label
            return counts

        dist_old = get_dist(df_old, old_ver)
        dist_new = get_dist(df_new, new_ver)
        all_dist = pd.concat([dist_old, dist_new])
        
        fig_dist = px.bar(
            all_dist, x='强度', y='数量', color='版本',
            barmode='group',
            text_auto=True,
            color_discrete_map={old_ver: '#94a3b8', new_ver: '#0ea5e9'}
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    with tab_single:
        st.markdown("### ⚔️ 单课跨版对比")
        all_courses = sorted(list(set(df_old['课程名称'].dropna()) | set(df_new['课程名称'].dropna())))
        
        target_course = st.selectbox("选择课程:", options=all_courses, index=0, key="compare_course_select")
        
        if target_course:
            # Get Codes
            c_old_code = '-'
            if target_course in df_old['课程名称'].values:
                c_old_code = df_old[df_old['课程名称'] == target_course].iloc[0].get('课程编码', '-')
            
            c_new_code = '-'
            if target_course in df_new['课程名称'].values:
                c_new_code = df_new[df_new['课程名称'] == target_course].iloc[0].get('课程编码', '-')
            
            st.info(f"🔢 课程代码: **{old_ver} [{c_old_code}]**  →  **{new_ver} [{c_new_code}]**")

            # Get Support Data
            def get_course_support(dataframe, course_name):
                if course_name not in dataframe['课程名称'].values: return {}
                row = dataframe[dataframe['课程名称'] == course_name].iloc[0]
                indicator_cols = get_indicator_cols(dataframe)
                return {k: v for k, v in row[indicator_cols].items() if pd.notna(v) and str(v).strip() != ""}

            s_old = get_course_support(df_old, target_course)
            s_new = get_course_support(df_new, target_course)

            all_inds = sorted(list(set(s_old.keys()) | set(s_new.keys())))
            comparison_data = []
            for ind in all_inds:
                v_old, v_new = s_old.get(ind, ""), s_new.get(ind, "")
                status = "⏹️ 保持" if v_old == v_new else ("❌ 移除" if v_old and not v_new else ("🆕 新增" if not v_old and v_new else "🔄 变更"))
                comparison_data.append({"指标点": ind, old_ver: v_old, new_ver: v_new, "状态": status})
            
            if comparison_data:
                comp_df = pd.DataFrame(comparison_data)
                
                # Style check
                def style_change(row):
                    css = ''
                    if "新增" in row['状态']: css = 'color: #198754; font-weight: bold'
                    elif "移除" in row['状态']: css = 'color: #dc3545; font-weight: bold'
                    elif "变更" in row['状态']: css = 'color: #fd7e14; font-weight: bold'
                    return [css] * len(row)
                
                st.dataframe(
                    comp_df.style.apply(style_change, axis=1), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("该课程在两个版本中均无指标点支撑数据。")


    # --- 4. Export ---
    st.markdown("### 📥 数据导出")

    
    def convert_to_long_format(dataframe):
        ind_cols = get_indicator_cols(dataframe)
        long_df = dataframe.melt(
            id_vars=['课程名称'], 
            value_vars=ind_cols, 
            var_name='指标点', 
            value_name='支撑强度'
        )
        return long_df[long_df['支撑强度'].notna() & (long_df['支撑强度'].str.strip() != "")]

    c1, c2 = st.columns(2)
    with c1:
        st.caption(f"{old_ver} 数据")
        long_old = convert_to_long_format(df_old)
        st.download_button(
            "下载 CSV", 
            long_old.to_csv(index=False).encode('utf-8-sig'), 
            f"matrix_{old_ver}.csv",
            mime='text/csv',
            key='dl_old_full'
        )
    with c2:
        st.caption(f"{new_ver} 数据")
        long_new = convert_to_long_format(df_new)
        st.download_button(
            "下载 CSV", 
            long_new.to_csv(index=False).encode('utf-8-sig'), 
            f"matrix_{new_ver}.csv",
            mime='text/csv',
            key='dl_new_full'
        )
