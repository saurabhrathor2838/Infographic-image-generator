"""
Visual rendering package.

Sub-modules contain back-end renderers that turn a
:class:`~app.models.visual_spec.VisualSpecification` into an asset (e.g. an
SVG or PNG image).  Renderers implement a uniform interface: a ``render``
method that accepts a validated ``VisualSpecification`` and returns the
rendered asset.

Both renderers are pure Python — no AI image-generation APIs, no native
C graphics libraries.  ``SVGRenderer`` produces an SVG document string;
``PNGRenderer`` produces PNG bytes by drawing every SVG element via Pillow.
``LayoutEngine`` generates reusable, complexity-scaled diagram layouts.
"""

from app.renderers.svg_renderer import SVGRenderer
from app.renderers.png_renderer import PNGRenderer
from app.renderers.layouts import LayoutEngine

__all__ = ["SVGRenderer", "PNGRenderer", "LayoutEngine"]
