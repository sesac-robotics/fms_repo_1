import assert from "node:assert/strict";
import test from "node:test";
import { desktopCallback, desktopRequest } from "../src/desktopSignIn.js";

const challenge = "a".repeat(43);
const state = "b".repeat(43);
const code = "c".repeat(43);
const valid = `?port=54321&challenge=${challenge}&state=${state}`;

test("only accepts one loopback port, S256 challenge and correlation state", () => {
  assert.deepEqual(desktopRequest(valid), { port: 54321, challenge, state });
  assert.equal(desktopRequest(valid + "&port=44321"), null);
  assert.equal(desktopRequest(valid.replace("54321", "65536")), null);
  assert.equal(desktopRequest(valid.replace("54321", "0800")), null);
  assert.equal(desktopRequest(valid.replace(challenge, "short")), null);
  assert.equal(desktopRequest(valid.replace(state, "bad.state")), null);
});

test("only navigates to the IPv4 loopback path and returns no access token", () => {
  const request = desktopRequest(valid + "&redirect=https%3A%2F%2Fexample.org");
  const success = new URL(desktopCallback(request, code));
  assert.equal(success.origin, "http://127.0.0.1:54321");
  assert.equal(success.pathname, "/amo-callback");
  assert.deepEqual(
    [...success.searchParams],
    [
      ["state", state],
      ["code", code],
    ],
  );
  const cancel = new URL(desktopCallback(request));
  assert.deepEqual(
    [...cancel.searchParams],
    [
      ["state", state],
      ["error", "access_denied"],
    ],
  );
  assert.throws(() => desktopCallback(request, "unsafe"));
});
