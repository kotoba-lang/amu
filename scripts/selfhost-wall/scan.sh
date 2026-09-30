#!/bin/zsh
# Usage: scan.sh <list.txt> <out.tsv>   (same env as check-one.sh). Prints the pass count.
here=$(cd "$(dirname "$0")" && pwd)
xargs -P 6 -n1 $here/check-one.sh < $1 > $2
echo "OK: $(grep -c '	OK$' $2) of $(wc -l < $2)"
cut -f2 $2 | cut -c1-100 | sort | uniq -c | sort -rn | head -15
