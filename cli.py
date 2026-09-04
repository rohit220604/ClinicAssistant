"""Command-line chat for the clinic assistant.

    python cli.py --patient p1            # live (needs GROQ_API_KEY)
    python cli.py --patient p1 --offline  # deterministic, no key needed

Type 'quit' or press Ctrl-D to exit.
"""
from __future__ import annotations

import argparse

from agent import Agent, new_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Clinic assistant CLI")
    parser.add_argument("--patient", default="cli-user", help="patient id for this session")
    parser.add_argument("--offline", action="store_true", help="use the deterministic stub (no API key)")
    args = parser.parse_args()

    agent = Agent(offline=args.offline)
    state = new_state(args.patient)

    mode = "offline stub" if agent.offline else "live (Groq)"
    print(f"Clinic assistant [{mode}] - patient '{args.patient}'. Type 'quit' to exit.\n")

    while True:
        try:
            message = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not message:
            continue
        if message.lower() in {"quit", "exit"}:
            break
        result = agent.run_turn(state, message)
        print(f"bot> {result.reply}\n")


if __name__ == "__main__":
    main()
