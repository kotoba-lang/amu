#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { cpus, loadavg, tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { assessComparatorCoverage } from "./runtime-multidomain-evidence.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const manifestPath = join(root, "bench", "runtime-comparison", "multidomain-suite.json");
const manifestBytes = readFileSync(manifestPath);
const manifest = JSON.parse(manifestBytes);

function option(name, fallback) {
  const index = process.argv.lastIndexOf(name);
  return index < 0 ? fallback : process.argv[index + 1];
}

function execute(command, args, timeout = 600_000) {
  const result = spawnSync(command, args, {
    cwd: root, encoding: "utf8", timeout, maxBuffer: 64 * 1024 * 1024,
  });
  if (result.error) throw result.error;
  if (result.status !== 0)
    throw new Error(`${command} ${args.join(" ")} failed (${result.status})\n${result.stdout}${result.stderr}`);
  return result.stdout;
}

const outputPath = option("--output", null);
const suite = option("--suite", "core");
if (!new Set(["core", "competitive"]).has(suite))
  throw new Error("--suite must be core or competitive");
const disabledEngines = option("--disable-engines", "");
const requestedRuns = Number(option("--runs", "5"));
const requestedCalls = Number(option("--calls", "100000"));
const n = Number(option("--n", "200"));
if (!Number.isSafeInteger(requestedRuns) || requestedRuns < 1 || requestedRuns > 30)
  throw new Error("--runs must be an integer from 1 through 30");
if (!Number.isSafeInteger(requestedCalls) || requestedCalls < 1 || requestedCalls > 1_000_000)
  throw new Error("--calls must be an integer from 1 through 1000000");

const logicalCpus = cpus().length;
const initialLoad = loadavg();
const initialLoadQualified = initialLoad[0] <= logicalCpus * 0.75;
const runs = initialLoadQualified ? requestedRuns : 1;
const calls = initialLoadQualified ? requestedCalls : Math.min(requestedCalls, 1_000);
const warmup = initialLoadQualified ? Math.min(10_000, calls) : Math.min(100, calls);
const directory = mkdtempSync(join(tmpdir(), "amu-runtime-multidomain-"));

try {
  const domains = [];
  for (const domain of manifest.requiredDomains) {
    const reportPath = join(directory, `${domain.id}.json`);
    execute(process.execPath, [join(root, "scripts", "runtime-comparison.mjs"),
      "--suite", suite, "--fixture", domain.fixture,
      "--runs", String(runs), "--calls", String(calls),
      "--warmup", String(warmup), "--n", String(n), "--output", reportPath,
      ...(disabledEngines ? ["--disable-engines", disabledEngines] : [])]);
    const report = JSON.parse(readFileSync(reportPath, "utf8"));
    if (report.benchmark !== domain.knownAnswer)
      throw new Error(`${domain.id} benchmark identity drifted`);
    domains.push({
      id: domain.id,
      fixture: domain.fixture,
      knownAnswer: {
        benchmark: report.benchmark,
        n: report.contract.n,
        result: report.contract.expectedResult,
        verifiedBy: Object.keys(report.engines),
      },
      contract: {
        rotation: report.contract.rotation,
        runs: report.contract.runs,
        samplesPerEngine: report.contract.samplesPerEngine,
        calls: report.contract.calls,
        rustOptimization: report.contract.rustOptimization,
      },
      artifacts: report.artifacts,
      environment: report.environment,
      qualification: report.qualification,
      engines: report.engines,
    });
  }

  const hostLoadQualified = initialLoadQualified
    && domains.every(domain => domain.qualification.hostLoad.qualified);
  const rustCoverage = suite === "competitive"
    ? assessComparatorCoverage(manifest, domains, "rust")
    : {
        status: "not-requested", requiredDomainCount: manifest.requiredDomains.length,
        measuredDomainCount: 0, missingDomains: [], toolVersion: null,
        complete: false, evidence: [],
      };
  const report = {
    format: "kotoba.runtime-multidomain-report/v1",
    suite: manifest.id,
    manifest: {
      path: "bench/runtime-comparison/multidomain-suite.json",
      sha256: createHash("sha256").update(manifestBytes).digest("hex"),
    },
    contract: {
      requiredDomainCount: manifest.requiredDomains.length,
      measuredDomainCount: domains.length,
      complete: domains.length === manifest.requiredDomains.length,
      reducedUnderHostLoad: !initialLoadQualified,
      externalComparators: suite === "core"
        ? "not requested; optional adapters are outside the core dependency closure"
        : "optional adapters measured outside the compiler and runtime dependency closure",
    },
    qualification: {
      hostLoadQualified,
      perfgate: null,
      broadFastestClaimQualified: false,
      reason: hostLoadQualified
        ? "core domains complete; no external comparator covers every required domain"
        : "host load failed closed; timings are diagnostic only",
    },
    externalComparators: { rust: rustCoverage },
    domains,
  };
  const perfgateInput = join(directory, "multidomain-input.json");
  writeFileSync(perfgateInput, `${JSON.stringify(report, null, 2)}\n`);
  report.qualification.perfgate = JSON.parse(execute("bash",
    [join(root, "scripts", "perfgate-qualify.sh"), perfgateInput]));
  report.qualification.rustComparisonQualified
    = report.qualification.perfgate["rust-comparison-qualified?"];
  report.qualification.broadFastestClaimQualified = false;
  report.qualification.reason = report.qualification.rustComparisonQualified
    ? "qualified against Rust on all six domains; broad competitor universe remains incomplete"
    : rustCoverage.complete
      ? "Rust covers every domain, but host/perfgate qualification is incomplete"
      : "no external comparator has complete qualified coverage";
  const encoded = `${JSON.stringify(report, null, 2)}\n`;
  if (outputPath) writeFileSync(resolve(outputPath), encoded);
  process.stdout.write(encoded);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
