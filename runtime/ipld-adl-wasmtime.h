#ifndef KOTOBA_IPLD_ADL_WASMTIME_H
#define KOTOBA_IPLD_ADL_WASMTIME_H

/*
 * ipld-adl-wasm-v1 guest ABI for the Wasmtime reference engine.
 *
 * A guest has no imports and exports exactly one linear memory plus:
 *
 *   i32 adl_alloc(i32 input_length)
 *   i64 adl_transform(i32 operation, i32 input_pointer, i32 input_length)
 *
 * adl_transform returns `(output_pointer << 32) | output_length`. Operations
 * are 0 validate-representation, 1 decode, 2 encode, 3 validate-logical.
 * Input and output are canonical DAG-CBOR. The engine, not the guest, measures
 * Wasmtime fuel and memory pages and enforces the wall-clock deadline.
 */

#define KOTOBA_IPLD_ADL_VALIDATE_REPRESENTATION 0
#define KOTOBA_IPLD_ADL_DECODE 1
#define KOTOBA_IPLD_ADL_ENCODE 2
#define KOTOBA_IPLD_ADL_VALIDATE_LOGICAL 3

#endif
