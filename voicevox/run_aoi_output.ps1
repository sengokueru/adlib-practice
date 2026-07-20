# run_aoi_output.ps1 — アオイ独自声(B4)の一括出力
# kirinukiフォルダで実行: Set-ExecutionPolicy -Scope Process Bypass; .\run_aoi_output.ps1
# やること: エンジン起動 → 依存導入 → 許可実査 → 候補生成 → 本編8本にB4適用 → 定型30本合成

$ErrorActionPreference = "Stop"
cd $PSScriptRoot

Write-Host "=== 0. VOICEVOXエンジン起動 ===" -ForegroundColor Cyan
$engine = "$env:LOCALAPPDATA\Programs\VOICEVOX\vv-engine\run.exe"
if (-not (Get-Process -Name run -ErrorAction SilentlyContinue)) {
    Start-Process $engine -WindowStyle Hidden
}
# 起動待ち(最大120秒)
$ok = $false
foreach ($i in 1..60) {
    try { Invoke-RestMethod http://127.0.0.1:50021/version -TimeoutSec 2 | Out-Null; $ok = $true; break }
    catch { Start-Sleep -Seconds 2 }
}
if (-not $ok) { Write-Host "エンジンが起動しない。手動起動して再実行を" -ForegroundColor Red; exit 1 }
Write-Host "エンジンOK"

Write-Host "=== 1. 依存導入(初回のみ時間がかかる) ===" -ForegroundColor Cyan
py -3.11 -m pip install --quiet praat-parselmouth numpy

Write-Host "=== 2. モーフィング許可の全数実査 ===" -ForegroundColor Cyan
py -3.11 -X utf8 aoi_voice_lab.py survey

Write-Host "=== 3. 候補声サンプル生成(聞き比べ用) ===" -ForegroundColor Cyan
py -3.11 -X utf8 aoi_voice_lab.py generate

Write-Host "=== 4. 本編ナレーション8本へB4適用 ===" -ForegroundColor Cyan
$wavs = Get-ChildItem "output\長尺\voicevox_aoi\*_AOI.wav" -ErrorAction SilentlyContinue
if ($wavs) {
    foreach ($w in $wavs) { py -3.11 -X utf8 aoi_voice_lab.py process $w.FullName }
} else {
    Write-Host "output\長尺\voicevox_aoi\ にWAVが見つからない(パス確認を)" -ForegroundColor Yellow
}

Write-Host "=== 5. アオイ定型ゼリフ30本をB4声で合成 ===" -ForegroundColor Cyan
py -3.11 -X utf8 aoi_greetings.py --fx B4

Write-Host ""
Write-Host "=== 完了 ===" -ForegroundColor Green
Write-Host "・候補聞き比べ    : output\voice_samples\aoi_lab\ (A=現行 と B4=採用版 を聴き比べ)"
Write-Host "・本編(採用声)   : output\長尺\voicevox_aoi\*_SIG.wav (DaVinciではこちらを使う)"
Write-Host "・定型ゼリフ      : output\voice_samples\aoi_stock\"
Write-Host "・モーフィング実査結果 : aoi_lab_survey.json"
Write-Host ""
Write-Host "最終ゲート: FOCUS_AOI_SIG.wav の冒頭2分を耳で確認(こもり・金属感がなければ編集へ)"
