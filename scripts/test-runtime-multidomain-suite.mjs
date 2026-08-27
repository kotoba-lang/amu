#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { readFileSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { assessComparatorCoverage } from "./runtime-multidomain-evidence.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-multidomain-test-"));
const manifest = JSON.parse(readFileSync(join(root, "bench", "runtime-comparison",
  "multidomain-suite.json"), "utf8"));

function syntheticRustDomain(required) {
  const hash = "a".repeat(64);
  return {
    id: required.id,
    fixture: required.fixture,
    knownAnswer: { benchmark: required.knownAnswer, result: 42, verifiedBy: ["rust"] },
    contract: {
      rotation: "all-engine-pairs ABBA/BAAB per run",
      rustOptimization: "rustc --edition 2021 -C opt-level=3 -C codegen-units=1 -C strip=symbols",
    },
    artifacts: { rust: { sha256: hash }, rustSource: { sha256: hash } },
    environment: { rustc: "rustc test-version" },
    engines: { rust: { samples: [{ result: 42 }] } },
  };
}

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
    if (domain.contract.rotation !== "all-engine-pairs ABBA/BAAB per run"
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

  const tamperedInput = join(directory, "perfgate-domain-host-load.json");
  writeFileSync(tamperedInput, `${JSON.stringify({
    format: "kotoba.runtime-multidomain-report/v1",
    suite: "amu-native-core-multidomain-v1",
    contract: { complete: true },
    qualification: { hostLoadQualified: true },
    externalComparators: { rust: { complete: true } },
    domains: [{
      id: "narrow-arithmetic",
      fixture: "kernel",
      qualification: { hostLoad: { qualified: false } },
      engines: {
        "amu-wasm32": { samples: Array.from({ length: 5 }, () => ({ nanosecondsPerKernel: 100 })) },
        "amu-native": { samples: Array.from({ length: 5 }, () => ({ nanosecondsPerKernel: 90 })) },
        rust: { samples: Array.from({ length: 5 }, () => ({ nanosecondsPerKernel: 100 })) },
      },
    }],
  })}\n`);
  const tamperedBridge = spawnSync("bash",
    [join(root, "scripts", "perfgate-qualify.sh"), tamperedInput],
    { cwd: root, encoding: "utf8", timeout: 300_000, maxBuffer: 32 * 1024 * 1024 });
  if (tamperedBridge.status !== 0)
    throw new Error(`perfgate bridge failed on tampered report\n${tamperedBridge.stdout}${tamperedBridge.stderr}`);
  const tamperedGate = JSON.parse(tamperedBridge.stdout);
  if (tamperedGate["host-load-qualified?"]
      || tamperedGate["all-domains-perfgate-qualified?"]
      || tamperedGate.domains[0].verdict["qualified?"]
      || tamperedGate["rust-comparison-qualified?"]
      || tamperedGate["broad-fastest-claim-qualified?"]
      || tamperedGate["external-comparators"].rust.domains[0].verdict["qualified?"]) {
    throw new Error("perfgate must fail closed when a domain host-load gate is false");
  }

  const synthetic = manifest.requiredDomains.map(syntheticRustDomain);
  const completeRust = assessComparatorCoverage(manifest, synthetic);
  if (!completeRust.complete || completeRust.measuredDomainCount !== 6)
    throw new Error("complete Rust coverage was rejected");
  const missingRust = assessComparatorCoverage(manifest, synthetic.slice(0, -1));
  if (missingRust.complete || missingRust.status !== "incomplete"
      || missingRust.missingDomains.length !== 1)
    throw new Error("one missing Rust domain did not fail closed");
  const wrong = structuredClone(synthetic);
  wrong[2].engines.rust.samples[0].result = 41;
  let wrongAnswerRejected = false;
  try { assessComparatorCoverage(manifest, wrong); }
  catch (error) { wrongAnswerRejected = /known-answer rejection/.test(error.message); }
  if (!wrongAnswerRejected) throw new Error("wrong Rust answer was accepted");

  process.stdout.write("runtime-multidomain: 6 domains, known answers, hashes, rotation, host gate, perfgate and Rust fail-close coverage OK\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
