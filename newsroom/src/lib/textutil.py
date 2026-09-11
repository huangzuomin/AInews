# -*- coding: utf-8 -*-
"""文本工具：清洗、归一、指纹、相似度。

为什么用**字符二元组（bigram）**而不是分词：NAS 上没有 jieba，
而中文的字符 bigram + Jaccard 在"同一条新闻的不同报道"上表现足够好，
且完全确定、可重放 —— 这是"可重放"红线要求的性质。
后续接入 LLM 归并时，本模块退化为"预筛"，不删除。
"""
from __future__ import annotations

import difflib
import html
import re
import unicodedata

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# 归一化时剥离的字符：标点、符号、空白、emoji
_STRIP_RE = re.compile(
    r"[\s\u3000!-/:-@\[-`{-~"
    r"\u2010-\u2027\u2030-\u205e\u3001-\u303f\uff01-\uff5e"
    r"\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]+"
)
# 标题尾部常见的站名后缀
_SUFFIX_RE = re.compile(
    r"\s*[|\-–—·]\s*(the verge|techcrunch|ars technica|bbc|nyt|the guardian|"
    r"venturebeat|reuters|bloomberg|wired|cnbc|the information|"
    r"量子位|机器之心|36氪|infoq|it之家|虎嗅|钛媒体|新智元)\s*$",
    re.I,
)
_EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]+")


def strip_html(s: str) -> str:
    """去标签 + 反转义实体 + 折叠空白。"""
    if not s:
        return ""
    s = _TAG_RE.sub(" ", s)
    s = html.unescape(s)
    return _WS_RE.sub(" ", s).strip()


def norm_width(s: str) -> str:
    """全角 → 半角（NFKC），保留中文。"""
    return unicodedata.normalize("NFKC", s or "")


def norm_title(s: str) -> str:
    """标题归一：供相似度比较使用。不保留任何格式信息。"""
    if not s:
        return ""
    s = strip_html(s)
    s = _EMOJI_RE.sub("", s)
    s = _SUFFIX_RE.sub("", s)
    s = norm_width(s).lower()
    s = _STRIP_RE.sub("", s)
    return s.strip()


def bigrams(s: str) -> set[str]:
    """字符二元组集合。长度 < 2 时退化为 unigram。"""
    if not s:
        return set()
    if len(s) < 2:
        return {s}
    return {s[i:i + 2] for i in range(len(s) - 1)}


def jaccard(a: str, b: str) -> float:
    """归一化标题的 bigram Jaccard 相似度。"""
    A, B = bigrams(a), bigrams(b)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter / union if union else 0.0


def ratio(a: str, b: str) -> float:
    """difflib 序列相似度（对语序敏感，与 Jaccard 互补）。"""
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def clip(s: str, n: int, ellipsis: str = "…") -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - len(ellipsis)] + ellipsis


def slugify(title: str, max_len: int = 50) -> str:
    """从标题生成 slug。中文标题无法转 ASCII，故回退为拼音无关的短哈希后缀策略：
    取归一化标题的哈希前 10 位；调用方负责拼接日期前缀。
    """
    import hashlib
    base = norm_title(title)
    if not base:
        return "article"
    h = hashlib.sha256(base.encode("utf-8")).hexdigest()[:10]
    return h


def count_sentences(text: str) -> int:
    return len([x for x in re.split(r"[。！？.!?]+", text or "") if x.strip()])


def has_number(s: str) -> bool:
    return bool(re.search(r"\d", s or ""))


def to_cjk_punct(s: str) -> str:
    """半角标点 → 全角（中文正文排版用）。只处理句内标点，不动数字与英文。"""
    if not s:
        return s
    # 仅当两侧都是中文时才替换，避免破坏 URL 与英文
    s = re.sub(r"(?<=[\u4e00-\u9fff]),(?=[\u4e00-\u9fff])", "，", s)
    s = re.sub(r"(?<=[\u4e00-\u9fff]);(?=[\u4e00-\u9fff])", "；", s)
    s = re.sub(r"(?<=[\u4e00-\u9fff]):(?=[\u4e00-\u9fff])", "：", s)
    return s


# ── RSS description 清洗 ─────────────────────────────────────────────
# 实测（2026-09-11 首跑）：多数 feed 的 <description> 不是摘要，而是**正文开头**，
# 于是把署名行、栏目标记、编号小标题一起带了进来，例如
#   "文｜王欣逸 编辑｜张雨忻 世界模型赛道将再添一笔大额融资。"
#   "一、活跃人数：月活5.77亿，7月重回增长…"
# 早报是"零创作"产品，摘要只能来自原文片段，所以**必须清洗**而不是改写。

_BYLINE_HEAD_RE = re.compile(
    r"^\s*(?:(?:文|作者|编辑|编译|记者|来源|原标题|题图|视觉|出品|栏目|责编|校对)"
    r"[\s｜|:：·][^\n。！？]{0,18}\s*){1,5}"
)
# 栏目标记：《智能涌现》独家获悉 / 36氪获悉 / 据xx报道
_PROMO_INLINE_RE = re.compile(r"^(?:《[^》]{1,14}》|[\u4e00-\u9fff]{2,6})?(?:独家获悉|获悉|独家|首发|编译)[，,、\s]*")
_SOURCE_TAIL_RE = re.compile(r"(?:原文链接|本文来自|转载自|来源)[\s：:][^\n]{0,50}$")
_ENUM_HEAD_RE = re.compile(r"^\s*(?:[一二三四五六七八九十]+[、.．]|\d{1,2}[、.．])\s*")
_PROMO_HEAD_RE = re.compile(r"^\s*(?:36氪首发|36氪独家|独家|首发|编译|快讯|钛媒体|雷峰网)[｜|\s]*")
_TRAIL_ELLIPSIS_RE = re.compile(r"(?:[….。！？]{2,}|\s+)\s*$")


_DISPLAY_TAIL_RE = re.compile(
    r"\s*[｜|]\s*(?:36氪首发|36氪独家|独家|首发|编译|钛媒体|雷峰网|机器之心|量子位|新智元"
    r"|原创|首发于|文｜[^\s]{1,12})\s*$"
)
_DISPLAY_TAIL2_RE = re.compile(r"\s*[（(]\s*(?:图源|图片来源|题图|编辑|责编)[^）)]{0,20}[）)]\s*$")


def display_title(s: str) -> str:
    """标题的**展示形态**：去掉发布渠道尾巴，不改动表意。

    （评分用的是原始标题，展示用的是这个 —— 两者分离，
    因为"标题党"要扣分，而"｜36氪首发"只是渠道标记，不该影响判断。）
    """
    if not s:
        return ""
    s = strip_html(s)
    s = _DISPLAY_TAIL_RE.sub("", s)
    s = _DISPLAY_TAIL2_RE.sub("", s)
    return s.strip().rstrip("。").strip()


# 垃圾摘要：部分源的 description 是页面骨架或 JS 占位（实测 openai.com 的 RSS
# 返回 "Loading… Share Connect to the company data and context…"），
# 这种片段进了早报就是噪声，宁可留空。
_JUNK_RE = re.compile(
    r"^(?:Loading|Loading…|Share|Home|Menu|Skip to|Cookie|We use cookies|"
    r"Thanks for|Subscribe|Sign in|Log in)\b",
    re.I,
)


_SENT_END_CJK = "。！？!?"
# 开括号 → 闭括号。截断后可能留下未闭合的开括号，需要退回去。
_BRACKETS = {"（": "）", "(": ")", "「": "」", "『": "』", "【": "】", "《": "》"}


def _last_sentence_end(s: str) -> int:
    """最后一个**真句末**的下标；没有则 -1。

    为什么不能直接 `max(s.rfind(c) for c in "。！？!?.")`：
    实测把「全网渗透率52.6%，过半移动网民在用AI应用…」切成了「全网渗透率52.」——
    ASCII 句点同时是小数点，而 `max(rfind)` 会让**更靠后的小数点**盖掉**更早的真句号**，
    结果是摘要停在半个百分数上。所以 "." 必须在两侧都是数字时被排除。
    """
    best = -1
    for i, ch in enumerate(s):
        if ch in _SENT_END_CJK:
            best = i
        elif ch == ".":
            prev = s[i - 1] if i else ""
            nxt = s[i + 1] if i + 1 < len(s) else ""
            if prev.isdigit() and nxt.isdigit():
                continue                     # 小数点，不是句末
            best = i
    return best


def _trim_dangling_bracket(s: str) -> str:
    """若截断留下了未闭合的开括号，退回到最早那个开括号之前。

    半句里带一个孤零零的「（」进了 frontmatter 比少一句话更脏。
    闭合判定用栈：成对出现的括号不影响结果，只有真正没配上的才回退。
    """
    stack: list[tuple[int, str]] = []
    for i, ch in enumerate(s):
        if ch in _BRACKETS:
            stack.append((i, ch))
        elif ch in _BRACKETS.values():
            # 关掉离它最近的那个同类开括号
            for j in range(len(stack) - 1, -1, -1):
                if _BRACKETS[stack[j][1]] == ch:
                    del stack[j]
                    break
    if stack:
        return s[: stack[0][0]].rstrip("，、；：,;: 　")
    return s


def is_junk_summary(s: str) -> bool:
    if not s:
        return True
    s = strip_html(s).strip()
    if len(s) < 24:
        return True
    if _JUNK_RE.match(s):
        return True
    # 大量 "…" 或重复短语 → 页面骨架
    if s.count("…") >= 3 or s.count("Share") >= 2:
        return True
    return False


def clean_summary(s: str, title: str = "", max_len: int = 200) -> str:
    """把 RSS 正文片段清洗成可用作早报摘要的一句话。

    只做**删除**，不做改写 —— 早报的契约是"零创作"。
    """
    if not s or is_junk_summary(s):
        return ""
    s = strip_html(s)
    s = _BYLINE_HEAD_RE.sub("", s)
    s = _PROMO_HEAD_RE.sub("", s)
    s = _PROMO_INLINE_RE.sub("", s)
    s = _SOURCE_TAIL_RE.sub("", s)
    s = _ENUM_HEAD_RE.sub("", s)
    # 摘要以标题开头时去掉重复的标题部分
    t = strip_html(title or "").strip()
    if t and len(t) >= 8 and s.startswith(t):
        s = s[len(t):].lstrip("，。：: 　")
    s = _WS_RE.sub(" ", s).strip()
    s = _TRAIL_ELLIPSIS_RE.sub("", s)
    # 截断纪律：优先在**句末**断开，退而求其次才加省略号。
    # （早报是 10 条并排的清单页，摘要在句中硬断会读起来很脏。）
    if len(s) > max_len:
        head = s[:max_len]
        cut = _last_sentence_end(head)
        if cut >= max_len * 0.5:
            s = head[: cut + 1]
        else:
            tail = head.rstrip("，、；：,;: 　")
            # 英文词边界：别把 "alpha" 切成 "al…"（只对 ASCII 生效，中文整段回退会很怪）
            k = len(tail)
            if k and tail[-1].isascii() and tail[-1].isalnum():
                while k > 0 and tail[k - 1].isascii() and tail[k - 1].isalnum():
                    k -= 1
                if k >= max_len * 0.4:
                    tail = tail[:k].rstrip("，、；：,;: 　-")
            s = tail + "…"
    # 兜底：切点可能落在括号内部，留下半个「（」
    s = _trim_dangling_bracket(s)
    return s.strip()
