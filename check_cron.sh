#!/bin/bash
echo "=== 当前定时任务 ==="
crontab -l
echo ""
echo "=== X 采集日志最后5行 ==="
tail -5 v2/logs/cron_x.log 2>/dev/null || echo "日志不存在"
