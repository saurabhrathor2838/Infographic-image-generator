"""
Critics package — programmatic quality validation for generated visuals.

Sub-modules contain critics that analyse a
:class:`~app.models.visual_spec.VisualSpecification` and its rendered output
(SVG / PNG) to detect issues such as out-of-bounds elements, overlapping
nodes, broken connections, complexity mismatches, and template mismatches.

All critics are pure Python and do **not** use any AI / LLM image-evaluation
API.  They operate on the structured spec and the SVG document string.
"""

from app.critics.quality_critic import VisualQualityCritic
from app.models.quality_report import QualityReport

__all__ = ["VisualQualityCritic", "QualityReport"]
