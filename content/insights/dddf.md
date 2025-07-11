---
title: "人形机器人大模型新篇章：智在无界如何突破具身智能瓶颈"
date: 2025-06-14T23:12:48+08:00
draft: false
summary: "由前智源研究院核心团队创立的北京智在无界科技有限公司获得联想之星和智谱Z基金等数千万元投资，旨在开发通用人形机器人大模型。该公司通过创新性地利用互联网人类视频进行预训练，并结合自学习框架，致力于解决具身智能领域长期存在的数据稀缺和泛化能力不足的难题，为人形机器人走向商业化应用铺平道路。"
tags: 
  - "人形机器人"
  - "具身智能"
  - "大模型"
  - "智在无界"
  - "智谱AI"
  - "智源研究院"
  - "投资"
  - "AI技术"
  - "泛化能力"
  - "机器学习"
main_topics: 
  - "具身智能技术突破"
  - "AI投资趋势"
  - "人形机器人产业化"
---

> 北京智在无界科技有限公司，一家由前智源研究院核心团队创立的初创公司，近日获得了联想之星和智谱Z基金等数千万元投资。该公司致力于开发通用人形机器人大模型，其核心创新在于通过解析海量互联网人类视频数据来训练机器人，有望解决具身智能领域长期面临的数据稀缺与泛化能力不足的难题，推动人形机器人从实验室走向实际应用。

在人工智能浪潮的持续推动下，通用智能体的愿景正逐步从概念走向现实，而人形机器人作为具身智能的终极形态，正吸引着全球的目光和资本的涌入。近日，北京智在无界科技有限公司（BeingBeyond）宣布完成数千万元融资，由联想之星领投，智谱Z基金、燕缘创投、彬复资本跟投，这一事件不仅标志着资本市场对具身智能前景的坚定看好，更揭示了由前智源研究院核心团队带来的创新技术路径，有望为人形机器人领域带来一次范式上的突破 [^1]。

### 具身智能的症结：数据困境与泛化鸿沟

长久以来，具身智能机器人的发展一直面临着两大核心制约：**数据规模的庞大需求**和**泛化能力的瓶颈**。要让机器人实现高度拟人化的行动与决策，需要海量且多样化的真实世界交互数据进行深度训练。这些数据不仅覆盖日常操作，更包括复杂环境下的精细交互。然而，数据的采集过程异常艰难，需要大量人力、高昂成本，并且随着数据需求的指数级增长，存储成本也随之飙升。

更严峻的挑战在于泛化能力。即使拥有海量数据，现有模型在面对未知环境、新任务或新物体时，往往表现不尽如人意，难以将其所学知识有效迁移至全新的情境。这意味着机器人仍缺乏在动态、开放世界中灵活适应和自主学习的能力，严重阻碍了其实际应用和商业化落地。如何在有限的数据规模下提升模型的泛化能力，已成为具身大脑突破性能瓶颈，迈向实用化的关键。

### 智在无界的创新解法：从人类视频中学习

正是为了解决这些核心矛盾，智在无界（BeingBeyond）提出了其独特的技术路线。该公司成立于2025年1月，创始人卢宗青是北京大学计算机学院长聘副教授，曾任智源研究院多模态交互研究中心负责人，并主导过首个国家自然科学基金委原创探索计划通用智能体项目。团队核心成员均来自智源研究院，在强化学习、计算机视觉、机器人控制和多模态等领域拥有深厚的技术积累 [^1]。

智在无界的核心创新在于，其通用大模型系统并非强依赖于昂贵的机器人真机数据，而是从**互联网端的人类运动和手部操作视频**中进行预训练。卢宗青指出，这种以公开视频数据为驱动的技术路线，实现了从“人类行为示范”到“机器人动作生成”的跨模态迁移，有效规避了传统方案在数据采集上的高门槛和低效率。

具体而言，智在无界将其通用大模型系统划分为三层：

*   **具身多模态大语言模型 (Embodied Multimodal Large Language Model)**：该模型自主研发了_Video Tokenizer_技术，专注于时空环境的理解与推理，尤其擅长解析第一人称视角视频。通过将连续视频流解构为兼具时间序列与空间语义的视觉token单元，模型能够精准捕捉动作的时序逻辑（如伸手、抬升手臂到抓起物体的连贯过程），并基于物体方位、肢体相对位置等空间特征理解物理世界和人类行为 [^1]。
*   **多模态姿态大模型 (Multimodal Pose Large Model)**：利用互联网上丰富的视频资源，包括行走、舞蹈等全身运动，以及抓取物体、工具使用等第一人称视角的精细手部操作数据，为模型提供了丰富且多元的动作样本。这使得模型能够学习各种动作在不同环境下的表现形式，并根据实时环境信息与任务要求，实现具有泛化性的端到端运动操作 [^1]。
*   **运动模型 (Motion Model)**：负责将经过预训练和推理得到的动作指令，转化为机器人本体能够执行的精确运动控制。

为了进一步增强机器人的自主学习能力和对动态环境的适应性，智在无界还提出了**Retriever-Actor-Critic (RAC) 框架**。该框架通过对真实交互数据进行检索增强生成（RAG）与强化学习的协同应用，形成“数据收集-模型优化-效果反馈”的闭环。这不仅能提升模型的响应准确性，还能使机器人具备动态适应多变场景的能力，为其规模化落地提供了可行的技术路径 [^1]。卢宗青强调，这种“互联网视频预训练通用动作模型，再通过后期适配训练实现对不同机器人本体及场景的迁移”的技术路径，可以有效避免因硬件迭代导致的数据浪费，从根本上解决真机数据稀缺与场景泛化的矛盾 [^1]。

### 资本的视角：生态布局与未来愿景

此次融资的联想之星和智谱Z基金，其投资逻辑也映射出对具身智能和通用AI赛道的深远布局。联想之星合伙人高天垚指出，当前具身大模型的技术路线尚未收敛，而BeingBeyond团队的技术路线解决了训练数据来源有限的问题，同时采用模块化方式构建了一套完整的技术框架，具备全栈技术能力，有望在任务与环境泛化性、跨本体等问题上实现“零样本”泛化 [^1]。

智谱Z基金作为智谱AI的生态基金，其投资行为更是智谱AI整体战略的缩影。智谱AI本身已是中国估值最高的AI大模型创业公司之一，此前完成了30亿元融资，投前估值高达200亿元人民币 [^4]。智谱Z基金正在积极通过“Z计划”投资布局AI大模型产业，据了解已投资超过13家相关创业公司 [^3]，其中包括另一家同样获得智谱生态基金投资的人形机器人厂商“动易科技” [^2]。智谱Z基金合伙人王璞表示，智在无界构建了业界首个百万规模的MotionLib数据集，并开发了端到端的Being-M0动作生成模型，验证了“大数据+大模型”在具身智能中的规模效应，并实现了跨平台动作迁移的技术闭环 [^1]。这表明智谱AI不仅着眼于基础大模型的研发，更在积极构建包括具身智能在内的应用生态，以期推动通用机器人走进千家万户 [^1]。

智在无界的技术路径，无疑为人形机器人的未来发展提供了新的想象空间。随着公司与头部机器人厂商推进场景验证合作，其创新的预训练和自学习框架，有望加速具身智能在更多领域的应用落地。然而，将这些在互联网视频中习得的“通用动作”真正转化为复杂、高风险工业场景或精细家庭服务中的可靠行为，仍需大量工程化努力和安全伦理考量。但毋庸置疑，智在无界正站在一个关键的十字路口，其技术路线可能重塑我们对未来人机交互和智能自动化潜力的认知。

## References
[^1]: 黄楠 (2025/6/13)。前智源团队创业，联想、智谱AI投了一家人形机器人大模型公司｜硬氪首发。硬氪。检索日期2025/6/14。
[^2]: 36氪 (2025/6/14)。峰瑞、智谱生态基金，投了一家人形机器人公司丨36氪独家。36氪。检索日期2025/6/14。
[^3]: 新浪财经 (2024/8/13)。智谱正在变成一家投资公司|AI。新浪财经。检索日期2025/6/14。
[^4]: 搜狐 (2024/12)。智谱AI宣布获30亿融资：投前估值200亿，对标OpenAI，附路演PPT。搜狐。检索日期2025/6/14。
