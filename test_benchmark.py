"""Offline unit tests for benchmark.py's deterministic functions - no API key needed."""
import pandas as pd
import pytest

from benchmark import blocking_key, extract_json


def test_blocking_key_uses_surname_when_present():
    row = pd.Series({"surname": "Waller", "given_name": "Kayla", "postcode": "4011"})
    assert blocking_key(row) == "surname:wall"


def test_blocking_key_falls_back_to_given_name_when_surname_missing():
    row = pd.Series({"surname": float("nan"), "given_name": "Lachlan", "postcode": "4814"})
    assert blocking_key(row) == "given_name:lach"


def test_blocking_key_falls_back_to_postcode_when_names_missing():
    row = pd.Series({"surname": float("nan"), "given_name": float("nan"), "postcode": "4011"})
    assert blocking_key(row) == "postcode:4011"


def test_blocking_key_returns_none_when_everything_missing():
    row = pd.Series({"surname": float("nan"), "given_name": float("nan"), "postcode": float("nan")})
    assert blocking_key(row) is None


def test_extract_json_strips_fences():
    assert extract_json('```json\n[{"a": 1}]\n```') == [{"a": 1}]


def test_extract_json_rejects_malformed_json():
    with pytest.raises(Exception):
        extract_json("not json at all")
