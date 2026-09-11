# -*- coding: utf-8 -*-
"""L1 归并层：Source → Event。

**这是整个设计里最重要的一个建模决定**（设计文档 §2）。
原始系统的病根不在提示词、不在封装形式，而在**缺少 Event 这个实体**：
它把"一条 RSS 条目"当作"一篇文章"的单位。同一件事被 5 家媒体报道，
就产生 5 篇结构雷同的文章 —— 这既是额度烧穿的直接原因，
也是"规模化生成"政策风险最典型的样子（只有 guid 判重，无语义去重）。

Event 一次解决三个问题：
  1. 去重：从字符串匹配升级为"归属同一事件"
  2. 日报的 5 条天然来自 5 个不同 Event（保证"5 条是 5 件事"）
  3. 内链是免费的：同一 Event 的 Source 互为引用

用法：
    python3 -m src.cluster
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


def _same_event(a: dict, b: dict, cfg: dict) -> tuple[bool, str]:
    """判定两条 Source 是否属于同一事件。返回 (是否, 依据)。"""
    # URL 判等必须走归一化：尾斜杠 / www / 跟踪参数的差异会让同一条新闻分裂成两个 Event
    # （实测：RSSHub 的 OpenAI 条目带尾斜杠，AIHOT 的不带 → 早报出现中英重复两条）
    if cfg.get("url_exact_always_merge", True):
        na, nb = T.norm_url(a.get("url", "")), T.norm_url(b.get("url", ""))
        if na and na == nb:
            return True, "url_exact"

    ta, tb = a.get("norm_title", ""), b.get("norm_title", "")
    if not ta or not tb:
        return False, ""
    # 长度差过大直接跳过，省掉大量无意义比较
    if len(ta) < 6 or len(tb) < 6:
        return False, ""
    if max(len(ta), len(tb)) / max(1, min(len(ta), len(tb))) > 2.2:
        return False, ""

    j = T.jaccard(ta, tb)
    if j >= float(cfg.get("title_jaccard", 0.55)):
        return True, f"jaccard={j:.2f}"
    r = T.ratio(ta, tb)
    if r >= float(cfg.get("title_similarity", 0.72)):
        return True, f"ratio={r:.2f}"
    return False, ""


def _rep_source(sources: list[dict], cfg: dict) -> dict:
    """代表信源 = **显示标题与署名必须来自同一条来源**。

    为什么两者必须绑定：标题和署名若来自不同来源，读者会以为中文标题是
    一手源写的 —— 那是把"转引"伪装成"官方表述"。所以标题与署名一起选。
    （署名由 digest 的 `_top_source` 取"层级最高"，而这里选出的代表可能不是它，
    所以事件里额外记下 `rep_fingerprint`，让产物层能按同一条记录取标题与摘要。）

    排序键（第一项可在 scoring.yaml 的 `cluster.prefer_lang` 关掉）：
      1. 语言优先 —— 面向中文读者，中文条目的标题优先，让英文一手源的中文线索能顶上来
         （这正是接入 AIHOT 要买的东西：它给英文一手源提供了中文标题）
      2. 信源层级 —— 一手源 > 专业媒体 > 聚合
      3. 标题长度 —— 长标题通常信息量更大
    """
    prefer = (cfg.get("prefer_lang") or "").strip()

    def key(s):
        lang_rank = 1 if (prefer and s.get("lang") == prefer) else 0
        return (lang_rank, _TIER_RANK.get(s.get("tier", "media"), 2), len(s.get("title", "")))

    return sorted(sources, key=key, reverse=True)[0] if sources else {}


def build_events(records: list[dict], cfg: dict, day: str) -> list[dict]:
    clusters: list[dict] = []

    # 高价值源先入簇：让一手源的标题成为代表标题
    ordered = sorted(records, key=lambda r: (-_TIER_RANK.get(r.get("tier", "media"), 2),
                                             -(r.get("weight") or 0)))
    for rec in ordered:
        placed = False
        for cl in clusters:
            for member in cl["sources"]:
                same, why = _same_event(rec, member, cfg)
                if same:
                    cl["sources"].append(rec)
                    cl["merge_reasons"].append(why)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            clusters.append({"sources": [rec], "merge_reasons": ["seed"]})

    events: list[dict] = []
    for i, cl in enumerate(clusters, start=1):
        srcs = cl["sources"]
        pubs = [C.parse_iso(s.get("published_at", "")) for s in srcs]
        pubs = [p for p in pubs if p]
        rep = _rep_source(srcs, cfg)
        title = rep.get("title", "")
        tiers = [s.get("tier", "media") for s in srcs]
        primary = max(tiers, key=lambda t: _TIER_RANK.get(t, 1))
        events.append({
            "event_id": f"ev-{day.replace('-', '')}-{i:04d}",
            "day": day,
            "cluster_key": C.short_hash(T.norm_title(title), 20),
            "title": title,
            "norm_title": T.norm_title(title),
            "rep_fingerprint": rep.get("fingerprint", ""),   # 标题/摘要的取用依据
            "sources": srcs,
            "source_count": len(srcs),
            "distinct_sources": len({s["source_id"] for s in srcs}),
            "langs": sorted({s.get("lang", "en") for s in srcs}),
            "primary_tier": primary,
            "first_published": C.iso(min(pubs)) if pubs else "",
            "latest_published": C.iso(max(pubs)) if pubs else "",
            "merge_reasons": cl["merge_reasons"],
            "created_at": C.iso(C.bjnow()),
        })
    return events


def run(day: str | None = None) -> dict:
    scfg = C.load_config("scoring")
    ccfg = scfg.get("cluster", {})
    run_rec = C.Run("cluster")
    day = day or C.day_key()

    records = C.read_jsonl(C.RAW_DIR / day / "sources.jsonl")
    if not records:
        run_rec.error(f"无原始条目：{C.RAW_DIR / day / 'sources.jsonl'} —— 先跑 fetch")
        run_rec.finish(ok=False)
        return {"events": 0}

    events = build_events(records, ccfg, day)
    C.write_jsonl(C.STATE_DIR / f"events-{day}.jsonl", events)

    merged = sum(1 for e in events if e["source_count"] > 1)
    multi = [e for e in events if e["distinct_sources"] > 1]
    run_rec.set(sources=len(records), events=len(events), multi_source=merged,
                merged_away=len(records) - len(events), day=day)
    run_rec.finish()
    C.log(f"归并完成：{len(records)} 条 Source → {len(events)} 个 Event"
          f"（{merged} 个多源事件，压缩率 {(1 - len(events) / max(1, len(records))) * 100:.0f}%）")
    for e in multi[:8]:
        C.log(f"  · [{e['distinct_sources']}源] {T.clip(e['title'], 60)}")
    return {"events": len(events)}


def main() -> int:
    ap = argparse.ArgumentParser(description="L1 归并层")
    ap.add_argument("--day", default=None)
    a = ap.parse_args()
    run(a.day)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
