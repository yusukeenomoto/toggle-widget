#!/bin/sh
# macOS 上で toggle-widget.app と .dmg を作る
set -eu
cd "$(dirname "$0")"

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade "pip>=26.2"   # venv 同梱の古い pip を上げる
python -m pip install -r requirements-build.txt
pyinstaller --noconfirm --clean toggle-widget.spec

hdiutil create -volname toggle-widget -srcfolder dist/toggle-widget.app \
  -ov -format UDZO dist/toggle-widget-macos.dmg

echo "完成: dist/toggle-widget.app / dist/toggle-widget-macos.dmg"
