"""Real UIClip provider — official BIG Lab checkpoint via standard `transformers` CLIP classes.

Checkpoint: `biglab/uiclip_jitteredwebsites-2-224-paraphrased` (default, see
`Settings.uiclip_model_id`), MIT licensed, from Wu et al., "UIClip: A
Data-driven Model for Assessing User Interface Design" (UIST 2024,
arXiv:2404.12500). See docs/research/uiclip-integration.md for the full
verification writeup and why this exact checkpoint was chosen.

Loads via `transformers.CLIPModel`/`CLIPProcessor` — no bespoke/unofficial
model code, no retraining. The model is loaded exactly once at construction
time (never inside `evaluate()`); `app.dependencies.get_uiclip_provider` is
`lru_cache`d, so a single instance is reused across every request.

Score: `outputs.logits_per_image[0, 0]` — the standard CLIP dual-encoder
output, `logit_scale * (image_embedding · text_embedding)`. This is exactly
the "dot product between the image embedding and text embedding" the
official paper describes, with no additional calibration — an uncalibrated
similarity/logit value, not a 0-100 or 0-1 quality percentage. Never
normalized here; `UIClipEvaluationService` always leaves
`normalized_quality_score` null for this reason.

Two details are taken directly from the checkpoint's official model card
(https://huggingface.co/biglab/uiclip_jitteredwebsites-2-224-paraphrased),
not invented here:

1. The UIClip checkpoints only publish `config.json` + `model.safetensors`
   — no processor/tokenizer files. The documented usage loads the
   processor from the base model they were fine-tuned from,
   `openai/clip-vit-base-patch32` (small, config/tokenizer/preprocessor
   files only, no separate vision weights are used from it). This is a
   loading-mechanics detail, not a UIClip config choice, so it is a fixed
   constant here rather than a new Settings field.
2. The documented usage encodes `"ui screenshot. well-designed. " +
   description`, not the bare description — the checkpoint was fine-tuned
   against text in that exact template. This is part of feeding the model
   the input format it expects, not a normalization of its output score.
"""

import logging
from typing import Any

import torch
from PIL.Image import Image
from transformers import CLIPModel, CLIPProcessor

from app.uiclip.exceptions import UIClipEvaluationError, UIClipProviderUnavailableError

logger = logging.getLogger("lucidui.uiclip.huggingface")

# The UIClip checkpoints ship only model weights; the processor is the
# unmodified base CLIP processor per the official model card. Not
# user-configurable — it is a fixed property of how these checkpoints load,
# not a policy choice like `uiclip_model_id`/`uiclip_device`.
_PROCESSOR_MODEL_ID = "openai/clip-vit-base-patch32"

# Fixed text template the checkpoint was fine-tuned to expect, per the
# official model card's example code. Applied to whatever real user
# description is supplied; never applied to a score after the fact.
_DESCRIPTION_PREFIX = "ui screenshot. well-designed. "


class HuggingFaceUIClipProvider:
    """Real UIClip provider. Requires a genuine user-submitted description
    (see `requires_description`) — evaluating the generic screenshot
    placeholder against the real model would produce a misleading score, so
    `UIClipEvaluationService` skips calling this provider entirely when no
    real description was submitted, returning `unavailable` instead.
    """

    name = "huggingface"
    requires_description = True

    def __init__(self, model_id: str, device: str) -> None:
        try:
            self._model = CLIPModel.from_pretrained(model_id)
            self._processor = CLIPProcessor.from_pretrained(_PROCESSOR_MODEL_ID)
        except Exception as exc:
            raise UIClipProviderUnavailableError(f"Could not load UIClip model '{model_id}'.") from exc

        self._model_id = model_id
        self.device = self._move_to_device(self._resolve_device(device))
        self._model.eval()

    def evaluate(self, image: Image, description: str) -> dict[str, Any]:
        try:
            inputs = self._processor(
                text=[_DESCRIPTION_PREFIX + description], images=image, return_tensors="pt", padding=True
            )
            inputs = {key: value.to(self.device) for key, value in inputs.items()}
            with torch.inference_mode():
                outputs = self._model(**inputs)
            raw_score = float(outputs.logits_per_image[0, 0].item())
        except Exception as exc:
            raise UIClipEvaluationError("UIClip inference failed.") from exc

        return {
            "model_version": self._model_id,
            "raw_score": raw_score,
            "observations": [],  # the loaded checkpoint scores only; no suggestion-generation model is integrated
        }

    def _move_to_device(self, device: str) -> str:
        try:
            self._model.to(device)
            return device
        except Exception:
            logger.exception("Failed to move UIClip model to device '%s'; falling back to CPU", device)
            self._model.to("cpu")
            return "cpu"

    @staticmethod
    def _resolve_device(requested: str) -> str:
        """`cpu`/`mps`/`cuda` are honored if actually available, else fall
        back to CPU rather than raising. `auto` (or any unrecognized value)
        prefers CUDA, then MPS, then CPU."""
        if requested == "cpu":
            return "cpu"
        if requested == "cuda":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if requested == "mps":
            return "mps" if torch.backends.mps.is_available() else "cpu"
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"
