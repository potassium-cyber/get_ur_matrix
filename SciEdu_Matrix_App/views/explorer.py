import streamlit as st

def view_explorer(df, selected_version):
    """
    全表浏览视图
    """
    st.markdown(f"## 📋 完整关联矩阵 ({selected_version})")
    
    # Add +1 to index for display
    df_display = df.copy()
    df_display.index = df_display.index + 1
    
    # Use Container Width
    st.dataframe(
        df_display, 
        use_container_width=True, 
        height=700
    )
