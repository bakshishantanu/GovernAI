from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.domain.governance.middleware import govern_tool
from app.domain.policies.engine import PolicyEngine
from app.domain.policies.models import Policy, PolicyRule
from app.runtime.agent_graph import run_agent
from app.runtime.figma.adapter import FigmaAdapter
from app.runtime.figma.models import (
    FigmaColorPalette,
    FigmaComponentItem,
    FigmaSection,
    FigmaWireframeRequest,
)
from app.runtime.figma.validator import validate_figma_request
from app.runtime.llm.base import LLMProvider, LLMResponse, TokenUsage, ToolCall
from app.runtime.llm.service import LLMService
from app.runtime.solr.adapter import SolrAdapter
from app.skills.figma_design import (
    FigmaDesignSkill,
    GenerateFigmaWireframeTool,
    GetFigmaComponentsTool,
)
from app.skills.solr_search import SolrSearchSkill


def _make_mock_agent(passport_lifecycle: str = "ACTIVE"):
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.org_id = uuid.uuid4()
    agent.passport = MagicMock()
    agent.passport.id = uuid.uuid4()
    agent.passport.lifecycle_state = passport_lifecycle
    return agent


def _build_policy_engine(
    agent: Any,
    granted_permissions: list[str],
    policies: list[Policy] | None = None,
) -> PolicyEngine:
    agent_repo = MagicMock()
    agent_repo.get_agent = AsyncMock(return_value=agent)

    perm_repo = MagicMock()
    perm_mocks = []
    for p in granted_permissions:
        m = MagicMock()
        m.permission = p
        perm_mocks.append(m)
    perm_repo.get_permissions_for_passport = AsyncMock(return_value=perm_mocks)

    policy_repo = MagicMock()
    policy_repo.get_active_policies_for_org = AsyncMock(return_value=policies or [])

    audit_repo = MagicMock()
    audit_repo.count_recent_tool_calls = AsyncMock(return_value=0)

    return PolicyEngine(
        agent_repo=agent_repo,
        perm_repo=perm_repo,
        policy_repo=policy_repo,
        audit_repo=audit_repo,
    )


class _ScriptedLLMProvider(LLMProvider):
    name = "scripted_figma_test"

    def __init__(self, responses: list[LLMResponse]):
        self._responses = list(responses)
        self.call_count = 0

    async def chat(self, messages, *, tools=None, temperature=0.7, max_tokens=None) -> LLMResponse:
        response = self._responses[self.call_count]
        self.call_count += 1
        return response


# ==============================================================================
# 1. Figma Adapter & Validator Unit Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_figma_adapter_mock_generation():
    adapter = FigmaAdapter()
    req = FigmaWireframeRequest(
        screen_name="Mobile Checkout",
        layout_type="mobile",
        sections=[
            FigmaSection(
                name="Order Details",
                layout="column",
                components=[
                    FigmaComponentItem(name="Subtotal Card", type="card", label="Total: $99"),
                    FigmaComponentItem(
                        name="Pay CTA", type="button", variant="primary", label="Pay Now"
                    ),
                ],
            )
        ],
        palette=FigmaColorPalette(
            canvas="#FBF7EE",
            primary="#1E1B4B",
            accent="#FF3366",
            card_bg="#FFFFFF",
        ),
    )

    result = await adapter.generate_wireframe(req)
    assert result.screen_name == "Mobile Checkout"
    assert result.layout_type == "mobile"
    assert result.embed_url.startswith("https://www.figma.com/embed")
    assert "<svg" in result.svg_content
    assert "#FF3366" in result.svg_content
    assert "#1E1B4B" in result.svg_content
    assert result.sections_count == 1
    assert result.components_count == 2
    assert "UX Architecture" in result.ux_breakdown


def test_figma_validator_rejects_invalid_layout():
    req = FigmaWireframeRequest(
        screen_name="Invalid Screen",
        layout_type="hologram",
        sections=[],
    )
    val = validate_figma_request(req)
    assert val.allowed is False
    assert "unsupported" in val.reason


def test_figma_validator_sanitizes_palette():
    req = FigmaWireframeRequest(
        screen_name="Custom Colors",
        layout_type="desktop",
        sections=[],
        palette=FigmaColorPalette(
            canvas="#fbf7ee",
            primary="invalid_color",
            accent="#ff3366",
        ),
    )
    val = validate_figma_request(req)
    assert val.allowed is True
    # Sanitized invalid hex back to GovernAI Navy default
    assert val.request.palette.primary == "#1E1B4B"


# ==============================================================================
# 2. Skill Tools Execution & Audit Metadata Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_generate_wireframe_tool_execution_and_audit():
    adapter = FigmaAdapter()
    tool = GenerateFigmaWireframeTool(adapter=adapter)
    res = await tool.execute(
        screen_name="Settings Dashboard",
        layout_type="desktop",
        sections=[
            {
                "name": "Profile",
                "layout": "column",
                "components": [
                    {"name": "Email Input", "type": "input", "label": "user@example.com"},
                    {"name": "Save Button", "type": "button", "variant": "primary"},
                ],
            }
        ],
        color_palette={"canvas": "#FBF7EE", "accent": "#FF3366"},
    )

    assert res["success"] is True
    assert res["screen_name"] == "Settings Dashboard"
    assert "embed_url" in res
    assert "svg_content" in res

    meta = tool.audit_metadata({"screen_name": "Settings Dashboard"}, res)
    assert meta is not None
    assert meta["screen_name"] == "Settings Dashboard"
    assert meta["sections_count"] == 1
    assert meta["components_count"] == 2
    assert meta["embed_url"] == res["embed_url"]
    assert meta["svg_content"] == res["svg_content"]


@pytest.mark.asyncio
async def test_get_figma_components_tool():
    adapter = FigmaAdapter()
    tool = GetFigmaComponentsTool(adapter=adapter)
    res = await tool.execute(filter_type="button")
    assert res["success"] is True
    assert res["total"] >= 1
    assert any("Button" in c["name"] for c in res["components"])


# ==============================================================================
# 3. Governance Firewall & Policy Enforcement Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_governance_denies_without_figma_permission():
    agent = _make_mock_agent()
    # Agent only has solr permissions, missing figma:design:generate
    engine = _build_policy_engine(agent, ["solr:search:knowledge_base"])
    audit_service = AsyncMock()

    tool = GenerateFigmaWireframeTool(adapter=FigmaAdapter())
    decision = await govern_tool(
        policy_engine=engine,
        audit_service=audit_service,
        org_id=agent.org_id,
        agent_id=agent.id,
        execution_id=uuid.uuid4(),
        tool=tool,
        arguments={"screen_name": "Test Screen"},
    )

    assert decision == {
        "error": "denied",
        "reason": "Missing required permission: 'figma:design:generate'",
    }
    assert audit_service.log_tool_call.awaited
    call_args = audit_service.log_tool_call.call_args[0]
    assert call_args[4] is False  # allowed=False


@pytest.mark.asyncio
async def test_governance_brand_color_check_policy_rule():
    agent = _make_mock_agent()
    brand_policy = Policy(
        id=uuid.uuid4(),
        org_id=agent.org_id,
        name="Strict Brand Palette Policy",
        description="Blocks unauthorized non-brand colors in UI generation",
        enabled=True,
    )
    brand_policy.rules = [
        PolicyRule(
            id=uuid.uuid4(),
            policy_id=brand_policy.id,
            name="Brand Token Validator",
            rule_type="brand_color_check",
            config={"allowed_hex_codes": ["#FBF7EE", "#1E1B4B", "#FF3366", "#FFFFFF"]},
            priority=100,
            enabled=True,
        )
    ]

    engine = _build_policy_engine(
        agent,
        ["figma:design:generate", "figma:design:read"],
        policies=[brand_policy],
    )

    # 1. Allowed call with approved brand token
    allowed_dec = await engine.evaluate(
        agent_id=agent.id,
        tool_name="generate_wireframe",
        tool_args={"color_palette": {"accent": "#FF3366"}},
        required_permission="figma:design:generate",
    )
    assert allowed_dec.allowed is True

    # 2. Denied call with unapproved rogue color #00FF00
    denied_dec = await engine.evaluate(
        agent_id=agent.id,
        tool_name="generate_wireframe",
        tool_args={"color_palette": {"accent": "#00FF00"}},
        required_permission="figma:design:generate",
    )
    assert denied_dec.allowed is False
    assert "not in approved brand palette" in denied_dec.reason


# ==============================================================================
# 4. Multi-Skill Chaining: Search Solr PRD -> Generate Wireframe in Figma
# ==============================================================================


@pytest.mark.asyncio
async def test_multi_skill_chaining_solr_prd_to_figma_wireframe():
    agent = _make_mock_agent()
    engine = _build_policy_engine(
        agent,
        ["solr:search:knowledge_base", "figma:design:generate", "figma:design:read"],
    )
    audit_service = AsyncMock()
    cost_service = AsyncMock()

    solr_skill = SolrSearchSkill(
        permitted_collections={"knowledge_base"},
        adapter=SolrAdapter(),
    )
    figma_skill = FigmaDesignSkill(adapter=FigmaAdapter())

    tools = solr_skill.get_tools() + figma_skill.get_tools()

    # Step 1: Agent searches Solr for the PRD
    turn_1 = LLMResponse(
        content="",
        model="gpt-4o",
        provider="scripted",
        usage=TokenUsage(prompt_tokens=30, completion_tokens=20, total_tokens=50),
        tool_calls=[
            ToolCall(
                id="call_solr_prd",
                name="search_solr",
                arguments={
                    "collection": "knowledge_base",
                    "query": "mobile checkout flow PRD",
                    "question": "what are the specs for mobile checkout?",
                },
            )
        ],
    )

    # Step 2: Agent reads Solr PRD result and calls generate_wireframe with extracted specs
    turn_2 = LLMResponse(
        content="",
        model="gpt-4o",
        provider="scripted",
        usage=TokenUsage(prompt_tokens=80, completion_tokens=40, total_tokens=120),
        tool_calls=[
            ToolCall(
                id="call_figma_wf",
                name="generate_wireframe",
                arguments={
                    "screen_name": "Mobile Checkout Flow",
                    "layout_type": "mobile",
                    "source_spec_doc": "KB-021",
                    "sections": [
                        {
                            "name": "Order Summary",
                            "layout": "column",
                            "components": [
                                {"name": "Subtotal", "type": "card", "label": "Subtotal: $89.00"}
                            ],
                        },
                        {
                            "name": "Payment",
                            "layout": "row",
                            "components": [
                                {
                                    "name": "Pay Button",
                                    "type": "button",
                                    "variant": "primary",
                                    "label": "Complete Purchase - $96.12",
                                }
                            ],
                        },
                    ],
                    "color_palette": {
                        "canvas": "#FBF7EE",
                        "primary": "#1E1B4B",
                        "accent": "#FF3366",
                    },
                },
            )
        ],
    )

    # Step 3: Agent returns textual breakdown
    final_ux_text = (
        "Generated Figma wireframe for Mobile Checkout Flow with Order Summary "
        "and primary CTA button adhering to GovernAI design tokens."
    )
    turn_3 = LLMResponse(
        content=final_ux_text,
        model="gpt-4o",
        provider="scripted",
        usage=TokenUsage(prompt_tokens=120, completion_tokens=50, total_tokens=170),
        tool_calls=[],
    )

    llm_service = LLMService([_ScriptedLLMProvider([turn_1, turn_2, turn_3])])

    execution_id = uuid.uuid4()
    result = await run_agent(
        llm_service=llm_service,
        tools=tools,
        agent_id=agent.id,
        org_id=agent.org_id,
        execution_id=execution_id,
        policy_engine=engine,
        audit_service=audit_service,
        cost_service=cost_service,
        goal=(
            "Search Solr knowledge base for mobile checkout PRD and "
            "generate the wireframe in Figma."
        ),
    )

    assert result["final_answer"] == final_ux_text
    assert audit_service.log_tool_call.call_count == 2
    # Verify first call was Solr and second was Figma
    logged_tools = [call[0][3] for call in audit_service.log_tool_call.call_args_list]
    assert logged_tools == ["search_solr", "generate_wireframe"]
    assert cost_service.record_llm_cost.call_count == 3


# ==============================================================================
# 5. Live Mode, Error Handling, & Metadata Contract Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_figma_adapter_live_mode_success():
    adapter = FigmaAdapter(access_token="figd_mock_token_123")
    assert adapter.is_live is True

    mock_client = AsyncMock()
    mock_file_resp = MagicMock(status_code=200)
    mock_file_resp.json.return_value = {
        "nodes": {
            "10:20": {
                "document": {
                    "id": "10:20",
                    "name": "Live Cloud Frame",
                    "type": "FRAME",
                    "children": [{"name": "Header", "children": [{"name": "Logo"}]}],
                }
            }
        }
    }

    mock_img_resp = MagicMock(status_code=200)
    mock_img_resp.json.return_value = {
        "images": {"10:20": "https://figma-alpha.s3.amazonaws.com/test.svg"}
    }

    mock_svg_resp = MagicMock(status_code=200, text="<svg>live figma svg content</svg>")

    async def _mock_get(url, *args, **kwargs):
        if "/nodes?" in url:
            return mock_file_resp
        elif "/images/" in url:
            return mock_img_resp
        elif "s3.amazonaws.com" in url:
            return mock_svg_resp
        return MagicMock(status_code=404)

    mock_client.get.side_effect = _mock_get
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        req = FigmaWireframeRequest(
            screen_name="Live Cloud Frame",
            layout_type="desktop",
            file_key="real_file_123",
            node_id="10:20",
            sections=[],
        )
        res = await adapter.generate_wireframe(req)
        assert res.screen_name == "Live Cloud Frame"
        assert res.svg_content == "<svg>live figma svg content</svg>"
        assert "real_file_123" in res.embed_url
        assert "10:20" in res.embed_url
        assert res.sections_count == 1
        assert res.components_count == 1


@pytest.mark.asyncio
async def test_figma_adapter_live_mode_timeout_fallback():
    adapter = FigmaAdapter(access_token="figd_mock_token_123")
    assert adapter.is_live is True

    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.TimeoutException("Figma API timeout")
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        req = FigmaWireframeRequest(
            screen_name="Fallback Screen",
            layout_type="mobile",
            file_key="real_file_123",
            node_id="10:20",
            sections=[],
        )
        # Should gracefully fall back to engine synthesis instead of raising
        res = await adapter.generate_wireframe(req)
        assert res.screen_name == "Fallback Screen"
        assert res.layout_type == "mobile"
        assert "<svg" in res.svg_content


@pytest.mark.asyncio
async def test_figma_adapter_live_components_fetch():
    adapter = FigmaAdapter(access_token="figd_mock_token_123")
    mock_client = AsyncMock()
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "meta": {
            "components": [{"key": "comp_1", "name": "Primary Button", "description": "CTA button"}]
        }
    }
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        comps = await adapter.get_components("remote_file_key")
        assert len(comps) == 1
        assert comps[0]["name"] == "Primary Button"


@pytest.mark.asyncio
async def test_generate_wireframe_tool_invalid_layout_rejection():
    tool = GenerateFigmaWireframeTool(adapter=FigmaAdapter())
    res = await tool.execute(
        screen_name="Bad Screen",
        layout_type="3d_vr_cube",
        sections=[],
    )
    assert res["success"] is False
    assert res["error"] == "validation_failed"
    assert "unsupported" in res["reason"]


def test_enrich_arguments_fills_source_spec_doc_from_prior_solr_search():
    """The model doesn't always pass source_spec_doc even when it just used a
    search_solr result to build the wireframe (that argument is optional and
    LLM-discretionary). enrich_arguments should ground it deterministically to
    whatever document the most recent search_solr call actually found."""
    tool = GenerateFigmaWireframeTool(adapter=FigmaAdapter())
    prior_messages = [
        {"role": "assistant", "content": None, "tool_calls": []},
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": (
                '{"success": true, "documents": '
                '[{"id": "KB-001", "title": "Password Reset Procedure"}], '
                '"total_found": 1}'
            ),
        },
    ]

    enriched = tool.enrich_arguments(
        {"screen_name": "Password Reset", "layout_type": "desktop"}, prior_messages
    )

    assert enriched["source_spec_doc"] == "KB-001"


def test_enrich_arguments_respects_explicit_source_spec_doc():
    tool = GenerateFigmaWireframeTool(adapter=FigmaAdapter())
    prior_messages = [
        {
            "role": "tool",
            "content": '{"success": true, "documents": [{"id": "KB-002"}]}',
        },
    ]

    enriched = tool.enrich_arguments(
        {"screen_name": "VPN Setup", "source_spec_doc": "KB-999"}, prior_messages
    )

    assert enriched["source_spec_doc"] == "KB-999"


def test_enrich_arguments_no_op_without_prior_solr_search():
    tool = GenerateFigmaWireframeTool(adapter=FigmaAdapter())
    prior_messages = [{"role": "assistant", "content": "just thinking out loud"}]

    enriched = tool.enrich_arguments({"screen_name": "Dashboard"}, prior_messages)

    assert "source_spec_doc" not in enriched


def test_figma_skill_metadata_and_permissions():
    skill = FigmaDesignSkill(adapter=FigmaAdapter())
    assert skill.name == "figma_design"
    assert skill.display_name == "Figma Design Studio"
    assert "figma:design:generate" in skill.required_permissions
    assert "figma:design:read" in skill.required_permissions
    tool_names = [t.name for t in skill.get_tools()]
    assert "generate_wireframe" in tool_names
    assert "get_figma_components" in tool_names
