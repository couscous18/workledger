# Framework Examples

You can get value from WorkLedger today without a dedicated adapter package.

- [examples/langchain_to_workledger.py](/Users/anji/Documents/GitHub/Work%20Unit/examples/langchain_to_workledger.py)
- [examples/crewai_to_workledger.py](/Users/anji/Documents/GitHub/Work%20Unit/examples/crewai_to_workledger.py)
- [examples/otel_to_workledger.py](/Users/anji/Documents/GitHub/Work%20Unit/examples/otel_to_workledger.py)

Common pattern:

```bash
wl ingest exported_traces.jsonl
wl rollup
wl classify
wl report
```
