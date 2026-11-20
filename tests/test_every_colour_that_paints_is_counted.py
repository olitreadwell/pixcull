"""v3.104 — the colour count was off in both directions.

`scripts/lint_design_tokens.py` reports two numbers: *undesigned* (a hex in
no design token, ratcheted) and *unmigrated* (a token's value written as a
literal). The charter called the unmigrated half "mechanical". Measuring
it first showed the count itself was wrong, two ways at once.

**It counted colours that never paint.** 51 `var(--x, <colour>)`
fallbacks sat on properties declared in `:root`. A `var()` fallback is
used only when the property is undefined, and a `:root` property is
inherited by every element in both themes, so none of the 51 could ever
reach the screen. Twelve of them were colours nobody designed — a blue,
an emerald, a red from the purple-era palette — and they made up part of
the ratcheted number. Removing them changed nothing a user sees:
2,082 elements and pseudo-elements, both themes, computed paint compared
before and after, zero differences.

**It missed colours that do paint.** The scanner read three surfaces:
stylesheets, `style="…"` attributes and paint attributes. JavaScript
also writes CSS as text — `"#lbVideoBar button.on{background:#d5b584}"`,
or a `style='…` attribute split across concatenated lines that never
closes on one line — and 31 literals in `results.html` painted that way,
eleven of them undesigned.

The two errors nearly cancelled (−12 dead, +11 hidden), which is why the
number looked stable while describing the wrong set.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINTER = ROOT / "scripts" / "lint_design_tokens.py"
TEMPLATES = ROOT / "pixcull" / "report" / "templates"
SRC = TEMPLATES / "src"

#: A colour value as it can appear in a var() fallback.
_COLOUR = (r"(?:#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)"
           r"|oklch\([^)]*\))")
_FALLBACK = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*,\s*(" + _COLOUR + r")\s*\)")


def _lint():
    spec = importlib.util.spec_from_file_location("ldt104", LINTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _without_css_comments(text: str) -> str:
    # Blank rather than delete, so line numbers in messages stay true.
    return re.sub(r"/\*.*?\*/",
                  lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)


def _root_properties(text: str) -> set[str]:
    """Custom properties declared inside a `:root { … }` block.

    Parsed by brace depth, not by "`--x:` appears somewhere": a property
    set on `.lp-group > summary` or in a `style=` attribute is defined
    only there, and a fallback on it is live everywhere else.
    """
    text = _without_css_comments(text)
    found: set[str] = set()
    for m in re.finditer(r"\{", text):
        # The selector is whatever sits between the previous block or
        # declaration boundary and this brace. v3.104 review: the first
        # cut matched `:root` only when a brace followed it, so the
        # selector list `:root, html[data-theme="light"] {` declared
        # nothing.
        start = max(text.rfind(c, 0, m.start()) for c in "{};") + 1
        parts = [p.rsplit(">", 1)[-1].strip()
                 for p in text[start:m.start()].split(",")]
        if ":root" not in parts:
            continue
        i = j = m.end()
        depth = 1
        while depth and j < len(text):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        found |= set(re.findall(r"(--[A-Za-z0-9_-]+)\s*:", text[i:j]))
    return found


def _dead_fallbacks(sources: dict[str, str], root: set[str]) -> list[str]:
    out = []
    for name, text in sources.items():
        for m in _FALLBACK.finditer(text):
            if m.group(1) in root:
                line = text.count("\n", 0, m.start()) + 1
                out.append(f"{name}:{line}  {m.group(0)}")
    return out


def _results_sources() -> dict[str, str]:
    files = (sorted(SRC.rglob("*.css")) + sorted(SRC.rglob("*.js"))
             + [SRC / "results.src.html"])
    return {str(f.relative_to(ROOT)): f.read_text(encoding="utf-8")
            for f in files}


def test_no_colour_fallback_sits_on_a_property_every_element_inherits():
    """A fallback on a `:root` property never paints, in either theme.

    It still reads as a colour decision, still counts in the linter, and
    still tells the next person editing the rule that `#10b981` is what
    `--c-success` looks like when it has been `#63bd7f` since v2.21."""
    sources = _results_sources()
    root = set()
    for name, text in sources.items():
        if name.endswith((".css", ".html")):
            root |= _root_properties(text)
    # Sentinel: the parser must actually be reading tokens.css. If it
    # found nothing, every fallback would look live and this would pass.
    assert {"--accent", "--surface-2", "--c-success", "--keep"} <= root, (
        f"the :root parser found only {len(root)} properties")
    assert len(root) >= 60, len(root)

    dead = _dead_fallbacks(sources, root)
    for page in ("video_review.html", "timeline.html"):
        text = (TEMPLATES / page).read_text(encoding="utf-8")
        dead += _dead_fallbacks({page: text}, _root_properties(text))
    assert not dead, (
        "these var() fallbacks can never paint — the property is declared "
        "in :root, so every element inherits a value. Drop the fallback:\n  "
        + "\n  ".join(dead))


def test_the_fallback_check_can_see_one(tmp_path):
    """The check above, pointed at a planted case and at its look-alike."""
    css = (":root{--a:#111111}\n"
           ".x{color:var(--a, #222222)}\n"          # dead: --a is :root
           ".y{--b:#333333}\n"
           ".z{color:var(--b, #444444)}\n")         # live: --b is scoped
    root = _root_properties(css)
    assert root == {"--a"}, root
    dead = _dead_fallbacks({"t.css": css}, root)
    assert len(dead) == 1 and "#222222" in dead[0], dead
    # A commented-out :root declares nothing.
    assert _root_properties("/* :root{--c:#555555} */") == set()
    # :root first in a selector list, last in one, and inside @media.
    assert _root_properties(':root, html[data-theme="light"] {--d:#1}') == {"--d"}
    assert _root_properties("html, :root {--e:#1}") == {"--e"}
    assert _root_properties("@media (min-width:1px){ :root{--f:#1} }") == {"--f"}
    # Not :root: a theme-only block, and a selector that merely contains it.
    assert _root_properties('html[data-theme="light"] {--g:#1}') == set()
    assert _root_properties(".x :root-ish {--h:#1}") == set()


def test_the_scanner_reads_css_that_javascript_writes(tmp_path):
    """The third surface. Each line here is a shape found in results.html."""
    mod = _lint()
    p = tmp_path / "t.html"
    p.write_text(
        "<body><p>issue #123456 is text, not paint</p>\n"
        "<script>\n"
        '  css = "#bar button.on{background:#a1b2c3;color:#fff}";\n'
        "  html = \"<div style='font-weight:600;color:#c4d5e6;\" +\n"
        "         \"margin:0'>\";\n"
        '  _bar("V1", v1, max, "#0d0e0f");\n'
        "  // a colour named in a comment paints nothing: #9a9b9c\n"
        "  /* nor in a block comment: #8a8b8c\n"
        "     spanning lines #7a7b7c */ x = 1;\n"
        "  u = 'https://example.test/'; c = \"#d1d2d3\";\n"
        '  s += \'<path stroke="#445566"/>\';\n'
        "</script>\n"
        "<p>#556677 after the script is text again</p></body>\n",
        encoding="utf-8")
    found = {}
    for _ln, h, k in mod._scan(p):
        found.setdefault(h.lower(), []).append(k)

    assert found.get("#a1b2c3") == ["script"], found
    assert found.get("#c4d5e6") == ["script"], (
        f"a style= attribute split across concatenated lines: {found}")
    assert found.get("#0d0e0f") == ["script"], found
    assert found.get("#445566") == ["paint"], (
        f"a paint attribute keeps its kind and is not counted twice: {found}")
    for silent in ("#9a9b9c", "#8a8b8c", "#7a7b7c"):
        assert silent not in found, f"{silent} is in a comment: {found}"
    for text in ("#123456", "#556677"):
        assert text not in found, f"{text} is page text, not script: {found}"
    assert "#fff" not in found, "sanctioned primitives stay sanctioned"
    # `//` inside a URL does not start a comment; if it did, every
    # colour after a link on the same line would vanish.
    assert found.get("#d1d2d3") == ["script"], found


def test_the_scanner_reads_script_the_way_a_browser_does(tmp_path):
    """Edge cases the v3.104 review reproduced against the first cut."""
    mod = _lint()
    p = tmp_path / "t.html"
    p.write_text(
        "<script>\n"
        '  a = "see //docs then #a1a1a1";\n'        # // inside a string
        "  b = `first line\n"
        "  #b2b2b2 // still the template literal\n"
        "  `; // #c3c3c3 is a comment\n"
        "</script>\n"
        '<script type="application/json">{"brand": "#d4d4d4"}</script>\n'
        '<script type="module">m = "#e5e5e5";</script>\n'
        "<script>\n"
        '  s = "</script>"; t = "#f6f6f6";\n'       # ends the element here
        "</script>\n",
        encoding="utf-8")
    found = {h.lower() for _ln, h, k in mod._scan(p) if k == "script"}
    assert {"#a1a1a1", "#b2b2b2", "#e5e5e5"} <= found, found
    assert "#c3c3c3" not in found, "a comment after a template literal"
    assert "#d4d4d4" not in found, (
        "a JSON data block is not script; nothing in it paints")
    # The HTML tokenizer closes a script at the first </script>, string or
    # not, so what follows on that line is page text to a browser too.
    assert "#f6f6f6" not in found, found


def test_the_shipped_page_has_its_script_paint_counted():
    """On the real template, because that is where the 31 were."""
    mod = _lint()
    vs = mod._scan(TEMPLATES / "results.html")
    script = [h.lower() for _ln, h, k in vs if k == "script"]
    assert len(script) >= 25, (
        f"the scanner finds {len(script)} colours in results.html's "
        "scripts; there were 31 when this was written")
    # The lightbox video bar writes its stylesheet from JavaScript.
    assert "#9aa0aa" in script, script
