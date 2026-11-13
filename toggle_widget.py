#!/usr/bin/env python3
"""tkinter トグルスイッチで A / B の表示を切り替えるシンプルなウィジェット (macOS / Windows 対応)

- ヘッダー : タイトル
- その下   : トグルの行。右端にトグルスイッチ、その左に A / B のテキスト
- タイトル・トグルの数とテキスト・デザイン・スイッチの状態は data.json で扱う
  (Windows: %APPDATA%\\toggle-widget / macOS: ~/Library/Application Support/toggle-widget)
"""

import copy
import json
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont

APP_NAME = "toggle-widget"

# ---- OS ごとの違いをここに集約 ----
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"
HAND_CURSOR = "pointinghand" if IS_MAC else "hand2"   # pointinghand は macOS 専用


def get_data_file() -> Path:
    """OS ごとのユーザー領域に data.json の保存先を作る。"""
    if IS_WIN:
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif IS_MAC:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    folder = base / APP_NAME
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        folder = Path.cwd()  # 作れない場合はカレントディレクトリにフォールバック
    return folder / "data.json"


DATA_FILE = get_data_file()

# toggles の 1 件分。value が false なら a、true なら b を表示する
DEFAULT_TOGGLE = {"a": "", "b": "", "value": False}

DEFAULT_DATA = {
    "title": "Toggle Widget",
    "toggles": [
        {"a": "A: 通知を受け取らない", "b": "B: 通知を受け取る", "value": False},
        {"a": "A: ライトモード", "b": "B: ダークモード", "value": False},
        {"a": "A: 自動保存しない", "b": "B: 自動保存する", "value": True},
    ],
    "design": {
        # height が null ならトグルの数に合わせて自動で決める
        "window": {"width": 420, "height": None, "bg": "#F2F2F7"},
        # family が null なら OS の標準フォント
        "font": {"family": None, "title_size": 16, "text_size": 13},
        "header": {"bg": "#2C2C2E", "fg": "#FFFFFF", "padding": 16},
        # fg_off はトグルが false (A を表示) のときの文字色。null なら fg と同じ
        "row": {"bg": "#FFFFFF", "fg": "#1C1C1E", "fg_off": None,
                "padding": 12, "separator": "#D1D1D6"},
        "toggle": {
            "width": 52,
            "height": 28,
            "on_color": "#34C759",   # macOS のグリーン
            "off_color": "#C7C7CC",
            "knob_color": "#FFFFFF",
        },
    },
}


# --------------------------------------------------------------------------
# JSON の読み書き
# --------------------------------------------------------------------------
def merge_defaults(data: dict, defaults: dict) -> dict:
    """defaults にあって data に無いキーを補う (入れ子の dict も)。"""
    for key, value in defaults.items():
        if isinstance(value, dict):
            if not isinstance(data.get(key), dict):
                data[key] = {}
            merge_defaults(data[key], value)
        else:
            data.setdefault(key, copy.deepcopy(value))
    return data


def normalize(data: dict) -> dict:
    """足りない項目を既定値で補い、toggles を dict のリストにそろえる。"""
    merge_defaults(data, DEFAULT_DATA)
    if not isinstance(data["toggles"], list):
        data["toggles"] = copy.deepcopy(DEFAULT_DATA["toggles"])
    data["toggles"] = [
        merge_defaults(t, DEFAULT_TOGGLE) for t in data["toggles"] if isinstance(t, dict)
    ]
    return data


def load_data() -> dict:
    """data.json を読み込む。無い・壊れている場合はデフォルトを返す。"""
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return normalize(data)
        except (json.JSONDecodeError, OSError):
            pass
    data = copy.deepcopy(DEFAULT_DATA)
    save_data(data)
    return data


def save_data(data: dict) -> None:
    try:
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"保存に失敗しました: {e}")


# --------------------------------------------------------------------------
# トグルスイッチ (Canvas で描画)
# --------------------------------------------------------------------------
class ToggleSwitch(tk.Canvas):
    PAD = 3

    def __init__(self, master, value=False, command=None, bg="#FFFFFF",
                 width=52, height=28, on_color="#34C759", off_color="#C7C7CC",
                 knob_color="#FFFFFF"):
        super().__init__(
            master,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0,
            cursor=HAND_CURSOR,
        )
        self.W, self.H = width, height
        self._on_color = on_color
        self._off_color = off_color
        self._knob_color = knob_color
        self._value = bool(value)
        self._command = command
        self._after_id = None
        self._x = self._target_x()
        self._draw()
        self.bind("<Button-1>", lambda _e: self.toggle())

    def _target_x(self) -> float:
        d = self.H - 2 * self.PAD
        return self.W - self.PAD - d if self._value else self.PAD

    def _draw(self) -> None:
        self.delete("all")
        w, h, pad = self.W, self.H, self.PAD
        color = self._on_color if self._value else self._off_color
        # トラック (角丸の長方形)
        self.create_oval(0, 0, h, h, fill=color, outline="")
        self.create_oval(w - h, 0, w, h, fill=color, outline="")
        self.create_rectangle(h / 2, 0, w - h / 2, h, fill=color, outline="")
        # つまみ
        d = h - 2 * pad
        self.create_oval(
            self._x, pad, self._x + d, pad + d, fill=self._knob_color, outline="#d0d0d0"
        )

    def _animate(self) -> None:
        target = self._target_x()
        diff = target - self._x
        if abs(diff) < 1:
            self._x = target
            self._draw()
            return
        self._x += diff * 0.4
        self._draw()
        self._after_id = self.after(16, self._animate)

    def get(self) -> bool:
        return self._value

    def set(self, value: bool, notify: bool = True) -> None:
        self._value = bool(value)
        if self._after_id:
            self.after_cancel(self._after_id)
        self._animate()
        if notify and self._command:
            self._command(self._value)

    def toggle(self) -> None:
        self.set(not self._value)


# --------------------------------------------------------------------------
# アプリ本体
# --------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.data = load_data()
        design = self.data["design"]
        win, header_d, row_d = design["window"], design["header"], design["row"]

        self.title(self.data["title"])
        self.configure(bg=win["bg"])

        family = design["font"]["family"] or tkfont.nametofont("TkDefaultFont").actual("family")
        title_font = tkfont.Font(family=family, size=design["font"]["title_size"], weight="bold")
        self.text_font = tkfont.Font(family=family, size=design["font"]["text_size"])

        # ヘッダー: タイトル
        header = tk.Frame(self, bg=header_d["bg"], padx=header_d["padding"],
                          pady=header_d["padding"] * 3 // 4)
        header.pack(fill="x")
        tk.Label(
            header, text=self.data["title"], bg=header_d["bg"], fg=header_d["fg"],
            font=title_font,
        ).pack(side="left")

        # トグルの行を並べる白いカード
        card = tk.Frame(self, bg=row_d["bg"])
        card.pack(fill="x", padx=16, pady=16)
        self.rows = []
        for i, item in enumerate(self.data["toggles"]):
            if i:
                tk.Frame(card, bg=row_d["separator"], height=1).pack(fill="x")
            self.rows.append(self._build_row(card, item))

        # 幅は設定値、高さは設定値か中身に合わせる
        self.update_idletasks()
        height = win["height"] or self.winfo_reqheight()
        self.geometry(f"{win['width']}x{height}")
        self.minsize(280, min(height, 160))

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_row(self, master, item: dict) -> tk.Label:
        """右端にトグル、その左に A / B のテキストを置いた 1 行を作る。"""
        row_d = self.data["design"]["row"]
        toggle_d = self.data["design"]["toggle"]
        pad = row_d["padding"]

        row = tk.Frame(master, bg=row_d["bg"], padx=pad, pady=pad)
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)

        label = tk.Label(
            row, bg=row_d["bg"], fg=row_d["fg"], font=self.text_font,
            anchor="w", justify="left",
        )
        label.grid(row=0, column=0, sticky="we", padx=(0, pad))

        def on_toggle(value: bool) -> None:
            item["value"] = value
            self.update_row(label, item)
            save_data(self.data)

        ToggleSwitch(
            row,
            value=item["value"],
            command=on_toggle,
            bg=row_d["bg"],
            width=toggle_d["width"],
            height=toggle_d["height"],
            on_color=toggle_d["on_color"],
            off_color=toggle_d["off_color"],
            knob_color=toggle_d["knob_color"],
        ).grid(row=0, column=1, sticky="e")

        # 行の幅に合わせてテキストを折り返す。高さの自動計算に間に合うよう、
        # 最初は設定上のウィンドウ幅 (カードの左右余白 16 を引く) から求めておく
        def wrap_for(row_width: int) -> int:
            return max(row_width - toggle_d["width"] - 3 * pad, 60)

        label.config(wraplength=wrap_for(self.data["design"]["window"]["width"] - 32))
        row.bind("<Configure>", lambda e: label.config(wraplength=wrap_for(e.width)))
        self.update_row(label, item)
        return label

    # ---- 表示更新 ----
    def update_row(self, label: tk.Label, item: dict) -> None:
        row_d = self.data["design"]["row"]
        if item["value"]:
            label.config(text=item["b"], fg=row_d["fg"])
        else:
            label.config(text=item["a"], fg=row_d["fg_off"] or row_d["fg"])

    # ---- イベント ----
    def on_close(self) -> None:
        save_data(self.data)
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
