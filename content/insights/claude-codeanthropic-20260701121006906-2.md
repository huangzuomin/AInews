---
title: Claude Code偷偷给你打标签？Anthropic的「双喜临门」变「翻车现场」
date: 2026-07-01T12:10:06+08:00
draft: false
featured_image: images/default (17).png
summary: Anthropic今天一边庆祝出口管制解除，一边被实锤Claude Code偷偷用隐写术给中国用户打标签。这段代码会检测时区、代理和AI实验室域名，然后把信息藏在日期格式和标点符号的微小变化里。虽然动机是为了遏制转售，但偷偷摸摸搞监控让开发者信任碎了一地，好在官方承诺明天就删。
tags: 
  - Claude Code
  - 隐写术
  - 数据隐私
  - 偷查用户
  - 翻车现场
main_topics: 
  - AI伦理与治理
---

### TL;DR
> Anthropic一边喜提美国商务部解除出口管制，一边被开发者实锤：Claude Code在偷偷检测用户时区、代理和中国AI实验室域名，并把这些信息用隐写术藏进系统提示词里。说好的安全透明呢？这波操作，属实让人有点绷不住。

---

就在今天（2026年7月1日），Anthropic迎来了所谓的「双喜临门」——新模型Claude Sonnet 5性能直逼Opus 4.8，同时美国商务部也解除了对Claude Fable 5和Mythos 5的出口管制。消息一出，AI圈一片欢腾，仿佛又到了「OpenAI你慌不慌」的剧本时间。

但反转来得比翻书还快。另一边，开发者社区直接炸了锅——有人扒出来，Claude Code一直在用户不知情的情况下，偷偷收集你的时区、代理IP，甚至检测你是不是在用中国AI实验室的域名，然后把这些信息用肉眼根本分辨不出的字符变化，塞进发给AI的提示词里。

好家伙，这哪是「代码助手」，这分明是「间谍软件」啊。

---

### 一场「隐形」的指纹识别

事情是这样的。一位Reddit老哥首先发帖质疑，随后在GitHub上放出了完整验证报告，矛头直指Claude Code的2.1.193、2.1.195、2.1.196三个版本。报告确认，Claude Code里藏着一套隐蔽检测逻辑：

- 它会检查环境变量`ANTHROPIC_BASE_URL`——如果你把Claude Code指向了非官方的API代理（比如国内镜像），它就开始了。
- 接着提取代理域名，读取你的系统时区，重点看是不是`Asia/Shanghai`或`Asia/Urumqi`。
- 然后，检测到的域名会跟一份147个条目的「黑名单」比对——百度、阿里巴巴、蚂蚁、字节、Moonshot AI、MiniMax、Stepfun……几乎所有中国AI实验室和Claude转售/镜像服务都在上面。

到这里，还只是常规「反滥用」统计？不，真正骚的操作在后面。

---

### 日期分隔符里藏玄机，'的变种你看不出来的

最绝的是信息传递方式。Claude Code没有单独设一个telemetry字段上报数据，而是把「小纸条」塞进了系统提示词里那句最不起眼的「Today's date is...」。

当识别到你是中国时区时，日期分隔符从短横线变成斜杠，例如`2026-06-30`变成`2026/06/30`。同时，`Today's date`里的撇号开始在几个形近的Unicode字符之间切换——`'`、`'`、`ʼ`、`ʹ`。这几个符号在常规界面里肉眼根本分不出来，但对机器来说，就是一组完美的指纹码。

如果符合条件（时区+命中黑名单），每一次请求都会带着这样一枚不易察觉的标记。这可不是巧合，而是精心设计的「隐写术」（Steganography）。

---

### 动机能理解，但信任呢？

有人可能会说：AI公司想做用户行为识别、防范滥用、遏制转售、规避制裁风险，这很正常啊。确实，从商业角度讲，Anthropic希望遏制Claude访问权限在中国市场被违规转售，动机不难理解。

但**争议不在于目的，而在于方法**。

Telemetry数据采集在软件行业很常见，但前提是告知用户、提供选择权。把标记信息藏在几乎无法察觉的字符差异里，这已经不是「数据采集」，而是「隐蔽监控」了。对一款coding assistant而言，用户把源代码、项目结构、密钥都暴露给它，信任就是根基。你现在告诉用户：我不仅看你的代码，还偷偷给你打标签？这信任一旦被突破，修复起来可没那么容易。

更何况，Claude Code内置的权限系统本身就有「审批疲劳」（approval fatigue）问题——大多数用户会习惯性点批准，甚至完全关闭权限审批。Anthropic自己的博客也承认，他们的agentic系统出现过误删远程git分支、意外上传token、对生产数据库执行迁移等翻车案例。在这种背景下，再搞个隐藏通道，用户自然会追问：还有哪些信息被偷偷记录了？client端还有没有其他没公开的检测逻辑？

---

### Anthropic的回应：明天就删

事件曝光后，Anthropic技术团队成员@trq212火速回应，承认代码存在，并表示这段代码将在次日的版本中移除。公关速度确实快，但「被发现才删」和「主动透明披露」之间，隔着一条信任鸿沟。

另一边，美国商务部的出口管制解除倒是实打实的利好——从明天起，Claude Mythos 5和Fable 5的出口、再出口不再需要许可证。但Anthropic也得履行承诺，继续跟政府保持密切合作，发现恶意活动时及时通报。看起来，Anthropic在跟政府的「相爱相杀」中暂时占了上风，但在用户信任这一局，自己给自己挖了个坑。

---

### 最后的灵魂拷问

当你的AI代码助手比你自己更清楚你在哪个时区、用了哪个代理、连到了哪家实验室的API时，你还敢放心地让它接管你的代码库吗？

信任这种东西，建立起来要很久，崩塌只需要一次「偷查」。Anthropic这次虽然及时「认错删代码」，但吃瓜群众的目光已经锁定——下次再有新版本，开发者们怕是要先拿反编译工具过一遍了。

---

## 引用

[^1]: FBI警告：美国大型银行即将遭受重大网络攻击·安知讯·Erica·检索日期2026/7/1  
[https://mp.weixin.qq.com/s?__biz=MzA3MzI4MjgzMw==&mid=2651042100&idx=2&sn=d16ecaa5493aba7f3a7face73458743f](https://mp.weixin.qq.com/s?__biz=MzA3MzI4MjgzMw==&mid=2651042100&idx=2&sn=d16ecaa5493aba7f3a7face73458743f)

[^2]: Clude Code Prompt Steganography·thereallo.dev·检索日期2026/7/1  
[https://thereallo.dev/blog/claude-code-prompt-steganography](https://thereallo.dev/blog/claude-code-prompt-steganography)

[^3]: Anthropic Fable 5遭美國出口管制強制下架：越獄風波·數位時代·检索日期2026/7/1  
[https://www.bnext.com.tw/article/91244/anthropic-fable-5-us-export-control-jailbreak-and-china-ai-risk](https://www.bnext.com.tw/article/91244/anthropic-fable-5-us-export-control-jailbreak-and-china-ai-risk)

[^4]: Claude Fable 5 提示詞外洩引美出口管制中國AI 實力受關注·Yahoo奇摩股市·检索日期2026/7/1  
[https://tw.stock.yahoo.com/news/claude-fable-5-提示詞外洩引美出口管制-中國-113150695.html](https://tw.stock.yahoo.com/news/claude-fable-5-提示詞外洩引美出口管制-中國-113150695.html)

[^5]: Hacker News Discussion·检索日期2026/7/1  
[https://news.ycombinator.com/item?id=48734373](https://news.ycombinator.com/item?id=48734373)

[^6]: Claude Code Accused of Hiding China Proxy Fingerprints Inside System Prompts·International Cyber Digest·检索日期2026/7/1  
[https://www.internationalcyberdigest.com/claude-code-accused-of-hiding-china-proxy-fingerprints-inside-system-prompts/](https://www.internationalcyberdigest.com/claude-code-accused-of-hiding-china-proxy-fingerprints-inside-system-prompts/)
