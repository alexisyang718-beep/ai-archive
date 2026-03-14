# 📧 邮件推送最佳实践

## 正确方式

使用 Python smtplib 通过 QQ 邮箱 SMTP（smtp.qq.com:465 SSL）发送。

### 关键要点
1. 邮件 HTML **必须用 premailer** 将 CSS class 转为内联 style
   - 邮件客户端会剥离 `<style>` 标签导致空白
2. From 头必须是纯邮箱地址，不能加别名
3. QQ 邮箱授权码存在 macOS 钥匙串
   - service: `qq-smtp-auth`
   - account: `422548579@qq.com`

### CSS 适配清单

| 操作 | 原因 |
|------|------|
| CSS 变量 → 硬编码值 | 邮件不支持 CSS 变量 |
| 去掉 @import url() | 邮件不加载外部字体 |
| 去掉 :root 块 | 无用 |
| 去掉 [data-theme="dark"] | 邮件无暗色模式 |
| 去掉所有 :hover 规则 | 邮件不支持 |
| 去掉 transition 属性 | 邮件不支持 |
| grid → block | 邮件兼容性差 |
| 780px → 680px 容器 | 移动端优化 |
| 去掉 `<script>` 标签 | 邮件不执行 JS |
| 去掉固定定位元素 | back-to-top / theme-toggle 无用 |
| premailer 内联 CSS | 最终一步，去除所有 class |

## 已验证不可用的方式

| 方式 | 问题 |
|------|------|
| 本地 postfix | 无 SPF/DKIM 认证，被拒收 |
| AppleScript `set html content` | 80KB+ 大 HTML 有 bug，收件端空白 |
| .eml + Apple Mail | 可作备选但不如直接 SMTP |

## 备选方案

`build_eml.py` 生成 .eml 文件，用 Apple Mail 手动发送。
