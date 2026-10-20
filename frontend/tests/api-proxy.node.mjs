import assert from "node:assert/strict";
import test from "node:test";
import { createApiProxy } from "../server/api-proxy.ts";

test("cloud identity stays server-side while owned ranges and cookies are streamed", async () => {
  const origin = "https://dojo-api-abc.a.run.app";
  const token = "header." + Buffer.from(JSON.stringify({ aud: origin, exp: Date.now() / 1000 + 3600 })).toString("base64url") + ".signature";
  const calls = [];
  const proxy = createApiProxy({ origin, identity: true, apiHost: "api.example", fetcher: async (url, init) => {
    calls.push([String(url), init]);
    if (String(url).startsWith("http://metadata.google.internal/")) return new Response(token, { headers: { "Metadata-Flavor": "Google" } });
    assert.equal(init.headers.get("X-Serverless-Authorization"), "Bearer " + token);
    assert.equal(init.headers.get("Cookie"), "sessionid=owned");
    assert.equal(init.headers.get("Authorization"), "Bearer user-token");
    assert.equal(init.headers.get("Range"), "bytes=0-3");
    assert.equal(init.redirect, "manual");
    return new Response("data", { status: 206, headers: { "Content-Range": "bytes 0-3/100", "Content-Type": "video/mp4", "Set-Cookie": "csrftoken=owned; Secure; Path=/", "X-Serverless-Authorization": token } });
  } });
  const response = await proxy(new Request("https://dojo.example/api/assets/owned/preview/media", { headers: {
    Cookie: "sessionid=owned", Authorization: "Bearer user-token", Range: "bytes=0-3", "X-Serverless-Authorization": "forged",
  } }));
  assert.equal(response.status, 206);
  assert.equal(await response.text(), "data");
  assert.equal(response.headers.get("Content-Range"), "bytes 0-3/100");
  assert.match(response.headers.get("Set-Cookie"), /csrftoken=owned/);
  assert.equal(response.headers.get("X-Serverless-Authorization"), null);
  assert.equal(response.headers.get("Cache-Control"), "private, no-store");
  assert.equal(calls.length, 2);
});

test("local proxy streams a write with CSRF and no cloud identity request", async () => {
  const proxy = createApiProxy({ origin: "http://127.0.0.1:8000", identity: false, fetcher: async (url, init) => {
    assert.equal(String(url), "http://127.0.0.1:8000/api/upload-sessions?mode=preview");
    assert.equal(init.headers.get("X-CSRFToken"), "owned");
    assert.equal(init.headers.get("Origin"), "https://dojo.example");
    assert.equal(init.headers.get("X-Serverless-Authorization"), null);
    assert.equal(await new Response(init.body).text(), '{"preview_only":true}');
    return Response.json({ state: "UPLOADING" }, { status: 201 });
  } });
  const response = await proxy(new Request("http://localhost/api/upload-sessions?mode=preview", {
    method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": "owned", Origin: "https://dojo.example" }, body: '{"preview_only":true}',
  }));
  assert.equal(response.status, 201);
});

test("encoded API identities remain supported but traversal cannot reach internal dispatch", async () => {
  let called = 0;
  const proxy = createApiProxy({ origin: "http://127.0.0.1:8000", identity: false, fetcher: async (url) => {
    called++; assert.match(String(url), /\/api\/knowledge\/jin%2Fbuild%2Fuf4/); return Response.json({});
  } });
  assert.equal((await proxy(new Request("http://localhost/api/knowledge/jin%2Fbuild%2Fuf4"))).status, 200);
  assert.equal((await proxy(new Request("http://localhost/api/%252e%252e%252finternal/dispatch"))).status, 400);
  assert.equal(called, 1);
});

test("configuration, oversized uploads and redirects fail without disclosing secrets", async () => {
  const bad = createApiProxy({ origin: "https://foreign.example", identity: false, fetcher: async () => { throw new Error("must not fetch"); } });
  assert.equal((await bad(new Request("https://dojo.example/api/session"))).status, 503);
  const redirect = createApiProxy({ origin: "http://127.0.0.1:8000", identity: false, fetcher: async () => new Response("", { status: 302, headers: { Location: "https://foreign.example" } }) });
  const response = await redirect(new Request("https://dojo.example/api/session"));
  assert.equal(response.status, 503); assert.equal(response.headers.get("Location"), null);
  assert.equal((await redirect(new Request("https://dojo.example/api/upload", { method: "POST", headers: { "Content-Length": "999999999" } }))).status, 413);
  assert.doesNotMatch(await response.text(), /foreign|token|127\.0\.0\.1/);
});

test("foreign-audience metadata cannot authorize a private API request", async () => {
  let count = 0;
  const proxy = createApiProxy({ origin: "https://other-api-xyz.a.run.app", identity: true, apiHost: "api.example", fetcher: async () => {
    count++; return new Response("a." + Buffer.from(JSON.stringify({ aud: "foreign", exp: Date.now() / 1000 + 3600 })).toString("base64url") + ".c", { headers: { "Metadata-Flavor": "Google" } });
  } });
  assert.equal((await proxy(new Request("https://dojo.example/api/session"))).status, 503);
  assert.equal(count, 1);
});

test("cloud gateway rejects cross-origin writes before identity or upstream requests", async () => {
  const proxy = createApiProxy({ origin: "https://dojo-api-abc.a.run.app", identity: true, apiHost: "api.example", fetcher: async () => { throw new Error("must not fetch"); } });
  const response = await proxy(new Request("https://dojo.example/api/assets/owned/preview", { method: "DELETE", headers: { Origin: "https://foreign.example", Cookie: "sessionid=owned", "X-CSRFToken": "owned" } }));
  assert.equal(response.status, 403);
});
