"""
Mojibake repair.

29 of 36 legacy CMS pages carry double-encoded UTF-8. Repair must fix those
without corrupting text that is already correct -- an over-eager repair is worse
than none, because it damages good data silently.
"""

import pytest

from legacy_import.text import clean, clean_email, clean_phone, looks_mojibake, repair_mojibake


class TestRepairsDamage:
    @pytest.mark.parametrize(
        ("damaged", "expected"),
        [
            ("youâ\x80\x99re", "you’re"),          # U+2019 read as latin1
            ("cafÃ©", "café"),                       # U+00E9 read as latin1
            ("MÃ¼ller", "Müller"),
            ("ZoÃ«", "Zoë"),
            ("you\x92re", "you’re"),                # cp1252 smart quote
            ("dashâ\x80\x93here", "dash–here"),      # en dash
        ],
    )
    def test_damaged_text_is_recovered(self, damaged, expected):
        assert repair_mojibake(damaged) == expected


class TestLeavesCleanTextAlone:
    @pytest.mark.parametrize(
        "text",
        [
            "plain ascii text",
            "Zoë Müller",              # already correct UTF-8
            "café",
            "M&M Austin Limousine",
            "you're",                  # straight apostrophe
            "price: $95.00",
            "",
        ],
    )
    def test_clean_text_is_unchanged(self, text):
        assert repair_mojibake(text) == text

    def test_none_passes_through(self):
        assert repair_mojibake(None) is None

    def test_repair_is_idempotent(self):
        once = repair_mojibake("youâ\x80\x99re")
        assert repair_mojibake(once) == once


class TestDetection:
    def test_detects_damage(self):
        assert looks_mojibake("youâ\x80\x99re")
        assert looks_mojibake("cafÃ©")

    def test_does_not_flag_clean_text(self):
        assert not looks_mojibake("café")
        assert not looks_mojibake("plain")
        assert not looks_mojibake("")


class TestClean:
    def test_collapses_whitespace_and_strips(self):
        assert clean("  hello    world  ") == "hello world"

    def test_removes_null_bytes(self):
        assert clean("bad\x00value") == "badvalue"

    def test_truncates_to_max_length(self):
        assert clean("abcdefghij", max_length=4) == "abcd"

    def test_none_becomes_empty_string(self):
        assert clean(None) == ""

    def test_repairs_while_cleaning(self):
        assert clean("  cafÃ©  ") == "café"


class TestCleanEmail:
    def test_lowercases(self):
        assert clean_email("John.Smith@Example.COM") == "john.smith@example.com"

    def test_strips_surrounding_space(self):
        assert clean_email("  a@b.com ") == "a@b.com"


class TestCleanPhone:
    def test_keeps_common_formatting(self):
        assert clean_phone("+1 (512) 555-0134") == "+1 (512) 555-0134"

    def test_strips_letters_and_noise(self):
        assert clean_phone("call 512-555-0134 asap") == "512-555-0134"

    def test_truncates(self):
        assert len(clean_phone("1" * 80)) <= 32
