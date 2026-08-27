#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-multidomain-test-"));

try {
  const output = join(directory, "report.json");
  const run = spawnSync(process.execPath,
    [join(root, "scripts", "runtime-multidomain-suite.mjs"),
      "--runs", "1", "--calls", "1000", "--n", "200", "--output", output],
    { cwd: root, encoding: "utf8", timeout: 900_000, maxBuffer: 64 * 1024 * 1024 });
  if (run.error) throw run.error;
  if (run.status !== 0)
    throw new Error(`multidomain suite failed\n${run.stdout}${run.stderr}`);
  const report = JSON.parse(readFileSync(output, "utf8"));
  if (report.format !== "kotoba.runtime-multidomain-report/v1")
    throw new Error("wrong multidomain report format");
  if (!report.contract.complete || report.contract.requiredDomainCount !== 6
      || report.contract.measuredDomainCount !== 6)
    throw new Error("required multidomain set is incomplete");
  if (!/^[0-9a-f]{64}$/.test(report.manifest.sha256))
    throw new Error("manifest identity is not sealed");
  for (const domain of report.domains) {
    if (domain.contract.rotation !== "ABBA/BAAB per run pair"
        || domain.contract.samplesPerEngine !== 2)
      throw new Error(`${domain.id} did not use the paired rotation`);
    if (domain.knownAnswer.verifiedBy.join(",") !== "amu-wasm32,amu-native")
      throw new Error(`${domain.id} did not verify both core engines`);
    for (const key of ["kotobaSource", "kotobaWasmSource", "amuWasm32",
      "amuNativeKexe", "amuNativeCode", "amuNativeProvenance"]) {
      if (!/^[0-9a-f]{64}$/.test(domain.artifacts[key]?.sha256 ?? ""))
        throw new Error(`${domain.id} omitted ${key} SHA-256`);
    }
  }
  const gate = report.qualification.perfgate;
  if (gate.format !== "amu.multidomain-perfgate-qualification/v1"
      || gate.domains.length !== 6 || gate["domain-set-complete?"] !== true)
    throw new Error("perfgate did not cover the complete domain set");
  if (report.qualification.broadFastestClaimQualified !== false
      || gate["broad-fastest-claim-qualified?"] !== false)
    throw new Error("core evidence manufactured a broad fastest claim");
  if (!report.qualification.hostLoadQualified
      && (gate["host-load-qualified?"] || gate["all-domains-perfgate-qualified?"]))
    throw new Error("perfgate did not fail closed under host load");
  process.stdout.write("runtime-multidomain: 6 domains, known answers, hashes, rotation, host gate and perfgate OK\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
