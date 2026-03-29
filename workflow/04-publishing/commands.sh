#!/bin/bash
# 发布流程常用命令速查

# ===== 配置 =====
DATE=$(date +%Y-%m-%d)
BRIEF_FILE="brief/${DATE}.html"
PROJECT_DIR="/Users/yangliu/Documents/Claude Code/codebuddy/tech-daily-brief"
RAPHAEL_DIR="/Users/yangliu/Documents/Claude Code/codebuddy/raphael-publish"

# ===== Step 1: GitHub Pages =====
pushd "/Users/yangliu/Documents/Claude Code/codebuddy"
git add "tech-daily-brief/${BRIEF_FILE}"
git commit -m "Add daily brief ${DATE}"
git push origin main
popd

# ===== Step 2: 测试邮件 =====
cd "${PROJECT_DIR}"
python scripts/send_email.py "${BRIEF_FILE}" --to alexisyang@tencent.com

# ===== Step 3: 群发邮件 =====
cd "${PROJECT_DIR}"
python scripts/send_email.py "${BRIEF_FILE}"

# ===== Step 4: 公众号 =====
cd "${RAPHAEL_DIR}"
node publish-daily.mjs "../tech-daily-brief/${BRIEF_FILE}"

# ===== 一键发布 =====
cd "${PROJECT_DIR}"
python scripts/publish_all.py "${BRIEF_FILE}"
