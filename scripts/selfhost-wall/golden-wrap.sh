# Needs $HERE (the scripts directory) set by the caller. Sourced by ds-diff.sh / tm-diff.sh / vx-diff.sh. With WALL_GOLDEN_CACHE=1 the host side of the differential is
# stored once per (host function CID, case-set CID) by golden-cache.sh and reused; unset, nothing changes.
#   golden_begin <name> <module[:module..]> <case-input|@literal>...   exports WALL_GOLDEN (reused file or fresh path)
#   golden_end <exit status>                                            stores a fresh golden output
golden_begin() {
  [ -n "$WALL_GOLDEN_CACHE" ] || return 0
  _gc=$HERE/golden-cache.sh; _gdir=$(mktemp -d ${TMPDIR:-/tmp}/golden.XXXXXX); export WALL_GOLDEN=$_gdir/host.edn
  _gkey=$($_gc key "$@") || { echo "golden: no key, running uncached" >&2; unset WALL_GOLDEN _gkey; return 0; }
  _gstat=miss; $_gc get $_gkey $WALL_GOLDEN && _gstat=hit
  echo "golden: $1 key=${_gkey%${_gkey#????????????}} $_gstat" >&2
}
golden_end() {
  [ -n "$_gkey" ] || return $1
  [ "$_gstat" = miss ] && [ $1 -le 1 ] && [ -s "$WALL_GOLDEN" ] && $_gc put $_gkey $WALL_GOLDEN
  rm -rf $_gdir; return $1
}
