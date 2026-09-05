"""Drive the dataset through the full agent so the real latency logger runs, then
report p50/p95 from logs/latency.jsonl.

    python evals/measure.py --offline        # deterministic
    python evals/measure.py                   # live (needs GROQ_API_KEY)

This is the Part 5 measurement: per-turn and per-LLM-call latency are appended to
the JSONL by the agent itself (clinic/metrics.py); we just summarise them.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from agent import Agent, new_state  # noqa: E402
from clinic.config import LATENCY_LOG  # noqa: E402
from clinic.metrics import summarise  # noqa: E402

DATASET = pathlib.Path(__file__).with_name("dataset.yaml")


def main() -> None:
    parser = argparse.ArgumentParser(description="Latency measurement over the eval set")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--keep", action="store_true", help="append to the existing log instead of starting fresh")
    args = parser.parse_args()

    if not args.keep and LATENCY_LOG.exists():
        LATENCY_LOG.unlink()

    with open(DATASET, "r", encoding="utf-8") as fh:
        cases = yaml.safe_load(fh)["cases"]

    agent = Agent(offline=args.offline)
    for i, case in enumerate(cases):
        agent.run_turn(new_state(f"eval-{i}"), case["message"])

    stats = summarise()
    print(f"Turns measured        : {stats['turns']}")
    print(f"Per-turn latency  p50 : {stats['turn_p50']:.2f} ms   p95 : {stats['turn_p95']:.2f} ms")
    print(f"Per-LLM-call      p50 : {stats['llm_p50']:.2f} ms   p95 : {stats['llm_p95']:.2f} ms")
    print(f"Avg LLM calls / turn  : {stats['avg_llm_calls_per_turn']:.2f}")


if __name__ == "__main__":
    main()
