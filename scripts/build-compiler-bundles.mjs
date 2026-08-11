#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, writeFileSync,
} from "node:fs";
import { delimiter, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputDirectory = join(root, ".tools", "compiler-bundles");
const nbbCli = join(root, "node_modules", "nbb", "cli.js");

function filesBelow(path) {
  if (!statSync(path).isDirectory()) return [path];
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    const child = join(path, entry.name);
    return entry.isDirectory() ? filesBelow(child) : [child];
  });
}

export function compilerSourceDigest() {
  const roots = ["deps.edn", "deps-lock.edn", "package-lock.json", "src", "resources"]
    .map((path) => join(root, path));
  const files = roots.flatMap(filesBelow)
    .sort((left, right) => {
      const a = relative(root, left);
      const b = relative(root, right);
      return a < b ? -1 : a > b ? 1 : 0;
    });
  const hash = createHash("sha256");
  for (const path of files) {
    hash.update(relative(root, path));
    hash.update("\0");
    hash.update(readFileSync(path));
    hash.update("\0");
  }
  return hash.digest("hex");
}

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: root, encoding: "utf8", maxBuffer: 32 * 1024 * 1024,
  });
  if (result.error) throw result.error;
  if (result.status !== 0)
    throw new Error(`${command} ${args.join(" ")} failed\n${result.stdout}${result.stderr}`);
  return result.stdout;
}

const resolved = run(process.execPath,
  [nbbCli, "--classpath", join(root, "src"),
    join(root, "scripts", "print-classpath.cljs"), root])
  .trim().split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
const classpath = [join(root, "src"), join(root, "resources"), ...resolved].join(delimiter);
const entries = {
  wasm: "wasm_cli.cljs",
  aarch64: "aarch64_cli.cljs",
  x86_64: "x86_64_cli.cljs",
};

rmSync(outputDirectory, { recursive: true, force: true });
mkdirSync(outputDirectory, { recursive: true });
for (const [name, source] of Object.entries(entries)) {
  run(process.execPath,
    [nbbCli, "--classpath", classpath, "bundle",
      join(root, "src", "kotoba", "compiler", "nbb", source),
      "--out", join(outputDirectory, `${name}.mjs`)]);
}
const manifest = {
  format: "kotoba.compiler-bundles/v2",
  sourceDigest: compilerSourceDigest(),
  entries: Object.fromEntries(Object.keys(entries).map((name) => {
    const file = `${name}.mjs`;
    const sha256 = createHash("sha256").update(readFileSync(join(outputDirectory, file))).digest("hex");
    return [name, { file, sha256 }];
  })),
};
const temporary = join(outputDirectory, ".manifest.json.tmp");
writeFileSync(temporary, `${JSON.stringify(manifest, null, 2)}\n`);
renameSync(temporary, join(outputDirectory, "manifest.json"));
process.stdout.write(`compiler-bundles: wrote ${Object.keys(entries).length} target closures (${manifest.sourceDigest})\n`);
