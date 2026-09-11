# PLAN: SEO / GEO 实施计划与决策记录

> 对象：AI内参（https://www.neican.ai）
> 日期：2026-09-11
> 上游：`SPEC-geo-seo-2026-09-11.md`（规格）
> 说明：SPEC 中 6 个待拍板项，本文件按「建议 + 最佳实践」直接决策并给出执行计划与验收标准。

---

## 一、决策记录（6 项待拍板 → 已定）

| # | 决策项 | **决定** | 依据 |
|---|---|---|---|
| D1 | AI 爬虫策略 | **全开，但分组声明并附加引用规范** | 本站瓶颈是"被发现"不是"被抄"；`.ai` 未备案 + 独立站在国内 AI 助手里抓取权重本就低，关闭等于放弃 GEO 主战场。用 `llms.txt` 的引用规范换取署名，比用 robots 拒绝换取"保护"更划算 |
| D2 | 「引用信息索引」 | **实现**（新增 `sources[]` frontmatter 契约 + 模板自动渲染 + schema `citation`） | 它是 GEO 的支点：一次改动同时修好①承诺违约 ②溯源可核 ③一手源权重 ④AI 引用锚点 |
| D3 | sitemap 里的标签页 | **阈值化：仅 ≥5 篇的标签页进 sitemap** | 保留真实主题聚合页的 SEO 价值，同时砍掉约 89% 薄页（67.2% 只有 1 篇） |
| D4 | 实体枢纽页 | **Phase 2 建**（本轮不做） | 眼下更缺的是 0% 的 JSON-LD；实体页没有 schema 支撑也是空壳。且需要先有 §D6 的实体注册表 |
| D5 | 程序化 OG 图 | **仅新文生成，存量回退站点默认图** | 全量 9,383 张会显著拖慢构建，收益递减；先验证再决定是否回填 |
| D6 | `llms-full.txt` | **不发布** | 全量正文再分发 = 把内容资产变成公开数据集，与既定的"原文全文不进公开仓库"原则冲突 |

### 本轮新增决策（实施中发现的必要项）

| # | 决策项 | **决定** | 依据 |
|---|---|---|---|
| D7 | 多个文章模板互相覆盖的问题 | **SEO 出口全部集中到 `layouts/_default/baseof.html`（项目级覆盖），不动各 single 模板** | 见 §二「实测发现」。一处生效，从根本上规避"改了一处没生效"这一类 bug |
| D8 | 构建环境不一致 | **锁定 Hugo 版本**（`package.json` 依赖或 CI 用 `hugomods/hugo` 固定 tag），本地与 CI 对齐 | 本地 0.147.0 vs 线上产物 0.147.8；**正是版本漂移让 `_internal/schema.html` 静默失效** |
| D9 | `main_topics` 闭集 | **12 项**（现网 11 个正常值 + `AI内参极速早报`），`--` 归入"待归类"并在 Phase 2 回填 | 治 616 值 / `--` 覆盖 9,308 篇 |

---

## 二、实测发现（本轮新增，改变实施方式）

### 2.1 四个文章模板，只有一个活着

对构建产物做模板指纹比对（2026-09-11）：

| 页面 | `article-content`（仅 `layouts/page.html` 与 `morningnews/newspaper single.html` 有） | `ttu`（仅 `_default/single.html` 有） | `ad-slot-top`（仅 `_default/single.html` 注入） |
|---|---|---|---|
| `insights/*` | 1 | 0 | 0 |
| `newspaper/*` | 1 | 0 | 0 |
| `morningnews/*` | 1 | 0 | 0 |
| `about` | 1 | 0 | 0 |

且 `article-content` **在主题 `themes/ananke/layouts/` 中完全不存在**。

**结论**：`layouts/_default/single.html`（mtime **2026-09-10 16:54**，昨天刚改过、内含广告位注入与 `<time datetime>`）**对所有页面都没有生效**。

**这解释了 ZCode review 里"改了一处没生效"的真实机制**：改动写进了 `layouts/_default/single.html`，但 Hugo 的模板查找把 `layouts/page.html` 排在它前面 → 改动静默作废。同时意味着**文内广告位从未渲染过**。

**处置（D7）**：不逐个修模板（那正是问题本身），而是把 SEO 出口集中到 `baseof.html`——它对**所有** kind 生效，一处生效。各 single 模板的收敛列为 Phase 2。

### 2.2 无 `/search/` 页面

线上 `/search/` 返回 404。因此 JSON-LD 的 `WebSite.potentialAction`（SearchAction **必须省略**，否则会指向一个不存在的搜索入口——这属于"结构性谎言"，比缺失更糟。

### 2.3 `_internal/schema.html` 静默失效（已最小复现）

```
调用 "_internal/nonexistent.html"  →  Error: no such template   （构建失败）
调用 "_internal/schema.html"       →  exit 0、静默、产物为空
```

Hugo 对**不存在**的模板会硬报错，因此 `schema.html` 是**存在但已无输出**的空操作模板 → 全站 JSON-LD = 0 而构建永远成功。

---

## 三、实施计划

### Phase 0 — 模板与配置层（本周，零内容改动，可独立回滚）

| # | 动作 | 产出文件 | 验收标准 |
|---|---|---|---|
| P0-1 | 项目级 baseof 覆盖 + JSON-LD | `layouts/_default/baseof.html`、`layouts/partials/seo/schema.html` | 定向构建产物中 JSON-LD 覆盖率 100%；`json.loads` 可解析；`NewsArticle` 必填字段非空 |
| P0-2 | 修 `og:image` 与 Twitter 卡 | `layouts/partials/seo/opengraph.html` | 每页有 `og:image`（绝对 URL，HTTP 200）与 `twitter:card=summary_large_image` |
| P0-3 | 来源索引渲染 | `layouts/partials/seo/sources.html` + 4 个 single 模板挂载 | 有 `sources` 的页面出现 `## 来源` 区块 + schema `citation`；无 `sources` 时**不出现空区块、不臆造** |
| P0-4 | sitemap 收敛 | `layouts/sitemap.xml` | 条目 26,961 → ≤11,000；`tags` 占比 <5%；内容页 100% 保留 |
| P0-5 | AI 爬虫入口 | `static/llms.txt`、`static/robots.txt` | `llms.txt` 返回 200；robots 含 4 段 UA 分组 + sitemap + llms 指针 |
| P0-6 | 幽灵产物归档 | 根级 5 个目录 → `newsroom/legacy/ghost-site/` | 根目录只剩 Hugo 源文件；归档可 `git checkout` 恢复 |
| P0-7 | 「引用信息索引」承诺对齐 | `layouts/partials/menu-contextual*.html` | 声明文字改为"当有来源时附来源索引"，或按 P0-3 落地后保留承诺 —— **二者必须一致** |

**回滚方式**：全部是新增文件 + 少量模板行替换，`git revert` 单次提交即可；不改任何 content。

### Phase 1 — 生成层与门禁（1–2 周）

| # | 动作 | 依赖 |
|---|---|---|
| P1-1 | `title` ≤30 字、`slug` 去时间戳后缀 | 改生成提示词（`SPEC-selection-and-style` 已备） |
| P1-2 | 正文强制 `##` 起（h2 大纲） | 同上 |
| P1-3 | `sources[]` 结构化 + 一手源域名白名单 | P0-3 的契约 |
| P1-4 | `data/entities.yaml` + `entities`/`main_topics` 闭集校验 | D9 |
| P1-5 | 门禁脚本接 CI（G1/G2/G3/G3-b） | `newsroom/gates/validate.py` |
| P1-6 | `/about/` 重写 + `/corrections/` 建页 | — |

### Phase 2 — 存量治理（1 个月，可与 Phase 1 并行）

| # | 动作 | 约束 |
|---|---|---|
| P2-1 | 实体枢纽页（`/entity/`、`/topic/`、`/timeline/`） | 用真 taxonomy 重建，不提交 HTML |
| P2-2 | 存量 `sources` 回填 | **只对能自动定位一手源的做**；找不到就留空，不臆造 |
| P2-3 | 文章模板收敛为 1 个 | 需先确认 newspaper/morningnews 的特化逻辑是否仍需要 |
| P2-4 | 构建环境统一（D8） | — |
| P2-5 | 程序化 OG 图是否回填存量 | 先看 P0-2 的构建耗时增量 |

---

## 四、门禁与观测（Phase 1 落地）

```
生成 ──▶ G1 结构 ──▶ G2 事实 ──▶ G3 元数据 ──▶ 发布 ──▶ G3-b 构建后抽检 ──▶ 观测
```

- **G1 结构**：h2 ≥2、h3/h2 ≤3、正文起始层级 `##`、段长 ≤150、句长 ≤60、TL;DR 存在
- **G2 事实**：数字句带来源比 ≥0.6、一手源比 ≥0.5、来源域名白名单、无占位符
- **G3 元数据**：title ≤30、summary 80–160、featured_image 存在、`main_topics`/`entities` ∈ 闭集、`sources` 非空
- **G3-b 构建后**：JSON-LD 可 `json.loads`、`NewsArticle` 必填非空、`og:image` 可达

**观测**：GSC + Bing Webmaster（索引率/CTR/位置，周）；`state/geo-probe.jsonl` 手工 AI 引用抽查（10 问 × 5 平台，周）。

---

## 五、风险与红线

| 风险 | 缓解 |
|---|---|
| schema partial 语法错误导致构建失败 | 先在临时内容集上定向构建验证，再全量；`baseof` 有项目级覆盖，回滚 = 删一个文件 |
| `og:image` 用绝对 URL 但域名/CDN 变更 | 统一走 `absURL`，勿硬编码域名 |
| sitemap 收敛过激导致内容页丢失 | 白名单逻辑以 **section 为准**（insights/newspaper/morningnews 全收），只对 taxonomy 设阈值 |
| 存量 9,383 篇无 `sources` → 页面出现空区块 | 模板判空：无 `sources` 时**整块不渲染** |
| 改 `robots.txt` 影响现有收录 | 只增不减：`User-agent: *` / `Allow: /` 保持原样，仅**追加**分组与指针 |

**红线（继承自上游设计）**：
1. 不为 GEO 牺牲诚实——schema 字段全部从真实 frontmatter 派生，`sources` 缺失留空
2. 不引入虚构实体/作者
3. 单一发布通道——SEO 改动随同一提交走 CI，不开第二条部署路径

---

## 六、Phase 0 交付清单

- [ ] `layouts/_default/baseof.html`（项目级覆盖，含 SEO 出口）
- [ ] `layouts/partials/seo/schema.html`
- [ ] `layouts/partials/seo/opengraph.html`
- [ ] `layouts/partials/seo/sources.html`
- [ ] `layouts/sitemap.xml`
- [ ] `static/llms.txt`、`static/robots.txt`
- [ ] `data/entities.yaml`
- [ ] `newsroom/gates/validate.py`
- [ ] 定向构建验证记录（JSON-LD 可解析、og:image 存在）
- [ ] 幽灵产物归档
