#!/bin/sh
# 生产线编排（L0→L1：采集 → 归并 → 评分 → 排产）
#
# 由 TrueNAS cronjob 调用（见 newsroom/ops/NAS-RUNBOOK.md）。
# 运行态全部落在仓库外，保证构建后 `git status` 恒为空。
#
# 用法：
#   run/pipeline.sh                # 全链路
#   run/pipeline.sh --from score   # 从评分起

set -u

REPO="/mnt/SSD_Apps/apps/neican-ai"
RUN_HOME="/mnt/SSD_Apps/apps/neican-run"
PY="${PY:-/usr/bin/python3}"

export NEICAN_RUN_HOME="$RUN_HOME"
export PYTHONUNBUFFERED=1
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

mkdir -p "$RUN_HOME/logs" "$RUN_HOME/state" "$RUN_HOME/raw"

LOG="$RUN_HOME/logs/pipeline.log"
STAMP="$(date '+%Y-%m-%d %H:%M:%S')"

# ── 日志轮转 ─────────────────────────────────────────────────────────
# 常驻进程的日志必须自己封顶。不封顶的后果不是"日志很大"，而是
# **磁盘写满之后的静默失败**：写日志失败、写 state 失败、git 提交失败，
# 全都不报错——正是本项目要治的那个病。
# 保留策略：超过 4000 行就截到最近 1200 行（约 1 天多的量，够定位最近故障）。
rotate() {
  f="$1"; max="$2"; keep="$3"
  [ -f "$f" ] || return 0
  n=$(wc -l < "$f" 2>/dev/null || echo 0)
  if [ "$n" -gt "$max" ]; then
    tail -n "$keep" "$f" > "$f.tmp" 2>/dev/null && mv "$f.tmp" "$f"
  fi
}

# ── 并发锁：用 mkdir 原子性，不依赖 flock（TrueNAS 上未必有）
LOCK="$RUN_HOME/state/.pipeline.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  AGE=$(( $(date +%s) - $(stat -c %Y "$LOCK" 2>/dev/null || echo 0) ))
  if [ "$AGE" -gt 3600 ]; then
    echo "[$STAMP] WARN 发现过期锁（${AGE}s），清除后继续" >> "$LOG"
    rmdir "$LOCK" 2>/dev/null
    mkdir "$LOCK" 2>/dev/null || { echo "[$STAMP] ERROR 无法获取锁" >> "$LOG"; exit 3; }
  else
    echo "[$STAMP] SKIP 上一次运行仍在进行（锁 ${AGE}s）" >> "$LOG"
    exit 0
  fi
fi

cleanup() { rmdir "$LOCK" 2>/dev/null; }
trap cleanup EXIT INT TERM

cd "$REPO/newsroom" || exit 2
echo "[$STAMP] ─── pipeline.sh 开始（args: $*）───" >> "$LOG"
"$PY" -m src.pipeline "$@" >> "$LOG" 2>&1
RC=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ─── pipeline.sh 结束 rc=$RC ───" >> "$LOG"
rotate "$LOG" 4000 1200
exit $RC
