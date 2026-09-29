/**
 * Production Reverse Proxy for XAUUSD Shadow Dashboard
 * Listens on Port 80 (HTTP) and routes traffic:
 *  - /api/*    -> FastAPI (127.0.0.1:8000)
 *  - /health   -> FastAPI (127.0.0.1:8000)
 *  - /ws/*     -> FastAPI WebSocket (127.0.0.1:8000)
 *  - /*        -> Next.js Dashboard (127.0.0.1:3000)
 * 
 * Zero external dependencies (uses Node.js built-in http & net modules).
 */
const http = require("http");
const net = require("net");
const url = require("url");

const PORT = 80;
const FASTAPI_HOST = "127.0.0.1";
const FASTAPI_PORT = 8000;
const NEXTJS_HOST = "127.0.0.1";
const NEXTJS_PORT = 3000;

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url);
  const pathname = parsedUrl.pathname || "/";

  // Route to FastAPI or Next.js
  const isFastApi = pathname === "/health" || pathname.startsWith("/api/") || pathname.startsWith("/ws/");
  const targetHost = isFastApi ? FASTAPI_HOST : NEXTJS_HOST;
  const targetPort = isFastApi ? FASTAPI_PORT : NEXTJS_PORT;

  const options = {
    hostname: targetHost,
    port: targetPort,
    path: req.url,
    method: req.method,
    headers: {
      ...req.headers,
      "x-forwarded-for": req.socket.remoteAddress,
      "x-forwarded-proto": "http",
      "x-forwarded-host": req.headers.host || "",
    },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on("error", (err) => {
    if (!res.headersSent) {
      res.writeHead(502, { "Content-Type": "text/plain" });
      res.end(`Bad Gateway: ${targetHost}:${targetPort} unavailable (${err.message})`);
    }
  });

  req.pipe(proxyReq, { end: true });
});

// WebSocket / HTTP Upgrade Proxy
server.on("upgrade", (req, clientSocket, head) => {
  const parsedUrl = url.parse(req.url);
  const pathname = parsedUrl.pathname || "/";

  const isFastApi = pathname.startsWith("/ws/");
  const targetHost = isFastApi ? FASTAPI_HOST : NEXTJS_HOST;
  const targetPort = isFastApi ? FASTAPI_PORT : NEXTJS_PORT;

  const targetSocket = net.connect(targetPort, targetHost, () => {
    // Reconstruct HTTP upgrade request to target
    let rawReq = `${req.method} ${req.url} HTTP/1.1\r\n`;
    for (const [key, value] of Object.entries(req.headers)) {
      rawReq += `${key}: ${value}\r\n`;
    }
    rawReq += "\r\n";

    targetSocket.write(rawReq);
    if (head && head.length > 0) {
      targetSocket.write(head);
    }

    // Bi-directional pipe
    targetSocket.pipe(clientSocket);
    clientSocket.pipe(targetSocket);
  });

  targetSocket.on("error", (err) => {
    clientSocket.destroy();
  });

  clientSocket.on("error", (err) => {
    targetSocket.destroy();
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`==========================================================`);
  console.log(`🚀 Production Reverse Proxy Active on Port ${PORT}`);
  console.log(`   - Frontend Dashboard : http://127.0.0.1:${NEXTJS_PORT} -> http://0.0.0.0:${PORT}/`);
  console.log(`   - FastAPI Backend    : http://127.0.0.1:${FASTAPI_PORT} -> http://0.0.0.0:${PORT}/api/`);
  console.log(`   - Live WebSocket     : ws://127.0.0.1:${FASTAPI_PORT}  -> ws://0.0.0.0:${PORT}/ws/`);
  console.log(`==========================================================`);
});
