---
title: 离大谱！Anthropic把Claude Code源码当“福利”发了：全能助手Kairos提前“被迫营业”
date: 2026-03-31T20:10:08+08:00
draft: false
featured_image: "/newsimages/selected_image_YYYY-03-Mar 31, 2026_20-01-42-117.jpg"
summary: Anthropic近期频发“低级失误”，Claude Code源码因npm包配置错误惨遭泄露，暴露了代号“Kairos”的全能Agent助手模式。这家主打安全人设的AI巨头正面临严重的组织成熟度质疑，而在源码泄露背后，其想要统治用户桌面的野心也彻底浮出水面。
tags: 
  - Claude Code
  - Anthropic
  - 源码泄露
  - AI Agent
  - Kairos
main_topics: 
  - AI与软件工程 (AI & Software Engineering)
---

### TL;DR：
> 顶级AI大厂Anthropic在发布npm包时忘了关掉source map，直接把Claude Code的源码“开源”给了全世界。大家顺藤摸瓜挖出了代号“Kairos”的全能助手模式——原来这哥们儿不只想帮你写代码，它还想住进你的电脑里，化身24小时不打烊的“贾维斯”。

就在大家还以为Claude Code只是个帮你敲代码、改Bug的“超级终端”时，Anthropic自己搞了个大新闻。

这次不是发了什么炸裂的新论文，也不是模型跑分又屠了榜，而是他们在发布npm安装包时，竟然把`cli.js.map`文件给顺手带了出来。[^1] 

稍微懂点前端的朋友都知道，source map通常是用来调试的，但Anthropic这次发的map文件里，居然直接包含了实打实的`sourcesContent`。**这就好比你以为自己买了个加密保险箱，结果卖家发货时连带着把内部构造图和备用钥匙全贴在了箱子外壳上。** 没有任何黑客参与，只要你会用`npm install`，这份价值连城的源码就躺在你的硬盘里了。

### 技术大揭秘：藏在源码里的“超级Agent”

如果只是代码泄露也就罢了，毕竟客户端逻辑不等于云端模型。但这次泄露最劲爆的地方在于，源码里藏着一个名为**KAIROS**的Feature Flag。

在源码注释里，工程师甚至直接写着“KAIROS (assistant mode)”。[^1] 翻成大白话，这就是Claude Code的“究极进化形态”。根据泄露的配置描述，Kairos模式不仅有自定义的系统提示词，还会切换到一种更简洁的助手视图。

它到底能干啥？看看这些泄露的模块名就知道了：
*   **MCP Channel Notifications**：意味着它能接管你的社交软件，你发个消息，它就开始干活。
*   **KAIROS_GITHUB_WEBHOOKS**：这哥们儿能实时盯着GitHub，代码一提交，它自动响应。
*   **Cron & Scheduled Tasks**：它支持定时检查和回访，是个真正的“24/7在线劳模”。

> “OpenClaw管得了的Kairos要管，OpenClaw管不了的Kairos更要管。”
> —— 这哪里是编程助手？这分明是想彻底接管你的操作系统，做一个能指挥全局的Agent系统。

原本我们以为Claude Code只是把Claude塞进终端，现在看来，Anthropic的野心大得吓人：它想取代的不仅是你的IDE，它甚至想把你的整个工作流都装进它的闭环里。

### 行业“地震”：谁在灯下黑？

这已经不是Anthropic最近第一次“漏水”了。就在几天前，他们的CMS（内容管理系统）也因为配置失误，泄露了包括下一代模型**Mythos**在内的3000多个内部资产。[^2]

作为一家以“安全（Safety）”为立身之本、估值千亿美金的巨头，这种连初级程序员都可能避免的“卫生习惯问题”，简直是把人设按在地上摩擦。企业客户现在可能都在犯嘀咕：**你连自己的npm包和服务器权限都管不好，我怎么放心把核心代码库交给你托管？**

更讽刺的是，Anthropic上个月刚发布了`Claude Code Security`工具，专门帮开发者扫漏洞。[^2] 结果自家工程师用着最强的Opus模型，却没扫出发布脚本里的低级失误，这大概就是传说中的“医不自医”。

### 未来预测：人设崩了，护城河还在吗？

虽然源码泄露让竞争对手看清了Anthropic的Agent逻辑，甚至可能引发一波“复刻潮”，但说Anthropic会因此倒闭还为时尚早。

毕竟，**你可以抄走它的“壳”，但拿不走它的“魂”。** 云端的基础设施、推理成本的优化、以及那套价值25000个Token的系统提示词（System Prompt），这些才是真正的护城河。[^3]

不过，这件事对Anthropic最致命的打击在于**IPO的想象空间**。资本市场最看重的是管理成熟度，一个在2026年还因为source map泄露核心产品逻辑的公司，在投资人眼里多少带点“草台班子”的味道。[^4]

尤其是在他们刚刚修改了《负责任扩展政策》（RSP 3.0）、取消了“若风险不可控就暂停训练”的硬约束之后，外界对其“安全优先”的承诺早已打上了问号。[^4] 现在的Anthropic，更像是一个在激烈的AI军备竞赛中，一边狂奔一边掉装备的“焦虑巨人”。

接下来的问题是：既然Kairos已经提前“被迫曝光”，Anthropic是会破罐子破摔加速上线，还是会躲进小黑屋重新修补那个摇摇欲坠的保险箱？

## 引用
[^1]: [Claude Code源码泄露，下一个王牌提前曝光](https://mp.weixin.qq.com/s/5617Ldm_lV5E-gY0Onlzig) · 字母AI · 苗正 (2026/03/31) · 检索日期2026/03/31
[^2]: [数据泄露！Anthropic未发布模型细节曝光- AI](https://www.bianews.com/news/details?id=234863) · 鞭牛士 (2026/03/27) · 检索日期2026/03/31
[^3]: [Claude 25000字提示词泄漏，我看到了AI的秘密，和AI的笑话](https://m.36kr.com/p/3290378020644357) · 36氪 · 太平洋科技 (2026/03/28) · 检索日期2026/03/31
[^4]: [Anthropic泄露背后：AI安全承诺的破产与重构](https://finance.sina.cn/stock/jdts/2026-03-28/detail-inhspryv7488537.d.html?oid=800&vt=4&cid=76993&node_id=76993) · 新浪财经 (2026/03/28) · 检索日期2026/03/31
[^5]: [Anthropic的大規模『Claude Mythos』泄露事件導致軟件名稱](https://news.futunn.com/hk/post/70748741/anthropic-s-massive-claude-mythos-leak-sends-software-names-and) · 富途牛牛 (2026/03/27) · 检索日期2026/03/31
