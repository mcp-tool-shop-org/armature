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

#

あなたはシュートを阻止します。モデルがそれを撮影します。

**[ランディングページとハンドブックはこちら →](https://mcp-tool-shop-org.github.io/armature/)**

ビデオモデルは、他のレンダラーでは再現できない動き、光、そして生命感を表現できます。画面に誰がいて、どこに立っているのかを正確に伝えることはできません。しかし、アームatureを使用することで、標準的なキャラクターメッシュをヘッドレスのBlenderで配置し、アニメーションさせることができます。これにより、各フレームごとにビデオモデルが従うべき「制御シーケンス」としてレンダリングされ、AIによって生成されたビデオでは、位置とポーズが常に把握できる一貫した主要なキャラクターを登場させることが可能になります。

**アームチャーは、画像ではなくGLB形式の3Dモデルを使用して、画像を動画に変換する機能です。** すべての空間的な要素が作成され、その上に3Dモデルが配置されて動きを与えます。最終的な成果物は映像であり、映画、カットシーン、キャラクターのポーズや動きなど、あらゆるショットが含まれます。ゲームはその映像を利用する手段の一つであり、決してこのツールの限界ではありません。

ブレンダーでキャラクターを配置します。コントロールシーケンスをレンダリングし、ビデオモデルにその上に生命の息吹を描き込ませます。構造はあなたが持つジオメトリから生まれ、生命はモデルから生まれます。そして、アイデンティティとは、プロンプトや参照スタックに組み込まれた、名前とバージョンが明確に定義されたものです。それは決して偶然の幸運によって生まれたものではありません。

## インストール

```bash
pip install armature-studio
```

```bash
npm install -g @mcptoolshop/armature-studio   # the same command, as a launcher
```

```bash
armature check
armature canon --help
armature verify --help
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

それらはリポジトリ内に保存され、そこで実際に機能するものが、記述されたものになります。
`armature_core.blender_scene`は、`bpy`をインポートする単一のモジュールです。`armature check`は、それを欠陥としてではなく、`needs-blender`として報告します。`check`は、実行したインストールに関して真であるものを記述します。単にインポートするものを記述するだけではありません。また、関数ローカルのインポートも解決するため、OpenCV、Pillow、またはmatplotlibが欠落しているソースのチェックアウトや`--no-deps`インストールでは、`needs-cv2` / `needs-PIL`行が出力され、`UNRESOLVED:`が出力され、終了コード1で終了します。これは、以前は、描画機能が実行できないインストールで「すべてのモジュールが解決されました」と出力していました。失敗した行は、例外のタイプとメッセージを出力します。`--json`は、`module_rows`の下で同じ行を保持します。

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
| 消費ゲート | **Gate CANON**は、機械可読なカノンに対して名前を付けることができない対象を持つ、有料の提出物を拒否します。表面は行であり、空の占有物は**欠如ではなく穴**であり、両方の方向がチェックされます（プロンプトはカノンを網羅し、プロンプト内のすべてがカノンです）。これは、出力ディレクトリが作成される**前**に、7つのペイロードビルダーのそれぞれの中で実行されます。これは、このリポジトリが所有する不可逆的なステップは、ペイロードの書き込みであるためです。エスケープは、国勢調査によって裏付けられています。カノンを持つ対象に対する`--no-canon`は拒否され、受け入れられません。また、最初の健全性チェック以降、**すべての支出で明確に**表示されます。各ビルダーは`[canon] ARMED: <subject>`を出力し、国勢調査のエスケープでは`[canon] UNGATED: <subject> — <the census row's reason>`を出力するため、ビルドログは、カノンが書き込まれなかった対象と、承認された穴を区別し、その結果を`gates.CANON`の下に記録します。そのため、カノンが有効化されたか、エスケープされたかという質問を未解決のままにすることはできません。 |
| テスト | **8051がリグで実行**（59回のスキップ、2026年9月7日にfeature-executeピン修正後に測定 - v0.4.0では7538、Stage D後では7811）。`-O`の下では、STATUSを記録したリハーサルで同一です。CIは、ランナーが正直に実行できることを実行します。リグローカルのアセットは**目に見えてスキップ**されます。 |
| 状況 | **v0.5.0** — ステージDのビジュアル改善と、v0.4.0の安定版に加えて新機能を追加。リポジトリ内で承認された提出ツール（`build_submit_payload.py`、テスト実行）、インストールされたCLIツール`canon` / `verify` / `spec` / `donor`、8051件のテスト。1.0.0ではありません：未完了の項目がまだ残っています。 |

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

`armature_core`はPyPI（上記）からインストールされます。**実験レコードとレンダリングツール**はこのリポジトリであり、クローンされて実行されます。サービスやデーモンはありません。すべてのツールは直接呼び出されます。

```
python tools/<name>.py --help                       # the 55 CPython instruments: measurement, sheets, payload builders
blender -b -P tools/<name>.py -- <args>             # the 21 Blender-side instruments (stage_render, the rig_* tools, the
                                                    # sheet composers): headless only; `python tools/<name>.py` on one of
                                                    # these fails with `No module named 'bpy'`
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, package build + two clean installs (wheel + sdist), site build
```

各ツールは、その実行方法と、独自の1行の説明を持ちます：[docs/tools.md](docs/tools.md)（ドキュメント文字列から生成、2026年9月5日）。

### 停止の読み取り

すべてのCPythonインストルメントは、実行したことを示す場合に**0**、意図的な拒否（ゲートが発動、前提が失敗、引数が拒否された）の場合に**2**、クラッシュの場合に**1**で終了します。拒否またはクラッシュは、正確に1行の形式`<TOOL>_HALT {json}`を出力し、そのレコードには6つのキーが含まれます。`tool`、`outcome`、`gate`、`error`、`message`、`evidence`。その中で、`outcome`は3つの文の1つ（`HALTED — a gate fired`、`REFUSED — the tool declined to proceed`、`FAILED — an unhandled error`), `message`）です。これは拒否自体のテキストであり、`evidence.clause`は、呼び出し側がブランチする機械可読な単語です。句の語彙は、スイートによって保持されます（`tests/test_refusal_clauses.py`）。成功は、ツールが効果によって獲得するセンチネルです（`BUILD_PAYLOAD_OK`、`RIG_OK`、`ENCODE_OK`、…）、終了コードだけではありません。`blender -b -P`は、スクリプトの例外が伝播した場合に0で終了します。そのため、Blender側のツールは、ローカルハンドラーとリグツールの5つを通じて、同じ停止行を保持します。また、出力しなかったものに隣接して`halt.json`を書き込みます。CPython契約の唯一の実装は`armature_core.parts.run_tool_main`です。そのドキュメント文字列は仕様です。レコードは、ツールの独自の散文を散文のままにして、厳密なJSONとして出力されます。ターミナルのエンコーディングで文字を表現できない場合、行は、出力の失敗ではなく、その文字に対して`\uXXXX`エスケープにフォールバックし、終了コードもどちらの方法でも影響を受けません。

Stage Cパス（2026年9月6日）で到着した3つの拒否ファミリーは、どこでも同じように読み取られます。

- **以前の実行のアーティファクトを上書きするツール**（ビルドのグラフとレコード、レンダリングのフレームなど）は、句`output_already_exists`で拒否し、それらに名前を付けます（ビルドは両方のファイルと両方のダイジェストに名前を付けます）。`--overwrite`はそれらを置き換え、成功レコードには`out_dir_pre_existed`と`overwrote`が含まれます。Gate CANONの`out_dir_not_empty`の下にある唯一の支出ビルダーは、1つ前のゲートで空でない`--out`を拒否し、フラグは受け取りません。
- **待機するツール**（エンコード、デコード、レンダリング、ダウンロードなど）は、待機の前後に（および作業がカウント可能な項目の場合は、各項目ごと）標準エラーに小文字の進行状況行`<tool> <stage> <done>/<total>  elapsed <e>s  bound <b>s`を出力します。標準出力には、依然として成功または停止の行が1つだけ含まれます。各サブプロセスには、作業から派生したバウンドが含まれており、そのバウンドに達した場合、ディスク上の部分的な作業に名前を付け、再試行しない名前による拒否（`ffmpeg_exceeded_the_time_bound`、`downloader_exceeded_the_time_bound`）になります。有料パスでは、再試行は、補償がない支出クレジットを消費します。
- **出力ディレクトリが存在した後に発動するゲート**は、そのことを伝えます。拒否は、ディレクトリに名前を付け、部分的な作業が含まれており、結果ではないこと、およびサポートされている次のステップを伝えます。

### スイートの実行

```
E:\AI\armature\.venv\Scripts\python.exe -m pytest -q            # from the repo root, on the repo venv — never the system Python
```

3つの環境レバーがあり、すべてオプションです。`PYTHONPATH=E:/AI/record-index`（インデックステストがインポートする、隣接するワーキングコピー。これがない場合、これらのテストは名前でスキップされます）、`ARMATURE_BLENDER`（Blender駆動のフィクスチャが実行するBlender実行可能ファイル。これがない場合、またはこのリグから実行しない場合、これらのテストは目に見えてスキップされます）、および`ARMATURE_GIT`（パッケージングテストが呼び出すgit）。CIの正確なレシピは、`python-tests`ジョブです。`.github/workflows/ci.yml`。`verify.ps1`は、同じスイートを2回実行します（1回は`-O`の下で）。その後、パッケージをビルドし、2つのクリーンルーム（ホイールとsdist）にインストールします。

シード仕様の`ceiling`ブロックには、バインドする数値が含まれます。`submissions`、アームごとまたはウェーブごとの分割、`counted_in`、`note`。それらの背後にある修正履歴は、[specs/ceiling-why-machine-readable.md](specs/ceiling-why-machine-readable.md)にあります（2026年9月6日に、仕様内の8つの同一のコピーから移動しました。`specs/*.json`は、80,321バイトから45,585バイトに減少しました）。

| | |
|---|---|
| プラットフォーム | リグ上のWindows 11（Omen 45L、RTX 5090）。厳密なテストもCIの`ubuntu-latest`で実行される。Blenderに依存するテストは、Blenderが存在しない場合にサイレントにパスするのではなく、目に見えてスキップされる。 |
| Python | パッケージごとに`>=3.11,<3.15`を設定。CIでは3.11と3.13、リグのvenvでは3.14を実行。`pip install armature-studio`はnumpy、opencv-python-headless、Pillow、matplotlibをインストールする。これらはコードが実際にインポートする実行時の依存関係である（wave-3のヘルスパス以降に宣言。クリーンなインストールを使用して`armature_core`をインポートし、最初の描画呼び出しでエラーが発生する）。pytestはテスト専用の依存関係であり、CIではリグのバージョンにopencvを固定する。これは、ポーズラスタテストがバイト単位で安定したラスタライズをアサートするためである。 |
| Blender | 5.2、ヘッドレスモードのみ。ライブGUIセッションでは、記録されたパラメータなしにアーティファクトが発生し、その出力を再現できないレシピはレシピとはみなされない。 |
| Node | `armature`ランチャー（`npm/`）は、CIで18と22でテストされる。`site/`の下にあるサイトは、22でビルドされる。 |
| 生成 | Comfy Cloudで実行され、オペレーターによって送信される。レンダリングと測定はローカルで行われる。 |

絶対的なリグパスは、多くのツールやドキュメントに組み込まれている — それらは秘密ではないが、ほとんどのツールを別のマシンで変更せずに実行することはできないことを意味する。

## ここですべてを形作るルール

**非商用モデルは一切使用しない（実験を含む）。** CC-BY-NC、研究専用および学術専用のライセンスは完全に禁止される。禁止されたモデルで得られた結論は破棄する必要があるため、最初から開始されない。

**メトリックは診断であり、ディレクターが判断する。** 画面上の図形が同じキャラクターであるかどうかはカノンであり、どのメトリックもそれを近似することはできない。すべての生成実験では、1つの数値が引用される前に、**コントロール | 出力 | 参照 | 来歴**シートを作成する。

**クラウドクレジットは使用前に制限される。** 使用済みのクレジットは元に戻せないため、各仕様では事前にアームごとの上限を明記する。

**ルートは、それと共に行うものを明らかにする**（ディレクターの決定、2026-08-12）。サードパーティ層を通るすべてのルートは、プロバイダーのデータ使用およびトレーニング姿勢、AIコンテンツ開示義務、およびライセンスマップから取得したドキュメントに基づくウォーターマークポリシーを文書化する。完全にローカルなルートでは、何もリグの外に出ないことが明記される。開示メモのないルートは不完全であり、最初のアプリケーションはE13の仕様に従う。

## 信頼と脅威モデル

完全なポリシーは[SECURITY.md](SECURITY.md)に記載されており、ツリーに対して測定されるのではなく、主張される。要約すると：

- **Data touched** — meshes, renders, videos, images and JSON on local disk, at paths you pass
  on the command line, plus `docs/index/armature.db`, a SQLite index *derived* from this repo's
  own markdown. Canonical assets are consumed read-only from sibling trees and never written to.
- **Data NOT touched** — no credentials of any kind: none are read, stored or transmitted, and
  a sweep of every tracked file for provider-prefixed keys, tokens, private-key blocks and
  inline secret assignments returns zero matches. **No telemetry, analytics or usage counting**
  is collected or sent; there is no opt-out because there is nothing to opt out of.
- **Network egress** — no Python networking library is imported anywhere in `tools/` or
  `tests/`. Two tools shell out to `curl.exe` to download the files listed in a dump *you*
  paste in, from a generation *you* submitted. Nothing else here makes a network call.
- **Permissions** — ordinary user permissions. No elevation, no service installation, no
  registry or system-settings writes.
- **The sharp edges, disclosed rather than claimed away** — file operations are not sandboxed;
  a tool writes wherever its arguments say. Unexpected failures print a raw traceback.
  Deliberate refusals do not: every gate raises a typed error carrying the measurement that
  fired it, and **none of them is an `assert`** — the suite runs a second time under `-O` in CI
  to prove they still raise.
- **Support status** — `main` is the only supported state. Tagged releases exist (`v0.5.0`
  is current); there is no backport policy and no SLA.

**出荷ゲート。** [SHIP_GATE.md](SHIP_GATE.md)には、実際の状態にある厳格なゲートA〜Dが記載されており、各行は証拠とともにチェックされるか、その妥当性に基づいてスキップされます。ソフトゲートの識別項目も正直にリストされており、まだ解決されていないものも含まれています。

## ライセンス

MIT — [LICENSE](LICENSE)を参照してください。このツールで使用される*モデル*のライセンスは別の問題であり、`docs/license-map.md`で追跡されます。
