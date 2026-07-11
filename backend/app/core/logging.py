"""Minimal standard-library logging setup.

Deliberately simple for Phase 1 — no external logging packages. Never logs
user-supplied description text at info level, secrets, or (in later phases)
raw image bytes, per CLAUDE.md.
"""

import logging


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def get_logger(name: str = "lucidui") -> logging.Logger:
    return logging.getLogger(name)
