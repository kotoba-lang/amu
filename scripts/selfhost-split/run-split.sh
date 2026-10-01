#!/bin/sh
# usage: run-split.sh SRC.cljk WORKDIR   -- analyse, partition, extract into WORKDIR/split (scratch)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=${1:?src}; W=${2:?workdir}; K=${K:-14}
mkdir -p "$W"
python3 "$HERE/analyze.py" partition "$SRC" "$W" --modules "$K" --names "$HERE/names-frontend.json"
rm -rf "$W/split"
python3 "$HERE/extract.py" "$SRC" "$W/partition.json" "$W/split"
