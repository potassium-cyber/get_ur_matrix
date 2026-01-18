import os
import shutil
import subprocess
import datetime

# === 配置路径 ===
# 1. 中央数据仓库路径 (源头)
SOURCE_DIR = "/Users/CHE/ai_zone/SciEdu_Central_Data"
# 2. App 数据目录 (目标)
TARGET_DIR = "/Users/CHE/ai_zone/get_ur_matrix/SciEdu_Matrix_App/data"
# 3. App 仓库根目录 (用于执行 Git)
REPO_ROOT = "/Users/CHE/ai_zone/get_ur_matrix"

def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Error running '{cmd}':\n{result.stderr}")
        exit(1)
    return result.stdout.strip()

def main():
    print("🚀 开始同步数据：Central Data -> Streamlit App")
    
    # 1. 检查源头是否存在
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ 找不到中央仓库: {SOURCE_DIR}")
        return

    # 2. 复制文件夹 (courses, programs)
    for folder in ["courses", "programs"]:
        src = os.path.join(SOURCE_DIR, folder)
        dst = os.path.join(TARGET_DIR, folder)
        
        if os.path.exists(dst):
            shutil.rmtree(dst) # 先删除旧的
        
        shutil.copytree(src, dst)
        print(f"✅ 已同步文件夹: {folder}")

    # 3. 复制 CSV 矩阵 (从 matrices 目录复制到 data 根目录)
    # 注意：这里我们把 matrices 里的文件直接平铺到 data 下，或者按需复制
    matrices_src = os.path.join(SOURCE_DIR, "matrices")
    if os.path.exists(matrices_src):
        for f in os.listdir(matrices_src):
            if f.endswith(".csv"):
                shutil.copy2(os.path.join(matrices_src, f), os.path.join(TARGET_DIR, f))
                print(f"✅ 已同步文件: {f}")
    
    # 4. 复制 YAML 到根目录 (为了兼容 app.py 的旧逻辑，如果有的话)
    programs_src = os.path.join(SOURCE_DIR, "programs")
    if os.path.exists(programs_src):
         for f in os.listdir(programs_src):
            if f.endswith(".yaml"):
                shutil.copy2(os.path.join(programs_src, f), os.path.join(TARGET_DIR, f))
                print(f"✅ 已同步文件: {f}")

    print("\n📦 文件复制完成。正在提交到 GitHub...")
    
    # 5. 执行 Git 命令
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 检查是否有变动
    status = run_cmd("git status --porcelain", cwd=REPO_ROOT)
    if not status:
        print("✨ 数据没有变化，无需提交。")
        return

    run_cmd("git add .", cwd=REPO_ROOT)
    run_cmd(f'git commit -m "data: sync from central_data at {timestamp}"', cwd=REPO_ROOT)
    print("⬆️  正在推送 (Git Push)...")
    run_cmd("git push origin main", cwd=REPO_ROOT)
    
    print("\n🎉 成功！Streamlit Cloud 将在几分钟内自动更新。")

if __name__ == "__main__":
    main()
