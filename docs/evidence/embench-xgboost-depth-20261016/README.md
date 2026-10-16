# M104 xgboost tree-depth diagnostic

`profile.json` records deterministic path lengths for the 128 samples and 400
trees in the M104 translated Kotoba port. Reproduce it from the repository root
with:

```sh
python3 docs/evidence/embench-xgboost-depth-20261016/profile.py
```

The profile follows the port's `walk` operation over its decoded byte arrays.
The measured M104 native image contains a four-walk `tw` sequence: it executes
five branch-free levels for each walk, keeps reached leaves in place, and
commits groups only when all four paths end at leaves. The corresponding
disassembly is at payload offsets `0x1330`–`0x1768` in
`bench/embench/reproduce-20261015/round-sa-m104-20261015/images/xgboost.bin`
(SHA-256 `885ab7534513bd0eab7d7061cd315bca2f2285e60ff0e8916a427d9ba7a19d87`).
The pattern matches `tw-entry` in the measured compiler source at commit
`a9edc1f0d5021efabf6864e70c5b92d59257f348`. A separate single-walk,
five-level sequence appears around `0x1aec`, consistent with the `tbat`
fallback shape.

For the recorded model, all 12,800 groups of four have maximum path depth at
most five; every visited feature index is below 64; and tree sizes range from
1 to 31, below the kernel's 1,024 bound. The mean dynamic walk is 3.58 steps
and 52.6% of walks end before step five. At five table/input loads per step,
the fixed-depth path would issue 363,590 loads beyond the dynamic-step count if
every group takes this path. This makes early leaf arrival a concrete
optimization candidate.

The v3 profile also records each group's maximum depth. An idealized group-stop
variant (finish the four walks together as soon as all have reached leaves)
would execute 216,712 steps instead of 256,000, saving 39,288 steps or 15.35%
of the fixed-depth work. It would still do 33,430 more steps than four
individually depth-limited walks. The group-depth histogram is 1: 1,493; 2:
498; 3: 630; 4: 1,096; 5: 9,083 groups. A branch after each of the first four
levels would require 45,095 group-stop decisions over the model and could save
196,440 table/input loads versus fixed-five traversal. This is an idealized
work count: it omits the instructions and branch behavior needed to detect that
all four walks are done, so it is a hypothesis to measure, not a speedup
estimate.

The refreshed profile compares idealized stop groups that divide each
40-tree class. Width two saves 21.24% of fixed-five steps, versus 15.35% for
the current width four, while raising stop decisions from 45,095 to 85,392.
Width one saves 28.41% and requires 159,034 decisions. Widths 8 and above save
less than 9%. These are work counts, not interchangeable implementations:
the current native kernel interleaves four tree lanes by depth. Width two
needs pair-specific control flow or a different code layout, neither of which
is represented by a four-instruction check. Its code cost remains unestimated.

For the directly matching four-wide layout, three `AND`s and one `TBNZ` can
check whether all four walks reached leaves and branch to the existing commit
validation. At the observed 14 instructions per walk-level, this gives a
static estimate of 369,652 net instructions saved over fixed-five traversal
on the pinned model. This excludes branch prediction, pipeline effects,
register pressure, code size, and cycle costs. The estimate is a ranking aid,
not a speedup claim; its inputs are recorded in `profile.json`.

To inspect the measured image on Apple silicon, wrap its payload as an object
and disassemble it. The reported addresses are offsets from the payload symbol:

```sh
tmpdir="$(mktemp -d)"
cat > "$tmpdir/xgboost.s" <<EOF
.section __TEXT,__text,regular,pure_instructions
.globl _payload
_payload:
.incbin "$(pwd)/bench/embench/reproduce-20261015/round-sa-m104-20261015/images/xgboost.bin"
EOF
xcrun clang -target arm64-apple-macos13 -c "$tmpdir/xgboost.s" -o "$tmpdir/xgboost.o"
xcrun otool -tvV "$tmpdir/xgboost.o" | sed -n '/0000000000001330/,/0000000000001768/p'
```

This is static code and input-data analysis. The data-dependent depth, feature,
and tree-size predicates pass for every recorded group, and the image contains
the matching `tw` code. The retained record does not trace runtime guard
outcomes or quantify the timing cost of its loads versus C's branch behavior.
The 363,590-load estimate is conditional on every group entering `tw`, not a
measured dynamic count. Any change needs exact result/fuel evidence and a
quiet-host paired xgboost timing before it can be retained as a performance
optimization.
