# AI Visual Generator — Documentation

This directory contains project documentation, architecture diagrams, and
phase-by-phase development notes.

## Table of Contents

- [Architecture Overview](architecture.md) (coming in Phase 2)
- [Agent Workflow](agent_workflow.md) (coming in Phase 2)
- [Provider Configuration](providers.md) (coming in Phase 2)
- [Development Guide](development.md) (coming in Phase 2)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional, for containerized deployment)

### Running the Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running with Docker

```bash
docker-compose up --build
```
