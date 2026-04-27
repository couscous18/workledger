# Installation

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

## PyPI Install

When the tagged release publish has completed, install the package with:

```bash
python -m pip install workledger
```

## Source Install

If you are working from the repository directly or the package is not visible on PyPI yet, use:

```bash
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras
```

If you want to initialize an empty local project instead of running a demo first:

```bash
uv run wl init --project-dir .workledger
```

Python 3.11+ is supported in this repository. The intended deployment target is Python 3.12+, but the codebase stays compatible with 3.11 for local-first development.
