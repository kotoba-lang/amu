#!/bin/sh
# Native syscall diagnostic: ONLY a private regular-file fixture is writable.
set -eu
: "${TMPDIR:?set TMPDIR to workspace scratch}"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../.." && pwd)
bootstrap="$root/seed/bootstrap/aarch64-macos"
[ "$(uname -s) $(uname -m)" = 'Darwin arm64' ] || exit 1
work=$(mktemp -d "$TMPDIR/block-offset.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir "$work/build" "$work/gen"
for kind in compiler packager; do
  if [ "$kind" = compiler ]; then file=amu-full-root.macho; else file=kotoba-packager-root.macho; fi
  expected=$(/usr/bin/plutil -extract "$kind.sha256" raw -o - "$bootstrap/root.json")
  actual=$(shasum -a 256 "$bootstrap/$file" | cut -c1-64)
  [ "$actual" = "$expected" ] || { echo "$kind hash mismatch" >&2; exit 1; }
done
cp "$root/seed/macos-offset-control-packager.kotoba" "$work/build/source.kotoba"
(cd "$work/build" && env -i PATH=/nonexistent "$bootstrap/amu-full-root.macho" compile source.kotoba --target aarch64-macos --output p.kseed 3<.) > "$work/compile.log" 2>&1
(cd "$work/build" && env -i PATH=/nonexistent "$bootstrap/amu-full-root.macho" extract-native p.kseed --symbol main --output p.raw 3<.) > "$work/extract.log" 2>&1
entry=$(sed -n 's/^{:ok true, :output "p.raw", :offset \([0-9][0-9]*\), :length \([0-9][0-9]*\), :arity 0}$/\1/p' "$work/extract.log")
[ -n "$entry" ] || { cat "$work/extract.log" >&2; exit 1; }
(cd "$work/build" && env -i PATH=/nonexistent "$bootstrap/kotoba-packager-root.macho" generator p.raw fs2-cli-stdio-general "$entry" 3<.) > "$work/package.log" 2>&1
chmod 755 "$work/build/generator"
/usr/bin/codesign --force --sign - "$work/build/generator" 2>/dev/null
(cd "$work/gen" && env -i PATH=/nonexistent "$work/build/generator" control.macho strict 3<.)
chmod 755 "$work/gen/control.macho"
/usr/bin/codesign --force --sign - "$work/gen/control.macho" 2>/dev/null
/usr/bin/codesign --verify --strict "$work/gen/control.macho"
if /usr/bin/otool -l "$work/gen/control.macho" | grep -q LC_LOAD_DYLIB; then echo 'unexpected dynamic library' >&2; exit 1; fi
# Only create and pass a new, private, non-device regular file.
dd if=/dev/zero of="$work/fixture" bs=8192 count=1 2>/dev/null
cp "$work/fixture" "$work/expected"
printf ABCD | dd of="$work/expected" bs=1 seek=4096 conv=notrunc 2>/dev/null
"$work/gen/control.macho" 3<>"$work/fixture"
cmp "$work/expected" "$work/fixture"
# Read-only FD must not succeed or mutate the file.
if "$work/gen/control.macho" 3<"$work/fixture"; then echo 'readonly accepted' >&2; exit 1; fi
cmp "$work/expected" "$work/fixture"
# Character devices and absent descriptors must be refused before any write.
if "$work/gen/control.macho" 3</dev/null; then echo 'character device accepted' >&2; exit 1; fi
if "$work/gen/control.macho" 3<&-; then echo 'absent fd accepted' >&2; exit 1; fi
printf '%s\n' 'native fixed-offset regular-file pwrite/fsync/pread passed; readonly/character/missing fd refused'
