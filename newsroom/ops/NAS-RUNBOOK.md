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
```

**性能基线（NAS 本地 SSD）**

| 项 | 实测 |
|---|---|
| 全量构建 | **58.7 秒**（SMB 上 40 分钟后被 SIGTERM） |
| 页面数 | 43,942 |
| sitemap 条目 | 11,582 |
| JSON-LD / og:image 覆盖 | 27,671 / 27,671 |
| `<time datetime>` | 9,983 |
| `public/` 体积 | 3.0G |

---

## 5. 未完成（按阻塞强度）

| # | 事项 | 为什么阻塞 |
|---|---|---|
| 1 | `resources/_gen/` 被追踪 → **每次构建都弄脏工作区** | 自动化的"干净工作区"前提不成立；应 `.gitignore` + `git rm -r --cached` |
| 2 | `origin` 仍指本地裸仓库，**未指 GitHub** | 决定 NAS 是否成为 GitHub 的写入前端 |
| 3 | **P1.8 `public/` 出史**（`.git` 仍 2.96 GiB） | GitHub 推荐上限 1GB，不重写历史 push 很可能直接失败 |
| 4 | 常驻运行层（systemd timer/service）**未建立** | "跑起来"的实体还没有 |
| 5 | 群晖 n8n **仍在写 `W:\hugo`**（2,851 项脏） | 双写未解除，与"单一写入者"红线冲突 |
| 6 | `W:\hugo` 与 `D:\Work\neican-ai` **未退役** | 三副本并存 |
