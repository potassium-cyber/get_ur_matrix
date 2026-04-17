import streamlit as st
import pandas as pd

def view_home(program_data, selected_version, selected_major):
    """
    查看培养目标视图
    """
    st.markdown(f"## 🎯 {selected_major}专业培养目标 ({selected_version})")
    
    # Read training objectives
    training_obj = program_data.get('training_objectives', {})
    obj_desc = training_obj.get('description', '暂无培养目标描述。') if isinstance(training_obj, dict) else '暂无培养目标描述。'
    obj_goals = training_obj.get('goals', []) if isinstance(training_obj, dict) else []
    
    # Hero Section for Objective
    st.markdown(
        f"""
        <div class="training-hero">
            <h3>✨ 培养总目标</h3>
            <p>{obj_desc}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    
    # Goals List
    if obj_goals:
        st.markdown("### 📋 培养目标分条")
        for goal in obj_goals:
            goal_name = goal.get('name', '')
            goal_content = goal.get('content', '')
            goal_id = goal.get('id', '')
            
            with st.expander(f"**{goal_id}. {goal_name}**", expanded=False):
                st.info(goal_content)
    
    # Graduation Requirements
    st.divider()
    st.markdown("### 📜 毕业要求概览")
    
    grad_reqs = program_data.get('graduation_requirements', [])
    if grad_reqs:
        for idx, req in enumerate(grad_reqs):
            req_name = req.get('name', '')
            req_desc = req.get('description', '')
            req_id = req.get('id', '')
            indicators = req.get('indicators', [])
            
            # Using columns for a cleaner layout
            with st.container():
                st.markdown(f"#### {req_id}: {req_name}")
                st.markdown(f"> {req_desc}")
                
                if indicators:
                    with st.expander(f"查看 {len(indicators)} 个分解指标点"):
                        for ind in indicators:
                            ind_id = ind.get('id', '')
                            ind_title = ind.get('title', '')
                            ind_content = ind.get('content', '')
                            st.markdown(f"- **{ind_id} {ind_title}**：{ind_content}")
                st.divider()
