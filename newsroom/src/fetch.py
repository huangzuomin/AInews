# -*- coding: utf-8 -*-
"""L0 采集层。

职责：信源 → 原始条目（Source）。

三条硬规则（设计文档 §8）：
  1. **原文原样落盘**：原始字节 gzip 存 `raw/<day>/blobs/<fp>.xml.gz` + sha256。
     这是"可重放"的落地方式 —— 任取一天，能离线重放整条链路得到相同结果。
  2. **采集不引依赖**：stdlib `urllib`。NAS 无 pip3，不为采集破坏这个前提。
  3. **单源失败不升级为全局失败**：一个源 429/503/畸形 XML，只记 manifest，不影响其他源。

用法：
    python3 -m src.fetch              # 采集今天
    python3 -m src.fetch --day 2026-09-11
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lib import common as C          # type: ignore
    from lib import rss as R             # type: ignore
    from lib import textutil as T        # type: ignore
else:
    from .lib import common as C
    from .lib import rss as R
    from .lib import textutil as T


def _url_for(src: dict, cfg: dict) -> str:
    if src.get("kind") == "rsshub":
        return cfg["rsshub_base"].rstrip("/") + "/" + src["route"].lstrip("/")
    if src.get("kind") == "aihot":
        return _aihot_url(src)
    return src.get("url", "")


# ─────────────────────── aihot 发现层 ───────────────────────
# aihot.news 在链路里的位置是**线索层（discovery）**，不是内容源。三条理由：
#
#  1. 它的 `title` / `summary` 是 AIHOT 自己的**中文改写**（`originalTitle` 才是原文标题）。
#     把它当原文摘录用，等于把别人的改写当成了原始素材 —— 早报"零创作、只从原文删"
#     的契约会当场失效。所以摘要必须带 `summary_origin` 标记，产物层据此署名。
#  2. 但它补上了两个我们自己的真实缺口：① 我们没有 RSS 的源（公众号 / X / 各家 Blog）
#     ② **英文一手源没有中文标题**（首跑早报第 7–10 条是原样英文标题）。
#  3. 它自带一个外部质量分（`score` 0–100）+ 分类 + 入选理由 —— 这是现成的**先验**，
#     正好喂给 score.py 的 impact 维做融合（见 scoring.yaml 的 `aihot_prior`）。
#
# 红线落地：`url` 一律取 `links.original`，且 `source_name` 带 `AIHOT·` 前缀 ——
# 后者同时满足 AIHOT 的 attribution 要求（它的 `attribution` 字段即为此设）。
#
# `source_id` 固定为注册表里的 id（= "aihot"）而不是按 origin 拆分：
# 这样 scoring.yaml 的 `diversity` 配额会把全部线索当作**一个源**去限额，
# 13 条线索不可能淹没 10 条早报。origin 保留在 `source_name` 与 `aihot.origin` 里。

_ORIGIN_TAIL_RE = re.compile(r"\s*[（(][^（()）]{0,40}[）)]\s*$")


def _clean_origin(name: str) -> str:
    """去掉出处名尾部的括号限定语。

    实测 AIHOT 的出处名常见：
        `OpenAI：官网动态（RSS · 排除企业/客户案例）`
        `Anthropic：Research（发表成果 · 网页）`
    署名行是 `AIHOT·<出处>` 且整体再包一层括号，不清理的话
    Markdown 链接里的括号会看起来像嵌套错误，且显示名过长挤占列表。
    """
    raw = (name or "").strip()
    s, prev = raw, None
    while s and s != prev:
        prev = s
        s = _ORIGIN_TAIL_RE.sub("", s).strip()
    return s or raw


def _aihot_url(src: dict) -> str:
    base = src.get("url") or "https://aihot.news/api/v1/items"
    params = {
        "mode": src.get("mode", "selected"),
        "window": src.get("window", "24h"),
        "limit": int(src.get("limit", 100)),
    }
    sep = "&" if "?" in base else "?"
    return base + sep + urllib.parse.urlencode(params)


def _aihot_records(items: list[dict], src: dict, now, max_age_h: float) -> tuple[list[dict], int]:
    """aihot item → Source 记录。返回 (records, skipped)。"""
    sid = src.get("id", "aihot")
    label = src.get("name", "AIHOT")
    out: list[dict] = []
    skipped = 0
    for it in items:
        links = it.get("links") or {}
        original = (links.get("original") or "").strip()
        title = (it.get("title") or it.get("originalTitle") or "").strip()
        if not original or not title:
            skipped += 1                      # 没有原文链接的线索不能用（红线）
            continue
        pub = C.parse_iso(it.get("publishedAt", ""))
        if pub and C.hours_between(now, pub) > max_age_h:
            skipped += 1
            continue
        origin = _clean_origin((it.get("source") or {}).get("name") or "") or "未知出处"
        fp = C.short_hash(f"{sid}|{it.get('id') or original}")
        out.append({
            "source_id": sid,
            "source_name": f"{label}·{origin}",
            "tier": src.get("tier", "aggregator"),
            "lang": src.get("lang", "zh"),     # title/summary 都是 AIHOT 的中文版本
            "weight": float(src.get("weight", 0.5)),
            "title": title,
            "original_title": (it.get("originalTitle") or "").strip(),
            "url": original,
            "summary": (it.get("summary") or "").strip(),
            "summary_origin": "aihot",
            "image": "",
            "guid": it.get("id", ""),
            "published_at": it.get("publishedAt", ""),
            "fetched_at": C.iso(now),
            "fingerprint": fp,
            "norm_title": T.norm_title(title),
            "via": "aihot",
            "aihot": {
                "id": it.get("id", ""),
                "url": links.get("aihot", ""),
                "score": it.get("score"),
                "category": it.get("category", ""),
                "selected": bool(it.get("selected")),
                "reason": (it.get("reason") or "").strip(),
                "origin": origin,
                "discovered_at": it.get("discoveredAt", ""),
            },
        })
    return out, skipped



def _fetch(url: str, ua: str, timeout: int) -> tuple[int, bytes, str]:
    """返回 (http_status, body, error)。永不抛异常 —— 采集层对网络免疫。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip",
    })
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read()
            if (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
                try:
                    body = gzip.decompress(body)
                except OSError:
                    pass
            return resp.status, body, ""
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, body, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return 0, b"", f"URLError {e.reason}"
    except Exception as e:  # 超时 / SSL / 其他
        return 0, b"", f"{type(e).__name__}: {e}"


def run(day: str | None = None, only: list[str] | None = None) -> dict:
    cfg = C.load_config("sources")
    C.ensure_dirs()
    run_rec = C.Run("fetch")

    day = day or C.day_key()
    day_dir = C.RAW_DIR / day
    blob_dir = day_dir / "blobs"
    blob_dir.mkdir(parents=True, exist_ok=True)

    ua = cfg.get("user_agent", "neican-bot/1.0")
    timeout = int(cfg.get("timeout_seconds", 30))
    cap = int(cfg.get("max_items_per_source", 40))
    max_age_h = float(cfg.get("max_age_hours", 72))
    now = C.bjnow()

    sources = [s for s in cfg.get("sources", []) if s.get("status") == "ok"]
    if only:
        sources = [s for s in sources if s["id"] in only]

    records: list[dict] = []
    manifest: list[dict] = []
    seen_fp: set[str] = set()

    for src in sources:
        url = _url_for(src, cfg)
        sid = src["id"]
        t0 = time.time()
        status, body, err = _fetch(url, ua, timeout)
        elapsed = round(time.time() - t0, 2)

        entry = {
            "source_id": sid, "name": src.get("name", sid), "url": url,
            "http": status, "bytes": len(body), "elapsed_s": elapsed,
            "items_total": 0, "items_fresh": 0, "items_new": 0,
            "ok": status == 200 and bool(body), "error": err,
        }

        if not entry["ok"]:
            run_rec.error(f"信源失败 {sid}: {err} ({elapsed}s)")
            manifest.append(entry)
            continue

        # 原文原样落盘（可重放的凭证）
        fp_blob = C.sha256_bytes(body)
        ext = "json" if src.get("kind") == "aihot" else "xml"
        with gzip.open(blob_dir / f"{fp_blob[:16]}.{ext}.gz", "wb") as f:
            f.write(body)
        entry["sha256"] = fp_blob

        # ── aihot：JSON 线索层（与 RSS 的差别大于共性，单独一条支路更清楚）──
        if src.get("kind") == "aihot":
            try:
                payload = json.loads(body.decode("utf-8", "replace"))
                items = payload.get("items") or []
            except (ValueError, UnicodeDecodeError) as e:
                entry["ok"] = False
                entry["error"] = f"JSON {type(e).__name__}"
                run_rec.error(f"线索源解析失败 {sid}: {type(e).__name__}: {e}")
                manifest.append(entry)
                continue
            entry["items_total"] = len(items)
            recs, skipped = _aihot_records(items, src, now, max_age_h)
            entry["items_fresh"] = len(recs)
            entry["items_skipped"] = skipped
            for rec in recs:
                if rec["fingerprint"] in seen_fp:
                    continue
                seen_fp.add(rec["fingerprint"])
                entry["items_new"] += 1
                records.append(rec)
            # 线索单独留一份：便于"AIHOT 今天报了哪些、我们漏了哪些"逐日对照
            C.write_jsonl(day_dir / "aihot.jsonl", recs)
            manifest.append(entry)
            C.log(f"  {sid:<20} http={status} {len(body):>7}B "
                  f"{entry['items_new']:>3}新/{len(items):>3}线索 {elapsed}s")
            continue

        items = R.parse_feed(body)
        entry["items_total"] = len(items)

        for it in items:
            pub = C.parse_iso(it.get("published", ""))
            if pub and C.hours_between(now, pub) > max_age_h:
                continue
            entry["items_fresh"] += 1
            key = it.get("link") or it.get("guid") or it.get("title")
            fp = C.short_hash(f"{sid}|{key}")
            if fp in seen_fp:
                continue
            seen_fp.add(fp)
            entry["items_new"] += 1
            records.append({
                "source_id": sid,
                "source_name": src.get("name", sid),
                "tier": src.get("tier", "media"),
                "lang": src.get("lang", "en"),
                "weight": float(src.get("weight", 0.5)),
                "title": it.get("title", ""),
                "url": it.get("link", ""),
                "summary": it.get("summary", ""),
                "summary_origin": "feed",     # 原文片段（可能仍需清洗，但至少是原文）
                "image": it.get("image", ""),
                "guid": it.get("guid", ""),
                "published_at": it.get("published", ""),
                "fetched_at": C.iso(now),
                "fingerprint": fp,
                "norm_title": T.norm_title(it.get("title", "")),
            })

        if len(records) > cap * len(sources):
            pass
        manifest.append(entry)
        C.log(f"  {sid:<20} http={status} {len(body):>7}B {entry['items_fresh']:>3}新/{entry['items_total']:>3}总 {elapsed}s")

    # 落盘
    n = C.write_jsonl(day_dir / "sources.jsonl", records)
    clues = sum(1 for r in records if r.get("via") == "aihot")
    C.write_json_atomic(day_dir / "manifest.json", {
        "day": day, "fetched_at": C.iso(now), "sources": len(sources),
        "records": n, "clues": clues, "entries": manifest,
    })

    run_rec.set(sources_ok=sum(1 for m in manifest if m["ok"]),
                sources_total=len(sources), records=n, clues=clues, day=day)
    if len(sources) - sum(1 for m in manifest if m["ok"]) > 0:
        run_rec.set(sources_failed=len(sources) - sum(1 for m in manifest if m["ok"]))
    run_rec.finish()
    C.log(f"采集完成：{n} 条新条目（其中 aihot 线索 {clues} 条）→ {day_dir/'sources.jsonl'}")
    return {"records": n, "clues": clues, "manifest": manifest}


def main() -> int:
    ap = argparse.ArgumentParser(description="L0 采集层")
    ap.add_argument("--day", default=None)
    ap.add_argument("--only", default=None, help="逗号分隔的 source_id，仅采集这些源")
    a = ap.parse_args()
    only = [s.strip() for s in a.only.split(",")] if a.only else None
    run(a.day, only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
