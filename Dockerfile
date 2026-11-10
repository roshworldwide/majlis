# MAJLIS app container (mirrors the reference repo: Ollama runs as a separate service).
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends make tesseract-ocr libreoffice-writer && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY majlis/ majlis/
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
ENV MAJLIS_OLLAMA_BASE_URL=http://ollama:11434 MAJLIS_REF_DIR=/app/_ref/ITUAIReadiness
# Offline demo by default: replay the golden run from cache and verify the audit chain.
CMD ["sh", "-c", "majlis verify golden && ./scripts/experiments.sh --replay-only && majlis dashboard golden --compare reform --no-open"]
