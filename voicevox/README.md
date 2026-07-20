# voicevox/ — VOICEVOX セットアップ資材

Googleドライブ(kirinukiプロジェクト)にあったVOICEVOX関連の設定・スクリプトをこのリポジトリに取り込んだもの。

## ファイル一覧

| ファイル | 用途 |
|---|---|
| `VOICEVOX_SETUP.md` | ¥0プラン用の導入&運用ガイド(GUI操作手順) |
| `NEW_PC_MIGRATION.md` | 新PCでの環境再現手順(所要約1時間) |
| `setup_new_pc.ps1` | winget+pip+VOICEVOXを一発で入れるPowerShellスクリプト |
| `setup_aoi_dict.py` | エンジン起動後、固有名詞(Yale/Wharton/Claude等)の発音辞書を登録 |
| `voicevox_batch.py` | ナレーションtxt → 章別WAVを一括合成 |
| `voicevox_dialogue.py` | 【そら】/【玄野】等の話者切替対話台本 → 1本のWAV |
| `aoi_voice_lab.py` | アオイ独自声(B4チェーン)の探索・生成・既存WAVへの適用 |
| `run_aoi_output.ps1` | 上記アオイ声パイプラインの一括実行ラッパ |
| `AOI_VOICE_DECISION.md` | 波形分析によるB4採用の根拠と適用手順 |

## 最短セットアップ手順(Windows想定)

1. `voicevox/` を作業PCにコピー
2. PowerShellで:
   ```powershell
   cd voicevox
   Set-ExecutionPolicy -Scope Process Bypass
   .\setup_new_pc.ps1
   ```
3. インストール後、エンジン起動確認:
   ```powershell
   Start-Process "$env:LOCALAPPDATA\Programs\VOICEVOX\vv-engine\run.exe" -WindowStyle Hidden
   Invoke-RestMethod http://127.0.0.1:50021/version
   ```
4. 辞書登録:
   ```powershell
   py -3.11 -X utf8 setup_aoi_dict.py
   ```
5. 合成テスト:
   ```powershell
   py -3.11 -X utf8 voicevox_batch.py sample.txt out\ 14 1.10
   ```

詳細は `VOICEVOX_SETUP.md` と `NEW_PC_MIGRATION.md` を参照。
