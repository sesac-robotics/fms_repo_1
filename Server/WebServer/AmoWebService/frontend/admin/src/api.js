export class RequestError extends Error {
  /** @param {number} status HTTP status returned by the gateway. */
  constructor(status) {
    super("Request failed");
    this.status = status;
  }
}

async function readCsrf(signal) {
  const response = await fetch("/api/auth/csrf", {
    credentials: "same-origin",
    signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) return null;
  const data = await response.json();
  return data.token ?? null;
}

/**
 * Send a same-origin gateway request with a shared 25-second deadline.
 * @param {string} path Slash-prefixed gateway path without the /api prefix.
 * @param {{method?: string, body?: unknown, signal?: AbortSignal}} options JSON body and optional cancellation.
 * @returns {Promise<unknown>} Parsed JSON, or undefined for an empty response.
 * @throws {RequestError} If the gateway returns a non-success HTTP status.
 * @throws {DOMException|TypeError|SyntaxError} On cancellation, network failure or invalid JSON.
 */
export async function api(path, { method = "GET", body, signal } = {}) {
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new TypeError("Expected a gateway path.");
  }
  const deadline = AbortSignal.timeout(25000);
  const requestSignal = signal ? AbortSignal.any([signal, deadline]) : deadline;
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (!["GET", "HEAD"].includes(method)) {
    const token = await readCsrf(requestSignal);
    if (token) headers["X-XSRF-TOKEN"] = token;
  }
  const response = await fetch("/api" + path, {
    method,
    headers,
    credentials: "same-origin",
    signal: requestSignal,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new RequestError(response.status);
  if (response.status === 204) return undefined;
  const value = await response.text();
  return value ? JSON.parse(value) : undefined;
}
