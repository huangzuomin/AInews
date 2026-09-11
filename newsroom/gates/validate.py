#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
neican.ai 发布门禁校验器（G1 / G2 / G3 / G3-b）

用法：
    python newsroom/gates/validate.py --content content/insights --gates g1,g2,g3
    python newsroom/gates/validate.py --built public --gates g3b
    python newsroom/gates/validate.py --content content --built public --gates all --json

退出码：0 = 全部通过；1 = 存在违规（CI 应据此阻断）

设计原则：
  - 只读，绝不修改内容
  - 阈值与闭集集中在 RULES 常量，P4 时外置为配置文件
  - G3-b 是唯一在"构建产物"上跑的闸 —— 因为结构化数据是模板产物，
    构建时无法自证（这正是 _internal/schema.html 静默失效潜伏数月的原因）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

# ----------------------------------------------------------------------------
# RULES —— 阈值与闭集（P4 外置为 newsroom/gates/rules.yaml）
# ----------------------------------------------------------------------------

RULES = {
    # G1 结构
    "h2_min": 2,
    "h3_per_h2_max": 3,
    "para_chars_max": 150,
    "sentence_chars_max": 60,
    "require_tldr": True,
    # G2 事实
    "numeric_sentence_sourced_ratio_min": 0.60,
    "primary_source_ratio_min": 0.50,
    # G3 元数据
    "title_chars_max": 30,
    "summary_chars_min": 80,
    "summary_chars_max": 160,
    "slug_timestamp_suffix": re.compile(r"-\d{20,}-\d+$"),
    # 一手源域名白名单（子串匹配，小写）
    "primary_source_domains": [
        "openai.com", "anthropic.com", "deepmind.google", "blog.google",
        "ai.meta.com", "microsoft.com", "nvidia.com", "apple.com",
        "deepseek.com", "api-docs.deepseek.com", "moonshot.cn", "zhipuai.cn",
        "minimaxi.com", "qwen.ai", "aliyun.com", "volcengine.com",
        "hunyuan.tencent.com", "yiyan.baidu.com", "baidu.com",
        "arxiv.org", "github.com", "huggingface.co", "openreview.net",
        "nature.com", "science.org", "acm.org", "ieee.org", "paperswithcode.com",
    ],
    # 明确拒绝的低质来源域名（子串匹配）
    "banned_source_domains": [
        "baike.baidu.com", "baijiahao.baidu.com", "zhihu.com/search",
    ],
    # 占位符模式
    "placeholder_patterns": [
        re.compile(r"\bYYYY\b"), re.compile(r"\bMM\b"), re.compile(r"\bDD\b"),
        re.compile(r"^--$", re.M), re.compile(r"\{\{.+\}\}"),
        re.compile(r"TODO|FIXME|待补充|请填写"),
    ],
    # 未兑现的承诺文字（文末声明中出现即视为违约，除非该页真有 sources）
    "unbacked_promises": ["引用信息索引"],
}

# main_topics 闭集（与 data/topics.yaml 保持一致）
MAIN_TOPICS = {
    "前沿模型与算法", "AI Agent与自主系统", "算力与芯片", "企业级AI与数字化",
    "产业生态与商业版图", "投融资与市场洞察", "AI伦理与治理", "社会影响与未来工作",
    "机器人与具身智能", "AIGC与内容科技", "AI与软件工程", "AI内参极速早报",
}

# 从 data/entities.yaml 读取实体注册表（canonical 闭集）
def load_entity_registry(root: Path) -> set[str]:
    p = root / "data" / "entities.yaml"
    if not p.exists():
        return set()
    txt = p.read_text(encoding="utf-8")
    return set(re.findall(r"^- canonical:\s*(.+?)\s*$", txt, re.M))


# ----------------------------------------------------------------------------
# frontmatter / 正文 解析
# ----------------------------------------------------------------------------

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def split_page(text: str) -> tuple[str, str]:
    m = FM_RE.match(text)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def fm_scalar(fm: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}\s*:\s*(.*)$", fm, re.M)
    if not m:
        return None
    v = m.group(1).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v


def fm_list(fm: str, key: str) -> list[str]:
    """解析 key: 下的 YAML 短横线列表（仅同层，遇到下一个顶层键停止）"""
    m = re.search(rf"^{re.escape(key)}\s*:\s*(.*)$", fm, re.M)
    if not m:
        return []
    inline = m.group(1).strip()
    if inline.startswith("[") and inline.endswith("]"):
        return [x.strip().strip("\"'") for x in inline[1:-1].split(",") if x.strip()]
    out: list[str] = []
    rest = fm[m.end():]
    for line in rest.split("\n"):
        if not line.strip():
            continue
        if re.match(r"^\s*-\s+", line):
            out.append(re.sub(r"^\s*-\s+", "", line).strip().strip("\"'"))
        elif re.match(r"^[A-Za-z_]", line):
            break
        else:
            continue
    return out


def fm_block(fm: str, key: str) -> list[dict]:
    """解析 key: 下的对象列表（用于 sources）"""
    m = re.search(rf"^{re.escape(key)}\s*:\s*$", fm, re.M)
    if not m:
        return []
    out: list[dict] = []
    cur: dict | None = None
    for line in fm[m.end():].split("\n"):
        if re.match(r"^[A-Za-z_]", line):
            break
        mm = re.match(r"^\s*-\s+(\w+)\s*:\s*(.*)$", line)
        if mm:
            if cur:
                out.append(cur)
            cur = {mm.group(1): mm.group(2).strip().strip("\"'")}
            continue
        m2 = re.match(r"^\s+(\w+)\s*:\s*(.*)$", line)
        if m2 and cur is not None:
            cur[m2.group(1)] = m2.group(2).strip().strip("\"'")
    if cur:
        out.append(cur)
    return out


# ----------------------------------------------------------------------------
# 文本度量
# ----------------------------------------------------------------------------

CJK = re.compile(r"[\u4e00-\u9fff]")


def char_len(s: str) -> int:
    """按"视觉宽度"计数：CJK 记 1，其余非空白按 0.5 累加后取整——此处直接返回字符数，
    但剔除空白与 markdown 标记，便于与 30/150/60 这类阈值口径一致。"""
    s = re.sub(r"[*_`#>\[\]()!]", "", s)
    s = re.sub(r"\s+", "", s)
    return len(s)


def paras(body: str) -> list[str]:
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    out = []
    for blk in re.split(r"\n\s*\n", body):
        b = blk.strip()
        if not b or b.startswith("|") or b.startswith("- ") or re.match(r"^\d+\.", b):
            continue
        out.append(b)
    return out


def sentences(p: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；;])|(?<=\.)\s+", p)
    return [x.strip() for x in parts if x.strip()]


def is_probably_table_row(block: str) -> bool:
    return block.strip().startswith("|")


# ----------------------------------------------------------------------------
# 各闸
# ----------------------------------------------------------------------------

def gate_g1(text: str, path: Path) -> list[str]:
    fm, body = split_page(text)
    v: list[str] = []

    heads = [(len(m.group(1)), m.group(2).strip())
             for m in re.finditer(r"^(#{1,6})\s+(.+)$", body, re.M)]
    h2 = [h for lv, h in heads if lv == 2]
    h3 = [h for lv, h in heads if lv == 3]
    h4 = [h for lv, h in heads if lv == 4]

    if heads and heads[0][0] != 2:
        v.append(f"[G1] 正文首个标题层级为 h{heads[0][0]}（应为 h2）：{heads[0][1][:24]}")
    if len(h2) < RULES["h2_min"]:
        v.append(f"[G1] h2 数量 {len(h2)} < {RULES['h2_min']}")
    if h2 and len(h3) / len(h2) > RULES["h3_per_h2_max"]:
        v.append(f"[G1] h3/h2 = {len(h3)}/{len(h2)} 超过 {RULES['h3_per_h2_max']}")
    if not h2 and h4:
        v.append("[G1] 出现 h4 但无 h2，层级倒挂")

    if RULES["require_tldr"] and not re.search(r"TL;?DR", body, re.I):
        v.append("[G1] 缺少 TL;DR")

    long_paras = [p for p in paras(body) if char_len(p) > RULES["para_chars_max"]]
    if long_paras:
        v.append(f"[G1] {len(long_paras)} 个段落超过 {RULES['para_chars_max']} 字"
                 f"（最长 {max(char_len(p) for p in long_paras)}）")

    long_sent = []
    for p in paras(body):
        for s in sentences(p):
            if char_len(s) > RULES["sentence_chars_max"]:
                long_sent.append(s)
    if long_sent:
        v.append(f"[G1] {len(long_sent)} 个句子超过 {RULES['sentence_chars_max']} 字"
                 f"（最长 {max(char_len(s) for s in long_sent)}）")
    return v


NUM_RE = re.compile(r"\d")


def gate_g2(text: str, path: Path) -> list[str]:
    fm, body = split_page(text)
    v: list[str] = []

    srcs = fm_block(fm, "sources")
    # 数字句是否带来源
    numeric, sourced = 0, 0
    for blk in re.split(r"\n\s*\n", body):
        if is_probably_table_row(blk):
            continue
        for s in sentences(blk):
            if not NUM_RE.search(s):
                continue
            numeric += 1
            if re.search(r"据|来源|报告|官方|论文|公告|release|blog|arxiv|http", s, re.I):
                sourced += 1
    if numeric >= 3:
        ratio = sourced / numeric
        if ratio < RULES["numeric_sentence_sourced_ratio_min"]:
            v.append(f"[G2] 含数字句子带来源比例 {ratio:.0%} "
                     f"< {RULES['numeric_sentence_sourced_ratio_min']:.0%}（{sourced}/{numeric}）")

    # 一手源比例
    if srcs:
        prim = sum(1 for s in srcs if (s.get("type") or "").lower() == "primary")
        r = prim / len(srcs)
        if r < RULES["primary_source_ratio_min"]:
            v.append(f"[G2] 一手源比例 {r:.0%} < {RULES['primary_source_ratio_min']:.0%}"
                     f"（{prim}/{len(srcs)}）")
        # 来源域名白名单 / 黑名单
        for s in srcs:
            u = (s.get("url") or "").lower()
            if not u:
                v.append(f"[G2] 来源缺 url：{(s.get('title') or '')[:30]}")
                continue
            if any(b in u for b in RULES["banned_source_domains"]):
                v.append(f"[G2] 来源命中拒绝名单：{u[:60]}")
            if (s.get("type") or "").lower() == "primary" and \
               not any(d in u for d in RULES["primary_source_domains"]):
                v.append(f"[G2] 标记为一手源但域名不在白名单：{u[:60]}")
    else:
        v.append("[G2] 缺少 sources（无来源索引 → 不可引用）")

    # 占位符
    for pat in RULES["placeholder_patterns"]:
        m = pat.search(fm) or pat.search(body)
        if m:
            v.append(f"[G2] 占位符残留：{m.group(0)[:20]!r}")

    # 未兑现承诺
    if not srcs:
        for phrase in RULES["unbacked_promises"]:
            if phrase in body:
                v.append(f"[G2] 正文出现「{phrase}」但无 sources —— 承诺未兑现")
    return v


def gate_g3(text: str, path: Path, entities: set[str]) -> list[str]:
    fm, _ = split_page(text)
    v: list[str] = []

    title = fm_scalar(fm, "title") or ""
    if not title:
        v.append("[G3] 缺少 title")
    elif char_len(title) > RULES["title_chars_max"]:
        v.append(f"[G3] title {char_len(title)} 字 > {RULES['title_chars_max']}")

    summ = fm_scalar(fm, "summary") or ""
    if not summ:
        v.append("[G3] 缺少 summary")
    else:
        n = char_len(summ)
        if n < RULES["summary_chars_min"] or n > RULES["summary_chars_max"]:
            v.append(f"[G3] summary {n} 字，超出 "
                     f"{RULES['summary_chars_min']}–{RULES['summary_chars_max']}")

    if not fm_scalar(fm, "featured_image"):
        v.append("[G3] 缺少 featured_image（og:image 会退化为站点默认图）")

    mts = fm_list(fm, "main_topics")
    if not mts:
        v.append("[G3] 缺少 main_topics")
    else:
        for t in mts:
            if t not in MAIN_TOPICS:
                v.append(f"[G3] main_topics 不在闭集：{t!r}")

    ents = fm_list(fm, "entities")
    if ents and entities:
        for e in ents:
            if e not in entities:
                v.append(f"[G3] entities 不在注册表：{e!r}")

    slug = path.stem
    if RULES["slug_timestamp_suffix"].search(slug):
        v.append(f"[G3] slug 含时间戳后缀（URL 关键词信号被噪声稀释）：{slug}")

    return v


def gate_g3b(built: Path) -> tuple[list[str], int]:
    """在构建产物上抽检 JSON-LD 与 og:image"""
    v: list[str] = []
    checked = 0
    htmls = list(built.rglob("index.html"))
    for f in htmls:
        rel = f.relative_to(built)
        # 只抽检文章页
        parts = rel.parts
        if not parts or parts[0] not in ("insights", "newspaper", "morningnews"):
            continue
        checked += 1
        if checked > 50:
            break
        try:
            html = f.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            v.append(f"[G3b] 读取失败 {rel}: {e}")
            continue

        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        if not m:
            v.append(f"[G3b] 无 JSON-LD：{rel}")
        else:
            raw = m.group(1)
            try:
                data = json.loads(raw)
            except Exception as e:
                v.append(f"[G3b] JSON-LD 不可解析 {rel}: {e}")
                data = None
            if isinstance(data, dict):
                graph = data.get("@graph") or []
                art = next((n for n in graph
                            if n.get("@type") in ("NewsArticle", "Article", "BlogPosting")), None)
                if not art:
                    v.append(f"[G3b] @graph 中无文章实体：{rel}")
                else:
                    for k in ("headline", "datePublished", "author", "publisher", "mainEntityOfPage"):
                        if not art.get(k):
                            v.append(f"[G3b] NewsArticle 缺必填字段 {k}：{rel}")

        if 'property="og:image"' not in html:
            v.append(f"[G3b] 无 og:image：{rel}")
        if 'name="twitter:card" content="summary_large_image"' not in html:
            v.append(f"[G3b] twitter:card 非 summary_large_image：{rel}")
        if "<time" not in html:
            v.append(f"[G3b] 无 <time> 元素：{rel}")
    return v, checked


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="neican.ai 发布门禁校验")
    ap.add_argument("--content", default=None, help="内容目录（G1/G2/G3）")
    ap.add_argument("--built", default=None, help="构建产物目录（G3-b）")
    ap.add_argument("--gates", default="all", help="g1,g2,g3,g3b 或 all")
    ap.add_argument("--json", action="store_true", help="输出 JSON 报告")
    ap.add_argument("--root", default=None, help="仓库根（默认自动推断）")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    gates = {"g1", "g2", "g3", "g3b"} if args.gates == "all" else \
            {g.strip().lower() for g in args.gates.split(",") if g.strip()}

    entities = load_entity_registry(root)
    report: dict = {
        "gates": sorted(gates),
        "entity_registry_size": len(entities),
        "files_checked": 0,
        "violations": [],
    }

    if args.content and (gates & {"g1", "g2", "g3"}):
        files = sorted(Path(args.content).rglob("*.md"))
        report["files_checked"] = len(files)
        for f in files:
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                report["violations"].append({"file": str(f), "issues": [f"读取失败: {e}"]})
                continue
            issues: list[str] = []
            if "g1" in gates:
                issues += gate_g1(text, f)
            if "g2" in gates:
                issues += gate_g2(text, f)
            if "g3" in gates:
                issues += gate_g3(text, f, entities)
            if issues:
                report["violations"].append({"file": str(f), "issues": issues})

    if args.built and "g3b" in gates:
        issues, checked = gate_g3b(Path(args.built))
        report["g3b_files_checked"] = checked
        if issues:
            report["violations"].append({"file": str(args.built), "issues": issues})

    n = len(report["violations"])
    report["verdict"] = "pass" if n == 0 else "fail"

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"门禁: {','.join(sorted(gates))}")
        print(f"实体注册表: {len(entities)} 项")
        print(f"检查文件: {report['files_checked']}")
        if "g3b" in gates:
            print(f"G3-b 抽检页面: {report.get('g3b_files_checked', 0)}")
        print(f"违规文件: {n}")
        for item in report["violations"][:40]:
            print(f"\n  {item['file']}")
            for i in item["issues"][:12]:
                print(f"    - {i}")
        if n > 40:
            print(f"\n  … 另有 {n - 40} 个文件未显示")
        print(f"\n结论: {report['verdict'].upper()}")

    return 0 if n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
