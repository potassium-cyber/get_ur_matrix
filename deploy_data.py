"""
deploy_data.py — 从外部 SSoT 同步矩阵数据到 Streamlit App 目录

默认行为：
- 自动将当前仓库根目录识别为 REPO_ROOT
- 自动将 SciEdu_Matrix_App/data 识别为目标目录
- 优先从环境变量 SCIEDU_SSOT_DIR 读取外部 SSoT 路径
- 若未设置环境变量，则尝试使用兄弟目录 ../SciEdu_Central_Data

支持多专业结构：
  SSoT: majors/{major_name}/matrix_{version}.csv + program_{version}.yaml
  App:  data/majors/{major_name}/matrix_{version}.csv + {version}_program.yaml

示例：
  python deploy_data.py --dry
  python deploy_data.py
  python deploy_data.py --major sci_edu
  SCIEDU_SSOT_DIR=/path/to/SciEdu_Central_Data python deploy_data.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import stat
import shutil
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parent
TARGET_DIR = REPO_ROOT / "SciEdu_Matrix_App" / "data"
DEFAULT_SSOT_DIR = REPO_ROOT.parent / "SciEdu_Central_Data"
DEFAULT_MAJORS = ("sci_edu", "physics")
SYNCABLE_SUFFIXES = (".csv", ".yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="同步外部 SSoT 数据到 Streamlit App")
    parser.add_argument(
        "--source-dir",
        default=os.environ.get("SCIEDU_SSOT_DIR"),
        help="外部 SSoT 根目录；默认读取环境变量 SCIEDU_SSOT_DIR，若为空则尝试 ../SciEdu_Central_Data",
    )
    parser.add_argument(
        "--target-dir",
        default=str(TARGET_DIR),
        help="App 数据目录，默认是当前仓库下的 SciEdu_Matrix_App/data",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Git 仓库根目录，默认是当前 deploy_data.py 所在仓库",
    )
    parser.add_argument(
        "--major",
        action="append",
        dest="majors",
        help="仅同步指定专业，可重复传入；默认同步所有已配置专业",
    )
    parser.add_argument(
        "--dry",
        action="store_true",
        help="仅预览，不复制文件，也不提交 Git",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="复制文件后不自动创建 Git 提交",
    )
    return parser.parse_args()


def resolve_source_dir(cli_value: str | None) -> Path:
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    return DEFAULT_SSOT_DIR.resolve()


def normalize_program_filename(filename: str) -> str:
    if filename.startswith("program_"):
        version = filename.removeprefix("program_").removesuffix(".yaml")
        return f"{version}_program.yaml"
    return filename


def remove_existing_file(path: Path) -> None:
    """Remove an existing destination file even if it is read-only."""
    if not path.exists():
        return

    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IWUSR)
    path.unlink()


def run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)


def validate_paths(source_dir: Path, target_dir: Path, repo_root: Path) -> None:
    if not source_dir.exists():
        raise FileNotFoundError(f"未找到外部 SSoT 目录: {source_dir}")
    if not (source_dir / "majors").exists():
        raise FileNotFoundError(f"SSoT 缺少 majors/ 目录: {source_dir / 'majors'}")
    if not target_dir.exists():
        raise FileNotFoundError(f"未找到目标数据目录: {target_dir}")
    if not (repo_root / ".git").exists():
        raise FileNotFoundError(f"未找到 Git 仓库根目录: {repo_root}")


def sync_major(source_dir: Path, target_dir: Path, major_name: str, dry_run: bool) -> int:
    src_dir = source_dir / "majors" / major_name
    dst_dir = target_dir / "majors" / major_name

    if not src_dir.exists():
        print(f"  ⚠️ 跳过，源目录不存在: {src_dir}")
        return 0

    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for src_path in sorted(src_dir.iterdir()):
        if not src_path.is_file() or src_path.suffix not in SYNCABLE_SUFFIXES:
            continue
        if src_path.name == "metadata.yaml":
            continue

        dst_name = normalize_program_filename(src_path.name)
        dst_path = dst_dir / dst_name

        if dry_run:
            print(f"  📋 {src_path} -> {dst_path}")
        else:
            remove_existing_file(dst_path)
            shutil.copy2(src_path, dst_path)
            print(f"  ✅ {src_path.name} -> majors/{major_name}/{dst_name}")
        count += 1

    return count


def git_commit(repo_root: Path) -> None:
    run_cmd(["git", "add", "SciEdu_Matrix_App/data/"], cwd=repo_root)

    diff_result = run_cmd(["git", "diff", "--cached", "--quiet"], cwd=repo_root)
    if diff_result.returncode == 0:
        print("\n📭 没有数据变更，跳过 Git 提交。")
        return

    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"data: sync from SSoT ({timestamp})"
    commit_result = run_cmd(["git", "commit", "-m", message], cwd=repo_root)
    if commit_result.returncode != 0:
        print("\n❌ Git 提交失败：")
        print(commit_result.stderr.strip())
        sys.exit(commit_result.returncode)

    print(f"\n📦 Git 已提交: {message}")


def main() -> None:
    args = parse_args()
    source_dir = resolve_source_dir(args.source_dir)
    target_dir = Path(args.target_dir).expanduser().resolve()
    repo_root = Path(args.repo_root).expanduser().resolve()
    majors = args.majors or list(DEFAULT_MAJORS)

    validate_paths(source_dir, target_dir, repo_root)

    mode = "预览模式" if args.dry else "同步模式"
    print(f"🚀 数据同步 ({mode})")
    print(f"   SSoT: {source_dir}")
    print(f"   App:  {target_dir}")
    print(f"   Repo: {repo_root}")
    print()

    total = 0
    for major in majors:
        print(f"📁 {major}/")
        total += sync_major(source_dir, target_dir, major, args.dry)

    print(f"\n📊 共同步 {total} 个文件")

    if not args.dry and not args.no_commit:
        git_commit(repo_root)

    print("\n✅ 完成!")


if __name__ == "__main__":
    main()
