# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

FROM base AS builder
RUN python -m pip install --no-cache-dir --upgrade pip
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM base AS test
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels anemiaiaback \
    && python -m pip install --no-cache-dir "pytest>=8,<9" "httpx>=0.28,<1"
COPY tests ./tests
RUN API_KEY=test-api-key-with-at-least-32-characters pytest

FROM base AS runtime
RUN addgroup --system app && adduser --system --ingroup app --home /app app
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels anemiaiaback \
    && rm -rf /wheels
USER app
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn anemiaiaback.api.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
