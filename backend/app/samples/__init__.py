"""
Sample visual specifications.

Each module provides a ready-made :class:`~app.models.visual_spec.VisualSpecification`
that can be rendered or served as an example.  The Water Cycle sample is the
default reference infographic for Phase 4.
"""

from app.samples.water_cycle import water_cycle, water_cycle_spec

__all__ = ["water_cycle", "water_cycle_spec"]
