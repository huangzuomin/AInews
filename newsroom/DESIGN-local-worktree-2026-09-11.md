# 本机工作树迁移方案（Local Worktree）

> 日期：2026-09-11
> 状态：**已执行**（迁移完成；全量构建验证进行中）
> 上游：`PLAN-master-2026-09-11.md` §3 P1.1 / §5；`REVIEW-zcode-plan-2026-09-11.md` §1
> 定位：本文是 `PLAN-master` 的**前置决策补丁**——它解除 P0.8 与 P1.1 的执行阻塞。

---

## 0. 一句话结论

**把工作树从 SMB（NAS）迁到本机 D 盘，NAS 从「工作树」降级为「只读镜像 + 媒体归档」。**

这一步不是性能优化，而是**解锁两个原计划无法执行的任务的前提**：

- P0.8「全量构建验证」——在 SMB 上每次都被拖到超时
- P1.1「`public/` 出仓」——在 SMB 上每次 `git` 操作都要 stat 5 万+ 文件，必被 SIGTERM

---

## 1. 为什么 SMB 不能当工作树（全部为 2026-09-11 实测）

| # | 操作 | 结果 | 机制 |
|---|---|---|---|
| 1 | `git status --short \| head -40` | **SIGTERM**（Exit 1, Signal SIGTERM） | `public/` 51,940 文件在版本控制内 → git 需 stat 全部条目，每次等于 5 万次网络往返 |
| 2 | `find public -type f \| wc -l` | **SIGTERM** | 同上，目录遍历延迟放大 |
| 3 | `Glob` 工具 | **30s 超时**（`Search timeout after 30000ms`） | 工具级超时，非磁盘速度问题 |
| 4 | `hugo` 构建（destination 指 C 盘） | 75.8s 后死于 `error copying static files: not enough space` | 静态资源 6,420 张图先拷贝，正文页其实已渲染完 |
| 5 | `hugo --staticDir <path>` | `--staticDir` **不是 CLI 参数** | 无法用命令行参数绕开 static 拷贝 |
| 6 | config 覆盖 `staticDir` | 未生效 | 该覆盖对构建路径不生效，静态文件照拷 |

**关键判断**：问题**不是带宽**，而是**小文件元数据操作的延迟放大**。`W:` 上任何 O(全库) 的操作都会撞上超时，而 git 的基本操作恰好都是 O(全库)。这不是调参能解决的，是**位置选错了**。

**旁证**：迁到 D 盘后，`content/`（9,989 文件）复制耗时约 3 分 47 秒——**一次性代价**；此后所有 git 与构建操作都在本地块设备上，不再有 O(5 万) 网络往返。

---

## 2. 目标拓扑

```
┌─────────────────────────────────────────────────────────────┐
│  D:\Work\neican-ai\        ← 唯一可写工作树（Single Writer）  │
│    ├── content/  layouts/  themes/  static/  data/            │
│    ├── newsroom/  （已 gitignore：文档 / 脚本 / 状态）          │
│    ├── .git/      （完整历史）                                 │
│    └── public/    （构建产物，P1.1 后不再入库）                 │
│                                                              │
│    职责：开发 · 构建 · git 操作 · push                         │
└───────────────────────┬─────────────────────────────────────┘
                        │ git push（唯一出口）
                        ▼
              ┌──────────────────┐
              │  GitHub (公开库)  │  ← 权威副本 + CI 调度
              └────────┬─────────┘
                       │ GitHub Actions
                       ▼
              ┌──────────────────┐
              │ Vercel / CF Pages │  ← 发布层
              └──────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  W:\hugo (NAS /volume4/docker/hugo/hugo)  ← 降级              │
│    ✗ 不再执行 git 操作                                        │
│    ✗ 不再执行构建                                             │
│    ✓ 媒体归档（图片 / 视频）                                   │
│    ✓ 证据归档（P4.1 的全文归档）                               │
│    ✓ 由 D 盘单向 rsync 同步（只读镜像）                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 为什么落在 `D:\Work` 而不是 `D:\SSOT`

`D:\SSOT` 是 Syncthing「唯一真理」（folder id `r9mya-zkrve`）的同步根。

**把 git 工作树放进 Syncthing 同步目录是反模式**：git 已有自己的同步机制（GitHub），再叠一层文件级同步会带来 `.git/index` 与 `objects` 的并发改写，正是"单一写入者"红线要排除的情形。

Syncthing 实测配置（`%LOCALAPPDATA%\Syncthing\config.xml`）：

| folder | label | path |
|---|---|---|
| `r9mya-zkrve` | 唯一真理 | `D:\SSOT` |
| `chcfr-weex7` | VMbrain | `D:\SSOT\claudesidian\brain` |

`D:\Work` **不在同步范围内** → 选它。

> **副作用（须知）**：该工作树不会被 Syncthing 同步到家庭 PC / 办公室 PC。这是**有意的**——跨机一致性由 GitHub 承担，不由文件同步承担。

---

## 4. 单一写入者如何保障

| 层 | 权限 |
|---|---|
| **D 盘工作树** | 唯一持有 git 写权限 |
| **W 盘（NAS）** | 只读镜像；**不得**执行 `git commit` / `git push` |
| **CI** | 唯一持有发布权（写入部署目标） |
| **agent（会话）** | 只出 PR / Issue 评论，永不进入自动链路 |

**过渡期规则**：迁移完成到 W 盘正式退役之间，
1. 所有改动**只写 D 盘**；
2. 需要时由 D 盘 → W 盘**单向** `robocopy`（W 盘不接受反向写入）；
3. **PAT 轮换**（P0.1）后，W 盘上残留的 `deploy.py` 即使被误执行也必然 401——凭据撤回是物理约束，比"约定不改"可靠。

---

## 5. 迁移执行记录（已完成）

**源**：`W:\hugo`（SMB）→ **目标**：`D:\Work\neican-ai`（本地 NTFS）

**排除项**（构建产物 / 幽灵产物，非源文件）：

| 排除 | 原因 |
|---|---|
| `public/`（51,940） | 构建产物；P1.1 后出仓 |
| `public-test/`（469） | 同上 |
| 根级 `index.html` / `insights/` / `briefs/` / `topics/` / `entities/` / `concepts/` / `timeline/` / `categories/` / `tags/` 等 | 幽灵站产物（Hugo 0.161.1 生成，线上全 404）→ P0.7 归档 |

**已复制**：

| 目录 | 文件数 | 耗时 |
|---|---|---|
| `content/` | 9,989 | ≈3m47s |
| `static/` | 7,394 | ≈5m |
| `themes/` | 592 | 21s |
| `newsroom/` | 559 | 21s |
| `layouts/` | 29 | 2s |
| `data/` | 2 | 2s |
| `archetypes/` / `resources/` | 5 | 2s |
| `.git/` | 完整历史 | — |

**顺带发现**：`newsroom/` 有 559 个文件，其中 `_verify/`（26）+ `_verify2/`（500）是历次验证构建的脚手架残留（6MB）。已 gitignore，不影响仓库，但建议整理进 `newsroom/_scratch/`。

---

## 6. 验收标准

| # | 判据 | 状态 |
|---|---|---|
| 1 | `git status` 在 D 盘 3 秒内返回 | ✅（本地，无 SMB 往返） |
| 2 | 全量构建完成且 exit 0 | 进行中 |
| 3 | 构建产物含 JSON-LD 且可 `json.loads` | 进行中（单页验证已通过） |
| 4 | 构建可直接输出到 `D:\Work\neican-ai\public`，无 ENOSPC | 进行中 |
| 5 | 迁移后源文件清单与 W 盘一致（除排除项） | 待核 |

---

## 7. 风险与回滚

| 风险 | 缓解 | 回滚 |
|---|---|---|
| D 盘单点故障 | GitHub 是权威副本；每次 push 即异地备份 | `git clone` 重建 |
| 迁移期间 W 盘被并发写入 → 分叉 | 迁移窗口内冻结 W 盘写入；`git status` 交叉核对 | 以 GitHub 为准仲裁 |
| 排除 `public/` 后 Vercel 构建配置未对齐 | **切 CI 前必须先确认 Vercel 项目设置**（`vercel.json` 无 `buildCommand`/`outputDirectory`） | 保留 W 盘的旧产物 |
| `D:\Work` 不参与 Syncthing | **有意设计**：跨机一致性由 GitHub 承担 | 如需临时同步，改放 `D:\SSOT` 并接受反模式 |

**回滚成本**：低。W 盘原树**未被修改**（纯读取复制），随时可切回。

---

## 8. 迁移过程中修掉的一个真 bug（P0.8 附带）

在本地首次构建后抽检，发现 JSON-LD **被双重序列化**：

```html
<script type="application/ld+json">"{\"@context\":\"https://schema.org\",...}"</script>
```

外层多了一个引号、内层引号全部被转义 → `JSON.parse` 必然失败，等于**结构化数据仍然无效**。

**根因**：在 `<script>` 内，Go `html/template` 的上下文是 JavaScript；而 `jsonify` 返回 `template.HTML`（HTML 上下文类型）。类型不匹配时 Go 会把整段 JSON **再按 JS 字符串编码一次**。

**修复**：`| jsonify | safeJS`（`safeJS` → `template.JS`，与 JS 上下文匹配，原样输出）。

**这条正是 G3-b 存在的意义**：JSON-LD 是模板产物，构建时无法自证；若不解析产物，这个 bug 会带着"已经有了结构化数据"的假象上线。

> **教训（比 bug 本身重要）**：`grep -c 'application/ld+json'` 返回 1，**不等于**结构化数据有效。门禁必须做到 `json.loads`，而不是字符串计数。

---

## 附：一句话总结

**SMB 的问题不是慢，是 git 的每个基本操作都是 O(全库)，而 SMB 把每次元数据访问都变成一次网络往返——所以工作树必须落在本地块设备上，NAS 退回它擅长的角色：存大文件。**
