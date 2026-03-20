---
title: 凌晨两点被窝“投喂”Bug？Claude Code支持Telegram遥控，AI编程彻底“龙虾化”了！
date: 2026-03-20T16:40:05+08:00
draft: false
featured_image: "/newsimages/selected_image_YYYY-03-Mar 20, 2026_16-32-18-783.jpg"
summary: 本文深度解析了 Anthropic 旗下 Claude Code 新推出的 Channels 功能。该功能允许开发者通过 Telegram 和 Discord 远程控制 AI 编写代码，标志着 AI 编程工具正式迈入“远程遥控”与“异步协作”的“龙虾化”时代。
tags: 
  - Claude Code
  - AI 编程
  - 龙虾化
  - MCP 协议
  - 赛博搬砖
main_topics: 
  - AI与软件工程 (AI & Software Engineering)
---

### TL;DR：
> 别再盯着终端屏幕抠代码了！Claude Code 新增 Channels 功能，支持通过 Telegram 和 Discord 远程“发号施令”。只要在手机上给 AI 递个话，家里的电脑就能自动搬砖。从此，程序员终于实现了“人在马桶坐，代码天上来”的带薪摸鱼（或半夜被迫营业）新境界。

程序员的终极梦想是什么？不是年薪百万，而是“我还没到工位，活儿已经干完了”。

就在这两天，Anthropic 旗下的 AI 编程“悍将” Claude Code 又整了个大活。其工程师 Thariq Shihipar 宣布，Claude Code 正式上线 **Channels 功能**。简单来说，就是给你的 AI 编程助手配了个“对讲机”，首批支持 Telegram 和 Discord。[^1]

这意味着，那个曾经只能锁死在终端里的“黑窗口”工具，现在终于长腿跑到了你的手机里。这种“通过即时通讯软件远程遥控 AI 搬砖”的模式，被圈内戏称为 **“龙虾化”（Lobster-ization）**——致敬了那个把这种交互模式带火的开源项目 OpenClaw（其 Logo 正是一只龙虾）。

### 赛博忠犬：凌晨两点的“灵光一闪”有救了

想象一下这个扎心的场景：凌晨两点，你刚躺下准备进入梦乡，突然脑子里蹦出一个绝妙的重构方案，或者想起下午写的代码有个致命的逻辑漏洞。

以前的你：挣扎着爬起来，打开电脑，等待开机，在蓝光刺激下彻底失眠。
现在的你：翻身摸出手机，打开 Telegram 给 Claude 发条消息：“嘿，把支付模块的那个风控逻辑改一下，加个异常捕获，顺便把测试跑了。”

几秒钟后，你放在书房的 Mac Mini 悄然亮屏。Claude Code 就像一只永不睡觉的“赛博忠犬”，立刻开始翻阅项目、修改代码、运行单元测试。等你第二天慢悠悠吃完早餐打开 GitHub，一个注释清晰、测试全绿的 Pull Request 已经静静地躺在那儿等你了。[^2]

这就是所谓的**“氛围编程”**：你只管输出意志，剩下的脏活累活，AI 在后台帮你默默搞定。

### 技术大揭秘：它是怎么“偷跑”进你手机的？

很多小伙伴可能会问：这不就是个远程桌面吗？还真不是。

这背后的功臣是一个叫 **MCP（模型上下文协议）** 的“万能插座”。[^4] Anthropic 去年底开源了这个标准，旨在解决 AI 与各种工具对接时的“适配器难题”。

这次的 Channels 功能，本质上就是一个 MCP server。它的操作逻辑非常“极客”：
1. **安装插件**：在终端敲下一行 `/plugin install telegram@claude-plugins-official`。
2. **安全配对**：配置一个 Bot，设置白名单（毕竟你也不想路人甲在群里发条消息就黑了你的电脑）。
3. **一键启动**：带上 `--channels` 参数运行，通道就此打通。

好玩的是，这种交互非常“拟人”。当你通过 Telegram 下达任务时，对话框会显示“正在输入…”，这提示 Claude 已经开始在你的本地环境里翻箱倒柜了。它甚至能把运行结果、报错截图甚至生成的文件（50MB 以内）直接回传给你。[^1]

> **调侃式点评**：这种“已读且正在狂写”的既视感，比催甲方打款时的反馈感强多了。

### 行业“地震”：AI 交互的“窗口时代”要终结了？

在此之前，大家用 AI 还是习惯于“打开网页 -> 输入 Prompt -> 复制粘贴”。但 Anthropic 最近的一系列动作（Dispatch 功能、百万级上下文、现在的 Channels）都在传递一个信号：**AI 应当是“随时待命”的搭档，而不是一个需要特意点击的网页。**[^3][^5]

虽然目前 Claude Code 的这个龙虾化还处于“呼吸机模式”——即你的本地终端必须开着会话，通道才有效。相比之下，它的“老对手” OpenClaw 已经能做到本地守护进程 7×24 小时待命。[^1] 

但 Anthropic 的优势在于**“正规军”的安全性**。Channels 维护着独立的发送者 ID 白名单，验证粒度精准到人。即便你在一个几百人的 Discord 频道里调戏 AI，只要对方不在你的白名单上，Claude 就会优雅地装死，绝不执行任何越权指令。[^1]

当用户习惯了“发条消息就把活干了”，传统的对话框交互可能真的要成为历史了。龙虾化不是终点，而是一张通往“自主 Agent 时代”的入场券。

接下来的问题只有一个：既然 AI 已经能半夜帮我写代码了，那它什么时候能顺便帮我把明天的早会也开了？

## 引用
[^1]: [Claude Code也要龙虾化，凌晨床上发条消息，Mac Mini瞬间亮屏狂敲代码](https://www.163.com/dy/article/KOFITB7F05568W0A.html) · 36氪/新智元 · KingHZ 好困 (2026/03/20) · 检索日期 2026/03/20
[^2]: [Claude Code 概述- Claude Code Docs](https://code.claude.com/docs/zh-CN/overview) · Claude Code Docs · Anthropic (2026/03/20) · 检索日期 2026/03/20
[^3]: [Introducing Claude Code Channels](https://www.reddit.com/r/ClaudeCode/comments/1ryf2pd/introducing_claude_code_channels/) · Reddit (2026/03/20) · 检索日期 2026/03/20
[^4]: [AI产品经理进阶：万字深析大模型的MCP（上）](https://www.woshipm.com/ai/6190336.html) · 人人都是产品经理 · AI贾维斯 (2026/03/20) · 检索日期 2026/03/20
[^5]: [Claude一夜拆掉AI编程天花板！百万token上下文登场，吞下整个代码库](https://hub.baai.ac.cn/view/53134) · 智源社区/新智元 (2026/03/15) · 检索日期 2026/03/20
