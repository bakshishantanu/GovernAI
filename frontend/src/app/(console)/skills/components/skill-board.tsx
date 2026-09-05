"use client";

import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api-client";
import { BoardPanel, ViewTabs, ToolbarChip } from "@/components/board/board-panel";
import { ShieldCheck, Users, FlaskConical, Wrench } from "lucide-react";

/**
 * The skill registry.
 *
 * A skill is the unit an agent is built from, and its `required_permissions`
 * are what the agent inherits — so the permissions are the headline on the
 * card, not a footnote. Trust level is the single filled colour per card.
 *
 * Read-only: the registry is populated by the backend's seed script, and
 * there is no create-skill route to build against.
 */

type Tool = { name: string; description: string; required_permission: string };

type Skill = {
  id: string;
  name: string;
  display_name: string;
  description: string;
  version: string;
  trust_level: "VERIFIED" | "COMMUNITY" | "EXPERIMENTAL";
  tools: Tool[];
  required_permissions: string[];
};

const TRUST = {
  VERIFIED: { label: "Verified", fill: "bg-gv-cleared text-gv-cleared-fg", Icon: ShieldCheck },
  COMMUNITY: { label: "Community", fill: "bg-gv-review text-gv-review-fg", Icon: Users },
  EXPERIMENTAL: { label: "Experimental", fill: "bg-gv-watch text-gv-watch-fg", Icon: FlaskConical },
} as const;

function trustOf(level: string) {
  return TRUST[level as keyof typeof TRUST] ?? TRUST.EXPERIMENTAL;
}

export function SkillBoard() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchApi("/skills/")
      .then((data) => {
        if (!cancelled) setSkills(Array.isArray(data) ? data : []);
      })
      .catch((err: any) => {
        if (!cancelled) setError(err.message || "Could not load the skill registry");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const toolCount = skills.reduce((sum, skill) => sum + (skill.tools?.length ?? 0), 0);

  return (
    <>
      <ViewTabs views={[{ name: "Registry", icon: "table" }]} active="Registry" />

      <BoardPanel
        toolbar={
          <>
            <ToolbarChip>{skills.length} skills</ToolbarChip>
            <ToolbarChip>{toolCount} tools</ToolbarChip>
          </>
        }
      >
        {error && (
          <div role="alert" className="px-4 py-6 text-[13px] font-extrabold text-gv-held">
            {error}
          </div>
        )}

        {!error && loading && (
          <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">Loading skills…</p>
        )}

        {!error && !loading && skills.length === 0 && (
          <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">
            The registry is empty. Run the backend seed script to populate it.
          </p>
        )}

        <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-2">
          {skills.map((skill) => {
            const trust = trustOf(skill.trust_level);
            return (
              <article
                key={skill.id}
                className="gv-card flex flex-col overflow-hidden rounded-lg border-2 border-border bg-gv-row"
              >
                <header className="flex h-12 items-center gap-2 border-b-2 border-border px-4">
                  <h2 className="min-w-0 flex-1 truncate font-display text-[19px] leading-none text-gv-ink">
                    {skill.display_name}
                  </h2>
                  <span
                    className={`inline-flex h-[22px] shrink-0 items-center gap-1 rounded border border-border px-1.5 text-[10px] font-extrabold uppercase tracking-[0.06em] ${trust.fill}`}
                  >
                    <trust.Icon className="h-3 w-3" strokeWidth={2.6} aria-hidden="true" />
                    {trust.label}
                  </span>
                </header>

                <div className="flex flex-1 flex-col gap-3 p-4">
                  <p className="text-[13px] font-semibold text-gv-body">{skill.description}</p>

                  <div>
                    <span className="mb-1.5 block text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label">
                      Grants these permissions
                    </span>
                    {skill.required_permissions?.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {skill.required_permissions.map((permission) => (
                          <span
                            key={permission}
                            className="inline-flex h-[22px] items-center rounded-full border-2 border-border bg-gv-lilac px-2.5 font-mono text-[11px] text-gv-ink"
                          >
                            {permission}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[13px] font-semibold text-gv-body">
                        None — this skill cannot reach anything privileged.
                      </p>
                    )}
                  </div>

                  {skill.tools?.length > 0 && (
                    <div>
                      <span className="mb-1.5 block text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label">
                        Tools
                      </span>
                      <ul className="flex flex-col gap-1">
                        {skill.tools.map((tool) => (
                          <li key={tool.name} className="flex items-start gap-2">
                            <Wrench
                              className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gv-muted"
                              strokeWidth={2.4}
                              aria-hidden="true"
                            />
                            <span className="min-w-0 text-[12.5px] font-bold text-foreground">
                              <span className="font-mono text-[12px]">{tool.name}</span>
                              <span className="font-semibold text-gv-muted">
                                {" "}
                                — {tool.description}
                              </span>
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <footer className="mt-auto pt-1 font-mono text-[11px] text-gv-muted">
                    {skill.name} · v{skill.version}
                  </footer>
                </div>
              </article>
            );
          })}
        </div>
      </BoardPanel>
    </>
  );
}
