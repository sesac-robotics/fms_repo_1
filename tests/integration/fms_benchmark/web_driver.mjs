// Drive the actual Vue search forms in a separate Chrome process.
import assert from "node:assert/strict";
import { appendFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { setTimeout as wait } from "node:timers/promises";

const [origin, trace, start, duration] = process.argv.slice(2);
const { chromium } = await import(pathToFileURL(process.env.AMO_BENCH_PLAYWRIGHT));
const browser = await chromium.launch({
  executablePath: process.env.AMO_BENCH_CHROME,
  headless: false,
});
try {
  const page = await browser.newPage({ viewport: { width: 900, height: 780 } });
  await page.addInitScript(() => {
    localStorage.setItem("amo.admin.preferences", JSON.stringify({ locale: "en", tutorialEnabled: false }));
  });
  const started = new WeakMap();
  page.on("request", (request) => started.set(request, performance.now()));
  page.on("requestfinished", async (request) => {
    const url = new URL(request.url());
    if (!url.pathname.startsWith("/api/")) return;
    const response = await request.response();
    appendFileSync(trace, JSON.stringify({
      endpoint: url.pathname, searched: Boolean(url.searchParams.get("q")), status: response.status(),
      elapsed_ms: performance.now() - started.get(request)
    }) + "\n");
  });
  await page.goto(origin);
  await page.locator('input[type="email"]').fill("admin@amo.test");
  await page.locator('input[type="password"]').fill(process.env.AMO_BENCH_DEMO_PASSWORD);
  await page.locator("form button.primary").first().click();
  await page.locator("aside.sidebar nav button").first().waitFor();
  const dialog = page.locator("dialog[open]");
  if (await dialog.count()) await page.keyboard.press("Escape");
  const workload = [
    ["Members and roles", "bench-passenger-999", "/api/admin/members/page"],
    ["Trip history", "ONE_WAY", "/api/operations/trip-history"],
    ["Test results", "Benchmark", "/api/operations/test-history"],
  ];
  const schedule = Number(duration) >= 42 ? [...workload, ...workload] : workload;
  for (const [index, [menu, query, endpoint]] of schedule.entries()) {
    await wait(Math.max(0, Number(start) * 1000 + 3000 + index * 7000 - Date.now()));
    await page.locator("aside.sidebar nav button").filter({ hasText: menu }).click();
    const form = page.locator("section.panel form").first();
    await form.locator('button:enabled').first().waitFor();
    await form.locator('input:not([type="date"])').first().fill(query);
    const response = page.waitForResponse((r) => {
      const url = new URL(r.url());
      return url.pathname === endpoint && url.searchParams.get("q") === query;
    });
    await form.locator("button").first().click();
    assert.equal((await response).status(), 200);
  }
} finally {
  await browser.close();
}
