# AI 快速启动指南

> 零上下文AI的救命稻草

---

## 用户说了一句话，我该做什么？

### 场景1："给我看今天的选题"

**立即执行**：
```
1. 读 workflow/README.md
2. 读 workflow/02-selection/README.md
3. 读 workflow/scripts/README.md
4. 检查 workflow/output/candidates_2026-03-26.csv 是否存在
   - 存在 → 读取CSV
   - 不存在 → 执行 python3 workflow/scripts/01_preprocess_candidates.py 2026-03-26
5. 读 workflow/02-selection/news-preferences.md
6. 读 workflow/02-selection/prompt.md
7. 生成选题报告
8. 输出到 v2/docs/daily_selection_2026-03-26.md
9. 告知用户等待确认
```

**跑偏警报**：
- ❌ 直接读原始JSON文件（重复劳动）
- ❌ 不读preferences凭感觉选
- ❌ 跳过脚本执行

---

### 场景2："写日报"

**立即执行**：
```
1. 读 workflow/README.md
2. 读 workflow/03-generation/README.md
3. 检查 v2/docs/daily_selection_2026-03-26.md 是否已确认
   - 未确认 → 停止，告知用户先确认选题
4. 读 workflow/scripts/README.md
5. 检查 workflow/output/fulltext_2026-03-26.json 是否存在
   - 存在 → 读取
   - 不存在 → 执行 python3 workflow/scripts/02_fetch_fulltext.py 2026-03-26
6. 读 workflow/03-generation/writing-preferences.md
7. 读 template.html
8. 撰写日报
9. 输出到 brief/2026-03-26.html
```

**跑偏警报**：
- ❌ 选题未确认就写（大忌）
- ❌ 不读template.html自行写HTML
- ❌ 丢失原始链接

---

### 场景3："发布"

**立即执行**：
```
1. 读 workflow/README.md
2. 读 workflow/04-publishing/README.md
3. 检查 brief/2026-03-26.html 是否存在
   - 不存在 → 停止，告知用户先生成日报
4. 执行 python3 workflow/scripts/03_publish_pipeline.py 2026-03-26
5. 等待人工确认测试邮件
6. 自动完成群发和公众号同步
```

**跑偏警报**：
- ❌ 跳过测试邮件直接群发
- ❌ 不等待确认

---

## 如果我不确定该做什么

**万能公式**：
```
1. 读 workflow/README.md
2. 读对应工作流的 README.md
3. 读 workflow/scripts/README.md
4. 读对应工作流的 preferences.md
5. 读对应工作流的 prompt.md
6. 执行
```

**如果还是不确定 → 问用户**："我需要执行工作流X，确认吗？"

---

## 记忆口诀

```
先读README定方向
再读工作流知步骤
检查脚本别重复
偏好配置要记牢
prompt是操作手册
checklist是安全带
不确定时就问人
别凭感觉瞎操作
```
