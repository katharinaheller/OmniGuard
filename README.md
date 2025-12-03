# OmniGuard LLM Service

This README provides a **precise, factual, and unambiguous description** of the current state of OmniGuard.  
Nothing here overpromises functionality that is still under development.  
The description is **scientifically concise**, **logically structured**, **technically clean**, and **realistic**.

---

## Overview

OmniGuard is a modular FastAPI backend designed to provide a **fully instrumented LLM request pipeline** for Vertex AI (Gemini).  
The focus is not on UI features but on a **transparent, technically traceable execution path** in which all LLM interactions generate structured observability signals (latency, tokens, drift, logs, spans, sessions).

The current implementation forms the foundation of the observability stack.  
Several components of the evaluation layer (detection semantics, thresholds, rule logic) are intentionally left open and will be refined.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running the Service](#running-the-service)
- [API Endpoints](#api-endpoints)
- [Observability Stack](#observability-stack)
- [Telemetry Signals (Current State)](#telemetry-signals-current-state)
- [Notes](#notes)

---

## Features

Currently implemented and functional:

- Non-streaming and streaming chat endpoints  
- Vertex AI Gemini 2.0 integration  
- Token, latency and usage extraction  
- Hybrid embedding drift detection (Vertex + MiniLM)  
- Redaction filter (emails, IPs, credit cards, IBANs)  
- Session tracking (turns, lifecycle, token accumulation)  
- Structured JSON logs with Datadog trace correlation  
- Export of telemetry to Datadog (metrics, logs, events, cases)

Under active development:

- Evaluation layer (interpretation of drift/latency signals)  
- Final detection-layer semantics (monitors, SLO mapping)  
- Datadog dashboard, depending on the finalized metric surface

---

## Installation

```bash
# Install uv
curl -Ls https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
````

---

## Environment Variables

Set via environment or `.env`:

```env
OMNIGUARD_GCP_PROJECT_ID=your-project
OMNIGUARD_GCP_LOCATION=europe-west4
OMNIGUARD_VERTEX_MODEL_NAME=gemini-2.0-flash-001

OMNIGUARD_TELEMETRY_ENABLED=true

DD_API_KEY=your-datadog-api-key
DD_APP_KEY=your-datadog-app-key
DD_SITE=datadoghq.eu
```

For local tests without Datadog, DD keys may be omitted.
Telemetry export will then be inactive for metrics/events/cases.

---

## Running the Service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## API Endpoints

### `POST /api/v1/chat` — non-streaming

```json
{
  "messages": [
    {"role": "user", "content": "Hello OmniGuard"}
  ],
  "stream": false,
  "max_output_tokens": 512,
  "temperature": 0.3,
  "top_p": 0.95
}
```

### `POST /api/v1/chat/stream` — streaming

Server-sent JSON lines.

### `GET /health`

Simple health indicator.

---

## Observability Stack

The service generates:

* **Structured JSON logs** (with `dd.trace_id` and `dd.span_id`)
* **LLMObs annotations** (Datadog LLM Observability)
* **Token/latency metrics** (Datadog API v2 series)
* **Hybrid embedding drift signals**
* **Event/Case creation** (Datadog API v1/v2)
* **Session accumulation** (in-memory)

`ddtrace` auto-instrumentation is enabled via `patch_all()`.
If no local Datadog agent is running, APM traces remain local (expected behavior).

---

## Telemetry Signals (Current State)

### Logs

* `chat_request`
* `chat_response`
* `chat_stream_request`
* `llm_observability_summary`

### Metrics

* `omniguard.llm.latency_ms`
* `omniguard.llm.tokens.input`
* `omniguard.llm.tokens.output`
* `omniguard.llm.tokens.total`
* `omniguard.llm.cost_usd`
* `omniguard.llm.embedding_drift.score`

### Events

* Drift event
* Latency event

### Cases

* Drift case
* Latency case
  (created only when thresholds are exceeded)

---

## Notes

* No persistent storage: sessions and embedding histories are in-memory only.
* Evaluation semantics (drift meaning, thresholds, rule system) will be refined.
* Datadog dashboards and detection rules will be created after the metric surface stabilizes.
