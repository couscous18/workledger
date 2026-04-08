import json
from pathlib import Path

from workledger.schema import generate_schema_bundle


def test_checked_in_schema_matches_generator() -> None:
    schema_path = Path("schemas/workledger.schema.json")
    checked_in = json.loads(schema_path.read_text(encoding="utf-8"))
    assert checked_in == generate_schema_bundle()
    assert checked_in["$id"].startswith("https://raw.githubusercontent.com/couscous18/workledger/")
    assert "workledger.dev" not in checked_in["$id"]
