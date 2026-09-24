# Incident Copilot operator dashboard

The Streamlit dashboard is the human-control surface for Incident Copilot. It talks
only to the Python control plane; it never contacts the Java simulator or a
model provider directly.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The default control-plane address is `http://localhost:8000`. Override it with
the `INCIDENT_COPILOT_API_URL` environment variable or from the dashboard sidebar.

```bash
INCIDENT_COPILOT_API_URL=http://localhost:8000 streamlit run app.py
```

The page remains usable when the control plane is offline: it shows the local
scenario catalogue, disables mutation controls, and provides a clear recovery
message instead of failing during import or rendering.

## Container

Build from this directory:

```bash
docker build -t incident-copilot-dashboard .
docker run --rm -p 8501:8501 \
  -e INCIDENT_COPILOT_API_URL=http://host.docker.internal:8000 \
  incident-copilot-dashboard
```

## Workflow represented in the UI

1. Launch a deterministic simulator scenario.
2. Select its incident from the command queue.
3. Run the AI investigation and inspect its cited evidence.
4. Review the typed action and its exact arguments.
5. Approve or reject it with an attributed operator comment.
6. Verify recovery against deterministic thresholds.
7. Review the append-only audit timeline and portfolio metrics.

All displayed outcomes are explicitly labelled as simulation results.
