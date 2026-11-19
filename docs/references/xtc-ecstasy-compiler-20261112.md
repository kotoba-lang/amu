# XTC / Ecstasy / XVM を Kotoba・Amu compiler の参考にする

調査日: 2026-11-12 JST
追跡: [KOTOBA-938](https://linear.app/kotobalabs/issue/KOTOBA-938)
位置づけ: 外部設計・ソースの読解メモ。採用 ADR、性能測定、実行による適合証跡ではない。

XTC は Ecstasy 言語と XVM のプロジェクト。入口は [xtclang.org](https://xtclang.org/)、
実装は [xtclang/xvm](https://github.com/xtclang/xvm)。
Amu への参考としては、**compiler の段階境界、依存情報を持つモジュール、検証の責任分担、
外部 resource の明示的な注入**を優先する。XVM への backend 追加や Java / Gradle の導入を提案する資料ではない。

## 調査の固定点と限界

- XVM のソース参照 revision:
  [856fa585e4183313ea55a84a7f935365658a524f](https://github.com/xtclang/xvm/tree/856fa585e4183313ea55a84a7f935365658a524f)。
  調査時の GitHub API `commits/HEAD` から取得。以下のソースリンクはこの SHA に固定した。
- Amu の比較 revision:
  [aa6bd425d6120d27c106e3053b4919f79aa1f0e9](https://github.com/kotoba-lang/amu/tree/aa6bd425d6120d27c106e3053b4919f79aa1f0e9)。
  ソース上の接点を確認した範囲であり、公開 binary や deployment の資格を確認したものではない。
- 公式ブログは 2019 年の設計説明として読む。現在の実装保証とは区別する。
- 今回取得したものは HTML、GitHub の tree/commit metadata と参照用テキストソースのみ。
  XDK、JDK、Gradle、XVM runtime はインストール・ビルド・実行していない。
  速度、メモリ使用量、完全 selfhost、sandbox の耐攻撃性は未検証。

## 読む順序と一次資料

| 順 | 資料 | 読みどころ / 証拠の種類 |
|---|---|---|
| 1 | [公式サイト](https://xtclang.org/) | 言語、設計ブログ、repository への入口 |
| 2 | [README（固定 revision）](https://github.com/xtclang/xvm/blob/856fa585e4183313ea55a84a7f935365658a524f/README.md) | portable IR、toolchain、project layout。概要説明であり実行証明ではない |
| 3 | [Compiler.java](https://github.com/xtclang/xvm/blob/856fa585e4183313ea55a84a7f935365658a524f/javatools/src/main/java/org/xvm/compiler/Compiler.java#L100-L310) | module 構造生成から resolve / validate / emit までの実装 |
| 4 | [StageMgr.java](https://github.com/xtclang/xvm/blob/856fa585e4183313ea55a84a7f935365658a524f/javatools/src/main/java/org/xvm/compiler/ast/StageMgr.java) | AST stage、再訪問、最終試行の扱い |
| 5 | [FileStructure.java](https://github.com/xtclang/xvm/blob/856fa585e4183313ea55a84a7f935365658a524f/javatools/src/main/java/org/xvm/asm/FileStructure.java) / [ModuleStructure.java](https://github.com/xtclang/xvm/blob/856fa585e4183313ea55a84a7f935365658a524f/javatools/src/main/java/org/xvm/asm/ModuleStructure.java) | file format、module link、dependency fingerprint / version |
| 6 | [ConstantPool.java](https://github.com/xtclang/xvm/blob/856fa585e4183313ea55a84a7f935365658a524f/javatools/src/main/java/org/xvm/asm/ConstantPool.java#L155-L205) | 定数・型の登録と共有。DefCID と同一視しない |
| 7 | [Ecstasy modules（2019-04-08）](https://xtclang.blogspot.com/2019/04/ecstasy-modules.html) | compilation / deployment 単位、依存 fingerprint、link-time conditionality の設計 |
| 8 | [Type System（2019-06-17）](https://xtclang.blogspot.com/2019/06/an-introduction-to-ecstasy-type-system.html) | reified generics、immutability、compile / link / runtime の型検証分担 |
| 9 | [Security Model（2019-04-14）](https://xtclang.blogspot.com/2019/04/on-god-turtles-balloons-and-sandboxes.html) / [runtime Container.java](https://github.com/xtclang/xvm/blob/856fa585e4183313ea55a84a7f935365658a524f/javatools/src/main/java/org/xvm/runtime/Container.java#L237-L249) | resource injection の設計と API 接点 |
| 10 | [Ecstasy Compiler.x](https://github.com/xtclang/xvm/blob/856fa585e4183313ea55a84a7f935365658a524f/lib_ecstasy/src/main/x/ecstasy/lang/src/Compiler.x) | Ecstasy 側の compiler interface。ファイルの存在だけでは selfhost 証明にならない |

## Compiler の実装から参考にする点

### 1. 各段階の入出力と未解決状態を明示する

`Compiler.java` の入口はすでに module AST を受け取っている。
その後は構造登録、module link、名前解決、式検証、code emission の順に進む。
`generateCode` は `Validated` 到達を要求し、重大なエラーがない場合に定数を再登録して
module 全体を validate する。これを parse からの全 frontend 実装と取り違えない。

`StageMgr` は AST の段階処理を振り分け、未解決 node の再訪問を扱う。
`markLastAttempt` / `logDeferredAsErrors` は、保留を完了扱いせず診断に変える接点になる。

**Amu への検討案:** 既存の直列 pipeline を置き換えず、段階ごとの失敗と未解決依存を
診断・再利用条件としてどこまで分離できるか読む。再訪問の導入が必要なら、
回数・作業量・進捗判定に上限を持たせ、循環を無制限に再試行しない。

比較先:
[seed/90-drv.kotoba](../../seed/90-drv.kotoba) の `drv-c0..drv-c8`
（比較 revision の 404–436 行）に lex / read / names / check / lower 以降の接続がある。
[seed/21-check.kotoba](../../seed/21-check.kotoba) の `ck-run` と合わせて読む。

### 2. 配布形式に依存関係と検査対象を残す

`FileStructure` は magic / format version の読み取りと module linking を持ち、
`ModuleStructure` は外部 module の fingerprint と version 条件を表現する。
公式 module 記事では、依存 API の fingerprint を保持してロード時に依存閉包を解決する設計を説明している。

**Amu への検討案:** 再利用 object の metadata に「何を使ったか」と「何と互換か」を残し、
link 時に target / ABI / dependency interface / resource contract を照合する観点で参照する。
XTC の fingerprint を暗号学的 content hash、署名、Kotoba の Definition CID と同一視しない。
optional / version selection を採用するなら、選択後の閉包を lock と identity に結び付け、
未宣言の自動取得・fallback を許さない。

比較先:
[seed/07-definition-objects.kotoba](../../seed/07-definition-objects.kotoba)、
[seed/09-definition-build.kotoba](../../seed/09-definition-build.kotoba)、
[Definition CID 文書](../definition-cids-native.md)。
ソースに機構があることと、全 target の再利用が qualified であることは別である。

### 3. 定数の共有と永続 identity を分ける

`ConstantPool.register` は typedef の解決後、既存の定数を検索して共有する。
未解決情報や別 pool と共有できない型は、その場で通常の登録対象にしない分岐がある。

**Amu への検討案:** 型・定数 descriptor の重複削減や比較コストの検討に使う。
pool 内の番号・object identity・登録順を永続 cache key に使わず、
DefCID の canonical payload、compiler/target を含む build identity と切り分ける。
共有化で意味や割当上限を変えないかを測る。

比較先:
[seed/04-definition-cid.kotoba](../../seed/04-definition-cid.kotoba)、
[seed/05-checked-definition.kotoba](../../seed/05-checked-definition.kotoba)。

### 4. compile / link / runtime ごとの検証責任を列挙する

型システム記事は reified generics、推移的に閉じた型体系と段階ごとの検証を説明する。
これは「compiler が通れば runtime validation が不要」という設計ではない。
今回のソース確認だけでは全 instruction の verifier の健全性を認定できない。

**Amu への検討案:** 各境界で失われる情報、再検査する条件、実行まで残る制約を表にする。
特に外部値・capability return の検証、ABI / layout、fuel / arena 上限を
型検査済みという一語でまとめない。XTC の型体系全体の移植は別の設計判断になる。

比較先:
[seed/21-check.kotoba](../../seed/21-check.kotoba)、
[seed/30-lower.kotoba](../../seed/30-lower.kotoba)、
[Component Model baseline](../component-model-baseline.md)。
最後の文書は設計・過去の実装説明として参照し、現行 native route の対応証明には使わない。

### 5. resource injection を capability 境界の比較に使う

security 記事は外部 resource を container の外から注入する設計を説明する。
実装上の接点として `Container.getInjectable(frame, name, type, opts)` がある。
この抽象 API の存在だけで各 concrete provider の隔離や同意処理が確認できたとはしない。

**Amu / Kotoba への検討案:** 外部資源を暗黙の ambient authority にしないという観点を比較する。
ただし DI の成功は権限付与・操作同意ではない。browser end-user app では既存の
`kotoba.app.client-runtime.v1` と正本 broker、操作ごとの新鮮な同意を引き続き必要とする。
compiler metadata や module load が実行権限を新たに与えてはならない。

## 取り込まない前提と未検証

- Java / JVM / Gradle を Amu の native build / gate / runtime の依存には追加しない。
  XTC の実装を読むことと、その実装基盤を採用することを分ける。
- Ecstasy 側の `Compiler.x` は今回確認した範囲では interface。
  Java compiler が存在するため「完全 selfhost 済み」とは記載しない。
- portable IR という位置づけから、native AOT の速さ、Wasm 対応、Amu との ABI 互換性を推定しない。
- link-time conditionality は有用な設計例だが、全組合せの現行実装・検証量は今回未確認。
- 公式 security 記事自体も設計だけでは安全性を保証しないと説明している。
  container の語を OS process / VM 隔離の証拠にしない。

## 次に比較実験するなら

以下は候補であり、今回の実装タスクや採用決定ではない。

| 優先 | 比較対象 | 正常系 | 負の対照 / 判定材料 |
|---|---|---|---|
| 1 | 依存 interface と link metadata | 同一 source / lock / target で同一結果 | 依存の型・ABI・lock の変更、欠落・破損 object で誤再利用しない |
| 2 | phase 診断と未解決依存 | 前方参照が宣言した規則で解決 | 未定義名・循環・上限超過を有限の手順で拒否し、emit しない |
| 3 | 定数 / 型の共有 | 共有前後で値・出力・拒否結果が一致 | 同値でない型の誤共有と arena 上限の変化を検出する |

性能比較をする場合は同一 workload、target、compiler revision、host、入力上限を固定し、
cold / warm、実行時間、peak memory、生成物の大きさを別々に記録する。
まず Amu の native route のみで検証し、XTC を実行比較に使うなら別途その toolchain と入力を
固定した測定証跡を作る。今回の読解を実測値として扱わない。

## 比較中に見つけた既存文書とコードの不一致

比較 revision では [native-incremental-build.md](../native-incremental-build.md) の
73 行「not yet in FULL-MANIFEST」、86 行「remain outside FULL-MANIFEST」と、
[AGENTS.md](../../AGENTS.md) の 428 行・466 行「remain outside FULL-MANIFEST」が、
[seed/FULL-MANIFEST](../../seed/FULL-MANIFEST) の 21–30 行にある
04 / 05 / 06 / 07 / 08 / 09 系 module の列挙と一致していない。

本メモは manifest を実態として扱う。これは manifest への収録確認であり、
各機構の全機能・全 target の qualification を示さない。
既存の正本・説明文書はこの調査では変更していない。更新範囲は別途 owner 判断とする。
