# -*- coding: utf-8 -*-
"""早报 / 日报编排（模板轨）。

**模板轨的价值不是"临时方案"，而是"分级降级"的落地**（设计文档 §14）：
LLM 全挂时，早报仍必须能出 —— 标题 + 来源 + 链接，无 LLM 也是合法产品。
旧系统单一供应商断供就导致全站冻结 37 天，就是因为没有这条轨道。

产物契约（与现存 280 篇早报 / 321 篇日报对齐）：
    content/morningnews/<YYYY-MM-DD>.md    main_topics: ["AI内参极速早报"]
    content/newspaper/<YYYY-MM-DD>.md      main_topics: ["AI内参日报"]

用法：
    python3 -m src.digest --kind morning
    python3 -m src.digest --kind daily
    python3 -m src.digest --kind morning --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lib import common as C          # type: ignore
    from lib import textutil as T        # type: ignore
else:
    from .lib import common as C
    from .lib import textutil as T

DEFAULT_IMAGE = "/images/ai-report-default.png"

CHANNEL = {
    "morning": {"dir": "morningnews", "topic": "AI内参极速早报",
                "title_fmt": "AI早报 {y}年{m:02d}月{d:02d}日", "hour": 7, "minute": 30},
    "daily":   {"dir": "newspaper", "topic": "AI内参日报",
                "title_fmt": "AI日报 {y}年{m:02d}月{d:02d}日", "hour": 19, "minute": 0},
}


def _yaml_list(items: list[str], indent: str = "  ") -> str:
    if not items:
        return " []"
    return "\n" + "\n".join(f'{indent}- "{i}"' for i in items)


def _yaml_str(s: str) -> str:
    s = (s or "").replace('"', '\\"').replace("\n", " ")
    return f'"{s}"'


def _derive_tags(events: list[dict], limit: int = 6) -> list[str]:
    """标签 = 事件里最高频的实体（有则用），不足则回退到主话题。"""
    from collections import Counter
    cnt: Counter = Counter()
    for e in events:
        for ent in e.get("entities") or []:
            cnt[ent] += 1
    tags = [k for k, _ in cnt.most_common(limit)]
    if len(tags) < 3:
        for e in events:
            for s in e.get("sources", []):
                if s.get("source_name"):
                    tags.append(s["source_name"])
                if len(tags) >= limit:
                    break
    out, seen = [], set()
    for t in tags:
        t = T.clip(t.strip(), 18)
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out[:limit]


def _summary_of(events: list[dict], kind: str) -> str:
    """模板轨摘要 = 机械聚合（**不是创作**）：把最强的几条压成一个短句。

    首跑实测踩到的坑：直接取标题前 28 字会把"OpenAI这是拿千禧年难题当Benchmark刷啊。…"
    这类口语化标题和截断省略号带进 frontmatter。
    这里做三件事：去渠道尾巴、去掉标点结尾、长度收敛。
    """
    parts = []
    for e in events[:3]:
        t = T.display_title(e.get("title", ""))
        t = t.split("：")[0].split(":")[0].strip()
        t = t.rstrip("。，、；：！？….,;:!? ")
        if len(t) > 26:
            # 先切、后收尾。顺序反过来的话，切片会把刚删掉的标点又切回来
            # ——实测产出过 "AMD 发布锐龙AI Max PRO 400 系列，。"，多一个逗号。
            t = t[:26].rstrip("。，、；：！？….,;:!? ")
        if t:
            parts.append(t)
    if not parts:
        return ""
    label = "今日要点" if kind == "daily" else "过去 24 小时"
    return f"{label}：{'；'.join(parts)}。"


def _source_line(event: dict) -> str:
    """署名 + 原文链接。取信源层级最高的一条。"""
    rank = {"first_party": 3, "media": 2, "aggregator": 1}
    srcs = sorted(event.get("sources", []), key=lambda s: -rank.get(s.get("tier", "media"), 2))
    if not srcs:
        return ""
    s = srcs[0]
    name = s.get("source_name") or s.get("source_id") or "来源"
    url = s.get("url") or ""
    extra = ""
    if event.get("distinct_sources", 0) >= 2:
        extra = f"，另有 {event['distinct_sources'] - 1} 家报道"
    return f"（[{name}]({url}){extra}）" if url else f"（{name}{extra}）"


def _best_summary(event: dict, title: str, limit: int) -> str:
    """取"层级最高且清洗后最长"的摘要。

    为什么要挑而不是直接取第一条：实测多数 feed 的 description 是正文开头，
    不同源的片段长短差别很大；而早报的契约是"零创作"，只能从原文片段里**删**，
    所以清洗质量直接决定产物质量（首跑实测：不清洗会带进"文｜王欣逸 编辑｜张雨忻"）。
    """
    rank = {"first_party": 3, "media": 2, "aggregator": 1}
    best = ""
    for s in sorted(event.get("sources", []),
                    key=lambda x: (-rank.get(x.get("tier", "media"), 2), len(x.get("summary") or ""))):
        cand = T.clean_summary(s.get("summary") or "", title, limit)
        if len(cand) > len(best):
            best = cand
    return best


def render_morning(events: list[dict], day: str, dt_iso: str) -> str:
    y, m, d = (int(x) for x in day.split("-"))
    cfg = CHANNEL["morning"]
    fm = [
        "---",
        f"title: {_yaml_str(cfg['title_fmt'].format(y=y, m=m, d=d))}",
        f"date: {dt_iso}",
        "draft: false",
        f'featured_image: "{DEFAULT_IMAGE}"',
        f"summary: {_yaml_str(_summary_of(events, 'morning'))}",
        f"tags:{_yaml_list(_derive_tags(events))}",
        f"main_topics:{_yaml_list([cfg['topic']])}",
        f"selected_article_count: {len(events)}",
        "---",
    ]
    body = [f"今天是{y}年{m:02d}月{d:02d}日。以下 {len(events)} 条为过去 24 小时值得关注的 AI 动态，"
            f"每条附原始来源，不做二次加工。", ""]
    for i, e in enumerate(events, 1):
        title = T.display_title(e.get("title", ""))
        summary = _best_summary(e, title, 110)
        line = f"{i}.  **{title}**"
        if summary:
            line += f"，{summary}"
        if not line.rstrip().endswith(("。", "！", "？", ".")):
            line += "。"
        line += _source_line(e)
        body.append(line)
    body += ["", "---", "",
             f"*本期由 neican.ai 自动编排（模板轨，无人工创作）。共聚合 {len(events)} 个事件，"
             f"来源 {sum(e.get('distinct_sources', 1) for e in events)} 个信源条目。*"]
    return "\n".join(fm) + "\n\n" + "\n".join(body) + "\n"


def render_daily(events: list[dict], day: str, dt_iso: str) -> str:
    y, m, d = (int(x) for x in day.split("-"))
    cfg = CHANNEL["daily"]
    fm = [
        "---",
        f"title: {_yaml_str(cfg['title_fmt'].format(y=y, m=m, d=d))}",
        f"date: {dt_iso}",
        "draft: false",
        f'featured_image: "{DEFAULT_IMAGE}"',
        f"summary: {_yaml_str(_summary_of(events, 'daily'))}",
        f"tags:{_yaml_list(_derive_tags(events))}",
        f"main_topics:{_yaml_list([cfg['topic']])}",
        f"selected_article_count: {len(events)}",
        "---",
    ]
    body = [f"**今天是{y}年{m:02d}月{d:02d}日。** 以下是当日最重要的 {len(events)} 件事。", "",
            "### 今日速览", ""]
    for e in events:
        title = T.display_title(e.get("title", ""))
        summary = _best_summary(e, title, 160)
        item = f"* **{title}**"
        if summary:
            item += f"：{summary}"
        item += _source_line(e)
        body.append(item)
    body += ["", "### 信源分布", ""]
    from collections import Counter
    tier_cn = {"first_party": "一手源", "media": "专业媒体", "aggregator": "聚合源"}
    cnt = Counter(e.get("primary_tier", "media") for e in events)
    body.append("　·　".join(f"{tier_cn.get(k, k)} {v} 条" for k, v in cnt.most_common()))
    body += ["", "---", "",
             f"*本期由 neican.ai 自动编排（模板轨）。{len(events)} 条均为不同事件"
             f"（Event 归并已保证去重）。主编综述需生成层启用后补入。*"]
    return "\n".join(fm) + "\n\n" + "\n".join(body) + "\n"


def run(kind: str, day: str | None = None, dry_run: bool = False, force: bool = False) -> dict:
    cfg = CHANNEL[kind]
    run_rec = C.Run(f"digest-{kind}")
    day = day or C.day_key()

    plan_path = C.STATE_DIR / f"plan-{day}.json"
    plan = C.read_json(plan_path)
    if not plan:
        run_rec.error(f"无排产文件：{plan_path} —— 先跑 select")
        run_rec.finish(ok=False)
        return {"written": None}

    ids = plan.get(kind) or []
    by_id = plan.get("by_id", {})
    events = [by_id[i] for i in ids if i in by_id]
    if not events:
        run_rec.error(f"排产中 {kind} 为空（阈值过高或当日无合格事件）")
        run_rec.finish(ok=False)
        return {"written": None}

    y, m, d = (int(x) for x in day.split("-"))
    now = C.bjnow()
    nominal = f"{cfg['hour']:02d}:{cfg['minute']:02d}"
    # 名义时点 vs 实际时点：早报 07:30 / 日报 19:00 是硬承诺，
    # 但补跑（手动触发、失败重试）时若还写名义时间，产物就在说谎。
    # 判定规则：两者相差在 3 小时内视为"准点"，否则用实际时间并告警。
    within = abs((now.hour * 60 + now.minute) - (cfg["hour"] * 60 + cfg["minute"])) <= 180
    if within:
        dt_iso = f"{day}T{nominal}:00+08:00"
    else:
        dt_iso = C.iso(now)
        C.log(f"补跑：当前 {now.strftime('%H:%M')} 距名义时点 {nominal} 超过 3 小时，"
              f"date 记为实际时间 {dt_iso}（不让产物说谎）", "WARN")
    text = render_morning(events, day, dt_iso) if kind == "morning" else render_daily(events, day, dt_iso)

    out_dir = C.CONTENT_DIR / cfg["dir"]
    out_path = out_dir / f"{day}.md"

    if out_path.exists() and not force:
        run_rec.error(f"目标已存在，拒绝覆盖（加 --force 才覆盖）：{out_path}")
        run_rec.finish(ok=False)
        return {"written": None}

    if dry_run:
        C.log(f"[dry-run] 将写入 {out_path}（{len(text)} 字节，{len(events)} 条）")
        print("\n" + "─" * 70 + "\n" + text)
        run_rec.set(dry_run=True, events=len(events), day=day)
        run_rec.finish()
        return {"written": None}

    C.write_text_atomic(out_path, text)
    try:
        rel = str(out_path.relative_to(C.REPO))
    except ValueError:
        rel = str(out_path)          # CONTENT_DIR 被覆盖时（联调），退化为绝对路径
    run_rec.set(events=len(events), bytes=len(text.encode("utf-8")),
                path=rel, day=day)
    run_rec.finish()
    C.log(f"{kind} 已生成：{rel}（{len(events)} 条）")
    return {"written": str(out_path)}


def main() -> int:
    ap = argparse.ArgumentParser(description="早报/日报编排（模板轨）")
    ap.add_argument("--kind", choices=["morning", "daily"], required=True)
    ap.add_argument("--day", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    r = run(a.kind, a.day, a.dry_run, a.force)
    return 0 if r.get("written") or a.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
