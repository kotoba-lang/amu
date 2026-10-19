# Kotoba + Amu: a Lisp machine for Artificial Intelligence (Super Intelligence)

Kotoba is a Lisp machine and programming language designed to bring explicit safety boundaries and native performance into one system. Amu is the deny-by-default, multi-target compiler for Kotoba.

We are building this architecture for artificial intelligence, including the possibility of superintelligence. That makes honest performance evidence important: a fast kernel is useful, but it does not prove that a language or AI system is safe.

## What the benchmarks show

The available results do not establish that Kotoba or Amu is the world's fastest language. They answer narrower questions, on particular workloads and machines. The corrected M104 Embench comparison used a selfhost fixed-point compiler (G1 = G2 = G3), built from the public bootstrap; the September cross-language comparison used the Node/nbb bootstrap route. Selfhosting describes how the compiler was produced, not why a benchmark workload runs faster.

| Study | Result | Compiler provenance | Interpretation |
| --- | --- | --- | --- |
| Embench IoT translated-port comparison, 15 October 2026 | 19 Kotoba ports; one accepted sample per workload; reported geometric-mean time ratio 0.7999 against upstream C built with Apple Clang 17 at -O2 | m93 seed compiler, bootstrap reference; compiler source commit be7f0ce358ebe8d1a715b2784f272ce0eda8e934 | Exploratory only. Five ports were marked as workload substitutions, and the Kotoba SHA-256 path used ARMv8 SHA instructions that the C baseline did not. This is not a certified Embench score, a like-for-like language ranking, or a universal fastest claim. |
| Corrected Embench-derived comparison, M104 | Geometric-mean Kotoba/C time ratio 0.8213 on one Apple M4 cycle; 0.7877703356 on a separate M4 Mac mini cycle. On the latter, Kotoba was faster on 12 of 19 workloads; C was faster on 7. | Selfhost fixed-point M104 compiler, source `a9edc1f0`; the separate cycle rebuilt C with Apple Clang 21.0.0. | Same-algorithm-only translated-port comparison with scalar SHA-256. It is workload-specific, uses one accepted sample per workload, and is not a certified Embench score or universal fastest claim. |
| Amu native cross-language runtime comparison, 7 September 2026 | Six kernel domains against Rust, Clang/C11, Zig, Go c-shared, and Swift; 19 of 30 comparator/domain pairs qualified in every recorded run | Amu native artifacts produced with the canonical bin/amu Node/nbb bootstrap route; compiler commit 42f092ea5b6192f02f3c361535a37521b2ab6ab1 | All 30 known answers were verified, but the bounded fastest claim did not qualify. This report is historical and outside the suite's 24-hour freshness window. |

The cross-language qualified-pair counts were: Clang/C11 2 of 6, Rust 1 of 6, Zig 5 of 6, Go c-shared 6 of 6, and Swift 5 of 6. A pair counted only when Amu was at least 5% faster and the result was separated from the measured spread. These counts describe the named M4 workload suite, not all programs or processors.

The M93 Embench ratio is included so the historical result stays visible; its substitutions and Kotoba-only SHA instructions make it unsuitable as a like-for-like claim. The corrected M104 result shows that a selfhosted compiler can produce faster code on some measured workloads, but exact output checks alone do not make different implementations equivalent. The M104 audit records the same-algorithm kernel scope, and its geometric mean still includes seven workloads where C was faster.

## Raising the bar for the next comparison

The Amu benchmark policy requires at least 10 alternating ABBA/BAAB rounds per domain for competitive comparisons, a quiet-host gate, verified answers for every comparator, and a report no older than 24 hours before it can support a current fastest claim. The full samples, tool versions, machine details, source and artifact hashes, and claim gates remain part of the report.

A credible Embench ranking also needs the same algorithm on both sides and comparable instruction-set paths. The next release will use that narrower comparison before making a language-level speed claim.

## Why a Lisp machine

Kotoba's Lisp-machine architecture treats computation as closed programs with explicit state and bounded authority. Amu checks and compiles Kotoba programs; the host and runtime enforce the admitted execution boundary. These design choices are intended to make safety part of the system's structure rather than a benchmark feature.

The benchmark results measure execution speed only. They do not qualify the safety of an AI model, prove the security of every runtime path, or show that a superintelligent system can be controlled.

## Evidence

- [Kotoba and Amu source, architecture, and compiler](https://github.com/kotoba-lang/amu)
- [Pinned Embench result and kernel audit](https://github.com/kotoba-lang/kotoba-lang/blob/27b90068eda38d19b521a383167fb2c631a09eb5/site/benchmarks/embench-c-parity-20261015.json)
- [Embench offline reproduction package at its exact commit](https://github.com/kotoba-lang/amu/tree/72e59fa97288f8fd881bd014b65a66ae35a3d03d/bench/embench/reproduce-20261015/)
- [Pinned Amu cross-language report snapshot](https://github.com/kotoba-lang/kotoba-lang/blob/27b90068eda38d19b521a383167fb2c631a09eb5/bench/public-runtime-comparison/latest.json)
- [Current competitive comparison policy and raw artifacts](https://github.com/kotoba-lang/amu/tree/main/bench/runtime-comparison)

The cross-language source report has SHA-256 66b81c7403100a96c9d81a3cc7876dcf2bc69d64c42c67af937b8bf223fa493a. Status as of 15 October 2026. We will update the comparisons when a fresh run clears the published qualification gates.
