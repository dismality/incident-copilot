# LinkedIn project assets

## Project title

Incident Copilot — AI-Assisted Incident Response

## Description

Built an AI-assisted incident response platform that moves beyond a basic chatbot. A Java infrastructure simulator produces realistic service failures, Prometheus detects abnormal metrics, and Alertmanager opens incidents through an authenticated webhook. The Python/FastAPI copilot gathers logs, health checks, deployment history and runbooks to form an evidence-backed hypothesis and recommend a specific remediation.

Safety is built into the workflow: high-risk changes require role-aware human approval, exact tool arguments are shown before execution, retries are idempotent, and an incident cannot be marked resolved until deterministic health checks confirm recovery. PostgreSQL stores incidents, evidence, approvals and an append-only audit history, while the Streamlit operator console makes the complete decision trail visible.

Tech: Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Java, Spring Boot, Prometheus, Alertmanager, Streamlit, Docker Compose and pytest.

GitHub: https://github.com/dismality/incident-copilot

## Suggested LinkedIn skills

- Artificial Intelligence (AI)
- Python
- FastAPI
- Prometheus
- Java

## Image order

1. `01-incident-copilot-cover.png`
2. `02-approval-and-audit.png`

The cover's atmospheric backdrop was generated with OpenAI image generation. The product interface in the second image comes directly from the working application.
