#!/usr/bin/env node
/**
 * 一键发布日报到微信公众号
 * 
 * 流程: HTML → Markdown → Raphael 排版 → 微信草稿箱
 * 
 * 用法: node publish-daily.mjs <input.html> [theme]
 */

import { readFileSync, writeFileSync } from 'fs';
import { resolve, dirname, basename } from 'path';
import { JSDOM } from 'jsdom';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';

// Raphael 主题样式
const THEMES = {
  nyt: {
    name: 'NYT',
    styles: {
      container: 'max-width: 100%; margin: 0 auto; padding: 24px 20px 48px 20px; font-family: Georgia, "Times New Roman", Times, serif; font-size: 16px; line-height: 1.7 !important; color: #000000 !important; background-color: #fdfaf6 !important; word-wrap: break-word;',
      h1: 'font-size: 32px; font-weight: 700; color: #111 !important; line-height: 1.3 !important; margin: 38px 0 16px; letter-spacing: -0.015em; border-bottom: 2px solid #000; padding-bottom: 12px; font-family: Georgia, "Times New Roman", Times, serif;',
      h2: 'font-size: 26px; font-weight: 700; color: #111 !important; line-height: 1.35 !important; margin: 32px 0 16px; font-family: Georgia, "Times New Roman", Times, serif;',
      h3: 'font-size: 21px; font-weight: 600; color: #000000 !important; line-height: 1.4 !important; margin: 28px 0 14px; font-family: Georgia, "Times New Roman", Times, serif;',
      h4: 'font-size: 18px; font-weight: 600; color: #000000 !important; line-height: 1.4 !important; margin: 24px 0 12px; font-family: Georgia, "Times New Roman", Times, serif;',
      p: 'margin: 18px 0 !important; line-height: 1.7 !important; color: #000000 !important; font-family: Georgia, "Times New Roman", Times, serif; font-size: 16px;',
      strong: 'font-weight: 700; color: #000 !important;',
      em: 'font-style: italic; color: #666 !important;',
      a: 'color: #326891 !important; text-decoration: none; border-bottom: 1px solid #326891; padding-bottom: 1px;',
      ul: 'margin: 16px 0; padding-left: 28px; list-style-type: disc !important;',
      ol: 'margin: 16px 0; padding-left: 28px; list-style-type: decimal !important;',
      li: 'margin: 8px 0; line-height: 1.7 !important; color: #000000 !important;',
      blockquote: 'margin: 24px 0; padding: 16px 20px; background-color: #f0ede8 !important; border-left: 4px solid #326891; color: #555 !important; border-radius: 4px; font-style: italic; font-family: Georgia, "Times New Roman", Times, serif; line-height: 1.7 !important; font-size: 16px;',
      code: 'font-family: "SF Mono", Consolas, monospace; padding: 3px 6px; background-color: #f0ede8 !important; color: #326891 !important; border-radius: 4px; font-size: 12px !important; line-height: 1.5 !important;',
      pre: 'margin: 24px 0; padding: 20px; background-color: #f0ede8 !important; border-radius: 8px; overflow-x: auto; font-size: 12px !important; line-height: 1.5 !important;',
      hr: 'margin: 36px auto; border: none; height: 1px; background-color: #d5cfc5 !important; width: 100%;',
      img: 'max-width: 100%; height: auto; display: block; margin: 24px auto; border-radius: 12px;',
      table: 'width: 100%; margin: 24px 0; border-collapse: collapse; font-size: 15px;',
      th: 'background-color: #f0ede8 !important; padding: 12px 16px; text-align: left; font-weight: 600; color: #000000 !important; border: 1px solid #d5cfc5;',
      td: 'padding: 12px 16px; border: 1px solid #d5cfc5; color: #000000 !important;',
    }
  },
  claude: {
    name: 'Claude',
    styles: {
      container: 'max-width: 100%; margin: 0 auto; padding: 24px 20px 48px 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size: 16px; line-height: 1.7 !important; color: #2b2b2b !important; background-color: #f8f6f0 !important; word-wrap: break-word;',
      h1: 'font-size: 32px; font-weight: 700; color: #b75c3d !important; line-height: 1.3 !important; margin: 38px 0 16px; letter-spacing: -0.015em; text-align: center;',
      h2: 'font-size: 26px; font-weight: 600; color: #b75c3d !important; line-height: 1.35 !important; margin: 32px 0 16px; border-bottom: 2px solid #e8e2d9; padding-bottom: 12px;',
      h3: 'font-size: 21px; font-weight: 600; color: #2b2b2b !important; line-height: 1.4 !important; margin: 28px 0 14px;',
      h4: 'font-size: 18px; font-weight: 600; color: #2b2b2b !important; line-height: 1.4 !important; margin: 24px 0 12px;',
      p: 'margin: 18px 0 !important; line-height: 1.7 !important; color: #2b2b2b !important;',
      strong: 'font-weight: 700; color: #b75c3d !important; background-color: rgba(183,92,61,0.08); padding: 0 4px; border-radius: 4px;',
      em: 'font-style: italic; color: #666 !important;',
      a: 'color: #b75c3d !important; text-decoration: none; border-bottom: 1px solid #b75c3d; padding-bottom: 1px;',
      ul: 'margin: 16px 0; padding-left: 28px; list-style-type: disc !important;',
      ol: 'margin: 16px 0; padding-left: 28px; list-style-type: decimal !important;',
      li: 'margin: 8px 0; line-height: 1.7 !important; color: #2b2b2b !important;',
      blockquote: 'margin: 24px 0; padding: 16px 20px; background-color: rgba(183, 92, 61, 0.04) !important; border-left: 4px solid #b75c3d; color: #555 !important; border-radius: 4px;',
      code: 'font-family: "SF Mono", Consolas, monospace; padding: 3px 6px; background-color: #f0ece4 !important; color: #b75c3d !important; border-radius: 4px; font-size: 12px !important; line-height: 1.5 !important;',
      pre: 'margin: 24px 0; padding: 20px; background-color: #f0ece4 !important; border-radius: 8px; overflow-x: auto; font-size: 12px !important; line-height: 1.5 !important;',
      hr: 'margin: 36px auto; border: none; height: 1px; background-color: #d4c5b0 !important; width: 100%;',
      img: 'max-width: 100%; height: auto; display: block; margin: 24px auto; border-radius: 12px;',
      table: 'width: 100%; margin: 24px 0; border-collapse: collapse; font-size: 15px;',
      th: 'background-color: #f0ece4 !important; padding: 12px 16px; text-align: left; font-weight: 600; color: #2b2b2b !important; border: 1px solid #d4c5b0;',
      td: 'padding: 12px 16px; border: 1px solid #d4c5b0; color: #2b2b2b !important;',
    }
  },
  wechat: {
    name: '微信',
    styles: {
      container: 'max-width: 100%; margin: 0 auto; padding: 24px 20px 48px 20px; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; font-size: 16px; line-height: 1.75 !important; color: #3e3e3e !important; background-color: #ffffff !important; word-wrap: break-word;',
      h1: 'font-size: 24px; font-weight: 700; color: #333 !important; line-height: 1.4 !important; margin: 24px 0 16px; text-align: center;',
      h2: 'font-size: 20px; font-weight: 700; color: #333 !important; line-height: 1.4 !important; margin: 20px 0 12px;',
      h3: 'font-size: 18px; font-weight: 600; color: #3e3e3e !important; line-height: 1.4 !important; margin: 16px 0 10px;',
      h4: 'font-size: 16px; font-weight: 600; color: #3e3e3e !important; line-height: 1.4 !important; margin: 14px 0 8px;',
      p: 'margin: 16px 0 !important; line-height: 1.75 !important; color: #3e3e3e !important; text-align: justify;',
      strong: 'font-weight: 700; color: #333 !important;',
      em: 'font-style: italic; color: #666 !important;',
      a: 'color: #576b95 !important; text-decoration: none;',
      ul: 'margin: 14px 0; padding-left: 24px; list-style-type: disc !important;',
      ol: 'margin: 14px 0; padding-left: 24px; list-style-type: decimal !important;',
      li: 'margin: 6px 0; line-height: 1.75 !important; color: #3e3e3e !important;',
      blockquote: 'margin: 16px 0; padding: 12px 16px; background-color: #f7f7f7 !important; border-left: 4px solid #576b95; color: #666 !important; border-radius: 2px;',
      code: 'font-family: Menlo, Consolas, monospace; padding: 2px 6px; background-color: #f7f7f7 !important; color: #c7254e !important; border-radius: 3px; font-size: 13px !important;',
      pre: 'margin: 16px 0; padding: 16px; background-color: #f7f7f7 !important; border-radius: 4px; overflow-x: auto; font-size: 13px !important;',
      hr: 'margin: 24px auto; border: none; height: 1px; background-color: #e5e5e5 !important; width: 100%;',
      img: 'max-width: 100%; height: auto; display: block; margin: 16px auto; border-radius: 4px;',
      table: 'width: 100%; margin: 16px 0; border-collapse: collapse; font-size: 14px;',
      th: 'background-color: #f7f7f7 !important; padding: 10px 12px; text-align: left; font-weight: 600; color: #333 !important; border: 1px solid #e5e5e5;',
      td: 'padding: 10px 12px; border: 1px solid #e5e5e5; color: #3e3e3e !important;',
    }
  }
};

// 初始化 Markdown 解析器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: false
});

// HTML 转 Markdown（简化版）
function htmlToMarkdown(html) {
  const dom = new JSDOM(html);
  const doc = dom.window.document;
  
  let markdown = '';
  
  // 标题
  const h1 = doc.querySelector('.header h1');
  const date = doc.querySelector('.header .date');
  if (h1) markdown += `# ${h1.textContent.trim()}\n\n`;
  if (date) markdown += `**${date.textContent.trim()}**\n\n`;
  
  // 核心要闻
  const summaryCard = doc.querySelector('.summary-card');
  if (summaryCard) {
    let text = summaryCard.innerHTML;
    text = text.replace(/<strong>([^<]+)<\/strong>/g, '**$1**');
    text = text.replace(/<[^>]+>/g, '');
    text = text.replace(/\s+/g, ' ').trim();
    markdown += `---\n\n**核心要闻**\n\n${text}\n\n`;
  }
  
  // 目录
  markdown += `---\n\n## 目录\n\n`;
  doc.querySelectorAll('.toc li').forEach(li => {
    const text = li.textContent.trim();
    if (text) {
      markdown += `- ${text}\n`;
    }
  });
  markdown += '\n';
  
  // 章节
  doc.querySelectorAll('.section').forEach(section => {
    const h2 = section.querySelector('.section-header h2');
    const icon = section.querySelector('.section-header .icon');
    if (h2) {
      markdown += `---\n\n## ${(icon?.textContent || '')}${h2.textContent.trim()}\n\n`;
    }
    
    section.querySelectorAll('.item').forEach(item => {
      const title = item.querySelector('.item-title');
      if (title) {
        const tag = title.querySelector('.tag');
        const tagText = tag ? `【${tag.textContent.trim()}】` : '';
        const titleText = title.textContent.replace(tag?.textContent || '', '').trim();
        markdown += `### ${tagText}${titleText}\n\n`;
      }
      
      const body = item.querySelector('.item-body');
      if (body) {
        let text = body.innerHTML;
        text = text.replace(/<strong>([^<]+)<\/strong>/g, '**$1**');
        text = text.replace(/<a href="([^"]+)"[^>]*>([^<]+)<\/a>/g, '[$2]($1)');
        text = text.replace(/<[^>]+>/g, '');
        text = text.replace(/\s+/g, ' ').trim();
        markdown += text + '\n\n';
      }
      
      const stats = item.querySelectorAll('.stat');
      if (stats.length > 0) {
        const statTexts = [];
        stats.forEach(s => {
          const parts = s.textContent.split(/\s+/);
          if (parts.length >= 2) {
            const label = parts[0];
            const value = s.querySelector('em')?.textContent || parts.slice(1).join(' ');
            statTexts.push(`**${label}** *${value}*`);
          }
        });
        if (statTexts.length > 0) {
          markdown += statTexts.join(' · ') + '\n\n';
        }
      }
      
      const source = item.querySelector('.item-source');
      if (source) {
        let text = source.innerHTML;
        text = text.replace(/<a href="([^"]+)"[^>]*>([^<]+)<\/a>/g, '[$2]($1)');
        text = text.replace(/<[^>]+>/g, '').trim();
        // 移除已有的"来源："前缀，避免重复
        text = text.replace(/^来源：/, '');
        markdown += `来源：${text}\n\n`;
      }
      
      const insight = item.querySelector('.insight-box .insight-content');
      if (insight) {
        let text = insight.innerHTML;
        text = text.replace(/<strong>([^<]+)<\/strong>/g, '**$1**');
        text = text.replace(/<[^>]+>/g, '');
        text = text.replace(/\s+/g, ' ').trim();
        markdown += `> **💡 深度洞察**\n>\n> ${text.replace(/\n/g, '\n> ')}\n\n`;
      }
      
      markdown += '---\n\n';
    });
    
    // 处理 GitHub 项目（.gh-item）
    section.querySelectorAll('.gh-item').forEach(ghItem => {
      const name = ghItem.querySelector('.gh-name');
      const desc = ghItem.querySelector('.gh-desc');
      const star = ghItem.querySelector('.gh-star');
      
      if (name) {
        const link = name.querySelector('a');
        if (link) {
          markdown += `### [${link.textContent.trim()}](${link.href})\n\n`;
        } else {
          markdown += `### ${name.textContent.trim()}\n\n`;
        }
      }
      if (desc) {
        markdown += `${desc.textContent.trim()}\n\n`;
      }
      if (star) {
        markdown += `${star.textContent.trim()}\n\n`;
      }
      markdown += '---\n\n';
    });
  });
  
  // 处理页脚
  const footer = doc.querySelector('.footer');
  if (footer) {
    markdown += `\n---\n\n`;
    const brand = footer.querySelector('.footer-brand');
    if (brand) {
      markdown += `**${brand.textContent.trim()}**\n\n`;
    }
    footer.querySelectorAll('p').forEach((p, i) => {
      if (i > 0) { // 跳过 footer-brand
        let text = p.innerHTML;
        text = text.replace(/<strong>([^<]+)<\/strong>/g, '**$1**');
        text = text.replace(/<[^>]+>/g, '');
        text = text.trim();
        if (text) {
          markdown += `${text}\n\n`;
        }
      }
    });
  }
  
  return markdown;
}

// 应用主题样式
function applyTheme(html, themeId) {
  const theme = THEMES[themeId] || THEMES.claude;
  const style = theme.styles;
  
  const dom = new JSDOM(html);
  const doc = dom.window.document;
  
  Object.keys(style).forEach((selector) => {
    if (selector === 'container') return;
    try {
      doc.querySelectorAll(selector).forEach(el => {
        if (selector === 'code' && el.parentElement?.tagName === 'PRE') return;
        const currentStyle = el.getAttribute('style') || '';
        el.setAttribute('style', currentStyle + '; ' + style[selector]);
      });
    } catch (e) {}
  });
  
  doc.querySelectorAll('ul, ol').forEach(el => {
    const type = el.tagName === 'UL' ? 'disc' : 'decimal';
    const currentStyle = el.getAttribute('style') || '';
    el.setAttribute('style', `${currentStyle}; list-style-type: ${type} !important; list-style-position: outside;`);
  });
  
  const container = doc.createElement('section');
  container.setAttribute('style', style.container);
  container.innerHTML = doc.body.innerHTML;
  
  return container.outerHTML;
}

// 微信兼容性处理
function makeWeChatCompatible(html, themeId) {
  const theme = THEMES[themeId] || THEMES.claude;
  const dom = new JSDOM(html);
  const doc = dom.window.document;
  
  const fontMatch = theme.styles.container.match(/font-family:\s*([^;]+);/);
  const colorMatch = theme.styles.container.match(/color:\s*([^!]+)!important/);
  const sizeMatch = theme.styles.container.match(/font-size:\s*([^;]+);/);
  const lineHeightMatch = theme.styles.container.match(/line-height:\s*([^!]+)!important/);
  
  doc.querySelectorAll('p, li, h1, h2, h3, h4, blockquote, span, td, th').forEach(node => {
    if (node.tagName === 'SPAN' && node.closest('pre, code')) return;
    let currentStyle = node.getAttribute('style') || '';
    
    if (fontMatch && !currentStyle.includes('font-family:')) {
      currentStyle += ` font-family: ${fontMatch[1]};`;
    }
    if (lineHeightMatch && !currentStyle.includes('line-height:')) {
      currentStyle += ` line-height: ${lineHeightMatch[1]};`;
    }
    if (sizeMatch && !currentStyle.includes('font-size:') && ['P', 'LI', 'BLOCKQUOTE', 'SPAN', 'TD', 'TH'].includes(node.tagName)) {
      currentStyle += ` font-size: ${sizeMatch[1]};`;
    }
    if (colorMatch && !currentStyle.includes('color:')) {
      currentStyle += ` color: ${colorMatch[1]};`;
    }
    
    node.setAttribute('style', currentStyle.trim());
  });
  
  // 去除微信域名链接（WeChat API 不允许 mp.weixin.qq.com 链接，否则报 45166 invalid content hint）
  let result = doc.body.innerHTML;
  result = result.replace(/href="https?:\/\/mp\.weixin\.qq\.com\/[^"]*"/g, 'href="#"');
  return result;
}

// 微信公众号 API
const WECHAT_APPID = 'wxc0acff84c3ba27b0';
const WECHAT_SECRET = '7af6a2678e804ecbe3425f0889c1d28d';

async function getAccessToken() {
  const url = `https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${WECHAT_APPID}&secret=${WECHAT_SECRET}`;
  const response = await fetch(url);
  const data = await response.json();
  if (data.errcode) throw new Error(`获取 access_token 失败: ${data.errmsg}`);
  return data.access_token;
}

async function uploadImage(accessToken, imagePath) {
  const { readFileSync } = await import('fs');
  const imageBuffer = readFileSync(imagePath);
  
  const url = `https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=${accessToken}&type=image`;
  const formData = new FormData();
  const blob = new Blob([imageBuffer], { type: 'image/jpeg' });
  formData.append('media', blob, basename(imagePath));
  
  const response = await fetch(url, { method: 'POST', body: formData });
  const data = await response.json();
  if (data.errcode) throw new Error(`上传图片失败: ${data.errmsg}`);
  return data.media_id;
}

async function createDraft(accessToken, title, content, coverMediaId, digest) {
  const url = `https://api.weixin.qq.com/cgi-bin/draft/add?access_token=${accessToken}`;

  const articles = {
    articles: [{
      title: title,
      author: 'Tech Daily Brief',
      digest: (digest || title).substring(0, 120),
      content: content,
      thumb_media_id: coverMediaId,
      need_open_comment: 1,
      only_fans_can_comment: 0
    }]
  };
  
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(articles)
  });
  
  const data = await response.json();
  if (data.errcode) throw new Error(`创建草稿失败: ${data.errmsg}`);
  return data.media_id;
}

// 主函数
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 1) {
    console.error('用法: node publish-daily.mjs <input.html> [theme]');
    console.error('\n可用主题: nyt, claude, wechat');
    process.exit(1);
  }
  
  const inputFile = resolve(args[0]);
  const themeId = args[1] || 'nyt';
  const coverImage = args[2] || resolve('/Users/yangliu/Desktop/cover.png');
  
  console.log(`📄 读取日报: ${inputFile}`);
  const html = readFileSync(inputFile, 'utf-8');
  
  console.log('📝 转换为 Markdown...');
  const markdown = htmlToMarkdown(html);
  
  // 保存 Markdown（可选）
  const mdFile = inputFile.replace(/\.html$/, '.md');
  writeFileSync(mdFile, markdown, 'utf-8');
  console.log(`💾 Markdown: ${mdFile}`);
  
  console.log(`🎨 应用主题: ${themeId}`);
  const renderedHtml = md.render(markdown);
  const themedHtml = applyTheme(renderedHtml, themeId);
  
  console.log('📱 微信兼容处理...');
  const wechatHtml = makeWeChatCompatible(themedHtml, themeId);
  
  // 保存微信 HTML（可选）
  const wechatFile = inputFile.replace(/\.html$/, '-wechat.html');
  writeFileSync(wechatFile, wechatHtml, 'utf-8');
  console.log(`💾 微信 HTML: ${wechatFile}`);
  
  // 提取标题
  const dateMatch = html.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
  const title = dateMatch ? `科技资讯日报｜${dateMatch[2]}月${dateMatch[3]}日` : '科技资讯日报';

  // 提取摘要（核心要闻）
  const dom = new JSDOM(html);
  const summaryCard = dom.window.document.querySelector('.summary-card');
  let digest = title;
  if (summaryCard) {
    digest = summaryCard.textContent
      .replace(/\s+/g, ' ')
      .trim()
      .substring(0, 120);
  }

  console.log('🔑 获取微信 access_token...');
  const accessToken = await getAccessToken();

  console.log(`📷 上传封面图...`);
  const mediaId = await uploadImage(accessToken, coverImage);

  console.log('📝 创建草稿...');
  const draftMediaId = await createDraft(accessToken, title, wechatHtml, mediaId, digest);
  
  console.log('\n✅ 发布成功！');
  console.log(`📰 标题: ${title}`);
  console.log(`📎 media_id: ${draftMediaId}`);
  console.log('📱 请登录微信公众号后台查看草稿');
}

main().catch(err => {
  console.error('❌ 错误:', err);
  process.exit(1);
});
