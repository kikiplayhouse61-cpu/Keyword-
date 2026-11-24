import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import find_matching_keywords, build_message_key, truncate, paginate


def test_case_insensitive_match():
    matched = find_matching_keywords("I NEED POP urgently", ["Need Pop"])
    assert "Need Pop" in matched


def test_lowercase_match():
    matched = find_matching_keywords("hello i need pop", ["Need Pop"])
    assert "Need Pop" in matched


def test_mixed_case_match():
    matched = find_matching_keywords("Hello, I Need Pop urgently", ["Need Pop"])
    assert "Need Pop" in matched


def test_multiple_keywords():
    matched = find_matching_keywords("I need pop and netflix", ["Need Pop", "Netflix"])
    assert "Need Pop" in matched
    assert "Netflix" in matched


def test_no_match():
    matched = find_matching_keywords("Hello everyone", ["Need Pop"])
    assert matched == []


def test_empty_text():
    matched = find_matching_keywords("", ["Need Pop"])
    assert matched == []


def test_empty_keywords():
    matched = find_matching_keywords("Need Pop", [])
    assert matched == []


def test_message_key():
    key = build_message_key(123, 456)
    assert key == "123:456"


def test_truncate():
    assert truncate("hello", 10) == "hello"
    assert truncate("a" * 300, 200).endswith("…")
    assert len(truncate("a" * 300, 200)) == 201


def test_paginate():
    items = list(range(25))
    page_items, total_pages, page = paginate(items, 0, 10)
    assert len(page_items) == 10
    assert total_pages == 3
    assert page == 0

    page_items2, _, page2 = paginate(items, 2, 10)
    assert len(page_items2) == 5
    assert page2 == 2


def test_paginate_out_of_bounds():
    items = list(range(5))
    page_items, total_pages, page = paginate(items, 99, 10)
    # Clamped to last valid page (0 since there's only 1 page)
    assert page == 0
    assert total_pages == 1

def test_paginate_out_of_bounds_multi_page():
    items = list(range(25))
    page_items, total_pages, page = paginate(items, 99, 10)
    # Clamped to last valid page = 2
    assert page == total_pages - 1


def test_available_keyword():
    matched = find_matching_keywords("Is anyone available?", ["Available"])
    assert "Available" in matched


def test_phrase_keyword():
    matched = find_matching_keywords("I need OTT subscription today", ["Need OTT"])
    assert "Need OTT" in matched
