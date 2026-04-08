# Installation

```bash
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras
uv run wl init --project-dir .workledger
```

PyPI is not published yet. Do not advertise a PyPI install command until the package actually exists there.

Python 3.11+ is supported in this repository. The intended deployment target is Python 3.12+, but the codebase stays compatible with 3.11 for local-first development.
