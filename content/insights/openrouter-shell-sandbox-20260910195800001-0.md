---
title: "OpenRouter 把 Linux 沙箱做成了公共事业：任何模型都能跑 shell 了"
date: 2026-09-10T19:58:00+08:00
draft: false
featured_image: "/images/ai-report-default.png"
summary: "OpenRouter 发布服务端 shell 工具与 Files API：平台上任何支持工具调用的模型，都能在托管 Linux 容器里执行命令、读写文件。模型路由器正在变成智能体基础设施公司——执行环境正在从“各家 SDK 的私活”变成“平台的标准供电”。"
tags:
  - OpenRouter
  - 智能体
  - 沙箱
  - 工具调用
  - 开发者基础设施
main_topics:
  - 企业级AI与数字化
  - 产业生态与商业版图
---

TL;DR：
> OpenRouter 上线 `openrouter:shell` 服务端工具与 Files API（beta）：不再绑定某一家模型的代码执行能力，任何接入了工具调用的模型都可以在托管 Linux 容器中执行命令。执行环境被平台化，智能体的"手和脚"第一次变成了标准配置。

### 这一步改变了什么：从“模型的附加功能”到“平台的公共设施”

过去两年，代码执行能力的供给是碎片化的：OpenAI 有 Code Interpreter，Anthropic 有分析工具，各家 SDK 里还散落着自建沙箱方案。换模型就要换执行环境，智能体框架的很大一部分工程量花在适配这些私有实现上。OpenRouter 的做法是把执行环境从模型侧剥离：任何支持工具调用的模型——无论开源还是闭源——调用同一个标准化的 shell 工具，背后是平台统一托管的 Linux 容器。

对多模型智能体工作流，这直接简化了架构：路由层换模型，工具层不用动。配套的 Files API 补上了最后一块——文件的上传、生命周期管理与执行环境打通，让"跑一段代码并持久化产物"成为完整闭环。

### 商业视角：路由器的护城河升级

OpenRouter 的起点是模型路由（比价和容灾），但路由层的天花板很低——价差套利的空间会随市场透明化消失。加上执行环境后，它提供的是"模型无关的智能体运行时"，卡位比路由深得多：一旦团队的工具链建立在平台的 shell/Files 标准上，迁移成本就不再是换个 API key 那么简单。官方公布的定价、容器网络策略与文件生命周期细节显示，这是有完整商业化设计的功能，而非演示性 beta。

### 展望

值得跟踪的是容器网络策略的演进（沙箱能不能访问外网，决定了它能承接的任务类型）和定价曲线。如果"模型无关执行环境"成为品类，下一步就该轮到各大模型网关跟进——执行环境的标准化战争，本质是智能体时代的云之争。

## 引用

[^1]: [Announcing the Shell Tool and Files API](https://openrouter.ai/blog/announcements/shell-tool) · OpenRouter Blog · 2026/9/10 · 检索日期2026/9/10

[^2]: [AIHOT 精选条目：OpenRouter shell 沙箱](https://aihot.news/) · AIHOT · 2026/9/10 · 检索日期2026/9/10
