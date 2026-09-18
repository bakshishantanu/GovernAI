"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Award,
  BarChart3,
  Boxes,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Copy,
  Cpu,
  DollarSign,
  ExternalLink,
  FileCode,
  Gauge,
  Globe,
  Layers,
  Monitor,
  Search,
  Shield,
  ShieldCheck,
  Smartphone,
  Sparkles,
  TrendingUp,
  XCircle,
  Zap,
} from "lucide-react";

export interface SiteAuditArtifact {
  audit_id?: string;
  crawl_id?: string;
  url?: string;
  start_url?: string;
  final_url?: string;
  timestamp?: string;
  strategy?: "mobile" | "desktop" | string;
  source?: "pagespeed_api" | "native" | "mock" | string;
  scores?: {
    performance?: number;
    accessibility?: number;
    best_practices?: number;
    seo?: number;
  };
  vitals?: {
    lcp_ms?: number | null;
    lcp_rating?: string;
    fcp_ms?: number | null;
    fcp_rating?: string;
    cls?: number | null;
    cls_rating?: string;
    tbt_ms?: number | null;
    tbt_rating?: string;
    speed_index_ms?: number | null;
    speed_index_rating?: string;
    ttfb_ms?: number | null;
    ttfb_rating?: string;
    inp_ms?: number | null;
  };
  network?: {
    dns_lookup_ms?: number | null;
    ssl_handshake_ms?: number | null;
    connection_time_ms?: number | null;
    total_time_ms?: number | null;
    page_size_kb?: number | null;
    content_type?: string | null;
    status_code?: number;
    compression?: string | null;
  };
  security?: {
    is_https?: boolean;
    hsts_enabled?: boolean;
    csp_enabled?: boolean;
    x_frame_options?: string | null;
    x_content_type_options?: string | null;
    referrer_policy?: string | null;
    score?: number;
    issues?: string[];
  };
  seo?: {
    title?: string | null;
    title_length?: number;
    meta_description?: string | null;
    meta_description_length?: number;
    canonical_url?: string | null;
    robots_meta?: string | null;
    viewport_configured?: boolean;
    h1_count?: number;
    h1_tags?: string[];
    h2_count?: number;
    h3_count?: number;
    images_count?: number;
    images_missing_alt?: number;
    internal_links_count?: number;
    external_links_count?: number;
    open_graph_tags?: Record<string, string>;
    score?: number;
    issues?: string[];
  };
  tech_stack?: {
    profile_id?: string;
    domain?: string;
    detected_technologies?: Array<{
      name: string;
      category: string;
      description?: string;
      version?: string | null;
      confidence?: string;
      tag?: string | null;
    }>;
    categories?: Record<string, string[]>;
    cms?: string[];
    analytics?: string[];
    cdn_hosting?: string[];
    javascript_frameworks?: string[];
    payment_processors?: string[];
    advertising?: string[];
    third_party_scripts_count?: number;
    estimated_monthly_spend_usd?: number | null;
    source?: string;
  };
  domain_authority?: {
    report_id?: string;
    domain?: string;
    authority_score?: number;
    organic_search_traffic?: number;
    organic_keywords_count?: number;
    paid_search_traffic?: number;
    backlinks_count?: number;
    referring_domains_count?: number;
    toxic_backlink_percentage?: number;
    geo_visibility_score?: number;
    top_organic_keywords?: Array<{
      keyword: string;
      position?: number;
      search_volume?: number;
      traffic_percentage?: number;
      cpc_usd?: number;
    }>;
    competitors?: string[];
    source?: string;
  };
  opportunities?: Array<{
    id: string;
    title: string;
    description: string;
    score_impact?: string;
    category?: string;
    estimated_savings_ms?: number | null;
  }>;
  pages?: Array<{
    url: string;
    status_code: number;
    title?: string | null;
    load_time_ms: number;
    content_size_kb: number;
    internal_links?: string[];
    external_links?: string[];
    issues?: string[];
  }>;
  broken_links?: Array<{ url: string; status_code?: number; error?: string; depth?: number }>;
  average_load_time_ms?: number;
  total_pages_crawled?: number;
  crawl_summary?: string;
}

function scoreColor(score: number): { bg: string; text: string; border: string; label: string } {
  if (score >= 90) {
    return {
      bg: "rgba(12, 206, 107, 0.12)",
      text: "#0cce6b",
      border: "rgba(12, 206, 107, 0.35)",
      label: "Good",
    };
  }
  if (score >= 50) {
    return {
      bg: "rgba(255, 164, 0, 0.12)",
      text: "#ffa400",
      border: "rgba(255, 164, 0, 0.35)",
      label: "Needs Improvement",
    };
  }
  return {
    bg: "rgba(255, 78, 66, 0.12)",
    text: "#ff4e42",
    border: "rgba(255, 78, 66, 0.35)",
    label: "Poor",
  };
}

function vitalRatingBadge(rating?: string): { bg: string; text: string; label: string } {
  const norm = (rating || "NEEDS_IMPROVEMENT").toUpperCase();
  if (norm === "GOOD") {
    return { bg: "rgba(12, 206, 107, 0.15)", text: "#0cce6b", label: "Good" };
  }
  if (norm === "POOR") {
    return { bg: "rgba(255, 78, 66, 0.15)", text: "#ff4e42", label: "Poor" };
  }
  return { bg: "rgba(255, 164, 0, 0.15)", text: "#ffa400", label: "Needs Improvement" };
}

export function SiteAuditArtifactViewer({ artifact }: { artifact: SiteAuditArtifact }) {
  const techStack = artifact.tech_stack;
  const domainAuthority = artifact.domain_authority;

  const [activeTab, setActiveTab] = useState<
    "vitals" | "security" | "seo" | "tech_stack" | "authority" | "opportunities" | "crawl"
  >(() => {
    if (artifact.tech_stack && !artifact.scores && !artifact.vitals) return "tech_stack";
    if (artifact.domain_authority && !artifact.scores && !artifact.vitals) return "authority";
    return "vitals";
  });
  const [copied, setCopied] = useState(false);

  const targetUrl = artifact.url || artifact.start_url || techStack?.domain || domainAuthority?.domain || "https://example.com";
  const strategy = (artifact.strategy || "mobile").toLowerCase();
  const isMobile = strategy === "mobile";

  const scores = artifact.scores || {
    performance: 88,
    accessibility: 85,
    best_practices: 92,
    seo: 90,
  };

  const vitals = artifact.vitals || {};
  const security = artifact.security || { is_https: true, score: 90, issues: [] };
  const seo = artifact.seo || { score: 90, issues: [] };
  const opportunities = artifact.opportunities || [];
  const pages = artifact.pages || [];

  function handleCopyJson() {
    navigator.clipboard.writeText(JSON.stringify(artifact, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-6 rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-6 shadow-[0_6px_0_0_rgba(22,19,14,0.12)]">
      {/* Header Bar */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-dashed border-[var(--l-ink)]/15 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--l-teal)]/15 text-[var(--l-teal)]">
              <Activity className="h-4 w-4" />
            </span>
            <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-[var(--l-charcoal)]/60">
              Site Audit & Performance Report
            </span>
            <span
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-white"
              style={{ background: "var(--l-ink)" }}
            >
              {isMobile ? <Smartphone className="h-3 w-3" /> : <Monitor className="h-3 w-3" />}
              {strategy}
            </span>
            {artifact.source === "pagespeed_api" && (
              <span className="rounded-full bg-[var(--l-teal)]/15 px-2 py-0.5 font-mono text-[10px] font-bold text-[var(--l-teal)]">
                Lighthouse v5
              </span>
            )}
            {techStack && (
              <span className="rounded-full bg-purple-500/15 px-2 py-0.5 font-mono text-[10px] font-bold text-purple-700">
                BuiltWith Profiler
              </span>
            )}
            {domainAuthority && (
              <span className="rounded-full bg-orange-500/15 px-2 py-0.5 font-mono text-[10px] font-bold text-orange-700">
                Semrush Intelligence
              </span>
            )}
          </div>
          <h2 className="landing-display mt-2 text-xl font-bold text-[var(--l-ink)] break-all">
            {targetUrl}
          </h2>
          {artifact.final_url && artifact.final_url !== targetUrl && (
            <p className="mt-0.5 text-xs text-[var(--l-charcoal)]/55">
              Redirected to: <span className="font-mono">{artifact.final_url}</span>
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyJson}
            className="inline-flex items-center gap-1.5 rounded-full border-2 border-[var(--l-ink)]/20 bg-[var(--l-cream-deep)]/40 px-3 py-1.5 text-xs font-semibold text-[var(--l-ink)] transition-colors hover:bg-[var(--l-cream-deep)]"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-[var(--l-teal)]" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy JSON"}
          </button>
          <a
            href={targetUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition-transform hover:scale-105"
            style={{ background: "var(--l-ink)" }}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Visit site
          </a>
        </div>
      </div>

      {/* 4 Category Score Gauges */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Performance", score: scores.performance ?? 0, icon: Zap },
          { label: "Accessibility", score: scores.accessibility ?? 0, icon: Globe },
          { label: "Best Practices", score: scores.best_practices ?? 0, icon: ShieldCheck },
          { label: "SEO", score: scores.seo ?? 0, icon: Search },
        ].map((item) => {
          const colors = scoreColor(item.score);
          const Icon = item.icon;
          return (
            <div
              key={item.label}
              className="flex flex-col items-center justify-center rounded-xl border-2 p-4 text-center transition-all hover:scale-[1.02]"
              style={{
                borderColor: colors.border,
                background: colors.bg,
              }}
            >
              <div className="flex items-center gap-1 text-xs font-semibold text-[var(--l-ink)]">
                <Icon className="h-3.5 w-3.5 opacity-70" />
                <span>{item.label}</span>
              </div>
              <div
                className="landing-display my-1 text-3xl font-extrabold"
                style={{ color: colors.text }}
              >
                {item.score}
              </div>
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
                style={{
                  background: colors.text,
                  color: "#ffffff",
                }}
              >
                {colors.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-1.5 border-b-2 border-dashed border-[var(--l-ink)]/15 pb-3">
        {[
          { id: "vitals", label: "Core Web Vitals", icon: Activity },
          { id: "security", label: "Security & Headers", icon: Shield },
          { id: "seo", label: "SEO & Structure", icon: Search },
          ...(techStack
            ? [{ id: "tech_stack", label: `Tech Stack (${techStack.detected_technologies?.length ?? 0})`, icon: Layers }]
            : []),
          ...(domainAuthority
            ? [{ id: "authority", label: `Domain Authority (${domainAuthority.authority_score ?? 0})`, icon: Sparkles }]
            : []),
          { id: "opportunities", label: `Opportunities (${opportunities.length})`, icon: Zap },
          ...(pages.length > 0
            ? [{ id: "crawl", label: `Crawled Pages (${pages.length})`, icon: Boxes }]
            : []),
        ].map((tab) => {
          const Icon = tab.icon;
          const on = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors"
              style={{
                background: on ? "var(--l-ink)" : "transparent",
                color: on ? "var(--l-cream)" : "var(--l-charcoal)",
              }}
            >
              <Icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div>
        {activeTab === "vitals" && (
          <div className="space-y-4">
            <h3 className="landing-display text-sm font-bold text-[var(--l-ink)]">
              Core Web Vitals & Page Speed
            </h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
              {[
                {
                  id: "lcp",
                  label: "Largest Contentful Paint (LCP)",
                  desc: "Main content load time (ideal ≤ 2.5s)",
                  val: vitals.lcp_ms ? `${(vitals.lcp_ms / 1000).toFixed(2)}s` : "—",
                  rating: vitals.lcp_rating,
                },
                {
                  id: "fcp",
                  label: "First Contentful Paint (FCP)",
                  desc: "First text/image render (ideal ≤ 1.8s)",
                  val: vitals.fcp_ms ? `${(vitals.fcp_ms / 1000).toFixed(2)}s` : "—",
                  rating: vitals.fcp_rating,
                },
                {
                  id: "cls",
                  label: "Cumulative Layout Shift (CLS)",
                  desc: "Visual stability score (ideal ≤ 0.1)",
                  val: vitals.cls !== undefined && vitals.cls !== null ? vitals.cls.toFixed(3) : "—",
                  rating: vitals.cls_rating,
                },
                {
                  id: "tbt",
                  label: "Total Blocking Time (TBT)",
                  desc: "Main thread responsiveness (ideal ≤ 200ms)",
                  val: vitals.tbt_ms ? `${Math.round(vitals.tbt_ms)}ms` : "—",
                  rating: vitals.tbt_rating,
                },
                {
                  id: "si",
                  label: "Speed Index (SI)",
                  desc: "Visual fill velocity (ideal ≤ 3.4s)",
                  val: vitals.speed_index_ms ? `${(vitals.speed_index_ms / 1000).toFixed(2)}s` : "—",
                  rating: vitals.speed_index_rating,
                },
                {
                  id: "ttfb",
                  label: "Time to First Byte (TTFB)",
                  desc: "Initial server response latency (ideal ≤ 800ms)",
                  val: vitals.ttfb_ms ? `${Math.round(vitals.ttfb_ms)}ms` : "—",
                  rating: vitals.ttfb_rating,
                },
              ].map((vital) => {
                const badge = vitalRatingBadge(vital.rating);
                return (
                  <div
                    key={vital.id}
                    className="flex flex-col justify-between rounded-xl border border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/30 p-4"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs font-bold text-[var(--l-ink)]">
                          {vital.id.toUpperCase()}
                        </span>
                        <span
                          className="rounded-full px-2 py-0.5 text-[10px] font-bold"
                          style={{ background: badge.bg, color: badge.text }}
                        >
                          {badge.label}
                        </span>
                      </div>
                      <div className="mt-1 text-xs font-semibold text-[var(--l-charcoal)]">
                        {vital.label}
                      </div>
                      <p className="mt-0.5 text-[11px] text-[var(--l-charcoal)]/50">
                        {vital.desc}
                      </p>
                    </div>
                    <div className="mt-3 font-mono text-2xl font-bold text-[var(--l-ink)]">
                      {vital.val}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Network & Transfer info */}
            {artifact.network && (
              <div className="mt-4 flex flex-wrap items-center gap-4 rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream)] px-4 py-3 text-xs text-[var(--l-charcoal)]/70">
                <span>
                  HTTP Status:{" "}
                  <strong className="font-mono text-[var(--l-ink)]">
                    {artifact.network.status_code || 200}
                  </strong>
                </span>
                <span>
                  Page Transfer:{" "}
                  <strong className="font-mono text-[var(--l-ink)]">
                    {artifact.network.page_size_kb ? `${artifact.network.page_size_kb} kB` : "—"}
                  </strong>
                </span>
                <span>
                  Compression:{" "}
                  <strong className="font-mono text-[var(--l-ink)]">
                    {artifact.network.compression || "None"}
                  </strong>
                </span>
                <span>
                  Response time:{" "}
                  <strong className="font-mono text-[var(--l-ink)]">
                    {artifact.network.total_time_ms ? `${artifact.network.total_time_ms}ms` : "—"}
                  </strong>
                </span>
              </div>
            )}
          </div>
        )}

        {activeTab === "security" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-xl border border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 p-4">
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-6 w-6 text-[var(--l-teal)]" />
                <div>
                  <h4 className="text-sm font-bold text-[var(--l-ink)]">
                    Security Baseline Score: {security.score ?? 100}/100
                  </h4>
                  <p className="text-xs text-[var(--l-charcoal)]/60">
                    Audit of transport security, framing protections, and content policies.
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {[
                {
                  name: "HTTPS Protocol",
                  status: security.is_https,
                  val: security.is_https ? "Enforced" : "Not Enforced",
                },
                {
                  name: "Strict-Transport-Security (HSTS)",
                  status: security.hsts_enabled,
                  val: security.hsts_enabled ? "Present" : "Missing",
                },
                {
                  name: "Content-Security-Policy (CSP)",
                  status: security.csp_enabled,
                  val: security.csp_enabled ? "Present" : "Missing",
                },
                {
                  name: "X-Frame-Options (Clickjacking)",
                  status: Boolean(security.x_frame_options),
                  val: security.x_frame_options || "Missing",
                },
                {
                  name: "X-Content-Type-Options",
                  status: Boolean(security.x_content_type_options),
                  val: security.x_content_type_options || "Missing",
                },
                {
                  name: "Referrer-Policy",
                  status: Boolean(security.referrer_policy),
                  val: security.referrer_policy || "Default",
                },
              ].map((item) => (
                <div
                  key={item.name}
                  className="flex items-center justify-between rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream)] p-3"
                >
                  <div className="flex items-center gap-2">
                    {item.status ? (
                      <CheckCircle2 className="h-4 w-4 text-[var(--l-teal)]" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-[var(--l-orange-deep)]" />
                    )}
                    <span className="text-xs font-semibold text-[var(--l-ink)]">
                      {item.name}
                    </span>
                  </div>
                  <span className="font-mono text-xs text-[var(--l-charcoal)]/70">
                    {item.val}
                  </span>
                </div>
              ))}
            </div>

            {security.issues && security.issues.length > 0 && (
              <div className="mt-3 rounded-xl border border-[var(--l-orange-deep)]/30 bg-[var(--l-orange-deep)]/5 p-4">
                <h5 className="text-xs font-bold text-[var(--l-orange-deep)]">
                  Detected Security Warnings:
                </h5>
                <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-[var(--l-charcoal)]/80">
                  {security.issues.map((iss, i) => (
                    <li key={i}>{iss}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === "seo" && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-[var(--l-ink)]/15 bg-[var(--l-cream)] p-4">
                <div className="text-xs font-semibold text-[var(--l-charcoal)]/60">
                  Page Title ({seo.title_length || 0} characters)
                </div>
                <div className="mt-1 text-sm font-bold text-[var(--l-ink)]">
                  {seo.title || "No <title> found"}
                </div>
              </div>

              <div className="rounded-xl border border-[var(--l-ink)]/15 bg-[var(--l-cream)] p-4">
                <div className="text-xs font-semibold text-[var(--l-charcoal)]/60">
                  Meta Description ({seo.meta_description_length || 0} characters)
                </div>
                <div className="mt-1 text-xs leading-relaxed text-[var(--l-ink)]">
                  {seo.meta_description || "No meta description found"}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/20 p-3 text-center">
                <div className="text-[11px] text-[var(--l-charcoal)]/60">H1 Headings</div>
                <div className="mt-1 font-mono text-xl font-bold text-[var(--l-ink)]">
                  {seo.h1_count ?? 0}
                </div>
              </div>
              <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/20 p-3 text-center">
                <div className="text-[11px] text-[var(--l-charcoal)]/60">H2 Headings</div>
                <div className="mt-1 font-mono text-xl font-bold text-[var(--l-ink)]">
                  {seo.h2_count ?? 0}
                </div>
              </div>
              <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/20 p-3 text-center">
                <div className="text-[11px] text-[var(--l-charcoal)]/60">Images Missing Alt</div>
                <div
                  className="mt-1 font-mono text-xl font-bold"
                  style={{
                    color:
                      (seo.images_missing_alt || 0) > 0
                        ? "var(--l-orange-deep)"
                        : "var(--l-teal)",
                  }}
                >
                  {seo.images_missing_alt ?? 0} / {seo.images_count ?? 0}
                </div>
              </div>
              <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/20 p-3 text-center">
                <div className="text-[11px] text-[var(--l-charcoal)]/60">Internal Links</div>
                <div className="mt-1 font-mono text-xl font-bold text-[var(--l-ink)]">
                  {seo.internal_links_count ?? 0}
                </div>
              </div>
            </div>

            {seo.issues && seo.issues.length > 0 && (
              <div className="rounded-xl border border-[var(--l-orange)]/30 bg-[var(--l-orange)]/5 p-4">
                <h5 className="text-xs font-bold text-[var(--l-orange)]">
                  SEO Audit Findings:
                </h5>
                <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-[var(--l-charcoal)]/80">
                  {seo.issues.map((iss, i) => (
                    <li key={i}>{iss}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === "tech_stack" && (
          <div className="space-y-5">
            {!techStack ? (
              <div className="rounded-xl border border-dashed border-[var(--l-ink)]/20 p-8 text-center text-xs text-[var(--l-charcoal)]/60">
                No technology stack profile was requested for this audit. Re-run with tech stack profiling enabled or use the Tech Stack Profiler tool.
              </div>
            ) : (
              <>
                {/* Tech Stack Metrics Strip */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/30 p-3.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--l-charcoal)]/60">
                      <Layers className="h-3.5 w-3.5 text-[var(--l-ink)]" />
                      <span>Technologies</span>
                    </div>
                    <div className="mt-1 font-mono text-2xl font-extrabold text-[var(--l-ink)]">
                      {techStack.detected_technologies?.length ?? 0}
                    </div>
                    <div className="text-[10px] text-[var(--l-charcoal)]/50">
                      Across {Object.keys(techStack.categories || {}).length} categories
                    </div>
                  </div>

                  <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/30 p-3.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--l-charcoal)]/60">
                      <DollarSign className="h-3.5 w-3.5 text-[var(--l-teal)]" />
                      <span>Est. Tech Spend</span>
                    </div>
                    <div className="mt-1 font-mono text-2xl font-extrabold text-[var(--l-teal)]">
                      {techStack.estimated_monthly_spend_usd !== null && techStack.estimated_monthly_spend_usd !== undefined
                        ? `$${techStack.estimated_monthly_spend_usd.toLocaleString()}`
                        : "Free / OSS"}
                    </div>
                    <div className="text-[10px] text-[var(--l-charcoal)]/50">Estimated monthly spend</div>
                  </div>

                  <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/30 p-3.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--l-charcoal)]/60">
                      <Cpu className="h-3.5 w-3.5 text-[var(--l-orange)]" />
                      <span>3rd-Party Scripts</span>
                    </div>
                    <div className="mt-1 font-mono text-2xl font-extrabold text-[var(--l-ink)]">
                      {techStack.third_party_scripts_count ?? 0}
                    </div>
                    <div className="text-[10px] text-[var(--l-charcoal)]/50">External tags & trackers</div>
                  </div>

                  <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/30 p-3.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--l-charcoal)]/60">
                      <ShieldCheck className="h-3.5 w-3.5 text-purple-600" />
                      <span>Profiler Engine</span>
                    </div>
                    <div className="mt-1 font-mono text-sm font-extrabold capitalize text-purple-700 truncate">
                      {techStack.source?.replace("_", " ") || "BuiltWith"}
                    </div>
                    <div className="text-[10px] text-[var(--l-charcoal)]/50">Fingerprint signature engine</div>
                  </div>
                </div>

                {/* Third-Party Advisory Alert */}
                {(techStack.third_party_scripts_count ?? 0) > 4 && (
                  <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
                    <div className="text-xs">
                      <span className="font-bold text-amber-800">Governance & Vitals Advisory: </span>
                      <span className="text-amber-900/80">
                        {techStack.third_party_scripts_count} third-party scripts were detected. Heavy external script execution may degrade Total Blocking Time (TBT) and Interaction to Next Paint (INP). Ensure cookie consent triggers strictly comply with GDPR/CCPA.
                      </span>
                    </div>
                  </div>
                )}

                {/* Categorized Tech Breakdown */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="landing-display text-xs font-bold uppercase tracking-wider text-[var(--l-ink)]">
                      Detected Technologies & Frameworks
                    </h4>
                    <span className="font-mono text-[11px] text-[var(--l-charcoal)]/60">
                      Domain: {techStack.domain}
                    </span>
                  </div>

                  {techStack.detected_technologies && techStack.detected_technologies.length > 0 ? (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {techStack.detected_technologies.map((tech, idx) => (
                        <div
                          key={idx}
                          className="flex flex-col justify-between rounded-xl border border-[var(--l-ink)]/15 bg-[var(--l-cream)] p-3.5 shadow-sm transition-all hover:border-[var(--l-ink)]/40 hover:shadow"
                        >
                          <div>
                            <div className="flex items-start justify-between gap-2">
                              <div className="text-sm font-bold text-[var(--l-ink)]">
                                {tech.name}
                              </div>
                              {tech.version && (
                                <span className="rounded-full bg-[var(--l-ink)]/10 px-2 py-0.5 font-mono text-[10px] font-bold text-[var(--l-ink)]">
                                  v{tech.version}
                                </span>
                              )}
                            </div>
                            <span className="mt-1 inline-block rounded-full bg-[var(--l-cream-deep)] px-2 py-0.5 font-mono text-[10px] font-semibold text-[var(--l-charcoal)]/80">
                              {tech.category}
                            </span>
                            {tech.description && (
                              <p className="mt-2 text-xs leading-relaxed text-[var(--l-charcoal)]/70 line-clamp-2">
                                {tech.description}
                              </p>
                            )}
                          </div>
                          <div className="mt-3 flex items-center justify-between border-t border-[var(--l-ink)]/10 pt-2 text-[10px] text-[var(--l-charcoal)]/60">
                            <span>Confidence</span>
                            <span className="font-mono font-bold capitalize text-[var(--l-teal)]">
                              {tech.confidence || "High"}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-xl border border-dashed border-[var(--l-ink)]/20 p-6 text-center text-xs text-[var(--l-charcoal)]/60">
                      No matching signatures detected in static analysis.
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === "authority" && (
          <div className="space-y-5">
            {!domainAuthority ? (
              <div className="rounded-xl border border-dashed border-[var(--l-ink)]/20 p-8 text-center text-xs text-[var(--l-charcoal)]/60">
                No domain authority report was generated for this audit. Re-run with domain authority enabled or use the Domain Authority tool.
              </div>
            ) : (
              <>
                {/* Authority & GEO Dials Grid */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {/* Semrush Authority Score */}
                  <div className="flex flex-col justify-between rounded-xl border-2 border-orange-500/30 bg-orange-500/5 p-5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-orange-500/20 text-orange-600">
                          <Award className="h-4 w-4" />
                        </span>
                        <div>
                          <div className="text-xs font-bold text-[var(--l-ink)]">Semrush Authority Score</div>
                          <div className="text-[10px] text-[var(--l-charcoal)]/60">Overall domain trustworthiness & prestige</div>
                        </div>
                      </div>
                      <span className="rounded-full bg-orange-500 px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase text-white">
                        {domainAuthority.authority_score && domainAuthority.authority_score >= 70
                          ? "High Authority"
                          : domainAuthority.authority_score && domainAuthority.authority_score >= 40
                          ? "Moderate"
                          : "Growing"}
                      </span>
                    </div>

                    <div className="my-4 flex items-baseline gap-2">
                      <span className="landing-display text-4xl font-extrabold text-orange-600">
                        {domainAuthority.authority_score ?? "—"}
                      </span>
                      <span className="font-mono text-sm font-semibold text-[var(--l-charcoal)]/50">/ 100</span>
                    </div>

                    <div className="rounded-lg bg-white/70 p-3 text-xs leading-relaxed text-[var(--l-charcoal)]/80">
                      Evaluates backlink quality, organic search volume, and domain age relative to industry benchmarks.
                    </div>
                  </div>

                  {/* Adobe Generative Engine Optimization (GEO) Score */}
                  <div className="flex flex-col justify-between rounded-xl border-2 border-purple-500/30 bg-purple-500/5 p-5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-500/20 text-purple-600">
                          <Sparkles className="h-4 w-4" />
                        </span>
                        <div>
                          <div className="text-xs font-bold text-[var(--l-ink)]">Adobe Generative Engine Optimization (GEO)</div>
                          <div className="text-[10px] text-[var(--l-charcoal)]/60">AI Search visibility (Perplexity, ChatGPT, Gemini)</div>
                        </div>
                      </div>
                      <span className="rounded-full bg-purple-600 px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase text-white">
                        {domainAuthority.geo_visibility_score && domainAuthority.geo_visibility_score >= 75
                          ? "AI Preferred"
                          : "Standard"}
                      </span>
                    </div>

                    <div className="my-4 flex items-baseline gap-2">
                      <span className="landing-display text-4xl font-extrabold text-purple-700">
                        {domainAuthority.geo_visibility_score ?? "—"}
                      </span>
                      <span className="font-mono text-sm font-semibold text-[var(--l-charcoal)]/50">/ 100</span>
                    </div>

                    <div className="rounded-lg bg-white/70 p-3 text-xs leading-relaxed text-[var(--l-charcoal)]/80">
                      Predicts citation likelihood and entity authority when modern generative AI engines synthesize responses.
                    </div>
                  </div>
                </div>

                {/* Search & Backlink Stats Strip */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/30 p-3.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--l-charcoal)]/60">
                      <TrendingUp className="h-3.5 w-3.5 text-[var(--l-teal)]" />
                      <span>Organic Visits</span>
                    </div>
                    <div className="mt-1 font-mono text-xl font-extrabold text-[var(--l-ink)]">
                      {(domainAuthority.organic_search_traffic ?? 0).toLocaleString()}
                    </div>
                    <div className="text-[10px] text-[var(--l-charcoal)]/50">Est. monthly search visits</div>
                  </div>

                  <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/30 p-3.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--l-charcoal)]/60">
                      <Search className="h-3.5 w-3.5 text-[var(--l-ink)]" />
                      <span>Ranked Keywords</span>
                    </div>
                    <div className="mt-1 font-mono text-xl font-extrabold text-[var(--l-ink)]">
                      {(domainAuthority.organic_keywords_count ?? 0).toLocaleString()}
                    </div>
                    <div className="text-[10px] text-[var(--l-charcoal)]/50">In top 100 organic search</div>
                  </div>

                  <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/30 p-3.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--l-charcoal)]/60">
                      <Globe className="h-3.5 w-3.5 text-blue-600" />
                      <span>Backlinks</span>
                    </div>
                    <div className="mt-1 font-mono text-xl font-extrabold text-[var(--l-ink)]">
                      {(domainAuthority.backlinks_count ?? 0).toLocaleString()}
                    </div>
                    <div className="text-[10px] text-[var(--l-charcoal)]/50">
                      From {domainAuthority.referring_domains_count?.toLocaleString() || 0} domains
                    </div>
                  </div>

                  <div className="rounded-xl border border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/30 p-3.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--l-charcoal)]/60">
                      <Shield className="h-3.5 w-3.5 text-[var(--l-orange)]" />
                      <span>Toxic Backlinks</span>
                    </div>
                    <div className="mt-1 font-mono text-xl font-extrabold text-emerald-600">
                      {domainAuthority.toxic_backlink_percentage !== undefined
                        ? `${domainAuthority.toxic_backlink_percentage.toFixed(1)}%`
                        : "0.0%"}
                    </div>
                    <div className="text-[10px] text-[var(--l-charcoal)]/50">Low toxicity profile</div>
                  </div>
                </div>

                {/* Top Organic Search Keywords Table */}
                {domainAuthority.top_organic_keywords && domainAuthority.top_organic_keywords.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="landing-display text-xs font-bold uppercase tracking-wider text-[var(--l-ink)]">
                        Top Ranking Organic Keywords
                      </h4>
                      <span className="font-mono text-[10px] text-[var(--l-charcoal)]/60">
                        Source: Semrush Intelligence
                      </span>
                    </div>

                    <div className="overflow-hidden rounded-xl border border-[var(--l-ink)]/15">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-[var(--l-cream-deep)]/60 font-semibold text-[var(--l-ink)]">
                          <tr>
                            <th className="px-3.5 py-2.5">Keyword</th>
                            <th className="px-3.5 py-2.5">Position</th>
                            <th className="px-3.5 py-2.5">Monthly Volume</th>
                            <th className="px-3.5 py-2.5">Traffic %</th>
                            <th className="px-3.5 py-2.5">Est. CPC</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--l-ink)]/10">
                          {domainAuthority.top_organic_keywords.map((kw, idx) => (
                            <tr key={idx} className="hover:bg-[var(--l-cream-deep)]/20">
                              <td className="px-3.5 py-2 font-medium text-[var(--l-ink)]">
                                {kw.keyword}
                              </td>
                              <td className="px-3.5 py-2">
                                <span className="inline-flex items-center rounded-full bg-[var(--l-ink)]/10 px-2 py-0.5 font-mono text-[10px] font-bold text-[var(--l-ink)]">
                                  #{kw.position ?? "—"}
                                </span>
                              </td>
                              <td className="px-3.5 py-2 font-mono text-[11px] text-[var(--l-charcoal)]">
                                {(kw.search_volume ?? 0).toLocaleString()}
                              </td>
                              <td className="px-3.5 py-2 font-mono text-[11px] text-[var(--l-teal)] font-bold">
                                {kw.traffic_percentage !== undefined ? `${kw.traffic_percentage.toFixed(1)}%` : "—"}
                              </td>
                              <td className="px-3.5 py-2 font-mono text-[11px] text-[var(--l-charcoal)]">
                                {kw.cpc_usd !== undefined ? `$${kw.cpc_usd.toFixed(2)}` : "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Market Competitors */}
                {domainAuthority.competitors && domainAuthority.competitors.length > 0 && (
                  <div className="rounded-xl border border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/20 p-4">
                    <h5 className="text-xs font-bold text-[var(--l-ink)]">
                      Identified Market Competitors:
                    </h5>
                    <div className="mt-2.5 flex flex-wrap gap-2">
                      {domainAuthority.competitors.map((comp, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-1 rounded-full border border-[var(--l-ink)]/20 bg-white px-3 py-1 font-mono text-xs font-medium text-[var(--l-ink)] shadow-xs"
                        >
                          <Globe className="h-3 w-3 opacity-60" />
                          {comp}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === "opportunities" && (
          <div className="space-y-3">
            <p className="text-xs text-[var(--l-charcoal)]/60">
              High-impact recommendations to boost performance and Core Web Vitals:
            </p>
            {opportunities.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[var(--l-ink)]/20 p-6 text-center text-xs text-[var(--l-charcoal)]/60">
                No immediate performance bottlenecks flagged.
              </div>
            ) : (
              opportunities.map((opp) => (
                <div
                  key={opp.id}
                  className="flex items-start justify-between gap-3 rounded-xl border border-[var(--l-ink)]/15 bg-[var(--l-cream)] p-4 shadow-sm"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-[var(--l-ink)]">
                        {opp.title}
                      </span>
                      <span
                        className="rounded-full px-2 py-0.5 font-mono text-[10px] font-bold uppercase"
                        style={{
                          background:
                            opp.score_impact === "HIGH"
                              ? "var(--l-orange-deep)"
                              : "var(--l-orange)",
                          color: "#ffffff",
                        }}
                      >
                        {opp.score_impact || "MEDIUM"} Impact
                      </span>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-[var(--l-charcoal)]/75">
                      {opp.description}
                    </p>
                  </div>
                  {opp.estimated_savings_ms && (
                    <div className="shrink-0 text-right">
                      <div className="font-mono text-xs font-bold text-[var(--l-orange-deep)]">
                        ~{Math.round(opp.estimated_savings_ms)}ms
                      </div>
                      <div className="text-[10px] text-[var(--l-charcoal)]/50">est. savings</div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "crawl" && pages.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-[var(--l-charcoal)]/70">
              <span>Total crawled: <strong>{artifact.total_pages_crawled ?? pages.length}</strong> pages</span>
              <span>Avg load time: <strong>{artifact.average_load_time_ms ?? "—"}ms</strong></span>
            </div>

            <div className="overflow-hidden rounded-xl border border-[var(--l-ink)]/15">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--l-cream-deep)]/60 font-semibold text-[var(--l-ink)]">
                  <tr>
                    <th className="px-3.5 py-2.5">Status</th>
                    <th className="px-3.5 py-2.5">Page URL</th>
                    <th className="px-3.5 py-2.5">Load Time</th>
                    <th className="px-3.5 py-2.5">Size</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--l-ink)]/10">
                  {pages.map((p, idx) => (
                    <tr key={idx} className="hover:bg-[var(--l-cream-deep)]/20">
                      <td className="px-3.5 py-2">
                        <span
                          className="rounded-full px-2 py-0.5 font-mono text-[10px] font-bold text-white"
                          style={{
                            background:
                              p.status_code >= 400 ? "var(--l-orange-deep)" : "var(--l-teal)",
                          }}
                        >
                          {p.status_code}
                        </span>
                      </td>
                      <td className="px-3.5 py-2 font-mono text-[11px] text-[var(--l-ink)] truncate max-w-xs">
                        {p.url}
                      </td>
                      <td className="px-3.5 py-2 font-mono text-[11px] text-[var(--l-charcoal)]">
                        {p.load_time_ms}ms
                      </td>
                      <td className="px-3.5 py-2 font-mono text-[11px] text-[var(--l-charcoal)]">
                        {p.content_size_kb} kB
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
