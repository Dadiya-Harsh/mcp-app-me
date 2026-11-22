// What the screens can ask the host to do. main.tsx builds this from the ext-apps `App`.

/** The parts of a tool result the screens read. */
export type ToolResult = {
  isError?: boolean;
  structuredContent?: unknown;
  content?: { type: string; text?: string }[];
};

export type HostActions = {
  /** Opens a URL through the host (the iframe can't navigate on its own). */
  openLink: (url: string) => void;
  /** Sends a message as if the visitor typed it. Rejects if the host doesn't allow it. */
  sendMessage: (text: string) => Promise<void>;
  /** Calls one of the server's tools from the UI. Rejects if the host doesn't allow it. */
  callTool: (name: string, args: Record<string, unknown>) => Promise<ToolResult>;
  /** Tells the model what the visitor is looking at, without sending a chat message. */
  updateContext: (text: string) => void;
};
