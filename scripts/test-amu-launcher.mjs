#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-launcher-test-"));
try {
  const report = join(directory, "report.json");
  const comparison = spawnSync(process.execPath,
    [join(root, "scripts", "launcher-comparison.mjs"), "--runs", "1", "--output", report],
    { cwd: root, encoding: "utf8", timeout: 180_000, maxBuffer: 16 * 1024 * 1024 });
  if (comparison.error) throw comparison.error;
  if (comparison.status !== 0)
    throw new Error(`launcher comparison failed\n${comparison.stdout}${comparison.stderr}`);
  const evidence = JSON.parse(readFileSync(report, "utf8"));
  if (evidence.format !== "amu.launcher-comparison/v1" || evidence.runs !== 1
      || !evidence.parity.artifactSha256 || !evidence.parity.provenanceSha256)
    throw new Error("launcher parity evidence is incomplete");

  const aliasOutput = join(directory, "alias.wasm");
  const alias = spawnSync(process.execPath,
    [join(root, "bin", "amu"), "-M", "compile", "examples/w1-pure.kotoba",
      "--target", "wasm32", "--output", aliasOutput],
    { cwd: root, encoding: "utf8", timeout: 120_000, maxBuffer: 16 * 1024 * 1024 });
  if (alias.error) throw alias.error;
  if (alias.status !== 0 || !alias.stdout.includes(":ok true"))
    throw new Error(`-M compatibility failed\n${alias.stdout}${alias.stderr}`);
  process.stdout.write("amu-launcher: direct and -M commands preserve native artifact/provenance parity\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
