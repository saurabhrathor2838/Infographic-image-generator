"""
Agent package — skeleton implementations for the agentic AI workflow.

The agents follow the pipeline described in the project README:

    Planner → Router → {InfographicAgent | ComplexityAgent}
                → DesignPlanner → ImagePromptGenerator
                → ImageGenerator → CriticAgent
                → {Critic PASS → Final Image | Critic FAIL → RevisionAgent → loop}
"""

from app.agents.base import AgentBase, AgentContext, AgentResult

__all__ = [
    "AgentBase",
    "AgentContext",
    "AgentResult",
]
