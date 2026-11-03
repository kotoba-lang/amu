#!/bin/sh
# Native syscall diagnostic: ONLY a private regular-file fixture is writable.
set -eu
echo 'disabled: Disk Arbitration daemon crash investigation (JUN-767)' >&2
exit 1
: "${TMPDIR:?set TMPDIR to workspace scratch}"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../.." && pwd)
bootstrap="$root/seed/bootstrap/aarch64-macos"
[ "$(uname -s) $(uname -m)" = 'Darwin arm64' ] || exit 1
work=$(mktemp -d "$TMPDIR/da-claimed.XXXXXXXX")
rawdev=
current_image=
# Safety observer: match both the temporary backing image and its device in
# DiskImages' current attachment list before opening or detaching anything.
owned_image() {
  hdiutil info -plist | /usr/bin/python3 -c 'import os, plistlib, sys
p=plistlib.loads(sys.stdin.buffer.read())
dev,image=sys.argv[1:]
matches=[x for x in p.get("images",[]) if os.path.realpath(x.get("image-path", "")) == os.path.realpath(image) and any(y.get("dev-entry") == dev for y in x.get("system-entities", []))]
sys.exit(0 if len(matches)==1 else 1)' "$1" "$2"
}
cleanup() {
  if [ -z "$rawdev" ] && [ -s "$work/attach.plist" ]; then
    rawdev=$(/usr/bin/plutil -extract system-entities.0.dev-entry raw -o - "$work/attach.plist" 2>/dev/null || true)
    if [ -z "$rawdev" ]; then echo "cannot identify attached image; retaining $work" >&2; return 1; fi
  fi
  if [ -n "$rawdev" ]; then
    case "$rawdev" in /dev/disk[0-9]*) ;; *) echo "invalid attached image; retaining $work" >&2; return 1;; esac
    case "$rawdev" in /dev/disk*[!0-9]*) echo "invalid attached image; retaining $work" >&2; return 1;; esac
    if [ -z "$current_image" ] || ! owned_image "$rawdev" "$current_image"; then echo "image identity changed; retaining $work" >&2; return 1; fi
    if ! hdiutil detach "$rawdev" >/dev/null 2>&1; then echo "detach failed; retaining $work" >&2; return 1; fi
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
cp "$root/seed/macos-da-claimed-packager.kotoba" "$work/build/source.kotoba"
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
# Attach only a fresh private read-only test image and query the matching disk.
hdiutil create -size 4m -type SPARSE -layout NONE "$work/fixture.sparseimage" > "$work/create.log"
current_image="$work/fixture.sparseimage"
hdiutil attach -nomount -readonly -plist "$current_image" > "$work/attach.plist"
rawdev=$(/usr/bin/plutil -extract system-entities.0.dev-entry raw -o - "$work/attach.plist")
case "$rawdev" in /dev/disk[0-9]*) ;; *) exit 1;; esac
case "$rawdev" in /dev/disk*[!0-9]*) exit 1;; esac
owned_image "$rawdev" "$current_image" || exit 1
printf '%s\0' "$rawdev" > "$work/query"
"$work/gen/control.macho" < "$work/query" > "$work/result"
printf '\000\000\000\000' > "$work/unclaimed"
printf '\001\000\000\000' > "$work/claimed"
if ! cmp -s "$work/unclaimed" "$work/result" && ! cmp -s "$work/claimed" "$work/result"; then echo 'invalid claim state' >&2; exit 1; fi
printf '/dev/disk999999\0' > "$work/missing"
if "$work/gen/control.macho" < "$work/missing" > "$work/refused"; then echo 'missing disk accepted' >&2; exit 1; fi
[ ! -s "$work/refused" ]
if "$work/gen/control.macho" </dev/null > "$work/refused"; then echo 'missing request accepted' >&2; exit 1; fi
[ ! -s "$work/refused" ]
printf '/dev/disk1' > "$work/nonul"
if "$work/gen/control.macho" < "$work/nonul" > "$work/refused"; then echo 'unterminated request accepted' >&2; exit 1; fi
[ ! -s "$work/refused" ]
printf '%s\n' 'native Disk Arbitration claim-state: private image returned a boolean; missing disk/request refused'
