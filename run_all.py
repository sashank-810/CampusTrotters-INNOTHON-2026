"""Reproduce every derived table, model output, figure and report from the shipped data.

    python run_all.py

Network access is NOT required: all supplementary data are shipped in data/external with
provenance in data/external/SOURCE_MANIFEST.csv.
"""
from __future__ import annotations

import json
import platform
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import scipy

from src import allocation, audit, config as C, figures, forecast, prepare, report, scenarios


def main() -> int:
    t0 = time.time()
    log = {"started_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0],
           "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__,
           "scipy": scipy.__version__, "steps": {}}
    for name, fn in [("prepare", prepare.main), ("audit", audit.main), ("forecast", forecast.main),
                     ("scenarios", scenarios.main), ("allocation", allocation.main), ("figures", figures.main), ("report", report.main)]:
        t = time.time()
        res = fn()
        log["steps"][name] = {"seconds": round(time.time() - t, 2),
                              "result": res if isinstance(res, dict) and len(json.dumps(res, default=str)) < 4000 else "ok"}
    log["total_seconds"] = round(time.time() - t0, 2)
    (C.OUTPUTS / "run_log.json").write_text(json.dumps(log, indent=2, default=str))
    print(f"[run_all] completed in {log['total_seconds']} s -> outputs/run_log.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
