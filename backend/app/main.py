import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analysis, analytics, auth, exams, submissions
from app.core.config import get_settings

settings = get_settings()
settings.validate_for_runtime()
logging.basicConfig(level=logging.INFO, format='{"ts":"%(asctime)s","lvl":"%(levelname)s","log":"%(name)s","msg":"%(message)s"}')

app = FastAPI(title="BCN LearnDNA — Ölçme ve Değerlendirme API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):  # secure error handling: no stack traces to clients
    logging.getLogger("learndna").exception("unhandled error: %s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Beklenmeyen bir hata oluştu."})


@app.get("/health")
def health():
    return {"status": "ok", "vision_provider": settings.vision_provider, "llm_provider": settings.llm_provider}


for r in (auth.router, exams.router, submissions.router, analysis.router, analytics.router):
    app.include_router(r, prefix="/api/v1")
