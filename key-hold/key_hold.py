# -*- coding: utf-8 -*-
"""
キー押しっぱなしツール (Key Hold Tool)

Enterキーや任意のキーを「押しっぱなし」または「連打」状態にするツール。
ON/OFFの切替キー(ホットキー)は好きなキーに変更できます。

必要ライブラリ: pynput
    pip install pynput

起動:
    python key_hold.py
"""

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from pynput import keyboard
    from pynput.keyboard import Controller, Key, KeyCode
except ImportError:
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

DEFAULT_TOGGLE = Key.f6

# 設定ファイル(実行ファイルと同じ場所ではなくユーザーフォルダに保存)
CONFIG_PATH = os.path.join(
    os.path.expanduser("~"), ".key_hold_config.json"
)


def key_to_text(key) -> str:
    """キーオブジェクトを画面表示用の名前にする。"""
    if isinstance(key, KeyCode):
        if key.char:
            return key.char.upper()
        return f"<{key.vk}>"
    name = getattr(key, "name", str(key))
    return name.upper() if len(name) <= 3 else name.capitalize()


def key_to_store(key) -> str:
    """キーオブジェクトを設定ファイル保存用の文字列にする。"""
    if isinstance(key, KeyCode):
        if key.char:
            return "char:" + key.char
        return "vk:" + str(key.vk)
    return "key:" + key.name


def key_from_store(text: str):
    """保存された文字列をキーオブジェクトに戻す。失敗したらNone。"""
    try:
        kind, _, value = text.partition(":")
        if kind == "char":
            return KeyCode.from_char(value)
        if kind == "vk":
            return KeyCode.from_vk(int(value))
        if kind == "key":
            return getattr(Key, value)
    except (AttributeError, ValueError):
        pass
    return None


def normalize(key):
    """左右のShift/Ctrl/Altを区別せず比較できる形にそろえる。"""
    pairs = {
        Key.shift_l: Key.shift, Key.shift_r: Key.shift,
        Key.ctrl_l: Key.ctrl, Key.ctrl_r: Key.ctrl,
        Key.alt_l: Key.alt, Key.alt_r: Key.alt, Key.alt_gr: Key.alt,
    }
    key = pairs.get(key, key)
    if isinstance(key, KeyCode) and key.char:
        return KeyCode.from_char(key.char.lower())
    return key


class KeyHoldApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.controller = Controller()
        self.active = False
        self.worker = None
        self.stop_event = threading.Event()

        self.toggle_key = DEFAULT_TOGGLE
        self.capturing = False  # 切替キーの設定待ち状態

        root.title("キー押しっぱなしツール")
        root.geometry("360x400")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        pad = {"padx": 12, "pady": 6}

        # 押しっぱなしにするキー
        ttk.Label(root, text="押しっぱなしにするキー:").pack(anchor="w", **pad)
        self.key_var = tk.StringVar(value="Enter")
        ttk.Combobox(
            root, textvariable=self.key_var,
            values=list(SPECIAL_KEYS.keys()), state="readonly"
        ).pack(fill="x", **pad)

        # モード
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

        ttk.Separator(root).pack(fill="x", padx=12, pady=4)

        # ON/OFF切替キーの設定
        hotkey_frame = ttk.Frame(root)
        hotkey_frame.pack(fill="x", **pad)
        ttk.Label(hotkey_frame, text="ON/OFF切替キー:").pack(side="left")
        self.hotkey_label = ttk.Label(hotkey_frame, text="F6",
                                      font=("", 10, "bold"))
        self.hotkey_label.pack(side="left", padx=6)
        self.capture_button = ttk.Button(hotkey_frame, text="変更",
                                         command=self.begin_capture)
        self.capture_button.pack(side="right")

        # 開始/停止
        self.button = tk.Button(
            root, text="開始", font=("", 14, "bold"),
            bg="#4caf50", fg="white", command=self.toggle
        )
        self.button.pack(fill="x", padx=12, pady=10, ipady=6)

        self.status = ttk.Label(root, text="", foreground="gray",
                                wraplength=330)
        self.status.pack(**pad)

        self.load_config()
        self.refresh_idle_text()

        # グローバルキー監視
        self.listener = keyboard.Listener(on_press=self.on_global_key)
        self.listener.daemon = True
        self.listener.start()

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- 設定の保存/読み込み ----------

    def load_config(self):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return

        key = key_from_store(data.get("toggle_key", ""))
        if key is not None:
            self.toggle_key = key
        if data.get("target_key") in SPECIAL_KEYS:
            self.key_var.set(data["target_key"])
        if data.get("mode") in ("hold", "repeat"):
            self.mode_var.set(data["mode"])
        if data.get("interval"):
            self.interval_var.set(str(data["interval"]))

        self.hotkey_label.config(text=key_to_text(self.toggle_key))

    def save_config(self):
        data = {
            "toggle_key": key_to_store(self.toggle_key),
            "target_key": self.key_var.get(),
            "mode": self.mode_var.get(),
            "interval": self.interval_var.get(),
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass  # 保存できなくても動作は続ける

    # ---------- 切替キーの変更 ----------

    def begin_capture(self):
        if self.active:
            self.stop()
        self.capturing = True
        self.capture_button.config(text="待機中…")
        self.status.config(text="新しく使いたいキーを押してください(Escで取消)",
                           foreground="#1565c0")

    def finish_capture(self, key):
        self.capturing = False
        self.capture_button.config(text="変更")

        if key == Key.esc:
            self.refresh_idle_text()
            return

        self.toggle_key = normalize(key)
        self.hotkey_label.config(text=key_to_text(self.toggle_key))
        self.save_config()

        if self.toggle_key == normalize(self.current_key()):
            messagebox.showwarning(
                "注意",
                "押しっぱなしにするキーと切替キーが同じです。\n"
                "動作が不安定になるため、別のキーをおすすめします。"
            )
        self.refresh_idle_text()

    # ---------- 動作 ----------

    def current_key(self):
        value = SPECIAL_KEYS[self.key_var.get()]
        return KeyCode.from_char(value) if isinstance(value, str) else value

    def refresh_idle_text(self):
        name = key_to_text(self.toggle_key)
        self.status.config(
            text=f"停止中 — {name} でどこからでも切替できます", foreground="gray")
        self.button.config(text=f"開始 ({name})")

    def on_global_key(self, key):
        if self.capturing:
            self.root.after(0, self.finish_capture, key)
        elif normalize(key) == self.toggle_key:
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
        self.save_config()

        self.worker = threading.Thread(
            target=self.run_worker, args=(key, mode, interval), daemon=True
        )
        self.worker.start()

        name = key_to_text(self.toggle_key)
        mode_text = "押しっぱなし" if mode == "hold" else "連打"
        self.button.config(text=f"停止 ({name})", bg="#e53935")
        self.status.config(text=f"{self.key_var.get()} を{mode_text}中…",
                           foreground="#e53935")

    def stop(self):
        self.active = False
        self.stop_event.set()
        if self.worker:
            self.worker.join(timeout=1)
            self.worker = None
        self.button.config(bg="#4caf50")
        self.refresh_idle_text()

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
        self.save_config()
        self.listener.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    KeyHoldApp(root)
    root.mainloop()
