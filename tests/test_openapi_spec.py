import json
from pathlib import Path

from workledger_server.app import create_app


def test_openapi_spec_in_sync() -> None:
    committed = json.loads(Path("schemas/openapi.json").read_text(encoding="utf-8"))
    generated = create_app().openapi()
    assert generated == committed
