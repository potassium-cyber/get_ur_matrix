"""
utils/analysis.py — 达成度分析工具库

从 Achievement_Analysis/processing_scripts/ 中提取的纯函数。
无 argparse、无 sys.exit、无 CLI print。返回 DataFrame / Figure。

Pipeline: 上传 Excel → clean_score_data() → match_courses() → compute_hml_breakdown()
"""

import pandas as pd
import numpy as np
import re
import os
import difflib
import plotly.express as px
import plotly.graph_objects as go


# ============================================================
# 1. 文本标准化 (源自 smart_data_cleaner.py)
# ============================================================

FULLWIDTH_MAP = {
    '（': '(', '）': ')',
    '１': '1', '２': '2', '３': '3', '４': '4', '５': '5',
    '６': '6', '７': '7', '８': '8', '９': '9', '０': '0',
    '－': '-', '—': '-', '–': '-',
    '：': ':', '；': ';', '，': ',',
    'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV',
    'Ⅴ': 'V', 'Ⅵ': 'VI', 'Ⅶ': 'VII', 'Ⅷ': 'VIII',
}

ROMAN_MAP = [
    ('VIII', '8'), ('VII', '7'), ('VI', '6'),
    ('III', '3'), ('II', '2'), ('IV', '4'), ('V', '5'), ('I', '1'),
]


def normalize_text(text: str) -> str:
    """全角字符 → 半角 + 去首尾空格"""
    if not isinstance(text, str):
        return text
    for full, half in FULLWIDTH_MAP.items():
        text = text.replace(full, half)
    return text.strip()


def normalize_name(name: str) -> str:
    """课程名称标准化: 全角→半角, 罗马→阿拉伯, 去空格"""
    if pd.isna(name):
        return ""
    name = normalize_text(str(name))
    # 统一符号
    for old, new in [('--', '一'), ('—', '一')]:
        name = name.replace(old, new)
    # 罗马数字 → 阿拉伯 (按长度降序)
    for roman, digit in ROMAN_MAP:
        name = name.replace(roman, digit)
    return name


def get_base_name(name: str) -> str:
    """
    提取课程基础名 (用于模糊匹配)
    '形势与政策III' → '形势与政策'
    '普通物理实验I(力热)' → '普通物理实验'
    """
    name = normalize_text(str(name))
    for roman, digit in ROMAN_MAP:
        name = name.replace(roman, digit)
    if name.startswith('C语言'):
        return 'C语言程序设计'
    if '之—' in name or '之--' in name:
        name = name.split('之')[0]
    name = re.sub(r'\([^)]*\)$', '', name).strip()
    name = re.sub(r'\d+$', '', name).strip()
    return name


# ============================================================
# 2. 智能清洗 (源自 smart_data_cleaner.py)
# ============================================================

def detect_columns(df: pd.DataFrame) -> dict:
    """
    智能检测列名，返回 {'code': col|None, 'name': col|None, 'score': col|None, 'achievement': col|None}
    """
    result = {'code': None, 'name': None, 'score': None, 'achievement': None}

    for candidate in ['课程代码', '课程编码', '课程号', 'course_code']:
        if candidate in df.columns:
            result['code'] = candidate
            break

    for candidate in ['课程名称', '课程名', 'course_name']:
        if candidate in df.columns:
            result['name'] = candidate
            break

    for candidate in ['达成度', 'achievement']:
        if candidate in df.columns:
            result['achievement'] = candidate
            break

    if result['achievement'] is None:
        for candidate in ['平均分', '平均成绩', 'average_score', '均分']:
            if candidate in df.columns:
                result['score'] = candidate
                break

    return result


def clean_score_data(df: pd.DataFrame) -> tuple:
    """
    清洗原始成绩 Excel DataFrame。

    Returns:
        (cleaned_df, report_dict)
        cleaned_df: 标准格式 DataFrame (课程代码, 课程名称, 达成度)
        report_dict: 清洗报告 (修正数、检测列、异常值等)
    """
    report = {}

    # Step 1: 全角→半角
    text_cols = df.select_dtypes(include=['object']).columns
    changes_count = 0
    for col in text_cols:
        original = df[col].copy()
        df[col] = df[col].apply(lambda x: normalize_text(x) if isinstance(x, str) else x)
        changes_count += (original != df[col]).sum()
    report['fullwidth_fixes'] = int(changes_count)

    # Step 2: 列名检测
    cols = detect_columns(df)
    report['detected_columns'] = cols

    if cols['name'] is None:
        report['error'] = '未找到课程名称列'
        return pd.DataFrame(), report

    # Step 3: 计算达成度
    if cols['achievement']:
        df['达成度'] = pd.to_numeric(df[cols['achievement']], errors='coerce')
        report['score_source'] = f"直接使用 '{cols['achievement']}' 列"
    elif cols['score']:
        df['达成度'] = pd.to_numeric(df[cols['score']], errors='coerce') / 100
        report['score_source'] = f"由 '{cols['score']}' 列计算 (÷100)"
    else:
        report['error'] = '未找到分数或达成度列'
        return pd.DataFrame(), report

    # Step 4: 课程代码处理
    if cols['code']:
        df['课程代码'] = df[cols['code']].astype(str).str.strip()
        df['课程代码'] = df['课程代码'].apply(
            lambda x: x.zfill(8) if x.replace('.0', '').isdigit() and len(x.replace('.0', '')) < 8 else x
        )
    else:
        df['课程代码'] = ''

    # 构造结果
    result = df[['课程代码', cols['name'], '达成度']].copy()
    result = result.rename(columns={cols['name']: '课程名称'})
    result = result.dropna(subset=['达成度'])
    result = result[result['达成度'] > 0]

    # 数据质量统计
    report['total_courses'] = len(result)
    report['missing_codes'] = int((result['课程代码'].isin(['', 'nan'])).sum())
    report['abnormal_high'] = int((result['达成度'] > 1.0).sum())
    report['low_achievement'] = int((result['达成度'] < 0.6).sum())

    return result, report


# ============================================================
# 3. 课程匹配 (源自 process_data.py)
# ============================================================

def normalize_code(code) -> str:
    """标准化课程代码: 去空格, 去 .0"""
    if pd.isna(code):
        return ""
    return str(code).strip().split('.')[0]


def match_courses(score_df: pd.DataFrame, matrix_df: pd.DataFrame) -> tuple:
    """
    将清洗后的成绩数据与关联矩阵进行课程匹配。

    Args:
        score_df: 清洗后 (课程代码, 课程名称, 达成度)
        matrix_df: 关联矩阵 CSV (课程编码, 课程名称, 指标点列...)

    Returns:
        (match_log_df, calc_ready_df)
        match_log_df: 匹配日志 (每行: Matrix课程, 匹配类型, 匹配到的成绩数据)
        calc_ready_df: 计算用长表 (课程名称, 指标点, 支撑强度, 达成度)
    """
    # 预处理标准化
    score_df = score_df.copy()
    score_df['norm_code'] = score_df['课程代码'].apply(normalize_code)
    score_df['norm_name'] = score_df['课程名称'].apply(normalize_name)

    matrix_df = matrix_df.copy()
    if '课程编码' in matrix_df.columns:
        matrix_df['norm_code'] = matrix_df['课程编码'].apply(normalize_code)
    else:
        matrix_df['norm_code'] = ''
    matrix_df['norm_name'] = matrix_df['课程名称'].apply(normalize_name)

    # 构建查找字典
    score_by_code = score_df.drop_duplicates(subset=['norm_code'])
    score_by_name = score_df.drop_duplicates(subset=['norm_name'])

    map_code = score_by_code.set_index('norm_code')[['课程代码', '课程名称', '达成度']].to_dict('index')
    map_name = score_by_name.set_index('norm_name')[['课程代码', '课程名称', '达成度']].to_dict('index')

    # 执行匹配
    match_results = []
    valid_matches = {}  # {norm_code: 达成度}

    for _, row in matrix_df.iterrows():
        m_code = row['norm_code']
        m_name = row['norm_name']
        m_orig_name = row['课程名称']
        m_orig_code = row.get('课程编码', '')

        match_data = None
        match_type = "❌ 未匹配"

        # 1. 编码精确
        if m_code and m_code in map_code:
            match_data = map_code[m_code]
            match_type = "✅ 编码精确"
        # 2. 编码补零
        elif m_code and m_code.zfill(8) in map_code:
            match_data = map_code[m_code.zfill(8)]
            match_type = "✅ 编码补零"
        # 3. 名称精确
        elif m_name in map_name:
            match_data = map_name[m_name]
            match_type = "✅ 名称精确"
        # 4. 模糊匹配
        else:
            all_names = list(map_name.keys())
            close = difflib.get_close_matches(m_name, all_names, n=1, cutoff=0.7)
            if close:
                match_data = map_name[close[0]]
                match_type = f"🔶 模糊 ({close[0]})"

        if match_data:
            valid_matches[m_code] = match_data['达成度']

        match_results.append({
            '矩阵课程编码': m_orig_code,
            '矩阵课程名称': m_orig_name,
            '匹配方式': match_type,
            '成绩课程名称': match_data['课程名称'] if match_data else "",
            '达成度': match_data['达成度'] if match_data else "",
        })

    match_log_df = pd.DataFrame(match_results)

    # 生成计算用长表
    meta_cols = ['课程编码', '课程名称', 'norm_code', 'norm_name']
    existing_meta = [c for c in meta_cols if c in matrix_df.columns]
    indicator_cols = [c for c in matrix_df.columns if c not in meta_cols]

    df_long = matrix_df.melt(
        id_vars=['课程名称', 'norm_code'],
        value_vars=indicator_cols,
        var_name='指标点',
        value_name='支撑强度'
    )
    df_long = df_long.dropna(subset=['支撑强度'])
    df_long = df_long[df_long['支撑强度'].astype(str).str.strip() != '']

    # 填入达成度
    final_rows = []
    for _, row in df_long.iterrows():
        m_code = row['norm_code']
        if m_code in valid_matches:
            final_rows.append({
                '课程名称': row['课程名称'],
                '指标点': row['指标点'],
                '支撑强度': str(row['支撑强度']).strip().upper(),
                '达成度': float(valid_matches[m_code]),
            })

    calc_ready_df = pd.DataFrame(final_rows)
    if not calc_ready_df.empty:
        calc_ready_df['达成度'] = pd.to_numeric(calc_ready_df['达成度'], errors='coerce')
        calc_ready_df = calc_ready_df.sort_values(by=['指标点', '课程名称'])

    return match_log_df, calc_ready_df


# ============================================================
# 4. HML 分解分析 (源自 analyze_sub_indicators.py)
# ============================================================

def compute_hml_breakdown(calc_df: pd.DataFrame, weights: dict = None) -> tuple:
    """
    按指标点和 HML 分组统计达成度。

    Args:
        calc_df: 计算用长表 (课程名称, 指标点, 支撑强度, 达成度)
        weights: HML 权重字典, 如 {'H': 0.7, 'M': 0.25, 'L': 0.05}。None 时使用默认值。

    Returns:
        (stats_df, pivot_df)
        stats_df: 详细统计 (指标点, 支撑强度, 平均达成度, 标准差, 课程门数)
        pivot_df: 透视表 (H/M/L 列 + 分解达成度 + 毕业要求达成度)
    """
    if weights is None:
        weights = {'H': 0.7, 'M': 0.25, 'L': 0.05}

    df = calc_df.copy()
    df['支撑强度'] = df['支撑强度'].astype(str).str.strip().str.upper()
    df['达成度'] = pd.to_numeric(df['达成度'], errors='coerce')

    # 分组统计
    stats = df.groupby(['指标点', '支撑强度'])['达成度'].agg(
        ['mean', 'std', 'count']
    ).reset_index()
    stats.columns = ['指标点', '支撑强度', '平均达成度', '标准差', '课程门数']

    # 透视表
    pivot = stats.pivot(index='指标点', columns='支撑强度', values='平均达成度')

    # 加权达成度
    def weighted_score(row):
        score_sum, weight_sum = 0, 0
        for col in ['H', 'M', 'L']:
            if col in row.index and pd.notna(row[col]):
                score_sum += row[col] * weights[col]
                weight_sum += weights[col]
        return score_sum / weight_sum if weight_sum > 0 else 0

    pivot['分解指标点达成度'] = pivot.apply(weighted_score, axis=1)

    # 大指标 → 毕业要求达成度
    pivot['大指标'] = pivot.index.to_series().apply(
        lambda x: str(x).split('-')[0]
    )
    major_scores = pivot.groupby('大指标')['分解指标点达成度'].mean()
    pivot['毕业要求达成度'] = pivot['大指标'].map(major_scores)

    # 清理
    pivot = pivot.drop(columns=['大指标'])
    for col in ['H', 'M', 'L']:
        if col not in pivot.columns:
            pivot[col] = pd.NA

    cols = ['H', 'M', 'L', '分解指标点达成度', '毕业要求达成度']
    pivot = pivot[[c for c in cols if c in pivot.columns]]

    return stats, pivot


def build_indicator_course_list(calc_df: pd.DataFrame, program_data: dict = None) -> pd.DataFrame:
    """
    生成“毕业要求 / 指标点 / HML 课程列表”明细表。

    Args:
        calc_df: 计算用长表 (课程名称, 指标点, 支撑强度, 达成度)
        program_data: 培养方案 YAML 解析结果，用于补充毕业要求和指标点名称

    Returns:
        DataFrame:
            毕业要求ID | 毕业要求名称 | 毕业要求显示名 | 指标点ID | 指标点名称
            | H课程列表 | M课程列表 | L课程列表 | 课程汇总显示
    """
    required_cols = {'课程名称', '指标点', '支撑强度'}
    if calc_df is None or calc_df.empty or not required_cols.issubset(calc_df.columns):
        return pd.DataFrame(columns=[
            '毕业要求ID', '毕业要求名称', '毕业要求显示名', '指标点ID', '指标点名称',
            'H课程列表', 'M课程列表', 'L课程列表', '课程汇总显示'
        ])

    requirement_name_map = {}
    indicator_title_map = {}
    requirement_order = []
    indicator_order = []

    if isinstance(program_data, dict):
        for req in program_data.get('graduation_requirements', []):
            req_id = str(req.get('id', '')).strip()
            req_name = str(req.get('name', '')).strip()
            if req_id:
                requirement_name_map[req_id] = req_name
                requirement_order.append(req_id)

            for ind in req.get('indicators', []):
                ind_id = str(ind.get('id', '')).strip()
                ind_title = str(ind.get('title', '')).strip()
                if ind_id:
                    indicator_title_map[ind_id] = ind_title
                    indicator_order.append(ind_id)

    df = calc_df[['课程名称', '指标点', '支撑强度']].copy()
    df['课程名称'] = df['课程名称'].astype(str).str.strip()
    df['指标点'] = df['指标点'].astype(str).str.strip()
    df['支撑强度'] = df['支撑强度'].astype(str).str.strip().str.upper()
    df = df[df['课程名称'] != '']
    df = df[df['指标点'] != '']
    df = df[df['支撑强度'].isin(['H', 'M', 'L'])]

    grouped = (
        df.groupby(['指标点', '支撑强度'])['课程名称']
        .apply(lambda s: '、'.join(sorted(pd.unique(s))))
        .reset_index(name='课程列表')
    )

    pivot = grouped.pivot(index='指标点', columns='支撑强度', values='课程列表').reset_index()
    for col in ['H', 'M', 'L']:
        if col not in pivot.columns:
            pivot[col] = ''

    pivot = pivot.rename(columns={
        '指标点': '指标点ID',
        'H': 'H课程列表',
        'M': 'M课程列表',
        'L': 'L课程列表',
    })

    pivot['毕业要求ID'] = pivot['指标点ID'].apply(lambda x: str(x).split('-')[0])
    pivot['毕业要求名称'] = pivot['毕业要求ID'].map(requirement_name_map).fillna('')
    pivot['毕业要求显示名'] = pivot.apply(
        lambda row: f"{row['毕业要求ID']} {row['毕业要求名称']}".strip()
        if row['毕业要求名称'] else row['毕业要求ID'],
        axis=1
    )
    pivot['指标点名称'] = pivot['指标点ID'].map(indicator_title_map).fillna('')

    for col, label in [('H课程列表', 'H'), ('M课程列表', 'M'), ('L课程列表', 'L')]:
        pivot[col] = pivot[col].fillna('').astype(str).str.strip()
        pivot[col] = pivot[col].replace('', '-')

    pivot['课程汇总显示'] = pivot.apply(
        lambda row: f"H: {row['H课程列表']} / M: {row['M课程列表']} / L: {row['L课程列表']}",
        axis=1
    )

    req_rank = {req_id: idx for idx, req_id in enumerate(requirement_order)}
    ind_rank = {ind_id: idx for idx, ind_id in enumerate(indicator_order)}

    def sort_requirement(req_id: str):
        if req_id in req_rank:
            return (0, req_rank[req_id])
        try:
            return (1, int(req_id))
        except (TypeError, ValueError):
            return (2, str(req_id))

    def sort_indicator(ind_id: str):
        if ind_id in ind_rank:
            return (0, ind_rank[ind_id])
        try:
            return (1, [int(part) for part in str(ind_id).split('-')])
        except (TypeError, ValueError):
            return (2, str(ind_id))

    pivot['_req_sort'] = pivot['毕业要求ID'].apply(sort_requirement)
    pivot['_ind_sort'] = pivot['指标点ID'].apply(sort_indicator)
    pivot = pivot.sort_values(by=['_req_sort', '_ind_sort']).drop(columns=['_req_sort', '_ind_sort'])

    return pivot[[
        '毕业要求ID', '毕业要求名称', '毕业要求显示名', '指标点ID', '指标点名称',
        'H课程列表', 'M课程列表', 'L课程列表', '课程汇总显示'
    ]]


# ============================================================
# 5. 可视化 (源自 visualize_hml.py)
# ============================================================

def create_hml_chart(stats_df: pd.DataFrame, threshold: float = 0.80) -> go.Figure:
    """
    创建 HML 分解达成度对比图 (Plotly)。

    Args:
        stats_df: 详细统计 DataFrame (指标点, 支撑强度, 平均达成度, 课程门数, 标准差)
        threshold: 达标红线

    Returns:
        Plotly Figure 对象
    """
    df = stats_df.copy()

    # 排序
    try:
        df['sort_key'] = df['指标点'].apply(
            lambda x: [int(i) for i in str(x).split('-')]
        )
        df = df.sort_values(by='sort_key').drop(columns=['sort_key'])
    except (ValueError, TypeError):
        df = df.sort_values(by='指标点')

    fig = px.bar(
        df,
        x="指标点",
        y="平均达成度",
        color="支撑强度",
        barmode="group",
        title="分解指标点 HML 达成度对比图",
        hover_data=["课程门数", "标准差"],
        color_discrete_map={'H': '#003366', 'M': '#336699', 'L': '#99CCFF'},
        labels={'平均达成度': '达成度均值', '指标点': '分解指标点'}
    )

    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text=f"达标线 {threshold}"
    )

    fig.update_layout(
        yaxis_range=[0.4, 1.05],
        xaxis_title="分解指标点",
        yaxis_title="达成度均值",
        legend_title="支撑强度",
        # plot_bgcolor='white',  <-- Removed to allow transparency
        font=dict(
            family="Inter, sans-serif",
            size=12,
            # color=... rely on default template for auto-text color
        ),
        xaxis_tickangle=-45,
    )
    # Use standard grid color or let theme handle it. Streamlit theme usually handles this.
    # fig.update_yaxes(showgrid=True, gridcolor='LightGray') # Optional: can keep if 'LightGray' is visible on dark
    fig.update_yaxes(showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)') # More subtle grid


    return fig


def create_graduation_achievement_chart(
    pivot_df: pd.DataFrame, threshold: float = 0.80
) -> go.Figure:
    """
    创建毕业要求达成度柱状图 (按大指标)。
    """
    # 提取毕业要求达成度 (每个大指标只保留一行)
    df = pivot_df.copy()
    df['大指标'] = df.index.to_series().apply(lambda x: str(x).split('-')[0])
    grad_df = df.groupby('大指标')['毕业要求达成度'].first().reset_index()

    # 排序
    try:
        grad_df['sort'] = grad_df['大指标'].astype(int)
        grad_df = grad_df.sort_values('sort').drop(columns=['sort'])
    except (ValueError, TypeError):
        grad_df = grad_df.sort_values('大指标')

    # 颜色: 低于阈值红色，高于阈值蓝色
    grad_df['颜色'] = grad_df['毕业要求达成度'].apply(
        lambda x: '#dc3545' if x < threshold else '#1f77b4'
    )

    fig = px.bar(
        grad_df,
        x='大指标',
        y='毕业要求达成度',
        text_auto='.3f',
        title="各毕业要求达成度总览",
        color='颜色',
        color_discrete_map='identity',
    )

    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text=f"达标线 {threshold}"
    )

    fig.update_layout(
        yaxis_range=[0, 1.1],
        showlegend=False,
        xaxis_title="毕业要求",
        yaxis_title="达成度",
        # plot_bgcolor='white', <-- Removed
        font=dict(
             family="Inter, sans-serif",
        )
    )
    fig.update_yaxes(showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)')


    return fig
