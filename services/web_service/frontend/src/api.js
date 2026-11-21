export class RequestError extends Error {
    constructor(status) {
        super("Request failed");
        this.status = status;
    }
}

async function readCsrf() {
    const response = await fetch("/api/auth/csrf", {
        credentials: "same-origin",
        signal: AbortSignal.timeout(25000),
        headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    const data = await response.json();
    return data.token ?? null;
}

export async function api(path, { method = "GET", body, signal } = {}) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (!["GET", "HEAD"].includes(method)) {
        const token = await readCsrf();
        if (token) headers["X-XSRF-TOKEN"] = token;
    }
    const response = await fetch("/api" + path, {
        method,
        headers,
        credentials: "same-origin",
        signal: signal
            ? AbortSignal.any([signal, AbortSignal.timeout(25000)])
            : AbortSignal.timeout(25000),
        body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) throw new RequestError(response.status);
    if (response.status === 204) return undefined;
    const value = await response.text();
    return value ? JSON.parse(value) : undefined;
}
