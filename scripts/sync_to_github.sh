#!/bin/bash

# 同步日报到 GitHub Pages
# 用法: ./sync_to_github.sh [日期，默认为今天]

# 设置日期
DATE="${1:-$(date +%Y-%m-%d)}"
BRIEF_FILE="brief/${DATE}.html"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  同步日报到 GitHub Pages${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查文件是否存在
if [ ! -f "$BRIEF_FILE" ]; then
    echo -e "${YELLOW}❌ 错误: 文件 $BRIEF_FILE 不存在${NC}"
    exit 1
fi

echo -e "${GREEN}📄 日报文件: $BRIEF_FILE${NC}"
echo ""

# Git 操作
echo -e "${BLUE}🔄 同步到 GitHub...${NC}"
git add "$BRIEF_FILE"
git add index.html 2>/dev/null || true
git commit -m "Add daily brief for $DATE" || echo "没有新变更需要提交"
git push origin main

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ GitHub 同步成功！${NC}"
else
    echo -e "${YELLOW}❌ GitHub 同步失败${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🎉 发布完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}📰 今日日报:${NC}"
echo -e "   https://alexisyang718-beep.github.io/ai-archive/brief/${DATE}.html"
echo ""
echo -e "${YELLOW}🏠 首页:${NC}"
echo -e "   https://alexisyang718-beep.github.io/ai-archive/"
echo ""
echo -e "${BLUE}========================================${NC}"
