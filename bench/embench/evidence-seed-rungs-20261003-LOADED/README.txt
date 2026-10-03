LOADED run, NOT a measurement (scripts/seed/embench-rungs.sh, HOUSE2, 2026-10-03): the host never had a 1-minute load average below 8
at any of the 19 polls (every 10 minutes for 3 hours; lowest seen 11.19), so it ran once with SEED_ALLOW_LOADED=1 at load 61-79.
Valid facts: all 19 workloads correct under the unchanged runner for the R2, R3 and R4 seeds (selfhost_built = true, fixed points
reproduced by bootstrap.sh --no-head), code bytes (table.tsv). Timings (compile ms, execute ns) are loaded-host numbers: only the
stage-0 vs seed ordering within one run is indicative. stage0 = bootstrap-reference (SEED_COMPILER), labelled so in its provenance.
