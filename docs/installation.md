# Installation

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

```bash
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras
```

PyPI is not published for this release. Do not advertise `pip install workledger` until the package actually exists and matches the source docs.

If you want to initialize an empty local project instead of running a demo first:

```bash
uv run wl init --project-dir .workledger
```

Python 3.11+ is supported in this repository. The intended deployment target is Python 3.12+, but the codebase stays compatible with 3.11 for local-first development.
