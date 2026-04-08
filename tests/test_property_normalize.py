from datetime import UTC, datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from workledger.ingest.normalize import normalize_event


@given(
    trace_id=st.text(min_size=1, max_size=20),
    span_id=st.text(min_size=1, max_size=20),
    token_input=st.integers(min_value=0, max_value=10000),
    token_output=st.integers(min_value=0, max_value=10000),
    direct_cost=st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
)
def test_sdk_normalization_preserves_basic_invariants(
    trace_id: str,
    span_id: str,
    token_input: int,
    token_output: int,
    direct_cost: float,
) -> None:
    start = datetime(2026, 4, 6, tzinfo=UTC)
    end = start + timedelta(seconds=5)
    span = normalize_event(
        {
            "event_type": "observation_span",
            "source_kind": "sdk",
            "trace_id": trace_id,
            "span_id": span_id,
            "span_kind": "llm",
            "name": "generated-span",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "token_input": token_input,
            "token_output": token_output,
            "direct_cost": direct_cost,
            "attributes": {},
            "facets": {},
        }
    )
    assert span.trace_id == trace_id
    assert span.span_id == span_id
    assert span.token_input == token_input
    assert span.token_output == token_output
    assert span.duration_ms == 5000
