# YAML examples

Staves (data sources) and clefs (quality checks). The loader reads a
`staves:` list and a `clefs:` list. Files that do not parse fail
`tests/test_examples_parse.py`.

| File | What it is |
|---|---|
| `demo-clickstream.yaml` | One sqlite stave and three clefs |
| `demo-complete.yaml` | Clickstream plus ecommerce |
| `staves.yaml` | Multi-stave template |
| `production-db.yaml` | Postgres template with env vars |
| `conflicting-config.yaml` | Intentionally invalid, used by tests |

Import, from `datametronome/podium`:

```bash
.venv/bin/python scripts/import_staves.py examples/demo-clickstream.yaml
.venv/bin/python scripts/import_staves.py examples/demo-complete.yaml --overwrite
.venv/bin/python scripts/import_staves.py examples/demo-complete.yaml --validate-only
```

`--overwrite` updates existing rows in place. Demo users come from
`make seed`, not from these files. The API does not auto-import anything
on boot.
