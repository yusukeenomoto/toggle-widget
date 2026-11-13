#!/usr/bin/env python3
"""tkinter トグルスイッチで表示を切り替えるシンプルなウィジェット (macOS / Windows 対応)

- トグル OFF : 一覧表示 (Treeview)
- トグル ON  : JSON 表示 (整形されたテキスト)
- データとスイッチの状態は data.json に保存される
  (Windows: %APPDATA%\\ToggleView / macOS: ~/Library/Application Support/ToggleView)
"""

import copy
import json
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

APP_NAME = "ToggleView"

# ---- OS ごとの違いをここに集約 ----
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"
HAND_CURSOR = "pointinghand" if IS_MAC else "hand2"   # pointinghand は macOS 専用
MONO_FONT = "Menlo" if IS_MAC else ("Consolas" if IS_WIN else "DejaVu Sans Mono")


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

DEFAULT_DATA = {
    "settings": {"json_view": False},
    "items": [
        {"id": 1, "name": "りんご", "price": 120, "tags": ["果物", "赤"]},
        {"id": 2, "name": "バナナ", "price": 80, "tags": ["果物", "黄"]},
        {"id": 3, "name": "牛乳", "price": 210, "tags": ["飲料"]},
    ],
}


# --------------------------------------------------------------------------
# JSON の読み書き
# --------------------------------------------------------------------------
def load_data() -> dict:
    """data.json を読み込む。無い・壊れている場合はデフォルトを返す。"""
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("settings", {}).setdefault("json_view", False)
            data.setdefault("items", [])
            return data
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
    W, H, PAD = 52, 28, 3
    COLOR_ON = "#34C759"   # macOS のグリーン
    COLOR_OFF = "#C7C7CC"

    def __init__(self, master, value=False, command=None):
        super().__init__(
            master,
            width=self.W,
            height=self.H,
            bg=self._parent_bg(master),
            highlightthickness=0,
            cursor=HAND_CURSOR,
        )
        self._value = bool(value)
        self._command = command
        self._after_id = None
        self._x = self._target_x()
        self._draw()
        self.bind("<Button-1>", lambda _e: self.toggle())

    @staticmethod
    def _parent_bg(master) -> str:
        try:
            return master.winfo_toplevel().cget("bg")
        except tk.TclError:
            return "#ececec"

    def _target_x(self) -> float:
        d = self.H - 2 * self.PAD
        return self.W - self.PAD - d if self._value else self.PAD

    def _draw(self) -> None:
        self.delete("all")
        w, h, pad = self.W, self.H, self.PAD
        color = self.COLOR_ON if self._value else self.COLOR_OFF
        # トラック (角丸の長方形)
        self.create_oval(0, 0, h, h, fill=color, outline="")
        self.create_oval(w - h, 0, w, h, fill=color, outline="")
        self.create_rectangle(h / 2, 0, w - h / 2, h, fill=color, outline="")
        # つまみ
        d = h - 2 * pad
        self.create_oval(
            self._x, pad, self._x + d, pad + d, fill="white", outline="#d0d0d0"
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
        self.title("Toggle View")
        self.geometry("420x320")
        self.minsize(360, 260)

        self.data = load_data()

        # ヘッダー: ラベル + トグル + 現在のモード名
        header = ttk.Frame(self, padding=(12, 12, 12, 6))
        header.pack(fill="x")
        ttk.Label(header, text="JSON表示").pack(side="left")
        self.toggle = ToggleSwitch(
            header,
            value=self.data["settings"]["json_view"],
            command=self.on_toggle,
        )
        self.toggle.pack(side="left", padx=10)
        self.mode_label = ttk.Label(header, text="")
        self.mode_label.pack(side="left")

        # 表示領域
        body = ttk.Frame(self, padding=(12, 0, 12, 12))
        body.pack(fill="both", expand=True)

        # 一覧ビュー
        self.list_view = ttk.Treeview(
            body, columns=("name", "price", "tags"), show="headings"
        )
        for col, title, width in (
            ("name", "名前", 120),
            ("price", "価格", 70),
            ("tags", "タグ", 140),
        ):
            self.list_view.heading(col, text=title)
            self.list_view.column(col, width=width, anchor="w")

        # JSON ビュー
        self.json_view = tk.Text(body, wrap="none", font=(MONO_FONT, 12))

        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---- 表示更新 ----
    def refresh(self) -> None:
        use_json = self.data["settings"]["json_view"]
        self.mode_label.config(text="JSON" if use_json else "一覧")

        if use_json:
            self.list_view.pack_forget()
            self.json_view.config(state="normal")
            self.json_view.delete("1.0", "end")
            self.json_view.insert(
                "1.0", json.dumps(self.data, ensure_ascii=False, indent=2)
            )
            self.json_view.config(state="disabled")
            self.json_view.pack(fill="both", expand=True)
        else:
            self.json_view.pack_forget()
            self.list_view.delete(*self.list_view.get_children())
            for item in self.data["items"]:
                self.list_view.insert(
                    "",
                    "end",
                    values=(
                        item.get("name", ""),
                        item.get("price", ""),
                        ", ".join(item.get("tags", [])),
                    ),
                )
            self.list_view.pack(fill="both", expand=True)

    # ---- イベント ----
    def on_toggle(self, value: bool) -> None:
        self.data["settings"]["json_view"] = value
        save_data(self.data)
        self.refresh()

    def on_close(self) -> None:
        save_data(self.data)
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
