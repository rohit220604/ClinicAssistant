"""Language detection + Stretch A: the script-purity check.

The stretch asks that a Devanagari reply must not leak romanized Latin ("aap"
where it should be "आप"). We check the utility and, more usefully, assert that
every Hindi canned reply we ship is actually script-pure.
"""
from __future__ import annotations

import pytest

from clinic.language import detect_language, script_purity_ok
from clinic.responses import RESPONSES


@pytest.mark.parametrize(
    "text,expected",
    [
        ("I want to book an appointment", "en"),
        ("book cardiology on 2026-10-10", "en"),
        ("mujhe bukhar hai", "hinglish"),
        ("seene mein dard ho raha hai", "hinglish"),
        ("मुझे बुखार है", "hi"),
        ("सीने में दर्द है", "hi"),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_script_purity_flags_romanized_leak():
    assert script_purity_ok("आप कैसे हैं", "hi") is True
    assert script_purity_ok("aap kaise hain", "hi") is False  # Latin leak
    assert script_purity_ok("aap kaise hain", "hinglish") is True  # not expected pure


def test_all_hindi_canned_replies_are_script_pure():
    for key, variants in RESPONSES.items():
        assert script_purity_ok(variants["hi"], "hi"), f"Latin leaked in {key}[hi]"
