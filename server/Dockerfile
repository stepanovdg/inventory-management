# Factory Inventory Management System — Backend (FastAPI)
# Multi-stage: a shared base, a lean `prod` target, and a `dev` target with hot reload.

FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code (incl. server/data/*.json loaded at startup)
COPY . .

EXPOSE 8001

# ---- Production image: plain uvicorn ----
FROM base AS prod
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

# ---- Development image: auto-reload (source is bind-mounted by compose) ----
FROM base AS dev
RUN pip install --no-cache-dir watchfiles
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
