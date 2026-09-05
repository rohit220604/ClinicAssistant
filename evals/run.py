"""Run the evaluation.

    python evals/run.py --offline     # deterministic, no API key
    python evals/run.py               # live (needs GROQ_API_KEY)
    python evals/run.py --offline --no-keyword   # force the model path (Part 5 "before")

Prints overall + per-class accuracy, a confusion matrix for intent and for
safety, every failing row, and - separately - the safety false negatives
(labelled EMERGENCY but not caught). Also prints a small latency / LLM-call
summary used by Part 5.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from clinic.classifier import classify_intent  # noqa: E402
from clinic.intents import INTENTS, VERDICTS, Verdict  # noqa: E402
from clinic.llm import get_client  # noqa: E402
from clinic.metrics import percentile  # noqa: E402
from clinic.safety import classify_safety  # noqa: E402

DATASET = pathlib.Path(__file__).with_name("dataset.yaml")

SHORT = {
    "LOG_SYMPTOM": "LOG", "BOOK_APPOINTMENT": "BOOK", "LIST_APPOINTMENTS": "LIST",
    "EMERGENCY": "EMRG", "MEDICAL_ADVICE": "MED", "SMALL_TALK": "TALK",
    "UNKNOWN": "UNK", "SAFE": "SAFE",
}


class CountingClient:
    """Wraps a client and counts how many times the model classifier is called.
    Lets us measure LLM calls per message with and without the keyword router."""

    def __init__(self, client):
        self._client = client
        self.calls = 0
        self.classifier_model = client.classifier_model
        self.chat_model = client.chat_model

    def classify(self, message, kind, timeout=None):
        self.calls += 1
        return self._client.classify(message, kind, timeout)

    def chat(self, *args, **kwargs):
        return self._client.chat(*args, **kwargs)


def load_cases(path=DATASET) -> list[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)["cases"]


def predict(case: dict, client: CountingClient, use_keyword: bool):
    before = client.calls
    start = time.perf_counter()
    safety = classify_safety(case["message"], client, use_keyword=use_keyword, log=False).verdict
    intent = classify_intent(case["message"], client, use_keyword=use_keyword)
    ms = (time.perf_counter() - start) * 1000
    return {"intent": intent, "safety": safety, "llm_calls": client.calls - before, "ms": ms}


def confusion(actuals: list[str], preds: list[str], labels: list[str]) -> dict:
    matrix = {a: {p: 0 for p in labels} for a in labels}
    for a, p in zip(actuals, preds):
        matrix[a][p] += 1
    return matrix


def per_class_recall(actuals: list[str], preds: list[str], labels: list[str]) -> dict:
    out = {}
    for label in labels:
        idx = [i for i, a in enumerate(actuals) if a == label]
        if idx:
            correct = sum(1 for i in idx if preds[i] == label)
            out[label] = (correct, len(idx))
    return out


def print_matrix(title: str, matrix: dict, labels: list[str]) -> None:
    present = [l for l in labels if any(matrix[a][l] or matrix[l][a] for a in labels)]
    width = 5
    header = " " * 6 + "".join(f"{SHORT[l]:>{width}}" for l in present)
    print(f"\n{title} (rows = actual, cols = predicted)")
    print(header)
    for a in present:
        row = "".join(f"{matrix[a][p]:>{width}}" for p in present)
        print(f"{SHORT[a]:>5} {row}")


def run(cases: list[dict], client: CountingClient, use_keyword: bool) -> dict:
    rows = [(c, predict(c, client, use_keyword)) for c in cases]

    intent_actual = [c["intent"] for c, _ in rows]
    intent_pred = [p["intent"] for _, p in rows]
    safety_actual = [c["safety"] for c, _ in rows]
    safety_pred = [p["safety"] for _, p in rows]

    intent_acc = sum(a == b for a, b in zip(intent_actual, intent_pred)) / len(rows)
    safety_acc = sum(a == b for a, b in zip(safety_actual, safety_pred)) / len(rows)

    print("=" * 64)
    print(f"Evaluation on {len(rows)} cases  |  keyword router: {'on' if use_keyword else 'OFF'}")
    print("=" * 64)
    print(f"Intent accuracy : {intent_acc:6.1%}")
    print(f"Safety accuracy : {safety_acc:6.1%}")

    print("\nPer-class recall (intent):")
    for label, (c, n) in per_class_recall(intent_actual, intent_pred, INTENTS).items():
        print(f"  {label:18} {c}/{n}")
    print("Per-class recall (safety):")
    for label, (c, n) in per_class_recall(safety_actual, safety_pred, VERDICTS).items():
        print(f"  {label:18} {c}/{n}")

    print_matrix("Intent confusion", confusion(intent_actual, intent_pred, INTENTS), INTENTS)
    print_matrix("Safety confusion", confusion(safety_actual, safety_pred, VERDICTS), VERDICTS)

    # Failing rows
    print("\nFailing rows (expected -> actual):")
    any_fail = False
    for c, p in rows:
        problems = []
        if p["intent"] != c["intent"]:
            problems.append(f"intent {c['intent']}->{p['intent']}")
        if p["safety"] != c["safety"]:
            problems.append(f"safety {c['safety']}->{p['safety']}")
        if problems:
            any_fail = True
            print(f"  #{c['id']:<2} {c['message'][:48]!r:50} {'; '.join(problems)}")
    if not any_fail:
        print("  (none)")

    # Safety false negatives - reported on their own, they are the only errors
    # here that can hurt someone.
    fns = [(c, p) for c, p in rows if c["safety"] == Verdict.EMERGENCY and p["safety"] != Verdict.EMERGENCY]
    print("\n" + "!" * 64)
    print(f"SAFETY FALSE NEGATIVES (EMERGENCY missed): {len(fns)}")
    for c, p in fns:
        print(f"  #{c['id']} {c['message']!r} -> predicted {p['safety']}")
    print("!" * 64)

    # Emergency precision/recall - the metric that matters when EMERGENCY is rare.
    tp = sum(1 for a, b in zip(safety_actual, safety_pred) if a == b == Verdict.EMERGENCY)
    pred_e = safety_pred.count(Verdict.EMERGENCY)
    actual_e = safety_actual.count(Verdict.EMERGENCY)
    precision = tp / pred_e if pred_e else 0.0
    recall = tp / actual_e if actual_e else 0.0
    print(f"\nEMERGENCY precision: {precision:5.1%}   recall: {recall:5.1%}")

    # Latency + LLM-call summary (feeds Part 5)
    times = [p["ms"] for _, p in rows]
    calls = [p["llm_calls"] for _, p in rows]
    resolved = sum(1 for c in calls if c == 0)
    print("\nLatency / cost:")
    print(f"  classify p50 : {percentile(times, 50):.2f} ms")
    print(f"  classify p95 : {percentile(times, 95):.2f} ms")
    print(f"  avg model classifier calls / msg : {sum(calls) / len(calls):.2f}")
    print(f"  handled by keyword router (0 calls): {resolved}/{len(rows)}")

    return {
        "intent_acc": intent_acc,
        "safety_acc": safety_acc,
        "safety_false_negatives": len(fns),
        "emergency_recall": recall,
        "p50_ms": percentile(times, 50),
        "p95_ms": percentile(times, 95),
        "avg_llm_calls": sum(calls) / len(calls),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Clinic assistant evaluation")
    parser.add_argument("--offline", action="store_true", help="use the deterministic stub")
    parser.add_argument("--no-keyword", action="store_true", help="disable the keyword pre-router")
    parser.add_argument("--dataset", default=str(DATASET))
    args = parser.parse_args()

    client = CountingClient(get_client(args.offline))
    cases = load_cases(args.dataset)
    run(cases, client, use_keyword=not args.no_keyword)


if __name__ == "__main__":
    main()
