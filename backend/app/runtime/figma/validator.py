from __future__ import annotations

import re
from dataclasses import dataclass

from app.runtime.figma.models import FigmaColorPalette, FigmaWireframeRequest

_HEX_COLOR_REGEX = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")
_ALLOWED_LAYOUTS = frozenset({"desktop", "mobile", "modal", "dashboard"})
_MAX_SECTIONS = 20
_MAX_TOTAL_COMPONENTS = 60

# GovernAI Brand Design System Defaults
_DEFAULT_PALETTE = FigmaColorPalette()


@dataclass(frozen=True)
class FigmaValidationResult:
    """Outcome of validating a wireframe request before dispatching to Figma."""

    allowed: bool
    reason: str | None
    request: FigmaWireframeRequest


def _sanitize_color(color_value: str | None, fallback: str) -> str:
    """Sanitize and validate a hex color code, falling back to brand default if invalid."""
    if not color_value or not isinstance(color_value, str):
        return fallback
    clean = color_value.strip()
    if not clean.startswith("#"):
        clean = f"#{clean}"
    if _HEX_COLOR_REGEX.match(clean):
        return clean.upper()
    return fallback


def validate_figma_request(request: FigmaWireframeRequest) -> FigmaValidationResult:
    """Validate and sanitize a Figma wireframe request."""
    if not request.screen_name or not request.screen_name.strip():
        return FigmaValidationResult(
            allowed=False,
            reason="screen_name must not be empty",
            request=request,
        )

    layout_type = request.layout_type.lower() if request.layout_type else "desktop"
    if layout_type not in _ALLOWED_LAYOUTS:
        return FigmaValidationResult(
            allowed=False,
            reason=(
                f"layout_type '{request.layout_type}' is unsupported. "
                f"Allowed: {sorted(_ALLOWED_LAYOUTS)}"
            ),
            request=request,
        )

    if len(request.sections) > _MAX_SECTIONS:
        return FigmaValidationResult(
            allowed=False,
            reason=f"Maximum sections limit exceeded ({len(request.sections)} > {_MAX_SECTIONS})",
            request=request,
        )

    total_components = sum(len(sec.components) for sec in request.sections)
    if total_components > _MAX_TOTAL_COMPONENTS:
        return FigmaValidationResult(
            allowed=False,
            reason=(
                f"Maximum components limit exceeded ({total_components} > {_MAX_TOTAL_COMPONENTS})"
            ),
            request=request,
        )

    # Sanitize color palette against GovernAI defaults
    sanitized_palette = FigmaColorPalette(
        canvas=_sanitize_color(request.palette.canvas, _DEFAULT_PALETTE.canvas),
        primary=_sanitize_color(request.palette.primary, _DEFAULT_PALETTE.primary),
        accent=_sanitize_color(request.palette.accent, _DEFAULT_PALETTE.accent),
        card_bg=_sanitize_color(request.palette.card_bg, _DEFAULT_PALETTE.card_bg),
        border=_sanitize_color(request.palette.border, _DEFAULT_PALETTE.border),
        text_muted=_sanitize_color(request.palette.text_muted, _DEFAULT_PALETTE.text_muted),
    )

    clean_request = request.model_copy(
        update={
            "layout_type": layout_type,
            "palette": sanitized_palette,
        }
    )

    return FigmaValidationResult(allowed=True, reason=None, request=clean_request)
