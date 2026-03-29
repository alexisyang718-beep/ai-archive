#!/bin/bash
# 科技日报定时任务配置更新脚本
# 执行后会将邮件推送设为12:00优先，数据采集延后

echo "=== 科技日报定时任务配置更新 ==="
echo ""

# 设置PATH
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:$HOME/.nvm/versions/node/v20.20.0/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/bin:$HOME/.browserwing"

# 备份当前crontab
echo "1. 备份当前crontab..."
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ 备份成功: /tmp/crontab_backup_*.txt"
else
    echo "   ⚠️  当前没有crontab任务，将创建新配置"
fi

# 创建新的crontab配置
echo ""
echo "2. 创建新的定时任务配置..."

cat > /tmp/new_crontab.txt << 'EOF'
# ========== 科技日报定时任务配置 ==========
# 更新时间: 2026-03-27
# 说明: 12:00邮件优先，数据采集延后

# ========== 12:00 邮件推送（优先）==========
# 群发日报邮件给所有订阅者
0 12 * * * cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 scripts/send_email.py brief/$(date +\%Y-\%m-\%d).html -y >> v2/logs/cron_email.log 2>&1

# ========== 12:05 X采集（延后）==========
# X/Twitter Following流采集（延后5分钟，避免与邮件冲突）
5 12 * * * cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 scripts/x_fetch_enhanced.py >> v2/logs/cron_x.log 2>&1

# ========== 12:10 RSS采集（延后）==========
# RSS聚合源扫描（延后10分钟）
10 12 * * * cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 scripts/rss_fetch.py >> v2/logs/cron_rss.log 2>&1

# ========== 定时采集任务 ==========
# X/Twitter采集（每2小时）
0 */2 * * * cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 scripts/x_fetch_enhanced.py >> v2/logs/cron_x.log 2>&1

# 微博采集（每2小时）
0 */2 * * * cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 scripts/weibo_fetch.py >> v2/logs/cron_weibo.log 2>&1

# RSS采集（每4小时）
0 */4 * * * cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 scripts/rss_fetch.py >> v2/logs/cron_rss.log 2>&1
EOF

# 应用新的crontab
echo ""
echo "3. 应用新的定时任务配置..."
crontab /tmp/new_crontab.txt

if [ $? -eq 0 ]; then
    echo "   ✅ Crontab 更新成功！"
    echo ""
    echo "=== 当前定时任务 ==="
    crontab -l | grep -v "^#" | grep -v "^$" | nl
    echo ""
    echo "=== 执行顺序 ==="
    echo "12:00 - 邮件群发（优先）"
    echo "12:05 - X/Twitter采集（延后）"
    echo "12:10 - RSS扫描（延后）"
    echo ""
    echo "=== 定时采集频率 ==="
    echo "X/Twitter: 每2小时"
    echo "微博: 每2小时"
    echo "RSS: 每4小时"
else
    echo "   ❌ Crontab 更新失败，请检查权限"
fi

# 清理临时文件
rm -f /tmp/new_crontab.txt

echo ""
echo "=== 完成 ==="
echo "按回车键退出..."
read
