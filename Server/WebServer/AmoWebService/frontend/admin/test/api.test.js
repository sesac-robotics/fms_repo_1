import assert from "node:assert/strict";
import test from "node:test";
import { api, RequestError } from "../src/api.js";

test("uses the caller cancellation for CSRF and avoids an aborted mutation", async (t) => {
  const controller = new AbortController();
  const requests = [];
  t.mock.method(globalThis, "fetch", async (path, { signal }) => {
    requests.push(path);
    controller.abort();
    signal.throwIfAborted();
  });

  await assert.rejects(
    api("/admin/demo/scenarios/history/reset", {
      method: "POST",
      body: { runs: 1, observations: 2, current: null },
      signal: controller.signal,
    }),
    { name: "AbortError" },
  );
  assert.deepEqual(requests, ["/api/auth/csrf"]);
});

test("preserves an HTTP denial and rejects malformed successful JSON", async (t) => {
  const responses = [new Response("", { status: 403 }), new Response("{")];
  t.mock.method(globalThis, "fetch", async () => responses.shift());
  await assert.rejects(api("/admin/menu"), (error) => {
    return error instanceof RequestError && error.status === 403;
  });
  await assert.rejects(api("/operations"), SyntaxError);
});
