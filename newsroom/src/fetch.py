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
import ssl
import sys
import time
import urllib.error
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
    return src.get("url", "")


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
        with gzip.open(blob_dir / f"{fp_blob[:16]}.xml.gz", "wb") as f:
            f.write(body)

        items = R.parse_feed(body)
        entry["items_total"] = len(items)
        entry["sha256"] = fp_blob

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
    C.write_json_atomic(day_dir / "manifest.json", {
        "day": day, "fetched_at": C.iso(now), "sources": len(sources),
        "records": n, "entries": manifest,
    })

    run_rec.set(sources_ok=sum(1 for m in manifest if m["ok"]),
                sources_total=len(sources), records=n, day=day)
    if len(sources) - sum(1 for m in manifest if m["ok"]) > 0:
        run_rec.set(sources_failed=len(sources) - sum(1 for m in manifest if m["ok"]))
    run_rec.finish()
    C.log(f"采集完成：{n} 条新条目 → {day_dir/'sources.jsonl'}")
    return {"records": n, "manifest": manifest}


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
