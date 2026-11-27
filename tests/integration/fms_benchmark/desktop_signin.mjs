// Complete a real staff sign-in in an isolated Chrome profile.
import { pathToFileURL } from "node:url";

const [url] = process.argv.slice(2);
const { chromium } = await import(pathToFileURL(process.env.AMO_BENCH_PLAYWRIGHT));
const browser = await chromium.launch({
  executablePath: process.env.AMO_BENCH_CHROME,
  headless: false,
});
try {
  const page = await browser.newPage({ locale: "en-US" });
  await page.goto(url);
  await page.locator('input[type="email"]').fill("admin@amo.test");
  await page.locator('input[type="password"]').fill(process.env.AMO_BENCH_DEMO_PASSWORD);
  await page.locator("form button.primary").click();
  await page.locator("section.sign-card button.primary").click();
  await page.waitForURL("http://127.0.0.1:*/amo-callback?*");
} finally {
  await browser.close();
}
