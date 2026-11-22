import { StrictMode, useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { useApp, useAutoResize, useHostStyles } from "@modelcontextprotocol/ext-apps/react";
import "./theme.css";
import "./components/components.css";
import { ErrorBox } from "./components/ErrorBox";
import { ProfileSkeleton } from "./components/Skeleton";
import type { HostActions } from "./host";
import { CaseStudyList } from "./screens/CaseStudyList";
import { CaseStudyViewer } from "./screens/CaseStudyViewer";
import { Profile } from "./screens/Profile";
import { Projects } from "./screens/Projects";
import type { CaseStudyData, CaseStudyListData, ProfileData, ProjectsData } from "./types";

// One iframe, several screens. The first screen comes from the tool the model called
// (picked by the shape of its result). After that the page moves between screens by
// calling the server's tools itself (callServerTool), so nothing reloads.
type Screen =
  | { kind: "loading" }
  | { kind: "error"; message?: string }
  | { kind: "profile" }
  | { kind: "list" }
  | { kind: "study"; id: string; initial?: CaseStudyData }
  | { kind: "projects"; data: ProjectsData };

// Data already fetched, so going back doesn't call the server again.
type Store = {
  profile?: ProfileData;
  list?: CaseStudyListData;
};

const isObject = (data: unknown): data is Record<string, unknown> => typeof data === "object" && data !== null;

function isProfile(d: unknown): d is ProfileData {
  return isObject(d) && "summary" in d && "focus" in d && "links" in d;
}
function isList(d: unknown): d is CaseStudyListData {
  return isObject(d) && Array.isArray(d.caseStudies);
}
function isStudy(d: unknown): d is CaseStudyData {
  return isObject(d) && typeof d.id === "string" && Array.isArray(d.sections);
}
function isProjects(d: unknown): d is ProjectsData {
  return isObject(d) && isObject(d.projects) && "group" in d;
}

function App() {
  const [screen, setScreen] = useState<Screen>({ kind: "loading" });
  const [store, setStore] = useState<Store>({});

  // Handlers go on before the host handshake, so the first tool result isn't missed.
  const { app, error } = useApp({
    appInfo: { name: "harsh-portfolio-ui", version: "0.2.0" },
    capabilities: {},
    autoResize: false,
    onAppCreated: (created) => {
      created.ontoolinput = () => setScreen({ kind: "loading" });
      created.ontoolresult = (result) => {
        if (result.isError) return setScreen({ kind: "error" });
        const data = result.structuredContent;
        if (isProfile(data)) {
          setStore((s) => ({ ...s, profile: data }));
          setScreen({ kind: "profile" });
        } else if (isList(data)) {
          setStore((s) => ({ ...s, list: data }));
          setScreen({ kind: "list" });
        } else if (isStudy(data)) {
          setScreen({ kind: "study", id: data.id, initial: data });
        } else if (isProjects(data)) {
          setScreen({ kind: "projects", data });
        } else {
          setScreen({ kind: "error" });
        }
      };
      created.ontoolcancelled = () => setScreen({ kind: "error" });
    },
  });

  useHostStyles(app, app?.getHostContext());
  useAutoResize(app);

  const host: HostActions = useMemo(
    () => ({
      openLink: (url) => {
        void app?.openLink({ url }).catch(() => undefined);
      },
      sendMessage: async (text) => {
        if (!app) throw new Error("not connected");
        const res = await app.sendMessage({ role: "user", content: [{ type: "text", text }] });
        if (res.isError) throw new Error("host refused the message");
      },
      callTool: async (name, args) => {
        if (!app) throw new Error("not connected");
        return app.callServerTool({ name, arguments: args });
      },
      updateContext: (text) => {
        // Best effort: a host that doesn't take context updates just ignores this.
        void app?.updateModelContext({ content: [{ type: "text", text }] }).catch(() => undefined);
      },
    }),
    [app],
  );

  // The case study list: from the store, or fetched. Rejects if it can't be loaded.
  const showList = useCallback(async () => {
    if (store.list) return setScreen({ kind: "list" });
    const res = await host.callTool("list_case_studies", {});
    if (res.isError || !isList(res.structuredContent)) throw new Error("no list");
    const list = res.structuredContent;
    setStore((s) => ({ ...s, list }));
    setScreen({ kind: "list" });
  }, [host, store.list]);

  // Back from a viewer that can't reach the list: say so instead of doing nothing.
  const [backFailed, setBackFailed] = useState(false);
  useEffect(() => setBackFailed(false), [screen]);

  if (error) return <ErrorBox message="The host didn't connect. Try asking again." />;

  switch (screen.kind) {
    case "loading":
      return <ProfileSkeleton />;
    case "error":
      return <ErrorBox message={screen.message} />;
    case "profile":
      return store.profile ? <Profile data={store.profile} host={host} onCaseStudies={showList} /> : <ErrorBox />;
    case "list":
      return !store.list ? (
        <ErrorBox />
      ) : (
        <CaseStudyList
          studies={store.list.caseStudies}
          siteUrl={store.list.siteUrl}
          host={host}
          onOpen={(id) => setScreen({ kind: "study", id })}
          onBackToProfile={store.profile ? () => setScreen({ kind: "profile" }) : undefined}
        />
      );
    case "study":
      return (
        <>
          <CaseStudyViewer
            key={screen.id}
            id={screen.id}
            listed={store.list?.caseStudies.find((s) => s.id === screen.id)}
            initial={screen.initial}
            host={host}
            onBack={() => void showList().catch(() => setBackFailed(true))}
          />
          {backFailed && (
            <p role="status" className="hint" style={{ padding: "8px 4px" }}>
              Couldn't load the list. Ask your assistant: "Show Harsh's case studies".
            </p>
          )}
        </>
      );
    case "projects":
      return <Projects data={screen.data} host={host} />;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
