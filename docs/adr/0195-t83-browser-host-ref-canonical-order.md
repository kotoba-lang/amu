# ADR 0195: T8.3 browser-host resolve ref in compareValue (set-of-record)

- Status: Accepted
- Date: 2026-08-01
- Depends: ADR 0194 typed-set-nth; set-in-record; provider ADR 0231–0235 kit-shaped set-of-header-records

## Context

Provider packages ADR 0231–0235 use `[:set [:ref :hdr/pair]]` (set of
header-record refs). `assertValue` already called `resolveDescriptor` so
construction worked, but **`compareValue` did not** — so `typed-set-conj` /
`set-op-ref` uniqueness + sort rejected with
`typed value has no canonical order` (descriptor kind stayed `"ref"`).

Live Node browser-host `main()` on those packages failed even though KIR
execute and package sha registration were green.

## Decision

1. At the start of `compareValue`, call `resolveDescriptor(descriptor)` so
   schema refs (e.g. `[:ref :hdr/pair]`) expand to the sealed record
   descriptor before kind dispatch.
2. Does **not** flip any kit `:wasm-aot :implemented` (W4 recursive nested
   EDN still open). Honesty residual only: host path for bounded set-of-record.

## Evidence

- Live browser-host `main()` → `-9002` on
  http-request-set-record / headers-edn-set-fold / request-edn-set-record /
  result-edn-set-record packages; multi-export kit package → `-9238`.
- Focused regression: set-of-record conj + count via browser-host.

## Related

- T8.3; provider ADR 0231–0238; W4 residual remains
