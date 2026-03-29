# 工作流4: 发布流程

> 执行发布：GitHub → 邮件 → 公众号
> AI角色：按步骤执行发布

---

## 该做什么

按顺序执行：
1. GitHub Pages 发布
2. 发送测试邮件
3. 群发邮件
4. 同步到公众号

---

## 前置条件

- 日报文件已生成：`../brief/YYYY-MM-DD.html`
- 已确认内容无误

---

## 怎么做

执行 `steps.md` 中的步骤，或参考 `commands.sh`。

### Step 1: GitHub Pages

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy
git add tech-daily-brief/brief/YYYY-MM-DD.html
git commit -m "Add daily brief YYYY-MM-DD"
git push origin main
```

**验证**：访问 `https://alexisyang718-beep.github.io/ai-archive/brief/YYYY-MM-DD.html`

### Step 2: 测试邮件

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief
python scripts/send_email.py brief/YYYY-MM-DD.html --to alexisyang@tencent.com
```

**注意**：
- 必须指定文件路径
- 测试邮件必须加 `--to alexisyang@tencent.com`
- 发送前会显示预览，需输入 `y` 确认

### Step 3: 群发邮件

确认测试邮件效果OK后：

```bash
python scripts/send_email.py brief/YYYY-MM-DD.html
```

或跳过确认：
```bash
python scripts/send_email.py brief/YYYY-MM-DD.html -y
```

### Step 4: 公众号同步

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/raphael-publish
node publish-daily.mjs ../tech-daily-brief/brief/YYYY-MM-DD.html
```

---

## 一键发布（可选）

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief

# 完整流程
python scripts/publish_all.py brief/YYYY-MM-DD.html

# 只发测试邮件
python scripts/publish_all.py brief/YYYY-MM-DD.html --test-email alexisyang@tencent.com
```

---

## 不该做什么

- ❌ 不要跳过测试邮件直接群发
- ❌ 不要不传文件路径直接运行send_email.py
- ❌ 不要在内容未确认前发布

---

## 发布后验证

- [ ] GitHub Pages 可访问
- [ ] 测试邮件已收到
- [ ] 群发邮件已发送（23人）
- [ ] 公众号草稿已生成

---

## 完成

日报发布流程完成。
