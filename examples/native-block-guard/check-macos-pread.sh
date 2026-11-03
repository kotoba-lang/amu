#!/bin/sh
# Native syscall diagnostic: ONLY a private regular-file fixture is writable.
set -eu
: "${TMPDIR:?set TMPDIR to workspace scratch}"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../.." && pwd)
bootstrap="$root/seed/bootstrap/aarch64-macos"
[ "$(uname -s) $(uname -m)" = 'Darwin arm64' ] || exit 1
work=$(mktemp -d "$TMPDIR/block-pread.XXXXXXXX")
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
cp "$root/seed/macos-pread-control-packager.kotoba" "$work/build/source.kotoba"
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
# Attach an independently populated private image read-only.
/usr/bin/python3 -c 'import sys; p=sys.argv[1]; f=open(p,"wb"); f.truncate(4194304); [(f.seek(s*512), f.write(bytes([(s+i)%256 for i in range(512)]))) for s in (0,17,8191)]; f.close()' "$work/fixture.img"
current_image="$work/fixture.img"
hdiutil attach -nomount -readonly -plist "$current_image" > "$work/attach.plist"
rawdev=$(/usr/bin/plutil -extract system-entities.0.dev-entry raw -o - "$work/attach.plist")
case "$rawdev" in /dev/disk[0-9]*) ;; *) exit 1;; esac
case "$rawdev" in /dev/disk*[!0-9]*) exit 1;; esac
owned_image "$rawdev" "$current_image" || { echo 'image identity mismatch' >&2; exit 1; }
info=$(diskutil info -plist "$rawdev")
[ "$(printf '%s' "$info" | /usr/bin/plutil -extract BusProtocol raw -o - -)" = 'Disk Image' ]
[ "$(printf '%s' "$info" | /usr/bin/plutil -extract VirtualOrPhysical raw -o - -)" = Virtual ]
[ "$(printf '%s' "$info" | /usr/bin/plutil -extract Size raw -o - -)" = 4194304 ]
rawchar="/dev/r${rawdev#/dev/}"
for sector in 0 17 8191; do
  /usr/bin/python3 -c 'import sys; sys.stdout.buffer.write(int(sys.argv[1]).to_bytes(8,"little"))' "$sector" > "$work/sector"
  "$work/gen/control.macho" 3<"$rawchar" < "$work/sector" > "$work/actual"
  /usr/bin/python3 -c 'import sys; s=int(sys.argv[1]); sys.stdout.buffer.write(bytes([(s+i)%256 for i in range(512)]))' "$sector" > "$work/expected"
  cmp "$work/expected" "$work/actual"
done
for sector in 8192 2251799813685248; do
  /usr/bin/python3 -c 'import sys; sys.stdout.buffer.write(int(sys.argv[1]).to_bytes(8,"little"))' "$sector" > "$work/sector"
  if "$work/gen/control.macho" 3<"$rawchar" < "$work/sector" > "$work/refused"; then echo 'out-of-range sector accepted' >&2; exit 1; fi
  [ ! -s "$work/refused" ]
done
if "$work/gen/control.macho" 3<"$rawchar" </dev/null > "$work/refused"; then echo 'missing request accepted' >&2; exit 1; fi
printf '\000\000\000\000' > "$work/short"
if "$work/gen/control.macho" 3<"$rawchar" < "$work/short" > "$work/refused"; then echo 'short request accepted' >&2; exit 1; fi
[ ! -s "$work/refused" ]
if "$work/gen/control.macho" 3<"$current_image" < "$work/sector" > "$work/refused"; then echo 'regular file accepted' >&2; exit 1; fi
if "$work/gen/control.macho" 3<&- < "$work/sector" > "$work/refused"; then echo 'missing fd accepted' >&2; exit 1; fi
[ ! -s "$work/refused" ]
printf '%s\n' 'native read-only pread: three sectors matched independent bytes; invalid requests and descriptors refused'
