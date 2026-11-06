#!/bin/sh
# Native syscall diagnostic: ONLY a private regular-file fixture is writable.
set -eu
: "${TMPDIR:?set TMPDIR to workspace scratch}"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../.." && pwd)
bootstrap="$root/seed/bootstrap/aarch64-macos"
[ "$(uname -s) $(uname -m)" = 'Darwin arm64' ] || exit 1
work=$(mktemp -d "$TMPDIR/block-raw-fixture.XXXXXXXX")
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
cp "$root/seed/macos-raw-fixture-packager.kotoba" "$work/build/source.kotoba"
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
# Build a separate read-only verifier from Kotoba using the same pinned root.
cp "$root/seed/macos-raw-readback-packager.kotoba" "$work/build/readback.kotoba"
(cd "$work/build" && env -i PATH=/nonexistent "$bootstrap/amu-full-root.macho" compile readback.kotoba --target aarch64-macos --output r.kseed 3<.) > "$work/compile-read.log" 2>&1
(cd "$work/build" && env -i PATH=/nonexistent "$bootstrap/amu-full-root.macho" extract-native r.kseed --symbol main --output r.raw 3<.) > "$work/extract-read.log" 2>&1
read_entry=$(sed -n 's/^{:ok true, :output "r.raw", :offset \([0-9][0-9]*\), :length \([0-9][0-9]*\), :arity 0}$/\1/p' "$work/extract-read.log")
[ -n "$read_entry" ] || { cat "$work/extract-read.log" >&2; exit 1; }
(cd "$work/build" && env -i PATH=/nonexistent "$bootstrap/kotoba-packager-root.macho" reader-generator r.raw fs2-cli-stdio-general "$read_entry" 3<.) > "$work/package-read.log" 2>&1
chmod 755 "$work/build/reader-generator"
/usr/bin/codesign --force --sign - "$work/build/reader-generator" 2>/dev/null
(cd "$work/gen" && env -i PATH=/nonexistent "$work/build/reader-generator" reader.macho strict 3<.)
chmod 755 "$work/gen/reader.macho"
/usr/bin/codesign --force --sign - "$work/gen/reader.macho" 2>/dev/null
/usr/bin/codesign --verify --strict "$work/gen/reader.macho"
if /usr/bin/otool -l "$work/gen/reader.macho" | grep -q LC_LOAD_DYLIB; then echo 'unexpected readback dynamic library' >&2; exit 1; fi
# Construct and mark a private raw file *before* attaching it. This test
# never accepts a caller-supplied device; only the attach result is opened.
dd if=/dev/zero of="$work/fixture.img" bs=1048576 count=4 2>/dev/null
printf JUN767V1 | dd of="$work/fixture.img" bs=1 count=8 conv=notrunc 2>/dev/null
cp "$work/fixture.img" "$work/expected.img"
printf JUN767V1 | dd of="$work/expected.img" bs=1 seek=4096 count=8 conv=notrunc 2>/dev/null
current_image="$work/fixture.img"
hdiutil attach -nomount -plist "$current_image" > "$work/attach.plist"
rawdev=$(/usr/bin/plutil -extract system-entities.0.dev-entry raw -o - "$work/attach.plist")
case "$rawdev" in /dev/disk[0-9]*) ;; *) echo 'invalid disk image device' >&2; exit 1;; esac
case "$rawdev" in /dev/disk*[!0-9]*) echo 'invalid disk image device' >&2; exit 1;; esac
owned_image "$rawdev" "$current_image" || { echo "image identity mismatch" >&2; exit 1; }
info=$(diskutil info -plist "$rawdev")
[ "$(printf '%s' "$info" | /usr/bin/plutil -extract BusProtocol raw -o - -)" = 'Disk Image' ]
[ "$(printf '%s' "$info" | /usr/bin/plutil -extract VirtualOrPhysical raw -o - -)" = Virtual ]
[ "$(printf '%s' "$info" | /usr/bin/plutil -extract Size raw -o - -)" = 4194304 ]
rawchar="/dev/r${rawdev#/dev/}"
# On the read-only descriptor the valid marker/geometry cannot authorize a
# write. Check the target sector is still zero before running the positive.
if "$work/gen/control.macho" 3<"$rawchar"; then echo 'readonly accepted' >&2; exit 1; fi
dd if="$rawchar" of="$work/before-sector" bs=512 skip=8 count=1 2>/dev/null
dd if=/dev/zero of="$work/zero-sector" bs=512 count=1 2>/dev/null
cmp "$work/zero-sector" "$work/before-sector"
owned_image "$rawdev" "$current_image" || { echo "image changed" >&2; exit 1; }
"$work/gen/control.macho" 3<>"$rawchar"
# The exact private backing image is checked after the device is detached.
owned_image "$rawdev" "$current_image" || { echo "image changed before detach" >&2; exit 1; }
hdiutil detach "$rawdev" > "$work/detach.log"
rm "$work/attach.plist"
rawdev=
cmp "$work/expected.img" "$work/fixture.img"
# Reattach the same image read-only and execute a separately generated
# Kotoba-native verifier. This checks the whole target block after reattach.
current_image="$work/fixture.img"
hdiutil attach -nomount -readonly -plist "$current_image" > "$work/attach.plist"
rawdev=$(/usr/bin/plutil -extract system-entities.0.dev-entry raw -o - "$work/attach.plist")
case "$rawdev" in /dev/disk[0-9]*) ;; *) echo 'invalid readback image device' >&2; exit 1;; esac
case "$rawdev" in /dev/disk*[!0-9]*) echo 'invalid readback image device' >&2; exit 1;; esac
owned_image "$rawdev" "$current_image" || { echo 'readback image identity mismatch' >&2; exit 1; }
rawchar="/dev/r${rawdev#/dev/}"
"$work/gen/reader.macho" 3<"$rawchar"
owned_image "$rawdev" "$current_image" || { echo 'readback image changed' >&2; exit 1; }
hdiutil detach "$rawdev" > "$work/detach.log"
rm "$work/attach.plist"
rawdev=
cmp "$work/expected.img" "$work/fixture.img"
# Fresh, task-owned negative images: wrong marker and wrong size. The
# observer compares each complete backing file before and after refusal.
for negative in marker geometry; do
  blocks=4
  if [ "$negative" = geometry ]; then blocks=8; fi
  dd if=/dev/zero of="$work/negative.img" bs=1048576 count="$blocks" 2>/dev/null
  if [ "$negative" = geometry ]; then
    printf JUN767V1 | dd of="$work/negative.img" bs=1 count=8 conv=notrunc 2>/dev/null
  fi
  cp "$work/negative.img" "$work/negative-before.img"
  current_image="$work/negative.img"
  hdiutil attach -nomount -plist "$current_image" > "$work/attach.plist"
  rawdev=$(/usr/bin/plutil -extract system-entities.0.dev-entry raw -o - "$work/attach.plist")
  case "$rawdev" in /dev/disk[0-9]*) ;; *) echo 'invalid negative image device' >&2; exit 1;; esac
  case "$rawdev" in /dev/disk*[!0-9]*) echo 'invalid negative image device' >&2; exit 1;; esac
  owned_image "$rawdev" "$current_image" || { echo "negative image identity mismatch" >&2; exit 1; }
  info=$(diskutil info -plist "$rawdev")
  [ "$(printf '%s' "$info" | /usr/bin/plutil -extract BusProtocol raw -o - -)" = 'Disk Image' ]
  [ "$(printf '%s' "$info" | /usr/bin/plutil -extract VirtualOrPhysical raw -o - -)" = Virtual ]
  [ "$(printf '%s' "$info" | /usr/bin/plutil -extract Size raw -o - -)" = "$((blocks * 1048576))" ]
  rawchar="/dev/r${rawdev#/dev/}"
  if "$work/gen/control.macho" 3<>"$rawchar"; then echo "$negative accepted" >&2; exit 1; fi
  if "$work/gen/reader.macho" 3<"$rawchar"; then echo "$negative readback accepted" >&2; exit 1; fi
  owned_image "$rawdev" "$current_image" || { echo "negative image changed" >&2; exit 1; }
  hdiutil detach "$rawdev" > "$work/detach.log"
  rm "$work/attach.plist"
  rawdev=
  cmp "$work/negative-before.img" "$work/negative.img"
done
# A valid image with a corrupted byte after the destination marker must
# fail the independent native verifier, without any write by the verifier.
dd if=/dev/zero of="$work/corrupt.img" bs=1048576 count=4 2>/dev/null
printf JUN767V1 | dd of="$work/corrupt.img" bs=1 seek=4096 count=8 conv=notrunc 2>/dev/null
printf X | dd of="$work/corrupt.img" bs=1 seek=4104 count=1 conv=notrunc 2>/dev/null
cp "$work/corrupt.img" "$work/corrupt-before.img"
current_image="$work/corrupt.img"
hdiutil attach -nomount -readonly -plist "$current_image" > "$work/attach.plist"
rawdev=$(/usr/bin/plutil -extract system-entities.0.dev-entry raw -o - "$work/attach.plist")
case "$rawdev" in /dev/disk[0-9]*) ;; *) echo 'invalid corrupt image device' >&2; exit 1;; esac
case "$rawdev" in /dev/disk*[!0-9]*) echo 'invalid corrupt image device' >&2; exit 1;; esac
owned_image "$rawdev" "$current_image" || { echo 'corrupt image identity mismatch' >&2; exit 1; }
rawchar="/dev/r${rawdev#/dev/}"
if "$work/gen/reader.macho" 3<"$rawchar"; then echo 'corruption accepted' >&2; exit 1; fi
owned_image "$rawdev" "$current_image" || { echo 'corrupt image changed' >&2; exit 1; }
hdiutil detach "$rawdev" > "$work/detach.log"
rm "$work/attach.plist"
rawdev=
cmp "$work/corrupt-before.img" "$work/corrupt.img"
# A regular-file descriptor and an absent descriptor must refuse.
if "$work/gen/control.macho" 3<"$work/fixture.img"; then echo 'regular file accepted' >&2; exit 1; fi
if "$work/gen/control.macho" 3<&-; then echo 'absent fd accepted' >&2; exit 1; fi
printf '%s\n' 'native raw image: aligned write/fsync and native readback after reattach passed; negative and corrupted fixtures refused'
