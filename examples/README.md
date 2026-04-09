# Examples

These examples show how raw traces become understandable work.

Smallest example first:

```bash
uv run python examples/tiny_pipeline.py
```

Then run the larger demo entrypoints:

```bash
uv run python examples/demo_coding.py
uv run python examples/demo_marketing.py
uv run python examples/demo_support.py
```

Additional integration examples:

- `hf_public_traces.py`
- `langchain_to_workledger.py`
- `crewai_to_workledger.py`
- `otel_to_workledger.py`
