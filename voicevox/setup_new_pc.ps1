# kirinuki 新PCセットアップスクリプト(2026-07-18更新: VOICEVOX+アオイ声対応)
# 使い方: kirinuki フォルダごと新PCにコピーし、PowerShellで
#   Set-ExecutionPolicy -Scope Process Bypass; .\setup_new_pc.ps1
# やること: Python3.11/ffmpeg/yt-dlp → pipパッケージ → VOICEVOX → アオイ辞書 → 動作確認

$ErrorActionPreference = "Continue"
Write-Host "=== kirinuki セットアップ開始 ===" -ForegroundColor Cyan

# 1. winget で基本ツール(入っていればスキップされる)
foreach ($pkg in @("Python.Python.3.11", "Gyan.FFmpeg", "yt-dlp.yt-dlp", "Git.Git")) {
    Write-Host "--- $pkg を確認/インストール"
    winget install --id $pkg -e --accept-source-agreements --accept-package-agreements --silent
}

# PATH再読込
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")

# 2. pip パッケージ
Write-Host "--- Python パッケージ"
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install faster-whisper budoux numpy

# 3. NVIDIA GPU 検出と CUDA 用ライブラリ
$gpu = (Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match "NVIDIA" }).Name
if ($gpu) {
    Write-Host "--- NVIDIA GPU 検出: $gpu → CUDA用ライブラリを導入" -ForegroundColor Green
    py -3.11 -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
    Write-Host "GPUを使うには config.json に `"device`": `"cuda`" を追加(HANDOFF.md参照)"
} else {
    Write-Host "--- NVIDIA GPUなし → CPU(int8)モードで動作します" -ForegroundColor Yellow
}

# 4. VOICEVOX(長尺ナレーション用・完全無料)
$vvExe = "$env:LOCALAPPDATA\Programs\VOICEVOX\VOICEVOX.exe"
if (Test-Path $vvExe) {
    Write-Host "--- VOICEVOX は導入済み" -ForegroundColor Green
} else {
    Write-Host "--- VOICEVOX をダウンロード(Webインストーラー→本体1.5GB)"
    # 重要: NSISインストーラーは深いパスだとクラッシュする(0xc0000005)。短いパスで実行する
    $vvUrl = "https://github.com/VOICEVOX/voicevox/releases/download/0.25.2/VOICEVOX-CPU.Web.Setup.0.25.2.exe"
    $vvSetup = "$env:USERPROFILE\Downloads\VOICEVOX-Setup.exe"
    Invoke-WebRequest -Uri $vvUrl -OutFile $vvSetup
    Unblock-File $vvSetup   # SmartScreenブロック解除(これがないとGUIが開かない)
    Write-Host "インストーラーを起動します。「現在のユーザーのみ」推奨で進めてください" -ForegroundColor Yellow
    Start-Process -FilePath $vvSetup -Wait
}

# 5. VOICEVOXエンジンを直接起動(GUIより安定)して、アオイ用の発音辞書を登録
$engine = "$env:LOCALAPPDATA\Programs\VOICEVOX\vv-engine\run.exe"
if (Test-Path $engine) {
    Write-Host "--- VOICEVOXエンジン起動 → アオイ辞書登録"
    $running = $false
    try { Invoke-RestMethod -Uri "http://127.0.0.1:50021/version" -TimeoutSec 2 | Out-Null; $running = $true } catch {}
    if (-not $running) { Start-Process -FilePath $engine -WindowStyle Hidden }
    # エンジン起動待ち(最大2分)
    for ($i=0; $i -lt 24; $i++) {
        Start-Sleep -Seconds 5
        try { Invoke-RestMethod -Uri "http://127.0.0.1:50021/version" -TimeoutSec 2 | Out-Null; break } catch {}
    }
    py -3.11 -X utf8 "$PSScriptRoot\setup_aoi_dict.py"
} else {
    Write-Host "--- エンジンが見つからない。VOICEVOXインストール後に setup_aoi_dict.py を手動実行してください" -ForegroundColor Yellow
}

# 6. 動作確認
Write-Host "--- 動作確認"
ffmpeg -version | Select-Object -First 1
yt-dlp --version
py -3.11 -c "import faster_whisper, budoux, numpy; print('faster-whisper / budoux / numpy OK')"

Write-Host ""
Write-Host "=== セットアップ完了 ===" -ForegroundColor Cyan
Write-Host "ショート制作: py -3.11 -X utf8 kirinuki.py prep <URL>"
Write-Host "長尺ナレーション: py -3.11 -X utf8 voicevox_batch.py narration_ready\XXX.txt output\長尺\voicevox_aoi 14 1.10"
Write-Host "※アオイ声パラメータの詳細は AOI_BRAND_PROPOSAL.md / NEW_PC_MIGRATION.md 参照"
Write-Host "※DaVinci Resolve は blackmagicdesign.com から手動インストール(無料版)"
