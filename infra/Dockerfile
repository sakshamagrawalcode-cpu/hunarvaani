FROM python:3.11-slim AS deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


FROM deps AS nlp-deps

ENV HF_HOME=/models

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements-nlp.txt .
RUN pip install --no-cache-dir -r requirements-nlp.txt


FROM node:22-alpine AS console

WORKDIR /console
COPY apps/console/package.json apps/console/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY apps/console ./
RUN npm run build


FROM deps AS api

ENV PYTHONPATH=/app

COPY apps ./apps
COPY --from=console /console/dist ./apps/console/dist
COPY core ./core
COPY audio ./audio
COPY data ./data
COPY db ./db
COPY scripts ./scripts

CMD ["uvicorn", "apps.voice.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM nlp-deps AS worker

ENV PYTHONPATH=/app

COPY apps ./apps
COPY core ./core
COPY audio ./audio
COPY data ./data
COPY db ./db
COPY scripts ./scripts

CMD ["python", "-m", "apps.worker.main"]
