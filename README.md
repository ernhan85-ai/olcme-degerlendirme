# BCN LearnDNA — Assessment & Evaluation Module (Ölçme ve Değerlendirme)

Implements, as running code, Parts 4 & 5 and Engine 1 of the BCN LearnDNA master prompt:

* **Exam management** — create exam, questions, answer keys, validated reference solutions,
  learning-outcome mapping (form or CSV), booklet PDF upload, key validation, publish lock.
* **"Yeni Öğrenci Yükle"** — single or bulk upload (PDF / PNG / JPEG / TIFF), magic-byte
  validation, optional ClamAV scan, document-processing jobs
  (`uploaded → queued → processing → requires_review | completed | failed`) with retry and Turkish error messages.
* **Engine 1 — AI Error Reasoning** — SymPy-verified step chain, 8 rule detectors, evidence with
  bounding boxes, alternative explanations, diagnostic questions, OCR-aware confidence,
  calibration from teacher reviews, mandatory teacher review for uncertain cases.
* **Three-panel analysis screen** — original scan with overlays · extracted steps (teacher-editable) · AI analysis with approve / modify / reject.
* **Item analysis (madde analizi)** — difficulty p, corrected point-biserial, upper–lower D,
  KR-20 / Cronbach α, SEM, distractor analysis, flags; per-outcome observed achievement.
* RBAC enforced in the backend, tenant isolation, audit log for every change.

Read **`TESLIM_NOTU.md`** (Turkish developer hand-off) and **`docs/`** first.

## Quick start (Docker)

```bash
docker compose up --build            # db, redis, api (+migrations), worker, web
docker compose exec api python -m app.seed
# open http://localhost:3000  →  ogretmen@demo.bcn / Demo123!
```

## Local development

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,pdf]"
cp .env.example .env                     # edit DATABASE_URL etc.
alembic upgrade head
python -m app.seed                       # synthetic demo data (no real students)
uvicorn app.main:app --reload            # http://localhost:8000/docs
pytest                                   # 42 tests (SQLite by default)
LEARNDNA_TEST_DATABASE_URL=postgresql+psycopg://... pytest   # same suite on PostgreSQL

# frontend
cd frontend
cp .env.example .env.local
npm install
npm run dev                              # http://localhost:3000
npm run typecheck && npm test && npm run build
```

Demo accounts (password `Demo123!`): `ogretmen@demo.bcn` (teacher, 7-A),
`ogretmen2@demo.bcn` (teacher, 7-B — cannot see the 7-A exam), `koordinator@demo.bcn`,
`kampus@demo.bcn`, `veli@demo.bcn` (parent — no access to this module).

Without AI credentials everything runs on clearly labelled mock providers (**SİMÜLASYON** badge).
In development a `*.transcript.json` file can be uploaded next to a scan to simulate handwriting
recognition (format: `backend/app/services/ai/providers.py::ExtractionResult`; sample pair in `backend/demo_fixtures/` — upload both files for student 1005).
