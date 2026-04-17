import streamlit as st
import os

# Import modular views
from views.home import view_home
from views.query import view_query
from views.compare import view_compare
from views.explorer import view_explorer
from views.analysis import view_analysis

# Import utilities
from utils.data_loader import (
    get_data_update_info,
    load_data_with_ts, 
    load_program_data, 
    MAJORS, 
    DATA_DIR
)

# Streamlit only honors the sidebar's "initial" state. To reliably open it
# for a fresh session, cycle once through the opposite state, then rerun.
DEFAULT_SIDEBAR_STATE = "expanded"

if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "collapsed"
    st.session_state.sidebar_state_bootstrap = True

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="课程关联矩阵速查",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state
)

if st.session_state.get("sidebar_state_bootstrap"):
    st.session_state.sidebar_state = DEFAULT_SIDEBAR_STATE
    st.session_state.sidebar_state_bootstrap = False
    st.rerun()

# --- Maintenance Mode ---
# Keep an explicit hard-stop switch for emergency use, but do not block
# normal deployments based on the legacy MAINTENANCE_MODE flag.
if os.environ.get("FORCE_MAINTENANCE_MODE") == "1":
    st.warning("🚧 系统正在进行数据更新与逻辑维护，暂时关闭查询服务。由此带来的不便，敬请谅解。")
    st.info("预计恢复时间：待定。如需紧急查询，请联系管理员。")
    st.stop()

# --- 2. Load Custom CSS ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(css_path):
    local_css(css_path)

# --- 3. Sidebar Navigation ---
with st.sidebar:
    st.title("🎓 矩阵速查")
    
    # Major & Version Selection
    with st.expander("⚙️ 设置 (专业/版本)", expanded=True):
        selected_major = st.selectbox(
            "专业:",
            options=list(MAJORS.keys()),
            index=0
        )
        major_config = MAJORS[selected_major]

        selected_version = st.selectbox(
            "版本:",
            options=list(major_config["versions"].keys()),
            index=0
        )
    
    current_config = major_config["versions"][selected_version]
    major_dir = major_config["dir"]
    
    st.divider()
    
    # Function Navigation
    st.markdown("### 📍 功能导航")
    
    # Using a clearer radio button with icons
    NAV_OPTIONS = {
        "home": "🏠 培养目标",
        "query": "🔎 数据查询",
        "analysis": "🧮 达成度分析",
        "compare": "📈 版本对比",
        "explorer": "📋 全表浏览",
    }
    
    # Store session state for navigation if needed, but radio is simple enough
    selection = st.radio(
        "Navigation", 
        list(NAV_OPTIONS.keys()), 
        format_func=lambda x: NAV_OPTIONS[x],
        label_visibility="collapsed"
    )

    st.divider()
    
    # Load Data (Eager loading for statistics)
    df = load_data_with_ts(major_dir, current_config["csv"])
    data_update_info = get_data_update_info(major_dir, selected_version, current_config["csv"])
    
    if df is not None:
        status_lines = [
            f"✅ {selected_version} 数据已就绪",
            f"📚 **{len(df)}** 门课程",
        ]
        if data_update_info.get("updated_at"):
            status_lines.append(f"🕒 数据更新时间：`{data_update_info['updated_at']}`")
        if data_update_info.get("note"):
            status_lines.append(f"📝 {data_update_info['note']}")
        st.success("\n\n".join(status_lines))
    else:
        st.error(f"❌ 数据加载失败: {current_config['csv']}")

# --- 4. Main Content Routing ---

# Load Program Data (YAML) for Home & Descriptions
program_data = load_program_data(major_dir, current_config["yaml"])

# Extract indicators map for Query view
indicators_map = {}
if 'graduation_requirements' in program_data:
    for req in program_data['graduation_requirements']:
        if 'indicators' in req:
            for ind in req['indicators']:
                ind_id = str(ind.get('id', '')).strip()
                indicators_map[ind_id] = ind.get('content', '')

# Routing
if selection == "home":
    view_home(program_data, selected_version, selected_major)

elif selection == "query":
    if df is not None:
        view_query(df, selected_version, indicators_map)

elif selection == "analysis":
    view_analysis(df, selected_version, selected_major, program_data)

elif selection == "compare":
    view_compare(major_config, selected_major)

elif selection == "explorer":
    if df is not None:
        view_explorer(df, selected_version)
