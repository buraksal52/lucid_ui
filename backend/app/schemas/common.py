"""Shared base model and enums used across the LucidUI schema package.

`CamelModel` is the base for every public schema: it auto-generates camelCase
aliases (e.g. `run_llm` -> `runLlm`) so Python code stays snake_case while the
public JSON contract stays camelCase, per docs/api/report-schema.md.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class AnalysisMode(str, Enum):
    SINGLE = "single"
    VARIANTS = "variants"


class AnalysisStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class AnalysisContext(str, Enum):
    GENERAL = "general"
    EXPERT = "expert"


class LLMStatus(str, Enum):
    COMPLETED = "completed"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    FALLBACK = "fallback"
    FAILED = "failed"


class UIClipStatus(str, Enum):
    COMPLETED = "completed"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class DescriptionSource(str, Enum):
    USER = "user"
    GENERIC = "generic"
    GENERATED = "generated"


class AgreementLevel(str, Enum):
    HIGH = "high"
    PARTIAL = "partial"
    LOW = "low"
    UNAVAILABLE = "unavailable"


ALLOWED_CONTEXTS: list[str] = [c.value for c in AnalysisContext]


class HealthResponse(CamelModel):
    status: str = "ok"
    service: str = "lucidui-backend"
    version: str
