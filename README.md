# Infographic-image-generator

# AI Visual Generator

## Project

**AI Visual Generator** — a web application that generates:

- **Infographic images**
- **Complexity images** (complex technical visuals)

The application uses an **Agentic AI workflow** to understand a user's request,
plan the visual, generate the image, evaluate it, and improve it automatically.

## Purpose

A web application for generating infographic images and complex
technical / complexity images using an agentic AI workflow.

## Planned Architecture

```
USER
  ↓
WEB APPLICATION
  ↓
BACKEND API
  ↓
AGENTIC AI ORCHESTRATOR
  ↓
PLANNER / ROUTER AGENT
  ↓
 ┌───────────────────────┐
 │                       │
 ▼                       ▼
INFOGRAPHIC AGENT   COMPLEXITY AGENT
 │                       │
 └───────────┬───────────┘
             ▓
      DESIGN PLANNER
             ▓
   IMAGE PROMPT GENERATOR
             ▓
      IMAGE GENERATOR
             ▓
        CRITIC AGENT
             ▓
      ┌──────┴──────┐
      │             │
     PASS          FAIL
      │             │
      ▼             ▼
 FINAL IMAGE    REVISION AGENT
                    │
                    └──→ Regenerate
```

### Workflow Explanation

| Step | Component | Description |
|------|-----------|-------------|
| 1 | **User** | Submits a text prompt with a chosen visual type and complexity. |
| 2 | **Web Application** | Frontend (Next.js) with a clean UI for input and preview. |
| 3 | **Backend API** | FastAPI server exposing generation endpoints. |
| 4 | **Orchestrator** | Coordinates the agent workflow end-to-end. |
| 5 | **Planner / Router Agent** | Analyses the request and routes it to the correct specialist. |
| 6 | **Infographic / Complexity Agent** | Runs the sub-workflow for the chosen visual type. |
| 7 | **Design Planner** | Creates a structured design plan (layout, colours, typography). |
| 8 | **Image Prompt Generator** | Converts the design plan into a detailed image-generation prompt. |
| 9 | **Image Generator** | Calls the configured image provider to generate the image. |
| 10 | **Critic Agent** | Evaluates the generated image against the design criteria. |
| 11 | **Revision Agent** | If the critic fails, refines the prompt and regenerates. |
| 12 | **Final Image** | The accepted image is returned to the user. |

## Technology

### Backend
- **Python 3.11**
- **FastAPI** — web framework with automatic OpenAPI docs
- **Pydantic** — data validation and settings management
- **Uvicorn** — ASGI server
- **Pytest** — testing framework

### Frontend
- **Next.js 14** (App Router)
- **React 18**
- **TypeScript**

### Infrastructure
- **Docker** — containerised services
- **Docker Compose** — local multi-service orchestration
- **GitHub** — version control and CI/CD

### AI Providers (planned, Phase 4+)
- **Text generation**: OpenAI, Anthropic, Google, or local LLMs
- **Image generation**: OpenAI DALL·E, Stability AI, AWS Bedrock, or local pipelines
- **Storage**: Local filesystem, S3, GCS, or Azure Blob

## Current Phase: Phase 1 — Project Initialization

✅ Project structure created
✅ Backend FastAPI app with health endpoint
✅ Frontend Next.js UI skeleton with professional design
✅ Agent architecture skeletons with clean interfaces
✅ Provider abstractions (TextGenerator, ImageGenerator, StorageProvider)
✅ `.env.example` with placeholder configuration
✅ `.gitignore` configured
✅ Docker Compose configuration
✅ Initial tests for the health endpoint

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project initialization + GitHub | ✅ Complete |
| 2 | Backend MVP | 🔄 Planned |
| 3 | Frontend MVP | 🔄 Planned |
| 4 | Image generation provider | 🔄 Planned |
| 5 | Planner / Router Agent | 🔄 Planned |
| 6 | Infographic Agent | 🔄 Planned |
| 7 | Complexity Agent | 🔄 Planned |
| 8 | Critic Agent | 🔄 Planned |
| 9 | Revision Agent | 🔄 Planned |
| 10 | History / database | 🔄 Planned |
| 11 | Advanced UI | 🔄 Planned |
| 12 | Docker | 🔄 Planned |
| 13 | Production hardening | 🔄 Planned |

## Getting Started

See [docs/README.md](docs/README.md) for detailed setup instructions.
