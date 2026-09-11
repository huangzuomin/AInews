# -*- coding: utf-8 -*-
"""L1 评分层：五维子分 + 加权总分。

**模型只出子分，加权在代码里**（设计文档 §6.3 规则 3）——
省 token，且让权重可被人工调参（这是学习闭环的落点）。

v1 为**纯规则**实现：确定、可重放、零成本。
v2 接入 LLM 后，模型只覆盖 `value`，本模块的规则值保留为 fallback 与交叉校验基线。

五维：novelty / impact / clarity / depth / **evidence**
`evidence`（证据可得性）权重 0.20，是相对原始设计新增的一维：
原始设计没有"能不能核到事实"这一维，这正是 9,383 篇只能靠聚合摘要成文的结构性原因。
有了它，"好看但核不动"的题会在选题阶段被淘汰，而不是在写作阶段变成编造。

用法：
    python3 -m src.score
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lib import common as C          # type: ignore
    from lib import textutil as T        # type: ignore
else:
    from .lib import common as C
    from .lib import textutil as T


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def load_entities() -> list[dict]:
    """读取实体注册表（data/entities.yaml），用于 impact 维。"""
    path = C.REPO / "data" / "entities.yaml"
    if not path.exists():
        return []
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return []
    raw = []
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "canonical" in v[0]:
                raw = v
                break
    out = []
    for e in raw:
        if not isinstance(e, dict) or not e.get("canonical"):
            continue
        names = [str(e["canonical"])] + [str(a) for a in (e.get("aliases") or [])]
        out.append({
            "canonical": str(e["canonical"]),
            "type": str(e.get("type", "other")),
            "patterns": [re.compile(re.escape(n), re.I) for n in names if len(str(n)) >= 2],
        })
    return out


def _entity_hits(text: str, entities: list[dict]) -> list[dict]:
    hits = []
    for e in entities:
        for p in e["patterns"]:
            if p.search(text):
                hits.append({"canonical": e["canonical"], "type": e["type"]})
                break
    return hits


def _prior_similarity(event: dict, prior_events: list[dict], ccfg: dict) -> int:
    """统计回看窗口内有多少个历史事件与当前事件"是同一件事"。"""
    nt = event.get("norm_title", "")
    if not nt:
        return 0
    n = 0
    for pe in prior_events:
        pt = pe.get("norm_title", "")
        if not pt:
            continue
        if max(len(nt), len(pt)) / max(1, min(len(nt), len(pt))) > 2.2:
            continue
        if (T.jaccard(nt, pt) >= float(ccfg.get("title_jaccard", 0.55))
                or T.ratio(nt, pt) >= float(ccfg.get("title_similarity", 0.72))):
            n += 1
    return n


def _aihot_prior(event: dict, ap: dict) -> dict | None:
    """取事件里最强的 AIHOT 线索分并归一。事件里没有 AIHOT 来源时返回 None（不参与融合）。

    为什么取"最强"而不是"平均"：同一件事可能被 AIHOT 报了不止一次（不同 origin），
    只要有一次被认定为高价值，这件事就值得看 —— 平均会把它稀释掉。

    归一为什么不用 score/100：AIHOT 的实际分数量程约 40–85，
    直接除 100 会把"该窗口最高分 81"压成 0.81，先验几乎不起作用。
    用 floor/ceil 做线性拉伸，先验才有分辨力。端点可在 config 里调，不写死在代码里。
    """
    best = None
    for s in event.get("sources", []):
        a = s.get("aihot") or {}
        sc = a.get("score")
        if sc is None:
            continue
        if best is None or float(sc) > float(best.get("score", -1)):
            best = {"score": sc, "category": a.get("category", ""),
                    "selected": bool(a.get("selected"))}
    if best is None:
        return None
    lo = float(ap.get("score_floor", 0))
    hi = float(ap.get("score_max", 100))
    norm = _clamp((float(best["score"]) - lo) / (hi - lo)) if hi > lo else 0.0
    if best.get("selected"):
        norm = _clamp(norm + float(ap.get("selected_bonus", 0.0)))
    return {"norm": round(norm, 4), "score": best["score"],
            "category": best["category"], "selected": best["selected"]}


def score_event(event: dict, scfg: dict, entities: list[dict],
                prior_events: list[dict], now) -> dict:
    w = scfg["weights"]
    cfg_n, cfg_i, cfg_c, cfg_d, cfg_e = (
        scfg["novelty"], scfg["impact"], scfg["clarity"], scfg["depth"], scfg["evidence"])
    ccfg = scfg.get("cluster", {})
    reasons: dict[str, str] = {}

    title = event.get("title", "")
    blob = " ".join([title] + [s.get("summary", "") for s in event.get("sources", [])])
    nt = event.get("norm_title", "")

    # ── novelty ──────────────────────────────────────────────
    priors = _prior_similarity(event, prior_events, ccfg)
    nov = cfg_n["first_seen_score"] - cfg_n["repeat_decay"] * priors
    pub = C.parse_iso(event.get("latest_published") or event.get("first_published") or "")
    if pub:
        age = C.hours_between(now, pub)
        if age <= cfg_n["recency_hours_full"]:
            rec = 1.0
        elif age >= cfg_n["recency_hours_zero"]:
            rec = 0.4
        else:
            span = cfg_n["recency_hours_zero"] - cfg_n["recency_hours_full"]
            rec = 1.0 - 0.6 * ((age - cfg_n["recency_hours_full"]) / span)
        nov *= rec
        reasons["novelty"] = f"回看窗口内相似事件 {priors} 个；发布距今 {age:.1f}h"
    else:
        reasons["novelty"] = f"回看窗口内相似事件 {priors} 个；无发布时间"
    nov = _clamp(nov, cfg_n["min_score"], 1.0)

    # ── impact ───────────────────────────────────────────────
    best_w = max([float(s.get("weight") or 0.5) for s in event.get("sources", [])] or [0.5])
    hits = _entity_hits(blob, entities)
    tier_w = {"first_party": 1.0, "product": 0.8, "person": 0.6}.get
    ent_score = _clamp(sum(tier_w(h["type"], 0.4) for h in hits) /
                       max(2.0, len(hits) + 1.0), 0.0, 1.0) if hits else 0.0
    signals = cfg_i["signals"]
    sig = 1.0 if any(re.search(p, blob, re.I) for p in signals) else 0.0
    imp = (cfg_i["source_weight_share"] * best_w
           + cfg_i["entity_share"] * ent_score
           + cfg_i["signal_share"] * sig)

    # 外部先验融合（AIHOT 线索分）。只对带分数的条目生效 —— 见 scoring.yaml 里的长注释：
    # 用"混合"而不是"相加"，是为了不给缺测的条目凭空扣分。
    ap = scfg.get("aihot_prior") or {}
    ext = _aihot_prior(event, ap) if ap.get("enabled", False) else None
    if ext is not None:
        w_ext = _clamp(float(ap.get("weight", 0.0)), 0.0, 1.0)
        rule_imp = imp
        imp = (1.0 - w_ext) * rule_imp + w_ext * ext["norm"]
    else:
        rule_imp = imp

    reasons["impact"] = (f"最高信源权重 {best_w:.2f}；命中实体 {len(hits)} 个"
                         f"（{', '.join(h['canonical'] for h in hits[:4]) or '无'}）；"
                         f"影响面信号 {'有' if sig else '无'}"
                         + (f"；AIHOT 线索分 {ext['score']}（{ext['category'] or '—'}）"
                            f"→ 规则值 {rule_imp:.2f} 混合为 {imp:.2f}"
                            if ext is not None else ""))

    # ── clarity ──────────────────────────────────────────────
    cla = 0.6
    L = len(title)
    if cfg_c["ideal_min"] <= L <= cfg_c["ideal_max"]:
        cla += 0.25
    elif L > cfg_c["ideal_max"]:
        cla -= cfg_c["long_penalty"]
    notes = [f"标题 {L} 字"]
    if any(re.search(p, title, re.I) for p in cfg_c["clickbait_patterns"]):
        cla -= cfg_c["clickbait_penalty"]
        notes.append("命中标题党模式")
    tab = [p for p in cfg_c.get("tabloid_patterns", []) if re.search(p, title, re.I)]
    if tab:
        cla -= float(cfg_c.get("tabloid_penalty", 0.0))
        notes.append("自媒体调性")
    if T.has_number(title):
        cla += cfg_c["number_bonus"]
        notes.append("含具体数字")
    if re.search(r"[「『“\"]", title):
        cla += cfg_c["quote_bonus"]
        notes.append("含引语")
    cla = _clamp(cla)
    reasons["clarity"] = "；".join(notes)

    # ── depth ────────────────────────────────────────────────
    sl = max([len(s.get("summary", "")) for s in event.get("sources", [])] or [0])
    if sl <= cfg_d["summary_len_floor"]:
        dep = 0.2
    elif sl >= cfg_d["summary_len_good"]:
        dep = 1.0
    else:
        dep = 0.2 + 0.8 * ((sl - cfg_d["summary_len_floor"])
                           / (cfg_d["summary_len_good"] - cfg_d["summary_len_floor"]))
    if T.has_number(blob):
        dep += cfg_d["number_bonus"]
    if any(s.get("url") for s in event.get("sources", [])):
        dep += cfg_d["link_bonus"]
    dep = _clamp(dep)
    reasons["depth"] = f"最长摘要 {sl} 字；{'含数字' if T.has_number(blob) else '无数字'}"

    # ── evidence ─────────────────────────────────────────────
    ev = cfg_e["tier_base"].get(event.get("primary_tier", "media"), 0.5)
    if any(s.get("url") for s in event.get("sources", [])):
        ev += cfg_e["has_url_bonus"]
    if event.get("distinct_sources", 0) >= cfg_e["corroboration_min_sources"]:
        ev += cfg_e["corroboration_bonus"]
    ev = _clamp(ev)
    reasons["evidence"] = (f"主源层级 {event.get('primary_tier')}；"
                           f"独立信源 {event.get('distinct_sources', 0)} 个（>={cfg_e['corroboration_min_sources']} 则加分）")

    subs = {"novelty": nov, "impact": imp, "clarity": cla, "depth": dep, "evidence": ev}
    total = sum(w[k] * subs[k] for k in w)
    return {
        "score": {k: round(v, 4) for k, v in subs.items()},
        "total": round(total, 4),
        "reasons": reasons,
        "entities": [h["canonical"] for h in hits],
        # 留痕：外部先验与"没有它时是多少"要能分离开，否则日后调权重无从归因
        "aihot_prior": ext,
        "impact_rule": round(rule_imp, 4),
    }


def _prior_events(days_back: int, exclude_day: str) -> list[dict]:
    out: list[dict] = []
    for p in sorted(C.STATE_DIR.glob("events-*.jsonl")):
        day = p.stem.replace("events-", "")
        if day == exclude_day:
            continue
        out.extend(C.read_jsonl(p))
    # 按窗口裁掉过老的
    return out[-3000:]


def run(day: str | None = None) -> dict:
    scfg = C.load_config("scoring")
    run_rec = C.Run("score")
    day = day or C.day_key()
    now = C.bjnow()

    # 只对通过分类闸的事件评分（首跑实测：不设闸会让《八仙！》票房进早报）
    events = (C.read_jsonl(C.STATE_DIR / f"classified-{day}.jsonl")
              or C.read_jsonl(C.STATE_DIR / f"events-{day}.jsonl"))
    if not events:
        run_rec.error(f"无已分类事件：{C.STATE_DIR / f'classified-{day}.jsonl'} —— 先跑 classify")
        run_rec.finish(ok=False)
        return {"scored": 0}

    entities = load_entities()
    priors = _prior_events(int(scfg["novelty"]["lookback_days"]), day)
    if not priors:
        # 首跑没有历史：回看集为空会系统性高估 novelty，必须显式记录这个偏差
        C.log("注意：无历史事件可比（首跑），novelty 将系统性偏高 —— 这是已知偏差，不是 bug", "WARN")

    scored = []
    for e in events:
        r = score_event(e, scfg, entities, priors, now)
        scored.append({**e, **r})
    scored.sort(key=lambda x: -x["total"])
    for i, e in enumerate(scored, 1):
        e["rank"] = i

    C.write_jsonl(C.STATE_DIR / f"scored-{day}.jsonl", scored)
    thr = scfg["thresholds"]
    passed = [e for e in scored if e["total"] >= thr["publish_min_total"]]
    ext_n = sum(1 for e in scored if e.get("aihot_prior"))
    ext_w = float((scfg.get("aihot_prior") or {}).get("weight", 0))
    run_rec.set(events=len(scored), above_floor=len(passed), entities_loaded=len(entities),
                priors=len(priors), external_prior=ext_n, day=day)
    run_rec.finish()
    C.log(f"评分完成：{len(scored)} 个事件，{len(passed)} 个过底线（{thr['publish_min_total']}）")
    if ext_n:
        C.log(f"  其中 {ext_n} 个带 AIHOT 线索分 → impact 按 {ext_w} 权重混合"
              f"（其余 {len(scored) - ext_n} 个走纯规则，行为不变）")
    for e in scored[:10]:
        C.log(f"  {e['rank']:>2}. {e['total']:.3f}  {T.clip(e['title'], 58)}")
    return {"scored": len(scored)}


def main() -> int:
    ap = argparse.ArgumentParser(description="L1 评分层")
    ap.add_argument("--day", default=None)
    a = ap.parse_args()
    run(a.day)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
