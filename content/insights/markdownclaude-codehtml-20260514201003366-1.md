---
title: "别再用Markdown了？Claude Code工程师狂吹HTML，卡帕西也\"叛变\"了！"
date: 2026-05-14T20:10:03+08:00
draft: false
featured_image: "/newsimages/selected_image_2026-05-14_20-01-02.jpg\n"
summary: "Claude Code工程师Thariq Shihipar发文，力挺HTML作为AI Agent时代默认输出格式，认为Markdown在信息密度和交互性上已成瓶颈。大佬卡帕西也从\"视觉信息处理\"的角度表示赞同。这场\"格式之争\"背后，折射出AI Agent从\"文本协作\"迈向\"界面协作\"的深刻变革。"
tags: 
  - Markdown过时
  - HTML复兴
  - AI输出格式
  - Claude Code
  - 卡帕西
main_topics: 
  - AI Agent与自主系统
---

### TL;DR：
> 那个让AI写代码的Claude Code，它的工程师突然"反水"，说自己几乎不用Markdown了，现在更爱HTML。更离谱的是，连AI大佬卡帕西（Andrej Karpathy）也公开站台，表示自己已经习惯让AI直接输出HTML。这波操作，是要革了Markdown的命吗？

如果现在有人告诉你，那个被无数程序员奉为"写作圣经"的Markdown，可能要过时了，你会不会觉得他疯了？

但这事儿，还真不是空穴来风。

最近，Anthropic旗下Claude Code的工程师Thariq Shihipar，发了一篇小作文，标题就很有杀伤力：《Using Claude Code: The Unreasonable Effectiveness of HTML》。简单翻译一下就是——用Claude Code写HTML，效果离谱得有点不讲道理。[^1]

他在文章里直接"摊牌"了："说实话，我现在几乎完全不用Markdown了。"[^2]

这话一出，整个AI开发者圈都炸了锅。

### 为什么Markdown突然不香了？

咱们先别急着站队，听听Thariq怎么说。

在他看来，Markdown不是不好，是它太"老实"了。当AI只是简单地回答"是或否"时，Markdown够用。但当AI Agent开始处理超长代码、复杂规划、多轮交互时，Markdown那点排版能力，就像用自行车去拉火车——有点力不从心了。

他举了个扎心的例子：**上百行的Markdown文档，连他这个写的人都不愿意读，更别说团队里的其他人了。**

你想想，一个AI辛辛苦苦生成的万字规划，结果因为格式太难看，被人类直接划走，这得有多冤？

这时候，HTML的优势就出来了。

### HTML凭啥能"逆袭"？这五个理由够不够？

Thariq和他的拥趸们总结了一套"HTML真香定律"，咱们给大伙儿盘一盘：

1.  **信息密度爆表**：Markdown能干的（标题、列表），HTML都能干。Markdown干不了的（表格、SVG插图、交互式滑块、颜色代码），HTML照样信手拈来。Thariq甚至放出狠话："凡Claude能读懂的信息，几乎都能用HTML高效呈现。"[^1]

2.  **阅读体验起飞**：当文档变长，HTML就开启了"美颜模式"。它可以通过标签页、交互式图表、超链接等，把长文档变得像网页一样好刷。甚至还能自适应手机屏幕，让你在蹲坑时也能流畅阅读。

3.  **分享起来贼方便**：Markdown文件发给别人，对方还得找个支持它的编辑器。但HTML文件直接丢到服务器上，生成一个链接，发到群里，同事用手机浏览器就能打开。这体验，属于是降维打击了。

4.  **双向交互，玩出花**：HTML最骚的操作是，它不仅能看，还能玩。Thariq提到，他经常让Claude生成带滑块、旋钮的HTML页面，用来调试设计参数。调完之后，还能一键把参数复制出来，贴回Claude Code继续干活。

5.  **创作体验更愉悦**：这一点Thariq说得挺走心——用HTML做东西，比用Markdown"爽"多了。这种参与感和成就感，本身就值得选择它。

### 卡帕西：别光说格式，AI输出就该是"视觉高速公路"

这场"格式之争"的火，还烧到了AI圈另一位大佬——Andrej Karpathy（卡帕西）身上。这位前特斯拉AI总监、OpenAI创始成员，最近也公开力挺HTML。

他提出了一个更宏大的视角：**AI的输出形式，不应该再局限于"文本"。**

卡帕西认为，人类大脑约有三分之一都在处理视觉信息，视觉就像一条通往大脑的"十车道高速公路"。[^3] 而纯文本阅读，成本最高。

他甚至画了一条AI输出形式的演（偷）化（懒）路径：

1.  纯文本 -> 费眼
2.  Markdown -> 稍微好点，但还是文本思维
3.  HTML -> 开始具备布局、图形、动画
4.  ...（省略无数中间步骤）
n.  由AI直接生成的交互式视频 / 模拟系统

在他看来，**HTML不是终点，但它是我们从"文档思维"走向"界面思维"的关键一步。** 换句话说，未来的AI可能不再只是给你"写文章"，而是直接给你"造应用"。

### 但是，事情真有那么完美吗？

当然不是。

虽然HTML听起来很香，但在开发者社区里，质疑的声音也不少。

**最大的痛点在于：可编辑性。**
Markdown轻量、直接，人类开发者可以随时"下场"手动修改。但HTML结构复杂，如果开发者想自己改点内容，还得先搞懂那一堆标签和样式，甚至需要重新给AI发Prompt。这让原本"共同创作"的模式，变成了一种"单向输出"。

**第二个现实问题是：人人都得变成前端？**
不是所有软件工程师都懂HTML布局和CSS。如果HTML成为默认格式，会不会变成一种新的"技术壁垒"？

### 写在最后：Markdown不是被取代，而是被"升级"了

说到底，这场争论的本质，不是谁要干掉谁，而是**AI Agent时代，人与机器的协作模式正在发生巨变。**

以前，我们期待AI当个"好秘书"，能写文档、查资料。
现在，我们期待AI当个"好搭档"，能看图、做界面、甚至直接操作软件。

当AI的输出不再是"文本"，而是"界面"时，Markdown这个为"文本"而生的格式，的确显得有些局促了。

所以，Markdown真的会消失吗？
大概率不会。它依然会是人类写作和轻量协作的最优解。
但在AI Agent的世界里，HTML可能正在成为新的"通用语言"。

至于你？要不今晚试试，在提问的最后加一句："以HTML的形式组织回答"？

欢迎在评论区分享你的"HTML初体验"。

### 引用
[^1]: Using Claude Code: The Unreasonable Effectiveness of HTML (https://thariqs.github.io/html-effectiveness)
[^2]: Anthropic工程师Thariq Shihipar的推文·X（Twitter）(https://x.com/trq212/status/2052809885763747935)
[^3]: 卡帕西公开支持HTML输出的相关讨论·Hacker News (https://news.ycombinator.com/item?id=48071940)
[^4]: 960万人围观！Claude Code工程师谈HTML“复兴”：Agent时代·知乎 (https://zhuanlan.zhihu.com/p/2037623843444012630)
[^5]: Claude Code团队揭秘：AI时代放弃Markdown转用HTML的实战指南·知乎 (https://zhuanlan.zhihu.com/p/2036771385641529388)
[^6]: Claude团队暴论: 去Markdown,HTM才是AI Agent最佳交互格式·网易 (https://www.163.com/dy/article/KSKN6MLI05566Y1D.html)
[^7]: The Unreasonable Effectiveness of HTML·Simon Willison (https://simonwillison.net/2026/May/8/unreasonable-effectiveness-of-html/)
[^8]: Markdown was a mistake for agent output? A Claude Code engineer just proved it·Medium (https://medium.com/@rentierdigital/markdown-was-a-mistake-for-agent-output-a-claude-code-engineer-just-proved-it-454b78971cc4)
