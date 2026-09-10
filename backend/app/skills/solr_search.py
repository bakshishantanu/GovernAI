from __future__ import annotations

from app.runtime.solr.adapter import SolrAdapter, SolrSearchError, SolrSearchTimeoutError
from app.runtime.solr.validator import SolrQueryRequest, validate_solr_query
from app.skills.base import BaseSkill, BaseTool, TrustLevel

_DEFAULT_SEED_DATA: dict[str, list[dict]] = {
    "knowledge_base": [
        {
            "id": "KB-001",
            "title": "Password Reset Procedure",
            "content": "To reset your corporate password, navigate to the IT Self-Service Portal at https://itportal.internal. Click 'Forgot Password', enter your employee ID, and follow the verification steps. If your account is locked after 5 failed attempts, contact the IT Help Desk at ext. 4500.",
            "department": "IT",
            "classification": "public",
            "author": "IT Support Team",
        },
        {
            "id": "KB-002",
            "title": "VPN Setup Guide for Remote Workers",
            "content": "Download the corporate VPN client from the Software Center. Install with default settings. Use your Active Directory credentials to authenticate. Select the nearest gateway: US-East, US-West, or EU-Central. Contact IT if you experience connection timeouts exceeding 30 seconds.",
            "department": "IT",
            "classification": "public",
            "author": "Network Operations",
        },
        {
            "id": "KB-003",
            "title": "Annual Leave Policy 2026",
            "content": "All full-time employees receive 20 days of paid annual leave per calendar year. Leave must be requested through the HR Portal at least 5 business days in advance. Carry-over of unused leave is limited to 5 days into the next calendar year. Managers must approve or deny requests within 48 hours.",
            "department": "HR",
            "classification": "public",
            "author": "HR Policy Team",
        },
        {
            "id": "KB-004",
            "title": "Expense Reimbursement Guidelines",
            "content": "Submit expense claims within 30 days of incurrence via the Finance Portal. Attach original receipts for all claims above $25. Travel expenses require pre-approval from your department head. Reimbursement is processed within 10 business days of approval. Corporate card statements are reconciled monthly.",
            "department": "Finance",
            "classification": "public",
            "author": "Finance Operations",
        },
        {
            "id": "KB-005",
            "title": "Onboarding Checklist for New Hires",
            "content": "Day 1: Collect laptop and badge from IT. Complete mandatory compliance training modules (4 hours). Day 2-3: Department-specific orientation. Week 1: Complete benefits enrollment through the HR Portal. Week 2: Shadow a senior team member. 30-day check-in with manager required.",
            "department": "HR",
            "classification": "public",
            "author": "HR Onboarding",
        },
        {
            "id": "KB-006",
            "title": "Incident Response Procedure",
            "content": "Severity 1 (system down): Page on-call engineer immediately via PagerDuty. Assemble war room within 15 minutes. Status updates every 30 minutes. Severity 2 (degraded service): Create ticket in JIRA with P2 priority. Acknowledge within 1 hour. Severity 3 (minor issue): Standard ticket queue, 4-hour SLA.",
            "department": "IT",
            "classification": "internal",
            "author": "SRE Team",
        },
        {
            "id": "KB-007",
            "title": "Data Classification Policy",
            "content": "All company data must be classified into one of four tiers: Public (no restrictions), Internal (employees only), Confidential (need-to-know basis), and Restricted (regulatory-controlled PII/PHI). Classification must be applied at creation time. Unclassified data defaults to Internal. Quarterly audits verify classification accuracy.",
            "department": "Security",
            "classification": "public",
            "author": "CISO Office",
        },
        {
            "id": "KB-008",
            "title": "Product Roadmap Q3 2026",
            "content": "Q3 priorities: Launch Enterprise Search feature across all tiers. Migrate remaining microservices to Kubernetes. Complete SOC 2 Type II audit. Ship mobile app v2.0 with offline support. Deprecate legacy REST API v1 endpoints by September 30.",
            "department": "Engineering",
            "classification": "internal",
            "author": "VP Engineering",
        },
        {
            "id": "KB-009",
            "title": "Customer Escalation Workflow",
            "content": "When a customer requests escalation: 1) Acknowledge within 15 minutes. 2) Assign a senior support engineer. 3) Create an escalation ticket linked to the original case. 4) Notify the account manager. 5) Provide status updates every 2 hours. 6) Conduct post-mortem within 48 hours of resolution.",
            "department": "Support",
            "classification": "internal",
            "author": "Support Leadership",
        },
        {
            "id": "KB-010",
            "title": "Vendor Security Assessment Checklist",
            "content": "Before onboarding any third-party vendor: Verify SOC 2 Type II certification. Review data processing agreement (DPA). Confirm encryption at rest and in transit. Validate incident notification SLA (must be under 72 hours). Annual reassessment required for all active vendors.",
            "department": "Security",
            "classification": "internal",
            "author": "Vendor Risk Team",
        },
    ],
    "compliance_docs": [
        {
            "id": "COMP-001",
            "title": "GDPR Data Subject Rights Procedure",
            "content": "Upon receiving a data subject access request (DSAR), the privacy team must acknowledge within 72 hours and fulfill within 30 calendar days. Right to erasure requests require verification of identity before processing. Maintain a log of all DSARs in the Privacy Management System.",
            "department": "Legal",
            "classification": "internal",
            "author": "Data Privacy Officer",
        },
        {
            "id": "COMP-002",
            "title": "SOX Compliance Controls for Financial Reporting",
            "content": "All financial transactions above $10,000 require dual authorization. Segregation of duties must be enforced between transaction initiation and approval. Quarterly reconciliation of all general ledger accounts. External audit access must be provisioned within 24 hours of request.",
            "department": "Finance",
            "classification": "confidential",
            "author": "Chief Compliance Officer",
        },
        {
            "id": "COMP-003",
            "title": "Anti-Money Laundering (AML) Monitoring Rules",
            "content": "Transactions flagged by the AML system must be reviewed within 24 hours. Suspicious Activity Reports (SARs) must be filed within 30 days of detection. Customer due diligence (CDD) records must be refreshed every 2 years for standard-risk clients and annually for high-risk clients.",
            "department": "Compliance",
            "classification": "confidential",
            "author": "AML Compliance Team",
        },
        {
            "id": "COMP-004",
            "title": "Information Security Policy - Access Control",
            "content": "All access follows the principle of least privilege. Multi-factor authentication is mandatory for all systems containing PII or financial data. Access reviews conducted quarterly. Terminated employee access must be revoked within 4 hours of HR notification. Privileged access requires manager and CISO approval.",
            "department": "Security",
            "classification": "internal",
            "author": "CISO Office",
        },
        {
            "id": "COMP-005",
            "title": "Business Continuity Plan - IT Systems",
            "content": "Recovery Time Objective (RTO): 4 hours for critical systems, 24 hours for non-critical. Recovery Point Objective (RPO): 1 hour for databases, 24 hours for file shares. Annual DR drill required. Backup verification tests run monthly. Failover to secondary data center initiated automatically when primary health check fails 3 consecutive times.",
            "department": "IT",
            "classification": "internal",
            "author": "Business Continuity Team",
        },
    ],
    "confidential_hr": [
        {
            "id": "HR-CONF-001",
            "title": "Executive Compensation Structure 2026",
            "content": "C-suite base salary ranges: CEO $450K-$600K, CTO $380K-$480K, CFO $350K-$450K. Annual bonus target: 40-60% of base. Long-term incentive plan: RSU grants vesting over 4 years with 1-year cliff. Retention bonuses for key personnel under review.",
            "department": "HR",
            "classification": "restricted",
            "author": "VP Human Resources",
        },
        {
            "id": "HR-CONF-002",
            "title": "Ongoing Workplace Investigation - Case WI-2026-047",
            "content": "Investigation initiated following anonymous ethics hotline report on 2026-07-15. Allegations: misuse of corporate resources and potential conflict of interest. Assigned investigator: External counsel (Morrison & Associates). Status: witness interviews in progress. Target completion: 2026-09-30.",
            "department": "HR",
            "classification": "restricted",
            "author": "General Counsel",
        },
    ],
}


class SearchSolrTool(BaseTool):
    name = "search_solr"
    description = (
        "Search enterprise documents using Apache Solr full-text search, "
        "scoped to the agent's permitted collections."
    )
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The natural-language question to answer from enterprise documents.",
            },
            "query": {
                "type": "string",
                "description": (
                    "A Solr query string to search for relevant documents. "
                    "Use field:value syntax for targeted search, e.g. "
                    "'title:password AND content:reset'. Use '*:*' to match all."
                ),
            },
            "collection": {
                "type": "string",
                "description": "The Solr collection to search within.",
            },
            "filters": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional filter queries in 'field:value' format, "
                    "e.g. ['department:IT', 'classification:public']."
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (1-100, default 10).",
            },
        },
        "required": ["question", "query", "collection"],
    }

    def __init__(
        self, adapter: SolrAdapter, permitted_collections: frozenset[str],
        permitted_fields: frozenset[str] | None = None,
    ) -> None:
        self._adapter = adapter
        self._permitted_collections = permitted_collections
        self._permitted_fields = permitted_fields
        self.required_permission = ",".join(
            f"solr:search:{c}" for c in sorted(permitted_collections)
        )

    async def execute(self, **kwargs) -> dict:
        rows = min(kwargs.get("max_results", 10), 100)
        request = SolrQueryRequest(
            question=kwargs["question"],
            query_string=kwargs["query"],
            collection=kwargs["collection"],
            permitted_collections=self._permitted_collections,
            permitted_fields=self._permitted_fields,
            rows=rows,
        )
        validation = validate_solr_query(request)
        if not validation.allowed:
            return {
                "success": False,
                "error": "denied",
                "reason": validation.reason,
            }

        try:
            result = self._adapter.search(
                collection=request.collection,
                query=request.query_string,
                filters=kwargs.get("filters"),
                rows=rows,
            )
        except SolrSearchTimeoutError as exc:
            return {"success": False, "error": "timeout", "reason": str(exc)}
        except SolrSearchError:
            return {
                "success": False,
                "error": "execution_failed",
                "reason": "search could not be executed against the collection",
            }

        return {
            "success": True,
            "documents": result.documents,
            "total_found": result.total_found,
        }


class FacetSolrTool(BaseTool):
    name = "facet_solr"
    description = (
        "Get facet counts for specified fields across enterprise documents, "
        "useful for exploring data distribution and drilling down into categories."
    )
    parameters = {
        "type": "object",
        "properties": {
            "collection": {
                "type": "string",
                "description": "The Solr collection to facet within.",
            },
            "query": {
                "type": "string",
                "description": "The Solr query to scope the facet counts. Use '*:*' for all documents.",
            },
            "facet_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of field names to compute facet counts for, e.g. ['department', 'classification'].",
            },
        },
        "required": ["collection", "query", "facet_fields"],
    }

    def __init__(
        self, adapter: SolrAdapter, permitted_collections: frozenset[str],
    ) -> None:
        self._adapter = adapter
        self._permitted_collections = permitted_collections
        self.required_permission = ",".join(
            f"solr:search:{c}" for c in sorted(permitted_collections)
        )

    async def execute(self, **kwargs) -> dict:
        collection = kwargs["collection"]
        if collection not in self._permitted_collections:
            return {
                "success": False,
                "error": "denied",
                "reason": f"collection '{collection}' is outside permitted scope",
            }

        try:
            result = self._adapter.facet_search(
                collection=collection,
                query=kwargs["query"],
                facet_fields=kwargs["facet_fields"],
            )
        except SolrSearchTimeoutError as exc:
            return {"success": False, "error": "timeout", "reason": str(exc)}
        except SolrSearchError:
            return {
                "success": False,
                "error": "execution_failed",
                "reason": "facet search could not be executed",
            }

        return {
            "success": True,
            "total_found": result.total_found,
            "facets": result.facets,
        }


class SolrSearchSkill(BaseSkill):
    name = "solr_search"
    display_name = "Enterprise Search"
    description = (
        "Full-text search over enterprise document collections via "
        "Apache Solr, scoped per agent."
    )
    version = "1.0.0"
    trust_level = TrustLevel.VERIFIED

    def __init__(
        self,
        permitted_collections: set[str] | frozenset[str],
        permitted_fields: set[str] | frozenset[str] | None = None,
        adapter: SolrAdapter | None = None,
    ) -> None:
        self._permitted_collections = frozenset(permitted_collections)
        self._permitted_fields = frozenset(permitted_fields) if permitted_fields else None
        self._adapter = adapter or SolrAdapter(seed_data=_DEFAULT_SEED_DATA)
        self.required_permissions = [
            f"solr:search:{c}" for c in sorted(self._permitted_collections)
        ]

    def get_tools(self) -> list[BaseTool]:
        return [
            SearchSolrTool(
                self._adapter, self._permitted_collections, self._permitted_fields
            ),
            FacetSolrTool(self._adapter, self._permitted_collections),
        ]
