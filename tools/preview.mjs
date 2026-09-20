#!/usr/bin/env node
// Local preview server for dist/, the same on Windows and macOS.
//
// .claude/launch.json used to start `py -m http.server`, and `py` is a
// Windows-only launcher; bare `python` is the Microsoft Store stub on the
// Windows box and `python3` does not exist there. Node is a hard requirement
// of the build on every machine (Tailwind), so a Node server needs nothing
// extra installed and no interpreter path.
//
// Usage: node tools/preview.mjs [port]      (default 8791, dist/ at the repo root)
//
// Local use only: it binds to 127.0.0.1, so it is not reachable from the
// network. Responses carry Cache-Control: no-store, which is what makes a
// rebuilt garden.html show up on reload instead of the browser's cached copy.
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { extname, join, resolve, sep } from "node:path";

const ROOT = resolve(fileURLToPath(new URL("../dist", import.meta.url)));
const PORT = Number(process.argv[2] ?? 8791);

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".csv": "text/csv; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
  ".ico": "image/x-icon",
  ".mp3": "audio/mpeg",
  ".mp4": "video/mp4",
  ".woff2": "font/woff2",
};

async function fileFor(urlPath) {
  let decoded;
  try {
    decoded = decodeURIComponent(urlPath);
  } catch {
    return null;
  }
  // A NUL byte is never a legitimate path character and some fs layers stop
  // reading at it, so refuse it outright.
  if (decoded.includes("\0")) return null;
  let target = resolve(join(ROOT, decoded));
  // Containment: a request such as /../package.json resolves outside dist/.
  if (target !== ROOT && !target.startsWith(ROOT + sep)) return null;
  try {
    if ((await stat(target)).isDirectory()) target = join(target, "index.html");
    return (await stat(target)).isFile() ? target : null;
  } catch {
    return null;
  }
}

createServer(async (req, res) => {
  const headers = { "Cache-Control": "no-store" };
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { ...headers, Allow: "GET, HEAD" }).end();
    return;
  }
  const urlPath = new URL(req.url, "http://localhost").pathname;
  const file = await fileFor(urlPath);
  if (file) {
    res.writeHead(200, { ...headers, "Content-Type": TYPES[extname(file).toLowerCase()] ?? "application/octet-stream" });
    res.end(req.method === "HEAD" ? undefined : await readFile(file));
    return;
  }
  // GitHub Pages serves 404.html for a missing path; do the same here.
  const notFound = await fileFor("/404.html");
  res.writeHead(404, { ...headers, "Content-Type": "text/html; charset=utf-8" });
  res.end(req.method === "HEAD" ? undefined : notFound ? await readFile(notFound) : "Not found");
}).listen(PORT, "127.0.0.1", () => {
  console.log(`Serving ${ROOT} at http://localhost:${PORT}/`);
});
