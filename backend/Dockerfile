FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[pdf]" && pip install --no-cache-dir pytest
COPY . .
RUN useradd -m appuser && mkdir -p /app/var/uploads && chown -R appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
