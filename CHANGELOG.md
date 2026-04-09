# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Optional `ObservationSpan.token_taxes` support for employer-style token tax metadata, including jurisdiction, rate, taxable token count, and tax amount
- GitHub release workflow that builds sdist and wheel artifacts and publishes them to the Releases page when a `v*` tag is pushed
- `wl demo open-traces` alias for the flagship public demo path

### Changed

- Reframed README, docs, and release copy around the open trace-to-work story instead of the older agent-cost-led narrative

## [0.1.0] - 2026-04-06

### Added

- Community files: CODE_OF_CONDUCT.md, SECURITY.md, CHANGELOG.md
- GitHub issue and PR templates
- GitHub Pages documentation deployment workflow
- README comparison table (workledger vs observability tools)
- README badges (CI, PyPI, Python version, license, docs)
- Codespace and GitPod dev environment configs
- Core data model: `ObservationSpan`, `WorkUnit`, `ClassificationTrace`, `PolicyDecision`, `EvidenceRef`, `PolicyPack`, and `ReportArtifact`
- Ingestion pipeline supporting JSONL, OpenInference, OTEL JSON, CloudEvents, and SDK event formats
- Rollup engine compressing low-level spans into business-level work units
- Declarative YAML policy pack engine with explainable rule matching
- Four built-in policy packs: management reporting, US GAAP, IFRS, and tax R&D
- DuckDB-backed local analytical store with Parquet, JSON, and CSV export
- `wl` CLI with commands: init, ingest, rollup, classify, report, export, explain, demo, doctor, override, policies
- FastAPI server (`workledger-server`) with full OpenAPI documentation
- Runnable demos for coding, marketing, and support scenarios
- JSON Schema export for core models
- Report outputs: terminal, JSON, CSV, Parquet, Markdown, HTML
- Review queue and manual override support
- Property-based tests with Hypothesis
- CI pipeline with ruff, mypy (strict), and pytest
- MkDocs documentation site with Material theme
- Docker and docker-compose support
- TypeScript SDK event helper (`packages/sdk/`)
