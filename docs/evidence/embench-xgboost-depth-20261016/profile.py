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
    group_max_histogram: collections.Counter[int] = collections.Counter()
    depths_by_sample: list[list[int]] = []
    visited_features: list[int] = []
    groups_within_five = 0
    total_groups = 0
    group_stop_steps = 0
    for sample in range(128):
        sample_base = sample * 64
        sample_depths: list[int] = []
        for tree in range(400):
            node = 0
            depth = 0
            while (node & 128) == 0:
                at = node_bases[tree] + node
                feature = arrays["comparison-idxs"][at]
                visited_features.append(feature)
                threshold = arrays["comparison-values"][at]
                value = arrays["x-test"][sample_base + feature]
                children = "left-children" if value < threshold else "right-children"
                node = arrays[children][at]
                depth += 1
                if depth > 128:
                    raise ValueError(f"tree walk did not reach a leaf: sample={sample}, tree={tree}")
            histogram[depth] += 1
            sample_depths.append(depth)
        depths_by_sample.append(sample_depths)
        for first_tree in range(0, 400, 4):
            total_groups += 1
            group_max = max(sample_depths[first_tree : first_tree + 4])
            group_max_histogram[group_max] += 1
            group_stop_steps += 4 * group_max
            if group_max <= 5:
                groups_within_five += 1

    walk_count = sum(histogram.values())
    fixed_steps = 5
    table_input_loads_per_step = 5
    dynamic_steps = sum(depth * count for depth, count in histogram.items())
    shallow_walks = sum(count for depth, count in histogram.items() if depth < fixed_steps)
    group_stop_saved_steps = walk_count * fixed_steps - group_stop_steps
    group_stop_extra_steps = group_stop_steps - dynamic_steps
    group_stop_checks = sum(min(depth, fixed_steps - 1) * count for depth, count in group_max_histogram.items())
    group_width_sensitivity = []
    for width in (1, 2, 4, 8, 10, 20, 40, 400):
        if 400 % width:
            raise ValueError(f"group width must divide the 400-tree class: {width}")
        groups = 0
        grouped_steps = 0
        stop_checks = 0
        for sample_depths in depths_by_sample:
            for first_tree in range(0, 400, width):
                group_max = max(sample_depths[first_tree : first_tree + width])
                groups += 1
                grouped_steps += width * group_max
                stop_checks += min(group_max, fixed_steps - 1)
        group_width_sensitivity.append({
            "groupWidth": width,
            "groups": groups,
            "steps": grouped_steps,
            "savedStepsVsFixedFive": walk_count * fixed_steps - grouped_steps,
            "savedPercentVsFixedFive": 100 * (walk_count * fixed_steps - grouped_steps) / (walk_count * fixed_steps),
            "stopChecks": stop_checks,
        })
    result = {
        "schema": "amu.embench.xgboost-depth-profile/v3",
        "source": "bench/embench/reproduce-20261015/ports/official-xgboost.kotoba",
        "sourceSha256": hashlib.sha256(source_bytes).hexdigest(),
        "model": {"samples": 128, "trees": 400, "walks": walk_count},
        "treeSizeMin": min(sizes),
        "treeSizeMax": max(sizes),
        "allTreeSizesBelow1024": all(size < 1024 for size in sizes),
        "visitedInternalFeatureCount": len(visited_features),
        "maxVisitedFeatureIndex": max(visited_features),
        "allVisitedFeatureIndicesBelow64": all(feature < 64 for feature in visited_features),
        "walkDepthHistogram": {str(k): histogram[k] for k in sorted(histogram)},
        "dynamicWalkSteps": dynamic_steps,
        "twFixedStepsPerWalk": fixed_steps,
        "twFixedWalkSteps": walk_count * fixed_steps,
        "walksEndingBeforeFiveSteps": shallow_walks,
        "groupsOfFourWithinFiveSteps": groups_within_five,
        "groupsOfFour": total_groups,
        "groupMaxDepthHistogram": {str(k): group_max_histogram[k] for k in sorted(group_max_histogram)},
        "twIdealGroupStopSteps": group_stop_steps,
        "twIdealGroupStopChecks": group_stop_checks,
        "twIdealGroupStopSavedStepsVsFixedFive": group_stop_saved_steps,
        "twIdealGroupStopSavedPercentVsFixedFive": 100 * group_stop_saved_steps / (walk_count * fixed_steps),
        "twIdealGroupStopExtraStepsVsDynamicWalk": group_stop_extra_steps,
        "twIdealGroupStopExtraLoadsVsDynamicWalk": group_stop_extra_steps * table_input_loads_per_step,
        "twIdealGroupStopSavedLoadsVsFixedFive": group_stop_saved_steps * table_input_loads_per_step,
        "groupWidthSensitivity": group_width_sensitivity,
        "extraStepsAgainstDynamicWalk": walk_count * fixed_steps - dynamic_steps,
        "twTableInputLoadsPerStep": table_input_loads_per_step,
        "extraLoadsIfAllGroupsTakeTw": (walk_count * fixed_steps - dynamic_steps) * table_input_loads_per_step,
        "meanDynamicStepsPerWalk": dynamic_steps / walk_count,
        "scope": "input-data and group-predicate analysis only; not runtime-admission trace, timing, or speedup evidence",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
