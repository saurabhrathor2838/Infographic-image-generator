# Infographic-image-generator

# AI Visual Generator

## Project

**AI Visual Generator** — a web application that generates:

- **Infographic images**
- **Complexity images** (complex technical visuals)

The application uses an **Agentic AI workflow** to understand a user's request,
plan the visual as a structured specification, and render it programmatically
to SVG — entirely in Python, with **no AI image-generation model or API**.

> **Architecture Principle:** AI is used to produce *structured visual
> specifications* (JSON). The final SVG/PNG images are generated *entirely by
> Python programmatic rendering* (`SVGRenderer`). No paid image-generation
> APIs (DALL·E, Stability AI, AWS Bedrock, etc.) are used at any point.

## Purpose

A web application for generating infographic images and complex
technical / complexity images using an agentic AI workflow where:

1. **AI** (text-generation LLM) analyses the user prompt and produces a
   validated `VisualSpecification` (JSON).
2. **Python** programmatically renders the specification to SVG via a
   dependency-free renderer.
3. **Frontend** displays the SVG directly — no image APIs, no external
   image files, no paid services.

## Architecture

### Current Architecture (Phase 5–7)

```
USER
  │  POST /api/plan {prompt, visual_type, complexity}
  ▼
FRONTEND (Next.js)
  │  Proxies /api/* → Backend
  ▼
BACKEND API (FastAPI)
  │  GET  /api/health
  │  POST /api/plan
  │  POST /api/render  (render a caller-supplied spec)
  │  GET  /api/samples/*
  ▼
VISUAL PLANNER AGENT (AI → spec)
  │  system_prompt = schema + prompt + visual_type + complexity
  │  LLM (OpenAI / Mock) → JSON string
  │  Parse → Validate (Pydantic) → VisualSpecification
  ▼
SVG RENDERER (Python → SVG)
  │  VisualSpecification → SVG document string
  │  (stdlib only, no external deps)
  ▼
SVG RESPONSE (image/svg+xml)
  │  Displayed inline in ResultArea via dangerouslySetInnerHTML
  ▼
USER sees the rendered SVG
```

### Data Flow

| Stage | Component | Technology | AI? |
|-------|-----------|------------|-----|
| 1 | User input | Frontend form | No |
| 2 | API endpoint | FastAPI `/api/plan` | No |
| 3 | Spec planning | `VisualPlannerAgent` + `TextGenerator` | **Yes (text only)** |
| 4 | Spec validation | Pydantic `VisualSpecification` | No |
| 5 | Image rendering | `SVGRenderer` (Python stdlib) | **No** |
| 6 | Display | Frontend `ResultArea` | No |

### Deprecated Architecture (Phases 1–3)

```
USER
  │  POST /api/generate
  ▼
BACKEND API (FastAPI)
  │  POST /api/generate
  ▼
GENERATION ORCHESTRATOR
  │  Planner → Router → Specialist
  │  → DesignPlanner → ImagePromptGenerator
  │  → IMAGE GENERATOR (DALL-E / Stability / Bedrock)  ← ❌ DEPRECATED
  │  → CriticAgent → RevisionAgent
  ▼
JSON response (plan, routing, mock=true, final_image=null)
```

The old `/api/generate` endpoint and `GenerationOrchestrator` used an
`ImageGenerator` provider abstraction to call paid image APIs. **This path
is deprecated.** Image generation is now exclusively handled by the Python
`SVGRenderer`. The `/api/generate` endpoint remains for backward compatibility
but is no longer the primary generation path.

## Technology

### Backend
- **Python 3.11**
- **FastAPI** — web framework with automatic OpenAPI docs
- **Pydantic v2** — data validation and settings management
- **Uvicorn** — ASGI server
- **Pytest** — testing framework
- **SVGRenderer** — dependency-free, stdlib-only CSS-to-SVG renderer

### Frontend
- **Next.js 14** (App Router)
- **React 18**
- **TypeScript**

### Infrastructure
- **Docker** — containerised services
- **Docker Compose** — local multi-service orchestration
- **GitHub** — version control

### AI & Rendering Providers

| Capability | Provider Type | Examples |
|------------|--------------|----------|
| **Text generation** (spec planning) | `TextGenerator` | OpenAI GPT, Anthropic Claude, Google Gemini, local LLMs |
| **Spec generation** (mock) | `TextGenerator` | `MockTextGenerator` (deterministic, no API) |
| **Image rendering** (Python) | `SVGRenderer` | Programmatic SVG from `VisualSpecification` (stdlib only) |
| **PNG export** (planned) | `PNGRenderer` | `cairosvg`, `svglib`, or Pillow (Python, no AI) |

> **No image-generation AI models are used.** The `ImageGenerator` provider
> abstraction (DALL·E, Stability AI, AWS Bedrock) has been **deprecated**.
> AI text generators only produce JSON specifications; Python produces all images.

## Current Phase: Phase 7 — Complexity Image Generator

✅ Phase 1 — Project initialization + GitHub  
✅ Phase 2 — Backend FastAPI app with health endpoint  
✅ Phase 3 — Frontend Next.js UI skeleton with professional design  
✅ Phase 4 — *Deprecated*: Image generation provider (replaced by Python `SVGRenderer`)  
✅ Phase 5 — VisualPlannerAgent (AI → VisualSpecification)  
✅ Phase 6 — Infographic generation flow (prompt → SVG via `/api/plan`)  
✅ Phase 7 — Complexity Image generation (Low/Medium/High detail via SVG)

> **Note:** Image generation is done **entirely by Python** (`SVGRenderer`).
> No paid AI APIs are called. The LLM provider (when configured) only produces
> structured `VisualSpecification` JSON. A mock provider (`AI_PROVIDER=mock`)
> allows full local testing with no API key.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check — returns service status. |
| GET | `/docs` | Interactive API documentation (Swagger UI). |
| POST | `/api/plan` | Plan a visual from a prompt and render to SVG (primary). |
| POST | `/api/render` | Render a caller-supplied specification to SVG. |
| GET | `/api/samples/water-cycle` | Render the bundled Water Cycle sample as SVG. |
| GET | `/api/samples/water-cycle/spec` | Return the Water Cycle sample spec as JSON. |
| POST | `/api/generate` | Legacy generation endpoint (deprecated, returns JSON plan). |

#### POST /api/plan

Request body:

```json
{
    "prompt": "Create an infographic explaining the water cycle.",
    "visual_type": "infographic",
    "complexity": "medium"
}
```

`visual_type` accepts: `auto`, `infographic`, `complexity_image` (defaults to `auto`).
`complexity` accepts: `low`, `medium`, `high` (defaults to `medium`).

Response:

```
Content-Type: image/svg+xml
<body>
  <svg xmlns="http://www.w3.org/2000/svg" width="900" height="650" ...>
    ...
  </svg>
</body>
```

Returns SVG on success (200), 422 for invalid input, 502 if the AI output
cannot be parsed into a valid specification, 503 if no LLM provider is
configured.

#### Complexity Levels

| Level | Nodes | Shapes | Connections | Text/Annotations |
|-------|-------|--------|-------------|-------------------|
| **Low** | 2–3 | 1 | 1 | 1 |
| **Medium** | 3–4 | 2–3 | 3 | 2 |
| **High** | 6 | 4–6 | 6+ | 4–5 |

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project initialization + GitHub | ✅ Complete |
| 2 | Backend FastAPI app with health & generation endpoints | ✅ Complete |
| 3 | Frontend Next.js UI skeleton | ✅ Complete |
| 4 | **Deprecated**: Image generation provider | 🚫 Deprecated (replaced by `SVGRenderer`) |
| 5 | VisualPlannerAgent (AI → `VisualSpecification` JSON) | ✅ Complete |
| 6 | Infographic generation flow (prompt → SVG) | ✅ Complete |
| 7 | Complexity Image generation (Low/Medium/High) | ✅ Complete |
| 8 | Critic Agent (spec critique, not image critique) | 🔄 Planned |
| 9 | Revision Agent (spec regeneration) | 🔄 Planned |
| 10 | PNG export (Python `cairosvg`/`svglib`) | 🔄 Planned |
| 11 | Advanced UI (zoom, pan, download SVG/PNG) | 🔄 Planned |
| 12 | Production Docker + CI/CD | 🔄 Planned |
| 13 | Testing & documentation | 🔄 Planned |

### Phase 8 — Critic Agent (Proposed)

**Scope:** Critique the *specification* (JSON), not the rendered image.
Since images are now Python-rendered (not AI-generated), image-based critique
is not applicable. The Critic Agent will evaluate the `VisualSpecification`
for completeness, layout balance, and semantic correctness, then optionally
request the planner to regenerate with a refined prompt.

### Phase 9 — Revision Agent (Proposed)

**Scope:** When the spec critique fails, the Revision Agent appends feedback
to the system prompt and re-runs the `VisualPlannerAgent` to produce an
improved `VisualSpecification`. The `SVGRenderer` then re-renders. No image
regeneration via AI is needed because rendering is deterministic and free.

### Phase 10 — PNG Export (Planned)

Export the rendered SVG to PNG using a Python library (`cairosvg`, `svglib`,
or Pillow). This keeps all image generation in Python — no AI image models.

## Configuration

The backend uses environment variables (optionally via a `.env` file):

```bash
# Required for real AI planning (set to "openai" or another provider)
AI_PROVIDER=mock          # Use "mock" for local dev/testing (no API key needed)
OPENAI_API_KEY=your-key   # Required when AI_PROVIDER=openai

# Optional
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
TEXT_MODEL=gpt-4o         # Text model for the planner
NEXT_PUBLIC_API_URL=http://localhost:8000  # Frontend → backend URL
```

## Getting Started

See [docs/README.md](docs/README.md) for detailed setup instructions.
