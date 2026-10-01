# Shared by scan-cached.sh and golden-cache.sh (source it). Effects only: the decisions are wall_cache.cljk's.
# Needs: here, AMU, K, CP, CPF, AMU_SRC, CHECK, work set by the caller.
plan() {  # stdin -> stdout, one invocation of the pure module
  if [ -n "$WALL_PLAN" ]; then eval "$WALL_PLAN"; else
    local nbbdir=${WALL_NBB_DIR:-$AMU}; [ -d $nbbdir/node_modules/nbb ] || nbbdir=/Users/junkawasaki/github/kotoba-lang/amu-measure
    (cd $nbbdir && node --stack-size=${WALL_STACK_SIZE:-8192} node_modules/nbb/cli.js --classpath "$AMU/src:$CP" $here/wall-cache-plan.cljs)
  fi
}
sha() { shasum -a 256 | cut -d' ' -f1; }

wc_graph() {  # $1 = file listing the root modules; fills $work/{graph.txt,nodes.txt,sha.tsv,checker.tsv,nodes.plan}, cpid, chk
local list=$1
roots="$(echo "$CP" | tr ':' '\n' | grep '/src$' | tr '\n' ':')$AMU_SRC"
awk -v ROOTS="$roots" -v COMPAT=$K/lang/compat -f $here/wall-graph.awk < $list > $work/graph.txt
awk '$1=="N"{print $2}' $work/graph.txt | sort -u > $work/nodes.txt
xargs -n 100 shasum -a 256 < $work/nodes.txt 2>/dev/null | awk '{print $2 "\t" $1}' | sort > $work/sha.tsv
# 2. checker identity: classpath string, and the bytes of the checker -- every non-amu local src/resources dir on
#    the classpath (the language implementation), the grant policy, the check script, the compat twins, extras.
#    gitlibs/.m2 entries are pinned by their path (a commit sha / a version).
{
  # A dir that holds one of the listed files (or is WALL_SUBJECT_DIRS, or is amu's own src) is SUBJECT, not checker:
  # editing it must only invalidate the files that require the edited module, not every verdict.
  echo "$CP" | tr ':' '\n' | grep -v "^$AMU_SRC\$" | grep '/\(src\|resources\)$' | grep -v '/\.gitlibs/\|/\.m2/' |
    awk -v LIST=$list -v SUBJ="$WALL_SUBJECT_DIRS" 'BEGIN { while ((getline l < LIST) > 0) files[++n] = l; ns = split(SUBJ, sd, ":") }
      { d = $0; for (i = 1; i <= n; i++) if (index(files[i], d "/") == 1) next; for (i = 1; i <= ns; i++) if (sd[i] == d) next; print d }' |
    while read d; do find $d -type f ! -name '.*' 2>/dev/null; done
  find $K/lang/compat -type f ! -name '.*'
  echo $K/lang/selfhost-compiler-grant.edn; echo $CHECK; echo $here/check-one.sh
  for x in ${=WALL_CHECKER_EXTRA} $AMU_NATIVE; do echo $x; done   # a native checker binary is part of the checker
  [ -n "$WALL_STRICT" ] && echo $AMU_SRC/kotoba/compiler/nbb/wasm_cli.cljk
} | sort -u | xargs -n 100 shasum -a 256 2>/dev/null | awk '{print $2 "\t" $1}' | sort > $work/checker.tsv
cpid=$(echo "$CP" | sha); chk=$(cat $work/checker.tsv | sha)
awk -v SHA=$work/sha.tsv -v G=$work/graph.txt '
  BEGIN { n = 0; while ((getline l < SHA) > 0) { split(l, a, "\t"); sh[a[1]] = a[2] }
          while ((getline l < G) > 0) { split(l, a, " "); if (a[1] == "E") deps[a[2]] = deps[a[2]] " " a[3] } }
  { id[$0] = n; path[n++] = $0 }
  END { for (i = 0; i < n; i++) { p = path[i]; ds = ""; split(deps[p], dd, " ")
          for (j in dd) ds = ds " " id[dd[j]]; sub(/^ /, "", ds)
          printf "N\t%s\t%s\t%s\n", p, (p in sh ? sh[p] : "MISSING"), ds } }' < $work/nodes.txt > $work/nodes.plan
}

