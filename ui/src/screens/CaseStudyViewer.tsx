import { useEffect, useRef, useState } from "react";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Markdown } from "../components/Markdown";
import { Tabs } from "../components/Tabs";
import type { HostActions } from "../host";
import type { CaseStudyData, CaseStudyMeta, SectionId, StudySection, StudyStep } from "../types";

// The four tabs. "Overview" shows two sections, the rest one each.
const TABS = [
  { id: "overview", label: "Overview", sections: ["overview", "problem"] },
  { id: "arch", label: "How it works", sections: ["architecture"] },
  { id: "hard", label: "What was hard", sections: ["hard"] },
  { id: "result", label: "Where it ended up", sections: ["result"] },
] as const satisfies readonly { id: string; label: string; sections: readonly SectionId[] }[];

type TabId = (typeof TABS)[number]["id"];

function tabFor(section: string): TabId {
  return TABS.find((t) => (t.sections as readonly string[]).includes(section))?.id ?? "overview";
}

type Props = {
  id: string;
  /** From the list, so the header shows straight away. */
  listed?: CaseStudyMeta;
  /** Set when the model called get_case_study and the host showed this screen. */
  initial?: CaseStudyData;
  host: HostActions;
  onBack: () => void;
};

/** Text before the first ### line, and the ### parts after it as title + body. */
function splitParts(markdown: string): { intro: string; parts: { title: string; body: string }[] } {
  const lines = markdown.split("\n");
  const intro: string[] = [];
  const parts: { title: string; body: string[] }[] = [];
  let fence = false;
  for (const line of lines) {
    if (/^\s*(```|~~~)/.test(line)) fence = !fence;
    const h = !fence && /^###\s+(.*)$/.exec(line);
    if (h) parts.push({ title: h[1].trim(), body: [] });
    else if (parts.length) parts[parts.length - 1].body.push(line);
    else intro.push(line);
  }
  return { intro: intro.join("\n").trim(), parts: parts.map((p) => ({ title: p.title, body: p.body.join("\n").trim() })) };
}

export function CaseStudyViewer({ id, listed, initial, host, onBack }: Props) {
  const [meta, setMeta] = useState<CaseStudyMeta | undefined>(initial ?? listed);
  const [sections, setSections] = useState<Partial<Record<SectionId, StudySection>>>(() =>
    Object.fromEntries((initial?.sections ?? []).map((s) => [s.id, s])),
  );
  const [steps, setSteps] = useState<StudyStep[]>(initial?.steps ?? []);
  const [failed, setFailed] = useState<Partial<Record<SectionId, true>>>({});
  const [tab, setTab] = useState<TabId>(initial ? tabFor(initial.requestedSection) : "overview");
  const [hint, setHint] = useState<string | null>(null);
  const [asked, setAsked] = useState<string | null>(null);
  const inflight = useRef(new Set<SectionId>());

  const current = TABS.find((t) => t.id === tab)!;

  // Load whatever the open tab needs and doesn't have yet. Each section is its own
  // call to get_case_study, made by the page through the host.
  useEffect(() => {
    const missing = current.sections.filter((s) => !sections[s] && !failed[s] && !inflight.current.has(s));
    for (const section of missing) {
      inflight.current.add(section);
      host
        .callTool("get_case_study", { id, section })
        .then((r) => {
          if (r.isError || !r.structuredContent) throw new Error("no section");
          const data = r.structuredContent as CaseStudyData;
          setMeta((m) => m ?? data);
          setSections((prev) => ({ ...prev, ...Object.fromEntries(data.sections.map((s) => [s.id, s])) }));
          if (data.steps?.length) setSteps(data.steps);
        })
        .catch(() => setFailed((f) => ({ ...f, [section]: true })))
        .finally(() => inflight.current.delete(section));
    }
  }, [current, sections, failed, host, id]);

  const title = meta?.title ?? "Case study";

  useEffect(() => {
    host.updateContext(`The visitor is reading the "${title}" case study (id: ${id}), on the "${current.label}" tab.`);
  }, [host, id, title, current.label]);

  const pick = (next: TabId) => {
    setTab(next);
    setAsked(null);
    setHint(null);
  };

  const ask = () => {
    const text = `Tell me more about ${current.label.toLowerCase()} in ${title}`;
    setHint(null);
    host
      .sendMessage(text)
      .then(() => setAsked(text))
      .catch(() => setHint(`Ask your assistant: "${text}"`));
  };

  const retry = () => setFailed((f) => ({ ...f, ...Object.fromEntries(current.sections.map((s) => [s, undefined])) }));

  const loaded = current.sections.filter((s) => sections[s]);
  const loading = current.sections.some((s) => !sections[s] && !failed[s]);
  const open = host.openLink;

  let body: React.ReactNode;
  if (loaded.length === 0 && !loading) {
    body = (
      <div role="alert" style={{ display: "flex", flexDirection: "column", gap: 10, alignItems: "flex-start" }}>
        <p className="hint">Couldn't load this part.</p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Button onClick={retry}>Try again</Button>
          {meta && (
            <Button href={meta.url} onOpen={open}>
              Read it on the site
            </Button>
          )}
        </div>
      </div>
    );
  } else if (loaded.length === 0) {
    body = (
      <div aria-busy="true" aria-label="Loading section" style={{ display: "grid", gap: 12 }}>
        <div className="skeleton" style={{ height: 16, width: "100%" }} />
        <div className="skeleton" style={{ height: 16, width: "85%" }} />
        <div className="skeleton" style={{ height: 96, width: "100%" }} />
      </div>
    );
  } else if (tab === "overview") {
    const { overview, problem } = sections;
    body = (
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {overview && <Markdown text={overview.markdown} onOpen={open} />}
        {problem && (
          <>
            <span className="eyebrow" style={{ marginTop: 6 }}>
              {problem.heading}
            </span>
            <Markdown text={problem.markdown} onOpen={open} />
          </>
        )}
        {loading && <div className="skeleton" style={{ height: 16, width: "60%" }} />}
      </div>
    );
  } else if (tab === "arch" && sections.architecture) {
    const { intro } = splitParts(sections.architecture.markdown);
    body =
      steps.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {intro && <Markdown text={intro} onOpen={open} />}
          <ol className="steps">
            {steps.map((s) => (
              <li key={s.number} className="step">
                <span className="step-number" aria-hidden="true">
                  {s.number}
                </span>
                <span className="step-title">
                  <span className="sr-only">Step {s.number}: </span>
                  {s.title}
                </span>
                <Markdown text={s.markdown} onOpen={open} />
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <Markdown text={sections.architecture.markdown} onOpen={open} />
      );
  } else if (tab === "hard" && sections.hard) {
    const { intro, parts } = splitParts(sections.hard.markdown);
    body = (
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {intro && <Markdown text={intro} onOpen={open} />}
        {parts.map((p) => (
          <div key={p.title} className="note-card">
            <h3>{p.title}</h3>
            <Markdown text={p.body} onOpen={open} />
          </div>
        ))}
      </div>
    );
  } else if (tab === "result" && sections.result) {
    body = <Markdown text={sections.result.markdown} onOpen={open} />;
  }

  return (
    <Card>
      <div style={{ padding: "24px 28px 18px", display: "flex", flexDirection: "column", gap: 10 }}>
        <div>
          <Button variant="link" onClick={onBack}>
            ← All case studies
          </Button>
        </div>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, letterSpacing: "-0.01em" }}>{title}</h1>
      </div>

      {meta && (
        <div style={{ padding: "0 28px" }}>
          <dl className="facts" style={{ margin: 0 }}>
            {(
              [
                ["Role", meta.role],
                ["Team", meta.team],
                ["Duration", meta.duration],
              ] as const
            ).map(([label, value]) => (
              <div key={label} className="fact">
                <dt className="eyebrow" style={{ letterSpacing: "0.06em" }}>
                  {label}
                </dt>
                <dd className="fact-value" style={{ margin: "4px 0 0" }}>
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <div style={{ marginTop: 20 }}>
        <Tabs tabs={TABS} value={tab} onChange={pick} idPrefix={`cs-${id}`} label="Case study sections" />
      </div>

      <div id={`cs-${id}-panel`} role="tabpanel" aria-labelledby={`cs-${id}-${tab}`} style={{ padding: "22px 28px 8px", minHeight: 240 }}>
        {body}
      </div>

      <div style={{ padding: "16px 28px 24px", display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <Button variant="primary" onClick={ask}>
          Ask about this section
        </Button>
        {meta && (
          <Button href={meta.url} onOpen={open}>
            Read full write-up
          </Button>
        )}
        {asked && (
          <span role="status" className="hint">
            Sent “{asked}” to the chat
          </span>
        )}
      </div>
      {hint && (
        <p role="status" className="hint" style={{ padding: "0 28px 16px" }}>
          {hint}
        </p>
      )}
      <div className="foot">From harshdadiya.in</div>
    </Card>
  );
}
