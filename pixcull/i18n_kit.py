"""Export and import translation kits.

Chinese is the source language. A kit is a CSV with one row per string:

    id,page,zh,en,context,file,line,status,<locale>

``zh`` is the source. ``en`` is the pivot, so a translator who does not
read Chinese can work from English. ``file`` and ``line`` say where the
string lives. ``status`` is ``done`` or ``todo`` for the target column.

The kit does not change the runtime. It reads the English catalogues
that already exist and writes a per-locale catalogue the existing loader
picks up.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

WORKSPACE_PAGE = "_workspace"
TARGET_COLUMN = "target"
FIELDS = ("id", "page", "zh", "en", "context", "file", "line",
          "status", TARGET_COLUMN)

_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


@dataclass(frozen=True)
class Entry:
    id: str
    page: str
    zh: str
    en: str
    context: str
    file: str
    line: int
    status: str = "todo"
    target: str = ""


def _repo_root(root: Path | None = None) -> Path:
    """Where the catalogues live. Defaults to the working directory, so
    the module never builds a path that climbs out of an installed
    package; the scripts pass the checkout root explicitly."""
    return Path(root) if root is not None else Path.cwd()


def _string_id(page: str, zh: str) -> str:
    """Advisory identifier. Rows are matched on ``(page, zh)``; this only
    gives a spreadsheet a stable-looking handle."""
    digest = hashlib.sha1(zh.encode("utf-8")).hexdigest()[:10]
    return f"{page}:{digest}"


def _page_titles(templates: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    for path in templates.rglob("*.html"):
        text = path.read_text("utf-8", errors="ignore")
        found = re.search(r"<title>(.*?)</title>", text, re.S)
        if found:
            titles[path.stem] = found.group(1).strip()
    return titles


def _locations(templates: Path, server: Path) -> tuple[list[tuple[str, str]], str]:
    """Text of every searchable file, so a source string can be located.

    Returns ``[(path, content)]``; call :func:`_find` to locate one
    string. Reading each file once keeps the export linear in file size
    instead of linear in strings times lines.
    """
    files: list[tuple[str, str]] = []
    for path in sorted(templates.rglob("*")):
        if path.suffix in (".html", ".js"):
            files.append((str(path), path.read_text("utf-8", errors="ignore")))
    if server.exists():
        files.append((str(server),
                      server.read_text("utf-8", errors="ignore")))
    return files, ""


def _find(files: list[tuple[str, str]], needle: str,
          prefer: str = "") -> tuple[str, int]:
    ordered = sorted(files, key=lambda item: 0 if prefer
                     and Path(item[0]).stem == prefer else 1)
    for path, content in ordered:
        index = content.find(needle)
        if index >= 0:
            return path, content.count("\n", 0, index) + 1
    return "", 0


def load_entries(lang: str = "en_US", root: Path | None = None) -> list[Entry]:
    """Every translatable string, with its English pivot and location."""
    base = _repo_root(root)
    templates = base / "pixcull" / "report" / "templates"
    server = base / "pixcull" / "report" / "serve_app.py"
    titles = _page_titles(templates)
    files, _ = _locations(templates, server)

    existing = _load_target(lang, base)
    entries: list[Entry] = []

    workspace = base / "pixcull" / "locale" / "en_US.json"
    if workspace.exists():
        for key, value in json.loads(workspace.read_text("utf-8")).items():
            target = existing["workspace"].get(key, "")
            entries.append(Entry(
                id=key, page=WORKSPACE_PAGE, zh=key, en=value,
                context="review workspace string", file=str(workspace),
                line=_line_of(workspace, key), status=_status(target),
                target=target,
            ))

    pages = base / "pixcull" / "locale" / "pages" / "en_US"
    if pages.is_dir():
        for path in sorted(pages.glob("*.json")):
            page = path.stem
            for zh, en in json.loads(path.read_text("utf-8")).items():
                target = existing["pages"].get(page, {}).get(zh, "")
                location = _find(files, zh, prefer=page)
                entries.append(Entry(
                    id=_string_id(page, zh), page=page, zh=zh, en=en,
                    context=titles.get(page, page), file=location[0],
                    line=location[1], status=_status(target), target=target,
                ))
    return entries


def _line_of(path: Path, needle: str) -> int:
    try:
        for number, line in enumerate(
                path.read_text("utf-8", errors="ignore").splitlines(), 1):
            if needle in line:
                return number
    except OSError:
        pass
    return 0


def _status(target: str) -> str:
    return "done" if target.strip() else "todo"


def _load_target(lang: str, base: Path) -> dict:
    out = {"workspace": {}, "pages": {}}
    workspace = base / "pixcull" / "locale" / f"{lang}.json"
    if workspace.exists() and lang != "en_US":
        out["workspace"] = json.loads(workspace.read_text("utf-8"))
    pages = base / "pixcull" / "locale" / "pages" / lang
    if pages.is_dir():
        for path in pages.glob("*.json"):
            out["pages"][path.stem] = json.loads(path.read_text("utf-8"))
    return out


def write_csv(entries: list[Entry], out: Path) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "id": entry.id, "page": entry.page, "zh": entry.zh,
                "en": entry.en, "context": entry.context,
                "file": entry.file, "line": entry.line,
                "status": entry.status, TARGET_COLUMN: entry.target,
            })
    return len(entries)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_rows(rows: list[dict[str, str]],
                  entries: list[Entry]) -> list[str]:
    """Problems that would produce a broken or dishonest catalogue."""
    known = {(entry.page, entry.zh) for entry in entries}
    problems: list[str] = []
    for number, row in enumerate(rows, 2):
        page = (row.get("page") or "").strip()
        zh = row.get("zh") or ""
        target = (row.get(TARGET_COLUMN) or "").strip()
        if not target:
            continue
        if (page, zh) not in known:
            problems.append(f"row {number}: unknown string for page {page!r}")
        if target == zh:
            problems.append(f"row {number}: target is still the Chinese source")
        lowered = target.lower()
        if "</script" in lowered or "<!--" in target:
            problems.append(f"row {number}: target would break the page script")
    return problems


def apply_rows(rows: list[dict[str, str]], lang: str,
               root: Path | None = None) -> dict[str, int]:
    """Write the target column into the per-locale catalogues."""
    base = _repo_root(root)
    pages: dict[str, dict[str, str]] = {}
    workspace: dict[str, str] = {}
    written = 0
    for row in rows:
        target = (row.get(TARGET_COLUMN) or "").strip()
        if not target:
            continue
        page = (row.get("page") or "").strip()
        if page == WORKSPACE_PAGE:
            workspace[row["id"]] = target
        else:
            pages.setdefault(page, {})[row["zh"]] = target
        written += 1

    if workspace:
        path = base / "pixcull" / "locale" / f"{lang}.json"
        path.write_text(
            json.dumps(workspace, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    for page, catalogue in pages.items():
        folder = base / "pixcull" / "locale" / "pages" / lang
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{page}.json").write_text(
            json.dumps(catalogue, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    return {"strings": written, "pages": len(pages)}


def coverage(lang: str, root: Path | None = None) -> dict[str, dict[str, int]]:
    """Per-page counts of translated and total strings for one locale."""
    base = _repo_root(root)
    entries = load_entries(lang, base)
    per_page: dict[str, dict[str, int]] = {}
    for entry in entries:
        bucket = per_page.setdefault(entry.page, {"done": 0, "total": 0})
        bucket["total"] += 1
        if entry.status == "done":
            bucket["done"] += 1
    return per_page
