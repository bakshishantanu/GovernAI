from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ScoreSummary(BaseModel):
    """Normalized 0-100 scores across key Lighthouse categories."""

    performance: int = Field(ge=0, le=100, default=0)
    accessibility: int = Field(ge=0, le=100, default=0)
    best_practices: int = Field(ge=0, le=100, default=0)
    seo: int = Field(ge=0, le=100, default=0)


class VitalsMetrics(BaseModel):
    """Core Web Vitals and key speed metrics with human-readable ratings."""

    lcp_ms: float | None = None
    lcp_rating: str = "NEEDS_IMPROVEMENT"  # GOOD, NEEDS_IMPROVEMENT, POOR
    fcp_ms: float | None = None
    fcp_rating: str = "NEEDS_IMPROVEMENT"
    cls: float | None = None
    cls_rating: str = "NEEDS_IMPROVEMENT"
    tbt_ms: float | None = None
    tbt_rating: str = "NEEDS_IMPROVEMENT"
    speed_index_ms: float | None = None
    speed_index_rating: str = "NEEDS_IMPROVEMENT"
    ttfb_ms: float | None = None
    ttfb_rating: str = "NEEDS_IMPROVEMENT"
    inp_ms: float | None = None


class NetworkMetrics(BaseModel):
    """HTTP and transport timings."""

    dns_lookup_ms: float | None = None
    ssl_handshake_ms: float | None = None
    connection_time_ms: float | None = None
    total_time_ms: float | None = None
    page_size_kb: float | None = None
    content_type: str | None = None
    status_code: int = 200
    compression: str | None = None  # gzip, br, none


class SecurityReport(BaseModel):
    """Transport security, header hygiene, and cookie checks."""

    is_https: bool = True
    hsts_enabled: bool = False
    csp_enabled: bool = False
    x_frame_options: str | None = None
    x_content_type_options: str | None = None
    referrer_policy: str | None = None
    score: int = Field(ge=0, le=100, default=100)
    issues: list[str] = Field(default_factory=list)


class SeoReport(BaseModel):
    """Search engine discovery, metadata, and structural tags."""

    title: str | None = None
    title_length: int = 0
    meta_description: str | None = None
    meta_description_length: int = 0
    canonical_url: str | None = None
    robots_meta: str | None = None
    viewport_configured: bool = False
    h1_count: int = 0
    h1_tags: list[str] = Field(default_factory=list)
    h2_count: int = 0
    h3_count: int = 0
    images_count: int = 0
    images_missing_alt: int = 0
    internal_links_count: int = 0
    external_links_count: int = 0
    open_graph_tags: dict[str, str] = Field(default_factory=dict)
    score: int = Field(ge=0, le=100, default=100)
    issues: list[str] = Field(default_factory=list)


class AuditOpportunity(BaseModel):
    """Actionable improvement item like Lighthouse opportunities."""

    id: str
    title: str
    description: str
    score_impact: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    category: str = "performance"  # performance, accessibility, best_practices, seo, security
    estimated_savings_ms: float | None = None


class AuditRequest(BaseModel):
    """Parameters for auditing a target URL."""

    url: str
    strategy: str = "mobile"  # mobile, desktop
    categories: list[str] = Field(
        default_factory=lambda: ["performance", "accessibility", "best-practices", "seo"]
    )
    extract_seo: bool = True
    extract_security: bool = True
    include_page_speed: bool = True


class AuditResult(BaseModel):
    """The complete site audit and vitals report."""

    audit_id: str = Field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:8]}")
    url: str
    final_url: str | None = None
    timestamp: str
    strategy: str
    scores: ScoreSummary
    vitals: VitalsMetrics
    network: NetworkMetrics
    security: SecurityReport
    seo: SeoReport
    opportunities: list[AuditOpportunity] = Field(default_factory=list)
    source: str = "native"  # pagespeed_api, native, mock


class CrawledPage(BaseModel):
    """Summary of one page inspected during a site crawl."""

    url: str
    status_code: int = 200
    title: str | None = None
    load_time_ms: float = 0.0
    content_size_kb: float = 0.0
    internal_links: list[str] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class CrawlRequest(BaseModel):
    """Parameters for crawling a website structure."""

    start_url: str
    max_pages: int = 5
    max_depth: int = 2
    stay_on_domain: bool = True


class CrawlResult(BaseModel):
    """Outcome of a recursive site crawl."""

    crawl_id: str = Field(default_factory=lambda: f"crawl_{uuid.uuid4().hex[:8]}")
    start_url: str
    domain: str
    total_pages_crawled: int
    pages: list[CrawledPage] = Field(default_factory=list)
    broken_links: list[dict[str, Any]] = Field(default_factory=list)
    average_load_time_ms: float = 0.0
    crawl_summary: str = ""
