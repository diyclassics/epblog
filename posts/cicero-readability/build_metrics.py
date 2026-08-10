"""Precompute the cached CSVs the post loads.

Extracts the python cells from index.qmd up to and including the `build` cell
and executes them, so this script cannot drift from the post it feeds. Run once
(~30 min for the full Cicero corpus); the post then renders from the CSVs.

    python build_metrics.py
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
QMD = HERE / "index.qmd"
STOP_AFTER = "build"

CELL = re.compile(r"^```\{python\}\n(.*?)^```", re.S | re.M)


def cells(text):
    for m in CELL.finditer(text):
        body = m.group(1)
        label = ""
        lines = []
        for line in body.splitlines():
            if line.startswith("#|"):
                if "label:" in line:
                    label = line.split("label:")[1].strip()
                continue
            lines.append(line)
        yield label, "\n".join(lines)


def main():
    import os

    smoke = int(os.environ.get("EP_SMOKE", "0"))
    ns = {"__name__": "__main__"}
    for label, code in cells(QMD.read_text()):
        print(f"[{label or '?'}] running…", flush=True)
        exec(compile(code, f"<{label}>", "exec"), ns)
        if label == "setup" and smoke:
            ns["FILES"] = ns["FILES"][:smoke]
            print(f"  SMOKE: limited to {len(ns['FILES'])} files")
        if label == STOP_AFTER:
            break
    print("\nwrote:")
    for p in ("cicero-metrics.csv", "cicero-hardest-sentences.csv"):
        f = HERE / p
        print(f"  {p}: {'OK' if f.exists() else 'MISSING'}")


if __name__ == "__main__":
    sys.exit(main())
