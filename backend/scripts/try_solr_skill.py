"""Interactively try the Enterprise Search (Solr) Skill against its seeded demo data.

Run: .venv/Scripts/python.exe scripts/try_solr_skill.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.skills.solr_search import SolrSearchSkill

SCHEMA_HINT = """
Seeded collections in this demo index:

  knowledge_base  (10 docs: IT, HR, Finance, Security, Engineering, Support)
      <- permitted, you can search this
  compliance_docs (5 docs: GDPR, SOX, AML, InfoSec, BCP)
      <- permitted, you can search this
  confidential_hr (2 docs: exec compensation, workplace investigation)
      <- NOT permitted, watch it get denied

Try things like:
  search knowledge_base password reset
  search compliance_docs GDPR data subject
  search confidential_hr compensation          (will be denied - out of scope)
  facet knowledge_base *:* department
  facet compliance_docs *:* department classification

Type 'quit' to exit.
"""


async def main() -> None:
    skill = SolrSearchSkill(
        permitted_collections={"knowledge_base", "compliance_docs"}
    )
    tools = {t.name: t for t in skill.get_tools()}
    print(SCHEMA_HINT)

    while True:
        raw = input("\nSolr> ").strip()
        if raw.lower() in ("quit", "exit"):
            break
        if not raw:
            continue

        parts = raw.split()
        if len(parts) < 3:
            print("Usage: search <collection> <query> | facet <collection> <query> <field1> [field2 ...]")
            continue

        cmd = parts[0].lower()
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
            print(f"Unknown command: {cmd}. Use 'search' or 'facet'.")
            continue

        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
