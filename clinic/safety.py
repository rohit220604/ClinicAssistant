"""The safety gate (Part 3).

Every message passes through here BEFORE any routing or tool call. It returns one
of three verdicts - EMERGENCY, MEDICAL_ADVICE, SAFE - and the loop refuses to run
any tool unless the verdict is SAFE.

Fail-closed by choice: if the classifier itself fails (timeout, rate limit, API
error) we do NOT let the message through. In a clinic, a missed emergency is the
one error that can hurt someone, so on failure we block and show cautious
guidance. Every failure is written to logs/safety.jsonl with degraded=true so it
is countable, not invisible. (See decision.md for the full argument.)
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from clinic.config import SAFETY_LOG, settings
from clinic.intents import Verdict
from clinic.metrics import append_jsonl
from clinic.rules import keyword_safety

_POOL = ThreadPoolExecutor(max_workers=4)


@dataclass
class SafetyResult:
    verdict: str
    source: str          # "keyword" | "llm" | "fail_closed"
    degraded: bool       # True when the classifier failed and we fell back
    latency_ms: float

    @property
    def is_safe(self) -> bool:
        return self.verdict == Verdict.SAFE and not self.degraded


def _run_with_timeout(fn, timeout: float):
    """Run fn() but give up after `timeout` seconds. A stuck classifier must not
    stall the whole turn - giving up here is what makes fail-closed possible."""
    future = _POOL.submit(fn)
    return future.result(timeout=timeout)


def classify_safety(
    message: str,
    client,
    use_keyword: bool = True,
    timeout: float | None = None,
    log: bool = True,
) -> SafetyResult:
    start = time.perf_counter()
    timeout = timeout if timeout is not None else settings.classifier_timeout

    # Fast, deterministic path for the obvious cases. Also means a clear
    # emergency is caught even if the LLM is down.
    if use_keyword:
        kw = keyword_safety(message)
        if kw is not None:
            return _finish(SafetyResult(kw, "keyword", False, _ms(start)), message, log)

    try:
        verdict = _run_with_timeout(lambda: client.classify(message, "safety", timeout), timeout)
        result = SafetyResult(verdict, "llm", False, _ms(start))
    except Exception:
        # Any failure - timeout, rate limit, API error - fails closed: we block
        # and treat the message as unverified/unsafe.
        result = SafetyResult(Verdict.EMERGENCY, "fail_closed", True, _ms(start))

    return _finish(result, message, log)


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def _finish(result: SafetyResult, message: str, log: bool) -> SafetyResult:
    if log:
        append_jsonl(
            SAFETY_LOG,
            {
                "ts": time.time(),
                "verdict": result.verdict,
                "source": result.source,
                "degraded": result.degraded,
                "latency_ms": round(result.latency_ms, 2),
                "preview": message[:80],
            },
        )
    return result


def failure_count(path=SAFETY_LOG) -> int:
    """How many times the classifier failed and we fell back. Countable, per the
    assignment."""
    from clinic.metrics import read_jsonl

    return sum(1 for r in read_jsonl(path) if r.get("degraded"))
