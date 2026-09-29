#!/usr/bin/env python3
"""Generate the lossless Kotoba correctness port for Embench depthconv."""

from __future__ import annotations

import argparse
import base64
import re
from pathlib import Path


def array(source: str, name: str) -> list[int]:
    match = re.search(rf"(?:static\s+)?(?:int8_t|int32_t)\s+{name}(?:\[[^]]*\])?\s*=\s*\{{(.*?)\}}\s*;", source, re.S)
    if match is None:
        raise ValueError(name)
    return [int(x) for x in re.findall(r"-?\d+", match.group(1))]


def b64(values: list[int]) -> str:
    return base64.b64encode(bytes(x & 255 for x in values)).decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = args.upstream.read_text()
    inputs = array(source, "INPUT_DATA")
    filters = array(source, "FILTER_DATA")
    biases = array(source, "BIAS_DATA")
    expected = array(source, "EXPECTED_OUTPUT")
    if [len(inputs), len(filters), len(biases), len(expected)] != [128, 128, 32, 32]:
        raise ValueError("unexpected depthconv dimensions")
    bias_literal = " ".join(map(str, biases))
    expected_literal = " ".join(map(str, expected))
    args.output.write_text(f'''(ns embench.depthconv (:export [run test-depthconv]))

;; Lossless correctness port of Embench-IoT depthconv.c.
;; Copyright 2024 The TensorFlow Authors. SPDX-License-Identifier: Apache-2.0.
;; This evaluates the complete 1x4x1x32 input, filter, bias, per-channel
;; requantization, and all 32 expected outputs for one benchmark iteration.

(def input-data "{b64(inputs)}")
(def filter-data "{b64(filters)}")
(def biases [{bias_literal}])
(def expected [{expected_literal}])

(defn- sextet [code :i64] :i64
  (if (and (>= code 65) (<= code 90)) (- code 65)
    (if (and (>= code 97) (<= code 122)) (+ (- code 97) 26)
      (if (and (>= code 48) (<= code 57)) (+ (- code 48) 52)
        (if (= code 43) 62 63)))))

(defn- byte-at [data :string index :i64] :i64
  (let [group (* (quot index 3) 4)
        lane (- index (* (quot index 3) 3))
        a (sextet (string-code-point-at data group))
        b (sextet (string-code-point-at data (+ group 1)))
        c (sextet (string-code-point-at data (+ group 2)))
        d (sextet (string-code-point-at data (+ group 3)))
        value (if (= lane 0)
                (+ (i64-shift-left a 2) (u64-shift-right b 4))
                (if (= lane 1)
                  (+ (i64-shift-left (bit-and b 15) 4) (u64-shift-right c 2))
                  (+ (i64-shift-left (bit-and c 3) 6) d)))]
    (if (> value 127) (- value 256) value)))

(defn- output-channel [channel :i64] :i64
  (let [acc (loop [y 0 total 0]
              (if (= y 4)
                total
                (let [index (+ (* y 32) channel)
                      input (byte-at input-data index)
                      filter (byte-at filter-data index)]
                  (recur (+ y 1) (+ total (* filter (+ input 128)))))))
        with-bias (+ acc (vector-at biases channel))
        rounded (+ (* with-bias 1152862902) 274877906944)
        scaled (i64-shift-right rounded 39)]
    (if (< scaled -128) -128 (if (> scaled 127) 127 scaled))))

(defn run [token :i64] :i64
  (if (= token 1)
    (loop [channel 0 matches 0]
      (if (= channel 32)
        matches
        (recur (+ channel 1)
               (+ matches (if (= (output-channel channel)
                                  (vector-at expected channel)) 1 0)))))
    0))

(defn test-depthconv [] :i64
  (if (= (run 1) 32) 1 0))
''')


if __name__ == "__main__":
    main()
