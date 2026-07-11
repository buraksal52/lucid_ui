"""LLM provider interface.

Any provider — mock, Gemini, or a future addition — implements this same
narrow contract: given a system prompt and a user prompt (both plain text,
built by `app.llm.prompt`), return a structured dict. Providers never see a
`DeterministicMetricResult`, a `DecodedImage`, or any image bytes directly;
they only ever see the two prompt strings handed to them, which keeps
"no screenshot is ever sent to the LLM" true regardless of which provider is
configured — see docs/architecture/decisions/ADR-003-json-only-llm-input.md.

Structural validation of the returned dict (does it match
`LLMStructuredOutput`?) is the service's job, not the provider's — a
provider is only responsible for producing *some* dict from the model API it
wraps; `LLMInterpretationService` is the single place that decides whether
that dict is usable.
"""

from typing import Any, Protocol


class LLMProvider(Protocol):
    """A named, swappable backend for LLM completions."""

    name: str

    def complete(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Return a structured response for the given prompts.

        Must raise `app.llm.exceptions.LLMProviderUnavailableError` if the
        provider itself could not be reached/authenticated, or
        `app.llm.exceptions.LLMInterpretationError` if it responded but the
        response could not be turned into a dict at all (e.g. empty or
        non-JSON output). Any other exception is treated by the caller as an
        unexpected failure and also degrades gracefully.
        """
        ...
