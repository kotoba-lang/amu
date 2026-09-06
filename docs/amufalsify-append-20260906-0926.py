import io, sys

path = "docs/codegen-coscientist.md"
with io.open(path, "r", encoding="utf-8") as f:
    text = f.read()

entry = ("2026-09-06 09:2x JST (amu-falsify cron): J-B idle-gate rerun PASSED and ran. "
         "Load fell through the tick (06:xx load1 60\u2192 09:22 vm.loadavg 8.16 29.89 39.07 \u2192 09:23 6.60 28.13 38.23 \u2192 during runs load1 4.1\u20135.3 sustained across 9 x 5s samples, 9/9 below 7.5). "
         "Preflighted binary /private/tmp/jb_imod_control_preflight (staged 04:08), ABBA-interleaved, checksum-agreeing (arms agree 764266). "
         "WARMUP (not counted): 3 runs x 40 alternations @200k iters = +6.7% / +5.4% / +6.9% (load1 ~11\u201310.9, borderline; kept only as trend). "
         "POLICY-COMPLIANT RUNS (24 alternations x 4,000,000 iters, per ADR 0335 protocol), 3 independent runs: "
         "opaque(sdiv) 5.085 / 5.147 / 5.156 ns/elem vs const(mulh) 4.714 / 4.785 / 4.824 ns/elem \u2192 ratios 1.079 / 1.076 / 1.069, savings +7.3% / +7.0% / +6.4%. "
         "All 3 checksum-agree, sign consistent, all \u2265 the 5% bar, spread tight (6.4\u20137.3%, range 0.9pp). Combined with ADR 0335 (+6.2/+7.0/+6.7) this is 6/6 positive checksum-agreeing quiet-ish runs \u2014 the J-B effect replicates; this entry supplies the idle-gate rerun numbers the population note demanded (J-B remains confirmed-diagnostic/unqualified; status change is amu-rank's call). No compiler change made (hand-patch measurement only). "
         "NEXT unchanged: H-Z3 quiet-host hand-patch A/B (host trending quiet as of 09:26), then H-C2 timed A/B.")

# Append to end of file (dated log section style used by prior falsify entries)
with io.open(path, "a", encoding="utf-8") as f:
    f.write("\n" + entry + "\n")
print("appended ok")
