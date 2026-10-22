# Require graph of the files named on stdin (one absolute path per line), breadth first.
#   awk -v ROOTS=r1:r2:... -v COMPAT=<dir> -f wall-graph.awk < list.txt
# Prints "N <path>" for every file reached and "E <from> <to>" for every resolved require.
# Resolution mirrors reach-list.py: roots in order, extensions .kotoba .cljk .cljc. A module that has a twin
# <COMPAT>/<ns path>.kotoba also depends on that twin (the project route may read either). The requires are
# every `[a.b ...` in the ns form, reader-conditional branches included: a superset of the real graph, so a
# key can only be too sensitive, never too stale. Plain awk on purpose: no nbb, no Python.
function exists(p,   r) { r = (getline _junk < p); if (r >= 0) { close(p); return 1 } return 0 }
function resolve(ns,   rel, i, e, p) {
  rel = ns; gsub(/\./, "/", rel); gsub(/-/, "_", rel)
  for (i = 1; i <= nroots; i++) for (e = 1; e <= 3; e++) { p = roots[i] "/" rel ext[e]; if (exists(p)) return p }
  return ""
}
function twin(ns,   rel, p) {
  rel = ns; gsub(/\./, "/", rel); gsub(/-/, "_", rel)
  p = COMPAT "/" rel ".kotoba"
  return exists(p) ? p : ""
}
function add(p) { if (!(p in seen)) { seen[p] = 1; queue[++qn] = p } }
function edge(from, to) { if (to != "" && to != from && !((from SUBSEP to) in edges)) { edges[from, to] = 1; print "E", from, to; add(to) } }
function requires(f,   line, innst, txt, m, name, n) {
  innst = 0; txt = ""
  while ((getline line < f) > 0) {
    if (!innst) { if (line ~ /^\(ns[ \t]/ || line ~ /^\(ns$/) { innst = 1; txt = line "\n" } }
    else { if (line ~ /^\(def/ || line ~ /^\(ns[ \t]/) break; txt = txt line "\n" }
  }
  close(f)
  while (match(txt, /\[[a-z][-A-Za-z0-9_.]*[] \t\n]/)) {
    name = substr(txt, RSTART + 1, RLENGTH - 2)
    txt = substr(txt, RSTART + RLENGTH - 1)
    if (index(name, ".") > 0) { edge(f, resolve(name)); edge(f, twin(name)) }
  }
}
BEGIN { nroots = split(ROOTS, roots, ":"); ext[1] = ".kotoba"; ext[2] = ".cljk"; ext[3] = ".cljc"; qn = 0 }
{ if ($0 != "") add($0) }
END {
  for (qi = 1; qi <= qn; qi++) { f = queue[qi]; print "N", f; if (exists(f)) requires(f) }
}
