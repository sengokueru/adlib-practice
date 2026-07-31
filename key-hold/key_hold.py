# -*- coding: utf-8 -*-
"""
キー押しっぱなしツール (Key Hold Tool)

Enterキーや任意のキーを「押しっぱなし」または「連打」状態にするツール。
ON/OFFの切替キー(ホットキー)は好きなキーに変更できます。
ウィンドウを閉じてもタスクトレイに常駐し、切替キーは効き続けます。

必要ライブラリ: pynput, pystray, pillow
    pip install pynput pystray pillow

起動:
    python key_hold.py
"""

import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from pynput import keyboard
    from pynput.keyboard import Controller, Key, KeyCode
except ImportError:
    print("pynput がインストールされていません。以下を実行してください:")
    print("  pip install pynput")
    sys.exit(1)

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except Exception:
    # 未インストール時だけでなく、トレイ機能が使えない環境でも本体は動かす
    HAS_TRAY = False

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

# 切替の最短間隔(秒)。取りこぼしではなく誤爆を防ぐための最低限の値
TOGGLE_COOLDOWN = 0.2

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
            # vk も残しておくと、次回起動後も Ctrl 併用時の照合が効く
            return f"char:{key.char}:{key.vk if key.vk is not None else ''}"
        return "vk:" + str(key.vk)
    return "key:" + key.name


def key_from_store(text: str):
    """保存された文字列をキーオブジェクトに戻す。失敗したらNone。"""
    try:
        kind, _, value = text.partition(":")
        if kind == "char":
            char, _, vk = value.partition(":")
            return KeyCode(char=char, vk=int(vk) if vk else None)
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
        # vk は Ctrl 併用時の照合に使うので保持したままにする
        return KeyCode(char=key.char.lower(), vk=key.vk)
    return key


def same_key(a, b) -> bool:
    """2つのキーが同じか判定する。

    Ctrlなどを押しっぱなしにしていると、文字キーの char が制御文字(Ctrl+J → '\\n')
    に化けて一致しなくなる。そのため vk(キーの物理的な番号)でも照合する。
    """
    if normalize(a) == normalize(b):
        return True
    # normalize は char を作り直すため vk が落ちる。元のキーのまま突き合わせる
    va, vb = getattr(a, "vk", None), getattr(b, "vk", None)
    return va is not None and va == vb


class KeyHoldApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.controller = Controller()
        self.active = False
        self.worker = None
        self.stop_event = threading.Event()

        self.toggle_key = DEFAULT_TOGGLE
        self.capturing = False       # 切替キーの設定待ち状態
        self.toggle_key_down = False  # 切替キーが物理的に押されたままか
        self.last_toggle_at = 0.0

        root.title("キー押しっぱなしツール")
        root.geometry("360x480")
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

        ttk.Label(
            root,
            text="※ ウィンドウを閉じてもタスクトレイに常駐し、切替キーは効き続けます",
            foreground="gray", wraplength=330, font=("", 8)
        ).pack(**pad)

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", side="bottom", padx=12, pady=8)
        ttk.Button(bottom, text="トレイにしまう",
                   command=self.hide_to_tray).pack(side="left")
        ttk.Button(bottom, text="アプリを終了",
                   command=self.quit_app).pack(side="right")

        self.load_config()
        self.refresh_idle_text()

        # グローバルキー監視
        self.listener = keyboard.Listener(on_press=self.on_global_key,
                                          on_release=self.on_global_release)
        self.listener.daemon = True
        self.listener.start()

        self.tray = None
        self.tray_notified = False
        self.setup_tray()

        # ✕ を押してもアプリは終了せず、トレイに隠れるだけ
        root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

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

    # ---------- タスクトレイ常駐 ----------

    def make_tray_image(self):
        """状態がひと目で分かるトレイアイコンを描く(停止=緑 / 動作中=赤)。"""
        color = "#e53935" if self.active else "#4caf50"
        image = Image.new("RGB", (64, 64), "#263238")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=12, fill=color)
        draw.rectangle((26, 20, 38, 44), fill="white")  # キーを模した図形
        return image

    def setup_tray(self):
        if not HAS_TRAY:
            return
        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: "停止" if self.active else "開始",
                lambda: self.root.after(0, self.toggle),
                default=True,
            ),
            pystray.MenuItem("設定ウィンドウを開く",
                             lambda: self.root.after(0, self.show_window)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("終了", lambda: self.root.after(0, self.quit_app)),
        )
        try:
            self.tray = pystray.Icon(
                "key_hold", self.make_tray_image(), "キー押しっぱなしツール", menu
            )
            threading.Thread(target=self.tray.run, daemon=True).start()
        except Exception:
            self.tray = None  # トレイが使えない環境でも本体は動かす

    def refresh_tray(self):
        if not self.tray:
            return
        state = "動作中" if self.active else "停止中"
        try:
            self.tray.icon = self.make_tray_image()
            self.tray.title = (
                f"キー押しっぱなしツール — {state}"
                f"({key_to_text(self.toggle_key)}で切替)"
            )
        except Exception:
            pass

    def hide_to_tray(self):
        """✕ で閉じたときはトレイに隠すだけ(切替キーは効き続ける)。"""
        if not self.tray:
            self.quit_app()  # トレイが無い環境では従来どおり終了
            return
        self.save_config()
        self.root.withdraw()
        if not self.tray_notified:
            self.tray_notified = True
            try:
                self.tray.notify(
                    f"タスクトレイで動作中です。"
                    f"{key_to_text(self.toggle_key)} で切替できます。",
                    "キー押しっぱなしツール",
                )
            except Exception:
                pass

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_app(self):
        self.stop()
        self.save_config()
        self.listener.stop()
        if self.tray:
            self.tray.stop()
        self.root.destroy()

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
        self.refresh_tray()

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
            self.toggle_key_down = True  # 登録直後の離すまでを押下中として扱う
            self.root.after(0, self.finish_capture, key)
            return

        if not same_key(key, self.toggle_key):
            return

        # キーを押しっぱなしにするとOSが同じ押下イベントを連続で送ってくるため、
        # 一度離すまでは次の切替を受け付けない(ON/OFFの高速な往復を防ぐ)
        if self.toggle_key_down:
            return
        self.toggle_key_down = True

        now = time.monotonic()
        if now - self.last_toggle_at < TOGGLE_COOLDOWN:
            return
        self.last_toggle_at = now
        self.root.after(0, self.toggle)

    def on_global_release(self, key):
        if same_key(key, self.toggle_key):
            self.toggle_key_down = False

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
        self.refresh_tray()

    def stop(self):
        self.stop_event.set()  # 先に合図を出して即座に離させる
        self.active = False
        if self.worker:
            self.worker.join(timeout=0.5)
            self.worker = None
        # 保険:ワーカーが止まりきらなくてもキーは離しておく
        try:
            self.controller.release(self.current_key())
        except Exception:
            pass
        self.button.config(bg="#4caf50")
        self.refresh_idle_text()
        self.refresh_tray()

    def run_worker(self, key, mode, interval):
        try:
            if mode == "hold":
                self.controller.press(key)
                self.stop_event.wait()  # 停止まで押しっぱなし
            else:
                while not self.stop_event.is_set():
                    self.controller.press(key)
                    self.controller.release(key)
                    self.stop_event.wait(interval)
        finally:
            # 何があってもキーは必ず離す(押されっぱなしで固まるのを防ぐ)
            try:
                self.controller.release(key)
            except Exception:
                pass

    # 旧名の互換用
    on_close = quit_app


if __name__ == "__main__":
    root = tk.Tk()
    KeyHoldApp(root)
    root.mainloop()
