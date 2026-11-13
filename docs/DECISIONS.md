# Decisions (ADR-lite)

1. **Rule + SymPy core, LLM only for prose.** Error categories, correctness and confidence come
   from deterministic, testable code. LLMs are non-deterministic and cannot be treated as
   verified facts (master prompt Engine 1). LLM text is stored as an unverified explanation.
2. **First invalid transition drives classification.** Later steps are often consequences of
   the first error; analysing all would double-count. Later invalid steps are still marked in the step list.
3. **Confidence = documented heuristic + Beta-Binomial calibration from teacher reviews.**
   Honest about not being a validated model; improves automatically as teachers review.
4. **Teacher transcription wins.** On re-processing, responses with `transcription_source=teacher` are kept.
5. **Hypotheses are regenerated on re-analysis; reviews are kept** (`hypothesis_id` → NULL), so
   calibration history survives OCR corrections.
6. **Questions are stored in a bank (`questions`) and linked via `exam_questions`** so later
   phases can reuse items and accumulate item statistics across administrations.
7. **Observed exam percentage ≠ mastery.** Item/outcome reports are labelled as observed
   statistics; mastery estimation (BKT/IRT) is Phase 4.
8. **Next.js route-handler proxy + httpOnly cookie** instead of exposing the API to the
   browser with a bearer token: removes token theft via XSS and avoids CORS.
9. **No shadcn CLI**: small in-house component set (`components/ui.tsx`) in the same spirit;
   shadcn can be adopted by the core team without changing page logic.
10. **Enum types created explicitly in the migration** because several tables share them.
11. **Mock providers never pretend to read handwriting.** Without a dev fixture, all answers
    go to teacher review — the system never fabricates student work.
