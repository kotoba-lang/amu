#!/usr/bin/env python3
"""Inventory direct ABI call sites in the pinned full compiler Mac candidate."""

import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path


RAW_SHA = '164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e'
IMAGE_SHA = '31db43821ee84ebbba81a9fbc3587ed5f3a9ce6ea90866bf54573c7376caa847'
CALLBACKS = {
    56: 'pair_new', 112: 'string_equal', 120: 'string_concat',
    128: 'typed_cap_call', 136: 'string_substring',
    144: 'string_code_point_at', 160: 'vector_conj',
    176: 'vector_at', 184: 'vector_assoc', 200: 'vector_alloc',
    216: 'string_index_of', 240: 'string_compare',
    352: 'string_from_utf8', 360: 'bytes_from_vector',
}
DIRECT_FIELDS = {
    288: 'pair_used_pointer', 296: 'pairs_base',
    304: 'pair_validated_base', 312: 'vector_used_pointer',
    320: 'vectors_base', 328: 'vector_items_base',
}
EXPECTED_TYPED = {
    (35, 1, 1): 1, (35, 8, 8): 2, (35, 9, 9): 1,
    (37, 1, 1): 2, (38, 1, 1): 2, (39, 1, 1): 1,
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def word(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def inspect(raw, image):
    if sha(raw) != RAW_SHA or sha(image) != IMAGE_SHA:
        raise ValueError('unexpected full compiler raw or Mac image digest')
    if image[8192:8192 + len(raw)] != raw:
        raise ValueError('Mac image does not contain the pinned full main')

    calls = Counter()
    examples = {}
    direct = Counter()
    typed = Counter()
    for offset in range(0, len(raw) - 4, 4):
        instruction = word(raw, offset)
        if ((instruction & 0xffc00000) == 0xf9400000
                and ((instruction >> 5) & 31) == 7):
            slot = ((instruction >> 10) & 0xfff) * 8
            if slot in DIRECT_FIELDS:
                direct[slot] += 1
        if (word(raw, offset + 4) == 0xd63f0200
                and (instruction & 0xffc003ff) == 0xf9400010):
            slot = ((instruction >> 10) & 0xfff) * 8
            calls[slot] += 1
            examples.setdefault(slot, offset)
            if slot == 128:
                kinds = []
                for delta, register in ((-16, 1), (-12, 2), (-8, 3)):
                    immediate = word(raw, offset + delta)
                    if (immediate & 0xffe0001f) != (0xd2800000 | register):
                        raise ValueError(f'typed call at {offset} has dynamic wire/kinds')
                    kinds.append((immediate >> 5) & 0xffff)
                typed[tuple(kinds)] += 1
    if set(calls) != set(CALLBACKS):
        raise ValueError(f'callback inventory drift: {sorted(calls)}')

    stores = {}
    for offset in range(1024, 6252, 4):
        instruction = word(image, offset)
        if ((instruction & 0xffc00000) == 0xf9000000
                and ((instruction >> 5) & 31) == 19
                and (instruction & 31) in (0, 8)):
            slot = ((instruction >> 10) & 0xfff) * 8
            if slot in CALLBACKS or slot in DIRECT_FIELDS:
                stores.setdefault(slot, []).append(offset)
    installed = sorted(set(calls) & set(stores))
    missing = sorted(set(calls) - set(stores))
    if missing != [160, 184, 216, 240]:
        raise ValueError(f'installed callback gap drift: {missing}')
    if not set(DIRECT_FIELDS).issubset(stores):
        raise ValueError('direct arena pointer setup incomplete')
    if not set(DIRECT_FIELDS) - {304} <= set(direct):
        raise ValueError('direct arena use inventory incomplete')
    if dict(typed) != EXPECTED_TYPED:
        raise ValueError(f'typed wire inventory drift: {dict(typed)}')

    return {
        'schema': 'amu.macos-full-abi-inventory.v1',
        'status': 'PASS_STATIC_ABI_GAP_INVENTORY',
        'scope': 'full-main direct call sites and static candidate slot stores only',
        'qualification': 'static inventory; no callback behavior or full Mac command execution is claimed',
        'rawSha256': sha(raw), 'imageSha256': sha(image),
        'requiredCallbacks': [
            {'offset': slot, 'name': CALLBACKS[slot], 'callSites': calls[slot],
             'firstRawOffset': examples[slot], 'installedStoreOffsets': stores.get(slot, [])}
            for slot in sorted(calls)],
        'installedCallbackOffsets': installed,
        'missingCallbackOffsets': missing,
        'directArenaFields': [
            {'offset': slot, 'name': DIRECT_FIELDS[slot],
             'rawLoadsFromX7': direct[slot], 'installedStoreOffsets': stores[slot]}
            for slot in sorted(DIRECT_FIELDS)],
        'typedWireShapes': [
            {'wire': wire, 'requestKind': request_kind,
             'resultKind': result_kind, 'callSites': count}
            for (wire, request_kind, result_kind), count in sorted(typed.items())],
        'typedProviderBoundary': 'wire 35 fs/app-data remains unimplemented; see live mac-bytes-utf8 receipt',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.raw.read_bytes(), args.image.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], 'missing=', result['missingCallbackOffsets'])
