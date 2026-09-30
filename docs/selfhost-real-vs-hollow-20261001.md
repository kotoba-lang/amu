# Selfhost: real vs hollow audit of the 94 OK files (2026-10-01)

Source: `/private/tmp/wall-scan-20.tsv` (94 files that print OK from `amu check` on the Kotoba project route). OK means the file compiles on the Kotoba route, not that the Kotoba route implements what the file exports. This document measures the second thing.

## Method

- Every file was read as the Kotoba route sees it: `#?(:kotoba X :default Y)` forms resolved to `X`, `#?(:kotoba nil ...)` dropped, `.kotoba` twins in `wt-K-kotoba-lang/lang/compat` substituted where they exist (two: `kotoba.kir.definition-identity`, `kotoba.verifier.signing`).
- The resolved public `defn`s were compared with the host (`:default`/`:cljs`/`:clj`) public `defn`s: absent, `nil`-bodied, refusal-bodied (`throw`, "not available on the Kotoba route"), or shrunk bodies were each inspected by hand.
- Tooling: a reader-conditional-aware S-expression resolver (scratch, not committed). Token counts in the evidence column are S-expression node counts of non-`ns` top-level forms on each route and are a rough size signal only.

## Classes

- **REAL**: the Kotoba route has a genuine implementation of every public function the host exports (pure Kotoba logic, or a call of the capability that IS the function, e.g. `hash/sha256`). Refusals that are domain semantics shared with the host (invalid input rejected) do not count against a file.
- **PARTIAL**: at least one substantive public function is real, and others are absent (inside `#?(:kotoba nil ...)`) or are named refusals/always-refusing stubs.
- **HOLLOW**: nothing substantive is real: constants and format tags, a single capability forward standing in for a larger module, or only refusals. The host behaviour sits behind `#?(:kotoba nil ...)` or the Kotoba body throws/prints "not available on the Kotoba route".

## Totals

**Totals: 94 files = REAL 68 / PARTIAL 14 / HOLLOW 12.** (REAL 72%, PARTIAL 15%, HOLLOW 13%.)


Function-level view: of 632 public `defn`s the host route exports across the 94 files, 448 (71%) have a Kotoba-route body; the other 184 are absent or refused. Those 184 sit almost entirely in the 26 PARTIAL/HOLLOW files (`value.cljk` 61, `package_contract.cljk` 16, `contract.cljk` 15, `compile_cache.cljk` 11, `cli_support.cljk` 11, then the rest).

**What this means for "100%":** 94 files OK is the compile-check count; 68 of them (72%) are genuinely implemented. The 26 PARTIAL/HOLLOW files cluster in three areas: (1) the CLI and trust plane (`run_cli`, `test_cli`, `trust_cli`, `nbb/*_cli`, `cli_support` serve!, `project_source` linked projects), which are named refusals; (2) host state and filesystem machinery (`module_lock`, `compile_cache`, `verdict_cache`, `output_attestation`, `atomic_output` temp/edn, `host/sys`); (3) contract/validator libraries (`abi/contract`, `package_contract`, `runtime_identity`, `component/admission`, `kir/value` streams and float conversions, `definition_identity` locked-definition checks). Also `backend/cljs` (the ClojureScript emitter) is present only as two constants.

Caveats: the audit is static (no differential execution of each function); only `defn`s were counted (constants are listed in evidence when relevant); a file classed REAL can still fail at runtime where its Kotoba body is only as good as the capabilities it calls; `.cljk` files shadowed by `.kotoba` twins were judged by the twin.

| file | class | evidence | functions refused / absent |
|---|---|---|---|
| `wt-A-amu-measure : kotoba/compiler/backend/cljs.cljk` | HOLLOW | ns exports only default-fuel / default-frames constants; the whole ClojureScript lowering (#?(:kotoba nil ...) over ~3000 tokens: lower-expr, lower-function, prelude, emit) is absent on the Kotoba route | emit (absent) |
| `wt-A-amu-measure : kotoba/compiler/module_lock.cljk` | HOLLOW | only lock-schema (constant keyword) is on the route; every lock/read/verify function is inside #?(:kotoba nil ...) | lock-cid read-lock load-locked-graph write-block! lock-from-source-paths (absent) |
| `wt-A-amu-measure : kotoba/compiler/nbb/compile_cache.cljk` | HOLLOW | only sha256 (a one-line hash/sha256 ability forward) is on the route; the cache itself is inside #?(:kotoba nil ...) | create create-context key-for stage-key-for lookup! remove! put! lookup-stage! put-stage! resolve-stage! stats (absent) |
| `wt-A-amu-measure : kotoba/compiler/nbb/evm_cli.cljk` | HOLLOW | main prints "the nbb EVM compile is not available on the Kotoba route" and returns 64; the EVM CLI (compile!/run!) is nil on the route | main (named refusal) |
| `wt-A-amu-measure : kotoba/compiler/nbb/test_cli.cljk` | HOLLOW | main prints "amu test is not available on the Kotoba route" and returns 64 | main (named refusal) |
| `wt-A-amu-measure : kotoba/compiler/nbb/trust_cli.cljk` | HOLLOW | main prints "the trust-plane commands are not available on the Kotoba route" and returns 64 | main (named refusal) |
| `wt-A-amu-measure : kotoba/compiler/reference_runtime.cljk` | HOLLOW | constants runtime-format / max-providers only; capability-contracts and instantiate are inside #?(:kotoba nil ...) | capability-contracts instantiate (absent) |
| `wt-A-amu-measure : kotoba/compiler/run_cli.cljk` | HOLLOW | commands is a constant list; dispatch! throws "amu run and measure-runtime are not available on the Kotoba route" | dispatch! (named refusal) |
| `wt-A-amu-measure : kotoba/compiler/test_cli.cljk` | HOLLOW | run throws "amu test is not available on the Kotoba route"; human-lines absent | run (named refusal); human-lines (absent) |
| `wt-A-amu-measure : kotoba/compiler/trust_cli.cljk` | HOLLOW | commands is a constant list of 17 trust-plane command names; dispatch! throws "the trust-plane commands are not available on the Kotoba route" | dispatch! (named refusal); now-seconds (absent) |
| `wt-E-artifact : kotoba/artifact/runtime_identity.cljk` | HOLLOW | only the two loader-source-sha256 constants (returning literals) are on the route; validation, identity hash and admission are inside #?(:kotoba nil ...) | loader-source-for-profile validate! identity-sha256 validate-measurement! admit! (absent) |
| `wt-E-kotoba-core-contracts : kotoba/lang/package_contract.cljk` | HOLLOW | only non-empty-string? and cid? are on the route (2 of 18 public fns); every manifest/lockfile/definition/signature validator is absent | invalid contract-keyword? missing-key contract-vector-error definition-cids-error contract-surfaces-error signatures-error manifest-without-self-cid compute-manifest-cid manifest-integrity-error tree-cid-error component-cid-of component-cid-error package-manifest-error lockfile-error validate-case (absent) |
| `gitlib org-ietf-cbor : cbor/core.cljk` | PARTIAL | Kotoba route is a different, fragment-based API: typed encoders encode-null/bool/uint/nint/int/f64/text/bytes/tag/array/map/map-ordered + fragment-bytes are real pure code; generic value encode and the whole decoder are not on the route | OrderedMap ordered Tagged tagged tagged? tag-number tag-value encode encode-ordered decode (absent) |
| `wt-A-amu-measure : kotoba/compiler/atomic_output.cljk` | PARTIAL | write-bytes! and write-text! real (via nbb io capability path); temp-file! and write-edn! absent | temp-file! write-edn! (absent) |
| `wt-A-amu-measure : kotoba/compiler/nbb/cli_support.cljk` | PARTIAL | option/options/source!/read-edn-file!/command-line-args/execute! are real (cli/args ability, bounded-edn); timed is a pass-through (no timing); serve! refuses; policy/artifact file readers absent | serve! (named refusal: worker mode not available on the Kotoba route); read-artifact-file! read-artifact-text! read-policy-material parse-policy-material read-policy + 6 more (absent) |
| `wt-A-amu-measure : kotoba/compiler/nbb/host/sys.cljk` | PARTIAL | cwd is the sys/cwd ability forward; the six host facts (nbb/Node process reads) have no Kotoba body | windows? tmpdir runtime-version argv path-delimiter homedir (absent) |
| `wt-A-amu-measure : kotoba/compiler/nbb/output_admission.cljk` | PARTIAL | provenance shape/digest/closed-key validation is real pure code, but admit! never admits: a well-formed wasm or kexe primary output is rejected with wasm-validator-unavailable / native-verifier-unavailable | admit! (named refusal for every well-formed provenance) |
| `wt-A-amu-measure : kotoba/compiler/nbb/output_attestation.cljk` | PARTIAL | format tags and parse-epoch! (real validator) only; attestation signing/verification is inside #?(:kotoba nil ...) | signer-id sign verify! (absent) |
| `wt-A-amu-measure : kotoba/compiler/nbb/project_source.cljk` | PARTIAL | source-roots and resolve-single-source! are real for one plain source file; linked projects (--source-path), --module-lock and --package are named refusals; the module-graph / package resolver is absent | resolve-single-source! refuses --source-path, --module-lock, --package paths; analyze-opts resolve-packages! resolve-source! attribute-error inputs-record module-graph (absent) |
| `wt-A-amu-measure : kotoba/compiler/nbb/verdict_cache.cljk` | PARTIAL | key-for and record-digest (artifact/sha256 over documents) are real; the on-disk store, toolchain/limits digests and resolve! are inside #?(:kotoba nil ...) | toolchain-digest limits-digest key-material open-store resolve! (absent) |
| `wt-D-osaho : kotoba/kir/definition_identity.cljk` | PARTIAL | project route takes the .kotoba twin (lang/compat/kotoba/kir/definition_identity.kotoba, 399 lines): normalize, identity-payload, canonical-bytes/hex and definition-cid are real (CIDv1 dag-cbor); locked-definition verification, build admission and conformance cases are absent | verify-locked-definitions admit-build check-case effect-row-from-hir definition-error (absent) |
| `wt-D-osaho : kotoba/kir/value.cljk` | PARTIAL | limit constants, f32/f64 bit casts, bounded-string!/bounded-keyword! and utf8 intrinsic forwards are real; float<->int conversions, the stream/task resource table, bounded-bytes/map/symbol checks are absent (61 of 90 public fns) | f64-to-f32-rounded f32-to-f64-exact i64-to-f32/f64-rounded/checked f64/f32-to-i64-checked/truncating bounded-bytes! utf8-invalid-at utf8-string->bytes resource-table-reset! stream-*/task-* make-*-stream/task concat-bytes bounded-symbol! bounded-map! ... (absent) |
| `wt-E-abi : kotoba/abi/contract.cljk` | PARTIAL | world/target/WIT constants, profile?, capability-id/import-name and cid? are real; every authority-envelope validator (plan, policy-decision, lease, approval, execution-identity, component-authority event/envelope) and the conformance vectors are absent (15 of 23) | valid-plan? valid-policy-decision? valid-capability-lease? valid-approval? valid-execution-identity? valid-component-authority-event? valid-component-authority-envelope? component-authority-signing-payload conformance-result valid-ability? valid-stream-limits? ... (absent) |
| `wt-E-io : kotoba/lang/io/stream.cljk` | PARTIAL | copy (drain/copy over BufferReader/BufferWriter records) is the only function on the route; resource/reader/writer/input-stream/output-stream constructors are nil | resource reader writer input-stream output-stream (absent) |
| `wt-E-io-multiformats : multiformats/core.cljk` | PARTIAL | base58btc/base32/base64url codecs, varint, multihash, cidv1 family, hexify/unhex are real pure code; the pluggable sha256 provider, sha384, varint-decode, cid parsing and cid-of-file are absent | portable-sha256 install-sha256! sha256-provider sha384 varint-decode cid->parts cid->multihash cid-of-file (absent) |
| `wt-E-kotoba-component : kotoba/component/admission.cljk` | PARTIAL | cid and cid-of-text (CIDv1 raw over sha256) real; the component admission request/complete protocol is absent | request complete (absent); format-tag envelope-keys composer-supplied-keys request-keys constants absent |
| `kotoba-sema : kotoba/compiler/affine.cljk` | REAL | all 8 public fns have Kotoba bodies; Kotoba route 8729 tokens vs host 2223; affine/linearity checker; module-linear-returning reduced by helper extraction | - |
| `kotoba-sema : kotoba/compiler/schema.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 928 tokens vs host 659; schema checks with Kotoba-only additions | - |
| `wt-A-amu-measure : kotoba/compiler/authority.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 1523 tokens vs host 887 | - |
| `wt-A-amu-measure : kotoba/compiler/backend/evm.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 1117 tokens vs host 644 | - |
| `wt-A-amu-measure : kotoba/compiler/base64_text.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 32 tokens vs host 22 | - |
| `wt-A-amu-measure : kotoba/compiler/bounded_edn.cljk` | REAL | all 4 public fns have Kotoba bodies; Kotoba route 888 tokens vs host 732; EDN reader over kotoba.reader with real depth/token/node/string limits; host read-string is exported as read-edn-text (read-string is reserved on Kotoba) | - |
| `wt-A-amu-measure : kotoba/compiler/cache.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 1494 tokens vs host 670; store and admit! over :form/r with real signing/verify-value and standing checks; trap-form only on invalid input | - |
| `wt-A-amu-measure : kotoba/compiler/coverage_evidence.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 1337 tokens vs host 468; sign / verify / verify-bundle real (trap-form only on invalid input) | - |
| `wt-A-amu-measure : kotoba/compiler/decimal_text.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 326 tokens vs host 297 | - |
| `wt-A-amu-measure : kotoba/compiler/definition_identity.cljk` | REAL | all 7 public fns have Kotoba bodies; Kotoba route 7578 tokens vs host 2022; full per-definition identity driver (definitions/describe/format-lines) over :form/r; f32 literals are a domain refusal (:f32-literal-unsupported) that the host also reports, not a stub | - |
| `wt-A-amu-measure : kotoba/compiler/diagnostic.cljk` | REAL | all 5 public fns have Kotoba bodies; Kotoba route 849 tokens vs host 493 | - |
| `wt-A-amu-measure : kotoba/compiler/host_integer.cljk` | REAL | all 6 public fns have Kotoba bodies; Kotoba route 37 tokens vs host 58 | - |
| `wt-A-amu-measure : kotoba/compiler/ios_aot.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 587 tokens vs host 319; package real (104 tokens, Kotoba-only pack path) | - |
| `wt-A-amu-measure : kotoba/compiler/json_text.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 159 tokens vs host 71 | - |
| `wt-A-amu-measure : kotoba/compiler/kexe_fs_forms.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 721 tokens vs host 353; refuse-unanswered! is the real loader-target check (same refusal as host, by design) | - |
| `wt-A-amu-measure : kotoba/compiler/limits.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 2027 tokens vs host 1867; limits table is a real document literal; "not implemented" strings are table data about backends, not refusals | - |
| `wt-A-amu-measure : kotoba/compiler/nbb/fs_tree.cljk` | REAL | all 6 public fns have Kotoba bodies; Kotoba route 356 tokens vs host 222; exists?/directory?/kind/entries/make-directories!/remove-tree! over fs capabilities | - |
| `wt-A-amu-measure : kotoba/compiler/nbb/host/cli.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 11 tokens vs host 50; cli/args 38 ability forward (the Kotoba body IS the ability call) | - |
| `wt-A-amu-measure : kotoba/compiler/nbb/host/entropy.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 11 tokens vs host 46; entropy/draw 23 ability forward | - |
| `wt-A-amu-measure : kotoba/compiler/nbb/host/fs.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 22 tokens vs host 1041; fs/app-data 35 and fs/browse 34 ability forwards; app-data-bytes is reached as the fs/app-data-bytes capability directly by callers (bounded_edn) | - |
| `wt-A-amu-measure : kotoba/compiler/nbb/host/hash.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 11 tokens vs host 18; hash/sha256 3 ability forward | - |
| `wt-A-amu-measure : kotoba/compiler/nbb/host/io.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 33 tokens vs host 317; io/write, io/write-error, io/read ability forwards | - |
| `wt-A-amu-measure : kotoba/compiler/nbb/host/process.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 11 tokens vs host 278; process/spawn 20 ability forward; programs/env/max-output are host handler config, not Kotoba surface | - |
| `wt-A-amu-measure : kotoba/compiler/nbb/io.cljk` | REAL | all 6 public fns have Kotoba bodies; Kotoba route 1272 tokens vs host 963; bounded read, write-set!, entries via fs capabilities; real | - |
| `wt-A-amu-measure : kotoba/compiler/nbb/output_set.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 497 tokens vs host 246; descriptor / serialize / verify! real over :form/r | - |
| `wt-A-amu-measure : kotoba/compiler/posix_path.cljk` | REAL | all 4 public fns have Kotoba bodies; Kotoba route 819 tokens vs host 774 | - |
| `wt-A-amu-measure : kotoba/compiler/process_wire.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 200 tokens vs host 135 | - |
| `wt-A-amu-measure : kotoba/compiler/provenance.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 895 tokens vs host 677; attach / verify! / descriptor real over :form/r | - |
| `wt-A-amu-measure : kotoba/compiler/release.cljk` | REAL | all 4 public fns have Kotoba bodies; Kotoba route 1580 tokens vs host 796; file-identity, sbom-bytes, attest, verify! real (trap-form only on invalid input) | - |
| `wt-A-amu-measure : kotoba/compiler/source_path.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 356 tokens vs host 155 | - |
| `wt-A-amu-measure : kotoba/compiler/target_names.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 65 tokens vs host 63 | - |
| `wt-A-amu-measure : kotoba/compiler/text_bytes.cljk` | REAL | all 11 public fns have Kotoba bodies; Kotoba route 96 tokens vs host 131; 11 fns, typed utf8 helpers | - |
| `wt-A-security : kotoba/security/abac.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 917 tokens vs host 433 | - |
| `wt-A-security : kotoba/security/crypto_policy.cljk` | REAL | all 13 public fns have Kotoba bodies; Kotoba route 1562 tokens vs host 804 | - |
| `wt-A-security : kotoba/security/hardware.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 390 tokens vs host 230; evaluate-signing is a real violations computation; "unavailable" is a qualification criterion | - |
| `wt-A-security : kotoba/security/information_flow.cljk` | REAL | all 4 public fns have Kotoba bodies; Kotoba route 690 tokens vs host 225 | - |
| `wt-D-kotoba-codegen : kotoba/codegen/layout.cljk` | REAL | all 8 public fns have Kotoba bodies; Kotoba route 1597 tokens vs host 1196 | - |
| `wt-D-kotoba-gmir : kotoba/gmir.cljk` | REAL | all 9 public fns have Kotoba bodies; Kotoba route 7890 tokens vs host 2958 | - |
| `wt-D-kotoba-hir : kotoba/form.cljk` | REAL | all 70 public fns have Kotoba bodies; Kotoba route 3908 tokens vs host 3908 | - |
| `wt-D-kotoba-hir : kotoba/hir.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 3573 tokens vs host 1192 | - |
| `wt-D-kotoba-native : kotoba/native/aggregate_abi.cljk` | REAL | all 12 public fns have Kotoba bodies; Kotoba route 4890 tokens vs host 1495; aggregate ABI planner; "unsupported" results are host-identical domain outcomes | - |
| `wt-D-kotoba-native : kotoba/native/document.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 5684 tokens vs host 5497 | - |
| `wt-D-kotoba-native : kotoba/native/image_scratch.cljk` | REAL | public surface is defs/constants exposed as Kotoba fns; Kotoba route 44 tokens vs host 43 | - |
| `wt-D-kotoba-native : kotoba/native/interrupt_abi.cljk` | REAL | all 10 public fns have Kotoba bodies; Kotoba route 3039 tokens vs host 2312; interrupt ABI frame/stride/fatal tables and checks; fatal-tail refuses only on malformed input | - |
| `wt-D-kotoba-native : kotoba/native/keyword_equality.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 2619 tokens vs host 428 | - |
| `wt-D-kotoba-native : kotoba/native/peephole.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 44 tokens vs host 26 | - |
| `wt-D-kotoba-native : kotoba/native/string_index.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 3299 tokens vs host 658 | - |
| `wt-D-kotoba-native : kotoba/native/string_search.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 2834 tokens vs host 401 | - |
| `wt-D-kotoba-native : kotoba/native/vector_region.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 5101 tokens vs host 961 | - |
| `wt-D-kotoba-verifier : kotoba/verifier/signing.cljk` | REAL | project route takes the .kotoba twin (435 lines): pure RFC 8032 Ed25519 sign/verify, hand-built SPKI/PKCS#8 envelopes, entropy/draw keypair, trust-policy validation; all 11 public fns real. Host throws become traps (assert), a documented difference | - |
| `wt-D-kotoba-wasm : kotoba/wasm/canonical_abi.cljk` | REAL | all 3 public fns have Kotoba bodies; Kotoba route 6857 tokens vs host 1584 | - |
| `wt-D-kotoba-wasm : kotoba/wasm/typed.cljk` | REAL | all 10 public fns have Kotoba bodies; Kotoba route 4909 tokens vs host 2126; typed-wasm encoder; infer-type/hetero-item-type delegate to ty-* cores; "unsupported" strings are the same refusals as host | - |
| `wt-D-osaho : kotoba/kir/admission.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 1554 tokens vs host 373 | - |
| `wt-D-osaho : kotoba/kir/alpha_normalization.cljk` | REAL | all 6 public fns have Kotoba bodies; Kotoba route 3922 tokens vs host 943 | - |
| `wt-D-osaho : kotoba/kir/cljs_i64.cljk` | REAL | all 8 public fns have Kotoba bodies; Kotoba route 115 tokens vs host 187; i64 helpers over native i64; bigint-value? is constant false (no bigints on Kotoba) | - |
| `wt-D-osaho : kotoba/kir/compatibility.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 201 tokens vs host 107 | - |
| `wt-D-osaho : kotoba/kir/decimal.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 3836 tokens vs host 183 | - |
| `wt-D-osaho : kotoba/kir/descriptor.cljk` | REAL | all 9 public fns have Kotoba bodies; Kotoba route 6666 tokens vs host 1522; descriptor encoder; host-identical unsupported-descriptor throw | - |
| `wt-D-osaho : kotoba/kir/iq_codebook.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 879 tokens vs host 717; codebook digests embedded as document-edn-read literal; real data | - |
| `wt-D-osaho : kotoba/kir/target.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 134 tokens vs host 515; profiles read from embedded EDN via document-edn-read; real data | - |
| `wt-D-osaho : kotoba/kir/xml.cljk` | REAL | all 8 public fns have Kotoba bodies; Kotoba route 6059 tokens vs host 1250; XML parser/printer; parse-elements delegates to parse-state | - |
| `wt-E-abi : kotoba/abi/wit_data.cljk` | REAL | public surface is defs/constants exposed as Kotoba fns; Kotoba route 13 tokens vs host 20; embedded WIT text as zero-arg function; host-only files drift-test var is not exported | - |
| `wt-E-artifact : kotoba/artifact/core.cljk` | REAL | all 5 public fns have Kotoba bodies; Kotoba route 946 tokens vs host 251 | - |
| `wt-E-bytes : kotoba/bytes.cljk` | REAL | all 22 public fns have Kotoba bodies; Kotoba route 3815 tokens vs host 3114 | - |
| `wt-E-bytes : kotoba/bytes/sha256.cljk` | REAL | all 4 public fns have Kotoba bodies; Kotoba route 1144 tokens vs host 1058 | - |
| `wt-E-io : kotoba/io.cljk` | REAL | public surface is defs/constants exposed as Kotoba fns; Kotoba route 181 tokens vs host 265 | - |
| `wt-E-io-multiformats : multiformats/base32.cljk` | REAL | all 2 public fns have Kotoba bodies; Kotoba route 306 tokens vs host 314 | - |
| `wt-E-kotoba-component : kotoba/component/embedded_resources.cljk` | REAL | all 1 public fns have Kotoba bodies; Kotoba route 162 tokens vs host 106; resource-text returns the embedded WIT/EDN strings as functions | - |
