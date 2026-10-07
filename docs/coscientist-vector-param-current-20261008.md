# Private parameter bounds：原19本の機能確認

既定OFFの実験compilerで、元の19入力のバイト差分検査と、baseline・candidate・新規Cの171件の有限な機能比較が完了した。現在の候補の性能向上、C以上の速度、公式Embenchスコア、製品採用はまだ認定していない。

旧 [parameter bounds checkpoint](coscientist-vector-param-bounds-20261007.md) の13か所・12本一致・4本HOLD、拒否スイートv1のHOLDとv2の46回目FAIL、および旧archiveは保持する。以下は別の事前登録とレビューを経た追加証拠であり、旧FAILをPASSへ読み替えるものではない。

| 受理した範囲 | 結果と限界 |
| --- | --- |
| 元19本の機械コード検査 | 全19本の差を登録した契約で説明。64か所の境界チェック省略、12本は全体バイト一致。機能・速度の証拠とは別 |
| 新7 fixtureの105回 | 正規の`fn-ref`構文の新2本と以前未実行だった5本。grounded self-neutralは12バイト削減、残り6本は3 armのKSEED/native全体一致。全7本×3入力×3 armの機能比較を確認 |
| 新規C19 build | 元のC入力・bridge・includeを固定し、Apple Clang17 / SDK26.2で19 build・14 identity query・23 clang invocation。歴史的なrecipe不明C binary／統計とは混ぜない |
| 現在の19 runner build | 正確なbaseline/candidate/C bytesを含むimmutable headerから同じClang17・SDK26.2で新規ビルド。19 build・14 identity query・23 clang invocationを独立監査 |
| 原19本の171件 | 各`n=0,1,maxN`×3 arm、57 triple。全call終了。nativeの結果・fuel・4種terminal arenaを厳密比較し、Cの境界値0／正の入力の検証値1を確認 |

64か所の内訳はedn 4、huffbench 6、nettle-sha256 11、picojpeg 30、qrduino 11、tarfind 1、ud 1。handle検査・descriptor・pool・address・loadを保持し、登録済みの分岐・export・データ位置補正を検査した。新7 fixtureは旧46回FAILの誤記fixtureと、既済みの最初3ケースを再実行していない。fixture比較だけで、内部guardの実際の発火原因やdirty sealの全経路を認定しない。

171件の独立raw監査は `fe2110aa53973d411f2cbf269eb1bbb7a07e592dc008be77116094fd94a45c28`。argv・環境・raw hash・停止順・全57 tripleを確認した。native arenaは最後の1 callのusedとcapacityの診断であり、peakや全call traceではない。Cは `unavailable-C` / `null` とし、Cのarena測定やnativeとのarena一致を捏造しない。source guardは固定されたdriverの制御から確認しており、各callで独立したsource snapshotを出したわけではない。有限な固定入力の一致は普遍的な意味保存の証明ではない。

最小限の[受理済み監査報告](evidence/coscientist-inverse-aes-20261007/vector-param-current/accepted-reports/functional171.json)と終了記録を保存する。これは報告の保存であり、全rawを含むportable archiveではない。完全なsource・argv・stdout/stderr・成果物・GO・失敗記録は、対応する`/Users/junkawasaki/github/workspaces/codex`の実験ディレクトリに保持している。旧archiveを上書きしていない。

[ComputeCID / ResultCID](coscientist-compute-addressed-analysis-20261007.md)のC0は、activation内exact memoと寄与の保存・新しい集計への再生が実装済みで、有限fixtureの証拠を持つ。C1のnative canonical encoding・stable reference・shadow receiptと、C2の検証済み永続／共有再利用は未実装である。現在のSHA-256をnative IPLD CIDと呼ばず、チェック省略やarena診断をCIDの性能効果とは扱わない。再利用には完全なread footprint、出力状態の更新、support・poison・診断、fuel／論理chargeの保存、cold／warm／disabledでの生成バイト一致が必要である。

タイミング計画v1はソースレビューでHOLDになった。独立171件監査の確認が無関係なPASS資料を受理できた点と、CPU診断失敗時に終了済みrunnerのrawを保存する前に止まる点がT1/T2である。v1を保持し、別のv2修正と独立レビューを待つ。171件の単発elapsed・RSSは性能結果へ転用しない。新しい測定は同一host・元19本・固定maxN・静穏条件・反復paired比較を満たした別の有限GOを必要とする。

実験compilerはsource `ea8281843170b65999ff5a6460a2ba2b3474f04e8e5fda8abc616bf283a0acf5`、native `4158d7de2dfe4d922450b60788bb5f6a950ca129f92f0b841069aa4c0f76b509`（943,320バイト）。別の6回の検査では3世代のnative/KSEEDが一致した。製品経路は変更していない。
