# 新PC移行ガイド(2026-07-18版)

**目的**: 別のPCで今の環境と同一の制作体制を再現する。所要約1時間(大半はダウンロード待ち)。

---

## STEP 1: ファイルの移動(10分)

### 方法A: OneDrive(推奨)
`OneDrive\kirinuki_移動用\` を新PCの好きな場所にコピー。
- `kirinuki\` → 作業フォルダに配置
- `claude_memory\` → `C:\Users\<user>\.claude\projects\<プロジェクトパス>\memory\` に配置(Claude Codeの記憶引き継ぎ)
- `README_新PCで最初に読む.md` に従う

### 方法B: git(全ドキュメント・スクリプトはコミット済み)
リポジトリごと持っていけるならこちらが確実。コミット `8bb69f2` 以降に全資産が入っている。
**gitに入っていないもの**(必要なら手動コピー):
- `output\` (完成動画・音声) — **基本は新PCで再生成でOK**(下記STEP4)
- `jobs\` (DL済み素材+文字起こし) — 再取得可能なので不要

---

## STEP 2: 環境構築(30分・ほぼ自動)

新PCのPowerShellで:
```powershell
cd <kirinukiフォルダ>
Set-ExecutionPolicy -Scope Process Bypass
.\setup_new_pc.ps1
```

これで入るもの:
- Python 3.11 / ffmpeg / yt-dlp / git
- faster-whisper / budoux / numpy
- VOICEVOX(インストーラーが開いたら「現在のユーザーのみ」で進める)
- アオイ用発音辞書(Yale→イェール等、自動登録)

**手動で入れるもの**:
- DaVinci Resolve(無料版): blackmagicdesign.com からDL
- Claude Code: 既存の手順でセットアップ→ `claude_memory\` を配置

---

## STEP 3: 動作確認(5分)

```powershell
# ① ショートパイプライン
py -3.11 -X utf8 kirinuki.py list

# ② VOICEVOXエンジン(GUI不要、直接起動が安定)
Start-Process "$env:LOCALAPPDATA\Programs\VOICEVOX\vv-engine\run.exe" -WindowStyle Hidden
# 30秒〜2分待って:
Invoke-RestMethod http://127.0.0.1:50021/version # → "0.25.2" が返ればOK
```

---

## STEP 4: 音声の再生成(必要な分だけ・各10分程度)

ナレーションWAVはgit外なので、新PCで再合成する(テキストから完全再現可能):

```powershell
# アオイ声(冥鳴ひまり+pitch-0.05+抑揚1.25)で全8本再生成する場合
py -3.11 -X utf8 -c "
import sys; sys.argv=['x']
exec(open('voicevox_batch.py',encoding='utf-8').read().replace('def main','def _main'))
" # ←使わない。下の個別コマンドを使う
```

**個別に作る場合**(voicevox_batch.pyはスピーカーIDと速度を引数で取る):
```powershell
# 注意: アオイ公式声のpitch/intonationはvoicevox_batch.pyには未実装。
# アオイ声で作る場合は過去セッションのbatch_aoi.py方式(pitchScale=-0.05, intonationScale=1.25)を使う。
# → 簡単なのは Claude Code に「narration_ready/XXX.txt をアオイ声で合成して」と頼むこと。
# アオイ声のパラメータは AOI_BRAND_PROPOSAL.md に記録済み。
```

---

## STEP 5: Claude Code の文脈引き継ぎ

新PCのClaude Codeで最初に伝えること:
```
kirinuki/START_HERE.md から読んで。前のPCからの移行です。
```
これで AGENTS.md → LOG.md → 各ドキュメントを辿って全文脈が入る。
`claude_memory\` を正しく配置していれば、メモリからも自動で文脈補完される。

---

## 環境の落とし穴(前PCで実際に踏んだもの)

| 症状 | 原因 | 対策 |
|---|---|---|
| VOICEVOXインストーラーが無反応 | SmartScreenブロック | `Unblock-File`してから実行 |
| インストーラーが即クラッシュ(0xc0000005) | 深いフォルダパス | `Downloads\`など短いパスから実行 |
| エンジンが起動しない | GUI経由の起動が不安定 | `vv-engine\run.exe` を直接起動 |
| PS1スクリプトで日本語パスが文字化け | cp932解釈 | Pythonドライバ経由で実行 |
| kirinuki.pyがcp932でクラッシュ | print文のエンコード | `-X utf8` フラグ必須 |
| yt-dlpがbot判定される | クッキー無し | `--cookies-from-browser chrome` |

---

## チャンネル情報(ログイン後に確認)

| チャンネル | ID | 用途 |
|---|---|---|
| シリコンバレーの声 @valleyvoicejp | UCL1PM6dL8Ev9syFIp9Z1CCg | AI/スタートアップ |
| 宇宙の声 @uchunokoe0711 | UCr0WutdMmtJl2jtO1l8yXgA | 宇宙・科学 |
| 心の声 | UCTqWNYXF4dM0aNy4hc3G8_Q | 心理学 |

Googleアカウントのログインと、YouTube Studioのチャンネル切替(channel_switcher)は手動。
