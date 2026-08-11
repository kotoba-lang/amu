import { test, expect } from "@playwright/test";

test("compiler-produced Wasm passes direct and Worker boundaries", async ({ page, browser, browserName }, testInfo) => {
  const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.goto("/index.html");
  await expect(page.locator("#status")).toHaveAttribute("data-result", "passed", { timeout: 15000 });
  const report = JSON.parse(await page.locator("#report").textContent());
  expect(report).toEqual({
    format: "kotoba.browser-conformance/v1",
    direct: "ok",
    worker: "ok",
    capability: "allowed-and-denied",
    heap: { heap: { capacity: 4096, used: 2 } },
    forged: "invalid-pair-handle"
  });
  expect(pageErrors).toEqual([]);
  const project = testInfo.project.name;
  // "-beta-" projects are the same vendor-branded Chrome/Edge builds as "-stable-", just
  // pinned to the beta release channel instead of stable (see playwright.config.mjs for
  // why this is forward-looking pre-stable signal, not previous-version compatibility).
  const evidenceKind = project.includes("-stable-") ? "branded-browser"
    : project.includes("-beta-") ? "branded-browser-beta"
    : project.includes("-emulation") ? "mobile-emulation" : "engine";
  testInfo.annotations.push({
    type: "kotoba-browser-identity",
    description: JSON.stringify({ project, browserName, version: browser.version(), evidenceKind })
  });
});

test("a .kotoba app answers real browser events", async ({ page }) => {
  const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.goto("/tests/browser/app.html");
  await expect(page.locator("#status")).toHaveAttribute("data-result", "passed", { timeout: 15000 });

  // The guest is ungranted, its attributes reached the DOM, and the three
  // exclusions ADR 0025 names stay closed against a real browser DOM.
  expect(JSON.parse(await page.locator("#report").textContent())).toEqual({
    format: "kotoba.dom-app-conformance/v1",
    capabilities: 0,
    labelled: "ok",
    handler: "invalid-ui-document",
    style: "invalid-ui-document",
    url: "invalid-ui-document",
    safeUrl: "accepted",
    mounted: "ok"
  });

  const app = page.locator("#app");
  const items = app.locator("li");
  await expect(items).toHaveCount(2);
  await expect(app.locator("p.count")).toHaveText("2 left");

  // Typing and clicking are real trusted events. Nothing in the page scripted
  // them, so reaching the guest means the whole path held: listener ->
  // nominal data-k -> step -> new state -> reconcile.
  await app.locator('[data-k="draft"]').fill("prove the loop");
  await app.locator('[data-k="add"]').click();
  await expect(items).toHaveCount(3);
  await expect(items.nth(2)).toContainText("prove the loop");
  await expect(app.locator('[data-k="draft"]')).toHaveValue("");

  // State the guest owns survives a re-render it did not ask for.
  await app.locator('[data-k="tc"]').click();
  await expect(items.nth(2).locator("button.toggle")).toHaveText("[x]");

  await app.locator('[data-k="f-active"]').click();
  await expect(items).toHaveCount(1);
  await expect(items.nth(0)).toContainText("carry a click back to the guest");

  await app.locator('[data-k="f-all"]').click();
  await app.locator('[data-k="da"]').click();
  await expect(items).toHaveCount(2);
  await expect(app.locator("p.count")).toHaveText("2 left");

  expect(pageErrors).toEqual([]);
});

test("CSP without wasm-unsafe-eval blocks Wasm compilation", async ({ page }) => {
  await page.goto("/tests/browser/csp-blocked.html");
  await expect(page.locator("#status")).toHaveAttribute("data-result", "passed");
  await expect(page.locator("#status")).toHaveText("wasm-blocked");
});
