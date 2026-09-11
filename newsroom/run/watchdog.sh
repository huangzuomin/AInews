#!/bin/sh
# 看门狗入口 —— 供 TrueNAS cronjob 调用（D30：走 midclt cronjob，不裸放 systemd）
#
# 为什么用 shell 包一层：cron 的环境极简（无 PATH 继承、无 TZ），
# 而 TrueNAS 上 / 只读、/home 与 /tmp 都挂 noexec——
# 所有可执行物与状态一律落在数据集内（见 NEICAN_RUN_DIR）。
set -eu

NEICAN_RUN_DIR="${NEICAN_RUN_DIR:-/mnt/SSD_Apps/apps/neican-run}"
export NEICAN_RUN_DIR
export TZ=Asia/Shanghai

SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WS=$(CDPATH= cd -- "$SELF_DIR/../.." && pwd)
cd "$WS"

mkdir -p "$NEICAN_RUN_DIR/state" "$NEICAN_RUN_DIR/logs"

# cron 里没有 stdout，一切都要自己落盘（否则失败无声 —— 正是本看门狗要治的病）
{
  echo "──── watchdog $(date '+%F %T %Z') ────"
  /usr/bin/python3 "$SELF_DIR/watchdog.py" "$@" || echo "watchdog exit=$?"
} >> "$NEICAN_RUN_DIR/logs/watchdog.cron.log" 2>&1

# 日志轮转：保留最近 2000 行
if [ -f "$NEICAN_RUN_DIR/logs/watchdog.cron.log" ]; then
  LINES=$(wc -l < "$NEICAN_RUN_DIR/logs/watchdog.cron.log")
  if [ "$LINES" -gt 2000 ]; then
    tail -n 1000 "$NEICAN_RUN_DIR/logs/watchdog.cron.log" > "$NEICAN_RUN_DIR/logs/watchdog.cron.log.tmp"
    mv "$NEICAN_RUN_DIR/logs/watchdog.cron.log.tmp" "$NEICAN_RUN_DIR/logs/watchdog.cron.log"
  fi
fi

exit 0
