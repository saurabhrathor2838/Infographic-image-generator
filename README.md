# AI Visual Generator

> **Phase 8 — Advanced Python Rendering Engine** is now implemented.
> Pure-Python SVG→PNG export, six reusable diagram layouts, and complexity
> scaling — with **no AI image-generation APIs** and **no native C graphics
> libraries** required.

## Quick Start

```bash
# Backend (Python 3.11+)
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
# .env is git-ignored — copy .env.example
cp ../.env.example .env
# Use mock provider (no API key) or openai
python -m uvicorn app.main:app --reload

# Frontend (Node 18+)
cd ../frontend
npm install
npm run dev
```

Backend:  [http://localhost:8000](http://localhost:8000)  
Frontend: [http://localhost:3000](http://localhost:3000)

## Architecture

### Overview

The project follows a clean, layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│   TypeScript / React / Tailwind — SVG/PNG display          │
└──────────────────────┬──────────────┬───────────────────────┘
                       │ REST API     │
┌──────────────────────▼──────────────▼──────────────────────┐
│                      Backend (FastAPI)                      │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐ │
│  │  /api/plan   │──▶│  Agents      │──▶│  Providers      │ │
│  │  /api/render │   │  (planner)   │   │  (mock/openai)  │ │
│  │  /api/health │   └──────────────┘   └─────────────────┘ │
│  │  /api/samples│                                          │
│  └──────────────┘                                          │
│        │                                                    │
│        ▼                                                    │
│  ┌──────────────────┐   ┌─────────────────────────────────┐ │
│  │ VisualSpec Model │──▶│ Renderers                       │ │
│  │ (Pydantic)       │   │  SVGRenderer  (stdlib only)    │ │
│  └──────────────────┘   │  PNGRenderer  (Pillow)          │ │
│                         │  LayoutEngine (6 layouts)        │ │
│                         └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Rendering Pipeline

1. **Prompt** → `VisualPlannerAgent` → `VisualSpecification` (Pydantic-validated JSON)
2. **Specification** → `SVGRenderer` → SVG string (pure Python, stdlib only)
3. **SVG string** → `PNGRenderer` → PNG bytes (Pillow, no native C libraries)
4. **Image** returned as `image/svg+xml` or `image/png`

```
POST /api/plan?format=svg   →  image/svg+xml
POST /api/plan?format=png   →  image/png  (Pillow, 144 DPI by default)
POST /api/render?format=png →  image/png
```

### Phase 8: Advanced Python Rendering Engine

#### PNGRenderer (`app/renderers/png_renderer.py`)

A pure-Python SVG→PNG converter built on **Pillow** — no `cairo`, no
`cairosvg`, no `svglib` native dependencies required. It parses the SVG
document produced by `SVGRenderer` and draws every element onto a Pillow
`Image`:

| SVG Element | Pillow Method |
|---|---|
| `<rect>` (sharp) | `ImageDraw.rectangle` |
| `<rect>` (rounded) | `ImageDraw.rounded_rectangle` |
| `<circle>` | `ImageDraw.ellipse` |
| `<ellipse>` | `ImageDraw.ellipse` |
| `<line>` | `ImageDraw.line` + triangle arrowhead |
| `<polygon>` | `ImageDraw.polygon` |
| `<text>` | `ImageDraw.text` (with anchor alignment) |

Features:
- **DPI scaling** (default 144 DPI = 2× the SVG's implicit 72 DPI)
- **Font fallback** (Arial → Arial Bold → DejaVu → Pillow bitmap)
- **Opacity support** via RGBA compositing
- **Arrowhead rendering** for directional lines (Marker-end)

```python
from app.renderers.png_renderer import PNGRenderer
from app.renderers.svg_renderer import SVGRenderer

svg = SVGRenderer().render(spec)        # → str
png = PNGRenderer().render(spec)        # → bytes (valid PNG)
png2 = PNGRenderer().render_svg(svg)    # render pre-existing SVG
```

#### LayoutEngine (`app/renderers/layouts.py`)

Six reusable, complexity-scaled diagram layouts that produce
`VisualSpecification` objects:

| Layout | Low | Medium | High |
|---|---|---|---|
| **process_flow** | 2 nodes | 4 nodes | 6 nodes + cross-connections |
| **timeline** | 2 events | 4 events | 6 events + time labels |
| **comparison** | 2×2 items | 3×2 items | 4×2 items + divider |
| **hierarchy** | root + 2 | root + 2 + 4 grandchildren | 3-level tree |
| **cycle** | 3 nodes | 5 nodes | 7 nodes (ring) |
| **technical_diagram** | 3 components | 5 components | 7 components + cross-flows |

```python
from app.renderers.layouts import LayoutEngine

spec = LayoutEngine.generate(
    prompt="Explain the software development lifecycle",
    layout="process_flow",      # or: timeline, comparison, hierarchy, cycle, technical_diagram
    complexity="medium",        # low / medium / high
)
png = PNGRenderer().render(spec)
```

### Providers

| Provider | Env Vars | Notes |
|---|---|---|
| `mock` | `AI_PROVIDER=mock` | Deterministic, no API key. For local dev & tests. |
| `openai` | `AI_PROVIDER=openai`, `OPENAI_API_KEY=...` | Real LLM (OpenAI). |

## Environment

See `.env.example` for all available settings. Copy to `.env` (git-ignored).

## Testing

```bash
cd backend
.venv\Scripts\pytest tests/ -v
```

## License

MIT
