"""Tests for review queue prioritization and overrides."""

from __future__ import annotations

from workledger.review import _top_competing_candidates


def test_top_competing_candidates_extracts_from_matching_decision() -> None:
    decisions = [
        {
            "trace_id": "wu-1",
            "competing_candidates": [
                {"rule_id": "r1", "value": "maintenance_bugfix", "confidence": 0.7},
                {"rule_id": "r2", "value": "research_and_development", "confidence": 0.6},
            ],
        }
    ]
    result = _top_competing_candidates("wu-1", decisions)
    assert len(result) == 2
    assert result[0]["rule_id"] == "r1"


def test_top_competing_candidates_matches_none_trace_id() -> None:
    decisions = [
        {
            "competing_candidates": [
                {"rule_id": "r1", "value": "maintenance_bugfix", "confidence": 0.7},
            ],
        }
    ]
    result = _top_competing_candidates("any-id", decisions)
    assert len(result) == 1


def test_top_competing_candidates_returns_empty_on_no_match() -> None:
    decisions = [
        {
            "trace_id": "wu-other",
            "competing_candidates": [{"rule_id": "r1", "value": "x", "confidence": 0.5}],
        }
    ]
    result = _top_competing_candidates("wu-1", decisions)
    assert result == []


def test_top_competing_candidates_filters_non_dict_items() -> None:
    decisions = [
        {
            "trace_id": "wu-1",
            "competing_candidates": [
                {"rule_id": "r1", "value": "x", "confidence": 0.5},
                "not-a-dict",
                42,
            ],
        }
    ]
    result = _top_competing_candidates("wu-1", decisions)
    assert len(result) == 1


def test_top_competing_candidates_empty_decisions() -> None:
    assert _top_competing_candidates("wu-1", []) == []


def test_top_competing_candidates_missing_candidates_key() -> None:
    decisions = [{"trace_id": "wu-1"}]
    result = _top_competing_candidates("wu-1", decisions)
    assert result == []
