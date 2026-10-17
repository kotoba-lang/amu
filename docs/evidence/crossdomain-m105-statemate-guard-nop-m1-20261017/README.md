# Statemate vector-shape guard: image-only upper-bound probe

Status: exactness passed for the registered input; generic correctness is not
established. This is not a compiler candidate.

## Probe

The source image SHA-256 is
`6cb09af5443a9e2ce159f2853b92db2e74b887e73a108349c4cde2b65d5e6636` and the
diagnostic image SHA-256 is
`aad9e10d97f0628386e4451e319f558ecb1a5a551df3c5117cbcf71abdc912e1`. Four
instructions were replaced with AArch64 NOPs:

| Offset | Original instruction |
|---:|---|
| `0x3db10` | `cmp x17, x16` |
| `0x3db14` | `b.hs trap` |
| `0x3db24` | `cmp x16, #0xa8` |
| `0x3db28` | `b.ls trap` |

Descriptor loads, fuel reservation, and state updates remain in the image. The
probe assumes the registered benchmark input is the valid 169-element vector
produced by `vector-alloc`; it does not show that the checks can be removed for
other inputs or call paths.

## Results

Both base and patched images passed the registered exactness check. The result
was 1, benchmark fuel `20159447042`, verify fuel 66, and arena use of one vector
with 169 items and 1368 heap bytes. Five ABBA blocks produced 20 exact timed
calls. Each block ratio is the mean of two patched-image times divided by the
mean of two base-image times.

| Block | Patched/base ratio | Start load1 |
|---:|---:|---:|
| 1 | 0.9856 | 25.77 |
| 2 | 0.9250 | 31.02 |
| 3 | 0.9716 | 33.50 |
| 4 | 0.9733 | 30.09 |
| 5 | 0.9710 | 28.78 |
| **Median** | **0.9716** | — |

The roughly 2.8% median reduction is an exploratory estimate on a loaded host,
with a large outlier. It does not establish a safe compiler transformation.
The next useful compiler experiment is to prove the vector-length invariant
through the repeated `vector-assoc!` path, hoist the shape guard while retaining
a fallback, and then check exactness before timing.

[`sanitized-report.json`](sanitized-report.json) retains all timing samples,
exactness fields, arena use, and load snapshots while omitting local timer paths
and binaries. The runner and image artifacts remain in the ignored local work
area, so this is not a standalone reproduction package.
