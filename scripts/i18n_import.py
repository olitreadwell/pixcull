#!/usr/bin/env python3
"""Write a filled translation kit back into the locale catalogues.

    python scripts/i18n_import.py translations/es_ES.csv --lang es_ES --check
    python scripts/i18n_import.py translations/es_ES.csv --lang es_ES

``--check`` validates only. Without it, the ``target`` column is written to
``pixcull/locale/pages/<locale>/`` and ``pixcull/locale/<locale>.json``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pixcull.i18n import _normalize_lang
from pixcull.i18n_kit import (
    apply_rows, load_entries, read_csv, validate_rows,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--lang", required=True)
    parser.add_argument("--check", action="store_true",
                        help="report problems without writing anything")
    args = parser.parse_args(argv)

    lang = _normalize_lang(args.lang)
    rows = read_csv(args.csv)
    entries = load_entries(lang, ROOT)
    problems = validate_rows(rows, entries)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        print(f"{len(problems)} problem(s); nothing written", file=sys.stderr)
        return 1
    if args.check:
        done = sum(1 for row in rows if (row.get("target") or "").strip())
        print(f"{args.csv}: {done} translated row(s), no problems")
        return 0
    written = apply_rows(rows, lang)
    print(f"wrote {written['strings']} strings across "
          f"{written['pages']} page catalogue(s) for {lang}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
