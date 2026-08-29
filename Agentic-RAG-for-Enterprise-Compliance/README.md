<div align="center">

<br/>

# GroundedRAG — Multi-Agent RAG with Hallucination Mitigation

<p>A multi-agent compliance auditing engine — replacing single-pass RAG with a cyclical<br/>graph state machine that verifies its own outputs before writing a single audit line.</p>

<br/>

![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-FF6F61?style=for-the-badge&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-DC244C?style=for-the-badge&logo=qdrant&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

![Tests](https://img.shields.io/badge/tests-29%20passing-brightgreen?style=flat-square)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)
![Eval](https://img.shields.io/badge/eval-0%20contradictions-brightgreen?style=flat-square)

<br/>

> **Multi-Agent RAG · Hybrid Vector Search · Deterministic Audit Ledger** &nbsp;|&nbsp; Self-correcting · Citation-verified · Fully containerised

<br/>

---

</div>

## Why This Exists

Standard RAG fails in legal and compliance contexts. It hallucinates in the middle of long documents, chunks text without respecting clause boundaries, and has no mechanism to cross-examine what it just retrieved against what it actually cited.

The result: audits that look confident and are silently wrong.

GroundedRAG approaches this differently. Instead of a single prompt-and-return pipeline, it runs a **cyclical multi-agent graph** where a Planner maps the document, an Auditor identifies violations with direct clause citations, and a Critic rejects the output and triggers a retry loop if the citations don't hold. Nothing reaches the audit ledger unless it passes verification.

<br/>

---

## Key Numbers

<br/>

<div align="center">

| Cyclical Graph | Hybrid Search | Actor-Critic + Consistency Pass | Automated Test Suite |
|:---:|:---:|:---:|:---:|
| 7-node LangGraph state machine, with a bounded retry loop | Dense + lexical fusion (RRF) + cross-encoder rerank | Evidence grounding, plus a final cross-sub-task contradiction check | 29 pytest tests, run in CI on every push |

</div>

<br/>

---

## How It Works

<br/>

```
                    ┌─────────────┐
                    │   Planner   │   splits the audit objective into sub-queries
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
        ┌────▶│        Retrieve         │   hybrid RRF + cross-encoder rerank
        │     └────────────┬────────────┘
        │                  │
        │     ┌────────────▼────────────┐
        │     │         Auditor         │   LLM drafts a finding + verbatim quote
        │     └────────────┬────────────┘
        │                  │
        │     ┌────────────▼────────────┐
        │     │          Critic         │   ① fuzzy-matches the quote against the
        │     │                         │      real retrieved chunk text
        │     └────────────┬────────────┘   ② judges compliance + citation validity
        │                  │
        │            ╔═════▼═════╗
        └───reject────╢ verified? ║
         (< 2 retries) ╚═════╤═════╝
                              │ pass — or retries exhausted
                              │ (tagged UNVERIFIED_EVIDENCE, never silently dropped)
                    ┌─────────▼─────────┐
     more sub-tasks │     Finalize      │   reconciles duplicate findings — a
        ◀────────── │  (severity gate)  │   NON_COMPLIANT verdict can never be
                    └─────────┬─────────┘   silently overwritten by a later
                              │ all sub-tasks done   COMPLIANT one on the same clause
                  ┌───────────▼───────────┐
                  │  Consistency Editor   │   cross-checks ALL findings together —
                  └───────────┬───────────┘   catches contradictions between sub-tasks
                              │               that never saw each other's work
                  ┌───────────▼───────────┐
                  │    Generate Report    │   risk score + fully-cited PDF
                  └───────────────────────┘
```

<br/>

---

## Technical Decisions

<br/>

| Layer | Choice | Rationale |
|---|---|---|
| Agent Orchestration | LangGraph | Cyclic loops, state persistence, conditional routing — impossible with basic DAGs |
| Vector Engine | Qdrant (Dockerised) | Native hybrid search: dense embeddings + exact clause keyword matching |
| Chunking Strategy | Clause-boundary aware | Detects numbered clause/section headers and keeps each clause as one atomic chunk, with real PDF-derived bounding boxes and character offsets — not fixed-size windows with fabricated coordinates |
| Quality Gate | Auditor-Critic Loop | No output passes without citation validation — eliminates blind pass-throughs |
| Cross-Task Consistency | Consistency Editor pass | One final LLM pass groups duplicate findings across independent sub-tasks; the actual keep/merge decision stays deterministic code, never an LLM rewrite of evidence |
| Backend | FastAPI + Uvicorn | Async execution built for enterprise REST endpoints and streaming agent logs |
| Job Queue | Celery + Redis | Long-running audits run off the request thread; job state and live progress persist and stream via SSE |
| Frontend | React + Vite (`aegis-ui`) | Master-detail findings inspector with live pipeline progress over a real SSE connection |
| API Hardening | Opt-in key auth + upload caps | `API_KEY` env var gates write endpoints when set; uploads capped at `MAX_UPLOAD_SIZE_MB`; stale report PDFs swept on startup |

<br/>

---

## Evaluation Results

<br/>

Rather than claim accuracy, `src/eval/run_accuracy_eval.py` measures it: it runs the full graph end-to-end against two synthetic contracts with known, deliberately planted violations, and checks whether the reported findings actually caught them.

| Document | Findings | Violations Caught | Contradictions |
|---|:---:|:---:|:---:|
| Corporate MSA (retention + cross-border transfer) | 2 | 1 / 2 | **0** |
| Employee Data Agreement (biometric consent + breach notice) | 3 | 1 / 2 | **0** |

**Zero cross-finding contradictions** in both runs — the `finalize.py` reconciliation and the Consistency Editor pass are doing their job.

**2 of 4 known violations missed**, and the reason is worth stating plainly rather than hiding: clause-boundary chunking means each clause is now retrieved once instead of being fragmented and re-retrieved 2-3 times. That's exactly why contradictions dropped to zero — but it also removes the redundancy that previously gave the Auditor multiple independent chances to successfully quote a clause. If its one attempt at an exact quote fails fuzzy verification, the finding is marked `UNVERIFIED_EVIDENCE` (flagged for human review, never silently dropped) rather than retried against a different phrasing of the same evidence. That's a real, open trade-off between deduplication and retry redundancy — not a solved problem.

<br/>

---

## Quickstart

<br/>

**Prerequisites**
- Docker Desktop, with a few GB of free disk space (image builds for this project are not small)
- [Ollama](https://ollama.com) running on the host, with the two models this project actually uses pulled:
  ```bash
  ollama pull llama3.2:3b
  ollama pull nomic-embed-text
  ```
  Local model choice matters here: an LLM that doesn't fit in whatever RAM is actually free is a real failure mode, not a theoretical one — `llama3.2:3b` (~2GB) is the safe default.

**Run the full stack**
```bash
git clone <this-repo>
cd Agentic_AI_Project
docker compose up -d --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

**Run the test suite**
```bash
cd Agentic-RAG-for-Enterprise-Compliance
pip install -r requirements.txt
pytest tests/ -v
```

**Run the accuracy eval** (needs the full stack up — Qdrant, Redis, and Ollama reachable)
```bash
python generate_mock_pdf.py && python generate_mock_pdf_2.py   # build the two test contracts
python -m src.eval.run_accuracy_eval
```

<br/>

---

## Business Framing

<br/>

> **What's the operational problem?**
>
> Manual compliance reviews are slow, expensive, and inconsistent. Legal teams spend hours cross-referencing contracts against policy standards — work that creates bottlenecks, delays contract sign-offs, and introduces human oversight risk at scale.

<br/>

> **What does better look like?**
>
> An automated pipeline that reads a contract, maps it against a policy standard, identifies violations with direct clause citations, validates its own findings, and produces a reproducible audit ledger — without a human in the loop until the output is already verified.

<br/>

> **Is this deployable?**
>
> Yes. `docker-compose.yml` at the repository root (one level above this folder) orchestrates five services: `qdrant`, `redis`, `api`, `celery_worker`, and `ui` (the React/Vite frontend, in the sibling `aegis-ui/` directory). The LLM itself runs outside the container network via Ollama on the host. Deploys to AWS ECS, GCP Cloud Run, or on-premise infrastructure.

<br/>

---

## Tech Stack

<br/>

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-FF6F61?style=flat-square)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square)
![Qdrant](https://img.shields.io/badge/Qdrant-DC244C?style=flat-square&logo=qdrant&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=flat-square&logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)

</div>

<br/>

---

## Repository Structure

This folder is the backend half of the project. The full stack — including the
`aegis-ui/` frontend and the root `docker-compose.yml` that wires everything
together — lives one directory up.

```
Agentic_AI_Project/
├── docker-compose.yml           # Orchestrates qdrant, redis, api, celery_worker, ui
├── aegis-ui/                    # React + Vite frontend (served via nginx)
└── Agentic-RAG-for-Enterprise-Compliance/    # <- this folder
    ├── src/
    │   ├── agents/
    │   │   └── nodes/          # planner, retrieval, auditor, critic, finalize, editor, report_generator
    │   ├── api/                # FastAPI app, Celery task queue, job manager
    │   ├── database/           # Qdrant initialisation, clause-aware PDF chunking, vector indexing
    │   ├── retrieval/          # Hybrid RRF dense + lexical retriever with cross-encoder rerank
    │   ├── verification/       # Evidence-quote grounding checks used by the Critic
    │   ├── inference/          # Hardware-aware LLM/embedding backend selection, LLM-call timeouts
    │   ├── eval/                # End-to-end accuracy eval against ground-truth documents
    │   ├── state/              # Redis-backed (or in-memory) job state store
    │   ├── events/             # SSE event broadcaster for live job progress
    │   └── utils/              # PDF report rendering and highlighting
    ├── tests/                  # Real pytest suite — infra-free, deterministic (`pytest` to run)
    ├── .github/workflows/      # CI: runs the pytest suite on every push/PR
    ├── generate_mock_pdf.py    # Ground-truth test contract #1 (retention + cross-border)
    ├── generate_mock_pdf_2.py  # Ground-truth test contract #2 (biometric + breach notice)
    ├── app.py                  # Legacy Streamlit dashboard (superseded by aegis-ui, kept as a lightweight fallback)
    ├── Dockerfile              # Multi-stage build for the FastAPI/Celery service
    └── requirements.txt        # Production dependencies
```

<br/>

---

## About

<br/>

<div align="center">

Built by **Suresh Kanchamreddy** — B.Tech CS student and data analyst focused on turning raw data and LLM-driven pipelines into decision-ready systems.

*Most RAG systems are built to sound right. This one is built to be verifiable.*

<br/>

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/kanchamreddy-suresh)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Suresh-Note)

<br/>

</div>
