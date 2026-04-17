import argparse
import os
import sys

import pandas as pd
import yaml


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ACHIEVEMENT_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(ACHIEVEMENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from process_data import get_matrix_path  # noqa: E402
from SciEdu_Matrix_App.utils.analysis import compute_hml_breakdown, match_courses  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="查询指定指标点下的课程及平均达成度")
    parser.add_argument("--major", default="sci_edu", help="专业代码，如 sci_edu 或 physics")
    parser.add_argument("--year", default="2019", help="培养方案版本年份，如 2019")
    parser.add_argument("--indicator", required=True, help="指标点编号，如 3-1")
    parser.add_argument("--levels", default="H,M,L", help="支撑强度，逗号分隔，如 H,M")
    parser.add_argument("--input", default=None, help="成绩文件路径；不传则自动探测")
    parser.add_argument("--output", default=None, help="可选：导出结果到 .csv 或 .xlsx")
    return parser.parse_args()


def resolve_input_path(major: str, explicit_path: str = None) -> str:
    if explicit_path:
        return explicit_path

    candidates = [
        os.path.join(ACHIEVEMENT_DIR, major, "2021_course_achievement_final.csv"),
        os.path.join(ACHIEVEMENT_DIR, major, f"{major}_2021_course_achievement.csv"),
        os.path.join(ACHIEVEMENT_DIR, major, f"{major}_2021级物理学_cleaned.csv"),
        os.path.join(ACHIEVEMENT_DIR, "output", "2021_course_achievement_final.csv"),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        f"未找到可用成绩文件，请显式传入 --input。已尝试: {', '.join(candidates)}"
    )


def get_program_path(major: str, year: str) -> str | None:
    ssot_dir = os.environ.get(
        "SCIEDU_SSOT_DIR",
        os.path.join(os.path.dirname(PROJECT_ROOT), "SciEdu_Central_Data")
    )

    candidates = [
        os.path.join(ssot_dir, "majors", major, f"program_{year}.yaml"),
        os.path.join(PROJECT_ROOT, "SciEdu_Matrix_App", "data", "majors", major, f"{year}_program.yaml"),
        os.path.join(PROJECT_ROOT, "central_data", "programs", f"{year}_program.yaml"),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


def get_indicator_meta(major: str, year: str, indicator_id: str) -> dict:
    program_path = get_program_path(major, year)
    meta = {
        "requirement_id": indicator_id.split("-")[0],
        "requirement_name": "",
        "indicator_title": "",
    }

    if not program_path:
        return meta

    with open(program_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    for req in data.get("graduation_requirements", []):
        req_id = str(req.get("id", "")).strip()
        if req_id == meta["requirement_id"]:
            meta["requirement_name"] = str(req.get("name", "")).strip()

        for ind in req.get("indicators", []):
            ind_id = str(ind.get("id", "")).strip()
            if ind_id == indicator_id:
                meta["indicator_title"] = str(ind.get("title", "")).strip()
                if not meta["requirement_name"]:
                    meta["requirement_name"] = str(req.get("name", "")).strip()
                return meta

    return meta


def normalize_levels(levels_text: str) -> list[str]:
    levels = [part.strip().upper() for part in levels_text.split(",") if part.strip()]
    valid = [level for level in levels if level in {"H", "M", "L"}]
    if not valid:
        raise ValueError("`--levels` 至少需要包含一个有效值：H / M / L")
    return valid


def export_result(df: pd.DataFrame, summary_df: pd.DataFrame, output_path: str):
    if output_path.lower().endswith(".csv"):
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return

    if output_path.lower().endswith(".xlsx"):
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="课程明细", index=False)
            summary_df.to_excel(writer, sheet_name="分组均值", index=False)
        return

    raise ValueError("`--output` 仅支持 .csv 或 .xlsx")


def main():
    args = parse_args()
    levels = normalize_levels(args.levels)
    input_path = resolve_input_path(args.major, args.input)
    matrix_path = get_matrix_path(args.major, args.year)
    indicator_meta = get_indicator_meta(args.major, args.year, args.indicator)

    score_df = pd.read_csv(input_path, encoding="utf-8-sig")
    matrix_df = pd.read_csv(matrix_path, encoding="utf-8-sig", dtype={"课程编码": str})

    _, calc_ready = match_courses(score_df, matrix_df)

    result_df = calc_ready[
        (calc_ready["指标点"] == args.indicator) &
        (calc_ready["支撑强度"].isin(levels))
    ].copy()

    if result_df.empty:
        print("未查询到符合条件的数据。")
        print(f"指标点: {args.indicator}")
        print(f"支撑强度: {', '.join(levels)}")
        return

    result_df = result_df.sort_values(by=["支撑强度", "课程名称"]).reset_index(drop=True)

    _, hml_pivot = compute_hml_breakdown(calc_ready)
    indicator_achievement = None
    if args.indicator in hml_pivot.index:
        indicator_achievement = hml_pivot.loc[args.indicator, "分解指标点达成度"]

    result_df["核心课程（关联度）"] = result_df.apply(
        lambda row: f"{row['课程名称']}（{row['支撑强度']}）",
        axis=1
    )
    result_df["平均成绩"] = pd.to_numeric(result_df["达成度"], errors="coerce") * 100
    result_df["总成绩（默认100分）"] = 100
    result_df["课程达成度"] = pd.to_numeric(result_df["达成度"], errors="coerce")

    summary_df = (
        result_df.groupby("支撑强度", as_index=False)["课程达成度"]
        .mean()
        .rename(columns={"课程达成度": "平均达成度"})
    )

    req_display = indicator_meta["requirement_id"]
    if indicator_meta["requirement_name"]:
        req_display = f"{req_display} {indicator_meta['requirement_name']}"

    ind_display = args.indicator
    if indicator_meta["indicator_title"]:
        ind_display = f"{ind_display} {indicator_meta['indicator_title']}"

    result_df["毕业要求"] = req_display
    result_df["指标点"] = ind_display
    result_df["毕业要求指标点达成度"] = indicator_achievement

    result_df["平均成绩"] = result_df["平均成绩"].round(2)
    result_df["课程达成度"] = result_df["课程达成度"].round(4)
    if indicator_achievement is not None:
        result_df["毕业要求指标点达成度"] = result_df["毕业要求指标点达成度"].round(6)

    result_df = result_df[
        [
            "毕业要求",
            "指标点",
            "核心课程（关联度）",
            "平均成绩",
            "总成绩（默认100分）",
            "课程达成度",
            "毕业要求指标点达成度",
            "支撑强度",
            "课程名称",
        ]
    ]

    print("=" * 72)
    print(f"专业: {args.major}")
    print(f"版本: {args.year}")
    print(f"毕业要求: {req_display}")
    print(f"指标点: {ind_display}")
    print(f"支撑强度: {', '.join(levels)}")
    print(f"成绩文件: {input_path}")
    print("=" * 72)
    print()
    print(
        result_df[
            [
                "毕业要求",
                "指标点",
                "核心课程（关联度）",
                "平均成绩",
                "总成绩（默认100分）",
                "课程达成度",
                "毕业要求指标点达成度",
            ]
        ].to_string(index=False)
    )
    print()
    print("--- 分组平均达成度 ---")
    print(summary_df.to_string(index=False))

    if args.output:
        export_result(result_df, summary_df, args.output)
        print()
        print(f"已导出: {args.output}")


if __name__ == "__main__":
    main()
