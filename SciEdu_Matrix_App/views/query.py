import streamlit as st
import pandas as pd
import plotly.express as px

def get_indicator_cols(dataframe):
    """获取所有指标点列（排除元数据列）"""
    return [c for c in dataframe.columns if c not in ['课程名称', '课程编码']]

def view_query(df, selected_version, indicators_map):
    """
    查询视图：包含“课程查指标”和“指标查课程”
    """
    st.markdown("## 🔎 数据关联查询")
    
    tab1, tab2 = st.tabs(["📚 课程查指标", "📌 指标查课程"])
    
    # --- Tab 1: 课程查指标 ---
    with tab1:
        st.markdown(f"### 📘 课程 -> 毕业要求 ({selected_version})")
        st.caption("查看特定课程支撑了哪些毕业要求指标点，并获取详细描述。")
        
        # Search Box
        selected_courses = st.multiselect(
            "请选择课程 (支持关键词搜索):",
            options=df['课程名称'].unique(),
            placeholder="例如：输入'创新'...",
            key="query_course_multiselect"
        )
        
        if selected_courses:
            for course in selected_courses:
                # Extract course details
                row = df[df['课程名称'] == course].iloc[0]
                code = row.get('课程编码', '')
                title_str = f"{course} ({code})" if code else f"{course}"

                with st.expander(f"📖 {title_str}", expanded=True):
                    # Filter supported indicators
                    supported = []
                    for col in get_indicator_cols(df):
                        val = row[col]
                        if pd.notna(val) and str(val).strip() != "":
                            desc = indicators_map.get(col, "（暂无描述）")
                            supported.append({
                                "指标点": col,
                                "支撑强度": val,
                                "指标点描述": desc
                            })
                    
                    if supported:
                        res_df = pd.DataFrame(supported)
                        
                        # Use Column Config for better visuals
                        st.dataframe(
                            res_df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "指标点": st.column_config.TextColumn("指标点", width="small"),
                                "支撑强度": st.column_config.Column(
                                    "支撑强度",
                                    width="small",
                                    help="H=强, M=中, L=弱"
                                ),
                                "指标点描述": st.column_config.TextColumn("描述", width="large")
                            }
                        )
                        
                        # Download button
                        csv = res_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label=f"📥 下载【{course}】数据",
                            data=csv,
                            file_name=f"{course}_{selected_version}.csv",
                            mime='text/csv',
                            key=f"dl_{course}"
                        )
                    else:
                        st.info("该课程暂无关联指标点。")
                        
    # --- Tab 2: 指标查课程 ---
    with tab2:
        st.markdown(f"### 🎯 毕业要求 -> 支撑课程 ({selected_version})")
        st.caption("查看某个指标点由哪些课程来支撑。")
        
        indicators = get_indicator_cols(df)
        col1, col2 = st.columns([1, 2])
        
        with col1:
            selected_ind = st.selectbox("选择指标点:", indicators, key="query_ind_selectbox")
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
                    fig.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"⚠️ 目前没有课程支撑指标点 {selected_ind}")

            if not filtered.empty:
                st.divider()
                st.markdown(f"#### ✅ 支撑课程列表 ({len(filtered)} 门)")
                
                cols = ['课程名称', selected_ind]
                if '课程编码' in filtered.columns:
                    cols.insert(0, '课程编码')
                
                display_df = filtered[cols].copy()
                display_df.rename(columns={selected_ind: '支撑强度'}, inplace=True)
                
                # Sort by strength H > M > L
                display_df['Rank'] = display_df['支撑强度'].map({'H': 0, 'M': 1, 'L': 2})
                display_df = display_df.sort_values('Rank').drop(columns=['Rank'])
                
                st.dataframe(
                    display_df, 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "支撑强度": st.column_config.Column(
                            "强度",
                            width="small"
                        )
                    }
                )
