// Server route only. No credentials/configuration from this module reach client bundles.
type Options = { origin: string; identity: boolean; apiHost?: string; fetcher?: typeof fetch };
const MAX_BODY = 537919488;
const tokenCache = new Map<string, { value: string; until: number }>();
const incoming = ["accept", "authorization", "content-type", "cookie", "origin", "referer", "range", "if-range", "x-csrftoken"];
const outgoing = ["content-type", "content-range", "accept-ranges", "content-disposition", "last-modified", "etag", "retry-after", "vary", "www-authenticate"];

function validOrigin(value: string, identity: boolean) {
  const url = new URL(value);
  if (url.username || url.password || url.pathname !== "/" || url.search || url.hash) throw new Error("API configuration");
  const local = url.protocol === "http:" && ["127.0.0.1", "localhost"].includes(url.hostname);
  const cloud = url.protocol === "https:" && /^[a-z0-9.-]+\.run\.app$/.test(url.hostname);
  if (identity ? !cloud : !local) throw new Error("API configuration");
  return url.origin;
}

function safePath(path: string) {
  let decoded = path;
  for (let i = 0; i < 5; i++) {
    const next = decodeURIComponent(decoded);
    if (next === decoded) break;
    decoded = next;
    if (i === 4) throw new Error("Invalid API path");
  }
  return decoded.startsWith("/api/") && !decoded.includes("\\") && !Array.from(decoded).some(c => c.charCodeAt(0) < 32)
    && !decoded.split("/").some(part => part === "." || part === "..");
}

async function identityToken(origin: string, fetcher: typeof fetch) {
  const cached = tokenCache.get(origin);
  if (cached && cached.until > Date.now()) return cached.value;
  const url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?format=full&audience=" + encodeURIComponent(origin);
  const response = await fetcher(url, { headers: { "Metadata-Flavor": "Google" }, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(5000) });
  if (!response.ok || response.headers.get("Metadata-Flavor") !== "Google") throw new Error("Service identity unavailable");
  const value = await readBounded(response.body, 16384);
  const token = new TextDecoder().decode(value).trim();
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("Invalid service identity");
  const claims = JSON.parse(Buffer.from(parts[1], "base64url").toString("utf8"));
  if (claims.aud !== origin || typeof claims.exp !== "number" || !Number.isFinite(claims.exp) || claims.exp * 1000 <= Date.now() + 60000) throw new Error("Invalid service identity");
  tokenCache.clear(); // At most one private service token per process.
  tokenCache.set(origin, { value: token, until: Math.min(claims.exp * 1000 - 60000, Date.now() + 600000) });
  return token;
}

async function readBounded(body: ReadableStream<Uint8Array> | null, maximum: number) {
  const reader = body?.getReader();
  if (!reader) throw new Error("Empty service identity");
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > maximum) throw new Error("Service identity limit");
      chunks.push(value);
    }
  } catch (error) {
    await reader.cancel();
    throw error;
  } finally { reader.releaseLock(); }
  return Buffer.concat(chunks);
}

function boundedBody(body: ReadableStream<Uint8Array>) {
  let size = 0;
  return body.pipeThrough(new TransformStream({ transform(chunk, controller) {
    size += chunk.byteLength;
    if (size > MAX_BODY) throw new Error("API body limit");
    controller.enqueue(chunk);
  } }));
}

export function createApiProxy(options: Options) {
  const fetcher = options.fetcher ?? fetch;
  return async function proxy(request: Request): Promise<Response> {
    try {
      const origin = validOrigin(options.origin, options.identity);
      const input = new URL(request.url);
      if (!safePath(input.pathname)) return Response.json({ error: "Invalid API path" }, { status: 400 });
      const target = new URL(input.pathname + input.search, origin);
      if (target.origin !== origin || !safePath(target.pathname)) throw new Error("Invalid API target");
      const length = request.headers.get("content-length");
      if (length && (!/^\d+$/.test(length) || Number(length) > MAX_BODY)) return Response.json({ error: "Request body too large" }, { status: 413 });
      const headers = new Headers({ "Accept-Encoding": "identity" });
      for (const name of incoming) { const value = request.headers.get(name); if (value) headers.set(name, value); }
      if (options.identity) {
        if (!options.apiHost || !/^[a-z0-9.-]{1,253}$/.test(options.apiHost)) throw new Error("API host configuration");
        const browserOrigin = request.headers.get("origin");
        const referer = request.headers.get("referer");
        if (!["GET", "HEAD", "OPTIONS"].includes(request.method)) {
          if ((browserOrigin && browserOrigin !== input.origin) || (!browserOrigin && referer && new URL(referer).origin !== input.origin)) {
            return Response.json({ error: "Cross-origin request denied" }, { status: 403 });
          }
          if (browserOrigin) headers.set("Origin", "https://" + options.apiHost);
          if (referer) headers.set("Referer", "https://" + options.apiHost + "/");
        }
        headers.set("X-Forwarded-Host", options.apiHost);
        headers.set("X-Serverless-Authorization", "Bearer " + await identityToken(origin, fetcher));
      }
      const init: RequestInit & { duplex?: "half" } = {
        method: request.method, headers, cache: "no-store", redirect: "manual",
        signal: AbortSignal.any([request.signal, AbortSignal.timeout(60000)]),
      };
      if (request.method !== "GET" && request.method !== "HEAD" && request.body) {
        init.body = boundedBody(request.body); init.duplex = "half";
      }
      const response = await fetcher(target, init);
      if (response.status >= 300 && response.status < 400) {
        await response.body?.cancel();
        throw new Error("API redirect denied");
      }
      const result = new Headers({ "Cache-Control": "private, no-store" });
      for (const name of outgoing) { const value = response.headers.get(name); if (value) result.set(name, value); }
      for (const cookie of response.headers.getSetCookie()) result.append("Set-Cookie", cookie);
      return new Response(request.method === "HEAD" || response.status === 204 ? null : response.body, { status: response.status, headers: result });
    } catch {
      // Do not expose tokens, cookies, private origins or upstream exception details.
      return Response.json({ error: "Private API temporarily unavailable" }, { status: 503, headers: { "Cache-Control": "private, no-store" } });
    }
  };
}

export async function proxyApi(request: Request) {
  return createApiProxy({ origin: process.env.DOJOPULSE_API_ORIGIN ?? "http://127.0.0.1:8000", identity: process.env.DOJOPULSE_API_IDENTITY === "GCP", apiHost: process.env.DOJOPULSE_API_HOST })(request);
}
