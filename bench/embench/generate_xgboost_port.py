#!/usr/bin/env python3
"""Generate the lossless Kotoba correctness port for Embench xgboost."""

from __future__ import annotations

import argparse
import base64
import re
from pathlib import Path


ARRAYS = (
    "tree_sizes",
    "comparison_idxs",
    "comparison_values",
    "left_children",
    "right_children",
    "leaf_values",
    "X_test",
    "Y_test",
)


def extract_array(source: str, name: str) -> list[int]:
    match = re.search(
        rf"const\s+uint8_t\s+{name}(?:\[[^;=]*\])*\s*=\s*\{{(.*?)\}}\s*;",
        source,
        re.DOTALL,
    )
    if match is None:
        raise ValueError(f"missing uint8_t array: {name}")
    return [int(value) for value in re.findall(r"\d+", match.group(1))]


def kotoba_string(values: list[int]) -> str:
    # ASCII base64 keeps byte offsets stable and fits the compiler's 64 KiB
    # aggregate string-literal admission limit for the complete model.
    encoded = base64.b64encode(bytes(values)).decode("ascii")
    return f'"{encoded}"'


def render(arrays: dict[str, list[int]]) -> str:
    sizes = {name: len(values) for name, values in arrays.items()}
    if sizes["tree_sizes"] != 400 or sizes["X_test"] != 128 * 64 or sizes["Y_test"] != 128:
        raise ValueError(f"unexpected upstream dimensions: {sizes}")
    constants = "\n\n".join(
        f"(def {name.replace('_', '-').lower()} {kotoba_string(values)})"
        for name, values in arrays.items()
    )
    return f'''(ns embench.xgboost (:export [run test-xgboost]))

;; Lossless correctness port of Embench-IoT xgboost.c and testbench.c.
;; Copyright (C) Embench contributors. SPDX-License-Identifier: GPL-3.0-or-later.
;; Every upstream uint8_t model and test value is encoded below. The original
;; 400 decision trees, 128 x 64 samples, and class labels are all evaluated.
;; This is one correctness iteration, not an official timed Embench score.

{constants}

(defn- sextet [code :i64] :i64
  (if (and (>= code 65) (<= code 90))
    (- code 65)
    (if (and (>= code 97) (<= code 122))
      (+ (- code 97) 26)
      (if (and (>= code 48) (<= code 57))
        (+ (- code 48) 52)
        (if (= code 43) 62 63)))))

(defn- byte-at [data :string index :i64] :i64
  (let [group (* (quot index 3) 4)
        lane (- index (* (quot index 3) 3))
        a (sextet (string-code-point-at data group))
        b (sextet (string-code-point-at data (+ group 1)))
        c (sextet (string-code-point-at data (+ group 2)))
        d (sextet (string-code-point-at data (+ group 3)))]
    (if (= lane 0)
      (+ (i64-shift-left a 2) (u64-shift-right b 4))
      (if (= lane 1)
        (+ (i64-shift-left (bit-and b 15) 4) (u64-shift-right c 2))
        (+ (i64-shift-left (bit-and c 3) 6) d)))))

(defn- walk-tree [sample-base :i64 node-base :i64 leaf-base :i64] :i64
  (loop [node 0]
    (if (= (bit-and node 128) 128)
      (byte-at leaf-values (+ leaf-base (bit-and node 127)))
      (let [feature (byte-at comparison-idxs (+ node-base node))
            threshold (byte-at comparison-values (+ node-base node))
            sample (byte-at x-test (+ sample-base feature))]
        (if (< sample threshold)
          (recur (byte-at left-children (+ node-base node)))
          (recur (byte-at right-children (+ node-base node))))))))

(defn- class-votes [sample-base :i64 class-index :i64
                    tree-index :i64 node-base :i64 leaf-base :i64] :i64
  (loop [j 0 tree tree-index node-offset node-base leaf-offset leaf-base total 0]
    (if (= j 40)
      total
      (let [tree-size (byte-at tree-sizes tree)
            vote (walk-tree sample-base node-offset leaf-offset)]
        (recur (+ j 1) (+ tree 1) (+ node-offset tree-size)
               (+ leaf-offset tree-size 1) (+ total vote))))))

(defn- class-node-base [class :i64] :i64
  (loop [tree 0 total 0]
    (if (= tree (* class 40))
      total
      (recur (+ tree 1) (+ total (byte-at tree-sizes tree))))))

(defn- votes-for-class [sample-base :i64 class :i64] :i64
  (let [tree (* class 40)
        node-base (class-node-base class)]
    (class-votes sample-base class tree node-base (+ node-base tree))))

(defn- predict [sample :i64] :i64
  (let [sample-base (* sample 64)
        votes [(votes-for-class sample-base 0) (votes-for-class sample-base 1)
               (votes-for-class sample-base 2) (votes-for-class sample-base 3)
               (votes-for-class sample-base 4) (votes-for-class sample-base 5)
               (votes-for-class sample-base 6) (votes-for-class sample-base 7)
               (votes-for-class sample-base 8) (votes-for-class sample-base 9)]]
    (loop [class 1 best-class 0 best-votes (vector-at votes 0)]
      (if (= class 10)
        best-class
        (let [candidate (vector-at votes class)]
          (if (> candidate best-votes)
            (recur (+ class 1) class candidate)
            (recur (+ class 1) best-class best-votes)))))))

(defn run [token :i64] :i64
  (if (= token 1)
    (loop [sample 0 correct 0]
      (if (= sample 128)
        correct
        (recur (+ sample 1)
               (+ correct (if (= (predict sample) (byte-at y-test sample)) 1 0)))))
    0))

(defn test-xgboost [] :i64
  ;; The upstream verifier only requires 128 / 12 correct predictions. Match
  ;; the full C oracle count instead so a damaged model cannot pass this port.
  (if (= (run 1) 126) 1 0))
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = args.upstream.read_text()
    arrays = {name: extract_array(source, name) for name in ARRAYS}
    args.output.write_text(render(arrays))


if __name__ == "__main__":
    main()
