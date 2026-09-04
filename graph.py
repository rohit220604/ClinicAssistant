r"""Part 2 - the routing decision expressed as a LangGraph graph.

This does NOT reimplement anything. The nodes call the exact same Agent steps the
plain loop uses (_safety_step, block_reply, _model_loop), so behaviour is
identical - the graph only makes the routing explicit:

    START -> classify --(conditional on verdict)--> act ----> END
                                                \--> respond -> END

- classify: run the safety gate, write the verdict into state.
- conditional edge: SAFE goes to `act`; EMERGENCY / MEDICAL_ADVICE / a failed
  classifier go to `respond`.
- act: run the tool-calling loop and produce a reply.
- respond: produce the canned safe reply, no tools.

State is a TypedDict of plain values plus the two objects the nodes need to do
their work. Every node is a pure state -> partial-state function with no globals.
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agent import Agent, TurnResult
from clinic.intents import Verdict
from clinic.metrics import log_turn, stopwatch
from clinic.state import ConversationState


class RouterState(TypedDict, total=False):
    message: str
    language: str
    verdict: str
    source: str
    degraded: bool
    blocked: bool
    reply: str
    llm_calls: int
    tool_calls: int
    tools_used: list[str]
    agent: Any
    conv: Any


def classify_node(state: RouterState) -> RouterState:
    agent: Agent = state["agent"]
    lang, safety, llm_calls = agent._safety_step(state["message"])
    state["conv"].language = lang
    return {
        "language": lang,
        "verdict": safety.verdict,
        "source": safety.source,
        "degraded": safety.degraded,
        "llm_calls": llm_calls,
    }


def act_node(state: RouterState) -> RouterState:
    agent: Agent = state["agent"]
    reply, tool_calls, tools_used, chat_llm_calls = agent._model_loop(
        state["conv"], state["message"], state["language"]
    )
    return {
        "reply": reply,
        "blocked": False,
        "tool_calls": tool_calls,
        "tools_used": tools_used,
        "llm_calls": state["llm_calls"] + chat_llm_calls,
    }


def respond_node(state: RouterState) -> RouterState:
    agent: Agent = state["agent"]
    reply = agent.block_reply(state["verdict"], state["degraded"], state["language"])
    return {"reply": reply, "blocked": True, "tool_calls": 0, "tools_used": []}


def route_on_verdict(state: RouterState) -> str:
    """The one conditional edge: only a clean SAFE verdict may act."""
    if state["degraded"] or state["verdict"] != Verdict.SAFE:
        return "respond"
    return "act"


def build_router():
    graph = StateGraph(RouterState)
    graph.add_node("classify", classify_node)
    graph.add_node("act", act_node)
    graph.add_node("respond", respond_node)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", route_on_verdict, {"act": "act", "respond": "respond"})
    graph.add_edge("act", END)
    graph.add_edge("respond", END)
    return graph.compile()


ROUTER = build_router()


class GraphAgent:
    """Same public shape as Agent.run_turn, but routed through the graph."""

    def __init__(self, agent: Agent | None = None, offline: bool = False):
        self.agent = agent or Agent(offline=offline)
        self.offline = self.agent.offline
        self.graph = ROUTER

    def run_turn(self, state: ConversationState, message: str) -> TurnResult:
        with stopwatch() as elapsed:
            out = self.graph.invoke({"message": message, "agent": self.agent, "conv": state})
            log_turn(elapsed(), out.get("llm_calls", 0), self.offline)
            return TurnResult(
                out["reply"], out["verdict"], out["source"], out["blocked"],
                out.get("degraded", False), out.get("tool_calls", 0),
                out.get("llm_calls", 0), elapsed(), out.get("tools_used", []),
            )
