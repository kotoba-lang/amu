# Compute結果の再利用と下流停止：次の検証契約

ユーザーのComputeCID／ResultCID案を、[現行の再利用契約](coscientist-compute-canonical-next-20261008.md)と[独立gap監査](evidence/coscientist-masked32-clone-20261008/compute-replay-gap-audit-v1/source/AUDIT.md)へ統合する。これは実装・検証を進めるための受入条件であり、再利用や高速化の資格ではない。C2はOFF、キー除外は空、新しい解析省略は0を維持する。

[独立SOURCEレビューの13対照](evidence/coscientist-masked32-clone-20261008/compute-result-consumer-review-v1/review/CONTRACT.md)も保存した。受入条件の確認にとどまり、完全なread閉包、owned Result、下流停止、native負例の実拒否、費用計測は未資格である。

## 三つの識別と検証境界

ComputeCIDは定義・依存・入力状態・解析器・規則・工程・ABI・effect／trap・資源の計算要求を識別する。ResultCIDは問い合わせが所有する意味上の答えと、順序・重複・arity・-1／0を保存した呼び出し辺の寄与を識別する。現在の集計へのmerge、callerのsupport低下／poison処理、現在の権限・予算・論理消費はTransitionReceiptで検査する。

Resultのpayloadへ要求CIDや可変global scratchを混ぜない。ただし結果の意味に必要な情報は、所有者とread-roleを検証する前に除外しない。異なる要求から同じ結果を得ても、現在のadmissionとtransitionを実行する。内部解析workの減少と、言語上観測可能なfuel／課金の保存は別に判定する。

## ResultCID一致だけで下流を止めない

下流consumerが読むものを版付きの契約として閉じる必要がある。型、effect、interface、診断、依存辺の存在・順序、予算状態、権限、集計などをconsumerが直接読むなら、その変化は別の依存として失効を伝える。Answerが同じでも、それらの変化を消してはいけない。

同じAnswerに対して現在のtarget集計が異なる場合も、保存した寄与を元の順序とmerge規則で再適用する。再適用後のconsumer可視状態まで一致した場合に限り、その依存辺からの追加再解析を止める候補にする。これは現在の集計・副作用まで結果CIDに含める設計を要求するものではなく、純粋なAnswerと現在状態のTransitionを別に検証する条件である。

循環する依存では、一つのAnswer一致をSCC全体の固定点と扱わない。pending worklist、support低下、poison、外部入力の更新を処理し、宣言した全consumer入力が安定したことを確認する。順序変更で結果が変わる処理を可換と仮定しない。digest衝突への対応・保存内容の検証もbinding／import契約に従う。

| 対照 | 必要な判定 | 現時点 |
| --- | --- | --- |
| 入力変更後に完全なowned Answerが同じ | 現在transitionを再実行し、consumer入力が同じなら追加再解析停止の候補 | 未資格 |
| Answerは同じ、target集計／caller poisonが異なる | 更新を保存し、影響するconsumerを失効させる | 未資格 |
| ABI・規則・effect・trap・依存・予算の一項目変更 | 実際のnative lookup／admissionが旧bindingを拒否する | 全項目の実拒否は未資格 |
| 同じ寄与値だが辺順序・重複・arity・ownerが異なる | 誤ったAnswer／transitionを拒否する | 次のnative負例 |
| unsupported・trap・予算不足・途中valid公開 | 成功bindingへ登録せず、再適用もしない | 完全なnative境界は未資格 |
| SCCの一つの結果だけ一致、pending更新あり | 固定点／全下流停止と判定しない | 未資格 |

## 実装の順序

[SOURCEの照合](evidence/coscientist-masked32-clone-20261008/compute-owned-answer-lineage-v1/source/CONTRACT.md)で、監査済みcurrent16／current41には従来の`vw-*` stage6 shape memo経路がなく、旧`41-result.kotoba`は別の拡張解析ソースであることが見つかった。rootも4凍結ファイル・27入力の実バイトhashと全16moduleの関数定義を照合した。current7618をbuilderとして使うことと、その現在の製品解析を観測することを区別する。存在しない経路へobserverを挿入したとは報告しない。旧解析を診断subjectとして使う場合は、その全ソース・変更・builderを別の版として登録し、旧結果を現在の製品へ移さない。

観測対象の解析variantを確定した後、元CRC32／SLREのowned summary、全辺のtarget更新前後、caller support低下／poisonを記録する。既存hitのsummaryに所有権の証拠がなければ`SUMMARY_NOT_OWNED`とし、global scratchから答えを作らない。新observerのcompile／extractと元2本のcompile／extract、最大6呼出はSOURCE・資源契約・独立レビューを確定した後の別試験である。既存shadow／元19本の観測を再実行したことにしない。

その後、実native importer／admissionへ失効・owner・辺・公開・予算の負例を渡す。cacheなし／shadow／replayのAnswerと全transitionが一致してから、seal・encode・hash・lookup・検証・再適用・公開・失敗経路を含むcold／warm実費用を測る。consumer停止はその先の独立した仮説とする。

解析時間の改善と、生成コードのEmbench実行時間は別の測定である。局所graph rewriteの型・effect・trap条件と、cache公開／失効／再適用の状態遷移も別に検証する。有限対照を一般の定理証明やモデル検査と呼ばない。最終性能条件は元19本、selfhost固定点、同一quiet hostでのCとの比較を維持する。
