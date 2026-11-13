# toggle-widget

tkinter のトグル表示ウィジェット (`toggle_widget.py`) を PyInstaller で配布物にする。
PyInstaller はクロスコンパイルできないので、各 OS 上でビルドする。

| OS | 成果物 |
|---|---|
| Windows | `dist/toggle-widget.exe` (単一ファイル) |
| macOS | `dist/toggle-widget.app` と `toggle-widget-macos.dmg` |

## GitHub Actions でビルド

`.github/workflows/build.yml` が Windows / macOS ランナーで両方ビルドする。

- `v1.0.0` のようなタグを push すると、ビルド後にそのタグの Release が作られ、
  `toggle-widget-windows.zip` / `toggle-widget-macos.dmg` が添付される
- Actions 画面から `build` を手動実行した場合は Release は作らず、実行結果の Artifacts にだけ上がる
- macOS は `macos-latest` (Apple Silicon) 向け

## 手元でビルド

Python 3.10 以上 (tkinter 入り) が必要。

- Windows: `build_win.bat`
- macOS: `./build_mac.sh`
  - Homebrew の python を使う場合は `brew install python-tk` が必要
  - python.org のインストーラ版なら tkinter 同梱

## data.json の編集

中身 (タイトル・トグル・状態・ウインドウの大きさ) は data.json、見た目はスキン (後述) で決まる。

- 開き方: ウィジェット下の「data.json を開く」、macOS ならメニューの「設定…」(⌘,) でも開ける
  - macOS は .json に割り当てたアプリ (無ければテキストエディット)、Windows はメモ帳で開く
  - テキストエディットは `"` を「“ ”」に置き換えることがある。編集 → 自動置換 →「スマート引用符」を切っておくとよい
- 置き場所: macOS `~/Library/Application Support/toggle-widget/`、Windows `%APPDATA%\toggle-widget\`
- 保存すると、アプリを開いたままでも約 1 秒で反映される
- 書き間違えて読めないときは、ウィジェットの上に赤い帯で場所 (何行目何文字目) が出る。
  その間アプリはファイルを上書きしないので、直して保存すればよい
- ファイルを消すと、次に保存するとき既定の内容で作り直される

| キー | 内容 |
|---|---|
| `title` | ヘッダーのタイトル |
| `skin` | 使うスキンの名前 (`skins/<名前>.json`)。`"default"` は内蔵の標準スキン |
| `window` | `width` 幅 / `height` 高さ (null なら中身に合わせる) |
| `toggles[]` | トグルの行。上から順に並ぶ |
| `toggles[].a` / `.b` | スイッチが false / true のときの文言 |
| `toggles[].value` | スイッチの状態 (true / false) |
| `toggles[].textbox` | true なら行の下にテキストボックスを出す |
| `toggles[].text` | テキストボックスの内容 |

足りないキーは既定値で補われる。

以前の版の data.json (中に `design` があるもの) は、新しい版で初めて起動したときに自動で移す。
見た目を変えていなければ標準スキンに、変えていれば `skins/my-skin.json` を作ってそれを使う。

## スキン

見た目 (色・フォント・余白・スイッチの大きさ) を 1 つの JSON にまとめたもの。
data.json と同じフォルダの `skins/` に置くと、フッターの「スキン ▾」から選べる
(「スキンフォルダを開く」でそのフォルダが開く)。

```json
{
  "format": 1,
  "name": "Ocean",
  "author": "someone",
  "design": {
    "header": { "bg": "#0B3D5C" },
    "toggle": { "on_color": "#00B4D8" }
  }
}
```

- サンプルとしてダークモードの `skins/dark.json` を同梱している。初めて起動したとき (skins フォルダが無いとき) だけ
  ユーザーの skins フォルダにコピーされるので、自分のスキンを作るときの雛形にできる。消しても次の起動で戻らない
- ファイル名 (`ocean.json` なら `ocean`) が data.json の `skin` に入る名前。`name` / `author` はメニューの表示に使う
- `design` に書いたキーだけが標準スキンを上書きする。色だけ変えるスキンなら数行でよい
- `format` はスキンの形式の版 (今は 1)。アプリより新しい形式のスキンは読まない
- 使用中のスキンを保存すると、すぐ見た目に反映される (作りながら確かめられる)
- 読めない・値がおかしいスキンは赤い帯で知らせ、標準のスキンで表示する。アプリはスキンファイルに書き込まない
- スキンは JSON なので、他の人が作ったものを入れてもプログラムは実行されない

| キー | 内容 |
|---|---|
| `design.window` | 背景色 `bg` |
| `design.font` | `family` (null なら OS 標準) / `title_size` / `text_size` / `footer_size` |
| `design.header` | ヘッダーの `bg` / `fg` / `padding` / `align` (タイトルの位置: `"left"` / `"center"` / `"right"`) |
| `design.row` | 行の `bg` / `fg` / `fg_off` (false のときの文字色、null なら fg) / `padding` / `separator` |
| `design.toggle` | 行のスイッチの `width` / `height` / `radius` (角丸の半径。null なら丸い形、0 なら四角) / `on_color` / `off_color` / `knob_color` / `knob_outline` (つまみの縁の色、null なら縁なし)。大きさと形はヘッダーのスイッチにも使う |
| `design.header_toggle` | ヘッダーの一括 OFF スイッチの `on_color` / `off_color` / `knob_color` / `knob_outline` |
| `design.textbox` | テキストボックスの `bg` / `fg` / `border` / `focus_border` |
| `design.footer` | フッターのリンクの色 `link_fg` |

標準スキンの全部の値は `toggle_widget.py` の `DEFAULT_DESIGN` にある。

## 表示言語

メニューバー (macOS)・フッター・エラー表示・スキンメニューは OS の言語設定に合わせて日本語 / 英語になる。

- macOS: システム設定の「優先する言語」で、日本語が英語より上にあれば日本語。
  システム設定 → 一般 → 言語と地域 →「アプリケーション」で toggle-widget だけ言語を変えることもできる。
  試すとき: `open dist/toggle-widget.app --args -AppleLanguages "(ja)"`
- Windows: 表示言語が日本語なら日本語

## アイコン

元データは `assets/icon.svg`。変えたら macOS で次を実行し、できたファイルもコミットする
(ビルド時には作り直さない)。

```sh
pip install resvg-py pillow
python assets/build_icons.py                       # assets/icon.svg から作り直す
python assets/build_icons.py ~/Desktop/toggle.svg  # Illustrator から書き出した SVG を取り込んで作る
```

取り込むときは、埋め込み画像 (下絵) を外し、本体の角丸四角がアイコン格子 (1024 のうち 824) に
来るよう切り出し、角丸四角からはみ出した部分を切り取ってから `assets/icon.svg` に保存する。

`assets/icon.icns` (macOS の .app)・`assets/icon.ico` (Windows の .exe とウインドウ)・
`assets/icon.png` (1024x1024) ができる。

## 配布時の注意

署名していないので初回起動時に警告が出る。

- Windows: SmartScreen「WindowsによってPCが保護されました」→「詳細情報」→「実行」
- macOS: 一度開こうとした後、システム設定 → プライバシーとセキュリティ →「このまま開く」

## ライセンス

MIT
