# SciEdu Matrix Explorer: Streamlit Web App Guide

这是一个基于 **Streamlit** 的 Web 应用项目方案，旨在将《课程与毕业要求关联矩阵》的可视化与查询功能从命令行迁移到浏览器，打造一个全院教师皆可零门槛使用的查询平台。

## 1. 项目愿景
打造一个**零门槛**的数据查询平台，教师只需通过下拉菜单或搜索框，即可实时查看课程对毕业要求的支撑情况，或反向查询指标点的课程覆盖度。

## 2. 技术栈
- **核心框架**: [Streamlit](https://streamlit.io/) (极速构建数据应用)
- **数据处理**: [Pandas](https://pandas.pydata.org/) (高效处理 CSV 表格)
- **数据源**: `课程与毕业要求关联矩阵.csv`

## 3. 项目结构建议
建议在新的工作目录下（例如 `SciEdu_Matrix_Web`）创建如下结构：

```text
sciedu_matrix_app/
├── .streamlit/
│   └── config.toml      # (可选) 界面主题配置
├── data/
│   └── matrix.csv       # 【重要】将原来的 csv 文件复制到这里并重命名为 matrix.csv
├── app.py               # 主应用程序 (代码见下文)
├── requirements.txt     # 依赖列表
└── README.md            # 项目说明
```

## 4. 核心代码 (`app.py`)
(核心代码保持原有结构，建议参考实际项目文件中的最新版本 `SciEdu_Matrix_App/app.py`)

## 5. 依赖配置 (`requirements.txt`)

```text
streamlit
pandas
openpyxl
requests
```

## 6. 部署与运行

> **注意**: 在此项目中，请始终使用 `python` 命令而非 `python3`。

1.  **准备环境**:
    在终端中运行：
    ```bash
    mkdir SciEdu_Matrix_App
    cd SciEdu_Matrix_App
    mkdir data
    # (此时将 matrix.csv 放入 data 目录)
    ```

2.  **创建文件**:
    将 `app.py` 和 `requirements.txt` 内容写入对应文件。

3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **启动应用**:
    ```bash
    streamlit run app.py
    ```

5.  **开始使用**:
    系统会自动打开浏览器（通常是 `http://localhost:8501`），您将看到一个美观的现代化交互界面。

## 7. 进阶功能展望
- **统计图表**: 添加饼图展示“强支撑(H)”课程的比例。
- **导出报告**: 一键生成某门课程的达成度分析报告 (PDF)。
- **多版本对比**: 比较 2019 版和 2023 版矩阵的差异。

## 8. 未来优化路线图 (Roadmap)
以下功能已规划但暂缓实施，可视项目发展情况择机启动：

### A. 架构重构 (模块化)
随着 `app.py` 规模增长，建议进行模块拆分以提升可维护性：
- `logic.py`: 封装核心计算逻辑（如达成度聚合算法）。
- `ai.py`: 封装 LLM 调用与 Prompt 管理。
- `exporter.py`: 封装 Excel 样式与导出逻辑。
- `ui_components.py`: 封装侧边栏、图表组件等 UI 元素。

### B. 健壮性增强 (Robustness)
针对 Excel 数据上传模块增强校验：
- **模糊列名匹配**: 兼容用户上传的“得分”、“分数”等非标准列名。
- **数据强清洗**: 自动处理百分号、空格等非数值字符。
- **友好报错**: 提供具体的错误引导而非通用异常信息。

### C. 测试策略 (Testing Strategy)
鉴于项目性质为内部工具，全量的 UI 测试（E2E）成本较高，暂不建议引入。但建议针对**核心计算逻辑**引入单元测试：
- **Pytest**: 编写针对 `run_aggregation` 等数学计算函数的单元测试，确保达成度计算公式的准确性（这对教学评估至关重要）。
- **Type Hints**: 在核心函数中添加 Python 类型提示，辅助 IDE 检查和代码理解。