from __future__ import annotations

import json
from typing import Any

from app.runtime.figma.adapter import FigmaAdapter, FigmaError, FigmaTimeoutError
from app.runtime.figma.models import (
    FigmaColorPalette,
    FigmaComponentItem,
    FigmaSection,
    FigmaWireframeRequest,
)
from app.runtime.figma.validator import validate_figma_request
from app.skills.base import BaseSkill, BaseTool, TrustLevel


class GenerateFigmaWireframeTool(BaseTool):
    name = "generate_wireframe"
    description = (
        "Generate an interactive UI wireframe directly from Figma based on natural "
        "language specifications, layout form factor, sections, and optional brand color palette."
    )
    required_permission = "figma:design:generate"
    parameters = {
        "type": "object",
        "properties": {
            "screen_name": {
                "type": "string",
                "description": "Title of the screen, e.g. 'Customer Dispute Resolution Dashboard'.",
            },
            "layout_type": {
                "type": "string",
                "enum": ["desktop", "mobile", "modal", "dashboard"],
                "description": "Layout form factor. Default is 'desktop'.",
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Section header, e.g. 'Metric Summary'.",
                        },
                        "layout": {
                            "type": "string",
                            "enum": ["row", "column", "grid"],
                            "description": "Layout direction for items in this section.",
                        },
                        "components": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {
                                        "type": "string",
                                        "enum": [
                                            "button",
                                            "input",
                                            "card",
                                            "badge",
                                            "table",
                                            "navbar",
                                            "modal",
                                        ],
                                    },
                                    "variant": {
                                        "type": "string",
                                        "enum": ["primary", "secondary", "outline", "ghost"],
                                    },
                                    "label": {"type": "string"},
                                },
                                "required": ["name", "type"],
                            },
                        },
                    },
                    "required": ["name"],
                },
                "description": "List of UI layout sections containing components.",
            },
            "color_palette": {
                "type": "object",
                "properties": {
                    "canvas": {
                        "type": "string",
                        "description": "Hex color for background (defaults to #FBF7EE)",
                    },
                    "primary": {
                        "type": "string",
                        "description": "Hex color for brand headers (defaults to #1E1B4B)",
                    },
                    "accent": {
                        "type": "string",
                        "description": "Hex color for primary CTA buttons (defaults to #FF3366)",
                    },
                    "card_bg": {
                        "type": "string",
                        "description": "Hex color for cards/surface (defaults to #FFFFFF)",
                    },
                },
                "description": "Optional user-defined color palette hex codes.",
            },
            "source_spec_doc": {
                "type": "string",
                "description": (
                    "Optional reference to a source PRD or technical specification "
                    "document used to derive this design."
                ),
            },
        },
        "required": ["screen_name"],
    }

    def __init__(self, adapter: FigmaAdapter) -> None:
        self._adapter = adapter

    def enrich_arguments(self, arguments: dict, prior_messages: list[dict]) -> dict:
        # source_spec_doc is optional in the schema, so whether a wireframe
        # gets grounded to the document a preceding search_solr call actually
        # found is otherwise up to the model choosing to pass it — it does so
        # inconsistently. If the model already named a doc, respect it;
        # otherwise fall back to the id of the top result from the most
        # recent successful search_solr call in this execution, if any.
        if arguments.get("source_spec_doc"):
            return arguments
        for message in reversed(prior_messages):
            if message.get("role") != "tool":
                continue
            try:
                content = json.loads(message.get("content") or "")
            except (TypeError, ValueError):
                continue
            if not isinstance(content, dict):
                continue
            docs = content.get("documents")
            if isinstance(docs, list) and docs and isinstance(docs[0], dict):
                doc_id = docs[0].get("id")
                if doc_id:
                    return {**arguments, "source_spec_doc": doc_id}
        return arguments

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        screen_name = kwargs.get("screen_name", "").strip()
        layout_type = kwargs.get("layout_type", "desktop")
        source_spec_doc = kwargs.get("source_spec_doc")

        # Parse sections if provided
        sections: list[FigmaSection] = []
        raw_sections = kwargs.get("sections") or []
        if isinstance(raw_sections, list):
            for s in raw_sections:
                if not isinstance(s, dict):
                    continue
                comps = []
                for c in s.get("components", []):
                    if isinstance(c, dict) and "name" in c and "type" in c:
                        comps.append(
                            FigmaComponentItem(
                                name=c["name"],
                                type=c["type"],
                                variant=c.get("variant", "default"),
                                label=c.get("label", ""),
                            )
                        )
                sections.append(
                    FigmaSection(
                        name=s.get("name", "Section"),
                        layout=s.get("layout", "column"),
                        components=comps,
                    )
                )

        # Parse custom palette if provided
        raw_palette = kwargs.get("color_palette") or {}
        palette = FigmaColorPalette()
        if isinstance(raw_palette, dict):
            if "canvas" in raw_palette:
                palette.canvas = str(raw_palette["canvas"])
            if "primary" in raw_palette:
                palette.primary = str(raw_palette["primary"])
            if "accent" in raw_palette:
                palette.accent = str(raw_palette["accent"])
            if "card_bg" in raw_palette:
                palette.card_bg = str(raw_palette["card_bg"])

        request = FigmaWireframeRequest(
            screen_name=screen_name,
            layout_type=layout_type,
            sections=sections,
            palette=palette,
            source_spec_doc=source_spec_doc,
        )

        validation = validate_figma_request(request)
        if not validation.allowed:
            return {
                "success": False,
                "error": "validation_failed",
                "reason": validation.reason,
            }

        try:
            result = await self._adapter.generate_wireframe(validation.request)
        except FigmaTimeoutError as exc:
            return {"success": False, "error": "timeout", "reason": str(exc)}
        except FigmaError as exc:
            return {"success": False, "error": "figma_error", "reason": str(exc)}

        return {
            "success": True,
            "wireframe_id": result.wireframe_id,
            "screen_name": result.screen_name,
            "layout_type": result.layout_type,
            "embed_url": result.embed_url,
            "figma_file_url": result.figma_file_url,
            "svg_content": result.svg_content,
            "palette": result.palette,
            "node_tree": result.node_tree,
            "ux_breakdown": result.ux_breakdown,
            "sections_count": result.sections_count,
            "components_count": result.components_count,
        }

    def audit_metadata(self, arguments: dict[str, Any], result: Any) -> dict[str, Any] | None:
        if not isinstance(result, dict):
            return None
        return {
            "wireframe_id": result.get("wireframe_id"),
            "screen_name": arguments.get("screen_name") or result.get("screen_name"),
            "layout_type": arguments.get("layout_type") or result.get("layout_type", "desktop"),
            "sections_count": result.get("sections_count", 0),
            "components_count": result.get("components_count", 0),
            "embed_url": result.get("embed_url"),
            "figma_file_url": result.get("figma_file_url"),
            "svg_content": result.get("svg_content"),
            "palette": result.get("palette"),
            "node_tree": result.get("node_tree"),
            "ux_breakdown": result.get("ux_breakdown"),
            "source_spec_doc": arguments.get("source_spec_doc"),
        }


class GetFigmaComponentsTool(BaseTool):
    name = "get_figma_components"
    description = (
        "Inspect available UI components, design system tokens, and templates "
        "from the Figma component library."
    )
    required_permission = "figma:design:read"
    parameters = {
        "type": "object",
        "properties": {
            "file_key": {
                "type": "string",
                "description": "Optional Figma file key. Uses default design system if omitted.",
            },
        },
    }

    def __init__(self, adapter: FigmaAdapter) -> None:
        self._adapter = adapter

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        file_key = kwargs.get("file_key")
        try:
            components = await self._adapter.get_components(file_key)
            return {"success": True, "components": components, "total": len(components)}
        except FigmaError as exc:
            return {"success": False, "error": "figma_error", "reason": str(exc)}

    def audit_metadata(self, arguments: dict[str, Any], result: Any) -> dict[str, Any] | None:
        if not isinstance(result, dict):
            return None
        return {
            "file_key": arguments.get("file_key", "default"),
            "total_components": result.get("total", 0),
        }


class FigmaDesignSkill(BaseSkill):
    name = "figma_design"
    display_name = "Figma Design Studio"
    description = (
        "Generate interactive UI wireframes, design system tokens, and layouts directly "
        "from Figma based on natural language prompts and PRD specifications."
    )
    version = "1.0.0"
    trust_level = TrustLevel.VERIFIED
    required_permissions = ["figma:design:generate", "figma:design:read"]

    def __init__(self, adapter: FigmaAdapter | None = None) -> None:
        self._adapter = adapter or FigmaAdapter()

    def get_tools(self) -> list[BaseTool]:
        return [
            GenerateFigmaWireframeTool(self._adapter),
            GetFigmaComponentsTool(self._adapter),
        ]
