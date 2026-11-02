#!/usr/bin/env python3
# design-verify-s215to220.py -- JUN-59 session 221: the control-question
# pre-registration's DESIGN-VERIFY (the s220 carry-forward's first
# remaining component): fail-closed quote + arithmetic re-derivation
# vs the committed bytes the six draft files (state-s215.txt,
# refs-provenance-s216.txt, arms-statistic-s217.txt, letters-s218.txt,
# invalidation-s219.txt, threestate-s220.txt) cite.
#
# SCOPE (named, not hidden): (1) FILE PINS -- size + sha256 over every
# file the six draft files cite (byte-level fail-closed over the whole
# quotation surface); (2) LINE WANTS -- (file, line number, substring)
# triples checking that the cited source lines actually carry the
# cited content: the four-cut control-state record (every C1 letter,
# c2/c8/VERIFY/branch/D2 line), the frozen protocol's decision bases
# (the C1 machinery + frozen name, the arms/statistic/instrument pin,
# the invalidation criterion, the W1 mapping), the act machinery
# quotes (check shape, pre-choice principle, analysis-defect
# precedent), the committed-reference provenance chain (sessions 1/4
# primary records, the s27 census, the s7/s12/s32/s33/s34 chain), and
# the six draft files' mutual citations; (3) ARITHMETIC
# re-derivations of every labelled DERIVED quantity in the
# s218/s219/s220 decisions (the 16-sequence enumeration, block and
# identity distributions, the B=3 set, I=2 iff B>=2, the 16+1 act
# outcome space, the 4*(3+3) act process count, the c8 +/-5%
# percentages, the c2 floor-band membership); (4) DERIVED
# re-computations FROM COMMITTED BYTES (the four letters re-extracted
# from the publications, the draft D-claims parsed and compared to
# the re-derivation, the frozen-name core text cross-checked between
# the frozen protocol and the 19th cut's publication, the ROUNDS6400
# source pin re-hashed).
#
# FAIL-CLOSED: ANY missing line, mismatched byte, wrong arithmetic or
# incoherent letter assignment is a hard failure (exit 1).
#
# QUOTE-ONLY / ARITHMETIC-ONLY: this script verifies the pre-
# registration draft's quotations and arithmetic against committed
# bytes. It computes NO control-question quantity -- NO run, NO
# letter act, NO class, NO verdict, NO claim. Every control-question
# quantity stays UNMEASURED. RULE 4 unchanged: NOTHING MOVES; the
# committed bracket stays EXACTLY (254,923, 255,045].
import hashlib
import itertools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.dirname(HERE)

FILES = {
    "pub169": os.path.join(GPU, "anv-b3bisect16-20261101", "publication-s169.txt"),
    "pub185": os.path.join(GPU, "anv-b3bisect17-20261101", "publication-s185.txt"),
    "pub197": os.path.join(GPU, "anv-b3bisect18-20261101", "publication-s197.txt"),
    "pub209": os.path.join(GPU, "anv-b3bisect19-20261102", "publication-s209.txt"),
    "pr19": os.path.join(GPU, "anv-b3bisect19prereg-20261102", "protocol.txt"),
    "rec19": os.path.join(GPU, "anv-b3bisect19prereg-20261102", "record.txt"),
    "spec": os.path.join(GPU, "anv-b3confrontation-spec-20261031", "confrontation-spec.txt"),
    "a209id": os.path.join(GPU, "anv-b3bisect19-20261102", "analysis-s209-identity.txt"),
    "r6400": os.path.join(GPU, "anv-b3bisect17-20261101", "gpu-subgroup-reduce-anv-ndiv-rounds6400.c.txt"),
    "pub4": os.path.join(GPU, "anv-batchscale-20261027", "publication-s4.txt"),
    "as7": os.path.join(GPU, "anv-bonset-20261027", "analysis-s7.py"),
    "dc27": os.path.join(GPU, "anv-b3bisect7-20261027", "derivation-census-s27.txt"),
    "dc26": os.path.join(GPU, "anv-b3bisect6-20261027", "derivation-census-s26.txt"),
    "a147id": os.path.join(GPU, "anv-b3bisect14-20261031", "analysis-s147-identity.txt"),
    "a147": os.path.join(GPU, "anv-b3bisect14-20261031", "analysis-s147.py"),
    "pub1": os.path.join(GPU, "anv-subgroupsize-81632-20261027", "publication.txt"),
    "ndivc": os.path.join(GPU, "anv-b3anchorrec-20261027", "gpu-subgroup-reduce-anv-ndiv.c.txt"),
    "wdpr": os.path.join(GPU, "anv-workdown-20261027", "protocol.txt"),
    "as12": os.path.join(GPU, "anv-workdown-20261027", "analysis-s12.py"),
    "as32": os.path.join(GPU, "anv-b3x1rec-20261028", "analysis-s32.py"),
    "as33": os.path.join(GPU, "anv-b3repr-20261028", "analysis-s33.py"),
    "as34": os.path.join(GPU, "anv-b3minwander-20261028", "analysis-s34.py"),
    "ab64a": os.path.join(GPU, "anv-subgroupsize-batch64-20261027", "analysis.py"),
    "ab64p": os.path.join(GPU, "anv-subgroupsize-batch64-20261027", "publication.txt"),
    "s215": os.path.join(HERE, "state-s215.txt"),
    "s216": os.path.join(HERE, "refs-provenance-s216.txt"),
    "s217": os.path.join(HERE, "arms-statistic-s217.txt"),
    "s218": os.path.join(HERE, "letters-s218.txt"),
    "s219": os.path.join(HERE, "invalidation-s219.txt"),
    "s220": os.path.join(HERE, "threestate-s220.txt"),
}

SHORT = {k: os.path.basename(p) for k, p in FILES.items()}

# (id, file key, expected size in bytes, expected sha256 hex)
FILE_PINS = [
    ("F-PUB169", "pub169", 56352,
     "c9aab750fd20120b3abe8db6e9cac554b6c8ea0fbb1b37d9169d1539e4ff7687"),
    ("F-PUB185", "pub185", 59777,
     "c62c01e17a045933782cc3fb8c67e452ae0f35a513ad1f396a9dea08834d6d34"),
    ("F-PUB197", "pub197", 62811,
     "f3d7465ad60a7de2be20d4edfcbb4743f73849d7b0a93e7ff6f2eccbd1ff5e53"),
    ("F-PUB209", "pub209", 66774,
     "d3a338f39a9cdb75938da3a412fee7ec299813d38bc46f1f7b9cb773bc2c2ebe"),
    ("F-PR19", "pr19", 26405,
     "9a6f7b75e932c51d8a45d5586bdfda15a73d350892153f31aec29c70b8ace6f6"),
    ("F-REC19", "rec19", 17270,
     "f67a5ba4c0547bb956804f985c6659eeaadc8df5badb60d32e47dde4d2a5e6e5"),
    ("F-SPEC", "spec", 9660,
     "c0eff7fb0a5997658c94c7be36f776229d29aabe99f4f96be6ebb48c821d5ec7"),
    ("F-A209ID", "a209id", 2916,
     "80adc36467c8b06ac5643286590ace490ea533e73ef82ba74a490ecd2f24e5b6"),
    ("F-R6400", "r6400", 29535,
     "c2704aaad6bfeeae1f4f9cfa916d0160efb03926892237554c7dffc8386e84e0"),
    ("F-PUB4", "pub4", 16602,
     "435c45aa6f33e6ca6792bfabea5bf97c0fd50a1e095aefd155819005c29796de"),
    ("F-AS7", "as7", 13742,
     "f8fb62c8315dfe96b9c66c3b1ae6a46b21aabd78186eb20f3ea7994e2ab1c715"),
    ("F-DC27", "dc27", 4891,
     "e199d4c496199f380e1e5c20ca65e87e6fde2ab22d53b86f46363c4408bdcec1"),
    ("F-DC26", "dc26", 3578,
     "03423193ee855ccd4d241a412b08ff1d74f2fcdbd74d0d755799cf583d882bf2"),
    ("F-A147ID", "a147id", 1377,
     "320c33ea50a4fa7171903046f90b9d92afdec9e273cbc61ab75ae0e472db25e0"),
    ("F-A147", "a147", 44769,
     "e5d0b62eddf53c6c5ef4686799ccec329f3a29ea4ed0971a02ab11ec588605cf"),
    ("F-PUB1", "pub1", 23824,
     "89473fe6f10606f594bca10ebfbd7b44b43a6c18c37218d1e19387b9a1d6d320"),
    ("F-NDIVC", "ndivc", 29533,
     "a5e539f0ad1c5d732cda1eaa1cd2abb1aa4d1a66795c09c4ecb35ed2c3520556"),
    ("F-WDPR", "wdpr", 10005,
     "322976c5b19198766e800682a67d919a725fefe429e85d2108220d381f38dc5d"),
    ("F-AS12", "as12", 17794,
     "0dc597d2b0b814a1f5ef23538c602cc106a59f933dc6b092e206039f95cc9886"),
    ("F-AS32", "as32", 23084,
     "473215f1bb1527eee215b09f0cdfa3768c24df0e108e2be17db9eea9aa6536db"),
    ("F-AS33", "as33", 23248,
     "f956bbb92a6029cde2aca26424c4dacc4b9f8d908226b9f8146416a69be5564f"),
    ("F-AS34", "as34", 24525,
     "5e318d47c062cb282684210c88ea4fbef57612dcbd0116de05c1f96c62d8a10a"),
    ("F-AB64A", "ab64a", 14348,
     "ef42220ba2db1e0deaca7ebf7f09d17148853f408f6f5f01b8f6a99b6fcab4d1"),
    ("F-AB64P", "ab64p", 11158,
     "b2d6634f5074666e119137bf92590dcf75ccd17e52cd16b02282207be3769508"),
    ("F-S215", "s215", 10214,
     "545b1ab8c7eafbdfc9e3db10fa43e4acc2fbe1d9bc0236d887f6b0474d42425f"),
    ("F-S216", "s216", 11969,
     "dec785c7cb47a6c0a7593d8bc30a36e36ec5e30a2e5c1943d14857d5f8a13a7a"),
    ("F-S217", "s217", 13524,
     "90ef67574780a8b146441c906536ec958857a65c0d65aa8f0ea0c3edbf1e5736"),
    ("F-S218", "s218", 15736,
     "62d7b1f6012e95f11f26002ba8c7c143fbe9214507f255d1cbf07132009908da"),
    ("F-S219", "s219", 12509,
     "2958817b52968f6efdfc6ff4f308efc62621117dee47ce51f299f17a480c868e"),
    ("F-S220", "s220", 17492,
     "67de0879234e704ef3aad7c1b00690db2aa7f25ca2c7219b53a3e8f1c2c3d60b"),
]

# (id, file key, 1-based line number, exact substring expected on that line)
LINE_WANTS = [
    # -- GROUP 1: the four-cut control-state record (the row question's
    #    object; state-s215's record, re-cited by s218/s220) --
    ("Q-169-607", "pub169", 607, "c2 (sum,128,S=16) pooled median m 30, deep-pooling"),
    ("Q-169-608", "pub169", 608, "class FLOOR (committed floor band 31..32 at B=2): False"),
    ("Q-169-609", "pub169", 609, "c8 (sum,128,S=16) pooled median m 32820 within +/-5% of committed 32915 (session 4 pooled median): True (-0.29%)"),
    ("Q-169-610", "pub169", 610, "control arms free of VERIFY mismatches (frozen INVALIDATION criterion): True"),
    ("Q-169-611", "pub169", 611, "VERDICT: branch (b) replication discrepancy (W1 (d) INVALID"),
    ("Q-169-612", "pub169", 612, "fires); cause UNMEASURED."),
    ("Q-169-637", "pub169", 637, "C1 (control replication): (b)"),
    ("Q-169-742", "pub169", 742, "5. VERDICT SUMMARY: C1 (b); C2 (c) at fm (254,801); W1 (d)."),
    ("Q-185-624", "pub185", 624, "c2 (sum,128,S=16) pooled median m 31, deep-pooling"),
    ("Q-185-625", "pub185", 625, "class FLOOR (committed floor band 31..32 at B=2): True"),
    ("Q-185-626", "pub185", 626, "c8 (sum,128,S=16) pooled median m 32775 within +/-5% of committed 32915 (session 4 pooled median): True (-0.43%)"),
    ("Q-185-627", "pub185", 627, "control arms free of VERIFY mismatches (frozen INVALIDATION criterion): True"),
    ("Q-185-628", "pub185", 628, "VERDICT: branch (a) both controls satisfy their criteria --"),
    ("Q-185-629", "pub185", 629, "W1 is evaluated against the row question."),
    ("Q-185-630", "pub185", 630, "D2 SUPERSESSION (arm (a), the frozen rule): this cut's C1"),
    ("Q-185-631", "pub185", 631, "(a) reading SUPERSEDES the 16th cut's C1 (b) reading AS THE"),
    ("Q-185-632", "pub185", 632, "CURRENT CONTROL STATE (the 16th's (b) remains committed"),
    ("Q-185-633", "pub185", 633, "history; the discrepancy cause stays UNMEASURED, L2 binds)."),
    ("Q-185-662", "pub185", 662, "C1 (control replication): (a)"),
    ("Q-185-766", "pub185", 766, "5. VERDICT SUMMARY: C1 (a); C2 (c) at q1 (254,679); W1 (c)."),
    ("Q-197-630", "pub197", 630, "c2 (sum,128,S=16) pooled median m 31, deep-pooling"),
    ("Q-197-631", "pub197", 631, "class FLOOR (committed floor band 31..32 at B=2): True"),
    ("Q-197-632", "pub197", 632, "c8 (sum,128,S=16) pooled median m 32778 within +/-5% of committed 32915 (session 4 pooled median): True (-0.42%)"),
    ("Q-197-633", "pub197", 633, "control arms free of VERIFY mismatches (frozen INVALIDATION criterion): True"),
    ("Q-197-634", "pub197", 634, "VERDICT: branch (a) both controls satisfy their criteria --"),
    ("Q-197-635", "pub197", 635, "W1 is evaluated against the row question."),
    ("Q-197-636", "pub197", 636, "D2 CONTROL-STATE CONFRONTATION (arm (a), the frozen rule):"),
    ("Q-197-637", "pub197", 637, "the current control state (the 17th cut's C1 (a)) REPLICATES"),
    ("Q-197-638", "pub197", 638, "at back-to-back cuts -- no supersession needed (the 17th"),
    ("Q-197-639", "pub197", 639, "cut's C1 (a) stands confirmed; named)."),
    ("Q-197-662", "pub197", 662, "C1 (control replication): (a)"),
    ("Q-197-790", "pub197", 790, "5. VERDICT SUMMARY: C1 (a); C2 (a) at q3 (254,923); W1 (b)."),
    ("Q-209-657", "pub209", 657, "c2 (sum,128,S=16) pooled median m 30, deep-pooling"),
    ("Q-209-658", "pub209", 658, "class FLOOR (committed floor band 31..32 at B=2): False"),
    ("Q-209-659", "pub209", 659, "c8 (sum,128,S=16) pooled median m 32559 within +/-5% of committed 32915 (session 4 pooled median): True (-1.08%)"),
    ("Q-209-660", "pub209", 660, "control arms free of VERIFY mismatches (frozen INVALIDATION criterion): True"),
    ("Q-209-661", "pub209", 661, "VERDICT: branch (b) replication discrepancy (W1 (d) INVALID"),
    ("Q-209-662", "pub209", 662, "fires); cause UNMEASURED."),
    ("Q-209-663", "pub209", 663, "D2 CONTROL-STATE CONFRONTATION (arm (a), the frozen rule):"),
    ("Q-209-664", "pub209", 664, "NOTHING is superseded in the prior cuts' favour and the"),
    ("Q-209-665", "pub209", 665, "control question RE-OPENS as a named open control question"),
    ("Q-209-666", "pub209", 666, "carried forward: a three-state control record on the"),
    ("Q-209-667", "pub209", 667, "ROUNDS6400 instrument (the 16th cut's (b), the 17th cut's"),
    ("Q-209-668", "pub209", 668, "(a), the 18th cut's (a), this cut's (b)); W1 (d) fires, CUT"),
    ("Q-209-669", "pub209", 669, "VERDICT INVALID; the discrepancy cause stays UNMEASURED (L2"),
    ("Q-209-670", "pub209", 670, "binds). NAMED LIMITATION (the D2 shape): this cut cannot"),
    ("Q-209-671", "pub209", 671, "resolve the historical discrepancy cause by design."),
    ("Q-209-701", "pub209", 701, "C1 (control replication): (b)"),
    ("Q-209-828", "pub209", 828, "5. VERDICT SUMMARY: C1 (b); C2 (c) at q2 (254,984); W1 (d)."),
    # -- GROUP 2: the frozen protocol's decision bases (pr19) --
    ("Q-PR19-103", "pr19", 103, "at both cuts). This cut's C1 letter confronts it: if THIS"),
    ("Q-PR19-104", "pr19", 104, "cut's own c2 control lands FLOOR inside the committed floor"),
    ("Q-PR19-105", "pr19", 105, "band 31..32 (C1 (a)) and c8 within +/-5% of 32,915 with the"),
    ("Q-PR19-106", "pr19", 106, "control arms VERIFY-mismatch-free, the current control state"),
    ("Q-PR19-107", "pr19", 107, "REPLICATES at three consecutive cuts (no supersession"),
    ("Q-PR19-108", "pr19", 108, "needed -- the C1 (a) state stands confirmed; named). If"),
    ("Q-PR19-109", "pr19", 109, "this cut's c2 lands out of band (C1 (b)), NOTHING is"),
    ("Q-PR19-110", "pr19", 110, "superseded in the prior cuts' favour and the control"),
    ("Q-PR19-111", "pr19", 111, "question RE-OPENS as a named open control question carried"),
    ("Q-PR19-112", "pr19", 112, "forward: a three-state control record on the ROUNDS6400"),
    ("Q-PR19-113", "pr19", 113, "instrument (the 16th cut's (b), the 17th cut's (a), the"),
    ("Q-PR19-114", "pr19", 114, "18th cut's (a), this cut's (b)); W1 (d) fires, CUT VERDICT"),
    ("Q-PR19-115", "pr19", 115, "INVALID; the discrepancy cause stays UNMEASURED (L2 binds)."),
    ("Q-PR19-116", "pr19", 116, "NAMED LIMITATION (the D2 shape): this cut cannot resolve"),
    ("Q-PR19-117", "pr19", 117, "the historical discrepancy cause by design."),
    ("Q-PR19-181", "pr19", 181, "(i) INSTRUMENT VARIANT: '#define ROUNDS 25' -> '#define"),
    ("Q-PR19-182", "pr19", 182, "ROUNDS R', R = 6,400 (one line of the committed"),
    ("Q-PR19-183", "pr19", 183, "a5e539f0... copy: line 81, beside '#define WARMUP 3'"),
    ("Q-PR19-184", "pr19", 184, "line 80). The variant source gpu-subgroup-reduce-anv-"),
    ("Q-PR19-185", "pr19", 185, "ndiv-rounds6400.c.txt is frozen at SHA-256 source pin"),
    ("Q-PR19-186", "pr19", 186, "c2704aaad6bfeeae1f4f9cfa916d0160efb03926892237554c7df"),
    ("Q-PR19-187", "pr19", 187, "fc8386e84e0 (ADOPTED UNCHANGED from the s166 freeze;"),
    ("Q-PR19-188", "pr19", 188, "re-hashed this tick at the freeze, MATCH; diff verified"),
    ("Q-PR19-191", "pr19", 191, "(ii) PER UNIT PER CELL: m_c = pooled sample median"),
    ("Q-PR19-192", "pr19", 192, "gpu_ticks over the unit's samples for cell c; MAD_c ="),
    ("Q-PR19-193", "pr19", 193, "sample median |x - m_c|; CI half-width h_c = 3.6420 *"),
    ("Q-PR19-194", "pr19", 194, "MAD_c / sqrt(N) (95% normal-approximation CI for the"),
    ("Q-PR19-195", "pr19", 195, "population median: 1.96 * 1.2533 * 1.4826 = 3.6420,"),
    ("Q-PR19-196", "pr19", 196, "frozen formula). Units: a block of 3 runs x R rounds"),
    ("Q-PR19-197", "pr19", 197, "per cell (N = 3R = 19,200) or the pooled-48 arm of 48"),
    ("Q-PR19-198", "pr19", 198, "runs x R rounds (N = 48R = 307,200)."),
    ("Q-PR19-199", "pr19", 199, "(iii) UNIT CLASSES at the FROZEN 1,000-tick threshold (the"),
    ("Q-PR19-200", "pr19", 200, "threshold itself UNCHANGED -- only the statistic"),
    ("Q-PR19-201", "pr19", 201, "changes): CAPTURED iff all 18 pipeline-ok cells m_c -"),
    ("Q-PR19-202", "pr19", 202, "h_c >= 1,000; FLOOR iff all 18 m_c + h_c <= 100;"),
    ("Q-PR19-203", "pr19", 203, "INTERMEDIATE/MIXED iff (some m_c + h_c < 1,000) AND"),
    ("Q-PR19-204", "pr19", 204, "(some m_c - h_c > 100); IN-BAND-UNDECIDED otherwise."),
    ("Q-PR19-205", "pr19", 205, "THE CONSTANT R = 6,400 is ADOPTED UNCHANGED"),
    ("Q-PR19-206", "pr19", 206, "at this cut (the s166 D2/D3 shape, the 17th cut's D4 shape,"),
    ("Q-PR19-207", "pr19", 207, "the 18th cut's D4 shape): it was fixed by the PRE-REGISTERED"),
    ("Q-PR19-208", "pr19", 208, "DERIVATION RULE run in the pre-reg census before the"),
    ("Q-PR19-210", "pr19", 210, "twice byte-identical): R = the smallest ladder value"),
    ("Q-PR19-212", "pr19", 212, "pipeline-ok cells of 3.6420 * MAD_c / sqrt(3R) <= 2.0 ticks,"),
    ("Q-PR19-215", "pr19", 215, "as cross-check). Result: R=3,200 h_max 2.6949 > 2.0 FAILS;"),
    ("Q-PR19-216", "pr19", 216, "R=6,400 h_max 1.9056 <= 2.0 PASSES (binding cell idx 22,"),
    ("Q-PR19-217", "pr19", 217, "MAD 72.5; s147-mid cross-check R* = 6,400, binding idx 22,"),
    ("Q-PR19-218", "pr19", 218, "MAD 69.0). OPTION (ii) (the tolerance rule: every in-band"),
    ("Q-PR19-261", "pr19", 261, "bounds it. The statistic is chosen NOW, before any run of"),
    ("Q-PR19-262", "pr19", 262, 'this cut (spec L123: "A statistic chosen after the runs are'),
    ("Q-PR19-263", "pr19", 263, "read is never a confrontation.\"); the spec's arm-(c) (iii)"),
    ("Q-PR19-277", "pr19", 277, "(d) INVALID -- the frozen INVALIDATION criterion (the"),
    ("Q-PR19-278", "pr19", 278, "standing cut protocol): > 0 VERIFY mismatches in any"),
    ("Q-PR19-279", "pr19", 279, "run makes that run DEFECTIVE and the arm INVALID"),
    ("Q-PR19-280", "pr19", 280, "(bit-exact correctness re-check inside every run)."),
    ("Q-PR19-359", "pr19", 359, "B=2, WM=1, NDIV=1"),
    ("Q-PR19-364", "pr19", 364, "B=8, WM=1, NDIV=1"),
    ("Q-PR19-365", "pr19", 365, "ONE NEW KNOB TRIPLE (q2 (307, 1204): new-to-history -- n=254,984"),
    ("Q-PR19-366", "pr19", 366, "has never been measured at any binary; the s131 ZERO-NEW-KNOB-"),
    ("Q-PR19-367", "pr19", 367, "TRIPLES precedent does NOT hold, NAMED; L8 APPLIES: WM != 1 and"),
    ("Q-PR19-368", "pr19", 368, "NDIV != 1 combination-risk class; 6 in-box same-ratio doubles"),
    ("Q-PR19-371", "pr19", 371, "order: c2-r01..03, q2-r01..48, c8-r01..03 (controls bookend;"),
    ("Q-PR19-372", "pr19", 372, "one B=3 arm, so the s139 interleaved pair order degenerates to"),
    ("Q-PR19-380", "pr19", 380, "LETTERS: C1 (control replication, UNCHANGED thresholds from the"),
    ("Q-PR19-381", "pr19", 381, "standing cut protocol: c2 FLOOR in the committed floor band"),
    ("Q-PR19-382", "pr19", 382, "31..32 at B=2; c8 within +/-5% of the committed 32,915; C1 (b)"),
    ("Q-PR19-383", "pr19", 383, "-> W1 (d) INVALID; + the D2 control-state confrontation/"),
    # -- GROUP 3: the act machinery quotes (pub209 check shape, rec19
    #    W1 mapping, spec pre-choice principle, a209id precedent) --
    ("Q-209-162", "pub209", 162, "runs parsed: 54 (c2 x3, q2 x48, c8 x3 -- the frozen ARM TABLE's"),
    ("Q-209-163", "pub209", 163, "3 rows govern the count; run-count self-check 3+48+3 = 54 -> True); cell map"),
    ("Q-209-164", "pub209", 164, "identical across runs: True"),
    ("Q-209-165", "pub209", 165, "all per-log integrity checks pass (cell/verify counts, tail,"),
    ("Q-209-177", "pub209", 177, "tail '# done cells=24' in 54/54 runs: True"),
    ("Q-209-178", "pub209", 178, "SAMPLE lines: 115,200 per run (18 ok cells x 6,400 rounds) in 54/54 runs: True"),
    ("Q-209-179", "pub209", 179, "VERIFY mismatch total over all runs: 0 (per-arm: c2=0, q2=0, c8=0)"),
    ("Q-209-181", "pub209", 181, "324 cell-runs (6 per run x 54 runs = 324 expected"),
    ("Q-REC19-148", "rec19", 148, "W1 (b) -> (254,984, 255,045] / W1 (c) NOTHING MOVES /"),
    ("Q-REC19-149", "rec19", 149, "W1 (d) INVALID; both (a)/(b) narrow with EQUAL clips 61/61."),
    ("Q-SP-123", "spec", 123, "A statistic chosen after the runs are read is never a confrontation."),
    ("Q-A209ID-19", "a209id", 19, "NAMED, NOT HIDDEN -- TWO run defects, both fail-closed asserts caught"),
    ("Q-A209ID-20", "a209id", 20, "before any publication was trusted; both fixed by patch; the draft"),
    ("Q-A209ID-21", "a209id", 21, "pairs are kept visible:"),
    ("Q-A209ID-22", "a209id", 22, "(i) draft1 pair (analysis-s209-draft1-run{1,2}.txt/.err, rc 1 both,"),
    ("Q-A209ID-23", "a209id", 23, "stderr 318 bytes byte-identical): the q3 quarter-grid derivation"),
    ("Q-A209ID-35", "a209id", 35, "(iii) the FIRST rc=0 run's stdout/stderr were consumed by a"),
    ("Q-A209ID-36", "a209id", 36, "mis-ordered comparison step before its publication copy was saved"),
    ("Q-A209ID-37", "a209id", 37, "(publication byte-count 66,774 observed; the file itself NOT kept) --"),
    ("Q-A209ID-38", "a209id", 38, "NOT claimed as a pair leg; the official run-twice pair was RE-TAKEN"),
    ("Q-A209ID-39", "a209id", 39, "fresh afterwards (the pair above). Extra corroboration kept out of the"),
    ("Q-A209ID-40", "a209id", 40, "pair: run2-vs-run3 publication cmp exit 0 (byte-identical) before the"),
    ("Q-A209ID-41", "a209id", 41, "official pair was taken."),
    # -- GROUP 4: the committed-reference provenance chain (refs-s216) --
    ("Q-PUB4-51", "pub4", 51, "pooled median bracket gpu_ticks per (op, W, S, B) over the 3"),
    ("Q-PUB4-52", "pub4", 52, "runs x 25 rounds (75 samples); DERIVED per-dispatch = bracket/B"),
    ("Q-PUB4-53", "pub4", 53, "(ticks and ns at timestampPeriod 52.083 ns). FLOOR condition"),
    ("Q-PUB4-54", "pub4", 54, "(session 2's pre-registered 248-tick threshold): pooled median"),
    ("Q-PUB4-57a", "pub4", 57, "B2:31(PIN)"),
    ("Q-PUB4-57b", "pub4", 57, "B8:32915"),
    ("Q-PUB4-58a", "pub4", 58, "B2:31(PIN)"),
    ("Q-PUB4-58b", "pub4", 58, "B8:32228"),
    ("Q-PUB4-59a", "pub4", 59, "B2:32(PIN)"),
    ("Q-PUB4-59b", "pub4", 59, "B8:32198"),
    ("Q-PUB4-112", "pub4", 112, "committed record: session 1's single-dispatch bracket pinned at"),
    ("Q-PUB4-113", "pub4", 113, "31 ticks = 1,614.6 ns at every cell): THIS instrument's B=1"),
    ("Q-PUB4-114", "pub4", 114, "bracket is 31 ticks (1614.57 ns) at (sum,128,16) -- the 31-tick floor"),
    ("Q-PUB4-115", "pub4", 115, "value is REPRODUCED here at B<=2 (B=1 pooled medians are 31"),
    ("Q-PUB4-116", "pub4", 116, "ticks at all 18 arms; B=2 medians are 31-32 ticks -- section 3"),
    ("Q-PUB4-155", "pub4", 155, "32faster in 3/3"),
    ("Q-AS7-23", "as7", 23, "COMMITTED = {1: 31, 2: 31, 4: 11674, 8: 32915}"),
    ("Q-DC27-43", "dc27", 43, "committed controls: c2 31 (floor band 31..32); c8 32,915 (session 4 pooled median)"),
    ("Q-DC26-42", "dc26", 42, "committed controls: c2 31 (floor band 31..32); c8 32,915 (session 4 pooled median)"),
    ("Q-A147ID-24", "a147id", 24, "s27 controls census (anv-b3bisect7-20261027, line 103) and the"),
    ("Q-A147-103", "a147", 103, 's27c = open(os.path.join(GPU, "anv-b3bisect7-20261027",'),
    ("Q-PUB1-1", "pub1", 1, "# publication -- JUN-59 subgroup 8/16/32, FIRST session, INSTRUMENT"),
    ("Q-PUB1-2", "pub1", 2, "# channel (raw ANV on aiueos-6600hs-1; not the removed wire-42 loader"),
    ("Q-NDIVC-4", "ndivc", 4, "DERIVED from gpu-subgroup-reduce-anv-subgroupsize.c (the first session's"),
    ("Q-NDIVC-5", "ndivc", 5, "instrument, kept byte-stable; this file is the batch variant of it). The"),
    ("Q-NDIVC-6", "ndivc", 6, "first session's gpu_ns medians PINNED AT THE TIMESTAMP FLOOR (31 ticks ="),
    ("Q-NDIVC-7", "ndivc", 7, "1614.6 ns at every (op, W, S) cell), so the S=16-vs-32 timing question"),
    ("Q-WDPR-95", "wdpr", 95, "sessions 7-11; committed floor band 31..32 ticks, committed"),
    ("Q-AS12-26", "as12", 26, 'COMMITTED_SRC = {"c2": "sessions 1-11 floor band 31..32", "c8": "session 4 pooled median"}'),
    ("Q-AS32-41", "as32", 41, 'COMMITTED_SRC = {"c2": "sessions 1-31 floor band 31..32",'),
    ("Q-AS33-40", "as33", 40, 'COMMITTED_SRC = {"c2": "sessions 1-32 floor band 31..32",'),
    ("Q-AS34-44", "as34", 44, 'COMMITTED_SRC = {"c2": "sessions 1-33 floor band 31..32",'),
    ("Q-AB64A-24a", "ab64a", 24, "FLOOR_LIFT_TICKS = 248"),
    ("Q-AB64A-24b", "ab64a", 24, "8 x session 1's 31-tick single-dispatch floor median"),
    # -- GROUP 5: the six draft files' mutual citations --
    ("Q-S215-29", "s215", 29, "anv-b3bisect19prereg-20261102/protocol.txt L109-115; identical"),
    ("Q-S215-30", "s215", 30, "text at publication-s209.txt L663-670):"),
    ("Q-S215-104", "s215", 104, "16th's (b) remains committed history). NAMED, NOT HIDDEN: the"),
    ("Q-S215-105", "s215", 105, "frozen name's \"three-state\" is carried verbatim and is NOT"),
    ("Q-S215-106", "s215", 106, "separately defined anywhere in the frozen protocol beyond its"),
    ("Q-S215-107", "s215", 107, "parenthetical record -- under one reading the record has three"),
    ("Q-S215-108", "s215", 108, "state-blocks ((b) | (a,a) | (b)); the name's semantics is a"),
    ("Q-S215-109", "s215", 109, "DESIGN DECISION of this pre-registration, NOT made this tick."),
    ("Q-S215-111", "s215", 111, "THE ROW QUESTION (decided this tick; design): on the ROUNDS6400"),
    ("Q-S215-112", "s215", 112, "instrument, is the committed CURRENT CONTROL STATE (the 17th"),
    ("Q-S215-113", "s215", 113, "cut's C1 (a), replicated by the 18th: c2 pooled median m 31"),
    ("Q-S215-114", "s215", 114, "FLOOR in the committed floor band 31..32 at B=2; c8 within +/-5%"),
    ("Q-S215-115", "s215", 115, "of the committed 32,915; control arms VERIFY-mismatch-free) a"),
    ("Q-S215-116", "s215", 116, "SINGLE-STATE STABLE control state across consecutive cuts, or"),
    ("Q-S215-117", "s215", 117, "does the instrument's control record carry more than one state"),
    ("Q-S215-118", "s215", 118, "(the 16th's and 19th's (b) readings: c2 pooled median m 30 out"),
    ("Q-S215-119", "s215", 119, "of band)? The resolution act answers WHICH control state the"),
    ("Q-S215-120", "s215", 120, "instrument is in, and thereby whether a future cut's C1"),
    ("Q-S215-121", "s215", 121, "confronts a known state or re-reads a discrepancy."),
    ("Q-S216-59", "s216", 59, "committed controls: c2 31 (floor band 31..32); c8 32,915"),
    ("Q-S216-133", "s216", 133, "(ii) The floor band's committed floor observations parsed this"),
    ("Q-S216-134", "s216", 134, "tick are exactly {31, 32}: session 1's every-cell 31-tick pin"),
    ("Q-S216-135", "s216", 135, "(every (op,W,S) cell) and session 4's B=2 medians 31/31/32. The"),
    ("Q-S216-136", "s216", 136, "16th and 19th cuts' c2 pooled median m 30 (publication-s169.txt"),
    ("Q-S216-137", "s216", 137, '"c2 ... m 30 ... FLOOR (committed floor band 31..32 at'),
    ("Q-S216-138", "s216", 138, "B=2): False\"; publication-s209.txt L657-658 same shape at m 30)"),
    ("Q-S216-139", "s216", 139, "sits BELOW every floor observation in the provenance chain parsed"),
    ("Q-S216-140", "s216", 140, "this tick. Whether m 30 is a NEW control state of the instrument"),
    ("Q-S216-141", "s216", 141, "or a tolerance/defect reading is a DESIGN DECISION of this"),
    ("Q-S216-142", "s216", 142, "pre-registration -- NOT made this tick -- and its resolution is"),
    ("Q-S216-143", "s216", 143, "the resolution measurement act's own business."),
    ("Q-S217-28", "s217", 28, "L359:"),
    ("Q-S217-29", "s217", 29, "L364:"),
    ("Q-S217-38", "s217", 38, "protocol.txt L181-188 (quote)"),
    ("Q-S217-97", "s217", 97, "protocol.txt L380-383, quote"),
    ("Q-S217-109", "s217", 109, "protocol.txt L205ff, quote"),
    ("Q-S217-121", "s217", 121, "protocol.txt L215-218"),
    ("Q-S217-180", "s217", 180, "protocol.txt L199-204"),
    ("Q-S218-60", "s218", 60, "(b) DOMAIN OF THE ALPHABET (named boundary): the letters are"),
    ("Q-S218-61", "s218", 61, "defined ONLY on readings where c8 lands within +/-5% of"),
    ("Q-S218-62", "s218", 62, "32,915 and the control arms are VERIFY-mismatch-free --"),
    ("Q-S218-63", "s218", 63, "exactly the domain of every one of the four committed"),
    ("Q-S218-64", "s218", 64, "record readings (re-extracted this tick: all four report"),
    ("Q-S218-65", "s218", 65, "the c8 check True and the VERIFY check True, at the exact"),
    ("Q-S218-66", "s218", 66, "lines quoted in section 3). A reading where c8 lands out"),
    ("Q-S218-67", "s218", 67, "of band, or a VERIFY mismatch appears, is OUT of the"),
    ("Q-S218-68", "s218", 68, "letter domain and is NOT given a letter by this decision."),
    ("Q-S218-69", "s218", 69, "What the act does with such a reading (invalidate the act,"),
    ("Q-S218-70", "s218", 70, "abort it, re-run it) is the INVALIDATION CRITERIA decision,"),
    ("Q-S218-71", "s218", 71, "NOT made this tick -- named open, carried."),
    ("Q-S218-72", "s218", 72, "(c) THE LETTER IS A FUNCTION OF THE POOLED MEDIAN m AGAINST THE"),
    ("Q-S218-73", "s218", 73, "BAND ONLY. The CI half-width h (the s217 statistic"),
    ("Q-S218-74", "s218", 74, "machinery) is NOT part of the letter derivation -- adopted"),
    ("Q-S218-75", "s218", 75, "unchanged from the record's own derivation (every quoted"),
    ("Q-S218-76", "s218", 76, "C1 block's band check is on m itself"),
    ("Q-S218-131", "s218", 131, "This decision SEPARATES two things the word"),
    ("Q-S218-132", "s218", 132, "conflates: STATE CONSTANCY (all four letters"),
    ("Q-S218-133", "s218", 133, "equal) and STATE IDENTITY (which letter). The row"),
    ("Q-S218-136", "s218", 136, "requires BOTH constancy AND identity (a); prong B"),
    ("Q-S218-138", "s218", 138, "confronted by any non-constant sequence, and by an"),
    ("Q-S218-141", "s218", 141, "ALONE shows one present state and does not by itself"),
    ("Q-S218-142", "s218", 142, "establish two states."),
    ("Q-S218-202", "s218", 202, "four-reading act's sequence space is 2^4 = 16 sequences; the"),
    ("Q-S218-203", "s218", 203, "constant sequences are exactly 2 of 16 (all-(a), all-(b));"),
    ("Q-S218-204", "s218", 204, "the non-constant sequences 14 of 16; the committed record's"),
    ("Q-S218-205", "s218", 205, "(b)/(a)/(a)/(b) is 1 of the 14 non-constant sequences."),
    ("Q-S218-207", "s218", 207, "4. NAMED, NOT HIDDEN / SEMANTIC BOUNDARY OF THIS SLICE:"),
    ("Q-S218-208", "s218", 208, "(a) This decision defines the per-reading letters and the"),
    ("Q-S218-209", "s218", 209, "sequence meaning. It does NOT decide: the INVALIDATION"),
    ("Q-S218-210", "s218", 210, "CRITERIA (the cut protocol's"),
    ("Q-S218-211", "s218", 211, "for the resolution act -- what an out-of-domain reading"),
    ("Q-S218-212", "s218", 212, "or an act defect DOES; next slice); the"),
    ("Q-S218-213", "s218", 213, 'SEMANTICS of the name "a three-state control record"'),
    ("Q-S218-214", "s218", 214, "(what the (b) | (a,a) | (b) block reading MEANS as a"),
    ("Q-S218-215", "s218", 215, "state count -- next slice); the design-verify, the"),
    ("Q-S218-216", "s218", 216, "protocol freeze, and the landing (later slices)."),
    ("Q-S218-222", "s218", 222, "(c) The letters do not encode WHY a reading is (b); the"),
    ("Q-S218-223", "s218", 223, "discrepancy cause is UNMEASURED under every reading"),
    ("Q-S218-224", "s218", 224, "(L2 binds)."),
    ("Q-S218-239", "s218", 239, "sequence space 2^4 = 16; 2 constant / 14 non-constant; 1"),
    ("Q-S219-116", "s219", 116, "NOT a letter and NOT a state reading: it does not confront the"),
    ("Q-S219-117", "s219", 117, "row question at all (neither prong); NOTHING MOVES -- the"),
    ("Q-S219-157", "s219", 157, "EVALUABLE acts 2^4 = 16; ACT INVALID is a distinct non-letter"),
    ("Q-S219-158", "s219", 158, "outcome -> act outcome space 16 + 1 = 17; act process count"),
    ("Q-S219-159", "s219", 159, "4*(3+3) = 24 -> the run-count self-check shape re-checks ok"),
    ("Q-S219-162", "s219", 162, "4. NAMED, NOT HIDDEN / WHAT THIS SLICE DOES NOT DECIDE:"),
    ("Q-S219-163", "s219", 163, 'SEMANTICS of the name "a three-state'),
    ("Q-S219-165", "s219", 165, "decision -- next slice); the design-verify, the protocol"),
    ("Q-S219-166", "s219", 166, "freeze, and the landing (later slices)."),
    ("Q-S219-167", "s219", 167, "(b) The alternative REJECTED here, named not hidden: giving"),
    ("Q-S219-168", "s219", 168, "c8-out-of-band its own letter instead of invalidating --"),
    ("Q-S219-169", "s219", 169, "REJECTED with rationale: the s218 alphabet is ADOPTED"),
    ("Q-S219-170", "s219", 170, "UNCHANGED {a,b} defined on the four record readings' domain;"),
    ("Q-S219-171", "s219", 171, "a new symbol would have no counterpart in the committed"),
    ("Q-S219-172", "s219", 172, "record and would break the one-for-one confrontation (design"),
    ("Q-S219-173", "s219", 173, "reading)."),
    ("Q-S220-25", "s220", 25, "L109-115 (quote)"),
    ("Q-S220-33", "s220", 33, "own copy, publication-s209.txt L663-671 (quote)"),
    ("Q-S220-45", "s220", 45, "state-s215.txt L104-109 (quote)"),
    ("Q-S220-53", "s220", 53, "L207-216 (quote)"),
    ("Q-S220-62", "s220", 62, "invalidation-s219.txt L162-166 (quote)"),
    ("Q-S220-71", "s220", 71, "L630-633 (quote)"),
    ("Q-S220-75", "s220", 75, "publication-s197.txt L636-639 (quote)"),
    ("Q-S220-82", "s220", 82, "letters-s218.txt L131-142 (quote)"),
    ("Q-S220-92", "s220", 92, "state-s215.txt L111-121 (quote)"),
    ("Q-S220-193", "s220", 193, "alphabet these two coincide (DERIVED: I=2 iff B>=2 on all 16"),
    ("Q-S220-218", "s220", 218, "(e) TERMINOLOGY FIX imposed on the protocol-freeze slice (design"),
    ("Q-S220-221", "s220", 221, "state-BLOCK (epoch; a maximal constant-letter run) or state-"),
    ("Q-S220-222", "s220", 222, "IDENTITY (a distinct letter) -- and wherever the protocol text"),
    ("Q-S220-223", "s220", 223, "quotes the frozen name it glosses it in place as"),
    ("Q-S220-224", "s220", 224, "BLOCKS ((b) | (a,a) | (b)) at letter granularity; identity count"),
    ("Q-S220-225", "s220", 225, "2; underlying-state count UNMEASURED"),
    ("Q-S220-232", "s220", 232, "block-count distribution B=1: 2, B=2: 6, B=3: 6, B=4: 2 (sum 16);"),
    ("Q-S220-233", "s220", 233, "identity distribution I=1: 2, I=2: 14"),
    ("Q-S220-235", "s220", 235, "record b a a b -> B=3, I=2; the B=3 set is exactly {aaba, abaa,"),
    ("Q-S220-236", "s220", 236, "abba, baab, babb, bbab} (6 of 16; the record is one of the 6);"),
    ("Q-S220-237", "s220", 237, "tool-checked on all 16: I=2 iff B>=2 (prong-B coincidence in"),
    ("Q-S220-241", "s220", 241, "(a) After this slice NO design decision of the pre-registration"),
    ("Q-S220-242", "s220", 242, "remains open. NOT decided here (later slices): the design-"),
    ("Q-S220-243", "s220", 243, "verify, the protocol freeze (which must carry the 2(e)"),
    ("Q-S220-244", "s220", 244, "gloss), and the landing; then the control question's"),
    ("Q-S220-270", "s220", 270, "enumeration; block counts 2/6/6/2; identity counts 2/14; I=2 iff"),
]

# whole-file content wants (id, file key, substring anywhere in the bytes)
CONTENT_WANTS = [
    ("C-AB64P-RERUN", "ab64p", "JUN-59 subgroup 16-vs-32 FLOOR-LIFTING rerun"),
    ("C-AB64P-PIN", "ab64p", "FLOOR-LIFTING"),
]

# (id, description, computed string, expected string) -- the labelled
# DERIVED quantities of the s218/s219/s220 decisions, re-derived here.
ARITH_WANTS = [
    ("A-ALPHABET", "alphabet size over {a,b}", "2", "2"),
    ("A-SEQSPACE", "four-letter sequence space 2^4",
     str(2 ** 4), "16"),
    ("A-ARM-TABLE", "act run-count self-check 4*(3+3)",
     str(4 * (3 + 3)), "24"),
    ("A-OUTCOME", "act outcome space 16 + 1 (ACT INVALID is not a letter)",
     str(16 + 1), "17"),
    ("A-C8-32820-PCT", "32820 vs 32915 percent",
     "%.2f" % ((32820 - 32915) / 32915 * 100), "-0.29"),
    ("A-C8-32775-PCT", "32775 vs 32915 percent",
     "%.2f" % ((32775 - 32915) / 32915 * 100), "-0.43"),
    ("A-C8-32778-PCT", "32778 vs 32915 percent",
     "%.2f" % ((32778 - 32915) / 32915 * 100), "-0.42"),
    ("A-C8-32559-PCT", "32559 vs 32915 percent",
     "%.2f" % ((32559 - 32915) / 32915 * 100), "-1.08"),
    ("A-C8-BAND", "all four c8 medians within +/-5% of 32915",
     str(all(abs(m - 32915) <= 0.05 * 32915
             for m in (32820, 32775, 32778, 32559))), "True"),
    ("A-C2-M30-OUT", "m 30 in floor band 31..32 at B=2",
     str(31 <= 30 <= 32), "False"),
    ("A-C2-M31-IN", "m 31 in floor band 31..32 at B=2",
     str(31 <= 31 <= 32), "True"),
    ("A-CROSS-S-32228", "session-4 cross-S: 32228 vs 32915 percent",
     "%.2f" % ((32228 - 32915) / 32915 * 100), "-2.09"),
    ("A-CROSS-S-32198", "session-4 cross-S: 32198 vs 32915 percent",
     "%.2f" % ((32198 - 32915) / 32915 * 100), "-2.18"),
]


def line_of(texts, key, lineno):
    return texts[key].split(b"\n")[lineno - 1].decode("utf-8")


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def main():
    ok = 0
    failed = 0
    texts = {}
    for key in sorted(FILES):
        with open(FILES[key], "rb") as f:
            texts[key] = f.read()

    def record(want_id, detail, good):
        nonlocal ok, failed
        if good:
            ok += 1
            print("ok   %s  %s" % (want_id, detail))
        else:
            failed += 1
            print("FAIL %s  %s" % (want_id, detail))

    print("== DESIGN-VERIFY S215-TO-S220 (session 221) ==")
    print("== the control-question pre-registration's design-verify ==")
    print("== fail-closed quote + arithmetic re-derivation vs committed bytes ==")
    print("== QUOTE-ONLY / ARITHMETIC-ONLY: NO control-question quantity is computed ==")
    print()

    # 1. file-level pins (size + sha256) -- byte-level fail-closed over
    #    the whole quotation surface of the six draft files
    for want_id, key, size, sha in FILE_PINS:
        got = texts[key]
        got_sha = hashlib.sha256(got).hexdigest()
        detail = "%s size %d sha256 %s" % (SHORT[key], len(got), got_sha)
        record(want_id, detail, len(got) == size and got_sha == sha)

    # 2. line-pinned quote wants
    for want_id, key, lineno, substr in LINE_WANTS:
        lines = texts[key].split(b"\n")
        good = lineno <= len(lines) and substr.encode("utf-8") in lines[lineno - 1]
        detail = "%s:%d contains %r" % (SHORT[key], lineno, substr)
        record(want_id, detail, good)

    # 3. whole-file content wants
    for want_id, key, substr in CONTENT_WANTS:
        good = substr.encode("utf-8") in texts[key]
        record(want_id, "%s contains %r" % (SHORT[key], substr), good)

    # 4. arithmetic re-derivations (the labelled DERIVED quantities)
    for want_id, desc, computed, expected in ARITH_WANTS:
        detail = "%s -> %s (expected %s)" % (desc, computed, expected)
        record(want_id, detail, computed == expected)

    # 5. derived re-computations FROM COMMITTED BYTES
    # 5a. the four record letters re-extracted from the publications
    letters = []
    for key, lineno in (("pub169", 637), ("pub185", 662),
                        ("pub197", 662), ("pub209", 701)):
        m = re.search(r"C1 \(control replication\): \(([ab])\)",
                      line_of(texts, key, lineno))
        letters.append(m.group(1) if m else None)
    record("D-RECORD-LETTERS",
           "C1 letters re-extracted from the four publications: %s (expected ['b', 'a', 'a', 'b'])"
           % (letters,), letters == ["b", "a", "a", "b"])

    # 5b. the c8 lines: parsed percent vs re-derived percent vs the band
    c8_re = re.compile(
        r"pooled median m (\d+) within \+/-5% of committed 32915 "
        r"\(session 4 pooled median\): True \((-?\d+\.\d+)%\)")
    c8_rows = []
    c8_good = True
    for key, lineno in (("pub169", 609), ("pub185", 626),
                        ("pub197", 632), ("pub209", 659)):
        m = c8_re.search(line_of(texts, key, lineno))
        if not m:
            c8_good = False
            c8_rows.append((key, None, None, None))
            continue
        med = int(m.group(1))
        parsed_pct = float(m.group(2))
        derived_pct = round((med - 32915) / 32915 * 100, 2)
        row_ok = (parsed_pct == derived_pct
                  and abs(med - 32915) <= 0.05 * 32915)
        c8_good = c8_good and row_ok
        c8_rows.append((key, med, parsed_pct, derived_pct))
    record("D-C8-PCT",
           "c8 medians parsed/re-derived vs the +/-5% band: %s" % (c8_rows,),
           c8_good)

    # 5c. the c2 lines: pooled median vs the committed floor band flag
    c2_re = re.compile(r"pooled median m (\d+)")
    flag_re = re.compile(r"band 31\.\.32 at B=2\): (True|False)")
    c2_rows = []
    c2_good = True
    cur_m = None
    for key, lineno, want_flag in (("pub169", 607, "False"), ("pub169", 608, "False"),
                                   ("pub185", 624, "True"), ("pub185", 625, "True"),
                                   ("pub197", 630, "True"), ("pub197", 631, "True"),
                                   ("pub209", 657, "False"), ("pub209", 658, "False")):
        if lineno % 2 == 1:
            m = c2_re.search(line_of(texts, key, lineno))
            cur_m = int(m.group(1)) if m else None
        else:
            m = flag_re.search(line_of(texts, key, lineno))
            flag = m.group(1) if m else None
            in_band = cur_m is not None and 31 <= cur_m <= 32
            row_ok = (flag == want_flag and (flag == "True") == in_band)
            c2_good = c2_good and row_ok
            c2_rows.append((key, cur_m, flag, in_band))
    record("D-C2-BAND",
           "c2 pooled medians vs the committed floor band 31..32 at B=2: %s" % (c2_rows,),
           c2_good)

    # 5d. the VERIFY lines (the frozen INVALIDATION criterion's input)
    verify_good = all(
        "control arms free of VERIFY mismatches (frozen INVALIDATION criterion): True"
        in line_of(texts, key, lineno)
        for key, lineno in (("pub169", 610), ("pub185", 627),
                            ("pub197", 633), ("pub209", 660)))
    record("D-VERIFY",
           "all four record readings report control arms VERIFY-mismatch-free: True",
           verify_good)

    # 5e. the 16-sequence enumeration (the s218/s220 DERIVED machinery)
    seqs = ["".join(t) for t in itertools.product("ab", repeat=4)]

    def blocks(s):
        return 1 + sum(1 for i in range(1, len(s)) if s[i] != s[i - 1])

    def ident(s):
        return len(set(s))

    b_dist = dict((k, sum(1 for s in seqs if blocks(s) == k)) for k in (1, 2, 3, 4))
    i_dist = dict((k, sum(1 for s in seqs if ident(s) == k)) for k in (1, 2))
    b3_set = sorted(s for s in seqs if blocks(s) == 3)
    record("D-B-DIST",
           "block-count distribution over the 16 sequences: %s (expected {1: 2, 2: 6, 3: 6, 4: 2})"
           % (b_dist,), b_dist == {1: 2, 2: 6, 3: 6, 4: 2})
    record("D-I-DIST",
           "identity distribution over the 16 sequences: %s (expected {1: 2, 2: 14})"
           % (i_dist,), i_dist == {1: 2, 2: 14})
    record("D-B3-SET",
           "the B=3 set: %s (expected ['aaba', 'abaa', 'abba', 'baab', 'babb', 'bbab'])"
           % (b3_set,), b3_set == ["aaba", "abaa", "abba", "baab", "babb", "bbab"])
    record("D-RECORD-BAAB",
           "record b a a b -> blocks %d, identity %d (expected 3, 2)"
           % (blocks("baab"), ident("baab")),
           blocks("baab") == 3 and ident("baab") == 2)
    iff_good = all((ident(s) == 2) == (blocks(s) >= 2) for s in seqs)
    record("D-IFF",
           "I=2 iff B>=2 on all 16 sequences (prong-B coincidence)", iff_good)
    record("D-RECORD-IN-B3",
           "the record b a a b is one of the 6 B=3 sequences", "baab" in b3_set)

    # 5f. the draft D-claims parsed and compared to the re-derivation
    s220_join = norm(" ".join(line_of(texts, "s220", n) for n in range(232, 238)))
    m = re.search(r"B=1: (\d+), B=2: (\d+), B=3: (\d+), B=4: (\d+)", s220_join)
    claimed_b = tuple(int(m.group(i)) for i in (1, 2, 3, 4)) if m else None
    m = re.search(r"I=1: (\d+), I=2: (\d+)", s220_join)
    claimed_i = tuple(int(m.group(i)) for i in (1, 2)) if m else None
    m = re.search(r"the B=3 set is exactly \{([^}]+)\}", s220_join)
    claimed_set = sorted(x.strip() for x in m.group(1).split(",")) if m else None
    m = re.search(r"record b a a b -> B=(\d+), I=(\d+)", s220_join)
    claimed_rec = (int(m.group(1)), int(m.group(2))) if m else None
    record("D-S220-CLAIMS",
           "threestate-s220 L232-237 D-claims: B-dist %s vs %s; I-dist %s vs %s; "
           "B=3 set %s vs %s; record %s vs (3, 2)"
           % (claimed_b, (2, 6, 6, 2), claimed_i, (2, 14),
              claimed_set, b3_set, claimed_rec),
           claimed_b == (2, 6, 6, 2) and claimed_i == (2, 14)
           and claimed_set == b3_set and claimed_rec == (3, 2))
    s220_270 = line_of(texts, "s220", 270)
    m = re.search(r"block counts (\d+)/(\d+)/(\d+)/(\d+); identity counts (\d+)/(\d+)",
                  s220_270)
    claimed_summary = tuple(int(m.group(i)) for i in range(1, 7)) if m else None
    record("D-S220-SUMMARY",
           "threestate-s220 L270 summary counts %s vs (2, 6, 6, 2, 2, 14)"
           % (claimed_summary,),
           claimed_summary == (2, 6, 6, 2, 2, 14))

    s218_join = norm(" ".join(line_of(texts, "s218", n) for n in range(202, 206)))
    m = re.search(r"sequence space is 2\^4 = (\d+)", s218_join)
    sp = int(m.group(1)) if m else None
    m = re.search(r"exactly (\d+) of (\d+)", s218_join)
    consts = (int(m.group(1)), int(m.group(2))) if m else None
    m = re.search(r"non-constant sequences (\d+) of (\d+)", s218_join)
    nonconsts = (int(m.group(1)), int(m.group(2))) if m else None
    m = re.search(r"is 1 of the (\d+) non-constant", s218_join)
    rec_rank = int(m.group(1)) if m else None
    record("D-S218-CLAIMS",
           "letters-s218 L202-205 D-claims: space %s vs 16; constants %s vs (2, 16); "
           "non-constants %s vs (14, 16); record 1 of %s vs 14"
           % (sp, consts, nonconsts, rec_rank),
           sp == 16 and consts == (2, 16) and nonconsts == (14, 16)
           and rec_rank == 14)

    s219_join = norm(" ".join(line_of(texts, "s219", n) for n in range(157, 160)))
    m = re.search(r"acts 2\^4 = (\d+)", s219_join)
    sp19 = int(m.group(1)) if m else None
    m = re.search(r"act outcome space 16 \+ 1 = (\d+)", s219_join)
    out19 = int(m.group(1)) if m else None
    m = re.search(r"4\*\(3\+3\) = (\d+)", s219_join)
    proc19 = int(m.group(1)) if m else None
    record("D-S219-CLAIMS",
           "invalidation-s219 L157-159 D-claims: space %s vs 16; outcomes %s vs 17; "
           "processes %s vs 24" % (sp19, out19, proc19),
           sp19 == 16 and out19 == 17 and proc19 == 24)

    # 5g. the frozen-name core text: the pr19 quote and the pub209 copy
    core = ("NOTHING is superseded in the prior cuts' favour and the control "
            "question RE-OPENS as a named open control question carried forward: "
            "a three-state control record on the ROUNDS6400 instrument (the 16th "
            "cut's (b), the 17th cut's (a), the 18th cut's (a), this cut's (b)); "
            "W1 (d) fires, CUT VERDICT INVALID; the discrepancy cause stays "
            "UNMEASURED (L2 binds).")
    pr19_join = norm(" ".join(line_of(texts, "pr19", n) for n in range(109, 116)))
    pub209_join = norm(" ".join(line_of(texts, "pub209", n) for n in range(663, 672)))
    record("D-FROZEN-NAME",
           "the frozen-name core text appears in both the frozen protocol (L109-115) "
           "and the 19th cut's publication D2 copy (L663-671) at identical wording",
           core in pr19_join and core in pub209_join)

    # 5h. the ROUNDS6400 instrument source pin re-hashed from committed bytes
    pin = line_of(texts, "pr19", 186).strip() + \
        line_of(texts, "pr19", 187).strip().split(" ")[0]
    got_sha = hashlib.sha256(texts["r6400"]).hexdigest()
    record("D-R6400-PIN",
           "pr19 source pin %s == sha256(%s) %s" % (pin, SHORT["r6400"], got_sha),
           pin == got_sha and re.fullmatch(r"[0-9a-f]{64}", pin) is not None)
    ndivc_sha = hashlib.sha256(texts["ndivc"]).hexdigest()
    record("D-NDIVC-PIN",
           "pr19 cites the committed a5e539f0... copy; sha256(%s) = %s"
           % (SHORT["ndivc"], ndivc_sha),
           ndivc_sha.startswith("a5e539f0")
           and "a5e539f0" in line_of(texts, "pr19", 183))

    # 5i. the act run count: arm table vs the 19th cut's own self-check
    m = re.search(r"runs parsed: (\d+)", line_of(texts, "pub209", 162))
    runs = int(m.group(1)) if m else None
    record("D-RUN-COUNT",
           "publication-s209 runs parsed %s vs the arm table 3+48+3 = %d"
           % (runs, 3 + 48 + 3), runs == 3 + 48 + 3)

    print()
    print("DESIGN-VERIFY S215-TO-S220 SUMMARY: %d ok / %d failed" % (ok, failed))
    if failed == 0:
        print("DESIGN-VERIFY S215-TO-S220 COMPLETE (fail-closed: 0 failed)")
        return 0
    print("DESIGN-VERIFY S215-TO-S220 FAILED (fail-closed)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
