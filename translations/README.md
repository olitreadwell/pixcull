# Translation kits

One CSV per locale. See `docs/I18N.md` for the column meanings.

```
make i18n-export LANG=fr_FR
```

Fill the `target` column, then:

```
.venv/bin/python scripts/i18n_import.py translations/fr_FR.csv --lang fr_FR --check
.venv/bin/python scripts/i18n_import.py translations/fr_FR.csv --lang fr_FR
```

Chinese stays the source of truth. English is the pivot, so you do not
need to read Chinese to translate.
