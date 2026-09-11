# neican.ai 编辑部值班手册（RUNBOOK）

本站内容生产与运维由 ZCode 担任总编辑。本手册是每个值班班次的唯一执行依据。

## 信源

主信源（选题雷达）：aihot.news 精选 API，匿名无需 key：

```
curl -s "https://aihot.news/api/v1/items?mode=selected&window=24h&limit=30"
```

返回 JSON：`items[]`，字段含 `score`（质量分）、`title`、`summary`（事实摘要）、
`links.original`（原文链接）、`category`（ai-models/ai-products/industry/paper/tip）、`reason`。

合规红线：aihot 仅作发现与排序信号；**成稿一律基于 `links.original` 指向的原始信源**
撰写，文末引用原文链接。禁止照抄 aihot 摘要成文。

## 去重规则

写稿前必须查重：对候选条目的标题关键词（如 `V4.1-Flash`、`RSA-260`）在
`content/insights/` 与 `content/newspaper/`、`content/morningnews/` 中 grep。
已覆盖的事件不得重复成文（日报/早报综述引用不算重复）。

## 成稿规范（洞察 insights/）

文件名：`slug-YYYYMMDDHHMMSSNNN-0.md`（slug 用英文连字符小写）。

frontmatter 必填字段（参考现有文件）：

```
---
title: 中文主标题（可带副题）
date: YYYY-MM-DDTHH:MM:SS+08:00
draft: false
featured_image: "/images/ai-report-default.png"
summary: "100-160字摘要，进首页列表与SEO description"
tags: 3-5 个
main_topics: 1-2 个（用站内已有分类：模型与算法/产业生态与商业版图/企业级AI与数字化/安全与地缘政治/AI伦理与治理/前沿研究/社会影响与未来工作）
---
```

正文结构：`TL;DR：` 引用块（一句话判断）→ 2-3 个 `###` 小节（事实+分析，禁止编造数字）
→ `### 展望` → `## 引用`（脚注列出 `links.original` 原文链接 + 检索日期）。

QC 清单（发布前逐项过）：
1. 每个事实都能对应到源摘要或原文，不虚构数字、引语、事件细节
2. 无中英文夹杂残留、无占位符
3. summary 长度合规、tags/main_topics 存在
4. 引用链接来自 `links.original`
5. 文件名与 frontmatter 日期一致

## 班次 SOP

### 早报班（每日 06:40）
1. 拉取 aihot `mode=selected&window=24h`，取分数最高且过去24h未覆盖的 8-10 条
2. 生成 `content/morningnews/YYYY-MM-DD-ai-YYYY-MM-DD-.md`（参考既有早报格式：
   title "AI早报 YYYY年MM月DD日"，main_topics: ["AI内参极速早报"]，导语 + 编号列表
   （每条一句话核心事实，粗体标题）+ 【今日总结】）
3. QC 后执行部署：`python newsroom/deploy.py "早报 YYYY-MM-DD"`

### 流水班（每日 09/13/17/21 点）
1. 拉取 aihot 24h 精选，查重后取未覆盖且 score≥70 的条目，写 2-5 篇洞察
2. 选题优先级：ai-models > industry/paper > ai-products > tip；同事件多源合并为一篇
3. QC 后执行部署：`python newsroom/deploy.py "洞察 N 篇：<主题列表>"`

### 日报班（每日 19:15）
1. 基于当日已发布的洞察文章 + aihot 当日精选，写当日日报
2. 生成 `content/newspaper/YYYY-MM-DD-MM-DD-.md`（title 格式
   "MM-DD日报|主题式标题"；结构：导语段 → ### 今日速览 4-5 条粗体要点 →
   2-3 个 ### 主线剖析 → **【今日总结】**；main_topics: ["AI内参日报"]）
3. 部署：`python newsroom/deploy.py "日报 YYYY-MM-DD"`

## 运维

- 部署即构建：`deploy.py` 会在 NAS 容器内跑 `hugo`，构建失败不会推送
- 验证上线：部署 2-3 分钟后 `curl -s https://www.neican.ai/` 检查新内容
- **部署卡住**：若推送后 10 分钟新内容仍未上线（Vercel 偶发卡队列，2026-09-10 实录），
  推空提交触发重新部署：在 NAS 上
  `cd /volume4/docker/hugo/hugo && git commit --allow-empty -m 'chore: trigger vercel redeploy' && git push`
  （deploy.py 会自动清无进程占用的 .git/index.lock；若提示 lock 且有 git 进程在跑，等一分钟再试）
- 广告：AdSense 自动广告已全局停用；文章页两个受控广告位代码已就位
  （`hugo.toml [params.adsense]`），启用与否不影响发布流程
- 站点停更超过 6 小时视为事故：优先排查本机是否开机、NAS SSH 是否可达
