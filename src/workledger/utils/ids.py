from __future__ import annotations

from hashlib import sha256
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def stable_id(prefix: str, *parts: object) -> str:
    digest = sha256("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:16]}"
