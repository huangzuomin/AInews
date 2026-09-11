# -*- coding: utf-8 -*-
"""neican.ai 内容生产线 —— 共享基础设施。

约束（NAS 实测）：无 pip3 → 只用 stdlib（`yaml` 为系统自带 python3-yaml）。
路径约定：
    仓库内  = 代码 / 配置 / 提示词 / 已发布内容（进 git，可 diff、可回滚）
    仓库外  = 原始抓取、运行状态、日志、密钥（不进 git：体积大 / 版权敏感 / 含密钥）
这条边界是硬的：**只要仓库外的运行态不回流，构建后 git status 就恒为空**，
"干净工作区"这个自动化前提才成立（P1.1 的同类教训）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# ─────────────────────────── 路径 ───────────────────────────

_LIB = Path(__file__).resolve().parent          # newsroom/src/lib
SRC_DIR = _LIB.parent                            # newsroom/src
NEWSROOM = SRC_DIR.parent                        # newsroom
REPO = NEWSROOM.parent                           # 仓库根

CONFIG_DIR = NEWSROOM / "config"
PROMPT_DIR = NEWSROOM / "prompts"
# 可被 NEICAN_CONTENT_DIR 覆盖：用于"真写但不污染线上"的联调
# （否则补跑会为同一天生成与人工版重复的早报 —— 首跑实测踩到）
CONTENT_DIR = Path(os.environ.get("NEICAN_CONTENT_DIR", REPO / "content"))

RUN_HOME = Path(os.environ.get("NEICAN_RUN_HOME", "/mnt/SSD_Apps/apps/neican-run"))
RAW_DIR = RUN_HOME / "raw"                       # 原文原样落盘（可重放）
STATE_DIR = RUN_HOME / "state"                   # 事件 / 打分 / 排产 / 决策
EVID_DIR = RUN_HOME / "evidence"                 # 证据包（全文不进公开仓库）
LOG_DIR = RUN_HOME / "logs"

BJT = _dt.timezone(_dt.timedelta(hours=8))


def ensure_dirs() -> None:
    for d in (RAW_DIR, STATE_DIR, EVID_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ─────────────────────────── 时间 ───────────────────────────

def bjnow() -> _dt.datetime:
    """北京时间当前时刻（带时区）。整条链路只用这一个时间源。"""
    return _dt.datetime.now(tz=BJT)


def day_key(dt: _dt.datetime | None = None) -> str:
    return (dt or bjnow()).strftime("%Y-%m-%d")


def iso(dt: _dt.datetime) -> str:
    return dt.isoformat(timespec="seconds")


def hours_between(a: _dt.datetime, b: _dt.datetime) -> float:
    return abs((a - b).total_seconds()) / 3600.0


def parse_iso(s: str) -> _dt.datetime | None:
    if not s:
        return None
    try:
        d = _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=BJT)
    return d


# ─────────────────────────── 配置 ───────────────────────────

_cfg_cache: dict[str, dict] = {}


def load_config(name: str) -> dict:
    """加载 newsroom/config/<name>.yaml（带缓存）。"""
    if name in _cfg_cache:
        return _cfg_cache[name]
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"配置不存在：{path}")
    if yaml is None:
        raise RuntimeError("系统缺少 yaml 模块（python3-yaml）")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _cfg_cache[name] = data
    return data


def load_prompt(rel: str) -> str:
    """读取提示词模板（版本化、无密钥）。"""
    path = NEWSROOM / rel
    if not path.exists():
        raise FileNotFoundError(f"提示词不存在：{path}")
    return path.read_text(encoding="utf-8")


# ─────────────────────────── IO ───────────────────────────

def write_json_atomic(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def write_jsonl(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return n


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ─────────────────────────── 指纹 ───────────────────────────

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def short_hash(s: str, n: int = 16) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:n]


# ─────────────────────────── 日志 ───────────────────────────

_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
_MIN_LEVEL = _LEVELS.get(os.environ.get("NEICAN_LOG_LEVEL", "INFO").upper(), 20)


def log(msg: str, level: str = "INFO") -> None:
    """统一日志：只写 stdout。

    **不要在这里再写文件** —— 调用方（run/*.sh）已经把 stdout 重定向到日志文件，
    两边都写会导致每条日志出现两次（首跑实测踩到）。
    需要独立日志时由 shell 层决定，而不是由库层猜测。
    """
    if _LEVELS.get(level, 20) < _MIN_LEVEL:
        return
    line = f"[{bjnow().strftime('%Y-%m-%d %H:%M:%S')}] {level:<5} {msg}"
    print(line, flush=True)


# ─────────────────────────── 运行摘要 ───────────────────────────

class Run:
    """一次 run 的摘要记录 —— 回答"今天为什么只有 2 篇"必须是文件能回答的。"""

    def __init__(self, stage: str):
        self.stage = stage
        self.started = bjnow()
        self.metrics: dict = {}
        self.errors: list[str] = []
        self.cost_cny = 0.0

    def set(self, **kw) -> None:
        self.metrics.update(kw)

    def error(self, msg: str) -> None:
        self.errors.append(msg)
        log(msg, "ERROR")

    def finish(self, ok: bool = True) -> dict:
        ended = bjnow()
        rec = {
            "stage": self.stage,
            "started_at": iso(self.started),
            "ended_at": iso(ended),
            "duration_s": round((ended - self.started).total_seconds(), 2),
            "ok": ok and not self.errors,
            "metrics": self.metrics,
            "errors": self.errors,
            "cost_cny": round(self.cost_cny, 4),
        }
        ensure_dirs()
        hist = STATE_DIR / "runs" / f"{day_key()}.jsonl"
        hist.parent.mkdir(parents=True, exist_ok=True)
        with hist.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log(f"run 结束 stage={self.stage} ok={rec['ok']} {rec['duration_s']}s {self.metrics}")
        return rec
