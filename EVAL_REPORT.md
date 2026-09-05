# Evaluation report

All numbers below are from **offline** mode (deterministic keyword classifier, no
API key), on the 34-row dev set in [evals/dataset.yaml](evals/dataset.yaml).
Reproduce with:

```powershell
python evals/run.py --offline
python evals/measure.py --offline
```

> The grader's held-out 20 messages will score lower than this — see
> **"How confident am I in these numbers?"** below. That section is the point of
> this report.

---

## Headline numbers (offline, 34 cases)

| Metric | Value |
| --- | --- |
| Intent accuracy | **100.0%** (34/34) |
| Safety accuracy | **100.0%** (34/34) |
| EMERGENCY precision | 100.0% |
| EMERGENCY recall | 100.0% |
| **Safety false negatives (EMERGENCY → not caught)** | **0** |

### Confusion matrix — intent (rows = actual, cols = predicted)

```
        LOG BOOK LIST EMRG  MED TALK  UNK
  LOG     6    0    0    0    0    0    0
 BOOK     0    6    0    0    0    0    0
 LIST     0    0    4    0    0    0    0
 EMRG     0    0    0    6    0    0    0
  MED     0    0    0    0    6    0    0
 TALK     0    0    0    0    0    4    0
  UNK     0    0    0    0    0    0    2
```

### Confusion matrix — safety (rows = actual, cols = predicted)

```
       EMRG  MED SAFE
 EMRG     6    0    0
  MED     0    6    0
 SAFE     0    0   22
```

---

## Safety false negatives (reported separately)

**0 on the dev set.** These are the only errors here that can hurt someone, so
they are not allowed to dissolve into an average. Zero on 34 rows is *not* proof
of zero on unseen data — the honest caveat is in the confidence section. The eval
prints this count in its own block on every run, and prints the offending rows if
any appear on the held-out set.

---

## Three worst failure modes (honest, forward-looking)

The dev set is clean, so these are where I *expect* to lose points, ranked by
harm:

1. **Novel emergency phrasing → safety false negative (most dangerous).**
   The offline safety layer is phrase-based. An emergency with no listed trigger
   ("everything went black and I fell", "I can't feel my left arm") returns
   *unsure* from the keyword layer and, offline, becomes `SAFE`. That is exactly a
   false negative. On the held-out set this is the most likely place to miss an
   emergency. In **live** mode the LLM classifier backs up the keywords, which is
   the main reason the live pipeline is safer than the offline stub.

2. **Diagnosis requests that dodge trigger words → MEDICAL_ADVICE missed.**
   I deliberately narrowed the bare "do i have" phrase so it wouldn't collide with
   "do I have any appointment". The side effect: an open-ended "do I have
   something serious?" without a keyword can slip through as `LOG_SYMPTOM`/`SAFE`
   and break the "don't act as a doctor" contract. Less dangerous than #1, but a
   contract violation.

3. **Shallow offline slot/symptom extraction.**
   Offline, the logged symptom text is taken from the first user message, and
   relative-date parsing only covers today / tomorrow / day-after. So
   "book me sometime next week" won't extract a date — it correctly *asks* rather
   than inventing (safe), but completion suffers. The live model handles this;
   offline it's a known limitation, not a safety issue.

---

## How confident am I in these numbers? (the "you scored 100%, so what?" answer)

**Not very — and that's the correct reaction to 100% on 34 rows.**

- **The set is tiny.** One mislabel moves accuracy ~3 points. With only 6
  emergencies, EMERGENCY recall has a wide interval: a single miss on the
  held-out set drops recall from 100% to ~86%. A 6-positive sample cannot
  support a tight claim.
- **Mild optimism / leakage.** The classifier and the dataset were developed
  together — I added phrases while reading my own rows — so the dev score is
  biased upward. It measures "does the pipeline handle phrasings I already
  thought of", not "does it generalise".
- **What I actually trust:** the *ordering* (safety before tools), the
  fail-closed behaviour, and the emergency **keyword recall** on the patterns I
  listed. What I do **not** trust is that 100% transfers. My realistic
  expectation on the held-out 20 is high-80s to low-90s overall, and my one hard
  requirement is that **no emergency is missed** — which is why #1 above is my
  first fix.

**What I'd fix first:** broaden EMERGENCY phrase coverage (recall-first), and in
live deployment run the LLM safety classifier even when keywords look SAFE —
reserving the fast-path *only* for keyword-positive emergencies, so the keyword
layer can only ever *add* a block, never skip a check. That costs a little
latency and buys fewer false negatives, which is the right trade for a safety
gate.

---

## Latency & cost (Part 5)

Measured through the real JSONL logging path (`logs/latency.jsonl`) via
`python evals/measure.py --offline`.

| Metric | Value (offline) |
| --- | --- |
| Per-turn latency p50 | 5.21 ms |
| Per-turn latency p95 | 16.97 ms |
| Per-LLM-call p50 | 0.81 ms |
| Per-LLM-call p95 | 2.56 ms |
| Avg LLM calls / turn | 1.47 |

Offline latencies are sub-millisecond-ish because the stub has no network; they
prove the measurement path works and give real percentiles. The **live** table
needs `GROQ_API_KEY` and the same command without `--offline`.

### Optimisation: deterministic keyword pre-router (before / after)

`python evals/run.py --offline --no-keyword` vs `--offline`:

| Config | Intent acc | Safety acc | Model classifier calls / msg | classify p50 |
| --- | --- | --- | --- | --- |
| Before (no pre-router) | 100.0% | 100.0% | **2.00** | 1.05 ms |
| After (pre-router) | 100.0% | 100.0% | **0.71** | 1.34 ms |

- **Accuracy unchanged** (well within the 1-point budget) — the pre-router only
  short-circuits high-confidence keyword matches.
- **−64% model classifier calls** (2.00 → 0.71); **12/34** messages resolved with
  **zero** model calls.
- This reduction is **mode-independent** and is the real mechanism of the live
  speedup: every avoided call removes a network round-trip (typically hundreds of
  ms live), which is where the live p50/p95 improvement would appear.
