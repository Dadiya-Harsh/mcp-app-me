import type { ReactNode } from "react";
import "./markdown.css";

// A small markdown renderer for the case study text. It handles what those files use:
// paragraphs, ### headings, bullet and numbered lists, tables, code blocks, quotes,
// **bold**, *italic*, `code`, links and images. It builds React elements (no HTML
// strings), so nothing in the text can inject markup. Links go through the host.

type Ctx = { onOpen: (url: string) => void };

const INLINE = /(\*\*[^*]+?\*\*)|(`[^`]+`)|(!\[[^\]]*\]\([^)\s]+\))|(\[[^\]]+\]\([^)\s]+\))|(\*[^*\s][^*]*?\*)/;
const SAFE_LINK = /^(https?:|mailto:)/i;

function inline(text: string, ctx: Ctx, key = ""): ReactNode[] {
  const out: ReactNode[] = [];
  let rest = text;
  let n = 0;
  while (rest) {
    const m = INLINE.exec(rest);
    if (!m) {
      out.push(rest);
      break;
    }
    if (m.index > 0) out.push(rest.slice(0, m.index));
    const tok = m[0];
    const k = `${key}${n++}`;
    if (m[1]) {
      out.push(<strong key={k}>{inline(tok.slice(2, -2), ctx, k)}</strong>);
    } else if (m[2]) {
      out.push(<code key={k}>{tok.slice(1, -1)}</code>);
    } else if (m[3]) {
      const img = /^!\[([^\]]*)\]\(([^)\s]+)\)$/.exec(tok);
      if (img && img[2].startsWith("https://")) {
        out.push(<img key={k} src={img[2]} alt={img[1]} loading="lazy" onError={(e) => (e.currentTarget.style.display = "none")} />);
      } else if (img?.[1]) {
        out.push(img[1]);
      }
    } else if (m[4]) {
      const link = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(tok);
      if (link && SAFE_LINK.test(link[2])) {
        const url = link[2];
        out.push(
          <a
            key={k}
            href={url}
            target="_blank"
            rel="noreferrer noopener"
            onClick={(e) => {
              e.preventDefault();
              ctx.onOpen(url);
            }}
          >
            {inline(link[1], ctx, k)}
          </a>,
        );
      } else if (link) {
        out.push(link[1]);
      }
    } else {
      out.push(<em key={k}>{inline(tok.slice(1, -1), ctx, k)}</em>);
    }
    rest = rest.slice(m.index + tok.length);
  }
  return out;
}

const FENCE = /^\s*(```|~~~)/;
const HEADING = /^(#{1,6})\s+(.*)$/;
const RULE = /^\s*-{3,}\s*$/;
const BULLET = /^\s*[-*]\s+(.*)$/;
const NUMBERED = /^\s*\d+\.\s+(.*)$/;
const QUOTE = /^\s*>\s?(.*)$/;
const TABLE_SEPARATOR = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

const cells = (line: string) =>
  line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim());

function startsBlock(line: string, next: string | undefined): boolean {
  return (
    FENCE.test(line) ||
    HEADING.test(line) ||
    RULE.test(line) ||
    BULLET.test(line) ||
    NUMBERED.test(line) ||
    QUOTE.test(line) ||
    (line.includes("|") && next !== undefined && TABLE_SEPARATOR.test(next))
  );
}

function blocks(text: string, ctx: Ctx): ReactNode[] {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const out: ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const key = `b${i}`;
    if (!line.trim()) {
      i++;
    } else if (FENCE.test(line)) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !FENCE.test(lines[i])) code.push(lines[i++]);
      i++;
      out.push(
        <pre key={key}>
          <code>{code.join("\n")}</code>
        </pre>,
      );
    } else if (HEADING.test(line)) {
      out.push(
        <h4 key={key} className="md-heading">
          {inline(HEADING.exec(line)![2], ctx, key)}
        </h4>,
      );
      i++;
    } else if (RULE.test(line)) {
      out.push(<hr key={key} />);
      i++;
    } else if (line.includes("|") && TABLE_SEPARATOR.test(lines[i + 1] ?? "")) {
      const head = cells(line);
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) rows.push(cells(lines[i++]));
      out.push(
        <div key={key} className="md-table">
          <table>
            <thead>
              <tr>
                {head.map((c, j) => (
                  <th key={j}>{inline(c, ctx, `${key}h${j}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, j) => (
                <tr key={j}>
                  {r.map((c, k) => (
                    <td key={k}>{inline(c, ctx, `${key}r${j}c${k}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
    } else if (BULLET.test(line) || NUMBERED.test(line)) {
      const ordered = NUMBERED.test(line) && !BULLET.test(line);
      const re = ordered ? NUMBERED : BULLET;
      const items: string[] = [];
      while (i < lines.length && re.test(lines[i])) items.push(re.exec(lines[i++])![1]);
      const li = items.map((t, j) => <li key={j}>{inline(t, ctx, `${key}i${j}`)}</li>);
      out.push(ordered ? <ol key={key}>{li}</ol> : <ul key={key}>{li}</ul>);
    } else if (QUOTE.test(line)) {
      const quote: string[] = [];
      while (i < lines.length && QUOTE.test(lines[i])) quote.push(QUOTE.exec(lines[i++])![1]);
      out.push(<blockquote key={key}>{inline(quote.join(" "), ctx, key)}</blockquote>);
    } else {
      const para: string[] = [line];
      i++;
      while (i < lines.length && lines[i].trim() && !startsBlock(lines[i], lines[i + 1])) para.push(lines[i++]);
      // A line break inside a paragraph stays a line break ("The problem: ..." / "What I did: ...").
      const parts = para.flatMap((p, j) => (j === 0 ? [p] : [<br key={`${key}br${j}`} />, p]));
      out.push(
        <p key={key}>
          {parts.map((p, j) => (typeof p === "string" ? inline(p, ctx, `${key}p${j}`) : p))}
        </p>,
      );
    }
  }
  return out;
}

export function Markdown({ text, onOpen }: { text: string; onOpen: (url: string) => void }) {
  return <div className="md">{blocks(text, { onOpen })}</div>;
}
