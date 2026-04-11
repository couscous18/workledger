# Contributing to workledger

Thank you for your interest in contributing to workledger. Every contribution matters, whether it's code, documentation, bug reports, or feature ideas.

The repository is currently centered on a local pipeline:

`ingest -> ObservationSpan -> WorkUnit -> optional ClassificationTrace -> reports / review / exports`

Policy packs, benchmarks, demos, documentation, input adapters, and report improvements are all fair game for contribution. Please assume review is best effort rather than on a guaranteed support schedule.

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
# Clone the repository
git clone https://github.com/couscous18/workledger.git
cd workledger

# Install dependencies (includes dev tools)
uv sync --all-extras

# Install pre-commit hooks
pre-commit install

# Verify everything works
make ci
```

### Run a full local demo

```bash
uv run wl demo coding --project-dir .workledger/coding --open-report
```

## Development Loop

```bash
make lint      # ruff check + mypy strict
make test      # pytest
make format    # ruff format
make demo      # full ingest -> rollup -> classify -> report
make docs      # build MkDocs site locally
make ci        # lint + test (same as CI)
```

## What to Work On

- Issues labeled [`good first issue`](https://github.com/couscous18/workledger/labels/good%20first%20issue) are a great starting point
- Issues labeled [`help wanted`](https://github.com/couscous18/workledger/labels/help%20wanted) are more involved but well-defined
- Documentation improvements are always welcome
- Benchmarks, example demos, policy packs, report summaries, and integrations are intentionally small starter surfaces and welcome expansion

## Contribution Guidelines

- **Keep the core schema stable and explicit.** Breaking changes to `ObservationSpan`, `WorkUnit`, `ClassificationTrace`, or `PolicyDecision` require discussion first.
- **Prefer extension facets over bloating core models.** The facet system exists for domain-specific metadata.
- **Preserve explainability.** Rollup and policy changes must produce traceable, auditable decisions.
- **Add or update fixtures** for every behavior change in rollup or classification.
- **Preserve lineage.** Public trace adapters must keep stable source refs in `raw_payload_ref`.
- **Keep the repo story truthful.** Docs should describe the implemented CLI and pipeline, not an assumed product narrative.

## Adding A Public Trace Adapter

Keep adapters small and explicit.

Minimum expectations:

- map source rows into `ObservationSpan`
- preserve source lineage in `raw_payload_ref`
- use namespaced `facets` for adapter-specific metadata
- keep review-needed ambiguity visible instead of flattening it away
- add fixture-driven tests
- add a demo-sized path that can run on a small public sample

Recommended mapping:

- stable dataset metadata in `facets["hf"]` or another source namespace
- source row or message/span IDs in `raw_payload_ref`
- `work_unit_key` when a source row should become a single rolled work candidate
- `attributes["review_required"]` when the trace shape is ambiguous

## Other Real Extension Points

- input normalization in `src/workledger/ingest/normalize.py`
- rollup heuristics in `src/workledger/rollup/`
- YAML policy packs under `policies/`
- reporting summaries in `src/workledger/reporting/engine.py`
- benchmark cases under `benchmark-data/`
- canonical emitters in `src/workledger_observe/` and `packages/sdk/`

## Pull Requests

1. Fork the repository and create a feature branch from `main`
2. Make your changes with clear, focused commits
3. Ensure `make ci` passes (ruff + mypy strict + pytest)
4. Update documentation and examples if behavior changes
5. Call out policy behavior changes explicitly in the PR description
6. Open a PR using the [PR template](.github/pull_request_template.md)

### Commit Messages

Use clear, imperative commit messages:

```
Add OpenInference v2 span normalization
Fix rollup grouping when trace_id is missing
Update policy engine to support negated conditions
```

## Architecture Decisions

Major changes (new storage backends, schema changes, new policy evaluation strategies) should start as a [GitHub Discussion](https://github.com/couscous18/workledger/discussions) before implementation.

## Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_rollup.py

# With coverage
uv run pytest --cov=workledger --cov-report=term-missing

# Property-based tests only
uv run pytest tests/test_property_normalize.py
```

## Documentation

Docs are built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/):

```bash
# Build docs
uv run mkdocs build

# Serve locally with hot reload
uv run mkdocs serve
```

## Questions?

Open a [GitHub Discussion](https://github.com/couscous18/workledger/discussions) or check the [FAQ](docs/faq.md). Discussions and issues are the primary community support channels for this repository.
