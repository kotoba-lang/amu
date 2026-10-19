#!/usr/bin/env python3
"""Independent integer check of the AArch64 signed reciprocal quotient."""

import random

MASK64 = (1 << 64) - 1
MIN_I64 = -(1 << 63)
MAX_I64 = (1 << 63) - 1


def trunc_dividend_by_positive_divisor(value: int, divisor: int) -> int:
    quotient = abs(value) // divisor
    return -quotient if value < 0 else quotient


def reciprocal_quotient(value: int, divisor: int) -> tuple[int, int, int]:
    shift = divisor.bit_length() - 1
    magic = ((1 << (64 + shift)) + divisor - 1) // divisor
    if magic > MASK64 or magic < (1 << 63):
        raise AssertionError((divisor, magic))
    signed_magic = magic - (1 << 64)
    signed_high_product = (value * signed_magic) // (1 << 64)
    quotient = (signed_high_product + value) >> shift
    if value < 0:
        quotient += 1
    return quotient, magic, shift


divisors = [d for d in range(3, 1000) if d & (d - 1)][:53] + [1_000_003]
if len(divisors) != 54 or len(set(divisors)) != 54:
    raise AssertionError("divisor set must contain 54 distinct values")

rng = random.Random(0xA64_20261016)
dividends_per_divisor = 0
for divisor in divisors:
    p = divisor.bit_length() - 1
    dividends = {
        MIN_I64,
        MIN_I64 + 1,
        -divisor - 1,
        -divisor,
        -1,
        0,
        1,
        divisor,
        divisor + 1,
        MAX_I64 - 1,
        MAX_I64,
    }
    for k in (-1000, -2, -1, 0, 1, 2, 1000):
        for delta in (-1, 0, 1):
            candidate = k * divisor + delta
            if MIN_I64 <= candidate <= MAX_I64:
                dividends.add(candidate)
    for _ in range(256):
        dividends.add(rng.randint(MIN_I64, MAX_I64))
    for value in dividends:
        got, magic, shift = reciprocal_quotient(value, divisor)
        expected = trunc_dividend_by_positive_divisor(value, divisor)
        if got != expected:
            raise AssertionError({
                "divisor": divisor,
                "value": value,
                "expected": expected,
                "got": got,
                "magic": hex(magic),
                "shift": shift,
            })
    dividends_per_divisor += len(dividends)

magic, shift = reciprocal_quotient(0, 1_000_003)[1:]
assert (magic, shift) == (0x8637A2A24E5ACE35, 19)
print(
    "PASS signed reciprocal quotient: "
    f"divisors={len(divisors)} dividends={dividends_per_divisor} "
    f"boundary+near-multiple+seeded-random; "
    f"1000003 magic=0x{magic:016x} shift={shift}"
)
