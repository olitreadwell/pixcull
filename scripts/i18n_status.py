#!/usr/bin/env python3
"""Coverage per locale, and a CI gate.

    python scripts/i18n_status.py
    python scripts/i18n_status.py --min 90

Exits non-zero when a locale with any translations sits below ``--min``.
A locale with no catalogue at all is reported as ``0%`` and does not fail
unless it is named with ``--require``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pixcull.i18n import SUPPORTED_LOCALES
from pixcull.i18n_kit import coverage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min", type=int, default=0,
                        help="fail when a started locale is below this percent")
    parser.add_argument("--require", action="append", default=[],
                        help="locale that must also meet --min")
    args = parser.parse_args(argv)

    failures: list[str] = []
    for lang in SUPPORTED_LOCALES:
        if lang in ("zh_CN", "en_US"):
            continue
        pages = coverage(lang, ROOT)
        done = sum(v["done"] for v in pages.values())
        total = sum(v["total"] for v in pages.values())
        percent = (100 * done / total) if total else 0
        started = done > 0
        marker = ""
        if started and percent < args.min:
            marker = "  <-- below minimum"
            failures.append(f"{lang}: {percent:.0f}%")
        if lang in args.require and percent < args.min:
            if lang not in failures:
                failures.append(f"{lang}: {percent:.0f}%")
        print(f"{lang:6} {done:4}/{total:<4} {percent:5.1f}%{marker}")
    if failures:
        print(f"below {args.min}%: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
