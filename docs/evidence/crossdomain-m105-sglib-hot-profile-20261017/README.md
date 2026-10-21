# Sglib guest hot-path profile and list-merge experiment (2026-10-17)

Status: profile is exploratory; the source-level list-merge rewrite is rejected.
No timing claim or compiler change is promoted.

## Control profile

The profiled artifact is the unchanged M105 Sglib control image used by the
input-table probe. At `n=253952`, the official timer returned result `1`,
benchmark fuel `3,858,038,786`, and verification fuel `605`. The timer was
started with the registered KEXE CPU and wall caps, and the guest process was
sampled for two seconds at a 1 ms interval. The run was on a loaded host and is
not a quiet-host performance measurement.

The sample report contained 1,656 call-graph samples. I mapped sampled PCs to
the image's disassembly using the guest image base from `vmmap.txt`. These are
coarse address regions, not precise function-time shares:

| Image offsets | Samples | Manual disassembly mapping |
|---|---:|---|
| `0x3e00–0x4300` | 390 | Linked-list merge path (`list-merge`) |
| `0x6600–0x6c00` | 187 | Heap sift-down (`heap-down`) |
| `0x9200–0x9b00` | 363 | Tree search, insertion, and rebalance path |
| `0x9b00–0xb000` | 113 | Later tree traversal/helper region; exact function boundary not established |

The four regions account for 1,053 samples (63.6% of all samples). The largest
individual sampled PCs were in list merge, heap sift-down, and tree insertion.
This ranks those paths for further investigation; it does not show that
rewriting them will improve elapsed time.

## Falsify: branchless source-level list merge

The candidate replaced `list-merge`'s two recursive compare branches with a
`take-a` predicate and conditional selection of the winner and next references.
It was built from a private copy of the port, using the verified M105 G3
selfhost compiler. The official exactness run at `n=253952` passed: result,
benchmark fuel (`3,858,038,786`), verification fuel (`605`), and arena report
matched the control.

Three registered instruction-count runs per arm gave these medians:

| Arm | Median dynamic native instructions |
|---|---:|
| M105 control | 30,970,746,764 |
| Branchless source candidate | 37,418,799,985 |

The candidate/control ratio is `1.20820`, or about 20.82% more dynamic
instructions. The harness rejected it against the preregistered ±2% diagnostic
gate. No timing was run. This falsifies the source rewrite as a performance
candidate while preserving its exactness result; it does not falsify
compiler-level if-conversion on the original source.

## Explain the source rewrite regression

`seed/41-a64gen.kotoba` has an exact-shape `lp-entry` recognizer that emits a
104-word AArch64 body for the original list-sort source. A byte fingerprint of
that body is present in the M105 control image at offset `16280` and in the
input-table source candidate at offset `16232`. The fingerprint is absent from
the branchless list-merge candidate. The only port change in that candidate
was the `list-merge` rewrite, and the recognizer checks the linked helper IR
shapes; the image evidence therefore shows that this rewrite no longer uses
the existing specialized body. That accounts for the large dynamic-instruction
regression more plausibly than the changed compare alone. The fingerprint
check is reproducible with `verify-lp-kernel-fingerprint.py`.

## Next-ranked experiments

Keep the original port and its shape matcher. A new isolated compiler
experiment carries the two node addresses through the merge loop, updating
only the address for the chosen side; this should replace two address
calculations per comparison with one. Require fixed-point selfhost, exact
result/fuel/arena checks, and a paired instruction-count and timing comparison.
If it does not help, inspect tree insertion and heap sift-down next.

## Provenance

- Control source SHA-256: `2122b3005ad248c096153bc148ac9df58b6022b37ae025caea948dd0dc7c0210`
- Control image SHA-256: `5e0b9072eb8a404479d569c5986ba6f008bd6143b8815fb0ea2db3f2e91d0040`
- Timer SHA-256: `d3d0a129d24de28e8dc5ab785c9b5ad5061c790838bea4a0723c2be75fcea417`
- Sample report SHA-256: `bc91171b3629cd62f520525ae7326c7b69415e4489e769afd73e4481772e88cb`
- VM map SHA-256: `c79bcb947476ae9c1a7f8ec0ef97612c4667782151c778b7f328eff008647e60`
- Control disassembly SHA-256: `15e8fd50f780739814f7a7c7355d1b43549b4456717a4fdfdc6ecdfc159a0408`
- Candidate source SHA-256: `01ede54850244a7585e1e8e53f08cdad02dcef884c217e920c6061fe73ca86ec`
- Candidate kseed SHA-256: `73585f24f8dfae9ee864f954a6cf5b5f166c104e7ad4bdc72382a41d7621cf1d`
- Candidate native image SHA-256: `550065d1c25bd088745b2a3937308c49712cecfecbb24ac8081d7da915ef9f24`
- Candidate disassembly SHA-256: `243c4a6b236d1eecad68a868fbafdb7d7318156c05c05cefc1754a29c1110fce`
- Exactness report SHA-256: `125b93b1fc1e58a692470ff9ef84b911de9e6094026d1b3f1521abeafe2faf59`
- Instruction-count report SHA-256: `3bfcc6952ee93c056a4034852a014d0c70c9f7558c9f61e6c086e66804bb0724`
- Raw artifacts: `workspaces/codex/amu-sglib-input-table-20261017/attempt-1/profile-control/` and `workspaces/codex/amu-sglib-list-branchless-20261017/attempt-1/`
