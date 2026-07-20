@echo off
REM install_voicevox.bat — ダブルクリックで VOICEVOX 環境を一発セットアップ
REM やること: 管理者昇格 → 実行ポリシー回避 → setup_new_pc.ps1 実行

setlocal
cd /d "%~dp0"

REM --- 管理者権限チェック ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 管理者権限が必要です。UAC ダイアログで「はい」を押してください...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================
echo   VOICEVOX 自動セットアップ
echo ============================================
echo.
echo Python 3.11 / ffmpeg / yt-dlp / git / VOICEVOX を
echo winget でまとめてインストールします。所要 15-30 分程度。
echo.
pause

REM --- SmartScreen ブロック解除 ---
powershell -NoProfile -Command "Get-ChildItem -Path '%~dp0' -Recurse | Unblock-File"

REM --- PS1 スクリプト実行 ---
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_new_pc.ps1"

set RC=%errorlevel%
echo.
if %RC% neq 0 (
    echo ============================================
    echo   セットアップが途中で失敗しました(コード %RC%)
    echo   ログを見て手動で続きを進めてください。
    echo ============================================
) else (
    echo ============================================
    echo   セットアップ完了!
    echo   次のステップ: VOICEVOX を起動して声を確認
    echo ============================================
)
echo.
pause
endlocal
