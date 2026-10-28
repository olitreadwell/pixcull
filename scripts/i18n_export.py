#!/usr/bin/env python3
"""Write a translation kit CSV for one locale.

    python scripts/i18n_export.py --lang es_ES --out translations/es_ES.csv

Every row carries the Chinese source, the English pivot, where the string
lives, and whatever the locale already translates. A volunteer fills the
``target`` column. See docs/I18N.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pixcull.i18n import SUPPORTED_LOCALES, _normalize_lang
from pixcull.i18n_kit import load_entries, write_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", required=True,
                        help=f"target locale: {', '.join(SUPPORTED_LOCALES)}")
    parser.add_argument("--out", type=Path, default=None,
                        help="output CSV (default translations/<locale>.csv)")
    args = parser.parse_args(argv)

    lang = _normalize_lang(args.lang)
    if lang not in SUPPORTED_LOCALES:
        parser.error(f"unsupported locale {args.lang!r}; "
                     f"add it to SUPPORTED_LOCALES first")
    out = args.out or Path("translations") / f"{lang}.csv"
    entries = load_entries(lang)
    count = write_csv(entries, out)
    todo = sum(1 for entry in entries if entry.status == "todo")
    print(f"{out}: {count} strings, {count - todo} translated, {todo} todo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
