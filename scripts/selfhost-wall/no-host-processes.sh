#!/usr/bin/env bash
# no-host-processes.sh -- the 100% selfhost acceptance probe (bash only).
#
#   scripts/selfhost-wall/no-host-processes.sh -- <command> [args...]
#   e.g. scripts/selfhost-wall/no-host-processes.sh -- ./amu-selfbuilt check src/kotoba/compiler/core.cljk
#
# Runs the command and records every program it (and its descendants) execs.
# Exit 0 only when the command succeeded AND no exec'd program is node, nodejs,
# nbb, java, javac, clojure, clj, graalvm/native-image tooling, python or bun/deno.
# Exit 3 when a forbidden program ran; 2 when no tracer is available (fails
# closed: an unverified run is not a pass). Pass --list to print the exec list.
#
#   Linux : strace -f -e trace=execve,execveat
#   macOS : dtruss -f -t execve   (needs sudo; set SUDO=sudo)
#   else  : not supported -> exit 2
#
# Denylist is matched on the basename of the exec'd path.
set -u
LIST=0
[ "${1:-}" = "--list" ] && { LIST=1; shift; }
[ "${1:-}" = "--" ] && shift
[ $# -gt 0 ] || { sed -n '2,16p' "$0"; exit 64; }
OUT=$(mktemp "${TMPDIR:-/tmp}/noproc.XXXXXX"); trap 'rm -f "$OUT"' EXIT
case "$(uname -s)" in
  Linux)
    command -v strace >/dev/null || { echo "no-host-processes: strace not found (fail closed)" >&2; exit 2; }
    strace -f -qq -e trace=execve,execveat -o "$OUT" -- "$@"; rc=$?
    PROGS=$(sed -nE 's/.*exec(ve|veat)\((AT_FDCWD, )?"([^"]+)".*/\3/p' "$OUT") ;;
  Darwin)
    command -v dtruss >/dev/null || { echo "no-host-processes: dtruss not found (fail closed)" >&2; exit 2; }
    ${SUDO:-sudo} dtruss -f -t execve -o "$OUT" "$@"; rc=$?
    PROGS=$(sed -nE 's/.*execve\("([^"]+)".*/\1/p' "$OUT") ;;
  *) echo "no-host-processes: unsupported OS (fail closed)" >&2; exit 2 ;;
esac
[ "$LIST" -eq 1 ] && printf '%s\n' "$PROGS"
BAD=$(printf '%s\n' "$PROGS" | awk -F/ '{print $NF}' | grep -E '^(node|nodejs|nbb|java|javac|jshell|clojure|clj|bb|python[0-9.]*|native-image|bun|deno|npx|npm)$' | sort | uniq -c)
if [ -n "$BAD" ]; then echo "no-host-processes: FORBIDDEN processes ran:" >&2; echo "$BAD" >&2; exit 3; fi
[ "$rc" -eq 0 ] || { echo "no-host-processes: command exited $rc" >&2; exit "$rc"; }
echo "no-host-processes: OK ($(printf '%s\n' "$PROGS" | grep -c .) execs, none forbidden)"
