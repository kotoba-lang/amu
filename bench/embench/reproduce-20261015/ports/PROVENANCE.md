# Provenance and licenses of the 19 measured port sources

The files `official-<w>.kotoba` are byte-identical to the sources the 15 October 2026 round compiled (their SHA-256 is in
`expected/measured-images.json`; changing a byte would change the measured inputs, so license notes are recorded here rather
than added to the files). Each is a translated Kotoba port of the Embench IoT C program `src/<w>/` at upstream commit
`09c2ed8c3b7008c95d08b038de4a3f6dc103ed70` (https://github.com/embench/embench-iot), with the measured interface
`benchmark-unchecked` (timed body), `verify-state` (checked outside the timed interval) and `bench-verify`. The round114
artifact table records that each was derived from an earlier full translation ("original" below) with every original
function byte-equal. The license of each port is the license of its upstream program (column "license"); the full texts
are in `bench/embench/licenses/` (GPL-3.0, MIT) and the repository root `LICENSE` (Apache-2.0).

## aha-mont64

* measured source: `ports/official-aha-mont64.kotoba`, 3530 bytes, sha256 `80e4830944505c1fdf00d9414729d8a036987c53995e67356546bc0d50485c10`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/aha-mont64/mont64.c` (`52b99661f046…`)
* upstream copyright: This version, copyright (C) 2013-2019 Embecosm Limited and University of
* port header (verbatim): `;; Original complete mont64 body; verification once after repetition.` / `;; SPDX-License-Identifier: GPL-3.0-or-later; Embecosm/Bristol 2013-2019.`
* lineage: round114 artifact `originalSHA256` `05ce65b5791786c347199162028c098d1c9a51cfb890241bac10c08c983fbf7c` (original functions byte-equal: True)

## crc32

* measured source: `ports/official-crc32.kotoba`, 4661 bytes, sha256 `6b953d94432051b683d947e1d3b67ee7b563c2c100408dc0b5c0165db90d6958`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/crc32/crc_32.c` (`98966b59550c…`)
* upstream copyright: This version, copyright (C) 2013-2019 Embecosm Limited and University of
* port header (verbatim): `;; Complete original 1024-byte CRC body; verification once after repetition.` / `;; Copyright 2013-2019 Embecosm/Bristol; SPDX-License-Identifier: GPL-3.0-or-later.`
* lineage: round114 artifact `originalSHA256` `d3ef82a6a6f973002aef29ac6a443d46437fc60d9e1151808220a4635a3d01c3` (original functions byte-equal: True)

## depthconv

* measured source: `ports/official-depthconv.kotoba`, 3725 bytes, sha256 `94ab10e40d516b465c088cd8409439ba527c02b86a551c691aba0fe6fbb7a68e`
* license: **Apache-2.0** (upstream SPDX); text: the repository root `LICENSE` (Apache-2.0)
* upstream files at 09c2ed8c: `src/depthconv/depthconv.c` (`a6aadf6e0741…`)
* upstream copyright: Copyright 2024 The TensorFlow Authors. All Rights Reserved.
* port header (verbatim): `;; Generated fixed-workload port of Embench 2.0rc2 depthconv.c.` / `;; Copyright 2024 The TensorFlow Authors. SPDX-License-Identifier: Apache-2.0.` / `;; Representation: table. Inner loop unrolled: True. Channel inline: True.` / `;; No expected answer substitutes for the kernel.`
* lineage: round114 artifact `originalSHA256` `886b9f612857da9f6dab52782e44b60d18e4febcd79cc1dcc9b4af4bb8a894c1` (original functions byte-equal: True)

## edn

* measured source: `ports/official-edn.kotoba`, 11613 bytes, sha256 `9233c807252a4baa49cb0528765ce44bf85e81448d83c20732cdd2ec3a7b3563`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/edn/libedn.c` (`2604a80fbe70…`)
* upstream copyright: This version, copyright (C) 2014-2019 Embecosm Limited and University of
* port header (verbatim): `;; Complete Embench 2.0rc2 EDN fixed workload. SPDX-License-Identifier: GPL-3.0-or-later.`
* lineage: round114 artifact `originalSHA256` `f34ec1384dd2b9b05fd0498d581e36421e379726eddb5a613427241e3c3a8e20` (original functions byte-equal: True)

## huffbench

* measured source: `ports/official-huffbench.kotoba`, 10001 bytes, sha256 `658d06ba38e98d65f649539b9c523abb266b19b1152efa87e34be769ad85695e`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/huffbench/libhuffbench.c` (`db93b8ea3c68…`)
* upstream copyright: This version, copyright (C) 2014-2019 Embecosm Limited and University of
* port header (verbatim): (none in the measured file; this entry is its license notice: GPL-3.0-or-later, copyright Embecosm Limited and University of Bristol 2014-2019 per upstream)
* lineage: round114 artifact `originalSHA256` `33099ec837abd05a63008d6330af670b906401c80848a8613673b5ae00269dec` (original functions byte-equal: True)

## matmult-int

* measured source: `ports/official-matmult-int.kotoba`, 11706 bytes, sha256 `e20b85a139f4b0e54ac3b3826527431d1680cef9c2d4d1eb804b7ff6fd5c4642`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/matmult-int/matmult-int.c` (`a52a60dfc82e…`)
* upstream copyright: This version, copyright (C) 2013-2019 Embecosm Limited and University of
* port header (verbatim): `;; Complete original RNG/init/copy/20x20x20 multiplication and final verifier.` / `;; Copyright 2013-2019 Embecosm/Bristol; SPDX-License-Identifier: GPL-3.0-or-later.`
* lineage: round114 artifact `originalSHA256` `84717e4e930a593acbc0b4389d791e51ed53683a982deb19fe85864178152e34` (original functions byte-equal: True)

## md5sum

* measured source: `ports/official-md5sum.kotoba`, 4923 bytes, sha256 `36c704016e3dd46a8502918be49813188da2fd855aa2cb17e77b7f6754b37c35`
* license: **MIT** (upstream SPDX); text: `bench/embench/licenses/MIT.txt`
* upstream files at 09c2ed8c: `src/md5sum/md5.c` (`59c2d7bb48fa…`)
* port header (verbatim): `;; Complete original 1000-byte MD5 profile; SPDX-License-Identifier: MIT.`
* lineage: round114 artifact `originalSHA256` `154816149d8c87b18ff665c6ad57161ed45e65ed852c0212ac30ca47f80e1dde` (original functions byte-equal: True)

## nettle-aes

* measured source: `ports/official-nettle-aes.kotoba`, 39547 bytes, sha256 `c5900becf3196c4dc398839ef4894da5d883bfbf23ce544cb7575e88f51e5afe`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/nettle-aes/nettle-aes.c` (`140117d48a83…`)
* upstream copyright: Copyright (C) 2000, 2001, 2002 Rafael R. Sevilla, Niels Möller; Copyright (C) 2001, 2002, 2010, 2013  Niels Möller; Copyright (C) 2019 Embecosm Limited
* port header (verbatim): `;; Full pinned Nettle AES-256 workload: both schedules, inversion, 16 blocks.` / `;; Copyright 2000-2013 Rafael R. Sevilla/Niels Moeller, 2019 Embecosm.` / `;; SPDX-License-Identifier: GPL-3.0-or-later.`
* lineage: round114 artifact `originalSHA256` `5c224278b7abb7db9e70a118204f4772bb108483e1369828aabb12cc6f2408c4` (original functions byte-equal: True)

## nettle-sha256

* measured source: `ports/official-nettle-sha256.kotoba`, 6706 bytes, sha256 `402d5131d710b18cefc3f6497be4e1fe4af9b125baca18d495fe161c3e30fed4`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/nettle-sha256/nettle-sha256.c` (`afe00fb383d2…`)
* upstream copyright: Copyright (C) 2001 Niels Möller; Copyright (C) 2019 Embecosm Limited
* port header (verbatim): `;; Nettle SHA256 original input; GPL-3.0-or-later, Niels Moller/Embecosm.`
* lineage: round114 artifact `originalSHA256` `30b76a306b744fbdd9ab0018df2e1f49e9f01b74206dbbb77e4700b0cde8526e` (original functions byte-equal: True)

## nsichneu

* measured source: `ports/official-nsichneu.kotoba`, 30636 bytes, sha256 `965ef6f0336b21e40fda035b073e6c9a587ca9fdacde899ef4af008340127ffe`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/nsichneu/libnsichneu.c` (`7d15a238b045…`)
* upstream copyright: This version, copyright (C) 2014-2019 Embecosm Limited and University of; Copyright (c) 1998/1999, C-LAB, Paderborn
* port header (verbatim): `;; Complete pinned Embench NSichneu: all 6 T1 and 120 T2 transitions.` / `;; Copyright 1998/1999 C-LAB Paderborn, 2014-2019 Embecosm/University of Bristol.` / `;; Contributors Friedhelm Stappert, James Pallister, Jeremy Bennett.` / `;; SPDX-License-Identifier: GPL-3.0-or-later.` / `;; State: 3 marking counts, P1[3], P2[5], P3[6].`
* lineage: round114 artifact `originalSHA256` `24eb0464fd75b4d3ff0fde5bf044611a7cfebd2054222194fc54642f164cb9e7` (original functions byte-equal: True)

## picojpeg

* measured source: `ports/official-picojpeg.kotoba`, 36985 bytes, sha256 `60bf92069c7e02b38bf69297835cb5db5760c280b0498a5c111749fbbce6609b`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/picojpeg/libpicojpeg.c` (`ed1fb932e9c2…`), `src/picojpeg/picojpeg.h` (`50dbd519c3e7…`), `src/picojpeg/picojpeg_test.c` (`fab1ba5e93f8…`)
* upstream copyright: This version, copyright (C) 2014-2019 Embecosm Limited and University of
* port header (verbatim): `;; Original 570-byte 51x64 YH1V1 fixture, all 56 MCUs, reused owned workspace.` / `;; Copyright 2014-2019 Embecosm/Bristol; picojpeg Rich Geldreich, public domain.`
* lineage: round114 artifact `originalSHA256` `f570d637a074437c8bf80dccd646efae834962a312f0cea72638f5376350b8cd` (original functions byte-equal: True)

## qrduino

* measured source: `ports/official-qrduino.kotoba`, 24473 bytes, sha256 `c51a32d2848c7f3a73b975919c60ec4e6a0a2dc8f8cbe8f30a19b84439e26a84`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/qrduino/ecctable.h` (`54e176fa47d4…`), `src/qrduino/qrbits.h` (`af772ed9bd01…`), `src/qrduino/qrencode.c` (`05d2147e1809…`), `src/qrduino/qrencode.h` (`0e53eccb11ab…`), `src/qrduino/qrframe.c` (`3d3400ff94ba…`), `src/qrduino/qrtest.c` (`7556be13dbcb…`)
* upstream copyright: This version, copyright (C) 2014-2019 Embecosm Limited and University of
* port header (verbatim): `;; Full v2/L original byte mode, ECC, frame, placement, eight masks, scoring and format.` / `;; Copyright 2014-2019 Embecosm/Bristol, qrduino contributors; GPL-3.0-or-later.`
* lineage: round114 artifact `originalSHA256` `5c5f1eb44dee7195bfcee2101010334edde40b00253754bb23e2dd1ecf35a657` (original functions byte-equal: True)

## sglib-combined

* measured source: `ports/official-sglib-combined.kotoba`, 14596 bytes, sha256 `2122b3005ad248c096153bc148ac9df58b6022b37ae025caea948dd0dc7c0210`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/sglib-combined/combined.c` (`7d817bec0dd8…`), `src/sglib-combined/sglib.h` (`335eef568a35…`)
* upstream copyright: This version, copyright (C) 2014-2019 Embecosm Limited and University of
* port header (verbatim): `;; Full pinned container algorithms; pointer identities are owned node indices.` / `;; Copyright 2014-2019 Embecosm / University of Bristol.` / `;; SGLIB copyright 2003-2005 Marian Vittek, Bratislava.` / `;; SPDX-License-Identifier: GPL-3.0-or-later.`
* lineage: round114 artifact `originalSHA256` `b0755e54485eb3c8365b2b1f389e21807b5e52b1b030a95194f63aa4a07e19e0` (original functions byte-equal: True)

## slre

* measured source: `ports/official-slre.kotoba`, 12109 bytes, sha256 `9020ba092635916ce7c52e3dd8a3482de64bc3ba9f6b4a9b8026d8557957c086`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/slre/libslre.c` (`ff918566aa58…`), `src/slre/slre.h` (`87bdc34b18e2…`)
* upstream copyright: Copyright (c) 2004-2013 Sergey Lyubka <valenok@gmail.com>; Copyright (c) 2013 Cesanta Software Limited All rights reserved; This version, copyright (C) 2014-2019 Embecosm Limited and University of
* port header (verbatim): `;; Complete pinned SLRE algorithm, ASCII Embench profile, owned indexed state.` / `;; Copyright 2004-2013 Sergey Lyubka and Cesanta Software Limited.` / `;; Copyright 2014-2019 Embecosm Limited / University of Bristol.` / `;; SPDX-License-Identifier: GPL-3.0-or-later.`
* lineage: round114 artifact `originalSHA256` `84cdac4d3fec6a086f3aa186c1ebb7ee1c4fd274a1c09fa229b7e6b079dfbcea` (original functions byte-equal: True)

## statemate

* measured source: `ports/official-statemate.kotoba`, 60571 bytes, sha256 `cdf45943f041953ad73b8780517e4eee50d99ae1bf1d8f011049a87f26c33d6d`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/statemate/libstatemate.c` (`389c4bae5cab…`)
* upstream copyright: This version, copyright (C) 2014-2019 Embecosm Limited and University of
* port header (verbatim): `;; All pinned STARC controller functions and switch/while control flow.` / `;; Copyright 1998/1999 C-LAB Paderborn, 2014-2019 Embecosm/University of Bristol.` / `;; SPDX-License-Identifier: GPL-3.0-or-later.`
* lineage: round114 artifact `originalSHA256` `977d840bc3beee78ff8fcc43fd5c34bdb786b65da494c5926a4745515cc0bf44` (original functions byte-equal: True)

## tarfind

* measured source: `ports/official-tarfind.kotoba`, 2707 bytes, sha256 `76631742d69859b03bd39fd2ce1504291731a316f61ff98245f00d409803ec71`
* license: **MIT** (upstream SPDX); text: `bench/embench/licenses/MIT.txt`
* upstream files at 09c2ed8c: `src/tarfind/tarfind.c` (`169eceee1116…`)
* port header (verbatim): `;; tarfind MIT; BEEBS RNG GPL-3.0-or-later. Original 35 full 257-byte headers.`
* lineage: round114 artifact `originalSHA256` `fd6157fb8fdc82a056baf5ed94cc47cac66bf0a77f86d7eb6983370a18407653` (original functions byte-equal: True)

## ud

* measured source: `ports/official-ud.kotoba`, 3100 bytes, sha256 `dc5a74d9cde50cb5cb420fecabdbeb6af4c699a5202909049cdb50d9910d4221`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/ud/libud.c` (`eb9cb63f7a5d…`)
* upstream copyright: This version, copyright (C) 2014-2019 Embecosm Limited and University of
* port header (verbatim): `;; Original 6 active equations, 20x20 storage, LU and both substitutions.` / `;; Copyright 2014-2019 Embecosm/Bristol; SPDX-License-Identifier: GPL-3.0-or-later.`
* lineage: round114 artifact `originalSHA256` `fc511e2fec1a165a7eead3188deb823f957aefa29d47baac3f5d97fcb0caf41b` (original functions byte-equal: True)

## wikisort

* measured source: `ports/official-wikisort.kotoba`, 21520 bytes, sha256 `b19beb075a6622caf63da7876d97d2ccf44c97fb68dfecad6b2a7bbac19e5c3d`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/wikisort/libwikisort.c` (`8cad015cb2e7…`)
* upstream copyright: This version, copyright (C) 2014-2019 Embecosm Limited and University of
* port header (verbatim): `;; Original 400-item/cache-512 path, nine generators and stable value/index pairs.` / `;; Copyright 2014-2019 Embecosm/Bristol and WikiSort contributors; GPL-3.0-or-later.`
* lineage: round114 artifact `originalSHA256` `89d70084e21651c328dd312538603e4eb9e67757d5f94b9253ebeb3f98b9890c` (original functions byte-equal: True)

## xgboost

* measured source: `ports/official-xgboost.kotoba`, 57374 bytes, sha256 `78c33ca4cb05425ad5a6b6f4de0725dedb07a05ef772b9f370768d0b1d23acdf`
* license: **GPL-3.0-or-later** (upstream SPDX); text: `bench/embench/licenses/GPL-3.0.txt`
* upstream files at 09c2ed8c: `src/xgboost/testbench.c` (`f357fe4b10ef…`), `src/xgboost/xgboost.c` (`f8bfdbe790a5…`), `src/xgboost/xgboost.h` (`ccc41929ab9a…`)
* port header (verbatim): `;; All original 400 trees / 128 inputs. GPL-3.0-or-later, Embench contributors.`
* lineage: round114 artifact `originalSHA256` `abdc982d1feebe0260bf5d8c5d326d48387fa2ece229208b308be5fa7ba4bfbe` (original functions byte-equal: True)

