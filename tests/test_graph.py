"""Part 2 - the graph must not change behaviour vs the plain loop."""
from __future__ import annotations

from agent import Agent, new_state
from graph import GraphAgent

MESSAGES = [
    "I have a headache",
    "3",
    "book cardiology",
    "2026-10-10",
    "my appointments",
    "seene mein dard ho raha hai",
    "which medicine should I take for fever",
]


def test_graph_matches_plain_loop():
    loop = Agent(offline=True)
    loop_state = new_state("pa")
    graph = GraphAgent(Agent(offline=True))
    graph_state = new_state("pb")

    for message in MESSAGES:
        r_loop = loop.run_turn(loop_state, message)
        r_graph = graph.run_turn(graph_state, message)
        assert r_loop.reply == r_graph.reply
        assert r_loop.verdict == r_graph.verdict
        assert r_loop.blocked == r_graph.blocked
