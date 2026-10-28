# Selfhost Nettle-AES: complete AES-256 workload

The pinned Nettle-AES benchmark now has a complete native Kotoba alternative.
Source-built Amu accepts both check and compile. **12,680 state cells** match
C across four input profiles and five stages; the actual production body also
matches all **634 observable final cells** for the original profile. Batches
0/1/2/17/32 agree. asher is offline and the local host is busy, so this wave
has **no timing comparison**, optimization promotion or C-or-better claim.
Six adapted workloads still lack complete alternatives.

## Algorithm and execution path

`bench/embench/batch-ports/nettle-aes.kotoba` executes the same AES-256 work:
expand 60 encryption-key words, encrypt all 16 blocks (256 bytes), independently
expand the decryption schedule, reverse it in four-word groups, mix its middle
52 words, then decrypt all 16 blocks. Each block runs 13 table rounds and the
final S-box round. This is the pinned 32-byte-key/256-byte profile, not a
new general AES API or an AES-128/AES-192 implementation.

`generate_aes_port.py` extracts the exact upstream encryption/decryption
S-boxes and eight round tables, inverse-column table, rcon, key, plaintext
and expected ciphertext. Checked literal vectors are split at the seed's
128-element limit. The algorithm remains in `aes-full-body.kotoba`; generated
numbers are profile/table data. The expected ciphertext is used only in the
final verifier. There is no hardware AES shortcut, host crypto callback,
stored output substituted for encryption, or simplified roundtrip model.
The historical `ports/nettle-aes.kotoba` is unchanged.

One owned 635-cell i64 workspace holds both 60-word schedules, both 256-byte
buffers, both round counts and a block-offset scratch cell. The oracle compares
all 634 cells corresponding to C fields; the extra scratch cell is a native
implementation detail. C uses uint32/uint8/unsigned storage; native values are
canonical unsigned values held in i64 cells. Rotations explicitly truncate to
32 bits. A batch allocates once and reuses its workspace, regenerating both
schedules and overwriting both outputs on every body as C does.

Native check initially refused a direct scratch store after conditional
read-only input expressions. The accepted source places that one store in
a typed helper, called after all scalar reads; no handle is used after its
consuming call. The helper still emits the checked `vector-assoc!`. We did not
change the compiler or ignore a check refusal. Four-input bitwise expressions
use scalar helpers composed from the seed's binary bitwise primitives.
Bounds and fuel guards remain enabled; a diagnostic accepts workspace index
634 and traps at 635 (SIGILL), while a one-fuel batch traps (SIGTRAP).
PRODUCT dependencies are unchanged. Python/C bootstrap generation and audit
scaffolding do not enter the native codec/compiler execution path. This does
not prove the separate 100% product-selfhost or own-source process-trace gates.

## C differential and claim boundary

The C observation adapter invokes the **unchanged upstream AES functions** in
the benchmark's order; it does not reimplement AES. It snapshots:

1. Zeroed initial contexts and output buffers.
2. Encryption schedule and its round count.
3. Encryption output.
4. Regenerated, inverted decryption schedule and its round count.
5. Decryption output.

Profiles are original input, key XOR 255, plaintext XOR its byte index, and
zero key/plaintext. All 4 x 5 x 634 values agree. Each observed final state is
also compared with unchanged `benchmark_body(1,1)` for the same inputs. For the
original profile, unchanged C verification confirms every ciphertext byte
against its golden and every decrypted byte against plaintext. A separate
native diagnostic exercises the production `body` directly and compares all
634 original-profile fields, rather than relying solely on the staged path.
The five batch counts match unchanged C plus its original verifier.

These are correctness and resource checks on a busy Apple M1 Max, not
performance measurements. Incidental elapsed fields from diagnostic runner
calls are not ranked or interpreted as speed. The snapshot input domain is
profiles 0..3, stages 0..4, cells 0..633, encoded as
`profile*4096 + stage*634 + cell`. Batch comparison is for positive uint32
iteration counts; zero is a no-op returning zero. Arbitrary unsupported audit
encodings are outside the comparison. Full-suite official timing/initialization
and dummy-subtracted size qualification remain open.

## Reproduction and evidence

Upstream Embench commit: `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`;
AES source SHA256: `140117d48a832ecdc13ae817ea88a7436c01ec654d25d5dd0ba48cdf5f3ab3bc`.
Source-built native Amu SHA256:
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`.
Both generators reject a changed upstream profile even under Python -O.

Generate with `generate_aes_port.py <nettle-aes.c> <nettle-aes.kotoba>` and
`generate_aes_oracle.py <nettle-aes.c> <c-bridge.c>`. Native-check, compile and
extract `batch`, `stage-cell` and `test-nettle-aes`, retaining
`<symbol>-extract.log`. Place the directory beside `runner`, pinned `upstream`
and the source-built `images/r6m`, then run:

```
python3 scripts/seed/image/measure-aes-full.py <directory> --correctness-only
# On reachable, quiet asher, with a fresh directory having no results.json:
python3 scripts/seed/image/measure-aes-full.py <fresh-directory>
```

The harness requires native check acceptance, builds its C adapter, verifies
all snapshots and the production body, checks batches/fuel, refuses replacement
of a report and persists failures. Timing mode requires load <= 4, 32 bodies
per call, one untimed warmup, calibrated counts and 30 rotated samples per arm.
Formal native perfgate and CPU-idle qualification remain separate requirements.
No running remote job is claimed; the replay bundle is only prepared.

`docs/evidence/coscientist-aes-20261004/` contains complete reports, all
source/native/C artifacts, check/compile/extraction logs and provenance,
accepted and refused scratch-store formulations, bounds/fuel evidence,
regeneration/profile-pin checks, and a member hash manifest. Canonical-source
attribution is regenerated separately; its native bytes equal the audited
baseline. This is new algorithm/profile authoring, with no AST refactor rule
covering it and no product source edits.

Remaining complete alternatives: picojpeg, qrduino, sglib-combined, slre,
statemate and wikisort. Next run the queued full comparisons and Huffbench
reset hypotheses on asher, recover pending reports, and rank compiler
optimizations from separated measurements. The full-suite C-or-better goal
remains active.
