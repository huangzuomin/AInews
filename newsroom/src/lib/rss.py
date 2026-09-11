# -*- coding: utf-8 -*-
"""RSS 2.0 / Atom 解析（stdlib，命名空间无关）。

设计取舍：
  * 先剥离命名空间再解析 —— 各站 feed 的 ns 前缀千奇百怪，逐一写映射不可维护。
  * 解析失败时退回正则抽条目 —— feed 是外部输入，**不能因为一个源的畸形 XML 就让整轮采集挂掉**。
    这与"分级降级"是同一条原则：单一源的问题不应升级为全局失败。
"""
from __future__ import annotations

import email.utils
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from . import textutil as T

_NS_RE = re.compile(rb"<(/?)[A-Za-z0-9_.-]+:")
_CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)
_ITEM_RE = re.compile(r"<(item|entry)\b.*?</\1>", re.S | re.I)
_TAG_FMT = r"<{0}\b[^>]*>(.*?)</{0}>"


def _strip_ns(raw: bytes) -> bytes:
    return _NS_RE.sub(rb"<\1", raw)


def _text_of(elem, *tags: str) -> str:
    """按 tag 名（忽略命名空间）取元素文本。"""
    for tag in tags:
        for child in elem.iter():
            if child.tag.lower() == tag.lower():
                if child.text:
                    return child.text.strip()
                # 富内容可能藏在子节点里
                inner = "".join(child.itertext()).strip()
                if inner:
                    return inner
    return ""


def _link_of(elem) -> str:
    """RSS 的 <link> 是文本；Atom 的 <link href> 是属性；Atom 优先 rel=alternate。"""
    best = ""
    for child in elem.iter():
        if child.tag.lower() != "link":
            continue
        href = child.get("href")
        if href:
            rel = (child.get("rel") or "alternate").lower()
            if rel == "alternate" and not best:
                best = href.strip()
            elif not best:
                best = href.strip()
        elif child.text and child.text.strip().startswith("http") and not best:
            best = child.text.strip()
    return best


def _date_of(elem) -> datetime:
    for tag in ("pubDate", "published", "updated", "dc:date", "date"):
        raw = _text_of(elem, tag)
        if not raw:
            continue
        dt = _try_date(raw)
        if dt:
            return dt
    return datetime.now(timezone.utc)


def _try_date(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    # RFC 822（RSS）
    try:
        d = email.utils.parsedate_to_datetime(raw)
        if d:
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    # ISO 8601（Atom）
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = datetime.strptime(raw, fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _image_of(elem) -> str:
    """尝试取条目配图：enclosure / media:content / 正文内首个 img。"""
    for child in elem.iter():
        tag = child.tag.lower()
        if tag in ("enclosure", "content", "thumbnail"):
            url = child.get("url") or child.get("href")
            if url and re.search(r"\.(jpe?g|png|webp|gif)\b", url, re.I):
                return url.strip()
        if tag in ("encoded", "description", "summary", "content"):
            inner = "".join(child.itertext())
            m = re.search(r'<img[^>]+src=["\']([^"\']+)', inner or "", re.I)
            if m:
                return m.group(1).strip()
    return ""


def _parse_items_raw(body: bytes) -> list[bytes]:
    """正则兜底：从畸形 XML 里抠出 <item>/<entry> 块。"""
    return [m.group(0) for m in _ITEM_RE.finditer(body.decode("utf-8", "replace"))]


def parse_feed(raw: bytes) -> list[dict]:
    """把 feed 字节流解析为条目列表。

    返回每项：{title, link, summary, published(iso), guid, image}
    解析失败的条目被跳过，不抛异常 —— 采集层必须对单条脏数据免疫。
    """
    if not raw:
        return []
    cleaned = _CDATA_RE.sub(lambda m: m.group(1), raw.decode("utf-8", "replace")).encode("utf-8")
    items: list[bytes] = []
    try:
        root = ET.fromstring(_strip_ns(cleaned))
        if isinstance(root.tag, str) and root.tag.lower() in ("rss", "feed", "rdf"):
            for child in root.iter():
                if child.tag.lower() in ("item", "entry"):
                    items.append(ET.tostring(child, encoding="utf-8"))
        if not items:
            # 有些源根节点直接是 item 列表
            for child in root.iter():
                if child.tag.lower() in ("item", "entry"):
                    items.append(ET.tostring(child, encoding="utf-8"))
    except ET.ParseError:
        items = [i.encode("utf-8") for i in _parse_items_raw(cleaned)]

    if not items:
        items = [i.encode("utf-8") for i in _parse_items_raw(cleaned)]

    out: list[dict] = []
    for blob in items:
        try:
            elem = ET.fromstring(_strip_ns(blob))
        except ET.ParseError:
            continue
        title = T.strip_html(_text_of(elem, "title"))
        link = _link_of(elem)
        summary = T.strip_html(_text_of(elem, "description", "summary", "content", "encoded"))
        if not title and not link:
            continue
        published = _date_of(elem)
        guid = _text_of(elem, "guid", "id") or link or title
        out.append({
            "title": title,
            "link": link,
            "summary": T.clip(summary, 1200),
            "published": published.astimezone(timezone.utc).isoformat(timespec="seconds"),
            "guid": guid,
            "image": _image_of(elem),
        })
    return out
