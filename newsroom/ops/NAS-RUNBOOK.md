# NAS 工作区运维手册

> 日期：2026-09-11
> 定位：`PLAN-master-2026-09-11.md` 决策 **D28** 的配套运行文档。
> **本文档回答一个问题：这台机器怎么从零重放。**

---

## 0. 一句话

**工作树 = TrueNAS `truenasPAN` 的 `/mnt/SSD_Apps/apps/neican-ai`，经 SSH 操作。PC 只是编辑终端。**

---

## 1. 拓扑

```
        PC (任意终端)                      TrueNAS truenasPAN (192.168.50.224)
   ┌────────────────────┐              ┌──────────────────────────────────────┐
   │ VS Code Remote-SSH │─── ssh ─────▶│ /mnt/SSD_Apps/apps/neican-ai         │
   │ 或 SFTP 挂载       │   局域网      │   ├── content/ layouts/ static/ ...   │
   └────────────────────┘              │   ├── .git/   （唯一可写副本）        │
                                       │   └── public/ （构建产物，不入库）    │
   ┌────────────────────┐              │                                      │
   │ 记忆目录（暂留）    │              │ /mnt/SSD_Apps/apps/neican-ai.git     │
   │ W:\hugo\.workbuddy │              │   └── 裸仓库（本地镜像 / 传输通道）   │
   └────────────────────┘              │                                      │
                                       │ /mnt/SSD_Apps/apps/tools/bin/hugo     │
        GitHub (公开库) ◀──待接通───── │   └── v0.147.8 extended               │
        └─ CI 构建 + 发布              └──────────────────────────────────────┘
```

**为什么不在 PC、也不在群晖**
- 不在 PC：不满足 24/7 常驻（PC 关机即断）。原 D26 选 PC 的**理由**是"git 基本操作 O(全库)，SMB 把元数据访问变网络往返"——**真约束是"不在 SMB 上"，不是"在 PC 上"**。
- 不在群晖 247：`W:\hugo` 正是 SMB 那一份（`\\192.168.50.247\docker\hugo\hugo`），且只有 8GB 内存还被 Dify 全家占着。
- 在 TrueNAS 224：本地 SSD 块设备（满足 D26 的理由）+ 24/7 + 30GB 内存。

---

## 2. 从零重建（可重放）

```bash
# ── A. 权限（只能以 root 做一次）────────────────────────────
# 在 TrueNAS Web UI 的 Shell（root）里执行：
zfs create SSD_Apps/apps
zfs create SSD_Apps/apps/neican-ai
chown -R admin:builtin_administrators /mnt/SSD_Apps/apps
chmod 775 /mnt/SSD_Apps/apps /mnt/SSD_Apps/apps/neican-ai
usermod -aG docker admin

# sudo 免密：注意 /etc/sudoers 里【没有】@includedir /etc/sudoers.d
cp /etc/sudoers /etc/sudoers.bak
sed -i 's|^admin ALL=(ALL) ALL$|admin ALL=(ALL) NOPASSWD:ALL|' /etc/sudoers
visudo -c          # 必须 parsed OK

# ── B. 工具（装到数据集，不能装 /usr/local/bin）─────────────
mkdir -p /mnt/SSD_Apps/apps/tools/bin
cd /tmp && curl -sLO https://github.com/gohugoio/hugo/releases/download/v0.147.8/hugo_extended_0.147.8_linux-amd64.tar.gz
tar xzf hugo_extended_0.147.8_linux-amd64.tar.gz -C /mnt/SSD_Apps/apps/tools/bin hugo
chmod +x /mnt/SSD_Apps/apps/tools/bin/hugo
/mnt/SSD_Apps/apps/tools/bin/hugo version   # 必须 0.147.8 extended

# ── C. 仓库落地 ────────────────────────────────────────────
git init --bare -b main /mnt/SSD_Apps/apps/neican-ai.git
# 从来源（PC 或 GitHub）推入 main，然后本地 clone：
git clone /mnt/SSD_Apps/apps/neican-ai.git /mnt/SSD_Apps/apps/neican-ai

# ── D. 构建 ────────────────────────────────────────────────
export PATH=/mnt/SSD_Apps/apps/tools/bin:$PATH
export HUGO_CACHEDIR=/mnt/SSD_Apps/apps/tools/hugo_cache
cd /mnt/SSD_Apps/apps/neican-ai
hugo --gc --cleanDestinationDir --logLevel warn
python3 newsroom/gates/validate.py --gates g3b --built public --json
```

---

## 3. 四个平台陷阱（全部实测踩过）

| # | 现象 | 真因 | 正解 |
|---|---|---|---|
| 1 | 往 `/etc/sudoers.d/` 写的免密文件**永不生效** | TrueNAS 的 `/etc/sudoers` 只有 10 行、**没有 `@includedir /etc/sudoers.d`** | 直接改主文件里的 `admin ALL=(ALL) ALL` 行；改前备份、改后 `visudo -c` |
| 2 | `Permission denied` / `Read-only file system` | `/home` 与 `/tmp` 挂 **noexec**；`/usr/local/bin` 所在 root fs **只读** | 一切可执行文件装到数据集路径（`/mnt/SSD_Apps/apps/tools/bin`） |
| 3 | 后台任务里 `git push` 报 `~/.ssh Permission denied` | 沙箱拦 `~/.ssh`，后台任务拿不到提权通道 | **前台**执行 + 关闭沙箱 |
| 4 | `docker ps` 报 `permission denied ... docker.sock` | `admin` 不在 `docker` 组 | `usermod -aG docker admin`（需重新登录会话生效） |

---

## 4. 日常操作

```bash
# 构建（约 60 秒 / 43,942 页）
ssh openclaw224 'export PATH=/mnt/SSD_Apps/apps/tools/bin:$PATH; \
  cd /mnt/SSD_Apps/apps/neican-ai && hugo --gc --cleanDestinationDir'

# 产物抽检（阻断性门禁）
ssh openclaw224 'cd /mnt/SSD_Apps/apps/neican-ai && \
  python3 newsroom/gates/validate.py --gates g3b --built public --json'

# ── 内容生产线（L0→L1，约 21 秒）────────────────────────────
ssh openclaw224 '/mnt/SSD_Apps/apps/neican-ai/newsroom/run/pipeline.sh'
#   采集 → 归并 → 相关性闸 → 评分 → 排产
#   结果：raw/<day>/sources.jsonl、state/{events,scored,plan}-<day>

# 只渲染不落盘（看产物长什么样）
ssh openclaw224 'cd /mnt/SSD_Apps/apps/neican-ai/newsroom && \
  NEICAN_RUN_HOME=/mnt/SSD_Apps/apps/neican-run \
  python3 -m src.digest --kind morning --dry-run'

# 出完整一期（落盘 + 提交 + 尝试推送）
ssh openclaw224 '/mnt/SSD_Apps/apps/neican-ai/newsroom/run/emit.sh morning'
#   --dry-run     只渲染
#   --no-publish  落盘但不提交

# 运行态快照
ssh openclaw224 'cat /mnt/SSD_Apps/apps/neican-run/logs/{pipeline,pipeline.cron,watchdog,health}.log'
ssh openclaw224 'ls /mnt/SSD_Apps/apps/neican-run/state/'

# 今日 aihot 线索（`aihot.jsonl` 是线索层单独留的一份，便于"它报了哪些、我们漏了哪些"逐日对照）
ssh openclaw224 'cat /mnt/SSD_Apps/apps/neican-run/raw/2026-09-11/aihot.jsonl' \
  | python3 -c 'import sys,json;[print(json.loads(l)["source_name"],"|",json.loads(l)["title"][:40]) for l in sys.stdin if l.strip()]'

# 本地闸与 aihot 的判断分歧（有则说明两套独立判断不一致，是规则改进的燃料）
ssh openclaw224 'cat /mnt/SSD_Apps/apps/neican-run/state/disagreement-2026-09-11.jsonl 2>/dev/null | wc -l'
```

**生产线为什么是脚本不是工作流引擎**

链路需要的性质（确定性、可重放、便宜、可并发）与工作流引擎 / agent 的性质
（会话式、非线性、有状态）在数学上不兼容。把判断放进 cron，等于把不确定性放到
唯一有发布权的通道上。**纯 stdlib**（NAS 无 pip3），全部路径可重放。

**红线：写入 ≠ 发布**

```
NAS（写入）                           CI（发布）
pipeline → digest → git commit  ──▶  门禁校验 →（部署）
                    ↓
            只推送，不碰托管平台
```

`emit.sh` 只 commit + push；CI 保留校验与部署这层审计关卡。
**补跑不许说谎**：距名义时点 >3 小时则 `date` 记实际时间，不写 07:30。

**产物质量的唯一判据是读产物**

构建 rc=0、文件存在、字节数不为 0 —— 这三件事**都不代表产物是好的**。
实测踩过：摘要在 ASCII 小数点处被切断（「全网渗透率52.」）、frontmatter 结尾多一个逗号
（「…400 系列，。」）。两者都不报错、都不为空。所以改完清洗/截断逻辑必须**肉眼看 dry-run 输出**。

**性能基线（NAS 本地 SSD）**

| 项 | 实测 |
|---|---|
| 全量构建 | **58.7 秒**（SMB 上 40 分钟后被 SIGTERM） |
| 页面数 | 43,942 |
| sitemap 条目 | 11,582 |
| JSON-LD / og:image 覆盖 | 27,671 / 27,671 |
| `<time datetime>` | 9,983 |
| `public/` 体积 | 3.0G |
| **生产线全链（L0→L1）** | **20.9 秒**（fetch 20.07 / cluster 0.68 / score 0.08 / select 0.00） |

---

## 5. 未完成（按阻塞强度）

> 更新于 2026-09-11 22:00。**阶段 1–3 已全绿，生产线已挂调度并实跑验证（F10）。**
> 下表已剔除已消项；**排在最前的是"发布链"，它现在是唯一的硬阻塞。**

| # | 事项 | 为什么阻塞 |
|---|---|---|
| 1 | 群晖 n8n **仍在写 `W:\hugo`** | 双写未解除，与"单一写入者"红线冲突。**需人做（无群晖 247 入口）** |
| 2 | **D29 细粒度 token 未到位** | NAS 能 commit 但**不能 push** → 产物堆在本地。**已不再阻塞调度**（产出/发布已解耦，堆积这件事被 `emit-last.json` 显式盯着），但它是"站点真更新"的最后一段 |
| 3 | **CI 发布闸 `vars.DEPLOY_TARGET` 未配** | 与 #2 独立：即使 push 成功，deploy job 仍 `skipped`，站点不会更新 |
| 4 | **钉钉 webhook 未填** | 看门狗只记录不发告警；阶段 2.4 验收无法完成。**当前站点确实停更（15.2h），告警正在被抑制而非投递** |
| 5 | **P8 CF 边缘缓存 24h** | 部署成功 ≠ 新内容可见；AI 爬虫 24h 内抓旧版，对 GEO 致命 |
| 6 | **P1.8 `public/` 出史**（`.git` 仍 2.96 GiB） | GitHub 推荐上限 1GB；属优化项（增量 push 只有几百 KB），非当前阻塞 |
| 7 | `W:\hugo` 与 `D:\Work\neican-ai` **未退役** | 三副本并存（退役依赖 #1） |
| 8 | **同日双份风险**：旧产线写 `<day>-<slug>.md`，新产线写 `<day>.md` | 两者并存时同日会出现两份早报（线上已有 `2026-09-11-ai-2026-09-11-.md`）。**退役 #1 即可消除**，不要靠改名掩盖 |

**已消项**（此前列在本表，现已完成）

| 事项 | 解除方式 |
|---|---|
| ~~`resources/_gen/` 被追踪，每次构建弄脏工作区~~ | 提交 `6c7e051aae`；重跑构建后脏项 = 0 |
| ~~`origin` 未指 GitHub~~ | 改指 `github.com/huangzuomin/AInews`，本地裸仓库降为 `nas-local` |
| ~~常驻运行层未建立~~ | `midclt cronjob` id=1 `*/15`（看门狗）、id=2 `5,20,35,50`（体检），D30 |
| ~~生产线未挂 cron~~ | cronjob id=3 `30 7 * * *` / id=4 `0 19 * * *`，落进 `/etc/cron.d/middlewared`，并以 now+2min 探针实跑验证（21:53:02 触发，rc=0） |
| ~~"产出没有"不可观测~~ | `state/emit-last.json` + `watchdog.py` 本地频道；告警体直接区分"没产出"与"产出没发布" |
