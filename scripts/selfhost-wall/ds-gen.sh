#!/bin/zsh
# Generate the desugar-differential guest from kotoba-sema's frontend.cljk (the :kotoba view of the desugar half).
HERE="$(cd "$(dirname "$0")" && pwd)"
TM_NAMES=$HERE/ds-names.txt TM_TAIL=$HERE/ds-tail.cljk TM_HEADER=$HERE/ds-header.cljk \
  python3 "$HERE/tm-gen.py" "${FRONTEND:?set FRONTEND}" "${DS_GUEST:-/tmp/ds_guest.cljk}"
