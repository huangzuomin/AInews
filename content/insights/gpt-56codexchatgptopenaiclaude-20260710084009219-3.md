---
title: "GPT-5.6「太阳系」全家桶上线，Codex并入ChatGPT，OpenAI这次要干翻Claude？"
date: 2026-07-10T08:40:09+08:00
draft: false
featured_image: images/default (8).png
summary: "OpenAI今日全量发布GPT-5.6三款模型，性能价格双杀Claude Fable 5；同时将Codex融入ChatGPT，推出跨App自主Agent“ChatGPT Work”。最令人震惊的是，旗舰模型Sol能自动训练出小弟Luna，AI自我进化时代拉开序幕。"
tags: 
  - "GPT-5.6"
  - OpenAI
  - ChatGPT Work
  - AI Agent
  - Claude Fable 5
main_topics: 
  - 前沿模型与算法
---

TL;DR：
>OpenAI今天一口气放出GPT-5.6三兄弟——Sol（太阳）、Terra（大地）、Luna（月亮），性能全面碾压Claude Fable 5，价格却只要一半。同时Codex正式退役，ChatGPT Work登场，一个能跨App自主干活的AI Agent。最恐怖的是，大哥Sol亲自训练出了小弟Luna，AI开始自己造AI了。

重磅消息不等人，直接开讲。

今天，OpenAI把GPT-5.6全家桶端到了所有人面前。Sol、Terra、Luna，一个不少[^1]。与此同时，ChatGPT桌面端完成重大升级，Codex彻底消失，ChatGPT Work上线——一个能跨App自主干活的Agent，真正意义上的“AI打工神器”[^2]。从之前Facebook上的创业新闻也能看出，这次OpenAI准备大规模扩展预览权限[^6]。

如果你还没反应过来，简单说：Claude Fable 5刚被捧上神坛，OpenAI反手就给了它一记组合拳。

### 价格屠夫，性能还碾压

先看Sol。OpenAI管它叫“迄今最强编程模型”，这话不是吹的。

在Artificial Analysis Coding Agent Index上，Sol拿下80分，成为新SOTA，比Claude Fable 5高2.8分[^1]。更离谱的是，输出token不到一半，耗时不到一半，成本还低约1/3。在Agents' Last Exam上，Sol豪取53.6%，甩开Fable 5整整13.1分。Terminal-Bench 2.1上88.8%，Ultra模式飙到91.9%[^1]。第三方评测机构也确认，Sol在多项编码和Agents指标上领先[^3][^5]。

但真正让人拍桌子的，是价格。

Fable 5每百万token输入$10、输出$50，Sol直接对折，只要$5和$30。Terra再砍半，Luna干脆只要$1和$6[^1]。这哪是价格战，这是直接把对手的桌子掀了。而且不是只有旗舰强，Terra略高于Fable 5，Luna也越过了Opus 4.8，各自的成本都只有对手的1/4左右。

同样的活，OpenAI这次用更小的代价干完了。

### 四个Agent一起上，Ultra模式有多狂？

大模型不是万能的，但四个大模型可能是。

GPT-5.6新增了Ultra档：默认一次派出四个Agent并行开工，重活儿还能上到十六个[^1]。在BrowseComp、SEC-Bench Pro、Terminal-Bench 2.1上，加了并行Agent之后，分数和耗时曲线整体向左上移动——分更高，还更快。这相当于你一个人写代码，旁边还站着三个同事随时搭把手。

另外，GPT-5.6补上了过去的一大短板——设计审美。它能自己去看渲染结果，检查视觉和功能问题，然后动手修复。从航海小游戏到博物馆网站，设计能力质的飞跃[^1]。看来AI美工也要开始慌了。

### AI训练AI，这可能是最细思极恐的细节

如果说性能价格只是常规升级，那接下来的这个，才是真正让人后背发凉的。

OpenAI透露，GPT-5.6是他们迄今最能加速AI研究的模型。内部研究员用它诊断故障、优化训练、跑实验。在GPT-5.6内测期间，每位活跃研究员的日均输出token量，是GPT-5.5最高水平的两倍多[^1]。过去半年，内部编程推理的算力份额涨了100倍，Agent的token用量涨了约22倍。

但最科幻的还不是这些数字。

发布会直播中，研究员透露了一个细节：全家桶里最小的Luna，是老大哥Sol后训练出来的[^1]！过程很简单：输入大致的需求，Sol就开始自己找训练配置、挑选GPU、启动脚本、确认跑通，从头到尾包圆了整个后训练流程。这活儿放在过去，是一整队资深研究员的工作。而现在，那个“自动化研究员”，真的已经很近了。

在一套衡量“递归自我改进”的内部评测上，Sol比GPT-5.5高出16.2分[^1]。OpenAI正在用AI，加速造下一个更强的AI。AI永动机，从概念变成现实。有国内媒体感叹，普通用户可能暂时无法直接用上这些高端特性[^4]。

### ChatGPT Work：你的电脑，它的工位

同在今天，ChatGPT桌面端真正变身“超级应用”。内置浏览器和Computer Use，可以直接调用你本地的文件和应用，替你点击、打字、搬文件[^2]。更重磅的是，原来的Codex应用彻底并入ChatGPT，从此你只需要一个应用。

配合GPT-5.6，ChatGPT Work是一个能跨App和文件自主干活的Agent，能盯着一个项目连续跑好几个小时，把目标变成成品。这是OpenAI版的“Claude Cowork”，甚至还能通过手机端远程操控，电脑不在身边也能推进工作[^2]。Reddit上的开发者们已经开始热烈讨论这次升级的实际体验[^7]。

从预览到全量上线，不过半个月。从追赶到反超，OpenAI只用了一次发布会。

但真正让人后背发凉的，不是那几张榜单，是Sol亲手训出了Luna。当AI开始训练AI，时间就不再是线性的了。竞赛的终点线正在消失，剩下的只是下一个版本号。

[^1]: GPT-5.6 · OpenAI (2026/7/10) · https://openai.com/index/gpt-5-6/
[^2]: ChatGPT for your most ambitious work · OpenAI (2026/7/10) · https://openai.com/index/chatgpt-for-your-most-ambitious-work/
[^3]: GPT-5.6 vs Claude Fable 5: The Real Comparison for PMs · Vibe Coding Academy (2026) · https://www.vibecodingacademy.ai/blog/gpt-5-6-vs-claude-fable-5-product-managers
[^4]: GPT-5.6突然上线：比Mythos强，普通用户彻底无缘 · 知乎 (2026/7/10) · https://zhuanlan.zhihu.com/p/2054121932627489994
[^5]: GPT-5.6 vs Claude Fable 5: Which Model to Choose 2026 · Layer3 Labs (2026/7/10) · https://www.layer3labs.io/comparisons/gpt-5-6-vs-claude-fable-5
[^6]: ChatGPT maker OpenAI has announced that GPT-5.6 Sol, Terra and Luna will launch publicly this Thursday · Indian Startup News / Facebook (2026/7/10) · https://www.facebook.com/indianstartupnews/posts/chatgpt-maker-openai-has-announced-that-gpt-56-sol-terra-and-luna-will-launch-pu/1658068652619360
[^7]: OpenAI 5.6 vs. Fable 5 · Reddit r/codex (2026) · https://www.reddit.com/r/codex/comments/1u3bv7y/openai_56_vs_fable_5
