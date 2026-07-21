"""Deterministic display-string formatting for the Presentation Report layer.

Formats already-computed numeric values for display only. Rounding here
never changes the underlying numeric value stored elsewhere in the report
(e.g. `lucidui.raw`, `lucidui.weightedScore`) — those are passed through
unchanged; only these derived strings are rounded, per CLAUDE.md ("Never
discard raw values").
"""

NO_DATA_DISPLAY = "No data available"


def format_ratio_to_one(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return NO_DATA_DISPLAY
    return f"{value:.{decimals}f}:1"


def format_decimal(value: float | None, decimals: int = 4) -> str:
    if value is None:
        return NO_DATA_DISPLAY
    return f"{value:.{decimals}f}"


def format_percentage(ratio: float | None, decimals: int = 2) -> str:
    if ratio is None:
        return NO_DATA_DISPLAY
    return f"{ratio * 100:.{decimals}f}%"


def format_ms(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return NO_DATA_DISPLAY
    return f"{value:.{decimals}f} ms"


def format_fraction(numerator: int | None, denominator: int | None) -> str:
    if numerator is None or denominator is None:
        return NO_DATA_DISPLAY
    return f"{numerator} / {denominator}"


def format_count(value: int | None, unit: str) -> str:
    if value is None:
        return NO_DATA_DISPLAY
    return f"{value} {unit}"


def format_plain(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return NO_DATA_DISPLAY
    return f"{value:.{decimals}f}"


def format_score_over_100(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f} / 100"


def format_delta(value: float | None, decimals: int = 2) -> str:
    """Formats a signed difference (e.g. a variant-comparison delta).

    Always shows an explicit sign for positive values so the direction is
    unambiguous at a glance; negative values already carry their own `-` via
    the format spec, zero shows no sign.
    """
    if value is None:
        return NO_DATA_DISPLAY
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}"
