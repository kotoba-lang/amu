#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import {
  mkdtempSync, readFileSync, rmSync, writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const directory = mkdtempSync(join(tmpdir(), "amu-compiler-bundle-test-"));
const fixture = join(root, "bench", "runtime-comparison", "kernel.kotoba");
const manifestPath = join(root, ".tools", "compiler-bundles", "manifest.json");

function run(args, env = {}) {
  const result = spawnSync(join(root, "bin", "kotoba"), args, {
    cwd: root, encoding: "utf8", timeout: 120_000,
    env: { ...process.env, KOTOBA_COMPILER_DAEMON: "0", ...env },
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.error) throw result.error;
  if (result.status !== 0)
    throw new Error(`kotoba ${args.join(" ")} failed\n${result.stdout}${result.stderr}`);
  return result;
}

try {
  const profiles = [
    { target: "wasm32", key: "wasm", extension: "wasm", provenance: false },
    { target: "aarch64", key: "aarch64", extension: "kexe", provenance: true },
    { target: "x86_64", key: "x86_64", extension: "kexe", provenance: true },
  ];
  for (const profile of profiles) {
    const bundled = join(directory, `${profile.key}-bundled.${profile.extension}`);
    const source = join(directory, `${profile.key}-source.${profile.extension}`);
    const args = (output) => ["-M", "compile", fixture, "--target", profile.target,
      "--output", output];
    const hit = run(args(bundled), { KOTOBA_COMPILER_BUNDLE_TRACE: "1" });
    if (!hit.stderr.includes(`compiler bundle hit ${profile.key}`))
      throw new Error(`valid ${profile.key} bundle was not selected`);
    run(args(source), { KOTOBA_COMPILER_BUNDLE: "0" });
    const suffixes = profile.provenance ? ["", ".provenance.edn"] : [""];
    for (const suffix of suffixes) {
      if (!readFileSync(`${bundled}${suffix}`).equals(readFileSync(`${source}${suffix}`)))
        throw new Error(`${profile.key} bundle changed artifact bytes for ${suffix || profile.extension}`);
    }
  }

  const extracted = join(directory, "aarch64-main.bin");
  const extraction = run(["-M", "extract-native", join(directory, "aarch64-bundled.kexe"),
    "--symbol", "main", "--output", extracted], { KOTOBA_COMPILER_BUNDLE_TRACE: "1" });
  if (!extraction.stderr.includes("compiler bundle hit x86_64") || readFileSync(extracted).length === 0)
    throw new Error("extract-native did not select the native tooling bundle");

  const stale = join(directory, "stale-fallback.kexe");
  const staleArgs = (output) => ["-M", "compile", fixture, "--target", "aarch64",
    "--output", output];
  const original = readFileSync(manifestPath);
  try {
    const manifest = JSON.parse(original.toString("utf8"));
    manifest.sourceDigest = "0".repeat(64);
    writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
    const fallback = run(staleArgs(stale), { KOTOBA_COMPILER_BUNDLE_TRACE: "1" });
    if (!fallback.stderr.includes("compiler bundle stale; using source entrypoint"))
      throw new Error("stale bundle did not fail closed to source loading");
  } finally {
    writeFileSync(manifestPath, original);
  }

  const aarch64Bundle = join(root, ".tools", "compiler-bundles", "aarch64.mjs");
  const originalBundle = readFileSync(aarch64Bundle);
  try {
    writeFileSync(aarch64Bundle, Buffer.concat([originalBundle, Buffer.from("\n// corrupt\n")]));
    const fallback = run(staleArgs(stale), { KOTOBA_COMPILER_BUNDLE_TRACE: "1" });
    if (!fallback.stderr.includes("compiler bundle stale; using source entrypoint"))
      throw new Error("modified bundle did not fail closed to source loading");
  } finally {
    writeFileSync(aarch64Bundle, originalBundle);
  }
  process.stdout.write("compiler-bundles: byte parity, target selection, stale source, and bundle integrity fallback passed\n");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
