"""Tests for the real UIClip provider (app.uiclip.huggingface_provider).

`transformers.CLIPModel`/`CLIPProcessor` are monkeypatched at the module
level everywhere here — no test downloads or runs the real BIG Lab
checkpoint, per CLAUDE.md ("Tests must not require ... UIClip ... GPU").
Real, local `torch` tensors are used for fake processor/model outputs since
constructing a CPU tensor needs no network or GPU.
"""

import pytest
import torch
from PIL import Image

import app.uiclip.huggingface_provider as hf_module
from app.uiclip.exceptions import UIClipEvaluationError, UIClipProviderUnavailableError
from app.uiclip.huggingface_provider import HuggingFaceUIClipProvider


class _FakeOutputs:
    def __init__(self, score: float) -> None:
        self.logits_per_image = torch.tensor([[score]])


class _FakeBatchEncoding(dict):
    """A dict whose values already respond to `.to(device)`, like a real
    `transformers.BatchEncoding` of torch tensors."""


class _FakeProcessor:
    def __call__(self, text, images, return_tensors, padding):
        return _FakeBatchEncoding(
            input_ids=torch.zeros((1, 3), dtype=torch.long),
            pixel_values=torch.zeros((1, 3, 224, 224)),
        )


class _FakeModel:
    def __init__(self, score: float = 42.0, fail_on_device: str | None = None) -> None:
        self.eval_called = False
        self.to_calls: list[str] = []
        self.call_count = 0
        self._score = score
        self._fail_on_device = fail_on_device
        self._forward_should_fail = False

    def eval(self):
        self.eval_called = True
        return self

    def to(self, device: str):
        self.to_calls.append(device)
        if device == self._fail_on_device:
            raise RuntimeError(f"backend '{device}' is not available on this build")
        return self

    def __call__(self, **kwargs):
        self.call_count += 1
        if self._forward_should_fail:
            raise RuntimeError("forward pass exploded")
        return _FakeOutputs(self._score)


def _patch_transformers(monkeypatch: pytest.MonkeyPatch, model: _FakeModel, processor: _FakeProcessor | None = None):
    monkeypatch.setattr(hf_module.CLIPModel, "from_pretrained", lambda model_id, **kwargs: model)
    monkeypatch.setattr(hf_module.CLIPProcessor, "from_pretrained", lambda model_id, **kwargs: processor or _FakeProcessor())


# ---------- Model loading: once, cached, eval() called ----------


def test_model_and_processor_load_exactly_once_and_reused_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeModel()
    load_calls = {"model": 0, "processor": 0}

    def fake_model_load(model_id, **kwargs):
        load_calls["model"] += 1
        return model

    def fake_processor_load(model_id, **kwargs):
        load_calls["processor"] += 1
        return _FakeProcessor()

    monkeypatch.setattr(hf_module.CLIPModel, "from_pretrained", fake_model_load)
    monkeypatch.setattr(hf_module.CLIPProcessor, "from_pretrained", fake_processor_load)
    monkeypatch.setattr(hf_module.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(hf_module.torch.backends.mps, "is_available", lambda: False)

    provider = HuggingFaceUIClipProvider(model_id="biglab/uiclip_jitteredwebsites-2-224-paraphrased", device="cpu")

    assert load_calls == {"model": 1, "processor": 1}
    assert model.eval_called is True

    # Two evaluate() calls must not reload the model.
    provider.evaluate(Image.new("RGB", (10, 10)), "a description")
    provider.evaluate(Image.new("RGB", (10, 10)), "another description")

    assert load_calls == {"model": 1, "processor": 1}
    assert model.call_count == 2


# ---------- Score extraction ----------


def test_evaluate_returns_real_logits_per_image_score(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeModel(score=17.25)
    _patch_transformers(monkeypatch, model)
    monkeypatch.setattr(hf_module.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(hf_module.torch.backends.mps, "is_available", lambda: False)

    provider = HuggingFaceUIClipProvider(model_id="biglab/uiclip_jitteredwebsites-2-224-paraphrased", device="cpu")
    result = provider.evaluate(Image.new("RGB", (10, 10)), "A checkout page")

    assert result["raw_score"] == pytest.approx(17.25)
    assert result["model_version"] == "biglab/uiclip_jitteredwebsites-2-224-paraphrased"
    assert result["observations"] == []


def test_raw_score_is_not_normalized_to_0_100_or_0_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fake model deliberately returns a value outside [0, 1] and
    outside [0, 100] to prove nothing clamps/rescales it."""
    model = _FakeModel(score=-250.0)
    _patch_transformers(monkeypatch, model)
    monkeypatch.setattr(hf_module.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(hf_module.torch.backends.mps, "is_available", lambda: False)

    provider = HuggingFaceUIClipProvider(model_id="x", device="cpu")
    result = provider.evaluate(Image.new("RGB", (10, 10)), "A page")
    assert result["raw_score"] == pytest.approx(-250.0)


# ---------- Device resolution and fallback ----------


def test_device_cpu_is_honored(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeModel()
    _patch_transformers(monkeypatch, model)

    provider = HuggingFaceUIClipProvider(model_id="x", device="cpu")
    assert provider.device == "cpu"
    assert model.to_calls == ["cpu"]


def test_device_auto_prefers_mps_when_cuda_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeModel()
    _patch_transformers(monkeypatch, model)
    monkeypatch.setattr(hf_module.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(hf_module.torch.backends.mps, "is_available", lambda: True)

    provider = HuggingFaceUIClipProvider(model_id="x", device="auto")
    assert provider.device == "mps"


def test_device_auto_falls_back_to_cpu_when_nothing_available(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeModel()
    _patch_transformers(monkeypatch, model)
    monkeypatch.setattr(hf_module.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(hf_module.torch.backends.mps, "is_available", lambda: False)

    provider = HuggingFaceUIClipProvider(model_id="x", device="auto")
    assert provider.device == "cpu"


def test_requested_mps_falls_back_to_cpu_when_mps_reports_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeModel()
    _patch_transformers(monkeypatch, model)
    monkeypatch.setattr(hf_module.torch.backends.mps, "is_available", lambda: False)

    provider = HuggingFaceUIClipProvider(model_id="x", device="mps")
    assert provider.device == "cpu"


def test_mps_move_failure_falls_back_to_cpu_in_a_controlled_way(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even when MPS reports available but actually moving the model to it
    raises (a real-world MPS backend quirk), the provider must not crash —
    it must fall back to CPU."""
    model = _FakeModel(fail_on_device="mps")
    _patch_transformers(monkeypatch, model)
    monkeypatch.setattr(hf_module.torch.backends.mps, "is_available", lambda: True)
    monkeypatch.setattr(hf_module.torch.cuda, "is_available", lambda: False)

    provider = HuggingFaceUIClipProvider(model_id="x", device="mps")

    assert provider.device == "cpu"
    assert model.to_calls == ["mps", "cpu"]  # attempted mps, then fell back


# ---------- Failure handling ----------


def test_model_load_failure_raises_provider_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(model_id, **kwargs):
        raise OSError("could not resolve huggingface.co")

    monkeypatch.setattr(hf_module.CLIPModel, "from_pretrained", boom)
    with pytest.raises(UIClipProviderUnavailableError):
        HuggingFaceUIClipProvider(model_id="x", device="cpu")


def test_processor_load_failure_raises_provider_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hf_module.CLIPModel, "from_pretrained", lambda model_id, **kwargs: _FakeModel())

    def boom(model_id, **kwargs):
        raise OSError("could not resolve huggingface.co")

    monkeypatch.setattr(hf_module.CLIPProcessor, "from_pretrained", boom)
    with pytest.raises(UIClipProviderUnavailableError):
        HuggingFaceUIClipProvider(model_id="x", device="cpu")


def test_inference_failure_raises_uiclip_evaluation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeModel()
    model._forward_should_fail = True
    _patch_transformers(monkeypatch, model)
    monkeypatch.setattr(hf_module.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(hf_module.torch.backends.mps, "is_available", lambda: False)

    provider = HuggingFaceUIClipProvider(model_id="x", device="cpu")
    with pytest.raises(UIClipEvaluationError):
        provider.evaluate(Image.new("RGB", (10, 10)), "A page")


# ---------- Interface declarations ----------


def test_provider_declares_name() -> None:
    assert HuggingFaceUIClipProvider.name == "huggingface"
