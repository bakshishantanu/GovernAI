from __future__ import annotations

import logging
import re
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.runtime.site_audit.models import TechStackProfile, TechnologyItem

logger = logging.getLogger(__name__)

# Heuristic technology signatures: (Technology Name, Category, Description, Regex/Substrings in HTML/Headers)
TECH_SIGNATURES: list[dict[str, Any]] = [
    # --- CMS & Platforms ---
    {
        "name": "WordPress",
        "category": "CMS",
        "description": "Open-source Content Management System powering over 40% of the web.",
        "html_patterns": [r"wp-content/", r"wp-includes/", r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']WordPress', r"wp-json"],
        "header_patterns": [],
    },
    {
        "name": "Shopify",
        "category": "CMS",
        "description": "Leading multi-channel cloud e-commerce platform.",
        "html_patterns": [r"cdn\.shopify\.com", r"Shopify\.theme", r"window\.Shopify", r"shopify-features"],
        "header_patterns": [("x-shopid", r".+"), ("powered-by", r"Shopify")],
    },
    {
        "name": "Adobe Experience Manager (AEM)",
        "category": "CMS",
        "description": "Enterprise comprehensive content management solution for building websites and mobile apps.",
        "html_patterns": [r"/etc\.clientlibs/", r"/content/dam/", r"cq:template", r"granite\.csrf"],
        "header_patterns": [],
    },
    {
        "name": "Magento / Adobe Commerce",
        "category": "CMS",
        "description": "High-performance enterprise e-commerce platform by Adobe.",
        "html_patterns": [r"mage/cookies", r"/static/frontend/", r"Mage\.Cookies", r"checkout/cart"],
        "header_patterns": [("x-magento-tags", r".+")],
    },
    {
        "name": "Webflow",
        "category": "CMS",
        "description": "Visual website builder and modern SaaS CMS.",
        "html_patterns": [r"data-wf-page", r"data-wf-site", r"assets\.website-files\.com"],
        "header_patterns": [],
    },
    {
        "name": "Drupal",
        "category": "CMS",
        "description": "Flexible enterprise open-source content management system.",
        "html_patterns": [r"Drupal\.settings", r"/sites/default/files", r'<meta[^>]+name=["\']Generator["\'][^>]+content=["\']Drupal'],
        "header_patterns": [("x-drupal-cache", r".+"), ("x-generator", r"Drupal")],
    },
    {
        "name": "Squarespace",
        "category": "CMS",
        "description": "All-in-one website building and hosting platform.",
        "html_patterns": [r"static1\.squarespace\.com", r"Squarespace\.onInitialize", r"squarespace-headers"],
        "header_patterns": [],
    },
    {
        "name": "Ghost",
        "category": "CMS",
        "description": "Modern headless Node.js blogging and publication platform.",
        "html_patterns": [r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']Ghost', r"ghost-portal"],
        "header_patterns": [],
    },

    # --- JavaScript Frameworks ---
    {
        "name": "Next.js",
        "category": "Framework",
        "description": "The React Framework for the Web with hybrid static & server rendering.",
        "html_patterns": [r"/_next/static/", r'<div[^>]+id=["\']__next["\']', r'id=["\']__NEXT_DATA__["\']'],
        "header_patterns": [("x-powered-by", r"Next\.js")],
    },
    {
        "name": "React",
        "category": "Framework",
        "description": "The library for web and native user interfaces.",
        "html_patterns": [r"react\.production\.min\.js", r"react-dom", r"data-reactroot", r"_reactListening", r"/_next/static/chunks/"],
        "header_patterns": [],
    },
    {
        "name": "Vue.js",
        "category": "Framework",
        "description": "Progressive JavaScript framework for building user interfaces.",
        "html_patterns": [r"vue\.global\.js", r"data-v-[a-f0-9]+", r"__vue_app__", r"v-bind", r"v-model"],
        "header_patterns": [],
    },
    {
        "name": "Nuxt.js",
        "category": "Framework",
        "description": "The intuitive Vue Framework for server-rendered and static web applications.",
        "html_patterns": [r'<div[^>]+id=["\']__nuxt["\']', r"/_nuxt/", r"data-n-head"],
        "header_patterns": [],
    },
    {
        "name": "Angular",
        "category": "Framework",
        "description": "Platform for building mobile and desktop web applications.",
        "html_patterns": [r"ng-version", r"ng-app", r"angular\.min\.js", r"angular\.js"],
        "header_patterns": [],
    },
    {
        "name": "Svelte",
        "category": "Framework",
        "description": "Cybernetically enhanced web apps with compile-time reactivity.",
        "html_patterns": [r"class=[\"'][^\"']*svelte-[a-zA-Z0-9]+", r"__svelte"],
        "header_patterns": [],
    },
    {
        "name": "jQuery",
        "category": "JavaScript",
        "description": "Fast, small, and feature-rich JavaScript DOM manipulation library.",
        "html_patterns": [r"jquery[\.\-_0-9]*\.min\.js", r"jQuery v[0-9]"],
        "header_patterns": [],
    },

    # --- UI & Styling ---
    {
        "name": "Tailwind CSS",
        "category": "Framework",
        "description": "Utility-first CSS framework for rapid UI development.",
        "html_patterns": [r"tailwindcss", r"/tailwind", r'class=[\"\'][^\"\']*(?:flex|grid|px-[0-9]|py-[0-9]|text-[a-z]+-[0-9]+)[^\"\']*[\"\']'],
        "header_patterns": [],
    },
    {
        "name": "Bootstrap",
        "category": "Framework",
        "description": "Powerful, extensible, and feature-packed frontend toolkit.",
        "html_patterns": [r"bootstrap(?:\.bundle)?\.min\.css", r"bootstrap(?:\.bundle)?\.min\.js", r'class=[\"\'][^\"\']*(?:container-fluid|col-md-[0-9])[^\"\']*[\"\']'],
        "header_patterns": [],
    },
    {
        "name": "Material UI (MUI)",
        "category": "Framework",
        "description": "Comprehensive suite of UI tools implementing Google's Material Design.",
        "html_patterns": [r"MuiButton", r"MuiBox", r"MuiTypography", r"@mui/material"],
        "header_patterns": [],
    },

    # --- Analytics & Tag Management ---
    {
        "name": "Google Analytics 4 (GA4)",
        "category": "Analytics",
        "description": "Google's next-generation event-based web and app analytics.",
        "html_patterns": [r"googletagmanager\.com/gtag/js", r"gtag\(['\"]config['\"],\s*['\"]G-[A-Z0-9]+['\"]\)", r"window\.dataLayer"],
        "header_patterns": [],
    },
    {
        "name": "Google Tag Manager",
        "category": "Analytics",
        "description": "Tag management system for deploying and updating measurement tags.",
        "html_patterns": [r"googletagmanager\.com/gtm\.js", r"GTM-[A-Z0-9]+"],
        "header_patterns": [],
    },
    {
        "name": "Adobe Experience Platform / Adobe Analytics",
        "category": "Analytics",
        "description": "Adobe enterprise customer data platform and web analytics service.",
        "html_patterns": [r"assets\.adobedtm\.com", r"satelliteLib-", r"_satellite", r"adobeDataLayer"],
        "header_patterns": [],
    },
    {
        "name": "Meta Pixel",
        "category": "Advertising",
        "description": "Conversion tracking and audience optimization tool for Meta/Facebook.",
        "html_patterns": [r"connect\.facebook\.net/[a-zA-Z_]+/fbevents\.js", r"fbq\(['\"]init['\"]"],
        "header_patterns": [],
    },
    {
        "name": "Segment",
        "category": "Analytics",
        "description": "Customer Data Platform (CDP) routing data to 200+ analytics destinations.",
        "html_patterns": [r"cdn\.segment\.com/analytics\.js", r"analytics\.load\("],
        "header_patterns": [],
    },
    {
        "name": "Hotjar",
        "category": "Analytics",
        "description": "Product experience insights, behavioral heatmaps, and user recordings.",
        "html_patterns": [r"static\.hotjar\.com/c/hotjar-", r"hjid:"],
        "header_patterns": [],
    },
    {
        "name": "Mixpanel",
        "category": "Analytics",
        "description": "Self-serve product analytics for tracking user conversion and retention.",
        "html_patterns": [r"cdn\.mxpnl\.com/libs/mixpanel", r"mixpanel\.init"],
        "header_patterns": [],
    },
    {
        "name": "Datadog RUM",
        "category": "Analytics",
        "description": "Real User Monitoring (RUM) for frontend performance and error tracking.",
        "html_patterns": [r"datadog-rum", r"datadogRum\.init"],
        "header_patterns": [],
    },

    # --- Cloud, Hosting & CDN ---
    {
        "name": "Cloudflare",
        "category": "CDN & Hosting",
        "description": "Global edge cloud network offering CDN, DDoS mitigation, and DNS services.",
        "html_patterns": [r"cdnjs\.cloudflare\.com", r"challenges\.cloudflare\.com/turnstile"],
        "header_patterns": [("server", r"cloudflare"), ("cf-ray", r".+")],
    },
    {
        "name": "Vercel",
        "category": "CDN & Hosting",
        "description": "Frontend cloud platform for developing, previewing, and shipping Jamstack and Next.js sites.",
        "html_patterns": [r"/_vercel/insights", r"/_vercel/speed-insights"],
        "header_patterns": [("server", r"vercel"), ("x-vercel-id", r".+")],
    },
    {
        "name": "Amazon CloudFront (AWS)",
        "category": "CDN & Hosting",
        "description": "Low-latency content delivery network service securely integrated with AWS.",
        "html_patterns": [r"cloudfront\.net"],
        "header_patterns": [("via", r"CloudFront"), ("x-amz-cf-id", r".+")],
    },
    {
        "name": "Fastly",
        "category": "CDN & Hosting",
        "description": "High-performance edge cloud platform and content delivery network.",
        "html_patterns": [],
        "header_patterns": [("x-served-by", r"cache-"), ("fastly-restarts", r".+")],
    },
    {
        "name": "Akamai",
        "category": "CDN & Hosting",
        "description": "Global distributed CDN, cybersecurity, and cloud service provider.",
        "html_patterns": [],
        "header_patterns": [("server", r"Akamai"), ("x-akamai-transformed", r".+")],
    },
    {
        "name": "GitHub Pages",
        "category": "CDN & Hosting",
        "description": "Static site hosting service that takes HTML, CSS, and JavaScript files straight from a repository.",
        "html_patterns": [r"github\.io"],
        "header_patterns": [("server", r"GitHub\.com")],
    },

    # --- Payment Gateways ---
    {
        "name": "Stripe",
        "category": "Payments",
        "description": "Financial infrastructure platform for payments, billing, and fraud prevention.",
        "html_patterns": [r"js\.stripe\.com/v3/", r"Stripe\(['\"]pk_"],
        "header_patterns": [],
    },
    {
        "name": "PayPal",
        "category": "Payments",
        "description": "Global digital payments platform enabling online money transfers.",
        "html_patterns": [r"paypal\.com/sdk/js", r"paypal-button"],
        "header_patterns": [],
    },
    {
        "name": "Klarna",
        "category": "Payments",
        "description": "Buy Now Pay Later (BNPL) and seamless checkout provider.",
        "html_patterns": [r"klarna\.com", r"x-klarna"],
        "header_patterns": [],
    },

    # --- Security & Verification ---
    {
        "name": "Cloudflare Turnstile",
        "category": "Security",
        "description": "Smart, CAPTCHA-free user verification solution.",
        "html_patterns": [r"challenges\.cloudflare\.com/turnstile"],
        "header_patterns": [],
    },
    {
        "name": "Google reCAPTCHA",
        "category": "Security",
        "description": "Risk analysis engine protecting websites from spam and automated abuse.",
        "html_patterns": [r"recaptcha/api\.js", r"grecaptcha"],
        "header_patterns": [],
    },
]


class BuiltWithAdapter:
    """BuiltWith technology profiler adapter with live API support and native zero-cost heuristic fallback."""

    def __init__(self, api_key: str | None = None, mock: bool = False) -> None:
        self.api_key = api_key or settings.BUILTWITH_API_KEY
        self.mock = mock

    async def detect_technologies(
        self,
        url_or_domain: str,
        html_content: str | None = None,
        response_headers: dict[str, str] | None = None,
    ) -> TechStackProfile:
        """Inspect and categorize the technology stack powering the target domain."""
        domain = self._clean_domain(url_or_domain)

        # Mock / Test Mode
        if self.mock or domain in {"test-audit.local", "localhost"} or domain.endswith(".mock.test"):
            return self._generate_mock_profile(domain)

        # Tier 1: BuiltWith API (when key is available)
        if self.api_key:
            try:
                api_profile = await self._query_builtwith_api(domain)
                if api_profile:
                    return api_profile
            except Exception as exc:
                logger.warning("BuiltWith API lookup failed for %s (%s); falling back to native profiler", domain, exc)

        # Tier 2: Native Heuristic Profiler (Zero API key needed)
        return await self._run_native_profiler(url_or_domain, domain, html_content, response_headers)

    def _clean_domain(self, url_or_domain: str) -> str:
        raw = url_or_domain.strip()
        if not raw.startswith("http://") and not raw.startswith("https://"):
            raw = f"https://{raw}"
        try:
            parsed = urlparse(raw)
            return (parsed.hostname or "").lower()
        except Exception:
            return raw.lower()

    async def _query_builtwith_api(self, domain: str) -> TechStackProfile | None:
        """Query BuiltWith Domain API v25."""
        endpoint = f"https://api.builtwith.com/v25/api.json?KEY={self.api_key}&LOOKUP={domain}"
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(endpoint)
            if resp.status_code != 200:
                logger.warning("BuiltWith API returned HTTP %s for %s", resp.status_code, domain)
                return None
            data = resp.json()

        results = data.get("Results", [])
        if not results:
            return None

        result_obj = results[0].get("Result", {})
        paths = result_obj.get("Paths", [])
        meta = result_obj.get("Meta", {})

        tech_items: list[TechnologyItem] = []
        seen = set()

        for path in paths:
            for tech in path.get("Technologies", []):
                name = tech.get("Name")
                if not name or name in seen:
                    continue
                seen.add(name)
                tag = tech.get("Tag", "General")
                tech_items.append(
                    TechnologyItem(
                        name=name,
                        category=tag,
                        description=tech.get("Description", ""),
                        confidence="HIGH",
                        tag=tag,
                    )
                )

        categories: dict[str, list[str]] = {}
        for item in tech_items:
            categories.setdefault(item.category, []).append(item.name)

        spend = meta.get("Spend")
        spend_usd = float(spend) if spend is not None else None

        return TechStackProfile(
            profile_id=f"tech_{uuid.uuid4().hex[:8]}",
            domain=domain,
            detected_technologies=tech_items,
            categories=categories,
            cms=[t.name for t in tech_items if t.category.lower() in {"cms", "ecommerce"}],
            analytics=[t.name for t in tech_items if t.category.lower() in {"analytics", "tracking"}],
            cdn_hosting=[t.name for t in tech_items if t.category.lower() in {"cdn", "hosting"}],
            javascript_frameworks=[t.name for t in tech_items if t.category.lower() in {"framework", "javascript"}],
            payment_processors=[t.name for t in tech_items if t.category.lower() in {"payments"}],
            advertising=[t.name for t in tech_items if t.category.lower() in {"advertising"}],
            third_party_scripts_count=len(tech_items),
            estimated_monthly_spend_usd=spend_usd,
            source="builtwith_api",
        )

    async def _run_native_profiler(
        self,
        target_url: str,
        domain: str,
        html_content: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> TechStackProfile:
        """Detect technologies from live HTML and response headers without external API keys."""
        raw_html = html_content
        raw_headers = {k.lower(): v for k, v in (headers or {}).items()}

        if raw_html is None:
            url = target_url if target_url.startswith("http") else f"https://{target_url}"
            try:
                async with httpx.AsyncClient(
                    timeout=10.0,
                    follow_redirects=True,
                    headers={"User-Agent": "GovernAI-BuiltWith-Profiler/1.0 (+https://governai.local)"},
                ) as client:
                    resp = await client.get(url)
                    raw_html = resp.text
                    raw_headers = {k.lower(): v for k, v in resp.headers.items()}
            except Exception as exc:
                logger.warning("Failed to fetch HTML for native tech profiling on %s: %s", domain, exc)
                raw_html = ""

        detected: list[TechnologyItem] = []
        seen_names = set()

        for sig in TECH_SIGNATURES:
            name = sig["name"]
            matched = False

            # Check HTML patterns
            if raw_html:
                for pattern in sig.get("html_patterns", []):
                    if re.search(pattern, raw_html, re.IGNORECASE):
                        matched = True
                        break

            # Check Header patterns
            if not matched and raw_headers:
                for h_name, h_val_pattern in sig.get("header_patterns", []):
                    val = raw_headers.get(h_name.lower())
                    if val and re.search(h_val_pattern, val, re.IGNORECASE):
                        matched = True
                        break

            if matched and name not in seen_names:
                seen_names.add(name)
                detected.append(
                    TechnologyItem(
                        name=name,
                        category=sig["category"],
                        description=sig["description"],
                        confidence="HIGH",
                        tag=sig["category"],
                    )
                )

        # Count third-party script tags
        script_matches = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', raw_html or "", re.IGNORECASE)
        third_party_scripts = [s for s in script_matches if not s.startswith("/") and domain not in s]

        categories: dict[str, list[str]] = {}
        for item in detected:
            categories.setdefault(item.category, []).append(item.name)

        # Calculate estimated monthly spend based on detected technologies
        spend_map = {
            "Adobe Experience Manager (AEM)": 8500.0,
            "Magento / Adobe Commerce": 3500.0,
            "Shopify": 299.0,
            "Datadog RUM": 450.0,
            "Segment": 350.0,
            "Hotjar": 199.0,
            "Cloudflare": 200.0,
            "Stripe": 150.0,
            "Google Analytics 4 (GA4)": 0.0,
            "Vercel": 150.0,
        }
        est_spend = sum(spend_map.get(t.name, 50.0) for t in detected if t.name in spend_map)

        return TechStackProfile(
            profile_id=f"tech_{uuid.uuid4().hex[:8]}",
            domain=domain,
            detected_technologies=detected,
            categories=categories,
            cms=[t.name for t in detected if t.category == "CMS"],
            analytics=[t.name for t in detected if t.category == "Analytics"],
            cdn_hosting=[t.name for t in detected if t.category == "CDN & Hosting"],
            javascript_frameworks=[t.name for t in detected if t.category == "Framework" or t.category == "JavaScript"],
            payment_processors=[t.name for t in detected if t.category == "Payments"],
            advertising=[t.name for t in detected if t.category == "Advertising"],
            third_party_scripts_count=len(third_party_scripts),
            estimated_monthly_spend_usd=est_spend if detected else 0.0,
            source="native_heuristic",
        )

    def _generate_mock_profile(self, domain: str) -> TechStackProfile:
        """Deterministic mock profile for test suites."""
        mock_techs = [
            TechnologyItem(
                name="Next.js",
                category="Framework",
                description="The React Framework for the Web with hybrid static & server rendering.",
                version="16.3.3",
                confidence="HIGH",
            ),
            TechnologyItem(
                name="React",
                category="Framework",
                description="The library for web and native user interfaces.",
                version="19.0.0",
                confidence="HIGH",
            ),
            TechnologyItem(
                name="Tailwind CSS",
                category="Framework",
                description="Utility-first CSS framework for rapid UI development.",
                confidence="HIGH",
            ),
            TechnologyItem(
                name="Google Analytics 4 (GA4)",
                category="Analytics",
                description="Google's next-generation event-based web and app analytics.",
                confidence="HIGH",
            ),
            TechnologyItem(
                name="Google Tag Manager",
                category="Analytics",
                description="Tag management system for deploying and updating measurement tags.",
                confidence="HIGH",
            ),
            TechnologyItem(
                name="Cloudflare",
                category="CDN & Hosting",
                description="Global edge cloud network offering CDN, DDoS mitigation, and DNS services.",
                confidence="HIGH",
            ),
            TechnologyItem(
                name="Vercel",
                category="CDN & Hosting",
                description="Frontend cloud platform for developing and shipping Jamstack sites.",
                confidence="HIGH",
            ),
            TechnologyItem(
                name="Stripe",
                category="Payments",
                description="Financial infrastructure platform for payments and billing.",
                confidence="HIGH",
            ),
        ]
        categories: dict[str, list[str]] = {}
        for t in mock_techs:
            categories.setdefault(t.category, []).append(t.name)

        return TechStackProfile(
            profile_id=f"tech_mock_{domain.replace('.', '_')}",
            domain=domain,
            detected_technologies=mock_techs,
            categories=categories,
            cms=[],
            analytics=["Google Analytics 4 (GA4)", "Google Tag Manager"],
            cdn_hosting=["Cloudflare", "Vercel"],
            javascript_frameworks=["Next.js", "React"],
            payment_processors=["Stripe"],
            advertising=[],
            third_party_scripts_count=4,
            estimated_monthly_spend_usd=500.0,
            source="mock",
        )
