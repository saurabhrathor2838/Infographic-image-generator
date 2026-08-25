"""
Template package for programmatic infographic generation.

Exports :class:`~app.templates.engine.TemplateEngine` — a reusable engine
that selects an appropriate diagram template from a natural-language prompt
and generates a validated :class:`~app.models.visual_spec.VisualSpecification`.

Supported templates:

* ``process_flow`` — sequential steps with arrows
* ``timeline`` — events on a horizontal time axis
* ``comparison`` — side-by-side item comparison
* ``cycle`` — nodes arranged in a circular cycle
* ``hierarchy`` — tree structure with parent→child connections
* ``statistics`` — bar-chart / data visualisation
* ``technical_system`` — system architecture with data flows
* ``step_by_step`` — numbered vertical steps

All templates scale across Low / Medium / High complexity and produce
specs that are rendered entirely by Python (SVGRenderer / PNGRenderer) —
no AI image-generation APIs are involved.
"""

from app.templates.engine import TemplateEngine

__all__ = ["TemplateEngine"]
