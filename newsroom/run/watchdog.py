#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
neican.ai 站点新鲜度看门狗 —— 心跳倒挂（P0.6 / D30 阶段 2.2）

设计命题：**沉默本身是最贵的故障。**
证据：旧管线三频道同时停摆 36–37 天（洞察 8/5–9/9、早报 8/5–9/10、日报 8/4–9/9），
零告警。系统一直在"跑"，每天失败 30–50%，没有任何一环会告诉你它断了。

方向必须反过来：不是"我去问站点更新了没有"（轮询；检查器自己死了就静默），
而是"**没按时交货我就知道**"（心跳倒挂；缺席本身即是信号）。

判定依据取**线上产物**而非 content/ 目录 —— 这样同时覆盖两种故障：
  (a) 内容没生成  (b) 生成成功但部署失败
只看仓库会漏掉 (b)。实测 Vercel 是连着的（commit status 有 Vercel），
所以部署这一环确实会独立失败。

约束（实测得出，勿改）：
  * 本机无 pip3 → 只用 stdlib
  * /home 与 /tmp 挂 noexec，/ 只读 → 脚本与状态一律放数据集
    （默认 /mnt/SSD_Apps/apps/neican-run，见 RUN_DIR）
  * 运行态**必须**在仓库外，否则每次告警都会把工作区弄脏，
    破坏"构建后 git status 恒为空"这个自动化前提
  * 线上 /index.xml 是 7.2 MB 且 Cloudflare **不支持 Range**（实测 HTTP/2 200 无 Content-Range）
    → 但 Hugo RSS 按时间倒序，只需读头部若干 KB 即可拿到最新 pubDate。
      用 read(N) 截断流，不下载全文。

退出码：0 = 一切新鲜（或未配置告警通道而仅记录）；1 = 检出停更；2 = 自身故障（如全部源不可达）
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

# ── 路径 ────────────────────────────────────────────────────────────
RUN_DIR = os.environ.get("NEICAN_RUN_DIR", "/mnt/SSD_Apps/apps/neican-run")
STATE_FILE = os.path.join(RUN_DIR, "state", "watchdog.json")
# 生产线自产信号（由 run/emit.sh 的 EXIT trap 写入，仓库外）
EMIT_STATE_FILE = os.path.join(RUN_DIR, "state", "emit-last.json")
EMIT_MAX_AGE_H = 14
LOG_FILE = os.path.join(RUN_DIR, "logs", "watchdog.log")
CONF_FILE = os.environ.get("NEICAN_WATCHDOG_CONF", os.path.join(RUN_DIR, "watchdog.conf"))

SITE = "https://www.neican.ai"

# ── 监控对象 ────────────────────────────────────────────────────────
# max_age_h 的依据：
#   site      —— 全站（含洞察）任意频道有产出就会推进。14h 容纳发布延迟，
#                 远小于"一天没货"。（PLAN-truenas §2.3 定的阈值）
#   morningnews —— 早报，承诺每日 07:30。30h = 漏一次就报，容忍一次迟到。
#   newspaper —— 日报，承诺每日 19:00。同上。
#   insights  —— 洞察，目标每日多篇，暂无硬承诺 → 24h。
# read_bytes 只控制下载量，不影响判定（RSS 时间倒序，最新条目必在头部）。
CHANNELS = [
    {"key": "site",        "label": "全站",   "path": "/index.xml",             "max_age_h": 14, "read_bytes": 32768},
    {"key": "morningnews", "label": "早报",   "path": "/morningnews/index.xml", "max_age_h": 30, "read_bytes": 65536},
    {"key": "newspaper",   "label": "日报",   "path": "/newspaper/index.xml",   "max_age_h": 30, "read_bytes": 65536},
    {"key": "insights",    "label": "洞察",   "path": "/insights/index.xml",    "max_age_h": 24, "read_bytes": 65536},
]

RE_ITEM_DATE = re.compile(r"<(?:pubDate|dc:date)>([^<]+)</(?:pubDate|dc:date)>")
RE_ITEM = re.compile(r"<item>")

# 同一故障的重复告警间隔：避免每 15 分钟刷一次群；但也不能只报一次就哑
# （只报一次的话，夜里发生、早上才看到，等于没报）。
REALERT_AFTER_H = 6


# ── 基础设施 ────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    line = "%s [%s] %s" % (datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"), level, msg)
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as exc:            # 日志写不了不能影响判定
        print("WARN 日志写入失败: %s" % exc, flush=True)


def load_conf():
    """极简 key=value 配置（含密钥，故不入版本控制）。"""
    conf = {}
    if os.path.exists(CONF_FILE):
        with open(CONF_FILE, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().strip('"').strip("'")
    # 环境变量优先（便于一次性测试覆盖）
    for k in ("DINGTALK_WEBHOOK", "HEARTBEAT_URL", "STALE_HOURS_OVERRIDE"):
        if os.environ.get(k):
            conf[k] = os.environ[k]
    return conf


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, STATE_FILE)


def fetch_head(url, nbytes, timeout=30, retries=3):
    """只读前 nbytes 字节。Hugo RSS 时间倒序 → 最新条目必在头部。

    不做 Range（Cloudflare 实测不支持，会退化成全量 7.2 MB）；
    用 read(N) 截断，urllib 会在拿到 N 字节后停止读取并关闭连接。
    """
    ctx = ssl.create_default_context()
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "neican-watchdog/1.0 (+https://www.neican.ai)",
                "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
                "Cache-Control": "no-cache",
            })
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                body = resp.read(nbytes)
            return body.decode("utf-8", errors="replace"), None
        except Exception as exc:                      # noqa: BLE001 —— 网络层什么都可能抛
            last = "%s: %s" % (type(exc).__name__, exc)
            if attempt < retries:
                time.sleep(5 * attempt)
    return None, last


def parse_latest(body):
    m = RE_ITEM_DATE.search(body)
    if not m:
        return None, 0
    raw = m.group(1).strip()
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None, 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt, len(RE_ITEM.findall(body))


# ── 告警 ────────────────────────────────────────────────────────────
def dingtalk(webhook, title, text):
    payload = json.dumps({
        "msgtype": "markdown",
        "markdown": {"title": title, "text": text},
    }).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=payload,
        headers={"Content-Type": "application/json;charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        obj = json.loads(raw)
    except ValueError:
        return False, raw[:200]
    ok = obj.get("errcode") == 0
    return ok, raw[:200]


def heartbeat(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            resp.read(256)
        return True, "ok"
    except Exception as exc:                          # noqa: BLE001
        return False, str(exc)


def check_local_emit(max_age_h):
    """生产线自产信号（本地事实，不需要网络）。

    为什么必须单列一条：站点的对外信号与它互为盲区 ——
      · push 凭据缺失 / CI 发布闸未开时，站点日期**根本不会推进**，
        对外信号恒为"停更"，无法区分「没产出」与「产出没发布」；
      · 反过来，本地产出正常但站点没更新，也只有对外信号能看出来。
    所以两个方向都要看，且告警体里要能一眼分清是哪种。

    判定：`rc != 0` 直接算故障（产出失败是硬故障，与"多久没产出"无关）；
    否则看距 `finished_at` 的时长是否超阈。
    """
    row = {"key": "emit", "label": "生产线产出", "url": EMIT_STATE_FILE,
           "max_age_h": max_age_h, "hours": None, "latest": None,
           "latest_local": None, "items": 0, "error": None, "stale": False,
           "rc": None, "committed": None, "pushed": None, "ahead": None}
    try:
        with open(EMIT_STATE_FILE, encoding="utf-8") as fh:
            d = json.load(fh)
    except OSError:
        row["error"] = "无记录（emit 从未运行过 → 生产线没跑起来）"
        row["stale"] = True
        return row
    except ValueError as exc:
        row["error"] = "状态文件损坏：%s" % exc
        row["stale"] = True
        return row

    row["rc"] = d.get("rc")
    row["committed"] = d.get("committed")
    row["pushed"] = d.get("pushed")
    row["ahead"] = d.get("commits_ahead_of_origin")

    fin = d.get("finished_at") or ""
    try:
        dt = datetime.fromisoformat(fin)
        row["hours"] = round((datetime.now(dt.tzinfo) - dt).total_seconds() / 3600.0, 2)
        row["latest"] = dt.isoformat()
        row["latest_local"] = dt.astimezone().strftime("%m-%d %H:%M")
    except ValueError:
        row["error"] = "finished_at 不可解析：%r" % fin

    tail = "%s rc=%s" % (d.get("kind") or "?", row["rc"])
    if row["committed"] and not row["pushed"]:
        # 提交在本地 = 发布链断了。这不是"停更"，是"产出了但出不去"，
        # 必须与停更区分开，否则排查会走错方向。
        tail += "，已提交未推送(ahead=%s)" % row["ahead"]

    if row["rc"] not in (0, None):
        row["stale"] = True
        row["error"] = "上一次运行失败 rc=%s" % row["rc"]
    elif row["error"]:
        row["stale"] = True
    elif row["hours"] is not None and row["hours"] >= max_age_h:
        row["stale"] = True

    row["latest_local"] = "%s %s" % (row["latest_local"] or "?", tail)
    if row["error"]:
        row["latest_local"] += " ← %s" % row["error"]
    return row


def build_alert(site_result, stale):
    now_local = datetime.now().astimezone()
    lines = [
        "## neican.ai 产出异常告警",
        "",
        "**检测时间**：%s" % now_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "",
        "对外频道（线上站点）与本地频道（生产线自产）**互为盲区**，",
        "两者不一致时按下面第 1–2 步定位：",
        "",
        "| 频道 | 最新产出 | 距今 | 阈值 |",
        "|---|---|---|---|",
    ]
    for c in site_result:
        age = "不可达" if c["hours"] is None else ("%.1f h" % c["hours"])
        mark = " **← 超阈**" if c["stale"] else ""
        lines.append("| %s | %s | %s | %dh |" % (
            c["label"],
            c.get("latest_local") or c.get("error") or "?",
            age, c["max_age_h"],
        ))
        if mark:
            lines[-1] = lines[-1][:-1] + mark
    lines += [
        "",
        "**排查顺序**（先分清是产出问题还是发布问题）",
        "1. 本地是否产出成功：`state/emit-last.json` 的 `rc` 与 `finished_at`"
        "（`rc≠0` = 产出失败；`rc=0` 但「已提交未推送」= 发布链断了）",
        "2. 已提交未推送的提交数：`git rev-list --count origin/main..HEAD`",
        "3. Vercel 部署状态（提交上的 Vercel commit status；CI 的发布闸 `DEPLOY_TARGET` 是否已配）",
        "4. 上游信源是否整体不可达（`logs/pipeline.log` 的 `sources_failed`）",
        "5. 域名与 DNS",
        "",
        "_由 NAS `newsroom/run/watchdog.py` 自动维护（心跳倒挂）。_",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="neican.ai 站点新鲜度看门狗")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结果（供机器消费）")
    ap.add_argument("--threshold", type=float, default=None,
                    help="全局覆盖阈值（小时）——用于验收测试")
    ap.add_argument("--force-alert", action="store_true",
                    help="即使未配置 webhook 也打印将要发送的告警体")
    ap.add_argument("--dry-run", action="store_true", help="只检测，不发任何网络告警")
    args = ap.parse_args()

    conf = load_conf()
    webhook = conf.get("DINGTALK_WEBHOOK", "").strip()
    hb_url = conf.get("HEARTBEAT_URL", "").strip()

    override = args.threshold
    if override is None and conf.get("STALE_HOURS_OVERRIDE"):
        try:
            override = float(conf["STALE_HOURS_OVERRIDE"])
        except ValueError:
            override = None

    now = datetime.now(timezone.utc)
    results = []
    for ch in CHANNELS:
        url = SITE + ch["path"]
        body, err = fetch_head(url, ch["read_bytes"])
        max_age = override if override is not None else ch["max_age_h"]
        row = {"key": ch["key"], "label": ch["label"], "url": url,
               "max_age_h": max_age, "hours": None, "latest": None,
               "latest_local": None, "items": 0, "error": err, "stale": False}
        if body is None:
            # 不可达：本身就是要报的故障（站点/域名层）
            row["stale"] = True
        else:
            dt, items = parse_latest(body)
            row["items"] = items
            if dt is None:
                row["error"] = "feed 可访问但解析不到 pubDate"
                row["stale"] = True
            else:
                hours = (now - dt).total_seconds() / 3600.0
                row["hours"] = round(hours, 2)
                row["latest"] = dt.isoformat()
                row["latest_local"] = dt.astimezone().strftime("%m-%d %H:%M")
                row["stale"] = hours >= max_age
        results.append(row)
        log("%-11s latest=%s age=%s h thr=%sh %s" % (
            ch["label"], row["latest_local"] or "-",
            "N/A" if row["hours"] is None else "%.1f" % row["hours"],
            max_age, "STALE" if row["stale"] else "ok"))

    # ── 生产线自产信号（本地事实）──────────────────────────────────
    # 放在对外信号之后：先给出"站点怎么了"，再给出"本地到底产出了没有"。
    # 两者不一致时，答案自然浮现（例：站点停更 + 本地 rc=0 未推送 = 发布链断了）。
    row = check_local_emit(override if override is not None else EMIT_MAX_AGE_H)
    results.append(row)
    log("%-11s latest=%s age=%s h thr=%sh %s%s" % (
        row["label"], row["latest_local"] or "-",
        "N/A" if row["hours"] is None else "%.1f" % row["hours"],
        row["max_age_h"], "STALE" if row["stale"] else "ok",
        "" if not row["error"] else "  ← %s" % row["error"]))

    stale_any = any(r["stale"] for r in results)
    # 只统计对外频道：本地信号不可达不算"网络层全挂"，否则 exit code 会撒谎
    unreachable_all = all(r["error"] for r in results if r["key"] != "emit")

    # ── 决定是否发告警（幂等）──────────────────────────────────────
    state = load_state()
    now_ts = int(time.time())
    alerted = False
    suppressed = []
    to_alert = []
    for r in results:
        if not r["stale"]:
            state.pop(r["key"], None)                # 恢复即清除，下次断开立刻响
            continue
        last = state.get(r["key"], {}).get("last_alert_ts", 0)
        if now_ts - last >= REALERT_AFTER_H * 3600:
            to_alert.append(r)
        else:
            suppressed.append(r["key"])

    if stale_any and to_alert and not args.dry_run:
        text = build_alert(results, to_alert)
        if webhook:
            try:
                ok, detail = dingtalk(webhook, "neican.ai 停更告警", text)
                log("钉钉告警发送: %s (%s)" % ("成功" if ok else "失败", detail))
                alerted = ok
            except Exception as exc:                  # noqa: BLE001
                log("钉钉告警异常: %s" % exc, level="ERROR")
        elif args.force_alert:
            log("未配置 DINGTALK_WEBHOOK —— 以下为将发送的内容：", level="WARN")
            print(text, flush=True)
        else:
            log("检出停更，但未配置 DINGTALK_WEBHOOK → 仅记录（阶段 2.3 待接入）", level="WARN")
        for r in to_alert:
            state.setdefault(r["key"], {})["last_alert_ts"] = now_ts
            state[r["key"]]["last_hours"] = r["hours"]
    elif suppressed:
        log("停更持续中，告警已抑制（%s），未到 %dh 重报间隔" % (",".join(suppressed), REALERT_AFTER_H))

    state["_last_run"] = {"ts": now_ts, "iso": datetime.now().astimezone().isoformat(),
                          "stale": stale_any, "unreachable_all": unreachable_all}
    save_state(state)

    # ── 反向心跳：只有一切新鲜才上报（缺席即告警）─────────────────
    if hb_url and not stale_any and not args.dry_run:
        ok, detail = heartbeat(hb_url)
        log("外部心跳上报: %s (%s)" % ("成功" if ok else "失败", detail))

    if args.json:
        print(json.dumps({"stale": stale_any, "alerted": alerted,
                          "channels": results,
                          "generated_at": datetime.now().astimezone().isoformat()},
                         ensure_ascii=False, indent=2))
    else:
        log("结果：%s" % ("检出停更" if stale_any else "全部新鲜"))

    if unreachable_all:
        return 2
    return 1 if stale_any else 0


if __name__ == "__main__":
    sys.exit(main())
