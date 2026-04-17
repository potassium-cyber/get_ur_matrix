import streamlit as st
import pandas as pd
import os
import yaml

# --- Configuration ---
# Define data directory (Use absolute path for cloud compatibility)
# Assuming this file is in SciEdu_Matrix_App/utils/
# So we go up two levels to get to SciEdu_Matrix_App/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Multi-major configuration
MAJORS = {
    "科学教育": {
        "dir": "majors/sci_edu",
        "versions": {
            "2023版": {"csv": "matrix_2023.csv", "yaml": "2023_program.yaml"},
            "2019版": {"csv": "matrix_2019.csv", "yaml": "2019_program.yaml"}
        }
    },
    "物理学": {
        "dir": "majors/physics",
        "versions": {
            "2019版": {"csv": "matrix_2019.csv", "yaml": "2019_program.yaml"}
        }
    }
}

# --- Helper Functions ---

def get_indicator_cols(dataframe):
    """Get all indicator columns (excluding metadata columns)"""
    return [c for c in dataframe.columns if c not in ['课程名称', '课程编码']]

@st.cache_data
def load_data(major_dir, file_name, timestamp):
    """Load CSV matrix data, supporting multi-major paths"""
    # Priority: majors/ directory
    file_path = os.path.join(DATA_DIR, major_dir, file_name)
    
    # Fallback: data/ root directory
    if not os.path.exists(file_path):
        file_path = os.path.join(DATA_DIR, file_name)
    
    if not os.path.exists(file_path):
        return None
    
    try:
        # Read CSV, handle BOM and blank lines
        df = pd.read_csv(file_path, encoding='utf-8-sig', skip_blank_lines=True, dtype={'课程编码': str})
        
        # Data cleaning
        df.columns = df.columns.str.strip()
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        
        # Fill missing codes
        if '课程编码' in df.columns:
            df['课程编码'] = df['课程编码'].fillna('')

        # Drop empty names
        if '课程名称' in df.columns:
            df = df.dropna(subset=['课程名称'])
            
        return df
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None

@st.cache_data
def load_program_data(major_dir, yaml_file):
    """Parse YAML file and return configuration data"""
    file_path = os.path.join(DATA_DIR, major_dir, yaml_file)
    
    if not os.path.exists(file_path):
        file_path = os.path.join(DATA_DIR, yaml_file)
    
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data
    except Exception as e:
        st.error(f"配置文件加载失败: {e}")
        return {}

def load_data_with_ts(major_dir, filename):
    """Helper to load data with timestamp checking (for cache invalidation)"""
    fp = os.path.join(DATA_DIR, major_dir, filename)
    if not os.path.exists(fp):
        fp = os.path.join(DATA_DIR, filename)
    ts = os.path.getmtime(fp) if os.path.exists(fp) else 0
    return load_data(major_dir, filename, ts)
