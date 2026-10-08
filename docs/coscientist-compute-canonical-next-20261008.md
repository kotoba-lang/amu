# ComputeCID／ResultCIDを解析の再利用へ適用する次段階

ユーザーの提案を[既存の設計](coscientist-compute-addressed-analysis-20261007.md)と[C1bのnative前提試験](coscientist-compute-c1b-native-20261008.md)へ統合する。ComputeCIDは計算前に確定できる要求のcontent address、ResultCIDは計算後の結果と再適用する状態更新のcontent addressである。対応の正しさはCIDだけから導けない。最初は直接計算を毎回実行して照合するshadow診断とし、解析を省略するC2はOFFのままにする。

要求には、正確な同一snapshotの型付き対象・依存・解析器・規則・ABI・整数／effect／trap・資源契約に加え、4つの入口bound、呼び出し先の既存集計値、support／poison、work／admission状態を含める。既存集計値は更新と消費量へ影響するので、boundだけをキーにして完全性を主張しない。contextは一度封じ、queryごとの全メモリhashを避ける。ただし全61定義の参照閉包と11 readerについて、immutable入力、query入力、reset-before-read scratch、出力の役割と所有期間を閉じる必要がある。未分類readや外部writer／aliasはHOLDとする。

結果には意味上の答え、元の順序を保つ全呼び出し辺のbound寄与、support／poison、診断・trap／effect状態、更新前提、論理的な解析消費量を封じる。同じtargetでも別の辺は統合せず、-1と0を区別する。独立したfresh集計へのreplayと、保存した既存集計へのreplayをそれぞれ直接計算と比較する。拒否・途中計算・予算切れは成功したCompute→Result対応として公開しない。

schema・規則・ABI・bound・既存集計・依存・型・effect・trap・予算を一つずつ変更して、ComputeCIDの変更または拒否を確認する。結果の辺欠落／並べ替え、poison・診断・消費量の改変、別snapshotの参照、途中書込みを拒否し、有効bitは全検証の最後にだけ公開する。旧nativeの有限3ケース通過は、この完全なcanonical payloadや共有cacheの証明ではない。

次のSOURCE実装はstrict canonical encoder／decoder、同一snapshotの型付きresolver、read-role／所有期間の検査、ordered replay、valid-last取引を対象にする。8193個のLABEL indexを省略せず、符号化領域の増分を明記し、元の解析work上限268,435,456と診断scalar上限536,870,912は維持する。seal・hash・resolve・replay・read検証の費用も計上し、超過は拒否する。

これはコンパイル時の解析再利用の検証である。Embenchの生成コード実行時間への効果、canonical shape C1、C2、跨snapshot／process共有は未認定。将来のResultCID一致による下流再解析の停止も、query依存と結果更新の完全性を確認した別段階で検証する。生成コードの最適化は、元19本の意味保存・selfhost固定点・同一quiet hostのC比較で別に判定する。
