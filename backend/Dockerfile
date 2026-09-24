FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY backend/pyproject.toml backend/README.md ./
COPY backend/incident_copilot_api ./incident_copilot_api
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY runbooks /runbooks
RUN pip install --no-cache-dir .

ENV RUNBOOK_DIRECTORY=/runbooks
EXPOSE 8000
CMD ["uvicorn", "incident_copilot_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
