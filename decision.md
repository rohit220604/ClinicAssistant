# Design decisions

Why the code looks the way it does, and how to extend it with the smallest
possible change. Written so I can explain any part of it in the demo.

---

## 1. Fail-closed on classifier failure (the one that matters)

**Decision: fail closed.** If the safety classifier raises, rate-limits, or times
out, the assistant **blocks the message**, shows cautious guidance (contact
emergency services / try again), and runs **no tools**.

**Why.** In a clinic the errors are not symmetric. A missed emergency can hurt
someone; a wrongly-blocked booking is an annoyance the patient can retry. The
brief says it directly — "a fast agent that misses one emergency is worse than a
slow agent that does not." Fail-open optimises availability; for a safety gate in
a medical context, availability is the wrong thing to optimise. So on any
classifier failure we treat the message as *unverified = potentially unsafe* and
refuse to act.

**What it costs.** Some perfectly safe messages get blocked during an outage.
That is the deliberate trade. We make it visible instead of silent: every failure
is written to `logs/safety.jsonl` with `degraded=true`, and
`clinic.safety.failure_count()` counts them, so we can see exactly how often the
fallback fired and tune the timeout.

**The keyword safety net.** Fail-closed does not mean useless during an outage.
The deterministic keyword layer runs first, so a clear emergency ("chest pain",
"साँस नहीं", "seene mein dard") is still caught even with the LLM completely down.

**When I would revisit it.** If this were a high-volume, low-acuity channel where
blocking caused patients to give up and not seek care at all, fail-open with
aggressive keyword screening could become the safer real-world choice. It is a
context call, not an absolute — but for this brief, closed is right.

---

## 2. The safety gate runs before everything

Classification happens before routing and before any tool call. The agent loop
and the LangGraph router both call the *same* `classify_safety` first, and only a
clean `SAFE` verdict is allowed to reach a tool. This keeps the guarantee in one
place instead of scattered across handlers.

Order inside the gate: **keyword fast-path → LLM classifier (with timeout) →
fail-closed**. The fast-path doubles as the Part 5 optimisation and as the outage
safety net.

---

## 3. One concern per file → new functionality = small change

The `clinic/` package is split by concern on purpose. Concretely:

- **Add a language** → add a column to the dicts in
  [clinic/responses.py](clinic/responses.py) and a few markers in
  [clinic/language.py](clinic/language.py). No logic changes.
- **Add a tool** → write the function in [clinic/tools.py](clinic/tools.py), add
  a schema in [clinic/schemas.py](clinic/schemas.py), and one line in the
  `TOOL_REGISTRY` in [clinic/registry.py](clinic/registry.py). The loop, safety
  gate, and graph are untouched.
- **Improve classification** → add phrases to the tables in
  [clinic/rules.py](clinic/rules.py). Everything that classifies (offline stub,
  eval, fast pre-router, outage net) improves at once because they share one
  source.
- **Swap the LLM provider** → implement the same tiny interface
  (`classify` + `chat`) as `GroqClient` in [clinic/llm.py](clinic/llm.py). The
  agent is provider-agnostic; nothing else changes.

`patient_id` is injected by the registry, never supplied by the model, so tools
can't act on the wrong patient no matter what the model does.

---

## 4. Storage: single JSON file, atomic writes

The brief fixes this. `clinic/storage.py` reads the whole file, and writes via a
temp file + `os.replace` so a crash mid-write can't corrupt the store. The store
path is override-able (default argument resolves at call time) purely so tests get
an isolated file — no globals mutated in tests.

---

## 5. Idempotent booking (stretch B)

`book_appointment` derives a key from `patient_id | department | date`. A repeat
of the same slot returns the existing appointment with `duplicate: True` instead
of creating a second row. This makes a webhook retry safe by construction, and is
proven in `tests/test_idempotency.py` (both at the tool level and through two
fresh agent turns).

---

## 6. Offline stub as a first-class citizen

`OfflineClient` is a deterministic, key-free stand-in that implements the exact
same interface as the real client. It exists so (a) the eval's deterministic
parts and the whole test suite run with no API key, and (b) the CLI is
demonstrable offline. It is built on the same keyword rules the live fast-path
uses, so it is honest about what the deterministic layer can and cannot do.

---

## 7. Reply in the user's language (stretch A)

Language is detected per message and the system prompt instructs the model to
reply in kind; canned safety replies are pre-translated. The script-purity check
in [clinic/language.py](clinic/language.py) flags a Devanagari-intended reply that
leaks romanized Latin, and a test asserts every shipped Hindi reply is
script-pure.
