# LucidUI backend — see CLAUDE.md/ROADMAP.md Phase 11 ("Production Readiness").
#
# Tesseract (pytesseract wraps the external binary, not pip-installable) and
# OpenCV's runtime shared libraries (opencv-python-headless still needs
# libgl1/libglib2.0 at the OS level despite excluding GUI bindings) are not
# available on Railway's default Nixpacks builder, so this image is required
# rather than optional — see requirements.txt for why torch/transformers are
# also always installed (the real UIClip provider, `UICLIP_PROVIDER=huggingface`).
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# torch's default PyPI wheel bundles CUDA runtimes (multi-GB) even though
# this container only ever runs UIClip on CPU. That size blows past Railway
# free-tier build/image and memory limits, so install the CPU-only build
# from PyTorch's own index first, matching the version range pinned in
# requirements.txt. pip then finds `torch` already satisfied and skips it
# when installing the rest of requirements.txt below.
RUN pip install --no-cache-dir "torch>=2.2,<3.0" --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# Railway injects $PORT at runtime; 8000 is the local-dev fallback only.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
