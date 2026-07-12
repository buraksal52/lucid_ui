#!/usr/bin/env python3
"""Manual smoke test for the real UIClip provider.

NOT part of the automated test suite — this downloads and runs the actual
BIG Lab UIClip checkpoint (torch + transformers), which the test suite must
never require (see CLAUDE.md, "Tests must not require ... UIClip ... GPU").
Run it by hand to confirm the real provider actually works end to end on
your machine:

    cd backend
    source .venv/bin/activate
    python scripts/uiclip_smoke_test.py \\
        --image /path/to/screenshot.png \\
        --description "A settings screen with a dark sidebar and a save button"

Optional flags: --model-id, --device (default to whatever is configured in
Settings, i.e. .env / .env.example).
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.uiclip.huggingface_provider import HuggingFaceUIClipProvider  # noqa: E402


def main() -> None:
    settings = get_settings()

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image", required=True, type=Path, help="Path to a local screenshot image.")
    parser.add_argument("--description", required=True, help="Natural-language description of the UI.")
    parser.add_argument("--model-id", default=settings.uiclip_model_id, help="Hugging Face checkpoint ID.")
    parser.add_argument("--device", default=settings.uiclip_device, help="cpu | mps | cuda | auto")
    args = parser.parse_args()

    if not args.image.is_file():
        parser.error(f"Image not found: {args.image}")

    print(f"Loading model {args.model_id!r} (requested device={args.device!r}) ...")
    load_start = time.monotonic()
    provider = HuggingFaceUIClipProvider(model_id=args.model_id, device=args.device)
    load_ms = round((time.monotonic() - load_start) * 1000)
    print(f"Model loaded in {load_ms} ms on resolved device: {provider.device!r}")

    image = Image.open(args.image).convert("RGB")

    eval_start = time.monotonic()
    result = provider.evaluate(image, args.description)
    inference_ms = round((time.monotonic() - eval_start) * 1000)

    print()
    print("image:            ", args.image)
    print("description:      ", args.description)
    print("model_id:         ", args.model_id)
    print("device:           ", provider.device)
    print("model_version:    ", result["model_version"])
    print("raw_score:        ", result["raw_score"])
    print("inference_time_ms:", inference_ms)


if __name__ == "__main__":
    main()
