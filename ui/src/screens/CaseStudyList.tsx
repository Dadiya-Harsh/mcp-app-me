import { useEffect } from "react";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import type { HostActions } from "../host";
import type { CaseStudyMeta } from "../types";

type Props = {
  studies: CaseStudyMeta[];
  siteUrl?: string;
  host: HostActions;
  onOpen: (id: string) => void;
  /** Set when the visitor came from the profile card. */
  onBackToProfile?: () => void;
};

export function CaseStudyList({ studies, siteUrl, host, onOpen, onBackToProfile }: Props) {
  useEffect(() => {
    host.updateContext("The visitor is looking at the list of Harsh's case studies.");
  }, [host]);

  const allOnSite = siteUrl ? `${siteUrl.replace(/\/$/, "")}/case-studies` : undefined;

  return (
    <Card>
      <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="panel-head">
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {onBackToProfile && (
              <div>
                <Button variant="link" onClick={onBackToProfile}>
                  ← Back to profile
                </Button>
              </div>
            )}
            <span className="eyebrow">Case studies</span>
            <h1 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>Systems I've built at work</h1>
          </div>
          {allOnSite && (
            <Button variant="link" href={allOnSite} onOpen={host.openLink}>
              All on site
            </Button>
          )}
        </div>

        {studies.length === 0 && <p className="hint">No case studies are published yet.</p>}

        {studies.map((s) => (
          <article key={s.id} className="item-card" aria-label={s.title}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span className="pill">{s.type}</span>
            </div>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>{s.title}</h2>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: "var(--text-soft)" }}>{s.desc}</p>
            <div style={{ display: "flex", gap: "4px 16px", flexWrap: "wrap", fontSize: 13, color: "var(--text-muted)" }}>
              <strong style={{ color: "var(--text)" }}>{s.role}</strong>
              <span>{s.team}</span>
              <span>{s.duration}</span>
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {s.techStack.map((t) => (
                <span key={t} className="tech">
                  {t}
                </span>
              ))}
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", paddingTop: 4 }}>
              <Button variant="primary" onClick={() => onOpen(s.id)}>
                Open here
              </Button>
              <Button href={s.url} onOpen={host.openLink}>
                Read on site
              </Button>
            </div>
          </article>
        ))}
      </div>
      <div className="foot">From harshdadiya.in</div>
    </Card>
  );
}
