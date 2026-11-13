# Security & privacy — assessment module

| Control | Implementation | Status |
|---|---|---|
| Authentication | JWT (HS256, 60 min) issued by FastAPI; browser keeps it only in an **httpOnly, SameSite=Strict** cookie set by the Next.js route handler; page JS never sees it. Passwords: PBKDF2-SHA256, 310k iterations. | ✅ (SSO/MFA: core team) |
| Authorization | Permission → role map + object-level checks in `core/deps.py`; roles re-read from DB on every request (token roles ignored). | ✅ tested |
| Tenant isolation | `organization_id` on every row and query; foreign tenants get 404. | ✅ tested |
| Upload validation | Magic-byte sniffing (PDF/PNG/JPEG/TIFF), size limit, filename sanitised, storage keys random, path-traversal guard. JSON transcript fixtures accepted **only** when `LEARNDNA_ENV=development`. | ✅ tested |
| Malware scanning | ClamAV INSTREAM hook; infected files rejected and audited; scanner unreachable → upload refused (fail closed). Default `none` = `not_scanned` recorded on each file. | ✅ (enable in prod) |
| File serving | Authenticated, object-level checked, `no-store`, `nosniff`. | ✅ |
| Code injection via math | SymPy input whitelist (see AI_ENGINE_DESIGN §3). | ✅ tested |
| Prompt injection | Vision/LLM prompts declare page/student text as data; outputs schema-validated and re-verified by SymPy; LLM text cannot change decisions. | ✅ |
| Provider data minimisation | Only page images + question numbers/types (vision) or anonymous step text (explainer). No names, numbers, school. | ✅ |
| Audit log | Login, exam create/edit/import/publish, uploads, retries, transcription corrections (before/after), reviews, score overrides, malware blocks. | ✅ |
| Secure errors | Global handler returns generic Turkish message; details only in server logs. | ✅ |
| Secrets | Env vars only; app refuses to start outside development with the default JWT secret. | ✅ |
| Encryption in transit / at rest | TLS at ingress; PostgreSQL & object storage encryption at the infrastructure level. | ⏳ infra |
| Rate limiting | Recommended at reverse proxy (login endpoint first). | ⏳ |
| Retention / deletion | Cascades exist (submission → files/responses/steps/hypotheses); retention scheduler and storage purge not implemented. | ⏳ |

## KVKK notes (for the compliance assessment — not legal advice)
* Student exam scans and error analyses are personal data of minors; handwriting images may
  be considered more sensitive in context. Processing should rest on the school's documented
  legal basis; parental consent alone may not cover every activity (e.g. profiling-like analysis).
* **Cross-border transfer:** sending scans to a foreign AI provider is a transfer abroad under
  KVKK Art. 9. Keep `VISION_PROVIDER=mock` (or a provider hosted in Türkiye) until the legal
  basis, standard contract / notification steps and a DPIA-style assessment are completed.
* The UI marks every AI output as a hypothesis and every mock result as SİMÜLASYON; teachers
  remain the decision-makers (human-in-the-loop).
* **Before going live with real student data, get approval** (master prompt Part 21).
