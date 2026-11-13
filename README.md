# toggle-widget

tkinter のトグル表示ウィジェット (`toggle_widget.py`) を PyInstaller で配布物にする。
PyInstaller はクロスコンパイルできないので、各 OS 上でビルドする。

| OS | 成果物 |
|---|---|
| Windows | `dist/toggle-widget.exe` (単一ファイル) |
| macOS | `dist/toggle-widget.app` と `toggle-widget-macos.dmg` |

## GitHub Actions でビルド

`.github/workflows/build.yml` が Windows / macOS ランナーで両方ビルドする。

- `v1.0.0` のようなタグを push する、または Actions 画面から `build` を手動実行
- 実行結果の Artifacts に `toggle-widget-Windows` / `toggle-widget-macOS` が上がる
- macOS は `macos-latest` (Apple Silicon) 向け

## 手元でビルド

Python 3.10 以上 (tkinter 入り) が必要。

- Windows: `build_win.bat`
- macOS: `./build_mac.sh`
  - Homebrew の python を使う場合は `brew install python-tk` が必要
  - python.org のインストーラ版なら tkinter 同梱

## 配布時の注意

署名していないので初回起動時に警告が出る。

- Windows: SmartScreen「WindowsによってPCが保護されました」→「詳細情報」→「実行」
- macOS: 一度開こうとした後、システム設定 → プライバシーとセキュリティ →「このまま開く」

## ライセンス

MIT
