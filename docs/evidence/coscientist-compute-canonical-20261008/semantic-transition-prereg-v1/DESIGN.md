# ComputeCID / ResultCID: semantic query と admission / transition の分離

この登録は新しい source-only 仮説です。実装・native 実行・キャッシュ有効化の許可ではありません。現在の canonical V2 の完全 request、35 項目の Result 投影、512 項目の Transition、valid-last の関連付けは保存します。

既存の実測3ケースは同一 Snapshot の別 subject 5/4/3 で、完全 Compute request の重複は0件でした。case-id を変えた request2 はシリアライズ確認です。正の work charge が積み上がる同一 activation では、reset がない限り work80 を含む完全キーが変わります。この完全キーは証拠・admission identity として保持し、これだけによる cache speed 仮説を停止します。

semantic query は evaluator/rules/型付き subject/完全 read context/four entry bounds/alias・return・effect・lifetime・support・poison を拘束します。admission は current work/refusal/resource budgets、preaggregate、memo-valid/lastkey、capture phase を保持します。ただし role を記述したことはキー除外の証明ではありません。初期除外承認は空です。曖昧な読み取りは完全キーに残し、分類できなければ shadow を拒否します。

`vw-arg-bound` は target の旧 aggregate を読み、その minima 更新後に独立した per-edge contribution を capture します。これは出力側 role の候補を示しますが、support・poison・制御分岐への推移的影響がないことは未証明です。`vw-memo-query` は valid と four-bound key で経路を選び、replay は既存 minima を読み直します。memo state をキーから除くことは現在承認しません。

Result は同一 Snapshot の original edge 順序と caller/site/target/base、全 four contributions、-1 neutral、0 unknown、support/poison/diagnostics/logical charge を持ちます。繰返し target を集合化せず、現在の preaggregate または fresh neutral state に ordered replay します。完全 Transition は Compute に拘束します。同じ ResultCID は downstream の完全 read footprint と authority が変わらない証明を代替しません。

新しい有限 shadow は3 subject ×5条件です。独立した二つの M 上で、元の問い合わせを固定した C0 設定のまま評価し、work・preaggregate・control・memo を各1項目だけ変えます。mode や provenance 不明の valid1 は拒否を正直に記録します。異なる出力・charge・trap・support・poison を見つけたら、該当キー除外仮説を停止します。陰性を Result 同一へ読み替えません。native 原型は未実装で、17 proposed calls は新 source/resource review 後の別 GO が必要です。

二つの M だけで128 MiBの scalar payload、追加 fresh replay copy はさらに64 MiBです。per-side diagnostic ledger は536,870,912、pairの合計上限は1,073,741,824と明示します。これは VM fuel、hardware命令数、時間ではありません。コピーの zero/read/write、trace、codec/hash、resolve/replay/publication/cleanup、他の vector/string/pair pools と nonrollback fuel を resource admission で扱います。

false hit は domain/schema/evaluator/rules/Snapshot/subject/mode/bounds/型・effect・ABI・read cell・edge順序・support/poison の一変異で拒否します。unknown input は元の問い合わせへ fallback し、resource/fuel が足りない場合も元の deterministic first failure を保存します。partial write は invalid に戻し、valid-last が完了するまで共有可能な receipt を出しません。persistent importer の信頼や C2 lookup は実装対象外です。

次の計測は original19 の問い合わせを変更せず、同一対象・同一 Snapshot の actual query を数えます。完全 request の重複と、証明済み role 分離後の semantic 重複を別集計します。旧 serialization control や four-bound 一致を hit に数えません。seal、hash、lookup、direct、replay、失敗経路の費用を含め、overhead が節約を上回る、実際の重複がない、証拠が partial の場合は speed 仮説を停止します。

full19・3世代 selfbuild の byte/export parity、171 functional、同じ C0/local memo 設定、quiet な現在の C 比較が後続 gate です。CID による compiler analysis の節約と、emitter が変えた runtime speed は別に報告します。公式正規化なしの custom C 比較を official score としません。
