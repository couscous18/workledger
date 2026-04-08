"""Property-based tests for the policy engine condition evaluators."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from workledger.policy.engine import _contains, _evaluate_condition

# --- _contains ---


@given(
    haystack=st.text(min_size=1, max_size=50),
    needle=st.text(min_size=1, max_size=10),
)
def test_contains_string_is_case_insensitive(haystack: str, needle: str) -> None:
    result = _contains(haystack, needle)
    assert result == (needle.lower() in haystack.lower())


@given(items=st.lists(st.integers(), min_size=1, max_size=20))
def test_contains_list_membership(items: list[int]) -> None:
    assert _contains(items, items[0]) is True


@given(value=st.integers())
def test_contains_non_iterable_returns_false(value: int) -> None:
    assert _contains(value, "anything") is False


# --- _evaluate_condition: eq / neq ---


@given(value=st.text(min_size=1, max_size=20))
def test_eq_matches_identical_values(value: str) -> None:
    features = {"field": value}
    assert _evaluate_condition(features, {"feature": "field", "op": "eq", "value": value}) is True


@given(
    a=st.text(min_size=1, max_size=10),
    b=st.text(min_size=1, max_size=10),
)
def test_neq_differs_when_values_differ(a: str, b: str) -> None:
    features = {"field": a}
    assert _evaluate_condition(features, {"feature": "field", "op": "neq", "value": b}) == (a != b)


# --- _evaluate_condition: gte / lte ---


@given(
    actual=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
    threshold=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
)
def test_gte_matches_float_comparison(actual: float, threshold: float) -> None:
    features = {"score": actual}
    result = _evaluate_condition(features, {"feature": "score", "op": "gte", "value": threshold})
    assert result == (actual >= threshold)


@given(
    actual=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
    threshold=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
)
def test_lte_matches_float_comparison(actual: float, threshold: float) -> None:
    features = {"score": actual}
    result = _evaluate_condition(features, {"feature": "score", "op": "lte", "value": threshold})
    assert result == (actual <= threshold)


# --- _evaluate_condition: in ---


@given(
    items=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=10),
)
def test_in_matches_when_value_present(items: list[str]) -> None:
    features = {"kind": items[0]}
    result = _evaluate_condition(features, {"feature": "kind", "op": "in", "value": items})
    assert result is True


# --- _evaluate_condition: overlaps ---


@given(
    a=st.lists(st.text(min_size=1, max_size=5), min_size=1, max_size=5),
    b=st.lists(st.text(min_size=1, max_size=5), min_size=1, max_size=5),
)
def test_overlaps_matches_set_intersection(a: list[str], b: list[str]) -> None:
    features = {"labels": a}
    result = _evaluate_condition(features, {"feature": "labels", "op": "overlaps", "value": b})
    assert result == bool(set(a) & set(b))


# --- _evaluate_condition: exists ---


def test_exists_true_when_present() -> None:
    features = {"field": "value"}
    assert _evaluate_condition(features, {"feature": "field", "op": "exists"}) is True


def test_exists_false_when_missing() -> None:
    features: dict[str, object] = {}
    assert _evaluate_condition(features, {"feature": "field", "op": "exists"}) is False


# --- _evaluate_condition: missing feature defaults ---


def test_gte_with_missing_feature_uses_zero() -> None:
    features: dict[str, object] = {}
    result = _evaluate_condition(features, {"feature": "score", "op": "gte", "value": 0.5})
    assert result is False


def test_eq_with_missing_feature_matches_none() -> None:
    features: dict[str, object] = {}
    result = _evaluate_condition(features, {"feature": "field", "op": "eq", "value": None})
    assert result is True
