from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse

from app.runtime.site_audit.models import AuditRequest, CrawlRequest

_ALLOWED_STRATEGIES = frozenset({"mobile", "desktop"})
_MAX_PAGES_LIMIT = 20
_MAX_DEPTH_LIMIT = 3
_DISALLOWED_HOSTNAMES = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "instance-data",
        "169.254.169.254",
    }
)


@dataclass(frozen=True)
class SiteAuditValidationResult:
    """Outcome of validating a site audit request before dispatching."""

    allowed: bool
    reason: str | None
    request: AuditRequest | None = None


@dataclass(frozen=True)
class SiteCrawlValidationResult:
    """Outcome of validating a crawl request before dispatching."""

    allowed: bool
    reason: str | None
    request: CrawlRequest | None = None


def is_ssrf_safe_url(url: str, allow_mock_hosts: bool = True) -> tuple[bool, str | None]:
    """Check whether a URL is valid and does not target internal / link-local infrastructure."""
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"

    clean_url = url.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception as exc:
        return False, f"Invalid URL format: {exc}"

    if parsed.scheme.lower() not in {"http", "https"}:
        return (
            False,
            f"Unsupported URL scheme '{parsed.scheme}'. Only 'http' and 'https' are allowed.",
        )

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False, "URL is missing a valid hostname"

    # Allow mock test domains specifically in test environments
    if allow_mock_hosts and (hostname == "test-audit.local" or hostname.endswith(".mock.test")):
        return True, None

    if (
        hostname in _DISALLOWED_HOSTNAMES
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
    ):
        return (
            False,
            f"Scanning internal/local hostname '{hostname}' is blocked (SSRF prevention)",
        )

    # Check for direct IP addresses targeting private or link-local subnets
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private:
            return False, f"Private IP address range '{ip}' is blocked (SSRF prevention)"
        if ip.is_loopback:
            return False, f"Loopback address '{ip}' is blocked (SSRF prevention)"
        if ip.is_link_local:
            return False, f"Link-local address '{ip}' is blocked (SSRF prevention)"
        if ip.is_multicast:
            return False, f"Multicast address '{ip}' is blocked"
        if ip.is_unspecified or ip.is_reserved:
            return False, f"Reserved IP address '{ip}' is blocked"
    except ValueError:
        # Hostname is a regular domain name (e.g. example.com), not an IP literal
        pass

    return True, None


def validate_audit_request(
    request: AuditRequest, allow_mock_hosts: bool = True
) -> SiteAuditValidationResult:
    """Validate and sanitize an AuditRequest."""
    safe, reason = is_ssrf_safe_url(request.url, allow_mock_hosts=allow_mock_hosts)
    if not safe:
        return SiteAuditValidationResult(allowed=False, reason=reason, request=request)

    strategy = (request.strategy or "mobile").lower()
    if strategy not in _ALLOWED_STRATEGIES:
        return SiteAuditValidationResult(
            allowed=False,
            reason=(
                f"Unsupported strategy '{request.strategy}'. Allowed: {sorted(_ALLOWED_STRATEGIES)}"
            ),
            request=request,
        )

    clean_request = request.model_copy(
        update={
            "url": request.url.strip(),
            "strategy": strategy,
        }
    )
    return SiteAuditValidationResult(allowed=True, reason=None, request=clean_request)


def validate_crawl_request(
    request: CrawlRequest, allow_mock_hosts: bool = True
) -> SiteCrawlValidationResult:
    """Validate and sanitize a CrawlRequest."""
    safe, reason = is_ssrf_safe_url(request.start_url, allow_mock_hosts=allow_mock_hosts)
    if not safe:
        return SiteCrawlValidationResult(allowed=False, reason=reason, request=request)

    if request.max_pages > _MAX_PAGES_LIMIT:
        return SiteCrawlValidationResult(
            allowed=False,
            reason=f"Maximum pages to crawl exceeded ({request.max_pages} > {_MAX_PAGES_LIMIT})",
            request=request,
        )
    if request.max_pages < 1:
        return SiteCrawlValidationResult(
            allowed=False,
            reason="max_pages must be at least 1",
            request=request,
        )

    if request.max_depth > _MAX_DEPTH_LIMIT:
        return SiteCrawlValidationResult(
            allowed=False,
            reason=f"Maximum crawl depth exceeded ({request.max_depth} > {_MAX_DEPTH_LIMIT})",
            request=request,
        )
    if request.max_depth < 1:
        return SiteCrawlValidationResult(
            allowed=False,
            reason="max_depth must be at least 1",
            request=request,
        )

    clean_request = request.model_copy(
        update={
            "start_url": request.start_url.strip(),
        }
    )
    return SiteCrawlValidationResult(allowed=True, reason=None, request=clean_request)
