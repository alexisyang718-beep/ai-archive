#!/usr/bin/env python3
"""
发布流水线脚本
功能：GitHub Push → 测试邮件 → 人工确认 → 群发 → 公众号
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
RAPHAEL_DIR = Path("/Users/yangliu/Documents/Claude Code/codebuddy/raphael-publish")

def run_cmd(cmd, cwd=None, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return r.returncode == 0, r.stdout, r.stderr
    except Exception as e:
        return False, "", str(e)

def github_push(date_str):
    print("\n[Step 1] GitHub Push")
    github = Path("/Users/yangliu/Documents/Claude Code/codebuddy")
    file_path = f"tech-daily-brief/brief/{date_str}.html"
    
    cmds = [
        f"cd '{github}' && git add '{file_path}'",
        f"cd '{github}' && git commit -m 'Add daily brief {date_str}' || true",
        f"cd '{github}' && git push origin main"
    ]
    for cmd in cmds:
        ok, out, err = run_cmd(cmd)
        if not ok and "commit" not in cmd:
            print(f"  ❌ {err}")
            return False
    print("  ✅ 成功")
    print(f"   https://alexisyang718-beep.github.io/ai-archive/brief/{date_str}.html")
    return True

def test_email(date_str):
    print("\n[Step 2] 测试邮件")
    cmd = f"cd '{PROJECT_ROOT}' && python3 scripts/send_email.py brief/{date_str}.html --to alexisyang@tencent.com"
    ok, out, err = run_cmd(cmd, timeout=120)
    if ok or "发送成功" in out:
        print("  ✅ 已发送")
        return True
    print(f"  ❌ {err}")
    return False

def confirm():
    print("\n[Step 3] 人工确认")
    r = input("测试邮件OK? 群发请输入yes: ").strip().lower()
    return r in ['yes', 'y']

def mass_email(date_str):
    print("\n[Step 4] 群发邮件")
    cmd = f"cd '{PROJECT_ROOT}' && python3 scripts/send_email.py brief/{date_str}.html"
    ok, out, err = run_cmd(cmd, timeout=120)
    if ok or "发送成功" in out:
        print("  ✅ 已群发")
        return True
    print(f"  ❌ {err}")
    return False

def wechat(date_str):
    print("\n[Step 5] 公众号同步")
    if not RAPHAEL_DIR.exists():
        print("  ❌ raphael-publish不存在")
        return False
    cmd = f"cd '{RAPHAEL_DIR}' && node publish-daily.mjs ../tech-daily-brief/brief/{date_str}.html"
    ok, out, err = run_cmd(cmd, timeout=60)
    if ok:
        print("  ✅ 已同步")
        return True
    print(f"  ❌ {err}")
    return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 03_publish_pipeline.py YYYY-MM-DD")
        sys.exit(1)
    
    date_str = sys.argv[1]
    brief = PROJECT_ROOT / "brief" / f"{date_str}.html"
    if not brief.exists():
        print(f"❌ 文件不存在: {brief}")
        sys.exit(1)
    
    print(f"📅 发布: {date_str}")
    
    # 执行流程
    if github_push(date_str):
        if test_email(date_str):
            if confirm():
                mass_email(date_str)
    
    wechat(date_str)
    
    print("\n✅ 发布流程完成")

if __name__ == "__main__":
    main()
