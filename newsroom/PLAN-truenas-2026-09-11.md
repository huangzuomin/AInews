# TrueNAS 实施计划

> 日期：2026-09-11 · 状态：**执行中**（阶段 1 已完成，阶段 2 已上线待接告警通道）
> 定位：`PLAN-master-2026-09-11.md` 是**总口径**（做什么、为什么）；本文件是**执行册**（在哪做、怎么落、怎么验）。
> 冲突时以本文件为准，并把变更回写 master。

---

## 执行状态（2026-09-11 19:00 更新）

| # | 任务 | 状态 | 证据 |
|---|---|---|---|
| 1.1 | `resources/_gen/` 出仓 | ✅ | 提交 `6c7e051aae`；**重跑构建后 `git status` 脏项 = 0** |
| 1.2 | `origin` 指向 GitHub | ✅ | `origin`=github.com/huangzuomin/AInews；本地裸仓库降为 `nas-local` |
| 1.3 | 首次 push | ✅ | `dd49f6fe33..6c7e051aae`，174 对象 / 717 KiB |
| 1.4 | CI 首跑 | ✅ | run `34591260495`：门禁 success / 构建 success / 发布 skipped |
| 1.4 | 仓库 Variables | ✅ | `GATES_ENFORCE=false`、`STALE_HOURS=14`（Secrets 为空） |
| 2.1 | 调度器走 `midclt` | ✅ | cronjob id=1 `*/15`、id=2 `5,20,35,50`，enabled；`/etc/cron.d/middlewared` 已装载，cron 服务 active |
| 2.2 | 心跳倒挂看门狗 | ✅ | `newsroom/run/watchdog.py`（提交 `4d47b013f3`）；**生产路径 `cronjob.run 1` 首跑通过**，4 频道全部解析 |
| 2.3 | 告警通道（钉钉） | ⏳ | 代码就绪；缺 `DINGTALK_WEBHOOK`（**需人提供**） |
| 2.4 | 验收：停更 15 分钟内告警 | ⏳ | 检测逻辑已验（`--threshold 0` 正确触发、告警体渲染正确）；**投递未验**（通道未接） |
| 0.2 | 停 n8n 容器 | ⛔ | 无群晖 247 入口 |
| 0.3 | 撤销 GitHub PAT | ⛔ | 需网页操作（GitHub 无 API 可撤 classic PAT） |
| 0.4 | 凭据轮换（21 组） | ⛔ | 依赖 0.2 / 0.3 |
| 1.5 | 旧副本退役 | ⏸ | 等 0.2（否则双写未解除，退役会丢东西） |
| D29 | NAS 持写凭据 | ⏳ | 通道已铺：`credential.helper` → 仓库外 600 文件 `/mnt/SSD_Apps/apps/neican-run/git-credentials`；**缺细粒度 token** |

### 执行中新增的硬事实（回写 master）

**F1 · Vercel 是连着的，`push → 部署`自动发生。**
提交上有 `Vercel | pending | "Vercel is deploying your app"`；历史 Production deployments 与每次 push 一一对应（`dd49f6fe33`、`f46b09b666`…）。
→ 含义有两面：**部署不是需要新接的环节**；但**部署会独立失败**（它有自己的构建队列，且比 CI 慢得多）。看门狗取「线上产物」而非「仓库内容」，正是为了覆盖这一层。

**F2 · 线上 `/index.xml` = 7.2 MB 且 Cloudflare 不支持 Range。**
实测 `HTTP/2 200`、无 `Content-Range`，请求 `0-3000` 字节仍回全量。
→ 看门狗必须用 `read(N)` 截断流取头部（Hugo RSS 时间倒序，最新条目必在头部）。**不要改成"先下载全文再解析"。**

**F3 · `/index.xml` 有 9,984 条 —— feed 自身需要治理。**
7.2 MB 单文件对爬虫与读者都不友好（`rssLimit` 疑似未设）。
→ 新增待办 **P7**：`rssLimit` 收敛到 50–100（与 sitemap 收敛属同源问题：默认值即"全量"，而全量对本站从来不是正确值）。

**F4 · 部署完成前不能判定模板失效。**
截至 18:58，`/llms.txt` 仍 404、`/robots.txt` 仍 67 B —— 但那是**部署尚未完成**，不是模板写错。
→ 判定纪律：`/llms.txt`、新版 robots、JSON-LD 的线上验证**必须等 Vercel 部署结束**再做，否则会把"还没部署"误判成"模板没写对"。

**F5 · `fetch-depth: 0` 的代价可接受，但 Actions 版本已过时。**
门禁 job 约 3 分钟完成（含全史 checkout）。
但出现弃用警告：`actions/checkout@v4`、`actions/setup-python@v5` 已被强制运行在 Node 24。
→ 待办：升 `actions/checkout@v5` / `actions/setup-python@v6`。

**F6 · CI 首次运行的产物数字（GitHub 侧，与 NAS 本地一致）。**
`期望 0.147.8，实际 0.147.8` · 构建 **87.2 s**（NAS 本地 58.7 s）· HTML 27,674 · sitemap 11,582 · JSON-LD 27,671 · og:image 27,671 · G3-b 抽检 **60 篇 verdict=pass**。

---

## 0. 三条新证据（2026-09-11 实测，直接决定实施方式）

| 证据 | 实测值 | 对实施的硬影响 |
|---|---|---|
| **旧 n8n 其实已死 38 天** | 最后一次产出 `8/4 18:40`，提交信息是 `📈 Daily AI digest: {{ items.length }} articles` —— **模板字面量漏出，说明当时的渲染已经坏了** | 「关闭旧系统」不是止血，是**解除双写 + 收回凭据**。风险远低于预期 |
| **`/etc` 挂在 `boot-pool/ROOT/24.10.2.4/etc`** | `/` 只读、`/etc` 独立 `rw`；路径含版本号 | 裸放 systemd 单元**会被系统升级重置**（换 BE = 换 /etc）→ 常驻层必须走 `midclt` |
| **NAS 直连国内 LLM 全通** | bigmodel 200 / deepseek 401 / ark 401 / siliconflow 404 | 生成层可完全落在 NAS，不必绕 CI |

其他已确认前提：SSD_Apps 1.3T 几乎全空 · Python 3.11.9（**无 pip3**）· Hugo 0.147.8 extended 在 `/mnt/SSD_Apps/apps/tools/bin/hugo` · 全量构建 43,942 页 / **58.7 秒** · NAS 无 systemd 定制单元、无 crontab、`midclt cronjob.query` 返回 `[]`。

---

## 1. 现状判定：谁在写仓库

按提交信息签名可分三个写入者，**边界清晰**：

| 写入者 | 签名 | 活跃区间 | 状态 |
|---|---|---|---|
| 旧 n8n | `📈 Daily AI digest: {{ items.length }} ...` | ≤ 8/4 18:40 | **已停 38 天** |
| n8n 推送链（3 个工作流） | `cat > content/…` → `git add/commit/push ghp_…` | — | 在库中 **`active=0`** |
| **人工 + agent 复产** | `流水班 HH:MM：洞察《…》` / `content: 复产第一批` | 9/10 – 至今 | **当前唯一真实产能** |

n8n 里真正 `active=1` 的 7 个是**钉钉驱动的选题/写作链**（`[Module 1] Idea Amplifier copy` → `IndepthTopicPlanning` → `IdeaGenerationandWriting` → `Finaldraftcopywriting`）+ 图片选择子流 + `Steemit 自动发布`（cron 21:00）。

**结论：现在没有"自动内容生产系统"在跑，只有"人肉产线 + 一个 38 天没产出的旧引擎"。** 本计划的核心任务就是把这条人肉产线搬到 NAS 上做成无人值守。

---

## 阶段 0 · 冻结旧系统（可逆，1 小时内）

**0.1 已完成的导出** ✅
线上 30 个工作流已只读导出 → `D:\Work\n8n\live-export-20260911\`（旧存档 `D:\Work\n8n\*.json` 是 2025-06 版本，**已过期 15 个月，不可作数**）。下一步：脱敏后入 `newsroom/legacy/n8n-live/`。

**0.2 停容器**（需群晖侧操作）
DSM → Container Manager → 容器 `n8nio-n8n-1-2` → 停止。
安全性来自 compose 定义本身：`restart: "no"` → **停掉不会自启；`start` 即完全恢复**。不删卷、不删容器。

**0.3 撤销 GitHub PAT** `ghp_****Jj8W`
GitHub → Settings → Developer settings → Personal access tokens → Revoke。
这是**唯一能立即生效的 kill switch**，同时清掉"明文口令进仓库"的历史遗留。撤销后旧链路的 push 能力即刻归零。

**0.4 凭据清点与轮换**（n8n 内共 **21 个**）
8×Google Gemini / DeepSeek / OpenAI / OpenRouter / 硅基流动 / Supabase ×2 / GitHub / Pexels / 钉钉 / Steemit。
处置原则：**用不到的废弃，要复用的轮换后另存**（旧的留在 n8n 里的那份等于泄露）。

**0.5 保留期**
`/volume4/docker/n8n/` 整卷**保留 30 天不删**（含 `database.sqlite` 7.63 GB + 加密密钥 `config` 56 B）。30 天后单独确认再删。

> ⚠️ **两条安全发现，请单独处理**
> 1. `/volume4/docker/n8n/config`（56 字节）= **n8n 凭据加密密钥明文**，且该目录在 SMB 共享 `\\192.168.50.247\docker` 上 → 任何能挂这个共享的设备都能解密全部 21 组凭据。
> 2. n8n 有**公网入口** `http://n8n.huangzuomin.com:7100`，且 `N8N_SECURE_COOKIE=false`、`NODE_TLS_REJECT_UNAUTHORIZED=0`。停容器即关闭该面。

**验收**：`W:\hugo` 连续 24h 无新提交；n8n `healthz` 不可达。

---

## 阶段 1 · NAS 成为唯一写入者（半天）

| # | 动作 | 命令/位置 | 验收 |
|---|---|---|---|
| 1.1 | `resources/_gen/` 出仓 | `git rm -r --cached resources/_gen && echo 'resources/_gen/' >> .gitignore` | NAS `git status` **恒为空**（含构建后） |
| 1.2 | `origin` 指向 GitHub | 保留本地裸仓库为 `nas-local`，新增 `origin` = `github.com/huangzuomin/AInews` | `git remote -v` 三行 |
| 1.3 | 首次 push | 8 提交 / 120 对象（几百 KB） | GitHub 上出现 `de5c7ac6f8` |
| 1.4 | CI 首跑 + 配 Variables | `.github/workflows/build.yml`；`GATES_ENFORCE` / `HEARTBEAT_URL` / `DEPLOY_TARGET` | Actions 全绿，artifact 可下载 |
| 1.5 | 旧副本降级 | `W:\hugo` → 只读归档；`D:\Work\neican-ai` → 退役 | 两处不再产生提交 |

> 1.1 是**前提而非优化**：`resources/_gen/` 每次构建都会改写（指纹抖动 + 删旧指纹），它被追踪就意味着**每次构建都让工作区变脏**，"干净工作区"这个自动化前提不成立。

---

## 阶段 2 · 常驻层与观测（1–2 天）— **先告警，后自愈**

**2.1 调度器选型：`midclt` 而非裸 systemd**
```bash
sudo midclt call cronjob.create '{"command":"/mnt/SSD_Apps/apps/neican-ai/newsroom/run/health.sh","description":"neican health","schedule":{"minute":"*/15"},"enabled":true,"user":"admin"}'
```
理由（有证据）：`/etc` 位于 boot environment，**升级即重置**；cronjob 存在 TrueNAS 配置库，升级保留。
配套要求：所有常驻脚本放在**数据集**上（`/mnt/SSD_Apps/apps/neican-ai/newsroom/run/`），因为 `/` 只读、`/home` 与 `/tmp` 都是 `noexec`。

**2.2 心跳倒挂看门狗上线**
取**线上产物**（`neican.ai` RSS / sitemap）判停更，不依赖 NAS 自报。这是唯一的**真外部**信号。

**2.3 告警通道**
钉钉群机器人（复用旧系统的习惯，零新增依赖）。阈值：`STALE_HOURS=14`（早报 07:30 + 日报 19:00 之间不应有 >14h 空档）。

**2.4 为什么这一步排在生成层之前**
旧引擎连续停摆 **36–37 天，零告警**，三频道同时断（洞察 8/5–9/9、早报 8/5–9/10、日报 8/4–9/9）。**沉默本身是最贵的故障。** 在没有告警之前上线生成层，等于把同一个失败模式再复制一遍。

**验收**：人为制造停更 → **15 分钟内**收到告警。

---

## 阶段 3 · 采集层（2–3 天）

- **3.1 Source registry** —— `data/sources.yaml` 闭集（RSS / RSSHub / API），每条带 `tier`（一手源 / 二手源）与 `license`。
- **3.2 采集** —— stdlib `urllib`（NAS 无 pip3，不为采集引依赖）→ 原文**原样落盘** `newsroom/raw/YYYY-MM-DD/`，带 `sha256` + `fetched_at`。**落盘即可重放**，这是"可重放"红线的落地方式。
- **3.3 归一 + 去重** —— 字符串匹配升级为 **Event 归并**（Source → Event → Story）：同一事件的多家报道合并为一个 Event，日报 5 条 = 5 个不同 Event。

**验收**：给定任意一天，能从 `raw/` 离线重放整条链路得到相同结果。

---

## 阶段 4 · 生成层（3–5 天）

| 环节 | 模型 | 说明 |
|---|---|---|
| 分类闸 / 打分 | GLM-4.7-Flash（含免费档） | 先筛价值，再花钱 |
| 深度稿 | DeepSeek-V4-Pro | 产出 `content/insights/` |
| 审校 | **换另一家** | 交叉验证，不用同一家自审 |
| 配图 | vision 模型 | 只接受站内路径（外链图是版权盗链风险） |

**门禁挂载点**：G1 结构 → G2 事实（一手源 ≥50%）→ G3 元数据（闭集·非空）→ **G3-b 构建后抽检**。
两档策略不变：P0–P3 `warn-only`，**G3-b 从 P0 起即阻断**。

**验收**：连续 3 天产出，`newsroom/gates/validate.py` 零阻断，G3-b 零失败。

---

## 阶段 5 · 发布层（2 天）

- **早报 07:30 / 日报 19:00** —— 硬承诺。落点：NAS 定时（不依赖 GitHub 调度器，见 D29）。
- **发布闸** —— 写入 ≠ 发布：NAS 完成提交与推送，**CI 保留校验 + 部署**这层审计关卡。
- **NAS 凭据最小化** —— 只持一枚**单仓库、`contents:write` 的细粒度 token**，替代旧的全权 `ghp_`。

**验收**：连续 7 天，两个时点各准点一次，误差 <10 分钟；无人工介入。

---

## 8. 架构决策记录

**D28（已生效）** 工作区宿主 = TrueNAS `SSD_Apps` 池 `/mnt/SSD_Apps/apps/neican-ai`。
推翻 D26 的**结论**（原定 D 盘本地树），保留其**理由**（工作树必须落在本地块设备）——NAS 上的 SSD 数据集同样满足，且额外满足 24/7。SMB 换成 SSH/本地 IO 是硬要求：同样内容 SMB 上 40 分钟被 SIGTERM，本地 **58.7 秒**。

**D29（本计划提出）** 执行架构取 **B：NAS 跑全链路，CI 只做校验与发布**。部分推翻 D02「GitHub Actions 是唯一调度器」与 D05「NAS 零凭据」。
论据：① D07 承诺的 07:30 / 19:00 若依赖 GitHub 调度器要叠外部 cron（Actions scheduled 会延迟，且**仓库 60 天无提交会被自动禁用**）；② NAS 已 24/7；③ 「写入 ≠ 发布」的红线仍然成立，CI 依旧是发布闸。**代价明示：NAS 必须持有仓库写凭据**（因此要求 D29 配套的细粒度 token）。

**D30（本计划提出）** 常驻层用 `midclt cronjob`，不裸放 systemd 单元。见 2.1。

**D31（本计划提出）** 旧系统：**停容器 + 留卷 30 天 + 撤凭据**，不迁移、不导入。见阶段 0。

---

## 9. 明确不做的事

- **不把 n8n 搬到 TrueNAS** —— 不搬旧引擎。
- **不导入旧 `database.sqlite`** —— 7.63 GB 病理性膨胀本身就是故障源。
- **不让 Hugo 构建里出现 LLM 调用** —— 构建必须快且确定（58.7 秒的前提）。
- **不为了迁移而迁移** —— 旧系统已 38 天无产出，没有"停机窗口压力"。

---

## 10. 总验收（"跑通"的定义）

| 维度 | 判据 |
|---|---|
| 单一写入者 | NAS 一处可写，构建后 `git status` 恒为空 |
| 无人值守 | 连续 7 天，早报 07:30 / 日报 19:00 准点，零人工 |
| 可重放 | 任取一天，能从 `raw/` 离线重放得到相同产物 |
| 可观测 | 人为停更 → 15 分钟内告警 |
| 可回退 | 旧卷保留 30 天；任一阶段可单独回滚 |
| 凭据最小 | 无全权 PAT；无明文凭据在版本控制或共享目录 |

---

## 附：需要人来做的事（AI 无法代办）

1. **群晖侧停容器**（`n8nio-n8n-1-2`）—— 或提供群晖 SSH 通道。
2. **撤销 GitHub PAT `ghp_****Jj8W`**。
3. **钉钉群机器人 webhook**（告警通道用）。
4. **确认 D29 架构选型**（NAS 持写凭据）—— 这条推翻了两项原红线，需明确背书。
