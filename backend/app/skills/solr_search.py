from __future__ import annotations

from typing import Any

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
        {
            "id": "KB-011",
            "title": "Incident Post-Mortem and Blameless Review Guide",
            "content": "A blameless post-mortem must be conducted within 48 hours for all Severity 1 and 2 incidents. The incident commander coordinates the retro meeting with on-call engineers, product owners, and SREs. Identify root causes using the 5 Whys framework. Document timeline, impact metrics, action items, and preventative Jira tickets. Post-mortem reports are published to the internal Engineering Wiki.",
            "department": "Engineering",
            "classification": "internal",
            "author": "Site Reliability Engineering",
        },
        {
            "id": "KB-012",
            "title": "Kubernetes Pod CrashLoopBackOff Troubleshooting Runbook",
            "content": "When a pod enters CrashLoopBackOff status: 1) Run 'kubectl describe pod <name>' to inspect exit codes and termination reasons (e.g., OOMKilled code 137). 2) Retrieve container logs via 'kubectl logs <name> --previous'. 3) Check liveness and readiness probe timeouts in the deployment manifest. 4) Verify ConfigMap and Secret volume mounts exist and contain expected keys. 5) For database connection failures, inspect PgBouncer connection pool saturation.",
            "department": "Engineering",
            "classification": "internal",
            "author": "Platform Infrastructure Team",
        },
        {
            "id": "KB-013",
            "title": "PostgreSQL Connection Pooling and Query Optimization",
            "content": "All production services must connect to PostgreSQL through PgBouncer connection pooling. Direct connections to the primary database are strictly prohibited. Configure transaction pooling mode with max client connections set to 500 and default pool size set to 25 per pod replica. Long-running queries exceeding 5000ms are logged to Datadog APM and automatically terminated by statement_timeout.",
            "department": "Engineering",
            "classification": "internal",
            "author": "Database Engineering",
        },
        {
            "id": "KB-014",
            "title": "API Rate Limiting and Gateway Quotas",
            "content": "External REST API endpoints enforce rate limiting via Envoy gateway with Redis token buckets. Tier 1 (Free): 60 requests per minute, 10,000 per day. Tier 2 (Pro): 600 requests per minute, 100,000 per day. Tier 3 (Enterprise): 3,000 requests per minute with burst capability up to 5,000 requests. When rate limit is exceeded, gateway returns HTTP 429 Too Many Requests with Retry-After header.",
            "department": "Engineering",
            "classification": "public",
            "author": "API Platform Team",
        },
        {
            "id": "KB-015",
            "title": "Remote Work Hardware Allowance and Equipment Stipend",
            "content": "Full-time remote employees are eligible for a one-time $1,500 home office setup allowance upon hire and an annual $500 peripheral refresh budget. Reimbursable items include ergonomic chairs, sit-stand desks, 4K monitors, webcams, and noise-canceling headsets. Submit receipts via the Finance Portal under category 'Remote Office Expense'. Approved equipment remains company property for asset tracking.",
            "department": "HR",
            "classification": "public",
            "author": "People Operations",
        },
        {
            "id": "KB-016",
            "title": "Employee Referral Program and Bonus Payouts",
            "content": "Employees who refer a candidate successfully hired into a full-time role receive a referral bonus. Standard roles: $2,500 payout. Senior and Leadership roles: $5,000 payout. Hard-to-fill Engineering and AI Specialist roles: $7,500 payout. 50% of bonus is paid on the candidate's 30th day of employment, and the remaining 50% is paid upon completing 90 days. Referrals must be submitted through Workday before candidate first contact.",
            "department": "HR",
            "classification": "public",
            "author": "Talent Acquisition",
        },
        {
            "id": "KB-017",
            "title": "Secure Coding Standard and OWASP Top 10 Mitigations",
            "content": "All production code must comply with the GovernAI Secure Coding Standard. Mitigate SQL injection by exclusively using parameterized queries and ORM abstractions. Prevent Cross-Site Scripting (XSS) with contextual HTML escaping and strict Content Security Policy (CSP) headers. Never log credentials, API tokens, or PII. Static Application Security Testing (SAST) runs automatically on every pull request via GitHub Actions.",
            "department": "Security",
            "classification": "internal",
            "author": "Application Security Team",
        },
        {
            "id": "KB-018",
            "title": "Single Sign-On (SSO) and Okta Provisioning Guide",
            "content": "Enterprise single sign-on is managed through Okta SAML 2.0 and OIDC federation. All internal applications must authenticate via the central identity provider with FIDO2/WebAuthn hardware keys or Okta Verify with Push challenge. Just-In-Time (JIT) provisioning automatically maps SCIM groups to application roles upon initial login. Role changes in Workday propagate within 15 minutes.",
            "department": "IT",
            "classification": "public",
            "author": "Identity & Access Management",
        },
        {
            "id": "KB-019",
            "title": "Disaster Recovery Runbook: Multi-Region Database Failover",
            "content": "In the event of a total AWS us-east-1 region failure: 1) Executive Incident Commander declares regional failover. 2) Update Route53 DNS latency records to steer traffic to us-west-2. 3) Promote the PostgreSQL read replica in us-west-2 to standalone primary using 'pg_ctl promote'. 4) Verify Kafka cluster replication stream synchronization. 5) Run automated smoke tests against frontend web endpoints. Target RTO is under 15 minutes.",
            "department": "IT",
            "classification": "internal",
            "author": "Infrastructure Core Team",
        },
        {
            "id": "KB-020",
            "title": "Tier 3 VIP Customer Escalation Matrix",
            "content": "Enterprise Tier 3 accounts (contract value > $100K ARR) have access to 24/7 dedicated support escalation with 15-minute response SLA. Severity 1 tickets immediately notify the VP of Customer Success and on-call Solutions Architect. If an outage is unresolved after 60 minutes, the Chief Technology Officer is briefed and an executive conference bridge is opened for customer stakeholders.",
            "department": "Support",
            "classification": "internal",
            "author": "Customer Success Leadership",
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
        {
            "id": "COMP-006",
            "title": "ISO/IEC 27001:2022 Information Security Management Controls",
            "content": "GovernAI maintains compliance with ISO/IEC 27001:2022 standards across all cloud infrastructure and application tiers. Security controls encompass Annex A controls for organizational, people, physical, and technological safeguards. Internal ISMS audits are conducted semi-annually. Non-conformities must be remediated within 30 days for major findings and 90 days for minor findings.",
            "department": "Compliance",
            "classification": "internal",
            "author": "InfoSec Compliance Director",
        },
        {
            "id": "COMP-007",
            "title": "SOC 2 Type II Trust Services Criteria & Evidence Collection",
            "content": "Continuous SOC 2 Type II compliance monitors five Trust Services Categories: Security, Availability, Processing Integrity, Confidentiality, and Privacy. Automated evidence collectors run weekly checks across AWS CloudTrail, GitHub branch protection, and Okta MFA configurations. External auditor observation period runs continuously from October 1 to September 30 annually.",
            "department": "Security",
            "classification": "internal",
            "author": "Governance, Risk & Compliance (GRC)",
        },
        {
            "id": "COMP-008",
            "title": "PCI-DSS 4.0 Cardholder Data Environment Isolation",
            "content": "GovernAI delegates payment processing to PCI-DSS Level 1 certified processors via tokenized client-side iframes. No Primary Account Numbers (PAN), CVVs, or cardholder magnetic stripe data may ever enter, process through, or be stored on GovernAI application servers or databases. Quarterly vulnerability scans are executed by an Approved Scanning Vendor (ASV).",
            "department": "Security",
            "classification": "confidential",
            "author": "Payment Security Officer",
        },
        {
            "id": "COMP-009",
            "title": "HIPAA Security Rule Safeguards for Protected Health Information",
            "content": "When enterprise tenants process Protected Health Information (PHI), Business Associate Agreements (BAAs) must be executed prior to ingestion. Administrative safeguards require role-based access audits every 30 days. Technical safeguards mandate AES-256 encryption at rest and TLS 1.3 in transit. Any suspected PHI breach requires notification to affected tenants within 24 hours.",
            "department": "Legal",
            "classification": "confidential",
            "author": "Health Privacy Compliance Counsel",
        },
        {
            "id": "COMP-010",
            "title": "Global Data Retention and Destruction Schedule",
            "content": "Customer logs and audit event histories are retained for 365 days before automated archiving to immutable cold storage. Financial transaction ledgers are retained for 7 years in accordance with IRS and statutory regulations. Upon enterprise tenant contract termination, tenant data is purged within 30 days and a cryptographic certificate of destruction is issued.",
            "department": "Legal",
            "classification": "internal",
            "author": "Corporate Records Office",
        },
        {
            "id": "COMP-011",
            "title": "Whistleblower Protection and Ethics Hotline Policy",
            "content": "Employees, contractors, and third parties may report suspected accounting fraud, code-of-conduct violations, or regulatory non-compliance through the third-party anonymous ethics hotline (available 24/7 online and via phone). Retaliation against any individual reporting in good faith is strictly prohibited and subject to immediate termination. All reports are independently evaluated by the Audit Committee.",
            "department": "Legal",
            "classification": "internal",
            "author": "Office of the Ombudsman",
        },
        {
            "id": "COMP-012",
            "title": "AI Model Governance and Algorithmic Bias Assessment Framework",
            "content": "All generative AI agent pipelines and LLM prompts deployed to production must complete an Algorithmic Impact Assessment (AIA). Evaluations include automated testing for toxic outputs, protected class disparate impact, prompt injection resilience, and hallucinations. Models exceeding defined error thresholds or exhibiting safety degradation are blocked by the Governance Firewall.",
            "department": "Compliance",
            "classification": "internal",
            "author": "AI Safety & Ethics Committee",
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
        {
            "id": "HR-CONF-003",
            "title": "Executive Performance Ratings and Equity Grant Allocations",
            "content": "Annual Board Compensation Committee review results: Executive tier performance multipliers determined at 125% for engineering leadership and 110% for commercial leadership. Supplemental equity grants totaling 250,000 RSUs approved for retention purposes, with staggered cliff vesting scheduled across Q4 2026 and Q2 2027.",
            "department": "HR",
            "classification": "restricted",
            "author": "Compensation Committee",
        },
        {
            "id": "HR-CONF-004",
            "title": "Severance and Change-in-Control Agreements for Officers",
            "content": "Double-trigger change-in-control provisions apply to all Vice President and C-level executive officers. In the event of an acquisition resulting in involuntary termination without cause, executive is entitled to 18 months base salary continuation, 100% target bonus payout, 18 months COBRA coverage reimbursement, and full accelerated vesting of unvested equity options.",
            "department": "HR",
            "classification": "restricted",
            "author": "Board of Directors",
        },
        {
            "id": "HR-CONF-005",
            "title": "Internal Whistleblower Complaint - Financial Misstatement Allegations Case #8821",
            "content": "Confidential investigation into whistleblower disclosure regarding premature revenue recognition on Q2 enterprise multi-year contracts. Audit Committee forensic accountants engaged to review sales agreements and invoice timing. Access to this file is restricted strictly to General Counsel, Audit Committee Chair, and lead forensic investigator.",
            "department": "HR",
            "classification": "restricted",
            "author": "Audit Committee",
        },
        {
            "id": "HR-CONF-006",
            "title": "Key Personnel Retention Bonus Matrix - M&A Transition Period",
            "content": "Strategic retention packages structured for core platform engineers, security architects, and principal machine learning researchers during pending corporate acquisition discussions. Total retention pool capped at $4.2M, distributed as quarterly cash bonuses conditional upon active service through transaction closing plus 12 months.",
            "department": "HR",
            "classification": "restricted",
            "author": "People Executive Team",
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
        collection = kwargs.get("collection", "")
        question = kwargs.get("question") or kwargs.get("query", "")
        query_string = kwargs.get("query") or kwargs.get("question", "")
        request = SolrQueryRequest(
            question=question,
            query_string=query_string,
            collection=collection,
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

    def audit_metadata(self, arguments: dict, result: Any) -> dict | None:
        """Structured preview of search queries and matched documents for
        the audit record and timeline UI."""
        if not isinstance(result, dict):
            return None
        if not result.get("success"):
            return {
                "collection": arguments.get("collection"),
                "query": arguments.get("query") or arguments.get("question"),
                "error": result.get("error"),
                "reason": result.get("reason"),
            }

        docs = result.get("documents") or []
        doc_previews = []
        for doc in docs[:10]:
            content = str(doc.get("content", ""))
            doc_previews.append({
                "id": doc.get("id"),
                "title": doc.get("title"),
                "department": doc.get("department"),
                "classification": doc.get("classification"),
                "score": doc.get("_score"),
                "preview": content[:300],
            })
        return {
            "collection": arguments.get("collection"),
            "query": arguments.get("query") or arguments.get("question"),
            "total_found": result.get("total_found", len(docs)),
            "documents": doc_previews,
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
        collection = kwargs.get("collection", "")
        if collection not in self._permitted_collections:
            return {
                "success": False,
                "error": "denied",
                "reason": f"collection '{collection}' is outside permitted scope",
            }

        try:
            result = self._adapter.facet_search(
                collection=collection,
                query=kwargs.get("query", "*:*"),
                facet_fields=kwargs.get("facet_fields", []),
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

    def audit_metadata(self, arguments: dict, result: Any) -> dict | None:
        """Structured preview of facet queries and counts for the audit
        record and timeline UI."""
        if not isinstance(result, dict):
            return None
        return {
            "collection": arguments.get("collection"),
            "query": arguments.get("query"),
            "facet_fields": arguments.get("facet_fields"),
            "total_found": result.get("total_found", 0),
            "facets": result.get("facets", {}),
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
