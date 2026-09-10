"""Interactively try the Enterprise Search (Solr) Skill against its seeded demo data.

Run: .venv/Scripts/python.exe scripts/try_solr_skill.py
"""

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.skills.solr_search import SolrSearchSkill

SCHEMA_HINT = """
================================================================================
  GovernAI — Enterprise Search (Apache Solr) Interactive Demo
================================================================================

Seeded collections:
  * knowledge_base  (10 docs: IT, HR, Finance, Security, Engineering, Support)
      -> PERMITTED in agent passport
  * compliance_docs (5 docs: GDPR, SOX, AML, InfoSec, BCP)
      -> PERMITTED in agent passport
  * confidential_hr (2 docs: exec compensation, workplace investigation)
      -> RESTRICTED (not in passport - watch governance firewall deny it)

--------------------------------------------------------------------------------
HOW TO USE:
--------------------------------------------------------------------------------
1. AI AGENT MODE (Human Natural Language -> LLM Tool Call -> Solr -> Answer):
   ask How do I fix VPN timeout issues?
   ask What is the GDPR response timeline for data requests?
   ask What is the CEO's compensation?        (Watch GovernAI block the LLM!)

2. DIRECT TOOL MODE (Inspect Raw Solr Tool Execution):
   search knowledge_base password reset
   search compliance_docs GDPR data subject
   search confidential_hr compensation       (Direct denial check)
   facet compliance_docs *:* department classification

Type 'quit' to exit.
================================================================================
"""


def _simulate_llm_agent_intent(question: str) -> tuple[str, str, str]:
    """Simulate how an LLM evaluates the user prompt and selects collection + query."""
    q_lower = question.lower()
    if any(k in q_lower for k in ["salary", "compensation", "investigation", "ceo", "pay", "bonus"]):
        return "confidential_hr", "compensation salary", "Targeting HR records for compensation data"
    elif any(k in q_lower for k in ["gdpr", "sox", "aml", "compliance", "audit", "security policy", "dsar", "bcp"]):
        return "compliance_docs", question, "Targeting compliance repository for regulatory guidelines"
    else:
        return "knowledge_base", question, "Targeting enterprise knowledge base for operational procedures"


async def handle_agent_mode(question: str, tools: dict) -> None:
    print(f"\n[1. User Natural Language Prompt]")
    print(f"    \"{question}\"\n")

    collection, query, reason = _simulate_llm_agent_intent(question)

    print(f"[2. LLM Reasoning & Function Call]")
    print(f"    Thought : {reason}")
    print(f"    Action  : search_solr(")
    print(f"                collection=\"{collection}\",")
    print(f"                query=\"{query}\"")
    print(f"              )\n")

    print(f"[3. GovernAI Policy & Passport Gate]")
    print(f"    Validating: Agent Passport -> Permissions for '{collection}'...")

    result = await tools["search_solr"].execute(
        question=question, query=query, collection=collection
    )

    if not result.get("success"):
        print(f"    [BLOCKED] Policy Firewall Denied Query!")
        print(f"    Reason   : {result.get('reason')}\n")
        print(f"[4. Audit Trail]")
        print(f"    [SECURITY EVENT] Access denied logged to immutable audit ledger.\n")
        print(f"[5. Agent Final Response to User]")
        print(f"    \"I cannot fulfill this request. My passport does not grant me permission")
        print(f"     to access the '{collection}' collection. Please contact an administrator")
        print(f"     if you require authorized access to this data.\"\n")
        return

    docs = result.get("documents", [])
    print(f"    [ALLOWED] Passport permission confirmed (solr:search:{collection}).\n")
    print(f"[4. Solr Retrieval Engine]")
    print(f"    Retrieved {len(docs)} matching document(s) (Total in index: {result.get('total_found')})")
    if docs:
        top = docs[0]
        print(f"    Top Match: [{top.get('id')}] \"{top.get('title')}\" (Relevance Score: {top.get('_score')})\n")

        print(f"[5. Agent Final Response to User (Synthesized from Solr results)]")
        print(f"    \"According to {top.get('title')} ({top.get('id')}):")
        print(f"     {top.get('content')}\"")
        print(f"     (Source: {top.get('department')} / Classification: {top.get('classification')})\n")
    else:
        print("    No matching documents found.\n")
        print(f"[5. Agent Final Response to User]")
        print(f"    \"I searched the knowledge base, but could not find any relevant documentation on that topic.\"\n")


async def main() -> None:
    skill = SolrSearchSkill(
        permitted_collections={"knowledge_base", "compliance_docs"}
    )
    tools = {t.name: t for t in skill.get_tools()}
    print(SCHEMA_HINT)

    while True:
        try:
            raw = input("Solr> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if raw.lower() in ("quit", "exit"):
            break
        if not raw:
            continue

        # If user accidentally pastes "Solr> search ...", strip the leading prompt text
        cleaned = re.sub(r"^(solr\s*>\s*)+", "", raw, flags=re.IGNORECASE).strip()
        parts = cleaned.split()
        if not parts:
            continue

        cmd = parts[0].lower()

        # Handle 'ask' command (Natural Language Agent Mode)
        if cmd == "ask":
            question = " ".join(parts[1:]).strip()
            if not question:
                print("Usage: ask <natural language question>")
                continue
            await handle_agent_mode(question, tools)
            continue

        # Direct tool commands
        if len(parts) < 3:
            print("Usage:")
            print("  ask <natural language question>")
            print("  search <collection> <query>")
            print("  facet <collection> <query> <field1> [field2 ...]")
            continue

        collection = parts[1]

        if cmd == "search":
            query = " ".join(parts[2:])
            result = await tools["search_solr"].execute(
                question="interactive test", query=query, collection=collection
            )
        elif cmd == "facet":
            query = parts[2]
            facet_fields = parts[3:] if len(parts) > 3 else ["department"]
            result = await tools["facet_solr"].execute(
                collection=collection, query=query, facet_fields=facet_fields
            )
        else:
            print(f"Unknown command: '{cmd}'. Use 'ask', 'search', or 'facet'.")
            continue

        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

