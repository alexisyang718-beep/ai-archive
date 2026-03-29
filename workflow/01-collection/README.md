# 工作流1: 定时采集

> 自动化采集X、微博、RSS数据
> AI角色：监控状态、报告异常

---

## 该做什么

1. 监控定时采集任务的执行状态
2. 检查采集数据是否正常
3. 如发现异常，报告给用户

---

## 怎么做

### 检查采集状态

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief
python3 v2/scripts/collector_cron.py --status
```

### 查看日志

```bash
# X采集日志
tail -30 v2/logs/cron_x.log

# X采集错误日志
tail -30 v2/logs/cron_x_debug.log

# 微博采集日志
tail -30 v2/logs/cron_weibo.log

# RSS采集日志
tail -30 v2/logs/cron_rss.log
```

### 手动执行采集（如需补采）

```bash
# 采集X
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief
export PATH="/Users/yangliu/.local/bin:$PATH"
python3 v2/scripts/collector.py --source x --date 2026-03-26

# 采集微博
python3 v2/scripts/collector.py --source weibo --date 2026-03-26

# 采集RSS
python3 v2/scripts/collector.py --source rss --date 2026-03-26
```

---

## 正常标准

| 渠道 | 正常条数 | 说明 |
|------|---------|------|
| X | 100-300条 | Cookie有效时可正常采集 |
| RSS | 100-200条 | 依赖RSS源更新频率 |
| 微博 | 300-800条 | 依赖博主更新频率 |
| **合计** | **>500条** | 正常标准 |

---

## 异常处理

### X采集失败（Cookie过期）

**症状**：`cron_x_debug.log` 显示认证失败

**解决**：
```bash
export PATH="/Users/yangliu/.local/bin:$PATH"
twitter status  # 检查状态

# 如确实过期，告知用户重新登录
```

### 某渠道数据为0

**检查**：
1. 检查该渠道日志是否有错误
2. 检查网络连接
3. 检查配置文件

---

## 不该做什么

- ❌ 不要修改采集配置（`config.yaml`）
- ❌ 不要删除采集数据文件
- ❌ 不要频繁手动触发采集（可能触发限流）

---

## 输出

更新 `status.md`：

```markdown
## 今日采集状态（YYYY-MM-DD）

| 渠道 | 状态 | 条数 | 最后采集时间 | 备注 |
|------|------|------|-------------|------|
| X | ✅/❌ | N | HH:MM | 正常/异常说明 |
| RSS | ✅/❌ | N | HH:MM | |
| 微博 | ✅/❌ | N | HH:MM | |
| **合计** | | **N** | | |
```

---

## 进入下一步

采集正常后，进入 **工作流2：选题报告**
