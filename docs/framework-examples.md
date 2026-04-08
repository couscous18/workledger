# Framework Examples

You can get value from WorkLedger today without a dedicated adapter package.

- [examples/langchain_to_workledger.py](https://github.com/couscous18/workledger/blob/main/examples/langchain_to_workledger.py)
- [examples/crewai_to_workledger.py](https://github.com/couscous18/workledger/blob/main/examples/crewai_to_workledger.py)
- [examples/otel_to_workledger.py](https://github.com/couscous18/workledger/blob/main/examples/otel_to_workledger.py)

Common pattern:

```bash
wl ingest exported_traces.jsonl
wl rollup
wl classify
wl report
```
