# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in workledger, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Use GitHub's private vulnerability reporting flow for this repository when the Security tab shows **Report a vulnerability**.

If private reporting is not available, open a regular GitHub issue that asks for a private follow-up path, but do not include exploit details or sensitive data in the public issue.

For non-sensitive bugs or hardening suggestions, use the normal bug-report workflow.

workledger is community-maintained, so security review and response are best effort. No response timeline is guaranteed.

## Scope

The following are in scope:

- The `workledger` Python package (`src/workledger/`)
- The `workledger-server` FastAPI application (`src/workledger_server/`)
- The `workledger_observe` SDK (`src/workledger_observe/`)
- Policy pack evaluation logic
- DuckDB storage layer

The following are out of scope:

- Demo scripts and example data
- Documentation site infrastructure
- Third-party dependencies (please report those to the respective maintainers)

## Disclosure

We prefer coordinated disclosure when a maintainer is available to engage. Any timeline for disclosure or credit will be agreed case by case through the GitHub reporting thread.

## Security Considerations

workledger processes AI trace data that may contain sensitive information:

- **PII in traces**: Raw LLM spans may contain user inputs. Use the `mask_pii` facet and configure your ingestion pipeline to redact sensitive fields before they reach workledger.
- **Cost data**: Work unit cost figures may be commercially sensitive. Restrict access to the DuckDB file and exported reports.
- **Policy decisions**: Accounting classifications are candidate interpretations, not authoritative. Do not use them as the sole basis for financial reporting without human review.
