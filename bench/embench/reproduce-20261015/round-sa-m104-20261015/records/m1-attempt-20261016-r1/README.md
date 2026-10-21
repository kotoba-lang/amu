# Apple M1 Max CPU-gated attempt (16 October 2026)

This is an **unqualified attempt, not a result or score**. It uses round *sa-m104-20261015* and the pinned Embench IoT commit *09c2ed8c3b7008c95d08b038de4a3f6dc103ed70*.

The external 10-second raw-idle gate reached 70.3912% once and started the campaign. The per-run protocol then rejected every executed sample because raw CPU idle during the timed interval was below 70%. The Kotoba and C arms each executed *aha-mont64* twice; both attempts in each arm were rejected. The other 18 workloads in each arm had only quiet-admission timeouts. Final acceptance was 0/19 for Kotoba and 0/19 for C; the geometric mean is null. The upstream drivers returned nonzero because there was no qualified observation for the suite. No M1 score is claimed.

The full per-workload attempt and quiet-admission JSON records, driver stdout/stderr, external gate windows, final report, M1 build/exactness reports, and C-build receipt are retained here. *m1-image-sha256.json* maps the rebuilt *official-*.kseed* names to the packaged workload images; all 19 hashes match.

The raw-attempt report records elapsed time for rejected runs as diagnostic data only. Those timings must not be used as benchmark results.
