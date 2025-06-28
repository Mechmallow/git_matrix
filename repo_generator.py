# -*- coding: utf-8 -*-
import json
import os
import subprocess
import shutil
import logging
import sys
from datetime import datetime, timedelta

def check_git_installed():
    """检查系统中是否安装了 Git."""
    if shutil.which("git") is None:
        logging.error("系统中未找到 'git' 命令。")
        logging.error("请先安装 Git 然后再运行此脚本: https://git-scm.com/downloads")
        return False
    return True

def run_command(command, cwd):
    """在指定目录下运行一个命令，并处理错误。"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            shell=True,
            text=True,
            capture_output=True,
            encoding='utf-8'
        )
        return result
    except subprocess.CalledProcessError as e:
        logging.error(f"命令执行失败: {' '.join(command)}")
        logging.error(f"返回码: {e.returncode}")
        logging.error(f"输出: {e.stdout}")
        logging.error(f"错误: {e.stderr}")
        return None
    except FileNotFoundError:
        logging.error(f"命令执行失败: {command[0]} 未找到。请确保它在系统的 PATH 中。")
        return None


def create_repo_from_pattern(config_path):
    """
    从 pattern.json 配置文件创建包含伪造提交历史的 Git 仓库。
    此版本依赖于系统中已安装的 Git。
    """
    if not check_git_installed():
        return

    # --- 1. 读取和解析配置文件 ---
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error(f"找不到配置文件 '{config_path}'")
        return

    repo_name = config.get("repository_name", "my-contribution-art")
    user_name = config.get("git_config", {}).get("user_name", "User")
    user_email = config.get("git_config", {}).get("user_email", "user@example.com")
    start_date_str = config.get("start_date")
    levels = config.get("levels", {})
    pattern = config.get("pattern", [])

    if not all([repo_name, start_date_str, pattern]):
        logging.error("配置文件缺少必要的字段 (repository_name, start_date, pattern)。")
        return
        
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    repo_path = os.path.abspath(repo_name)

    # --- 2. 初始化仓库 ---
    if not os.path.exists(repo_path):
        os.makedirs(repo_path)

    logging.info(f"正在仓库 '{repo_name}' 中进行初始化...")
    if run_command("git init", cwd=repo_path) is None: return
    if run_command(f'git config user.name "{user_name}"', cwd=repo_path) is None: return
    if run_command(f'git config user.email "{user_email}"', cwd=repo_path) is None: return

    # --- 3. 循环生成提交 ---
    commit_count_total = 0
    readme_path = os.path.join(repo_path, 'README.md')
    num_rows = len(pattern)
    num_cols = len(pattern[0]) if pattern else 0

    for col in range(num_cols):
        for row in range(num_rows):
            level_char = pattern[row][col]
            commit_count_for_day = int(levels.get(str(level_char), 0))

            if commit_count_for_day > 0:
                current_date = start_date + timedelta(days=(col * 7 + row)+1)
                
                for i in range(commit_count_for_day):
                    commit_count_total += 1
                    
                    # a. 修改文件
                    with open(readme_path, 'w', encoding='utf-8') as f:
                        f.write(f"Commit #{commit_count_total} on {current_date.date()}\n")
                    
                    # b. 添加文件到暂存区
                    if run_command("git add README.md", cwd=repo_path) is None: return
                    
                    # c. 使用特定日期进行提交
                    commit_date = current_date.isoformat()
                    commit_message = f"feat: commit #{commit_count_total}"
                    
                    env = os.environ.copy()
                    env['GIT_AUTHOR_DATE'] = commit_date
                    env['GIT_COMMITTER_DATE'] = commit_date
                    
                    try:
                        subprocess.run(
                            ['git', 'commit', '-m', commit_message],
                            cwd=repo_path,
                            env=env,
                            check=True,
                            capture_output=True,
                            encoding='utf-8'
                        )
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Git commit 失败: {e.stderr}")
                        return

            # 打印进度 (使用 sys.stdout 来实现单行刷新)
            processed_days = col * num_rows + row + 1
            total_days = num_cols * num_rows
            progress = processed_days / total_days * 100
            progress_message = f"\r处理进度: {progress:.1f}% ({processed_days}/{total_days} 天), 已生成 {commit_count_total} 次提交..."
            sys.stdout.write(progress_message)
            sys.stdout.flush()
    
    sys.stdout.write('\n') # 结束进度条，换行
    logging.info(f"处理完成！总共生成了 {commit_count_total} 次提交。")

    # --- 4. 显示后续操作指南 ---
    instructions = f"""
        {'='*60}
        🎉 Git 仓库已成功在本地生成!

        下一步操作:
        1. 前往 GitHub 创建一个新的 **空** 仓库 (不要勾选'Add a README file').
        2. 在你的终端中，进入刚刚生成的目录并执行以下命令:

            cd "{repo_name}"
            git remote add origin <你的远程仓库URL>
            git branch -M main
            git push -u origin main

        推送完成后，稍等片刻，你的 GitHub 贡献图就会更新！
        {'='*60}
        """
    # 使用一个专用的 logger 或者直接 print 来获得干净的输出
    # 这里我们选择直接 print，因为它不是一个“日志”，而是给用户的最终指令
    print(instructions)


if __name__ == '__main__':
    # 配置 logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s',
        stream=sys.stdout
    )
    
    config_file = 'pattern.json'
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    create_repo_from_pattern(config_file)
