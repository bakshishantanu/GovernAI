from __future__ import annotations

import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

import logging
from app.runtime.site_audit.builtwith_adapter import BuiltWithAdapter
from app.runtime.site_audit.models import (
    AuditOpportunity,
    AuditRequest,
    AuditResult,
    CrawledPage,
    CrawlRequest,
    CrawlResult,
    DomainAuthorityReport,
    NetworkMetrics,
    ScoreSummary,
    SecurityReport,
    SeoReport,
    TechStackProfile,
    VitalsMetrics,
)
from app.runtime.site_audit.semrush_adapter import SemrushAdapter

logger = logging.getLogger(__name__)


class SiteAuditError(Exception):
    """Base exception for site audit failure."""


class SiteAuditTimeoutError(SiteAuditError):
    """Raised when a site or audit endpoint times out."""


class SiteAuditConnectionError(SiteAuditError):
    """Raised when the target host cannot be reached."""


class _AuditHTMLParser(HTMLParser):
    """Standard-library HTML parser extracting SEO, structure, and links without external deps."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.title: str | None = None
        self._in_title = False
        self.meta_description: str | None = None
        self.robots_meta: str | None = None
        self.viewport_configured = False
        self.canonical_url: str | None = None
        self.open_graph_tags: dict[str, str] = {}

        self.h1_tags: list[str] = []
        self._in_h1 = False
        self._current_h1_text = ""
        self.h2_count = 0
        self.h3_count = 0

        self.images_count = 0
        self.images_missing_alt = 0

        self.internal_links: set[str] = set()
        self.external_links: set[str] = set()
        self.scripts_count = 0
        self.stylesheets_count = 0

        parsed = urlparse(base_url)
        self.base_domain = (parsed.hostname or "").lower()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        attr_dict: dict[str, str] = {
            (k or "").lower(): (v or "") for k, v in attrs if k is not None
        }

        if tag_lower == "title":
            self._in_title = True
        elif tag_lower == "h1":
            self._in_h1 = True
            self._current_h1_text = ""
        elif tag_lower == "h2":
            self.h2_count += 1
        elif tag_lower == "h3":
            self.h3_count += 1
        elif tag_lower == "script":
            self.scripts_count += 1
        elif tag_lower == "link":
            rel = attr_dict.get("rel", "").lower()
            if rel == "canonical":
                self.canonical_url = attr_dict.get("href")
            elif "stylesheet" in rel:
                self.stylesheets_count += 1
        elif tag_lower == "meta":
            name = attr_dict.get("name", "").lower()
            prop = attr_dict.get("property", "").lower()
            content = attr_dict.get("content", "")

            if name == "description":
                self.meta_description = content
            elif name == "robots":
                self.robots_meta = content
            elif name == "viewport":
                self.viewport_configured = True
            elif prop.startswith("og:") or prop.startswith("twitter:"):
                self.open_graph_tags[prop] = content
        elif tag_lower == "img":
            self.images_count += 1
            alt = attr_dict.get("alt")
            if alt is None or not alt.strip():
                self.images_missing_alt += 1
        elif tag_lower == "a":
            href = attr_dict.get("href", "").strip()
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                full_url = urljoin(self.base_url, href)
                parsed_href = urlparse(full_url)
                link_domain = (parsed_href.hostname or "").lower()
                if link_domain == self.base_domain or link_domain.endswith(f".{self.base_domain}"):
                    self.internal_links.add(full_url)
                elif link_domain:
                    self.external_links.add(full_url)

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower == "title":
            self._in_title = False
        elif tag_lower == "h1":
            self._in_h1 = False
            if self._current_h1_text.strip():
                self.h1_tags.append(self._current_h1_text.strip())

    def handle_data(self, data: str) -> None:
        if self._in_title and self.title is None:
            self.title = data.strip()
        elif self._in_h1:
            self._current_h1_text += data


def _rate_vital(metric: str, value: float | None) -> str:
    """Classify Core Web Vitals into standard Lighthouse ratings."""
    if value is None:
        return "NEEDS_IMPROVEMENT"
    if metric == "lcp":
        return "GOOD" if value <= 2500 else ("NEEDS_IMPROVEMENT" if value <= 4000 else "POOR")
    if metric == "fcp":
        return "GOOD" if value <= 1800 else ("NEEDS_IMPROVEMENT" if value <= 3000 else "POOR")
    if metric == "cls":
        return "GOOD" if value <= 0.1 else ("NEEDS_IMPROVEMENT" if value <= 0.25 else "POOR")
    if metric == "tbt":
        return "GOOD" if value <= 200 else ("NEEDS_IMPROVEMENT" if value <= 600 else "POOR")
    if metric == "speed_index":
        return "GOOD" if value <= 3400 else ("NEEDS_IMPROVEMENT" if value <= 5800 else "POOR")
    if metric == "ttfb":
        return "GOOD" if value <= 800 else ("NEEDS_IMPROVEMENT" if value <= 1800 else "POOR")
    return "NEEDS_IMPROVEMENT"


class SiteAuditAdapter:
    """Client for auditing web pages via Lighthouse / Google PageSpeed Insights & native crawler."""

    PAGESPEED_API_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    DEFAULT_TIMEOUT_SECONDS = 25.0

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        mock_mode: bool = False,
        builtwith_adapter: BuiltWithAdapter | None = None,
        semrush_adapter: SemrushAdapter | None = None,
    ) -> None:
        self._client = http_client
        self.mock_mode = mock_mode
        self.builtwith = builtwith_adapter or BuiltWithAdapter(mock=mock_mode)
        self.semrush = semrush_adapter or SemrushAdapter(mock=mock_mode)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.DEFAULT_TIMEOUT_SECONDS),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.0.0 Safari/537.36 GovernAIBot/1.0"
                )
            },
        )

    async def audit(self, request: AuditRequest) -> AuditResult:
        """Run a full performance, vitals, SEO, security, tech stack, and domain authority audit."""
        parsed_url = urlparse(request.url)
        is_mock_host = parsed_url.hostname in {"test-audit.local"} or (
            parsed_url.hostname and parsed_url.hostname.endswith(".mock.test")
        )

        if self.mock_mode or is_mock_host:
            return self._generate_mock_audit_result(request)

        # 1. Inspect URL directly with native HTTP & DOM parser
        native_data = await self._inspect_native(request.url)

        # 2. If requested, attempt to fetch Google PageSpeed Insights (Lighthouse)
        pagespeed_data = None
        if request.include_page_speed:
            try:
                pagespeed_data = await self._fetch_pagespeed_insights(
                    request.url, request.strategy, request.categories
                )
            except Exception:
                # Silently fall back to native data if Google API is rate-limited or unavailable
                pagespeed_data = None

        # 3. BuiltWith Tech Stack Profiling
        tech_profile = None
        if getattr(request, "include_tech_stack", True):
            try:
                tech_profile = await self.builtwith.detect_technologies(
                    url_or_domain=request.url,
                    html_content=native_data.get("raw_html"),
                    response_headers=native_data.get("raw_headers"),
                )
            except Exception as exc:
                logger.warning("BuiltWith profiling failed for %s: %s", request.url, exc)

        # 4. Semrush by Adobe Domain Authority & Search Intelligence
        domain_auth = None
        if getattr(request, "include_domain_authority", True):
            try:
                domain_auth = await self.semrush.get_domain_authority(
                    url_or_domain=request.url,
                    html_content=native_data.get("raw_html"),
                    seo_report=native_data.get("seo"),
                    security_report=native_data.get("security"),
                )
            except Exception as exc:
                logger.warning("Semrush domain authority check failed for %s: %s", request.url, exc)

        return self._build_audit_result(
            request,
            native_data,
            pagespeed_data,
            tech_profile=tech_profile,
            domain_authority=domain_auth,
        )

    async def detect_tech_stack(self, domain_or_url: str) -> TechStackProfile:
        """Standalone technology stack detection via BuiltWith."""
        return await self.builtwith.detect_technologies(domain_or_url)

    async def get_domain_authority(self, domain_or_url: str) -> DomainAuthorityReport:
        """Standalone domain authority and search footprint analysis via Semrush by Adobe."""
        return await self.semrush.get_domain_authority(domain_or_url)

    async def crawl(self, request: CrawlRequest) -> CrawlResult:
        """Crawl website starting from start_url up to max_pages and max_depth."""
        parsed_start = urlparse(request.start_url)
        is_mock_host = parsed_start.hostname in {"test-audit.local"} or (
            parsed_start.hostname and parsed_start.hostname.endswith(".mock.test")
        )

        if self.mock_mode or is_mock_host:
            return self._generate_mock_crawl_result(request)

        client = await self._get_client()
        domain = (parsed_start.hostname or "").lower()

        visited: set[str] = set()
        to_visit: list[tuple[str, int]] = [(request.start_url, 0)]  # (url, depth)
        pages: list[CrawledPage] = []
        broken_links: list[dict[str, Any]] = []
        total_load_time = 0.0

        owns_client = self._client is None
        try:
            while to_visit and len(pages) < request.max_pages:
                curr_url, curr_depth = to_visit.pop(0)
                norm_url = curr_url.split("#")[0]
                if norm_url in visited:
                    continue
                visited.add(norm_url)

                t0 = time.perf_counter()
                try:
                    resp = await client.get(norm_url)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    total_load_time += elapsed_ms

                    content_type = resp.headers.get("content-type", "")
                    content_size_kb = len(resp.content) / 1024.0

                    parser = _AuditHTMLParser(norm_url)
                    if "text/html" in content_type:
                        try:
                            parser.feed(resp.text)
                        except Exception:
                            pass

                    issues = []
                    if resp.status_code >= 400:
                        issues.append(f"HTTP {resp.status_code} response error")
                        broken_links.append(
                            {"url": norm_url, "status_code": resp.status_code, "depth": curr_depth}
                        )

                    crawled_page = CrawledPage(
                        url=norm_url,
                        status_code=resp.status_code,
                        title=parser.title,
                        load_time_ms=round(elapsed_ms, 1),
                        content_size_kb=round(content_size_kb, 1),
                        internal_links=sorted(parser.internal_links),
                        external_links=sorted(parser.external_links),
                        issues=issues,
                    )
                    pages.append(crawled_page)

                    # Discover next links if within depth
                    if curr_depth < request.max_depth:
                        for link in parser.internal_links:
                            norm_link = link.split("#")[0]
                            if norm_link not in visited:
                                link_domain = (urlparse(norm_link).hostname or "").lower()
                                if not request.stay_on_domain or (link_domain == domain):
                                    to_visit.append((norm_link, curr_depth + 1))

                except (httpx.TimeoutException, httpx.RequestError) as exc:
                    broken_links.append(
                        {"url": norm_url, "error": str(exc), "depth": curr_depth}
                    )
        finally:
            if owns_client:
                await client.aclose()

        avg_load = total_load_time / max(len(pages), 1)
        summary = (
            f"Crawled {len(pages)} pages on {domain}. "
            f"Average load time: {avg_load:.1f}ms. "
            f"Identified {len(broken_links)} broken or unreachable links."
        )

        return CrawlResult(
            start_url=request.start_url,
            domain=domain,
            total_pages_crawled=len(pages),
            pages=pages,
            broken_links=broken_links,
            average_load_time_ms=round(avg_load, 1),
            crawl_summary=summary,
        )

    async def _inspect_native(self, url: str) -> dict[str, Any]:
        """Fetch URL directly with httpx and perform DOM/headers inspection."""
        client = await self._get_client()
        owns_client = self._client is None
        t0 = time.perf_counter()

        try:
            resp = await client.get(url)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
        except httpx.TimeoutException as exc:
            raise SiteAuditTimeoutError(f"Connection to '{url}' timed out") from exc
        except httpx.RequestError as exc:
            raise SiteAuditConnectionError(f"Could not connect to '{url}': {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

        content_size_kb = len(resp.content) / 1024.0
        content_type = resp.headers.get("content-type", "")

        parser = _AuditHTMLParser(str(resp.url))
        if "text/html" in content_type:
            try:
                parser.feed(resp.text)
            except Exception:
                pass

        # Security Headers Evaluation
        is_https = str(resp.url).startswith("https://")
        hsts_enabled = "strict-transport-security" in resp.headers
        csp_enabled = "content-security-policy" in resp.headers
        x_frame = resp.headers.get("x-frame-options")
        x_content = resp.headers.get("x-content-type-options")
        referrer_policy = resp.headers.get("referrer-policy")

        sec_issues = []
        sec_score = 100
        if not is_https:
            sec_score -= 40
            sec_issues.append("Site does not use HTTPS protocol")
        if not hsts_enabled:
            sec_score -= 15
            sec_issues.append("Strict-Transport-Security (HSTS) header is missing")
        if not csp_enabled:
            sec_score -= 15
            sec_issues.append("Content-Security-Policy (CSP) header is missing")
        if not x_frame:
            sec_score -= 15
            sec_issues.append("X-Frame-Options header missing (vulnerable to clickjacking)")
        if not x_content:
            sec_score -= 15
            sec_issues.append("X-Content-Type-Options: nosniff header missing")

        sec_report = SecurityReport(
            is_https=is_https,
            hsts_enabled=hsts_enabled,
            csp_enabled=csp_enabled,
            x_frame_options=x_frame,
            x_content_type_options=x_content,
            referrer_policy=referrer_policy,
            score=max(0, min(100, sec_score)),
            issues=sec_issues,
        )

        # SEO Evaluation
        seo_issues = []
        seo_score = 100
        title_len = len(parser.title or "")
        desc_len = len(parser.meta_description or "")

        if not parser.title:
            seo_score -= 25
            seo_issues.append("Page is missing a <title> element")
        elif title_len < 10 or title_len > 70:
            seo_score -= 10
            seo_issues.append(
                f"Page title length ({title_len} chars) is outside optimal range (10-70)"
            )

        if not parser.meta_description:
            seo_score -= 20
            seo_issues.append("Meta description is missing")
        elif desc_len < 50 or desc_len > 160:
            seo_score -= 10
            seo_issues.append(
                f"Meta description length ({desc_len} chars) is outside optimal range (50-160)"
            )

        if not parser.viewport_configured:
            seo_score -= 20
            seo_issues.append("Missing <meta name='viewport'> tag for mobile responsiveness")

        if len(parser.h1_tags) == 0:
            seo_score -= 15
            seo_issues.append("No <h1> heading found on page")
        elif len(parser.h1_tags) > 1:
            seo_score -= 10
            seo_issues.append(f"Multiple <h1> headings found ({len(parser.h1_tags)} found)")

        if parser.images_missing_alt > 0:
            seo_score -= min(15, parser.images_missing_alt * 5)
            seo_issues.append(
                f"{parser.images_missing_alt} of {parser.images_count} images missing alt text"
            )

        seo_report = SeoReport(
            title=parser.title,
            title_length=title_len,
            meta_description=parser.meta_description,
            meta_description_length=desc_len,
            canonical_url=parser.canonical_url,
            robots_meta=parser.robots_meta,
            viewport_configured=parser.viewport_configured,
            h1_count=len(parser.h1_tags),
            h1_tags=parser.h1_tags,
            h2_count=parser.h2_count,
            h3_count=parser.h3_count,
            images_count=parser.images_count,
            images_missing_alt=parser.images_missing_alt,
            internal_links_count=len(parser.internal_links),
            external_links_count=len(parser.external_links),
            open_graph_tags=parser.open_graph_tags,
            score=max(0, min(100, seo_score)),
            issues=seo_issues,
        )

        network_metrics = NetworkMetrics(
            total_time_ms=round(elapsed_ms, 1),
            page_size_kb=round(content_size_kb, 1),
            content_type=content_type,
            status_code=resp.status_code,
            compression=resp.headers.get("content-encoding"),
        )

        return {
            "final_url": str(resp.url),
            "status_code": resp.status_code,
            "elapsed_ms": elapsed_ms,
            "security": sec_report,
            "seo": seo_report,
            "network": network_metrics,
            "scripts_count": parser.scripts_count,
            "stylesheets_count": parser.stylesheets_count,
            "raw_html": resp.text,
            "raw_headers": dict(resp.headers),
        }

    async def _fetch_pagespeed_insights(
        self, url: str, strategy: str, categories: list[str]
    ) -> dict[str, Any] | None:
        """Query Google PageSpeed Insights v5 API for real Lighthouse scores and vitals."""
        client = await self._get_client()
        owns_client = self._client is None

        params = [("url", url), ("strategy", strategy)]
        for cat in categories:
            params.append(("category", cat))

        try:
            resp = await client.get(self.PAGESPEED_API_ENDPOINT, params=params)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            return None
        finally:
            if owns_client:
                await client.aclose()
        return None

    def _build_audit_result(
        self,
        request: AuditRequest,
        native_data: dict[str, Any],
        pagespeed_data: dict[str, Any] | None,
        tech_profile: TechStackProfile | None = None,
        domain_authority: DomainAuthorityReport | None = None,
    ) -> AuditResult:
        """Combine Google PageSpeed Insights (if available) with native DOM/network audit."""
        timestamp = datetime.now(timezone.utc).isoformat()
        final_url = native_data.get("final_url", request.url)
        sec_report: SecurityReport = native_data["security"]
        seo_report: SeoReport = native_data["seo"]
        net_metrics: NetworkMetrics = native_data["network"]

        if pagespeed_data and "lighthouseResult" in pagespeed_data:
            lr = pagespeed_data["lighthouseResult"]
            cats = lr.get("categories", {})
            audits = lr.get("audits", {})

            perf_score = int(round((cats.get("performance", {}).get("score") or 0.0) * 100))
            a11y_score = int(round((cats.get("accessibility", {}).get("score") or 0.0) * 100))
            bp_score = int(round((cats.get("best-practices", {}).get("score") or 0.0) * 100))
            page_seo_score = int(round((cats.get("seo", {}).get("score") or 0.0) * 100))

            # Combine PageSpeed SEO with native tag checks
            combined_seo = int(round((page_seo_score + seo_report.score) / 2))

            scores = ScoreSummary(
                performance=perf_score,
                accessibility=a11y_score,
                best_practices=bp_score,
                seo=combined_seo,
            )

            # Extract Core Web Vitals
            lcp_val = audits.get("largest-contentful-paint", {}).get("numericValue")
            fcp_val = audits.get("first-contentful-paint", {}).get("numericValue")
            cls_val = audits.get("cumulative-layout-shift", {}).get("numericValue")
            tbt_val = audits.get("total-blocking-time", {}).get("numericValue")
            si_val = audits.get("speed-index", {}).get("numericValue")
            ttfb_val = audits.get("server-response-time", {}).get("numericValue")

            vitals = VitalsMetrics(
                lcp_ms=round(lcp_val, 1) if lcp_val is not None else None,
                lcp_rating=_rate_vital("lcp", lcp_val),
                fcp_ms=round(fcp_val, 1) if fcp_val is not None else None,
                fcp_rating=_rate_vital("fcp", fcp_val),
                cls=round(cls_val, 3) if cls_val is not None else None,
                cls_rating=_rate_vital("cls", cls_val),
                tbt_ms=round(tbt_val, 1) if tbt_val is not None else None,
                tbt_rating=_rate_vital("tbt", tbt_val),
                speed_index_ms=round(si_val, 1) if si_val is not None else None,
                speed_index_rating=_rate_vital("speed_index", si_val),
                ttfb_ms=round(ttfb_val, 1) if ttfb_val is not None else None,
                ttfb_rating=_rate_vital("ttfb", ttfb_val),
            )

            # Extract Lighthouse Opportunities
            opps = []
            for audit_id, audit in audits.items():
                details = audit.get("details", {})
                if details.get("type") == "opportunity" and audit.get("score") not in (1, None):
                    savings = details.get("overallSavingsMs")
                    opps.append(
                        AuditOpportunity(
                            id=audit_id,
                            title=audit.get("title", audit_id),
                            description=audit.get("description", ""),
                            score_impact=(
                                "HIGH"
                                if (savings and savings > 1000)
                                else ("MEDIUM" if savings and savings > 300 else "LOW")
                            ),
                            category="performance",
                            estimated_savings_ms=round(savings, 1) if savings else None,
                        )
                    )

            # Sort opportunities by highest savings first
            opps.sort(key=lambda o: (o.estimated_savings_ms or 0.0), reverse=True)

            return AuditResult(
                url=request.url,
                final_url=final_url,
                timestamp=timestamp,
                strategy=request.strategy,
                scores=scores,
                vitals=vitals,
                network=net_metrics,
                security=sec_report,
                seo=seo_report,
                opportunities=opps[:6],
                tech_stack=tech_profile,
                domain_authority=domain_authority,
                source="pagespeed_api",
            )

        # Native Calculation Fallback
        elapsed = native_data.get("elapsed_ms", 300.0)
        estimated_lcp = max(600.0, elapsed * 1.8)
        estimated_fcp = max(300.0, elapsed * 0.9)
        estimated_cls = 0.02
        estimated_tbt = 50.0 if elapsed < 800 else 180.0
        estimated_si = max(700.0, elapsed * 1.4)

        perf_calc = 100
        if elapsed > 1500:
            perf_calc -= 30
        elif elapsed > 800:
            perf_calc -= 15
        if net_metrics.page_size_kb and net_metrics.page_size_kb > 2000:
            perf_calc -= 20
        elif net_metrics.page_size_kb and net_metrics.page_size_kb > 1000:
            perf_calc -= 10
        if not net_metrics.compression:
            perf_calc -= 15

        scores = ScoreSummary(
            performance=max(20, min(100, perf_calc)),
            accessibility=88 if seo_report.images_missing_alt == 0 else 72,
            best_practices=sec_report.score,
            seo=seo_report.score,
        )

        vitals = VitalsMetrics(
            lcp_ms=round(estimated_lcp, 1),
            lcp_rating=_rate_vital("lcp", estimated_lcp),
            fcp_ms=round(estimated_fcp, 1),
            fcp_rating=_rate_vital("fcp", estimated_fcp),
            cls=estimated_cls,
            cls_rating=_rate_vital("cls", estimated_cls),
            tbt_ms=round(estimated_tbt, 1),
            tbt_rating=_rate_vital("tbt", estimated_tbt),
            speed_index_ms=round(estimated_si, 1),
            speed_index_rating=_rate_vital("speed_index", estimated_si),
            ttfb_ms=round(elapsed, 1),
            ttfb_rating=_rate_vital("ttfb", elapsed),
        )

        opportunities = []
        if not net_metrics.compression:
            opportunities.append(
                AuditOpportunity(
                    id="enable-compression",
                    title="Enable text compression (gzip or brotli)",
                    description="Compress network responses to reduce transfer bytes.",
                    score_impact="HIGH",
                    category="performance",
                    estimated_savings_ms=250.0,
                )
            )
        if seo_report.images_missing_alt > 0:
            opportunities.append(
                AuditOpportunity(
                    id="image-alt-tags",
                    title="Add missing alt attributes to images",
                    description=(
                        f"Provide descriptive alt text for "
                        f"{seo_report.images_missing_alt} image(s)."
                    ),
                    score_impact="MEDIUM",
                    category="accessibility",
                )
            )
        if not sec_report.hsts_enabled:
            opportunities.append(
                AuditOpportunity(
                    id="enable-hsts",
                    title="Enable HTTP Strict Transport Security (HSTS)",
                    description=(
                        "Protect site users against SSL-stripping man-in-the-middle attacks."
                    ),
                    score_impact="HIGH",
                    category="security",
                )
            )

        return AuditResult(
            url=request.url,
            final_url=final_url,
            timestamp=timestamp,
            strategy=request.strategy,
            scores=scores,
            vitals=vitals,
            network=net_metrics,
            security=sec_report,
            seo=seo_report,
            opportunities=opportunities,
            tech_stack=tech_profile,
            domain_authority=domain_authority,
            source="native",
        )

    def _generate_mock_audit_result(self, request: AuditRequest) -> AuditResult:
        """Deterministic mock response for unit tests and offline testing."""
        domain = urlparse(request.url).hostname or "test-audit.local"
        tech_stack = self.builtwith._generate_mock_profile(domain)
        domain_authority = self.semrush._generate_mock_report(domain)
        return AuditResult(
            url=request.url,
            final_url=request.url,
            timestamp=datetime.now(timezone.utc).isoformat(),
            strategy=request.strategy,
            scores=ScoreSummary(
                performance=94,
                accessibility=91,
                best_practices=96,
                seo=98,
            ),
            vitals=VitalsMetrics(
                lcp_ms=1640.0,
                lcp_rating="GOOD",
                fcp_ms=890.0,
                fcp_rating="GOOD",
                cls=0.015,
                cls_rating="GOOD",
                tbt_ms=45.0,
                tbt_rating="GOOD",
                speed_index_ms=1320.0,
                speed_index_rating="GOOD",
                ttfb_ms=120.0,
                ttfb_rating="GOOD",
            ),
            network=NetworkMetrics(
                total_time_ms=120.0,
                page_size_kb=142.5,
                content_type="text/html; charset=utf-8",
                status_code=200,
                compression="gzip",
            ),
            security=SecurityReport(
                is_https=True,
                hsts_enabled=True,
                csp_enabled=True,
                x_frame_options="DENY",
                x_content_type_options="nosniff",
                referrer_policy="strict-origin-when-cross-origin",
                score=100,
                issues=[],
            ),
            seo=SeoReport(
                title="GovernAI - Enterprise AI Agent Governance Platform",
                title_length=51,
                meta_description=(
                    "GovernAI provides real-time security, token budget guards, "
                    "and compliance governance for autonomous AI agents."
                ),
                meta_description_length=124,
                canonical_url=request.url,
                robots_meta="index, follow",
                viewport_configured=True,
                h1_count=1,
                h1_tags=["Enterprise AI Agent Governance Platform"],
                h2_count=4,
                h3_count=8,
                images_count=6,
                images_missing_alt=0,
                internal_links_count=14,
                external_links_count=3,
                open_graph_tags={"og:title": "GovernAI Platform", "og:type": "website"},
                score=100,
                issues=[],
            ),
            opportunities=[
                AuditOpportunity(
                    id="serve-images-next-gen",
                    title="Serve images in next-gen formats (WebP/AVIF)",
                    description=(
                        "Image formats like WebP often provide better compression than PNG or JPEG."
                    ),
                    score_impact="LOW",
                    category="performance",
                    estimated_savings_ms=60.0,
                )
            ],
            tech_stack=tech_stack,
            domain_authority=domain_authority,
            source="mock",
        )

    def _generate_mock_crawl_result(self, request: CrawlRequest) -> CrawlResult:
        """Deterministic mock crawl outcome for unit tests."""
        domain = urlparse(request.start_url).hostname or "example.com"
        mock_pages = [
            CrawledPage(
                url=request.start_url,
                status_code=200,
                title="Homepage | Demo",
                load_time_ms=115.0,
                content_size_kb=85.4,
                internal_links=[
                    f"{request.start_url}/about",
                    f"{request.start_url}/pricing",
                    f"{request.start_url}/docs",
                ],
                external_links=["https://twitter.com/governai", "https://github.com/governai"],
                issues=[],
            ),
            CrawledPage(
                url=f"{request.start_url}/about",
                status_code=200,
                title="About Us | Demo",
                load_time_ms=95.0,
                content_size_kb=62.1,
                internal_links=[request.start_url, f"{request.start_url}/pricing"],
                external_links=[],
                issues=[],
            ),
            CrawledPage(
                url=f"{request.start_url}/pricing",
                status_code=200,
                title="Pricing Plans | Demo",
                load_time_ms=130.0,
                content_size_kb=71.2,
                internal_links=[request.start_url, f"{request.start_url}/signup"],
                external_links=[],
                issues=[],
            ),
        ]

        return CrawlResult(
            start_url=request.start_url,
            domain=domain,
            total_pages_crawled=min(len(mock_pages), request.max_pages),
            pages=mock_pages[: request.max_pages],
            broken_links=[],
            average_load_time_ms=113.3,
            crawl_summary=(
                f"Crawled {min(len(mock_pages), request.max_pages)} pages on {domain}. "
                "Average load time: 113.3ms. All examined links are healthy (0 broken)."
            ),
        )
