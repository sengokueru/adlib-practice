@echo off
rem アドリブ練習アプリをローカル配信するサーバー
rem 同じWi-Fiのスマホから http://<このPCのIP>:8734/ で開けます
cd /d "%~dp0"
echo このPCのIPアドレス:
ipconfig | findstr /C:"IPv4"
echo.
echo スマホで http://上のIPアドレス:8734/ を開いてください
echo 停止するには Ctrl+C
npx -y http-server . -p 8734 -c-1
