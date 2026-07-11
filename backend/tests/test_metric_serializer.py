import numpy as np
import pytest

from app.metrics.serializer import to_json_safe


def test_converts_numpy_int32() -> None:
    result = to_json_safe(np.int32(7))
    assert result == 7
    assert isinstance(result, int)


def test_converts_numpy_int64() -> None:
    result = to_json_safe(np.int64(9))
    assert result == 9
    assert isinstance(result, int)


def test_converts_numpy_float32() -> None:
    result = to_json_safe(np.float32(1.5))
    assert result == 1.5
    assert isinstance(result, float)


def test_converts_numpy_float64() -> None:
    result = to_json_safe(np.float64(2.25))
    assert result == 2.25
    assert isinstance(result, float)


def test_converts_numpy_array_to_list() -> None:
    result = to_json_safe(np.array([1, 2, 3]))
    assert result == [1, 2, 3]
    assert isinstance(result, list)


def test_converts_nested_dictionaries() -> None:
    value = {"a": np.float64(1.0), "b": {"c": np.int32(2), "d": [np.int32(3), np.int32(4)]}}
    result = to_json_safe(value)
    assert result == {"a": 1.0, "b": {"c": 2, "d": [3, 4]}}
    assert isinstance(result["a"], float)
    assert isinstance(result["b"]["c"], int)
    assert isinstance(result["b"]["d"][0], int)


def test_converts_lists_and_tuples() -> None:
    assert to_json_safe([np.int32(1), np.int32(2)]) == [1, 2]
    assert to_json_safe((np.int32(1), np.int32(2))) == [1, 2]
    assert isinstance(to_json_safe((1, 2)), list)


def test_preserves_none() -> None:
    assert to_json_safe(None) is None
    assert to_json_safe({"a": None, "b": [None, 1]}) == {"a": None, "b": [None, 1]}


def test_preserves_plain_python_values_unchanged() -> None:
    assert to_json_safe(387.7) == 387.7
    assert to_json_safe("averageContrastRatio") == "averageContrastRatio"
    assert to_json_safe(True) is True
    assert to_json_safe(5) == 5


def test_does_not_change_precision_of_already_rounded_values() -> None:
    rounded = round(387.66666, 1)
    assert to_json_safe(np.float64(rounded)) == pytest.approx(rounded)
    assert to_json_safe(np.float64(rounded)) == 387.7
