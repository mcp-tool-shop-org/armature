<p align="center">
  <a href="README.md">English</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/armature/readme.png" alt="armature — you block the shot, the model shoots it" width="820">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/armature/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/armature/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/armature/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

#申し訳ありませんが、翻訳するテキストが提供されていません

あなたはシュートを阻止します。モデルがそれを撮影します。

**[ランディングページとハンドブックはこちら →](https://mcp-tool-shop-org.github.io/armature/)**

ビデオモデルは、他のレンダラーでは再現できない動き、光、そして生命感を表現できます。画面に誰がいて、どこに立っているのかを正確に伝えることはできません。しかし、アームatureを使用することで、標準的なキャラクターメッシュをヘッドレスのBlenderで配置し、アニメーションさせることができます。これにより、各フレームごとにビデオモデルが従うべき「制御シーケンス」としてレンダリングされ、AIによって生成されたビデオでは、位置とポーズが常に把握できる一貫した主要なキャラクターを登場させることが可能になります。

**アームチャーは、画像ではなくGLB形式の3Dモデルを使用して、画像を動画に変換する機能です。** すべての空間的な要素が作成され、その上に3Dモデルが配置されて動きを与えます。最終的な成果物は映像であり、映画、カットシーン、キャラクターのポーズや動きなど、あらゆるショットが含まれます。ゲームはその映像を利用する手段の一つであり、決してこのツールの限界ではありません。

ブレンダーでキャラクターを配置します。コントロールシーケンスをレンダリングし、ビデオモデルにその上に生命の息吹を描き込ませます。構造はあなたが持つジオメトリから生まれ、生命はモデルから生まれます。そして、アイデンティティとは、プロンプトや参照スタックに組み込まれた、名前とバージョンが明確に定義されたものです。それは決して偶然の幸運によって生まれたものではありません。

## インストール

```bash
pip install armature-previz
```

```bash
npm install -g @mcptoolshop/armature   # the same command, as a launcher
```

```bash
armature check
```

インストール可能なパッケージは**`armature_core`**です。これには、ゲート、フレームワーク、およびターンアラウンドソルバー、ショット仕様契約、チャネル数学、およびペイロードビルダーが含まれます。これらのすべては、プレーンなCPythonの下でインポートされます。これにより、Blenderがなくてもテストやパッケージ化が可能になります。

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**レンダリングスクリプトはコンソールエントリポイントではありません。これは意図的なものです。**
`render_turnaround.py`、`stage_render.py`およびそれらの関連モジュールは、**Blender独自のインタープリター内**で実行されます。Pythonのコンソールスクリプトから`bpy`をインポートすることはできず、最初の行でエラーが発生します。したがって、それを配布しても、パッケージが約束を守ることはできません。

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

これらはリポジトリ内に留まり、そこで動作する呼び出しは記述されたとおりです。
`armature_core.blender_scene`は、`bpy`をインポートする単一のモジュールであり、`armature check`はそれを欠陥としてではなく、`needs-blender`として報告します。

npmパッケージは**ランチャーであり、移植ではありません**。別の言語でしきい値を再実装すると、しきい値が変動するため、真実を保持するPythonに転送し、何らかのものをインストールする代わりに、明確かつ大きなエラーメッセージを表示します。

---

## 状態：この仮説は、製品レベルで検証されます

**2026年8月10日に設立されました。** 13件の実験が終了し、論文は*テスト中*から**製品レベルで測定可能**へと移行しました。キャラクターは自身のリグによって駆動され、自由に画面上で踊ります。手作業で作られた世界は、最後のフレームまで2つのシード（E12）で維持されます。また、**アイデンティティは、作成された参照のみを供給される、ホストされ、人間がトレーニングした階層で生き残ります**（E13）。これらはすべて、ディレクターの目で評価されます。設立時の監査は[docs/audit-first-arc.md](docs/audit-first-arc.md)にあります。2026年8月12日以降は、学習モノリポジトリとして運用されており、実験によってパスが証明され、慣性によって特定のルートが標準となることはありません（CLAUDE.md）。

| | |
|---|---|
| 実験 | **E01〜E14は終了しました**（E05は虚偽の前提に基づいて中止されました）。コントロールアーク（E01〜E06）、リグの修理とスケルトンの承認（E07）、**最初のレンダリングされたショット**（E08）、クリーンチェーンベースライン（E09）、高密度化された駆動方式の採用（E10）、制御なしのルート、3つの段階を経て明確な失敗に至る（E11）、**自由なルートが世界を獲得し、6.0 / uni_pcベースラインに到達する**（E12）、**合成されたルートがその質問に答える**（E13 — 実行され、ゼロのコストで停止し、サポートアークによって修復され、再武装され、実行され、同じ日付内に終了しました。アイデンティティはディレクターの目で維持され、参照に基づいてモデルによって決定される世界を導きます）、**LoRAシーンレバーによるライブ価格設定**（E14 — ベイクオフ：両方のスタイルLoRAが派生ウェイトにバインドされます。キャラクターは`technically_color`で維持され、フォトリアルなペアでは失敗します。勝者は、解決できない配信ファイル階層とクレジット義務を持ち、これらはすべて記録されます）。 |
| 経路、ルート | **3つ、測定済み** — **駆動されたルート**（リグレンダリングされたAAPoseスティック→Animate。ショットレベルで証明され、一時停止され、再開時にライセンスがクリアされます）· **自由なルート**（GLBによって作成された開始フレーム→カメラ階層は6.0 / uni_pcベースラインにあります。アイデンティティはアンカーなしで維持され、手作業で作られた世界は2つのシードで維持され、LoRAシーンレバーがライブで測定されます — E14）· **合成されたルート**（作成された参照をホストされたアイデンティティロック階層に組み込みます — E13によって卒業：アイデンティティロックされた、モデルによって決定される映画制作。世界は参照に含まれるものによって導かれます。仕様には注記があります）。 |
| 使う、費やす。 | 設立時のアークでは、それぞれ4クレジットで22件のプローブが実行されました。E08〜E12のアークでは、**0クレジット**（GPU時間課金）が、実験ごとの上限の下で使用されました。**E13の4つの世代は、リポジトリの最初のパートナークレジット支出であり、事前に指定された424〜844の範囲内です**。E14の2つの世代では、2世代の上限に達し、正確に**0のパートナークレジット**が使用されました。 |
| ライセンスマップ | 採用されたすべての依存関係には、**取得済みのライセンス文書**が添付されます。検証されていない場合は「NO」として扱われます。また、サードパーティの層を経由する場合、追加で**ルートごとの情報開示**が行われます（2026年8月12日にディレクターによって決定）。ゲートの目的は、スタジオのアート作品を公開することです。 |
| テスト | **1311 passing on the rig** (13 skips, measured 2026-08-15 at the v0.2.0 cut), under `-O` too; CI exercises what a runner honestly can — rig-local assets **skip visibly** |
| 状況 | **v0.2.0は2026年8月15日にリリースされました** — レコードはインストール可能なツールキットになります。`armature_core`はPyPIで`armature-previz`として、npmで`@mcptoolshop/armature`として公開され、OIDCによってタグから発行され、どこにも長期間有効なトークンはありません。レコードは依然としてドキュメントツリーであり、それはまだ完全です。 |

### 何が測定されているのか（電流の弧）

- **Identity holds** — driven (E08: the face reads as the twin's through the shot) *and*
  unanchored (E11 wave 1: every feature to the last frame with no reference, no clip-vision,
  no driving signal). The Director's eye is the verdict of record on both.
- **The camera obeys explicit control to one pixel** on the camera-tier weights (E11 wave 3) —
  and pushes in uncommanded without it (E11 wave 1).
- **Density moves the signal, not the performance** (E10) — resampling smooths steps 41 %,
  the performance 8.6 %; adopted anyway by eye: more fps reads better.
- **A licence row is not a wiring claim** (E11 wave 2) — a mapped-Apache model and a graph that
  never loaded it produced 65 frames of noise with every gate green. Gate PAIR now exists.
- **Scene composition is seed-volatile** (E10 / E11) — identical text re-composed the world
  wholesale across seeds. **A scene claim needs two seeds before it is a property.**
- **A handed world holds** (E12) — a real room in the start frame survives to the last frame
  on two seeds on the camera tier, one-variable-attributed to the start image by field diff.
  The same tier handed a previz void held a void (E11 wave 3): worlds are authored, then kept.
- **The catalog's 6.0 / uni_pc is the camera tier's baseline** (E12) — the inherited
  3.5 / euler premise fell to its own rung: at the catalog settings the same seeds that lost a
  head and grew a limb hold the figure to f80. The cost is named — stronger adherence pushed
  the **unscoped identity clause** onto the crowd on one seed of two; the subject-scoped
  prompt is the promoted lever.
- **Identity survives a hosted tier fed only authored references** (E13) — on wan2.7's
  reference-to-video, both arms, both seeds, the stylized wooden performer came through a
  human-trained model as the same character at the Director's eye. Three blind predictions
  across two seats expected the tier to overwrite non-human structure; none was right —
  one-directional pessimism about these models is now written down as calibration doctrine.
- **Reference grounds steer model-decided worlds, and dominate seed chaos on that tier**
  (E13) — grey plates begat a grey studio, a warm bar clip begat a warm interior, and both
  seeds per arm agreed. Mechanism attribution (plate-bleed vs studio-default) honestly open
  at four generations; a property-grade claim runs under the two-seed law in a designed
  follow-up.
- **A constructed VIDEO reaches VIDEO sockets** (E13) — no upload path exists for clips, but
  81 authored frames assembled in-graph (`CreateVideo`) were accepted at a reference-video
  socket. Every VIDEO-typed input on the platform is in principle reachable from authored
  frames.

### 何ではないのか

- **高速で腕と手を動かす。** いずれの設定（E12）でも、両方のシードでf80のテストに失敗している。
レバーは「プレゼンテーション重視」になるように再調整された — 手首とカメラの配置を、GLBにおけるディレクター自身の診断に基づいて行う（爪はメッシュの損傷ではなく、投影によるアーティファクトである）。フォールバックとしてメッシュ手術を行うが、最初に行うことはない。
- **写真の世界におけるカメラの役割。** 4つのE12クリップすべてで、水平検出が0/81回というのは、この世界には存在しないシームを検出しようとしていることを意味する — 提出前に登録され、カメラの結果に変換されることはない。実際の部屋でカメラ番号を読み取る前に、「シームのないカメラ装置」を用意する必要がある。
- **ナレーションの棚**（#7を参照）：ビートの終点、チャンクごとのプロンプト、ビデオ時間領域の条件設定、カメラ埋め込み — 採用され、必要に応じてライセンス供与され、テストは行われていない。

否定的な回答でも、ここでは完全に成功とみなされる — E11での大きな失敗により、3つのゲート、2つのルールが確立され、次の作業の正確な形状とロードマップが決まり、証拠が得られる前にそれが示された。

## このリポジトリの使い方

- [CLAUDE.md](CLAUDE.md) — ここでの作業方法：3つの役割、各役割が従うルール、譲れない点（ライセンスゲート、制限されたクレジット、アイデンティティは目で判断される）。
- [docs/ROADMAP.md](docs/ROADMAP.md) — ビルド全体をセッションごとに示し、事前に名前のついたドリフトトリップワイヤーも含まれる。
- `docs/experiments/` — 重要でない変更すべてが番号付きの実験として実行される：**作業前に仕様を記述 → 作業後にレポートを作成 → アドバイザーが最後に判断する。**
- `docs/license-map.md` — 検証済みの商用利用マップ。ライセンスドキュメントを取得せずに、パイプラインに何も入力されない。

この方法は[facet](../facet)から継承されたものであり、そこで費用が支払われた：facetの最初のセッションでは、6つの継承された主張が数分で偽りであることが判明した。なぜなら、それぞれが実行可能なコードの隣に配置されていたからである。armatureはfacetの下流にある — facetが図形を切り刻んで着色し、armatureがそれをステージングして実行する。

## 実行方法

インストールする必要はない。これはクローンして実行するリポジトリであり、どのレジストリにもパッケージはなく、サービスもデーモンもない。すべてのツールは直接呼び出される：

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| プラットフォーム | リグ上のWindows 11（Omen 45L、RTX 5090）。厳密なテストもCIの`ubuntu-latest`で実行される。Blenderに依存するテストは、Blenderが存在しない場合にサイレントにパスするのではなく、目に見えてスキップされる。 |
| Python | 3.13+ — CIでは3.13が実行され、リグのvenvでは3.14が実行される。テスト依存関係は、numpy、pillow、pytest、opencv（リグのバージョンに固定されている。これは、ポーズラスタライズテストでバイト安定したラスタライズをアサートするためである）およびmatplotlibである。 |
| Blender | 5.2、ヘッドレスモードのみ。ライブGUIセッションでは、記録されたパラメータなしにアーティファクトが発生し、その出力を再現できないレシピはレシピとはみなされない。 |
| Node | 22、`site/`の下にあるサイトでのみ使用。 |
| 生成 | Comfy Cloudで実行され、オペレーターによって送信される。レンダリングと測定はローカルで行われる。 |

絶対的なリグパスは、多くのツールやドキュメントに組み込まれている — それらは秘密ではないが、ほとんどのツールを別のマシンで変更せずに実行することはできないことを意味する。

## ここですべてを形作るルール

**非商用モデルは一切使用しない（実験を含む）。** CC-BY-NC、研究専用および学術専用のライセンスは完全に禁止される。禁止されたモデルで得られた結論は破棄する必要があるため、最初から開始されない。

**メトリックは診断であり、ディレクターが判断する。** 画面上の図形が同じキャラクターであるかどうかはカノンであり、どのメトリックもそれを近似することはできない。すべての生成実験では、1つの数値が引用される前に、**コントロール | 出力 | 参照 | 来歴**シートを作成する。

**クラウドクレジットは使用前に制限される。** 使用済みのクレジットは元に戻せないため、各仕様では事前にアームごとの上限を明記する。

**ルートは、それと共に行うものを明らかにする**（ディレクターの決定、2026-08-12）。サードパーティ層を通るすべてのルートは、プロバイダーのデータ使用およびトレーニング姿勢、AIコンテンツ開示義務、およびライセンスマップから取得したドキュメントに基づくウォーターマークポリシーを文書化する。完全にローカルなルートでは、何もリグの外に出ないことが明記される。開示メモのないルートは不完全であり、最初のアプリケーションはE13の仕様に従う。

## 信頼と脅威モデル

完全なポリシーは[SECURITY.md](SECURITY.md)に記載されており、ツリーに対して測定されるのではなく、主張される。要約すると：

- **アクセスされるデータ** — ローカルディスク上のメッシュ、レンダリング、ビデオ、画像、JSON。コマンドラインで指定されたパスに保存されます。さらに、このリポジトリ自身のマークダウンから派生したSQLiteインデックスである`docs/index/armature.db`も含まれます。標準的なアセットは、関連するディレクトリツリーから読み取り専用でアクセスされ、書き込まれることはありません。
- **アクセスされないデータ** — あらゆる種類の認証情報（ユーザー名、パスワードなど）は一切読み取られず、保存または送信されません。また、追跡されているすべてのファイルに対して、プロバイダーのプレフィックスが付いたキー、トークン、秘密鍵ブロック、インラインシークレット割り当てを検索しても、一致するものはありません。**テレメトリ、分析、使用状況のカウントは一切収集または送信されません。**オプトアウト機能もありません。なぜなら、オプトアウトする対象が存在しないからです。
- **ネットワークへのデータ送信** — `tools/`または`tests/`内のどこにも、Pythonのネットワークライブラリはインポートされていません。2つのツールが`curl.exe`にアクセスして、*ユーザーが*貼り付けたリストにあるファイルを、*ユーザーが*提出したバージョンからダウンロードします。それ以外の処理でネットワークへの接続が行われることはありません。
- **権限** — 通常のユーザー権限のみを使用します。管理者権限の昇格、サービスプログラムのインストール、レジストリまたはシステム設定への書き込みは行いません。
- **潜在的な問題点（隠蔽せず開示）** — ファイル操作はサンドボックス化されていません。ツールは、引数で指定された場所にファイルを書き込みます。予期しないエラーが発生した場合、生のトレースバックが出力されます。意図的な拒否の場合、エラーは出力されません。すべてのゲートは、トリガーとなった測定値を伴う型付きのエラーを発生させます。そして、**それらのどれもが`assert`ではありません**。このスイートは、CI環境で`-O`の下で2回実行され、引き続きエラーが発生することが確認されます。
- **サポート状況** — `main`のみがサポート対象です。リリースチャンネル、バックポートポリシー、SLA（サービス品質保証）はありません。

**出荷ゲート。** [SHIP_GATE.md](SHIP_GATE.md)には、実際の状態にある厳格なゲートA〜Dが記載されており、各行は証拠とともにチェックされるか、その妥当性に基づいてスキップされます。ソフトゲートの識別項目も正直にリストされており、まだ解決されていないものも含まれています。

## ライセンス

MIT — [LICENSE](LICENSE)を参照してください。このツールで使用される*モデル*のライセンスは別の問題であり、`docs/license-map.md`で追跡されます。
