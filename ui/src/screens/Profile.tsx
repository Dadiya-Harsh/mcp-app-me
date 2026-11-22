import { useState } from "react";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Chip } from "../components/Chip";
import { StatTile } from "../components/StatTile";
import type { HostActions } from "../host";
import type { ProfileData } from "../types";

const LABEL: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.08em",
  color: "var(--text-muted)",
  textTransform: "uppercase",
};

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function Photo({ src, name }: { src: string; name: string }) {
  const [failed, setFailed] = useState(false);
  const style: React.CSSProperties = {
    width: 76,
    height: 76,
    borderRadius: 999,
    flexShrink: 0,
    border: "2px solid var(--divider)",
  };
  if (failed || !src) {
    return (
      <div
        aria-hidden="true"
        style={{
          ...style,
          display: "grid",
          placeItems: "center",
          background: "var(--elevated)",
          color: "var(--text-muted)",
          fontWeight: 700,
          fontSize: 22,
        }}
      >
        {initials(name)}
      </div>
    );
  }
  return <img src={src} alt={name} style={{ ...style, objectFit: "cover" }} onError={() => setFailed(true)} />;
}

type Props = {
  data: ProfileData;
  host: HostActions;
  /** Opens the case study list inside this iframe. Rejects if it can't. */
  onCaseStudies: () => Promise<void>;
};

export function Profile({ data, host, onCaseStudies }: Props) {
  // If the host won't take a message, tell the visitor what to ask instead.
  const [hint, setHint] = useState<string | null>(null);
  const [opening, setOpening] = useState(false);
  const ask = (text: string) => {
    setHint(null);
    host.sendMessage(text).catch(() => setHint(`Ask your assistant: "${text}"`));
  };

  const years = data.experienceYears.toFixed(1);
  const { links } = data;

  return (
    <Card>
      <div style={{ padding: "28px 28px 22px", display: "flex", gap: 20, alignItems: "center" }}>
        <Photo src={data.photo} name={data.name} />
        <div style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, letterSpacing: "-0.01em" }}>{data.name}</h1>
            {data.openToRoles && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "4px 10px",
                  borderRadius: 999,
                  background: "var(--ok-bg)",
                  color: "var(--ok-text)",
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: 999, background: "var(--ok-dot)" }} />
                {data.openToRolesLabel}
              </span>
            )}
          </div>
          <span style={{ fontSize: 15, color: "var(--text-muted)" }}>
            {data.title} · {data.location}
          </span>
        </div>
      </div>

      <p style={{ margin: 0, padding: "0 28px 22px", lineHeight: 1.6, color: "var(--text-soft)" }}>{data.summary}</p>

      <div
        style={{
          margin: "0 28px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: 12,
        }}
      >
        <StatTile value={`${years}+ yrs`} label="of experience" />
        {data.stats.map((s) => (
          <StatTile key={s.value} value={s.value} label={s.label} />
        ))}
      </div>

      {data.focus.length > 0 && (
        <div style={{ padding: "22px 28px 0", display: "flex", flexDirection: "column", gap: 10 }}>
          <span style={LABEL}>What I work on</span>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {data.focus.map((f) => (
              <Chip key={f.title}>{f.title}</Chip>
            ))}
          </div>
        </div>
      )}

      {data.nowBuilding && (
        <div
          style={{
            margin: "22px 28px 0",
            padding: "16px 18px",
            border: "1px dashed var(--border)",
            borderRadius: "var(--radius-tile)",
            display: "flex",
            gap: 14,
            alignItems: "flex-start",
          }}
        >
          <span
            aria-hidden="true"
            style={{ marginTop: 7, width: 8, height: 8, borderRadius: 999, background: "var(--accent)", flexShrink: 0 }}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ ...LABEL, fontSize: 12, letterSpacing: "0.06em" }}>Now building</span>
            <span style={{ fontSize: 14, color: "var(--text-soft)", lineHeight: 1.5 }}>
              <strong style={{ color: "var(--text)" }}>{data.nowBuilding.name}</strong>: {data.nowBuilding.description}
            </span>
          </div>
        </div>
      )}

      <div style={{ padding: "24px 28px 26px", display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <Button
          variant="primary"
          onClick={() => {
            if (opening) return;
            setHint(null);
            setOpening(true);
            // If the host won't let the page call the server, fall back to a chat message.
            onCaseStudies()
              .catch(() => ask("Show me Harsh's case studies"))
              .finally(() => setOpening(false));
          }}
        >
          {opening ? "Loading…" : "See case studies"}
        </Button>
        <Button href={links.resume} onOpen={host.openLink}>
          Resume
        </Button>
        <Button onClick={() => ask("How can I contact Harsh?")}>Contact</Button>
        <div style={{ flex: 1 }} />
        <Button variant="link" href={links.github} onOpen={host.openLink}>
          GitHub
        </Button>
        <Button variant="link" href={links.linkedin} onOpen={host.openLink}>
          LinkedIn
        </Button>
        <Button variant="link" href={links.medium} onOpen={host.openLink}>
          Medium
        </Button>
      </div>

      {hint && (
        <p role="status" style={{ margin: 0, padding: "0 28px 16px", fontSize: 13, color: "var(--text-muted)" }}>
          {hint}
        </p>
      )}

      <div
        style={{
          borderTop: "1px solid var(--divider)",
          padding: "10px 28px",
          fontSize: 12,
          color: "var(--text-muted)",
        }}
      >
        From harshdadiya.in
      </div>
    </Card>
  );
}
