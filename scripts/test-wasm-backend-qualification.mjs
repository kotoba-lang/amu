#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  extractDepsPin,
  extractLockPin,
  promotionState,
} from "./qualify-wasm-backend.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const depsPin = extractDepsPin(readFileSync(join(root, "deps.edn"), "utf8"));
const lockPin = extractLockPin(readFileSync(join(root, "deps-lock.edn"), "utf8"));
assert.match(depsPin, /^[0-9a-f]{40}$/);
assert.equal(lockPin, depsPin, "checked-in dependency lock must match deps.edn");

assert.deepEqual(
  promotionState({ commit: depsPin, dirty: false, depsPin, lockPin, checksPassed: true,
    remoteAdvertisesCommit: true }),
  {
    candidateQualified: true,
    backendClean: true,
    pinsAgree: true,
    compilerPinsHeadCommit: true,
    remoteAdvertisesCommit: true,
    candidateTreePublished: true,
    promotionReady: true,
  },
);
assert.equal(
  promotionState({ commit: depsPin, dirty: true, depsPin, lockPin, checksPassed: true })
    .promotionReady,
  false,
  "a dirty backend must never be promotion-ready",
);
assert.equal(
  promotionState({ commit: depsPin, dirty: false, depsPin, lockPin, checksPassed: true })
    .promotionReady,
  false,
  "an unverified remote publication must never be promotion-ready",
);
assert.equal(
  promotionState({ commit: "0".repeat(40), dirty: false, depsPin, lockPin, checksPassed: true })
    .promotionReady,
  false,
  "a compiler pin mismatch must never be promotion-ready",
);
assert.equal(
  promotionState({ commit: depsPin, dirty: false, depsPin, lockPin, checksPassed: false })
    .promotionReady,
  false,
  "unqualified bytes must never be promotion-ready",
);

assert.throws(() => extractDepsPin("io.github.kotoba-lang/kotoba-wasm {:git/sha \"short\"}"));
console.log("wasm-backend-qualification: pin parsing and fail-closed promotion state passed");
