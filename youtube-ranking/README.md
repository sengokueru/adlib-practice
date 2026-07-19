# ツベランキング 📈

ニコニコ動画のランキングみたいに、YouTubeの人気動画を「地域別 × ジャンル別」で一覧表示する単一HTMLのサイト。

## 使い方

1. `youtube-ranking/index.html` をブラウザで開く（ローカルファイルのままでもOK、静的ホスティングでもOK）
2. 初回のみ YouTube Data API v3 のAPIキー（無料）を入力
   - [Google Cloud Console](https://console.cloud.google.com/apis/library/youtube.googleapis.com) で「YouTube Data API v3」を有効化 →「認証情報」→「APIキーを作成」
   - キーは端末の localStorage にだけ保存され、Google以外には送信されない
3. タブでジャンル（音楽/ゲーム/エンタメ/…）、右上で地域を切り替え

## 仕組み

YouTube Data API v3 の `videos.list?chart=mostPopular` を使用。
`regionCode` と `videoCategoryId` を指定すると、地域×カテゴリの人気上位50件（再生数・高評価・コメント数付き）が取れる。
無料枠（1日10,000ユニット、1リクエスト=1ユニット）で個人利用には十分。

※ 一部のカテゴリは地域によってチャート未提供（APIがエラーを返す）。その場合は画面にその旨を表示する。
