# Native LLM wire 11 on Darwin arm64

The single-source Darwin compiler lowers `typed-cap-call :llm/generate` with
the exact request and result schemas in the LLM v1 kit. It checks names by
interned spelling, evaluates the request once, serializes it, and checks the
complete result frame before constructing the nominal result. Inline and
`:ref` declarations use the same path. Linux, browser Wasm, and the existing
AIUEOS user-v3 ELF continue to refuse this native call. Darwin project
lowering also requires its own integration. [Capability kit](../resources/kotoba/lang/capability-kits/llm-v1.edn)

The compiler and standalone codec share the guest encoder and result
decoder. The Mac gate verifies that the source fragment embedded in the
compiler is byte-equivalent to the canonical Kotoba fragment. The standalone
codec includes the complementary host-side operations for the synthetic wire
vectors. [Codec source](../seed/runtime/llm-v1-wire.kotoba)

## Frames

The ABI preserves the KLM1 and KLR1 v1 header layouts from the AIUEOS
candidate. The Darwin frame places each payload span immediately after its
predecessor. Each span has an independent declared length. A frame ends
after the last declared byte. All integers are little-endian.

| Offset | KLM1 request | KLR1 result |
| --- | --- | --- |
| 0, 4, 8 | Magic KLM1, version 1, wire 11 | Magic KLR1, version 1, wire 11 |
| 12 | Model byte length | Tag 1 completion, tag 2 error |
| 16, 20 | System, prompt byte lengths | Text, finish-reason byte lengths |
| 24, 28 | Max output tokens, temperature-milli | Code, message byte lengths |
| 32, 36 | Total payload, result text capacity | Input tokens as a single 64-bit word |
| 40, 44 | Zero | Output tokens as a single 64-bit word |
| 48, 52 | Zero | Retryable 0 or 1, total payload |
| 56, 60 | Zero | Zero |
| 64 onward | Model, system, prompt | Text then finish reason, or code then message |

Keywords use the full UTF-8 spelling including the leading colon, up to
512 bytes. System, prompt, completion text and error message each have a
65,536-byte limit. The guest advertises a result text capacity of 65,536
bytes. The codec enforces a max-output-token range of 1–4096 and a
temperature-milli range of 0–2000. On success, output usage must fit the
request's token budget, both usage counts must be nonnegative, and all error
fields must be zero. On error, completion fields and both usage counts must
be zero. Truncation, trailing bytes, invalid UTF-8, and unknown tags refuse.
The v1 shapes admit synchronous text generation.

## Native boundary and artifact identity

The generated call uses the existing private Darwin
`typed_cap(ctx, wire, request_kind, result_kind, request_handle)` slot at
context offset 128 with wire 11 and both kinds set to 12. The request and
result handles each designate a bounded byte value in the current guest
arena. A host adapter must validate the handle, copy the bytes into a
host-owned request buffer, and copy its verified response into a fresh guest
byte value. The maximum whole-frame sizes are 131,648 bytes for KLM1 and
66,112 for KLR1. The adapter may borrow a span only during the synchronous
copy. The provider contract carries complete frames as bytes.

An extracted wire-11 payload ends with `AMU-LLM-REQUIREMENT-V1`, the wire
name and number, both qualified schema names, and the schema digest
`768859620bef185169b794b3ca1dbabb0de8e96186c61e698e61418afd27a034`.
The digest is SHA-256 of the canonical EDN vector of the two kit descriptors,
request first, with one space between forms. The signed Mach-O covers the
payload and its requirement. The gate binds the whole Mach-O SHA-256 to the
schema digest and records the compiler, packager and source hashes. Host
admission must derive the requirement from the checked source and verify the
complete artifact. A matching byte sequence in a guest literal conveys no
authority.

The shipped Darwin callback traps on kind 12. The guest decoder also traps
when the frame is invalid, before exposing a nominal result. Public
`amu run` retains its five-second deadline and normal descriptor closure.
The diagnostic codec harness runs separately under its own timeout.

The next Darwin integration is a scoped launcher and broker. The launcher
must match an independent runtime grant to the verified artifact hash,
schema digest, profile, provider and endpoint. The broker must compare the
full model spelling, validate complete request bounds, and reserve budget
before calling the provider. Denial, mismatch, absent provider and exhausted
budget must yield zero provider calls. Once a provider is installed, test
both result arms and verify that invalid results publish no guest value.
The ELF/CPL3 host binding remains KOTOBA-423.

## Reproduce the diagnostic

Run from the Amu checkout on Darwin arm64.

```sh
compiler=seed/bootstrap/aarch64-macos/amu-full-root.macho
python3 scripts/seed/check_llm_v1_checker_macos.py --wire11 \
  --image "$compiler" --expected-image-sha256 "$(shasum -a 256 "$compiler" | cut -d ' ' -f 1)" \
  --output "$(mktemp -d)/wire11"
```

The receipt reports checker controls, reproducible containers, native codec
execution, and the packaged guest's ungranted refusal separately. Provider
execution and a live Itonami turn require the scoped broker and an approved
Murakumo artifact and endpoint. [Amu #1901](https://github.com/kotoba-lang/amu/issues/1901)
