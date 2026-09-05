"use client";

import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api-client";
import { BoardPanel, ViewTabs } from "@/components/board/board-panel";
import { motion, staggerContainer, staggerItem, useReducedMotion } from "@/components/motion";
import { ThemeToggle } from "@/components/theme-toggle";
import { ShieldAlert, Info } from "lucide-react";

/**
 * Settings — what is configured for this organisation, and what enforces it.
 *
 * Almost all of it is **read-only, and the page says so**. The budget cap and
 * the dev-token bypass are environment values read at startup, so a control
 * here could not write them back. A switch that silently does nothing is
 * worse than no switch, and worst of all on a settings page, which is exactly
 * where someone goes when they want to change something.
 *
 * So each value states where it comes from. "Set in backend/.env" is a real
 * answer; a disabled toggle with no explanation is not.
 */

type Settings = {
  user: { id: string; org_id: string; role: string };
  organization: {
    id: string;
    name: string;
    agent_count: number;
    policy_count: number;
    automation_count: number;
  };
  budget_cap_usd: number;
  budget_window_hours: number;
  dev_token_enabled: boolean;
};

const LABEL = "text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label";

function Card({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <motion.section
      variants={staggerItem}
      className="gv-card overflow-hidden rounded-lg border-2 border-border bg-gv-row"
    >
      <header className="flex h-[38px] items-center gap-2 border-b-2 border-border bg-gv-head px-4">
        <h2 className={LABEL}>{title}</h2>
        {note && (
          <span className="ml-auto font-mono text-[10.5px] text-gv-muted">{note}</span>
        )}
      </header>
      <div className="p-4">{children}</div>
    </motion.section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-gv-rule/30 py-2 last:border-b-0">
      <span className="text-[12.5px] font-bold text-gv-body">{label}</span>
      <span className="min-w-0 text-right">{children}</span>
    </div>
  );
}

const MONO = "font-mono text-[11.5px] text-foreground";

export function SettingsBoard() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const still = useReducedMotion();

  useEffect(() => {
    let cancelled = false;
    fetchApi("/auth/settings")
      .then((data) => {
        if (!cancelled) setSettings(data ?? null);
      })
      .catch((err: any) => {
        if (!cancelled) setError(err.message || "Could not load settings");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <ViewTabs views={[{ name: "Configuration", icon: "overview" }]} active="Configuration" />

      <BoardPanel>
        {error && (
          <div role="alert" className="px-4 py-6 text-[13px] font-extrabold text-gv-held">
            {error}
          </div>
        )}

        {!error && loading && (
          <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">Loading settings…</p>
        )}

        {!error && !loading && settings && (
          <motion.div
            className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-2"
            variants={staggerContainer}
            initial={still ? false : "hidden"}
            animate="shown"
          >
            <Card title="You" note="from your token">
              <Row label="Role">
                <span
                  className={`inline-flex h-[22px] items-center rounded border border-border px-1.5 text-[10px] font-extrabold uppercase tracking-[0.06em] ${
                    settings.user.role === "admin"
                      ? "bg-gv-cleared text-gv-cleared-fg"
                      : "bg-gv-draft text-gv-draft-fg"
                  }`}
                >
                  {settings.user.role}
                </span>
              </Row>
              <Row label="User id">
                <span className={MONO}>{settings.user.id}</span>
              </Row>
              <p className="pt-3 text-[12.5px] font-semibold text-gv-muted">
                Name and email live in Supabase, not in this database, so they are not shown
                here rather than being guessed at.
              </p>
            </Card>

            <Card title="Organisation">
              <Row label="Name">
                <span className="text-[13px] font-extrabold text-foreground">
                  {settings.organization.name}
                </span>
              </Row>
              <Row label="Organisation id">
                <span className={MONO}>{settings.organization.id}</span>
              </Row>
              <Row label="Agents">
                <span className={MONO}>{settings.organization.agent_count}</span>
              </Row>
              <Row label="Policies">
                <span className={MONO}>{settings.organization.policy_count}</span>
              </Row>
              <Row label="Automations">
                <span className={MONO}>{settings.organization.automation_count}</span>
              </Row>
            </Card>

            <Card title="Budget enforcement" note="read-only">
              <Row label="Cap per agent">
                <span className="font-display text-[19px] leading-none text-foreground">
                  ${settings.budget_cap_usd.toFixed(2)}
                </span>
              </Row>
              <Row label="Rolling window">
                <span className={MONO}>{settings.budget_window_hours}h</span>
              </Row>
              {/* Icon and prose are separate flex items; the prose itself is a
                  normal text block. Putting inline <span>s directly into a
                  flex container makes each one its own flex item and the
                  sentence wraps in the wrong places. */}
              <div className="flex items-start gap-2 pt-3">
                <Info
                  className="mt-0.5 h-4 w-4 shrink-0 text-gv-muted"
                  strokeWidth={2.2}
                  aria-hidden="true"
                />
                <p className="text-[12.5px] font-semibold text-gv-muted">
                  Set by <span className="font-mono">AGENT_BUDGET_USD_24H</span> in{" "}
                  <span className="font-mono">backend/.env</span> and read at startup. It
                  applies to every agent; a per-agent cap needs a column that does not exist
                  yet. This is the same value the guard checks before every tool call.
                </p>
              </div>
            </Card>

            <Card title="Appearance">
              <div className="flex items-center justify-between gap-4 py-2">
                <span className="text-[12.5px] font-bold text-gv-body">Theme</span>
                <ThemeToggle />
              </div>
              <p className="pt-3 text-[12.5px] font-semibold text-gv-muted">
                Stored in your browser. The dark palette was derived from the light one and has
                not been reviewed against a design.
              </p>
            </Card>

            {settings.dev_token_enabled && (
              <motion.div variants={staggerItem} className="lg:col-span-2">
                <div
                  role="alert"
                  className="gv-card flex items-start gap-3 rounded-lg border-2 border-gv-held bg-gv-held/10 p-4"
                >
                  <ShieldAlert
                    className="mt-0.5 h-5 w-5 shrink-0 text-gv-held"
                    strokeWidth={2.4}
                    aria-hidden="true"
                  />
                  <div>
                    <h2 className="text-[13px] font-extrabold text-gv-held-fg">
                      The development authentication bypass is switched on
                    </h2>
                    <p className="mt-1 text-[12.5px] font-semibold text-gv-body">
                      <span className="font-mono">AUTH_ALLOW_DEV_TOKEN</span> is true, so the
                      literal token <span className="font-mono">dummy-token</span> is accepted as
                      an administrator. That is correct for local work and must be off anywhere
                      the API can be reached from the internet.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </BoardPanel>
    </>
  );
}
