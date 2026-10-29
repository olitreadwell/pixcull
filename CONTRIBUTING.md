# Contributing to PixCull

Thanks for your interest. PixCull is a single-author project that took shape
through hundreds of small, scoped commits — the same rhythm works for
contributions.

## Quick start for contributors

```bash
git clone https://github.com/ChrisChen667788/pixcull.git
cd pixcull
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ --ignore=tests/test_v1_1_scripts.py   # the whole suite: minutes, not seconds
python scripts/preflight.py                                   # the release bookkeeping gates
pixcull serve                                                 # the review workspace, localhost:8770
```

A test that needs an optional model, `exiftool` or ffmpeg skips when it is
missing, and every skip is reported with its reason; CI installs what the
hermetic lane needs.

## Workflow

1. **One concern per PR.** A change like "filter pill row no longer wraps
   on 13" displays" is much easier to review than "polish the UI".
2. **Tag with a prefix** in the commit subject so the log stays readable:
   - `P-UX-N` for a results-page UX milestone
   - `INFRA-N` for sync / tether / API plumbing
   - `Vx.y` for a versioned model / pipeline change
   - `docs:` / `tests:` / `chore:` for non-code work
3. **Tests.** Anything touching `pixcull/scoring/`, `pixcull/pipeline/`, or
   `pixcull/report/serve_app.py` (the server; `scripts/serve_demo.py` only
   forwards to it) needs a pytest entry. UI-only changes need a
   browser smoke note in the PR description (size, screen, browser).
4. **Identifiers and file names stay ASCII.** Strings a photographer reads
   may be Chinese or carry an emoji, as many in `pixcull/` already do; names
   in code stay searchable.
5. **Don't open up sync / license / billing layers** without flagging it
   first — those are intentionally minimal and any growth needs an
   explicit design discussion in an issue.

## What's a good first PR?

- A new entry in the cull-reason taxonomy
  (`_CULL_REASONS` in `pixcull/report/serve_app.py` + an `I18N_SIM_REASON`-style
  label in `pixcull/report/templates/src/results.js`)
- A new vertical's scoring policy (`pixcull/verticals.py`)
- A new scene template (`pixcull/scoring/templates/scene_templates.yaml`)
- A new XMP keyword in the export path (`pixcull/io/xmp.py`)
- Translating the UI to another language (the string tables in `pixcull/locale/`)

## Anything that's NOT a good first PR

- Rewriting the rescorer (V1.x → V2.x took weeks)
- New scoring axes (the rescorer and every taste profile read the six
  axes by name; adding a 7th breaks the rescorer joblibs)
- Multi-user / multi-tenant changes (V28 already exists; talk first)

## Code style

- Python: PEP 8, 80-col soft limit, no formatter enforced. Type hints
  where it clarifies intent, not as decoration.
- JS for the results page: no framework. It lives in
  `pixcull/report/templates/src/` (`results.js` and `modules/*.js`) and is
  spliced into `pixcull/report/templates/results.html` by
  `python scripts/build_results_html.py`; edit the sources, never the built
  file, which a test compares with them. Prefer plain DOM + delegated
  event listeners. Read existing code first — there are patterns you'll
  want to mirror (`registerModal`, `pushUndo`, etc).
- CSS: keep variables in `:root` block. Don't introduce a preprocessor.

## License

By contributing, you agree your code is released under the MIT License
that covers the rest of the project.
