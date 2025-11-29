# OmniGuard LLM Service

A FastAPI-based backend service for interacting with Google's Vertex AI LLMs (Gemini) and integrated observability via Datadog. Designed for observability-first applications with latency, drift, and token usage monitoring.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Observability](#observability)
- [Telemetry Events](#telemetry-events)

---

## Features

- Chat endpoint (streaming & non-streaming)
- Vertex AI (Gemini 2.0) integration
- Token, cost & latency tracking
- Drift detection (Vertex + MiniLM hybrid)
- Feedback & session tracking
- Full Datadog integration (events, metrics, logs, cases)

---

## Installation

```bash
# Install uv (if not already installed)
curl -Ls https://astral.sh/uv/install.sh | sh

# Create virtual environment using uv
uv venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install Python dependencies
uv pip install -r requirements.txt
````

---

## Environment Variables

Required (set as env vars or via `.env`):

```env
OMNIGUARD_GCP_PROJECT_ID=your-gcp-project
OMNIGUARD_GCP_LOCATION=europe-west4
OMNIGUARD_VERTEX_MODEL_NAME=gemini-2.0-flash-001

OMNIGUARD_TELEMETRY_ENABLED=true

DD_API_KEY=your-datadog-api-key
DD_APP_KEY=your-datadog-app-key
DD_SITE=datadoghq.eu
```

---

## Usage

Start the FastAPI app:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## API Endpoints

* `POST /api/v1/chat` — non-streaming chat
* `POST /api/v1/chat/stream` — streaming chat
* `GET /health` — health check

Each request must follow this schema:

```json
{
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false,
  "max_output_tokens": 512,
  "temperature": 0.3,
  "top_p": 0.95
}
```

---

## Observability

Enabled via [Datadog LLMObs](https://docs.datadoghq.com). Includes:

* Token usage + cost
* Latency metrics
* Drift detection (embedding shift)
* Event and case reporting (Datadog Cases)
* JSON logs

---

## Telemetry Events

* `chat_request`, `chat_response`
* `chat_stream_request`
* `llm_observability_summary`
* `drift_event`, `latency_event`
* Redacted input/output for privacy

---

## Notes

* Uses VertexAI `GenerativeModel` and `TextEmbeddingModel`
* Embedding drift calculated via cosine distance
* Optional MiniLM model via `sentence-transformers`
* No database: all observability is in-memory or externalized (Datadog)

---


