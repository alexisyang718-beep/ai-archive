#!/usr/bin/env python3
"""
日报生成工作流脚本
整合所有检查和生成步骤
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime


def run_command(cmd, description):
    """运行命令并输出结果"""
    print(f"\n{'='*50}")
    print(f"📌 {description}")
    print('='*50)
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"⚠️  {result.stderr}")
    
    return result.returncode == 0


def main():
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    date_num = date_str.replace('-', '')
    
    print(f"🚀 启动日报生成工作流: {date_str}")
    
    base_path = Path("/Users/yangliu/Documents/Claude Code/codebuddy/tech-daily-brief")
    
    # 阶段1：信源检查
    print("\n" + "="*50)
    print("📋 阶段1: 信源检查")
    print("="*50)
    
    check_script = base_path / "scripts/daily_brief_check.py"
    result = subprocess.run(
        ["python3", str(check_script), date_num],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    
    if "❌" in result.stdout or result.returncode != 0:
        print("\n❌ 信源检查未通过，请先修复问题！")
        response = input("是否继续? (y/N): ")
        if response.lower() != 'y':
            return 1
    
    # 阶段2：生成日报
    print("\n" + "="*50)
    print("📝 阶段2: 生成日报")
    print("="*50)
    print("请根据检查清单撰写日报...")
    print(f"模板: {base_path}/template.html")
    print(f"输出: {base_path}/brief/{date_str}.html")
    input("\n撰写完成后按回车继续...")
    
    # 阶段3：质量检查
    print("\n" + "="*50)
    print("🔍 阶段3: 质量检查")
    print("="*50)
    
    html_path = base_path / f"brief/{date_str}.html"
    
    # 检查重复链接
    dup_script = base_path / "scripts/check_duplicate_links.py"
    subprocess.run(["python3", str(dup_script), str(html_path)])
    
    # 阶段4：预览
    print("\n" + "="*50)
    print("👁️ 阶段4: 预览检查")
    print("="*50)
    print(f"请打开: http://localhost:8080/brief/{date_str}.html")
    print("检查项:")
    print("  - 格式是否正确")
    print("  - 链接是否可点击")
    print("  - 字数是否符合要求")
    input("\n预览完成后按回车继续...")
    
    # 阶段5：发布
    print("\n" + "="*50)
    print("🚀 阶段5: 发布")
    print("="*50)
    
    # GitHub
    print("\n1. GitHub同步")
    print(f"   cd {base_path}")
    print(f"   git add brief/{date_str}.html")
    print(f'   git commit -m "Add daily brief for {date_str}"')
    print("   git push origin main")
    
    # 测试邮件
    print("\n2. 测试邮件")
    print(f"   python3 scripts/send_email.py brief/{date_str}.html --to alexisyang@tencent.com")
    
    # 公众号
    print("\n3. 公众号")
    print("   cd ../raphael-publish")
    print(f"   node publish-daily.mjs ../tech-daily-brief/brief/{date_str}.html nyt")
    
    print("\n" + "="*50)
    print("✅ 工作流完成！")
    print("="*50)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
