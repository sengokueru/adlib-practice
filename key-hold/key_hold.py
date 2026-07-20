# -*- coding: utf-8 -*-
"""
キー押しっぱなしツール (Key Hold Tool)

Enterキーや任意のキーを「押しっぱなし」または「連打」状態にするツール。
F6キーでどのアプリにいてもON/OFFを切り替えられます。

必要ライブラリ: pynput
    pip install pynput

起動:
    python key_hold.py
"""

import threading
import time
import tkinter as tk
from tkinter import ttk

try:
    from pynput import keyboard
    from pynput.keyboard import Controller, Key
except ImportError:
    import sys
    print("pynput がインストールされていません。以下を実行してください:")
    print("  pip install pynput")
    sys.exit(1)

# 選べる特殊キー
SPECIAL_KEYS = {
    "Enter": Key.enter,
    "Space": Key.space,
    "Shift": Key.shift,
    "Ctrl": Key.ctrl,
    "Alt": Key.alt,
    "Tab": Key.tab,
    "↑ (上)": Key.up,
    "↓ (下)": Key.down,
    "← (左)": Key.left,
    "→ (右)": Key.right,
    "W": "w",
    "A": "a",
    "S": "s",
    "D": "d",
}

TOGGLE_KEY = keyboard.Key.f6  # グローバル切替キー


class KeyHoldApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.controller = Controller()
        self.active = False
        self.worker = None
        self.stop_event = threading.Event()

        root.title("キー押しっぱなしツール")
        root.geometry("340x300")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        pad = {"padx": 12, "pady": 6}

        # キー選択
        ttk.Label(root, text="押しっぱなしにするキー:").pack(anchor="w", **pad)
        self.key_var = tk.StringVar(value="Enter")
        key_box = ttk.Combobox(
            root, textvariable=self.key_var,
            values=list(SPECIAL_KEYS.keys()), state="readonly"
        )
        key_box.pack(fill="x", **pad)

        # モード選択
        self.mode_var = tk.StringVar(value="hold")
        mode_frame = ttk.Frame(root)
        mode_frame.pack(anchor="w", **pad)
        ttk.Radiobutton(mode_frame, text="押しっぱなし(ホールド)",
                        variable=self.mode_var, value="hold").pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="連打(リピート)",
                        variable=self.mode_var, value="repeat").pack(anchor="w")

        # 連打間隔
        interval_frame = ttk.Frame(root)
        interval_frame.pack(anchor="w", **pad)
        ttk.Label(interval_frame, text="連打間隔(秒):").pack(side="left")
        self.interval_var = tk.StringVar(value="0.05")
        ttk.Entry(interval_frame, textvariable=self.interval_var,
                  width=6).pack(side="left", padx=6)

        # 開始/停止ボタン
        self.button = tk.Button(
            root, text="開始 (F6)", font=("", 14, "bold"),
            bg="#4caf50", fg="white", command=self.toggle
        )
        self.button.pack(fill="x", padx=12, pady=10, ipady=6)

        self.status = ttk.Label(root, text="停止中 — F6でどこからでも切替できます",
                                foreground="gray")
        self.status.pack(**pad)

        # グローバルホットキー (F6)
        self.listener = keyboard.Listener(on_press=self.on_global_key)
        self.listener.daemon = True
        self.listener.start()

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def current_key(self):
        return SPECIAL_KEYS[self.key_var.get()]

    def on_global_key(self, key):
        if key == TOGGLE_KEY:
            # Tkinterのメインスレッドで実行
            self.root.after(0, self.toggle)

    def toggle(self):
        if self.active:
            self.stop()
        else:
            self.start()

    def start(self):
        try:
            interval = max(0.01, float(self.interval_var.get()))
        except ValueError:
            interval = 0.05
            self.interval_var.set("0.05")

        self.active = True
        self.stop_event.clear()
        key = self.current_key()
        mode = self.mode_var.get()

        self.worker = threading.Thread(
            target=self.run_worker, args=(key, mode, interval), daemon=True
        )
        self.worker.start()

        self.button.config(text="停止 (F6)", bg="#e53935")
        label = self.key_var.get()
        mode_text = "押しっぱなし" if mode == "hold" else "連打"
        self.status.config(text=f"{label} を{mode_text}中…", foreground="#e53935")

    def stop(self):
        self.active = False
        self.stop_event.set()
        if self.worker:
            self.worker.join(timeout=1)
            self.worker = None
        self.button.config(text="開始 (F6)", bg="#4caf50")
        self.status.config(text="停止中 — F6でどこからでも切替できます",
                           foreground="gray")

    def run_worker(self, key, mode, interval):
        if mode == "hold":
            self.controller.press(key)
            self.stop_event.wait()  # 停止まで押しっぱなし
            self.controller.release(key)
        else:
            while not self.stop_event.is_set():
                self.controller.press(key)
                self.controller.release(key)
                self.stop_event.wait(interval)

    def on_close(self):
        self.stop()
        self.listener.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    KeyHoldApp(root).mainloop()
