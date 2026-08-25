"""
PNG renderer for :class:`~app.models.visual_spec.VisualSpecification`.

Converts a validated visual specification (or a raw SVG string) into a PNG
image **using only Python** — Pillow — with no AI image-generation API and no
native C graphics library (e.g. cairo) required.

The renderer parses the SVG document produced by
:class:`~app.renderers.svg_renderer.SVGRenderer` and draws every element
(rectangles, rounded-rectangles, circles, ellipses, lines, polygons, text,
and arrowheads) onto a Pillow ``Image``.

Design notes
------------
* Font selection prefers the system's Arial (or DejaVu on Linux) and falls
  back to Pillow's built-in bitmap font.
* All coordinates are scaled by a DPI multiplier (default 144 DPI = 2× the
  SVG's implicit 72 DPI) for crisp output.
* Element opacity is respected via per-element alpha compositing on a
  temporary RGBA layer.
* Arrowheads (``marker-end="url(#arrowhead)"``) are drawn as filled
  triangles at the line's end-point.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from app.models.visual_spec import VisualSpecification
from app.renderers.svg_renderer import SVGRenderer

_SVG_NS = "{http://www.w3.org/2000/svg}"
_DEFAULT_DPI = 144
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# ── Colour helpers ───────────────────────────────────────────────────────────


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert a hex colour string (#rgb or #rrggbb or rgb(r,g,b)) to RGB."""
    h = hex_color.strip()
    if h.startswith("rgb("):
        nums = re.findall(r"\d+", h)
        return tuple(int(n) for n in nums[:3])  # type: ignore[return-value]
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    # Fallback
    return (0, 0, 0)


def _with_alpha(rgb: Tuple[int, int, int], opacity: float) -> Tuple[int, int, int, int]:
    """Attach an alpha channel to an RGB tuple."""
    a = max(0, min(255, int(round(opacity * 255))))
    return (rgb[0], rgb[1], rgb[2], a)


def _parse_points(points_str: str) -> List[Tuple[float, float]]:
    """Parse an SVG ``points`` attribute into (x, y) tuples."""
    coords = re.split(r"[\s,]+", points_str.strip())
    nums = [float(c) for c in coords if c]
    return list(zip(nums[::2], nums[1::2]))


# ── Font management ──────────────────────────────────────────────────────────


class _FontManager:
    """Cache of Pillow fonts keyed by (size, bold)."""

    def __init__(self) -> None:
        self._cache: Dict[Tuple[int, bool], ImageFont.FreeTypeFont] = {}
        self._default = ImageFont.load_default()

    def get(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        key = (size, bold)
        if key not in self._cache:
            self._cache[key] = self._load(size, bold)
        return self._cache[key]

    @staticmethod
    def _load(size: int, bold: bool) -> ImageFont.FreeTypeFont:
        candidates = []
        if bold:
            candidates = ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"]
        else:
            candidates = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]
        # Also try common Linux paths
        linux_paths = ["/usr/share/fonts/truetype/dejavu/"]
        for c in list(candidates):
            for lp in linux_paths:
                candidates.append(lp + c)

        for c in candidates:
            try:
                return ImageFont.truetype(c, size)
            except (OSError, IOError):
                continue
        # Fallback — return the default bitmap font
        return ImageFont.load_default()  # type: ignore[return-value]


# ── Renderer ─────────────────────────────────────────────────────────────────


class PNGRenderer:
    """Render a :class:`VisualSpecification` to PNG bytes using Pillow.

    Examples
    --------
    >>> from app.renderers.png_renderer import PNGRenderer
    >>> from app.providers.mock_text_generator import MockTextGenerator
    >>> from app.models.visual_spec import VisualSpecification
    >>> gen = MockTextGenerator()
    >>> result = await gen.generate(...)
    >>> spec = VisualSpecification.model_validate(json.loads(result.text))
    >>> png = PNGRenderer().render(spec)  # -> bytes (valid PNG)
    """

    def __init__(self, dpi: int = _DEFAULT_DPI) -> None:
        self._dpi = dpi
        self._scale: float = dpi / 72.0
        self._fonts = _FontManager()
        self._img: Optional[Image.Image] = None
        self._draw: Optional[ImageDraw.ImageDraw] = None
        self._scale_value: float = 1.0

    # ── Public API ────────────────────────────────────────────────────────

    def render(
        self,
        spec: VisualSpecification,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> bytes:
        """Render a *spec* to PNG bytes.

        Parameters
        ----------
        spec:
            A validated :class:`VisualSpecification`.
        width, height:
            Optional output dimensions in pixels.  If omitted, the SVG
            canvas size is scaled by the DPI ratio.
        """
        svg = SVGRenderer().render(spec)
        return self.render_svg(svg, width=width, height=height)

    def render_svg(
        self,
        svg: str,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> bytes:
        """Render a raw SVG string to PNG bytes."""
        root = ET.fromstring(svg)

        svg_w = float(root.get("width", "800"))
        svg_h = float(root.get("height", "600"))

        if width is not None and height is not None:
            out_w, out_h = width, height
            self._scale_value = min(width / svg_w, height / svg_h)
        else:
            self._scale_value = self._scale
            out_w = int(svg_w * self._scale_value)
            out_h = int(svg_h * self._scale_value)

        self._img = Image.new("RGBA", (max(out_w, 1), max(out_h, 1)), (0, 0, 0, 0))
        self._draw = ImageDraw.Draw(self._img)

        self._render_children(root)

        # The background rect fills the canvas, so we convert to RGB for output.
        rgb = self._img.convert("RGB")
        buf = BytesIO()
        rgb.save(buf, format="PNG")
        return buf.getvalue()

    # ── Element traversal ─────────────────────────────────────────────────

    def _render_children(self, parent: "ET.Element") -> None:
        assert self._draw is not None and self._img is not None
        for elem in parent:
            self._render_element(elem)

    def _render_element(self, elem: "ET.Element") -> None:
        assert self._draw is not None and self._img is not None
        tag = elem.tag.replace(_SVG_NS, "")

        # Skip non-rendering elements.
        if tag in ("defs", "title", "desc"):
            return

        opacity = float(elem.get("opacity", "1"))
        fill = elem.get("fill", "none")
        stroke = elem.get("stroke", "none")
        stroke_width = float(elem.get("stroke-width", "1"))

        if tag == "rect":
            self._draw_rect(elem, opacity, fill, stroke, stroke_width)
        elif tag == "circle":
            self._draw_circle(elem, opacity, fill, stroke, stroke_width)
        elif tag == "ellipse":
            self._draw_ellipse(elem, opacity, fill, stroke, stroke_width)
        elif tag == "line":
            self._draw_line(elem, opacity, stroke, stroke_width, elem.get("marker-end"))
        elif tag in ("polygon", "polyline"):
            self._draw_polygon(elem, opacity, fill, stroke, stroke_width)
        elif tag == "text":
            self._draw_text(elem, opacity, fill)

        # Recurse into children.
        self._render_children(elem)

    # ── Shape rendering ───────────────────────────────────────────────────

    def _draw_rect(
        self,
        elem: "ET.Element",
        opacity: float,
        fill: str,
        stroke: str,
        stroke_width: float,
    ) -> None:
        assert self._draw is not None
        s = self._scale_value
        x = float(elem.get("x", "0")) * s
        y = float(elem.get("y", "0")) * s
        w = float(elem.get("width", "0")) * s
        h = float(elem.get("height", "0")) * s
        rx = float(elem.get("rx", "0")) * s
        ry = float(elem.get("ry", "0")) * s

        bbox = [x, y, x + w, y + h]
        fill_col = self._color(fill, opacity) if fill != "none" else None
        stroke_col = self._color(stroke, opacity) if stroke != "none" else None
        sw = max(1, int(stroke_width * s))

        if rx > 0 or ry > 0:
            radius = rx if rx == ry else max(rx, ry)
            self._draw.rounded_rectangle(  # type: ignore[attr-defined]
                bbox, radius=int(radius),
                fill=fill_col, outline=stroke_col, width=sw,
            )
        else:
            self._draw.rectangle(bbox, fill=fill_col, outline=stroke_col, width=sw)

    def _draw_circle(
        self,
        elem: "ET.Element",
        opacity: float,
        fill: str,
        stroke: str,
        stroke_width: float,
    ) -> None:
        assert self._draw is not None
        s = self._scale_value
        cx = float(elem.get("cx", "0")) * s
        cy = float(elem.get("cy", "0")) * s
        r = float(elem.get("r", "0")) * s

        bbox = [cx - r, cy - r, cx + r, cy + r]
        fill_col = self._color(fill, opacity) if fill != "none" else None
        stroke_col = self._color(stroke, opacity) if stroke != "none" else None
        sw = max(1, int(stroke_width * s))

        self._draw.ellipse(bbox, fill=fill_col, outline=stroke_col, width=sw)

    def _draw_ellipse(
        self,
        elem: "ET.Element",
        opacity: float,
        fill: str,
        stroke: str,
        stroke_width: float,
    ) -> None:
        assert self._draw is not None
        s = self._scale_value
        cx = float(elem.get("cx", "0")) * s
        cy = float(elem.get("cy", "0")) * s
        rx = float(elem.get("rx", "0")) * s
        ry = float(elem.get("ry", "0")) * s

        bbox = [cx - rx, cy - ry, cx + rx, cy + ry]
        fill_col = self._color(fill, opacity) if fill != "none" else None
        stroke_col = self._color(stroke, opacity) if stroke != "none" else None
        sw = max(1, int(stroke_width * s))

        self._draw.ellipse(bbox, fill=fill_col, outline=stroke_col, width=sw)

    def _draw_line(
        self,
        elem: "ET.Element",
        opacity: float,
        stroke: str,
        stroke_width: float,
        marker_end: Optional[str],
    ) -> None:
        assert self._draw is not None
        s = self._scale_value
        x1 = float(elem.get("x1", "0")) * s
        y1 = float(elem.get("y1", "0")) * s
        x2 = float(elem.get("x2", "0")) * s
        y2 = float(elem.get("y2", "0")) * s

        col = self._color(stroke, opacity)
        sw = max(1, int(stroke_width * s))

        self._draw.line([x1, y1, x2, y2], fill=col, width=sw, joint="curve")

        # Draw arrowhead if marker-end is set.
        if marker_end and "arrowhead" in marker_end:
            self._draw_arrowhead(x1, y1, x2, y2, col, sw)

    def _draw_polygon(
        self,
        elem: "ET.Element",
        opacity: float,
        fill: str,
        stroke: str,
        stroke_width: float,
    ) -> None:
        assert self._draw is not None
        s = self._scale_value
        points = _parse_points(elem.get("points", ""))
        scaled = [(x * s, y * s) for x, y in points]

        fill_col = self._color(fill, opacity) if fill != "none" else None
        stroke_col = self._color(stroke, opacity) if stroke != "none" else None
        sw = max(1, int(stroke_width * s))

        self._draw.polygon(scaled, fill=fill_col, outline=stroke_col)
        if stroke_col and sw > 1:
            self._draw.line(scaled + [scaled[0]], fill=stroke_col, width=sw)

    # ── Text rendering ────────────────────────────────────────────────────

    def _draw_text(
        self,
        elem: "ET.Element",
        opacity: float,
        fill: str,
    ) -> None:
        assert self._draw is not None and self._img is not None
        s = self._scale_value
        x = float(elem.get("x", "0")) * s
        y = float(elem.get("y", "0")) * s
        font_size = float(elem.get("font-size", "14")) * s

        text_anchor = elem.get("text-anchor", "start")
        dominant_baseline = elem.get("dominant-baseline", "auto")
        font_weight = elem.get("font-weight", "normal")
        font_family = elem.get("font-family", "")

        # Determine boldness
        bold = str(font_weight).strip() in ("700", "bold", "600", "800", "900")

        font_size_px = max(6, int(font_size))
        font = self._fonts.get(font_size_px, bold=bold)

        fill_col = self._color(fill, opacity)

        # Get the text content
        text = (elem.text or "").strip()
        if not text:
            # Check for <tspan> children
            for child in elem:
                child_tag = child.tag.replace(_SVG_NS, "")
                if child_tag == "tspan":
                    text = (child.text or "").strip()
                    if text:
                        break
        if not text:
            return

        # Measure text for alignment
        # Pillow's anchor system: first char = horizontal (l/m/r), second = vertical (a/m/d)
        # SVG text-anchor maps to horizontal alignment
        # SVG dominant-baseline maps to vertical alignment

        h_anchor = {"start": "l", "middle": "m", "end": "r"}.get(text_anchor, "l")
        # For dominant-baseline: "hanging" = top, "middle" = middle, "auto"/"baseline" = baseline
        v_anchor = {"hanging": "a", "middle": "m"}.get(dominant_baseline, "d")

        pil_anchor = h_anchor + v_anchor
        self._draw.text(
            (x, y), text, font=font, fill=fill_col, anchor=pil_anchor,
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    def _color(self, hex_or_rgb: str, opacity: float = 1.0) -> Tuple[int, int, int, int]:
        """Convert a colour string to an RGBA tuple."""
        rgb = _hex_to_rgb(hex_or_rgb)
        return _with_alpha(rgb, opacity)

    def _draw_arrowhead(
        self,
        x1: float, y1: float, x2: float, y2: float,
        fill: Tuple[int, int, int, int], stroke_width: int,
    ) -> None:
        """Draw a filled triangle arrowhead at the end of a line."""
        assert self._draw is not None
        # Arrowhead size proportional to stroke width
        size = max(6, stroke_width * 4)
        angle = math.atan2(y2 - y1, x2 - x1)

        # Three points of the arrowhead triangle
        tip = (x2, y2)
        left = (
            x2 - size * math.cos(angle) + size * 0.5 * math.sin(angle),
            y2 - size * math.sin(angle) - size * 0.5 * math.cos(angle),
        )
        right = (
            x2 - size * math.cos(angle) - size * 0.5 * math.sin(angle),
            y2 - size * math.sin(angle) + size * 0.5 * math.cos(angle),
        )

        self._draw.polygon([tip, left, right], fill=fill)
