# -*- coding: utf-8 -*-
"""生产线编排器（L0 → L1）。

    fetch ──► cluster ──► classify ──► score ──► select
    信源      Event       相关性闸      五维分     配额分流

为什么编排是脚本而不是工作流引擎：
  链路需要的性质（确定性、可重放、便宜、可并发）与工作流引擎/agent 的性质
  （会话式、非线性、有状态）在数学上不兼容（设计文档 §11、§16.4）。
  把判断放进 cron，等于把不确定性放到唯一有发布权的通道上。

用法：
    python3 -m src.pipeline                 # 全链路
    python3 -m src.pipeline --stage select  # 只跑某一阶段
    python3 -m src.pipeline --from cluster  # 从某阶段起
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lib import common as C          # type: ignore
    import fetch as _fetch               # type: ignore
    import cluster as _cluster           # type: ignore
    import classify as _classify         # type: ignore
    import score as _score               # type: ignore
    import select as _select             # type: ignore
else:
    from .lib import common as C
    from . import fetch as _fetch
    from . import cluster as _cluster
    from . import classify as _classify
    from . import score as _score
    from . import select as _select

STAGES = ["fetch", "cluster", "classify", "score", "select"]
STAGE_FN = {
    "fetch": lambda day: _fetch.run(day),
    "cluster": lambda day: _cluster.run(day),
    "classify": lambda day: _classify.run(day),
    "score": lambda day: _score.run(day),
    "select": lambda day: _select.run(day),
}


def run(day: str | None = None, only: str | None = None, start: str | None = None) -> int:
    C.ensure_dirs()
    day = day or C.day_key()

    if only:
        stages = [only]
    elif start:
        stages = STAGES[STAGES.index(start):]
    else:
        stages = STAGES

    C.log(f"═══ 生产线启动 day={day} stages={','.join(stages)} ═══")
    rc = 0
    for st in stages:
        C.log(f"─── 阶段：{st} ───")
        try:
            STAGE_FN[st](day)
        except Exception as e:
            C.log(f"阶段 {st} 异常：{type(e).__name__}: {e}", "ERROR")
            C.log(traceback.format_exc(), "DEBUG")
            rc = 1
            break
    C.log(f"═══ 生产线结束 rc={rc} ═══")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="neican.ai 生产线编排器")
    ap.add_argument("--day", default=None)
    ap.add_argument("--stage", default=None, choices=STAGES, help="只跑某一阶段")
    ap.add_argument("--from", dest="start", default=None, choices=STAGES, help="从某阶段起跑到末尾")
    a = ap.parse_args()
    return run(a.day, a.stage, a.start)


if __name__ == "__main__":
    raise SystemExit(main())
