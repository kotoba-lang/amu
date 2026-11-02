#!/bin/sh
# Native selfhost diagnostic using regular files only, never a device path.
set -eu
: "${TMPDIR:?set TMPDIR to workspace scratch}"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../.." && pwd)
bootstrap="$root/seed/bootstrap/aarch64-macos"
[ "$(uname -s) $(uname -m)" = 'Darwin arm64' ] || { echo 'Apple Silicon macOS required' >&2; exit 1; }
work=$(mktemp -d "$TMPDIR/block-file-host.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir "$work/build" "$work/scope"
for kind in compiler packager; do
  if [ "$kind" = compiler ]; then file=amu-full-root.macho; else file=kotoba-packager-root.macho; fi
  expected=$(/usr/bin/plutil -extract "$kind.sha256" raw -o - "$bootstrap/root.json")
  actual=$(shasum -a 256 "$bootstrap/$file" | cut -c1-64)
  [ "$actual" = "$expected" ] || { echo "$kind hash mismatch" >&2; exit 1; }
done
for f in 00-ns-static 01-mem 02-io; do cat "$root/seed/$f.kotoba"; printf '\n'; done > "$work/build/program.kotoba"
sed '1d; /^(defn main /,$d' "$here/guard.kotoba" >> "$work/build/program.kotoba"
cat "$here/file-host.kotoba" >> "$work/build/program.kotoba"
(cd "$work/build" && env -i PATH=/nonexistent "$bootstrap/amu-full-root.macho" compile program.kotoba --target aarch64-macos --output program.kseed 3<.) > "$work/compile.log" 2>&1
(cd "$work/build" && env -i PATH=/nonexistent "$bootstrap/amu-full-root.macho" extract-native program.kseed --symbol main --output program.raw 3<.) > "$work/extract.log" 2>&1
entry=$(sed -n 's/^{:ok true, :output "program.raw", :offset \([0-9][0-9]*\), :length \([0-9][0-9]*\), :arity 0}$/\1/p' "$work/extract.log")
[ -n "$entry" ] || { cat "$work/extract.log" >&2; exit 1; }
(cd "$work/build" && env -i PATH=/nonexistent "$bootstrap/kotoba-packager-root.macho" program.macho program.raw fs2-cli-stdio-general "$entry" 3<.) > "$work/package.log" 2>&1
chmod 755 "$work/build/program.macho"
/usr/bin/codesign --force --sign - "$work/build/program.macho" 2>/dev/null
for mode in deny replay different mounted expired session size internal busy allow; do
  mkdir "$work/scope/$mode"
  (cd "$work/scope/$mode" && env -i PATH=/nonexistent "$work/build/program.macho" "$mode" 3<.) > "$work/$mode.out" 2> "$work/$mode.err"
  [ ! -s "$work/$mode.err" ]
  if [ "$mode" = allow ]; then
    [ -f "$work/scope/$mode/fixture" ]
    [ "$(cat "$work/scope/$mode/fixture")" = AMU ]
    [ "$(wc -c < "$work/scope/$mode/fixture" | tr -d ' ')" = 4 ]
  else
    [ ! -e "$work/scope/$mode/fixture" ] || { echo "$mode wrote a file" >&2; exit 1; }
  fi
done
mkdir "$work/scope/no-grant"
no_grant=0
(cd "$work/scope/no-grant" && env -i PATH=/nonexistent "$work/build/program.macho" allow 3<&-) > "$work/no-grant.out" 2> "$work/no-grant.err" || no_grant=$?
[ ! -e "$work/scope/no-grant/fixture" ] || { echo 'missing grant wrote a file' >&2; exit 1; }
[ "$no_grant" != 0 ] || { echo 'missing grant incorrectly reported success' >&2; exit 1; }
printf '%s\n' 'native scoped file host: allow writes; ten refusal conditions leave no file'
