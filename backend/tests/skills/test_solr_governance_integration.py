from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.governance.middleware import govern_tool
from app.domain.policies.engine import PolicyEngine
from app.domain.policies.models import Policy, PolicyRule
from app.runtime.agent_graph import run_agent
from app.runtime.llm.base import LLMProvider, LLMResponse, TokenUsage, ToolCall
from app.runtime.llm.service import LLMService
from app.runtime.solr.adapter import SolrAdapter
from app.skills.solr_search import SearchSolrTool, SolrSearchSkill

_SEED = {
    "knowledge_base": [
        {
            "id": "KB-001",
            "title": "Password Reset Procedure",
            "content": "Reset your corporate password via IT Self-Service Portal.",
            "department": "IT",
            "classification": "public",
        },
        {
            "id": "KB-002",
            "title": "VPN Setup Guide",
            "content": "Install the corporate VPN client from the Software Center.",
            "department": "IT",
            "classification": "public",
        },
    ],
    "compliance_docs": [
        {
            "id": "COMP-001",
            "title": "GDPR Subject Access Requests",
            "content": "Acknowledge DSARs within 72 hours and fulfill within 30 days.",
            "department": "Legal",
            "classification": "internal",
        },
    ],
    "confidential_hr": [
        {
            "id": "HR-001",
            "title": "Executive Compensation 2026",
            "content": "CEO base salary 500K with performance bonus.",
            "department": "HR",
            "classification": "restricted",
        },
    ],
}


def _make_agent(passport_lifecycle: str = "ACTIVE"):
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.org_id = uuid.uuid4()
    agent.passport = MagicMock()
    agent.passport.id = uuid.uuid4()
    agent.passport.lifecycle_state = passport_lifecycle
    return agent


def _build_policy_engine(agent, permissions: list[str], rules: list[PolicyRule] | None = None):
    agent_repo = AsyncMock()
    agent_repo.get_agent.return_value = agent

    perm_repo = AsyncMock()
    perm_objs = []
    for p in permissions:
        m = MagicMock()
        m.permission = p
        perm_objs.append(m)
    perm_repo.get_permissions_for_passport.return_value = perm_objs

    policy_repo = AsyncMock()
    if rules:
        policy = Policy(
            id=uuid.uuid4(),
            org_id=agent.org_id,
            name="Test Policy",
            enabled=True,
            rules=rules,
        )
        policy_repo.get_active_policies_for_org.return_value = [policy]
    else:
        policy_repo.get_active_policies_for_org.return_value = []

    return PolicyEngine(agent_repo, perm_repo, policy_repo)


# ==============================================================================
# 1. PolicyEngine evaluating search_solr and facet_solr
# ==============================================================================


@pytest.mark.asyncio
async def test_policy_engine_allows_search_for_permitted_collection():
    agent = _make_agent()
    engine = _build_policy_engine(agent, ["solr:search:knowledge_base"])

    decision = await engine.evaluate(
        agent_id=agent.id,
        tool_name="search_solr",
        tool_args={"collection": "knowledge_base", "query": "password reset"},
        required_permission="solr:search:compliance_docs,solr:search:knowledge_base",
    )

    assert decision.allowed is True


@pytest.mark.asyncio
async def test_policy_engine_denies_search_for_unpermitted_collection():
    agent = _make_agent()
    # Agent only has access to knowledge_base, NOT confidential_hr
    engine = _build_policy_engine(agent, ["solr:search:knowledge_base"])

    decision = await engine.evaluate(
        agent_id=agent.id,
        tool_name="search_solr",
        tool_args={"collection": "confidential_hr", "query": "executive salary"},
        required_permission="solr:search:compliance_docs,solr:search:knowledge_base",
    )

    assert decision.allowed is False
    assert "solr:search:confidential_hr" in decision.reason


@pytest.mark.asyncio
async def test_policy_engine_denies_when_agent_has_no_solr_permissions():
    agent = _make_agent()
    # Agent only has ticketing permissions, no solr search permissions
    engine = _build_policy_engine(agent, ["ticket:read"])

    decision = await engine.evaluate(
        agent_id=agent.id,
        tool_name="search_solr",
        tool_args={"collection": "knowledge_base", "query": "password reset"},
        required_permission="solr:search:compliance_docs,solr:search:knowledge_base",
    )

    assert decision.allowed is False
    assert "Missing required permission" in decision.reason


@pytest.mark.asyncio
async def test_policy_engine_blocks_keywords_via_solr_query_blocklist():
    agent = _make_agent()
    rule = PolicyRule(
        rule_type="solr_query_blocklist",
        enabled=True,
        config={"keywords": ["DROP", "DELETE", "TRUNCATE"]},
    )
    engine = _build_policy_engine(agent, ["solr:search:knowledge_base"], rules=[rule])

    decision = await engine.evaluate(
        agent_id=agent.id,
        tool_name="search_solr",
        tool_args={"collection": "knowledge_base", "query": "DROP TABLE knowledge"},
        required_permission="solr:search:compliance_docs,solr:search:knowledge_base",
    )

    assert decision.allowed is False
    assert "Disallowed keyword 'DROP' detected" in decision.reason


# ==============================================================================
# 2. govern_tool execution and audit logging
# ==============================================================================


@pytest.mark.asyncio
async def test_govern_tool_executes_search_solr_and_records_audit_metadata():
    agent = _make_agent()
    engine = _build_policy_engine(agent, ["solr:search:knowledge_base"])
    audit_service = AsyncMock()

    adapter = SolrAdapter(seed_data=_SEED)
    tool = SearchSolrTool(adapter=adapter, permitted_collections=frozenset({"knowledge_base"}))

    result = await govern_tool(
        policy_engine=engine,
        audit_service=audit_service,
        org_id=agent.org_id,
        agent_id=agent.id,
        execution_id=uuid.uuid4(),
        tool=tool,
        arguments={"collection": "knowledge_base", "query": "password reset"},
    )

    assert result["success"] is True
    assert result["total_found"] >= 1
    assert any("KB-001" in doc["id"] for doc in result["documents"])

    # Verify audit metadata was generated and passed to audit_service
    audit_service.log_tool_call.assert_awaited_once()
    call_args = audit_service.log_tool_call.await_args.args
    assert call_args[3] == "search_solr"
    assert call_args[4] is True  # allowed
    metadata = call_args[6]
    assert metadata is not None
    assert metadata["collection"] == "knowledge_base"
    assert metadata["total_found"] >= 1
    assert any(d["id"] == "KB-001" for d in metadata["documents"])


@pytest.mark.asyncio
async def test_search_solr_handles_missing_question_gracefully():
    adapter = SolrAdapter(seed_data=_SEED)
    tool = SearchSolrTool(adapter=adapter, permitted_collections=frozenset({"knowledge_base"}))

    # Calling with only query and collection (omitting question) should succeed without KeyError
    result = await tool.execute(collection="knowledge_base", query="vpn setup")
    assert result["success"] is True
    assert result["total_found"] >= 1


# ==============================================================================
# 3. LangGraph run_agent end-to-end loop with Solr tool
# ==============================================================================


class _ScriptedLLMProvider(LLMProvider):
    name = "scripted_solr_test"

    def __init__(self, responses: list[LLMResponse]):
        self._responses = list(responses)
        self.call_count = 0

    async def chat(self, messages, *, tools=None, temperature=0.7, max_tokens=None) -> LLMResponse:
        response = self._responses[self.call_count]
        self.call_count += 1
        return response


@pytest.mark.asyncio
async def test_run_agent_calls_search_solr_and_synthesizes_answer():
    agent = _make_agent()
    engine = _build_policy_engine(
        agent, ["solr:search:knowledge_base", "solr:search:compliance_docs"]
    )
    audit_service = AsyncMock()
    cost_service = AsyncMock()

    skill = SolrSearchSkill(
        permitted_collections={"knowledge_base", "compliance_docs"},
        adapter=SolrAdapter(seed_data=_SEED),
    )
    tools = skill.get_tools()

    # Step 1: LLM decides to call search_solr
    turn_1 = LLMResponse(
        content="",
        model="mock-gpt",
        provider="scripted",
        usage=TokenUsage(prompt_tokens=20, completion_tokens=15, total_tokens=35),
        tool_calls=[
            ToolCall(
                id="call_solr_1",
                name="search_solr",
                arguments={
                    "collection": "knowledge_base",
                    "query": "password reset",
                    "question": "how to reset password",
                },
            )
        ],
    )
    # Step 2: LLM answers based on retrieved documents
    expected_answer = (
        "According to the Password Reset Procedure (KB-001), use the IT Self-Service Portal."
    )
    turn_2 = LLMResponse(
        content=expected_answer,
        model="mock-gpt",
        provider="scripted",
        usage=TokenUsage(prompt_tokens=45, completion_tokens=20, total_tokens=65),
        tool_calls=[],
    )

    llm_service = LLMService([_ScriptedLLMProvider([turn_1, turn_2])])

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
        goal="How do I reset my password?",
    )

    assert result["final_answer"] == expected_answer
    assert audit_service.log_tool_call.awaited
    assert cost_service.record_llm_cost.awaited
