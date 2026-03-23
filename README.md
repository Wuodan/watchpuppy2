# Python Repo Template

Starter template for small Python repositories.

Included:

- lint setup via `ruff`, `pyright`, `yamllint`, and `pymarkdown`
- `scripts/lint.sh`
- repo-level structure and visibility tests
- starter dependency files
- Dependabot config

## Use

1. Create a new repository from this template.
2. Clone it locally.

## Change In The New Repo

- replace this `README.md`
- fill out `pyproject.toml`
- add runtime dependencies to `requirements.txt`
- adjust `requirements-dev.txt`
- update `.github/dependabot.yml`
- tune `AGENTS.md`

## Lint

```bash
./scripts/lint.sh
pytest
```

## Notes

- source layout is expected under `src/`
- tests are expected under `tests/` as packages
- `tests/repo_rules/` is generic and does not need renaming
