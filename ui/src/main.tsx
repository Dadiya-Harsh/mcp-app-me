import { StrictMode, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { useApp, useAutoResize, useHostStyles } from "@modelcontextprotocol/ext-apps/react";
import "./theme.css";
import "./components/components.css";
import { ErrorBox } from "./components/ErrorBox";
import { ProfileSkeleton } from "./components/Skeleton";
import { Profile, type HostActions } from "./screens/Profile";
import type { ProfileData } from "./types";

// What the screen is showing. M5 and M6 add the other screens here.
type View =
  | { kind: "loading" }
  | { kind: "error"; message?: string }
  | { kind: "profile"; data: ProfileData };

function isProfile(data: unknown): data is ProfileData {
  return typeof data === "object" && data !== null && "summary" in data && "focus" in data && "links" in data;
}

function App() {
  const [view, setView] = useState<View>({ kind: "loading" });

  // Handlers go on before the host handshake, so the first tool result isn't missed.
  const { app, error } = useApp({
    appInfo: { name: "harsh-portfolio-ui", version: "0.1.0" },
    capabilities: {},
    autoResize: false,
    onAppCreated: (created) => {
      created.ontoolinput = () => setView({ kind: "loading" });
      created.ontoolresult = (result) => {
        if (result.isError) return setView({ kind: "error" });
        const data = result.structuredContent;
        setView(isProfile(data) ? { kind: "profile", data } : { kind: "error" });
      };
      created.ontoolcancelled = () => setView({ kind: "error" });
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
    }),
    [app],
  );

  if (error) return <ErrorBox message="The host didn't connect. Try asking again." />;
  switch (view.kind) {
    case "loading":
      return <ProfileSkeleton />;
    case "error":
      return <ErrorBox message={view.message} />;
    case "profile":
      return <Profile data={view.data} host={host} />;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
