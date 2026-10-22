#!/usr/bin/env python3
"""Generate the lossless Kotoba correctness port for Embench depthconv."""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
from pathlib import Path


def array(source: str, name: str) -> list[int]:
    match = re.search(rf"(?:static\s+)?(?:int8_t|int32_t)\s+{name}(?:\[[^]]*\])?\s*=\s*\{{(.*?)\}}\s*;", source, re.S)
    if match is None:
        raise ValueError(name)
    return [int(x) for x in re.findall(r"-?\d+", match.group(1))]


def b64(values: list[int]) -> str:
    return base64.b64encode(bytes(x & 255 for x in values)).decode("ascii")


def batch_source(source: str, representation: str, unroll: bool = False, inline_channel: bool = False) -> str:
    """A new fixed-workload implementation; the historical port stays intact.

    Repeat the convolution into one output buffer, then verify all channels
    once. This matches the C benchmark_body/verify boundary. Table mode
    changes the input representation, not the convolution or its answers.
    """
    if hashlib.sha256(source.encode()).hexdigest() != 'a6aadf6e0741922d4b32b8a7821cbea64f9eae00ca8cb8603b1586ec49c94bad':
        raise ValueError('batch port requires the reviewed 2.0rc2 depthconv profile')
    inputs = array(source, 'INPUT_DATA')
    filters = array(source, 'FILTER_DATA')
    biases = array(source, 'BIAS_DATA')
    expected = array(source, 'EXPECTED_OUTPUT')
    if array(source, 'OUTPUT_MULTIPLIER') != [1152862902] * 32 or array(source, 'OUTPUT_SHIFT') != [-8] * 32:
        raise ValueError('unreviewed requantization profile')
    literal = lambda xs: '[' + ' '.join(map(str, xs)) + ']'
    helpers = ''
    if representation == 'table':
        data = f'(def input-data {literal(inputs)})\n(def filter-data {literal(filters)})'
        access = 'vector-at'
    else:
        data = f'(def input-data "{b64(inputs)}")\n(def filter-data "{b64(filters)}")'
        access = 'byte-at'
        helpers = '''
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
        value (if (= lane 0) (+ (i64-shift-left a 2) (u64-shift-right b 4))
                (if (= lane 1) (+ (i64-shift-left (bit-and b 15) 4) (u64-shift-right c 2))
                  (+ (i64-shift-left (bit-and c 3) 6) d)))]
    (if (> value 127) (- value 256) value)))
'''
    accumulation = f'''(loop [y 0 total 0]
              (if (= y 4) total
                (let [index (+ (* y 32) channel)
                      input ({access} input-data index)
                      filter ({access} filter-data index)]
                  (recur (+ y 1) (+ total (* filter (+ input 128)))))))'''
    if unroll:
        terms = [f'(* ({access} filter-data (+ channel {row * 32})) (+ ({access} input-data (+ channel {row * 32})) 128))'
                 for row in range(4)]
        accumulation = f'(+ (+ {terms[0]} {terms[1]}) (+ {terms[2]} {terms[3]}))'
    channel_value = f'''(let [acc {accumulation}
        with-bias (+ acc (vector-at biases channel))
        rounded (+ (* with-bias 1152862902) 274877906944)
        scaled (i64-shift-right rounded 39)]
    (if (< scaled -128) -128 (if (> scaled 127) 127 scaled)))'''
    kernel_value = channel_value if inline_channel else '(output-channel channel)'
    return f'''(ns embench.depthconv-batch (:export [batch test-depthconv output-channel]))
;; Generated fixed-workload port of Embench 2.0rc2 depthconv.c.
;; Copyright 2024 The TensorFlow Authors. SPDX-License-Identifier: Apache-2.0.
;; Representation: {representation}. Inner loop unrolled: {unroll}. Channel inline: {inline_channel}.
;; No expected answer substitutes for the kernel.
{data}
(def biases {literal(biases)})
(def expected {literal(expected)})
{helpers}
(defn output-channel [channel :i64] :i64 {channel_value})
(defn- kernel-step [out :vector-i64 channel :i64] :vector-i64
  (if (= channel 32) out
    (let [updated (vector-assoc! out channel {kernel_value})]
      (kernel-step updated (+ channel 1)))))
(defn- kernel [out :vector-i64] :vector-i64 (kernel-step out 0))
(defn- verify-output [out :vector-i64] :i64
  (loop [channel 0 matches 0]
    (if (= channel 32) (if (= matches 32) 1 0)
      (recur (+ channel 1)
        (+ matches (if (= (vector-at out channel) (vector-at expected channel)) 1 0))))))
(defn batch [iterations :i64] :i64
  (let [out (vector-alloc 32)
        result (loop [i 0 current out]
                 (if (= i iterations) current
                   (recur (+ i 1) (kernel current))))]
    (verify-output result)))
(defn test-depthconv [] :i64 (batch 1))
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument('--batch-representation', choices=['base64', 'table'])
    parser.add_argument('--unroll', action='store_true', help='expand the four fixed input rows in the batch port')
    parser.add_argument('--inline-channel', action='store_true', help='generate the channel calculation inside the kernel')
    args = parser.parse_args()
    source = args.upstream.read_text()
    if args.batch_representation:
        args.output.write_text(batch_source(source, args.batch_representation, args.unroll, args.inline_channel))
        return
    if args.unroll or args.inline_channel:
        parser.error('--unroll and --inline-channel require --batch-representation')
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
