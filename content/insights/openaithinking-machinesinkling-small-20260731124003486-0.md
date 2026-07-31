---
title: "翁荔刚回OpenAI，Thinking Machines反手开源Inkling-Small：员工跑路速度赶不上模型狂飙"
date: 2026-07-31T12:40:03+08:00
draft: false
featured_image: images/default (5).png
summary: "翁荔刚回OpenAI，前东家Thinking Machines就开源新模型Inkling-Small，体量缩小四倍，性能反超万亿参数前辈。更戏剧性的是，公司核心联创加速出走，但模型迭代速度却越来越快，上演了一出“人才跑路挡不住AI狂飙”的黑色幽默剧情。"
tags: 
  - AI模型
  - Thinking Machines
  - 开源
  - MoE
  - 人事变动
main_topics: 
  - 前沿模型与算法 (Frontier Models & Algorithms)
---

TL;DR：

> 翁荔刚确认回归OpenAI，Thinking Machines就甩出开源新模型Inkling-Small，体量缩小到前代的四分之一，性能却反超万亿参数的前辈。更离谱的是，这模型是用前代当老师“教”出来的，两周强化学习就完成了“学生超越老师”。员工加速跑路，模型加速迭代，这剧情比宫斗剧还精彩。

如果说AI圈最近有什么比“前OpenAI安全大将翁荔宣布回归”更炸裂的新闻，那一定是她刚离开的公司Thinking Machines的反手一击——在她回归消息确认的第三天，这家刚刚失去核心大将的创业公司，直接把新模型Inkling-Small的全量权重甩了出来，开源，随便下，不要钱。

剧情反转之快，堪比网飞爽剧。

### 剧情反转：大将刚回OpenAI，新模型反手开源

故事要从半个月前说起。Thinking Machines憋了17个月，终于交出了首个大模型Inkling，9750亿参数，开源即巅峰，在AI圈掀起巨浪。

但浪还没平息，联创之一翁荔就官宣离职。两天后，OpenAI证实了她的回归，带队攻坚“递归自我提升”（RSI）。

按照正常剧本，一家公司核心人物出走，怎么也得动荡一阵子。但Thinking Machines偏不。

就在翁荔回归消息公开后的第三天，他们直接把第二款模型Inkling-Small的全量权重甩了出来，开源，且附赠详细技术报告。

这操作，仿佛在说：“你走你的阳关道，我发我的新模型。”

### 技术暴击：四分之一体量，干翻万亿大哥

Inkling-Small有多猛？数据说话。

总参数2760亿，单次推理激活120亿，属于MoE架构。体量浓缩到前代Inkling的四分之一，但综合实力反而飙升。

在数学、推理、智能体编码、多模态等基准上，Inkling-Small直接对标甚至超越了Inkling和DeepSeek V4 Flash。在ARC-AGI-2上刷新开源SOTA，在HLE、Terminal-Bench、IFBench这三个核心指标上，每一FLOP换来的性能都高于Inkling。

说白了，就是花四分之一的算力，干出同样甚至更好的活。

官方曲线更是直观：Inkling-Small的性能曲线，从头到尾压在老大哥Inkling上面。一个体积只有四分之一的模型，在推理和智能体任务上把前代按在地板上摩擦。

怎么做到的？官方把后训练细节写得明明白白。

### 技术揭秘：学生怎么超越老师？

关键就两步。

第一步，拿老模型Inkling当老师，做on-policy蒸馏，先产出一个preview检查点。

第二步，从这个检查点开始，跑了整整两周的智能体编码强化学习。

两周，仅两周，学生反超老师。

这意味着什么？Thinking Machines跑通了一条能反复生产模型的产线。第一个模型是作品，第二个模型是产能证明。

Pytorch大神Horace He说得直白：“Inkling-Small根本不用举全村之力，直接沿用前代技术就成了。”

### 120亿激活，这才是真香定律

对绝大多数开发者来说，真正的惊喜是这120亿激活参数。

原版Inkling门槛高得离谱：BF16检查点最低要求2TB聚合显存，示例配置是8张B300或16张H200；就算换成NVFP4量化版，也要600GB起步。

Inkling-Small把这道门槛整个往下拽了一大截。

LMSYS评价很直接：276B总参数配12B激活，是强化学习的甜点位，LoRA和全参数训练都变得“够得着”。

实测显示，8张B200、TP8、NVFP4、batch size 1环境下，用SGLang在DSpark下达648 tok/s解码，不开也有288 tok/s。

以前只有大厂能玩的定制化模型，现在一个中等团队也有机会训成自己的东西。开源的精神，不就该这样吗？

### 人才加速流失，模型加速狂飙：AI的残酷真相

但最让人唏嘘的，是背后的剧情。

去年2月，Thinking Machines带着“OpenAI梦之队”六人名单开局：Mira Murati、John Schulman、Barret Zoph、翁荔、Andrew Tulloch、Luke Metz。20亿美元种子轮，120亿美元估值，剧本逆天。

如今，六人团只剩Murati和Schulman。走了的四个人里，Zoph和Metz先后回了OpenAI，现在翁荔成为第三个。

一家由OpenAI“叛逆者”组建的公司，核心骨干最终还是没能逃脱OpenAI的引力场。

但真正充满戏剧性的是团队面临动荡时的反应：沉默17个月后首发大模型；不到两周翁荔离职；仅三天后，第二个带着全量权重的开源模型紧跟着上线。

人才在加速流失，模型在加速狂飙。

这两条背道而驰的曲线，成了AI行业中最具代表性的一幕。也许这就是通向ASI的必经之路：不管留下的人有多少，机器向前的车轮，只会越转越快。

---

引用

[^1]: Inkling-Small (https://thinkingmachines.ai/news/inkling-small/) · Thinking Machines · 2026/7/31 · 检索日期2026/7/31

[^2]: 翁荔刚回OpenAI，Thinking Machines反手甩出新模型 (https://mp.weixin.qq.com/s/X0LrI38AiJD_p6BpLRYUgQ) · 新智元 · ASI启示录 · 2026/7/31 · 检索日期2026/7/31
