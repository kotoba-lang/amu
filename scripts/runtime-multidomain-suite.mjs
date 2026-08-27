#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { cpus, loadavg, tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

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
      "--suite", "core", "--fixture", domain.fixture,
      "--runs", String(runs), "--calls", String(calls),
      "--warmup", String(warmup), "--n", String(n), "--output", reportPath]);
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
      },
      artifacts: report.artifacts,
      environment: report.environment,
      qualification: report.qualification,
      engines: report.engines,
    });
  }

  const hostLoadQualified = initialLoadQualified
    && domains.every(domain => domain.qualification.hostLoad.qualified);
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
      externalComparators: "not requested; optional adapters are outside the core dependency closure",
    },
    qualification: {
      hostLoadQualified,
      perfgate: null,
      broadFastestClaimQualified: false,
      reason: hostLoadQualified
        ? "core domains complete; no external comparator covers every required domain"
        : "host load failed closed; timings are diagnostic only",
    },
    domains,
  };
  const perfgateInput = join(directory, "multidomain-input.json");
  writeFileSync(perfgateInput, `${JSON.stringify(report, null, 2)}\n`);
  report.qualification.perfgate = JSON.parse(execute("bash",
    [join(root, "scripts", "perfgate-qualify.sh"), perfgateInput]));
  const encoded = `${JSON.stringify(report, null, 2)}\n`;
  if (outputPath) writeFileSync(resolve(outputPath), encoded);
  process.stdout.write(encoded);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
