# Portable integrated proof replay

Copy `integrated-proof.tgz`, `archive-manifest.json`, and `replay.py` into one directory. Run:

    python3 replay.py

Python standard library only. The script extracts a separate temporary snapshot. It never invokes the compiler, native guest binaries, a solver, SSH, or a benchmark. It verifies every archived file, recomputes actual generation byte equalities, source/dependency content pins, original19 measured native bytes/offsets, all391 checker and compile classifications, all891 export classifications (including the missing export), full391 checker output pairs,1780 candidate result/status files, and330 native code/export table equalities against distinct previous snapshots.

Only the exact committed clone-root/corpus-root prefixes and relocated `bench.embench.ports` report IDs normalize. Checker display text is regenerated from the full saved NEW outputs after root normalization and before the existing200-character truncation. No messages, classifications, results or fuel values are changed. Both raw372-source and supplemental19-source reports remain archived. All19 relocated source hashes match previous authoritative provenance.

The compact selection is not the full21698-file original integration pin set. It retains all3generation162objects/117frontend/artifacts, frozenexternalinputs, compiler/source dependency snapshots,391corpus sources and oracle cache, distinctold/new raw parity records, original19source+code+logs and measured code. Gitadministration/history, unrelateddocs/repository sources, redundantloader/build intermediates and measurement outputs are omitted. Because old baseline files are added, the selected pin count can exceed the original new-evidence count; these are different sets. `selection.json` records original file paths and exact selection.

This proves retained finite correctness evidence. It does not make a timing, release, main-merge, universal equivalence, full own-source100percent or C-or-better completion claim.
