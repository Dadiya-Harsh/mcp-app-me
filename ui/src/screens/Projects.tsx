import { useEffect, useState } from "react";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import type { HostActions } from "../host";
import type { Project, ProjectGroup, ProjectsData } from "../types";

type Filter = "all" | ProjectGroup;

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "recent", label: "Recent" },
  { id: "openSource", label: "Open source" },
  { id: "earlier", label: "Earlier" },
];
const TAG: Record<ProjectGroup, string> = { recent: "Recent", openSource: "Open source", earlier: "Earlier" };
const ORDER: ProjectGroup[] = ["recent", "openSource", "earlier"];

export function Projects({ data, host }: { data: ProjectsData; host: HostActions }) {
  const [shown, setShown] = useState<ProjectsData>(data);
  const [filter, setFilter] = useState<Filter>(data.group);
  // If the model asked for one group, the others are fetched here so the counts are right.
  const [loadingAll, setLoadingAll] = useState(data.group !== "all");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (data.group === "all") return;
    let live = true;
    host
      .callTool("list_projects", { group: "all" })
      .then((r) => {
        if (!live) return;
        if (r.isError || !r.structuredContent) throw new Error("no data");
        setShown(r.structuredContent as ProjectsData);
      })
      .catch(() => live && setFailed(true))
      .finally(() => live && setLoadingAll(false));
    return () => {
      live = false;
    };
  }, [data.group, host]);

  useEffect(() => {
    const label = FILTERS.find((f) => f.id === filter)?.label ?? "All";
    host.updateContext(`The visitor is looking at Harsh's projects, filter: ${label}.`);
  }, [filter, host]);

  const count = (id: Filter) => (id === "all" ? ORDER.flatMap((g) => shown.projects[g]).length : shown.projects[id].length);
  const knownCounts = !loadingAll && !failed;
  const groups = filter === "all" ? ORDER : [filter];
  const items: { group: ProjectGroup; project: Project }[] = groups.flatMap((g) =>
    shown.projects[g].map((project) => ({ group: g, project })),
  );
  // Until the other groups arrive only the group the model asked for has anything in it.
  const waiting = loadingAll && filter !== data.group && data.group !== "all" && items.length === 0;

  const allOnSite = shown.siteUrl ? `${shown.siteUrl.replace(/\/$/, "")}/projects` : undefined;

  return (
    <Card>
      <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 18 }}>
        <div className="panel-head">
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span className="eyebrow">Projects</span>
            <h1 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>Projects &amp; code</h1>
          </div>
          {allOnSite && (
            <Button variant="link" href={allOnSite} onOpen={host.openLink}>
              All on site
            </Button>
          )}
        </div>

        <div className="filters" role="group" aria-label="Filter projects">
          {FILTERS.map((f) => (
            <button key={f.id} type="button" className="filter" aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}>
              {knownCounts ? `${f.label} · ${count(f.id)}` : f.label}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }} aria-live="polite">
          {waiting && <p className="hint">Loading…</p>}
          {!waiting && items.length === 0 && <p className="hint">Nothing in this group.</p>}
          {failed && (
            <p role="status" className="hint">
              Couldn't load the other groups. Ask your assistant: "Show all of Harsh's projects".
            </p>
          )}
          {items.map(({ group, project }) => (
            <article
              key={`${group}-${project.title}`}
              style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-tile)", padding: "16px 18px", display: "flex", flexDirection: "column", gap: 8 }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span className="pill pill-plain">{TAG[group]}</span>
                <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>{project.title}</h2>
              </div>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: "var(--text-soft)" }}>{project.description}</p>
              {project.links.length > 0 && (
                <div style={{ display: "flex", gap: "0 16px", flexWrap: "wrap" }}>
                  {project.links.map((l) => (
                    <Button key={l.url} variant="link" href={l.url} onOpen={host.openLink}>
                      {l.label}
                    </Button>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      </div>
      <div className="foot">From harshdadiya.in</div>
    </Card>
  );
}
