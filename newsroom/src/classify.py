# -*- coding: utf-8 -*-
"""S1 分类闸：相关性判定 + 主题归类（闭集）。

**这一层直接来自原始 n8n 工作流的 `Is AI Related1` 节点**，是规范资产而非新发明。
原提示词里的 7 条 include/exclude 判定标准在此落成可执行规则。

为什么必须独立成一层（首跑实测）：
    没有它，早报里会出现《国产动画电影〈八仙！〉票房破 19 亿》（IT之家）
    和《Datasette 安全更新》（个人博客）。综合科技源本身是合法信源，
    但**必须经过相关性判定**才能进内参 —— 这正是"内参"与"科技聚合"的分界线。

主题闭集与原始提示词的「官方主题列表」逐项对齐（14 项）。
原提示词早已写明"严禁创造列表之外的新主题"，但存量里仍长出 616 个碎片：
**规范写在提示词里、没有落在代码里，等于不存在。**

v1 为纯规则；v2 接 GLM-4.7-Flash 后模型只覆盖 `relevance`，
本层的规则值保留为 fallback 与交叉校验基线（与 score.py 同一套约定）。

用法：
    python3 -m src.classify
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

_STRONG_W = 0.34
_WEAK_W = 0.11
_STRONG_CAP = 3
_WEAK_CAP = 6

# Unicode 各类连字符/空格 → ASCII。
# 首跑实测：`GPT‑Live‑1` 用的是 U+2011（非断行连字符），导致 `\bGPT\b` 这类
# 词边界匹配全部失效，一条明显的 AI 新闻被判为无关。匹配前必须归一。
_DASH_MAP = str.maketrans({
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
    "\u2014": "-", "\u2015": "-", "\u2212": "-", "\uff0d": "-",
    "\u00a0": " ", "\u3000": " ", "\u2009": " ", "\u202f": " ",
})


def _normalize(s: str) -> str:
    return (s or "").translate(_DASH_MAP)


def _compile(patterns: list[str]) -> list[re.Pattern]:
    out = []
    for p in patterns or []:
        try:
            out.append(re.compile(p, re.I))
        except re.error:
            continue
    return out


class Gate:
    def __init__(self, cfg: dict):
        r = cfg.get("relevance", {})
        self.min_score = float(r.get("min_score", 0.30))
        self.soft_min = float(r.get("soft_min", 0.18))
        self.strong = _compile(r.get("strong_terms", []))
        self.weak = _compile(r.get("weak_terms", []))
        self.exclude = _compile(r.get("exclude_patterns", []))
        self.topics = [(t["topic"], _compile(t.get("patterns", [])))
                       for t in (cfg.get("topics") or [])]
        # 外部线索（AIHOT）的分类 → 本地闭集主题。放在本层而不是评分层：
        # 主题归属是分类层的职责。见 classify.yaml 的 aihot_category_topics。
        self.aihot_topics = dict(cfg.get("aihot_category_topics") or {})

    def relevance(self, text: str, title: str = "") -> tuple[float, list[str], str | None]:
        """返回 (相关度, 命中的强信号, 硬排除原因)。

        ⚠️ 硬排除的适用范围是**标题**，且**不是一票否决**。
        首跑实测的两次误杀：
          · "「星测未来」…太空算力星座"      → 正文里的"星座"命中了星座运势规则
          · "《三体》最狠的一句话，正在重写AI时代…" → 正文里的"电影"命中了影视规则
        教训：排除规则用来判"这条的**主题**是不是跑偏了"，而主题写在标题里；
        拿正文做硬排除，等于让一个无关名词杀掉一条 AI 新闻。
        因此：标题命中排除词时，只有**没有足够强信号**才真的丢掉。
        """
        text = _normalize(text)
        title_n = _normalize(title)

        s_hits = [p.search(text).group(0) for p in self.strong if p.search(text)]
        w_hits = [p.search(text).group(0) for p in self.weak if p.search(text)]
        score = (min(len(s_hits), _STRONG_CAP) * _STRONG_W
                 + min(len(w_hits), _WEAK_CAP) * _WEAK_W)
        score = min(score, 1.0)

        excl = None
        if title_n:
            for p in self.exclude:
                m = p.search(title_n)
                if m:
                    excl = m.group(0)
                    break
        # 保留门槛：标题跑偏时，至少要有 1 个强信号（=0.34）才留下
        if excl and score < _STRONG_W + 0.06:
            return 0.0, [], f"硬排除（标题含「{excl}」且无足够 AI 信号）"
        return score, s_hits, None

    def topics_of(self, text: str, limit: int = 3, extra: list[str] | None = None) -> list[str]:
        text = _normalize(text)
        scored = []
        for name, pats in self.topics:
            n = sum(1 for p in pats if p.search(text))
            if n:
                scored.append((n, name))
        # 外部线索的分类只做**补充**：本地词表命中优先，外部映射填空（n=0 排最后）。
        # 这样它不会覆盖本地判断，只在本地词表对不上时补一个主题。
        if extra:
            have = {n for _, n in scored}
            for t in extra:
                if t and t not in have:
                    scored.append((0, t))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [n for _, n in scored[:limit]]

    def topics_from_aihot(self, category: str) -> list[str]:
        """AIHOT 分类 → 本地主题。无映射的分类返回空（**不做模糊归属**）。"""
        t = self.aihot_topics.get(category or "")
        return [t] if t else []


def _aihot_meta(event: dict) -> dict:
    """取事件里的 AIHOT 线索元数据（有则返回，无则空 dict）。"""
    for s in event.get("sources", []):
        a = s.get("aihot")
        if a:
            return a
    return {}


def run(day: str | None = None) -> dict:
    cfg = C.load_config("classify")
    gate = Gate(cfg)
    run_rec = C.Run("classify")
    day = day or C.day_key()

    events = C.read_jsonl(C.STATE_DIR / f"events-{day}.jsonl")
    if not events:
        run_rec.error(f"无事件文件：{C.STATE_DIR / f'events-{day}.jsonl'} —— 先跑 cluster")
        run_rec.finish(ok=False)
        return {"kept": 0}

    kept, dropped, borderline = [], [], []
    disagree = []
    for e in events:
        blob = " ".join([e.get("title", "")] + [s.get("summary", "") for s in e.get("sources", [])])
        score, hits, excl = gate.relevance(blob, e.get("title", ""))
        e["relevance"] = round(score, 4)
        e["relevance_hits"] = hits[:6]
        am = _aihot_meta(e)
        e["topics"] = gate.topics_of(blob, extra=gate.topics_from_aihot(am.get("category", "")))
        if excl:
            e["gate"] = "excluded"
            e["gate_reason"] = excl
            dropped.append(e)
        elif score >= gate.min_score:
            e["gate"] = "pass"
            e["gate_reason"] = f"相关性 {score:.2f}（命中 {', '.join(hits[:3]) or '—'}）"
            kept.append(e)
        elif score >= gate.soft_min:
            e["gate"] = "borderline"
            e["gate_reason"] = f"相关性 {score:.2f} 介于软阈值与硬阈值之间（未接 LLM 闸时按丢弃处理）"
            borderline.append(e)
            dropped.append(e)
        else:
            e["gate"] = "excluded"
            e["gate_reason"] = f"相关性 {score:.2f} 低于阈值 {gate.min_score}"
            dropped.append(e)
        # ── 分歧留痕：AIHOT 选中 ≠ 本地规则认可 ──
        # 两套独立判断的分歧是**规则改进的燃料**（AIHOT 说这是 AI 新闻，我们的词表说不是
        # ——要么它错了，要么我们的强信号词表漏了词）。但 v1 **不改变入选行为**：
        # 只记录，不动结果。让外部源能改变入选，等于把发布权部分交给了不可审计的第三方。
        if am and e["gate"] != "pass":
            e["disagreement"] = (f"AIHOT 选中（分类 {am.get('category') or '—'}，"
                                 f"分 {am.get('score')}）但本地闸判 {e['gate']}")
            disagree.append(e)

    # 未通过的事件不删除 —— 保留在独立文件里，"为什么被拒"是改进规则的燃料
    C.write_jsonl(C.STATE_DIR / f"classified-{day}.jsonl", kept)
    C.write_jsonl(C.STATE_DIR / f"rejected-{day}.jsonl", dropped)
    if disagree:
        C.write_jsonl(C.STATE_DIR / f"disagreement-{day}.jsonl", disagree)

    run_rec.set(events=len(events), kept=len(kept), dropped=len(dropped),
                borderline=len(borderline), disagreement=len(disagree), day=day,
                keep_rate=round(len(kept) / max(1, len(events)), 3))
    run_rec.finish()
    C.log(f"分类闸：{len(events)} → 保留 {len(kept)}，剔除 {len(dropped)}"
          f"（其中临界 {len(borderline)}），保留率 {len(kept) / max(1, len(events)) * 100:.0f}%")
    if disagree:
        C.log(f"  ⚠️ 与 AIHOT 判断分歧 {len(disagree)} 条（已记录，不改变入选）")
        for e in disagree[:4]:
            C.log(f"    ? {T.clip(e['title'], 50)}  ← {e['gate_reason'][:30]}")
    C.log("  被剔除样例：")
    for e in dropped[:6]:
        C.log(f"    ✗ [{e['relevance']:.2f}] {T.clip(e['title'], 52)}  ← {e['gate_reason'][:34]}")
    return {"kept": len(kept), "dropped": len(dropped), "disagreement": len(disagree)}


def main() -> int:
    ap = argparse.ArgumentParser(description="S1 分类闸")
    ap.add_argument("--day", default=None)
    a = ap.parse_args()
    run(a.day)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
