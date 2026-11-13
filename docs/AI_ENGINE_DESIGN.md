# Engine 1 — AI Error Reasoning Engine (assessment module)

Code: `backend/app/services/error_reasoning.py` (pure, no DB), `math_verify.py`, `calibration.py`,
`ai/providers.py`, orchestration in `pipeline.py`.

## 1. Principles

| Requirement (master prompt) | How it is enforced |
|---|---|
| Distinguish observable mistakes from inferred causes | `observed_error` and `inferred_cause` are separate columns and separate UI blocks ("Gözlenen" vs "Olası neden (yapay zekâ hipotezi)"). |
| Evidence for every hypothesis | Every `HypothesisDraft` carries ≥1 `EvidenceItem` (step index, page, bbox, `verified_by` = `sympy` / `rule` / `ocr` / `llm_unverified`). Unit-tested. |
| Calibrated confidence | Heuristic prior × OCR factor, then Beta-Binomial shrinkage toward each detector's teacher acceptance rate (§4). |
| Flag uncertain cases | `needs_review` if: OCR < 0.60, correctness undecidable, any hypothesis < 0.70, insufficient evidence. |
| Store teacher corrections | `teacher_reviews` (approve / modify / reject + corrected category + detector). Feeds calibration. Transcription edits are audited with before/after. |
| No psychological diagnosis / stable traits | Category list is fixed; texts use "olabilir"; "possible attention mistake" is phrased as a one-off observation; LLM prompt forbids diagnosis. |
| Never invent missing handwritten work | Unreadable / absent work → `INSUFFICIENT_EVIDENCE` + the mandated message *"Öğrenci çözümü güvenilir biçimde analiz edilemedi. Öğretmen incelemesi gerekiyor."* The engine never synthesises steps. |
| LLM output is not verified fact | LLM is only used for an optional teacher-facing explanation, stored separately (`llm_explanation`) and labelled "Doğrulanmamış". It never affects category, correctness, score or confidence. |

## 2. Pipeline

```
scan files ─► VisionProvider.extract()  ─► responses + steps (+ OCR confidence, bbox)
                    (mock | OpenAI-compatible)        │
                                                       ▼
                       answers_match(final, key)  (SymPy / MC letter)
                                                       ▼
            step chain verification: step[i-1] ≡ step[i] ?  (SymPy, solution sets)
                                                       ▼
            first invalid transition ─► detectors (ordered) ─► hypotheses
                                                       ▼
            OCR penalty ─► calibration ─► review routing ─► (optional) LLM explanation
```

### Step verification
* Expressions: `simplify(a − b) == 0`.
* Single-variable equations: equal solution sets (`sympy.solve`).
* Multi-variable equations: zero-forms proportional by a non-zero constant.
* Crossed-out steps are excluded (verdict `not_checked`).
* First step is compared to `reference_steps[0]` (the problem in math form) to detect mis-copying.

### Detectors (ordered; first match wins for an invalid transition)

| Detector | Category | Rule | Prior |
|---|---|---|---|
| `fraction_add_num_den` | Conceptual misunderstanding (+ Missing prerequisite if the outcome has prerequisites) | `a/b + c/d → (a+c)/(b+d)` | 0.85 / 0.55 |
| `sign_transposition` | Incorrect procedure | negating exactly one (un-combined) term of the previous equation makes steps equivalent | 0.80 |
| `partial_distribution` | Incorrect procedure | `k(a ± b) → ka ± b` makes steps equivalent | 0.78 |
| `inverse_operation` | Incorrect procedure | `cx = r → x ∈ {r−c, r+c, r·c}` or `x + c = r → x ∈ {r+c, r·c}` | 0.75 |
| `numeric_slip` | Arithmetic error | structure/degree preserved, numbers differ (close values) | 0.62 |
| `unclassified_invalid_transition` | Incorrect procedure (low) | fallback | 0.45 |
| `setup_mismatch` | Problem interpretation | first step ≢ problem statement | 0.65 |
| `unresolved_last_step` | Incomplete solution | all valid, last step not of form `x = number` | 0.72 |
| `answer_transcription` | Possible attention-related mistake | last step matches key, answer box differs | 0.60 |
| `valid_chain_wrong_target` | Incorrect strategy | all valid, resolved, but wrong | 0.50 |
| `correct_answer_invalid_step` | Incorrect procedure | correct answer but an invalid step (compensating errors) | 0.40 |
| `mc_distractor_tag` | category tagged on the option | wrong MC option with a misconception tag | 0.45 |
| `mc_no_work` / `no_readable_work` | Insufficient evidence | no analysable work | 0.90–0.95 |

**Not yet detected automatically** (only via teacher modification): Transfer difficulty (needs
multi-exam history → Phase 4/5), Missing prerequisite beyond the fraction rule (needs knowledge graph → Phase 4).

## 3. Safety of math parsing
`sympy.parse_expr` calls `eval`. All OCR/LLM/teacher text passes `math_verify._check_safe`:
character whitelist, identifier whitelist (single letters + `sqrt`, `pi`, `abs`), length ≤ 200,
`__` forbidden, restricted `global_dict`. Tests cover `__import__`, `exec`, `lambda`, `open`.

## 4. Confidence & calibration
```
raw          = detector prior × (0.5 + 0.5 × min OCR confidence of evidence steps)
calibrated   = (raw × K + accepted) / (K + reviewed)        K = 10
```
`accepted` = teacher APPROVED; `reviewed` = APPROVED + MODIFIED + REJECTED for that detector
in the organisation. This is a documented heuristic, **not** a validated psychometric model.
Recommended next step once ≥ 200 reviews exist: per-detector isotonic/Platt calibration and a
reliability diagram in the management dashboard.

## 5. Providers
* `MockVisionProvider` — reads nothing; without a dev fixture every question becomes
  "unreadable → teacher review". `provider_is_mock` is stored on the job; the UI shows **SİMÜLASYON**.
* `OpenAICompatibleVisionProvider` — sends only page images + question numbers/types
  (no names/IDs); strict JSON schema validated with Pydantic; prompt treats page text as data
  (prompt-injection defence). PDF pages are rasterised with `pypdfium2` (optional extra `pdf`).
* Adding a provider: implement `VisionProvider.extract()` / `Explainer.explain()` and register
  it in `get_vision_provider()`.

## 6. Extending the taxonomy
Add a detector function → call it in `_classify_transition` in the right order → add a
parametrised case in `tests/test_math_and_engine.py`. Bump `ENGINE_VERSION`; it is stored on
every hypothesis so results stay traceable.
