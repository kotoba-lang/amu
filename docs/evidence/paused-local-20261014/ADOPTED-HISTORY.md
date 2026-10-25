# 週次枠の再開以降に採用済みの変更

停止時点のmainは `43524a1ce142538c028a4b3bf57edabc6e8a2d85`。以下の統合コミットがこのmainの祖先であることをローカルGitで確認済みです。古いpending/live等のstatus文字列より、統合記録と現在のmainを優先してください。

| 変更 | PR | 統合コミット | main祖先 |
| --- | --- | --- | --- |
| PF two-argument priority v7 | [#1296](https://github.com/kotoba-lang/amu/pull/1296) | `a81ba2207c4c04d0cfac237ae1deac6ed8735422` | 確認済み |
| One-call descriptor reuse | [#1298](https://github.com/kotoba-lang/amu/pull/1298) | `94dc85b96b04b92725c7543bd4cd2c9c656333a1` | 確認済み |
| Sequential scan | [#1300](https://github.com/kotoba-lang/amu/pull/1300) | `4d7337532bf2e14302a7c73e4a7fa90605456cea` | 確認済み |
| Masked positive quotient | [#1303](https://github.com/kotoba-lang/amu/pull/1303) | `841c7f23c7eb5c2defc9fec72a2cb0abcf0afb9c` | 確認済み |
| Direct mask source | [#1304](https://github.com/kotoba-lang/amu/pull/1304) | `e915af7347a0c07ab7046faf94fb4a066a752465` | 確認済み |
| Prepaid fuel register reuse | [#1306](https://github.com/kotoba-lang/amu/pull/1306) | `b7c85f39469920d50362b6bbbaa6f6f9a6cbda4a` | 確認済み |
| Nonzero guard charge | [#1307](https://github.com/kotoba-lang/amu/pull/1307) | `9a3ffd0c39a17d1471438b68ba549cbb67aed36d` | 確認済み |
| Adjacent fuel reload | [#1309](https://github.com/kotoba-lang/amu/pull/1309) | `00b43fcd09916faec57cf01ea170d33170a5006e` | 確認済み |
| One-word jump | [#1310](https://github.com/kotoba-lang/amu/pull/1310) | `35c65b589a52d084bf2a21f7c07b9695ec2297ee` | 確認済み |
| Picojpeg color NEON x4 | [#1311](https://github.com/kotoba-lang/amu/pull/1311) | `07c74ca9660da854408ae914a730543dbbd8eb69` | 確認済み |
| Copy/write available-value forwarding, 16 stages | [#1312](https://github.com/kotoba-lang/amu/pull/1312) | `43524a1ce142538c028a4b3bf57edabc6e8a2d85` | 確認済み |

これは採用された改善の一覧で、各変更の短縮率を合算するものではありません。全体の最新比較はround114です。未採用PR1313は含めていません。さらに以前の履歴は[前回の引継ぎ](../embench-paused-handoff-publication-20261013/HANDOFF.md)を参照してください。
