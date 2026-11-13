#!/usr/bin/env python3
"""tkinter トグルスイッチで A / B の表示を切り替えるシンプルなウィジェット (macOS / Windows 対応)

- ヘッダー : タイトルと、右端にリストのスイッチを一括で false にするスイッチ
- その下   : トグルの行。右端にトグルスイッチ、その左に A / B のテキスト。
             textbox が true の行は、その下にテキストボックスを置く
- フッター : data.json を開く / フォルダを表示 / スキンを選ぶ
- タイトルはヘッダーに出すので、ウインドウのタイトルバーには出さない
- 中身 (タイトル・トグル・状態・テキスト・ウインドウの大きさ) は data.json、
  見た目 (色・フォント・余白) はスキンで扱う
    data.json      : Windows %APPDATA%\\toggle-widget / macOS ~/Library/Application Support/toggle-widget
    skins/<名前>.json : data.json と同じフォルダの skins の中。標準のスキンはコードに内蔵
- data.json と使用中のスキンを外で編集して保存すると、すぐ読み直して画面に反映する。
  読めない・値がおかしいときはファイルを上書きせず、場所を示して直されるのを待つ
- メニューバー (macOS) とフッター・エラー表示は OS の言語設定に合わせて日本語 / 英語
"""

import copy
import ctypes
import json
import os
import shutil
import subprocess
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


def skins_dir() -> Path:
    return DATA_FILE.parent / "skins"


def bundled_skins_dir() -> Path:
    """アプリに同梱したサンプルスキンの場所 (PyInstaller で固めたときは展開先)。"""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "skins"


def prepare_skins_dir() -> None:
    """skins フォルダが無ければ作り、同梱のサンプルスキンを入れる。

    消したサンプルが次の起動で戻ってこないよう、入れるのはフォルダを作るときだけ。
    """
    folder = skins_dir()
    if folder.exists():
        return
    try:
        folder.mkdir(parents=True)
        for src in sorted(bundled_skins_dir().glob("*.json")):
            shutil.copyfile(src, folder / src.name)
    except OSError as e:
        print(f"サンプルスキンを用意できませんでした: {e}")


# toggles の 1 件分。value が false なら a、true なら b を表示する。
# textbox が true なら行の下にテキストボックスを置き、入力内容を text に保存する
DEFAULT_TOGGLE = {"a": "", "b": "", "value": False, "textbox": False, "text": ""}

DEFAULT_DATA = {
    "title": "Toggle Widget",
    "skin": "default",     # skins/<名前>.json の名前。"default" は内蔵の標準スキン
    # height が null ならトグルの数に合わせて自動で決める
    "window": {"width": 420, "height": None},
    "toggles": [
        {"a": "A: 通知を受け取らない", "b": "B: 通知を受け取る", "value": False,
         "textbox": True, "text": ""},
        {"a": "A: ライトモード", "b": "B: ダークモード", "value": False},
        {"a": "A: 自動保存しない", "b": "B: 自動保存する", "value": True},
    ],
}

# ---- スキン ----
DEFAULT_SKIN = "default"
SKIN_FORMAT = 1   # スキンファイルの形式。キーの形を変えるときに上げる

# 標準スキン。スキンファイルに書かれていないキーはここから補う
DEFAULT_DESIGN = {
    "window": {"bg": "#F2F2F7"},
    # family が null なら OS の標準フォント
    "font": {"family": None, "title_size": 16, "text_size": 13, "footer_size": 11},
    # align はタイトルの位置: "left" / "center" / "right"
    "header": {"bg": "#2C2C2E", "fg": "#FFFFFF", "padding": 16, "align": "left"},
    # fg_off はトグルが false (A を表示) のときの文字色。null なら fg と同じ
    "row": {"bg": "#FFFFFF", "fg": "#1C1C1E", "fg_off": None,
            "padding": 12, "separator": "#D1D1D6"},
    # width / height / radius はヘッダーの一括 OFF スイッチにも使う
    "toggle": {
        "width": 52,
        "height": 28,
        "radius": None,              # 角丸の半径。null なら丸い形、0 なら四角
        "on_color": "#34C759",   # macOS のグリーン
        "off_color": "#C7C7CC",
        "knob_color": "#FFFFFF",
        "knob_outline": "#D0D0D0",   # つまみの縁の色。null なら縁なし
    },
    # ヘッダー右端の一括 OFF スイッチ。大きさと形は toggle と同じ
    "header_toggle": {
        "on_color": "#0A84FF",   # リストのスイッチと見分けるため青
        "off_color": "#636366",  # 暗いヘッダーの上でも見える灰色
        "knob_color": "#FFFFFF",
        "knob_outline": "#D0D0D0",
    },
    "textbox": {
        "bg": "#F2F2F7",
        "fg": "#1C1C1E",
        "border": "#D1D1D6",
        "focus_border": "#0A84FF",
    },
    "footer": {"link_fg": "#007AFF"},
}

# アプリの文言。{app} はアプリ名、{file} はファイル名に置き換わる
UI_TEXT = {
    "en": {
        "about": "About {app}", "file": "File", "close": "Close", "edit": "Edit",
        "cut": "Cut", "copy": "Copy", "paste": "Paste", "select_all": "Select All",
        "window": "Window",
        "open_file": "Open data.json", "show_folder": "Show Folder", "skin_menu": "Skin ▾",
        "skin_default": "Standard", "open_skins": "Open Skins Folder",
        "error_json": "Can't read {file}: line {line}, column {col} ({msg}).",
        "error_encoding": "Can't read {file}. Save it as UTF-8.",
        "error_read": "Can't read {file} ({msg}).",
        "error_top": "{file} must be a single {{ ... }} object.",
        "error_values": "{file} has a value that can't be used ({msg}).",
        "error_skin_missing": "Skin \"{name}\" was not found ({file}).",
        "error_skin_format": "{file} is made for a newer version of this app.",
        "error_skin_design": "{file} has no \"design\": {{ ... }}.",
        "suffix_data": "Fix it and save to apply. Until then, changes in the app are not saved.",
        "suffix_skin": "Fix it and save to apply. Until then, the standard skin is used.",
    },
    "ja": {
        "about": "{app}について", "file": "ファイル", "close": "閉じる", "edit": "編集",
        "cut": "カット", "copy": "コピー", "paste": "ペースト", "select_all": "すべてを選択",
        "window": "ウインドウ",
        "open_file": "data.json を開く", "show_folder": "フォルダを表示", "skin_menu": "スキン ▾",
        "skin_default": "標準", "open_skins": "スキンフォルダを開く",
        "error_json": "{file} の {line} 行目 {col} 文字目が読めません ({msg})。",
        "error_encoding": "{file} を読めません。文字コードを UTF-8 にして保存してください。",
        "error_read": "{file} を読めません ({msg})。",
        "error_top": "{file} は全体を {{ }} で囲んだ形にしてください。",
        "error_values": "{file} に使えない値があります ({msg})。",
        "error_skin_missing": "スキン「{name}」が見つかりません ({file})。",
        "error_skin_format": "{file} はこのアプリより新しい版向けのスキンです。",
        "error_skin_design": "{file} に \"design\": {{ }} がありません。",
        "suffix_data": "直して保存するとすぐ反映されます。それまでアプリでの変更は保存されません。",
        "suffix_skin": "直して保存するとすぐ反映されます。それまで標準のスキンで表示します。",
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


def deep_update(base: dict, override: dict) -> dict:
    """override の値で base を上書きする (入れ子の dict はキーごと)。"""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def normalize(data: dict) -> dict:
    """足りない項目を既定値で補い、toggles を dict のリストにそろえる。"""
    merge_defaults(data, DEFAULT_DATA)
    if not isinstance(data["toggles"], list):
        data["toggles"] = copy.deepcopy(DEFAULT_DATA["toggles"])
    data["toggles"] = [
        merge_defaults(t, DEFAULT_TOGGLE) for t in data["toggles"] if isinstance(t, dict)
    ]
    return data


def default_data() -> dict:
    return normalize(copy.deepcopy(DEFAULT_DATA))


def read_json(path: Path, label: str):
    """JSON ファイルを読む。(中身, error) を返す。ファイルが無ければ (None, None)。

    error は (UI_TEXT のキー, 埋め込む値の dict)。
    """
    try:
        # Windows のメモ帳が付けることのある BOM も読めるよう utf-8-sig にする
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, None
    except json.JSONDecodeError as e:
        return None, ("error_json", {"file": label, "line": e.lineno, "col": e.colno, "msg": e.msg})
    except UnicodeDecodeError:
        return None, ("error_encoding", {"file": label})
    except OSError as e:
        return None, ("error_read", {"file": label, "msg": e.strerror or e})


def write_json(path: Path, obj: dict) -> bool:
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"保存に失敗しました: {e}")
        return False


def save_data(data: dict) -> bool:
    return write_json(DATA_FILE, data)


def stamp_of(path):
    """外で書き換えられたかを見分けるための (更新日時, サイズ)。無ければ None。"""
    if path is None:
        return None
    try:
        st = path.stat()
    except OSError:
        return None
    return st.st_mtime_ns, st.st_size


def file_stamp():
    return stamp_of(DATA_FILE)


def migrate_old_design(data: dict) -> bool:
    """旧形式 (data.json に design を持つ) を新形式に移す。移したら True。

    見た目を変えていなければ標準スキンに、変えていれば skins/my-skin.json に移す。
    """
    if "design" not in data:
        return False
    design = data.pop("design")
    if not isinstance(design, dict):
        return True
    window = design.get("window") if isinstance(design.get("window"), dict) else {}
    if not isinstance(data.get("window"), dict):
        data["window"] = {"width": window.get("width", 420), "height": window.get("height")}
    skin_design = copy.deepcopy(design)
    if isinstance(skin_design.get("window"), dict):
        skin_design["window"].pop("width", None)
        skin_design["window"].pop("height", None)

    if merge_defaults(copy.deepcopy(skin_design), DEFAULT_DESIGN) == DEFAULT_DESIGN:
        data.setdefault("skin", DEFAULT_SKIN)
        return True
    folder = skins_dir()
    name, n = "my-skin", 1
    while (folder / f"{name}.json").exists():
        n += 1
        name = f"my-skin-{n}"
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    skin = {"format": SKIN_FORMAT, "name": "My Skin", "design": skin_design}
    data["skin"] = name if write_json(folder / f"{name}.json", skin) else DEFAULT_SKIN
    return True


def read_data_file():
    """data.json を読む。(data, error, 旧形式から移したか) を返す。"""
    data, error = read_json(DATA_FILE, "data.json")
    if error or data is None:
        return None, error, False
    if not isinstance(data, dict):
        return None, ("error_top", {"file": "data.json"}), False
    try:
        migrated = migrate_old_design(data)
        return normalize(data), None, migrated
    except (TypeError, AttributeError, KeyError) as e:
        return None, ("error_values", {"file": "data.json", "msg": e}), False


# ---- スキンファイル ----
def skin_name_of(data: dict) -> str:
    name = data.get("skin")
    return str(name) if name else DEFAULT_SKIN


def skin_path(name: str):
    """スキン名からファイルを返す。標準スキンや、フォルダの外を指す名前なら None。"""
    if name == DEFAULT_SKIN or Path(name).name != name or name.startswith("."):
        return None
    return skins_dir() / f"{name}.json"


def skin_label(name: str) -> str:
    return f"skins/{name}.json"


def load_skin(name: str):
    """スキンの design を読む。(design, error)。標準スキンなら ({}, None)。"""
    if name == DEFAULT_SKIN:
        return {}, None
    path = skin_path(name)
    label = skin_label(name)
    missing = ("error_skin_missing", {"name": name, "file": label})
    if path is None:
        return {}, missing
    obj, error = read_json(path, label)
    if error:
        return {}, error
    if obj is None:
        return {}, missing
    if not isinstance(obj, dict):
        return {}, ("error_top", {"file": label})
    fmt = obj.get("format", SKIN_FORMAT)
    if not isinstance(fmt, int) or fmt > SKIN_FORMAT:
        return {}, ("error_skin_format", {"file": label})
    if not isinstance(obj.get("design"), dict):
        return {}, ("error_skin_design", {"file": label})
    return obj["design"], None


def list_skins() -> list:
    """skins フォルダのスキンを (名前, メニューに出す文言) の一覧で返す。"""
    result = []
    try:
        paths = sorted(skins_dir().glob("*.json"), key=lambda p: p.stem.lower())
    except OSError:
        return result
    for path in paths:
        name = path.stem
        if skin_path(name) is None:
            continue
        obj, _error = read_json(path, skin_label(name))
        label = name
        if isinstance(obj, dict) and isinstance(obj.get("name"), str) and obj["name"].strip():
            label = obj["name"].strip()
            if isinstance(obj.get("author"), str) and obj["author"].strip():
                label += f" — {obj['author'].strip()}"
        result.append((name, label))
    return result


def make_design(skin_design: dict, data: dict) -> dict:
    """標準スキン ← スキン の順に重ね、ウインドウの大きさは data.json から入れる。"""
    design = deep_update(copy.deepcopy(DEFAULT_DESIGN), skin_design)
    if not isinstance(design.get("window"), dict):
        design["window"] = {"bg": DEFAULT_DESIGN["window"]["bg"]}
    design["window"]["width"] = data["window"]["width"]
    design["window"]["height"] = data["window"]["height"]
    return design


# ---- 外部アプリで開く ----
def open_in_editor(path: Path) -> None:
    """テキストエディタで開く。"""
    try:
        if IS_MAC:
            # .json に割り当てたアプリで開く。割り当てが無ければテキストエディット
            if subprocess.run(["open", str(path)], capture_output=True).returncode != 0:
                subprocess.run(["open", "-t", str(path)], capture_output=True)
        elif IS_WIN:
            subprocess.Popen(["notepad.exe", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError as e:
        print(f"開けませんでした: {e}")


def reveal_in_folder(path: Path) -> None:
    """Finder / エクスプローラーでファイルを選んだ状態で表示する。"""
    try:
        if IS_MAC:
            subprocess.run(["open", "-R", str(path)], capture_output=True)
        elif IS_WIN:
            subprocess.Popen(f'explorer /select,"{path}"')
        else:
            subprocess.Popen(["xdg-open", str(path.parent)])
    except OSError as e:
        print(f"開けませんでした: {e}")


def open_folder(path: Path) -> None:
    try:
        if IS_MAC:
            subprocess.run(["open", str(path)], capture_output=True)
        elif IS_WIN:
            subprocess.Popen(["explorer", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError as e:
        print(f"開けませんでした: {e}")


# --------------------------------------------------------------------------
# macOS のメニューバーと表示言語
# --------------------------------------------------------------------------
# Tk はアプリメニューとウインドウメニューに英語固定の項目を自動で足す。
# 日本語のときは、項目のアクション (Objective-C のセレクタ) で見分けて書き換える
MAC_TK_ITEMS_JA = {
    "preferences:": "設定…",
    "hide:": "{app}を非表示",
    "hideOtherApplications:": "ほかを非表示",
    "unhideAllApplications:": "すべてを表示",
    "terminate:": "{app}を終了",
    "performMiniaturize:": "しまう",
    "performZoom:": "拡大/縮小",
    "selectPreviousTab:": "前のタブを表示",
    "selectNextTab:": "次のタブを表示",
    "moveTabToNewWindow:": "タブを新規ウインドウに移動",
    "mergeAllWindows:": "すべてのウインドウを結合",
    "arrangeInFront:": "すべてを手前に移動",
}
MAC_SERVICES_JA = "サービス"   # 「Services」はアクションを持たないサブメニューなので別扱い


class ObjC:
    """Objective-C ランタイムを ctypes で呼ぶための最小限のラッパー (PyObjC 不要)。"""

    def __init__(self):
        ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Foundation.framework/Foundation")
        lib = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        lib.objc_getClass.restype = ctypes.c_void_p
        lib.objc_getClass.argtypes = [ctypes.c_char_p]
        lib.sel_registerName.restype = ctypes.c_void_p
        lib.sel_registerName.argtypes = [ctypes.c_char_p]
        self._lib = lib
        self._msg_send = ctypes.cast(lib.objc_msgSend, ctypes.c_void_p).value
        self._protos = {}

    def cls(self, name: str):
        return self._lib.objc_getClass(name.encode())

    def sel(self, name: str):
        return self._lib.sel_registerName(name.encode())

    def send(self, obj, selector: str, *args, restype=ctypes.c_void_p, argtypes=()):
        # arm64 では objc_msgSend を引数の型どおりの関数として呼ぶ必要がある
        key = (restype, tuple(argtypes))
        if key not in self._protos:
            self._protos[key] = ctypes.CFUNCTYPE(
                restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)(self._msg_send)
        return self._protos[key](obj, self.sel(selector), *args)

    def to_str(self, nsstring) -> str:
        if not nsstring:
            return ""
        raw = self.send(nsstring, "UTF8String", restype=ctypes.c_char_p)
        return raw.decode("utf-8") if raw else ""

    def set_title(self, item, text: str) -> None:
        ns = self.send(self.cls("NSString"), "alloc")
        ns = self.send(ns, "initWithUTF8String:", text.encode("utf-8"),
                       argtypes=(ctypes.c_char_p,))
        self.send(item, "setTitle:", ns, restype=None, argtypes=(ctypes.c_void_p,))
        self.send(ns, "release", restype=None)

    def items(self, menu) -> list:
        count = self.send(menu, "numberOfItems", restype=ctypes.c_long)
        return [self.send(menu, "itemAtIndex:", i, argtypes=(ctypes.c_long,))
                for i in range(count)]


def mac_language(objc: ObjC) -> str:
    """OS の「優先する言語」の上から順に見て、対応している最初の言語を返す。

    macOS がアプリの表示言語を選ぶのと同じ決め方。システム設定のアプリごとの言語や
    起動引数 -AppleLanguages "(ja)" も反映される。
    """
    langs = objc.send(objc.cls("NSLocale"), "preferredLanguages")
    count = objc.send(langs, "count", restype=ctypes.c_ulong) if langs else 0
    for i in range(count):
        code = objc.to_str(objc.send(langs, "objectAtIndex:", i, argtypes=(ctypes.c_ulong,)))
        code = code.split("-")[0].lower()
        if code in UI_TEXT:
            return code
    return "en"


def detect_language(objc=None) -> str:
    """OS の言語設定から表示言語 (en / ja) を決める。"""
    try:
        if IS_MAC:
            return mac_language(objc) if objc else "en"
        if IS_WIN:
            # 下位 10 bit が主言語の ID。0x11 が日本語
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "ja" if langid & 0x3FF == 0x11 else "en"
        for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
            value = os.environ.get(key)
            if value:
                return "ja" if value.lower().startswith("ja") else "en"
    except (OSError, AttributeError, ctypes.ArgumentError):
        pass
    return "en"


def mac_app_name(objc: ObjC) -> str:
    """Tk がメニューに使うのと同じアプリ名 (CFBundleName、無ければプロセス名)。"""
    bundle = objc.send(objc.cls("NSBundle"), "mainBundle")
    key = objc.send(objc.cls("NSString"), "stringWithUTF8String:", b"CFBundleName",
                    argtypes=(ctypes.c_char_p,))
    name = objc.to_str(objc.send(bundle, "objectForInfoDictionaryKey:", key,
                                 argtypes=(ctypes.c_void_p,)))
    if not name:
        info = objc.send(objc.cls("NSProcessInfo"), "processInfo")
        name = objc.to_str(objc.send(info, "processName"))
    return name or APP_NAME


def hide_mac_window_title(objc: ObjC, title: str) -> None:
    """タイトルは残したまま、タイトルバーへの描画だけ止める (NSWindowTitleHidden)。

    名前はウインドウメニューや Mission Control には引き続き出る。
    """
    nsapp = objc.send(objc.cls("NSApplication"), "sharedApplication")
    windows = objc.send(nsapp, "windows")
    count = objc.send(windows, "count", restype=ctypes.c_ulong) if windows else 0
    for i in range(count):
        window = objc.send(windows, "objectAtIndex:", i, argtypes=(ctypes.c_ulong,))
        if objc.to_str(objc.send(window, "title")) == title:
            objc.send(window, "setTitleVisibility:", 1, restype=None, argtypes=(ctypes.c_long,))


def localize_mac_tk_items(objc: ObjC, app_name: str) -> None:
    """Tk が英語で足したメニュー項目を日本語にする。何度呼んでも結果は同じ。"""
    nsapp = objc.send(objc.cls("NSApplication"), "sharedApplication")
    main_menu = objc.send(nsapp, "mainMenu")
    if not main_menu:
        return
    services = objc.send(nsapp, "servicesMenu")
    titles = {objc.sel(s): t.format(app=app_name) for s, t in MAC_TK_ITEMS_JA.items()}
    for top in objc.items(main_menu):
        submenu = objc.send(top, "submenu")
        if not submenu:
            continue
        for item in objc.items(submenu):
            action = objc.send(item, "action")
            if action in titles:
                objc.set_title(item, titles[action])
            elif services and objc.send(item, "submenu") == services:
                objc.set_title(item, MAC_SERVICES_JA)


# --------------------------------------------------------------------------
# トグルスイッチ (Canvas で描画)
# --------------------------------------------------------------------------
class ToggleSwitch(tk.Canvas):
    PAD = 3

    def __init__(self, master, value=False, command=None, bg="#FFFFFF",
                 width=52, height=28, on_color="#34C759", off_color="#C7C7CC",
                 knob_color="#FFFFFF", knob_outline="#D0D0D0", radius=None):
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
        # Tk は None を渡すと既定の黒い縁を描くので、None は「縁なし」の "" にする
        self._knob_outline = knob_outline or ""
        # 角丸の半径。None なら高さの半分 (両端が半円の丸い形)、0 なら四角
        self._radius = height / 2 if radius is None else min(radius, height / 2)
        self._value = bool(value)
        self._command = command
        self._enabled = True
        self._after_id = None
        self._x = self._target_x()
        self._draw()
        self.bind("<Button-1>", lambda _e: self.toggle())
        # 読み直しで作り直されたとき、動きかけのアニメーションを止める
        self.bind("<Destroy>", lambda _e: self._cancel_animation())

    def _target_x(self) -> float:
        d = self.H - 2 * self.PAD
        return self.W - self.PAD - d if self._value else self.PAD

    def _draw(self) -> None:
        self.delete("all")
        w, h, pad, r = self.W, self.H, self.PAD, self._radius
        color = self._on_color if self._value else self._off_color
        # トラック
        if r >= h / 2:
            # 両端が半円の丸い形 (標準)
            self.create_oval(0, 0, h, h, fill=color, outline="")
            self.create_oval(w - h, 0, w, h, fill=color, outline="")
            self.create_rectangle(h / 2, 0, w - h / 2, h, fill=color, outline="")
        else:
            self._rounded_rect(0, 0, w, h, r, color, "")
        # つまみ。角はトラックの角から余白の分だけ小さくし、同心の形にそろえる
        d = h - 2 * pad
        x, kr = self._x, max(r - pad, 0)
        if kr >= d / 2:
            self.create_oval(x, pad, x + d, pad + d, fill=self._knob_color,
                             outline=self._knob_outline)
        else:
            self._rounded_rect(x, pad, x + d, pad + d, kr, self._knob_color, self._knob_outline)

    def _rounded_rect(self, x1, y1, x2, y2, r, fill, outline) -> None:
        """角丸の長方形。角は正確な円弧で描き、縁は継ぎ目が出ないよう線と弧で一周させる。"""
        if r <= 0:
            self.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline)
            return
        corners = ((x1 + r, y1 + r, 90), (x2 - r, y1 + r, 0),
                   (x2 - r, y2 - r, 270), (x1 + r, y2 - r, 180))
        # 塗り: 十字の 2 枚の長方形と、四隅の扇形
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
        self.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="")
        for cx, cy, start in corners:
            self.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=90,
                            style="pieslice", fill=fill, outline="")
        if not outline:
            return
        for cx, cy, start in corners:
            self.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=90,
                            style="arc", outline=outline)
        for line in ((x1 + r, y1, x2 - r, y1), (x2, y1 + r, x2, y2 - r),
                     (x1 + r, y2, x2 - r, y2), (x1, y1 + r, x1, y2 - r)):
            self.create_line(*line, fill=outline)

    def _cancel_animation(self) -> None:
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _animate(self) -> None:
        self._after_id = None
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
        self._cancel_animation()
        self._animate()
        if notify and self._command:
            self._command(self._value)

    def set_enabled(self, enabled: bool) -> None:
        """false の間はクリックしても切り替わらない (カーソルも通常の矢印にする)。"""
        self._enabled = bool(enabled)
        self.config(cursor=HAND_CURSOR if self._enabled else "")

    def toggle(self) -> None:
        if self._enabled:
            self.set(not self._value)


# --------------------------------------------------------------------------
# アプリ本体
# --------------------------------------------------------------------------
# design.header.align の値と、タイトルのラベルの anchor
HEADER_ANCHORS = {"left": "w", "center": "center", "right": "e"}

# data.json やスキンの値がおかしいときに画面作りで出うる例外
BUILD_ERRORS = (tk.TclError, TypeError, ValueError, KeyError, AttributeError)


def as_radius(value, name: str):
    """角丸の半径の設定。null か 0 以上の数でなければ、どのキーかが分かる例外にする。"""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{name}: {json.dumps(value, ensure_ascii=False)}"
                         " (null か 0 以上の数 / null or a number >= 0)")
    return value


def as_int(value, name: str) -> int:
    """数値の設定を int にする。できなければ、どのキーかが分かる例外にする。"""
    if isinstance(value, bool):
        raise ValueError(f"{name}: {json.dumps(value)}")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: {json.dumps(value, ensure_ascii=False)}") from None


class App(tk.Tk):
    SAVE_DELAY_MS = 500   # テキストボックスの入力は少し待ってからまとめて保存する
    POLL_MS = 1000        # data.json とスキンが外で書き換えられていないか見る間隔
    ERROR_BG, ERROR_FG = "#FF3B30", "#FFFFFF"

    def __init__(self):
        super().__init__()
        self.objc = None
        if IS_MAC:
            try:
                self.objc = ObjC()
            except OSError:
                pass
        self.lang = detect_language(self.objc)
        self.text = UI_TEXT[self.lang]

        self.data = None
        self.design = None       # 標準スキン + 選んだスキン + ウインドウの大きさ
        self.content = None      # ヘッダー・カード・フッターをまとめた Frame。読み直すと作り直す
        self.rows = []           # (item, スイッチ, ラベル)
        self.master_switch = None
        self._text_vars = []     # テキストボックスの StringVar を生かしておく
        self._fonts = []
        self._save_after_id = None
        self._data_error = None  # これがある間は data.json を上書きしない
        self._skin_error = None  # これがある間は標準スキンで表示している
        self._skin_stamp = None
        self._width_setting = self._height_setting = None

        # 旧形式からの移行で skins を作るより先に、サンプルを入れておく
        prepare_skins_dir()

        # data.json やスキンが読めないときに、上に出す帯
        self.banner = tk.Label(self, bg=self.ERROR_BG, fg=self.ERROR_FG,
                               justify="left", anchor="w", padx=16, pady=8)

        data, error, migrated = read_data_file()
        if data is None and error is None:     # 初回: 既定値で作る
            data = default_data()
            save_data(data)
        elif error:                            # 読めない: 上書きせず既定値で表示だけする
            data = default_data()
            self._data_error = error
        elif migrated:                         # 旧形式から移した
            save_data(data)
        self._file_stamp = file_stamp()

        build_error = self._render(data)
        if build_error:
            self._data_error = ("error_values", {"file": "data.json", "msg": build_error})
            self._render(default_data())
        self._show_errors(fit=False)

        if IS_MAC:
            self._build_mac_menubar()
        self._fit_window(keep_width=False)

        if IS_MAC and self.objc:
            # ウインドウが前面に来たときなどに Tk が手を入れ直すことがあるので、そのたびに直す
            self._on_mac_window_event()
            self.bind("<Map>", self._on_mac_window_event, add="+")
            self.bind("<FocusIn>", self._on_mac_window_event, add="+")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(self.POLL_MS, self._poll_files)

    # ---- 画面を作る ----
    def _render(self, data: dict):
        """data と、data が指すスキンで画面を作る。

        スキンが読めない・値がおかしいときは標準スキンで作り、_skin_error に理由を入れる。
        data.json 側の値がおかしくて作れなければ、前の画面のまま理由を返す。
        """
        name = skin_name_of(data)
        skin_design, skin_error = load_skin(name)
        skin_stamp = stamp_of(skin_path(name))
        error = self._apply(data, make_design(skin_design, data))
        if error and skin_design:
            # スキンのせいかもしれないので、標準スキンで作れるか試す
            if self._apply(data, make_design({}, data)) is None:
                skin_error = ("error_values", {"file": skin_label(name), "msg": error})
                error = None
        if error is None:
            self._skin_error, self._skin_stamp = skin_error, skin_stamp
        return error

    def _apply(self, data: dict, design: dict):
        """画面を作り直す。値がおかしくて作れなければ、前の画面のまま理由を返す。"""
        old = (self.data, self.design, self.rows, self.master_switch, self._text_vars, self._fonts)
        self.data, self.design = data, design
        self.rows, self._text_vars, self._fonts = [], [], []
        frame = tk.Frame(self)
        try:
            win = design["window"]
            width = as_int(win["width"], "window.width")
            height = None if win["height"] is None else as_int(win["height"], "window.height")
            self._build_content(frame)
        except BUILD_ERRORS as e:
            frame.destroy()
            (self.data, self.design, self.rows, self.master_switch,
             self._text_vars, self._fonts) = old
            if self.design:
                self.configure(bg=self.design["window"]["bg"])
            return str(e) or type(e).__name__
        if self.content is not None:
            self.content.destroy()
        self.content = frame
        frame.pack(fill="both", expand=True)
        self._width_setting, self._height_setting = width, height
        # タイトルはヘッダーに出すので、タイトルバーには出さない。
        # macOS は名前を残して描画だけ止める (_on_mac_window_event)。
        # Windows はタイトルバーの文字だけを消す標準の手段が無いので空にする
        self.title(data["title"] if IS_MAC else "")
        return None

    def _build_content(self, frame: tk.Frame) -> None:
        design = self.design
        win, header_d, row_d = design["window"], design["header"], design["row"]
        toggle_d, header_toggle_d = design["toggle"], design["header_toggle"]
        font_d = design["font"]
        radius = as_radius(toggle_d["radius"], "toggle.radius")

        self.configure(bg=win["bg"])
        frame.configure(bg=win["bg"])

        family = font_d["family"] or tkfont.nametofont("TkDefaultFont").actual("family")
        title_font = tkfont.Font(family=family, size=font_d["title_size"], weight="bold")
        self.text_font = tkfont.Font(family=family, size=font_d["text_size"])
        link_font = tkfont.Font(family=family, size=font_d["footer_size"])
        link_hover_font = tkfont.Font(family=family, size=font_d["footer_size"], underline=True)
        self._fonts = [title_font, self.text_font, link_font, link_hover_font]

        # ヘッダー: 左にタイトル、右端に一括 OFF スイッチ
        header = tk.Frame(frame, bg=header_d["bg"], padx=header_d["padding"],
                          pady=header_d["padding"] * 3 // 4)
        header.pack(fill="x")
        self.master_switch = ToggleSwitch(
            header,
            # 起動時にスライドして見えないよう、最初から状態を合わせておく
            value=any(t["value"] for t in self.data["toggles"]),
            command=self.on_master_toggle,
            bg=header_d["bg"],
            width=toggle_d["width"],
            height=toggle_d["height"],
            on_color=header_toggle_d["on_color"],
            off_color=header_toggle_d["off_color"],
            knob_color=header_toggle_d["knob_color"],
            knob_outline=header_toggle_d["knob_outline"],
            radius=radius,
        )
        align = header_d["align"]
        if align not in HEADER_ANCHORS:
            raise ValueError(f"header.align: {json.dumps(align, ensure_ascii=False)}"
                             f" ({' / '.join(HEADER_ANCHORS)})")
        # 先に右へ置き、タイトルが長くてもスイッチが押し出されないようにする
        self.master_switch.pack(side="right", padx=(header_d["padding"], 0))
        if align == "center":
            # スイッチと同じ幅の見えない余白を左に置き、ヘッダー全体の中央にそろえる
            tk.Frame(header, bg=header_d["bg"], height=1,
                     width=toggle_d["width"] + header_d["padding"]).pack(side="left")
        tk.Label(
            header, text=self.data["title"], bg=header_d["bg"], fg=header_d["fg"],
            font=title_font, anchor=HEADER_ANCHORS[align], justify=align,
        ).pack(side="left", fill="x", expand=True)

        # トグルの行を並べる白いカード
        card = tk.Frame(frame, bg=row_d["bg"])
        card.pack(fill="x", padx=16, pady=16)
        for i, item in enumerate(self.data["toggles"]):
            if i:
                tk.Frame(card, bg=row_d["separator"], height=1).pack(fill="x")
            self.rows.append(self._build_row(card, item))
        self._sync_master()

        # フッター: data.json を開く / フォルダを表示 / スキン
        footer = tk.Frame(frame, bg=win["bg"])
        footer.pack(fill="x", padx=16, pady=(0, 12))
        for key, command in (("open_file", lambda _e: self.open_data_file()),
                             ("show_folder", lambda _e: self.reveal_data_file()),
                             ("skin_menu", self._popup_skin_menu)):
            link = tk.Label(footer, text=self.text[key], font=link_font, cursor=HAND_CURSOR,
                            fg=design["footer"]["link_fg"], bg=win["bg"])
            link.pack(side="left", padx=(0, 16))
            link.bind("<Button-1>", command)
            link.bind("<Enter>", lambda _e, w=link: w.config(font=link_hover_font))
            link.bind("<Leave>", lambda _e, w=link: w.config(font=link_font))

    def _build_row(self, master, item: dict) -> tuple:
        """右端にトグル、その左に A / B のテキスト、必要ならその下にテキストボックス。"""
        row_d = self.design["row"]
        toggle_d = self.design["toggle"]
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
            self._sync_master()
            self.save()

        switch = ToggleSwitch(
            row,
            value=item["value"],
            command=on_toggle,
            bg=row_d["bg"],
            width=toggle_d["width"],
            height=toggle_d["height"],
            on_color=toggle_d["on_color"],
            off_color=toggle_d["off_color"],
            knob_color=toggle_d["knob_color"],
            knob_outline=toggle_d["knob_outline"],
            radius=as_radius(toggle_d["radius"], "toggle.radius"),
        )
        switch.grid(row=0, column=1, sticky="e")

        if item["textbox"]:
            self._build_textbox(row, item).grid(
                row=1, column=0, columnspan=2, sticky="we", pady=(pad * 2 // 3, 0))

        # 行の幅に合わせてテキストを折り返す。高さの自動計算に間に合うよう、
        # 最初は設定上のウィンドウ幅 (カードの左右余白 16 を引く) から求めておく
        def wrap_for(row_width: int) -> int:
            return max(row_width - toggle_d["width"] - 3 * pad, 60)

        label.config(wraplength=wrap_for(as_int(self.design["window"]["width"], "window.width") - 32))
        row.bind("<Configure>", lambda e: label.config(wraplength=wrap_for(e.width)))
        self.update_row(label, item)
        return item, switch, label

    def _build_textbox(self, master, item: dict) -> tk.Frame:
        """1 行のテキストボックス。入力内容は item["text"] に入れて保存する。"""
        tb_d = self.design["textbox"]
        if not isinstance(item["text"], str):
            item["text"] = ""

        # Entry は内側の余白を持てないので、枠線役の Frame で包む
        box = tk.Frame(master, bg=tb_d["bg"], highlightthickness=1,
                       highlightbackground=tb_d["border"], highlightcolor=tb_d["border"])
        var = tk.StringVar(self, value=item["text"])
        self._text_vars.append(var)
        entry = tk.Entry(
            box, textvariable=var, font=self.text_font,
            bg=tb_d["bg"], fg=tb_d["fg"], insertbackground=tb_d["fg"],
            relief="flat", borderwidth=0, highlightthickness=0,
        )
        entry.pack(fill="x", padx=8, pady=5)

        def set_border(color: str) -> None:
            box.config(highlightbackground=color, highlightcolor=color)

        entry.bind("<FocusIn>", lambda _e: set_border(tb_d["focus_border"]), add="+")
        entry.bind("<FocusOut>", lambda _e: set_border(tb_d["border"]), add="+")
        # 枠の余白部分をクリックしても入力できるように
        box.bind("<Button-1>", lambda _e: entry.focus_set())

        def on_text(*_args) -> None:
            item["text"] = var.get()
            self._schedule_save()

        var.trace_add("write", on_text)
        return box

    def _fit_window(self, keep_width: bool = True) -> None:
        """高さを中身 (か設定値) に合わせる。keep_width なら幅は今のまま。"""
        self.update_idletasks()
        width = self.winfo_width() if keep_width else self._width_setting
        height = self._height_setting or self.winfo_reqheight()
        self.geometry(f"{width}x{height}")
        self.minsize(280, min(height, 160))

    def _show_errors(self, fit: bool = True) -> None:
        """data.json やスキンの問題を上の帯に出す (無ければ消す)。"""
        lines = []
        for error, suffix in ((self._data_error, "suffix_data"), (self._skin_error, "suffix_skin")):
            if error:
                key, values = error
                lines.append(self.text[key].format(**values) + "\n" + self.text[suffix])
        if lines:
            self.banner.config(text="\n\n".join(lines),
                               wraplength=max((self._width_setting or 420) - 32, 200))
            if self.content is not None:
                self.banner.pack(fill="x", before=self.content)
            else:
                self.banner.pack(fill="x")
        else:
            self.banner.pack_forget()
        if fit:
            self._fit_window()

    # ---- スキンの選択 ----
    def _popup_skin_menu(self, event) -> None:
        menu = tk.Menu(self, tearoff=False)
        self._skin_var = tk.StringVar(self, value=skin_name_of(self.data))
        choices = [(DEFAULT_SKIN, self.text["skin_default"])] + list_skins()
        for name, label in choices:
            menu.add_radiobutton(label=label, value=name, variable=self._skin_var,
                                 command=lambda n=name: self.select_skin(n))
        menu.add_separator()
        menu.add_command(label=self.text["open_skins"], command=self.open_skins_folder)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def select_skin(self, name: str) -> None:
        if name == skin_name_of(self.data):
            return
        self.data["skin"] = name
        self.save()
        self._rerender_skin()

    def _rerender_skin(self) -> None:
        """今の data のまま、スキンだけ読み直して作り直す。"""
        self._render(self.data)
        self._show_errors(fit=False)
        self._fit_window(keep_width=True)
        if IS_MAC and self.objc:
            self._on_mac_window_event()

    # ---- macOS のメニューバー ----
    def _build_mac_menubar(self) -> None:
        """Tk 既定の英語メニュー (Source… / Run Widget Demo など) を、
        このアプリ用のメニューに置き換える。言語は OS の設定に合わせる。"""
        app_name = APP_NAME
        if self.objc:
            try:
                app_name = mac_app_name(self.objc)
            except (OSError, AttributeError, ctypes.ArgumentError):
                pass
        self._mac_app_name = app_name
        text = self.text

        menubar = tk.Menu(self)
        # name="apple" のメニューはアプリ名のメニューになる。
        # この後ろに Tk が「設定… / サービス / 非表示 / 終了」を足す
        app_menu = tk.Menu(menubar, name="apple", tearoff=False)
        app_menu.add_command(label=text["about"].format(app=app_name),
                             command=lambda: self.tk.call("::tk::mac::standardAboutPanel"))
        menubar.add_cascade(menu=app_menu)
        # 「設定…」(⌘,) は、このコマンドがあると有効になる
        self.createcommand("::tk::mac::ShowPreferences", self.open_data_file)

        # macOS の Tk ではアクセラレータは表示だけ。キー操作は bind や Tk 標準の
        # バインド (テキストボックスの ⌘X / ⌘C / ⌘V / ⌘A) が受け持つ
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label=text["close"], accelerator="Command-W",
                              command=self.on_close)
        menubar.add_cascade(label=text["file"], menu=file_menu)
        self.bind("<Command-w>", lambda _e: self.on_close())

        edit_menu = tk.Menu(menubar, tearoff=False)
        for key, accel, virtual in (("cut", "Command-X", "<<Cut>>"),
                                    ("copy", "Command-C", "<<Copy>>"),
                                    ("paste", "Command-V", "<<Paste>>"),
                                    (None, None, None),
                                    ("select_all", "Command-A", "<<SelectAll>>")):
            if key is None:
                edit_menu.add_separator()
                continue
            edit_menu.add_command(label=text[key], accelerator=accel,
                                  command=lambda v=virtual: self._send_to_focus(v))
        menubar.add_cascade(label=text["edit"], menu=edit_menu)

        # name="window" のメニューには Tk が「しまう / 拡大/縮小」などを足す
        window_menu = tk.Menu(menubar, name="window", tearoff=False)
        menubar.add_cascade(label=text["window"], menu=window_menu)
        self.config(menu=menubar)

    def _on_mac_window_event(self, _event=None) -> None:
        """タイトルバーの文字を隠し、日本語なら Tk が足した英語の項目を書き換える。"""
        try:
            hide_mac_window_title(self.objc, str(self.data["title"]))
            if self.lang == "ja":
                localize_mac_tk_items(self.objc, self._mac_app_name)
        except (OSError, AttributeError, ctypes.ArgumentError):
            pass

    def _send_to_focus(self, virtual_event: str) -> None:
        widget = self.focus_get()
        if widget is not None:
            widget.event_generate(virtual_event)

    # ---- 表示更新 ----
    def update_row(self, label: tk.Label, item: dict) -> None:
        row_d = self.design["row"]
        if item["value"]:
            label.config(text=item["b"], fg=row_d["fg"])
        else:
            label.config(text=item["a"], fg=row_d["fg_off"] or row_d["fg"])

    def _sync_master(self) -> None:
        """一括スイッチはリストのどれかが true の間だけ ON。全部 false なら OFF のまま動かない。"""
        any_on = any(item["value"] for item, _switch, _label in self.rows)
        self.master_switch.set(any_on, notify=False)
        self.master_switch.set_enabled(any_on)

    # ---- data.json・スキンとの同期 ----
    def save(self) -> None:
        """data.json に書く。ただし外での編集を上書きしない。スキンには書かない。"""
        if self._save_after_id:
            self.after_cancel(self._save_after_id)
            self._save_after_id = None
        if self._data_error:
            return  # 読めない (直している途中の) ファイルは上書きしない
        stamp = file_stamp()
        if stamp is not None and stamp != self._file_stamp:
            self._reload_from_file()  # 外で書き換えられていたら、そちらを優先する
            return
        if save_data(self.data):
            self._file_stamp = file_stamp()

    def _schedule_save(self) -> None:
        if self._save_after_id:
            self.after_cancel(self._save_after_id)
        self._save_after_id = self.after(self.SAVE_DELAY_MS, self._save_later)

    def _save_later(self) -> None:
        self._save_after_id = None
        self.save()

    def _poll_files(self) -> None:
        self.after(self.POLL_MS, self._poll_files)
        stamp = file_stamp()
        if stamp is not None and stamp != self._file_stamp:
            self._reload_from_file()
        elif stamp_of(skin_path(skin_name_of(self.data))) != self._skin_stamp:
            self._rerender_skin()

    def _reload_from_file(self) -> None:
        """外で書き換えられた data.json を読み直して画面を作り直す。"""
        self._file_stamp = file_stamp()
        if self._save_after_id:   # 保存待ちのアプリ側の入力より、外での編集を優先する
            self.after_cancel(self._save_after_id)
            self._save_after_id = None
        data, error, migrated = read_data_file()
        if data is None and error is None:
            return  # 消された: 次に保存するときに作り直す
        if error:
            self._data_error = error
            self._show_errors()
            return
        if migrated and save_data(data):
            self._file_stamp = file_stamp()
        old_width = self._width_setting
        build_error = self._render(data)
        self._data_error = (("error_values", {"file": "data.json", "msg": build_error})
                            if build_error else None)
        self._show_errors(fit=False)
        # 幅の設定が変わっていなければ、ユーザーが広げた幅をそのまま使う
        self._fit_window(keep_width=self._width_setting == old_width)
        if IS_MAC and self.objc:
            self._on_mac_window_event()

    # ---- イベント ----
    def open_data_file(self) -> None:
        if not DATA_FILE.exists():
            self.save()
        open_in_editor(DATA_FILE)

    def reveal_data_file(self) -> None:
        if not DATA_FILE.exists():
            self.save()
        reveal_in_folder(DATA_FILE)

    def open_skins_folder(self) -> None:
        try:
            skins_dir().mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        open_folder(skins_dir())

    def on_master_toggle(self, value: bool) -> None:
        """一括スイッチを OFF にしたら、リストのスイッチを全部 false にする (OFF 専用)。"""
        if value:
            self._sync_master()
            return
        for item, switch, label in self.rows:
            item["value"] = False
            switch.set(False, notify=False)
            self.update_row(label, item)
        self._sync_master()
        self.save()

    def on_close(self) -> None:
        self.save()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
