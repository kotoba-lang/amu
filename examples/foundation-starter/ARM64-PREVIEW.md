# Linux ARM64 starter: diagnostic preview

This is an engineering diagnostic, not a qualified release or a supported
public compiler profile. It uses the Amu ARM64 bootstrap root, not the x86
`bin/amu` entry. Author-controlled Linux ARM64 virtual machines and CI have
exercised the examples; a physical clean host and an independent user have
not yet qualified this profile. macOS is a different host profile.

On Linux ARM64, check the kernel and architecture with `uname -s` and
`uname -m`; expect `Linux` and `aarch64`. Git and Python 3 are required for
acquisition and observation. These checks alone do not establish host or
release qualification. In a dedicated shell, obtain the exact 40-character
commit reviewed on the [draft PR](https://github.com/kotoba-lang/amu/pull/1640):

```sh
set -e
git clone --filter=blob:none --depth 1 --no-checkout https://github.com/kotoba-lang/amu.git amu-arm-starter
cd amu-arm-starter
git fetch --filter=blob:none --depth 1 origin pull/1640/head
REVIEWED_REVISION=replace-with-reviewed-40-character-commit
test "$(git rev-parse FETCH_HEAD)" = "$REVIEWED_REVISION"
git sparse-checkout set --cone bin seed scripts examples
git checkout --detach "$REVIEWED_REVISION"
test "$(git rev-parse HEAD)" = "$REVIEWED_REVISION"
```

If the moving PR head differs from the reviewed revision, stop and review the
new head. The [main starter guide](README.md) describes the x86 entry; its
compiler image is not the ARM compiler.

From that checkout, in a dedicated shell with `set -e`, verify the diagnostic
root against both its descriptor and this fixed digest before executing it:

```sh
set -e
python3 - <<'PY'
import hashlib, json
from pathlib import Path

p = Path('seed/bootstrap/aarch64-linux-static-root.elf')
d = json.loads(Path('seed/bootstrap/aarch64-linux-static-root.json').read_text())
b = p.read_bytes()
digest = hashlib.sha256(b).hexdigest()
if (len(b) != 3621376 or
    digest != '8b56e3f0c4c1471003671279590c1e82d660c44dcd43221718529063e3da7d46' or
    d['image'] != {'bytes': len(b), 'sha256': digest}):
    raise SystemExit('ARM compiler or descriptor digest mismatch')
print('ARM compiler bytes verified')
PY
```

The digest checks bytes, not the authenticity or complete build provenance of
an unreviewed checkout. Stop on any mismatch; do not use a different compiler
or a hosted fallback. Acquire omitted files before disconnecting the network.

Choose a new absolute directory in your task workspace. The compiler receives
file authority scoped to this directory; the generated example gets no guest
capabilities. The direct commands below do not enforce a compiler source lock.

```sh
OUT=/absolute/task-workspace/arm-first-run
mkdir "$OUT"
cp examples/foundation-starter/hello.kotoba "$OUT/hello.kotoba"
COMPILER=seed/bootstrap/aarch64-linux-static-root.elf

KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35="$OUT" KEXE_STACK_BYTES=8388608 \
  "$COMPILER" check "$OUT/hello.kotoba"
KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35="$OUT" KEXE_STACK_BYTES=8388608 \
  "$COMPILER" compile "$OUT/hello.kotoba" --target aarch64-linux \
  --output "$OUT/hello.elf" --format static
chmod 700 "$OUT/hello.elf"
KEXE_ALLOW=- KEXE_FUEL=1000000 KEXE_STRUCTURED_REPORT=1 "$OUT/hello.elf"
```

Expect `:result 42`. Edit the copied expression from `(+ 40 2)` to
`(+ 40 3)`, compile to a **new** output filename and run it: expect 43.
Do not overwrite the original fixture or the first output.

To observe the same examples and their resource/authority refusals, choose a
second new absolute output directory and use the native queue:

```sh
python3 scripts/seed/native_build_queue.py -- \
  python3 scripts/seed/check-foundation-starter.py --experimental-arm64 \
  --host-profile linux-arm64-your-os-version \
  --output /absolute/task-workspace/arm-observation
```

The 20 operations include the edited sum 1 through 20, expected result 210,
fuel refusal and SHA-256 capability denial followed by a narrow grant. A
passing observation is not release qualification. Its receipt records
`experimentalArm64=true`, `publicReleaseReady=false` and
`externalUsersObserved=0`. Source-lock checks at `check` do not provide an
atomic lock for static ELF compilation.

If a step fails, retain the reviewed commit, broad OS/CPU profile, step,
diagnostic and expected/actual result. Remove private code, credentials and
personal data before sharing. The [Amu issue tracker](https://github.com/kotoba-lang/amu/issues)
is public; do not put sensitive data there.
