#!/bin/sh
# Native syscall diagnostic: ONLY a private regular-file fixture is writable.
set -eu
: "${TMPDIR:?set TMPDIR to workspace scratch}"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../.." && pwd)
bootstrap="$root/seed/bootstrap/aarch64-macos"
[ "$(uname -s) $(uname -m)" = 'Darwin arm64' ] || exit 1
work=$(mktemp -d "$TMPDIR/block-geometry.XXXXXXXX")
rawdev=
cleanup() {
  if [ -z "$rawdev" ] && [ -s "$work/attach.plist" ]; then
    rawdev=$(/usr/bin/plutil -extract system-entities.0.dev-entry raw -o - "$work/attach.plist" 2>/dev/null || true)
    if [ -z "$rawdev" ]; then echo "cannot identify attached image; retaining $work" >&2; return; fi
  fi
  if [ -n "$rawdev" ]; then
    case "$rawdev" in /dev/disk[0-9]*) ;; *) echo "invalid attached image; retaining $work" >&2; return;; esac
    case "$rawdev" in /dev/disk*[!0-9]*) echo "invalid attached image; retaining $work" >&2; return;; esac
    if ! hdiutil detach "$rawdev" >/dev/null 2>&1; then echo "detach failed; retaining $work" >&2; return; fi
  fi
  rm -rf "$work"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
mkdir "$work/build" "$work/gen"
for kind in compiler packager; do
  if [ "$kind" = compiler ]; then file=amu-full-root.macho; else file=kotoba-packager-root.macho; fi
  expected=$(/usr/bin/plutil -extract "$kind.sha256" raw -o - "$bootstrap/root.json")
  actual=$(shasum -a 256 "$bootstrap/$file" | cut -c1-64)
  [ "$actual" = "$expected" ] || { echo "$kind hash mismatch" >&2; exit 1; }
done
cp "$root/seed/macos-geometry-control-packager.kotoba" "$work/build/source.kotoba"
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
# Attach only a newly created read-only task-owned disk image. Never use an
# existing disk number as input. Detach precisely the image this test attached.
hdiutil create -size 4m -type SPARSE -layout NONE "$work/fixture.sparseimage" > "$work/create.log"
hdiutil attach -nomount -readonly -plist "$work/fixture.sparseimage" > "$work/attach.plist"
rawdev=$(/usr/bin/plutil -extract system-entities.0.dev-entry raw -o - "$work/attach.plist")
case "$rawdev" in /dev/disk[0-9]*) ;; *) echo 'invalid disk image device' >&2; exit 1;; esac
case "$rawdev" in /dev/disk*[!0-9]*) echo 'invalid disk image device' >&2; exit 1;; esac
info=$(diskutil info -plist "$rawdev")
[ "$(printf '%s' "$info" | /usr/bin/plutil -extract BusProtocol raw -o - -)" = 'Disk Image' ]
[ "$(printf '%s' "$info" | /usr/bin/plutil -extract VirtualOrPhysical raw -o - -)" = Virtual ]
[ "$(printf '%s' "$info" | /usr/bin/plutil -extract Size raw -o - -)" = 4194304 ]
rawchar="/dev/r${rawdev#/dev/}"
"$work/gen/control.macho" 3<"$rawchar" > "$work/geometry"
printf '\000\002\000\000\000\000\000\000\000\040\000\000\000\000\000\000' > "$work/expected"
cmp "$work/expected" "$work/geometry"
# A regular file, unsupported character device and absent descriptor refuse.
printf fixture > "$work/regular"
if "$work/gen/control.macho" 3<"$work/regular" > "$work/regular.out"; then echo 'regular file accepted' >&2; exit 1; fi
if "$work/gen/control.macho" 3</dev/null > "$work/null.out"; then echo 'unsupported device accepted' >&2; exit 1; fi
if "$work/gen/control.macho" 3<&- > "$work/absent.out"; then echo 'absent fd accepted' >&2; exit 1; fi
[ ! -s "$work/regular.out" ] && [ ! -s "$work/null.out" ] && [ ! -s "$work/absent.out" ]
printf '%s\n' 'native read-only device geometry: 512 bytes x 8192 blocks; invalid descriptors refused'
