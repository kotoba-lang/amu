#!/bin/sh
# The Kotoba-route proof for the Form-walking rewrites: fixtures/forms.cljk is refused by `amu check` as written, is still
# refused after rule (a) alone (map items are i64 on this route), and passes after (a)+(f).
#   WALL_CP=/private/tmp/wall-cp-5.txt WALL_AMU_SRC=<amu src> WALL_K=<kotoba-lang> kotoba-route-check.sh [workdir]
HERE="$(cd "$(dirname "$0")" && pwd)"; W=${1:-/tmp/codemod-kcheck}; mkdir -p "$W"
ONE=${WALL_ONE:-/private/tmp/wall-one.sh}
"$HERE/codemod.sh" "$HERE/fixtures/forms.cljk" --rules a --out "$W/forms.a.cljk" > /dev/null
"$HERE/codemod.sh" "$HERE/fixtures/forms.cljk" --rules a,f --out "$W/forms.af.cljk" > /dev/null
for f in "$HERE/fixtures/forms.cljk" "$W/forms.a.cljk" "$W/forms.af.cljk"; do "$ONE" "$f" | cut -c1-240; done
