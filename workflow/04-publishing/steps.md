# 发布流程步骤

## 前置条件

- 日报文件已生成：`../brief/YYYY-MM-DD.html`
- 已确认内容无误

## 发布步骤

### Step 1: GitHub Pages

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy
git add tech-daily-brief/brief/YYYY-MM-DD.html
git commit -m "Add daily brief YYYY-MM-DD"
git push origin main
```

**验证**：访问 `https://alexisyang718-beep.github.io/ai-archive/brief/YYYY-MM-DD.html`

---

### Step 2: 测试邮件

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief

# 发送给指定邮箱（测试用）
python scripts/send_email.py brief/YYYY-MM-DD.html --to alexisyang@tencent.com
```

**注意**：
- 必须指定文件路径
- 测试邮件必须加 `--to alexisyang@tencent.com`
- 发送前会显示预览，需输入 `y` 确认

---

### Step 3: 群发邮件

确认测试邮件效果OK后：

```bash
# 发给全部23人（显示预览确认）
python scripts/send_email.py brief/YYYY-MM-DD.html
```

或跳过确认：
```bash
python scripts/send_email.py brief/YYYY-MM-DD.html -y
```

---

### Step 4: 公众号同步

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/raphael-publish
node publish-daily.mjs ../tech-daily-brief/brief/YYYY-MM-DD.html
```

**默认配置**（已固化）：
- 标题：`科技资讯日报｜MM月DD日`
- 封面：`~/Desktop/cover.png`
- 主题：`nyt`（纽约时报风格）
- 页脚品牌：`Tech Daily Brief`

---

## 一键发布（可选）

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief

# 完整流程
python scripts/publish_all.py brief/YYYY-MM-DD.html

# 只发测试邮件
python scripts/publish_all.py brief/YYYY-MM-DD.html --test-email alexisyang@tencent.com

# 跳过某些步骤
python scripts/publish_all.py brief/YYYY-MM-DD.html --skip-github
python scripts/publish_all.py brief/YYYY-MM-DD.html --skip-wechat
```

---

## 发布后验证

- [ ] GitHub Pages 可访问
- [ ] 测试邮件已收到
- [ ] 群发邮件已发送（23人）
- [ ] 公众号草稿已生成
