# -*- mode: python ; coding: utf-8 -*-
# PyInstaller ビルド定義 (Windows / macOS 共通)
#   pyinstaller --noconfirm --clean toggle-widget.spec
#
# - Windows : dist/toggle-widget.exe   (単一ファイル)
# - macOS   : dist/toggle-widget.app   (アプリバンドル)

import sys

APP_NAME = "toggle-widget"
VERSION = "1.0.0"
IS_MAC = sys.platform == "darwin"

a = Analysis(
    ["toggle_widget.py"],
    # サンプルスキン。初回起動時にユーザーの skins フォルダへコピーされる
    datas=[("skins/*.json", "skins")],
    # 使っていない標準ライブラリを外してサイズを減らす
    excludes=["unittest", "pydoc", "doctest", "test"],
)
pyz = PYZ(a.pure)

if IS_MAC:
    # macOS は onedir + BUNDLE で .app を作る (onefile の .app は非推奨)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        console=False,
        argv_emulation=False,
    )
    coll = COLLECT(exe, a.binaries, a.datas, name=APP_NAME)
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        bundle_identifier="com.eeenoooo.toggle-widget",
        info_plist={
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            # 日本語対応を宣言する。これで macOS 側が足すメニュー項目
            # (フルスクリーンなど) や「情報」パネルも日本語になり、
            # システム設定でアプリごとの言語も選べるようになる
            "CFBundleDevelopmentRegion": "en",
            "CFBundleLocalizations": ["en", "ja"],
        },
    )
else:
    # Windows は単一の .exe (コンソール窓なし)
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name=APP_NAME,
        console=False,
        upx=False,
    )
