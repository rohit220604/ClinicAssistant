import pytest

from clinic.tools import book_appointment, list_appointments, log_symptom


def test_log_symptom_records():
    rec = log_symptom("p1", "headache", 3)
    assert rec["patient_id"] == "p1"
    assert rec["symptom"] == "headache"
    assert rec["severity"] == 3


@pytest.mark.parametrize("bad", [0, 6, -1])
def test_log_symptom_rejects_out_of_range_severity(bad):
    with pytest.raises(ValueError):
        log_symptom("p1", "headache", bad)


def test_log_symptom_rejects_non_int_severity():
    with pytest.raises(ValueError):
        log_symptom("p1", "headache", True)  # bool is not a valid severity


def test_book_requires_iso_date():
    with pytest.raises(ValueError):
        book_appointment("p1", "cardiology", "next tuesday")


def test_list_returns_only_this_patient_sorted():
    book_appointment("p1", "cardiology", "2026-12-01")
    book_appointment("p1", "dermatology", "2026-11-01")
    book_appointment("p2", "ent", "2026-10-01")

    mine = list_appointments("p1")
    assert [a["department"] for a in mine] == ["dermatology", "cardiology"]
