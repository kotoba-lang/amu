#!/usr/bin/env python3
"""Profile decoded tree path lengths in the pinned M104 Kotoba xgboost port.

This is a deterministic input-data analysis. It does not run or time Amu or C,
and it does not establish a performance result.
"""

from __future__ import annotations

import base64
import collections
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "bench/embench/reproduce-20261015/ports/official-xgboost.kotoba"


def main() -> None:
    source_bytes = SOURCE.read_bytes()
    source = source_bytes.decode("utf-8")
    arrays = {
        name: base64.b64decode(value)
        for name, value in re.findall(
            r'\(def ([a-z0-9-]+) "([A-Za-z0-9+/=]+)"\)', source
        )
    }
    required = {
        "tree-sizes": 400,
        "comparison-idxs": 6087,
        "comparison-values": 6087,
        "left-children": 6087,
        "right-children": 6087,
        "leaf-values": 6487,
        "x-test": 128 * 64,
        "y-test": 128,
    }
    actual = {name: len(arrays.get(name, b"")) for name in required}
    if actual != required:
        raise ValueError(f"unexpected decoded model dimensions: {actual}")

    sizes = arrays["tree-sizes"]
    node_bases: list[int] = []
    node_base = 0
    for size in sizes:
        node_bases.append(node_base)
        node_base += size

    histogram: collections.Counter[int] = collections.Counter()
    for sample in range(128):
        sample_base = sample * 64
        for tree in range(400):
            node = 0
            depth = 0
            while (node & 128) == 0:
                at = node_bases[tree] + node
                feature = arrays["comparison-idxs"][at]
                threshold = arrays["comparison-values"][at]
                value = arrays["x-test"][sample_base + feature]
                children = "left-children" if value < threshold else "right-children"
                node = arrays[children][at]
                depth += 1
                if depth > 128:
                    raise ValueError(f"tree walk did not reach a leaf: sample={sample}, tree={tree}")
            histogram[depth] += 1

    walk_count = sum(histogram.values())
    fixed_steps = 5
    dynamic_steps = sum(depth * count for depth, count in histogram.items())
    shallow_walks = sum(count for depth, count in histogram.items() if depth < fixed_steps)
    result = {
        "schema": "amu.embench.xgboost-depth-profile/v1",
        "source": "bench/embench/reproduce-20261015/ports/official-xgboost.kotoba",
        "sourceSha256": hashlib.sha256(source_bytes).hexdigest(),
        "model": {"samples": 128, "trees": 400, "walks": walk_count},
        "walkDepthHistogram": {str(k): histogram[k] for k in sorted(histogram)},
        "dynamicWalkSteps": dynamic_steps,
        "tbatFixedStepsPerWalk": fixed_steps,
        "tbatFixedWalkSteps": walk_count * fixed_steps,
        "walksEndingBeforeFiveSteps": shallow_walks,
        "extraStepsAgainstDynamicWalk": walk_count * fixed_steps - dynamic_steps,
        "meanDynamicStepsPerWalk": dynamic_steps / walk_count,
        "scope": "input-data path-length analysis only; not codegen, timing, or speedup evidence",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
