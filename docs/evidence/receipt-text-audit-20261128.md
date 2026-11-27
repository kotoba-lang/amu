# ZB31-24 text evidence audit

Inventory at `87ec570aff47a0a21b4876fcda4fa9d4e3b934fb` under `docs/evidence` and `docs/qualification`.

| Use | Candidate files |
| --- | ---: |
| GPU runs and instrumentation | 4,289 |
| GPU protocol and review records | 985 |
| GPU supporting artifacts such as captured output, summaries and build controls | 926 |
| Other GPU measurement and target evidence | 169 |
| Compiler and runtime assurance evidence | 75 |
| Android qualification evidence | 14 |
| **Text total** | **6,458** |

The first three rows are the 6,200 files under `docs/evidence/gpu`, grouped by filename families. All 6,458 tracked `.txt` files were inspected, including empty captures and pinned output. The structured inventory covered 2,063 `.json` and 12 `.receipt` files separately. The other 14,521 files have different suffixes and fall outside this publication check. They include raw sidecars with other extensions, sources, binaries and archives. Archived copies and Git history are outside this audit.

Recognized host paths occurred in 338 text files in total. Home/workspace paths occurred in 326 files (14,187 matches), temporary paths in 78 files (2,422 matches) and host paths in file URIs in 116 files. These groups overlap. No credential or contact information matched the rules. Public tool and device path metadata was retained, including a GPU tool installation reference and Android's shared-storage paths. The scan detects recognized credential formats, credential assignments, email addresses, labeled phone numbers and addresses, and known host path families.

The [custody manifest](receipt-path-redactions-20261128.json) records the original and publication digests and byte counts for 220 structured copies and 338 text copies. A direct check of full original digests found four reference files pointing to five text copies. These references, including the historical GPU record verifier, retain their original-byte meaning. Run the publication check from the repository root to verify the current copies. Pass `--verify-originals` with the original Git revision available locally to check both byte sets.
