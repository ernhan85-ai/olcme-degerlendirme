# Assessment & Evaluation Module — scope, status, API

## Workflow (Part 4)

| # | Step | Status |
|---|---|---|
| 1–2 | Teacher creates exam: grade, subject, classes, date | ✅ `POST /exams` (teacher only for own classes; single campus; grade must match) |
| 3 | Upload booklet PDF | ✅ `POST /exams/{id}/booklet?kind=booklet` (stored, validated) |
| 4 | Upload / define answer key | ✅ key per question in form/CSV; key PDF upload `?kind=answer_key` is stored only |
| 5 | Question → learning-outcome mapping | ✅ form chips or CSV `outcome_codes` |
| 6 | System extracts questions from booklet | ❌ **Not implemented** — needs a real vision provider; teachers enter or CSV-import questions |
| 7–8 | Teacher reviews & validates keys/outcomes | ✅ `POST /exams/{id}/validate-keys`; reference steps are SymPy-checked on save |
| 9 | Publish internally | ✅ `POST /exams/{id}/publish` with blocker list; published exams are locked |
| 10 | Student submissions | ✅ "Yeni Öğrenci Yükle": single + bulk (file name prefix = student number) |

Job statuses, retry, Turkish error messages, malware scanning hook, ambiguous-handwriting flags: ✅.

## Handwritten analysis (Part 5)
✅ steps, fractions, algebraic expressions, equations, crossed-out work, incomplete solutions,
procedural errors, comparison against validated reference solution, three-panel UI,
bounding-box overlays (image scans), teacher OCR correction, mandated "cannot analyse" message.
⚠️ Geometry annotations: data model supports it (free-text steps + bbox) but no geometry
verifier exists — such steps are `unverifiable`. ⚠️ Overlays are not drawn on PDF pages (v1);
images are fully supported.

## API (prefix `/api/v1`, full contract: `docs/openapi.json`, live: `/docs`)

| Method | Path | Role permission |
|---|---|---|
| POST | `/auth/login` · GET `/auth/me` | public / any |
| GET | `/meta/lookups` | exam:read |
| GET/POST | `/exams` | exam:read / exam:write |
| GET | `/exams/{id}` | exam:read |
| PUT | `/exams/{id}/questions` | exam:write |
| POST | `/exams/{id}/questions/import-csv` | exam:write |
| POST | `/exams/{id}/booklet` | exam:write |
| POST | `/exams/{id}/validate-keys` · `/publish` | exam:write · exam:publish |
| GET | `/exams/{id}/students` | exam:read |
| POST | `/exams/{id}/submissions` · `/submissions/bulk` | submission:upload |
| GET | `/exams/{id}/submissions` · `/submissions/{id}` | exam:read |
| POST | `/submissions/{id}/retry` | submission:upload |
| GET | `/submissions/{id}/responses` · `/responses/{id}` | exam:read |
| PUT | `/responses/{id}/transcription` | analysis:review |
| POST | `/responses/{id}/score` | analysis:review |
| POST | `/hypotheses/{id}/review` | analysis:review |
| GET | `/reviews/queue` | analysis:review |
| GET | `/exams/{id}/item-analysis` · `/outcome-report` | analytics:read |
| GET | `/files/{id}` | exam:read (object-level checked) |

Object-level access (`core/deps.py::ensure_exam_access`): org-wide roles → whole tenant;
campus admin → own campus; teacher → exams they created or exams of their assigned classes.
Other tenants always get **404** (no existence leak).

## CSV format for questions
```
position;answer_type;stem_text;correct_answer;points;outcome_codes;reference_steps;options
1;equation;3x+5=20 çözünüz;x=5;20;M.7.2.2.2;3x+5=20|3x=15|x=5;
2;multiple_choice;Hangisi?;C;10;M.7.2.2.2;;A=1/2|B=2|C=4|D=64
```
`answer_type`: multiple_choice | numeric | expression | equation | open_ended.

## Remaining work for this module (honest list)
1. Automatic question extraction from booklet PDF (vision provider + review UI).
2. Answer-sheet (optical form) recognition for MC-only exams.
3. Partial-credit rubric for multi-step questions (currently 0 / full, teacher override).
4. PDF overlay rendering (render pages with pdf.js and reuse the SVG overlay).
5. S3 storage adapter (interface exists, `NotImplementedError`).
6. Student / parent views of exam results (Phase 8) — API intentionally denies them now.
7. PDF reports (Part 14) — data endpoints exist; renderer not built.
8. Playwright E2E suite in CI (screens were verified manually with Playwright + Chrome).
9. Rate limiting (do at gateway / reverse proxy) and OpenTelemetry instrumentation.
10. Duplicate uploads for the same student create a new submission; statistics use the latest one.
