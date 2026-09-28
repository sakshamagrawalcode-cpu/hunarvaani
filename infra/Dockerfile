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


FROM deps AS api

COPY apps ./apps
COPY core ./core
COPY audio ./audio
COPY data ./data
COPY db ./db
COPY scripts ./scripts

CMD ["uvicorn", "apps.voice.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM nlp-deps AS worker

COPY apps ./apps
COPY core ./core
COPY audio ./audio
COPY data ./data
COPY db ./db
COPY scripts ./scripts

CMD ["python", "-m", "apps.worker.main"]
