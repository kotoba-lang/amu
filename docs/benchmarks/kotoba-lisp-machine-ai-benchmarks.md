# Kotoba + Amu: a Lisp machine for Artificial Intelligence (Super Intelligence)

Kotoba is a Lisp machine and programming language designed to bring explicit safety boundaries and native performance into one system. Amu is the deny-by-default, multi-target compiler for Kotoba.

We are building this architecture for artificial intelligence, including the possibility of superintelligence. That makes honest performance evidence important: a fast kernel is useful, but it does not prove that a language or AI system is safe.

## What the benchmarks show

The available results do not establish that Kotoba or Amu is the world's fastest language. They answer narrower questions, on particular workloads and machines.

| Study | Published result | What it does and does not show |
| --- | --- | --- |
| Embench IoT translated-port comparison, 15 October 2026 | 19 Kotoba ports; one accepted sample per workload; reported geometric-mean time ratio 0.7999 against upstream C built with Apple Clang 17 at -O2 | Exploratory only. Five ports were marked as workload substitutions, and the Kotoba SHA-256 path used ARMv8 SHA instructions that the C baseline did not. The result is not a certified Embench score, a like-for-like language ranking, or a universal fastest claim. |
| Amu native cross-language runtime comparison, 7 September 2026 | Six kernel domains compared with Rust, Clang/C11, Zig, Go c-shared, and Swift; 19 of 30 comparator/domain pairs cleared the perfgate threshold in every recorded run | All 30 known answers were verified, but the bounded fastest claim did not qualify. The report is historical and outside the suite's 24-hour freshness window. |

The cross-language qualified-pair counts were: Clang/C11 2 of 6, Rust 1 of 6, Zig 5 of 6, Go c-shared 6 of 6, and Swift 5 of 6. A pair counted only when Amu was at least 5% faster and the result was separated from the measured spread. These counts describe the named M4 workload suite, not all programs or processors.

The Embench ratio is included so the raw result is visible, not as a speed claim. Exact output checks passed, but exact answers alone do not make different amounts or kinds of algorithmic work comparable. The audit lists the affected workloads and the architecture-specific SHA path in the machine-readable report.

## Raising the bar for the next comparison

The Amu benchmark policy now requires at least 10 alternating ABBA/BAAB rounds per domain for competitive comparisons, a quiet-host gate, verified answers for every comparator, and a report no older than 24 hours before it can support a current fastest claim. The full samples, tool versions, machine details, source and artifact hashes, and claim gates remain part of the report.

A credible Embench ranking also needs the same algorithm on both sides and comparable instruction-set paths. The next release will use that narrower comparison before making a language-level speed claim.

## Why a Lisp machine

Kotoba's Lisp-machine architecture treats computation as closed programs with explicit state and bounded authority. Amu checks and compiles Kotoba programs; the host and runtime enforce the admitted execution boundary. These design choices are intended to make safety part of the system's structure rather than a benchmark feature.

The benchmark results measure execution speed only. They do not qualify the safety of an AI model, prove the security of every runtime path, or show that a superintelligent system can be controlled.

## Evidence

- [Kotoba and Amu source, architecture, and compiler](https://github.com/kotoba-lang/amu)
- [Embench result and kernel audit](https://github.com/kotoba-lang/kotoba-lang/blob/main/site/benchmarks/embench-c-parity-20261015.json)
- [Embench offline reproduction package](https://github.com/kotoba-lang/amu/tree/72e59fa97288f8fd881bd014b65a66ae35a3d03d/bench/embench/reproduce-20261015/)
- [Amu cross-language comparison report](https://github.com/kotoba-lang/kotoba-lang/blob/main/bench/public-runtime-comparison/latest.json)
- [Current competitive comparison policy and raw artifacts](https://github.com/kotoba-lang/amu/tree/main/bench/runtime-comparison)

*Status as of 15 October 2026. We will update the comparisons when a fresh run clears the published qualification gates.*
