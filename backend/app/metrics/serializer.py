"""Recursive JSON-safe conversion for deterministic metric engine output.

The legacy metric engine (backend/reference/legacy_metric_engine.py, never
modified — see CLAUDE.md) occasionally returns NumPy scalar types (e.g.
`round()` on a `np.float64` stays a `np.float64`), which Pydantic/FastAPI's
default JSON encoder cannot serialize. This utility converts those into
plain Python types without changing numeric precision, renaming keys,
altering `None`, or stringifying numbers — it only changes *type*, never
*value* or *structure* (aside from tuple -> list, since JSON has no tuple
type).
"""

from typing import Any

import numpy as np


def to_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return to_json_safe(value.tolist())
    return value
