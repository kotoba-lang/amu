# 符号付きliteral +2除算のnative候補

元19本でC以上という目標は未達。新しい `q2-feature` は既定OFFの隔離実験で、現在のEXTR計測cohortは変更していない。IPLD/CIDによる速度効果の主張でもない。

`quot x 2` を `ADD d,x,x LSR#63; ASR d,d,#1; MOVZ x17,#2` へ生成する。xが負なら1を加えてから算術右シフトするので、全i64で0方向への除算と一致し、MINでも加算はoverflowしない。最後のMOVZで元のscratch x17=2を復元し、3命令ともNZCVを変えない。x/d17と31は元の経路、x/d16とd==xは許可する。変更はinteger literal+2の分岐と3 helperに限定し、protect/ldt/fin/cache・元SIRのfuel経路を保持する。これらの実行時観測は後続検証が必要。

2語だけの置換はscratch x17を変えるため、継続コードの条件確認が必要だった。静的に2箇所を対応付けたが、[postpass案](evidence/coscientist-quotient-two-20261008/postpass-hold.json)はFIXに記録されないADRとinline tableを命令として誤認する恐れがありHOLDのまま。3語案は直接emitterで生成し、後続領域の全走査を避ける。

3語案は元の2語よりCODEが1語増える。ONの容量境界で以前通ったcompileが拒否される可能性と、label・offset・literal配置の変更を明示した新しい実験資源契約である。旧CODE容量・途中状態・ON出力バイトの同等性は主張しない。dirty MMERRは元の経路へ戻す。既定OFF、4 source variantの完全逆差分を確認し、[独立sourceレビュー](evidence/coscientist-quotient-two-20261008/source-review.json)は12,009符号付きモデルケースと900組のレジスタ符号化を確認した。

[有限native自己再ビルド](evidence/coscientist-quotient-two-20261008/build-report.json)はOFF1世代とON4世代、compile/extract計10回を実行し、すべて終了コード0・stderr空・timeoutなしで閉じた。旧76e9 producerで作るON1はbootstrapとして事前登録し、ON2・3・4の3世代全バイト一致を要求した。実際にON1は947,896 B、ON2〜4は947,944 Bで48 B異なり、後者のnative SHA-256は `65bccc45e9eb96ee9beddf8b1ce97c755461b37f76bdb2838bff19a5b0a02b3f`、KSEEDは `56444d10e8e44c034e49a8ee8177b60df00b865a312fbd3a3eaf3a69913591e3` で一致する。コンパイラ自身のsourceにもliteral2除算があるため、初代を後から失敗の計数から除いたものではない。

[独立raw監査](evidence/coscientist-quotient-two-20261008/build-actual-review.json)は10 argv・producer chain・root GO・review・入力・raw・全header/sole main0 payloadを照合した。[全内容packet](evidence/coscientist-quotient-two-20261008/content.tgz)は2,438,495 B、SHA-256 `3d651820dfb53f3f7f58d4d3e2190533ba2b7ce7409aaf2a13925d3fe393f0a7`、55 regular member・展開9,654,019 B。70元パスを54 content memberへ重複排除し、embedded manifestを含む。[内容監査](evidence/coscientist-quotient-two-20261008/packet-review.json)も抽出・実行なしで全件照合した。元の絶対パスとloader/producerを保存する内容証拠で、portable再実行やsource-to-loader由来証明ではない。

固定点は速度の証拠ではない。native深い状態・容量境界、実際に発行したCODEの符号付き入力実行、fuel・arena観測、元19本のOFF identity/ON machine比較と機能、同じ静穏hostでのCとの速度比較はまだ必要である。現在のEXTR cohort・製品baseline・bin entryを切り替えず、C以上・公式スコア・製品採用を未達のまま保持する。

## 成分試験V1の停止

Q2成分試験は上限14回で新規登録したが、[独立実監査](evidence/coscientist-quotient-two-20261008/state-v1-failure/independent-report.json)のとおり、compile・extract成功後の最初のprobeが終了コード91で停止した。全3回はtimeoutなし・stderr空で閉じた。raw stdoutは `PIPELINE 0 8 2`、allocation receipt、`END 0 0` の3行であり、必須のROOT／FN／SIR／STATE記録がない。想定したsiteの捕捉に入っていないので、容量境界・full M/G状態・算術・codegenのPASSにも反例にも判定しない。残る11ケースは未実行、元の試験は再実行しない。

コンパイラ自己再ビルド10回と、この失敗3回を区別して保存する。次は通常のcheck・refinement・lower後のSIR／FRECを観測する有限診断を別に登録し、実際の形を確認してから新しい成分試験をレビューする。観測のためのguardを広げて旧試験の成功と呼ばない。

[失敗の全内容packet](evidence/coscientist-quotient-two-20261008/state-v1-failure/content.tgz)は1,685,896 B、SHA-256 `9bdfbde1cc2538cceed706c637b190bc6b9fd94da508a0c18c8c4f6bb49dc3af`、36 regular members・39元パス・展開6,578,685 B。凍結ソース・入力producer／loader・有限GO・3回のraw・生成harness・独立失敗監査を保存する。

[失敗packetの独立内容監査](evidence/coscientist-quotient-two-20261008/state-v1-failure/independent-packet-report.json)は36 member・39元パスと独立実監査の37依存を照合した。失敗結果は上書きせず、後続診断と区別して保持する。

## 通常loweringの観測V1

別登録のcompile・extract・observe計3回はすべて終了コード0、stderr空、timeoutなしで閉じた。[独立実監査](evidence/coscientist-quotient-two-20261008/observation-v1/independent-report.json)は通常のcheck・refinement・lower、8 SIR行、2個の全16フィールドFREC、実際に訪問した7命令直前のframe／descriptorを照合した。失敗の原因は試験側の局所slot仮定だった。SIR3のLGETはtemp0へslot1を読み、V1のsite predicateはslot0を要求していた。隣接CONST2・BINquotと命令5への訪問は一致する。これは最適化の算術失敗ではなく、成分試験の捕捉条件の不一致である。

[観測の全内容packet](evidence/coscientist-quotient-two-20261008/observation-v1/content.tgz)は1,685,153 B、SHA-256 `d57c51860baebe9e5f13e1de8cef6812b99cffb949f42abff6494a432c0764da`、46 regular members・49元パス・展開6,592,180 B。自己再ビルド10回、失敗成分試験3回、観測3回の累計16回を区別して保持する。新しい成分試験はslot1の実観測に合わせ、独立source reviewと別の有限GOを必要とする。旧失敗・残り11ケースを再実行しない。成分状態、生成CODE実行、物理register／NZCV、fuel／arena、性能、製品採用の成功はこの観測から主張しない。

[観測packetの独立内容監査](evidence/coscientist-quotient-two-20261008/observation-v1/independent-packet-report.json)は全46 member・49元パス・47実監査依存を照合した。
