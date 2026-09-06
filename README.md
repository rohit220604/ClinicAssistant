# Clinic Assistant

A small **agentic** assistant for a clinic. Patients type in plain text — English,
Hindi (Devanagari), or Hinglish — and the assistant can:

1. **Log a symptom**
2. **Book an appointment**
3. **List a patient's appointments**
4. **Refuse to act as a doctor** — no diagnosis, no prescriptions
5. **Escalate a medical emergency** instead of handling it
6. Work in **English and Hindi/Hinglish**, and reply in the same language

Everything hard lives in 4–6 (the safety gate) and in proving it works (the eval).

---

## Quick start (clean clone → running in a few minutes)

```powershell
# 1. create + activate a virtual env
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 2. install
pip install -r requirements.txt

# 3. (optional) add a Groq key for LIVE mode
copy .env.example .env          # then edit GROQ_API_KEY
```

Everything below runs **without an API key** using `--offline` (a deterministic
stub). A `GROQ_API_KEY` is only needed for live LLM behaviour.

```powershell
# Chat (offline stub, no key)
python cli.py --offline --patient p1

# Chat (live, needs GROQ_API_KEY)
python cli.py --patient p1

# Evaluation: accuracy, per-class, confusion matrices, failing rows, safety FNs
python evals/run.py --offline

# Part 5 "before/after": model classifier calls with vs without the pre-router
python evals/run.py --offline --no-keyword    # before
python evals/run.py --offline                 # after

# Latency (p50/p95) via the real JSONL logging path
python evals/measure.py --offline

# Tests (safety failure paths, idempotency, slots, failure paths, graph parity)
pytest -q
```

Try these in the CLI: `I have a headache` → `3`, `book cardiology` →
`2026-10-10`, `my appointments`, `seene mein dard ho raha hai` (Hinglish
emergency), `which medicine should I take for fever` (medical advice).

---

## The fixed contract

Implemented exactly as specified, in [clinic/tools.py](clinic/tools.py):

```python
log_symptom(patient_id: str, symptom: str, severity: int) -> dict      # severity 1-5
book_appointment(patient_id: str, department: str, date: str) -> dict  # ISO date
list_appointments(patient_id: str) -> list[dict]
```

Import from either place:

```python
from clinic import log_symptom, book_appointment, list_appointments
# or
from agent import log_symptom, book_appointment, list_appointments
```

Storage is a **single JSON file** at `data/clinic_store.json` (created on first
write, git-ignored). No database, no Docker, no cloud.

---

## How it is put together

Each concern is its own small module, so adding a language, a tool, or a keyword
is a one-file change (see [decision.md](decision.md)).

| File | Responsibility |
| --- | --- |
| [agent.py](agent.py) | **Part 1** — the agent loop: safety gate → tool-calling → slot filling → cap → failure paths |
| [graph.py](graph.py) | **Part 2** — the routing decision as a LangGraph graph (typed state, pure nodes, one conditional edge) |
| [clinic/safety.py](clinic/safety.py) | **Part 3** — the safety gate; fail-closed on classifier failure; countable logging |
| [clinic/tools.py](clinic/tools.py) | the three contract functions (idempotent booking) |
| [clinic/llm.py](clinic/llm.py) | Groq client + deterministic offline stub, one interface |
| [clinic/rules.py](clinic/rules.py) | multilingual keyword tables (offline stub + fast pre-router) |
| [clinic/classifier.py](clinic/classifier.py) | intent classification with keyword fast-path |
| [clinic/slots.py](clinic/slots.py) | slot extraction (department / date / severity) |
| [clinic/prompts.py](clinic/prompts.py) | the system prompt (built per turn) |
| [clinic/responses.py](clinic/responses.py) | localized canned replies (en / hi / hinglish) |
| [clinic/language.py](clinic/language.py) | language detection + script-purity check (stretch A) |
| [clinic/state.py](clinic/state.py) | multi-turn conversation state |
| [clinic/storage.py](clinic/storage.py) | atomic single-file JSON persistence |
| [clinic/metrics.py](clinic/metrics.py) | latency JSONL logging + p50/p95 |
| [clinic/config.py](clinic/config.py) | settings + paths |
| [evals/](evals/) | dataset, runner, latency measurement |

---

## Part 1 — README answers

**1. What belongs in state, and what belongs in the prompt?**
State holds the durable facts that must survive across turns and that the model
must never fabricate: `patient_id`, the detected `language`, and the running
message history (which is also the half-filled booking — "what has been
collected so far"). The prompt holds instructions plus the small fresh facts the
model needs to phrase a correct reply *this* turn: the system rules, today's
date, and a read-only copy of `patient_id`/`language`. Rule of thumb — if losing
it breaks the next turn, it's state; if it's guidance or a per-turn fact the
model reads but shouldn't own, it's prompt. `patient_id` is the clearest case: it
lives in state and is injected into every tool call by our code, never taken from
the model.

**2. How do you stop the model inventing an argument it was never given?**
Three layers. The system prompt explicitly tells the model to *ask* for a missing
department/date/severity and not to call the tool until it has them. `patient_id`
is never a model-supplied argument at all — the registry injects it from state,
so the model physically cannot invent which patient it is acting for. And the
tools validate every argument (ISO date, severity 1–5) and raise on bad input,
with required-argument schemas, so a guessed or missing field is rejected at the
boundary rather than silently accepted.

**3. What does your agent do on a malformed tool call — and what should it do?**
It catches the malformed arguments (JSON that won't parse, or isn't an object)
and feeds a structured `{"error": ...}` back to the model as the tool result, so
the model can correct itself or ask the patient — it does not crash. The same
pattern covers the other two failure paths: an unknown tool name and a tool that
raises both return an error result instead of propagating. That is also what it
*should* do: a front-desk assistant must degrade gracefully, and the one thing it
must never do is fabricate a successful result.

**4. How many LLM calls does a one-tool turn cost, and how would you reduce it?**
A safe one-tool turn costs up to three: one safety classification, one chat call
that emits the tool call, and one chat call that reads the tool result and writes
the reply. The keyword pre-router already removes the classification call for
obvious messages (avg model classifier calls/msg dropped **2.00 → 0.71** on the
eval set; 12/34 messages required zero model classifier calls). Further wins: a smaller model for
classification only (already configurable), running the safety and intent
classifiers concurrently, and templating boilerplate confirmations (e.g. a
booking success) instead of a third round-trip.

---

## Part 3 — the safety gate, briefly

Every message is classified **before** any routing or tool call into
`EMERGENCY` / `MEDICAL_ADVICE` / `SAFE`. Only `SAFE` proceeds to the tool loop;
the other two return canned guidance and run **zero tools**.

When the classifier itself fails (timeout, rate limit, API error) we **fail
closed**: block, show cautious guidance, run no tools, and write a
`degraded=true` line to `logs/safety.jsonl` so failures are countable
(`clinic.safety.failure_count()`). Full argument in [decision.md](decision.md).

---

## Part 2 — what the graph bought / cost

**Bought:** the routing decision is now explicit and inspectable — `classify → (SAFE?)
→ act | respond` with one real conditional edge on the verdict, a typed state
object, and pure `state -> state` nodes that are trivial to test in isolation.
**Cost:** a dependency (LangGraph), a second code path to keep in step with the
loop, and a little object-passing ceremony in the state dict. Behaviour is
identical — `tests/test_graph.py` asserts the graph and the plain loop produce
the same reply/verdict/blocked for every message.

---

## What I cut, and why (timeboxed honestly)

- **Live latency numbers.** The latency harness is built and runs, and it logs
  per-turn and per-LLM-call latency to `logs/latency.jsonl`. I report **offline**
  p50/p95 (real, but sub-millisecond because the stub has no network) plus the
  **model-call reduction** from the pre-router, which is the real mechanism of
  the live speedup. The live p50/p95 table needs a `GROQ_API_KEY`; the exact
  command is `python evals/measure.py` (no `--offline`).
- **A benchmarked smaller classifier model.** The classifier model is a separate,
  configurable setting (`CLINIC_CLASSIFIER_MODEL`) but I did not benchmark model
  variants.
- **Deep offline slot extraction.** The offline stub fills slots with light
  regex/keyword heuristics (good enough for a key-free demo and tests); the live
  model does the nuanced extraction.

Nothing on the never-cut list was cut: the safety gate's failure-path tests and a
runnable eval are both present.

---

## Ground rules

- No secrets in the repo — see [.env.example](.env.example); `.env`, `data/`, and
  `logs/` are git-ignored.
- Everything runs from a clean clone with the commands above; `--offline` needs no
  key.
- Grader's held-out eval: drop a YAML with the same shape as
  [evals/dataset.yaml](evals/dataset.yaml) and run
  `python evals/run.py --offline --dataset path/to/your.yaml`.
