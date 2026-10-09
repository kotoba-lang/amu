# 計算要求・結果・再適用の証跡を分ける検証

ユーザーのComputeCID／ResultCID案を、[既存のconsumer契約](coscientist-compute-result-consumers-20261008.md)へ継続して適用する。ComputeCIDは正規化した計算要求のcontent addressであり、ResultCIDは所有した意味結果と順序付き寄与のcontent addressである。対応する結果の正しさ、現在状態への再適用、現在の権限・論理消費は、別のTransitionReceiptで検査する。

要求には解析実装、定義と推移的依存、全read-setのsnapshot、入力bound・alias・effect、規則と工程、ターゲット・ABI・数値／trap意味、資源契約を含める。可変入力は「同じオブジェクト」という理由で再利用せず、読み取り期間と更新検知を検証する。永続化には正規符号化とschema・domainを固定する。JSON/SHAの診断モデルはIPLD実装の証拠ではない。

再適用は同じ辺を二重加算しない。既存shape案の-1を中立とするminは数値上冪等だが、poison、診断、論理消費の冪等性まで保証しない。入力変更時の寄与撤回もmin単独ではできない。辺のowner・revisionを追跡し、変更した辺の古い寄与を置換して現在の全寄与から再集約する方式、またはepochを進めて全寄与を再構築する方式を、実解析の更新規則に合わせて検証する。順序・重複・arity・-1／0の区別は維持する。

ResultCID一致による下流停止は、consumerが読む状態、support／poison、循環依存の構成員、pending更新、worklist revisionまで安定した場合に限る。途中計算・途中書込み・予算切れ・trap・拒否を成功bindingとして公開しない。内部探索上限と観測可能なfuel・課金は別に扱う。

現在のG4 selfhost候補は、[元19本のcompile／extract 38回](evidence/coscientist-masked32-clone-20261008/current-g4-x8-original19-compile38-v1/snapshot.json)を完了し、全成果物のソース・export・完全payloadを独立監査した。これは生成物の同一性の証拠であり、全19本の実行や性能の証拠ではない。

その後の[95条件・190回の比較登録と独立失敗監査](evidence/coscientist-masked32-clone-20261008/current-g4-x8-runtime190-stopped6-v1/snapshot.json)は、6回目の`aha-mont64-ON-n2`で停止した。ゲストは終了コード0、保存rawの結果・fuel・17 arenaは隣接OFFと一致したが、プロセス帰属確認前の`member-getpgid` ESRCHを検証器が拒否した。5回を採用、完全な採用済み比較は2組、残り184回は未実行である。失敗実行の再試行や、raw一致を根拠にした成功への書換えは行わない。全6子プロセスの終了は確認済みである。

この失敗も再利用設計に使う。同じ意味結果を得ても、現在のTransitionが成功したとは推定しない。失敗receiptは保存し、成功ComputeCID→ResultCID bindingと分ける。現在のC2はOFF、キー除外は空、新しい解析省略は0である。

[追加契約と有限診断モデルV2](evidence/coscientist-masked32-clone-20261008/compute-replay-owned-ledger-contract-v2/source/CONTRACT.md)は、29対照・27拒否試験を通過し、rootが独立して同じ結果を再現した。辺の置換・古いminの撤回、順序とowner、fresh fuel消費、部分公開、SCC未収束、強制hash衝突時の完全key比較を検査した。旧V1で保存ResultCIDとの照合欠落を発見したため、その版と旧レビューを保存し、V2ではResultCIDの再計算・結果改変・不完全binding・欠落CIDの拒否を追加した。これはJSON/SHAによる説明用モデルで、実解析のread／writer閉包、native importer、IPLD符号化、永続化の原子性を証明しない。

次の解析実験はcacheなし／shadow／replayを同一snapshotで比較し、Answer・辺寄与・再集約・poison・診断・trap・論理消費を照合する。要求fieldの失効、重複再適用、寄与撤回、部分公開、SCC未収束の負例を加える。その後に封印・符号化・hash・lookup・検証・replay・失効・missを含むcold／warmの全体解析時間を測る。解析時間の改善と生成コードのEmbench実行時間は別々に判定する。元19本、自己再ビルド固定点、同じquiet hostでのC比較という最終条件を維持する。C以上の性能、公式Embenchスコア、CIDの性能効果は未達・未測定である。
