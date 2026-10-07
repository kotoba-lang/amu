# Parameter bounds：最初の実測と静穏条件による停止

元19本のbaseline・candidate・新規Cを比較する1回限りのcampaignは、2本目のCRC32でCPU静穏条件の試行上限に達して停止した。482 runner・936 load queryは終了済みで、再起動・基準緩和・過去の統計との合算はしていない。**全19本の比較とC以上の性能は未達**である。

完了したaha-mont64だけの同一host比較は次のとおり。n=32、30組採用／66組試行、1 callは元のbodyを32回実行する。数値は共通runnerのelapsedをcalls×32で割ったもので、公式Embenchスコアではない。

| 実装 | 平均 ns/body | 標準偏差 ns |
| --- | ---: | ---: |
| baseline | 718.08 | 10.72 |
| candidate | 718.05 | 9.90 |
| Apple Clang17 -O2 C | 578.16 | 11.32 |

candidate/Cは1.241954、候補が約24.20%遅かった。baselineとcandidateは生成コードが全体バイト一致しており、時間差は今回の最適化の効果として扱わない。3 armの相対標準偏差は全て0.1以下だが、この1本の結果を全19本の結論へ広げない。

CRC32は90組試行して12組採用、78組棄却。個々のarmで推定background CPUによる棄却が172件あり、host load／短い区間による棄却は0件だった。必要30組に達していないため、CRC32の性能値と全19本の幾何平均を認定しない。nativeの結果・fuel・4種terminal arena、Cの0/1 oracleとunavailable/null arenaは、保存された全packetで独立監査した。

[独立監査](evidence/coscientist-inverse-aes-20261007/vector-param-timing/actual-review.json)は`dcf873a676d3a69bc9d1cadc7c52d7cf5218d80a9777a2056d3b42283580dbc8`。ソースレビュー、事前登録、有限GO、監査入力の全hash、部分結果と終了記録を同じ証拠フォルダへ保存した。全生ログ3777ファイルは`/Users/junkawasaki/github/workspaces/codex/vector-param-original19-transfer-v1-root/collected-timing-campaign-v1`に保持する。この保存はportableな全raw archiveではない。外側のtoolがexit0を返した一方、remoteのFAILとtracebackは確認されており、exit0をcampaign合格へ読み替えていない。

CPUの確認範囲はrunner起動・warmup・親の生ログ保存を含むenvelopeだった。CRC32では平均timed/envelopeがbaseline 296.78/309.27ms、candidate 303.96/316.28ms、C 258.97/383.56msで、Cの区間外処理が特に長い。これだけで棄却原因を確定しない。次の別実験では、同じ閾値のまま実際のtimed loopを囲むCPU countersを取得し、起動時のenvelopeと区別する。元のFAILは保持し、異なる収集方式の統計を混ぜない。

次のコード生成候補は、allocator由来の有効なvector handleを証明した場合の検査省略である。現在の長さsealやCIDだけでは許可しない。本番ソースは容量不足でSIGILL、handlerはexit120とするが、既存ローダーbinaryとCソースのビルド来歴は未確認である。まず固定ローダーで正常・容量不足・継続不能を検証し、arena reset・未知callback・公開入口を拒否する。新しい省略はまだ実装・採用していない。製品経路は既定OFFのまま。
