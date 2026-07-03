# HANDOFF — アドリブ練習アプリ(メトロノーム + ランダムコード/スケール表示)

Claude Code で新規プロジェクトとして再構築するための引き継ぎ。
このチャットで作った成果物2つ(同一機能・実装違い)を同梱している:

- `adlib-practice.jsx` — React版(Tailwindクラス使用、Tone.js import前提)
- `adlib-practice.html` — 単一ファイル版(vanilla JS + Tone.js CDN)。**現時点で動作確認済みの正とする実装はこちら**

## 1. プロダクト概要

楽器のアドリブ練習用。精密メトロノームを鳴らしながら、コードと「そのコードで使うスケール」をフラッシュカード的にランダム表示する。
元ネタはユーザー提供のブラジル系教材画像(ディグリーネーム × モード対応表。例: Ⅳmaj7→リディアン、ⅶø→ロクリアン、Ⅴ7/ⅵ(E7)→Aハーモニックマイナー)。

コア体験: 「E7 が出た → Aハーモニックマイナーで弾く」を、任意キー・任意テンポで反復。

## 2. 機能仕様(実装済み)

- **メトロノーム**: Tone.js の Transport + Loop によるオーディオクロック駆動(setInterval不可、精度要件)。1拍目は低め(C5, -4dB)、他拍は高め(G5, -8dB)のtriangle短音。拍インジケータ(1拍目=琥珀色、他=白)。
- **BPM**: 30–300。±1ボタン、スライダー、TAPテンポ(直近5タップ・2.5秒窓の平均)。再生中のBPM変更は即反映(`Tone.Transport.bpm.value`)。
- **拍子**: 2/4〜7/4の単純拍子に加え、八分系の複合・変拍子 5/8(3+2)/6/8(3+3)/7/8(2+2+3)/9/8/12/8。八分系はグループ頭を中アクセント(G5)、弱パルスを小音量(E5, velocity 0.6)+小径ドットで表現。データは `TSIGS`(b=パルス数, u=単位, g=グループ配列)。
- **カスタム拍子(変則分母対応)**: 拍子セレクトの「カスタム…」で分子1〜24 × 分母{2,3,4,5,6,7,8,9,10,12,16}を自由指定。8/6(四分三連=6分音符単位)のような無理数拍子も可。アクセントグループは「3+3+2」形式のテキストで任意指定(合計が分子と一致しないと無視)。実装: `Tone.Transport.PPQ=2520`(2520×4=10080 が対象分母すべてで割り切れる)に上げ、クリックLoopの間隔を `PPQ*4/u` tick("Ni"表記)で指定。`Tone.Transport.timeSignature=[b,u]` は任意の数値ペアで動作(8/6→5.333拍)し、コード進行の "Nm" も正しく追従する。
- **ノリ(前ノリ/後ノリ)**: ジャスト/前ノリ/後ノリ × ズレ幅10/20/40ms。ジャスト以外では小音量の正拍ガイド音(square C6, -22dB)を鳴らし、メインクリックを±feelMsずらして再生。負方向(前ノリ)へのずらしはLoopのlookahead(約100ms)内なので安全。拍ドットもずらした時刻で点灯。
- **コード自動進行**: N小節ごと(1/2/4/8)に次のランダムコードへ。`Tone.Loop(..., barsPerChord+"m")`で実装。ON/OFF可。手動「次のコード」ボタンあり。
- **キー移調**: 12キー(C,G,D,A,E,B,F# / F,B♭,E♭,A♭,D♭)。キーごとにシャープ系/フラット系の音名表記を切替。
- **カテゴリフィルタ**(複数ON可、全OFF時は全エントリ使用):
  - ダイアトニック(7) / セカンダリードミナント(5) / 代理・ディミニッシュ(3) / マイナーⅱ-Ⅴ-ⅰ借用(3)
- **ランダム抽選**: 直前と同一エントリは連続させない。
- 表示内容: ディグリーネーム、実コード名(例 E7)、スケール名(例 A ハーモニックマイナー)、スケール構成音。
- **譜面表示**(HTML版のみ実装、JSX版は未反映): スケール1オクターブ+オクターブ音をSVGで五線譜(ト音記号、加線・臨時記号対応)とギターTAB譜に描画。TABはルートを6弦(ルートのフレットが7以上なら5弦)に置き、ルートフレット+3までのポジションボックスで弦を割り当てる簡易アルゴリズム。
- **特徴音の強調**: 各スケールに `ch`(ルートからの半音数の配列)と `chJa`(説明文)を定義。構成音テキスト・五線譜(琥珀ノートヘッド+リング)・TAB(琥珀丸囲み)の3箇所でハイライトし、カード下部に「特徴音: ♯11と♭7」等のラベルを表示。例: リディアン=♯4、ハーモニックマイナー=♭6と♮7、オルタード=♭9・♯9・♯11・♭13。

## 3. 理論データ(エンジンの核。正確に移植すること)

オフセットは「選択キーのトニックからの半音数」。`cr`=コードルート、`sr`=スケールルート。

```
ダイアトニック:
Ⅰmaj7  cr=0  maj7   sr=0  ionian
ⅱm7    cr=2  m7     sr=2  dorian
ⅲm7    cr=4  m7     sr=4  phrygian
Ⅳmaj7  cr=5  maj7   sr=5  lydian
Ⅴ7     cr=7  7      sr=7  mixolydian
ⅵm7    cr=9  m7     sr=9  aeolian
ⅶø7    cr=11 m7b5   sr=11 locrian

セカンダリードミナント:
Ⅴ7/ⅱ   cr=9  7  sr=9  mixolydian
Ⅴ7/ⅲ   cr=11 7  sr=11 mixolydian
Ⅴ7/Ⅳ   cr=0  7  sr=0  mixolydian
Ⅴ7/Ⅴ   cr=2  7  sr=2  mixolydian
Ⅴ7/ⅵ   cr=4  7  sr=9  harmonicMinor   ← 教材画像の核。E7でAハモマイ(key C時)

代理・ディミニッシュ:
subⅤ7      cr=1  7     sr=1  lydianDominant
subⅤ7/ⅱ   cr=3  7     sr=3  lydianDominant
ⅶ°7        cr=11 dim7  sr=11 wholeHalfDim

マイナーⅱ-Ⅴ-ⅰ(借用):
ⅱø7       cr=2 m7b5  sr=2 locrianNat2
Ⅴ7alt     cr=7 7     sr=7 altered
ⅰm(maj7)  cr=0 mMaj7 sr=0 melodicMinor
```

スケール定義(半音インターバル):
```
ionian 0,2,4,5,7,9,11 / dorian 0,2,3,5,7,9,10 / phrygian 0,1,3,5,7,8,10
lydian 0,2,4,6,7,9,11 / mixolydian 0,2,4,5,7,9,10 / aeolian 0,2,3,5,7,8,10
locrian 0,1,3,5,6,8,10 / harmonicMinor 0,2,3,5,7,8,11 / melodicMinor 0,2,3,5,7,9,11
locrianNat2 0,2,3,5,6,8,10 / altered 0,1,3,4,6,8,10
lydianDominant 0,2,4,6,7,9,10 / wholeHalfDim 0,2,3,5,6,8,9,11
```

## 4. 実装上の決定事項・ハマりどころ

- **Web Audioの自動再生制限**: 再生開始は必ずユーザー操作内で `await Tone.start()` してから Transport.start()。
- **UI更新は `Tone.Draw.schedule()`** でオーディオ時刻に同期(拍ドット・コード切替)。直接setStateするとズレる。
- **停止時のクリーンアップ**: Loop.dispose() + Synth.dispose() + `Transport.stop()` + `Transport.cancel()`。React版はuseEffectのcleanupで実施。
- **拍子変更**: 再生中は一旦stop→startで作り直すのが簡単(HTML版はそうしている)。
- **音名表記**: キーが#系かb系かのフラグ1つで SHARP_NAMES / FLAT_NAMES を切替える簡易実装。**既知の限界**: 機能和声的に厳密な異名同音表記(F#/G♭の文脈判定、ダブルシャープ等)は未対応。改善するならスケールごとの度数ベース綴りアルゴリズムに置き換える。
- iOSサイレントスイッチでWeb Audioが無音になる既知問題あり(仕様、対処不能)。

## 5. デザイントークン(踏襲する場合)

- 紙: #F5EFDD / 縁: #E3D9BC / 背景: #EDE7D3 / インク: #20242B / 補助: #5A6070 / アクセント(1拍目・開始ボタン): #E4A93B
- カテゴリ色: diatonic #2F5C7A(bg #D9E6EC) / secondary #B5651D(#F1DDB8) / subs #8A3B3B(#EACFCB) / minorii #5B4B8A(#DBD3EC)
- 見出しはセリフ(Georgia系)+ 五線譜風の背景ライン、操作系はsans、BPMは等幅tabular-nums。

## 5.5 PWA・スマホ対応(実装済み)

- `manifest.webmanifest`(standalone / portrait / テーマ色 #20242B)+ `sw.js`(cache-first、Tone.js CDN含む5アセットをプリキャッシュ、オフライン動作可)+ `icon-192.png` / `icon-512.png`(System.Drawingで生成した琥珀丸+音符)。
- SW登録は https または localhost のみ(HTML末尾)。**平文http(LAN IP)ではSW/インストールバナーは無効**なのが既知の制約。iOS Safariは「ホーム画面に追加」でフルスクリーン起動は可能(apple-mobile-web-app-capable設定済み)。
- `serve.cmd`: ダブルクリックで `npx http-server . -p 8734` を起動し、同一Wi-FiのスマホからPCのIP(例 http://192.168.0.69:8734/adlib-practice.html)でアクセスする運用。`qr.html` をPCブラウザで開くとアクセス用QRコードを表示(IPはページを開いたホスト名から自動組み立て、localhost時は192.168.0.69にフォールバック — IPが変わったら入力欄で書き換え可)。
- **本番URL: https://sengokueru.github.io/adlib-practice/** (GitHub Pages、リポジトリ sengokueru/adlib-practice ・公開)。HTTPSなのでSW・オフライン・ホーム画面インストールがフル動作。デプロイは同リポジトリへの push のみ(ビルド工程なし)。メインファイルは `index.html`(旧 adlib-practice.html からリネーム)。

## 6. 次の拡張候補(未着手・ユーザー未確認)

- HTTPSホスティングへのデプロイ(GitHub Pages / Netlify)で本格PWAインストール対応
- コード音のプレビュー再生 / ドローン(ルート持続音)
- ⅱ-Ⅴ-Ⅰなど「進行単位」での出題モード
- 練習ログ(出題履歴・苦手カテゴリ)
- 異名同音の厳密表記

## 7. 元教材画像の記載内容(参照)

Key C想定の帯: Fmaj7=Ⅳmaj7=Lídio(リディアン)、Bø=Ⅶø=Lócria(ロクリアン)、E7=Ⅴ7=Menor Harmônica A(Aハーモニックマイナー)。下段に Dm7 / G7 / Em7 の併記あり(ポルトガル語教材)。
