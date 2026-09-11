# -*- coding: utf-8 -*-
"""L1 排产层：加权排序 → 配额分流 → 落选留痕。

落选**全部写 `decisions/`**（含理由）——
因为"为什么没选它"和"为什么选了它"同样重要：
前者是改进评分权重的唯一燃料，后者是主编复核的依据。

三条产线的分流（设计文档 §10，风险分层）：
    早报  8–10 条聚合：标题 + 摘要 + 署名 + 原文链接，**零创作** → 政策风险最低
    日报  当日 5 个最强 Event + 主编综述 → 输入只有结构化摘要，强制综合而非复述
    洞察  深度解释稿 → T1 自动发 / T2 走主编确认

用法：
    python3 -m src.select
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


_TIER_RANK = {"first_party": 3, "media": 2, "aggregator": 1}


def _primary_source(event: dict) -> str:
    """事件的主源 = 层级最高、其次权重最高的那个信源。"""
    srcs = event.get("sources") or []
    if not srcs:
        return "?"
    best = sorted(srcs, key=lambda s: (-_TIER_RANK.get(s.get("tier", "media"), 2),
                                       -(s.get("weight") or 0)))[0]
    return best.get("source_id", "?")


def _take(pool: list[dict], n: int, taken_ids: set[str] | None = None) -> list[dict]:
    out = []
    for e in pool:
        if taken_ids is not None and e["event_id"] in taken_ids:
            continue
        out.append(e)
        if len(out) >= n:
            break
    return out


def _take_diverse(pool: list[dict], n: int, max_per_source: int,
                  taken_ids: set[str] | None = None) -> list[dict]:
    """配额 + **单源上限**。

    为什么需要：首跑实测早报 10 条里 7 条来自同一个 feed，日报也高度同源。
    单一源垄断会让"日报 5 条 = 5 件事"退化成"一个栏目的摘要"，
    而多源印证正是 Event 模型要买到的东西。这是编辑要求，不是性能优化。

    若因上限而凑不满 n，会做**第二轮放宽**（保底优先于多样性），
    并在返回值里体现实际来源数，使"今天为什么只有 6 条"可被文件回答。
    """
    from collections import Counter
    out: list[dict] = []
    seen: set[str] = set(taken_ids or ())
    per: Counter = Counter()

    for e in pool:
        if e["event_id"] in seen:
            continue
        sid = _primary_source(e)
        if per[sid] >= max_per_source:
            continue
        out.append(e)
        seen.add(e["event_id"])
        per[sid] += 1
        if len(out) >= n:
            return out

    # 第二轮：放宽单源上限，优先保证条数
    for e in pool:
        if e["event_id"] in seen:
            continue
        out.append(e)
        seen.add(e["event_id"])
        per[_primary_source(e)] += 1
        if len(out) >= n:
            break
    return out


def run(day: str | None = None) -> dict:
    scfg = C.load_config("scoring")
    thr = scfg["thresholds"]
    q = scfg["quota"]
    run_rec = C.Run("select")
    day = day or C.day_key()

    scored = C.read_jsonl(C.STATE_DIR / f"scored-{day}.jsonl")
    if not scored:
        run_rec.error(f"无评分文件：{C.STATE_DIR / f'scored-{day}.jsonl'} —— 先跑 score")
        run_rec.finish(ok=False)
        return {"plan": 0}

    scored.sort(key=lambda x: -x["total"])

    div = scfg.get("diversity", {})
    morning_pool = [e for e in scored if e["total"] >= thr["morning_min_total"]]
    daily_pool = [e for e in scored if e["total"] >= thr["daily_min_total"]]
    insight_pool = [e for e in scored if e["total"] >= thr["insight_min_total"]]

    m_n = min(q["morning"]["max"], max(q["morning"]["min"], q["morning"]["target"]))
    d_n = min(q["daily"]["max"], max(q["daily"]["min"], q["daily"]["target"]))
    i_n = int(q["insights"]["t1"]) + int(q["insights"]["t2"])

    morning = _take_diverse(morning_pool, m_n, int(div.get("morning_max_per_source", 3)))
    daily = _take_diverse(daily_pool, d_n, int(div.get("daily_max_per_source", 2)))
    insights = _take_diverse(insight_pool, i_n, int(div.get("insight_max_per_source", 1)))

    chosen = {e["event_id"] for e in morning} | {e["event_id"] for e in daily} | {e["event_id"] for e in insights}
    morning_sources = len({_primary_source(e) for e in morning})

    decisions = []
    for e in scored:
        if e["event_id"] in morning:
            verdict, reason = "morning", "总分过早报线"
        elif e["event_id"] in daily:
            verdict, reason = "daily", "总分过日报线"
        elif e["event_id"] in insights:
            verdict, reason = "insight", "总分过洞察线"
        else:
            verdict = "dropped"
            if e["total"] < thr["publish_min_total"]:
                reason = f"总分 {e['total']:.3f} 低于发布底线 {thr['publish_min_total']}"
            else:
                reason = "配额已满（低于当日入选者的最低总分）"
        decisions.append({
            "day": day, "event_id": e["event_id"], "rank": e.get("rank"),
            "total": e["total"], "score": e["score"], "verdict": verdict,
            "reason": reason, "reasons": e.get("reasons", {}),
            "title": e["title"], "source_count": e.get("source_count"),
            "primary_tier": e.get("primary_tier"),
            "entities": e.get("entities", []),
        })

    plan = {
        "day": day,
        "generated_at": C.iso(C.bjnow()),
        "counts": {"scored": len(scored), "morning": len(morning),
                   "daily": len(daily), "insights": len(insights),
                   "dropped": len(scored) - len(chosen)},
        "morning": [e["event_id"] for e in morning],
        "daily": [e["event_id"] for e in daily],
        "insights": [e["event_id"] for e in insights],
        "by_id": {e["event_id"]: e for e in scored},
    }
    # by_id 只保留入选者，避免 plan 文件膨胀
    plan["by_id"] = {k: v for k, v in plan["by_id"].items() if k in chosen}

    C.write_json_atomic(C.STATE_DIR / f"plan-{day}.json", plan)
    C.write_jsonl(C.STATE_DIR / "decisions" / f"{day}.jsonl", decisions)

    run_rec.set(**plan["counts"], day=day,
                morning_sources=morning_sources,
                daily_sources=len({_primary_source(e) for e in daily}),
                morning_min=round(min([e["total"] for e in morning]), 3) if morning else None,
                daily_min=round(min([e["total"] for e in daily]), 3) if daily else None)
    min_src = int(div.get("min_distinct_sources", 0) or 0)
    if min_src and morning_sources < min_src:
        run_rec.error(f"早报信源覆盖不足：{morning_sources} 家 < 要求 {min_src} 家"
                      f"（当日候选池只有这些源过线）")
    run_rec.finish()
    C.log(f"排产完成：早报 {len(morning)}（{morning_sources} 个源）/ 日报 {len(daily)} "
          f"/ 洞察 {len(insights)} / 落选 {plan['counts']['dropped']}（全部留痕）")
    C.log("  早报入选：" + " | ".join(T.clip(e["title"], 26) for e in morning[:5]))
    C.log("  日报入选：" + " | ".join(T.clip(e["title"], 26) for e in daily))
    return {"plan": plan["counts"]}


def main() -> int:
    ap = argparse.ArgumentParser(description="L1 排产层")
    ap.add_argument("--day", default=None)
    a = ap.parse_args()
    run(a.day)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
