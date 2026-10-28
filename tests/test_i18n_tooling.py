"""Translation kits: export, validate, import, coverage.

Chinese stays the source. Each row carries the English pivot, the file
and line the string came from, and the target column a volunteer fills.
"""

from __future__ import annotations

import json

from pixcull.i18n_kit import (
    TARGET_COLUMN, apply_rows, coverage, load_entries, read_csv,
    validate_rows, write_csv,
)


def _fixture(root):
    (root / "pixcull" / "locale" / "pages" / "en_US").mkdir(parents=True)
    (root / "pixcull" / "locale").mkdir(parents=True, exist_ok=True)
    (root / "pixcull" / "locale" / "en_US.json").write_text(
        json.dumps({"decision.keep": "Keep"}, ensure_ascii=False))
    (root / "pixcull" / "locale" / "pages" / "en_US" / "upload.json").write_text(
        json.dumps({"保留": "Keep", "开始分析": "Start analysis"},
                   ensure_ascii=False))
    templates = root / "pixcull" / "report" / "templates" / "pages"
    templates.mkdir(parents=True)
    (templates / "upload.html").write_text(
        "<html><title>Upload</title>保留 开始分析</html>")
    return root


def _rows(entries, target=""):
    return [{
        "id": e.id, "page": e.page, "zh": e.zh, "en": e.en,
        "context": e.context, "file": e.file, "line": str(e.line),
        "status": "done" if target else e.status, TARGET_COLUMN: target,
    } for e in entries]


def test_export_carries_source_pivot_and_location(tmp_path):
    root = _fixture(tmp_path)
    entries = load_entries("en_US", root)
    out = tmp_path / "kit.csv"
    assert write_csv(entries, out) == len(entries) == 3

    rows = read_csv(out)
    assert {row["zh"] for row in rows} == {"保留", "开始分析", "decision.keep"}
    assert {row["en"] for row in rows} == {"Keep", "Start analysis"}
    upload = [row for row in rows if row["page"] == "upload"]
    assert all(row["file"].endswith("upload.html") for row in upload)
    assert all(row["line"] == "1" for row in upload)


def test_import_writes_only_the_target_locale(tmp_path):
    root = _fixture(tmp_path)
    entries = load_entries("en_US", root)
    rows = _rows(entries, target="Garder")
    result = apply_rows(rows, "fr_FR", root)

    assert result["strings"] == 3
    page = json.loads(
        (root / "pixcull" / "locale" / "pages" / "fr_FR" / "upload.json")
        .read_text("utf-8"))
    assert page == {"保留": "Garder", "开始分析": "Garder"}
    assert json.loads(
        (root / "pixcull" / "locale" / "fr_FR.json").read_text("utf-8")
    ) == {"decision.keep": "Garder"}
    # The source locale is untouched.
    assert json.loads(
        (root / "pixcull" / "locale" / "pages" / "en_US" / "upload.json")
        .read_text("utf-8"))["保留"] == "Keep"


def test_validation_rejects_dishonest_or_breaking_rows(tmp_path):
    root = _fixture(tmp_path)
    entries = load_entries("en_US", root)
    rows = _rows(entries, target="ok")
    rows[0][TARGET_COLUMN] = rows[0]["zh"]          # still Chinese
    rows[1][TARGET_COLUMN] = "</script>"            # would break the page
    rows[2]["page"] = "nope"                        # unknown page

    problems = validate_rows(rows, entries)
    assert len(problems) == 3
    assert any("Chinese source" in p for p in problems)
    assert any("break the page script" in p for p in problems)
    assert any("unknown string" in p for p in problems)


def test_empty_target_rows_are_allowed_and_skipped(tmp_path):
    root = _fixture(tmp_path)
    entries = load_entries("en_US", root)
    rows = _rows(entries, target="")
    rows[0][TARGET_COLUMN] = "Garder"

    assert validate_rows(rows, entries) == []
    assert apply_rows(rows, "fr_FR", root)["strings"] == 1


def test_coverage_counts_done_and_total(tmp_path):
    root = _fixture(tmp_path)
    (root / "pixcull" / "locale" / "pages" / "fr_FR").mkdir(parents=True)
    (root / "pixcull" / "locale" / "pages" / "fr_FR" / "upload.json").write_text(
        json.dumps({"保留": "Garder"}, ensure_ascii=False))
    (root / "pixcull" / "locale" / "fr_FR.json").write_text(
        json.dumps({"decision.keep": "Garder"}, ensure_ascii=False))

    pages = coverage("fr_FR", root)
    assert pages["upload"] == {"done": 1, "total": 2}
    assert pages["_workspace"] == {"done": 1, "total": 1}
