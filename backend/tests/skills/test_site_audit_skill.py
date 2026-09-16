from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.governance.middleware import govern_tool
from app.domain.policies.engine import PolicyEngine
from app.domain.policies.models import Policy
from app.runtime.agent_graph import run_agent
from app.runtime.llm.base import LLMProvider, LLMResponse, TokenUsage, ToolCall
from app.runtime.llm.service import LLMService
from app.runtime.site_audit.adapter import (
    SiteAuditAdapter,
    _AuditHTMLParser,
    _rate_vital,
)
from app.runtime.site_audit.models import AuditRequest, CrawlRequest
from app.runtime.site_audit.validator import (
    is_ssrf_safe_url,
    validate_audit_request,
    validate_crawl_request,
)
from app.skills.site_audit import (
    AuditWebsiteTool,
    CrawlWebsiteTool,
    SiteAuditSkill,
)


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
    name = "scripted_audit_test"

    def __init__(self, responses: list[LLMResponse]):
        self._responses = list(responses)
        self.call_count = 0

    async def chat(self, messages, *, tools=None, temperature=0.7, max_tokens=None) -> LLMResponse:
        response = self._responses[self.call_count]
        self.call_count += 1
        return response


# ==============================================================================
# 1. Validator & SSRF Prevention Unit Tests
# ==============================================================================


def test_validator_accepts_valid_public_urls():
    req = AuditRequest(url="https://example.com/blog", strategy="desktop")
    val = validate_audit_request(req, allow_mock_hosts=False)
    assert val.allowed is True
    assert val.reason is None
    assert val.request is not None
    assert val.request.strategy == "desktop"


def test_validator_rejects_disallowed_schemes():
    req = AuditRequest(url="ftp://example.com")
    val = validate_audit_request(req)
    assert val.allowed is False
    assert "scheme" in val.reason.lower()


def test_validator_blocks_ssrf_loopback():
    for blocked_url in ["http://127.0.0.1:8000", "http://localhost:3000", "http://app.localhost"]:
        safe, reason = is_ssrf_safe_url(blocked_url, allow_mock_hosts=False)
        assert safe is False
        assert "ssrf" in reason.lower() or "loopback" in reason.lower()


def test_validator_blocks_ssrf_private_networks():
    private_ips = [
        "http://10.0.0.5/admin",
        "http://192.168.1.100/router",
        "http://172.16.0.1/",
    ]
    for url in private_ips:
        safe, reason = is_ssrf_safe_url(url, allow_mock_hosts=False)
        assert safe is False
        assert "private" in reason.lower()


def test_validator_blocks_cloud_metadata():
    metadata_urls = [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
    ]
    for url in metadata_urls:
        safe, reason = is_ssrf_safe_url(url, allow_mock_hosts=False)
        assert safe is False
        assert "link-local" in reason.lower() or "ssrf" in reason.lower()


def test_validator_rejects_unsupported_strategy():
    req = AuditRequest(url="https://example.com", strategy="smartwatch")
    val = validate_audit_request(req)
    assert val.allowed is False
    assert "strategy" in val.reason.lower()


def test_site_audit_skill_metadata_and_tools():
    skill = SiteAuditSkill()
    assert skill.name == "site_audit"
    assert skill.display_name == "Site Audit & Performance"
    assert len(skill.get_tools()) == 2
    assert skill.required_permissions == ["site:audit:run", "site:crawl:run"]


def test_crawl_validator_bounds_checking():
    # Valid
    val1 = validate_crawl_request(
        CrawlRequest(start_url="https://example.com", max_pages=5, max_depth=2)
    )
    assert val1.allowed is True

    # Exceeds max pages
    val2 = validate_crawl_request(CrawlRequest(start_url="https://example.com", max_pages=50))
    assert val2.allowed is False
    assert "max_pages" in val2.reason.lower() or "pages" in val2.reason.lower()

    # Exceeds max depth
    val3 = validate_crawl_request(CrawlRequest(start_url="https://example.com", max_depth=5))
    assert val3.allowed is False
    assert "depth" in val3.reason.lower()


# ==============================================================================
# 2. HTML Parser & Vitals Rating Unit Tests
# ==============================================================================


def test_html_parser_extracts_dom_elements():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Sample Enterprise Portal</title>
        <meta name="description" content="A comprehensive security compliance tool.">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="canonical" href="https://example.com/portal">
        <meta property="og:title" content="Enterprise Portal">
    </head>
    <body>
        <h1>Main Heading</h1>
        <h2>Subheading 1</h2>
        <h2>Subheading 2</h2>
        <img src="/img/logo.png" alt="Company Logo">
        <img src="/img/icon.png"> <!-- Missing alt -->
        <a href="/about">About Us</a>
        <a href="https://twitter.com/governai">Twitter</a>
    </body>
    </html>
    """
    parser = _AuditHTMLParser(base_url="https://example.com")
    parser.feed(html)

    assert parser.title == "Sample Enterprise Portal"
    assert parser.meta_description == "A comprehensive security compliance tool."
    assert parser.viewport_configured is True
    assert parser.canonical_url == "https://example.com/portal"
    assert parser.h1_tags == ["Main Heading"]
    assert parser.h2_count == 2
    assert parser.images_count == 2
    assert parser.images_missing_alt == 1
    assert "https://example.com/about" in parser.internal_links
    assert "https://twitter.com/governai" in parser.external_links


def test_rate_vital_classifications():
    assert _rate_vital("lcp", 1200) == "GOOD"
    assert _rate_vital("lcp", 3000) == "NEEDS_IMPROVEMENT"
    assert _rate_vital("lcp", 4500) == "POOR"

    assert _rate_vital("cls", 0.05) == "GOOD"
    assert _rate_vital("cls", 0.15) == "NEEDS_IMPROVEMENT"
    assert _rate_vital("cls", 0.3) == "POOR"

    assert _rate_vital("ttfb", 400) == "GOOD"
    assert _rate_vital("ttfb", 1200) == "NEEDS_IMPROVEMENT"
    assert _rate_vital("ttfb", 2500) == "POOR"


# ==============================================================================
# 3. Adapter & Tools Execution Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_site_audit_adapter_mock_mode():
    adapter = SiteAuditAdapter(mock_mode=True)
    req = AuditRequest(url="https://test-audit.local", strategy="mobile")
    res = await adapter.audit(req)

    assert res.url == "https://test-audit.local"
    assert res.scores.performance >= 90
    assert res.scores.seo >= 90
    assert res.vitals.lcp_ms is not None
    assert res.vitals.cls is not None
    assert res.security.is_https is True
    assert res.source == "mock"


@pytest.mark.asyncio
async def test_audit_website_tool_execution_and_metadata():
    adapter = SiteAuditAdapter(mock_mode=True)
    tool = AuditWebsiteTool(adapter=adapter)

    res = await tool.execute(url="https://test-audit.local", strategy="desktop")
    assert res["success"] is True
    assert res["url"] == "https://test-audit.local"
    assert "scores" in res
    assert "vitals" in res
    assert "opportunities" in res

    meta = tool.audit_metadata({"url": "https://test-audit.local"}, res)
    assert meta is not None
    assert meta["url"] == "https://test-audit.local"
    assert "performance_score" in meta
    assert "lcp_ms" in meta
    assert "seo_score" in meta


@pytest.mark.asyncio
async def test_crawl_website_tool_execution_and_metadata():
    adapter = SiteAuditAdapter(mock_mode=True)
    tool = CrawlWebsiteTool(adapter=adapter)

    res = await tool.execute(start_url="https://test-audit.local", max_pages=3)
    assert res["success"] is True
    assert res["start_url"] == "https://test-audit.local"
    assert len(res["pages"]) == 3
    assert "average_load_time_ms" in res

    meta = tool.audit_metadata({"start_url": "https://test-audit.local"}, res)
    assert meta is not None
    assert meta["total_pages_crawled"] == 3


@pytest.mark.asyncio
async def test_audit_website_tool_validation_failure():
    adapter = SiteAuditAdapter(mock_mode=True)
    tool = AuditWebsiteTool(adapter=adapter)

    # Invalid URL scheme
    res = await tool.execute(url="javascript:alert(1)")
    assert res["success"] is False
    assert res["error"] == "validation_failed"


# ==============================================================================
# 4. Governance & Policy Middleware Integration
# ==============================================================================


@pytest.mark.asyncio
async def test_governance_allows_site_audit_with_permission():
    agent = _make_mock_agent(passport_lifecycle="ACTIVE")
    engine = _build_policy_engine(agent=agent, granted_permissions=["site:audit:run"])

    audit_service = MagicMock()
    audit_service.log_tool_call = AsyncMock()

    adapter = SiteAuditAdapter(mock_mode=True)
    tool = AuditWebsiteTool(adapter=adapter)

    result = await govern_tool(
        policy_engine=engine,
        audit_service=audit_service,
        org_id=agent.org_id,
        agent_id=agent.id,
        execution_id=uuid.uuid4(),
        tool=tool,
        arguments={"url": "https://test-audit.local"},
    )

    assert result["success"] is True
    assert result["url"] == "https://test-audit.local"
    audit_service.log_tool_call.assert_awaited_once()
    call_args = audit_service.log_tool_call.call_args[0]
    assert call_args[3] == "audit_website"
    assert call_args[4] is True  # allowed


@pytest.mark.asyncio
async def test_governance_denies_site_audit_without_permission():
    agent = _make_mock_agent(passport_lifecycle="ACTIVE")
    # Missing site:audit:run
    engine = _build_policy_engine(agent=agent, granted_permissions=["document_search:read"])

    audit_service = MagicMock()
    audit_service.log_tool_call = AsyncMock()

    adapter = SiteAuditAdapter(mock_mode=True)
    tool = AuditWebsiteTool(adapter=adapter)

    result = await govern_tool(
        policy_engine=engine,
        audit_service=audit_service,
        org_id=agent.org_id,
        agent_id=agent.id,
        execution_id=uuid.uuid4(),
        tool=tool,
        arguments={"url": "https://test-audit.local"},
    )

    assert "error" in result
    assert result["error"] == "denied"
    audit_service.log_tool_call.assert_awaited_once()
    call_args = audit_service.log_tool_call.call_args[0]
    assert call_args[3] == "audit_website"
    assert call_args[4] is False  # denied


# ==============================================================================
# 5. LangGraph Agent Loop Execution with LLM Tool Calling
# ==============================================================================


@pytest.mark.asyncio
async def test_run_agent_calls_site_audit_tool():
    agent = _make_mock_agent(passport_lifecycle="ACTIVE")
    engine = _build_policy_engine(agent=agent, granted_permissions=["site:audit:run"])

    audit_service = MagicMock()
    audit_service.log_tool_call = AsyncMock()

    cost_service = MagicMock()
    cost_service.record_llm_cost = AsyncMock()

    scripted_provider = _ScriptedLLMProvider(
        [
            # Step 1: LLM decides to call audit_website
            LLMResponse(
                content="I will audit the website performance.",
                model="test-model",
                provider="test-provider",
                usage=TokenUsage(prompt_tokens=40, completion_tokens=25, total_tokens=65),
                tool_calls=[
                    ToolCall(
                        id="call_audit_123",
                        name="audit_website",
                        arguments={"url": "https://test-audit.local", "strategy": "mobile"},
                    )
                ],
            ),
            # Step 2: LLM receives tool output and summarizes final results
            LLMResponse(
                content="Audit complete: Performance score is 94/100 with LCP at 1.6s.",
                model="test-model",
                provider="test-provider",
                usage=TokenUsage(prompt_tokens=80, completion_tokens=30, total_tokens=110),
                tool_calls=[],
            ),
        ]
    )
    llm_service = LLMService([scripted_provider])

    adapter = SiteAuditAdapter(mock_mode=True)
    tools = [AuditWebsiteTool(adapter=adapter)]

    final_state = await run_agent(
        llm_service=llm_service,
        tools=tools,
        agent_id=agent.id,
        org_id=agent.org_id,
        execution_id=uuid.uuid4(),
        policy_engine=engine,
        audit_service=audit_service,
        cost_service=cost_service,
        goal="Audit https://test-audit.local for Lighthouse vitals and performance.",
        max_steps=5,
    )

    last_message = final_state["messages"][-1]
    assert "Audit complete" in last_message["content"]
    assert "Performance score is 94/100" in last_message["content"]
    assert audit_service.log_tool_call.await_count == 1
