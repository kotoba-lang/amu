# Resident fuel: native proof and AES-only timing qualification

The native selfhost candidate `a236b3e8` preserves six separate fuel decrements
and publications, using a resident scratch value only in the certified sufficient
fuel path. Four generations are byte identical. Only four original AES sites
change; the other eighteen benchmark images and all default-off images match
the AES v2 baseline. This candidate is not adopted.

Copy these three files into an empty directory and run:

```sh
python3 native-resident-fuel-replay.py --out ./replayed
```

- `native-resident-fuel.tgz`: 5,340 selected immutable files, including source,
  native images, raw observations, mathematical queries and authoring failures.
- `native-resident-fuel.manifest.json`: archive, inventory and reader hashes.
- `native-resident-fuel-replay.py`: standard-library offline recomputation;
  forbids external inputs, subprocesses and network calls during replay.

Both the publication owner and root independently copied only these three files
into separate empty directories and passed replay. `root-replay.json` records
the root result. Replay rechecks retained results; it does not repeat native
execution, solver execution or performance measurement. Three envelope mutations
were rejected before extraction. Reader authoring corrections are retained in
the archive without changing owner code, observations or semantic oracles.

Coverage includes full19 machine projection and eight machine faults, 211 full
state pairs, 50 positive publication traces, fifteen productive fault traces and
one nonproductive fault trace, six formal gates, 76 adapted G1 observations,
593 permanent fixtures / 25,658 observations, and archived SMT results (3 UNSAT,
7 SAT). The strict original G1 C-build cap **failed**: its helper built unused
versions as well. Adapted functional evidence and a subsequent budget amendment
do not erase that procedural deviation or establish unmodified G1 script PASS.

The scoped fuel ownership requirement is separate from a generic raw context
ABI. Diagnostic raw-u64 fuel does not expand product budget admission. No
universal compiler/OS/hardware proof, automatic product integration, official
Embench score, C-or-better result or performance qualification is claimed here.

That boundary describes the frozen native proof packet. The later separately
frozen [full19 timing proof](timing-proof/README.md) includes all 57 semantic
preflight calls, 2,061 attempted measurement arms, 145 calibration rows and the
independent audit. AES improved by 1.095870x (8.7483% shorter time), but remains
9.9885x slower than C. The full19 descriptive aggregate does not establish an
overall improvement; product adoption and official-score claims remain false.
The [full19 comparison](../../coscientist-resident-fuel-comparison-20261007.md)
lists every original body's timing.

The separately frozen [timing host setup proof](host-proof/README.md) checks the
new measured host's admission, unchanged timing loop and retained setup controls.
Its snapshot also precedes the full benchmark preflight and campaign.
