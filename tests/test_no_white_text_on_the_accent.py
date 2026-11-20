"""v3.104 — white text on the gold accent, wherever a page writes it.

`tests/test_text_on_accent_is_legible.py` measures the results page's
stylesheet in a browser. Review found what it cannot reach: a style that
JavaScript builds as a string (the active-learning "AL #N" badge, white on
champagne at 1.95:1), and the pages the server writes itself: their shared
primary-button rule was white on the champagne gradient, the history
page's demo button and the video-run call to action wrote white inline, and
the page templates under `templates/pages/` (upload, admin, tether,
verticals) had eight more. Those are text, so this reads them as text:
every declaration block, `style="…"` attribute and `cssText` string, with
JavaScript string concatenation joined first, so an attribute split across
`"…" +` lines is read whole.

Two rules. Text on an accent-family fill is never white. And text on a
*literal* champagne fill is never `var(--on-accent)`, because that token
turns white in the light theme while a literal stays champagne.

It runs without a browser, so the hermetic lane holds the line too. What it
cannot see is a background and a text colour set in different rules; the
browser test measures computed colour per rule and shares that limit.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "pixcull" / "report" / "templates"

#: An opaque accent-family background: the token ramp, the brand gradient,
#: the champagne ramp as literals, and champagne at 50% opacity or more.
_ACCENT_BG = re.compile(
    r"(?<![-\w])background(?:-color|-image)?\s*:\s*([^;{}]*?(?:"
    r"var\(--accent(?:-hi|-mid|-deep)?\)|var\(--brand-gradient\b"
    r"|#d5b584|#b5945f|#93743f|#eaca98|#d4a843"
    r"|rgba\(\s*213\s*,\s*181\s*,\s*132\s*,\s*(?:0?\.[5-9]\d*|1(?:\.0+)?)\s*\)"
    r")[^;{}]*)", re.I)
_LITERAL_CHAMPAGNE = re.compile(r"#d5b584|#b5945f|#93743f|#eaca98|#d4a843"
                                r"|rgba\(\s*213\s*,\s*181\s*,\s*132", re.I)
_TEXT = re.compile(r"(?<![-\w])color\s*:\s*([^;{}'\"`]+)", re.I)
#: White in each spelling CSS accepts: hex, the keyword, rgb() with commas
#: or spaces, hsl() at 100% lightness, and oklch()/oklab() at L = 1.
#: v3.104 recheck: the first cut knew only the comma form of rgb().
_WHITE = re.compile(
    r"^(?:#fff(?:f|fff|fffff)?\b|white\b"
    r"|rgba?\(\s*255\s*[, ]\s*255\s*[, ]\s*255\b"
    r"|hsla?\(\s*[\d.]+(?:deg)?\s*[, ]\s*[\d.]+%\s*[, ]\s*100%"
    r"|ok(?:lch|lab)\(\s*(?:1(?:\.0+)?|100%)\s)", re.I)


def _joined(text: str) -> str:
    """Python f-string braces undoubled, JS `"a" + "b"` glued to `"ab"`."""
    text = text.replace("{{", "{").replace("}}", "}")
    return re.sub(r"([\"'`])\s*\+\s*([\"'`])", "", text)


def _declaration_lists(text: str):
    """(line, declarations) for every place a colour can be declared."""
    t = _joined(text)
    line = lambda pos: t.count("\n", 0, pos) + 1  # noqa: E731
    for m in re.finditer(r"\{([^{}]*)\}", t):
        yield line(m.start()), m.group(1)
    for m in re.finditer(r"style\s*=\s*([\"'])(.*?)\1", t, re.S):
        yield line(m.start()), m.group(2)
    for m in re.finditer(r"cssText\s*=\s*\(?\s*([\"'`])(.*?)\1", t, re.S):
        yield line(m.start()), m.group(2)


def _violations(name: str, text: str, fixed_brand_gradient: bool = False):
    """``fixed_brand_gradient``: on the pages the server writes,
    `--brand-gradient` is champagne in both themes (only the results
    page derives it from the themed accent), so it counts as a literal."""
    out, seen = [], 0
    for ln, decls in _declaration_lists(text):
        bg = _ACCENT_BG.search(decls)
        if not bg:
            continue
        for colour in (c.strip() for c in _TEXT.findall(decls)):
            seen += 1
            if _WHITE.match(colour):
                out.append(f"{name}:~{ln}  white ({colour}) on {bg.group(1).strip()[:48]}")
            elif ("var(--on-accent" in colour
                  and ((_LITERAL_CHAMPAGNE.search(bg.group(1))
                        and "var(" not in bg.group(1))
                       or (fixed_brand_gradient
                           and "var(--brand-gradient" in bg.group(1)))):
                out.append(f"{name}:~{ln}  --on-accent on a literal champagne "
                           f"fill, white in the light theme: {bg.group(1).strip()[:48]}")
    return out, seen


def _sources() -> dict[str, str]:
    files = sorted((TEMPLATES / "src").rglob("*.css")) + \
        sorted((TEMPLATES / "src").rglob("*.js")) + \
        [TEMPLATES / "src" / "results.src.html"] + \
        sorted(p for p in TEMPLATES.rglob("*.html")
               if p.name != "results.html" and "src" not in p.parts) + \
        sorted((ROOT / "pixcull").rglob("*.py"))
    return {str(f.relative_to(ROOT)): f.read_text(encoding="utf-8") for f in files}


def test_no_page_writes_white_text_on_the_accent():
    bad, seen = [], 0
    for name, text in _sources().items():
        v, n = _violations(name, text,
                           fixed_brand_gradient="templates/src/" not in name)
        bad += v
        seen += n
    # Sentinel: the reader has to be finding the accent fills, or an empty
    # result would agree with anything.
    assert seen >= 25, f"only {seen} accent fills with a text colour found"
    assert not bad, ("text on the gold accent must be dark on champagne "
                     "(var(--on-accent) where the fill follows the theme, "
                     "#161616 where it is a fixed literal):\n  "
                     + "\n  ".join(bad))


def test_the_reader_sees_each_way_a_page_writes_a_colour():
    """One planted case per shape found in the product."""
    cases = {
        "css block": ".b { background: var(--accent); color: #fff; }",
        "f-string css": ".b {{ background: var(--brand-gradient) !important;"
                        " color: #ffffff !important; }}",
        "split style attribute": ("html = `<div style=\"position:absolute;\n"
                                  "  background:linear-gradient(90deg,#d5b584,#d5b584);\n"
                                  "  color:#fff;padding:2px\">AL</div>`;"),
        "concatenated style": ("x = \"<a style='background:#d5b584;\" +\n"
                               "    \"color:white'>go</a>\";"),
        "cssText": "el.style.cssText = \"background:rgba(213,181,132,0.85);color:#fff\";",
        "css in a js string": "s += \"#bar button.on{background:#d5b584;color:#fff}\";",
    }
    for white in ("#FFF", "#ffffffff", "rgb(255 255 255)", "rgba(255, 255, 255, 1)",
                  "hsl(0 0% 100%)", "hsl(0deg, 0%, 100%)", "oklch(1 0 0)",
                  "oklch(100% 0 0)", "WHITE"):
        cases[f"white as {white}"] = f".b {{ background: var(--accent); color: {white}; }}"
    for label, text in cases.items():
        v, _ = _violations(label, text)
        assert v, f"the reader missed white on the accent in a {label}"
    # And the two shapes that are right stay quiet.
    ok = (".b { background: var(--accent); color: var(--on-accent); }"
          ".c { background: rgba(213,181,132,0.85); color: #161616; }"
          ".t { background: var(--accent-soft); color: #fff; }")
    assert _violations("ok", ok)[0] == [], _violations("ok", ok)[0]
    flips = ".d { background: #d5b584; color: var(--on-accent); }"
    assert _violations("flips", flips)[0], (
        "--on-accent on a literal champagne fill turns white in the light "
        "theme and must be caught")
    server = ".e { background: var(--brand-gradient); color: var(--on-accent); }"
    assert _violations("server", server, fixed_brand_gradient=True)[0], (
        "the server pages' brand gradient is champagne in both themes")
    assert not _violations("results", server)[0], (
        "the results page's brand gradient follows the theme, so "
        "--on-accent is right there")
