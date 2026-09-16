from __future__ import annotations

from typing import Any

from app.runtime.site_audit.adapter import (
    SiteAuditAdapter,
    SiteAuditConnectionError,
    SiteAuditError,
    SiteAuditTimeoutError,
)
from app.runtime.site_audit.models import AuditRequest, CrawlRequest
from app.runtime.site_audit.validator import (
    validate_audit_request,
    validate_crawl_request,
)
from app.skills.base import BaseSkill, BaseTool, TrustLevel


class AuditWebsiteTool(BaseTool):
    name = "audit_website"
    description = (
        "Audit a website URL to generate Core Web Vitals (LCP, FCP, CLS, TBT, TTFB), "
        "Lighthouse performance scores (0-100), SEO diagnostics, security header audits, "
        "and actionable performance optimization opportunities."
    )
    required_permission = "site:audit:run"
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Target web page URL to audit (e.g. 'https://example.com').",
            },
            "strategy": {
                "type": "string",
                "enum": ["mobile", "desktop"],
                "description": "Emulated device strategy. Defaults to 'mobile'.",
            },
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Audit categories to inspect (defaults to "
                    "['performance', 'accessibility', 'best-practices', 'seo'])."
                ),
            },
            "include_page_speed": {
                "type": "boolean",
                "description": (
                    "Whether to query Google PageSpeed Insights for real Lighthouse metrics "
                    "(defaults to true)."
                ),
            },
        },
        "required": ["url"],
    }

    def __init__(self, adapter: SiteAuditAdapter) -> None:
        self._adapter = adapter

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        url = kwargs.get("url", "").strip()
        strategy = kwargs.get("strategy", "mobile")
        categories = kwargs.get(
            "categories", ["performance", "accessibility", "best-practices", "seo"]
        )
        include_page_speed = kwargs.get("include_page_speed", True)

        req = AuditRequest(
            url=url,
            strategy=strategy,
            categories=categories,
            include_page_speed=include_page_speed,
        )

        validation = validate_audit_request(req)
        if not validation.allowed or validation.request is None:
            return {
                "success": False,
                "error": "validation_failed",
                "reason": validation.reason,
            }

        try:
            result = await self._adapter.audit(validation.request)
            return {
                "success": True,
                "audit_id": result.audit_id,
                "url": result.url,
                "final_url": result.final_url,
                "timestamp": result.timestamp,
                "strategy": result.strategy,
                "scores": result.scores.model_dump(),
                "vitals": result.vitals.model_dump(),
                "network": result.network.model_dump(),
                "security": result.security.model_dump(),
                "seo": result.seo.model_dump(),
                "opportunities": [opp.model_dump() for opp in result.opportunities],
                "source": result.source,
            }
        except SiteAuditTimeoutError as exc:
            return {"success": False, "error": "timeout", "reason": str(exc)}
        except SiteAuditConnectionError as exc:
            return {"success": False, "error": "connection_error", "reason": str(exc)}
        except SiteAuditError as exc:
            return {"success": False, "error": "audit_error", "reason": str(exc)}

    def audit_metadata(self, arguments: dict[str, Any], result: Any) -> dict[str, Any] | None:
        if not isinstance(result, dict) or not result.get("success"):
            return None
        scores = result.get("scores", {})
        vitals = result.get("vitals", {})
        seo = result.get("seo", {})
        sec = result.get("security", {})
        return {
            "audit_id": result.get("audit_id"),
            "url": result.get("url") or arguments.get("url"),
            "strategy": result.get("strategy", "mobile"),
            "performance_score": scores.get("performance"),
            "accessibility_score": scores.get("accessibility"),
            "best_practices_score": scores.get("best_practices"),
            "seo_score": scores.get("seo"),
            "lcp_ms": vitals.get("lcp_ms"),
            "fcp_ms": vitals.get("fcp_ms"),
            "cls": vitals.get("cls"),
            "ttfb_ms": vitals.get("ttfb_ms"),
            "seo_issues_count": len(seo.get("issues", [])),
            "security_issues_count": len(sec.get("issues", [])),
            "opportunities_count": len(result.get("opportunities", [])),
            "source": result.get("source"),
        }


class CrawlWebsiteTool(BaseTool):
    name = "crawl_website"
    description = (
        "Crawl a website structure starting from a URL up to a maximum number of pages "
        "and depth to analyze page load times, structural links, and detect broken links."
    )
    required_permission = "site:crawl:run"
    parameters = {
        "type": "object",
        "properties": {
            "start_url": {
                "type": "string",
                "description": "Root URL from which to begin crawling.",
            },
            "max_pages": {
                "type": "integer",
                "description": "Maximum number of unique pages to crawl (1 to 20, default 5).",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum link hop depth from start_url (1 to 3, default 2).",
            },
            "stay_on_domain": {
                "type": "boolean",
                "description": (
                    "Whether to constrain crawling strictly to the same domain (default true)."
                ),
            },
        },
        "required": ["start_url"],
    }

    def __init__(self, adapter: SiteAuditAdapter) -> None:
        self._adapter = adapter

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        start_url = kwargs.get("start_url", "").strip()
        max_pages = int(kwargs.get("max_pages", 5))
        max_depth = int(kwargs.get("max_depth", 2))
        stay_on_domain = bool(kwargs.get("stay_on_domain", True))

        req = CrawlRequest(
            start_url=start_url,
            max_pages=max_pages,
            max_depth=max_depth,
            stay_on_domain=stay_on_domain,
        )

        validation = validate_crawl_request(req)
        if not validation.allowed or validation.request is None:
            return {
                "success": False,
                "error": "validation_failed",
                "reason": validation.reason,
            }

        try:
            result = await self._adapter.crawl(validation.request)
            return {
                "success": True,
                "crawl_id": result.crawl_id,
                "start_url": result.start_url,
                "domain": result.domain,
                "total_pages_crawled": result.total_pages_crawled,
                "pages": [p.model_dump() for p in result.pages],
                "broken_links": result.broken_links,
                "average_load_time_ms": result.average_load_time_ms,
                "crawl_summary": result.crawl_summary,
            }
        except SiteAuditTimeoutError as exc:
            return {"success": False, "error": "timeout", "reason": str(exc)}
        except SiteAuditConnectionError as exc:
            return {"success": False, "error": "connection_error", "reason": str(exc)}
        except SiteAuditError as exc:
            return {"success": False, "error": "crawl_error", "reason": str(exc)}

    def audit_metadata(self, arguments: dict[str, Any], result: Any) -> dict[str, Any] | None:
        if not isinstance(result, dict) or not result.get("success"):
            return None
        return {
            "crawl_id": result.get("crawl_id"),
            "start_url": result.get("start_url") or arguments.get("start_url"),
            "domain": result.get("domain"),
            "total_pages_crawled": result.get("total_pages_crawled", 0),
            "broken_links_count": len(result.get("broken_links", [])),
            "average_load_time_ms": result.get("average_load_time_ms", 0.0),
        }


class SiteAuditSkill(BaseSkill):
    name = "site_audit"
    display_name = "Site Audit & Performance"
    description = (
        "Audit website performance, Core Web Vitals, Lighthouse scores, SEO health, "
        "security headers, and crawl site structure."
    )
    version = "1.0.0"
    trust_level = TrustLevel.VERIFIED
    required_permissions = ["site:audit:run", "site:crawl:run"]

    def __init__(self, adapter: SiteAuditAdapter | None = None) -> None:
        self._adapter = adapter or SiteAuditAdapter()

    def get_tools(self) -> list[BaseTool]:
        return [
            AuditWebsiteTool(self._adapter),
            CrawlWebsiteTool(self._adapter),
        ]
