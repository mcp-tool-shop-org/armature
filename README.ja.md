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

**あなたは、そのショットを阻止します。モデルがそれを撮影します。**

**[ランディングページとハンドブック →](https://mcp-tool-shop-org.github.io/armature/)**

ビデオモデルは、どのレンダラーも再現できないモーション、光、生命を生み出すことができます。画面に誰がいて、どこに立っているのかを区別することはできません。armature はまさにそれを提供します。標準的なキャラクターメッシュをヘッドレス Blender で配置し、アニメーションを作成し、レンダリングすることで、フレームごとに**制御シーケンス**となり、ビデオモデルはそれに従う必要があります。これにより、AI によって生成されたビデオで、位置とポーズがすべてのフレームでわかっている一貫した主要なキャラクターを表示できます。

**armature は、画像ではなく GLB を使用して、画像をビデオに変換します。** すべての空間的な要素は作成され、モデルがその上に生命を吹き込みます。最終的な成果物は映像です。映画、カットシーン、キャラクターのポーズと動き、あらゆるショットなどです。ゲームはその映像を利用する消費者の一つであり、このツールの境界ではありません。

Blender でキャラクターを配置します。制御シーケンスをレンダリングします。ビデオモデルにその上に生命を吹き込ませます。構造は、あなたが所有するジオメトリから生まれます。生命はモデルから生まれます。アイデンティティは、プロンプトと参照スタックに含まれる名前付きのバージョン管理されたものです。偶然によって生成されることはありません。

## インストール

```bash
pip install armature-studio
```

```bash
npm install -g @mcptoolshop/armature-studio   # the same command, as a launcher
```

```bash
armature check
```

インストール可能なパッケージは **`armature_core`** です。ゲート、フレーミング、ターンアラウンドソルバー、ショット仕様契約、チャンネル数学、ペイロードビルダーが含まれます。これらはすべてプレーン CPython の下でインポートされます。これにより、Blender がなくてもテストおよびパッケージ化できます。

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**レンダリングスクリプトはコンソールエントリポイントではありません。これは意図的なものです。**
`render_turnaround.py`、`stage_render.py` およびそれらの兄弟は、**Blender 独自のインタープリター**内で実行されます。Python のコンソールスクリプトでは、`bpy` をインポートできず、最初の行でエラーが発生するため、それを配布することはパッケージが守ることのできない約束になります。

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

それらはここにリポジトリに留まり、そこで機能する呼び出しは記述されたものです。`armature_core.blender_scene` は `bpy` をインポートする単一のモジュールです。`armature check` はそれを `needs-blender` として報告し、欠陥としては扱いません。

npm パッケージは **ランチャーであり、移植ではありません**。別の言語で閾値を再実装すると、閾値がずれる可能性があります。そのため、Python に保存されている真の値に転送し、拒否します。大音量で、ゼロ以外の値で、それを修正する唯一のコマンドを使用して、あなたの代わりに何もインストールしません。

---

## 状態：仮説は製品レベルで測定されます

**2026 年 8 月 10 日に設立されました。** 13 件の実験が終了し、仮説は *テスト中* から **製品レベルで測定される** に移行しました。キャラクターが自身のリグから駆動され、自由に画面上で踊り、手作業で作られた世界が最後のフレームまで維持され（E12）、**アイデンティティは、作成された参照のみを供給されたホストされた人間によるトレーニング層で生き残ります**（E13）。すべてディレクターの目で判断されます。設立時の監査は [docs/audit-first-arc.md](docs/audit-first-arc.md) にあります。2026 年 8 月 12 日以降、学習モノリポジトリとして運用されています。実験によってパスが証明され、慣性によってカノンとなるルートはありません（CLAUDE.md）。

| | |
|---|---|
| 実験 | **E01～E14 は終了しました**（E05 は誤った前提に基づいて中止されました）。制御アーク（E01～E06）、リグの修正 + スケルトンの承認（E07）、**最初のレンダリングされたショット**（E08）、クリーンチェーンベースライン（E09）、高密度化された駆動方式を採用（E10）、制御なしのルート、3 つの段階を経て教訓的な失敗に終わる（E11）、**自由なルートが世界を獲得し、6.0 / uni_pc ベースラインになる**（E12）、**合成されたルートがその質問に答える**（E13 - 配信され、ゼロ費用で停止し、サポートアークによって修正され、再武装され、実行され、同じ日付内に終了しました。アイデンティティはディレクターの目で維持されます。参照グラウンドがモデルによって決定される世界を導きます）、**LoRA シーンレバーによるライブ価格設定**（E14 - ベイクオフ：両方のスタイル LoRA が派生ウェイトにバインドされます。キャラクターは `technically_color` で維持され、フォトリアルなペアで失敗します。勝者は解決できない提供ファイル層とクレジット義務を持ち、どちらも記録されます）。 |
| ルート | **3 つのルートがあり、測定されています**。**駆動されたルート**（リグレンダリングされた AAPose スティック → アニメーション。ショットレベルで証明され、一時停止され、再開のためにライセンスがクリアされました）。**自由なルート**（GLB で作成された開始フレーム → カメラ層は 6.0 / uni_pc ベースラインにあります。アイデンティティはアンカーなしで維持されます。手作業で作られた世界が 2 つのシードで維持され、LoRA シーンレバーがライブで測定されます - E14）。**合成されたルート**（作成された参照をホストされたアイデンティティロック層に投入 - E13 で卒業：アイデンティティロックされた、モデルによって決定される映画撮影。世界は参照に含まれるものによって導かれます。仕様には開示の注意書きが含まれています）。 |
| 費用 | 設立時のアークでは 22 件のプローブがあり、それぞれ 4 クレジットです。E08～E12 のアークでは、**0 クレジット**（GPU 時間課金）が実験ごとの上限の下で計上されました。**E13 の 4 つの世代は、リポジトリ初のパートナークレジット費用であり、事前に指定された 424 ～ 844 の範囲内です**。E14 の 2 つの世代では、**0 パートナークレジット**が 2 世代の上限で計上され、正確に上限に達しました。 |
| ライセンスマップ | 採用されたすべての依存関係には、**取得したライセンスドキュメント**が含まれています。検証されていないものは NO として扱われます。サードパーティの層を通るルートには、**ルートごとの開示**も含まれます（ディレクターによって 2026 年 8 月 12 日に決定）。ゲートの明記された目的は、スタジオのアートを公開することです。 |
| 費用ゲート | **ゲート CANON は、その対象が機械可読なカノンに対して名前で識別できない有料の提出物を拒否します。** 表面は行であり、null の占有者は **欠如ではなく穴** であり、両方の方向がチェックされます（プロンプトはカノンを網羅し、プロンプト内のすべてがカノンです）。これは、出力ディレクトリが作成される前に、7 つのペイロードビルダーのそれぞれの中で実行されます。このリポジトリが所有する不可逆的なステップは、ペイロードの書き込みであるためです。エスケープはコンセンサスによってサポートされています。`--no-canon` は、カノンを持つ対象に対して拒否され、許可されることはありません。 |
| テスト | **1351、リグ上で実行**（14回のスキップ、測定日：2026年8月18日）、`-O`の下で同一；CIはランナーが正直にできることを実行する—リグローカルのアセットは**目に見えてスキップされる** |
| ステータス | **v0.3.0** — レコードに支出ゲートと、自身を検証するインデックスが追加。`armature_core`はPyPIとして`armature-studio`、npmとして`@mcptoolshop/armature-studio`にデプロイされ、OIDCによるタグから公開され、どこにも永続的なトークンはない。 |

### 測定対象（現在の弧）

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

### そうでないもの

- **高速で動く腕と手**。両方のシードで両方の設定でf80で失敗し続けている（E12）。
レバーは再スコープされ、**プレゼンテーションを最優先とする**—手首とカメラの配置は、ディレクター自身のGLBに関する診断に基づいている（爪はメッシュの損傷ではなく、投影アーティファクトである）—
そして、フォールバックとしてメッシュ手術が行われ、それが最初に行われることはない。
- **写真の世界におけるカメラの主張**。すべてのE12クリップで0/81個の地平線検出は、この世界には存在しないシームを検出器が求めていることを示している—提出前に登録され、カメラの結果に変換されることはなかった。**シームのないカメラ機器**は、実際の部屋でカメラ番号を読み取る前に提供されるべきである。
- **ナレーションシェルフ**（#7を参照）：ビートの終点、チャンクごとのプロンプト、ビデオ時間領域コンディショニング、カメラ埋め込み—採用され、必要な場合はライセンス供与され、テストされていない。

否定的な答えは、ここでも完全な成功である—E11のハードフェイルにより、3つのゲート、2つの法則が購入され、次の作業とロードマップの正確な形状が決まり、証拠が到着する前にそれがそうなることが言われていた。

## このリポジトリの仕組み

- [CLAUDE.md](CLAUDE.md) — ここでの作業方法：3つの役割、各シートに適用されるルール、および譲れないこと（ライセンスゲート、制限されたクレジット、アイデンティティは視覚的に判断される）。
- [docs/ROADMAP.md](docs/ROADMAP.md) — 各セッションごとのビルド全体と、事前に名前が付けられたドリフトトリップワイヤー。
- `docs/experiments/` — すべての重要な変更は、番号付きの実験として実行される：
**作業前の仕様 → 作業後のレポート → アドバイザーによる最終的な判断。**
- `docs/license-map.md` — 検証済みの商用利用マップ。パイプラインに何も入力するには、取得されたライセンスドキュメントが必要である。

この方法は、[facet](../facet)から継承されており、そこで費用が支払われた：facetの最初のセッションでは、6つの継承された主張が数分で偽証され、それぞれが実行可能なコードの隣に配置されていた。armatureはfacetの下流にある—facetは図をカットしてペイントし、armatureはそれをステージングして実行する。

## 実行方法

`armature_core`はPyPIからインストールされる（上記）；**実験レコードとレンダリング機器**はこのリポジトリであり、クローンされて実行される—サービスやデーモンはない。すべての機器は直接呼び出される：

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| プラットフォーム | リグ上のWindows 11（Omen 45L、RTX 5090）。厳密なテストも、CIの`ubuntu-latest`で実行される；Blenderに依存するテストは、Blenderが存在しない場合にサイレントにパスするのではなく、**目に見えてスキップされる**。 |
| Python | 3.13+ — CIは3.13を実行し、リグvenvは3.14を実行する。テスト依存関係は、numpy、pillow、pytest、opencv（リグのバージョンに固定されているため、ポーズラスタライズテストはバイト安定したラスタライズをアサートする）およびmatplotlibである。 |
| Blender | 5.2、ヘッドレスモードのみ。GUIセッションを実行すると、記録されたパラメータなしで成果物が生成され、その出力を再現できないレシピは有効なレシピとはみなされない。 |
| ノード | 22、`site/`に限定 |
| 生成 | Comfy Cloud上で実行され、オペレーターによって送信される。レンダリングと測定はローカルで行われる。 |

絶対パスは多くのツールやドキュメントに組み込まれている。これらは秘密ではないが、ほとんどの機器を別のマシンで変更せずに実行することはできないことを意味する。

## ここに存在するすべての要素を規定する基本的なルール

**いかなる非営利モデルも使用しない（実験を含む）。** CC-BY-NC、研究専用、学術専用のライセンスは全面的に禁止される。禁止されたモデルに基づいて得られた結論は破棄する必要があるため、そのようなことは最初から行われない。

**指標は診断であり、最終的な判断はディレクターが行う。** 画面上の画像が同じキャラクターであるかどうかは、公式な設定であり、どの指標もそれを正確に表すものではない。すべての生成実験では、数値データを使用する前に、**コントロール | 出力 | 参照 | 起源** のシートを作成する。

**クラウドクレジットの使用量は事前に制限される。** 使用済みのクレジットは元に戻せないため、各仕様では、使用量の上限を事前に明記する。

**ルートは、それと連携するものを示す（ディレクターの決定、2026年8月12日）。** 外部サービスを経由するすべてのルートは、プロバイダーのデータ利用およびトレーニング方針、AIコンテンツ開示義務、およびウォーターマークポリシーを文書化し、ライセンスマップから取得したドキュメントに基づいて規定される。完全にローカルなルートでは、データがシステム外に出ないことが保証される。開示に関する注記がないルートは不完全であり、最初のアプリケーションはE13の仕様に従う。

## 信頼と脅威モデル

完全なポリシーは[SECURITY.md](SECURITY.md)に記載されており、ツリー構造に対して測定される。簡潔な概要は以下のとおり。

- **アクセスされたデータ** — ローカルディスク上のメッシュ、レンダリング、ビデオ、画像、およびJSONファイル。コマンドラインで指定されたパスと、このリポジトリのMarkdownから派生したSQLiteインデックスである`docs/index/armature.db`を含む。公式のアセットは、関連するツリーから読み取り専用で取得され、書き込まれることはない。
- **アクセスされないデータ** — あらゆる種類の認証情報：読み込み、保存、または送信されることはなく、プロバイダーのプレフィックスが付いたキー、トークン、秘密鍵ブロック、およびインラインの秘密情報の割り当てについて、追跡されているすべてのファイルをスキャンしても、一致するものが見つからない。**テレメトリ、分析、または使用状況の追跡は収集または送信されない。** オプトアウト機能はないため、オプトアウトする必要もない。
- **ネットワークからのデータ送信** — `tools/`または`tests/`内のどこにもPythonのネットワークライブラリはインポートされていない。2つのツールが`curl.exe`にシェルコマンドを送信して、*ユーザーが貼り付けた*ダンプにリストされているファイルをダウンロードし、*ユーザーが送信した*生成に使用する。それ以外の操作でネットワーク接続を行うことはない。
- **権限** — 通常のユーザー権限。昇格、サービスインストール、レジストリまたはシステム設定への書き込みは行われない。
- **開示することで対処する問題点（隠蔽しない）** — ファイル操作はサンドボックス化されない。ツールは、引数で指定された場所に書き込む。予期しないエラーが発生した場合、生のトレースバックが出力される。意図的な拒否の場合、エラーメッセージは出力されない。すべてのゲートは、測定結果を含む型付きのエラーを発生させ、**それらのどれも`assert`ではない**。スイートはCI環境で2回実行され、それらが引き続きエラーを発生させることを確認する（`-O`）。
- **サポート状況** — `main`のみがサポートされている状態である。リリースチャンネルはなく、バックポートポリシーやSLAもない。

**出荷ゲート。** [SHIP_GATE.md](SHIP_GATE.md)には、実際の状態でA〜Dの厳格なゲートが記載されており、各行は証拠とともにチェックされるか、またはその理由とともにスキップされる。ソフトゲートの識別項目も正直にリストされており、まだ解決されていないものも含まれている。

## ライセンス

MIT — [LICENSE](LICENSE)を参照。このツールで使用するすべての*モデル*のライセンスは別の問題であり、`docs/license-map.md`で追跡される。
