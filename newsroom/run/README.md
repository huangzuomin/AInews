# newsroom/run —— 常驻运行层

> 阶段 2（PLAN-truenas-2026-09-11.md §2）。**先告警，后自愈。**
> 理由：旧引擎连续停摆 **36–37 天、零告警**。在没有告警之前上线生成层，
> 等于把同一个失败模式再复制一遍。**沉默本身是最贵的故障。**

## 文件

| 文件 | 作用 | 谁调用 |
|---|---|---|
| `watchdog.py` | **对外**：取线上产物判停更（心跳倒挂） | cronjob，每 15 分钟 |
| `watchdog.sh` | 上面那个的 cron 包装（补环境 + 落盘 + 轮转） | cronjob |
| `health.sh` | **对内**：工作区/磁盘/调度器快照 | cronjob，每 15 分钟 |
| `watchdog.conf.example` | 配置模板（**真实配置在仓库外**） | 部署时复制 |

两个方向都要有，互为盲区补充：

- 只看线上 → 漏掉「本机早就死了，站点还在吃 Cloudflare 缓存」
- 只看本机 → 漏掉「本机一切正常，但 Vercel 部署失败」

## 拓扑（硬约束，实测得出）

```
代码（本仓库，版本控制）           运行态（仓库外，绝不入库）
/mnt/SSD_Apps/apps/neican-ai/      /mnt/SSD_Apps/apps/neican-run/
  newsroom/run/*.py  *.sh            watchdog.conf      ← 含密钥
                                     state/*.json       ← 告警幂等状态
                                     logs/*.log         ← cron 无 stdout，必须落盘
```

**为什么运行态必须在仓库外**：watchdog 每次运行都写状态文件。若放在仓库内，
每个周期都会把工作区弄脏 → 破坏「构建后 `git status` 恒为空」这个自动化前提
（该前提由 P1.1 `resources/_gen` 出仓换来，见 commit `6c7e051aae`）。

## TrueNAS 平台陷阱（每条都踩过）

| 陷阱 | 表现 | 对策 |
|---|---|---|
| `/etc` 在 boot environment | 路径含版本号 `boot-pool/ROOT/24.10.2.4/etc`，**系统升级换 BE 即重置** | 调度走 `midclt call cronjob.create`（存配置库，升级保留），**不裸放 systemd 单元** |
| `/` 只读 | 装不进 `/usr/local/bin` | 可执行物放数据集，如 `/mnt/SSD_Apps/apps/tools/bin` |
| `/home` 与 `/tmp` 挂 `noexec` | 脚本放这里**无法执行** | 一律放 `/mnt/SSD_Apps/apps/...` |
| 远端默认 shell 是 **zsh** | `for f in *.json` 无匹配时 `nomatch` 直接致命退出 | 传输脚本用 `ssh ... "bash -s"` 显式指定 |
| 无 pip3 | 装不了 requests 等 | 全部脚本 **只用 stdlib** |

## 部署（从零可重放）

```bash
RUN=/mnt/SSD_Apps/apps/neican-run
WS=/mnt/SSD_Apps/apps/neican-ai

sudo mkdir -p "$RUN"/{state,logs}
sudo chown -R admin "$RUN"
chmod +x "$WS"/newsroom/run/*.sh

# 配置（含密钥，600）
install -m 600 /dev/stdin "$RUN/watchdog.conf" <<'EOF'
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=<填>
HEARTBEAT_URL=
EOF

# 调度：走 midclt（见上表）
sudo midclt call cronjob.create '{
  "command":"/mnt/SSD_Apps/apps/neican-ai/newsroom/run/watchdog.sh",
  "description":"neican watchdog (site freshness)",
  "schedule":{"minute":"*/15"},
  "enabled":true,"user":"admin"}'

sudo midclt call cronjob.create '{
  "command":"/mnt/SSD_Apps/apps/neican-ai/newsroom/run/health.sh",
  "description":"neican health snapshot",
  "schedule":{"minute":"5,20,35,50"},
  "enabled":true,"user":"admin"}'
```

## 日常

```bash
# 手动跑一次（看检测结果，不发告警）
python3 /mnt/SSD_Apps/apps/neican-ai/newsroom/run/watchdog.py --dry-run

# 机器可读
python3 .../watchdog.py --json --dry-run

# 验收测试：强制判定停更（阈值 0），看告警体长什么样
python3 .../watchdog.py --threshold 0 --force-alert

# 看最近日志
tail -30 /mnt/SSD_Apps/apps/neican-run/logs/watchdog.cron.log
tail -30 /mnt/SSD_Apps/apps/neican-run/logs/health.log

# 调度器现状
sudo midclt call cronjob.query | python3 -m json.tool | head -40
```

## 阈值依据

| 频道 | 阈值 | 依据 |
|---|---|---|
| 全站 `/index.xml` | 14h | 早报 07:30 + 日报 19:00 → 最大自然间隔 12h，留 2h 发布余量 |
| 早报 `/morningnews/` | 30h | 承诺每日 07:30；漏一次就报 |
| 日报 `/newspaper/` | 30h | 承诺每日 19:00 |
| 洞察 `/insights/` | 24h | 目标每日多篇，暂无硬承诺 |

同一故障**每 6 小时最多告警一次**（`REALERT_AFTER_H`）：不能每 15 分钟刷群，
但也不能只报一次就哑 —— 只报一次的话，夜里发生、早上才看到，等于没报。

## 一个真实的技术约束

线上 `/index.xml` 是 **7.2 MB**，且 Cloudflare **不支持 Range 请求**
（实测 `HTTP/2 200`，无 `Content-Range`，直接回全量）。
但 Hugo RSS 按时间**倒序**，最新条目必在头部 → 脚本用 `read(N)` 截断流，
只取头部 32–64 KB。**不要**改成先下载全文再解析。
