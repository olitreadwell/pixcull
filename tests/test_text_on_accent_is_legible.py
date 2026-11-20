"""v3.104 — the main call to action failed contrast in the default theme.

Every primary button, active pill and selected chip wrote white text on the
accent. In the dark theme, which is the default, the accent is champagne
`#d5b584`, and white on it is 1.95:1. WCAG asks 4.5:1 for text; this was
less than half. The light theme's accent is deep bronze, where white is
right, and the one rule that had dark text (the burst-stack badge) was
2.42:1 there instead. A single colour cannot be right on both, so v3.104
adds `--on-accent`: `#161616` on champagne, white on bronze.

Measured in a browser, not read from the source, because the colours are
computed (`oklch(from var(--accent) …)`) and the second theme runs the same
arithmetic from a different base. Every stylesheet rule that paints an
accent-family background and sets a text colour is checked, so a new
button written the old way fails here without anyone listing it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "pixcull" / "report" / "templates"

#: Label text sits in the middle of a button, so the gradient's mean is
#: what it is read against; a stop is a corner of a 135° gradient, held to
#: the 3:1 WCAG gives large text and UI components.
TEXT_MIN = 4.5
STOP_MIN = 3.0
#: At or above this opacity a background is an accent fill, not a tint.
FILL_ALPHA = 0.5

#: Accent-coloured text on an accent *tint*, light theme, measured below
#: 4.5:1 (4.11–4.48) when v3.104 fixed the fills. A different defect —
#: the text colour, not the fill — and a visible change of its own, so it
#: is recorded rather than fixed here. The check below fails if this list
#: grows, and if an entry is fixed without being taken off it.
KNOWN_TINT_SHORTFALLS = {
    "light": {
        ".tuned-badge", ".presence-pill", ".stats .vertical-badge",
        ".cluster-divider .compare-btn", ".row1 .style-chip",
        ".filters button.export-btn:hover", ".row1 .rs.meta",
        ".chip--brand", ".row1 .moment-chip", ".onboard-tip .onb-dismiss",
        ".scene-anomaly-banner", ".shortcuts-ctx-badge",
        ".lightbox .info-pane .style-tag",
    },
}

_COLLECT = r"""(theme) => {
  if (theme === 'light') document.documentElement.setAttribute('data-theme', 'light');
  else document.documentElement.removeAttribute('data-theme');
  const probe = document.createElement('div');
  document.body.appendChild(probe);
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const g = cv.getContext('2d', {willReadFrequently: true});
  const rgba = c => { g.clearRect(0, 0, 1, 1); g.fillStyle = '#000'; g.fillStyle = c;
                      g.fillRect(0, 0, 1, 1); return Array.from(g.getImageData(0, 0, 1, 1).data); };
  probe.style.background = 'var(--bg)';
  const ground = rgba(getComputedStyle(probe).backgroundColor);
  const ACCENT = /--accent|--brand-gradient|213,\s*181,\s*132/;
  const STOP = /(?:rgba?|oklch|color|hsla?|lab|lch)\([^()]*(?:\([^()]*\)[^()]*)*\)|#[0-9a-fA-F]{3,8}/g;
  const out = [];
  const live = r => {
    if (r instanceof CSSSupportsRule) return CSS.supports(r.conditionText);
    if (r instanceof CSSMediaRule) return matchMedia(r.conditionText).matches;
    return true;
  };
  const walk = rules => { for (const r of rules) {
    if (!live(r)) continue;
    if (r instanceof CSSStyleRule) {
      const bg = r.style.getPropertyValue('background') || r.style.getPropertyValue('background-color')
              || r.style.getPropertyValue('background-image');
      const fg = r.style.getPropertyValue('color');
      if (bg && fg && ACCENT.test(bg) && !/^(inherit|currentcolor|transparent)$/i.test(fg.trim())) {
        probe.style.cssText = '';
        probe.style.background = bg; probe.style.color = fg;
        const cs = getComputedStyle(probe);
        const stops = (cs.backgroundImage.match(STOP) || []).map(rgba);
        const flat = rgba(cs.backgroundColor);
        out.push({sel: r.selectorText, fg: rgba(cs.color),
                  stops: stops.length ? stops : (flat[3] ? [flat] : [])});
      }
    }
    if (r.cssRules) walk(r.cssRules);
  } };
  for (const s of document.styleSheets) { try { walk(s.cssRules); } catch (e) {} }
  probe.remove();
  return {ground, rules: out};
}"""


def _lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def _ratio(a, b):
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _over(c, ground):
    """A translucent fill composited on the page ground."""
    a = c[3] / 255
    return [c[i] * a + ground[i] * (1 - a) for i in range(3)]


def measure(page: Path, themes=("dark", "light")):
    """{theme: [(selector, text-vs-mean, worst-stop, alpha)]} for one page.

    ``alpha`` is the most transparent stop: an accent *fill* is opaque or
    nearly so; a *tint* (`--accent-soft`, 10–16%) is mostly page ground.
    """
    from playwright.sync_api import sync_playwright
    res = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:")
                 else r.abort())
        pg.goto(page.resolve().as_uri(), wait_until="domcontentloaded",
                timeout=120_000)
        for theme in themes:
            got = pg.evaluate(_COLLECT, theme)
            rows = []
            for r in got["rules"]:
                if not r["stops"]:
                    continue
                stops = [_over(s, got["ground"]) for s in r["stops"]]
                mean = [sum(s[i] for s in stops) / len(stops) for i in range(3)]
                fg = _over(r["fg"], mean)
                rows.append((r["sel"], round(_ratio(fg, mean), 2),
                             round(min(_ratio(fg, s) for s in stops), 2),
                             min(s[3] for s in r["stops"]) / 255))
            res[theme] = rows
        browser.close()
    return res


def _failures(res, fills=True):
    bad = []
    for theme, rows in res.items():
        for sel, mean, worst, alpha in rows:
            if (alpha >= FILL_ALPHA) != fills:
                continue
            if mean < TEXT_MIN or worst < STOP_MIN:
                bad.append(f"[{theme}] {sel}: {mean}:1 on the fill, "
                           f"{worst}:1 at its worst stop")
    return bad


def test_text_on_the_accent_is_legible_in_both_themes():
    res = measure(TEMPLATES / "results.html")
    # Sentinel: the walk has to reach the primary buttons, or an empty
    # list would agree with any colour.
    sels = " ".join(r[0] for r in res["dark"])
    for must in (".btn.primary", "button.btn-primary", ".chip--active",
                 ".burst-stack-badge"):
        assert must in sels, f"{must} was not measured; found: {sels[:300]}"
    assert len(res["dark"]) >= 15, len(res["dark"])
    bad = _failures(res)
    assert not bad, ("text drawn on the accent below "
                     f"{TEXT_MIN}:1 — use var(--on-accent):\n  "
                     + "\n  ".join(bad))


@pytest.mark.parametrize("page", ["video_review.html", "timeline.html"])
def test_the_dark_only_pages_draw_legible_text_on_the_accent(page):
    """These two have one theme and their own palette."""
    res = measure(TEMPLATES / page, themes=("dark",))
    assert res["dark"], f"no accent rule with text measured in {page}"
    bad = _failures(res)
    assert not bad, "\n".join(bad)


def test_accent_text_on_a_tint_does_not_get_worse():
    """The ratchet for the defect v3.104 measured and did not fix."""
    res = measure(TEMPLATES / "results.html")
    now = {}
    for theme, rows in res.items():
        for sel, mean, worst, alpha in rows:
            if alpha < FILL_ALPHA and (mean < TEXT_MIN or worst < STOP_MIN):
                now.setdefault(theme, set()).add(sel)
    for theme in set(now) | set(KNOWN_TINT_SHORTFALLS):
        got, known = now.get(theme, set()), KNOWN_TINT_SHORTFALLS.get(theme, set())
        assert not got - known, (
            f"[{theme}] new accent text on a tint below {TEXT_MIN}:1: "
            f"{sorted(got - known)}")
        assert not known - got, (
            f"[{theme}] these pass now; take them off KNOWN_TINT_SHORTFALLS: "
            f"{sorted(known - got)}")


_PAGES = sorted(p.name for p in (TEMPLATES / "pages").glob("*.html"))


@pytest.mark.parametrize("name", _PAGES)
def test_the_server_pages_draw_legible_text_on_the_accent(name, tmp_path):
    """The pages under templates/pages/ carry the server's own token CSS,
    which has a light theme of its own. Rendered the way the server
    serves them, then measured like the results page. Measured on the tree
    before v3.104's second review, seven rules here failed, the lowest
    1.74:1 on the upload page's main button; two more were inline styles,
    which only tests/test_no_white_text_on_the_accent.py reads."""
    from pixcull.report import serve_app
    html = serve_app._read_template(f"pages/{name}")
    assert "--on-accent" in html, f"{name} does not get the shared tokens"
    page = tmp_path / name
    page.write_text(html, encoding="utf-8")
    res = measure(page)
    bad = _failures(res)
    assert not bad, f"{name}:\n  " + "\n  ".join(bad)
