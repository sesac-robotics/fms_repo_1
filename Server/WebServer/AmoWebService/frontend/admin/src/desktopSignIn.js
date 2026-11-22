const requestValue = /^[A-Za-z0-9_-]{43}$/;
const stateValue = /^[A-Za-z0-9_-]{32,128}$/;

/** Reads and validates the single callback request created by the native app. */
export function desktopRequest(search) {
  const query = new URLSearchParams(search);
  const fields = ["port", "challenge", "state"];
  if (fields.some((key) => query.getAll(key).length !== 1)) return null;
  const rawPort = query.get("port");
  const port = Number(rawPort);
  const challenge = query.get("challenge");
  const state = query.get("state");
  if (
    !/^\d{4,5}$/.test(rawPort) ||
    port < 1024 ||
    port > 65535 ||
    !requestValue.test(challenge) ||
    !stateValue.test(state)
  ) {
    return null;
  }
  return { port, challenge, state };
}

/** Builds a top-level loopback callback without accepting a redirect URL. */
export function desktopCallback(request, code) {
  if (code !== undefined && !requestValue.test(code)) {
    throw new Error("Invalid desktop authorization code");
  }
  const query = new URLSearchParams({ state: request.state });
  if (code === undefined) query.set("error", "access_denied");
  else query.set("code", code);
  return `http://127.0.0.1:${request.port}/amo-callback?${query}`;
}
