#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
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
const preparePath = option("--prepare", null);
const measurePath = option("--measure", null);
const expectedBundleDigest = option("--bundle-sha256", null);
if (preparePath && measurePath) throw new Error("--prepare and --measure are mutually exclusive");
const requestedRuns = Number(option("--runs", "5"));
const requestedCalls = Number(option("--calls", "100000"));
const n = Number(option("--n", "200"));
const quietWaitMilliseconds = Number(option("--quiet-wait-ms", "60000"));
if (!Number.isSafeInteger(requestedRuns) || requestedRuns < 1 || requestedRuns > 30)
  throw new Error("--runs must be an integer from 1 through 30");
if (!Number.isSafeInteger(requestedCalls) || requestedCalls < 1 || requestedCalls > 1_000_000)
  throw new Error("--calls must be an integer from 1 through 1000000");
if (!Number.isSafeInteger(quietWaitMilliseconds) || quietWaitMilliseconds < 0
    || quietWaitMilliseconds > 60_000)
  throw new Error("--quiet-wait-ms must be an integer from 0 through 60000");

const logicalCpus = cpus().length;
const directory = preparePath ? resolve(preparePath)
  : measurePath ? resolve(measurePath)
    : mkdtempSync(join(tmpdir(), "amu-runtime-multidomain-"));
const temporaryDirectory = !preparePath && !measurePath;
class PreparationComplete extends Error {
  constructor(encoded) { super("preparation complete"); this.encoded = encoded; }
}

function sleep(milliseconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);
}

function waitForQuiet() {
  const limit = logicalCpus * 0.75;
  const injected = process.env.AMU_BENCH_TEST_LOAD_SAMPLES?.split(",").map(Number) ?? null;
  const samples = [];
  const started = Date.now();
  let consecutive = 0;
  for (;;) {
    const value = injected
      ? injected[Math.min(samples.length, injected.length - 1)]
      : loadavg()[0];
    samples.push({ elapsedMilliseconds: Date.now() - started, load1: value,
      qualified: value <= limit });
    consecutive = value <= limit ? consecutive + 1 : 0;
    if (consecutive >= 3) return { qualified: true, limit, requiredConsecutive: 3, samples };
    if (Date.now() - started >= quietWaitMilliseconds)
      return { qualified: false, limit, requiredConsecutive: 3, samples,
        reason: "quiet-host-timeout" };
    sleep(Math.min(injected ? 1 : 1_000, quietWaitMilliseconds - (Date.now() - started)));
  }
}

try {
  // Phase 1: build every fixture before observing whether the host is quiet.
  // This prevents compiler load from being attributed to any timed domain.
  if (!measurePath) {
    if (preparePath && existsSync(directory) && readdirSync(directory).length !== 0)
      throw new Error("--prepare directory must be absent or empty");
    mkdirSync(directory, { recursive: true });
    const preparedDomains = [];
    for (const domain of manifest.requiredDomains) {
      const bundlePath = join(directory, `${domain.id}.bundle`);
      const prepared = JSON.parse(execute(process.execPath, [join(root, "scripts", "runtime-comparison.mjs"),
        "--suite", suite, "--fixture", domain.fixture, "--n", String(n),
        "--prepare", bundlePath,
        ...(disabledEngines ? ["--disable-engines", disabledEngines] : [])]));
      preparedDomains.push({ id: domain.id, fixture: domain.fixture,
        bundle: `${domain.id}.bundle`, bundleSha256: prepared.bundleSha256 });
    }
    const indexPath = join(directory, "multidomain-bundle.json");
    writeFileSync(indexPath, `${JSON.stringify({
      format: "kotoba.runtime-multidomain-prepared/v1",
      suite: manifest.id,
      manifestSha256: createHash("sha256").update(manifestBytes).digest("hex"),
      n, mode: suite,
      domains: preparedDomains,
    }, null, 2)}\n`);
    if (preparePath) {
      const bundleSha256 = createHash("sha256").update(readFileSync(indexPath)).digest("hex");
      const encoded = `${JSON.stringify({ format: "kotoba.runtime-multidomain-prepare-report/v1",
        bundle: directory, bundleSha256,
        domainCount: manifest.requiredDomains.length }, null, 2)}\n`;
      if (outputPath) writeFileSync(resolve(outputPath), encoded);
      throw new PreparationComplete(encoded);
    }
  } else {
    const indexBytes = readFileSync(join(directory, "multidomain-bundle.json"));
    const digest = createHash("sha256").update(indexBytes).digest("hex");
    if (!expectedBundleDigest || digest !== expectedBundleDigest)
      throw new Error(`multidomain bundle SHA-256 ${digest} does not match caller-bound digest`);
    const prepared = JSON.parse(indexBytes);
    if (prepared.format !== "kotoba.runtime-multidomain-prepared/v1"
        || prepared.suite !== manifest.id || prepared.n !== n || prepared.mode !== suite
        || prepared.manifestSha256 !== createHash("sha256").update(manifestBytes).digest("hex"))
      throw new Error("stale or incompatible multidomain prepared bundle");
  }
  const quietGate = waitForQuiet();
  const runs = quietGate.qualified ? requestedRuns : 1;
  const calls = quietGate.qualified ? requestedCalls : Math.min(requestedCalls, 1_000);
  const warmup = quietGate.qualified ? Math.min(10_000, calls) : Math.min(100, calls);

  // Phase 2 consumes only sealed bundles. runtime-comparison verifies every
  // source, executable, KEXE, code and provenance hash before timing.
  const domains = [];
  for (const domain of manifest.requiredDomains) {
    const reportPath = join(directory, `${domain.id}.json`);
    const bundlePath = join(directory, `${domain.id}.bundle`);
    const index = JSON.parse(readFileSync(join(directory, "multidomain-bundle.json"), "utf8"));
    const sealed = index.domains.find(value => value.id === domain.id && value.fixture === domain.fixture);
    if (!sealed || sealed.bundle !== `${domain.id}.bundle`
        || !/^[0-9a-f]{64}$/.test(sealed.bundleSha256))
      throw new Error(`${domain.id} prepared bundle index is incomplete`);
    execute(process.execPath, [join(root, "scripts", "runtime-comparison.mjs"),
      "--suite", suite, "--fixture", domain.fixture,
      "--runs", String(runs), "--calls", String(calls),
      "--warmup", String(warmup), "--n", String(n), "--measure", bundlePath,
      "--bundle-sha256", sealed.bundleSha256,
      "--output", reportPath]);
    const report = JSON.parse(readFileSync(reportPath, "utf8"));
    if (report.benchmark !== domain.knownAnswer)
      throw new Error(`${domain.id} benchmark identity drifted`);
    domains.push({
      id: domain.id,
      fixture: domain.fixture,
      target: {
        os: report.environment.platform,
        architecture: report.environment.architecture,
        isa: report.environment.architecture === "arm64" ? "aarch64"
          : report.environment.architecture === "x64" ? "x86-64" : null,
        execution: "native",
      },
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

  const hostLoadQualified = quietGate.qualified
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
    generatedAt: new Date().toISOString(),
    suite: manifest.id,
    manifest: {
      path: "bench/runtime-comparison/multidomain-suite.json",
      sha256: createHash("sha256").update(manifestBytes).digest("hex"),
    },
    contract: {
      mode: suite,
      claimContract: manifest.claimContract,
      requiredEngines: manifest.requiredEngines,
      requiredComparators: manifest.requiredComparators,
      requiredTargets: manifest.requiredTargets,
      requiredDomainCount: manifest.requiredDomains.length,
      measuredDomainCount: domains.length,
      complete: domains.length === manifest.requiredDomains.length,
      workflow: "prepare-all -> bounded quiet gate -> measure sealed bundles",
      reducedUnderHostLoad: !quietGate.qualified,
      externalComparators: suite === "core"
        ? "not requested; optional adapters are outside the core dependency closure"
        : "optional adapters measured outside the compiler and runtime dependency closure",
    },
    qualification: {
      hostLoadQualified,
      quietGate,
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
} catch (error) {
  if (error instanceof PreparationComplete) process.stdout.write(error.encoded);
  else throw error;
} finally {
  if (temporaryDirectory) rmSync(directory, { recursive: true, force: true });
}
