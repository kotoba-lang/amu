#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { chmodSync, existsSync, readFileSync, mkdtempSync, rmSync, statSync, writeFileSync } from "node:fs";
import { cpus, tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { assessComparatorCoverage } from "./runtime-multidomain-evidence.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-multidomain-test-"));
const bundle = join(directory, "prepared");
const script = join(root, "scripts", "runtime-multidomain-suite.mjs");
const manifest = JSON.parse(readFileSync(join(root, "bench", "runtime-comparison",
  "multidomain-suite.json"), "utf8"));

function syntheticRustDomain(required) {
  const hash = "a".repeat(64);
  return {
    id: required.id, fixture: required.fixture,
    knownAnswer: { benchmark: required.knownAnswer, result: 42, verifiedBy: ["rust"] },
    contract: { rotation: "all-engine-pairs ABBA/BAAB per run",
      rustOptimization: "rustc --edition 2021 -C opt-level=3 -C codegen-units=1 -C strip=symbols" },
    artifacts: { rust: { sha256: hash }, rustSource: { sha256: hash } },
    environment: { rustc: "rustc test-version" },
    engines: { rust: { samples: [{ result: 42 }] } },
  };
}

function run(args, env = {}, expectSuccess = true) {
  const result = spawnSync(process.execPath, [script, ...args], {
    cwd: root, encoding: "utf8", timeout: 900_000, maxBuffer: 64 * 1024 * 1024,
    env: { ...process.env, ...env },
  });
  if (result.error) throw result.error;
  if (expectSuccess && result.status !== 0)
    throw new Error(`multidomain suite failed\n${result.stdout}${result.stderr}`);
  if (!expectSuccess && result.status === 0)
    throw new Error("multidomain suite unexpectedly accepted invalid evidence");
  return result;
}

try {
  const prepared = run(["--n", "200", "--prepare", bundle]);
  const preparedReport = JSON.parse(prepared.stdout);
  if (preparedReport.domainCount !== 6)
    throw new Error("prepare did not seal all required domains");
  const nonempty = run(["--n", "200", "--prepare", bundle], {}, false);
  if (!`${nonempty.stdout}${nonempty.stderr}`.includes("absent or empty"))
    throw new Error("prepare did not reject a non-empty target");

  // This interceptor proves measurement never reaches either compiler verb;
  // perfgate's non-compiler Clojure invocation is delegated unchanged.
  const tools = join(directory, "tools");
  const marker = join(directory, "compiler-ran");
  if (spawnSync("mkdir", ["-p", tools]).status !== 0)
    throw new Error("could not create compiler interceptor");
  const realClojure = spawnSync("sh", ["-c", "command -v clojure"], { encoding: "utf8" }).stdout.trim();
  const wrapper = join(tools, "clojure");
  writeFileSync(wrapper, `#!/bin/sh\ncase " $* " in *" compile "*|*" extract-native "*) : > "${marker}";; esac\nexec "${realClojure}" "$@"\n`);
  chmodSync(wrapper, 0o755);

  const output = join(directory, "report.json");
  run(["--runs", "1", "--calls", "1000", "--n", "200", "--measure", bundle,
    "--bundle-sha256", preparedReport.bundleSha256,
    "--quiet-wait-ms", "10", "--output", output],
  { AMU_BENCH_TEST_LOAD_SAMPLES: "0,0,0", PATH: `${tools}:${process.env.PATH}` });
  if (existsSync(marker)) throw new Error("a compiler ran during measure");
  const report = JSON.parse(readFileSync(output, "utf8"));
  if (report.format !== "kotoba.runtime-multidomain-report/v1")
    throw new Error("wrong multidomain report format");
  if (!report.contract.complete || report.contract.requiredDomainCount !== 6
      || report.contract.measuredDomainCount !== 6)
    throw new Error("required multidomain set is incomplete");
  if (report.contract.workflow !== "prepare-all -> bounded quiet gate -> measure sealed bundles"
      || report.qualification.quietGate.samples.length < 3)
    throw new Error("two-phase quiet gate was not recorded");
  if (!/^[0-9a-f]{64}$/.test(report.manifest.sha256))
    throw new Error("manifest identity is not sealed");
  for (const domain of report.domains) {
    if (domain.contract.rotation !== "all-engine-pairs ABBA/BAAB per run"
        || domain.contract.samplesPerEngine !== 2)
      throw new Error(`${domain.id} did not use the paired rotation`);
    if (domain.knownAnswer.verifiedBy.join(",") !== "amu-wasm32,amu-native")
      throw new Error(`${domain.id} did not verify both core engines`);
    if (domain.environment.preparedBundle?.buildPhaseEnteredDuringMeasure !== false)
      throw new Error(`${domain.id} did not prove compiler-free measurement`);
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

  const perfgateInput = join(directory, "perfgate-domain-host-load.json");
  writeFileSync(perfgateInput, `${JSON.stringify({
    format: "kotoba.runtime-multidomain-report/v1", suite: manifest.id,
    contract: { complete: true }, qualification: { hostLoadQualified: true },
    externalComparators: { rust: { complete: true } },
    domains: [{ id: "narrow-arithmetic", fixture: "kernel",
      qualification: { hostLoad: { qualified: false } },
      engines: {
        "amu-wasm32": { samples: Array.from({ length: 5 }, () => ({ nanosecondsPerKernel: 100 })) },
        "amu-native": { samples: Array.from({ length: 5 }, () => ({ nanosecondsPerKernel: 90 })) },
        rust: { samples: Array.from({ length: 5 }, () => ({ nanosecondsPerKernel: 100 })) },
      } }],
  })}\n`);
  const bridge = spawnSync("bash", [join(root, "scripts", "perfgate-qualify.sh"), perfgateInput],
    { cwd: root, encoding: "utf8", timeout: 300_000, maxBuffer: 32 * 1024 * 1024 });
  if (bridge.status !== 0) throw new Error(`perfgate bridge failed\n${bridge.stdout}${bridge.stderr}`);
  const tamperedGate = JSON.parse(bridge.stdout);
  if (tamperedGate["host-load-qualified?"] || tamperedGate["all-domains-perfgate-qualified?"]
      || tamperedGate.domains[0].verdict["qualified?"]
      || tamperedGate["rust-comparison-qualified?"]
      || tamperedGate["broad-fastest-claim-qualified?"]
      || tamperedGate["external-comparators"].rust.domains[0].verdict["qualified?"])
    throw new Error("perfgate must fail closed when a domain host-load gate is false");

  const synthetic = manifest.requiredDomains.map(syntheticRustDomain);
  if (!assessComparatorCoverage(manifest, synthetic).complete)
    throw new Error("complete Rust coverage was rejected");
  if (assessComparatorCoverage(manifest, synthetic.slice(0, -1)).complete)
    throw new Error("missing Rust domain was accepted");
  const wrong = structuredClone(synthetic);
  wrong[2].engines.rust.samples[0].result = 41;
  let wrongRejected = false;
  try { assessComparatorCoverage(manifest, wrong); }
  catch (error) { wrongRejected = /known-answer rejection/.test(error.message); }
  if (!wrongRejected) throw new Error("wrong Rust answer was accepted");

  const firstBundle = join(bundle, "narrow-arithmetic.bundle");
  const provenancePath = join(firstBundle, "kernel.kexe.provenance.edn");
  const metadataPath = join(firstBundle, "bundle.json");
  const indexPath = join(bundle, "multidomain-bundle.json");
  const provenance = readFileSync(provenancePath);
  const metadataBytes = readFileSync(metadataPath);
  const indexBytes = readFileSync(indexPath);
  writeFileSync(provenancePath, Buffer.concat([provenance, Buffer.from("tampered")]));
  const tampered = run(["--runs", "1", "--calls", "1000", "--n", "200",
    "--measure", bundle, "--bundle-sha256", preparedReport.bundleSha256,
    "--quiet-wait-ms", "0"],
  { AMU_BENCH_TEST_LOAD_SAMPLES: "0,0,0" }, false);
  if (!`${tampered.stdout}${tampered.stderr}`.includes("hash mismatch"))
    throw new Error("tampered bundle did not fail at its hash gate");

  const stale = provenance.toString().replace(/:source-sha256\s+"[0-9a-f]{64}"/,
    `:source-sha256 "${"0".repeat(64)}"`);
  writeFileSync(provenancePath, stale);
  const metadata = JSON.parse(metadataBytes);
  metadata.files["kernel.kexe.provenance.edn"] = {
    bytes: statSync(provenancePath).size,
    sha256: createHash("sha256").update(readFileSync(provenancePath)).digest("hex"),
  };
  writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
  const rewrittenChildDigest = createHash("sha256").update(readFileSync(metadataPath)).digest("hex");
  const rewrittenIndex = JSON.parse(indexBytes);
  rewrittenIndex.domains.find(value => value.id === "narrow-arithmetic").bundleSha256 = rewrittenChildDigest;
  writeFileSync(indexPath, `${JSON.stringify(rewrittenIndex, null, 2)}\n`);
  const rewrittenIndexDigest = createHash("sha256").update(readFileSync(indexPath)).digest("hex");
  const staleRun = run(["--runs", "1", "--calls", "1000", "--n", "200",
    "--measure", bundle, "--bundle-sha256", rewrittenIndexDigest,
    "--quiet-wait-ms", "0"],
  { AMU_BENCH_TEST_LOAD_SAMPLES: "0,0,0" }, false);
  if (!`${staleRun.stdout}${staleRun.stderr}`.includes("does not identify its sealed source"))
    throw new Error("stale provenance did not fail closed");
  writeFileSync(provenancePath, provenance);
  writeFileSync(metadataPath, metadataBytes);
  writeFileSync(indexPath, indexBytes);

  const escapingMetadata = JSON.parse(metadataBytes);
  escapingMetadata.files["../outside"] = escapingMetadata.files["source.kotoba"];
  writeFileSync(metadataPath, `${JSON.stringify(escapingMetadata, null, 2)}\n`);
  const escapingChildDigest = createHash("sha256").update(readFileSync(metadataPath)).digest("hex");
  const escapingIndex = JSON.parse(indexBytes);
  escapingIndex.domains.find(value => value.id === "narrow-arithmetic").bundleSha256 = escapingChildDigest;
  writeFileSync(indexPath, `${JSON.stringify(escapingIndex, null, 2)}\n`);
  const escapingIndexDigest = createHash("sha256").update(readFileSync(indexPath)).digest("hex");
  const escapingRun = run(["--runs", "1", "--calls", "1000", "--n", "200",
    "--measure", bundle, "--bundle-sha256", escapingIndexDigest,
    "--quiet-wait-ms", "0"], { AMU_BENCH_TEST_LOAD_SAMPLES: "0,0,0" }, false);
  if (!`${escapingRun.stdout}${escapingRun.stderr}`.includes("path escapes its root"))
    throw new Error("bundle path traversal did not fail closed");
  writeFileSync(metadataPath, metadataBytes);
  writeFileSync(indexPath, indexBytes);

  const high = String(cpus().length * 2);
  const overloadedPath = join(directory, "overloaded.json");
  run(["--runs", "2", "--calls", "2000", "--n", "200", "--measure", bundle,
    "--bundle-sha256", preparedReport.bundleSha256,
    "--quiet-wait-ms", "0", "--output", overloadedPath],
  { AMU_BENCH_TEST_LOAD_SAMPLES: `${high},${high},${high}` });
  const overloaded = JSON.parse(readFileSync(overloadedPath, "utf8"));
  if (overloaded.qualification.quietGate.qualified
      || overloaded.qualification.quietGate.reason !== "quiet-host-timeout"
      || overloaded.qualification.hostLoadQualified
      || overloaded.qualification.perfgate["all-domains-perfgate-qualified?"])
    throw new Error("timeout/high-load evidence did not fail closed");

  process.stdout.write("runtime-multidomain: sealed prepare/measure, tamper, provenance, quiet timeout, compiler-free timing, known answers, rotation and perfgate OK\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
