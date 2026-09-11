#!/bin/sh
# 产出并发布一期（早报 / 日报）。
#
# 全链路：采集 → 归并 → 评分 → 排产 → 编排 → 提交（→ 推送）
#
# "写入 ≠ 发布"这条红线的落地：
#   NAS 完成**提交**（写入），CI 保留**校验 + 部署**（发布闸）。
#   所以本脚本只 commit + push，不碰托管平台。
#
# 用法：
#   run/emit.sh morning
#   run/emit.sh daily
#   run/emit.sh morning --dry-run     # 只渲染，不落盘不提交
#   run/emit.sh morning --no-publish  # 落盘但不提交

set -u

KIND="${1:-}"
shift 2>/dev/null || true
DRY=0
NOPUB=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --no-publish) NOPUB=1 ;;
  esac
done

case "$KIND" in
  morning|daily) ;;
  *) echo "用法: run/emit.sh morning|daily [--dry-run|--no-publish]" >&2; exit 2 ;;
esac

REPO="/mnt/SSD_Apps/apps/neican-ai"
RUN_HOME="/mnt/SSD_Apps/apps/neican-run"
PY="${PY:-/usr/bin/python3}"
LOG="$RUN_HOME/logs/emit.log"

export NEICAN_RUN_HOME="$RUN_HOME"
export PYTHONUNBUFFERED=1
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

mkdir -p "$RUN_HOME/logs"
stamp() { date '+%Y-%m-%d %H:%M:%S'; }
say() { echo "[$(stamp)] $*" | tee -a "$LOG"; }

cd "$REPO/newsroom" || exit 2

say "═══ emit.sh $KIND 开始（dry-run=$DRY no-publish=$NOPUB）═══"

# ── 1. 重跑生产线（保证拿到最新 plan）
if [ "$DRY" -eq 0 ]; then
  sh "$REPO/newsroom/run/pipeline.sh" >> "$LOG" 2>&1 || say "WARN pipeline 非零退出，继续尝试用既有 plan"
fi

# ── 2. 编排
if [ "$DRY" -eq 1 ]; then
  "$PY" -m src.digest --kind "$KIND" --dry-run 2>&1 | tee -a "$LOG"
  exit 0
fi

"$PY" -m src.digest --kind "$KIND" 2>&1 | tee -a "$LOG"
RC=$?
if [ "$RC" -ne 0 ]; then
  say "ERROR 编排失败 rc=$RC（目标文件可能已存在，或当日无合格事件）"
  exit $RC
fi

# ── 3. 提交
if [ "$NOPUB" -eq 1 ]; then
  say "已落盘，按 --no-publish 跳过提交"
  exit 0
fi

DAY="$(date '+%Y-%m-%d')"
TARGET="content/morningnews/$DAY.md"
[ "$KIND" = "daily" ] && TARGET="content/newspaper/$DAY.md"

if [ ! -f "$REPO/$TARGET" ]; then
  say "ERROR 预期产物不存在：$REPO/$TARGET"
  exit 1
fi

git -C "$REPO" add "$TARGET"
if git -C "$REPO" diff --cached --quiet; then
  say "无变更可提交（内容与上一版相同）"
  exit 0
fi

git -C "$REPO" -c user.name='neican-bot' -c user.email='bot@neican.ai' commit -q \
  -m "content($KIND): $DAY 自动产出

由 NAS 生产线生成（newsroom/src/digest.py 模板轨）。
每个入选条目均为独立 Event（归并去重），并附原始来源链接。" \
  -- "$TARGET" || { say "ERROR 提交失败"; exit 1; }

say "已提交：$(git -C "$REPO" log --oneline -1)"

# ── 4. 推送（凭据缺失时明确降级，不静默失败）
if [ -f "$RUN_HOME/git-credentials" ] && [ -s "$RUN_HOME/git-credentials" ]; then
  if git -C "$REPO" push --quiet origin main >> "$LOG" 2>&1; then
    say "已推送 origin/main"
  else
    say "WARN 推送失败（提交已留在本地，不会丢失）"
  fi
else
  say "未配置 push 凭据（$RUN_HOME/git-credentials 为空）→ 提交留在本地，等 token 到位后补推"
fi

say "═══ emit.sh $KIND 结束 ═══"
