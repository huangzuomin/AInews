# SPEC: SEO / GEO 优化规范 v1

> 对象：AI内参（https://www.neican.ai）
> 日期：2026-09-11
> 定位：**发布前**的机器可解析性与可引用性规格，不是发布后的优化清单
> 前置文档：`DESIGN-greenfield-2026-09-11.md`（架构）、`SPEC-selection-and-style-2026-09-11.md`（选题与风格）

---

## 0. 一页结论

**SEO 求"被发现"，GEO 求"被引用"。两者共同的物理前提是同一件事：内容必须能被机器切成"可独立搬运的断言单元"。**

现状诊断一句话：**站点为"人读"生产内容，但机器读不懂它**。具体是三个断点：

| 断点 | 实测证据 | 后果 |
|---|---|---|
| **结构层断了** | 全站 JSON-LD 页面数 = **0**；`<time datetime>` = **0**；正文从 `h3` 起（h1→h3 跳级），18.9% 文章无 `h2` | AI 引擎拿不到实体/时间/作者，无法建立事实归属 |
| **链接层断了** | 正文 markdown 内链 **0/1200 = 100% 零内链**；sitemap 里 **60.6% 是标签页**，67.2% 的标签页只有 1 篇文章 | 主题权威无法累积，爬虫预算烧在薄页上 |
| **信任层断了** | 每篇文末声明"文末附有详细的 [引用信息索引]，供您查证溯源"，但 1,500 篇抽样中**兑现 0 篇** | 公开承诺违约——这是 GEO 评估里最贵的一种负分 |

**最高杠杆的一件事**：写自己的 `partials/seo/schema.html`，把 JSON-LD 覆盖率从 0% 拉到 100%。它是纯构建期改动、零运行时成本、一次性修好 9,383 篇存量。

**最容易被忽略的一件事**：把"引用信息索引"那句承诺变成真实产物。它同时修好四件事——兑现承诺、建立溯源、抬高一手源权重、给 AI 引擎提供引用锚点。

---

## 1. 现状基线（全部实测，2026-09-11）

### 1.1 结构化数据与元标签

| 项 | 实测 | 判定 |
|---|---|---|
| JSON-LD 页面覆盖率 | **0 / 27,683** | 🔴 致命 |
| `og:image` | **0** | 🔴 分享无封面 |
| `twitter:card` | `summary`（无图） | 🟠 应为 `summary_large_image` |
| `<link rel=canonical>` | 有，正确 | 🟢 |
| `og:url/title/description/type` | 有 | 🟢 |
| `article:published_time` / `modified_time` | 有 | 🟢 |
| `<time datetime>` | **0** | 🟠 无 HTML 级时间信号 |
| `hreflang` | 无 | 🟢（单语站无需） |
| `robots` meta | `index, follow` | 🟢 |
| 404 状态码 | 正确返回 404 | 🟢 |

**根因（已最小复现）**：`themes/ananke/layouts/_default/baseof.html:52` 调用 `{{ template "_internal/schema.html" . }}`。该内建模板在 Hugo 0.147 中**已被清空为无输出**，但**名字仍可解析**，因此：

```
调用不存在的模板 "_internal/nonexistent.html"  → Error: no such template （构建失败）
调用 "_internal/schema.html"                   → exit 0、静默、产物为空
```

这是**静默失效**的最坏形态：构建永远成功、永远不报错、结构化数据归零且无人察觉。与"37 天停更"同源——**失败没有声音**。

> 旁证（另一个静默风险）：本地 Hugo 为 **v0.147.0**，而线上产物 `<meta name="generator">` 为 **Hugo 0.147.8**。构建环境不一致，属于可重放性缺陷。

### 1.2 内容可解析性（抽样 1,200 篇 insights）

| 指标 | 实测 | 阈值 | 判定 |
|---|---|---|---|
| 标题长度 | 中位 **35** 字，**73.3% >30 字**，22.8% >40 字 | ≤30 | 🟠 多数被 SERP 截断 |
| summary 长度 | 中位 120 字，12.3% >160 字 | 80–160 | 🟢 |
| `H2` 数 | 中位 **1**，**18.9% 为 0** | ≥2 | 🔴 |
| `H3` 数 | 中位 **4**，**73.2% >3** | ≤3/h2 | 🔴 层级倒挂 |
| 正文首个小标题层级 | `###`（h1→h3 跳级） | `##` | 🔴 |
| TL;DR 存在率 | **96.7%** | 100% | 🟢 已有资产，但未语义化 |
| 正文 markdown 内链 | 中位 **0**，**100% 零内链** | ≥3 | 🔴 致命 |
| 正文外链 | 279/400（70%）有外链 | — | 🟢 有，但源质量差 |
| 「引用信息索引」 | **0 / 1,500** | 100% | 🔴 承诺违约 |
| `source_url` 非空值 | **0** | 100% | 🔴 字段存在但全空 |

**正文外链的来源构成**（400 篇抽样，Top 10）：

```
43  finance.sina.com.cn      42  mp.weixin.qq.com     32  zhuanlan.zhihu.com
32  www.ft.com               24  m.36kr.com           22  www.wsj.com
19  www.huxiu.com            19  www.msn.com           18  www.36kr.com
16  static001.geekbang.org
```

→ **以二手聚合与自媒体平台为主**（微信公众号 / 知乎 / 新浪财经 / 36氪），一手源（官方博客、release notes、arXiv、GitHub、官方文档）占比低。对 GEO 而言，引用一手源的稿件本身更容易被 AI 引擎二次引用。

### 1.3 信息架构与站点卫生

| 项 | 实测 | 判定 |
|---|---|---|
| sitemap 条目 | **26,961** | 🔴 |
| ├ `tags` | **16,345（60.6%）** | 🔴 |
| ├ `insights` | 9,382 | 🟢 |
| ├ `main_topics` | 627 | 🔴 |
| └ `newspaper`+`morningnews` | 602 | 🟢 |
| 标签总数 | **16,237** | 🔴 文章数的 1.73 倍 |
| 标签页文章数分布 | **67.2% 只有 1 篇**；仅 10.5% ≥5 篇，6.0% ≥10 篇 | 🔴 薄页 |
| `main_topics` 去重值 | **616**（11 个正常 + 605 碎片 + `--`） | 🔴 |
| `main_topics: --` 的文章数 | **9,308**（占 99%） | 🔴 分类事实失效 |
| 标签命名归一化 | `ai-agent与自主系统` 与 `ai-agent与自主系统-ai-agents--autonomous-systems` **并存** | 🔴 实体未归一 |
| `priority` / `changefreq` | 0 / 0（仅 `lastmod`） | 🟡 可接受 |
| `llms.txt` / `ai.txt` | **404** | 🟠 缺失 |
| `robots.txt` | 全放开，无 AI 爬虫策略分段 | 🟡 |
| RSS `index.xml` | 正常 | 🟢 |
| 根级幽灵产物 | `entities/ topics/ briefs/ concepts/ timeline/` 共 22 个文件已入库，线上**全部 404**（Hugo 0.161.1 生成，源自 2026-05-01 的一次 deploy commit） | 🟠 卫生 + 泄漏了未实现的 IA |

> **幽灵站的价值**：那批文件的 IA（`/entities/`、`/topics/`、`/timeline/`、`/briefs/daily/`）恰好是 GEO 最想要的**实体枢纽**结构。正确的处置不是删除，而是**用真正的 Hugo taxonomy 重建**（见 §4.3）。

### 1.4 「相关阅读」的实际形态

- 模板：`layouts/partials/menu-contextual.html:18`，`{{ $related := .Site.RegularPages.Related . | collections.First 15 }}`
- **`hugo.toml` 中没有任何 `[related]` 配置** → 走 Hugo 默认索引与阈值
- 三篇文章的「相关阅读」列表哈希不同（`40342c0b…` / `c2a2794d…` / `76383e5b…`）→ **确实按内容计算，非静态列表** 🟢
- 但：标题用 `<p>` 而非 `<h2>`；15 条无分组无排序说明；在标签严重碎片化（16,237 个标签）的前提下，相关性质量不可控

---

## 2. 三个根因（第一性原理）

把所有症状归并，只有三条：

### 根因一：**内容的"事实归属"从未被结构化**
一个断言要被引用，必须同时具备三件事：

1. **谁说的**（来源）—— 现在 `source_url` 全空，来源只在散文里以 markdown 链接出现
2. **什么时候**（时效）—— 现在 HTML 里没有 `<time datetime>`，正文散文里的日期是自由文本
3. **说的是谁**（实体）—— 现在实体是 16,237 个未归一化的标签

**AI 引擎引用的不是"一篇文章"，是"一句能被单独搬运、且搬走之后还知道出处的断言"。** 三条全断，就是不可引用。

### 根因二：**"承诺"与"产物"之间没有校验**
「引用信息索引」声明 vs 0/1500 兑现；`source_url` 字段存在 vs 全空值；`main_topics: --` 9,308 篇。三次都是同一模式：**写了字段/声明，但没有一条机制保证它被真正填上**。

这跟上一轮 `SPEC-selection-and-style` 的结论一致：**承诺必须变成门禁，否则承诺会被时间吃掉。**

### 根因三：**SEO/GEO 被放在链路末端，而不是生成阶段的产物规格**
如果结构化数据、来源索引、实体归属是"发布后再补"的事情，那么按现状的产能（每天数十篇），它将永远补不上——事实上已经累积了 9,383 篇欠账。

**正确位置：在选题阶段确定实体与预期一手源，在写作阶段产出原子断言与来源，在入库门禁校验，发布只是最后一步。**

---

## 3. 设计与流水线的耦合：SEO/GEO 前移到每个环节

对照原始工作流，每个环节都有一条 SEO/GEO 产物：

| 环节 | 现状 | SEO/GEO 要求的产物 | 校验方式 |
|---|---|---|---|
| **① 发现选题** | 只看热度 | 同时判定 **主实体**（须命中实体注册表）+ **预期一手源可达性** | 实体闭集校验 |
| **② 确认写作** | 人工/自动确认 | 确认时锁定 `slug`（含实体关键词，非纯时间戳）、`main_topics`（闭集）、`entities`（闭集） | 门禁 G3 |
| **③ 查找相关素材** | 先写完再找 | **前移**：为每条候选断言取回一手源 URL + 抓取时间 + sha256 | 门禁 G2 |
| **④ AI 生成** | 自由发挥 | 强制 h2 大纲；数字句自带出处；TL;DR 语义化；对比用表格 | 门禁 G1 |
| **⑤ 自动发布** | 直接 push | 构建后抽检 JSON-LD 可解析性 + 关键字段非空 | 门禁 G3-b |
| **⑥ 选 5 条 → 日报** | 独立成文 | 每条要闻输出 `ItemList` 结构化 + 指向已发布洞察的内链 | 门禁 G1/G3 |
| **⑦ 发布日报** | 同上 | 同一发布通道（勿开第二条路径） | — |

**关键次序更正**：`slug` 与 `entities` 必须在**写作前**确定。现在的 slug 形如 `deepseek-v41-flash-20260910195000001-0`——前半段有人类可读关键词（好），后半段是时间戳+序号（噪声）。**URL 是最强的关键词信号之一，时间戳后缀应当移除。**

---

## 4. 三层规格

### 4.1 L1 可发现层（Discoverability）

#### 4.1.1 JSON-LD（P0，最高杠杆）

**动作**：新增 `layouts/partials/seo/schema.html`，在 `baseof.html` 中把

```go-html-template
{{- template "_internal/schema.html" . -}}
```

替换为

```go-html-template
{{- partial "seo/schema.html" . -}}
```

**输出 `@graph`（一次输出、多实体互引，优于多个独立 script）**：

| 页面类型 | 实体 | 关键属性 |
|---|---|---|
| 全站（每页都带） | `Organization` | `@id`、`name`、`url`、`logo`、`sameAs` |
| 全站 | `WebSite` | `@id`、`name`、`url`、`inLanguage`、`publisher`、`potentialAction`(SearchAction) |
| insights 单篇 | `NewsArticle` | `headline`(≤110字)、`description`、`datePublished`、`dateModified`、`author`、`publisher`、`image`、`mainEntityOfPage`、`articleSection`、`keywords`、`about`(实体)、`citation`(来源)、`isAccessibleForFree: true`、`inLanguage: zh-CN`、`abstract`(TL;DR) |
| 全部内页 | `BreadcrumbList` | `首页 → 栏目 → 文章` |
| 早报 | `ItemList` | 每条要闻一个 `ListItem`，`item` 指向详情页 |
| 日报 | `ItemList` + `NewsArticle` | 同上，附 `about` |
| 分类/实体/标签页 | `CollectionPage` + `ItemList` | `mainEntity` = 该实体 |
| 关于页 | `AboutPage` + `Organization` | 方法论、AI 使用声明 |

**设计原则**：**schema 从 frontmatter 生成，不手写。** 因此 frontmatter 缺字段 → schema 缺字段 → 这正是门禁 G3 的抓手。

可粘贴骨架（需按 frontmatter 实况微调）：

```go-html-template
{{/* layouts/partials/seo/schema.html — JSON-LD @graph */}}
{{- $base := .Site.BaseURL | strings.TrimSuffix "/" -}}
{{- $orgID := printf "%s#organization" $base -}}
{{- $webID := printf "%s#website" $base -}}

{{- $org := dict "@type" "Organization" "@id" $orgID
      "name" .Site.Title "url" .Site.BaseURL
      "logo" (dict "@type" "ImageObject" "url" (absURL .Site.Params.site_logo)) -}}

{{- $web := dict "@type" "WebSite" "@id" $webID
      "url" .Site.BaseURL "name" .Site.Title "inLanguage" "zh-CN"
      "publisher" (dict "@id" $orgID)
      "potentialAction" (dict "@type" "SearchAction"
        "target" (dict "@type" "EntryPoint" "urlTemplate" (printf "%s/search/?q={search_term_string}" $base))
        "query-input" "required name=search_term_string") -}}

{{- $nodes := slice $org $web -}}

{{- if .IsPage -}}
  {{- $post := dict "@type" "NewsArticle"
        "@id" (printf "%s#article" .Permalink)
        "headline" (.Title | plainify)
        "description" (.Description | default .Summary | plainify | truncate 200)
        "datePublished" (.Date.Format "2006-01-02T15:04:05+08:00")
        "dateModified" (.Lastmod.Format "2006-01-02T15:04:05+08:00")
        "inLanguage" "zh-CN"
        "isAccessibleForFree" true
        "mainEntityOfPage" (dict "@id" .Permalink)
        "publisher" (dict "@id" $orgID)
        "isPartOf" (dict "@id" $webID)
        "articleSection" (index (.Params.main_topics | default (slice)) 0)
        "keywords" (.Params.tags | default (slice)) -}}
  {{- with .Params.featured_image -}}
    {{- $post = merge $post (dict "image" (slice (absURL .))) -}}
  {{- end -}}
  {{/* 作者实体（E-E-A-T） */}}
  {{- $authorName := .Params.author | default .Site.Params.author -}}
  {{- $post = merge $post (dict "author" (dict "@type" "Organization" "name" $authorName "url" (absURL "about/"))) -}}
  {{/* 引用信息索引 → citation */}}
  {{- with .Params.sources -}}
    {{- $cites := slice -}}
    {{- range . -}}
      {{- $cites = $cites | append (dict "@type" "CreativeWork" "name" .title "url" .url
            "datePublished" (.date | default nil) "publisher" (dict "@type" "Organization" "name" (.publisher | default ""))) -}}
    {{- end -}}
    {{- $post = merge $post (dict "citation" $cites) -}}
  {{- end -}}
  {{- $nodes = $nodes | append $post -}}
{{- end -}}

<script type="application/ld+json">{{ (dict "@context" "https://schema.org" "@graph" $nodes) | jsonify }}</script>
```

> ⚠️ 上例的 `sources` 结构需与 §4.3.1 的 frontmatter 约定一致；`truncate`/`plainify` 与 `merge` 的行为请以本地构建实测为准。**该 partial 必须先在 3 篇样本上构建通过、并用 schema validator 校验后才全量启用。**

#### 4.1.2 OG 图片（P0）

**根因**：Hugo 内建 `_internal/opengraph.html` 只认 `.Params.images`（数组）或**页面资源**中的 `*feature*`/`*cover*` 图片。本站 frontmatter 用的是 `featured_image`（字符串路径指向 static），**两者不匹配** → `og:image` 恒为空。

**动作**：新增 `layouts/partials/seo/opengraph.html` 覆盖内建，或**更优雅**——用 Hugo 图像处理生成**程序化 OG 卡**（1200×630，标题 + 站点名 + 日期 + 栏目），彻底摆脱版权图问题：

```go-html-template
{{/* 程序化 OG 卡（extended 版支持 images.Text / images.Overlay） */}}
{{- $bg := resources.Get "og/base.png" -}}
{{- $img := $bg.Filter (images.Text .Title (dict
      "color" "#1A1A1A" "size" 56 "linespacing" 16 "x" 64 "y" 180)) -}}
{{- $img = $img.Filter (images.Text .Site.Title (dict
      "color" "#C53A2A" "size" 32 "x" 64 "y" 96)) -}}
{{- $final := $img.Resize "1200x630 png" -}}
<meta property="og:image" content="{{ $final.Permalink }}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{{ $final.Permalink }}">
```

**成本警告**：9,383 篇存量若全量生成 OG 图，构建时间会显著上升。**建议：仅新文生成，存量回退到站点默认图**（`site.Params.images`）。这是一条需要实测的取舍。

#### 4.1.3 sitemap 治理（P0）

**动作**：`hugo.toml` 中收窄 outputs + 分类法可见性：

```toml
[taxonomies]
  category = "main_topics"
  tag = "tags"
  author = "authors"

# 只让 tags 生成页面，不进 sitemap（薄页不提交）
[sitemap]
  # Hugo 无 per-taxonomy 排除，需自写 sitemap 模板或改 outputs
[outputs]
  home = ["HTML", "RSS", "JSON"]
  term = ["HTML"]        # 关键：去掉 term 的 RSS，减少薄页
  taxonomy = ["HTML"]
```

推荐做法是**自写 `layouts/sitemap.xml`**，加白名单逻辑：只收录 sections（insights/newspaper/morningnews）+ 实体页 + `main_topics` 闭集页 + 文章数 ≥5 的标签页。

预期效果：**26,961 → 约 10,500**，删掉 16,000+ 个薄页提交。

---

### 4.2 L2 可解析层（Chunkability）

#### 4.2.1 标题层级（P0，门禁 G1）

- 正文**必须**从 `##` 起（当前从 `###` 起，h1→h3 跳级）
- `h2` 数 ≥2；每个 `h2` 下 `h3` ≤3
- 首个 `h2` 建议为「摘要」或直接进主题（TL;DR 语义化后可作为 `abstract`）

#### 4.2.2 事实单元原子化（P0，门禁 G2）—— GEO 的核心

**规范**：**每段只承载一个可独立搬运的断言，且断言自足**（含主体、数值、时间、来源）。

| | 例 |
|---|---|
| ✅ 可引用 | 据 MarkTechPost 2026-09-10 的架构拆解，V4.1-Flash 的全局 KV 缓存降至 **890 字节/token**，约为上一代 V4-Flash 的 1/4。 |
| ❌ 不可搬运 | 它的意义不在单项跑分，而在证明长上下文的成本曲线还可以靠架构再砍一刀。 |

**门禁指标**：含数字的句子中，带来源标注的比例 ≥ 0.6。

#### 4.2.3 时间语义化（P1）

- 渲染 `<time datetime="{{ .Date.Format "2006-01-02T15:04:05+08:00" }}">`（当前 0）
- frontmatter 增 `lastmod`；**更新即改**，体现在 `dateModified`
- 门禁：`dateModified >= datePublished`

#### 4.2.4 TL;DR 语义化（P1）

现状 96.7% 有 TL;DR（极好的资产），但形如纯文本 `TL;DR：` + `blockquote`，机器不可识别。

**动作**：改用可识别的容器（如 `<div class="tldr">`），并让 schema 的 `abstract` 与 `og:description` 都取其内容。这是**一次改动、全站受益**的典型。

#### 4.2.5 对比内容表格化（P1）

对比/并列类内容（结构五型中的 D 型）强制用 `<table>`。AI 引擎对表格的摘取率显著高于散文——散文里的对比关系需要"理解"，表格里的对比关系只需"读取"。

---

### 4.3 L3 可引用层（Citability）

#### 4.3.1 兑现「引用信息索引」（P0，GEO 的支点）

**二选一，必须选**：实现它，或删掉那句声明。推荐实现。

frontmatter 约定：

```yaml
sources:
  - title: "DeepSeek-V4.1-Flash Technical Report"
    url: "https://api-docs.deepseek.com/news/v41-flash"
    publisher: "DeepSeek"
    type: primary          # primary | secondary
    accessed: 2026-09-10
    quote: "global KV cache 890 bytes/token"
```

正文末尾（**模板自动渲染，不由 LLM 手写**，避免格式漂移）：

```markdown
## 来源

1. DeepSeek，《DeepSeek-V4.1-Flash Technical Report》，一手源，访问于 2026-09-10。[链接](…)
2. MarkTechPost，《…架构拆解》，二手源，2026-09-10。[链接](…)
```

**这条路一次性修好四件事**：
1. 兑现公开承诺（E-E-A-T）
2. `citation` 结构化 → AI 引擎拿到引用锚点
3. 一手源比例可测、可门禁（≥0.5）
4. 来源域名白名单可校验（治掉低质源）

#### 4.3.2 实体注册表与归一化（P0）

**这是 GEO 长期复利最大的一条**，也是治 `main_topics: --`（9,308 篇）与 16,237 个碎标签的正解。

新增 `data/entities.yaml`（Hugo `data/` 目录，构建期可读、可版本化）：

```yaml
- canonical: "OpenAI"
  aliases: ["openai", "Open AI", "GPT", "奥特曼公司"]
  type: "Organization"
  official_url: "https://openai.com/"
  same_as: ["https://en.wikipedia.org/wiki/OpenAI"]
  topic: "产业生态与商业版图"
- canonical: "DeepSeek"
  aliases: ["deepseek", "深度求索", "DeepSeek AI"]
  type: "Organization"
  official_url: "https://www.deepseek.com/"
  topic: "产业生态与商业版图"
- canonical: "KV 缓存"
  aliases: ["KV cache", "kvcache", "KV缓存"]
  type: "DefinedTerm"
  topic: "模型与算法"
```

配套：
1. `main_topics` 收敛为**闭集 12 项**（含早报/日报两个栏目类）
2. 文章 frontmatter 增 `entities: [DeepSeek, KV 缓存]`，**必须来自注册表** → 门禁校验
3. 渲染时用 `<span itemscope>` 或至少统一锚文本指向实体页
4. 低价值标签不再进 sitemap；`tags` 逐步降级为内部检索用，**不再作为 SEO 资产**

#### 4.3.3 实体枢纽页（P1，幽灵站的正确复活）

仓库里 `entities/ topics/ briefs/ concepts/ timeline/` 那套幽灵 IA，正是 GEO 想要的形态——**但要以真 Hugo taxonomy 重建，而不是提交 HTML 产物**。

每页固定三段式（AI 引擎引用率最高的页面形态 = **定义 + 时间线 + 来源**）：

```markdown
# DeepSeek

**定义**：DeepSeek（深度求索）是一家中国 AI 公司，以 MoE 架构与低价长上下文模型著称。

## 关键事件
- 2026-09-10 — 发布 V4.1-Flash，KV 缓存降至 890 字节/token（来源）
- 2026-08-03 — V4-Flash 上线（来源）

## 相关洞察          ← 自动聚合，天然内链
## 官方链接          ← sameAs
```

URL 形如 `/entity/deepseek/`、`/topic/模型与算法/`。**这类页面单页就能承载一个实体，是 AI 引擎建立知识图谱时的最爱。**

#### 4.3.4 作者/机构与更正机制（P1，E-E-A-T）

现状：`author` 仅 71/800，站级作者固定为"温故智新AIGC实验室"。

- `/about/` 写明：机构、选题方法论、**AI 使用声明**（当前声明藏在每篇文末的 aside 里，且含未兑现承诺）、纠错渠道
- 新增 `/corrections/` 更正记录页——**"AI 生成 + 人工核查"若要有说服力，更正记录是最硬的证据**
- 作者用 `Person`（真人时）或 `Organization`（机构署名）schema，带 `sameAs`

---

## 5. 发布门禁（与上一轮设计对齐）

```
生成 ──▶ G1 结构门禁 ──▶ G2 事实门禁 ──▶ G3 元数据门禁 ──▶ 发布 ──▶ 构建后抽检 ──▶ 观测
```

| 闸 | 检查项 | 否决条件 |
|---|---|---|
| **G1 结构** | h2 数 ≥2；h3/h2 ≤3；正文起始层级 = `##`；段长 ≤150；句长 ≤60；TL;DR 存在且语义化；对比内容已表格化 | 任一不满足 |
| **G2 事实** | 数字句带来源比例 ≥0.6；一手源比例 ≥0.5；来源域名在白名单；无 `YYYY`/`--` 等占位符；无未兑现的"来源"承诺 | 任一不满足 |
| **G3 元数据** | `title` ≤30 字；`summary` 80–160 字；`featured_image` 存在；`main_topics` ∈ 闭集；`entities` ⊆ 注册表；`sources` 非空；`slug` 含实体关键词且无时间戳后缀 | 任一不满足 |
| **G3-b 构建后** | 对新增页面抽检：JSON-LD 可被 `json.loads` 解析；`NewsArticle` 必填字段非空；`og:image` 可达（HTTP 200） | 任一不满足 → 阻断部署 |

> **G3-b 不可省**：schema 是**模板产物**，构建时无法自证。这正是本次 `_internal/schema.html` 静默失效能潜伏数月的机制。CI 里必须有一条"把产物 HTML 里的 JSON-LD 抠出来解析"的断言。

---

## 6. 观测：把"核心指标"从审美变成数字

上一轮 `SPEC-selection-and-style` 已指出：**打分 → 发布 → 效果 → 重标定** 这个闭环缺失。SEO/GEO 的闭环同样必须有：

| 指标 | 工具 | 频率 | 目标 |
|---|---|---|---|
| 索引率（已收录/已提交） | Google Search Console、Bing Webmaster | 周 | 内容页 ≥90% |
| 展现量 / 点击率 / 平均位置 | GSC | 周 | 基线后 8 周翻倍 |
| 结构化数据有效率 | GSC「增强功能」报告 | 周 | 0 错误 |
| **AI 引用率** | **标准问题集手工抽查** | 周 | 见下 |

**AI 引用率测量法**（无需付费工具）：

固定 10 个问题，每周在 ChatGPT / Perplexity / Google AI Overviews / 豆包 / 元宝 各问一次，记录是否引用本站及其措辞：

```
1. DeepSeek V4.1-Flash 的 KV 缓存是多少？
2. 2026 年 9 月的 AI 要闻有哪些？
3. OpenAI Agents API 是什么？
4. 中国大模型价格战现状如何？
… （覆盖 5 个主实体 + 5 个主话题）
```

命中率写进 `state/geo-probe.jsonl`，**按月看趋势**。这是"被引用"这件事唯一诚实的度量方式。

---

## 7. 优先级与落地顺序

### P0 — 本周（全部是模板/配置改动，不依赖内容重写）

| # | 动作 | 影响面 | 依赖 |
|---|---|---|---|
| 1 | **自写 `partials/seo/schema.html`，替换已失效的 `_internal/schema.html`** | 全站 27,683 页 0%→100% | 无 |
| 2 | 修复 `og:image`（覆盖 opengraph partial；程序化 OG 卡先做新文） | 全站分享卡 | 无 |
| 3 | sitemap 收敛：剔除标签薄页、只留闭集分类 | 26,961→约 10,500 | 需先定闭集 |
| 4 | `llms.txt` + `robots.txt` AI 爬虫分段 | 全站 | 需先定爬虫策略 |
| 5 | **「引用信息索引」二选一**：实现 or 删除声明 | 全站文末 | 见 §8 拍板 |
| 6 | 清理根级幽灵产物 → 保留为 `newsroom/legacy/ghost-site/` | 仓库卫生 | 需先脱敏 |

### P1 — 2 周（生成提示词 + 门禁）

7. `title` ≤30 字规范 + `slug` 去时间戳后缀（**新文即生效，存量不动**）
8. 强制 h2 大纲（`##` 起步）
9. `sources` 结构化 + 一手源白名单 + 门禁 G2
10. `data/entities.yaml` + `entities` 闭集校验 + `main_topics` 闭集
11. G1/G2/G3 三层门禁接入 CI
12. `/about/` 重写 + `/corrections/` 建页

### P2 — 1 个月（存量治理）

13. 实体枢纽页重建（`/entity/`、`/topic/`、`/timeline/`）
14. 存量 9,383 篇的 `sources` 回填——**只对能自动找到来源的做，其余不臆造**（宁可缺，不可假）
15. 旧文 JSON-LD 校验（schema partial 上线即自动覆盖，此步只做抽检修复）
16. 构建环境统一（本地 0.147.0 vs 生产 0.147.8）

---

## 8. 需要拍板

| # | 决策 | 我的建议 | 理由 |
|---|---|---|---|
| 1 | **AI 爬虫策略：全开 / 只开检索类 / 关闭？** | **全开** | 本站的瓶颈是"被发现"，不是"被抄"。且 `.ai` 未备案 + 独立站身份，国内 AI 助手本就难引用；关掉等于放弃 GEO 主战场 |
| 2 | **「引用信息索引」：实现 or 删除？** | **实现** | 它是 GEO 的支点：一次改动同时修好承诺、溯源、一手源权重、引用锚点 |
| 3 | sitemap 里 tags：剔除 or 阈值化？ | **阈值化（≥5 篇才提交）** | 保留少量真实主题聚合页的 SEO 价值，同时砍掉 89% 薄页 |
| 4 | 实体枢纽页：现在建 or P2 建？ | **P2** | 眼下更缺的是 0% 的 JSON-LD；实体页没有 schema 支撑也是空壳 |
| 5 | 程序化 OG 图：只新文 or 全量？ | **只新文** | 全量 9,383 张会显著拖慢构建，收益递减 |
| 6 | `llms-full.txt` 是否发布？ | **不发布** | 全量正文的再分发等于把"内容资产"变成公开数据集，与既定的"原文全文不进公开仓库"原则一致 |

---

## 9. 边界与诚实提示（三条）

### 9.1 SEO 与 GEO 的市场不同，别用一套 KPI 衡量

| | SEO | GEO |
|---|---|---|
| 战场 | Google / Bing /（百度受限） | ChatGPT / Perplexity / Google AIO / 豆包 / 元宝 |
| 触发 | 关键词 | 自然语言问题 |
| 拿到的东西 | 点击流量 | **品牌提及 + 被引用的措辞权** |

**`.ai` 域名无法备案 → 百度覆盖天然受限**，这是域名选择的既定代价，不是可优化项。因此本规范的重心放在 **Google/Bing（SEO）+ ChatGPT/Perplexity/Google AIO（GEO）**。

### 9.2 国内 AI 助手的引用，靠站点本身几乎拿不到

豆包、元宝、Kimi 的检索源以微信公众号、知乎、头条、百家号为主，**独立站的抓取权重很低**。这意味着：

> 若目标是"被国内 AI 引用"，**必须做分发**（同一内容同步到公众号/知乎），而不是只做站点优化。

这是一条产品级结论，超出本规范范围，但必须先说清楚——否则会把"国内 AI 引用率低"误判为 SEO 做错了。

### 9.3 不要为了 GEO 牺牲诚实

GEO 领域流行一些技巧（堆 FAQ、加"专家观点"段落、虚构作者）。**这些在本站是负收益**：本站的核心资产是"温故智新AIGC实验室"的机构署名 + 一手源溯源。一旦引入虚构实体的 schema，等于自己拆掉 E-E-A-T 的地基。

本规范里所有 schema 字段都从**真实已有的 frontmatter** 派生；`sources` 缺失时**留空而不臆造**。

---

## 10. 交付检查清单

- [ ] `layouts/partials/seo/schema.html` 上线，3 篇样本通过 validator
- [ ] `baseof.html` 的中文 `_internal/schema.html` 调用已移除
- [ ] 全站抽检：JSON-LD 可解析率 100%，必填字段无空值
- [ ] `og:image` 全站可达（HTTP 200），`twitter:card` = `summary_large_image`
- [ ] sitemap 条目数 ≤11,000，`tags` 占比 <5%
- [ ] `llms.txt` 上线，`robots.txt` 含 AI 爬虫分段
- [ ] 「引用信息索引」承诺与产物一致（抽检 20 篇）
- [ ] `data/entities.yaml` 上线，`main_topics` 闭集生效
- [ ] G1/G2/G3 门禁接入 CI，含构建后 JSON-LD 抽检
- [ ] `state/geo-probe.jsonl` 建立，每周 AI 引用抽查开始
- [ ] 根级幽灵产物已清理并归档至 `newsroom/legacy/ghost-site/`

---

*本规范中所有"实测"数据来自 2026-09-11 对仓库、构建产物与线上站点的只读审计；复现脚本见 `newsroom/_geo_audit.py`。*
