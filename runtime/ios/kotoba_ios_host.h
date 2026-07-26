#ifndef KOTOBA_IOS_HOST_H
#define KOTOBA_IOS_HOST_H

#include <stdint.h>

#if defined(__cplusplus)
extern "C" {
#endif

#define KOTOBA_IOS_HOST_ABI_V1 1u
#define KOTOBA_IOS_MAX_CODE_BYTES (1024u * 1024u)
#define KOTOBA_IOS_MAX_ARITY 5u
#define KOTOBA_IOS_PAIR_CAPACITY 4096u
#define KOTOBA_IOS_STRING_POOL_BYTES 65536u

struct kotoba_ios_request_v1 {
  uint32_t abi_version;
  uint32_t arity;
  const char *target_profile;
  int64_t args[KOTOBA_IOS_MAX_ARITY];
  uint64_t allow[4];
};

struct kotoba_ios_result_v1 {
  uint32_t abi_version;
  uint32_t status;
  int64_t value;
  uint64_t fuel_remaining;
  uint64_t pairs_used;
};

enum kotoba_ios_status_v1 {
  KOTOBA_IOS_OK = 0,
  KOTOBA_IOS_INVALID_REQUEST = 1,
  KOTOBA_IOS_ALLOCATION_ERROR = 2,
  KOTOBA_IOS_UNSUPPORTED_HOST = 3,
  /* The guest executed a trap instruction -- fuel exhaustion, division by
     zero, a bounds violation, or a denied capability. On the kexe_loader
     path this surfaces as a supervised child's exit status; iOS has no
     fork/supervise, so the host contains it in-process and reports it here
     instead of letting SIGTRAP terminate the application. */
  KOTOBA_IOS_GUEST_TRAP = 4,
  /* The trap-containment handlers could not be installed. Executing without
     them would make any guest trap fatal to the whole app, so the host
     refuses to run rather than proceed unprotected. */
  KOTOBA_IOS_CONTAINMENT_UNAVAILABLE = 5
};

int kotoba_ios_execute_static_v1(const struct kotoba_ios_request_v1 *request,
                                 struct kotoba_ios_result_v1 *result);

#if defined(__cplusplus)
}
#endif

#endif
