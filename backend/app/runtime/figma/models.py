from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class FigmaColorPalette(BaseModel):
    """Design system color tokens, defaulting to GovernAI's brand palette."""

    canvas: str = "#FBF7EE"  # GovernAI Cream background
    primary: str = "#1E1B4B"  # GovernAI Navy Deep
    accent: str = "#FF3366"  # GovernAI Coral / Pink action
    card_bg: str = "#FFFFFF"  # White card surface
    border: str = "#E5E7EB"  # Subtle border line
    text_muted: str = "#64748B"  # Slate muted text


class FigmaComponentItem(BaseModel):
    """A single UI component within a wireframe section."""

    name: str
    type: str = "button"  # button, input, card, badge, table, navbar, modal
    variant: str = "default"  # primary, secondary, outline, ghost
    label: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class FigmaSection(BaseModel):
    """A layout section (e.g. Header, Summary Cards, Data Grid, Footer)."""

    name: str
    layout: str = "column"  # row, column, grid
    components: list[FigmaComponentItem] = Field(default_factory=list)


class FigmaWireframeRequest(BaseModel):
    """Request schema for generating or querying a Figma wireframe."""

    screen_name: str
    layout_type: str = "desktop"  # desktop, mobile, modal, dashboard
    sections: list[FigmaSection] = Field(default_factory=list)
    palette: FigmaColorPalette = Field(default_factory=FigmaColorPalette)
    source_spec_doc: str | None = None
    file_key: str | None = None
    node_id: str | None = None


class FigmaNode(BaseModel):
    """Representation of a node in a Figma document tree."""

    id: str
    name: str
    type: str  # DOCUMENT, CANVAS, FRAME, COMPONENT, INSTANCE, TEXT, RECTANGLE
    children: list[FigmaNode] = Field(default_factory=list)
    style: dict[str, Any] = Field(default_factory=dict)
    fills: list[dict[str, Any]] = Field(default_factory=list)


class FigmaWireframeResult(BaseModel):
    """The structured result returned from Figma / FigmaAdapter."""

    wireframe_id: str = Field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:8]}")
    screen_name: str
    layout_type: str
    embed_url: str
    figma_file_url: str
    svg_content: str
    palette: dict[str, str]
    node_tree: dict[str, Any]
    ux_breakdown: str
    sections_count: int
    components_count: int
