"""
Visual rendering package.

Sub-modules contain back-end renderers that turn a
:class:`~app.models.visual_spec.VisualSpecification` into an asset (e.g. an
SVG image).  Renderers implement a uniform interface: a ``render`` method that
accepts a validated ``VisualSpecification`` and returns the rendered asset.
"""

from app.renderers.svg_renderer import SVGRenderer

__all__ = ["SVGRenderer"]
