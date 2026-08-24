# AI Visual Generator — Agents Directory

This directory contains design documents, architecture notes, and future
implementation specs for the agentic AI workflow.

## Agent Workflow

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
             ▼
      DESIGN PLANNER
             ▼
   IMAGE PROMPT GENERATOR
             ▼
      IMAGE GENERATOR
             ▼
        CRITIC AGENT
             ▼
      ┌──────┴──────┐
      │             │
     PASS          FAIL
      │             │
      ▼             ▼
 FINAL IMAGE    REVISION AGENT
                    │
                    └──→ Regenerate
```

## Agent Descriptions

| Agent                  | File                          | Purpose                                      |
| ---------------------- | ----------------------------- | -------------------------------------------- |
| Planner Agent          | `backend/app/agents/planner.py`     | Analyses the user request and creates a plan.|
| Router Agent           | `backend/app/agents/router.py`      | Routes the request to the correct specialist.|
| Infographic Agent      | `backend/app/agents/infographic_agent.py` | Handles the infographic sub-workflow.    |
| Complexity Agent       | `backend/app/agents/complexity_agent.py`  | Handles the complexity-image sub-workflow.|
| Design Planner         | `backend/app/agents/design_planner.py`    | Creates a detailed design plan.             |
| Image Prompt Generator | `backend/app/agents/image_prompt_generator.py` | Creates a detailed image-generation prompt.|
| Critic Agent           | `backend/app/agents/critic.py`           | Evaluates generated images.                |
| Revision Agent         | `backend/app/agents/revision_agent.py`   | Improves prompts based on critic feedback. |

## Provider Abstractions

The application uses provider interfaces to remain agnostic of any single
AI provider:

- **TextGenerator** (`backend/app/providers/text_generator.py`) — LLM text generation
- **ImageGenerator** (`backend/app/providers/image_generator.py`) — Image generation
- **StorageProvider** (`backend/app/providers/storage_provider.py`) — Asset storage

See `backend/app/providers/` for the base class and interfaces.

## Orchestration

The `GenerationOrchestrator` (`backend/app/services/orchestrator.py`) coordinates
the agent workflow, managing state transitions and iteration loops.
