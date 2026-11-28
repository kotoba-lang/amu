# Native LLM wire 11 on Darwin arm64

The Darwin compiler lowers `typed-cap-call :llm/generate` with the exact
request and result schemas in the LLM v1 kit. It checks names by
interned spelling, evaluates the request once, serializes it, and checks the
complete result frame before constructing the nominal result. Inline and
`:ref` declarations use the same path. Linux, browser Wasm, and the existing
AIUEOS user-v3 ELF continue to refuse this native call. A locked KSL2 Darwin
project uses the same codec and emits one requirement for the linked image.
[Capability kit](../resources/kotoba/lang/capability-kits/llm-v1.edn)

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

## Scoped Darwin execution

Use the `amu-program-llm-v1` profile for a single-source KSL1 program or a
locked KSL2 project with an exported `main [] :i64` and a checked wire-11
call. `amu run-llm PROGRAM --grant FILE` accepts a separate grant from the
caller. The launcher uses the SHA-256 of the bytes read from `PROGRAM`,
checks their embedded sources with the pinned compiler, and rebuilds the
signed image in private staging with the pinned packager.
The complete rebuilt image must match the expected SHA-256. Before the
broker dispatches, it also checks the kernel's signed-process status and
CDHash for the running child against the SHA-256 CodeDirectory of that
rebuilt image. The rebuilt image is the one passed to the child process.

KLG1 is a grant file with the following fields in order, one per line,
terminated by a newline. This example grants the synthetic provider a
five-second window and at most 42 output tokens for the exact artifact.
The caller obtains the digest from the signed `.macho` produced by compile.

```sh
out=$(mktemp -d)
bin/amu compile seed/tests/llm-v1-darwin-broker.kotoba \
  --runtime-profile amu-program-llm-v1 -o "$out/guest.macho"
artifact=$(shasum -a 256 "$out/guest.macho" | cut -d ' ' -f 1)
cat > "$out/guest.grant" <<EOF
KLG1
artifact=$artifact
wire=11
schema=768859620bef185169b794b3ca1dbabb0de8e96186c61e698e61418afd27a034
profile=amu-program-llm-v1
provider=synthetic-v1
endpoint=local:wire11-fixture
model=:synthetic/model
seconds=5
tokens=42
EOF
bin/amu run-llm "$out/guest.macho" --grant "$out/guest.grant"
```

The launcher opens a private, synchronous socket pair for this run. The
guest receives its peer at FD 3 and the broker owns the other peer. Each
direction carries a four-byte little-endian frame length and that many bytes.
The broker copies the request into its own bounded storage and validates the
complete snapshot, exact model spelling and requested output tokens. It
checks its monotonic deadline and consumes its dispatch slot before calling
the installed provider. The grant permits one call in a window of one to
five seconds and a token budget of zero to 4096. A zero budget admits no
request. There is no environment-based provider selection.

The broker validates the full response, including its output-token count,
before sending it. The guest reads the complete response, copies it into a
fresh arena byte value, closes its peer, and decodes the nominal result.
Malformed frames expose no nominal value. Missing or denied grants and
unavailable transport refuse with exit 69. A child deadline expires with
exit 124. The broker closes its descriptors and reaps the child. Ordinary
`amu run` keeps its five-second deadline and supplies no broker descriptor.

The only installed provider is the deterministic `synthetic-v1` fixture.
The `local:wire11-fixture` endpoint identifies that fixture in the grant.
The broker can exercise both result arms without an external service.
The ELF/CPL3 host binding remains KOTOBA-423.

## Reproduce the diagnostic

Run from the Amu checkout on Darwin arm64.

```sh
compiler=seed/bootstrap/aarch64-macos/amu-full-root.macho
python3 scripts/seed/check_llm_v1_checker_macos.py --wire11 \
  --image "$compiler" --expected-image-sha256 "$(shasum -a 256 "$compiler" | cut -d ' ' -f 1)" \
  --output "$(mktemp -d)/wire11"
basilisp run -p scripts/seed scripts/seed/check-macos-llm-broker.cljc -- \
  --output "$(mktemp -d)/broker"
```

The wire receipt reports checker controls, reproducible containers, native
codec execution and ungranted refusal. The broker receipt reports the signed
guest, launcher, compiler and packager digests, both nominal results and
provider calls for each refusal. The synthetic fixture exercises the native
broker independently of live model qualification.

For a locked KSL2 project, use the explicit namespace-to-file map and source
digests already required by the project entry.

```sh
bin/amu check ENTRY.kotoba --source-lock FILE.ksl
bin/amu compile ENTRY.kotoba --source-lock FILE.ksl \
  --runtime-profile amu-program-llm-v1 -o PROGRAM
bin/amu run-llm PROGRAM --grant FILE
```

Set `artifact=` in the KLG1 grant to the SHA-256 of `PROGRAM`. Compile
checks every source against the lock and packages the canonicalized lock
and verified source bytes. At run time the launcher reconstructs the
private compiler input from that embedded bundle, verifies every source
against the embedded lock, checks the linked `main` ABI and recomputes the
signed artifact before admitting the broker. An on-disk edit causes a
stale-lock refusal when compiling again. The signed artifact still uses
its verified embedded snapshot.

The broker diagnostic exercises both result arms on a locked two-module
project and records project artifact hashes separately from KSL1. Itonami's
pinned KSL2 consumer and an approved Murakumo artifact and endpoint still
need their own live qualification. [Amu #1901](https://github.com/kotoba-lang/amu/issues/1901)
