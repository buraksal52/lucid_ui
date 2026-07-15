"""UIClip provider interface.

Any provider — mock, or a future official evaluator — implements this same
narrow contract: given a Pillow image and a resolved description string,
return a structured dict. Providers never see a `DeterministicMetricResult`,
Gemini/LLM output, or comparison results — they only ever see the decoded
image and description text, which keeps UIClip's independence from LucidUI
and the LLM interpretation layer true regardless of which provider is
configured — see docs/architecture/decisions/ADR-004-uiclip-independent-evaluator.md.

Structural validation of the returned dict (does it match
`UIClipProviderOutput`?) is the service's job, not the provider's — mirrors
`app.llm.provider.LLMProvider`.
"""

from typing import Any, Protocol

from PIL.Image import Image


class UIClipProvider(Protocol):
    """A named, swappable backend for UIClip evaluation."""

    name: str

    def evaluate(self, image: Image, description: str) -> dict[str, Any]:
        """Return a structured evaluation for the given image and description.

        Must raise `app.uiclip.exceptions.UIClipProviderUnavailableError` if
        the provider itself could not be reached/loaded/configured, or
        `app.uiclip.exceptions.UIClipEvaluationError` if it ran but the
        output could not be turned into a usable dict. Any other exception
        is treated by the caller as an unexpected failure and also degrades
        gracefully.
        """
        ...
