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
const manifestSha256 = createHash("sha256").update(readFileSync(join(root, "bench",
  "runtime-comparison", "multidomain-suite.json"))).digest("hex");
const nativeArtifactAbi = "kotoba.native-artifact-i64x8-to-i64-indirect/v1";

function syntheticRustDomain(required) {
  const hash = "a".repeat(64);
  return {
    id: required.id, fixture: required.fixture,
    knownAnswer: { benchmark: required.knownAnswer, result: 42, verifiedBy: ["rust"] },
    contract: { rotation: "all-engine-pairs ABBA/BAAB per run",
      nativeArtifactAbi,
      rustOptimization: "rustc --edition 2021 --crate-type cdylib -C opt-level=3 -C codegen-units=1 -C strip=symbols" },
    artifacts: { rust: { sha256: hash }, rustSource: { sha256: hash } },
    environment: { rustc: "rustc test-version" },
    engines: { rust: { samples: [{ result: 42, nativeArtifactAbi }] } },
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

function syntheticCompetitiveReport() {
  const generatedAt = new Date().toISOString();
  const hash = "b".repeat(64);
  const samples = (value, artifactKind, fuelConsumed) => Array.from({ length: 5 }, () => ({
    result: 42, nanosecondsPerKernel: value, nativeArtifactAbi,
    artifactKind,
    contextFuelBefore: 1_048_576, contextFuelAfter: 1_048_576 - fuelConsumed,
    contextFuelConsumed: fuelConsumed,
  }));
  return {
    format: "kotoba.runtime-multidomain-report/v1",
    generatedAt,
    suite: manifest.id,
    manifest: { path: "bench/runtime-comparison/multidomain-suite.json", sha256: manifestSha256 },
    contract: {
      mode: "competitive",
      claimContract: manifest.claimContract,
      requiredEngines: manifest.requiredEngines,
      requiredComparators: manifest.requiredComparators,
      requiredTargets: manifest.requiredTargets,
      preparedIndexSha256: hash,
      // These booleans are deliberately false: the bridge must derive completeness.
      complete: false,
    },
    qualification: { hostLoadQualified: true },
    externalComparators: { rust: { complete: false } },
    domains: manifest.requiredDomains.map(required => ({
      id: required.id,
      fixture: required.fixture,
      target: { os: "darwin", architecture: "arm64", isa: "aarch64", execution: "native" },
      knownAnswer: { benchmark: required.knownAnswer, n: 200, result: 42,
        verifiedBy: ["amu-wasm32", "amu-native", "rust"] },
      contract: { rotation: "all-engine-pairs ABBA/BAAB per run",
        nativeArtifactAbi,
        nativeArtifactArgMap: manifest.claimContract.nativeArtifactArgMap,
        nativeRunnerCompiler: manifest.claimContract.nativeRunnerCompiler,
        fuelPerInstance: 1_048_576,
        nativeArtifactTarget: "aarch64",
        preparedBundleSha256: hash,
        semanticVectors: required.verificationInputs.map((input, index) => ({
          input, expectedResult: required.verificationResults[index],
          verifiedBy: ["amu-native", "rust"],
          arms: {
            "amu-native": { result: required.verificationResults[index], nativeArtifactAbi,
              artifactKind: "raw", contextFuelConsumed: required.verificationAmuFuelConsumed[index] },
            rust: { result: required.verificationResults[index], nativeArtifactAbi,
              artifactKind: "dylib", contextFuelConsumed: 0 },
          },
        })),
        rustOptimization: "rustc --edition 2021 --crate-type cdylib -C opt-level=3 -C codegen-units=1 -C strip=symbols" },
      artifacts: {
        amuNativeKexe: { sha256: hash }, amuNativeCode: { sha256: hash },
        amuNativeProvenance: { sha256: hash }, rust: { sha256: hash },
        rustSource: { sha256: hash }, nativeBenchmarkRunner: { sha256: hash },
        nativeBenchmarkRunnerSource: { sha256: hash },
      },
      environment: {
        platform: "darwin", architecture: "arm64", cpu: "Synthetic Apple M4",
        logicalCpus: 10, compilerCommit: "c".repeat(40), compilerDirty: false,
        rustcVerbose: "rustc test-version\nhost: aarch64-apple-darwin",
        cc: "Apple clang version test",
        preparedBundle: { preparedAt: generatedAt, buildPhaseEnteredDuringMeasure: false },
      },
      qualification: { hostLoad: { qualified: true } },
      engines: {
        "amu-wasm32": { samples: samples(120, "wasm", 0) },
        "amu-native": { samples: samples(80, "raw",
          required.verificationAmuFuelConsumed[required.verificationInputs.indexOf(200)]) },
        rust: { samples: samples(100, "dylib", 0) },
      },
    })),
  };
}

function bridgeReport(report, expectSuccess = true) {
  const input = join(directory, `perfgate-${Math.random().toString(16).slice(2)}.json`);
  writeFileSync(input, `${JSON.stringify(report)}\n`);
  const result = spawnSync("bash", [join(root, "scripts", "perfgate-qualify.sh"), input],
    { cwd: root, encoding: "utf8", timeout: 300_000, maxBuffer: 32 * 1024 * 1024 });
  if (expectSuccess && result.status !== 0)
    throw new Error(`perfgate bridge failed\n${result.stdout}${result.stderr}`);
  if (!expectSuccess && result.status === 0)
    throw new Error("perfgate bridge accepted adversarial evidence");
  return expectSuccess ? JSON.parse(result.stdout) : result;
}

function validateManifestV1(value, expectSuccess = true) {
  const input = join(directory, `manifest-${Math.random().toString(16).slice(2)}.json`);
  writeFileSync(input, `${JSON.stringify(value)}\n`);
  const result = spawnSync("bash", [join(root, "scripts", "perfgate-qualify.sh"),
    "--validate-manifest-v1", input],
  { cwd: root, encoding: "utf8", timeout: 300_000, maxBuffer: 32 * 1024 * 1024 });
  if (expectSuccess && result.status !== 0)
    throw new Error(`v1 manifest validation failed\n${result.stdout}${result.stderr}`);
  if (!expectSuccess && result.status === 0)
    throw new Error("v1 manifest validator accepted an expanded contract");
}

try {
  validateManifestV1(manifest);
  const otherComparator = structuredClone(manifest);
  otherComparator.requiredComparators = ["go"];
  validateManifestV1(otherComparator, false);
  const otherEngine = structuredClone(manifest);
  otherEngine.requiredEngines = ["amu-wasm32"];
  validateManifestV1(otherEngine, false);
  const multipleTargets = structuredClone(manifest);
  multipleTargets.requiredTargets.push({ id: "darwin-x86-64-native", os: "darwin",
    architecture: "x64", isa: "x86-64", execution: "native" });
  validateManifestV1(multipleTargets, false);

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
      || report.qualification.quietGate.samples.length < 3
      || report.qualification.quietGate.limit !== Math.min(1, cpus().length * 0.10)
      || report.qualification.quietGate.policy
        !== "load1 <= min(1.0, logical-cpus * 0.10)")
    throw new Error("two-phase quiet gate was not recorded");
  if (!/^[0-9a-f]{64}$/.test(report.manifest.sha256))
    throw new Error("manifest identity is not sealed");
  for (const domain of report.domains) {
    if (domain.contract.rotation !== "all-engine-pairs ABBA/BAAB per run"
        || domain.contract.samplesPerEngine !== 2
        || domain.contract.nativeArtifactAbi !== nativeArtifactAbi)
      throw new Error(`${domain.id} did not use the paired rotation`);
    if (domain.engines["amu-native"].samples.some(
      sample => sample.nativeArtifactAbi !== nativeArtifactAbi || sample.artifactKind !== "raw"))
      throw new Error(`${domain.id} Amu did not cross the common native artifact ABI`);
    if (domain.contract.semanticVectors.map(vector => vector.input).join(",")
        !== manifest.requiredDomains.find(required => required.id === domain.id)
          .verificationInputs.join(","))
      throw new Error(`${domain.id} semantic vector corpus drifted`);
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

  const qualifiedEvidence = syntheticCompetitiveReport();
  const qualifiedGate = bridgeReport(qualifiedEvidence);
  if (!qualifiedGate["bounded-fastest-claim-qualified?"]
      || !/^[0-9a-f]{64}$/.test(qualifiedGate["bounded-fastest-claim"]?.sha256 ?? "")
      || qualifiedGate["bounded-fastest-claim"].body["allowed-sentence"]
        !== manifest.claimContract.allowedSentence
      || qualifiedGate["broad-fastest-claim-qualified?"] !== false)
    throw new Error("fully bound enumerated-universe evidence did not emit exactly one bounded claim");

  const originalClaim = qualifiedGate["bounded-fastest-claim"];
  const artifactChanged = structuredClone(qualifiedEvidence);
  artifactChanged.domains[0].artifacts.rust.sha256 = "d".repeat(64);
  const artifactChangedClaim = bridgeReport(artifactChanged)["bounded-fastest-claim"];
  if (artifactChangedClaim.body["evidence-report"].sha256
        === originalClaim.body["evidence-report"].sha256
      || artifactChangedClaim.sha256 === originalClaim.sha256)
    throw new Error("artifact SHA substitution did not change the evidence and claim addresses");

  const knownAnswerChanged = structuredClone(qualifiedEvidence);
  knownAnswerChanged.domains[0].knownAnswer.result = 43;
  for (const engine of Object.values(knownAnswerChanged.domains[0].engines))
    for (const sample of engine.samples) sample.result = 43;
  const knownAnswerChangedClaim = bridgeReport(knownAnswerChanged)["bounded-fastest-claim"];
  if (knownAnswerChangedClaim.body["evidence-report"].sha256
        === originalClaim.body["evidence-report"].sha256
      || knownAnswerChangedClaim.sha256 === originalClaim.sha256)
    throw new Error("known-answer substitution did not change the evidence and claim addresses");

  const oneDomain = syntheticCompetitiveReport();
  oneDomain.contract.complete = true;
  oneDomain.externalComparators.rust.complete = true;
  oneDomain.domains = oneDomain.domains.slice(0, 1);
  bridgeReport(oneDomain, false);

  const duplicate = syntheticCompetitiveReport();
  duplicate.domains[duplicate.domains.length - 1] = structuredClone(duplicate.domains[0]);
  bridgeReport(duplicate, false);

  const missingTargetEngine = syntheticCompetitiveReport();
  delete missingTargetEngine.domains[0].engines["amu-native"];
  bridgeReport(missingTargetEngine, false);

  const missingPhysicalTarget = syntheticCompetitiveReport();
  delete missingPhysicalTarget.domains[0].target;
  bridgeReport(missingPhysicalTarget, false);

  const missingComparator = syntheticCompetitiveReport();
  delete missingComparator.domains[0].engines.rust;
  bridgeReport(missingComparator, false);

  const directComparator = syntheticCompetitiveReport();
  delete directComparator.domains[0].engines.rust.samples[0].nativeArtifactAbi;
  bridgeReport(directComparator, false);

  const driftedAbi = syntheticCompetitiveReport();
  driftedAbi.domains[0].contract.nativeArtifactAbi = "direct-rust-call/v0";
  bridgeReport(driftedAbi, false);

  const constantComparator = syntheticCompetitiveReport();
  for (const vector of constantComparator.domains[0].contract.semanticVectors)
    vector.arms.rust.result = constantComparator.domains[0].contract.semanticVectors[0].expectedResult;
  bridgeReport(constantComparator, false);

  const wrongFuel = syntheticCompetitiveReport();
  wrongFuel.domains.at(-1).contract.semanticVectors.at(-1)
    .arms["amu-native"].contextFuelConsumed -= 1;
  bridgeReport(wrongFuel, false);

  const staleManifest = syntheticCompetitiveReport();
  staleManifest.manifest.sha256 = "0".repeat(64);
  bridgeReport(staleManifest, false);

  const dirty = syntheticCompetitiveReport();
  dirty.domains[0].environment.compilerDirty = true;
  const dirtyGate = bridgeReport(dirty);
  if (dirtyGate["bounded-fastest-claim-qualified?"]
      || dirtyGate["bounded-fastest-claim"] !== null || dirtyGate["evidence-clean?"])
    throw new Error("dirty evidence emitted a bounded claim");

  const staleReport = syntheticCompetitiveReport();
  const staleAt = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();
  staleReport.generatedAt = staleAt;
  for (const domain of staleReport.domains) domain.environment.preparedBundle.preparedAt = staleAt;
  const staleGate = bridgeReport(staleReport);
  if (staleGate["bounded-fastest-claim-qualified?"]
      || staleGate["bounded-fastest-claim"] !== null || staleGate["evidence-fresh?"])
    throw new Error("stale evidence emitted a bounded claim");

  const hostLoad = syntheticCompetitiveReport();
  hostLoad.domains[0].qualification.hostLoad.qualified = false;
  const hostGate = bridgeReport(hostLoad);
  if (hostGate["bounded-fastest-claim-qualified?"]
      || hostGate["bounded-fastest-claim"] !== null)
    throw new Error("host-load failure emitted a bounded claim");

  const synthetic = manifest.requiredDomains.map(syntheticRustDomain);
  if (!assessComparatorCoverage(manifest, synthetic).complete)
    throw new Error("complete Rust coverage was rejected");
  if (assessComparatorCoverage(manifest, synthetic.slice(0, -1)).complete)
    throw new Error("missing Rust domain was accepted");
  let duplicateRejected = false;
  try { assessComparatorCoverage(manifest, [...synthetic, synthetic[0]]); }
  catch (error) { duplicateRejected = /duplicate domain IDs/.test(error.message); }
  if (!duplicateRejected) throw new Error("duplicate comparator domain was accepted");
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

  // A host that would have passed the old 75%-of-CPU threshold must now fail.
  const high = String(Math.min(1, cpus().length * 0.10) + 0.01);
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

  process.stdout.write("runtime-multidomain: sealed prepare/measure, exact enumerated-universe claim, adversarial completeness, dirty/stale refusal, tamper, provenance, quiet timeout, compiler-free timing, known answers, rotation and perfgate OK\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
