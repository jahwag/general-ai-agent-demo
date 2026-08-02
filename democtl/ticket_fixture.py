from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SYNTHETIC_TAG = "synthetic-ai-demo"
ALLOWED_FIELDS = {
    "email",
    "subject",
    "description",
    "priority",
    "status",
    "tags",
}


def load_synthetic_ticket(path: Path) -> dict[str, Any]:
    """Load a deliberately synthetic, allow-listed Freshworks ticket fixture."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"ticket fixture is not valid JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError("ticket fixture must be a JSON object")

    unknown = set(value) - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"ticket fixture contains unsupported fields: {sorted(unknown)}")

    for field in ("email", "subject", "description"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"ticket fixture {field} must be a non-empty string")

    if not value["email"].casefold().endswith(".invalid"):
        raise ValueError("ticket fixture email must use the reserved .invalid domain")

    for field in ("priority", "status"):
        if not isinstance(value.get(field), int) or isinstance(value[field], bool):
            raise ValueError(f"ticket fixture {field} must be an integer")

    tags = value.get("tags")
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        raise ValueError("ticket fixture tags must be a list of strings")
    if SYNTHETIC_TAG not in tags:
        raise ValueError(f"ticket fixture must include the {SYNTHETIC_TAG!r} tag")

    return value
