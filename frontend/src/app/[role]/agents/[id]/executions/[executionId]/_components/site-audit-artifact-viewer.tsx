"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Copy,
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

/** One flattened key from `audit_metadata`, when it holds a real number. */
function flat(artifact: SiteAuditArtifact, key: string): number | undefined {
  const value = (artifact as unknown as Record<string, unknown>)[key];
  return typeof value === "number" ? value : undefined;
}

//: How an absent measurement reads. Deliberately not a score colour: nothing
//: was measured, so nothing should look like a verdict.
const NO_DATA = {
  bg: "rgba(22, 19, 14, 0.05)",
  text: "rgba(22, 19, 14, 0.45)",
  border: "rgba(22, 19, 14, 0.15)",
  label: "No data",
};

function vitalRatingBadge(rating?: string): { bg: string; text: string; label: string } {
  // An unrated vital used to fall through to "Needs Improvement", which reads
  // as a measurement that came back poor rather than one that never arrived.
  if (!rating) {
    return { bg: NO_DATA.bg, text: NO_DATA.text, label: NO_DATA.label };
  }
  const norm = rating.toUpperCase();
  if (norm === "GOOD") {
    return { bg: "rgba(12, 206, 107, 0.15)", text: "#0cce6b", label: "Good" };
  }
  if (norm === "POOR") {
    return { bg: "rgba(255, 78, 66, 0.15)", text: "#ff4e42", label: "Poor" };
  }
  return { bg: "rgba(255, 164, 0, 0.15)", text: "#ffa400", label: "Needs Improvement" };
}

export function SiteAuditArtifactViewer({ artifact }: { artifact: SiteAuditArtifact }) {
  const [activeTab, setActiveTab] = useState<"vitals" | "security" | "seo" | "opportunities" | "crawl">(
    "vitals"
  );
  const [copied, setCopied] = useState(false);

  const targetUrl = artifact.url || artifact.start_url || null;
  const strategy = (artifact.strategy || "mobile").toLowerCase();
  const isMobile = strategy === "mobile";

  // Two shapes reach this viewer and only one of them is nested. The full
  // tool result has `scores`/`vitals`/`seo`/`security`; what actually gets
  // persisted is SiteAuditTool.audit_metadata, which flattens them into
  // `performance_score`, `lcp_ms` and so on. Reading only the nested shape
  // meant `artifact.scores` was always undefined for a real run, and the
  // fallback that used to stand here filled the gap with invented numbers
  // (88/85/92/90) rendered identically to measured ones -- so a page that
  // genuinely scored 40 for best practices displayed 92 "GOOD". In an audit
  // product that is worse than showing nothing, so absent values now stay
  // absent and are rendered as "no data".
  const scores = artifact.scores ?? {
    performance: flat(artifact, "performance_score"),
    accessibility: flat(artifact, "accessibility_score"),
    best_practices: flat(artifact, "best_practices_score"),
    seo: flat(artifact, "seo_score"),
  };

  const vitals =
    artifact.vitals ??
    ({
      lcp_ms: flat(artifact, "lcp_ms"),
      fcp_ms: flat(artifact, "fcp_ms"),
      cls: flat(artifact, "cls"),
      tbt_ms: flat(artifact, "tbt_ms"),
      speed_index_ms: flat(artifact, "speed_index_ms"),
      ttfb_ms: flat(artifact, "ttfb_ms"),
    } as NonNullable<SiteAuditArtifact["vitals"]>);

  const security = artifact.security ?? {};
  const seo = artifact.seo ?? {};
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
          </div>
          <h2 className="landing-display mt-2 text-xl font-bold text-[var(--l-ink)] break-all">
            {targetUrl ?? <span className="text-[var(--l-charcoal)]/45">URL not recorded</span>}
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
          {targetUrl && (
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
          )}
        </div>
      </div>

      {/* 4 Category Score Gauges */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Performance", score: scores.performance, icon: Zap },
          { label: "Accessibility", score: scores.accessibility, icon: Globe },
          { label: "Best Practices", score: scores.best_practices, icon: ShieldCheck },
          { label: "SEO", score: scores.seo, icon: Search },
        ].map((item) => {
          // `?? 0` here used to turn a missing score into a red "Poor 0",
          // which is a verdict this run never reached.
          const colors = item.score === undefined ? NO_DATA : scoreColor(item.score);
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
                {item.score ?? "—"}
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
          { id: "opportunities", label: `Opportunities (${opportunities.length})`, icon: Zap },
          ...(pages.length > 0
            ? [{ id: "crawl", label: `Crawled Pages (${pages.length})`, icon: Layers }]
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
                // `audit_metadata` persists the measurements but not the
                // per-vital ratings, so a real 0.60s LCP arrives with no
                // rating. Labelling that "No data" next to a number that is
                // plainly there reads as a broken card, and deriving a
                // verdict from the thresholds printed below would be
                // inventing one the audit never gave -- so the badge is
                // simply omitted when there is nothing to report.
                const badge = vital.rating ? vitalRatingBadge(vital.rating) : null;
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
                        {badge && (
                          <span
                            className="rounded-full px-2 py-0.5 text-[10px] font-bold"
                            style={{ background: badge.bg, color: badge.text }}
                          >
                            {badge.label}
                          </span>
                        )}
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
                    Security Baseline Score:{" "}
                    {security.score === undefined ? "not recorded" : `${security.score}/100`}
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
