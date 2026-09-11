#!/bin/sh
# neican.ai 工作区健康快照 —— 供 TrueNAS cronjob 每 15 分钟调用
#
# 与 watchdog.py 的分工：
#   watchdog.py —— 对外（线上站点新鲜度，真外部信号）
#   health.sh   —— 对内（工作区/磁盘/调度器是否正常，本机信号）
# 两者都要有：只看线上会漏掉"本机早就死了但站点还在吃 CF 缓存"；
# 只看本机会漏掉"本机一切正常但部署失败"。
set -u

NEICAN_RUN_DIR="${NEICAN_RUN_DIR:-/mnt/SSD_Apps/apps/neican-run}"
export NEICAN_RUN_DIR TZ=Asia/Shanghai
mkdir -p "$NEICAN_RUN_DIR/logs" "$NEICAN_RUN_DIR/state"

SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WS=$(CDPATH= cd -- "$SELF_DIR/../.." && pwd)
OUT="$NEICAN_RUN_DIR/logs/health.log"
SNAP="$NEICAN_RUN_DIR/state/health.json"

cd "$WS" || exit 3

# ── 采集（每项都必须能在失败时给出一个值 —— 快照脚本自己不能崩）─────
HEAD_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "?")

# 与远端是否同步。origin 现已指向 GitHub，但 NAS 未必 fetch 过
# （推送目前由 PC 中转）→ 回退到本地裸仓库的引用，避免恒为 "?"。
REMOTE_REF=""
REMOTE_SHA="?"
for ref in origin/main nas-local/main; do
  if git rev-parse --verify --quiet "refs/remotes/$ref" >/dev/null 2>&1; then
    REMOTE_REF="$ref"
    REMOTE_SHA=$(git rev-parse --short "$ref" 2>/dev/null || echo "?")
    break
  fi
done
if [ "$REMOTE_SHA" = "?" ]; then
  SYNC="无远端引用可比（未 fetch）"
elif [ "$HEAD_SHA" = "$REMOTE_SHA" ]; then
  SYNC="与 $REMOTE_REF 一致"
else
  SYNC="本地($HEAD_SHA) ≠ $REMOTE_REF($REMOTE_SHA)"
fi

# `grep -c` 无匹配时**退出码为 1**（尽管打印 0）→ 必须 `|| true`，
# 否则 set -u 之外仍会被 `|| echo "?"` 追加出一个多余的 "?"。
stats_or() { grep -c "$1" 2>/dev/null || true; }

DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
PAGES=$(find public -name '*.html' 2>/dev/null | wc -l | tr -d ' ')
BUILT_AT=$(stat -c %y public/index.html 2>/dev/null | cut -d. -f1 || echo "?")
DISK=$(df -h /mnt/SSD_Apps 2>/dev/null | tail -1 | awk '{print $4" free ("$5" used)"}')
# `grep -c` 出的是"含 id 的行数"，而 midclt 输出的是**单行压缩 JSON** →
# 结果恒为 1。恒为 1 的指标比没有指标更糟：它看起来永远正常。
CRON_N=$(sudo -n midclt call cronjob.query 2>/dev/null \
  | python3 -c "import sys,json;print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
[ -n "$CRON_N" ] || CRON_N="?"

WD_ISO="(无记录)"; WD_STALE="(无记录)"
if [ -f "$NEICAN_RUN_DIR/state/watchdog.json" ]; then
  WD_ISO=$(python3 -c "import json,sys;d=json.load(open('$NEICAN_RUN_DIR/state/watchdog.json'));print(d.get('_last_run',{}).get('iso','(无记录)'))" 2>/dev/null || echo "(读取失败)")
  WD_STALE=$(python3 -c "import json;d=json.load(open('$NEICAN_RUN_DIR/state/watchdog.json'));print(d.get('_last_run',{}).get('stale','(无记录)'))" 2>/dev/null || echo "(读取失败)")
fi

# ── 生产线自身的产出状态（对内信号里最重要的一条）────────────────
# 只要 push 凭据缺失、或 CI 的发布闸没开，线上日期就不会推进，
# 于是 watchdog 看到的永远是"停更"——分不清「没产出」和「产出没发布」。
# emit-last.json 由 run/emit.sh 的 EXIT trap 无条件写入（含失败路径）。
EMIT_JSON="$NEICAN_RUN_DIR/state/emit-last.json"
EMIT_LINE="(无记录)"; EMIT_AGE="(无记录)"; EMIT_ALERT=""
# 只对 **发布目标**（GitHub origin/main）算差距。不能拿 nas-local 顶替 ——
# 那是 NAS 上的传输中转，跟"是否已发布"是两回事，混用会得出"一切同步"的假结论。
if git rev-parse --verify --quiet refs/remotes/origin/main >/dev/null 2>&1; then
  AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo "?")
else
  AHEAD="未fetch"
fi
if [ -f "$EMIT_JSON" ]; then
  EMIT_SUM=$(python3 -c "
import json, datetime
d = json.load(open('$EMIT_JSON', encoding='utf-8'))
fin = d.get('finished_at') or ''
age, age_s = None, '?'
try:
    t = datetime.datetime.fromisoformat(fin)
    age = (datetime.datetime.now(t.tzinfo) - t).total_seconds() / 3600.0
    age_s = '%.1fh' % age
except Exception:
    pass
alerts = []
if d.get('rc') not in (0, None):
    alerts.append('ALERT 上一次 emit 失败 rc=%s（%s %s）—— 生产线未产出' % (
        d.get('rc'), d.get('kind'), d.get('day')))
elif age is not None and age >= 14:
    alerts.append('ALERT 生产线已 %.1f 小时无产出（阈值 14h）' % age)
if d.get('committed') and not d.get('pushed'):
    a = d.get('commits_ahead_of_origin')
    behind = '未知（未 fetch origin/main）' if a in (-1, None) else '%s 个提交' % a
    alerts.append('ALERT 本期已提交未推送（origin 落后 %s）—— 发布链断了' % behind)
print('%s %s | rc=%s committed=%s pushed=%s | ahead=%s|%s|%s' % (
    d.get('kind'), d.get('day'), d.get('rc'), d.get('committed'), d.get('pushed'),
    d.get('commits_ahead_of_origin'), age_s, '; '.join(alerts)))
" 2>/dev/null || echo "(读取失败)|?|")
  EMIT_LINE=$(printf '%s\n' "$EMIT_SUM" | cut -d'|' -f1)
  EMIT_AGE=$(printf '%s\n' "$EMIT_SUM" | cut -d'|' -f2)
  EMIT_ALERT=$(printf '%s\n' "$EMIT_SUM" | cut -d'|' -f3)
fi

# ── 输出 ──────────────────────────────────────────────────────────
{
  echo "──── health $(date '+%F %T %Z') ────"
  echo "worktree      : $WS"
  echo "HEAD          : $HEAD_SHA  ($SYNC)"
  echo "dirty files   : $DIRTY          # 必须恒为 0 —— 非 0 说明自动化前提被破坏"
  echo "public pages  : $PAGES"
  echo "public built  : $BUILT_AT"
  echo "disk SSD_Apps : $DISK"
  echo "cronjob count : $CRON_N"
  echo "watchdog last : $WD_ISO"
  echo "watchdog stale: $WD_STALE"
  echo "emit last     : $EMIT_LINE"
  echo "emit age      : $EMIT_AGE        # 生产线产出新鲜度（阈值 14h）"
  echo "commits ahead : $AHEAD        # 相对 origin/main 已提交未推送；>0 = 发布链断了"
  echo ""
} >> "$OUT"

cat > "$SNAP.tmp" <<EOF
{
  "checked_at": "$(date -Iseconds)",
  "worktree": "$WS",
  "head": "$HEAD_SHA",
  "remote_ref": "$REMOTE_REF",
  "remote_sha": "$REMOTE_SHA",
  "in_sync": $([ "$HEAD_SHA" = "$REMOTE_SHA" ] && echo true || echo false),
  "dirty_files": $DIRTY,
  "public_pages": $PAGES,
  "public_built_at": "$BUILT_AT",
  "cronjob_count": $CRON_N,
  "watchdog_last_run": "$WD_ISO",
  "watchdog_stale": "$WD_STALE",
  "emit_last": "$EMIT_LINE",
  "emit_age": "$EMIT_AGE",
  "emit_alert": "$EMIT_ALERT",
  "commits_ahead": "$AHEAD"
}
EOF
mv "$SNAP.tmp" "$SNAP"

# 轮转
L=$(wc -l < "$OUT" 2>/dev/null || echo 0)
if [ "$L" -gt 3000 ]; then
  tail -n 1000 "$OUT" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
fi

# 工作区脏 = 自动化前提被破坏，必须响亮（这是"沉默的故障"的典型）
if [ "$DIRTY" != "0" ]; then
  echo "ALERT: 工作区脏项 $DIRTY 个 —— 检查是否有进程在写仓库（多头写入）" >> "$OUT"
  exit 1
fi

# 生产线自己没产出（或产出没发布）—— 与"站点停更"是两个不同的病，
# 对外信号分不清，所以必须在对内信号里单独响亮。
if [ -n "$EMIT_ALERT" ]; then
  echo "$EMIT_ALERT" >> "$OUT"
  exit 1
fi
exit 0
