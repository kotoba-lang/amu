#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <wasmtime.h>

#define ENGINE_ID "kotoba.ipld-adl-wasmtime/v1"
#define RECEIPT_FORMAT "kotoba.ipld-adl-wasmtime-receipt/v1"
#define WASM_PAGE_BYTES 65536ULL

struct deadline {
  const wasm_engine_t *engine;
  uint64_t timeout_ms;
  atomic_bool done;
};

static void *deadline_main(void *raw) {
  struct deadline *deadline = raw;
  struct timespec tick = {.tv_sec = 0, .tv_nsec = 1000000};
  for (uint64_t elapsed = 0; elapsed < deadline->timeout_ms; elapsed++) {
    nanosleep(&tick, NULL);
    if (atomic_load_explicit(&deadline->done, memory_order_acquire)) return NULL;
  }
  if (!atomic_load_explicit(&deadline->done, memory_order_acquire))
    wasmtime_engine_increment_epoch(deadline->engine);
  return NULL;
}

static void deadline_stop(struct deadline *deadline, pthread_t thread) {
  atomic_store_explicit(&deadline->done, true, memory_order_release);
  pthread_join(thread, NULL);
}

static int fail(const char *code) {
  fprintf(stdout,
          "{\"format\":\"%s\",\"status\":\"error\",\"code\":\"%s\"}\n",
          RECEIPT_FORMAT, code);
  return 1;
}

static const char *trap_code(const wasm_trap_t *trap, const char *fallback) {
  wasmtime_trap_code_t code;
  if (!trap || !wasmtime_trap_code(trap, &code)) return fallback;
  if (code == WASMTIME_TRAP_CODE_OUT_OF_FUEL) return "fuel-exhausted";
  if (code == WASMTIME_TRAP_CODE_INTERRUPT) return "timeout";
  return fallback;
}

static int parse_u64(const char *text, uint64_t *out) {
  char *end = NULL;
  errno = 0;
  unsigned long long value = strtoull(text, &end, 10);
  if (errno || end == text || *end != '\0') return 0;
  *out = (uint64_t)value;
  return 1;
}

static uint8_t *read_file(const char *path, size_t limit, size_t *size) {
  FILE *file = fopen(path, "rb");
  if (!file) return NULL;
  if (fseek(file, 0, SEEK_END) != 0) { fclose(file); return NULL; }
  long length = ftell(file);
  if (length < 0 || (uint64_t)length > limit || fseek(file, 0, SEEK_SET) != 0) {
    fclose(file);
    return NULL;
  }
  uint8_t *bytes = malloc(length == 0 ? 1 : (size_t)length);
  if (!bytes || (length > 0 && fread(bytes, 1, (size_t)length, file) != (size_t)length)) {
    free(bytes);
    fclose(file);
    return NULL;
  }
  fclose(file);
  *size = (size_t)length;
  return bytes;
}

static int write_file(const char *path, const uint8_t *bytes, size_t size) {
  FILE *file = fopen(path, "wb");
  if (!file) return 0;
  int ok = size == 0 || fwrite(bytes, 1, size, file) == size;
  ok = ok && fclose(file) == 0;
  return ok;
}

static int export_of_kind(wasmtime_context_t *context,
                          const wasmtime_instance_t *instance,
                          const char *name, wasmtime_extern_kind_t kind,
                          wasmtime_extern_t *out) {
  return wasmtime_instance_export_get(context, instance, name, strlen(name), out) &&
         out->kind == kind;
}

int main(int argc, char **argv) {
  if (argc != 10) return fail("invalid-arguments");
  const char *module_path = argv[1];
  const char *input_path = argv[2];
  const char *output_path = argv[3];
  uint64_t operation, fuel_limit, max_output, max_pages, timeout_ms, max_module;
  if (!parse_u64(argv[4], &operation) || operation > 3 ||
      !parse_u64(argv[5], &fuel_limit) || fuel_limit == 0 ||
      !parse_u64(argv[6], &max_output) ||
      !parse_u64(argv[7], &max_pages) || max_pages == 0 ||
      !parse_u64(argv[8], &timeout_ms) || timeout_ms == 0 ||
      !parse_u64(argv[9], &max_module) || max_module == 0 ||
      max_pages > INT64_MAX / WASM_PAGE_BYTES)
    return fail("invalid-limits");

  size_t module_size = 0, input_size = 0;
  uint8_t *module_bytes = read_file(module_path, (size_t)max_module, &module_size);
  uint8_t *input_bytes = read_file(input_path, SIZE_MAX, &input_size);
  if (!module_bytes || !input_bytes || input_size > INT32_MAX) {
    free(module_bytes); free(input_bytes);
    return fail("input-read-failed");
  }

  wasm_config_t *config = wasm_config_new();
  wasmtime_config_consume_fuel_set(config, true);
  wasmtime_config_epoch_interruption_set(config, true);
  wasm_engine_t *engine = wasm_engine_new_with_config(config);
  wasmtime_store_t *store = wasmtime_store_new(engine, NULL, NULL);
  wasmtime_store_limiter(store, (int64_t)(max_pages * WASM_PAGE_BYTES), 0, 1, 0, 1);
  wasmtime_context_t *context = wasmtime_store_context(store);
  wasmtime_context_set_epoch_deadline(context, 1);
  wasmtime_error_t *error = wasmtime_context_set_fuel(context, fuel_limit);
  if (error) {
    wasmtime_error_delete(error);
    free(module_bytes); free(input_bytes); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail("fuel-configuration-failed");
  }

  wasmtime_module_t *module = NULL;
  error = wasmtime_module_new(engine, module_bytes, module_size, &module);
  free(module_bytes);
  if (error) {
    wasmtime_error_delete(error);
    free(input_bytes); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail("invalid-module");
  }
  wasm_importtype_vec_t imports;
  wasmtime_module_imports(module, &imports);
  if (imports.size != 0) {
    wasm_importtype_vec_delete(&imports);
    free(input_bytes); wasmtime_module_delete(module); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail("forbidden-import");
  }
  wasm_importtype_vec_delete(&imports);

  struct deadline deadline = {.engine = engine, .timeout_ms = timeout_ms};
  atomic_init(&deadline.done, false);
  pthread_t deadline_thread;
  if (pthread_create(&deadline_thread, NULL, deadline_main, &deadline) != 0) {
    free(input_bytes); wasmtime_module_delete(module); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail("deadline-thread-failed");
  }

  wasmtime_instance_t instance;
  wasm_trap_t *trap = NULL;
  error = wasmtime_instance_new(context, module, NULL, 0, &instance, &trap);
  if (error || trap) {
    deadline_stop(&deadline, deadline_thread);
    const char *code = trap_code(trap, "instantiation-failed");
    if (error) wasmtime_error_delete(error);
    if (trap) wasm_trap_delete(trap);
    free(input_bytes); wasmtime_module_delete(module); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail(code);
  }
  wasmtime_extern_t memory_export, alloc_export, transform_export;
  if (!export_of_kind(context, &instance, "memory", WASMTIME_EXTERN_MEMORY, &memory_export) ||
      !export_of_kind(context, &instance, "adl_alloc", WASMTIME_EXTERN_FUNC, &alloc_export) ||
      !export_of_kind(context, &instance, "adl_transform", WASMTIME_EXTERN_FUNC, &transform_export)) {
    deadline_stop(&deadline, deadline_thread);
    free(input_bytes); wasmtime_module_delete(module); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail("invalid-abi");
  }

  wasmtime_val_t alloc_arg = {.kind = WASMTIME_I32, .of.i32 = (int32_t)input_size};
  wasmtime_val_t alloc_result = {.kind = WASMTIME_I32};
  error = wasmtime_func_call(context, &alloc_export.of.func, &alloc_arg, 1, &alloc_result, 1, &trap);
  if (error || trap || alloc_result.kind != WASMTIME_I32 || alloc_result.of.i32 < 0) {
    deadline_stop(&deadline, deadline_thread);
    const char *code = trap_code(trap, "allocation-trap");
    if (error) wasmtime_error_delete(error);
    if (trap) wasm_trap_delete(trap);
    free(input_bytes); wasmtime_module_delete(module); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail(code);
  }
  uint64_t input_offset = (uint32_t)alloc_result.of.i32;
  size_t memory_size = wasmtime_memory_data_size(context, &memory_export.of.memory);
  if (input_offset > memory_size || input_size > memory_size - input_offset) {
    deadline_stop(&deadline, deadline_thread);
    free(input_bytes); wasmtime_module_delete(module); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail("input-memory-bounds");
  }
  memcpy(wasmtime_memory_data(context, &memory_export.of.memory) + input_offset,
         input_bytes, input_size);
  free(input_bytes);

  wasmtime_val_t args[3] = {
    {.kind = WASMTIME_I32, .of.i32 = (int32_t)operation},
    {.kind = WASMTIME_I32, .of.i32 = (int32_t)input_offset},
    {.kind = WASMTIME_I32, .of.i32 = (int32_t)input_size}
  };
  wasmtime_val_t result = {.kind = WASMTIME_I64};
  error = wasmtime_func_call(context, &transform_export.of.func, args, 3, &result, 1, &trap);
  deadline_stop(&deadline, deadline_thread);
  if (error || trap || result.kind != WASMTIME_I64) {
    const char *code = trap_code(trap, "guest-trap");
    if (error) wasmtime_error_delete(error);
    if (trap) wasm_trap_delete(trap);
    wasmtime_module_delete(module); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail(code);
  }

  uint64_t packed = (uint64_t)result.of.i64;
  uint64_t output_offset = packed >> 32;
  uint64_t output_size = packed & UINT32_MAX;
  memory_size = wasmtime_memory_data_size(context, &memory_export.of.memory);
  uint64_t pages = wasmtime_memory_size(context, &memory_export.of.memory);
  uint64_t remaining = 0;
  error = wasmtime_context_get_fuel(context, &remaining);
  if (error || output_size > max_output || output_offset > memory_size ||
      output_size > memory_size - output_offset || pages > max_pages) {
    if (error) wasmtime_error_delete(error);
    wasmtime_module_delete(module); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail(output_size > max_output ? "output-limit-exceeded" : "invalid-engine-report");
  }
  uint8_t *memory = wasmtime_memory_data(context, &memory_export.of.memory);
  if (!write_file(output_path, memory + output_offset, (size_t)output_size)) {
    wasmtime_module_delete(module); wasmtime_store_delete(store); wasm_engine_delete(engine);
    return fail("output-write-failed");
  }
  uint64_t used = fuel_limit - remaining;
  fprintf(stdout,
          "{\"format\":\"%s\",\"status\":\"ok\",\"engineId\":\"%s\","
          "\"engineVersion\":\"%s\","
          "\"fuelUsed\":%" PRIu64 ",\"memoryPages\":%" PRIu64
          ",\"outputBytes\":%" PRIu64 "}\n",
          RECEIPT_FORMAT, ENGINE_ID, WASMTIME_VERSION, used, pages, output_size);

  wasmtime_module_delete(module);
  wasmtime_store_delete(store);
  wasm_engine_delete(engine);
  return 0;
}
