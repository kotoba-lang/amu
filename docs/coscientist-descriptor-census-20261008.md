# 元19本のdescriptor writer仮説：候補0件で停止

同じlocalのdescriptorを、既知のin-place mask writerをまたいで保持できるかを事前登録した。読み取り・writer・次の読み取りが同じfunction／正のslotに属し、物理register、alias、寿命、effect、fuel、制御条件を満たすことが必要である。字面の出現数から適用可能性を推定しない。

SOURCE V5と独立レビュー2件を固定した後、observerのcompile／extract2回と、変更していない元19本のcompile／extract38回、計40子プロセスを1回の有限runで実行した。全40回はrc0・空stderrで終了し、19本の全KSEED・native・exportが元と一致した。チェック済みSIR／FREC／FIX／LIT、訪問・skip・emission範囲、CODE／LABEL／layoutを保存した。guest実行・タイミングは実施していない。

mode1はmatmult-intの34 stepだけで、descriptor読み取り2件、writer0件だった。2読み取りは同じfunction／slot1だが、間にwriterがない。他18本は該当mode1読み取り・writerとも0件で、登録したjoin候補は0件である。[独立実監査](evidence/coscientist-descriptor-census-20261008/census-v5/independent-report.json)の判定どおり、この仮説は `STOP_HYPOTHESIS_ZERO_ACTUAL_JOINS` とする。条件を緩めて成功数を作らず、別の仮説を検討する。

実行前のclassifierレビューでは、bit22だけによるload判定がsigned-byte loadのRt更新を落とす問題を見つけた。V4をHOLDとして保持し、V5でsize／opcに沿った保守的なwrite分類と2048組の対照を追加した。ヘッダー・例外時の子プロセス回収の旧HOLDも上書きしていない。

[全内容packet](evidence/coscientist-descriptor-census-20261008/census-v5/content.tgz)はSHA-256 `88fe89ea9e2e0e543701c2de7b1eafdd033b422f3c6647fd589e4c8447e16db9`、4,032,832 B・227 member・393元パス・展開17,437,913 Bである。全入力、SOURCE／レビュー／GO、raw、生成成果物と実監査を封じる。indirect BLR／returnの全target集合は閉じておらず、この診断のanchor判定を最適化の許可と扱わない。最適化採用・性能改善・公式Embenchスコア・C以上の性能は認定しない。

[独立内容監査](evidence/coscientist-descriptor-census-20261008/census-v5/independent-packet-report.json)は全primary依存と393元パス、安全な227 member、余分なmemberがないことと、40回／19本／候補0件の停止境界を確認した。実監査作者controlsの内容監査への参加、SOURCE作者native_controls、root実行・packet構築の分担を明記した。展開・native再実行は行っていない。
