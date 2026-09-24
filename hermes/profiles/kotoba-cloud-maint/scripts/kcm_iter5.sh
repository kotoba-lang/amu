#!/bin/bash
for p in shadow-cljs "@noble/post-quantum"; do
  echo "$p latest: $(npm view $p version 2>/dev/null)"
done
