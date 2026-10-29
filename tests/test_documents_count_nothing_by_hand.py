"""v3.100 — a count written by hand is wrong by the next release.

The README said "614 tests passing" (a v0.10 figure), "1,200+ tests across
88 files" and, in its Chinese half, "240+ 用例" — three counts in one file,
none true. `CONTRIBUTING.md` said 240+ and about a minute, and its paths
pointed at the server where it lived before v2.31. When these were removed
there were well over three thousand tests in more than 250 files.

Nothing kept any of them true, and nothing can keep a hand-written total
true for longer than a release. So a public document does not state how
many tests there are; `pytest --collect-only -q` does. And the contributor
guide's paths and "this name lives in that file" pointers are checked
against the tree, because those are what a first contributor follows.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PUBLIC = ("README.md", "modelscope/README.md", "README-PYPI.md",
          "CONTRIBUTING.md", "docs/USER-GUIDE.md")

#: A suite total, in either language: "614 tests passing", "1,200+ tests",
#: "(240+ tests", "614 个测试通过", "240+ 用例". A sentence about an event
#: ("seven tests caught it") is written in words and is not a total.
_TOTALS = [
    re.compile(r"\b\d[\d,]*\+?\s+(?:unit\s+)?tests?\s+(?:passing|pass|across|green)\b", re.I),
    re.compile(r"\b\d[\d,]*\+\s*(?:unit\s+)?tests?\b", re.I),
    re.compile(r"\(\s*\d[\d,]*\+?\s*(?:unit\s+)?tests?\b", re.I),
    re.compile(r"\d[\d,]*\+?\s*个?(?:测试|用例)\s*(?:通过|全绿)"),
    re.compile(r"\d[\d,]*\+\s*个?(?:测试|用例)"),
    re.compile(r"[(（]\s*\d[\d,]*\+?\s*个?(?:测试|用例)"),
]


def _totals(text: str) -> list[str]:
    return [m.group(0) for p in _TOTALS for m in p.finditer(text)]


def test_no_public_document_states_how_many_tests_there_are():
    for rel in PUBLIC:
        found = _totals((ROOT / rel).read_text(encoding="utf-8"))
        assert not found, f"{rel} states a test count by hand: {found}"


def test_the_patterns_read_what_was_there():
    """The counts that were in the documents, so the patterns cannot rot."""
    for s in ("(614 tests passing, 7 charters shipped)", "(1,200+ tests across 88 files)",
              "pytest -q   # 240+ tests, ~60 s", "(614 个测试通过、7 个 charter", "(240+ 用例)"):
        assert _totals(s), s
    for s in ("Seven tests caught it in CI", "a test now fails if", "Fourteen mutations",
              "tests/test_packaging.py", "on 394 blind frames"):
        assert not _totals(s), s


# ------------------------------------------------- the contributor guide

#: A backticked repo path: starts at a top-level directory of the repo.
_PATH = re.compile(r"`((?:pixcull|scripts|tests|docs|mobile|modelscope)/[^`\s]*)`")
#: "`NAME` in `path`" and "`NAME`-style label in `path`", across a line
#: break: the guide is hard-wrapped, and the first version of this pattern
#: missed the second pair because "-style" ended a line (v3.100 review).
_NAME_IN = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`(?:-style\s+label)?\s+in\s+`([^`\s]+)`")


def _contributing() -> str:
    return (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")


def test_every_path_the_contributor_guide_names_exists():
    paths = _PATH.findall(_contributing())
    assert paths, "the guide names no repository path; this check reads nothing"
    missing = []
    for p in paths:
        hits = list(ROOT.glob(p)) if "*" in p else [ROOT / p]
        if not hits or not all(h.exists() for h in hits):
            missing.append(p)
    assert not missing, f"CONTRIBUTING.md names paths that do not exist: {missing}"


def test_every_name_it_places_in_a_file_is_in_that_file():
    """`_CULL_REASONS` in `scripts/serve_demo.py`: the file exists, as a
    one-line forwarder, and the name moved with the server in v2.31."""
    pairs = _NAME_IN.findall(_contributing())
    assert pairs, "the guide places no name in a file; this check reads nothing"
    wrong = [(n, p) for n, p in pairs
             if not (ROOT / p).is_file() or n not in (ROOT / p).read_text(encoding="utf-8")]
    assert not wrong, f"CONTRIBUTING.md places names in files that do not hold them: {wrong}"



# ------------------------------- counts the code defines (v3.100 review)
#
# The review that checked the fixes above swept the same documents for the
# same defect and found three more: "9 verticals" against the ten in
# `pixcull/verticals.py`, with four of the nine names belonging to no
# vertical at all; "27 actions across 7 groups" for a palette with six
# groups unless the user has made view presets or buckets; and a training
# file's row count. A count the code defines is checked against the code;
# a count that depends on the user's data is not written.


def _without_whats_new(text: str) -> str:
    """What's new retells old sentences on purpose; it is not a claim."""
    return re.sub(r"\n## (?:What's new|最近更新)\n[\s\S]*?(?=\n## )", "\n", text)


def _public(rel: str) -> str:
    return _without_whats_new((ROOT / rel).read_text(encoding="utf-8"))


def test_the_vertical_count_is_the_code_s():
    from pixcull.verticals import VERTICALS
    n = len(VERTICALS)
    pats = [re.compile(r"\b(\d+) (?:per-genre )?verticals\b"),
            re.compile(r"(\d+) 种 ?(?:vertical|细分领域)")]
    for rel in PUBLIC:
        found = [int(m.group(1)) for p in pats for m in p.finditer(_public(rel))]
        assert all(v == n for v in found), f"{rel} counts the verticals as {found}; the code has {n}"
        if rel in ("README.md", "modelscope/README.md"):
            assert found, f"{rel} no longer counts the verticals; this check reads nothing"


def test_the_verticals_named_are_the_code_s():
    """The README named wedding, wildlife, sports, landscape, portrait,
    event, journalism, commercial and still-life; the code's ten include
    no portrait, journalism, commercial or still-life."""
    from pixcull.verticals import VERTICALS
    en = re.search(r"\*\*Per-genre verticals\.\*\*([^.]*)\.", _public("README.md"))
    assert en, "the English feature entry moved"
    names = en.group(1).lower()
    stems = {"kids": "kid", "pet": "pet", "event": "event", "sports": "sport", "bird": "bird"}
    missing = [v.key for v in VERTICALS if stems.get(v.key, v.key) not in names]
    assert not missing, f"README.md's vertical list leaves out {missing}"
    zh_lists = [
        re.search(r"种细分领域 \(verticals\)。\*\*([^。]*)。", _public("README.md")),
        re.search(r"种细分领域 \(verticals\)\*\* —— (.*)", _public("modelscope/README.md")),
    ]
    for m in zh_lists:
        assert m, "a Chinese feature entry moved"
        missing = [v.zh for v in VERTICALS if v.zh.removesuffix("摄影") not in m.group(1)]
        assert not missing, f"a Chinese vertical list leaves out {missing}"


def _palette_actions() -> int:
    src = (ROOT / "pixcull/report/templates/src/modules/26-cmdk-palette.js").read_text(encoding="utf-8")
    body = src.split("function _cmdkStaticActions", 1)[1].split("function ", 1)[0]
    return len(re.findall(r'\{\s*id:\s*"', body))


def test_the_palette_is_counted_from_the_code():
    n = _palette_actions()
    assert n >= 10, f"read {n} palette actions; the parse is broken, not the palette"
    for rel in PUBLIC:
        lines = _public(rel).splitlines()
        near = [" ".join(lines[i:i + 4]) for i, l in enumerate(lines)
                if re.search(r"⌘K|Cmd\+K|command palette|命令面板", l)]
        text = "\n".join(near)
        stated = [int(x) for x in re.findall(r"\b(\d+)\s*(?:个\s*)?(?:actions?|commands)\b", text)]
        assert all(v == n for v in stated), f"{rel} counts the palette as {stated}; the code has {n}"
        groups = re.findall(r"\b\d+\s*(?:个\s*)?groups?\b", text)
        assert not groups, (f"{rel} counts the palette's groups ({groups}); two of them "
                            f"exist only once the user has made view presets or buckets")
