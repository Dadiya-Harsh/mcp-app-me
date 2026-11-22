import { renameSync } from "node:fs";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const OUT_DIR = resolve(__dirname, "../portfolio_mcp/ui_dist");

// Vite names the page after index.html. The server looks for app.html.
function renameToAppHtml(): Plugin {
  return {
    name: "rename-to-app-html",
    apply: "build",
    closeBundle() {
      renameSync(resolve(OUT_DIR, "index.html"), resolve(OUT_DIR, "app.html"));
    },
  };
}

// One self-contained HTML file: all JS and CSS inlined. It is committed to the repo
// (portfolio_mcp/ui_dist/app.html) because the Python build on Vercel doesn't run npm.
export default defineConfig({
  plugins: [react(), viteSingleFile(), renameToAppHtml()],
  build: {
    outDir: OUT_DIR,
    emptyOutDir: false,
    target: "es2022",
  },
});
