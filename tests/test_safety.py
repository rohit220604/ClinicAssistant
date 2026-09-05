from clinic.safety import classify_safety
from clinic.intents import Verdict


class BrokenClient:
    def classify(self, *args, **kwargs):
        raise RuntimeError("API down")


def test_classifier_failure_fails_closed(tmp_path):
    result = classify_safety(
        "book cardiology",
        BrokenClient(),
        timeout=1,
        log=False,
    )

    assert result.verdict == Verdict.EMERGENCY
    assert result.source == "fail_closed"
    assert result.degraded is True
    assert result.is_safe is False