# 📱 微信公众号推送指南

## 两步流程

### Step 1: 生成微信专用 HTML

```bash
python scripts/gen_wechat_copy.py
```

此脚本将网页版日报 HTML 转换为微信公众号兼容格式：
- 用 BeautifulSoup 解析原始 HTML
- 所有样式转为 inline style（微信不支持 class）
- div 布局转为 table 卡片模拟（微信编辑器兼容性更好）
- 处理标签颜色映射
- 去掉外部链接（微信不允许）
- 去掉 HTML 注释、data-* 属性
- 处理正文开头空格

### Step 2: 推送到草稿箱

```bash
python scripts/publish_wechat.py
```

此脚本调用微信公众号 API：
1. 上传封面图片（~/Desktop/cover.png）
2. 移除目录部分（微信不需要）
3. 用 div 包裹 table 实现圆角
4. 创建草稿并推送到公众号后台

## API 凭据

- AppID: `wxc0acff84c3ba27b0`
- AppSecret: `7af6a2678e804ecbe3425f0889c1d28d`
- 使用 wechat-publisher-skill 的 publisher.py

## 微信公众号排版注意事项

| 限制 | 处理方式 |
|------|----------|
| 不支持 CSS class | 全部转为 inline style |
| 不支持外部链接 | 保留文字，去掉 `<a>` 标签 |
| table 不支持 border-radius | 用 td + overflow:hidden 实现 |
| 不支持 JavaScript | 去掉所有 `<script>` |
| 内容限制 2MB | 监控内容大小 |
| 不支持 CSS 变量 | 硬编码颜色值 |

## 封面图

封面图路径：`~/Desktop/cover.png`，上传后获取 `thumb_media_id`。
