#!/bin/sh
# macOS 上で ToggleView.app と .dmg を作る
set -eu
cd "$(dirname "$0")"

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade "pip>=26.2"   # venv 同梱の古い pip を上げる
python -m pip install -r requirements-build.txt
pyinstaller --noconfirm --clean ToggleView.spec

hdiutil create -volname ToggleView -srcfolder dist/ToggleView.app \
  -ov -format UDZO dist/ToggleView-macos.dmg

echo "完成: dist/ToggleView.app / dist/ToggleView-macos.dmg"
