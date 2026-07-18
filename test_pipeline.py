"""Offline unit tests for pipeline.py's deterministic functions - no API key needed."""
import pandas as pd

from pipeline import cluster_key, extract_json, normalize_company, normalize_phone


def test_normalize_company_strips_suffixes_and_cases():
    assert normalize_company("Northgate Logistics") == "northgate logistics"
    assert normalize_company("Northgate Logistics Inc.") == "northgate logistics"
    assert normalize_company("Brightfield Consulting LLC") == "brightfield consulting"
    assert normalize_company("Meridian Supply Co") == "meridian supply"


def test_normalize_company_handles_empty():
    assert normalize_company("") == ""
    assert normalize_company(None) == ""


def test_normalize_phone_formats_ten_digits():
    assert normalize_phone("555-201-4471") == "(555) 201-4471"
    assert normalize_phone("(555) 201-4471") == "(555) 201-4471"
    assert normalize_phone("5552014471") == "(555) 201-4471"


def test_normalize_phone_leaves_malformed_input_alone():
    assert normalize_phone("123") == "123"
    assert normalize_phone("") == ""


def test_cluster_key_groups_by_lastname_and_normalized_company():
    row_a = pd.Series({"last_name": "Wu", "company": "northgate logistics"})
    row_b = pd.Series({"last_name": "Wu", "company": "Northgate Logistics"})
    assert cluster_key(row_a) == cluster_key(row_b)


def test_cluster_key_differs_for_different_people():
    row_a = pd.Series({"last_name": "Wu", "company": "Northgate Logistics"})
    row_b = pd.Series({"last_name": "Baptiste", "company": "DelCorp Trading"})
    assert cluster_key(row_a) != cluster_key(row_b)


def test_extract_json_strips_markdown_fences():
    fenced = '```json\n{"a": 1}\n```'
    assert extract_json(fenced) == {"a": 1}


def test_extract_json_handles_bare_json():
    assert extract_json('{"a": 1}') == {"a": 1}
